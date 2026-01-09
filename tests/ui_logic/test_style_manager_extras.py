from unittest.mock import MagicMock, patch

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.plotting.styles import StyleManager


@pytest.fixture
def mock_streamlit():
    with patch("src.plotting.styles.base_ui.st") as mock_st, patch(
        "src.plotting.styles.line_ui.st", mock_st
    ), patch("src.plotting.styles.bar_ui.st", mock_st):
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

    # We need to mock the returns for the new widgets
    # ColorPicker: 4 calls
    mock_streamlit.color_picker.side_effect = ["#aaaaaa", "#ff0000", "#bbbbbb", "#00ff00"]
    # Checkbox: 2 calls
    mock_streamlit.checkbox.side_effect = [True, False]
    # Selectbox (Symbol): 2 calls (one for A, one for B)
    mock_streamlit.selectbox.side_effect = ["circle", "square"]
    # NumberInput: 4 calls (MarkerSize A, LineWidth A, MarkerSize B, LineWidth B)
    mock_streamlit.number_input.side_effect = [10, 3, 12, 4]

    styles = sm.render_series_colors_ui(config, df)

    # A
    assert styles["A"]["use_color"] is True
    assert styles["A"]["color"] == "#ff0000"
    # Specific options should be collected
    assert styles["A"]["symbol"] == "circle"
    assert styles["A"]["marker_size"] == 10
    assert styles["A"]["line_width"] == 3

    # B
    assert styles["B"]["use_color"] is False
    assert styles["B"]["color"] == "#00ff00"
    assert styles["B"]["symbol"] == "square"


def test_render_xaxis_labels_ui_filtering(mock_streamlit):
    df = pd.DataFrame({"x": ["a", "b"]})
    config = {"x": "x", "xaxis_labels": {"a": "A_lbl"}}
    sm = StyleManager(1, "bar")

    # text_input calls: 'a' -> 'A_new', 'b' -> ''
    mock_streamlit.text_input.side_effect = ["A_new", ""]

    labels = sm.render_xaxis_labels_ui(config, df)

    assert labels["a"] == "A_new"
    assert "b" not in labels  # Not added because empty string input


def test_apply_styles_palette_and_series(mock_streamlit):
    sm = StyleManager(1, "scatter")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[1], y=[1], name="A"))
    fig.add_trace(go.Scatter(x=[2], y=[2], name="B"))

    config = {
        "color_palette": "Set1",  # Non-Plotly palette
        "series_styles": {
            "A": {
                "use_color": True,
                "color": "#123456",
                "symbol": "square",
                "marker_size": 15,
                "line_width": 5,
            }
        },
        "enable_stripes": True,  # Should be ignored for scatter
    }

    sm.apply_styles(fig, config)

    # Trace A (Custom)
    trace_a = fig.data[0]
    assert trace_a.marker.color == "#123456"
    assert trace_a.marker.symbol == "square"
    assert trace_a.marker.size == 15
    assert trace_a.line.width == 5

    # Trace B (Palette)
    trace_b = fig.data[1]
    # Set1 palette first color is usually red-ish, checking it's applied (not default)
    assert trace_b.marker.color is not None
    assert trace_b.marker.color != "#123456"


def test_apply_styles_axis_labels_sorting(mock_streamlit):
    sm = StyleManager(1, "bar")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["b", "a"], y=[1, 2]))

    config = {
        "xaxis_labels": {"a": "Alpha", "b": "Beta"},
        # No xaxis_order, reliant on sorting
    }

    sm.apply_styles(fig, config)

    # Check layoutxaxis tickvals/ticktext
    layout = fig.layout
    assert layout.xaxis.tickmode == "array"
    # Should be sorted 'a', 'b'
    assert list(layout.xaxis.tickvals) == ["a", "b"]
    assert list(layout.xaxis.ticktext) == ["Alpha", "Beta"]


def test_apply_styles_axis_order(mock_streamlit):
    sm = StyleManager(1, "bar")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["b", "a", "c"], y=[1, 2, 3]))

    config = {"xaxis_labels": {"a": "Alpha"}, "xaxis_order": ["c", "a", "b"]}

    sm.apply_styles(fig, config)

    layout = fig.layout
    # Should follow order
    assert list(layout.xaxis.categoryarray) == ["c", "a", "b"]
    # tickvals/text should also honor order if applied
    assert list(layout.xaxis.tickvals) == ["c", "a", "b"]
    # 'a' mapped, others default
    assert list(layout.xaxis.ticktext) == ["c", "Alpha", "b"]
