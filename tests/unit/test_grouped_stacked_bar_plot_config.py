from collections.abc import Generator
from typing import Any, cast
from unittest.mock import patch

import pandas as pd
import plotly.graph_objects as go
import pytest
from pandas import DataFrame

from src.web.pages.ui.plotting.types.grouped_stacked_bar_plot import (
    GroupedStackedBarPlot,
)
from tests.conftest import columns_side_effect


@pytest.fixture
def mock_streamlit() -> Generator[None, None, None]:
    with (
        patch("src.web.pages.ui.plotting.types.grouped_stacked_bar_plot.st") as mock_st,
        patch("src.web.components.plotting.config.plot_config_components.st", mock_st),
    ):
        mock_st.session_state = {}

        mock_st.columns.side_effect = columns_side_effect

        yield mock_st


@pytest.fixture
def sample_data() -> DataFrame:
    return pd.DataFrame(
        {"Benchmark": ["A", "B"], "Config": ["Low", "High"], "Value": [10, 20], "Value2": [5, 15]}
    )


def test_render_config_ui_basic(mock_streamlit: Any, sample_data: Any) -> None:
    """Test basic configuration UI rendering."""
    plot = GroupedStackedBarPlot(1, "Test Plot")
    saved_config = {"x": "Benchmark", "y_columns": ["Value"]}

    # Mocks for widgets
    # Col 1: X, Group
    # Text inputs: Title, XLabel, YLabel (3)
    # Then Renaming:
    #   Legend renames loops over y_columns (1 call: Value)
    #   X-axis renames loops over unique Benchmark (2 calls: A, B)
    #   Group renames (None, group is None)
    # Total Text Inputs: 3 + 1 + 2 = 6
    mock_streamlit.selectbox.side_effect = ["Benchmark", None]
    mock_streamlit.multiselect.return_value = ["Value"]
    mock_streamlit.text_input.side_effect = ["Title", "X Label", "Y Label", "Value", "A", "B"]

    config = plot.render_config_ui(sample_data, cast(Any, saved_config))

    assert config["x"] == "Benchmark"
    assert config["y_columns"] == ["Value"]
    assert config["group"] is None


def test_render_config_ui_grouped(mock_streamlit: Any, sample_data: Any) -> None:
    """Test configuration UI with grouping."""
    plot = GroupedStackedBarPlot(1, "Test Plot")
    saved_config = {"x": "Benchmark", "group": "Config", "y_columns": ["Value", "Value2"]}

    mock_streamlit.selectbox.side_effect = ["Benchmark", "Config"]
    mock_streamlit.multiselect.return_value = ["Value", "Value2"]

    # Text inputs: Title, XLabel, YLabel (3)
    # Then Renaming expander:
    #   Legend renames loops over y_columns (2 calls)
    #   X-axis renames loops over unique Benchmark (2 calls: A, B)
    #   Group renames loops over unique Config (2 calls: Low, High)
    # Total Text Inputs: 3 + 2 + 2 + 2 = 9

    # Side effects for widget simulation.
    mock_streamlit.text_input.return_value = "Test Input"

    config = plot.render_config_ui(sample_data, cast(Any, saved_config))

    assert config["x"] == "Benchmark"
    assert config["group"] == "Config"
    assert len(config["y_columns"]) == 2


def test_grouped_stacked_default_omits_colliding_x_axis_title(sample_data: DataFrame) -> None:
    # [test->req~ring5.plot.grouped-stacked-bar~1]
    module = "src.web.components.plotting.config.grouped_stacked_bar_config"
    with (
        patch(f"{module}.st") as mock_st,
        patch(f"{module}.detect_column_types") as mock_detect,
        patch(f"{module}.PlotConfigComponents") as mock_components,
    ):
        mock_st.session_state = {}
        mock_st.columns.side_effect = columns_side_effect
        mock_st.selectbox.side_effect = ["Benchmark", "Config"]
        mock_st.multiselect.return_value = ["Value", "Value2"]
        mock_st.checkbox.return_value = False
        mock_detect.return_value = (["Value", "Value2"], ["Benchmark", "Config"])
        mock_components.render_title_labels_section.return_value = {
            "title": "Title",
            "xlabel": "",
            "ylabel": "Value",
            "legend_title": "",
        }
        mock_components.render_filter_multiselects.return_value = (["A", "B"], ["Low", "High"])

        from src.web.components.plotting.config.grouped_stacked_bar_config import render

        render(sample_data, cast(Any, {}), 5)

    assert mock_components.render_title_labels_section.call_args.kwargs["default_xlabel"] == ""


def test_render_config_filter_options(mock_streamlit: Any, sample_data: Any) -> None:
    """Test filter options rendering."""
    plot = GroupedStackedBarPlot(1, "Test Plot")
    saved_config = {"x": "Benchmark", "group": "Config", "y_columns": ["Value"]}

    # Mocking selectboxes is crucial for control flow
    mock_streamlit.selectbox.side_effect = ["Benchmark", "Config"]

    # Multiselects:
    # Y-axis
    # X Filter
    # Group Filter

    def multiselect_side_effect(
        label: Any, options: Any, default: Any = None, key: Any = None, **kwargs: Any
    ) -> list:

        if "Statistics" in label:
            return ["Value"]
        if "Filter Benchmark" in label:
            return ["A"]
        if "Filter Config" in label:
            return ["Low"]
        return []

    mock_streamlit.multiselect.side_effect = multiselect_side_effect

    config = plot.render_config_ui(sample_data, cast(Any, saved_config))

    assert config["x_filter"] == ["A"]
    assert config["group_filter"] == ["Low"]


def test_create_figure_grouped_calculated(sample_data: Any) -> None:
    """Test figure creation with calculated logic for grouping."""
    plot = GroupedStackedBarPlot(1, "Test")
    config = {
        "x": "Benchmark",
        "group": "Config",
        "y_columns": ["Value"],
        "bargap": 0.2,
        "bargroupgap": 0.1,
    }

    fig = plot.create_figure(sample_data, config)

    # Implementation loops over y_columns and adds trace.
    # GSB adds one trace per Y column.

    assert len(list(fig.data)) == 1
    trace = cast(go.Bar, fig.data[0])

    # Data has 2 rows (A, Low) and (B, High).
    # So 2 bars.
    x_data = cast(tuple[str, ...], trace.x)
    assert len(x_data) == 2

    # Check customdata (totals)
    assert trace.customdata is not None
