"""Live Streamlit widget regressions for restored and edited configurations."""

from __future__ import annotations

import json
from textwrap import dedent

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
    assert app.number_input(key="y2_title_sz_1").value == 7
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
            {{"type": "selector", "column": "metric", "mode": "range", "range": [0.0, 2.0]}}, "p1_", 1
        )
    """)
    assert not app.exception
    result = app.session_state["result"]
    assert result["range"] == (
        [1.0, 1.0] if any(value is not None for value in values) else [0.0, 2.0]
    )


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


def test_variable_editor_preserves_repeat_on_ordinary_rerun() -> None:
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
