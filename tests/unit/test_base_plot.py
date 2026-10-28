from collections.abc import Generator
from typing import Any, Literal
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.components.common.reorderable_list import render_reorderable_list
from src.web.pages.ui.plotting.plot_factory import PlotFactory
from tests.conftest import columns_side_effect


# Concrete implementation for testing abstract class
class ConcretePlot(BasePlot):
    def render_config_ui(self, data: Any, saved_config: Any) -> dict:

        return {}

    def create_traces(self, data: Any, config: Any) -> TraceBuildResult:

        from src.core.models.visualization.trace_build_result import TraceBuildResult

        return TraceBuildResult(traces=[])


@pytest.fixture
def concrete_plot() -> ConcretePlot:
    return ConcretePlot(plot_id=1, name="Test Plot", plot_type="test")


@pytest.fixture
def mock_streamlit() -> Generator[MagicMock, None, None]:
    with (
        patch("src.web.pages.ui.plotting.plot_config_ui.st") as mock_st,
        patch("src.web.components.plotting.settings.advanced_settings.st", mock_st),
        patch("src.web.components.plotting.settings.engine_settings.st", mock_st),
        patch("src.web.components.common.reorderable_list.st", mock_st),
        patch("src.web.components.plotting.settings.shapes_settings.st", mock_st),
    ):
        mock_st.session_state = {}

        mock_st.columns.side_effect = columns_side_effect

        # Mock numeric inputs to return int for comparisons
        mock_st.number_input.return_value = 0
        mock_st.slider.return_value = 0

        # Mock selectbox to return first option or specific logic
        def selectbox_side_effect(label: Any, options: Any, index: Any = 0, **kwargs: Any) -> Any:

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


def test_source_snapshot_is_defensive_and_serialized(concrete_plot: Any) -> None:
    source = pd.DataFrame({"seed": [0, 1]})

    concrete_plot.replace_source_data(source)
    source.loc[0, "seed"] = 99

    assert concrete_plot.source_data is not None
    assert concrete_plot.source_data["seed"].tolist() == [0, 1]
    from src.core.common.typed_table_codec import TypedTableCodec

    decoded = TypedTableCodec.decode(concrete_plot.to_dict()["source_data"])
    assert decoded is not None
    pd.testing.assert_frame_equal(decoded, concrete_plot.source_data)


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


@patch("src.web.components.plotting.config.base_plot_config.st")
def test_auto_labels_follow_axis_changes_without_overwriting_custom_text(mock_st: Any) -> None:
    """Derived labels track new columns while user-authored labels remain stable."""
    from src.web.components.plotting.config.base_plot_config import _sync_auto_labels

    mock_st.session_state = {
        "plot.7.widgets.title": "seed by benchmark_name",
        "plot.7.widgets.xlabel": "benchmark_name",
        "plot.7.widgets.ylabel": "Publication value",
    }
    saved_config = {
        "x": "benchmark_name",
        "y": "seed",
        "title": "seed by benchmark_name",
        "xlabel": "benchmark_name",
        "ylabel": "Publication value",
    }

    _sync_auto_labels(saved_config, 7, "config_description", "system.cpu.ipc")

    assert mock_st.session_state == {
        "plot.7.widgets.title": "system.cpu.ipc by config_description",
        "plot.7.widgets.xlabel": "config_description",
        "plot.7.widgets.ylabel": "Publication value",
    }
    assert saved_config == {
        "x": "benchmark_name",
        "y": "seed",
        "title": "seed by benchmark_name",
        "xlabel": "benchmark_name",
        "ylabel": "Publication value",
    }


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_native_label_projection_preserves_engine_agnostic_names(
    engine: Literal["plotly", "matplotlib"],
) -> None:
    """Native display changes leave the caller's measured neutral input untouched."""
    import plotly.graph_objects as go
    from src.core.models.visualization.trace_build_result import TraceBuildResult
    from src.core.models.visualization.trace_config import BarTraceConfig
    from src.web.rendering.figure_preparation import prepare_figure
    from src.web.rendering.matplotlib_figure_builder import build_matplotlib_figure_from_prepared
    from src.web.rendering.plotly_figure_builder import build_plotly_figure

    result = TraceBuildResult(
        traces=[
            BarTraceConfig(name="trace1", x=["a", "b"], y=[3.0, 5.0]),
            BarTraceConfig(name="trace2", x=["a", "b"], y=[7.0, 9.0]),
        ]
    )
    prepared = prepare_figure(
        pd.DataFrame({"x": ["a", "b"], "value": [3.0, 5.0]}),
        {"legend_labels": {"trace1": "Renamed 1"}},
        "bar",
        lambda *_: result,
    )
    assert [trace.name for trace in prepared.trace_result.traces] == ["trace1", "trace2"]
    assert [trace.name for trace in result.traces] == ["trace1", "trace2"]
    if engine == "plotly":
        native = build_plotly_figure(prepared)
        names = []
        values = []
        for trace in native.figure.data:
            assert isinstance(trace, go.Bar)
            names.append(trace.name)
            assert trace.y is not None
            values.append(list(trace.y))
        assert names == ["Renamed 1", "trace2"]
        assert values == [[3.0, 5.0], [7.0, 9.0]]
    else:
        import matplotlib.pyplot as plt

        native_mpl = build_matplotlib_figure_from_prepared(prepared)
        try:
            legend = native_mpl.figure.axes[0].get_legend()
            assert legend is not None
            assert [text.get_text() for text in legend.texts] == ["Renamed 1", "trace2"]
            from matplotlib.patches import Rectangle

            heights = []
            for rectangle in native_mpl.figure.axes[0].patches:
                assert isinstance(rectangle, Rectangle)
                heights.append(rectangle.get_height())
            assert heights == [3.0, 5.0, 7.0, 9.0]

        finally:
            plt.close(native_mpl.figure)


def test_render_reorderable_list(concrete_plot: Any, mock_streamlit: Any) -> None:
    """Test reorderable list UI."""
    items = ["A", "B", "C"]

    # Initial render
    mock_streamlit.session_state = {}
    render_reorderable_list("Label", items, "test_key", plot_id=concrete_plot.plot_id)

    # Verify state initialization
    key = f"plot.{concrete_plot.plot_id}.widgets.appearance.test_key_order"
    assert key in mock_streamlit.session_state
    assert mock_streamlit.session_state[key] == items

    # Simulate Swap A and B (Up button on B, index 1)
    # Mock button returns
    # We have loops. Up on index 1 should trigger swap.
    # Pattern: up_{i}
    def button_side_effect(label: Any, key: Any, **kwargs: Any) -> int:

        if key == f"plot.{concrete_plot.plot_id}.widgets.appearance.test_key_up_1":
            return True
        return False

    mock_streamlit.button.side_effect = button_side_effect

    render_reorderable_list("Label", items, "test_key", plot_id=concrete_plot.plot_id)

    # State should be updated
    assert mock_streamlit.session_state[key] == ["B", "A", "C"]
    mock_streamlit.rerun.assert_called()


def test_rename_widget_keys_are_collision_resistant(
    concrete_plot: Any,
    mock_streamlit: Any,
) -> None:
    """Give visually similar legend values distinct stable widget keys."""
    mock_streamlit.text_input.return_value = ""
    mock_streamlit.button.return_value = False

    render_reorderable_list(
        "Legend items",
        ["a b", "a_b"],
        "legend",
        plot_id=concrete_plot.plot_id,
        enable_rename=True,
    )

    keys = [call.kwargs["key"] for call in mock_streamlit.text_input.call_args_list]
    assert len(keys) == len(set(keys)) == 2


def test_advanced_section_shapes(concrete_plot: Any, mock_streamlit: Any) -> None:
    """Test advanced options with shape management."""
    config: dict[str, Any] = {"shapes": []}

    # Mock adding a shape
    # Button "Add Shape" returns True
    # Inputs return minimal valid data
    def button_side_effect(label: Any, key: Any = None, **kwargs: Any) -> int:

        if "add_shape" in str(key):
            return True
        return False

    mock_streamlit.button.side_effect = button_side_effect

    result = concrete_plot.render_settings_section("advanced", config)

    # Shape editing returns a new config and leaves the input unchanged.
    assert config["shapes"] == []
    assert len(result["shapes"]) == 1
    assert result["shapes"][0]["type"] == "line"


def test_advanced_section_display(concrete_plot: Any, mock_streamlit: Any) -> None:
    """Test advanced options output dict."""
    config = {"export_scale": 3}

    res = concrete_plot.render_settings_section("advanced", config)

    assert res["export_scale"] == 3

    # Validate existence of expected configuration keys.
    assert "show_error_bars" in res
    assert "xaxis_tickangle" not in res
