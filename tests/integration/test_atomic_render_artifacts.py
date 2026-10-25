"""Public native artifacts publish configuration and measured content as one generation."""

from concurrent.futures import ThreadPoolExecutor
from collections.abc import Callable
from threading import Event, current_thread
from typing import Any, Literal, cast

import matplotlib.pyplot as plt
from matplotlib.figure import Figure as MplFigure
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
        assert plot.last_generated_fig is figure
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
        assert plot.last_generated_fig is None
        assert plot.last_traces is None and plot.last_figure_spec is None
        assert plot.last_figure_cache_key is None
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
