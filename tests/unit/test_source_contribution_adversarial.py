"""Adversarial scientific values and original-row identities across regrouping."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

import pandas as pd
import pytest

from src.core.common.content_identity import content_signature
from src.core.common.source_contributions import (
    SOURCE_CONTRIBUTIONS_ATTR,
    inspect_source_contributions,
    require_source_contributions,
)
from src.core.common.typed_table_codec import TypedTableCodec
from src.core.services.shapers.pipeline_service import PipelineService


@pytest.mark.parametrize("categorical", [False, True], ids=["strings", "ordered-category"])
def test_multikey_mean_matches_original_rows_after_missing_and_category_sorting(
    categorical: bool,
) -> None:
    # [test->req~ring5.plots.drill-down~1]
    workloads = ["A", "B", "A", None, "B", None, "A", "B"]
    source = pd.DataFrame(
        {
            "workload": (
                pd.Categorical(workloads, categories=["B", "A", "unused"], ordered=True)
                if categorical
                else workloads
            ),
            "region": ["east", "west", "east", "east", "west", "east", None, None],
            "variant": ["s0", "s0", "s1", "s0", "s1", "s1", "s0", "s0"],
            "value": [2.0, 10.0, 6.0, 20.0, 14.0, 28.0, 8.0, 16.0],
        },
        index=[7, 7, 1, 1, 0, 0, 7, 7],
    )
    snapshot = source.copy(deep=True)
    result = PipelineService.process_pipeline(
        source,
        [
            {
                "type": "mean",
                "meanVars": ["value"],
                "meanAlgorithm": "arithmean",
                "groupingColumns": ["workload", "region"],
                "replacingColumn": "variant",
            }
        ],
        track_source_rows=True,
    )
    expected_by_workload = {
        "A": [("A", "east", 4.0, [0, 2]), ("A", None, 8.0, [6])],
        "B": [("B", "west", 12.0, [1, 4]), ("B", None, 16.0, [7])],
    }
    order = ["B", "A"] if categorical else ["A", "B"]
    expected: list[tuple[str | None, str | None, float, list[int]]] = [
        entry for workload in order for entry in expected_by_workload[workload]
    ]
    expected.append((None, "east", 24.0, [3, 5]))

    assert len(result) == len(source) + len(expected)
    pd.testing.assert_frame_equal(
        result.iloc[: len(source)].reset_index(drop=True), source.reset_index(drop=True)
    )
    relation = require_source_contributions(source, result)
    assert [relation.resolve([position]) for position in range(len(source))] == [
        [position] for position in range(len(source))
    ]
    for position, (workload, region, value, contributors) in enumerate(expected, start=len(source)):
        row = result.iloc[position]
        assert (None if pd.isna(row["workload"]) else row["workload"]) == workload
        assert (None if pd.isna(row["region"]) else row["region"]) == region
        assert row["variant"] == "arithmean"
        assert row["value"] == value
        assert relation.resolve([position]) == contributors

    restored = TypedTableCodec.decode(TypedTableCodec.encode(result))
    assert restored is not None
    pd.testing.assert_frame_equal(restored, result)
    assert require_source_contributions(source, restored) == relation
    pd.testing.assert_frame_equal(source, snapshot)


def test_pivot_longer_merge_unions_multiple_metrics_and_original_observations() -> None:
    source = pd.DataFrame(
        {
            "key": ["B", "A", "A"],
            "metric_a": [100.0, 1.0, 3.0],
            "metric_b": [200.0, 2.0, 4.0],
            "metric_c": [300.0, 5.0, 7.0],
        },
        index=[99, 2, 2],
    )
    snapshot = source.copy(deep=True)
    result = PipelineService.process_pipeline(
        source,
        [
            {
                "type": "pivotLonger",
                "id_vars": ["key"],
                "value_vars": ["metric_a", "metric_b", "metric_c"],
                "var_name": "metric",
                "value_name": "measurement",
                "extract_pattern": "metric_(a|b|c)",
                "extract_group_indices": [1],
                "selection_filters": {"1": ["a"]},
                "selection_strategy": "merge",
                "merge_label": "other",
            }
        ],
        track_source_rows=True,
    )
    assert result.columns.tolist() == ["key", "metric", "measurement"]
    assert result.to_dict("records") == [
        {"key": "A", "metric": "a", "measurement": 4.0},
        {"key": "A", "metric": "other", "measurement": 18.0},
        {"key": "B", "metric": "a", "measurement": 100.0},
        {"key": "B", "metric": "other", "measurement": 500.0},
    ]
    relation = require_source_contributions(source, result)
    assert [relation.resolve([position]) for position in range(4)] == [[1, 2], [1, 2], [0], [0]]
    assert relation.resolve([1, 0, 1, 3]) == [0, 1, 2]
    pd.testing.assert_frame_equal(source, snapshot)


def test_split_apply_join_combines_different_source_samples_and_retains_unmatched_keys() -> None:
    source = pd.DataFrame(
        {
            "benchmark": ["B", "A", "A", "B", "C", "D"],
            "variant": ["left", "left", "right", "right", "left", "right"],
            "a": [10.0, 2.0, 1000.0, 2000.0, 30.0, 3000.0],
            "b": [1000.0, 2000.0, 4.0, 20.0, 3000.0, 40.0],
        },
        index=[1, 1, 9, 9, 1, 9],
    )
    snapshot = source.copy(deep=True)
    groups: list[dict[str, Any]] = []
    for column, variant in [("a", "left"), ("b", "right")]:
        groups.append(
            {
                "columns": [column],
                "pipeline": [
                    {
                        "type": "itemSelector",
                        "column": "variant",
                        "strings": [variant],
                        "mode": "exact",
                    },
                    {
                        "type": "mean",
                        "meanVars": [column],
                        "meanAlgorithm": "arithmean",
                        "groupingColumns": ["benchmark"],
                        "replacingColumn": "variant",
                    },
                    {
                        "type": "itemSelector",
                        "column": "variant",
                        "strings": ["arithmean"],
                        "mode": "exact",
                    },
                ],
            }
        )
    result = PipelineService.process_pipeline(
        source,
        [{"type": "splitApply", "joinColumns": ["benchmark", "variant"], "groups": groups}],
        track_source_rows=True,
    )
    expected = pd.DataFrame(
        {
            "benchmark": ["A", "B", "C", "D"],
            "variant": ["arithmean"] * 4,
            "a": [2.0, 10.0, 30.0, float("nan")],
            "b": [4.0, 20.0, float("nan"), 40.0],
        }
    )
    pd.testing.assert_frame_equal(result, expected)
    relation = require_source_contributions(source, result)
    assert [relation.resolve([position]) for position in range(4)] == [[1, 2], [0, 3], [4], [5]]
    assert relation.resolve([1, 0, 3, 2, 1]) == list(range(6))
    pd.testing.assert_frame_equal(source, snapshot)


@pytest.mark.parametrize(
    ("corruption", "message"),
    [
        ("boolean-source-count", "row count"),
        ("boolean-root", "output roots"),
        ("negative-root", "output roots"),
        ("float-root", "output roots"),
        ("boolean-child", "invalid or cyclic"),
        ("self-reference", "invalid or cyclic"),
        ("forward-reference", "invalid or cyclic"),
        ("duplicate-children", "unique and sorted"),
        ("unordered-children", "unique and sorted"),
        ("checksum", "checksum"),
    ],
)
def test_structurally_invalid_or_reassigned_relations_fail_inspection_and_encoding(
    corruption: str, message: str
) -> None:
    source = pd.DataFrame({"value": [1.0, 2.0, 3.0]})
    result = PipelineService.process_pipeline(source, [], track_source_rows=True)
    payload = deepcopy(result.attrs[SOURCE_CONTRIBUTIONS_ATTR])
    if corruption == "boolean-source-count":
        payload["source_rows"] = True
    elif corruption == "boolean-root":
        payload["roots"][0] = True
    elif corruption == "negative-root":
        payload["roots"][0] = -1
    elif corruption == "float-root":
        payload["roots"][0] = 0.0
    elif corruption == "boolean-child":
        payload["unions"] = [[False, 1]]
        payload["roots"][0] = 3
    elif corruption == "self-reference":
        payload["unions"] = [[0, 3]]
        payload["roots"][0] = 3
    elif corruption == "forward-reference":
        payload["unions"] = [[0, 4], [0, 1]]
        payload["roots"][0] = 3
    elif corruption == "duplicate-children":
        payload["unions"] = [[0, 0]]
        payload["roots"][0] = 3
    elif corruption == "unordered-children":
        payload["unions"] = [[1, 0]]
        payload["roots"][0] = 3
    else:
        payload["roots"] = [1, 0, 2]
    if corruption != "checksum":
        payload["relation_identity"] = content_signature(
            {key: value for key, value in payload.items() if key != "relation_identity"}
        )
    result.attrs[SOURCE_CONTRIBUTIONS_ATTR] = payload

    with pytest.raises(ValueError, match=message):
        inspect_source_contributions(result)
    with pytest.raises(ValueError, match=message):
        TypedTableCodec.encode(result)
    assert source["value"].tolist() == [1.0, 2.0, 3.0]
    assert SOURCE_CONTRIBUTIONS_ATTR not in source.attrs


def _encoded_contribution_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Locate the current codec's declared relation without changing scientific cells."""
    attrs = payload["attrs"]
    assert attrs["type"] == "dict"
    relation = dict(attrs["items"])[SOURCE_CONTRIBUTIONS_ATTR]
    assert relation["type"] == "dict"
    return dict(relation["items"])


@pytest.mark.parametrize("corruption", ["boolean-root", "forward-reference", "checksum"])
def test_codec_decode_rejects_malformed_or_reassigned_contribution_wire_values(
    corruption: str,
) -> None:
    source = pd.DataFrame({"value": [1.0, 2.0, 3.0]})
    result = PipelineService.process_pipeline(source, [], track_source_rows=True)
    encoded = TypedTableCodec.encode(result)
    assert encoded is not None
    fields = _encoded_contribution_fields(encoded)
    if corruption == "boolean-root":
        fields["roots"]["items"][0] = True
        message = "output roots"
    elif corruption == "forward-reference":
        fields["roots"]["items"][0] = 3
        fields["unions"]["items"] = [
            {"type": "list", "items": [0, 4]},
            {"type": "list", "items": [0, 1]},
        ]
        message = "invalid or cyclic"
    else:
        fields["roots"]["items"] = [1, 0, 2]
        message = "checksum"
    with pytest.raises(ValueError, match=message):
        TypedTableCodec.decode(encoded)
    assert require_source_contributions(source, result).resolve([0, 1, 2]) == [0, 1, 2]
