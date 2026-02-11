"""Tests for LayoutExtractor & LayoutMapper — uncovered extraction branches."""

import plotly.graph_objects as go
import pytest

from src.web.pages.ui.plotting.export.converters.impl.layout_mapper import (
    LayoutExtractor,
    LayoutMapper,
)


@pytest.fixture
def extractor() -> LayoutExtractor:
    return LayoutExtractor()


class TestAxisPropertyExtraction:
    """Test axis range, label, grid, type, and tick extraction."""

    def test_extract_axis_ranges(self, extractor: LayoutExtractor) -> None:
        fig = go.Figure()
        fig.update_layout(xaxis=dict(range=[0, 10]), yaxis=dict(range=[0, 100]))
        result = extractor.extract_layout(fig)
        assert result["x_range"] == [0, 10]
        assert result["y_range"] == [0, 100]

    def test_extract_axis_labels(self, extractor: LayoutExtractor) -> None:
        fig = go.Figure()
        fig.update_layout(xaxis_title="X Label", yaxis_title="Y Label", title="Title")
        result = extractor.extract_layout(fig)
        assert result["x_label"] == "X Label"
        assert result["y_label"] == "Y Label"
        assert result["title"] == "Title"

    def test_extract_grid_settings(self, extractor: LayoutExtractor) -> None:
        fig = go.Figure()
        fig.update_layout(xaxis=dict(showgrid=True), yaxis=dict(showgrid=False))
        result = extractor.extract_layout(fig)
        assert result["x_grid"] is True
        assert result["y_grid"] is False

    def test_extract_axis_types(self, extractor: LayoutExtractor) -> None:
        fig = go.Figure()
        fig.update_layout(xaxis=dict(type="linear"), yaxis=dict(type="log"))
        result = extractor.extract_layout(fig)
        assert result["x_type"] == "linear"
        assert result["y_type"] == "log"

    def test_extract_tickvals_ticktext(self, extractor: LayoutExtractor) -> None:
        fig = go.Figure()
        fig.update_layout(
            xaxis=dict(tickmode="array", tickvals=[0, 1, 2], ticktext=["A", "B", "C"])
        )
        result = extractor.extract_layout(fig)
        assert result["x_tickvals"] == [0, 1, 2]
        assert result["x_ticktext"] == ["A", "B", "C"]

    def test_y_axis_tickvals(self, extractor: LayoutExtractor) -> None:
        fig = go.Figure()
        fig.update_layout(yaxis=dict(tickmode="array", tickvals=[10, 20], ticktext=["Low", "High"]))
        result = extractor.extract_layout(fig)
        assert result["y_tickvals"] == [10, 20]
        assert result["y_ticktext"] == ["Low", "High"]

    def test_empty_layout_returns_empty(self, extractor: LayoutExtractor) -> None:
        fig = go.Figure()
        result = extractor.extract_layout(fig)
        # No explicit ranges/labels/grids → only keys that have values
        assert "x_range" not in result
        assert "y_range" not in result


class TestLegendExtraction:
    """Test legend settings extraction."""

    def test_extract_legend_position(self, extractor: LayoutExtractor) -> None:
        fig = go.Figure()
        fig.update_layout(legend=dict(x=0.5, y=1.0, xanchor="center", yanchor="bottom"))
        result = extractor.extract_layout(fig)
        assert result["legend"]["x"] == 0.5
        assert result["legend"]["y"] == 1.0
        assert result["legend"]["xanchor"] == "center"
        assert result["legend"]["yanchor"] == "bottom"

    def test_no_legend_returns_empty(self, extractor: LayoutExtractor) -> None:
        fig = go.Figure()
        result = extractor.extract_layout(fig)
        assert "legend" not in result


class TestAnnotationExtraction:
    """Test annotation extraction and Y-label detection."""

    def test_extract_annotations(self, extractor: LayoutExtractor) -> None:
        fig = go.Figure()
        fig.update_layout(
            annotations=[dict(x=0.5, y=0.5, text="Label", showarrow=False, xref="x", yref="y")]
        )
        result = extractor.extract_layout(fig)
        assert "annotations" in result
        assert len(result["annotations"]) == 1
        assert result["annotations"][0]["text"] == "Label"

    def test_annotation_with_font(self, extractor: LayoutExtractor) -> None:
        fig = go.Figure()
        fig.update_layout(
            annotations=[
                dict(
                    x=0.5,
                    y=0.5,
                    text="Bold",
                    showarrow=False,
                    font=dict(size=16, color="red"),
                )
            ]
        )
        result = extractor.extract_layout(fig)
        ann = result["annotations"][0]
        assert ann["font"]["size"] == 16
        assert ann["font"]["color"] == "red"

    def test_ylabel_annotation_detected_and_filtered(self, extractor: LayoutExtractor) -> None:
        """Y-axis label annotation with textangle=-90 is filtered from annotations list.

        Note: y_label is only set in result when layout.yaxis.title is falsy.
        Plotly Title() objects are truthy even when empty, so the annotation is
        filtered out but y_label key may not be set.
        """
        fig = go.Figure()
        fig.update_layout(
            annotations=[
                dict(
                    x=0.01,
                    y=0.5,
                    text="Y Label",
                    textangle=-90,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                )
            ]
        )
        result = extractor.extract_layout(fig)
        # The ylabel-like annotation is filtered from annotations list
        assert len(result.get("annotations", [])) == 0

    def test_annotation_with_textangle(self, extractor: LayoutExtractor) -> None:
        fig = go.Figure()
        fig.update_layout(
            annotations=[dict(x=1.0, y=0.5, text="Rotated", textangle=45, showarrow=False)]
        )
        result = extractor.extract_layout(fig)
        ann = result["annotations"][0]
        assert ann["textangle"] == 45

    def test_annotation_with_anchors(self, extractor: LayoutExtractor) -> None:
        fig = go.Figure()
        fig.update_layout(
            annotations=[
                dict(
                    x=0.5,
                    y=0.5,
                    text="Anchored",
                    xanchor="left",
                    yanchor="top",
                    showarrow=False,
                )
            ]
        )
        result = extractor.extract_layout(fig)
        ann = result["annotations"][0]
        assert ann["xanchor"] == "left"
        assert ann["yanchor"] == "top"


class TestLayoutMapper:
    """Test the static facade."""

    def test_extract_layout_delegates(self) -> None:
        fig = go.Figure()
        fig.update_layout(title="Test")
        result = LayoutMapper.extract_layout(fig)
        assert result["title"] == "Test"

    def test_escape_latex_special_chars(self) -> None:
        assert LayoutMapper._escape_latex("a_b") == r"a\_b"
        assert LayoutMapper._escape_latex("10%") == r"10\%"
        assert LayoutMapper._escape_latex("A&B") == r"A\&B"
        assert LayoutMapper._escape_latex("$x$") == r"\$x\$"
        assert LayoutMapper._escape_latex("#1") == r"\#1"
        assert LayoutMapper._escape_latex("{x}") == r"\{x\}"
        assert LayoutMapper._escape_latex("a~b") == r"a\textasciitilde{}b"
        assert LayoutMapper._escape_latex("a^b") == r"a\^{}b"

    def test_escape_latex_backslash(self) -> None:
        result = LayoutMapper._escape_latex("a\\b")
        assert "textbackslash" in result
