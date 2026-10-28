"""
Interactive Plotly Chart Component

Custom Streamlit component for rendering Plotly figures with interactive
event handling and relayout data capture.
"""

import json
import os
from functools import lru_cache
from importlib.metadata import version
from typing import Any

import plotly.graph_objects as go
import streamlit.components.v1 as components
from plotly.offline import get_plotlyjs
from plotly.utils import PlotlyJSONEncoder

# Create a reference to the component
# Use absolute path to ensure robustness
# Point to local directory
component_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "custom_plotly"))
_component_func = components.declare_component("interactive_plotly", path=component_path)


@lru_cache(maxsize=1)
def _plotly_bundle() -> str:
    """Return the offline JavaScript bundle shipped with Python Plotly."""
    return get_plotlyjs()


def interactive_plotly_chart(
    fig: go.Figure,
    config: dict[str, Any] | None = None,
    key: str | None = None,
    *,
    capture_selection: bool = False,
    capture_click: bool = False,
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
        capture_click: Capture a closest-point click without changing the figure.

    Returns:
        Dictionary containing relayoutData if an interaction occurred,
        None otherwise
    """
    # [impl->req~ring5.figure.interactive-editing~1]
    # [impl->req~ring5.plots.linked-selections~1]
    # [impl->req~ring5.plots.drill-down~1]
    spec = fig.to_plotly_json()
    if capture_click:
        # Unified hover supplies multiple series; exploration needs one clicked point.
        spec["layout"]["hovermode"] = "closest"
    # Avoid a late native orjson import while parser threads may be active.
    fig_json = json.dumps(
        spec,
        cls=PlotlyJSONEncoder,
        separators=(",", ":"),
    )

    # Render component
    component_value: dict[str, Any] | None = _component_func(
        spec=fig_json,
        plotly_js=_plotly_bundle(),
        plotly_version=version("plotly"),
        config=json.dumps(config) if config else "{}",
        capture_selection=capture_selection,
        capture_click=capture_click,
        key=key,
        default=None,
    )

    return component_value
