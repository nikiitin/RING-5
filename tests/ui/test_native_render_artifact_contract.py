"""Real widgets reuse or atomically replace the exact selected-engine native artifact."""

from typing import Literal, cast

import pandas as pd
import plotly.graph_objects as go
from matplotlib.figure import Figure as MplFigure
from matplotlib.patches import Rectangle
from streamlit.testing.v1 import AppTest

from src.core.application_api import ApplicationAPI
from src.core.models.plot_config import PlotConfig
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.web.pages.ui.plotting.base_plot import BasePlot
import pytest

from src.web.pages.ui.plotting.plot_service import PlotService
from src.web.rendering.engine_manager import EngineManager
from src.web.state.ui_state_manager import WidgetKeyBuilder
from tests.ui.helpers import create_app_with_data, get_api, navigate_to


def _app(
    engine: str, monkeypatch: pytest.MonkeyPatch
) -> tuple[AppTest, ApplicationAPI, BasePlot, list[str], set[str]]:
    app = create_app_with_data(pd.DataFrame({"kind": ["a", "b", "c"], "metric": [3.0, 5.0, 7.0]}))
    api = get_api(app)
    plot = PlotService.create_plot("Measured", "bar", api.state_manager)
    plot.replace_processed_data(api.state_manager.get_data())
    plot.config = {"x": "kind", "y": "metric", "title": "Measured"}
    callback = plot.create_traces
    calls: list[str] = []
    rejected: set[str] = set()

    def tracked(data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult:
        calls.append(str(config.get("title", "")))
        if config.get("title") in rejected:
            raise ValueError("Deliberate invalid rendering request")
        return callback(data, config)

    monkeypatch.setattr(plot, "create_traces", tracked)
    app.session_state[EngineManager.STATE_KEY] = engine
    navigate_to(app, "Manage Plots")
    assert not app.exception
    return app, api, plot, calls, rejected


def _native_values(plot: BasePlot) -> None:
    artifact = plot.render_artifact
    assert artifact.figure is plot.last_generated_fig
    assert artifact.preparation is not None
    assert artifact.source_data is not None
    assert artifact.source_data["metric"].tolist() == [3.0, 5.0, 7.0]
    if artifact.engine == "plotly":
        assert isinstance(artifact.figure, go.Figure)
        assert isinstance(artifact.figure.data[0], go.Bar)
        assert list(artifact.figure.data[0].y) == [3.0, 5.0, 7.0]
    else:
        assert isinstance(artifact.figure, MplFigure)
        assert all(isinstance(patch, Rectangle) for patch in artifact.figure.axes[0].patches)
        assert [
            cast(Rectangle, patch).get_height() for patch in artifact.figure.axes[0].patches
        ] == [3.0, 5.0, 7.0]


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_actual_widgets_cache_one_native_generation_and_manual_refresh_builds_once(
    engine: Literal["plotly", "matplotlib"], monkeypatch: pytest.MonkeyPatch
) -> None:
    # [test->req~ring5.plots.refresh-cache~1]
    app, api, plot, calls, _ = _app(engine, monkeypatch)
    try:
        assert calls == ["Measured"]
        original = plot.render_artifact
        _native_values(plot)
        app.run()
        assert not app.exception
        assert plot.render_artifact is original
        assert calls == ["Measured"]
        app.button(key=WidgetKeyBuilder.plot_key(plot.plot_id, "widgets.refresh")).click().run()
        assert not app.exception
        assert calls == ["Measured", "Measured"]
        assert plot.render_artifact is not original
        _native_values(plot)
    finally:
        api.close(wait=True)


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_manual_draft_and_failed_native_request_keep_the_published_figure_and_configuration(
    engine: Literal["plotly", "matplotlib"], monkeypatch: pytest.MonkeyPatch
) -> None:
    app, api, plot, calls, rejected = _app(engine, monkeypatch)
    try:
        original = plot.render_artifact
        app.toggle(key=WidgetKeyBuilder.plot_key(plot.plot_id, "widgets.auto_refresh")).set_value(
            False
        ).run()
        app.text_input(key=WidgetKeyBuilder.plot_key(plot.plot_id, "widgets.title")).set_value(
            "Rejected"
        ).run()
        assert not app.exception
        assert plot.render_artifact is original
        assert plot.config["title"] == "Measured"
        assert calls == ["Measured"]
        rejected.add("Rejected")
        app.button(key=WidgetKeyBuilder.plot_key(plot.plot_id, "widgets.refresh")).click().run()
        assert any("Deliberate invalid" in error.message for error in app.exception)
        assert plot.render_artifact is original
        assert plot.config["title"] == "Measured"
        assert calls == ["Measured", "Rejected"]
        _native_values(plot)
        rejected.clear()
        app.text_input(key=WidgetKeyBuilder.plot_key(plot.plot_id, "widgets.title")).set_value(
            "Accepted"
        ).run()
        assert plot.render_artifact is original
        app.button(key=WidgetKeyBuilder.plot_key(plot.plot_id, "widgets.refresh")).click().run()
        assert not app.exception
        assert plot.config["title"] == "Accepted"
        assert calls == ["Measured", "Rejected", "Accepted"]
        _native_values(plot)
    finally:
        api.close(wait=True)
