import json
import os

import streamlit.components.v1 as components

# Create a reference to the component
# Use absolute path to ensure robustness
_RELEASE = True

# Point to local directory
component_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "custom_plotly"))
_component_func = components.declare_component("interactive_plotly", path=component_path)


def interactive_plotly_chart(fig, config=None, key=None):
    """
    Render a Plotly figure using a custom HTML component that listens for relayout events.
    Returns the relayoutData (dict) if an interaction occurred, or None.

    Args:
        fig: The Plotly Figure object.
        config: Plotly configuration dictionary (optional).
        key: Streamlit component key.
    """
    # Serialize figure to JSON string
    fig_json = fig.to_json()

    # Render component
    component_value = _component_func(
        spec=fig_json, config=json.dumps(config) if config else "{}", key=key, default=None
    )

    return component_value
