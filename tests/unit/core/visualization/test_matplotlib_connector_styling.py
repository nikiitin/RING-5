"""Matplotlib connector — per-trace styling parity with the Plotly connector.

The Matplotlib (PDF/LaTeX export) path must apply the same per-series styling
and per-trace overrides as the Plotly preview, otherwise exported publication
figures silently differ from what the user designed in the app.
"""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import to_rgba  # noqa: E402

from src.core.models.visualization.figure_config import FigureConfig  # noqa: E402
from src.core.models.visualization.series_style_config import SeriesStyleConfig  # noqa: E402
from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib  # noqa: E402


def _bar_line_ax() -> tuple[plt.Figure, plt.Axes]:
    fig, ax = plt.subplots()
    ax.bar(["A", "B"], [1, 2], label="bars")
    ax.plot(["A", "B"], [3, 4], label="line")
    return fig, ax


def _by_label(ax: plt.Axes) -> dict:
    handles, labels = ax.get_legend_handles_labels()
    return dict(zip(labels, handles))


class TestTraceOverrides:
    # [test->req~ring5.figure.series-styling~1]
    def test_color_override_recolors_bar_and_line(self) -> None:
        fig, ax = _bar_line_ax()
        spec = FigureConfig(
            trace_overrides={
                "bars": SeriesStyleConfig(color="#ff0000"),
                "line": SeriesStyleConfig(color="#00ff00"),
            }
        )
        FigureSpecToMatplotlib._apply_trace_overrides(spec, ax)
        artists = _by_label(ax)
        assert tuple(artists["bars"].patches[0].get_facecolor()) == to_rgba("#ff0000")
        assert to_rgba(artists["line"].get_color()) == to_rgba("#00ff00")
        plt.close(fig)

    def test_hatch_override_on_bar(self) -> None:
        fig, ax = _bar_line_ax()
        spec = FigureConfig(trace_overrides={"bars": SeriesStyleConfig(hatching_pattern="/")})
        FigureSpecToMatplotlib._apply_trace_overrides(spec, ax)
        assert _by_label(ax)["bars"].patches[0].get_hatch() == "/"
        plt.close(fig)

    def test_display_name_renames_legend_entry(self) -> None:
        fig, ax = _bar_line_ax()
        spec = FigureConfig(trace_overrides={"line": SeriesStyleConfig(display_name="Renamed")})
        FigureSpecToMatplotlib._apply_trace_overrides(spec, ax)
        _, labels = ax.get_legend_handles_labels()
        assert "Renamed" in labels
        assert "line" not in labels
        plt.close(fig)

    def test_no_overrides_is_noop(self) -> None:
        fig, ax = _bar_line_ax()
        before = tuple(_by_label(ax)["bars"].patches[0].get_facecolor())
        FigureSpecToMatplotlib._apply_trace_overrides(FigureConfig(trace_overrides={}), ax)
        assert tuple(_by_label(ax)["bars"].patches[0].get_facecolor()) == before
        plt.close(fig)


class TestSeriesStyling:
    # [test->req~ring5.figure.series-styling~1]
    def test_bar_border_applied(self) -> None:
        fig, ax = _bar_line_ax()
        # series_styles apply by index; give every series the border so the
        # assertion is independent of the artist enumeration order.
        border = SeriesStyleConfig(bar_border_width=2.0, bar_border_color="#000000")
        spec = FigureConfig(series_styles=[border, border])
        FigureSpecToMatplotlib._apply_series_styling(spec, ax)
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
