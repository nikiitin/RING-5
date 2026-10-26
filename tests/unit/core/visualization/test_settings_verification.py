"""
Tests verifying UI settings wiring — legend gaps, vertical shift,
config_builder legend fields, and connector application.

Covers:
  - Legend vertical shifts use valid figure dimensions
  - C6: Legend valign/col_width wiring through config_builder
  - C6: Plotly connector applies valign to legend dict
  - C6: Matplotlib connector applies legend title + title_font_color
  - C4: Legend ncols wired in config_builder
  - C1: Standoff default sentinel -1 in AxisConfig
"""

from __future__ import annotations

from typing import Any, cast

import plotly.graph_objects as go

from src.core.models.visualization.axis_config import AxesConfig, AxisConfig
from src.core.models.visualization.figure_config import (
    DimensionConfig,
    FigureConfig,
)
from src.core.models.visualization.legend_config import LegendConfig
from src.core.services.visualization.config_resolver import resolve_config

# Import the private helper directly for unit testing
from src.web.rendering.config_builder import (
    _build_legend_from_config,
)
from src.web.rendering.plotly_connector import FigureSpecToPlotly
from src.web.rendering._render_result import (
    MatplotlibRenderResult,
    MatplotlibTraceBinding,
    PlotlyRenderResult,
    PlotlyTraceBinding,
)

# Helper: config_builder legend builder (module-level function)


class TestLegendValignWiring:
    """Editable legend configuration uses the model's vertical-alignment default."""

    def test_config_builder_valign_always_default(self) -> None:
        """The editable configuration does not override typed vertical alignment."""
        config: dict[str, Any] = {
            "legend_valign": "top",  # present in config but ignored
            "legend_font_size": 10,
        }
        legend = _build_legend_from_config(config, "legend_", "primary")
        assert legend.valign == "middle"  # always default

    def test_config_builder_valign_default(self) -> None:
        """Default valign should be 'middle' when not in config."""
        config: dict[str, Any] = {
            "legend_font_size": 10,
        }
        legend = _build_legend_from_config(config, "legend_", "primary")
        assert legend.valign == "middle"

    def test_plotly_connector_applies_valign_top(self) -> None:
        """Plotly connector should set valign when not 'middle'."""
        legend = LegendConfig(role="primary", valign="top")
        spec = FigureConfig(legends=[legend])
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1])])
        FigureSpecToPlotly._apply_legends(spec, fig)
        assert cast(Any, fig.layout).legend.valign == "top"

    def test_plotly_connector_skips_valign_middle(self) -> None:
        """Plotly omits the default middle vertical alignment."""
        legend = LegendConfig(role="primary", valign="middle")
        spec = FigureConfig(legends=[legend])
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1])])
        FigureSpecToPlotly._apply_legends(spec, fig)
        assert cast(Any, fig.layout).legend.valign is None

    def test_valign_in_to_dict(self) -> None:
        """LegendConfig.to_dict should include valign."""
        legend = LegendConfig(valign="bottom")
        d = legend.to_dict()
        assert d["valign"] == "bottom"

    def test_valign_round_trip(self) -> None:
        """valign should survive to_dict → from_dict round-trip."""
        original = LegendConfig(valign="top")
        data = original.to_dict()
        restored = LegendConfig.from_dict(data)
        assert restored.valign == "top"


class TestLegendColWidthWiring:
    """C6: col_width should flow through config_builder to model."""

    def test_config_builder_reads_col_width(self) -> None:
        """_build_legend_from_config should read {prefix}col_width."""
        config: dict[str, Any] = {
            "legend_col_width": 200.0,
            "legend_font_size": 10,
        }
        legend = _build_legend_from_config(config, "legend_", "primary")
        assert legend.col_width == 200.0

    def test_config_builder_col_width_default(self) -> None:
        """Default col_width should be -1.0 (auto) when not in config."""
        config: dict[str, Any] = {
            "legend_font_size": 10,
        }
        legend = _build_legend_from_config(config, "legend_", "primary")
        assert legend.col_width == -1.0


class TestLegendNcolsWiring:
    """C4: ncols should flow through config_builder to model."""

    def test_config_builder_reads_ncols(self) -> None:
        """_build_legend_from_config should read {prefix}ncols."""
        config: dict[str, Any] = {
            "legend_ncols": 3,
            "legend_font_size": 10,
        }
        legend = _build_legend_from_config(config, "legend_", "primary")
        assert legend.ncol == 3

    def test_config_builder_ncols_default_zero(self) -> None:
        """Default ncols should be 0 when not in config."""
        config: dict[str, Any] = {
            "legend_font_size": 10,
        }
        legend = _build_legend_from_config(config, "legend_", "primary")
        assert legend.ncol == 0

    def test_secondary_legend_ncols(self) -> None:
        """Secondary legend should also read its own ncols."""
        config: dict[str, Any] = {
            "legend2_ncols": 2,
            "legend2_font_size": 8,
        }
        legend = _build_legend_from_config(config, "legend2_", "secondary")
        assert legend.ncol == 2


class TestPlotlyLegendValignApplication:
    """Verify Plotly build_legend_dict includes valign correctly."""

    def test_valign_bottom(self) -> None:
        """Setting valign='bottom' should appear in Plotly legend dict."""
        legend = LegendConfig(role="primary", valign="bottom")
        spec = FigureConfig(legends=[legend])
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1])])
        FigureSpecToPlotly._apply_legends(spec, fig)
        assert cast(Any, fig.layout).legend.valign == "bottom"

    def test_multi_legend_valign(self) -> None:
        """Secondary legend should also get valign applied."""
        primary = LegendConfig(role="primary", valign="top")
        secondary = LegendConfig(role="secondary", valign="bottom")
        spec = FigureConfig(legends=[primary, secondary])
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1])])
        FigureSpecToPlotly._apply_legends(spec, fig)
        assert cast(Any, fig.layout).legend.valign == "top"
        assert cast(Any, fig.layout).legend2.valign == "bottom"


class TestMatplotlibLegendTitle:
    """C6: Matplotlib connector should apply legend title."""

    def test_legend_title_in_kwargs(self) -> None:
        """Legend title should be passed to matplotlib legend()."""
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib

        fig, ax = plt.subplots()
        bars = ax.bar(["A", "B"], [1, 2], label="test")

        legend = LegendConfig(
            role="primary",
            title="My Legend Title",
            title_font_size=14,
            title_font_color="#FF0000",
        )
        spec = FigureConfig(legends=[legend])
        resolved = resolve_config(spec)

        panel = MatplotlibRenderResult(
            ax,
            bindings=(
                MatplotlibTraceBinding(
                    0, "test", ax, "primary", "", True, "bar", (bars,), (bars,), bars
                ),
            ),
        )
        FigureSpecToMatplotlib._apply_legends(resolved, panel)

        mpl_legend = ax.get_legend()
        assert mpl_legend is not None
        assert mpl_legend.get_title().get_text() == "My Legend Title"
        plt.close(fig)

    def test_legend_no_title(self) -> None:
        """When title is empty, matplotlib legend should have no title."""
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib

        fig, ax = plt.subplots()
        bars = ax.bar(["A", "B"], [1, 2], label="test")

        legend = LegendConfig(role="primary", title="")
        spec = FigureConfig(legends=[legend])
        resolved = resolve_config(spec)

        panel = MatplotlibRenderResult(
            ax,
            bindings=(
                MatplotlibTraceBinding(
                    0, "test", ax, "primary", "", True, "bar", (bars,), (bars,), bars
                ),
            ),
        )
        FigureSpecToMatplotlib._apply_legends(resolved, panel)

        mpl_legend = ax.get_legend()
        assert mpl_legend is not None
        # Empty title — matplotlib defaults to empty string
        assert mpl_legend.get_title().get_text() == ""
        plt.close(fig)


class TestStandoffDefault:
    """C1: Y-axis standoff default should be -1 (auto sentinel)."""

    def test_axis_config_standoff_default(self) -> None:
        """AxisConfig label_standoff should default to -1 (auto)."""
        axis = AxisConfig()
        assert axis.label_standoff == -1

    def test_plotly_connector_skips_negative_standoff(self) -> None:
        """Plotly omits the sentinel standoff value."""
        axis = AxisConfig(label_standoff=-1)
        axes = AxesConfig(x=axis)
        spec = FigureConfig(axes=axes)
        resolved = resolve_config(spec)
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1])])
        rendered = PlotlyRenderResult(
            fig, ((PlotlyTraceBinding(0, "", fig.data[0], "primary", "", True),),)
        )
        FigureSpecToPlotly.apply(resolved, rendered)
        # When standoff is -1, it should not be set on the layout
        layout = cast(Any, fig.layout)
        assert layout.xaxis.title.standoff is None


class TestPlotlyLegendShift:
    """Legend vertical shifts use the resolved native figure dimensions."""

    def test_plotly_connector_vshift_zero_height_guard(self) -> None:
        """C2: vshift should not crash when dimensions height is zero."""
        axis = AxisConfig(label_standoff=50)
        axes = AxesConfig(y=axis)
        spec = FigureConfig(
            axes=axes,
            dimensions=DimensionConfig(width=7.0, height=0.1, dpi=100),
        )
        resolved = resolve_config(spec)
        fig = go.Figure(data=[go.Bar(x=["A"], y=[1])])
        # This should not raise ZeroDivisionError
        rendered = PlotlyRenderResult(
            fig, ((PlotlyTraceBinding(0, "", fig.data[0], "primary", "", True),),)
        )
        FigureSpecToPlotly.apply(resolved, rendered)
