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
# Chart render (Plotly iframe JS resize / Matplotlib st.pyplot) competes with 2
# other workers' browsers under -n 3, so a render can occasionally exceed 30s;
# 60s gives headroom while staying well under the per-test timeout.
CHART_TIMEOUT: int = 60_000
E2E_TIMEOUT: int = 60_000
# Raster downloads (png/svg/pdf) render the figure eagerly via Kaleido
# (fig.to_image()) BEFORE st.download_button, so the button is absent until the
# export finishes. Under -n 3 that Kaleido/Chromium export starves on CPU and
# can take well over E2E_TIMEOUT (90s proved insufficient). 120s headroom; run
# the e2e gate with --timeout=180 so a slow export isn't killed mid-flight.
EXPORT_TIMEOUT: int = 120_000


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


@pytest.fixture(scope="session", autouse=True)
def _isolated_data_dir(tmp_path_factory: pytest.TempPathFactory) -> Generator[None]:
    """Redirect the app data dir (pool / portfolios / configs) to an isolated,
    empty per-worker temp dir for the whole session.

    Keeps e2e runs off the user's cluttered ``.ring5`` pool (~150 CSVs that slow
    the Recent-mode render and caused ``-n 3`` timeouts) and gives each xdist
    worker its own clean, fast, race-free pool. ``RING5_DATA_DIR`` is set on
    ``os.environ`` before ``live_server_url`` starts, so the Streamlit server
    subprocess inherits it; the test process resets the path caches so its own
    pool staging targets the same temp dir.
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
    return _free_port()


@pytest.fixture(scope="session")
def live_server_url(_streamlit_port: int, _isolated_data_dir: None) -> Generator[str]:
    """Start a Streamlit server and yield its base URL.

    Depends on ``_isolated_data_dir`` so ``RING5_DATA_DIR`` is exported before the
    server subprocess (which inherits ``os.environ``) starts.
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
# State isolation — clean slate per test class
# ---------------------------------------------------------------------------


@pytest.fixture(scope="class", autouse=True)
def _reset_app_state(shared_page: Page, live_server_url: str) -> Generator[None]:
    """Reset the app to a clean slate at the start of each test class.

    ``ApplicationAPI`` is a process-wide ``@st.cache_resource`` singleton whose
    ``PlotRepository`` stores plots in plain instance attributes (not
    ``st.session_state``), so plots/data persist across browser sessions on the
    same server. This autouse class fixture clicks 'Reset All' before each
    class's tier/setup fixtures run, giving cross-class isolation under both
    ``-n 0`` and ``-n 3 --dist loadgroup`` (one xdist worker may run several
    groups against a single server). Autouse class fixtures instantiate before
    the explicitly-requested ``tier*_page`` fixtures, so the slate is clean
    before any data is loaded.
    """
    bp = BasePage(shared_page)
    bp.goto_and_wait(live_server_url)
    bp.reset_all()
    # Verify the reset actually cleared plots. A flaky/no-op reset would let
    # plots accumulate across classes in the shared singleton — the cause of the
    # plot-pill "resolved to N elements" failures. Fail loudly here instead.
    mp = ManagePlotsPage(shared_page)
    mp.navigate()
    expect(mp.no_plots_warning).to_be_visible(timeout=LOAD_TIMEOUT)
    yield


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
    _reset_app_state: None,
) -> Page:
    """Tier 0: Fresh app, navigated to home page.

    Depends on ``_reset_app_state`` so the clean-slate reset is guaranteed to run
    BEFORE any tier setup (autouse ordering alone proved unreliable — tier0 was
    instantiated before the reset, so a prior class's plots were still present).

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
    mp.select_all_columns()
    mp.add_shaper("Sort")
    mp.finalize_pipeline()

    # Navigate away and back
    mp.navigate_to("Data Source")
    mp.navigate()

    expect(mp.viz_x_axis_selectbox).to_be_visible(timeout=E2E_TIMEOUT)

    return tier2_page
