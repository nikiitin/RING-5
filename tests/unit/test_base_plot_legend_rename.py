from typing import Any

import pandas as pd
from ring5 import Session

import pytest

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.web.pages.ui.plotting.base_plot import BasePlot


class ConcretePlot(BasePlot):
    def render_config_ui(self, data: Any, saved_config: Any) -> dict:

        return {}

    def create_traces(self, data: Any, config: Any) -> TraceBuildResult:

        from src.core.models.visualization.trace_build_result import TraceBuildResult

        return TraceBuildResult(traces=[])


@pytest.fixture
def concrete_plot() -> ConcretePlot:
    return ConcretePlot(plot_id=1, name="Test Plot", plot_type="test")


def test_update_from_relayout_legend_title(concrete_plot: Any, plot_session: Session) -> None:
    """Test that legend title updates are processed."""

    # Initial State
    concrete_plot.config = {"legend_title": "Old Title"}
    concrete_plot.processed_data = pd.DataFrame({"x": [1], "y": [2]})
    plot_session.render(concrete_plot)

    # Simulate Relayout Event (Rename Legend)
    relayout_data = {"legend.title.text": "New Title"}

    changed = concrete_plot.update_from_relayout(relayout_data)

    # Assertions
    assert changed is True
    assert concrete_plot.config["legend_title"] == "New Title"
    assert concrete_plot.render_artifact.figure is None  # Cache invalidated


def test_update_from_relayout_mixed_events(concrete_plot: Any) -> None:
    """Test mixed events including drag and rename."""
    concrete_plot.config = {"legend_title": "Old", "legend_x": 0}

    # Drag AND Rename (unlikely in one event, but possible batching)
    relayout_data = {"legend.x": 0.5, "legend.title.text": "New"}

    changed = concrete_plot.update_from_relayout(relayout_data)

    assert changed is True
    assert concrete_plot.config["legend_x"] == 0.5
    assert concrete_plot.config["legend_title"] == "New"
