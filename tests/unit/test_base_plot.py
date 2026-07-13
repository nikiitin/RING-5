from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.plot_factory import PlotFactory
from tests.conftest import columns_side_effect


# Concrete implementation for testing abstract class
class ConcretePlot(BasePlot):
    def render_config_ui(self, data: Any, saved_config: Any) -> dict:

        return {}

    def create_traces(self, data: Any, config: Any) -> TraceBuildResult:

        from src.core.models.visualization.trace_build_result import TraceBuildResult

        return TraceBuildResult(traces=[])

    def get_legend_column(self, config: Any) -> str:

        return "col"


@pytest.fixture
def concrete_plot() -> ConcretePlot:
    return ConcretePlot(plot_id=1, name="Test Plot", plot_type="test")


@pytest.fixture
def mock_streamlit() -> Generator[None, None, None]:
    with (
        patch("src.web.pages.ui.plotting.plot_config_ui.st") as mock_st,
        patch("src.web.components.common.reorderable_list.st", mock_st),
        patch("src.web.components.plotting.settings.shapes_settings.st", mock_st),
    ):
        mock_st.session_state = {}

        mock_st.columns.side_effect = columns_side_effect

        # Mock numeric inputs to return int for comparisons
        mock_st.number_input.return_value = 0
        mock_st.slider.return_value = 0

        # Mock selectbox to return first option or specific logic
        def selectbox_side_effect(
            label: Any, options: Any, index: Any = 0, **kwargs: Any
        ) -> MagicMock:

            if isinstance(options, list) and len(options) > index:
                return options[index]
            return MagicMock()

        mock_st.selectbox.side_effect = selectbox_side_effect

        yield mock_st


def test_serialization(concrete_plot: Any) -> None:
    """Test to_dict and from_dict serialization."""
    concrete_plot.config = {"x": "col1"}
    concrete_plot.processed_data = pd.DataFrame({"col1": [1, 2, 3]})
    concrete_plot.pipeline = [{"type": "sort"}]

    data = concrete_plot.to_dict()

    assert data["id"] == 1
    assert data["name"] == "Test Plot"
    assert data["config"] == {"x": "col1"}
    assert "processed_data" in data

    # Restore through the factory while controlling the concrete plot type.
    with patch("src.web.pages.ui.plotting.plot_factory.PlotFactory.create_plot") as mock_factory:
        mock_factory.return_value = ConcretePlot(1, "Test Plot", "test")

        loaded_plot = PlotFactory.from_dict(data)

        assert loaded_plot.plot_id == 1
        assert loaded_plot.config == {"x": "col1"}
        assert len(loaded_plot.pipeline) == 1
        assert isinstance(loaded_plot.processed_data, pd.DataFrame)
        assert len(loaded_plot.processed_data) == 3


@patch("src.web.components.plotting.config.base_plot_config.st")
@patch("src.web.components.plotting.config.base_plot_config.PlotConfigComponents")
def test_render_common_config(mock_plc: Any, mock_st: Any, concrete_plot: Any) -> None:
    """Test common config component rendering."""
    from src.web.components.plotting.config.base_plot_config import render_common_config

    data = pd.DataFrame({"num": [1, 2], "cat": ["a", "b"]})
    saved_config: dict[str, Any] = {"x": "num", "title": "My Title"}

    # Mock widget returns
    col_ctx = MagicMock()
    col_ctx.__enter__ = MagicMock(return_value=col_ctx)
    col_ctx.__exit__ = MagicMock(return_value=False)
    mock_st.columns.return_value = [col_ctx, col_ctx]
    mock_st.selectbox.side_effect = ["num", "num"]

    mock_plc.render_title_labels_section.return_value = {
        "title": "My Title",
        "xlabel": "X Label",
        "ylabel": "Y Label",
        "legend_title": "Leg Title",
    }

    config = render_common_config(data, saved_config, plot_id=1)

    assert config["x"] == "num"
    assert config["title"] == "My Title"


def test_relabel_traces_renames_engine_agnostic_names() -> None:
    """Legend relabeling renames the engine-agnostic TraceConfig.name once
    (single source of truth) so both Plotly and Matplotlib honor it."""
    from src.core.models.visualization.trace_build_result import TraceBuildResult
    from src.core.models.visualization.trace_config import TraceConfig
    from src.web.pages.ui.plotting.base_plot import _relabel_traces

    result = TraceBuildResult(traces=[TraceConfig(name="trace1"), TraceConfig(name="trace2")])
    relabeled = _relabel_traces(result, {"trace1": "Renamed 1"})

    assert [t.name for t in relabeled.traces] == ["Renamed 1", "trace2"]
    # Input is not mutated (relabel returns new objects).
    assert [t.name for t in result.traces] == ["trace1", "trace2"]


def test_render_reorderable_list(concrete_plot: Any, mock_streamlit: Any) -> None:
    """Test reorderable list UI."""
    items = ["A", "B", "C"]

    # Initial render
    mock_streamlit.session_state = {}
    concrete_plot.render_reorderable_list("Label", items, "test_key")

    # Verify state initialization
    key = f"test_key_order_{concrete_plot.plot_id}"
    assert key in mock_streamlit.session_state
    assert mock_streamlit.session_state[key] == items

    # Simulate Swap A and B (Up button on B, index 1)
    # Mock button returns
    # We have loops. Up on index 1 should trigger swap.
    # Pattern: up_{i}
    def button_side_effect(label: Any, key: Any, **kwargs: Any) -> int:

        if key == f"test_key_up_1_{concrete_plot.plot_id}":
            return True
        return False

    mock_streamlit.button.side_effect = button_side_effect

    concrete_plot.render_reorderable_list("Label", items, "test_key")

    # State should be updated
    assert mock_streamlit.session_state[key] == ["B", "A", "C"]
    mock_streamlit.rerun.assert_called()


def test_render_advanced_options_shapes(concrete_plot: Any, mock_streamlit: Any) -> None:
    """Test advanced options with shape management."""
    config = {"shapes": []}

    # Mock adding a shape
    # Button "Add Shape" returns True
    # Inputs return minimal valid data
    def button_side_effect(label: Any, key: Any = None, **kwargs: Any) -> int:

        if "add_shape" in str(key):
            return True
        return False

    mock_streamlit.button.side_effect = button_side_effect

    result = concrete_plot.render_advanced_options(config)

    # Shape editing returns a new config and leaves the input unchanged.
    assert config["shapes"] == []
    assert len(result["shapes"]) == 1
    assert result["shapes"][0]["type"] == "line"


def test_render_advanced_options_display(concrete_plot: Any, mock_streamlit: Any) -> None:
    """Test advanced options output dict."""
    config = {"download_format": "png"}

    res = concrete_plot.render_advanced_options(config)

    assert res["download_format"] == "png"  # Mock selectbox passes through or default
    # If mock selectbox returns MagicMock, this fails.
    # mock_streamlit fixture returns MagicMock for everything by default.
    # We should update side_effect strictly or use loose assertions.

    # Validate existence of expected configuration keys.
    assert "show_error_bars" in res
    assert "xaxis_tickangle" in res
