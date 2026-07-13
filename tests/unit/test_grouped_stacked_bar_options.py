from collections.abc import Generator
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pandas as pd
import plotly.graph_objects as go
import pytest
from pandas import DataFrame

from src.web.pages.ui.plotting.types.grouped_stacked_bar_plot import (
    GroupedStackedBarPlot,
)


@pytest.fixture
def mock_streamlit() -> Generator[None, None, None]:
    with (
        patch("src.web.pages.ui.plotting.types.grouped_stacked_bar_plot.st") as mock_st_plot,
        patch("src.web.pages.ui.plotting.plot_config_ui.st", mock_st_plot),
        patch("src.web.pages.ui.plotting.styles.base_ui.st", mock_st_plot),
        patch("src.web.pages.ui.plotting.styles.factory.StyleUIFactory"),
        patch("src.web.components.common.reorderable_list.st", mock_st_plot),
        patch("src.web.components.plotting.settings.shapes_settings.st", mock_st_plot),
        patch("src.web.components.plotting.settings.reference_line_settings.st", mock_st_plot),
        patch("src.web.components.plotting.settings.ordering_settings.st", mock_st_plot),
        patch("src.web.components.plotting.settings.widget_factory.st", mock_st_plot),
    ):
        mock_st_plot.columns.side_effect = lambda n: (
            [MagicMock() for _ in range(n)] if isinstance(n, int) else [MagicMock() for _ in n]
        )
        mock_st_plot.expander.return_value.__enter__.return_value = MagicMock()
        mock_st_plot.number_input.return_value = 10
        mock_st_plot.selectbox.side_effect = lambda label, options, **kwargs: (
            options[kwargs.get("index", 0)] if options else None
        )

        yield mock_st_plot


@pytest.fixture
def sample_data() -> DataFrame:
    return pd.DataFrame(
        {
            "Benchmark": ["A", "A", "B", "B"],
            "Config": ["Small", "Large", "Small", "Large"],
            "Ticks": [100, 200, 150, 250],
            "Energy": [10, 20, 15, 25],
            "Ticks.sd": [5, 10, 7, 12],
        }
    )


def test_render_advanced_options_defaults(sample_data: Any, mock_streamlit: Any) -> None:

    plot = GroupedStackedBarPlot(1, "Test Plot")
    config = plot.render_advanced_options({}, sample_data)

    assert "bargap" in config
    assert "bargroupgap" in config
    assert "bar_border_width" in config
    assert "show_error_bars" in config


def test_specific_advanced_options_overrides(sample_data: Any, mock_streamlit: Any) -> None:
    """Widget overrides are preserved in the resulting configuration."""
    plot = GroupedStackedBarPlot(1, "Test Plot")

    mock_streamlit.checkbox.side_effect = [True, False, True]  # Error Bars, Ref Line, Editable
    mock_streamlit.number_input.return_value = 5.0
    # General export controls precede the shape-type control.
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


def test_create_figure_renaming(sample_data: Any, mock_streamlit: Any) -> None:

    plot = GroupedStackedBarPlot(1, "Test Plot")

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
    plot._applicator.apply_styles(fig, config)

    traces = cast(list[go.Bar], list(fig.data))
    t1 = next(t for t in traces if t.name == "Total Cycles")
    assert cast(go.bar.Marker, t1.marker).color == "#FF0000"

    t2 = next(t for t in traces if t.name == "Joules")
    assert cast(go.bar.Marker, t2.marker).color == "#00FF00"


def test_create_figure_major_minor_renaming(sample_data: Any, mock_streamlit: Any) -> None:

    plot = GroupedStackedBarPlot(1, "Test Plot")

    config = {
        "x": "Benchmark",
        "group": "Config",
        "y_columns": ["Ticks"],
        "xaxis_labels": {"A": "Alpha"},
        "group_renames": {"Small": "Tiny"},
        "bargroupgap": 0.1,
    }

    fig = plot.create_figure(sample_data, config)

    # The layout annotations are used for X-axis labels in this plot type
    layout = fig.layout
    annotations = layout.annotations
    labels = [a.text for a in annotations]

    assert "<b>Alpha</b>" in labels

    # Preserve string-valued minor-group labels instead of replacing them with indices.
    ticktext = fig.layout.xaxis.ticktext
    assert "Tiny" in ticktext, f"Expected 'Tiny' in ticktext, found: {ticktext}"
    assert "Large" in ticktext

    # A failed coordinate lookup leaves a gap in the rendered trace.
    trace0 = cast(go.Bar, fig.data[0])
    x_values = trace0.x
    assert x_values is not None
    assert len(list(x_values)) > 0
    assert all(
        x is not None for x in x_values
    ), f"Found None in X coordinates: {x_values}. Traces lost?"
