from collections.abc import Generator
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pandas as pd
import plotly.graph_objects as go
import plotly.graph_objs.bar as bar_mod
import pytest
from pandas import DataFrame

from src.web.pages.ui.plotting.types.grouped_bar_plot import GroupedBarPlot


@pytest.fixture
def sample_data() -> DataFrame:
    return pd.DataFrame(
        {
            "Category": ["Bench1", "Bench1", "Bench2", "Bench2"],
            "Group": ["X", "Y", "X", "Y"],
            "Value": [10, 20, 15, 25],
            "Value.sd": [1, 2, 1.5, 2.5],
        }
    )


@pytest.fixture
def mock_streamlit() -> Generator[None, None, None]:
    with patch("src.web.pages.ui.plotting.types.grouped_bar_plot.st") as mock_st:
        with (
            patch("src.web.components.plotting.config.base_plot_config.st", mock_st),
            patch("src.web.components.plotting.config.grouped_bar_config.st", mock_st),
            patch("src.web.components.plotting.config.plot_config_components.st", mock_st),
        ):
            mock_st.columns.side_effect = lambda n: (
                [MagicMock() for _ in range(n)] if isinstance(n, int) else [MagicMock() for _ in n]
            )
            yield mock_st


def test_render_config_ui(mock_streamlit: Any, sample_data: Any) -> None:

    plot = GroupedBarPlot(1, "Test Plot")
    saved_config = {"x": "Category"}

    mock_streamlit.selectbox.side_effect = ["Category", "Value", "Group"]
    mock_streamlit.text_input.side_effect = [
        "Title",
        "X",
        "Y",
        "Leg",
    ]  # title, xlabel, ylabel, legend_title
    mock_streamlit.multiselect.side_effect = [["A", "B"], ["X", "Y"]]  # filters

    config = plot.render_config_ui(sample_data, saved_config)

    assert config["x"] == "Category"
    assert config["y"] == "Value"
    assert config["group"] == "Group"
    assert config["x_filter"] == ["A", "B"]
    assert config["group_filter"] == ["X", "Y"]


def test_create_figure_basic(sample_data: Any) -> None:

    plot = GroupedBarPlot(1, "Test Plot")
    config = {
        "x": "Category",
        "y": "Value",
        "group": "Group",
        "title": "Title",
        "xlabel": "X",
        "ylabel": "Y",
        "show_error_bars": False,
    }

    fig = plot.create_figure(sample_data, config)

    assert isinstance(fig, go.Figure)
    # px.bar with barmode='group'
    # 2 groups (X, Y) -> 2 traces usually in px
    assert len(list(fig.data)) == 2
    assert fig.layout.barmode == "group"


def test_create_figure_with_error_bars_and_filters(sample_data: Any) -> None:

    plot = GroupedBarPlot(1, "Test Plot")
    config = {
        "x": "Category",
        "y": "Value",
        "group": "Group",
        "title": "Title",
        "xlabel": "X",
        "ylabel": "Y",
        "show_error_bars": True,
        "x_filter": ["Bench1"],  # Filter out Bench2
        "xaxis_order": ["Bench1"],
        "group_order": ["Y", "X"],
    }

    fig = plot.create_figure(sample_data, config)

    # Should only have Category Bench1
    # Group Y and X present
    assert len(list(fig.data)) == 2

    # Check data content
    # Trace 0 should be first group in order. px handles order via category_orders
    layout = fig.layout
    # Plotly might convert list to tuple internally for layout properties
    assert list(layout.xaxis.ticktext) == ["Bench1"]
    # Check logic for error bars
    bar_trace = cast(go.Bar, fig.data[0])
    assert bar_trace.error_y is not None
    error_y = cast(bar_mod.ErrorY, bar_trace.error_y)
    assert error_y.array is not None


def test_get_legend_column() -> None:
    plot = GroupedBarPlot(1, "Test Plot")
    assert plot.get_legend_column({"group": "G"}) == "G"
    assert plot.get_legend_column({}) is None


def test_render_advanced_options_filtering(sample_data: Any) -> None:

    plot = GroupedBarPlot(1, "Test Plot")
    config = {"x": "Category", "group": "Group", "x_filter": ["Bench1"], "group_filter": ["X"]}

    with patch(
        "src.web.pages.ui.plotting.types.grouped_bar_plot.BasePlot.render_advanced_options"
    ) as mock_super:
        plot.render_advanced_options(config, sample_data)

        # Verify passed data is filtered
        # A, X -> Should be 1 row
        args, _ = mock_super.call_args
        filtered_df = args[1]
        assert len(filtered_df) == 1
        assert filtered_df.iloc[0]["Category"] == "Bench1"
        assert filtered_df.iloc[0]["Group"] == "X"
