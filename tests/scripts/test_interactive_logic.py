from unittest.mock import MagicMock

from src.plotting.base_plot import BasePlot


class MockPlot(BasePlot):
    def create_figure(self, data, config):
        return MagicMock()

    def get_legend_column(self, config):
        return None

    def process_data(self, data):
        return data

    def render_config_ui(self, parent):
        pass


def test_update_from_relayout_zoom():
    plot = MockPlot(1, "test", "bar")
    plot.config = {}

    # Simulate Zoom (x-axis)
    relayout_data = {"xaxis.range[0]": 10, "xaxis.range[1]": 20}

    changed = plot.update_from_relayout(relayout_data)
    assert changed is True
    assert plot.config["range_x"] == [10, 20]

    # Same value should return False
    changed = plot.update_from_relayout(relayout_data)
    assert changed is False


def test_update_from_relayout_legend_drag():
    plot = MockPlot(1, "test", "bar")
    plot.config = {}

    # Simulate Legend Drag
    relayout_data = {"legend.x": 0.5, "legend.y": 0.5}

    changed = plot.update_from_relayout(relayout_data)
    assert changed is True
    assert plot.config["legend_x"] == 0.5
    assert plot.config["legend_y"] == 0.5
    # Verify Forced Anchors (The fix for "Jumping")
    assert plot.config["legend_xanchor"] == "left"
    assert plot.config["legend_yanchor"] == "top"


def test_update_from_relayout_anchor_sync():
    plot = MockPlot(1, "test", "bar")
    plot.config = {"legend_xanchor": "auto"}

    # Simulate Anchor Change from Plotly
    relayout_data = {"legend.xanchor": "right", "legend.yanchor": "bottom"}

    changed = plot.update_from_relayout(relayout_data)
    assert changed is True
    assert plot.config["legend_xanchor"] == "right"
    assert plot.config["legend_yanchor"] == "bottom"


def test_update_from_relayout_autosize():
    plot = MockPlot(1, "test", "bar")
    plot.config = {"range_x": [0, 10]}

    # Reset Zoom (Autorange)
    relayout_data = {"xaxis.autorange": True}

    changed = plot.update_from_relayout(relayout_data)
    assert changed is True
    assert plot.config["range_x"] is None


if __name__ == "__main__":
    # verification script
    print("Running tests...")
    test_update_from_relayout_zoom()
    test_update_from_relayout_legend_drag()
    test_update_from_relayout_autosize()
    print("All tests passed!")
