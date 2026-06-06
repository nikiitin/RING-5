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

import os
import shutil
import signal
import socket
import subprocess
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any, cast

import pytest
from playwright.sync_api import Browser, BrowserContext, Page

from tests.visual.pages.base_page import BasePage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ROOT_DIR: Path = Path(__file__).parents[2]
_APP_PY: Path = _ROOT_DIR / "app.py"
_PYTHON: str = str(_ROOT_DIR / "python_venv" / "bin" / "python")
_SCREENSHOTS_DIR: Path = Path(__file__).parent / "screenshots"
_ARTIFACTS_DIR: Path = Path(__file__).parent / "artifacts"


def _free_port() -> int:
    """Return a free TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return int(s.getsockname()[1])


def _wait_for_server(port: int, *, timeout: float = 30.0) -> None:
    """Block until *http://localhost:<port>* responds or timeout expires."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("localhost", port), timeout=1.0):
                return
        except OSError:
            time.sleep(0.5)
    raise TimeoutError(f"Streamlit server did not start within {timeout}s on port {port}")


# ---------------------------------------------------------------------------
# Session-scoped: server lifecycle
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def _streamlit_port() -> int:
    """Choose a free port once per session."""
    return _free_port()


@pytest.fixture(scope="session")
def live_server_url(
    _streamlit_port: int,
) -> Generator[str]:
    """Start a Streamlit server and yield its base URL.

    The server is started as a subprocess with ``--server.headless true``
    and killed after the entire test session completes.
    """
    port = _streamlit_port
    cmd = [
        _PYTHON,
        "-m",
        "streamlit",
        "run",
        str(_APP_PY),
        "--server.port",
        str(port),
        "--server.headless",
        "true",
        "--server.fileWatcherType",
        "none",
        "--browser.gatherUsageStats",
        "false",
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=str(_ROOT_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        _wait_for_server(port)
        yield f"http://localhost:{port}"
    finally:
        # Graceful shutdown, then force if needed
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


# ---------------------------------------------------------------------------
# Browser / page configuration
# ---------------------------------------------------------------------------


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
) -> Generator[Page]:
    """Class-scoped page — one browser tab shared across all tests in a class.

    This avoids re-creating a browser context and re-navigating for every
    single test within a consolidated test class, yielding significant
    speedups for visual/E2E tests where setup dominates execution time.
    """
    # Use cast to satisfy Pyright regarding BrowserContext options
    context = browser.new_context(**cast(Any, browser_context_args))
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture(scope="class", autouse=True)
def _reset_app_state(shared_page: Page, live_server_url: str) -> Generator[None]:
    """Reset the app to a clean slate at the start of each test class.

    ``ApplicationAPI`` is a process-wide ``@st.cache_resource`` singleton whose
    ``PlotRepository`` stores plots in plain instance attributes (not
    ``st.session_state``), so plots/data persist across browser sessions on the
    same server. This autouse class fixture clicks 'Reset All' before each
    class's setup runs, giving cross-class isolation under both ``-n 0`` and
    ``-n 3 --dist loadgroup`` (one xdist worker may run several groups against a
    single server).
    """
    bp = BasePage(shared_page)
    bp.goto_and_wait(live_server_url)
    bp.reset_all()
    yield


@pytest.fixture()
def screenshot_dir(request: pytest.FixtureRequest) -> Path:
    """Return a per-test screenshot directory, cleaned before use.

    Screenshots land in ``tests/visual/screenshots/<test_name>/``.
    """
    test_name: str = request.node.name
    path = _SCREENSHOTS_DIR / test_name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture(scope="class")
def shared_screenshot_dir(request: pytest.FixtureRequest) -> Path:
    """Return a per-class screenshot directory, cleaned once per class.

    Screenshots land in ``tests/visual/screenshots/<ClassName>/``.
    Used by consolidated test classes that share a ``shared_page``.
    """
    class_name: str = request.node.name
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

    if tracing:
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

    yield

    # Post-test: capture artifacts on failure
    rep_call = getattr(request.node, "rep_call", None)
    if rep_call is not None and rep_call.failed:
        _ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        test_name = request.node.name
        active_page.screenshot(
            path=str(_ARTIFACTS_DIR / f"{test_name}_failure.png"),
            full_page=True,
        )
        if tracing:
            context.tracing.stop(path=str(_ARTIFACTS_DIR / f"{test_name}_trace.zip"))
    elif tracing:
        context.tracing.stop()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item) -> Generator[None]:
    """Store test result on the node for ``_capture_failure_artifacts``."""
    import pluggy

    outcome: pluggy.Result = yield  # type: ignore[assignment]
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


# ---------------------------------------------------------------------------
# Headed mode
# ---------------------------------------------------------------------------


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
