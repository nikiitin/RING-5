"""Canonical public data values, immutable specifications and explicit interop."""

from __future__ import annotations

import importlib
import time
from dataclasses import FrozenInstanceError
from typing import get_type_hints

import pandas as pd
import pytest

import ring5
from ring5 import figure_spec
from ring5.shapers import available_shaper_types

pytestmark = pytest.mark.public_api


_DATA_METHODS = (
    "load",
    "load_import",
    "add_dataset",
    "get_dataset",
    "select_dataset",
    "get_dataset_revision",
    "append_datasets",
    "join_datasets",
    "join_datasets_validated",
    "compare_datasets",
    "profile_data",
    "infer_schema_contract",
    "validate_schema",
    "apply_semantics",
    "inspect_semantics",
    "convert_unit",
    "shape",
    "shape_submit",
    "reduce_seeds",
    "compare",
    "compare_statistics",
    "annotate_comparison",
    "export_regression_results",
    "remove_outliers",
    "apply_operation",
    "mix_columns",
    "create_plot",
    "plot",
    "create_report",
)


@pytest.mark.parametrize("name", _DATA_METHODS)
def test_session_declared_data_methods_do_not_advertise_raw_frames(name) -> None:
    # [test->req~ring5.api.table~1]
    hints = get_type_hints(getattr(ring5.Session, name))
    assert "DataFrame" not in repr(hints)


@pytest.mark.parametrize(
    "method,args,kwargs,error",
    [
        ("add_dataset", ("bad",), {}, ring5.DataValidationError),
        ("profile_data", (), {}, ring5.DataValidationError),
        ("infer_schema_contract", (), {}, ring5.DataValidationError),
        ("validate_schema", (), {"contract": None}, ring5.DataValidationError),
        ("apply_semantics", (), {"semantics": None}, ring5.DataValidationError),
        ("inspect_semantics", (), {}, ring5.DataValidationError),
        ("convert_unit", (), {"column": "v", "target_unit": "us"}, ring5.DataValidationError),
        ("shape", (), {"pipeline": []}, ring5.PipelineError),
        ("shape_submit", (), {"pipeline": []}, ring5.JobError),
        (
            "reduce_seeds",
            (),
            {"categorical_cols": ["key"], "statistic_cols": ["v"]},
            ring5.DataValidationError,
        ),
        ("annotate_comparison", (), {}, ring5.DataValidationError),
        ("export_regression_results", (), {}, ring5.DataValidationError),
        ("remove_outliers", (), {"outlier_col": "v"}, ring5.DataValidationError),
        (
            "apply_operation",
            (),
            {"operation": "Sum", "src1": "v", "src2": "v", "dest": "out"},
            ring5.DataValidationError,
        ),
        (
            "mix_columns",
            (),
            {"dest_col": "out", "source_cols": ["v", "w"]},
            ring5.DataValidationError,
        ),
        ("create_plot", ("bar",), {"config": {"x": "key", "y": "v"}}, ring5.DataValidationError),
        ("plot", ("bar",), {"config": {"x": "key", "y": "v"}}, ring5.DataValidationError),
    ],
)
def test_raw_frames_reject_before_workspace_or_job_publication(method, args, kwargs, error) -> None:
    frame = pd.DataFrame({"key": ["a"], "v": [1.0], "w": [2.0]})
    with ring5.Session() as session:
        call = getattr(session, method)
        with pytest.raises(error, match="ring5.Table"):
            if method in {"create_plot", "plot"}:
                call(*args, data=frame, **kwargs)
            elif method == "add_dataset":
                call(*args, frame, **kwargs)
            else:
                call(frame, **kwargs)
        assert session.plots == []
        assert session.background_jobs() == ()
        assert session.list_datasets() == ()


@pytest.mark.parametrize("method", ["compare", "compare_statistics"])
@pytest.mark.parametrize("raw_side", [0, 1])
def test_both_comparison_inputs_require_tables(method, raw_side) -> None:
    frame = pd.DataFrame({"key": ["a"], "v": [1.0]})
    values = [ring5.Table(frame), ring5.Table(frame)]
    values[raw_side] = frame
    with ring5.Session() as session:
        with pytest.raises(ring5.DataValidationError, match="ring5.Table"):
            getattr(session, method)(*values, ["key"], ["v"])


def test_workspace_ingestion_revision_join_comparison_and_import_results_are_tables(
    tmp_path,
) -> None:
    source = pd.DataFrame({"key": ["a", "b"], "v": [1.0, 2.0]})
    path = tmp_path / "source.csv"
    source.to_csv(path, index=False)
    with ring5.Session() as session:
        assert isinstance(session.load(str(path)), ring5.Table)
        assert isinstance(session.load_import(session.preview_import(str(path))), ring5.Table)
        session.add_dataset("left", ring5.Table(source))
        session.add_dataset("right", ring5.Table(source.assign(w=[3.0, 4.0])))
        assert isinstance(session.get_dataset("left"), ring5.Table)
        assert isinstance(session.select_dataset("left"), ring5.Table)
        revision = session.dataset_lineage("left").current_revision_id
        assert isinstance(session.get_dataset_revision(revision), ring5.Table)
        appended = session.append_datasets(["left", "right"], "appended")
        joined = session.join_datasets("left", "right", "joined", ["key"])
        confirmed, diagnostics = session.join_datasets_validated(
            "left", "right", "confirmed", ["key"], cardinality="one_to_one"
        )
        compared = session.compare_datasets("left", "right", ["key"], ["v"])
        assert all(
            isinstance(value, ring5.Table) for value in (appended, joined, confirmed, compared)
        )
        assert diagnostics is not None
        assert len(appended) == 4 and len(joined) == 2 and len(confirmed) == 2
        assert {row["outcome"] for row in compared.rows()} == {"unchanged"}


def test_table_handoffs_preserve_axes_dtypes_attrs_and_nested_ownership() -> None:
    source = pd.DataFrame(
        {
            "kind": pd.Categorical(["b", "a"], categories=["b", "a"], ordered=True),
            "nested": [{"values": [1]}, {"values": [2]}],
        },
        index=pd.Index([4, 7], name="sample"),
    )
    source.attrs["metadata"] = {"values": [3]}
    table = ring5.Table(source)
    with ring5.Session() as session:
        session.add_dataset("owned", table)
        revision = session.dataset_lineage("owned").current_revision_id
        for result in [
            session.get_dataset(),
            session.select_dataset("owned"),
            session.get_dataset_revision(revision),
            session.shape(table, []),
        ]:
            assert isinstance(result, ring5.Table)
            pd.testing.assert_frame_equal(result.frame, source)
            assert result.frame.attrs == source.attrs
            exposed = result.frame
            exposed.iloc[0, 1]["values"].append(99)
            exposed.attrs["metadata"]["values"].append(99)
            assert result.frame.iloc[0, 1] == {"values": [1]}
            assert result.frame.attrs["metadata"] == {"values": [3]}
        assert isinstance(session.api.state_manager.get_data(), pd.DataFrame)


def test_analysis_transform_semantics_and_explicit_report_frames_remain_supported() -> None:
    table = ring5.Table.from_rows(
        [
            {"key": "a", "v": 1.0, "w": 3.0},
            {"key": "a", "v": 2.0, "w": 4.0},
            {"key": "b", "v": 3.0, "w": 5.0},
        ]
    )
    with ring5.Session() as session:
        outputs = [
            session.shape(table, []),
            session.reduce_seeds(table, ["key"], ["v"]),
            session.remove_outliers(table, "v"),
            session.apply_operation(table, "Sum", "v", "w", "sum"),
            session.mix_columns(table, "mixed", ["v", "w"]),
        ]
        assert all(isinstance(value, ring5.Table) for value in outputs)
        semantics = ring5.DatasetSemantics((ring5.ColumnSemantics("v", "Value", "ms"),))
        annotated = session.apply_semantics(table, semantics)
        converted = session.convert_unit(annotated, "v", "us")
        assert isinstance(annotated, ring5.Table) and isinstance(converted, ring5.Table)
        assert converted.rows()[0]["v"] == pytest.approx(1000.0)
        assert session.inspect_semantics(converted).for_column("v").unit == "us"
        profile = session.profile_data(table)
        contract = session.infer_schema_contract(table)
        validation = session.validate_schema(table, contract)
        assert isinstance(profile.to_frame(), pd.DataFrame)
        assert isinstance(contract.to_frame(), pd.DataFrame)
        assert isinstance(validation.to_frame(), pd.DataFrame)
        assert isinstance(semantics.to_frame(), pd.DataFrame)
        accessibility = session.audit_figure_accessibility({}, "bar")
        assert isinstance(accessibility.to_frame(), pd.DataFrame)


def test_shape_background_result_is_an_owned_table() -> None:
    table = ring5.Table.from_rows([{"v": 2.0, "nested": {"values": [1]}}])
    pipeline = [{"type": "columnSelector", "columns": ["v", "nested"]}]
    with ring5.Session() as session:
        submitted = session.shape_submit(table, pipeline)
        pipeline[0]["columns"].clear()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            job = next(job for job in session.background_jobs() if job.job_id == submitted.job_id)
            if job.status in {"completed", "failed", "cancelled"}:
                break
            time.sleep(0.001)
        assert job.status == "completed", job
        result = session.background_job_result(job)
        assert isinstance(result, ring5.Table)
        assert result.rows() == [{"v": 2.0, "nested": {"values": [1]}}]


def test_drill_down_and_report_tables_use_owned_public_values() -> None:
    # [test->req~ring5.plots.drill-down~1]
    table = ring5.Table.from_rows([{"key": "a", "v": 1.0}, {"key": "b", "v": 2.0}])
    with ring5.Session() as session:
        session.add_dataset("source", table)
        plot = session.create_plot("bar", data=table, config={"x": "key", "y": "v"})
        result = session.drill_down(plot, {"key": "a"})
        assert isinstance(result, ring5.DrillDownResult)
        assert isinstance(result.rows, ring5.Table)
        assert result.rows.rows() == [{"key": "a", "v": 1.0}]
        assert result.row_count == 1 and result.columns == ("key", "v")
        exposed = result.rows.frame
        exposed.loc[0, "v"] = 99
        assert result.rows.rows()[0]["v"] == 1.0
        report = session.create_report("Report", [plot], tables={"Data": table})
        assert report.tables[0].total_rows == 2
        assert isinstance(report.tables[0].rows, tuple)
        with pytest.raises(ring5.DataValidationError, match="ring5.Table"):
            session.create_report("Report", [plot], tables={"Data": table.frame})
    with pytest.raises(TypeError, match="ring5.Table"):
        ring5.DrillDownResult(1, (), table.frame)


def test_saved_recipe_raw_configuration_does_not_acquire_figure_spec_defaults(tmp_path) -> None:
    path = tmp_path / "source.csv"
    pd.DataFrame({"key": ["a"], "v": [1.0]}).to_csv(path, index=False)
    raw = {"x": "key", "y": "v", "title": "Stored mapping"}
    recipe = ring5.AnalysisRecipe(
        "Exact config",
        ring5.RecipeSource("csv", str(path)),
        plots=(ring5.RecipePlot("Plot", "bar", raw),),
    )
    with ring5.Session() as session:
        result = session.run_analysis_recipe(recipe)
        assert result.rows == 1 and result.columns == ("key", "v")
        assert session.plots[0].config == raw
        assert "width" not in session.plots[0].config
        assert "margin_t" not in session.plots[0].config


@pytest.mark.parametrize(
    "value",
    [ring5.FigureSpec(), ring5.LegendOpts(), ring5.ReferenceLineOpts(), ring5.DualAxisOpts()],
)
def test_public_figure_values_are_frozen(value) -> None:
    name = next(iter(value.__dataclass_fields__))
    with pytest.raises(FrozenInstanceError):
        setattr(value, name, None)


def test_figure_spec_owns_nested_inputs_and_projects_fresh_editable_configuration() -> None:
    columns = ["v"]
    palette = ["red", "blue"]
    styles = {"v": {"dash": [1, 2]}}
    dual_columns = ["w"]
    spec = ring5.FigureSpec(
        y_columns=columns,
        palette=palette,
        category_groups={"a": "Group"},
        dual_axis=ring5.DualAxisOpts(columns=dual_columns),
        extra={"series_styles": styles},
    )
    columns.append("changed")
    palette.clear()
    styles["v"]["dash"].append(99)
    dual_columns.clear()
    assert tuple(spec.y_columns) == ("v",)
    assert tuple(spec.palette) == ("red", "blue")
    assert tuple(spec.dual_axis.columns) == ("w",)
    with pytest.raises(TypeError):
        spec.extra["new"] = 1
    with pytest.raises(TypeError):
        spec.extra["series_styles"]["v"]["dash"][0] = 3
    first = spec.to_config()
    first["color_palette"].clear()
    first["series_styles"]["v"]["dash"].append(100)
    second = spec.to_config()
    assert second["color_palette"] == ["red", "blue"]
    assert second["series_styles"]["v"]["dash"] == [1, 2]
    assert second["y_columns_right"] == ["w"]


def test_figure_spec_rejects_cycles_and_unsupported_mutable_values() -> None:
    cyclic = []
    cyclic.append(cyclic)
    with pytest.raises(ValueError, match="Cyclic"):
        ring5.FigureSpec(extra={"cycle": cyclic})
    with pytest.raises(TypeError, match="Unsupported mutable figure value"):
        ring5.FigureSpec(extra={"callback": lambda: None})


def test_figure_spec_owns_shared_nested_values_without_expanding_the_graph() -> None:
    shared = [1]
    for _ in range(30):
        shared = [shared, shared]
    spec = ring5.FigureSpec(extra={"first": shared, "second": shared})
    shared.clear()
    first = spec.to_config()
    assert first["first"] is first["second"]
    node = first["first"]
    for _ in range(30):
        assert node[0] is node[1]
        node = node[0]
    assert node == [1]
    node.append(2)
    second = spec.to_config()["first"]
    for _ in range(30):
        second = second[0]
    assert second == [1]


def test_public_constructor_and_execution_surface_has_no_removed_alternatives() -> None:
    module = importlib.import_module("ring5.shapers")
    assert set(module.__all__) == {
        "Shaper",
        "ShaperDefinition",
        "register_shaper",
        "available_shaper_types",
    }
    assert "mean" in available_shaper_types()
    assert not hasattr(module, "Mean") and not hasattr(module, "Selector")
    assert not hasattr(ring5, "FigureSpecBuilder")
    assert not hasattr(figure_spec, "FigureSpecBuilder")
    table = ring5.Table.from_rows([{"v": 2.0}])
    assert not hasattr(table, "apply")
    assert table.with_scalar_op("double", "v", "*", 2.0).rows()[0]["double"] == 4.0
    from src.core.services.shapers.impl.selector import Selector

    with pytest.raises(TypeError, match="abstract"):
        Selector({"column": "v"})


def test_figure_extra_numbering_projects_before_wire_validation_and_remains_owned() -> None:
    modes = ["Numbers"]
    spec = ring5.FigureSpec(
        numbered_xaxis_modes=["Labels"],
        number_legend=ring5.LegendOpts(font_size=8),
        extra={"numbered_xaxis_modes": modes, "nested": {"values": [1]}},
    )
    modes.append("Number legend")
    assert spec.extra["numbered_xaxis_modes"] == ("Numbers",)
    with pytest.raises(TypeError):
        spec.extra["nested"]["values"][0] = 2
    first = spec.to_config()
    assert first["numbered_xaxis_modes"] == ["Numbers"]
    assert first["legend2_font_size"] == 8
    first["numbered_xaxis_modes"].append("Labels")
    first["nested"]["values"].append(3)
    second = spec.to_config()
    assert second["numbered_xaxis_modes"] == ["Numbers"]
    assert second["legend2_font_size"] == 8
    assert second["nested"]["values"] == [1]


@pytest.mark.parametrize(
    "extra",
    [
        {"numbered_xaxis_modes": ("Numbers",)},
        {"numbered_xaxis_modes": "Numbers"},
        {"numbered_xaxis_modes": ["Numbers", "Numbers"]},
        {"numbered_xaxis_modes": ["unknown"]},
        {"numbered_xaxis": False},
    ],
)
def test_figure_extra_preserves_raw_numbering_admission_before_freezing(extra) -> None:
    with pytest.raises(ValueError, match="numbered.axis|numbered_xaxis_modes"):
        ring5.FigureSpec(extra=extra)
