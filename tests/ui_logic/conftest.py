"""Conftest for tests/ui_logic/ -- UI logic tests with mocked Streamlit.

Provides shared fixtures for testing UI orchestration, adapters,
controllers, and page-level logic without a real Streamlit runtime.
"""

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Minimal PlotHandle stub (satisfies the PlotHandle protocol)
# ---------------------------------------------------------------------------
class StubPlotHandle:
    """Lightweight stub satisfying the PlotHandle protocol."""

    def __init__(
        self,
        plot_id: int = 1,
        name: str = "Test Plot",
        plot_type: str = "grouped_bar",
        config: Optional[Dict[str, Any]] = None,
        processed_data: Optional[pd.DataFrame] = None,
        pipeline: Optional[List[Dict[str, Any]]] = None,
        pipeline_counter: int = 0,
    ) -> None:
        self.plot_id = plot_id
        self.name = name
        self.plot_type = plot_type
        self.config: Dict[str, Any] = config or {}
        self.processed_data = processed_data
        self.pipeline: List[Dict[str, Any]] = pipeline or []
        self.pipeline_counter = pipeline_counter

    # ConfigRenderer stubs (needed for RenderablePlot)
    def render_config_ui(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        return config

    def render_advanced_options(self, config: Dict[str, Any], data: pd.DataFrame) -> Dict[str, Any]:
        return config

    def render_display_options(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return config

    def render_theme_options(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return config


@pytest.fixture
def stub_plot() -> StubPlotHandle:
    """A minimal PlotHandle stub with default values."""
    return StubPlotHandle()


@pytest.fixture
def stub_plot_with_data(sample_data: pd.DataFrame) -> StubPlotHandle:
    """A PlotHandle stub with processed_data attached."""
    return StubPlotHandle(processed_data=sample_data)


@pytest.fixture
def stub_plot_with_pipeline() -> StubPlotHandle:
    """A PlotHandle stub with a 2-step pipeline."""
    return StubPlotHandle(
        pipeline=[
            {"id": 1, "type": "columnSelector", "config": {"columns": ["a"]}},
            {"id": 2, "type": "normalize", "config": {"target": "b"}},
        ],
        pipeline_counter=2,
    )


@pytest.fixture
def mock_ui_state() -> MagicMock:
    """Mock UIStateManager."""
    state = MagicMock()
    state.get.return_value = None
    state.set.return_value = None
    return state


@pytest.fixture
def mock_lifecycle() -> MagicMock:
    """Mock PlotLifecycleService."""
    lifecycle = MagicMock()
    lifecycle.create_plot.return_value = StubPlotHandle(plot_id=99, name="New")
    lifecycle.duplicate_plot.return_value = StubPlotHandle(plot_id=100, name="Copy")
    lifecycle.change_plot_type.return_value = StubPlotHandle(plot_type="line")
    return lifecycle


@pytest.fixture
def mock_registry() -> MagicMock:
    """Mock PlotTypeRegistry."""
    registry = MagicMock()
    registry.get_available_types.return_value = [
        "bar",
        "grouped_bar",
        "stacked_bar",
        "grouped_stacked_bar",
        "line",
        "scatter",
        "histogram",
        "dual_axis",
    ]
    return registry


@pytest.fixture
def mock_chart_display() -> MagicMock:
    """Mock ChartDisplay."""
    return MagicMock()


@pytest.fixture
def mock_pipeline_executor(sample_data: pd.DataFrame) -> MagicMock:
    """Mock PipelineExecutor that returns sample_data."""
    executor = MagicMock()
    executor.apply_shapers.return_value = sample_data
    executor.configure_shaper.return_value = {"type": "columnSelector", "columns": ["a"]}
    return executor
