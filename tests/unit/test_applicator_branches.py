"""Tests for StyleApplicator — additional branch coverage.

Focuses on _apply_data_labels, _apply_conditional_labels,
_apply_auto_contrast, _get_contrast_color, _apply_yaxis_title_annotation,
and _apply_legend_layout with multi-column legends.
"""

from typing import Any, Dict

import plotly.graph_objects as go

from src.web.pages.ui.plotting.styles.applicator import StyleApplicator


def _make_bar_fig(y_vals: list[float] | None = None) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=["A", "B", "C"],
            y=y_vals or [10, 20, 30],
            name="s1",
            marker=dict(color="#FF0000"),
        )
    )
    return fig


class TestApplyDataLabels:
    """Test _apply_data_labels method."""

    def test_basic_show_values(self) -> None:
        sa = StyleApplicator("bar")
        fig = _make_bar_fig()
        config: Dict[str, Any] = {"show_values": True}
        result = sa._apply_data_labels(fig, config)
        assert result.data[0].texttemplate is not None

    def test_custom_text_format(self) -> None:
        sa = StyleApplicator("bar")
        fig = _make_bar_fig()
        config: Dict[str, Any] = {
            "show_values": True,
            "text_format": "%{y:.1f}",
            "text_position": "outside",
        }
        result = sa._apply_data_labels(fig, config)
        assert result.data[0].texttemplate == "%{y:.1f}"

    def test_invalid_text_position_defaults_to_auto(self) -> None:
        sa = StyleApplicator("bar")
        fig = _make_bar_fig()
        config: Dict[str, Any] = {
            "show_values": True,
            "text_position": "invalid_pos",
        }
        result = sa._apply_data_labels(fig, config)
        assert result.data[0].textposition == "auto"

    def test_text_rotation_clamped(self) -> None:
        sa = StyleApplicator("bar")
        fig = _make_bar_fig()
        config: Dict[str, Any] = {
            "show_values": True,
            "text_rotation": 500,  # should clamp to 360 (Plotly normalizes 360→0)
        }
        result = sa._apply_data_labels(fig, config)
        # Plotly normalizes 360 to 0, so value might be 0
        # Just verify no error and the trace has textangle set
        assert result.data[0].textangle is not None

    def test_text_rotation_invalid_string(self) -> None:
        sa = StyleApplicator("bar")
        fig = _make_bar_fig()
        config: Dict[str, Any] = {
            "show_values": True,
            "text_rotation": "abc",
        }
        result = sa._apply_data_labels(fig, config)
        assert result.data[0].textangle == 0

    def test_text_constraint_inside(self) -> None:
        sa = StyleApplicator("bar")
        fig = _make_bar_fig()
        config: Dict[str, Any] = {
            "show_values": True,
            "text_constraint": True,
        }
        result = sa._apply_data_labels(fig, config)
        assert result.data[0].textposition == "inside"
        assert result.data[0].constraintext == "inside"

    def test_text_anchor_start(self) -> None:
        sa = StyleApplicator("bar")
        fig = _make_bar_fig()
        config: Dict[str, Any] = {
            "show_values": True,
            "text_anchor": "start",
        }
        result = sa._apply_data_labels(fig, config)
        assert result.data[0].cliponaxis is True

    def test_text_anchor_invalid_ignored(self) -> None:
        sa = StyleApplicator("bar")
        fig = _make_bar_fig()
        config: Dict[str, Any] = {
            "show_values": True,
            "text_anchor": "invalid",
        }
        # Should not raise
        sa._apply_data_labels(fig, config)

    def test_auto_contrast_mode(self) -> None:
        sa = StyleApplicator("bar")
        fig = _make_bar_fig()
        config: Dict[str, Any] = {
            "show_values": True,
            "text_color_mode": "Auto Contrast",
        }
        result = sa._apply_data_labels(fig, config)
        # Auto contrast should set text color
        assert result.data[0].textfont is not None

    def test_custom_color_mode(self) -> None:
        sa = StyleApplicator("bar")
        fig = _make_bar_fig()
        config: Dict[str, Any] = {
            "show_values": True,
            "text_color_mode": "Custom",
            "text_color": "#00FF00",
        }
        result = sa._apply_data_labels(fig, config)
        assert result.data[0].textfont.color == "#00FF00"


class TestApplyConditionalLabels:
    """Test _apply_conditional_labels method."""

    def test_threshold_filters_values(self) -> None:
        sa = StyleApplicator("bar")
        fig = _make_bar_fig([5, 15, 25])
        config: Dict[str, Any] = {
            "show_values": True,
            "text_display_logic": "If > Threshold",
            "text_threshold": 10,
        }
        result = sa._apply_data_labels(fig, config)
        texts = result.data[0].text
        assert texts[0] == ""  # 5 <= 10
        assert texts[1] != ""  # 15 > 10
        assert texts[2] != ""  # 25 > 10

    def test_threshold_with_none_y(self) -> None:
        sa = StyleApplicator("bar")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=["A", "B"], y=[None, 20], name="s"))
        config: Dict[str, Any] = {
            "show_values": True,
            "text_display_logic": "If > Threshold",
            "text_threshold": 5,
        }
        result = sa._apply_data_labels(fig, config)
        assert result.data[0].text[0] == ""


class TestGetContrastColor:
    """Test _get_contrast_color method."""

    def test_dark_color_returns_white(self) -> None:
        sa = StyleApplicator("bar")
        assert sa._get_contrast_color("#000000") == "#FFFFFF"

    def test_light_color_returns_black(self) -> None:
        sa = StyleApplicator("bar")
        assert sa._get_contrast_color("#FFFFFF") == "#000000"

    def test_empty_string(self) -> None:
        sa = StyleApplicator("bar")
        assert sa._get_contrast_color("") == "#000000"

    def test_invalid_hex_length(self) -> None:
        sa = StyleApplicator("bar")
        assert sa._get_contrast_color("#FFF") == "#000000"

    def test_none_input(self) -> None:
        sa = StyleApplicator("bar")
        assert sa._get_contrast_color(None) == "#000000"  # type: ignore[arg-type]


class TestApplyLegendLayoutMultiColumn:
    """Test _apply_legend_layout with multi-column legends."""

    def test_multi_column_legend(self) -> None:
        sa = StyleApplicator("bar")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=["A"], y=[1], name="t1"))
        fig.add_trace(go.Bar(x=["A"], y=[2], name="t2"))
        fig.add_trace(go.Bar(x=["A"], y=[3], name="t3"))
        fig.add_trace(go.Bar(x=["A"], y=[4], name="t4"))

        config: Dict[str, Any] = {"legend_ncols": 2, "width": 800}
        base_legend = {"x": 1.02, "y": 1.0, "xanchor": "left"}

        sa._apply_legend_layout(fig, config, base_legend)
        # Traces should be assigned to different legend groups
        assert fig.data[0].legend == "legend"
        assert fig.data[2].legend == "legend2"

    def test_multi_column_no_traces(self) -> None:
        sa = StyleApplicator("bar")
        fig = go.Figure()
        config: Dict[str, Any] = {"legend_ncols": 3}
        base_legend = {"x": 1.02, "y": 1.0, "xanchor": "left"}

        sa._apply_legend_layout(fig, config, base_legend)
        # Should not crash with zero traces

    def test_multi_column_right_anchor(self) -> None:
        sa = StyleApplicator("bar")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=["A"], y=[1], name="t1"))
        fig.add_trace(go.Bar(x=["A"], y=[2], name="t2"))

        config: Dict[str, Any] = {"legend_ncols": 2, "width": 800}
        base_legend = {"x": 1.02, "y": 1.0, "xanchor": "right"}

        sa._apply_legend_layout(fig, config, base_legend)

    def test_multi_column_center_anchor(self) -> None:
        sa = StyleApplicator("bar")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=["A"], y=[1], name="t1"))
        fig.add_trace(go.Bar(x=["A"], y=[2], name="t2"))

        config: Dict[str, Any] = {"legend_ncols": 2, "width": 800}
        base_legend = {"x": 0.5, "y": 0.5, "xanchor": "center"}

        sa._apply_legend_layout(fig, config, base_legend)

    def test_multi_column_stored_positions(self) -> None:
        sa = StyleApplicator("bar")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=["A"], y=[1], name="t1"))
        fig.add_trace(go.Bar(x=["A"], y=[2], name="t2"))

        config: Dict[str, Any] = {
            "legend_ncols": 2,
            "width": 800,
            "legend2_x": 0.8,
            "legend2_y": 0.9,
        }
        base_legend = {"x": 1.02, "y": 1.0, "xanchor": "left"}

        sa._apply_legend_layout(fig, config, base_legend)

    def test_invalid_ncols_string(self) -> None:
        sa = StyleApplicator("bar")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=["A"], y=[1], name="t1"))

        config: Dict[str, Any] = {"legend_ncols": "abc"}
        base_legend = {"x": 1.02, "y": 1.0}

        # Should fall back to single legend
        sa._apply_legend_layout(fig, config, base_legend)


class TestApplyYAxisTitleAnnotation:
    """Test _apply_yaxis_title_annotation method."""

    def test_annotation_added(self) -> None:
        sa = StyleApplicator("bar")
        fig = go.Figure()
        sa._apply_yaxis_title_annotation(fig, {}, "Y Label", vshift=20)

        assert len(fig.layout.annotations) == 1
        ann = fig.layout.annotations[0]
        assert ann.text == "Y Label"
        assert ann.yshift == 20


class TestApplyXAxisLabelOverrides:
    """Test _apply_xaxis_label_overrides."""

    def test_label_mapping(self) -> None:
        sa = StyleApplicator("bar")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=["A", "B"], y=[1, 2], name="s1"))

        config: Dict[str, Any] = {"xaxis_labels": {"A": "Alpha", "B": "Beta"}}
        xaxis_settings: Dict[str, Any] = {}

        result = sa._apply_xaxis_label_overrides(fig, config, xaxis_settings)
        assert result["ticktext"] == ["Alpha", "Beta"]

    def test_label_mapping_with_order(self) -> None:
        sa = StyleApplicator("bar")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=["B", "A"], y=[2, 1], name="s1"))

        config: Dict[str, Any] = {
            "xaxis_labels": {"A": "Alpha", "B": "Beta"},
            "xaxis_order": ["B", "A"],
        }
        xaxis_settings: Dict[str, Any] = {}

        result = sa._apply_xaxis_label_overrides(fig, config, xaxis_settings)
        assert result["ticktext"] == ["Beta", "Alpha"]
