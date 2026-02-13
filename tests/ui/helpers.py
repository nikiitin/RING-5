"""Shared helpers for AppTest-based e2e UI tests.

Provides utilities for booting the Streamlit app with pre-loaded data,
navigating between pages, and injecting plots into the application state.

Data Injection Pattern:
    AppTest.from_file("app.py") creates a fresh @st.cache_resource singleton.
    After the first .run(), the ApplicationAPI is accessible via
    at.session_state["api"]. Since RepositoryStateManager uses pure Python
    repositories (not st.session_state), mutations via
    api.state_manager.set_data(...) persist across subsequent .run() calls.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from streamlit.testing.v1 import AppTest

_APP_PATH: str = str(Path(__file__).parents[2] / "app.py")

# ---------------------------------------------------------------------------
# Rich e2e sample data
# ---------------------------------------------------------------------------


def make_e2e_sample_data() -> pd.DataFrame:
    """Create a rich DataFrame suitable for exercising all plot types and managers.

    Returns:
        DataFrame with 18 rows × 8 columns:
        - benchmark_name (3 benchmarks)
        - config_description (3 configs)
        - seed (2 seeds per benchmark/config)
        - system.cpu.ipc, system.cpu.numCycles, simTicks (numeric)
        - system.cpu.dcache.overall_miss_rate (float 0-1)
        - system.cpu.committedInsts (large int)
    """
    benchmarks: List[str] = ["mcf", "mcf", "omnetpp", "omnetpp", "xalancbmk", "xalancbmk"]
    configs: List[str] = ["baseline", "optimized", "baseline", "optimized", "baseline", "optimized"]
    seeds: List[int] = [0, 0, 0, 0, 0, 0]

    # Duplicate for second seed
    benchmarks = (
        benchmarks + benchmarks + ["mcf", "mcf", "omnetpp", "omnetpp", "xalancbmk", "xalancbmk"]
    )
    configs = (
        configs
        + configs
        + ["aggressive", "aggressive", "aggressive", "aggressive", "aggressive", "aggressive"]
    )
    seeds = seeds + [1, 1, 1, 1, 1, 1] + [0, 0, 0, 0, 0, 0]

    return pd.DataFrame(
        {
            "benchmark_name": benchmarks,
            "config_description": configs,
            "seed": seeds,
            "system.cpu.ipc": [
                2.10,
                2.35,
                1.45,
                1.62,
                1.78,
                1.98,
                2.12,
                2.33,
                1.47,
                1.60,
                1.80,
                1.96,
                2.50,
                2.50,
                1.70,
                1.70,
                2.05,
                2.05,
            ],
            "system.cpu.numCycles": [
                321000,
                289000,
                789000,
                712000,
                567000,
                510000,
                319000,
                291000,
                785000,
                715000,
                570000,
                508000,
                270000,
                270000,
                680000,
                680000,
                490000,
                490000,
            ],
            "simTicks": [
                3210000000,
                2890000000,
                7890000000,
                7120000000,
                5670000000,
                5100000000,
                3190000000,
                2910000000,
                7850000000,
                7150000000,
                5700000000,
                5080000000,
                2700000000,
                2700000000,
                6800000000,
                6800000000,
                4900000000,
                4900000000,
            ],
            "system.cpu.dcache.overall_miss_rate": [
                0.0234,
                0.0198,
                0.0312,
                0.0278,
                0.0189,
                0.0167,
                0.0240,
                0.0195,
                0.0318,
                0.0275,
                0.0192,
                0.0170,
                0.0180,
                0.0180,
                0.0250,
                0.0250,
                0.0155,
                0.0155,
            ],
            "system.cpu.committedInsts": [
                674100,
                679150,
                1144050,
                1153440,
                1009260,
                1009800,
                675200,
                678100,
                1145000,
                1152500,
                1010300,
                1008900,
                675000,
                675000,
                1156000,
                1156000,
                1005000,
                1005000,
            ],
        }
    )


# ---------------------------------------------------------------------------
# AppTest helpers
# ---------------------------------------------------------------------------


def create_app() -> AppTest:
    """Boot the AppTest from app.py and run the initial script.

    Returns:
        An AppTest instance that has completed its initial run.
    """
    at: AppTest = AppTest.from_file(_APP_PATH, default_timeout=10)
    at.run()
    return at


def create_app_with_data(df: Optional[pd.DataFrame] = None) -> AppTest:
    """Boot AppTest with pre-loaded data injected into the API state.

    Args:
        df: DataFrame to inject. Uses ``make_e2e_sample_data()`` if None.

    Returns:
        An AppTest instance with data loaded into ``api.state_manager``.
    """
    if df is None:
        df = make_e2e_sample_data()

    at: AppTest = create_app()
    api: Any = at.session_state["api"]
    api.state_manager.set_data(df)
    api.state_manager.set_processed_data(df.copy())
    return at


def navigate_to(at: AppTest, page_name: str) -> AppTest:
    """Navigate to a specific page via sidebar radio.

    Args:
        at: The AppTest instance.
        page_name: Exact page name from the sidebar radio options.

    Returns:
        The same AppTest instance after navigation and re-run.
    """
    at.sidebar.radio[0].set_value(page_name).run()
    return at


def get_api(at: AppTest) -> Any:
    """Retrieve the ApplicationAPI from AppTest session_state.

    Args:
        at: The AppTest instance (must have completed at least one .run()).

    Returns:
        The ApplicationAPI instance.
    """
    return at.session_state["api"]


def create_app_with_plots(
    df: Optional[pd.DataFrame] = None,
    plot_configs: Optional[List[Dict[str, Any]]] = None,
) -> AppTest:
    """Boot AppTest with data and pre-configured plots.

    Args:
        df: DataFrame to inject. Uses ``make_e2e_sample_data()`` if None.
        plot_configs: List of dicts with keys: name, plot_type, config.
            If None, creates a single bar plot.

    Returns:
        An AppTest instance with data and plots loaded.
    """
    # Import here to avoid circular imports at module level
    from src.web.pages.ui.plotting.plot_service import PlotService

    at: AppTest = create_app_with_data(df)
    api: Any = get_api(at)

    if plot_configs is None:
        plot_configs = [
            {
                "name": "E2E Test Plot",
                "plot_type": "bar",
                "config": {
                    "x": "benchmark_name",
                    "y": "system.cpu.ipc",
                    "title": "IPC by Benchmark",
                    "xlabel": "Benchmark",
                    "ylabel": "IPC",
                },
            }
        ]

    for pc in plot_configs:
        plot = PlotService.create_plot(pc["name"], pc["plot_type"], api.state_manager)
        if "config" in pc:
            plot.config = pc["config"]

    return at
