from unittest.mock import MagicMock, patch

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.web.pages.ui.plotting.styles import StyleManager


@pytest.fixture
def mock_streamlit():
    with patch("src.web.pages.ui.plotting.styles.base_ui.st") as mock_st, patch(
        "src.web.pages.ui.plotting.styles.line_ui.st", mock_st
    ), patch("src.web.pages.ui.plotting.styles.bar_ui.st", mock_st):
        # Mock columns
        mock_st.columns.side_effect = lambda n: (
            [MagicMock() for _ in range(n)] if isinstance(n, int) else [MagicMock() for _ in n]
        )
        # Mock session_state
        mock_st.session_state = {}
        # Mock expander
        mock_st.expander.return_value.__enter__.return_value = MagicMock()
        yield mock_st


def test_render_series_renaming_ui_full(mock_streamlit):
    # Setup data and config
    df = pd.DataFrame({"group": ["A", "B"], "val": [1, 2]})
    config = {"color": "group", "series_styles": {}}
    sm = StyleManager(1, "grouped_stacked_bar")

    # Mock return values for widgets
    # text_input (renaming): A -> A_new, B -> B_new
    mock_streamlit.text_input.side_effect = ["A_new", "B_new"]

    styles = sm.render_series_renaming_ui(config, df)

    assert styles["A"]["name"] == "A_new"
    assert styles["B"]["name"] == "B_new"


def test_render_series_colors_ui_full(mock_streamlit):
    # Setup data and config
    df = pd.DataFrame({"group": ["A", "B"], "val": [1, 2]})
    config = {"color": "group", "series_styles": {}}
    sm = StyleManager(1, "line")  # Use line to trigger symbol/line_width widgets

    # Mock return values for widgets
    # render_series_colors_ui:
    # 1. color_picker (Original A - disabled)
    # 2. color_picker (Custom A)
    # 3. checkbox (Override A)
    # 4. color_picker (Original B - disabled)
    # 5. color_picker (Custom B)
    # 6. checkbox (Override B)

    # We need to match the calls.
    # A: Original=#..., Custom=#ff0000, Override=True
    # B: Original=#..., Custom=#00ff00, Override=False

    # matched calls:
    # A: Original, Custom, Override, Expander(Marker), Symbol, MarkerSize, LineWidth
    # B: Original, Custom, Override, Expander(Marker), Symbol, MarkerSize, LineWidth

    # Mock calls setup for: ColorPicker (x4), Checkbox (x2), Selectbox (x2), NumberInput (x4)
    mock_streamlit.color_picker.side_effect = ["#aaaaaa", "#ff0000", "#bbbbbb", "#00ff00"]
    mock_streamlit.checkbox.side_effect = [True, False]
    mock_streamlit.selectbox.side_effect = ["circle", "square"]
    mock_streamlit.number_input.side_effect = [10, 3, 12, 4]

    styles = sm.render_series_colors_ui(config, df)

    assert styles["A"]["use_color"] is True
    assert styles["A"]["color"] == "#ff0000"
    assert styles["A"]["symbol"] == "circle"
    assert styles["A"]["marker_size"] == 10
    assert styles["A"]["line_width"] == 3

    assert styles["B"]["use_color"] is False
    assert styles["B"]["color"] == "#00ff00"
    assert styles["B"]["symbol"] == "square"


def test_render_xaxis_labels_ui_filtering(mock_streamlit):
    df = pd.DataFrame({"x": ["a", "b"]})
    config = {"x": "x", "xaxis_labels": {"a": "A_lbl"}}
    sm = StyleManager(1, "bar")

    mock_streamlit.text_input.side_effect = ["A_new", ""]

    labels = sm.render_xaxis_labels_ui(config, df)

    assert labels["a"] == "A_new"
    assert "b" not in labels


def test_apply_styles_palette_and_series(mock_streamlit):
    sm = StyleManager(1, "scatter")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[1], y=[1], name="A"))
    fig.add_trace(go.Scatter(x=[2], y=[2], name="B"))

    config = {
        "color_palette": "Set1",
        "series_styles": {
            "A": {
                "use_color": True,
                "color": "#123456",
                "symbol": "square",
                "marker_size": 15,
                "line_width": 5,
            }
        },
        "enable_stripes": True,
    }

    sm.apply_styles(fig, config)

    trace_a = fig.data[0]
    assert trace_a.marker.color == "#123456"
    assert trace_a.marker.symbol == "square"
    assert trace_a.marker.size == 15
    assert trace_a.line.width == 5

    trace_b = fig.data[1]
    assert trace_b.marker.color is not None
    assert trace_b.marker.color != "#123456"


def test_apply_styles_axis_labels_sorting(mock_streamlit):
    sm = StyleManager(1, "bar")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["b", "a"], y=[1, 2]))

    config = {
        "xaxis_labels": {"a": "Alpha", "b": "Beta"},
    }

    sm.apply_styles(fig, config)

    layout = fig.layout
    assert layout.xaxis.tickmode == "array"
    assert list(layout.xaxis.tickvals) == ["a", "b"]
    assert list(layout.xaxis.ticktext) == ["Alpha", "Beta"]


def test_apply_styles_axis_order(mock_streamlit):
    sm = StyleManager(1, "bar")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["b", "a", "c"], y=[1, 2, 3]))

    config = {"xaxis_labels": {"a": "Alpha"}, "xaxis_order": ["c", "a", "b"]}

    sm.apply_styles(fig, config)

    layout = fig.layout
    assert list(layout.xaxis.categoryarray) == ["c", "a", "b"]
    assert list(layout.xaxis.tickvals) == ["c", "a", "b"]
    assert list(layout.xaxis.ticktext) == ["c", "Alpha", "b"]
