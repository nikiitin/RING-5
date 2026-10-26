"""Public API coverage for complete multi-panel dashboard rendering."""

from __future__ import annotations

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
from matplotlib.collections import PathCollection
import pytest

import ring5
from tests.helpers.html_assertions import assert_plotly_document
from src.web.pages.ui.plotting.base_plot import BasePlot

pytestmark = pytest.mark.public_api


def _plots(session: ring5.Session) -> list[BasePlot]:
    bars = session.create_plot(
        "bar",
        data=ring5.Table(pd.DataFrame({"category": ["A", "B"], "value": [1.0, 2.0]})),
        config={
            "x": "category",
            "y": "value",
            "title": "Configured bar title",
            "xlabel": "Category",
            "ylabel": "Metric",
        },
        name="Bars",
    )
    line = session.create_plot(
        "line",
        data=ring5.Table(pd.DataFrame({"category": ["A", "B"], "value": [2.5, 1.5]})),
        config={
            "x": "category",
            "y": "value",
            "title": "Configured line title",
            "xlabel": "Category",
            "ylabel": "Metric",
        },
        name="Trend",
    )
    scatter = session.create_plot(
        "scatter",
        data=ring5.Table(pd.DataFrame({"category": ["A", "B"], "value": [0.5, 3.0]})),
        config={"x": "category", "y": "value"},
        name="Points",
    )
    return [bars, line, scatter]


def _assert_shared_source_glyphs(figure: go.Figure | Figure) -> None:
    """A shared name keeps distinct bar, line and scatter glyphs with exact values."""
    if isinstance(figure, go.Figure):
        bar, line, scatter = figure.data
        assert isinstance(bar, go.Bar)
        assert isinstance(line, go.Scatter) and line.mode is not None
        assert isinstance(scatter, go.Scatter) and scatter.mode is not None
        assert "lines" in line.mode and "markers" in scatter.mode
        assert [np.asarray(trace.y).tolist() for trace in (bar, line, scatter)] == [
            [1.0, 2.0],
            [2.5, 1.5],
            [0.5, 3.0],
        ]
        assert sum(trace.showlegend is not False for trace in (bar, line, scatter)) == 3
    else:
        assert len(figure.legends) == 1
        legend = figure.legends[0]
        assert [text.get_text() for text in legend.texts] == ["value"] * 3
        assert len(legend.legend_handles) == 3
        assert isinstance(legend.legend_handles[0], Rectangle)
        assert isinstance(legend.legend_handles[1], Line2D)
        assert isinstance(legend.legend_handles[2], PathCollection)
        heights = []
        for patch in figure.axes[0].patches:
            assert isinstance(patch, Rectangle)
            heights.append(patch.get_height())
        assert heights == [1.0, 2.0]
        assert np.asarray(figure.axes[1].lines[0].get_ydata()).tolist() == [2.5, 1.5]
        assert np.asanyarray(figure.axes[2].collections[0].get_offsets())[:, 1].tolist() == [
            0.5,
            3.0,
        ]


def test_public_dashboard_renders_both_engines_and_exports_whole_figure() -> None:
    # [test->req~ring5.plots.multi-panel-dashboard~1]
    with ring5.Session() as session:
        plots = _plots(session)
        dashboard = session.create_dashboard(
            plots,
            title="Performance overview",
            columns=2,
            width=1000,
            height=700,
            shared_xaxes=True,
            shared_yaxes=True,
            shared_legend=True,
            x_title="Workload",
            y_title="Normalized value",
        )

        assert isinstance(dashboard, ring5.DashboardSpec)
        assert dashboard.plot_ids == (0, 1, 2)
        assert dashboard.panel_titles == ("Bars", "Trend", "Points")
        assert (dashboard.rows, dashboard.columns) == (2, 2)

        plotly_figure = session.render_dashboard(dashboard, engine="plotly")
        assert isinstance(plotly_figure, go.Figure)
        assert len(plotly_figure.data) == 3
        assert plotly_figure.layout.title.text == "Performance overview"
        assert (plotly_figure.layout.width, plotly_figure.layout.height) == (1000, 700)
        annotations = {annotation.text for annotation in plotly_figure.layout.annotations}
        assert {"Bars", "Trend", "Points", "Workload", "Normalized value"} <= annotations
        _assert_shared_source_glyphs(plotly_figure)
        assert any(axis.matches for axis in plotly_figure.select_xaxes())
        assert any(axis.matches for axis in plotly_figure.select_yaxes())
        assert_plotly_document(session.export_bytes(plotly_figure, "html"))

        direct_figure = ring5.render_dashboard(session.plots, dashboard, engine="plotly")
        assert isinstance(direct_figure, go.Figure)
        assert len(direct_figure.data) == 3

        matplotlib_figure = session.render_dashboard(dashboard, engine="matplotlib")
        assert isinstance(matplotlib_figure, Figure)
        assert matplotlib_figure.get_size_inches().tolist() == pytest.approx([1000 / 96, 700 / 96])
        assert [axis.get_title() for axis in matplotlib_figure.axes[:3]] == [
            "Bars",
            "Trend",
            "Points",
        ]
        assert (
            matplotlib_figure.axes[0]
            .get_shared_x_axes()
            .joined(matplotlib_figure.axes[0], matplotlib_figure.axes[1])
        )
        _assert_shared_source_glyphs(matplotlib_figure)
        assert session.export_bytes(matplotlib_figure, "pdf")[:5] == b"%PDF-"


def test_dashboard_validation_and_live_plot_lookup_use_typed_errors() -> None:
    with ring5.Session() as session:
        plots = _plots(session)
        with pytest.raises(ring5.DataValidationError, match="at least two"):
            session.create_dashboard(plots[:1])
        with pytest.raises(ring5.DataValidationError, match="unknown plot IDs"):
            session.create_dashboard([plots[0], 999])

        dashboard = session.create_dashboard(plots[:2])
        session.api.state_manager.set_plots([plots[0]])
        with pytest.raises(ring5.RenderError, match="no longer available"):
            session.render_dashboard(dashboard)


def test_dashboard_can_keep_panel_titles_and_legends_independent() -> None:
    with ring5.Session() as session:
        plots = _plots(session)[:2]
        dashboard = session.create_dashboard(
            plots,
            columns=2,
            panel_titles=["Panel A", "Panel B"],
            shared_legend=False,
        )

        plotly_figure = session.render_dashboard(dashboard, engine="plotly")
        assert isinstance(plotly_figure, go.Figure)
        legends = []
        for trace in plotly_figure.data:
            assert isinstance(trace, (go.Bar, go.Scatter))
            legends.append(trace.legend)
        assert legends == ["legend", "legend2"]
        assert plotly_figure.layout.legend2 is not None

        matplotlib_figure = session.render_dashboard(dashboard, engine="matplotlib")
        assert isinstance(matplotlib_figure, Figure)
        assert [axis.get_title() for axis in matplotlib_figure.axes] == ["Panel A", "Panel B"]
        assert all(axis.get_legend() is not None for axis in matplotlib_figure.axes)


def test_publication_panel_composition_is_consistent_across_engines() -> None:
    # [test->req~ring5.figure.panel-composition~1]
    with ring5.Session() as session:
        plots = _plots(session)
        dashboard = session.create_dashboard(
            plots,
            title="Common publication title",
            columns=2,
            panel_labels="auto",
            panel_captions=["Baseline", "Optimized", "Validation"],
            horizontal_spacing=0.05,
            vertical_spacing=0.12,
            shared_legend=True,
        )

        assert dashboard.panel_labels == ("(a)", "(b)", "(c)")
        assert dashboard.panel_captions == ("Baseline", "Optimized", "Validation")

        plotly_figure = session.render_dashboard(dashboard, engine="plotly")
        assert isinstance(plotly_figure, go.Figure)
        annotation_text = set()
        for annotation in plotly_figure.layout.annotations:
            assert isinstance(annotation.text, str)
            annotation_text.add(annotation.text.replace("<b>", "").replace("</b>", ""))
        assert {
            "(a)",
            "(b)",
            "(c)",
            "Baseline",
            "Optimized",
            "Validation",
        } <= annotation_text
        assert plotly_figure.layout.title.text == "Common publication title"
        assert plotly_figure.layout.xaxis2.domain[0] - plotly_figure.layout.xaxis.domain[1] == (
            pytest.approx(0.05)
        )
        assert plotly_figure.layout.yaxis.domain[0] - plotly_figure.layout.yaxis3.domain[1] == (
            pytest.approx(0.12)
        )
        _assert_shared_source_glyphs(plotly_figure)

        matplotlib_figure = session.render_dashboard(dashboard, engine="matplotlib")
        assert isinstance(matplotlib_figure, Figure)
        labels: list[str] = []
        captions: list[str] = []
        for axis in matplotlib_figure.axes[:3]:
            labels.extend(
                text.get_text() for text in axis.texts if text.get_gid() == "ring5-panel-label"
            )
            captions.extend(
                text.get_text() for text in axis.texts if text.get_gid() == "ring5-panel-caption"
            )
        assert labels == ["(a)", "(b)", "(c)"]
        assert captions == ["Baseline", "Optimized", "Validation"]
        assert matplotlib_figure.get_suptitle() == "Common publication title"
        horizontal_extent = matplotlib_figure.subplotpars.right - matplotlib_figure.subplotpars.left
        vertical_extent = matplotlib_figure.subplotpars.top - matplotlib_figure.subplotpars.bottom
        axes = matplotlib_figure.axes
        assert (axes[1].get_position().x0 - axes[0].get_position().x1) / horizontal_extent == (
            pytest.approx(0.05)
        )
        assert (axes[0].get_position().y0 - axes[2].get_position().y1) / vertical_extent == (
            pytest.approx(0.12)
        )
        assert len(matplotlib_figure.legends) == 1
        _assert_shared_source_glyphs(matplotlib_figure)


def test_publication_panel_composition_rejects_misaligned_text() -> None:
    with ring5.Session() as session:
        plots = _plots(session)[:2]
        with pytest.raises(ring5.DataValidationError, match="panel_captions"):
            session.create_dashboard(plots, panel_captions=["Only one"])
        with pytest.raises(ring5.DataValidationError, match="panel_labels"):
            session.create_dashboard(plots, panel_labels="letters")  # type: ignore[arg-type]
