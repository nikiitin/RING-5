"""
Unit tests for LayoutExtractor class.

Tests the refactored extraction logic that breaks down the monolithic
extract_layout() into smaller, focused methods.
"""

import plotly.graph_objects as go

from src.web.pages.ui.plotting.export.converters.layout_mapper import LayoutExtractor


class TestLayoutExtractor:
    """Test LayoutExtractor class functionality."""

    def test_extract_axis_properties_basic(self) -> None:
        """Verify extraction of basic axis properties."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6]))
        fig.update_xaxes(range=[0, 10], title="X Axis", type="linear", showgrid=True)
        fig.update_yaxes(range=[0, 20], title="Y Axis", type="log", showgrid=False)

        extractor = LayoutExtractor()
        props = extractor._extract_axis_properties(fig.layout)

        assert props["x_range"] == [0, 10]
        assert props["y_range"] == [0, 20]
        assert props["x_label"] == "X Axis"
        assert props["y_label"] == "Y Axis"
        assert props["x_type"] == "linear"
        assert props["y_type"] == "log"
        assert props["x_grid"] is True
        assert props["y_grid"] is False

    def test_extract_axis_properties_with_ticks(self) -> None:
        """Verify extraction of custom tick values and labels."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6]))
        fig.update_xaxes(tickmode="array", tickvals=[1, 2, 3], ticktext=["A", "B", "C"])
        fig.update_yaxes(tickmode="array", tickvals=[10, 20], ticktext=["Low", "High"])

        extractor = LayoutExtractor()
        props = extractor._extract_axis_properties(fig.layout)

        assert props["x_tickvals"] == [1, 2, 3]
        assert props["x_ticktext"] == ["A", "B", "C"]
        assert props["y_tickvals"] == [10, 20]
        assert props["y_ticktext"] == ["Low", "High"]

    def test_extract_legend_settings(self) -> None:
        """Verify extraction of legend positioning."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6], name="Series"))
        fig.update_layout(
            legend=dict(
                x=0.8,
                y=0.95,
                xanchor="left",
                yanchor="top",
            )
        )

        extractor = LayoutExtractor()
        legend = extractor._extract_legend_settings(fig.layout)

        assert legend["legend"]["x"] == 0.8
        assert legend["legend"]["y"] == 0.95
        assert legend["legend"]["xanchor"] == "left"
        assert legend["legend"]["yanchor"] == "top"

    def test_extract_legend_settings_missing(self) -> None:
        """Verify extraction handles missing legend gracefully."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6]))

        extractor = LayoutExtractor()
        legend = extractor._extract_legend_settings(fig.layout)

        assert legend == {}

    def test_detect_ylabel_from_annotation(self) -> None:
        """Verify detection of Y-axis label stored as annotation."""
        # Create annotation that looks like a Y-axis label
        annotations = [
            {
                "text": "Y-Axis Label",
                "textangle": -90,
                "xref": "paper",
                "x": 0.05,
                "y": 0.5,
                "yref": "paper",
                "showarrow": False,
            },
            {
                "text": "Regular annotation",
                "x": 2,
                "y": 5,
                "showarrow": True,
            },
        ]

        # Convert to Plotly annotation objects
        fig = go.Figure()
        for ann in annotations:
            fig.add_annotation(**ann)

        extractor = LayoutExtractor()
        ylabel = extractor._detect_ylabel_from_annotation(fig.layout.annotations)

        assert ylabel == "Y-Axis Label"

    def test_detect_ylabel_from_annotation_none(self) -> None:
        """Verify returns None when no Y-axis label annotation found."""
        fig = go.Figure()
        fig.add_annotation(x=2, y=5, text="Regular", showarrow=True)

        extractor = LayoutExtractor()
        ylabel = extractor._detect_ylabel_from_annotation(fig.layout.annotations)

        assert ylabel is None

    def test_extract_annotations_filters_ylabel(self) -> None:
        """Verify Y-axis label annotations are filtered out."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6]))
        fig.update_yaxes(title="Y-Axis Title")

        # Add a Y-axis label annotation (should be filtered)
        fig.add_annotation(
            text="Y-Axis Title",
            textangle=-90,
            xref="paper",
            x=0.05,
            y=0.5,
            yref="paper",
            showarrow=False,
        )

        # Add a regular annotation (should be kept)
        fig.add_annotation(
            x=2,
            y=5,
            text="Peak Value",
            showarrow=True,
        )

        extractor = LayoutExtractor()
        result = extractor._extract_annotations(fig.layout)

        # Should only have 1 annotation (the regular one)
        assert len(result["annotations"]) == 1
        assert result["annotations"][0]["text"] == "Peak Value"

    def test_extract_layout_complete(self) -> None:
        """Verify complete layout extraction orchestration."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6], name="Data"))
        fig.update_xaxes(range=[0, 10], title="X Axis")
        fig.update_yaxes(range=[0, 20], title="Y Axis")
        fig.update_layout(title="Test Plot", legend=dict(x=0.8, y=0.95))
        fig.add_annotation(x=2, y=5, text="Peak", showarrow=True)

        extractor = LayoutExtractor()
        layout = extractor.extract_layout(fig)

        # Verify all sections present
        assert "x_range" in layout
        assert "y_range" in layout
        assert "x_label" in layout
        assert "y_label" in layout
        assert "title" in layout
        assert "legend" in layout
        assert "annotations" in layout

        # Verify values
        assert layout["title"] == "Test Plot"
        assert layout["x_label"] == "X Axis"
        assert layout["y_label"] == "Y Axis"
        assert len(layout["annotations"]) == 1

    def test_extract_layout_minimal(self) -> None:
        """Verify extraction works with minimal layout."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6]))

        extractor = LayoutExtractor()
        layout = extractor.extract_layout(fig)

        # Should return dict even with minimal layout
        assert isinstance(layout, dict)
        # May have some properties but won't have title, labels, etc.
        assert "title" not in layout
