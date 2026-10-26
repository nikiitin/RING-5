"""Matplotlib connector — per-trace styling parity with the Plotly connector.

The Matplotlib (PDF/LaTeX export) path must apply the same per-series styling
and per-trace overrides as the Plotly preview, otherwise exported publication
figures silently differ from what the user designed in the app.
"""

import matplotlib
from typing import Any

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import to_rgba  # noqa: E402

from src.core.models.visualization.figure_config import FigureConfig  # noqa: E402
from src.core.models.visualization.legend_config import LegendConfig  # noqa: E402
from src.core.models.visualization.series_style_config import SeriesStyleConfig  # noqa: E402
from src.core.services.visualization.config_resolver import resolve_config  # noqa: E402
from src.web.rendering._appearance import seed_matplotlib_appearance  # noqa: E402
from src.web.rendering._render_result import (  # noqa: E402
    MatplotlibFigureResult,
    MatplotlibRenderResult,
    MatplotlibTraceBinding,
)
from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib  # noqa: E402


def _bar_line_panel() -> tuple[plt.Figure, MatplotlibRenderResult]:
    """Bind the two declared fixture sources to their actual native emissions."""
    fig, ax = plt.subplots()
    bars = ax.bar(["A", "B"], [1, 2], label="bars")
    line = ax.plot(["A", "B"], [3, 4], label="line")[0]
    return fig, MatplotlibRenderResult(
        ax,
        bindings=(
            MatplotlibTraceBinding(
                0,
                "bars",
                ax,
                "primary",
                "",
                True,
                "bar",
                (bars,),
                (bars,),
                bars,
                appearance=seed_matplotlib_appearance(
                    (bars,),
                    opacity=1.0,
                    series_channels=tuple((patch, "face") for patch in bars.patches),
                ),
            ),
            MatplotlibTraceBinding(
                1,
                "line",
                ax,
                "primary",
                "",
                True,
                "line",
                (line,),
                (line,),
                line,
                appearance=seed_matplotlib_appearance(
                    (line,),
                    opacity=1.0,
                    series_channels=tuple(
                        (line, kind) for kind in ("line", "marker_face", "marker_edge")
                    ),
                ),
            ),
        ),
    )


def _by_label(ax: plt.Axes) -> dict[str, Any]:
    handles, labels = ax.get_legend_handles_labels()
    return dict(zip(labels, handles))


class TestTraceOverrides:
    # [test->req~ring5.figure.series-styling~2]
    def test_color_override_recolors_bar_and_line(self) -> None:
        fig, panel = _bar_line_panel()
        ax = panel.primary_axes
        spec = FigureConfig(
            trace_overrides={
                "bars": SeriesStyleConfig(color="#ff0000"),
                "line": SeriesStyleConfig(color="#00ff00"),
            }
        )
        FigureSpecToMatplotlib.apply(spec, MatplotlibFigureResult(fig, (panel,)))
        artists = _by_label(ax)
        assert tuple(artists["bars"].patches[0].get_facecolor()) == to_rgba("#ff0000")
        assert to_rgba(artists["line"].get_color()) == to_rgba("#00ff00")
        plt.close(fig)

    def test_hatch_override_on_bar(self) -> None:
        fig, panel = _bar_line_panel()
        ax = panel.primary_axes
        spec = FigureConfig(trace_overrides={"bars": SeriesStyleConfig(hatching_pattern="/")})
        FigureSpecToMatplotlib._apply_trace_overrides(spec, panel)
        assert _by_label(ax)["bars"].patches[0].get_hatch() == "/"
        plt.close(fig)

    def test_legend_labels_project_legend_entry(self) -> None:
        fig, panel = _bar_line_panel()
        ax = panel.primary_axes
        spec = resolve_config(
            FigureConfig(legends=[LegendConfig()], legend_labels={"line": "Renamed"})
        )
        FigureSpecToMatplotlib._apply_legends(spec, panel)
        legend = ax.get_legend()
        assert legend is not None
        labels = [text.get_text() for text in legend.get_texts()]
        assert "Renamed" in labels
        assert "line" not in labels
        assert "line" in _by_label(ax)
        assert [binding.original_name for binding in panel.bindings] == ["bars", "line"]
        plt.close(fig)

    def test_no_overrides_is_noop(self) -> None:
        fig, panel = _bar_line_panel()
        ax = panel.primary_axes
        before = tuple(_by_label(ax)["bars"].patches[0].get_facecolor())
        FigureSpecToMatplotlib._apply_trace_overrides(FigureConfig(trace_overrides={}), panel)
        assert tuple(_by_label(ax)["bars"].patches[0].get_facecolor()) == before
        plt.close(fig)


class TestSeriesStyling:
    # [test->req~ring5.figure.series-styling~2]
    def test_bar_border_applied(self) -> None:
        fig, panel = _bar_line_panel()
        ax = panel.primary_axes
        # Give both declared source slots the border under test.
        border = SeriesStyleConfig(bar_border_width=2.0, bar_border_color="#000000")
        spec = FigureConfig(series_styles=[border, border])
        FigureSpecToMatplotlib.apply(spec, MatplotlibFigureResult(fig, (panel,)))
        bar_patch = _by_label(ax)["bars"].patches[0]
        assert bar_patch.get_linewidth() == 2.0
        assert tuple(bar_patch.get_edgecolor()) == to_rgba("#000000")
        plt.close(fig)


class TestConnectorParity:
    # [test->req~ring5.extension.render-connector~1]

    def test_both_connectors_expose_per_trace_styling(self) -> None:
        from src.web.rendering.plotly_connector import FigureSpecToPlotly

        for cls in (FigureSpecToPlotly, FigureSpecToMatplotlib):
            assert hasattr(cls, "_apply_series_styling")
            assert hasattr(cls, "_apply_trace_overrides")

    def test_matplotlib_implements_every_pipeline_step(self) -> None:
        from src.web.rendering._connector_protocol import STYLING_PIPELINE_ORDER

        # Matplotlib is the canonical-order engine: it must implement an
        # _apply_<step> for every named step in the styling pipeline contract.
        for step in STYLING_PIPELINE_ORDER:
            assert hasattr(FigureSpecToMatplotlib, f"_apply_{step}"), f"missing _apply_{step}"
