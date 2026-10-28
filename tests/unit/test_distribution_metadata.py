"""Reserved Distribution declarations follow explicit coordinate-preserving policies."""

from copy import deepcopy
from collections.abc import Mapping, Sequence
from dataclasses import replace
from unittest.mock import patch
from typing import Literal, Required, TypedDict, cast

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from ring5 import ColumnSemantics, DatasetSemantics, Session, Table
from ring5.errors import DataLoadError, DataValidationError, PipelineError
from src.core.common import distribution_metadata as metadata
from src.core.common.dataframe_copy import copy_dataframe
from src.core.common.distribution_metadata import (
    DISTRIBUTION_LAYOUTS_ATTR,
    concat_distribution_layouts,
    inspect_distribution_layouts,
    preserve_distribution_layouts,
    with_distribution_layouts,
)
from src.core.common.typed_table_codec import TypedTableCodec
from src.core.models.distribution_geometry import DistributionGeometry, native_bucket_label
from src.core.models.native_distribution_layout import (
    DistributionColumn,
    NativeDistributionLayout,
    OpaqueDistributionLayout,
)
from src.core.services.managers.dataset_workspace_service import DatasetWorkspaceService
from src.core.services.managers.arithmetic_service import ArithmeticService
from src.core.services.managers.semantic_metadata_service import SemanticMetadataService
from src.core.services.shapers.impl.sort import Sort
from src.core.services.shapers.definition import ShaperDefinition, validate_sort
from src.core.services.shapers.factory import ShaperFactory
from src.core.services.shapers.pipeline_service import PipelineService, PipelineStepError
from src.core.state.repositories.data_repository import DataRepository


def _native(prefix: str = "x", *, maximum: float = 1.0) -> NativeDistributionLayout:
    geometry = DistributionGeometry(0, maximum, 1)
    columns = [DistributionColumn(f"{prefix}-tail-low", "underflows", "underflow", None)]
    columns.extend(
        DistributionColumn(
            f"{prefix}-slot-{index}", native_bucket_label(geometry, index), "bucket", index
        )
        for index in range(geometry.bucket_count)
    )
    columns.extend(
        [
            DistributionColumn(f"{prefix}-tail-high", "overflows", "overflow", None),
            DistributionColumn(f"{prefix}-summary", "mean", "summary", None),
        ]
    )
    return NativeDistributionLayout(geometry, "missing", tuple(columns))


def _frame() -> pd.DataFrame:
    native = _native()
    opaque = OpaqueDistributionLayout((DistributionColumn("literal", "0-1", "source", None),))
    frame = pd.DataFrame(
        {
            "bench": ["b", "a", "b", "a"],
            "config": ["base", "base", "other", "other"],
            "group": ["all"] * 4,
            **{binding.column: [1.0, 2.0, 3.0, 4.0] for binding in native.columns},
            "literal": pd.Series([1, 2, 3, 4], dtype="Int64"),
        }
    )
    frame.attrs["unrelated"] = {"owned": [1]}
    return with_distribution_layouts(frame, {"logical": native, "selected": opaque})


def _names(frame: pd.DataFrame) -> set[str]:
    return set(inspect_distribution_layouts(frame))


def _run(frame: pd.DataFrame, step: dict) -> pd.DataFrame:
    return PipelineService.process_pipeline(frame, [step])


def test_metadata_uses_explicit_arbitrary_bindings_and_owns_primitive_payloads() -> None:
    frame = _frame()
    before = deepcopy(frame.attrs)
    layout = inspect_distribution_layouts(frame)["logical"]
    assert [column.column for column in layout.columns] == [
        "x-tail-low",
        "x-slot-0",
        "x-slot-1",
        "x-tail-high",
        "x-summary",
    ]
    second = with_distribution_layouts(frame, inspect_distribution_layouts(frame))
    second.attrs[DISTRIBUTION_LAYOUTS_ATTR]["logical"]["columns"][0]["column"] = "changed"
    second.attrs["unrelated"]["owned"].append(2)
    assert frame.attrs == before
    assert layout.columns[0].column == "x-tail-low"
    assert second.dtypes.equals(frame.dtypes)
    assert _names(pd.DataFrame({"x..0-1": [1.0]})) == set()


def test_empty_writer_removes_key_and_does_not_mutate_input() -> None:
    frame = _frame()
    cleared = with_distribution_layouts(frame, {})
    assert DISTRIBUTION_LAYOUTS_ATTR not in cleared.attrs
    assert _names(frame) == {"logical", "selected"}
    cleared.attrs[DISTRIBUTION_LAYOUTS_ATTR] = {}
    assert inspect_distribution_layouts(cleared) == {}
    assert DISTRIBUTION_LAYOUTS_ATTR not in with_distribution_layouts(cleared, {}).attrs


@pytest.mark.parametrize(
    "raw", [None, [], "native", {"logical": None}, {"logical": []}, {1: {"columns": []}}]
)
def test_malformed_reserved_attrs_rejected_at_all_admission_boundaries(raw: object) -> None:
    frame = _frame()
    frame.attrs[DISTRIBUTION_LAYOUTS_ATTR] = raw
    with pytest.raises((TypeError, ValueError)):
        inspect_distribution_layouts(frame)
    with pytest.raises((TypeError, ValueError)):
        copy_dataframe(frame)
    with pytest.raises(DataValidationError) as error:
        Table(frame)
    assert isinstance(error.value.__cause__, (TypeError, ValueError))
    with pytest.raises(ValueError, match="typed table"):
        TypedTableCodec.encode(frame)


@pytest.mark.parametrize(
    "mutation",
    ["missing", "duplicate", "text", "bool", "complex", "overlap", "extra-key", "unknown-kind"],
)
def test_reserved_attrs_require_unique_real_numeric_physical_ownership(mutation: str) -> None:
    frame = _frame()
    if mutation == "missing":
        frame = frame.drop(columns="x-slot-0")
    elif mutation == "duplicate":
        frame = frame[[*frame.columns, "x-slot-0"]]
    elif mutation == "text":
        frame["x-slot-0"] = ["1", "2", "3", "4"]
    elif mutation == "bool":
        frame["x-slot-0"] = True
    elif mutation == "complex":
        frame["x-slot-0"] = 1j
    elif mutation == "overlap":
        frame.attrs[DISTRIBUTION_LAYOUTS_ATTR]["other"] = deepcopy(
            frame.attrs[DISTRIBUTION_LAYOUTS_ATTR]["logical"]
        )
    elif mutation == "extra-key":
        frame.attrs[DISTRIBUTION_LAYOUTS_ATTR]["logical"]["migrated"] = True
    else:
        frame.attrs[DISTRIBUTION_LAYOUTS_ATTR]["logical"]["kind"] = "old-distribution"
    with pytest.raises((TypeError, ValueError)):
        inspect_distribution_layouts(frame)


def test_shared_byte_admission_precedes_typed_binding_retention() -> None:
    frame = _frame()
    # Both values individually fit; their exact enclosing mapping does not.
    payload = frame.attrs[DISTRIBUTION_LAYOUTS_ATTR]
    import json

    one = len(
        json.dumps(
            {"logical": payload["logical"]},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    )
    monkeypatch_limit = one + 1
    with patch.object(metadata, "MAX_PARSED_SCHEMA_BYTES", monkeypatch_limit):
        with pytest.raises(ValueError, match="schema byte budget"):
            inspect_distribution_layouts(frame)
        with pytest.raises(ValueError, match="schema byte budget"):
            with_distribution_layouts(
                frame,
                {
                    "logical": _native(),
                    "selected": OpaqueDistributionLayout(
                        (DistributionColumn("literal", "0-1", "source", None),)
                    ),
                },
            )
    with (
        patch.object(metadata, "MAX_PARSED_SCHEMA_BYTES", 10),
        patch(
            "src.core.common.distribution_layout_codec.DistributionColumn",
            side_effect=AssertionError("must admit before retaining bindings"),
        ),
    ):
        with pytest.raises(ValueError, match="schema byte budget"):
            inspect_distribution_layouts(frame)


def test_aggregate_logical_and_physical_limits_reject_before_publication() -> None:
    frame = _frame()
    with patch.object(metadata, "MAX_PARSE_VARIABLES", 1):
        with pytest.raises(ValueError, match="logical output budget"):
            inspect_distribution_layouts(frame)
    with patch.object(metadata, "MAX_INCREMENTAL_CACHE_COLUMNS", 5):
        with pytest.raises(ValueError, match="physical column budget"):
            inspect_distribution_layouts(frame)


def test_typed_table_roundtrip_owns_layout_attrs_and_preserves_extension_dtype() -> None:
    frame = _frame()
    encoded = TypedTableCodec.encode(frame)
    decoded = TypedTableCodec.decode(encoded)
    assert decoded is not None
    assert_frame_equal(decoded, frame)
    assert decoded.attrs == frame.attrs
    decoded.attrs[DISTRIBUTION_LAYOUTS_ATTR]["selected"]["columns"].clear()
    assert len(frame.attrs[DISTRIBUTION_LAYOUTS_ATTR]["selected"]["columns"]) == 1
    # Encode a generic payload directly to exercise strict decode admission.
    invalid = frame.drop(columns="x-slot-0")
    with pytest.raises(ValueError, match="numeric columns"):
        TypedTableCodec.decode(TypedTableCodec._encode_frame(invalid))


def test_owned_copy_keeps_nested_cells_and_attrs_independent() -> None:
    frame = _frame()
    frame["objects"] = pd.Series([[{"values": [1]}] for _ in range(len(frame))], dtype=object)
    copied = copy_dataframe(frame)
    nested = cast(
        list[dict[str, list[int]]], copied.iat[0, cast(int, copied.columns.get_loc("objects"))]
    )
    nested[0]["values"].append(2)
    copied.attrs[DISTRIBUTION_LAYOUTS_ATTR]["logical"]["columns"].clear()
    assert frame["objects"].iloc[0] == [{"values": [1]}]
    assert _names(frame) == {"logical", "selected"}
    assert copied.dtypes.equals(frame.dtypes)


def test_state_replacement_validates_incoming_attrs_without_old_layout_borrowing() -> None:
    repository = DataRepository()
    original = _frame()
    repository.set_data(original)
    repository.set_processed_data(original)
    invalid = original.drop(columns="x-slot-0")
    with pytest.raises(ValueError):
        repository.set_data(invalid)
    with pytest.raises(ValueError):
        repository.set_processed_data(invalid)
    source, processed = repository.get_data(), repository.get_processed_data()
    assert source is not None and processed is not None
    assert_frame_equal(source, original)
    assert_frame_equal(processed, original)
    repository.set_data(pd.DataFrame({"new": [1.0]}))
    replaced = repository.get_data()
    assert replaced is not None
    assert DISTRIBUTION_LAYOUTS_ATTR not in replaced.attrs


def test_named_dataset_failure_preserves_existing_revision_and_data() -> None:
    repository = DataRepository()
    original = _frame()
    repository.add_dataset("source", original)
    before = repository.get_dataset_lineage("source")
    with pytest.raises(ValueError):
        repository.set_data(original.drop(columns="x-tail-high"))
    assert repository.get_dataset_lineage("source") == before
    retained = repository.get_data()
    assert retained is not None
    assert_frame_equal(retained, original)


def test_projection_keeps_whole_layout_and_native_order_independent_of_frame_order() -> None:
    frame = _frame()
    reversed_columns = list(reversed(frame.columns))
    projected = _run(frame, {"type": "columnSelector", "columns": reversed_columns})
    assert list(projected.columns) == reversed_columns
    assert inspect_distribution_layouts(projected) == inspect_distribution_layouts(frame)
    partial = _run(
        frame, {"type": "columnSelector", "columns": [c for c in frame.columns if c != "x-slot-0"]}
    )
    assert _names(partial) == {"selected"}
    duplicate = preserve_distribution_layouts(frame, frame[[*frame.columns, "x-slot-0"]])
    assert _names(duplicate) == {"selected"}
    assert _names(frame) == {"logical", "selected"}


@pytest.mark.parametrize(
    "step",
    [
        {"type": "itemSelector", "column": "bench", "strings": ["a"]},
        {"type": "conditionSelector", "column": "literal", "mode": "greater_than", "threshold": 2},
        {"type": "sort", "order_dict": {"bench": ["a", "b"]}},
        {
            "type": "groupCardinalitySelector",
            "groupBy": ["bench"],
            "countColumn": "config",
            "count": 2,
        },
        {
            "type": "groupPredicateSelector",
            "groupBy": ["bench"],
            "baselineColumn": "config",
            "baselineValue": "base",
            "predicateColumn": "literal",
            "drop_when": "zero_or_nan",
            "action": "drop",
        },
    ],
)
def test_builtin_row_operations_keep_all_declarations(step: dict) -> None:
    frame = _frame()
    result = _run(frame, step)
    assert result is not frame
    assert inspect_distribution_layouts(result) == inspect_distribution_layouts(frame)


def test_public_table_rows_sort_scalar_and_concat_keep_coordinate_contract() -> None:
    table = Table(_frame())
    assert _names(table.filter_eq("bench", "a").frame) == {"logical", "selected"}
    assert list(table.sort(["bench"]).frame["bench"]) == ["a", "a", "b", "b"]
    changed = table.with_scalar_op("x-slot-0", "x-slot-0", "*", 2)
    np.testing.assert_array_equal(changed.frame["x-slot-0"], [2, 4, 6, 8])
    assert _names(changed.frame) == {"logical", "selected"}
    assert _names(table.concat(changed).frame) == {"logical", "selected"}


@pytest.mark.parametrize(
    "step",
    [
        {
            "type": "mean",
            "meanVars": ["x-slot-0"],
            "meanAlgorithm": "arithmean",
            "groupingColumns": ["config"],
            "replacingColumn": "bench",
        },
        {
            "type": "normalize",
            "normalizeVars": ["x-slot-0"],
            "normalizerColumn": "config",
            "normalizerValue": "base",
            "groupBy": ["bench"],
        },
    ],
)
def test_mean_and_normalize_preserve_cell_roles_without_forging_auxiliary_bindings(
    step: dict,
) -> None:
    frame = _frame()
    frame["x-slot-0.sd"] = [0.1, 0.2, 0.3, 0.4]
    result = _run(frame, step)
    assert inspect_distribution_layouts(result) == inspect_distribution_layouts(frame)
    assert all(
        binding.column != "x-slot-0.sd"
        for layout in inspect_distribution_layouts(result).values()
        for binding in layout.columns
    )


@pytest.mark.parametrize("op", ["+", "-", "*", "/"])
def test_scalar_in_place_native_slot_retains_roles(op: str) -> None:
    frame = _frame()
    result = _run(
        frame,
        {
            "type": "deriveColumn",
            "op": "scalar",
            "dest": "x-slot-0",
            "sources": ["x-slot-0"],
            "scalar": 2.0,
            "scalar_op": op,
        },
    )
    assert _names(result) == {"logical", "selected"}


@pytest.mark.parametrize(
    "step,expected",
    [
        (
            {
                "type": "deriveColumn",
                "op": "scalar",
                "dest": "unrelated",
                "sources": ["x-slot-0"],
                "scalar": 2,
            },
            {"logical", "selected"},
        ),
        (
            {
                "type": "deriveColumn",
                "op": "scalar",
                "dest": "x-slot-0",
                "sources": ["x-slot-1"],
                "scalar": 2,
            },
            {"selected"},
        ),
        (
            {
                "type": "deriveColumn",
                "op": "sum",
                "dest": "x-slot-0",
                "sources": ["x-slot-0", "x-slot-1"],
            },
            {"selected"},
        ),
        (
            {
                "type": "deriveColumn",
                "op": "map",
                "dest": "literal",
                "sources": ["literal"],
                "mapping": {"1": 1},
            },
            {"logical"},
        ),
        ({"type": "transformer", "column": "literal", "target_type": "factor"}, {"logical"}),
        ({"type": "transformer", "column": "literal", "target_type": "scalar"}, {"logical"}),
        (
            {"type": "transformer", "column": "bench", "target_type": "factor"},
            {"logical", "selected"},
        ),
    ],
)
def test_derive_and_conversion_invalidate_only_affected_whole_layouts(
    step: dict, expected: set[str]
) -> None:
    assert _names(_run(_frame(), step)) == expected


def test_destructive_plugin_drops_layout_even_for_same_names_and_numeric_dtypes() -> None:
    frame = _frame()
    numeric = preserve_distribution_layouts(frame, frame.drop(columns=["bench", "config", "group"]))
    # A square transpose can retain every name and numeric dtype. The operation,
    # rather than shape/name matching, determines whether bindings are meaningful.
    numeric = pd.concat([numeric.iloc[[0]]] * len(numeric.columns), ignore_index=True)
    numeric.index = numeric.columns

    class Transpose:
        def __call__(self, source: pd.DataFrame) -> pd.DataFrame:
            transposed = source.T
            transposed.attrs = deepcopy(frame.attrs)
            return transposed

    with patch(
        "src.core.services.shapers.factory.ShaperFactory.create_shaper", return_value=Transpose()
    ):
        result = _run(numeric, {"type": "sort", "order_dict": {}})
    assert list(result.columns) == list(numeric.columns)
    assert DISTRIBUTION_LAYOUTS_ATTR not in result.attrs


class MetadataSortConfig(TypedDict):
    type: Required[Literal["metadataSort"]]
    order_dict: Required[dict[str, list[str]]]


def test_subclass_of_reviewed_builtin_defaults_to_dropping_layouts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class UnreviewedSort(Sort):
        pass

    frame = _frame()
    monkeypatch.setattr(ShaperFactory, "_definitions", dict(ShaperFactory._definitions))
    ShaperFactory.register(
        ShaperDefinition(
            "metadataSort", UnreviewedSort, "Metadata test sort", MetadataSortConfig, validate_sort
        )
    )
    result = _run(frame, {"type": "metadataSort", "order_dict": {}})
    assert DISTRIBUTION_LAYOUTS_ATTR not in result.attrs
    assert_frame_equal(result, frame)
    assert _names(frame) == {"logical", "selected"}


def test_pivot_and_split_reconstruction_drop_before_nested_pipeline_admission() -> None:
    frame = _frame()
    melted = _run(
        frame,
        {
            "type": "pivotLonger",
            "id_vars": ["bench", "config"],
            "value_vars": ["x-slot-0", "x-slot-1"],
            "var_name": "slot",
            "value_name": "value",
        },
    )
    assert DISTRIBUTION_LAYOUTS_ATTR not in melted.attrs
    split = _run(
        frame,
        {
            "type": "splitApply",
            "joinColumns": ["bench", "config"],
            "groups": [
                {"columns": ["x-slot-0"], "pipeline": [{"type": "sort", "order_dict": {}}]},
                {"columns": ["x-slot-1"], "pipeline": [{"type": "sort", "order_dict": {}}]},
            ],
        },
    )
    assert DISTRIBUTION_LAYOUTS_ATTR not in split.attrs
    assert len(split) == len(frame)


@pytest.mark.parametrize("difference", ["missing", "geometry", "zero-policy", "role", "nonnumeric"])
def test_row_concat_requires_exact_per_layout_parity_in_every_input(difference: str) -> None:
    frame = _frame()
    other = _frame()
    declarations = inspect_distribution_layouts(other)
    if difference == "missing":
        declarations.pop("logical")
    elif difference == "geometry":
        declarations["logical"] = _native(maximum=0.9)
    elif difference == "zero-policy":
        native = declarations["logical"]
        assert type(native) is NativeDistributionLayout
        declarations["logical"] = replace(native, zero_policy="nozero")
    elif difference == "role":
        declarations["logical"] = OpaqueDistributionLayout(
            tuple(
                DistributionColumn(binding.column, binding.source_label, "source", None)
                for binding in declarations["logical"].columns
            )
        )
    else:
        declarations.pop("logical")
        other["x-slot-0"] = "text"
    other = with_distribution_layouts(other, declarations)
    combined = DatasetWorkspaceService.append([frame, other])
    assert _names(combined) == {"selected"}
    combined_table = Table(frame).concat(Table(other)).frame
    assert _names(combined_table) == {"selected"}
    assert _names(frame) == {"logical", "selected"}


def test_row_concat_does_not_trust_pandas_attrs_and_column_join_always_drops() -> None:
    first, second = _frame(), _frame()
    stacked = DatasetWorkspaceService.append([first, second])
    assert _names(stacked) == {"logical", "selected"}
    stacked.attrs[DISTRIBUTION_LAYOUTS_ATTR]["logical"]["columns"].clear()
    assert _names(first) == {"logical", "selected"}
    empty = with_distribution_layouts(second, {})
    inherited = pd.concat([first, empty], ignore_index=True)
    inherited.attrs = deepcopy(first.attrs)
    assert (
        DISTRIBUTION_LAYOUTS_ATTR
        not in concat_distribution_layouts([first, empty], inherited).attrs
    )
    joined = DatasetWorkspaceService.join(first, second, ["bench", "config"])
    assert DISTRIBUTION_LAYOUTS_ATTR not in joined.attrs
    assert (
        DISTRIBUTION_LAYOUTS_ATTR
        not in with_distribution_layouts(pd.concat([first, second], axis=1), {}).attrs
    )


def test_whole_layout_invalidations_keep_unrelated_attrs_without_input_mutation() -> None:
    frame = _frame()
    result = preserve_distribution_layouts(
        frame, frame.reindex(index=[3, 1, 0]), invalidated_columns=["x-tail-low"]
    )
    assert _names(result) == {"selected"}
    assert result.attrs["unrelated"] == frame.attrs["unrelated"]
    result.attrs["unrelated"]["owned"].append(2)
    assert frame.attrs["unrelated"] == {"owned": [1]}
    assert _names(frame) == {"logical", "selected"}


def test_reconstruction_clears_reserved_attrs_without_copying_discarded_payload() -> None:
    class Uncopyable:
        def __deepcopy__(self, memo: dict) -> object:
            raise AssertionError("discarded declarations must not be copied")

    frame = _frame()
    frame.attrs[DISTRIBUTION_LAYOUTS_ATTR] = Uncopyable()
    result = with_distribution_layouts(frame, {})
    assert DISTRIBUTION_LAYOUTS_ATTR not in result.attrs
    assert result.attrs["unrelated"] == {"owned": [1]}


def test_public_reconstruction_controls_drop_stale_attrs_and_keep_scientific_values() -> None:
    original = _frame()
    table = Table(original)
    with Session() as session:
        reduced = session.reduce_seeds(table, ["config"], ["x-slot-0"]).frame
        compared = session.compare(table, table, ["bench", "config"], ["x-slot-0"]).frame
        assert DISTRIBUTION_LAYOUTS_ATTR not in reduced.attrs
        assert DISTRIBUTION_LAYOUTS_ATTR not in compared.attrs
        np.testing.assert_allclose(reduced["x-slot-0"], [1.5, 3.5])
        np.testing.assert_allclose(reduced["x-slot-0.sd"], [np.sqrt(0.5), np.sqrt(0.5)])
        np.testing.assert_array_equal(compared["absolute_change"], [0.0] * 4)
        assert list(compared["outcome"]) == ["unchanged"] * 4
        arithmetic = session.apply_operation(table, "Sum", "x-slot-0", "x-slot-1", "x-slot-0").frame
        assert _names(arithmetic) == {"selected"}
        np.testing.assert_array_equal(arithmetic["x-slot-0"], [2, 4, 6, 8])
        extra = session.mix_columns(table, "sum", ["x-slot-0", "x-slot-1"]).frame
        assert _names(extra) == {"logical", "selected"}
        np.testing.assert_array_equal(extra["sum"], [2, 4, 6, 8])
        annotated = session.apply_semantics(
            table, DatasetSemantics((ColumnSemantics("literal", "Latency", "s"),))
        )
        converted = session.convert_unit(annotated, "literal", "ms").frame
        assert _names(converted) == {"logical"}
        np.testing.assert_array_equal(converted["literal"], [1000, 2000, 3000, 4000])
    assert_frame_equal(table.frame, original)
    assert table.frame.attrs == original.attrs


def test_mixer_invalidates_actually_written_sd_binding_only() -> None:
    frame = _frame()
    frame["x-slot-0.sd"] = 0.2
    frame["x-slot-1.sd"] = 0.3
    frame["sum.sd"] = 0.1
    layouts = inspect_distribution_layouts(frame)
    layouts["uncertainty-slot"] = OpaqueDistributionLayout(
        (DistributionColumn("sum.sd", "literal-error", "source", None),)
    )
    frame = with_distribution_layouts(frame, layouts)
    result = ArithmeticService.apply_mixer(frame, "sum", ["x-slot-0", "x-slot-1"])
    assert _names(result) == {"logical", "selected"}
    np.testing.assert_allclose(result["sum.sd"], np.hypot(0.2, 0.3))
    no_error_source = ArithmeticService.apply_mixer(frame, "sum", ["literal", "literal"])
    assert _names(no_error_source) == {"logical", "selected", "uncertainty-slot"}
    np.testing.assert_array_equal(no_error_source["sum.sd"], [0.1] * 4)


def test_unit_conversion_invalidates_written_sd_binding_and_attach_owns_attrs() -> None:
    frame = _frame()
    frame["literal.sd"] = 0.1
    layouts = inspect_distribution_layouts(frame)
    layouts["uncertainty-slot"] = OpaqueDistributionLayout(
        (DistributionColumn("literal.sd", "literal-error", "source", None),)
    )
    frame = with_distribution_layouts(frame, layouts)
    annotated = SemanticMetadataService.attach(
        frame, DatasetSemantics((ColumnSemantics("literal", "Latency", "s"),))
    )
    result = SemanticMetadataService.convert(annotated, "literal", "ms")
    assert _names(result) == {"logical"}
    np.testing.assert_array_equal(result["literal.sd"], [100] * 4)
    annotated.attrs[DISTRIBUTION_LAYOUTS_ATTR]["logical"]["columns"].clear()
    assert _names(frame) == {"logical", "selected", "uncertainty-slot"}


def test_metadata_writer_owns_axis_names_and_preserves_nullable_column_types() -> None:
    frame = _frame()
    frame.index.name = "row"
    frame.columns.name = "quantity"
    result = with_distribution_layouts(frame, inspect_distribution_layouts(frame))
    assert_frame_equal(result, frame)
    result.index.name = "changed-row"
    result.columns.name = "changed-quantity"
    assert frame.index.name == "row" and frame.columns.name == "quantity"
    assert str(result["literal"].dtype) == "Int64"


def test_public_load_rejection_retains_prior_data_and_reports_typed_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = _frame()
    with Session() as session:
        session.api.state_manager.set_data(frame)

        def load_invalid(*args: object, **kwargs: object) -> None:
            session.api.state_manager.set_data(frame.drop(columns="x-slot-0"))

        monkeypatch.setattr(session.api, "load_data", load_invalid)
        with pytest.raises(DataLoadError, match="numeric columns"):
            session.load("declared.csv")
        retained = session.api.state_manager.get_data()
        assert retained is not None
        assert_frame_equal(retained, frame)


def test_concat_validates_later_inputs_even_after_all_layouts_are_dropped() -> None:
    frame = _frame()
    absent = with_distribution_layouts(frame, {})
    malformed = frame.drop(columns="x-slot-0")
    with pytest.raises(ValueError, match="numeric columns"):
        concat_distribution_layouts([frame, absent, malformed], frame)


@pytest.mark.parametrize(
    "case", ["malformed-metadata", "non-frame", "pipeline-text", "pipeline-null", "pipeline-width"]
)
def test_pipeline_admission_failure_has_no_invented_step_and_executes_nothing(case: str) -> None:
    data: object = _frame()
    pipeline: object = [{"type": "sort", "order_dict": {}}]
    if case == "malformed-metadata":
        data = _frame().drop(columns="x-slot-0")
    elif case == "non-frame":
        data = "not a frame"
    elif case == "pipeline-text":
        pipeline = "not a pipeline"
    elif case == "pipeline-null":
        pipeline = None
    else:
        from src.core.common.security_limits import MAX_PIPELINE_CONFIG_STEPS

        pipeline = [{"type": "sort", "order_dict": {}}] * (MAX_PIPELINE_CONFIG_STEPS + 1)
    with patch("src.core.services.shapers.factory.ShaperFactory.create_shaper") as create:
        with pytest.raises(PipelineStepError) as error:
            PipelineService.process_pipeline(
                cast(pd.DataFrame, data), cast(Sequence[Mapping[str, object]], pipeline)
            )
        create.assert_not_called()
    assert error.value.step_index is None
    assert error.value.shaper_type is None
    assert isinstance(error.value.__cause__, (TypeError, ValueError))


@pytest.mark.parametrize("pipeline", [None, "not a pipeline"])
def test_public_shape_preserves_pre_step_typed_error_location(pipeline: object) -> None:
    table = Table(_frame())
    with (
        Session() as session,
        patch("src.core.services.shapers.factory.ShaperFactory.create_shaper") as create,
    ):
        with pytest.raises(PipelineError) as error:
            session.shape(table, cast(Sequence[Mapping[str, object]], pipeline))
        create.assert_not_called()
    assert error.value.step_index is None
    assert error.value.shaper_type is None
    assert isinstance(error.value.__cause__, PipelineStepError)
    assert _names(table.frame) == {"logical", "selected"}
