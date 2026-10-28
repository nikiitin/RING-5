"""Owned native publication and repository retirement preserve borrowed figure content."""

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from dataclasses import replace
from threading import Event
from typing import Any, Literal, cast

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure as MplFigure
from matplotlib.patches import Rectangle
import pandas as pd
import pytest

import ring5
from src.core.common.typed_table_codec import TypedTableCodec
from src.core.common.plot_render_state import PlotRenderBinding
from src.core.models.portfolio_models import PortfolioData
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import BarTraceConfig
from src.core.state.repositories.plot_repository import PlotRepository
from src.core.state.repository_state_manager import RepositoryStateManager
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.plot_factory import PlotFactory
from src.web.pages.ui.plotting.plot_service import PlotService
from src.web.pages.ui.plotting.types.bar_plot import BarPlot
from src.web.rendering.figure_preparation import PreparedFigure, prepare_figure
from src.web.models.plot_protocols import PlotRenderSource
from src.web.models.render_artifact import RenderArtifact
from src.web.rendering.small_multiples_builder import _facet_views

matplotlib.use("Agg")


def _data() -> pd.DataFrame:
    return pd.DataFrame({"x": ["a", "b"], "y": [3.0, 4.0], "facet": ["one", "two"]})


def _plot(session: ring5.Session, name: str = "Measured") -> BasePlot:
    return session.create_plot(
        "bar", data=ring5.Table(_data()), config={"x": "x", "y": "y", "title": name}, name=name
    )


def _assert_borrowed_content(figure: MplFigure) -> None:
    assert [cast(Rectangle, patch).get_height() for patch in figure.axes[0].patches] == [3.0, 4.0]
    buffer = BytesIO()
    figure.savefig(buffer, format="svg")
    assert b"<svg" in buffer.getvalue()


def _assert_no_artifacts(plot: PlotRenderSource) -> None:
    assert plot.render_artifact.figure is None
    assert plot.render_artifact.preparation is None
    assert plot.render_artifact.cache_key is None


@pytest.mark.public_api
@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_public_native_publication_binds_the_exact_preparation_and_replaces_only_owned_manager(
    engine: Literal["plotly", "matplotlib"],
) -> None:
    # [test->req~ring5.plots.independent-state~1]
    with ring5.Session() as session:
        plot = _plot(session)
        previous = cast(MplFigure, session.render(plot, engine="matplotlib"))
        unrelated, axis = plt.subplots()
        axis.plot([1.0], [9.0])
        try:
            assert unrelated.number == previous.number
            plot.publish_render_artifact(replace(plot.render_artifact, cache_key="previous"))
            figure = session.render(plot, engine=engine)
            assert plot.render_artifact.figure is figure
            prepared = plot.render_artifact.preparation
            assert isinstance(prepared, PreparedFigure)
            assert prepared.trace_result is not None
            assert prepared.spec is not None
            assert plot.render_artifact.cache_key is None
            assert plot.config["title"] == prepared.spec.title == "Measured"
            if engine == "matplotlib":
                assert plot.render_artifact.preparation is prepared
            assert plt.fignum_exists(unrelated.number)
            assert plt.figure(unrelated.number) is unrelated
            _assert_borrowed_content(previous)
        finally:
            plt.close(unrelated)


@pytest.mark.public_api
@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_failed_native_build_retains_every_previously_published_binding(
    engine: Literal["plotly", "matplotlib"], monkeypatch: pytest.MonkeyPatch
) -> None:
    with ring5.Session() as session:
        plot = _plot(session)
        previous = cast(MplFigure, session.render(plot, engine="matplotlib"))
        plot.publish_render_artifact(replace(plot.render_artifact, cache_key="prior"))
        old_prepared = plot.render_artifact.preparation
        assert isinstance(old_prepared, PreparedFigure)
        old_config, old_result, old_spec = (
            plot.config,
            old_prepared.trace_result,
            old_prepared.spec,
        )
        unrelated, _ = plt.subplots()
        managers = set(plt.get_fignums())

        def invalid(_data: pd.DataFrame, config: dict[str, Any]) -> TraceBuildResult:
            config["title"] = "Unpublished"
            config["legend_bgcolor"] = "invalid"
            return TraceBuildResult(
                traces=[
                    BarTraceConfig(name="Measured", x=_data["x"].tolist(), y=_data["y"].tolist())
                ]
            )

        monkeypatch.setattr(plot, "create_traces", invalid)
        try:
            with pytest.raises(ring5.RenderError):
                session.render(plot, engine=engine)
            assert plot.config == old_config and plot.config["title"] == "Measured"
            assert plot.render_artifact.figure is previous
            current = plot.render_artifact.preparation
            assert isinstance(current, PreparedFigure)
            assert current is old_prepared
            assert current.trace_result is old_result
            assert current.spec is old_spec
            assert plot.render_artifact.cache_key == "prior"
            assert set(plt.get_fignums()) == managers
            _assert_borrowed_content(previous)
        finally:
            plt.close(unrelated)


@pytest.mark.public_api
@pytest.mark.parametrize(
    "action",
    [
        "invalidate",
        "processed",
        "source",
        "delete",
        "replace",
        "reorder",
        "clear",
        "reset",
        "restore",
        "type",
        "transfer",
        "close",
    ],
)
def test_plot_retirement_is_identity_scoped_and_borrowed_figures_stay_exportable(
    action: str,
) -> None:
    # [test->req~ring5.plots.delete~1]
    with ring5.Session() as session:
        plot, other = _plot(session), _plot(session, "Other")
        figure = cast(MplFigure, session.render(plot, engine="matplotlib"))
        other_figure = cast(MplFigure, session.render(other, engine="matplotlib"))
        plot.publish_render_artifact(replace(plot.render_artifact, cache_key="retained"))
        unrelated, axis = plt.subplots()
        axis.plot([1.0], [9.0])
        manager = session.api.state_manager
        payload = cast(
            PortfolioData,
            {
                "simulator": "gem5",
                "parser_strategy": "simple",
                "loaded_origin": None,
                "data": TypedTableCodec.encode(_data()),
                "plots": [plot.to_dict(), other.to_dict()],
            },
        )
        try:
            assert unrelated.number == figure.number == other_figure.number
            if action == "invalidate":
                plot.invalidate_figure()
            elif action == "processed":
                plot.replace_processed_data(_data().assign(y=[9.0, 10.0]))
            elif action == "source":
                plot.replace_source_data(_data().assign(y=[9.0, 10.0]))
            elif action == "delete":
                PlotService.delete_plot(plot.plot_id, manager)
            elif action == "replace":
                replacement = PlotFactory.from_dict(plot.to_dict())
                manager.set_plots([replacement, other])
            elif action == "reorder":
                manager.set_plots([other, plot])
            elif action == "clear":
                manager.clear_all()
            elif action == "reset":
                session.api.reset_session()
            elif action == "restore":
                assert manager.restore_session(payload).plots_restored == 2
                assert all(item is not plot and item is not other for item in manager.get_plots())
            elif action == "type":
                PlotService.change_plot_type(plot, "line", manager)
            elif action == "transfer":
                session.api.copy_plot_content(
                    other.plot_id, plot.plot_id, "settings", sections=["labels"]
                )
            else:
                session.close()
            if action in ("reorder", "close"):
                assert plot.render_artifact.figure is figure
                assert plot.render_artifact.cache_key == "retained"
            else:
                _assert_no_artifacts(plot)
            if action in ("clear", "reset", "restore"):
                _assert_no_artifacts(other)
            else:
                assert other.render_artifact.figure is other_figure
            assert plt.fignum_exists(unrelated.number)
            assert plt.figure(unrelated.number) is unrelated
            assert cast(Any, unrelated.axes[0].lines[0].get_ydata()).tolist() == [9.0]
            _assert_borrowed_content(figure)
            _assert_borrowed_content(other_figure)
        finally:
            plt.close(unrelated)
    _assert_borrowed_content(figure)


class _PluginBar(BarPlot):
    __slots__ = ("slot_state",)

    def __init__(self, plot_id: int, name: str) -> None:
        super().__init__(plot_id, name)
        self.plot_type = "lifecycle_plugin"
        self.slot_state = {"notes": [1]}


@pytest.mark.public_api
def test_duplicate_detaches_native_state_before_copy_and_preserves_private_domain_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # [test->req~ring5.plots.duplicate~1]
    monkeypatch.setitem(PlotFactory._plot_classes, "lifecycle_plugin", _PluginBar)
    frame = _data()
    frame["payload"] = pd.Series([{"nested": [1]}, {"nested": [2]}], dtype=object)
    with ring5.Session() as session:
        plot = session.create_plot(
            "lifecycle_plugin", data=ring5.Table(frame), config={"x": "x", "y": "y"}
        )
        source = cast(MplFigure, session.render(plot, engine="matplotlib"))
        source_prepared = plot.render_artifact.preparation
        assert isinstance(source_prepared, PreparedFigure)
        before = (source_prepared.trace_result, source_prepared.spec)

        def reject_copy(_self: Any, _memo: Any) -> Any:
            raise AssertionError("Native artifacts must not be traversed by duplication")

        monkeypatch.setattr(MplFigure, "__deepcopy__", reject_copy, raising=False)
        duplicate = PlotService.duplicate_plot(plot, session.api.state_manager)
        assert isinstance(duplicate, _PluginBar)
        assert duplicate.plot_id != plot.plot_id
        assert duplicate.name == f"{plot.name} (copy)"
        _assert_no_artifacts(duplicate)
        assert plot.render_artifact.figure is source
        current = plot.render_artifact.preparation
        assert isinstance(current, PreparedFigure)
        assert current is source_prepared
        assert current.trace_result is before[0]
        assert current.spec is before[1]
        assert duplicate.processed_data is not None and plot.processed_data is not None
        cast(dict[str, list[int]], duplicate.processed_data.at[0, "payload"])["nested"].append(9)
        duplicate.slot_state["notes"].append(2)
        assert plot.processed_data.at[0, "payload"] == {"nested": [1]}
        assert cast(_PluginBar, plot).slot_state == {"notes": [1]}
        _assert_borrowed_content(source)


@pytest.mark.public_api
def test_facet_views_drop_borrowed_artifacts_without_touching_source_or_domain_payloads() -> None:
    # [test->req~ring5.plots.small-multiples~1]
    frame = _data()
    frame["payload"] = pd.Series([{"nested": [1]}, {"nested": [2]}], dtype=object)
    with ring5.Session() as session:
        plot = session.create_plot("bar", data=ring5.Table(frame), config={"x": "x", "y": "y"})
        source = cast(MplFigure, session.render(plot, engine="matplotlib"))
        source_prepared = plot.render_artifact.preparation
        assert isinstance(source_prepared, PreparedFigure)
        source_result, source_spec = (
            source_prepared.trace_result,
            source_prepared.spec,
        )
        spec = session.create_small_multiples(plot, by="facet")
        views = _facet_views(plot, spec, plot.config)
        assert len(views) == 2
        for view, expected in zip(views, ([3.0], [4.0]), strict=True):
            _assert_no_artifacts(view)
            assert view.processed_data is not None
            assert view.processed_data["y"].tolist() == expected
            view.processed_data.iloc[0]["payload"]["nested"].append(9)
        assert plot.render_artifact.figure is source
        current = plot.render_artifact.preparation
        assert isinstance(current, PreparedFigure)
        assert current is source_prepared
        assert current.trace_result is source_result
        assert current.spec is source_spec
        assert plot.processed_data is not None
        assert plot.processed_data.at[0, "payload"] == {"nested": [1]}
        assert plot.processed_data.at[1, "payload"] == {"nested": [2]}
        _assert_borrowed_content(source)


@pytest.mark.public_api
@pytest.mark.parametrize("reuse_live", [False, True])
def test_rejected_restore_releases_only_new_candidate_artifacts(reuse_live: bool) -> None:
    # [test->req~ring5.portfolio.restore~1]
    entered, release = Event(), Event()
    captured: list[BasePlot] = []
    figures: list[MplFigure] = []
    with ring5.Session() as session:
        live = _plot(session)
        live_figure = cast(MplFigure, session.render(live, engine="matplotlib"))

        def restore_plot(payload: dict[str, Any]) -> BasePlot:
            candidate = live if reuse_live else PlotFactory.from_dict(payload)
            captured.append(candidate)
            figures.append(
                cast(MplFigure, session.render(candidate, engine="matplotlib"))
                if not reuse_live
                else live_figure
            )
            entered.set()
            assert release.wait(10)
            return candidate

        manager = RepositoryStateManager(plot_deserializer=restore_plot)
        manager.add_plot(live)
        payload = cast(
            PortfolioData,
            {
                "simulator": "gem5",
                "parser_strategy": "simple",
                "loaded_origin": None,
                "data": TypedTableCodec.encode(_data()),
                "plots": [live.to_dict()],
            },
        )
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(manager.restore_session, payload)
            try:
                assert entered.wait(10)
                manager.set_config({"newer": True})
            finally:
                release.set()
            with pytest.raises(ValueError, match="Workspace changed"):
                pending.result(timeout=10)
        assert manager.get_plots() == [live]
        assert manager.get_config() == {"newer": True}
        assert live.render_artifact.figure is live_figure
        if not reuse_live:
            _assert_no_artifacts(captured[0])
        _assert_borrowed_content(figures[0])
        _assert_borrowed_content(live_figure)


def test_repository_retains_object_identity_and_does_not_borrow_the_callers_list() -> None:
    repo = PlotRepository()
    plot = BarPlot(0, "Kept")
    unrelated = BarPlot(0, "Same ID, another object")
    incoming: list[Any] = [plot]
    repo.set_plots(incoming)
    incoming.clear()
    assert repo.get_plots() == [plot]
    repo.set_plots([plot, unrelated])
    repo.set_plots([unrelated, plot])
    assert repo.get_plots() == [unrelated, plot]


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_native_publication_retains_verified_key_and_clears_all_metadata_together(
    engine: str,
) -> None:
    from src.web.rendering.matplotlib_figure_builder import build_matplotlib_figure_from_prepared
    from src.web.rendering.plotly_figure_builder import build_plotly_figure

    plot = BarPlot(0, "Measured")
    prepared = prepare_figure(_data(), {"x": "x", "y": "y"}, "bar", plot.create_traces)
    rendered = (
        build_plotly_figure(prepared)
        if engine == "plotly"
        else build_matplotlib_figure_from_prepared(prepared)
    )
    figure = rendered.figure
    plot.publish_render_artifact(
        RenderArtifact(None, rendered, prepared, cache_key="verified-content")
    )
    assert plot.config == prepared.config
    assert plot.render_artifact.figure is figure
    assert plot.render_artifact.preparation is prepared
    assert plot.render_artifact.cache_key == "verified-content"
    plot.invalidate_figure()
    _assert_no_artifacts(plot)
    if isinstance(figure, MplFigure):
        _assert_borrowed_content(figure)
    else:
        assert list(cast(Any, figure.data[0]).y) == [3.0, 4.0]


@pytest.mark.public_api
@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
@pytest.mark.parametrize("phase", ["before_detach", "during_cleanup"])
def test_real_native_retirement_cannot_clear_a_new_publication_or_readmitted_plot(
    engine: Literal["plotly", "matplotlib"], phase: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # [test->req~ring5.plots.delete~1]
    entered, release = Event(), Event()
    with ring5.Session() as session:
        plot = _plot(session)
        prior = [session.render(plot, engine=engine)]
        token = plot.render_state.snapshot()
        original_dispose = PlotRenderBinding.dispose

        def retire(binding: PlotRenderBinding[Any]) -> None:
            if phase == "during_cleanup" and binding is token:
                entered.set()
                assert release.wait(5)
            original_dispose(binding)

        monkeypatch.setattr(PlotRenderBinding, "dispose", retire)
        manager = session.api.state_manager
        unrelated, axis = plt.subplots()
        axis.plot([0.0], [9.0])
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                if phase == "before_detach":
                    with manager.transaction():
                        manager.set_plots([])
                        fresh = pool.submit(session.render, plot, engine=engine).result(timeout=5)
                else:
                    pending = pool.submit(manager.set_plots, [])
                    try:
                        assert entered.wait(5)
                        assert plot.render_artifact.figure is None
                        manager.add_plot(plot)
                        fresh = session.render(plot, engine=engine)
                    finally:
                        release.set()
                    pending.result(timeout=5)
            assert plot.render_artifact.figure is fresh
            prepared = plot.render_artifact.preparation
            assert isinstance(prepared, PreparedFigure)
            assert prepared.trace_result is not None and prepared.spec is not None
            assert plot.render_artifact.cache_key is None
            assert manager.get_plots() == ([plot] if phase == "during_cleanup" else [])
            assert plt.figure(unrelated.number) is unrelated
            if engine == "matplotlib":
                _assert_borrowed_content(cast(MplFigure, prior[0]))
                _assert_borrowed_content(cast(MplFigure, fresh))
            else:
                assert list(cast(Any, prior[0]).data[0].y) == [3.0, 4.0]
                assert list(cast(Any, fresh).data[0].y) == [3.0, 4.0]
        finally:
            release.set()
            plt.close(unrelated)
