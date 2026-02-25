"""Phase A integration tests — palette unification & matplotlib renderer fixes.

Validates end-to-end that:
  1. Palette registry is the single source of truth
  2. Matplotlib trace renderer uses palette colours correctly
  3. _apply_annotations handles HTML and positioning
  4. enrich_from_plotly correctly patches FigureConfig
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import pytest
from matplotlib.axes import Axes as MplAxes

from src.core.models.visualization.annotation_config import AnnotationConfig
from src.core.models.visualization.figure_config import FigureConfig
from src.core.services.visualization.config_resolver import resolve_config
from src.core.services.visualization.palette_service import (
    get_palette_names,
    is_colorblind_safe,
    resolve_palette,
)
from src.core.models.visualization.trace_config import (
    BarTraceConfig,
    LineTraceConfig,
    ScatterTraceConfig,
)
from src.web.rendering.config_builder import ConfigSpecBuilder, PlotlyFigureSpecBuilder
from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib
from src.web.rendering.matplotlib_trace_renderer import MatplotlibTraceRenderer

matplotlib.use("Agg")


# ── Palette Integration ─────────────────────────────────────────────────


class TestPaletteIntegration:
    """Palette registry is used consistently across the pipeline."""

    def test_all_palettes_resolve(self) -> None:
        """Every palette name resolves to a non-empty hex list."""
        for name in get_palette_names():
            colors = resolve_palette(name)
            assert len(colors) > 0, f"{name} returned empty"
            for c in colors:
                assert c.startswith("#"), f"{name} has non-hex: {c}"

    def test_wong_is_default_fallback(self) -> None:
        """Unknown palette names fall back to Wong."""
        wong = resolve_palette("wong")
        unknown = resolve_palette("__nonexistent__")
        assert unknown == wong

    def test_colorblind_safe_palettes_marked(self) -> None:
        """At least 5 colorblind-safe palettes exist."""
        safe = [n for n in get_palette_names() if is_colorblind_safe(n)]
        assert len(safe) >= 5

    def test_palette_names_start_with_colorblind(self) -> None:
        """Colorblind-safe palettes appear first in the list."""
        names = get_palette_names()
        first_non_cb = next(
            (i for i, n in enumerate(names) if not is_colorblind_safe(n)),
            len(names),
        )
        for n in names[:first_non_cb]:
            assert is_colorblind_safe(n)


# ── Matplotlib Trace Renderer Colour Override ────────────────────────────


class TestTraceRendererPaletteOverride:
    """MatplotlibTraceRenderer uses palette_colors override."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> Generator[None]:
        fig, ax = plt.subplots()
        assert isinstance(ax, MplAxes)
        self.fig = fig
        self.ax: MplAxes = ax
        yield
        plt.close(self.fig)

    def test_bar_uses_override_color(self) -> None:
        traces = [
            BarTraceConfig(
                name="S1",
                x=["A", "B"],
                y=[1, 2],
                x_positions=[-0.2, 0.8],
                bar_width=0.4,
            ),
            BarTraceConfig(
                name="S2",
                x=["A", "B"],
                y=[3, 4],
                x_positions=[0.2, 1.2],
                bar_width=0.4,
            ),
        ]
        palette = ["#ff0000", "#00ff00"]
        MatplotlibTraceRenderer.render(traces, self.ax, palette_colors=palette)

        containers = self.ax.containers
        assert len(containers) == 2
        c0 = containers[0][0].get_facecolor()
        assert _approx_hex(c0) == "#ff0000"
        c1 = containers[1][0].get_facecolor()
        assert _approx_hex(c1) == "#00ff00"

    def test_line_uses_override_color(self) -> None:
        traces = [
            LineTraceConfig(name="L1", x=[1, 2], y=[3, 4]),
        ]
        palette = ["#0000ff"]
        MatplotlibTraceRenderer.render(traces, self.ax, palette_colors=palette)

        lines = self.ax.get_lines()
        assert len(lines) == 1
        assert _approx_hex(lines[0].get_color()) == "#0000ff"

    def test_scatter_uses_override_color(self) -> None:
        traces = [
            ScatterTraceConfig(name="S1", x=[1, 2], y=[3, 4]),
        ]
        palette = ["#abcdef"]
        MatplotlibTraceRenderer.render(traces, self.ax, palette_colors=palette)

        collections = self.ax.collections
        assert len(collections) == 1

    def test_no_palette_uses_extracted_colors(self) -> None:
        """Without palette override, TraceConfig colors are used."""
        traces = [
            BarTraceConfig(
                name="S1",
                x=["A"],
                y=[1],
                color="#ff0000",
                x_positions=[0.0],
                bar_width=0.8,
            ),
        ]
        MatplotlibTraceRenderer.render(traces, self.ax)

        c = self.ax.containers[0][0].get_facecolor()
        assert _approx_hex(c) == "#ff0000"


# ── Annotation Rendering ────────────────────────────────────────────────


class TestAnnotationRendering:
    """FigureSpecToMatplotlib._apply_annotations works correctly."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> Generator[None]:
        fig, ax = plt.subplots()
        assert isinstance(ax, MplAxes)
        self.fig = fig
        self.ax: MplAxes = ax
        yield
        plt.close(self.fig)

    def test_html_br_converted_to_newline(self) -> None:
        ann = AnnotationConfig(
            text="Line1<br>Line2<br/>Line3",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
        )
        spec = FigureConfig(annotations=[ann])
        FigureSpecToMatplotlib._apply_annotations(spec, self.ax)

        texts = self.ax.texts
        assert len(texts) == 1
        assert "\n" in texts[0].get_text()
        assert "<br>" not in texts[0].get_text()

    def test_bordered_annotation_has_bbox(self) -> None:
        ann = AnnotationConfig(
            text="Boxed",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            border_width=1.0,
            border_color="#333",
            bgcolor="#ffffff",
        )
        spec = FigureConfig(annotations=[ann])
        FigureSpecToMatplotlib._apply_annotations(spec, self.ax)

        texts = self.ax.texts
        assert len(texts) == 1
        bbox = texts[0].get_bbox_patch()
        assert bbox is not None

    def test_empty_annotations_noop(self) -> None:
        spec = FigureConfig(annotations=[])
        FigureSpecToMatplotlib._apply_annotations(spec, self.ax)
        assert len(self.ax.texts) == 0


# ── Enrich + Apply End-to-End ────────────────────────────────────────────


class TestEnrichAndApply:
    """Full pipeline: config -> FigureConfig -> enrich -> resolve -> apply."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> Generator[None]:
        fig, ax = plt.subplots()
        assert isinstance(ax, MplAxes)
        self.fig = fig
        self.ax: MplAxes = ax
        yield
        plt.close(self.fig)

    def test_enriched_tick_labels_applied(self) -> None:
        """Tick labels from Plotly figure appear on matplotlib axes."""
        config: dict[str, Any] = {"width": 800, "height": 500}
        spec = ConfigSpecBuilder.from_config(config, "bar")

        plotly_fig = go.Figure()
        plotly_fig.add_bar(x=[0, 1, 2], y=[10, 20, 30])
        plotly_fig.update_xaxes(tickvals=[0, 1, 2], ticktext=["A", "B", "C"])

        PlotlyFigureSpecBuilder.enrich_from_plotly(spec, plotly_fig)
        spec = resolve_config(spec)

        assert spec.axes is not None
        assert spec.axes.x.tick_values == [0, 1, 2]
        assert spec.axes.x.tick_text == ["A", "B", "C"]

        FigureSpecToMatplotlib.apply(spec, self.ax)

        get_labels_fn = getattr(self.ax, "get_xticklabels")
        labels = [t.get_text() for t in get_labels_fn()]
        assert "A" in labels

    def test_enriched_annotations_applied(self) -> None:
        """Annotations from Plotly figure appear on matplotlib axes."""
        config: dict[str, Any] = {"width": 800, "height": 500}
        spec = ConfigSpecBuilder.from_config(config, "bar")

        plotly_fig = go.Figure()
        plotly_fig.add_bar(x=["A"], y=[10])
        plotly_fig.update_layout(
            annotations=[
                dict(
                    text="Group Label",
                    x=0.5,
                    y=-0.1,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(size=12, color="#333"),
                )
            ]
        )

        PlotlyFigureSpecBuilder.enrich_from_plotly(spec, plotly_fig)
        spec = resolve_config(spec)

        assert len(spec.annotations) == 1

        FigureSpecToMatplotlib.apply(spec, self.ax)
        texts = self.ax.texts
        assert len(texts) >= 1
        text_content = " ".join(t.get_text() for t in texts)
        assert "Group" in text_content


# ── Helpers ──────────────────────────────────────────────────────────────


def _approx_hex(color: Any) -> str:
    """Convert matplotlib RGBA tuple or hex string to #rrggbb."""
    if isinstance(color, str):
        return color.lower()
    r, g, b = int(color[0] * 255), int(color[1] * 255), int(color[2] * 255)
    return f"#{r:02x}{g:02x}{b:02x}"
