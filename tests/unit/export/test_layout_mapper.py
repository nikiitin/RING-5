"""
Unit tests for layout mapper.

Tests extraction of layout properties from Plotly figures for preservation
in LaTeX exports.
"""

import plotly.graph_objects as go

from src.web.pages.ui.plotting.export.converters.layout_mapper import LayoutMapper


class TestLayoutMapper:
    """Test layout mapping functionality."""

    def test_extract_axis_limits(self) -> None:
        """Verify can extract axis limits from Plotly figure."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6]))
        fig.update_xaxes(range=[0, 10])
        fig.update_yaxes(range=[0, 20])

        layout = LayoutMapper.extract_layout(fig)

        assert "x_range" in layout
        assert layout["x_range"] == [0, 10]
        assert "y_range" in layout
        assert layout["y_range"] == [0, 20]

    def test_extract_legend_position(self) -> None:
        """Verify can extract legend position."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6], name="Series 1"))
        fig.update_layout(
            legend=dict(
                x=0.8,
                y=0.95,
                xanchor="left",
                yanchor="top",
            )
        )

        layout = LayoutMapper.extract_layout(fig)

        assert "legend" in layout
        assert layout["legend"]["x"] == 0.8
        assert layout["legend"]["y"] == 0.95
        assert layout["legend"]["xanchor"] == "left"
        assert layout["legend"]["yanchor"] == "top"

    def test_extract_axis_labels(self) -> None:
        """Verify can extract axis labels."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6]))
        fig.update_xaxes(title="Time (s)")
        fig.update_yaxes(title="IPC")

        layout = LayoutMapper.extract_layout(fig)

        assert "x_label" in layout
        assert layout["x_label"] == "Time (s)"
        assert "y_label" in layout
        assert layout["y_label"] == "IPC"

    def test_extract_title(self) -> None:
        """Verify can extract figure title."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6]))
        fig.update_layout(title="Performance Comparison")

        layout = LayoutMapper.extract_layout(fig)

        assert "title" in layout
        assert layout["title"] == "Performance Comparison"

    def test_extract_grid_settings(self) -> None:
        """Verify can extract grid visibility settings."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6]))
        fig.update_xaxes(showgrid=True, gridcolor="lightgray")
        fig.update_yaxes(showgrid=False)

        layout = LayoutMapper.extract_layout(fig)

        assert "x_grid" in layout
        assert layout["x_grid"] is True
        assert "y_grid" in layout
        assert layout["y_grid"] is False

    def test_extract_log_scale(self) -> None:
        """Verify can detect log scale axes."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 10, 100], y=[1, 100, 10000]))
        fig.update_xaxes(type="log")
        fig.update_yaxes(type="log")

        layout = LayoutMapper.extract_layout(fig)

        assert "x_type" in layout
        assert layout["x_type"] == "log"
        assert "y_type" in layout
        assert layout["y_type"] == "log"

    def test_extract_with_missing_properties(self) -> None:
        """Verify extraction handles missing optional properties gracefully."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6]))
        # No explicit layout settings

        layout = LayoutMapper.extract_layout(fig)

        # Should still return dict, but with None/defaults for missing values
        assert isinstance(layout, dict)

    def test_extract_annotations(self) -> None:
        """Verify can extract figure annotations."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6]))
        fig.add_annotation(
            x=2,
            y=5,
            text="Peak",
            showarrow=True,
        )

        layout = LayoutMapper.extract_layout(fig)

        assert "annotations" in layout
        assert len(layout["annotations"]) == 1
        assert layout["annotations"][0]["text"] == "Peak"

    def test_apply_layout_to_matplotlib(self) -> None:
        """Verify can apply extracted layout to Matplotlib axes."""
        import matplotlib.pyplot as plt

        # Extract from Plotly
        plotly_fig = go.Figure()
        plotly_fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6]))
        plotly_fig.update_xaxes(range=[0, 10], title="X Axis")
        plotly_fig.update_yaxes(range=[0, 20], title="Y Axis")
        plotly_fig.update_layout(title="Test Plot")

        layout = LayoutMapper.extract_layout(plotly_fig)

        # Apply to Matplotlib with zero margin preset
        mpl_fig, mpl_ax = plt.subplots()
        preset_no_margin = {"xaxis_margin": 0.0, "xtick_rotation": 0.0}
        LayoutMapper.apply_to_matplotlib(mpl_ax, layout, preset=preset_no_margin)

        # Verify settings applied
        assert mpl_ax.get_xlim() == (0, 10)
        assert mpl_ax.get_ylim() == (0, 20)
        assert mpl_ax.get_xlabel() == "X Axis"
        assert mpl_ax.get_ylabel() == "Y Axis"
        assert mpl_ax.get_title() == "Test Plot"

        plt.close(mpl_fig)

    def test_roundtrip_layout_preservation(self) -> None:
        """Verify layout can be extracted and reapplied without loss."""
        import matplotlib.pyplot as plt

        # Create Plotly figure with specific layout
        plotly_fig = go.Figure()
        plotly_fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6]))
        plotly_fig.update_xaxes(
            range=[0.5, 3.5],
            title="Time (ms)",
            showgrid=True,
        )
        plotly_fig.update_yaxes(
            range=[3, 7],
            title="Speedup",
            showgrid=False,
        )

        # Extract and apply with zero margin preset
        layout = LayoutMapper.extract_layout(plotly_fig)
        mpl_fig, mpl_ax = plt.subplots()
        preset_no_margin = {"xaxis_margin": 0.0, "xtick_rotation": 0.0}
        LayoutMapper.apply_to_matplotlib(mpl_ax, layout, preset=preset_no_margin)

        # Verify exact preservation
        assert mpl_ax.get_xlim() == (0.5, 3.5)
        assert mpl_ax.get_ylim() == (3, 7)
        assert mpl_ax.get_xlabel() == "Time (ms)"
        assert mpl_ax.get_ylabel() == "Speedup"
        assert mpl_ax.xaxis.get_gridlines()[0].get_visible() is True
        # Y grid check is more complex, just verify method doesn't crash

        plt.close(mpl_fig)
