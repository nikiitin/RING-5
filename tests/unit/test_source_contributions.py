"""Exact, bounded original-row mappings for every built-in pipeline strategy."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pandas as pd
import pytest

from src.core.common.source_contributions import (
    SOURCE_CONTRIBUTIONS_ATTR,
    contribution_frame_identity,
    inspect_source_contributions,
    require_source_contributions,
)
from src.core.common.typed_table_codec import TypedTableCodec
from src.core.services.shapers.pipeline_service import PipelineService, PipelineStepError


@pytest.fixture
def contribution_source() -> pd.DataFrame:
    """Distinct source observations with deliberately duplicated caller indexes."""
    return pd.DataFrame(
        {
            "benchmark": ["A", "A", "B", "B"],
            "variant": ["base", "fast", "base", "fast"],
            "value": [2.0, 4.0, 3.0, 9.0],
            "other": [4.0, 8.0, 6.0, 18.0],
            "seed": [0, 1, 0, 0],
            "flag": [0, 2, 1, 2],
            "token": ["0", "1", "2", "3"],
        },
        index=[9, 9, 2, 2],
    )


_CASES: list[tuple[dict[str, Any], list[list[int]]]] = [
    ({"type": "columnSelector", "columns": ["benchmark", "value"]}, [[0], [1], [2], [3]]),
    (
        {"type": "conditionSelector", "column": "value", "mode": "greater_than", "threshold": 3.0},
        [[1], [3]],
    ),
    (
        {"type": "itemSelector", "column": "variant", "strings": ["fast"], "mode": "exact"},
        [[1], [3]],
    ),
    (
        {
            "type": "groupCardinalitySelector",
            "groupBy": ["benchmark"],
            "countColumn": "seed",
            "count": 2,
            "mode": "eq",
        },
        [[0], [1]],
    ),
    (
        {
            "type": "groupPredicateSelector",
            "groupBy": ["benchmark"],
            "baselineColumn": "variant",
            "baselineValue": "base",
            "predicateColumn": "flag",
            "drop_when": "zero_or_nan",
            "action": "drop",
        },
        [[2], [3]],
    ),
    (
        {"type": "sort", "order_dict": {"benchmark": ["B", "A"], "variant": ["fast", "base"]}},
        [[3], [2], [1], [0]],
    ),
    ({"type": "transformer", "column": "token", "target_type": "scalar"}, [[0], [1], [2], [3]]),
    (
        {"type": "deriveColumn", "dest": "ratio", "sources": ["value", "other"], "op": "ratio"},
        [[0], [1], [2], [3]],
    ),
    (
        {
            "type": "mean",
            "meanVars": ["value"],
            "meanAlgorithm": "arithmean",
            "groupingColumns": ["benchmark"],
            "replacingColumn": "variant",
        },
        [[0], [1], [2], [3], [0, 1], [2, 3]],
    ),
    (
        {
            "type": "normalize",
            "normalizeVars": ["value"],
            "normalizerColumn": "variant",
            "normalizerValue": "base",
            "groupBy": ["benchmark"],
        },
        [[0], [0, 1], [2], [2, 3]],
    ),
    (
        {
            "type": "pivotLonger",
            "id_vars": ["benchmark", "variant"],
            "value_vars": ["value", "other"],
            "var_name": "metric",
            "value_name": "measurement",
        },
        [[0], [1], [2], [3], [0], [1], [2], [3]],
    ),
    (
        {"type": "pivotWider", "index": ["benchmark"], "columns": "variant", "values": "value"},
        [[0, 1], [2, 3]],
    ),
    (
        {
            "type": "splitApply",
            "joinColumns": ["benchmark", "variant"],
            "groups": [
                {
                    "columns": ["value"],
                    "pipeline": [
                        {
                            "type": "conditionSelector",
                            "column": "value",
                            "mode": "greater_than",
                            "threshold": 3.0,
                        }
                    ],
                },
                {"columns": ["other"], "pipeline": []},
            ],
        },
        [[0], [1], [2], [3]],
    ),
]


@pytest.mark.parametrize(("config", "expected"), _CASES, ids=[case[0]["type"] for case in _CASES])
def test_all_builtin_shapers_preserve_exact_original_contributors(
    contribution_source: pd.DataFrame, config: dict[str, Any], expected: list[list[int]]
) -> None:
    # [test->req~ring5.plots.drill-down~1]
    source = contribution_source
    snapshot = source.copy(deep=True)
    ordinary = PipelineService.process_pipeline(source, [config])
    traced = PipelineService.process_pipeline(source, [config], track_source_rows=True)
    assert contribution_frame_identity(traced) == contribution_frame_identity(ordinary)
    relation = require_source_contributions(source, traced)
    assert [relation.resolve([position]) for position in range(len(traced))] == expected
    pd.testing.assert_frame_equal(source, snapshot)
    encoded = TypedTableCodec.encode(traced)
    restored = TypedTableCodec.decode(encoded)
    assert restored is not None
    assert require_source_contributions(source, restored) == relation


@pytest.mark.parametrize("algorithm", ["arithmean", "geomean", "hmean"])
def test_mean_labels_select_original_samples_and_mapping_survives_numerical_cache(
    contribution_source: pd.DataFrame, algorithm: str
) -> None:
    pipeline = [
        {
            "type": "mean",
            "meanVars": ["value"],
            "meanAlgorithm": algorithm,
            "groupingColumns": ["benchmark"],
            "replacingColumn": "variant",
        },
        {"type": "itemSelector", "column": "variant", "strings": [algorithm], "mode": "exact"},
    ]
    for original in (contribution_source, contribution_source.assign(token=["a", "b", "c", "d"])):
        result = PipelineService.process_pipeline(original, pipeline, track_source_rows=True)
        relation = require_source_contributions(original, result)
        assert relation.resolve([0]) == [0, 1]
        assert relation.resolve([1]) == [2, 3]
        assert relation.resolve([0, 1, 0]) == [0, 1, 2, 3]


def test_pivot_wider_keeps_only_first_nonmissing_cell_contributors() -> None:
    source = pd.DataFrame(
        {
            "key": ["A"] * 5,
            "variant": ["a", "a", "a", "b", "b"],
            "value": [float("nan"), 2.0, 99.0, 3.0, 88.0],
        }
    )
    result = PipelineService.process_pipeline(
        source,
        [{"type": "pivotWider", "index": ["key"], "columns": "variant", "values": "value"}],
        track_source_rows=True,
    )
    assert require_source_contributions(source, result).resolve([0]) == [1, 3]
    assert result.loc[0, ["a", "b"]].tolist() == [2.0, 3.0]


@pytest.mark.parametrize("strategy", ["discard", "merge"])
def test_pivot_longer_extraction_tracks_actual_discard_and_merge(strategy: str) -> None:
    source = pd.DataFrame({"key": ["A", "B"], "metric_a": [2.0, 3.0], "metric_b": [4.0, 5.0]})
    config = {
        "type": "pivotLonger",
        "id_vars": ["key"],
        "value_vars": ["metric_a", "metric_b"],
        "var_name": "metric",
        "value_name": "value",
        "extract_pattern": "metric_(a|b)",
        "extract_group_indices": [1],
        "selection_filters": {"1": ["a"]},
        "selection_strategy": strategy,
        "merge_label": "other",
    }
    result = PipelineService.process_pipeline(source, [config], track_source_rows=True)
    relation = require_source_contributions(source, result)
    for position, row in enumerate(result.itertuples(index=False)):
        assert relation.resolve([position]) == [0 if row.key == "A" else 1]
    assert len(result) == (2 if strategy == "discard" else 4)


def test_nested_split_apply_unions_aggregate_and_outer_join_sources(
    contribution_source: pd.DataFrame,
) -> None:
    aggregate = [
        {
            "type": "mean",
            "meanVars": ["value"],
            "meanAlgorithm": "arithmean",
            "groupingColumns": ["benchmark"],
            "replacingColumn": "variant",
        },
        {"type": "itemSelector", "column": "variant", "strings": ["arithmean"], "mode": "exact"},
    ]
    config = {
        "type": "splitApply",
        "joinColumns": ["benchmark", "variant"],
        "groups": [
            {
                "columns": ["value", "flag"],
                "pipeline": [
                    {
                        "type": "splitApply",
                        "joinColumns": ["benchmark", "variant"],
                        "groups": [
                            {"columns": ["value"], "pipeline": aggregate},
                            {"columns": ["flag"], "pipeline": []},
                        ],
                    }
                ],
            },
            {"columns": ["other"], "pipeline": []},
        ],
    }
    result = PipelineService.process_pipeline(contribution_source, [config], track_source_rows=True)
    ordinary = PipelineService.process_pipeline(contribution_source, [config])
    assert contribution_frame_identity(result) == contribution_frame_identity(ordinary)
    assert len(result) == 6
    means = result.loc[result["variant"].eq("arithmean")]
    assert means["benchmark"].tolist() == ["A", "B"]
    assert means["value"].tolist() == [3.0, 6.0]
    assert means[["flag", "other"]].isna().all().all()
    originals = result.loc[result["variant"].ne("arithmean")]
    assert originals["value"].isna().all()
    pd.testing.assert_frame_equal(
        originals[["benchmark", "variant", "flag", "other"]].reset_index(drop=True),
        contribution_source[["benchmark", "variant", "flag", "other"]].reset_index(drop=True),
        check_dtype=False,
    )
    assert contribution_source["value"].tolist() == [2.0, 4.0, 3.0, 9.0]
    relation = require_source_contributions(contribution_source, result)
    for position, row in enumerate(result.itertuples(index=False)):
        if row.variant == "arithmean":
            assert relation.resolve([position]) == ([0, 1] if row.benchmark == "A" else [2, 3])
        else:
            expected = [
                index
                for index, original in enumerate(contribution_source.itertuples())
                if original.benchmark == row.benchmark and original.variant == row.variant
            ]
            assert relation.resolve([position]) == expected


@pytest.mark.parametrize("corruption", ["version", "root", "cycle", "identity", "missing"])
def test_invalid_or_missing_source_proof_is_a_visible_error(
    contribution_source: pd.DataFrame, corruption: str
) -> None:
    result = PipelineService.process_pipeline(contribution_source, [], track_source_rows=True)
    payload = deepcopy(result.attrs[SOURCE_CONTRIBUTIONS_ATTR])
    if corruption == "version":
        payload["version"] = True
    elif corruption == "root":
        payload["roots"][0] = 999999
    elif corruption == "cycle":
        payload["unions"] = [[0, len(contribution_source)]]
    elif corruption == "identity":
        payload["source_identity"] = "sha256:" + "0" * 64
    else:
        result.attrs.pop(SOURCE_CONTRIBUTIONS_ATTR)
    if corruption != "missing":
        result.attrs[SOURCE_CONTRIBUTIONS_ATTR] = payload
    with pytest.raises(ValueError, match="contribution|provenance"):
        require_source_contributions(contribution_source, result)


def test_source_and_output_edits_invalidate_their_exact_fingerprints(
    contribution_source: pd.DataFrame,
) -> None:
    result = PipelineService.process_pipeline(contribution_source, [], track_source_rows=True)
    changed = contribution_source.copy()
    changed.iloc[0, changed.columns.get_loc("value")] = 999.0
    with pytest.raises(ValueError, match="input identity"):
        require_source_contributions(changed, result)
    result.iloc[0, result.columns.get_loc("value")] = 999.0
    with pytest.raises(ValueError, match="output identity"):
        inspect_source_contributions(result)
    with pytest.raises(ValueError, match="output identity"):
        TypedTableCodec.encode(result)


def test_unknown_mapper_fails_without_fabricating_a_relation(
    contribution_source: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.core.services.shapers.factory import ShaperFactory

    monkeypatch.setattr(ShaperFactory, "create_shaper", lambda *args: object())
    with pytest.raises(PipelineStepError, match="does not define exact source contributions"):
        PipelineService.process_pipeline(
            contribution_source, [{"type": "sort", "order_dict": {}}], track_source_rows=True
        )
