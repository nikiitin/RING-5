"""
Debug script for legend configuration.
Run this in the Streamlit app context to see what values are being set.
"""

import plotly.graph_objects as go

from src.plotting.styles.applicator import StyleApplicator


def debug_legend_config():
    """Print out the legend configuration being applied."""
    applicator = StyleApplicator(plot_type="bar")

    # Create figure with 7 traces (like the user's plot)
    fig = go.Figure()
    trace_names = [
        "Abort",
        "Stalled and committed",
        "Stalled and aborted",
        "Waiting FL",
        "Holding FL",
        "Committed",
        "Non-Transactional",
    ]
    for name in trace_names:
        fig.add_trace(go.Bar(y=[1, 2], name=name))

    # Simulate config with 2 columns
    config = {
        "legend_ncols": 2,
        "legend_x": 0.15,  # Position similar to user's image
        "legend_y": 0.95,
        "width": 900,  # Typical plot width
        "legend_orientation": "h",
        "legend_xanchor": "left",
        "legend_yanchor": "top",
    }

    print("=" * 60)
    print("DEBUG: Legend Configuration Test")
    print("=" * 60)
    print("\nInput config:")
    print(f"  legend_ncols: {config.get('legend_ncols')}")
    print(f"  width: {config.get('width')}")
    print(f"  Expected entrywidth: {int((config['width'] * 0.8) / config['legend_ncols'])} pixels")

    # Apply styles
    fig = applicator.apply_styles(fig, config)

    # Extract legend config
    legend = fig.layout.legend
    print("\nActual legend properties:")
    print(f"  entrywidth: {legend.entrywidth}")
    print(f"  entrywidthmode: {legend.entrywidthmode}")
    print(f"  orientation: {legend.orientation}")
    print(f"  x: {legend.x}")
    print(f"  y: {legend.y}")
    print(f"  xanchor: {legend.xanchor}")
    print(f"  yanchor: {legend.yanchor}")

    # Check if there are any overrides
    print("\nFull legend dict:")
    print(fig.layout.legend.to_plotly_json())

    print("\n" + "=" * 60)
    print("With 7 items and 2 columns, expected layout:")
    print("  Row 1: Abort, Stalled and committed")
    print("  Row 2: Stalled and aborted, Waiting FL")
    print("  Row 3: Holding FL, Committed")
    print("  Row 4: Non-Transactional")
    print("=" * 60)

    return fig


if __name__ == "__main__":
    debug_legend_config()
