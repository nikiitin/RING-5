"""Fixtures for E2E test suites.

Provides:
- ``live_server_url``: Starts a Streamlit server on an ephemeral port.
- ``shared_page``: Class-scoped browser page (state accumulates).
- Tier fixtures: ``tier0_app`` → ``tier4_app`` for progressive state setup.
- ``e2e_csv_path``: Path to the E2E fixture CSV.

Usage::

    @pytest.mark.requires_browser
    class TestDataManagers:
        def test_outlier_remover(self, tier1_page, live_server_url):
            dm = DataManagersPage(tier1_page)
            ...
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any, cast

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, expect

# Page objects — reuse from visual tests
from tests.visual.pages.base_page import BasePage
from tests.visual.pages.data_managers_page import DataManagersPage
from tests.visual.pages.data_source_page import DataSourcePage
from tests.visual.pages.manage_plots_page import ManagePlotsPage

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_ROOT_DIR: Path = Path(__file__).parents[2]
_APP_PY: Path = _ROOT_DIR / "app.py"
_PYTHON: str = str(_ROOT_DIR / "python_venv" / "bin" / "python")
_FIXTURES_DIR: Path = Path(__file__).parent / "fixtures"
_ARTIFACTS_DIR: Path = Path(__file__).parent / "artifacts"
_E2E_CSV: Path = _FIXTURES_DIR / "sample_data.csv"

# Timeouts
LOAD_TIMEOUT: int = 30_000
CHART_TIMEOUT: int = 30_000
E2E_TIMEOUT: int = 60_000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
def live_server_url(_streamlit_port: int) -> Generator[str]:
    """Start a Streamlit server and yield its base URL."""
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
    """Override default browser context: 1280x720, en-US, dark mode."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "locale": "en-US",
        "color_scheme": "dark",
    }


@pytest.fixture(scope="session")
def browser_type_launch_args(
    browser_type_launch_args: dict[str, object],
) -> dict[str, object]:
    """Honour ``HEADED=1`` and ``SLOW_MO`` env vars."""
    headed = os.environ.get("HEADED", "").lower() in ("1", "true", "yes")
    try:
        slow_mo = int(os.environ.get("SLOW_MO", "0"))
    except ValueError:
        slow_mo = 0

    args: dict[str, object] = {**browser_type_launch_args}
    if headed:
        args["headless"] = False
    if slow_mo > 0:
        args["slow_mo"] = slow_mo
    return args


@pytest.fixture(scope="class")
def shared_page(
    browser: Browser,
    browser_context_args: dict[str, object],
) -> Generator[Page]:
    """Class-scoped page — one browser tab shared across all tests in a class."""
    context = browser.new_context(**cast(Any, browser_context_args))
    page = context.new_page()
    yield page
    context.close()


# ---------------------------------------------------------------------------
# Failure artifact capture
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _capture_failure_artifacts(request: pytest.FixtureRequest) -> Generator[None]:
    """Auto-capture screenshot on test failure."""
    tracing = os.environ.get("TRACING", "").lower() in ("1", "true", "yes")

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
    """Store test result on node for ``_capture_failure_artifacts``."""
    import pluggy

    outcome: pluggy.Result = yield  # type: ignore[assignment]
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


# ---------------------------------------------------------------------------
# Fixture path
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def e2e_csv_path() -> Path:
    """Path to the E2E fixture CSV (18 rows, 8 columns)."""
    assert _E2E_CSV.exists(), f"Fixture CSV not found: {_E2E_CSV}"
    return _E2E_CSV


# ---------------------------------------------------------------------------
# Tier fixtures — progressive state setup
# ---------------------------------------------------------------------------


@pytest.fixture(scope="class")
def tier0_page(
    shared_page: Page,
    live_server_url: str,
) -> Page:
    """Tier 0: Fresh app, navigated to home page.

    State: No data loaded, default page visible.
    """
    bp = BasePage(shared_page)
    bp.goto_and_wait(live_server_url)
    bp.assert_page_loaded()
    return shared_page


@pytest.fixture(scope="class")
def tier1_page(
    tier0_page: Page,
    e2e_csv_path: Path,
) -> Page:
    """Tier 1: App with CSV data loaded.

    State: 18-row DataFrame loaded via CSV upload mode.
    Columns: benchmark_name, config_description, seed, system.cpu.ipc,
             system.cpu.numCycles, simTicks, system.cpu.dcache.overall_miss_rate,
             system.cpu.committedInsts
    """
    ds = DataSourcePage(tier0_page)
    ds.navigate()
    ds.upload_csv(e2e_csv_path)
    ds.wait_for_streamlit()

    # Verify data loaded by navigating to Data Managers
    dm = DataManagersPage(tier0_page)
    dm.navigate()
    dm.assert_has_data()

    return tier0_page


@pytest.fixture(scope="class")
def tier2_page(
    tier1_page: Page,
) -> Page:
    """Tier 2: App with data loaded + one bar plot created.

    State: Tier 1 + bar plot "E2E Bar" with Sort pipeline finalized.
    """
    mp = ManagePlotsPage(tier1_page)
    mp.navigate()

    # Create bar plot
    mp.create_plot("E2E Bar", "bar")
    mp.assert_plot_pill_visible("E2E Bar")

    # Add Sort → Finalize
    mp.add_shaper("Sort")
    mp.finalize_pipeline()

    # Navigate away and back to trigger render fragment
    mp.navigate_to("Data Source")
    mp.navigate()

    # Configure axes
    expect(mp.viz_x_axis_selectbox).to_be_visible(timeout=E2E_TIMEOUT)
    mp.select_x_axis("benchmark_name")
    mp.select_y_axis("system.cpu.ipc")
    mp.refresh_plot()
    mp.assert_chart_visible(timeout=CHART_TIMEOUT)

    return tier1_page


@pytest.fixture(scope="class")
def tier3_page(
    tier2_page: Page,
) -> Page:
    """Tier 3: Tier 2 + shaper pipeline with column selector applied.

    State: Tier 2 + second plot "E2E Shaped" with Column Selector + Sort.
    """
    mp = ManagePlotsPage(tier2_page)
    mp.navigate()

    mp.create_plot("E2E Shaped", "bar")
    mp.assert_plot_pill_visible("E2E Shaped")

    # Add Column Selector → Sort → Finalize
    mp.add_shaper("Column Selector")
    mp.click_select_all_columns()
    mp.add_shaper("Sort")
    mp.finalize_pipeline()

    # Navigate away and back
    mp.navigate_to("Data Source")
    mp.navigate()

    expect(mp.viz_x_axis_selectbox).to_be_visible(timeout=E2E_TIMEOUT)

    return tier2_page
