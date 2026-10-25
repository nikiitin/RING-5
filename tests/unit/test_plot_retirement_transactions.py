"""Plot retirement publishes atomically and runs foreign cleanup outside locks."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from dataclasses import dataclass, field
from functools import partial
from threading import Event
from typing import Any

import pandas as pd
import pytest

from src.core.common.plot_render_state import PlotRenderState
from src.core.models.data_models import PipelineStep
from src.core.models.portfolio_models import PortfolioData
from src.core.models.plot_protocol import PlotProtocol
from src.core.state.repository_state_manager import RepositoryStateManager


@dataclass
class _Plot:
    plot_id: int = 0
    name: str = "Measured"
    plot_type: str = "test"
    config: dict[str, Any] = field(default_factory=dict)
    pipeline: list[PipelineStep] = field(default_factory=list)
    pipeline_counter: int = 0
    source_data: pd.DataFrame | None = None
    processed_data: pd.DataFrame | None = None
    render_state: PlotRenderState[str] = field(default_factory=PlotRenderState)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name}

    def invalidate_figure(self) -> None:
        raise AssertionError("Repository publication must not call a foreign lifecycle method.")

    def replace_processed_data(self, data: pd.DataFrame | None) -> None:
        self.processed_data = data


def _portfolio() -> PortfolioData:
    return {"parser_strategy": "simple", "simulator": "gem5", "plots": []}


@pytest.mark.parametrize("operation", ["replace", "clear_data", "clear_all", "restore"])
@pytest.mark.parametrize("nested", [False, True])
def test_retirement_callbacks_can_wait_for_foreign_source_and_slot_publication(
    operation: str, nested: bool
) -> None:
    # [test->req~ring5.plots.delete~1]
    state, plot = RepositoryStateManager(), _Plot()
    observed: list[int] = []
    with ThreadPoolExecutor(max_workers=1) as pool:

        def cleanup() -> None:
            observed.append(len(state.get_plots()))

            def foreign() -> None:
                assert plot.render_state.snapshot() is None
                state.set_data(pd.DataFrame({"value": [9.0]}))

            pool.submit(foreign).result(timeout=2)

        plot.render_state.publish("measured", cleanup)
        state.add_plot(plot)
        with state.transaction() if nested else nullcontext():
            with state.transaction() if nested else nullcontext():
                if operation == "replace":
                    state.set_plots([])
                elif operation == "restore":
                    if nested:
                        with pytest.raises(ValueError, match="outside a surrounding"):
                            state.restore_session(_portfolio())
                        state.set_plots([])
                    else:
                        state.restore_session(_portfolio())
                else:
                    getattr(state, operation)()
            if nested:
                assert observed == []
        assert observed == [0]
        data = state.get_data()
        assert data is not None and data["value"].tolist() == [9.0]


def test_nested_remove_and_readmit_preserves_the_same_live_binding() -> None:
    state, plot = RepositoryStateManager(), _Plot()
    retired: list[str] = []
    plot.render_state.publish("measured", lambda: retired.append("old"))
    captured = plot.render_state.snapshot()
    state.add_plot(plot)
    with state.transaction():
        state.set_plots([])
        with state.transaction():
            state.add_plot(plot)
        assert plot.render_state.snapshot() is captured
    assert plot.render_state.snapshot() is captured
    assert retired == []
    state.set_plots([])
    assert plot.render_state.snapshot() is None
    assert retired == ["old"]


def test_new_publication_after_removal_is_not_claimed_by_a_stale_retirement() -> None:
    state, plot = RepositoryStateManager(), _Plot()
    retired: list[str] = []
    plot.render_state.publish("old", lambda: retired.append("old"))
    state.add_plot(plot)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with state.transaction():
            state.set_plots([])

            def publish() -> None:
                previous = plot.render_state.publish("new", lambda: retired.append("new"))
                assert previous is not None
                previous.dispose()

            pool.submit(publish).result(timeout=2)
    current = plot.render_state.snapshot()
    assert current is not None and current.payload == "new"
    assert retired == ["old"]


def test_readmission_and_new_publication_while_old_cleanup_waits_keep_the_new_binding() -> None:
    state, plot = RepositoryStateManager(), _Plot()
    entered, release = Event(), Event()
    retired: list[str] = []

    def cleanup() -> None:
        entered.set()
        assert release.wait(5)
        retired.append("old")

    plot.render_state.publish("old", cleanup)
    state.add_plot(plot)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(state.set_plots, [])
        try:
            assert entered.wait(5)
            assert plot.render_state.snapshot() is None
            state.add_plot(plot)
            plot.render_state.publish("new", lambda: retired.append("new"))
        finally:
            release.set()
        pending.result(timeout=5)
    assert state.get_plots() == [plot]
    current = plot.render_state.snapshot()
    assert current is not None and current.payload == "new"
    assert retired == ["old"]


def test_failed_cleanup_still_attempts_every_binding_after_committed_publication() -> None:
    state = RepositoryStateManager()
    first, second = _Plot(), _Plot(1)
    retired: list[str] = []

    def failure() -> None:
        assert state.get_plots() == []
        retired.append("first")
        raise RuntimeError("cleanup failed")

    first.render_state.publish("first", failure)
    second.render_state.publish("second", lambda: retired.append("second"))
    state.set_plots([first, second])
    version = state._workspace_version
    with pytest.raises(RuntimeError, match="cleanup failed"):
        state.set_plots([])
    assert retired == ["first", "second"]
    assert state.get_plots() == []
    assert state._workspace_version == version + 1
    assert first.render_state.snapshot() is second.render_state.snapshot() is None


def test_exception_in_outer_transaction_does_not_defer_cleanup_under_its_lock() -> None:
    state, plot = RepositoryStateManager(), _Plot()
    retired: list[str] = []
    plot.render_state.publish("old", lambda: retired.append("old"))
    state.add_plot(plot)
    with pytest.raises(ValueError, match="application failure"):
        with state.transaction():
            state.set_plots([])
            raise ValueError("application failure")
    assert state.get_plots() == []
    assert retired == ["old"]


def test_rejected_candidate_cleanup_uses_its_admitted_token_and_keeps_new_publication() -> None:
    first, second = _Plot(), _Plot(1)
    admitted, release = Event(), Event()
    retired: list[str] = []
    first.render_state.publish("candidate", lambda: retired.append("candidate"))

    def deserialize(payload: dict[str, Any]) -> _Plot:
        if payload["name"] == "first":
            return first
        admitted.set()
        assert release.wait(5)
        return second

    state = RepositoryStateManager(plot_deserializer=deserialize)
    with ThreadPoolExecutor(max_workers=1) as pool:
        payload: PortfolioData = {**_portfolio(), "plots": [{"name": "first"}, {"name": "second"}]}
        pending = pool.submit(state.restore_session, payload)
        try:
            assert admitted.wait(5)
            previous = first.render_state.publish("independent", lambda: retired.append("new"))
            assert previous is not None
            previous.dispose()
            state.set_config({"newer": True})
        finally:
            release.set()
        with pytest.raises(ValueError, match="Workspace changed"):
            pending.result(timeout=5)
    current = first.render_state.snapshot()
    assert current is not None and current.payload == "independent"
    assert retired == ["candidate"]
    assert state.get_config() == {"newer": True}


def test_rejected_candidate_cleanup_can_publish_from_another_thread() -> None:
    plot = _Plot()
    with ThreadPoolExecutor(max_workers=1) as cleanup_pool:

        def cleanup() -> None:
            cleanup_pool.submit(state.set_data, pd.DataFrame({"x": [7.0]})).result(timeout=2)

        plot.render_state.publish("candidate", cleanup)

        def deserialize(_payload: dict[str, Any]) -> _Plot:
            state.set_config({"concurrent": True})
            return plot

        state = RepositoryStateManager(plot_deserializer=deserialize)
        with pytest.raises(ValueError, match="Workspace changed"):
            state.restore_session({**_portfolio(), "plots": [{"name": "first"}]})
    assert plot.render_state.snapshot() is None
    data = state.get_data()
    assert data is not None and data["x"].tolist() == [7.0]


def test_exact_binding_cleanup_is_once_and_can_reenter_its_plot_slot() -> None:
    state: PlotRenderState[str] = PlotRenderState()
    retired: list[str] = []

    def cleanup() -> None:
        state.publish("next", lambda: retired.append("next"))
        retired.append("old")

    state.publish("old", cleanup)
    binding = state.detach(state.snapshot())
    assert binding is not None
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: binding.dispose(), range(2)))
    assert retired == ["old"]
    current = state.snapshot()
    assert current is not None and current.payload == "next"


@pytest.mark.parametrize("body_fails", [False, True])
@pytest.mark.parametrize("cleanup_failures", [1, 2])
def test_cleanup_failures_preserve_exact_body_and_prior_cleanup_exceptions(
    body_fails: bool, cleanup_failures: int
) -> None:
    state = RepositoryStateManager()
    plots: list[PlotProtocol] = [_Plot(index) for index in range(3)]
    body_error = ValueError("original body failure")
    failures = [RuntimeError(f"cleanup-{index}") for index in range(cleanup_failures)]
    attempted: list[int] = []
    with ThreadPoolExecutor(max_workers=1) as pool:

        def cleanup(index: int) -> None:
            pool.submit(state.set_config, {"cleanup": index}).result(timeout=2)
            attempted.append(index)
            if index < cleanup_failures:
                raise failures[index]

        for index, plot in enumerate(plots):
            plot.render_state.publish(str(index), partial(cleanup, index))
        state.set_plots(plots)
        version = state._workspace_version
        with pytest.raises(RuntimeError) as caught:
            with state.transaction():
                with state.transaction():
                    state.set_plots([])
                    if body_fails:
                        raise body_error
    chain: list[BaseException] = []
    error: BaseException | None = caught.value
    while error is not None:
        assert all(error is not prior for prior in chain), "Exception context contains a cycle."
        chain.append(error)
        error = error.__context__
    expected: list[BaseException] = [*reversed(failures)]
    if body_fails:
        expected.append(body_error)
    assert len(chain) == len(expected)
    assert all(actual is original for actual, original in zip(chain, expected, strict=True))
    assert attempted == [0, 1, 2]
    assert state.get_plots() == []
    assert state._workspace_version == version + 4
    assert all(plot.render_state.snapshot() is None for plot in plots)


@pytest.mark.parametrize("explicit_cause", [False, True])
def test_cleanup_contexts_and_explicit_causes_keep_their_exact_objects(
    explicit_cause: bool,
) -> None:
    state = RepositoryStateManager()
    plots: list[PlotProtocol] = [_Plot(index) for index in range(3)]
    body_error = ValueError("body failure")
    failures = [RuntimeError(f"cleanup-{index}") for index in range(2)]
    details = [KeyError(f"cleanup detail-{index}") for index in range(2)]
    causes = [OSError(f"explicit cause-{index}") for index in range(2)]
    attempted: list[int] = []
    with ThreadPoolExecutor(max_workers=1) as pool:

        def cleanup(index: int) -> None:
            pool.submit(state.set_config, {"cleanup": index}).result(timeout=2)
            attempted.append(index)
            if index < 2:
                try:
                    raise details[index]
                except KeyError:
                    if explicit_cause:
                        raise failures[index] from causes[index]
                    raise failures[index]

        for index, plot in enumerate(plots):
            plot.render_state.publish(str(index), partial(cleanup, index))
        state.set_plots(plots)
        version = state._workspace_version
        with pytest.raises(RuntimeError) as caught:
            with state.transaction():
                state.set_plots([])
                raise body_error
    expected = [failures[1], details[1], failures[0], details[0], body_error]
    error: BaseException | None = caught.value
    for original in expected:
        assert error is original
        error = error.__context__
    assert error is None
    for index, failure in enumerate(failures):
        assert failure.__cause__ is (causes[index] if explicit_cause else None)
        assert failure.__suppress_context__ is explicit_cause
    assert attempted == [0, 1, 2]
    assert state.get_plots() == []
    assert state._workspace_version == version + 4
    assert all(plot.render_state.snapshot() is None for plot in plots)
