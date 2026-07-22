"""Public API coverage for complete multi-panel dashboard rendering."""

from __future__ import annotations

import pandas as pd
import pytest

import ring5

pytestmark = pytest.mark.public_api


def _plots(session: ring5.Session) -> list[object]:
    bars = session.create_plot(
        "bar",
        data=pd.DataFrame({"category": ["A", "B"], "value": [1.0, 2.0]}),
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
        data=pd.DataFrame({"category": ["A", "B"], "value": [2.5, 1.5]}),
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
        data=pd.DataFrame({"category": ["A", "B"], "value": [0.5, 3.0]}),
        config={"x": "category", "y": "value"},
        name="Points",
    )
    return [bars, line, scatter]


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
        assert len(plotly_figure.data) == 3
        assert plotly_figure.layout.title.text == "Performance overview"
        assert (plotly_figure.layout.width, plotly_figure.layout.height) == (1000, 700)
        annotations = {annotation.text for annotation in plotly_figure.layout.annotations}
        assert {"Bars", "Trend", "Points", "Workload", "Normalized value"} <= annotations
        assert sum(trace.showlegend is not False for trace in plotly_figure.data) == 1
        assert any(axis.matches for axis in plotly_figure.select_xaxes())
        assert any(axis.matches for axis in plotly_figure.select_yaxes())
        assert session.export_bytes(plotly_figure, "html").lstrip().startswith(b"<html")

        direct_figure = ring5.render_dashboard(session.plots, dashboard, engine="plotly")
        assert len(direct_figure.data) == 3

        matplotlib_figure = session.render_dashboard(dashboard, engine="matplotlib")
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
        assert [trace.legend for trace in plotly_figure.data] == ["legend", "legend2"]
        assert plotly_figure.layout.legend2 is not None

        matplotlib_figure = session.render_dashboard(dashboard, engine="matplotlib")
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
        annotation_text = {
            annotation.text.replace("<b>", "").replace("</b>", "")
            for annotation in plotly_figure.layout.annotations
        }
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
        assert sum(trace.showlegend is not False for trace in plotly_figure.data) == 1

        matplotlib_figure = session.render_dashboard(dashboard, engine="matplotlib")
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
        assert matplotlib_figure._suptitle.get_text() == "Common publication title"
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


def test_publication_panel_composition_rejects_misaligned_text() -> None:
    with ring5.Session() as session:
        plots = _plots(session)[:2]
        with pytest.raises(ring5.DataValidationError, match="panel_captions"):
            session.create_dashboard(plots, panel_captions=["Only one"])
        with pytest.raises(ring5.DataValidationError, match="panel_labels"):
            session.create_dashboard(plots, panel_labels="letters")  # type: ignore[arg-type]
