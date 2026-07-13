from typing import Any

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.web.pages.ui.plotting.base_plot import BasePlot


class MockPlot(BasePlot):
    def create_traces(self, data: Any, config: Any) -> TraceBuildResult:

        from src.core.models.visualization.trace_build_result import TraceBuildResult

        return TraceBuildResult(traces=[])

    def get_legend_column(self, config: Any) -> None:

        return None

    def process_data(self, data: Any) -> None:

        return data

    def render_config_ui(self, data: "Any", saved_config: "Any") -> "Any":  # type: ignore[override]
        pass


def test_update_from_relayout_zoom() -> None:
    plot = MockPlot(1, "test", "bar")
    plot.config = {}

    # Zoom simulation
    relayout_data = {"xaxis.range[0]": 10, "xaxis.range[1]": 20}

    changed = plot.update_from_relayout(relayout_data)
    assert changed is True
    assert plot.config["range_x"] == [10, 20]

    # Idempotency check
    changed = plot.update_from_relayout(relayout_data)
    assert changed is False


def test_update_from_relayout_legend_drag() -> None:
    plot = MockPlot(1, "test", "bar")
    plot.config = {}

    relayout_data = {"legend.x": 0.5, "legend.y": 0.5}

    changed = plot.update_from_relayout(relayout_data)
    assert changed is True
    assert plot.config["legend_x"] == 0.5
    assert plot.config["legend_y"] == 0.5
    assert plot.config["legend_xanchor"] == "left"
    assert plot.config["legend_yanchor"] == "top"


def test_update_from_relayout_anchor_sync() -> None:
    plot = MockPlot(1, "test", "bar")
    plot.config = {"legend_xanchor": "auto"}

    relayout_data = {"legend.xanchor": "right", "legend.yanchor": "bottom"}

    changed = plot.update_from_relayout(relayout_data)
    assert changed is True
    assert plot.config["legend_xanchor"] == "right"
    assert plot.config["legend_yanchor"] == "bottom"


def test_update_from_relayout_autosize() -> None:
    plot = MockPlot(1, "test", "bar")
    plot.config = {"range_x": [0, 10]}

    # Reset Zoom (Autorange)
    relayout_data = {"xaxis.autorange": True}

    changed = plot.update_from_relayout(relayout_data)
    assert changed is True
    assert plot.config["range_x"] is None
