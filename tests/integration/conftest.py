"""Conftest for tests/integration/ — integration tests.

Provides fixtures that wrap the synthetic gem5 data with ready-to-use
ApplicationAPI and ParseService instances. Synthetic gem5 data fixtures
are registered via ``tests/helpers/gem5_fixtures.py`` in the root conftest.
"""

from pathlib import Path
from typing import Any, Dict

import pandas as pd
import pytest

from src.core.application_api import ApplicationAPI
from src.core.state.repository_state_manager import RepositoryStateManager
from src.web.figures.engine import FigureEngine
from src.web.pages.ui.plotting.plot_factory import PlotFactory
from src.web.pages.ui.plotting.styles.applicator import StyleApplicator

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def facade() -> ApplicationAPI:
    """Create a fresh ApplicationAPI instance for each test."""
    return ApplicationAPI()


@pytest.fixture
def integration_output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory for parse results."""
    out = tmp_path / "integration_output"
    out.mkdir()
    return out


@pytest.fixture
def state_manager() -> RepositoryStateManager:
    """Create a fresh RepositoryStateManager for each test."""
    sm = RepositoryStateManager()
    sm.clear_all()
    return sm


@pytest.fixture
def rich_sample_data() -> pd.DataFrame:
    """DataFrame with columns suitable for grouped_bar and multi-column plots.

    Includes: benchmark_name, config_description, system.cpu.ipc,
    system.cpu.numCycles, simTicks — enough for all plot types.
    """
    return pd.DataFrame(
        {
            "benchmark_name": [
                "mcf",
                "mcf",
                "mcf",
                "omnetpp",
                "omnetpp",
                "omnetpp",
                "xalancbmk",
                "xalancbmk",
                "xalancbmk",
            ],
            "config_description": [
                "baseline",
                "optimized",
                "aggressive",
                "baseline",
                "optimized",
                "aggressive",
                "baseline",
                "optimized",
                "aggressive",
            ],
            "system.cpu.ipc": [
                2.10,
                2.35,
                2.50,
                1.45,
                1.62,
                1.70,
                1.78,
                1.98,
                2.05,
            ],
            "system.cpu.numCycles": [
                321000,
                289000,
                270000,
                789000,
                712000,
                680000,
                567000,
                510000,
                490000,
            ],
            "simTicks": [
                3210000000,
                2890000000,
                2700000000,
                7890000000,
                7120000000,
                6800000000,
                5670000000,
                5100000000,
                4900000000,
            ],
        }
    )


@pytest.fixture
def loaded_facade(facade: ApplicationAPI, rich_sample_data: pd.DataFrame) -> ApplicationAPI:
    """ApplicationAPI with sample data pre-loaded into state."""
    facade.state_manager.set_data(rich_sample_data)
    facade.state_manager.set_processed_data(rich_sample_data.copy())
    return facade


@pytest.fixture
def bar_config() -> Dict[str, Any]:
    """Minimal config for a bar plot."""
    return {
        "x": "benchmark_name",
        "y": "system.cpu.ipc",
        "title": "IPC by Benchmark",
        "xlabel": "Benchmark",
        "ylabel": "IPC",
    }


@pytest.fixture
def grouped_bar_config() -> Dict[str, Any]:
    """Minimal config for a grouped bar plot."""
    return {
        "x": "benchmark_name",
        "y": "system.cpu.ipc",
        "group": "config_description",
        "title": "IPC by Benchmark and Config",
        "xlabel": "Benchmark",
        "ylabel": "IPC",
    }


@pytest.fixture
def line_config() -> Dict[str, Any]:
    """Minimal config for a line plot."""
    return {
        "x": "benchmark_name",
        "y": "system.cpu.ipc",
        "title": "IPC Trend",
        "xlabel": "Benchmark",
        "ylabel": "IPC",
    }


@pytest.fixture
def scatter_config() -> Dict[str, Any]:
    """Minimal config for a scatter plot."""
    return {
        "x": "system.cpu.numCycles",
        "y": "system.cpu.ipc",
        "title": "IPC vs Cycles",
        "xlabel": "Cycles",
        "ylabel": "IPC",
    }


@pytest.fixture
def figure_engine() -> FigureEngine:
    """FigureEngine pre-configured with all plot types registered.

    Each plot type gets its own BasePlot creator and StyleApplicator styler.
    """
    engine = FigureEngine()
    for plot_type in PlotFactory.get_available_plot_types():
        creator = PlotFactory.create_plot(plot_type, plot_id=0, name=f"test_{plot_type}")
        styler = StyleApplicator(plot_type)
        engine.register(plot_type, creator, styler=styler)
    return engine
