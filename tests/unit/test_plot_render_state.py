"""Detached plot settings survive stale retirement and copy without lock-held hooks."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from typing import Any

from src.core.common.plot_render_state import PlotRenderState


def test_detach_retains_the_published_domain_payload_and_rejects_stale_tokens() -> None:
    state: PlotRenderState[dict[str, str]] = PlotRenderState({"title": "initial"})
    retired: list[str] = []
    state.publish(
        {"title": "rendered", "figure": "owned"},
        lambda: retired.append("old"),
        detached_payload={"title": "rendered"},
    )
    captured = state.snapshot()
    assert captured is not None
    assert state.detach(captured) is captured
    captured.dispose()
    assert state.snapshot() is None
    assert state.current_payload() == {"title": "rendered"}
    state.set_detached_payload({"title": "new edit"})
    assert state.detach(captured) is None
    assert state.detach(None) is None
    assert state.current_payload() == {"title": "new edit"}
    assert retired == ["old"]


def test_a_config_only_replacement_cannot_be_overwritten_by_an_older_native_retirement() -> None:
    state: PlotRenderState[str] = PlotRenderState("initial")
    state.publish("native", lambda: None, detached_payload="native config")
    captured = state.snapshot()
    assert state.set_detached_payload("new config") is captured
    assert state.detach(captured) is None
    assert state.current_payload() == "new config"


def test_detached_payload_copy_is_private_and_runs_arbitrary_copy_hooks_outside_slot_lock() -> None:
    class Payload:
        def __init__(self) -> None:
            self.values = [1]

        def __deepcopy__(self, memo: dict[int, Any]) -> "Payload":
            with ThreadPoolExecutor(max_workers=1) as executor:
                assert executor.submit(state.snapshot).result(timeout=2) is None
            result = Payload()
            result.values = list(self.values)
            return result

    payload = Payload()
    state: PlotRenderState[Payload] = PlotRenderState(payload)
    clone = deepcopy(state)
    copied = clone.current_payload()
    assert copied is not None and copied is not payload
    copied.values.append(2)
    assert payload.values == [1]
    assert state.current_payload() is payload
