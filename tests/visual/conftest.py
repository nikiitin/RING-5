"""Fixtures for Playwright visual tests.

Provides:
- ``live_server_url``: Starts a Streamlit server on an ephemeral port,
  waits for readiness, yields ``http://localhost:<port>``, tears down.
- ``screenshot_dir``: Per-test screenshot directory (gitignored).
- ``browser_context_args``: Default Chromium context overrides.
- ``headed``: Honour ``HEADED=1`` env var for debugging.

Usage::

    @pytest.mark.requires_browser
    def test_something(page: Page, live_server_url: str) -> None:
        page.goto(live_server_url)
        ...
"""

from __future__ import annotations

from dataclasses import dataclass
import os
import shutil
from collections.abc import Generator
from pathlib import Path
from typing import Any, cast

import pytest
from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

from tests.helpers.streamlit_server import artifact_stem, free_loopback_port, running_streamlit
from tests.visual.pages.base_page import BasePage

# Helpers

_ROOT_DIR: Path = Path(__file__).parents[2]
_APP_PY: Path = _ROOT_DIR / "app.py"
_SCREENSHOTS_DIR: Path = Path(__file__).parent / "screenshots"
_ARTIFACTS_DIR: Path = Path(__file__).parent / "artifacts"


@dataclass
class _SharedPageCapture:
    """Own the class page's trace chunk before function fixtures can run."""

    page: Page
    tracing: bool = False
    chunk_active: bool = False
    setup_failure_saved: bool = False


_SHARED_PAGE_CAPTURE = pytest.StashKey[_SharedPageCapture]()


def _shared_capture_for_node(node: pytest.Node) -> _SharedPageCapture | None:
    """Find only the shared-page fixture's explicit ancestor-owned capture."""
    for owner in reversed(node.listchain()):
        capture = owner.stash.get(_SHARED_PAGE_CAPTURE, None)
        if capture is not None:
            return capture
    return None


def _save_failure_screenshot(page: Page, nodeid: str) -> str:
    """Capture the existing page and return its artifact filename stem."""
    _ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    name = artifact_stem(nodeid, os.environ.get("PYTEST_XDIST_WORKER", "main"))
    if not page.is_closed():
        try:
            page.screenshot(
                path=str(_ARTIFACTS_DIR / f"{name}_failure.png"),
                full_page=True,
                timeout=10_000,
            )
        except PlaywrightTimeoutError:
            pass
    return name


# Session-scoped: server lifecycle


@pytest.fixture(scope="session", autouse=True)
def _isolated_data_dir(tmp_path_factory: pytest.TempPathFactory) -> Generator[None]:
    """Redirect the app data dir to an isolated, empty per-worker temp dir.

    Same rationale as the e2e suite: keeps browser tests off the user's
    cluttered ``.ring5`` pool (fast, race-free) by exporting ``RING5_DATA_DIR``
    before the Streamlit server subprocess starts.
    """
    from src.core.services.data_services.csv_pool_service import CsvPoolService
    from src.core.services.data_services.path_service import PathService

    worker = os.environ.get("PYTEST_XDIST_WORKER", "main")
    data_dir = tmp_path_factory.getbasetemp() / f"ring5_data_{worker}"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["RING5_DATA_DIR"] = str(data_dir)
    PathService.reset_caches()
    CsvPoolService._pool_dir = None
    yield
    os.environ.pop("RING5_DATA_DIR", None)
    PathService.reset_caches()
    CsvPoolService._pool_dir = None


@pytest.fixture(scope="session")
def _streamlit_port() -> int:
    """Choose a free port once per session."""
    return free_loopback_port()


@pytest.fixture(scope="session")
def live_server_url(
    _streamlit_port: int,
    _isolated_data_dir: None,
) -> Generator[str]:
    """Start a Streamlit server and yield its base URL.

    The server is started as a subprocess with ``--server.headless true``
    and killed after the entire test session completes.
    """
    with running_streamlit(_APP_PY, port=_streamlit_port) as url:
        yield url


# Browser / page configuration


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict[str, object]) -> dict[str, object]:
    """Override default browser context args.

    - Viewport: 1280×720 (consistent screenshots)
    - Locale: en-US (deterministic date/number formatting)
    - Color scheme: dark (matches RING-5 theme)
    """
    args: dict[str, object] = {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "locale": "en-US",
        "color_scheme": "dark",
    }
    return args


@pytest.fixture(scope="class")
def shared_page(
    browser: Browser,
    browser_context_args: dict[str, object],
    request: pytest.FixtureRequest,
) -> Generator[Page]:
    """Class-scoped page — one browser tab shared across all tests in a class.

    This avoids recreating a browser context and navigating for every test
    in an ordered visual suite.
    """
    # Use cast to satisfy Pyright regarding BrowserContext options
    context = browser.new_context(**cast(Any, browser_context_args))
    page = context.new_page()
    capture = _SharedPageCapture(page)
    request.node.stash[_SHARED_PAGE_CAPTURE] = capture
    try:
        if os.environ.get("TRACING", "").lower() in ("1", "true", "yes"):
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            capture.tracing = True
            capture.chunk_active = True
        yield page
    finally:
        try:
            if capture.tracing:
                context.tracing.stop()
        finally:
            del request.node.stash[_SHARED_PAGE_CAPTURE]
            context.close()


@pytest.fixture(scope="class", autouse=True)
def _reset_app_state(shared_page: Page, live_server_url: str) -> Generator[None]:
    """Reset the app to a clean slate at the start of each test class.

    Tests in a class deliberately reuse one browser context. Reset that
    session before the class setup runs so each class starts independently.
    """
    bp = BasePage(shared_page)
    bp.goto_and_wait(live_server_url)
    bp.reset_all()
    yield


@pytest.fixture()
def screenshot_dir(request: pytest.FixtureRequest) -> Path:
    """Return a per-test screenshot directory, cleaned before use.

    Screenshots land in ``tests/visual/screenshots/<worker-and-test-identity>/``.
    """
    test_name = artifact_stem(request.node.nodeid, os.environ.get("PYTEST_XDIST_WORKER", "main"))
    path = _SCREENSHOTS_DIR / test_name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture(scope="class")
def shared_screenshot_dir(request: pytest.FixtureRequest) -> Path:
    """Return a per-class screenshot directory, cleaned once per class.

    Screenshots land in ``tests/visual/screenshots/<worker-and-class-identity>/``.
    Used by ordered test classes that share a ``shared_page``.
    """
    class_name = artifact_stem(request.node.nodeid, os.environ.get("PYTEST_XDIST_WORKER", "main"))
    path = _SCREENSHOTS_DIR / class_name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture(autouse=True)
def _capture_failure_artifacts(
    request: pytest.FixtureRequest,
) -> Generator[None]:
    """Auto-capture screenshot + trace on test failure.

    Automatically detects whether the test uses `shared_page` (class-scoped)
    or `page` (function-scoped) and captures failure artifacts from whichever
    is active.  This avoids creating an extra browser context when the test
    only uses `shared_page`.
    """
    tracing = os.environ.get("TRACING", "").lower() in ("1", "true", "yes")

    # Resolve the active page without creating an unused fixture
    if "shared_page" in request.fixturenames:
        active_page: Page = request.getfixturevalue("shared_page")
    elif "page" in request.fixturenames:
        active_page = request.getfixturevalue("page")
    else:
        yield
        return

    context: BrowserContext = active_page.context
    shared_capture = _shared_capture_for_node(request.node)

    if tracing:
        if shared_capture is not None:
            # Successful class setup no longer needs its initial diagnostic chunk.
            if shared_capture.chunk_active:
                context.tracing.stop_chunk()
            context.tracing.start_chunk()
            shared_capture.chunk_active = True
        else:
            context.tracing.start(screenshots=True, snapshots=True, sources=True)

    yield

    reports = [getattr(request.node, name, None) for name in ("rep_setup", "rep_call")]
    failed = any(report is not None and report.failed for report in reports)
    trace_path = None
    if failed:
        name = _save_failure_screenshot(active_page, request.node.nodeid)
        trace_path = _ARTIFACTS_DIR / f"{name}_trace.zip"
    if tracing:
        if shared_capture is not None:
            context.tracing.stop_chunk(path=trace_path)
            shared_capture.chunk_active = False
        else:
            context.tracing.stop(path=trace_path)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item) -> Generator[None]:
    """Store test result on the node for ``_capture_failure_artifacts``."""
    import pluggy

    outcome: pluggy.Result = yield  # type: ignore[assignment]
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)

    if rep.when == "setup" and rep.failed:
        # Class setup can fail before the function capture fixture is reached.
        capture = _shared_capture_for_node(item)
        if (
            capture is not None
            and "_capture_failure_artifacts" not in item.funcargs
            and not capture.setup_failure_saved
        ):
            name = _save_failure_screenshot(capture.page, item.nodeid)
            sections = "\n\n".join(f"{title}\n{text}" for title, text in rep.sections)
            (_ARTIFACTS_DIR / f"{name}_setup.txt").write_text(sections, encoding="utf-8")
            if capture.tracing and capture.chunk_active:
                capture.page.context.tracing.stop_chunk(path=_ARTIFACTS_DIR / f"{name}_trace.zip")
                capture.chunk_active = False
            # Later items repeat the cached class-setup error without new work.
            capture.setup_failure_saved = True


# Headed mode


@pytest.fixture(scope="session")
def browser_type_launch_args(
    browser_type_launch_args: dict[str, object],
) -> dict[str, object]:
    """Honour ``HEADED=1`` env var and optional ``SLOW_MO`` milliseconds."""
    headed = os.environ.get("HEADED", "").lower() in ("1", "true", "yes")
    slow_mo_str = os.environ.get("SLOW_MO", "0")
    try:
        slow_mo = int(slow_mo_str)
    except ValueError:
        slow_mo = 0

    args: dict[str, object] = {**browser_type_launch_args}
    if headed:
        args["headless"] = False
    if slow_mo > 0:
        args["slow_mo"] = slow_mo
    return args
