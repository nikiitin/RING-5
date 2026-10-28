"""Public native artifacts publish configuration and measured content as one generation."""

from concurrent.futures import ThreadPoolExecutor
from collections.abc import Callable
from threading import Event, current_thread
from typing import Any, Literal, cast

import matplotlib.pyplot as plt
from matplotlib.figure import Figure as MplFigure
from matplotlib.patches import Rectangle
import pandas as pd
import plotly.graph_objects as go
import pytest

import ring5
from src.core.common.plot_render_state import PlotRenderBinding
from src.core.models.plot_config import PlotConfig
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.web.models.render_artifact import RenderArtifact
from src.web.rendering.figure_preparation import PreparedFigure


@pytest.mark.public_api
@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_concurrent_public_rendering_never_pairs_one_generation_config_with_another_figure(
    engine: Literal["plotly", "matplotlib"], monkeypatch: pytest.MonkeyPatch
) -> None:
    entered, release = Event(), Event()
    with ring5.Session() as session:
        plot = session.create_plot(
            "bar",
            data=ring5.Table(pd.DataFrame({"x": ["a", "b"], "y": [3.0, 4.0]})),
            config={"x": "x", "y": "y"},
        )
        callback = plot.create_traces
        publish = plot.render_state.publish

        def traces(data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult:
            config["title"] = "A" if current_thread().name.startswith("render-A") else "B"
            return callback(data, config)

        def gated_publish(
            payload: RenderArtifact, retire: Callable[[], None], **kwargs: Any
        ) -> PlotRenderBinding[RenderArtifact] | None:
            if payload.config["title"] == "A":
                entered.set()
                assert release.wait(5)
            return publish(payload, retire, **kwargs)

        monkeypatch.setattr(plot, "create_traces", traces)
        monkeypatch.setattr(plot.render_state, "publish", gated_publish)
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="render-A") as executor:
            pending = executor.submit(session.render, plot, engine=engine)
            try:
                assert entered.wait(5)
                other = session.render(plot, engine=engine)
                assert plot.config["title"] == "B"
            finally:
                release.set()
            figure = pending.result(timeout=5)
        assert plot.config["title"] == "A"
        assert plot.render_artifact.figure is figure
        artifact = plot.render_artifact
        assert artifact.config["title"] == "A"
        assert artifact.figure is figure
        assert artifact.preparation is not None
        if engine == "plotly":
            assert cast(go.Figure, figure).layout.title.text == "A"
            assert cast(go.Figure, other).layout.title.text == "B"
            assert list(cast(Any, figure).data[0].y) == [3.0, 4.0]
        else:
            assert cast(MplFigure, figure).axes[0].get_title() == "A"
            assert cast(MplFigure, other).axes[0].get_title() == "B"
            assert [patch.get_height() for patch in cast(Any, figure).axes[0].patches] == [3.0, 4.0]
            plt.close(cast(MplFigure, figure))
            plt.close(cast(MplFigure, other))


@pytest.mark.public_api
@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_configuration_reads_are_private_snapshots_and_assignment_invalidates_one_generation(
    engine: Literal["plotly", "matplotlib"],
) -> None:
    with ring5.Session() as session:
        plot = session.create_plot(
            "bar",
            data=ring5.Table(pd.DataFrame({"x": ["a"], "y": [3.0]})),
            config={"x": "x", "y": "y", "title": "Original", "custom": {"values": [1]}},
        )
        native = session.render(plot, engine=engine)
        published = plot.render_artifact
        snapshot = plot.config
        snapshot["title"] = "Changed"
        snapshot["custom"]["values"].append(2)
        assert plot.config["title"] == "Original"
        assert plot.config["custom"] == {"values": [1]}
        assert plot.render_artifact is published
        artifact_config = published.config
        artifact_config["title"] = "Artifact mutation"
        artifact_config["custom"]["values"].append(99)
        assert isinstance(published.preparation, PreparedFigure)
        prepared_config = published.preparation.config
        prepared_config["title"] = "Preparation mutation"
        assert plot.config["title"] == "Original"
        assert plot.config["custom"] == {"values": [1]}
        plot.config = snapshot
        assert plot.render_artifact.figure is None
        assert plot.render_artifact.preparation is None
        assert plot.render_artifact.cache_key is None
        assert plot.config == snapshot
        snapshot["custom"]["values"].append(9)
        assert plot.config["custom"] == {"values": [1, 2]}
        rendered = session.render(plot, engine=engine)
        assert plot.config["title"] == "Changed"
        if engine == "plotly":
            assert cast(go.Figure, native).layout.title.text == "Original"
            assert cast(go.Figure, rendered).layout.title.text == "Changed"
        else:
            assert cast(MplFigure, native).axes[0].get_title() == "Original"
            assert cast(MplFigure, rendered).axes[0].get_title() == "Changed"
            plt.close(cast(MplFigure, native))
            plt.close(cast(MplFigure, rendered))


@pytest.mark.public_api
@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_artifact_admission_rejects_retired_fields_and_partial_native_states(
    engine: Literal["plotly", "matplotlib"],
) -> None:
    from dataclasses import replace

    with ring5.Session() as session:
        plot = session.create_plot(
            "bar",
            data=ring5.Table(pd.DataFrame({"x": ["a"], "y": [3.0]})),
            config={"x": "x", "y": "y"},
        )
        figure = session.render(plot, engine=engine)
        original = plot.render_artifact
        assert original.engine == engine
        assert original.native_result is not None and original.native_result.figure is figure
        for changes in (
            {"engine": "matplotlib" if engine == "plotly" else "plotly"},
            {"engine": None},
            {"figure": None},
        ):
            with pytest.raises(TypeError, match="unexpected keyword"):
                replace(original, **changes)
            assert plot.render_artifact is original
            assert original.figure is figure
        for partial_changes in (
            {"preparation": None},
            {"native_result": None},
            {"native_result": figure},
        ):
            with pytest.raises(ValueError):
                replace(original, **partial_changes)
            assert plot.render_artifact is original
            assert original.figure is figure
        with pytest.raises(ValueError, match="complete native"):
            plot.publish_render_artifact(RenderArtifact({"title": "Detached"}))
        assert plot.render_artifact is original
        for detached_changes in (
            {"cache_key": "fake"},
            {"source_data": pd.DataFrame()},
        ):
            with pytest.raises(ValueError, match="configuration only"):
                RenderArtifact({}, **detached_changes)
        retired_engine: dict[str, Any] = {"engine": engine}
        with pytest.raises(TypeError, match="unexpected keyword"):
            RenderArtifact({}, **retired_engine)


@pytest.mark.public_api
@pytest.mark.parametrize("action", ["invalidate", "replace", "delete", "reset"])
def test_retirement_does_not_claim_a_manager_borrowers_register_after_publication(
    action: str,
) -> None:
    from io import BytesIO
    from matplotlib import _pylab_helpers
    from matplotlib.backend_bases import FigureManagerBase
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    with ring5.Session() as session:
        plot = session.create_plot(
            "bar",
            data=ring5.Table(pd.DataFrame({"x": ["a", "b"], "y": [3.0, 4.0]})),
            config={"x": "x", "y": "y"},
        )
        figure = session.render(plot, engine="matplotlib")
        assert isinstance(figure, MplFigure)
        assert not any(
            manager.canvas.figure is figure for manager in _pylab_helpers.Gcf.get_all_fig_managers()
        )
        canvas = FigureCanvasAgg(figure)
        number = max(plt.get_fignums(), default=0) + 1000
        borrowed_manager = FigureManagerBase(canvas, number)
        _pylab_helpers.Gcf._set_new_active_manager(borrowed_manager)
        try:
            if action == "invalidate":
                plot.invalidate_figure()
            elif action == "replace":
                session.render(plot, engine="plotly")
            elif action == "delete":
                session.api.state_manager.set_plots([])
            else:
                session.api.reset_session()
            assert _pylab_helpers.Gcf.get_fig_manager(number) is borrowed_manager
            assert [cast(Rectangle, patch).get_height() for patch in figure.axes[0].patches] == [
                3.0,
                4.0,
            ]
            buffer = BytesIO()
            figure.savefig(buffer, format="svg")
            assert b"<svg" in buffer.getvalue()
        finally:
            _pylab_helpers.Gcf.destroy(number)


@pytest.mark.public_api
@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_relayout_config_assignment_cannot_clear_a_fresh_concurrent_publication(
    engine: Literal["plotly", "matplotlib"],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entered, release = Event(), Event()
    with ring5.Session() as session:
        plot = session.create_plot(
            "bar",
            data=ring5.Table(pd.DataFrame({"x": ["a"], "y": [3.0]})),
            config={"x": "x", "y": "y"},
        )
        session.render(plot, engine=engine)
        set_config = plot.render_state.set_detached_payload

        def gated_config(payload: RenderArtifact) -> PlotRenderBinding[RenderArtifact] | None:
            previous = set_config(payload)
            entered.set()
            assert release.wait(5)
            return previous

        monkeypatch.setattr(plot.render_state, "set_detached_payload", gated_config)
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(plot.update_from_relayout, {"legend.x": 0.25})
            try:
                assert entered.wait(5)
                fresh = session.render(plot, engine=engine)
            finally:
                release.set()
            assert pending.result(timeout=5)
        assert plot.render_artifact.figure is fresh
        assert plot.config["legend_x"] == 0.25
