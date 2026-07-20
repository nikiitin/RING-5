"""
Interactive Plotly Chart Component

Custom Streamlit component for rendering Plotly figures with interactive
event handling and relayout data capture.
"""

import json
import os
from typing import Any

import plotly.graph_objects as go
import streamlit.components.v1 as components

# Create a reference to the component
# Use absolute path to ensure robustness
# Point to local directory
component_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "custom_plotly"))
_component_func = components.declare_component("interactive_plotly", path=component_path)


def interactive_plotly_chart(
    fig: go.Figure,
    config: dict[str, Any] | None = None,
    key: str | None = None,
    *,
    capture_selection: bool = False,
) -> dict[str, Any] | None:
    """
    Render a Plotly figure with custom interactivity.

    Uses a custom HTML component that listens for relayout events from
    user interactions like zoom, pan, and legend clicks.

    Args:
        fig: Plotly Figure object to render
        config: Optional Plotly configuration dictionary
        key: Optional Streamlit component key for state management
        capture_selection: Return sanitized Plotly box/lasso selection events.

    Returns:
        Dictionary containing relayoutData if an interaction occurred,
        None otherwise
    """
    # [impl->req~ring5.figure.interactive-editing~1]
    # [impl->req~ring5.plots.linked-selections~1]
    # Serialize figure to JSON string
    fig_json: str = fig.to_json() or ""

    # Render component
    component_value: dict[str, Any] | None = _component_func(
        spec=fig_json,
        config=json.dumps(config) if config else "{}",
        capture_selection=capture_selection,
        key=key,
        default=None,
    )

    return component_value
