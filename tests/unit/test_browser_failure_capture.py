"""Failure artifacts retain the original page and one explicit trace owner."""

from pathlib import Path
from typing import Literal
from unittest.mock import MagicMock, call

import pytest
from playwright.sync_api import BrowserContext, Page, TimeoutError as PlaywrightTimeoutError

from tests.helpers.browser_capture import (
    _shared_capture_for_node,
    capture_failure_artifacts,
    save_setup_failure,
    shared_page_capture,
)
from tests.helpers.streamlit_server import artifact_stem


def _page_and_context() -> tuple[MagicMock, MagicMock]:
    """Provide one observable page/context pair without launching a browser."""
    page = MagicMock(spec=Page)
    context = MagicMock(spec=BrowserContext)
    page.context = context
    page.is_closed.return_value = False
    context.new_page.return_value = page
    return page, context


def _nodes() -> tuple[MagicMock, MagicMock]:
    """Use real pytest stashes across a class/item ancestry boundary."""
    owner = MagicMock(spec=pytest.Class)
    owner.stash = pytest.Stash()
    owner.listchain.return_value = [owner]
    item = MagicMock(spec=pytest.Item)
    item.stash = pytest.Stash()
    item.nodeid = "tests/example.py::TestFlow::test_first"
    item.listchain.return_value = [owner, item]
    item.funcargs = {}
    item.rep_setup = None
    item.rep_call = None
    return owner, item


def _request(item: MagicMock, page: MagicMock, *, shared: bool) -> MagicMock:
    """Expose only fixtures already requested by the browser case."""
    request = MagicMock(spec=pytest.FixtureRequest)
    request.node = item
    request.fixturenames = ["shared_page", "page"] if shared else ["page"]
    request.getfixturevalue.return_value = page
    return request


def _failure(
    item: MagicMock, when: Literal["setup", "call", "teardown"] = "setup"
) -> pytest.TestReport:
    """Preserve real pytest failure text and captured report sections."""
    return pytest.TestReport(
        nodeid=item.nodeid,
        location=("tests/example.py", 1, "TestFlow.test_first"),
        keywords={},
        outcome="failed",
        longrepr="original failure",
        when=when,
        sections=[("Captured stderr setup", "original stderr")],
    )


def test_class_setup_failure_is_retained_once_before_function_capture(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Cached setup errors never overwrite the original failed page/trace."""
    monkeypatch.setenv("TRACING", "1")
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw1")
    page, context = _page_and_context()
    owner, item = _nodes()
    name = artifact_stem(item.nodeid, "gw1")
    with shared_page_capture(context, owner) as active:
        assert active is page
        save_setup_failure(item, _failure(item), tmp_path)
        item.nodeid = "tests/example.py::TestFlow::test_cached"
        save_setup_failure(item, _failure(item), tmp_path)
        capture = _shared_capture_for_node(item)
        assert capture is not None and capture.setup_failure_saved
        assert not capture.chunk_active
    context.new_page.assert_called_once_with()
    context.tracing.start.assert_called_once_with(screenshots=True, snapshots=True, sources=True)
    context.tracing.start_chunk.assert_not_called()
    context.tracing.stop_chunk.assert_called_once_with(path=tmp_path / f"{name}_trace.zip")
    context.tracing.stop.assert_called_once_with()
    context.close.assert_called_once_with()
    page.screenshot.assert_called_once_with(
        path=str(tmp_path / f"{name}_failure.png"),
        full_page=True,
        timeout=10_000,
    )
    assert (tmp_path / f"{name}_setup.txt").read_text() == (
        "original failure\n\nCaptured stderr setup\noriginal stderr"
    )
    assert len(list(tmp_path.glob("*_setup.txt"))) == 1
    assert _shared_capture_for_node(item) is None


def test_shared_test_chunks_handoff_without_restarting_the_class_trace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A successful setup chunk gives way to one chunk per function."""
    monkeypatch.setenv("TRACING", "true")
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "main")
    page, context = _page_and_context()
    owner, item = _nodes()
    request = _request(item, page, shared=True)
    name = artifact_stem(item.nodeid)
    with shared_page_capture(context, owner):
        with capture_failure_artifacts(request, tmp_path):
            item.rep_call = _failure(item, "call")
        item.rep_call = None
        with capture_failure_artifacts(request, tmp_path):
            pass
    context.tracing.start.assert_called_once_with(screenshots=True, snapshots=True, sources=True)
    assert context.tracing.start_chunk.call_count == 2
    assert context.tracing.stop_chunk.call_args_list == [
        call(path=None),
        call(path=tmp_path / f"{name}_trace.zip"),
        call(path=None),
    ]
    context.tracing.stop.assert_called_once_with()
    assert request.getfixturevalue.call_args_list == [call("shared_page"), call("shared_page")]
    context.new_page.assert_called_once_with()
    page.screenshot.assert_called_once()


@pytest.mark.parametrize("when", ["setup", "call"])
def test_function_page_failure_owns_its_trace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    when: Literal["setup", "call"],
) -> None:
    """Function pages retain setup/call failures without another context."""
    monkeypatch.setenv("TRACING", "yes")
    page, context = _page_and_context()
    _, item = _nodes()
    request = _request(item, page, shared=False)
    with capture_failure_artifacts(request, tmp_path):
        setattr(item, f"rep_{when}", _failure(item, when))
    request.getfixturevalue.assert_called_once_with("page")
    context.new_page.assert_not_called()
    context.tracing.start.assert_called_once_with(screenshots=True, snapshots=True, sources=True)
    assert context.tracing.stop.call_count == 1
    assert context.tracing.stop.call_args.kwargs["path"].suffix == ".zip"
    context.tracing.start_chunk.assert_not_called()
    context.tracing.stop_chunk.assert_not_called()
    context.close.assert_not_called()
    page.screenshot.assert_called_once()


def test_tracing_disabled_still_retains_setup_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Screenshots and error text do not depend on enabling tracing."""
    monkeypatch.delenv("TRACING", raising=False)
    page, context = _page_and_context()
    owner, item = _nodes()
    with shared_page_capture(context, owner):
        save_setup_failure(item, _failure(item), tmp_path)
    page.screenshot.assert_called_once()
    assert len(list(tmp_path.glob("*_setup.txt"))) == 1
    assert context.tracing.mock_calls == []
    context.close.assert_called_once_with()


def test_function_owner_prevents_duplicate_setup_hook_capture(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A started function fixture keeps ownership of its setup failure."""
    monkeypatch.setenv("TRACING", "1")
    page, context = _page_and_context()
    owner, item = _nodes()
    request = _request(item, page, shared=True)
    with shared_page_capture(context, owner):
        with capture_failure_artifacts(request, tmp_path):
            item.funcargs["_capture_failure_artifacts"] = None
            item.rep_setup = _failure(item)
            save_setup_failure(item, item.rep_setup, tmp_path)
            page.screenshot.assert_not_called()
        page.screenshot.assert_called_once()
    assert not list(tmp_path.glob("*_setup.txt"))
    assert context.tracing.stop_chunk.call_count == 2


@pytest.mark.parametrize("error", [PlaywrightTimeoutError("deadline"), RuntimeError("screenshot")])
def test_screenshot_error_releases_chunk_and_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    error: Exception,
) -> None:
    """Only screenshot timeouts are suppressed; trace cleanup always runs."""
    monkeypatch.setenv("TRACING", "1")
    page, context = _page_and_context()
    page.screenshot.side_effect = error
    owner, item = _nodes()
    request = _request(item, page, shared=True)

    def fail() -> None:
        """Close the capture after an existing failed call report."""
        with shared_page_capture(context, owner):
            with capture_failure_artifacts(request, tmp_path):
                item.rep_call = _failure(item, "call")

    if isinstance(error, PlaywrightTimeoutError):
        fail()
    else:
        with pytest.raises(RuntimeError, match="screenshot"):
            fail()
    assert context.tracing.stop_chunk.call_count == 2
    context.tracing.stop.assert_called_once_with()
    context.close.assert_called_once_with()
    assert _shared_capture_for_node(item) is None


@pytest.mark.parametrize("stage", ["new_page", "start", "stop"])
def test_class_context_closes_when_trace_lifecycle_raises(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    """Page/trace errors cannot leave the context or capture stash alive."""
    monkeypatch.setenv("TRACING", "1")
    _, context = _page_and_context()
    owner, item = _nodes()
    target = context.new_page if stage == "new_page" else getattr(context.tracing, stage)
    target.side_effect = RuntimeError(stage)
    with pytest.raises(RuntimeError, match=stage):
        with shared_page_capture(context, owner):
            pass
    context.close.assert_called_once_with()
    assert _shared_capture_for_node(item) is None


def test_capture_without_a_page_does_not_create_fixtures(tmp_path: Path) -> None:
    """Non-browser cases request no browser resources or artifacts."""
    request = MagicMock(spec=pytest.FixtureRequest)
    request.fixturenames = []
    with capture_failure_artifacts(request, tmp_path):
        pass
    request.getfixturevalue.assert_not_called()
    assert not list(tmp_path.iterdir())
