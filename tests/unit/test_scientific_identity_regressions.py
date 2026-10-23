"""Scientific identity, uncertainty and immutable transformation contracts."""

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from ring5 import Table
from ring5.errors import PipelineError
from src.core.models import ColumnSemantics, DatasetSemantics
from src.core.services.managers.semantic_metadata_service import SemanticMetadataService
from src.core.services.shapers.impl.mean import Mean
from src.core.services.shapers.impl.normalize import Normalize
from src.core.services.shapers.impl.sort import Sort
from src.core.services.shapers.impl.split_apply import SplitApply


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "config": ["base", "test"],
            "bench": ["B", "B"],
            "value": [10.0, 20.0],
            "value.sd": [1.0, 2.0],
            "label": ["old", "old"],
        }
    )


@pytest.mark.parametrize("kind", ["mean", "normalize"])
def test_caches_follow_retained_columns_uncertainty_index_and_semantics(kind: str) -> None:
    def make_shaper() -> Mean | Normalize:
        if kind == "mean":
            return Mean(
                {
                    "meanVars": ["value"],
                    "meanAlgorithm": "arithmean",
                    "groupingColumns": ["bench"],
                    "replacingColumn": "config",
                }
            )
        return Normalize(
            {
                "normalizeVars": ["value"],
                "normalizerColumn": "config",
                "normalizerValue": "base",
                "groupBy": ["bench"],
            }
        )

    before = _frame()
    before.attrs = {"units": {"value": "ms"}}
    make_shaper()(before)
    after = before.copy()
    after["value.sd"] = [4.0, 8.0]
    after["label"] = "new"
    after.index = [10, 11]
    after.attrs = {"units": {"value": "s"}}
    result = make_shaper()(after)
    assert result["label"].eq("new").all()
    assert result.attrs == after.attrs
    if kind == "normalize":
        assert result.index.tolist() == [10, 11]
        assert result["value.sd"].tolist() == [0.4, 0.8]
    else:
        assert result["value.sd"].iloc[-1] == pytest.approx(np.sqrt(80) / 2)


@pytest.mark.parametrize("errors", [[np.nan, np.nan], [1.0, np.nan]])
def test_mean_preserves_unknown_uncertainty(errors: list[float]) -> None:
    frame = _frame()
    frame["value.sd"] = errors
    shaper = Mean(
        {
            "meanVars": ["value"],
            "meanAlgorithm": "arithmean",
            "groupingColumns": ["bench"],
            "replacingColumn": "config",
        }
    )
    result = shaper(frame)
    assert result["value"].iloc[-1] == 15.0
    assert pd.isna(result["value.sd"].iloc[-1])


def test_normalization_preserves_duplicate_row_indexes_and_missing_groups() -> None:
    frame = pd.concat([_frame(), _frame()], ignore_index=True)
    frame["bench"] = ["B", None, "B", None]
    frame["config"] = ["base", "base", "test", "test"]
    frame.index = [5, 5, 5, 5]
    result = Normalize(
        {
            "normalizeVars": ["value"],
            "normalizerColumn": "config",
            "normalizerValue": "base",
            "groupBy": ["bench"],
        }
    )(frame)
    assert result.index.tolist() == frame.index.tolist()
    assert result["value"].tolist() == [1.0, 1.0, 1.0, 1.0]
    assert result["bench"].tolist() == frame["bench"].tolist()


@pytest.mark.parametrize(
    "source,target,value,sd,expected,expected_sd",
    [
        ("ms", "s", 1000.0, 100.0, 1.0, 0.1),
        ("°C", "°F", 0.0, 10.0, 32.0, 18.0),
    ],
)
def test_unit_conversion_scales_uncertainty_without_offsets(
    source: str, target: str, value: float, sd: float, expected: float, expected_sd: float
) -> None:
    frame = SemanticMetadataService.attach(
        pd.DataFrame({"metric": [value], "metric.sd": [sd]}),
        DatasetSemantics(
            (
                ColumnSemantics("metric", "Metric", source),
                ColumnSemantics("metric.sd", "Error", source),
            )
        ),
    )
    original = frame.copy(deep=True)
    converted = SemanticMetadataService.convert(frame, "metric", target)
    assert converted["metric"].iloc[0] == pytest.approx(expected)
    assert converted["metric.sd"].iloc[0] == pytest.approx(expected_sd)
    assert SemanticMetadataService.inspect(converted).for_column("metric.sd").unit == target
    assert_frame_equal(frame, original)


def test_split_apply_refuses_ambiguous_alignment() -> None:
    frame = pd.DataFrame({"bench": ["B", "B"], "x": [10, 20], "y": [1, 2]})
    shaper = SplitApply(
        {
            "joinColumns": ["bench"],
            "groups": [{"columns": ["x"], "pipeline": []}, {"columns": ["y"], "pipeline": []}],
        }
    )
    with pytest.raises(ValueError, match="duplicate join keys"):
        shaper(frame)


def test_table_defends_its_owned_frame_even_when_a_transform_fails() -> None:
    table = Table.from_rows([{"x": 1}])

    def mutate_then_fail(frame: pd.DataFrame) -> pd.DataFrame:
        frame["x"] = 999
        raise ValueError("rejected")

    with pytest.raises(PipelineError, match="rejected"):
        table.apply(mutate_then_fail)
    assert table.rows() == [{"x": 1}]


def test_sort_preserves_nulls_dtypes_ties_and_duplicate_indexes() -> None:
    frame = pd.DataFrame({"label": ["b", None, "a", "a"], "row": [0, 1, 2, 3]}, index=[7, 7, 7, 7])
    result = Sort({"order_dict": {"label": ["a", "b"]}})(frame)
    assert result["row"].tolist() == [2, 3, 0, 1]
    assert pd.isna(result["label"].iloc[-1])
    assert result["row"].dtype == frame["row"].dtype
    rows = [{"key": i % 3, "position": i} for i in range(100)]
    sorted_table = Table.from_rows(rows).sort(["key"]).rows()
    assert sorted_table == sorted(rows, key=lambda row: row["key"])


def test_transformer_partial_order_preserves_labels_and_missingness() -> None:
    from src.core.services.shapers.impl.transformer import Transformer

    frame = pd.DataFrame({"label": ["a", "b", None]})
    result = Transformer({"column": "label", "target_type": "factor", "order": ["a"]})(frame)
    assert result["label"].iloc[:2].tolist() == ["a", "b"]
    assert pd.isna(result["label"].iloc[2])
    assert list(result["label"].cat.categories) == ["a", "b"]


@pytest.mark.parametrize("baseline", [0.0, np.nan, np.inf, -np.inf])
def test_normalization_keeps_undefined_ratios_missing(baseline: float) -> None:
    frame = _frame()
    frame.loc[0, "value"] = baseline
    result = Normalize(
        {
            "normalizeVars": ["value"],
            "normalizerColumn": "config",
            "normalizerValue": "base",
            "groupBy": ["bench"],
        }
    )(frame)
    assert result["value"].isna().all()
    assert result["value.sd"].isna().all()


def test_normalization_missing_sum_component_and_negative_error_scale() -> None:
    frame = _frame()
    frame["other"] = [np.nan, 10.0]
    params = {
        "normalizeVars": ["value"],
        "normalizerVars": ["value", "other"],
        "normalizerColumn": "config",
        "normalizerValue": "base",
        "groupBy": ["bench"],
    }
    assert Normalize(params)(frame)["value"].isna().all()
    frame["other"] = [-20.0, 10.0]
    result = Normalize(params)(frame)
    assert result["value"].tolist() == [-1.0, -2.0]
    assert result["value.sd"].tolist() == [0.1, 0.2]


@pytest.mark.parametrize("kind", ["mean", "normalize"])
@pytest.mark.parametrize(
    "changed", ["column_axis_name", "typed_attrs", "object_values", "category_order"]
)
def test_cached_shapers_preserve_typed_retained_identity(kind: str, changed: str) -> None:
    frame = _frame()
    frame["retained"] = pd.Series([1, 1], dtype=object)
    frame.attrs = {"units": ("cycles",)}
    frame["category"] = pd.Categorical(["a", "b"], categories=["a", "b"], ordered=True)
    shaper = (
        Mean(
            {
                "meanVars": ["value"],
                "meanAlgorithm": "arithmean",
                "groupingColumns": ["bench"],
                "replacingColumn": "config",
            }
        )
        if kind == "mean"
        else Normalize(
            {
                "normalizeVars": ["value"],
                "normalizerColumn": "config",
                "normalizerValue": "base",
                "groupBy": ["bench"],
            }
        )
    )
    shaper(frame)
    other = frame.copy(deep=True)
    if changed == "column_axis_name":
        other.columns.name = "alternate"
    elif changed == "typed_attrs":
        other.attrs = {"units": ["cycles"]}
    elif changed == "object_values":
        other["retained"] = pd.Series(["1", "1"], dtype=object)
    else:
        other["category"] = other["category"].cat.reorder_categories(["b", "a"])
    result = shaper(other)
    assert result.attrs == other.attrs
    assert type(result["retained"].iloc[0]) is type(other["retained"].iloc[0])
    assert result.columns.name == other.columns.name
    if kind == "normalize":
        assert list(result["category"].cat.categories) == list(other["category"].cat.categories)
    else:
        # Mean may widen a categorical metadata column when appending its aggregate.
        assert result["category"].iloc[:2].tolist() == other["category"].tolist()


@pytest.mark.parametrize("kind", ["extended_scalar", "cyclic_metadata"])
def test_unsupported_metadata_bypasses_cache_without_recursive_failure(kind: str) -> None:
    from src.core.performance import compute_data_fingerprint

    frame = _frame()
    if kind == "extended_scalar":
        frame.attrs = {"precision": np.longdouble("1.25")}
    else:
        cycle: list[object] = []
        cycle.append(cycle)
        frame.attrs = {"cycle": cycle}
    first = compute_data_fingerprint(frame, {}, ["value"])
    second = compute_data_fingerprint(frame, {}, ["value"])
    assert first != second
