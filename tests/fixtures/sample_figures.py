"""
Sample Plotly figures for testing export functionality.

Provides reusable test fixtures for various plot types.
"""

import plotly.graph_objects as go


def create_simple_bar_figure() -> go.Figure:
    """
    Create a simple bar chart for testing.

    Returns:
        Plotly Figure with basic bar chart
    """
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=["Category A", "Category B", "Category C"],
            y=[10, 25, 15],
            name="Series 1",
            marker=dict(color="#1f77b4"),
        )
    )
    fig.update_layout(
        title="Sample Bar Chart",
        xaxis_title="Categories",
        yaxis_title="Values",
        showlegend=True,
        width=800,
        height=600,
    )
    return fig


def create_grouped_bar_figure() -> go.Figure:
    """
    Create grouped bar chart with multiple series.

    Returns:
        Plotly Figure with grouped bars
    """
    fig = go.Figure()
    fig.add_trace(
        go.Bar(x=["A", "B", "C"], y=[10, 20, 15], name="Series 1", marker=dict(color="#1f77b4"))
    )
    fig.add_trace(
        go.Bar(x=["A", "B", "C"], y=[15, 25, 10], name="Series 2", marker=dict(color="#ff7f0e"))
    )
    fig.update_layout(
        title="Grouped Bar Chart",
        xaxis_title="Category",
        yaxis_title="Value",
        barmode="group",
        showlegend=True,
    )
    return fig


def create_line_figure() -> go.Figure:
    """
    Create a simple line chart for testing.

    Returns:
        Plotly Figure with line plot
    """
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[1, 2, 3, 4, 5],
            y=[1, 4, 9, 16, 25],
            mode="lines",
            name="y = x²",
            line=dict(color="#2ca02c", width=2),
        )
    )
    fig.update_layout(
        title="Sample Line Plot",
        xaxis_title="X Axis",
        yaxis_title="Y Axis",
        showlegend=True,
    )
    return fig


def create_scatter_figure() -> go.Figure:
    """
    Create a scatter plot for testing.

    Returns:
        Plotly Figure with scatter plot
    """
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[1, 2, 3, 4, 5, 6],
            y=[2, 5, 3, 7, 4, 8],
            mode="markers",
            name="Data Points",
            marker=dict(size=10, color="#d62728"),
        )
    )
    fig.update_layout(
        title="Sample Scatter Plot",
        xaxis_title="X Variable",
        yaxis_title="Y Variable",
        showlegend=True,
    )
    return fig


def create_figure_with_custom_legend() -> go.Figure:
    """
    Create figure with custom legend position (user interaction simulation).

    Returns:
        Plotly Figure with custom legend placement
    """
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["A", "B", "C"], y=[10, 20, 15], name="Data"))
    fig.update_layout(
        title="Custom Legend Position",
        xaxis_title="Category",
        yaxis_title="Value",
        showlegend=True,
        legend=dict(x=0.05, y=0.95, xanchor="left", yanchor="top"),
    )
    return fig


def create_figure_with_zoom() -> go.Figure:
    """
    Create figure with custom axis ranges (user zoom simulation).

    Returns:
        Plotly Figure with custom axis ranges
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(range(100)), y=list(range(100)), mode="lines", name="Data"))
    fig.update_layout(
        title="Zoomed View",
        xaxis=dict(title="X", range=[20, 80]),  # User zoomed in
        yaxis=dict(title="Y", range=[20, 80]),
        showlegend=True,
    )
    return fig


def create_figure_with_log_scale() -> go.Figure:
    """
    Create figure with logarithmic scale.

    Returns:
        Plotly Figure with log-scaled axes
    """
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[1, 10, 100, 1000],
            y=[1, 10, 100, 1000],
            mode="lines+markers",
            name="Exponential",
        )
    )
    fig.update_layout(
        title="Logarithmic Scale",
        xaxis=dict(title="X (log scale)", type="log"),
        yaxis=dict(title="Y (log scale)", type="log"),
        showlegend=True,
    )
    return fig


def create_multi_series_line_figure() -> go.Figure:
    """
    Create line plot with multiple series.

    Returns:
        Plotly Figure with multiple line series
    """
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[1, 2, 3, 4, 5], y=[1, 4, 9, 16, 25], mode="lines", name="y = x²", line=dict(width=2)
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[1, 2, 3, 4, 5],
            y=[2, 4, 6, 8, 10],
            mode="lines",
            name="y = 2x",
            line=dict(width=2, dash="dash"),
        )
    )
    fig.update_layout(
        title="Multiple Series",
        xaxis_title="X",
        yaxis_title="Y",
        showlegend=True,
        legend=dict(x=0.02, y=0.98, xanchor="left", yanchor="top"),
    )
    return fig
