"""Live Streamlit widget regressions for restored and edited configurations."""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent
from typing import cast

import pytest
from streamlit.testing.v1 import AppTest


def _app(body: str) -> AppTest:
    return AppTest.from_string("import streamlit as st\n" + dedent(body)).run()


def test_large_multiselect_preserves_manual_hidden_bulk_and_threshold_changes() -> None:
    app = _app("""
        from src.web.components.common.filtered_selector import filtered_multiselect
        small = st.checkbox("Small options", key="small")
        options = [f"opt{i}" for i in range(2 if small else 101)]
        st.session_state["result"] = filtered_multiselect("Options", options, key="items")
    """)
    assert not app.exception
    app.multiselect(key="items").select("opt1").run()
    assert app.session_state["result"] == ["opt1"]
    app.text_input(key="items__search").set_value("opt99").run()
    app.multiselect(key="items").select("opt99").run()
    assert app.session_state["result"] == ["opt1", "opt99"]
    app.text_input(key="items__search").set_value("").run()
    app.multiselect(key="items").unselect("opt1").run()
    assert app.session_state["result"] == ["opt99"]
    app.button(key="items__clear").click().run()
    assert app.session_state["result"] == []
    app.checkbox(key="small").check().run()
    app.multiselect(key="items").select("opt1").run()
    assert app.session_state["result"] == ["opt1"]
    app.checkbox(key="small").uncheck().run()
    assert app.session_state["result"] == ["opt1"]
    assert not app.exception


@pytest.mark.parametrize("saved", [["0_1", "1_0"], []])
def test_pattern_restore_preserves_exact_correlated_and_empty_selections(saved: list[str]) -> None:
    app = _app(f"""
        from src.web.components.data_source.pattern_index_selector import PatternIndexSelector
        st.session_state["result"] = PatternIndexSelector.render_selector(
            r"system.l\\d+_cpu\\d+.ipc", ["0_0", "0_1", "1_0", "1_1"], "restore", {saved!r}
        )
    """)
    assert not app.exception
    assert app.session_state["result"] == (True, saved)
    app.run()
    assert app.session_state["result"] == (True, saved)


def test_right_axis_controls_preserve_primary_and_clear_fixed_step() -> None:
    app = _app("""
        from src.web.components.plotting.settings.axes_settings import AxesSettingsComponent
        saved = {"yaxis_tickangle": 15, "yaxis_dtick": 2, "yaxis2_dtick": 3,
                 "y2show_y_grid": True, "y2_grid_color": "#ff0000"}
        result = {}
        AxesSettingsComponent(1, "dual_axis_bar_dot")._render_y_axis_settings(saved, result, "y2")
        st.session_state["result"] = result
    """)
    assert not app.exception
    result = app.session_state["result"]
    assert result["y2_grid_color"] == "#ff0000"
    assert "y_grid_color" not in result
    assert "yaxis_tickangle" not in result
    assert result["yaxis2_tick_side"] == "right"
    app.number_input(key="y2ydtick_1").set_value(0).run()
    assert app.session_state["result"]["yaxis2_dtick"] is None
    assert "yaxis_dtick" not in app.session_state["result"]


def test_layout_preserves_saved_pixel_dimensions_margins_and_policy() -> None:
    app = _app("""
        from src.web.components.plotting.settings.layout_settings import LayoutSettingsComponent
        saved = {"width": 803, "height": 417, "margin_l": 80, "margin_r": 60,
                 "margin_t": 40, "margin_b": 70, "margin_pad": 9, "automargin": False}
        st.session_state["result"] = LayoutSettingsComponent(1, "bar").render(saved)
    """)
    assert not app.exception
    result = app.session_state["result"]
    assert (result["width"], result["height"]) == (803, 417)
    assert [result[f"margin_{side}"] for side in ("l", "r", "t", "b", "pad")] == [80, 60, 40, 70, 9]
    assert result["automargin"] is False


def test_right_axis_font_inheritance_and_primary_small_fonts_round_trip() -> None:
    app = _app("""
        from src.web.components.plotting.config.dual_axis_settings import (
            render_dual_axis_display_settings,
        )
        saved = {"yaxis_title_font_size": 7, "yaxis_tickfont_size": 7,
                 "yaxis2_title_font_size": -1, "yaxis2_tickfont_size": -1}
        result = {}
        render_dual_axis_display_settings(saved, result, 1)
        st.session_state["result"] = result
    """)
    assert not app.exception
    assert app.session_state["result"]["yaxis2_title_font_size"] == -1
    assert (
        next(
            widget for widget in app.number_input if widget.label == "Right Y-Axis Title Font Size"
        ).value
        == 7
    )
    app.checkbox(key="plot.1.inherit_y2_title_sz_1").uncheck().run()
    assert app.session_state["result"]["yaxis2_title_font_size"] == 7
    app.checkbox(key="plot.1.inherit_y2_title_sz_1").check().run()
    assert app.session_state["result"]["yaxis2_title_font_size"] == -1


def test_transformer_restore_keeps_nonfirst_target() -> None:
    app = _app("""
        import pandas as pd
        from src.web.components.shapers.selector_transformer_configs import TransformerConfig
        st.session_state["result"] = TransformerConfig.render(
            pd.DataFrame({"aaa": [1], "zzz": [2]}),
            {"type": "transformer", "column": "zzz", "target_type": "scalar"}, "p1_", 1
        )
    """)
    assert not app.exception
    assert app.session_state["result"]["column"] == "zzz"


@pytest.mark.parametrize("values", [[1.0, 1.0], [1.0], [None, None]])
def test_numeric_filter_handles_constant_single_and_unmeasured_columns(
    values: list[float | None],
) -> None:
    app = _app(f"""
        import pandas as pd
        from src.web.components.shapers.selector_transformer_configs import (
            ConditionSelectorConfig,
        )
        st.session_state["result"] = ConditionSelectorConfig.render(
            pd.DataFrame({{"metric": pd.Series({values!r}, dtype="float64")}}),
            {{"type": "conditionSelector", "column": "metric", "mode": "range",
              "range": [0.0, 2.0]}}, "p1_", 1
        )
    """)
    assert not app.exception
    result = app.session_state["result"]
    assert result["range"] == [0.0, 2.0]


@pytest.mark.parametrize("values", [[10.0, 10.0], [10.0, 20.0], [None, None]])
def test_opening_range_editor_preserves_the_scientific_selection(values) -> None:
    app = _app(f"""
        import pandas as pd
        from src.web.pages.ui.shaper_config import configure_shaper, apply_shapers
        frame = pd.DataFrame({{"metric": pd.Series({values!r}, dtype="float64")}})
        saved = {{"type": "conditionSelector", "column": "metric", "mode": "range",
                  "range": [0.0, 2.0]}}
        configured = configure_shaper("conditionSelector", frame, 1, saved, owner_id=1)
        st.session_state["configured"] = configured
        st.session_state["rows"] = len(apply_shapers(frame, [configured]))
    """)
    assert not app.exception
    assert app.session_state["configured"]["range"] == [0.0, 2.0]
    assert app.session_state["rows"] == 0
    app.run()
    assert not app.exception
    assert app.session_state["rows"] == 0


@pytest.mark.parametrize(
    "configs",
    [
        [{"type": "normalize"}],
        [{"type": "unknown"}],
        [{"type": "columnSelector", "columns": ["metric"]}, {"type": "normalize"}],
    ],
)
def test_invalid_nonempty_pipeline_never_publishes_a_shortened_result(configs) -> None:
    app = _app(f"""
        import pandas as pd
        from src.core.application_api import ApplicationAPI
        from src.web.controllers.plot.pipeline_controller import PipelineController
        from src.web.pages.plot_adapters import PipelineExecutorAdapter
        from src.web.pages.ui.plotting.plot_factory import PlotFactory
        from src.web.state.ui_state_manager import UIStateManager
        api = ApplicationAPI()
        try:
            plot = PlotFactory.create_plot("bar", 1, "Figure")
            plot.replace_source_data(pd.DataFrame({{"original": [3]}}))
            plot.replace_processed_data(pd.DataFrame({{"kept": [7]}}))
            plot.pipeline = [{{"id": i, "type": config["type"], "config": config}}
                             for i, config in enumerate({configs!r})]
            PipelineController(api, UIStateManager(), PipelineExecutorAdapter())._handle_finalize(
                plot, pd.DataFrame({{"metric": [10.0]}})
            )
            st.session_state["source"] = plot.source_data.to_dict("list")
            st.session_state["processed"] = plot.processed_data.to_dict("list")
        finally:
            api.close()
    """)
    assert len(app.exception) == 1
    assert "Failed to apply shaper" in app.exception[0].message
    assert app.session_state["source"] == {"original": [3]}
    assert app.session_state["processed"] == {"kept": [7]}


def test_pivot_capture_filter_survives_json_restore_and_editor_round_trip() -> None:
    config = {
        "id_vars": ["id"],
        "value_vars": ["cpu0", "cpu1"],
        "extract_pattern": r"cpu(\d+)",
        "extract_group_indices": [1],
        "selection_filters": {"1": ["0"]},
    }
    app = _app(f"""
        import json
        import pandas as pd
        from src.web.components.shapers.pivot_config import PivotLongerConfig
        saved = json.loads({json.dumps(json.dumps(config))})
        st.session_state["result"] = PivotLongerConfig.render(
            pd.DataFrame({{"id": ["x"], "cpu0": [1], "cpu1": [2]}}), saved, "p1_", 1
        )
    """)
    assert not app.exception
    assert app.session_state["result"]["selection_filters"] == {"1": ["0"]}

    from src.core.services.data_services.pipeline_config_exchange_service import (
        PipelineConfigExchangeService,
    )
    from src.core.services.shapers.factory import ShaperFactory
    import pandas as pd

    payload = PipelineConfigExchangeService.dumps("filtered", "", [app.session_state["result"]])
    restored = PipelineConfigExchangeService.loads(payload).shapers[0]
    assert restored["type"] == "pivotLonger"
    from src.core.models.shaper_models import PivotLongerShaperConfig

    assert cast(PivotLongerShaperConfig, restored)["selection_filters"] == {"1": ["0"]}
    transformed = ShaperFactory.create_shaper("pivotLonger", restored)(
        pd.DataFrame({"id": ["x"], "cpu0": [1], "cpu1": [2]})
    )
    assert transformed["variable"].tolist() == ["0"]
    assert transformed["value"].tolist() == [1]


@pytest.mark.xdist_group("perl_pool")
def test_variable_editor_preserves_repeat_on_ordinary_rerun(tmp_path: Path) -> None:
    app = _app("""
        from src.core.application_api import ApplicationAPI
        from src.web.components.data_source.variable_editor import VariableEditor
        api = ApplicationAPI()
        try:
            st.session_state["result"] = VariableEditor.render(
                api, [{"name": "ipc", "type": "scalar", "_id": "scalar", "repeat": "3"}]
            )
        finally:
            api.close()
    """)
    assert not app.exception
    assert app.session_state["result"][0]["repeat"] == "3"
    app.run()
    assert app.session_state["result"][0]["repeat"] == "3"

    from src.core.application_api import ApplicationAPI
    import pandas as pd

    (tmp_path / "stats.txt").write_text("ipc 2\nipc 4\nipc 6\n", encoding="utf-8")
    api = ApplicationAPI()
    try:
        batch = api.submit_parse_async(
            str(tmp_path), "stats.txt", app.session_state["result"], str(tmp_path / "out")
        )
        results = [future.result(timeout=30) for future in batch.futures]
        output = api.finalize_parsing(str(tmp_path / "out"), results, var_names=batch.var_names)
        assert output is not None
        assert pd.read_csv(output)["ipc"].tolist() == [4.0]
    finally:
        api.close()


def test_vector_combined_mode_preserves_entries_and_summary_members() -> None:
    app = _app("""
        from src.core.application_api import ApplicationAPI
        from src.web.components.data_source.variable_editor import VariableEditor
        api = ApplicationAPI()
        original = {"name": "v", "type": "vector", "_id": "v", "vectorEntries": ["cpu0", "mean"],
                    "statisticsOnly": False, "useSpecialMembers": True}
        result = {"name": "v", "type": "vector", "_id": "v"}
        try:
            VariableEditor.render_vector_config(api, result, original, "v",
                [{"name": "v", "type": "vector", "entries": ["cpu0", "cpu1", "mean"]}],
                None, "stats.txt")
            st.session_state["result"] = result
        finally:
            api.close()
    """)
    assert not app.exception
    assert app.session_state["result"]["vectorEntries"] == ["cpu0", "mean"]
    assert app.session_state["result"]["useSpecialMembers"] is True


@pytest.mark.parametrize("plot_type", ["bar", "line"])
def test_live_colors_route_exposes_specific_series_controls(plot_type: str) -> None:
    module = "bar_plot" if plot_type == "bar" else "line_plot"
    class_name = "BarPlot" if plot_type == "bar" else "LinePlot"
    app = _app(f"""
        import pandas as pd
        from src.web.pages.ui.plotting.types.{module} import {class_name}
        plot = {class_name}(1, "Figure")
        saved = {{"color": "series", "color_palette": "wong"}}
        st.session_state["result"] = plot.render_settings_section("colors", saved,
            pd.DataFrame({{"series": ["A"], "metric": [1.0]}}))
    """)
    assert not app.exception
    labels = [widget.label for widget in app.selectbox]
    assert ("Pattern" if plot_type == "bar" else "Marker Symbol") in labels
    if plot_type == "line":
        assert "Line Width" in [widget.label for widget in app.number_input]


def test_secondary_legend_fonts_keep_inheritance_for_text_and_title() -> None:
    app = _app("""
        from src.web.components.plotting.settings.legend_settings import LegendSettingsComponent
        saved = {"legend_font_size": 7, "legend_title_font_size": 7,
                 "legend2_font_size": -1, "legend2_title_font_size": -1}
        st.session_state["result"] = LegendSettingsComponent(1, "bar")._render_legend_appearance(
            saved, "legend2_", "legend2_")
    """)
    assert not app.exception
    result = app.session_state["result"]
    assert result["legend2_font_size"] == result["legend2_title_font_size"] == -1


def test_heatmap_explicit_no_facet_and_missing_group_round_trip() -> None:
    app = _app("""
        import pandas as pd
        from src.web.components.plotting.config.heatmap_config import render as heatmap_config
        st.session_state["result"] = heatmap_config(
            pd.DataFrame({"config": ["a"], "benchmark_name": ["b"], "metric": [1.0]}),
            {"x": "config", "metric_columns": ["metric"], "facet_col": None}, 1)
    """)
    assert not app.exception
    assert app.session_state["result"]["facet_col"] is None


def test_plot_transfer_clears_color_override_and_shaper_state() -> None:
    app = _app("""
        from src.web.components.plotting.plot_transfer_panel import PlotTransferPanel
        from src.web.components.plotting.settings.colors_settings import ColorsSettingsComponent
        from src.web.components.common.bounded_options import stable_widget_suffix
        suffix = stable_widget_suffix(0, "A")
        if "seeded" not in st.session_state:
            st.session_state[f"theme_color_1_{suffix}_wong"] = "#000000"
            st.session_state[f"theme_use_col_1_{suffix}"] = False
            st.session_state["p1_filter_col_0"] = "old"
            st.session_state["p2_filter_col_0"] = "other"
            st.session_state["plot_transfer_reset_1"] = {
                "series_styles": {"A": {"color": "#ff0000", "use_color": True}}}
            st.session_state["seeded"] = True
        PlotTransferPanel.apply_pending_widget_reset(1)
        st.session_state["result"] = ColorsSettingsComponent(1, "bar")._render_series_colors(
            {"series_styles": {"A": {"color": "#ff0000", "use_color": True}}},
            None, ["A"], "theme_", "wong")
    """)
    assert not app.exception
    assert app.session_state["result"]["A"]["color"] == "#ff0000"
    assert app.session_state["result"]["A"]["use_color"] is True
    assert "p1_filter_col_0" not in app.session_state
    assert app.session_state["p2_filter_col_0"] == "other"


def test_grouped_stack_missing_saved_group_offers_no_grouping() -> None:
    app = _app("""
        import pandas as pd
        from src.web.components.plotting.config.grouped_stacked_bar_config import render
        st.session_state["result"] = render(
            pd.DataFrame({"metric": [1.0, 2.0]}), {"group": "missing", "x": "metric"}, 1)
    """)
    assert not app.exception
    assert app.session_state["result"]["group"] is None


@pytest.mark.parametrize(
    ("initial_parser", "selected_mode"),
    [(False, "Parse gem5 Stats Files"), (True, "Upload data or portfolio")],
)
def test_input_workflow_choice_preserves_active_source(
    initial_parser: bool, selected_mode: str
) -> None:
    app = _app(f"""
        from unittest.mock import patch
        import pandas as pd
        from src.core.application_api import ApplicationAPI
        from src.web.pages.data_source import DataSourcePage
        api = ApplicationAPI()
        api.state_manager.set_data(pd.DataFrame({{"value": [3.0]}}))
        api.state_manager.set_use_parser({initial_parser!r})
        st.session_state["data_source_choice"] = {selected_mode!r}
        with patch("src.web.pages.data_source.DataSourceComponents.render_parser_config"), \\
             patch("src.web.pages.data_source.DataSourceComponents.render_browser_upload"):
            DataSourcePage(api).render()
        st.session_state["result"] = api.state_manager.is_using_parser()
        api.close()
    """)
    assert not app.exception
    assert app.session_state["result"] is initial_parser


@pytest.mark.parametrize("count", [2, 101])
def test_filtered_multiselect_keeps_explicit_empty_widget_state(count: int) -> None:
    app = _app(f"""
        from src.web.components.common.filtered_selector import filtered_multiselect
        st.session_state["pick"] = []
        st.session_state["result"] = filtered_multiselect(
            "Columns", [f"opt{{i}}" for i in range({count})], default=["opt1"], key="pick")
    """)
    assert not app.exception
    assert app.session_state["result"] == []
    assert app.multiselect(key="pick").value == []


@pytest.mark.parametrize("pixels", [10, 1])
def test_layout_enforces_backend_minimum_without_rejecting_saved_valid_pixels(pixels: int) -> None:
    app = _app(f"""
        from src.web.components.plotting.settings.layout_settings import LayoutSettingsComponent
        st.session_state["result"] = LayoutSettingsComponent(1, "bar").render(
            {{"width": {pixels}, "height": {pixels}}})
    """)
    assert not app.exception
    assert app.number_input(key="wi_1").min == 0.1
    assert app.session_state["result"]["width"] == 10
    assert app.session_state["result"]["height"] == 10
    assert bool(app.warning) is (pixels < 10)


@pytest.mark.parametrize(
    ("prefix", "own_font", "expected"),
    [
        ("legend_", 12, 12),
        ("legend2_", 20, 20),
        ("legend2_", -1, 12),
    ],
)
def test_legend_title_inherits_its_own_resolved_text_size(
    prefix: str, own_font: int, expected: int
) -> None:
    app = _app(f"""
        from src.web.components.plotting.settings.legend_settings import LegendSettingsComponent
        saved = {{"legend_font_size": 12, "{prefix}font_size": {own_font},
                 "{prefix}title_font_size": -1}}
        st.session_state["result"] = LegendSettingsComponent(1, "bar")._render_legend_appearance(
            saved, "{prefix}", "{prefix}")
    """)
    assert not app.exception
    assert app.session_state["result"][f"{prefix}title_font_size"] == -1
    title_widget = next(widget for widget in app.number_input if widget.label == "Title Size")
    assert title_widget.disabled
    assert title_widget.value == expected
    if own_font > 0:
        text_widget = next(widget for widget in app.number_input if widget.label == "Font Size")
        text_widget.set_value(expected + 3).run()
        assert not app.exception
        assert (
            next(widget for widget in app.number_input if widget.label == "Title Size").value
            == expected + 3
        )
        assert app.session_state["result"][f"{prefix}title_font_size"] == -1


def test_active_line_style_panel_preserves_fractional_width() -> None:
    app = _app("""
        import pandas as pd
        from src.web.pages.ui.plotting.types.line_plot import LinePlot
        saved = {"color": "series", "color_palette": "wong",
                 "series_styles": {"A": {"line_width": 1.5, "marker_size": 8}}}
        st.session_state["result"] = LinePlot(1, "Figure").render_settings_section(
            "colors", saved, pd.DataFrame({"series": ["A"], "metric": [1.0]}))
    """)
    assert not app.exception
    assert app.session_state["result"]["series_styles"]["A"]["line_width"] == 1.5
    assert next(widget for widget in app.number_input if widget.label == "Line Width").value == 1.5


def test_enabling_legend_title_inheritance_updates_its_display_immediately() -> None:
    app = _app("""
        from src.web.components.plotting.settings.legend_settings import LegendSettingsComponent
        st.session_state["result"] = LegendSettingsComponent(1, "bar")._render_legend_appearance(
            {"legend_font_size": 12, "legend_title_font_size": 22}, "theme_", "legend_")
    """)
    assert not app.exception
    assert next(widget for widget in app.number_input if widget.label == "Title Size").value == 22
    app.checkbox(key="plot.1.inherit_theme_leg_title_sz_1").check().run()
    assert not app.exception
    assert app.session_state["result"]["legend_title_font_size"] == -1
    assert next(widget for widget in app.number_input if widget.label == "Title Size").value == 12


@pytest.mark.parametrize(
    ("dtype", "cardinality", "included"),
    [
        ("object", 101, True),
        ("str", 101, True),
        ("string", 101, True),
        ("category", 101, True),
        ("int64", 101, False),
        ("int64", 5, True),
    ],
)
def test_reduction_candidates_cover_pandas_string_and_numeric_contracts(
    dtype: str, cardinality: int, included: bool
) -> None:
    app = _app(f"""
        import pandas as pd
        from src.core.application_api import ApplicationAPI
        from src.web.components.data_managers.seeds_reducer import SeedsReducerManager
        ids = [i % {cardinality} for i in range(101)]
        if {dtype!r} != "int64":
            ids = [str(value) for value in ids]
        api = ApplicationAPI()
        api.state_manager.set_data(pd.DataFrame({{
            "run_id": pd.Series(ids, dtype={dtype!r}), "bench": ["b"] * 101, "metric": range(101)
        }}))
        SeedsReducerManager(api).render()
        api.close()
    """)
    assert not app.exception
    assert (
        "run_id" in app.selectbox(key="manager.seeds_reducer.target_column").options
    ) is included


def test_pipeline_finalize_rejects_every_incomplete_step_without_replacing_data() -> None:
    app = _app("""
        import pandas as pd
        from src.core.application_api import ApplicationAPI
        from src.web.controllers.plot.pipeline_controller import PipelineController
        from src.web.pages.plot_adapters import PipelineExecutorAdapter
        from src.web.pages.ui.plotting.plot_factory import PlotFactory
        from src.web.state.ui_state_manager import UIStateManager
        api = ApplicationAPI()
        plot = PlotFactory.create_plot("bar", 1, "Figure")
        plot.replace_processed_data(pd.DataFrame({"kept": [7]}))
        plot.pipeline = [
            {"id": 0, "type": "sort", "config": {
                "type": "sort", "order_dict": {"label": ["a", "b"]}}},
            {"id": 1, "type": "conditionSelector", "config": {}},
        ]
        PipelineController(api, UIStateManager(), PipelineExecutorAdapter())._handle_finalize(
            plot, pd.DataFrame({"label": ["b", "a"], "value": [2, 1]}))
        st.session_state["result"] = plot.processed_data.to_dict(orient="list")
        api.close()
    """)
    assert app.session_state["result"] == {"kept": [7]}
    assert len(app.exception) == 1
    assert "Every displayed pipeline step" in app.exception[0].message


def test_filtered_selectbox_preserves_selection_across_search_clear_and_removed_options() -> None:
    app = _app("""
        from src.web.components.common.filtered_selector import filtered_selectbox
        remove = st.checkbox("Remove selected option", key="remove_option")
        options = [f"v{i}" for i in range(500) if not remove or i != 250]
        st.session_state["result"] = filtered_selectbox("Value", options, key="pick")
    """)
    assert not app.exception
    app.text_input(key="pick__search").set_value("v250").run()
    app.selectbox(key="pick").select("v250").run()
    assert app.session_state["result"] == "v250"
    for query in ("", "does-not-exist", "v1"):
        app.text_input(key="pick__search").set_value(query).run()
        assert not app.exception
        assert app.session_state["result"] == "v250"
        assert app.selectbox(key="pick").value == "v250"
        assert len(app.selectbox(key="pick").options) <= 50
    app.selectbox(key="pick").select("").run()
    assert app.session_state["result"] is None
    app.text_input(key="pick__search").set_value("v250").run()
    app.selectbox(key="pick").select("v250").run()
    app.checkbox(key="remove_option").check().run()
    assert not app.exception
    assert app.session_state["result"] is None
