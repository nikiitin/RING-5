from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.web.pages.ui.plotting.types.grouped_stacked_bar_plot import (
    GroupedStackedBarPlot,
)


@pytest.fixture
def mock_streamlit():
    with (
        patch("src.web.pages.ui.plotting.types.grouped_stacked_bar_plot.st") as mock_st_plot,
        patch("src.web.pages.ui.plotting.base_plot.st", mock_st_plot),
        patch("src.web.pages.ui.plotting.styles.base_ui.st", mock_st_plot),
        patch("src.web.pages.ui.plotting.styles.manager.StyleUIFactory"),
    ):  # Mock factory to avoid side effects if needed

        # Setup common mock behaviors
        mock_st_plot.columns.side_effect = lambda n: (
            [MagicMock() for _ in range(n)] if isinstance(n, int) else [MagicMock() for _ in n]
        )
        mock_st_plot.expander.return_value.__enter__.return_value = MagicMock()
        mock_st_plot.number_input.return_value = 10
        # Configure selectbox to return first option if index not specified, or something sensible
        mock_st_plot.selectbox.side_effect = lambda label, options, **kwargs: (
            options[kwargs.get("index", 0)] if options else None
        )

        yield mock_st_plot


@pytest.fixture
def sample_data():
    return pd.DataFrame(
        {
            "Benchmark": ["A", "A", "B", "B"],
            "Config": ["Small", "Large", "Small", "Large"],
            "Ticks": [100, 200, 150, 250],
            "Energy": [10, 20, 15, 25],
            "Ticks.sd": [5, 10, 7, 12],
        }
    )


def test_render_advanced_options_defaults(sample_data, mock_streamlit):
    plot = GroupedStackedBarPlot(1, "Test Plot")
    config = plot.render_advanced_options({}, sample_data)

    # Check default keys exist
    assert "bargap" in config
    assert "bargroupgap" in config
    assert "bar_border_width" in config
    assert "show_error_bars" in config


def test_specific_advanced_options_overrides(sample_data, mock_streamlit):
    """Test that advanced options correctly capture user overrides."""
    plot = GroupedStackedBarPlot(1, "Test Plot")

    # Mock interactions for general and bar settings:
    # 1. st.checkbox("Error Bars") -> True
    # 2. st.number_input("Y-axis Step") -> 5.0
    # 3. st.selectbox("Download Format") -> "pdf"
    # 4. st.selectbox("Export Scale") -> 2
    # 5. st.slider("X-axis Rotation") -> 15
    # 6. st.slider("Bar Gap") -> 0.3
    # 7. st.slider("Bar Group Gap") -> 0.1
    # 8. st.slider("Bar Border Width") -> 1.5
    # 9. st.checkbox("Enable Interactive Editing") -> True

    # Note: GroupedStackedBarPlot doesn't have the "Series Renaming" checkbox from BasePlot.
    mock_streamlit.checkbox.side_effect = [True, True]  # Error Bars, Editable
    mock_streamlit.number_input.return_value = 5.0
    # Selectbox needs to match specific keys or order.
    # General section has 2 (fmt, scale). Reorderable list uses none.
    # But StyleManager.render_series_renaming_ui is called, it doesn't use selectbox.
    # BasePlot._render_shapes_ui uses 1 selectbox.
    mock_streamlit.selectbox.side_effect = ["pdf", 2, "line"]
    mock_streamlit.slider.side_effect = [15, 0.3, 0.1, 1.5]

    saved_config = {"x": "Benchmark", "group": "Config", "y_columns": ["Ticks"]}

    config = plot.render_advanced_options(saved_config, sample_data)

    assert config["show_error_bars"] is True
    assert config["yaxis_dtick"] == 5.0
    assert config["download_format"] == "pdf"
    assert config["export_scale"] == 2
    assert config["xaxis_tickangle"] == 15
    assert config["bargap"] == 0.3
    assert config["bargroupgap"] == 0.1
    assert config["bar_border_width"] == 1.5
    assert config.get("enable_editable") is True


def test_create_figure_renaming(sample_data, mock_streamlit):
    plot = GroupedStackedBarPlot(1, "Test Plot")

    # Config with renaming via StyleManager (Stacks)
    # The plot now explicitly renders generic series styling for y_columns
    config = {
        "x": "Benchmark",
        "group": "Config",
        "y_columns": ["Ticks", "Energy"],
        "series_styles": {
            "Ticks": {"name": "Total Cycles", "color": "#FF0000", "use_color": True},
            "Energy": {"name": "Joules", "color": "#00FF00", "use_color": True},
        },
    }

    fig = plot.create_figure(sample_data, config)
    plot.style_manager.apply_styles(fig, config)

    # Check traces - Ticks and Energy
    # Ticks -> Total Cycles
    t1 = next(t for t in fig.data if t.name == "Total Cycles")
    assert t1.marker.color == "#FF0000"

    t2 = next(t for t in fig.data if t.name == "Joules")
    assert t2.marker.color == "#00FF00"


def test_create_figure_major_minor_renaming(sample_data, mock_streamlit):
    plot = GroupedStackedBarPlot(1, "Test Plot")

    # Rename Major Group (Benchmark): A -> Alpha
    # Rename Minor Group (Config): Small -> Tiny
    config = {
        "x": "Benchmark",
        "group": "Config",
        "y_columns": ["Ticks"],
        "xaxis_labels": {"A": "Alpha"},  # Major Group
        "group_renames": {"Small": "Tiny"},  # Minor Group
        "bargroupgap": 0.1,
    }

    fig = plot.create_figure(sample_data, config)

    # The layout annotations are used for X-axis labels in this plot type
    layout = fig.layout
    annotations = layout.annotations
    labels = [a.text for a in annotations]

    # Major Group Check
    assert "<b>Alpha</b>" in labels

    # Bug 1 Check: Minor Group labels should NOT be numeric indices if they were strings ("Small", "Large")  # noqa: E501
    ticktext = fig.layout.xaxis.ticktext
    # We expect "Tiny" and "Large" in ticktext.
    # If they turned into numbers (like 0, 1), this assertion will fail or we can assert explicitly.
    assert "Tiny" in ticktext, f"Expected 'Tiny' in ticktext, found: {ticktext}"
    assert "Large" in ticktext

    # Bug 2 Check: Bars should exist (have valid X coordinates)
    # If data mismatch occurred, X coordinates would be None (or NaNs)
    # We check the first trace (Ticks)
    trace0 = fig.data[0]
    # Check if x values are valid numbers
    assert len(trace0.x) > 0
    # If get_coord returned None, we might see None in x or Plotly might filter them.
    # GroupedStackedBarPlot puts None if lookup fails.
    assert all(
        x is not None for x in trace0.x
    ), f"Found None in X coordinates: {trace0.x}. Traces lost?"


if __name__ == "__main__":
    pass
