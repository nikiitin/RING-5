"""Tests for the Plotly download path (Kaleido v1).

Validates that ``plotly_download_bytes`` produces valid image bytes
with correct headers/magic bytes for PNG, SVG, and PDF formats.
"""

from __future__ import annotations

import plotly.graph_objects as go
import pytest

from src.web.pages.ui.plotting.download_section import (
    get_plotly_extension,
    get_plotly_mime,
    plotly_download_bytes,
)

# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture()
def simple_bar_figure() -> go.Figure:
    """A minimal Plotly bar figure for export tests."""
    fig = go.Figure(
        data=[
            go.Bar(
                x=["A", "B", "C"],
                y=[1, 3, 2],
                name="series",
            )
        ]
    )
    fig.update_layout(width=300, height=200, title="Test")
    return fig


@pytest.fixture()
def simple_line_figure() -> go.Figure:
    """A minimal Plotly line figure for export tests."""
    fig = go.Figure(
        data=[
            go.Scatter(
                x=[1, 2, 3],
                y=[10, 20, 15],
                mode="lines",
                name="line",
            )
        ]
    )
    fig.update_layout(width=300, height=200)
    return fig


# ── PNG tests ────────────────────────────────────────────────────


class TestPlotlyPNG:
    """Verify PNG export via Kaleido."""

    def test_png_magic_bytes(self, simple_bar_figure: go.Figure) -> None:
        """PNG output starts with the PNG magic header."""
        data = plotly_download_bytes(simple_bar_figure, "png")
        assert data[:4] == b"\x89PNG"

    def test_png_returns_bytes(self, simple_bar_figure: go.Figure) -> None:
        """Return type is bytes, not empty."""
        data = plotly_download_bytes(simple_bar_figure, "png")
        assert isinstance(data, bytes)
        assert len(data) > 100

    def test_png_scale_produces_larger(self, simple_bar_figure: go.Figure) -> None:
        """Higher scale factor produces more bytes (higher res)."""
        small = plotly_download_bytes(simple_bar_figure, "png", scale=1)
        large = plotly_download_bytes(simple_bar_figure, "png", scale=3)
        assert len(large) > len(small)


# ── SVG tests ────────────────────────────────────────────────────


class TestPlotlySVG:
    """Verify SVG export via Kaleido."""

    def test_svg_starts_with_xml_or_svg(self, simple_bar_figure: go.Figure) -> None:
        """SVG output starts with <svg or <?xml."""
        data = plotly_download_bytes(simple_bar_figure, "svg")
        text = data.decode("utf-8")
        assert text.startswith("<svg") or text.startswith("<?xml")

    def test_svg_returns_bytes(self, simple_bar_figure: go.Figure) -> None:
        """Return type is bytes, not empty."""
        data = plotly_download_bytes(simple_bar_figure, "svg")
        assert isinstance(data, bytes)
        assert len(data) > 100

    def test_svg_contains_svg_tag(self, simple_bar_figure: go.Figure) -> None:
        """SVG contains an <svg> element."""
        data = plotly_download_bytes(simple_bar_figure, "svg")
        assert b"<svg" in data


# ── PDF tests ────────────────────────────────────────────────────


class TestPlotlyPDF:
    """Verify PDF export via Kaleido."""

    def test_pdf_magic_bytes(self, simple_bar_figure: go.Figure) -> None:
        """PDF output starts with %PDF-."""
        data = plotly_download_bytes(simple_bar_figure, "pdf")
        assert data[:5] == b"%PDF-"

    def test_pdf_returns_bytes(self, simple_bar_figure: go.Figure) -> None:
        """Return type is bytes, not empty."""
        data = plotly_download_bytes(simple_bar_figure, "pdf")
        assert isinstance(data, bytes)
        assert len(data) > 100


# ── Error handling ───────────────────────────────────────────────


class TestPlotlyDownloadErrors:
    """Verify error handling."""

    def test_invalid_format_raises(self, simple_bar_figure: go.Figure) -> None:
        """Unsupported format raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported format"):
            plotly_download_bytes(simple_bar_figure, "tiff")  # type: ignore[arg-type]


# ── Helper functions ─────────────────────────────────────────────


class TestPlotlyHelpers:
    """Verify MIME and extension helpers."""

    def test_mime_png(self) -> None:
        assert get_plotly_mime("png") == "image/png"

    def test_mime_svg(self) -> None:
        assert get_plotly_mime("svg") == "image/svg+xml"

    def test_mime_pdf(self) -> None:
        assert get_plotly_mime("pdf") == "application/pdf"

    def test_extension_png(self) -> None:
        assert get_plotly_extension("png") == ".png"

    def test_extension_svg(self) -> None:
        assert get_plotly_extension("svg") == ".svg"

    def test_extension_pdf(self) -> None:
        assert get_plotly_extension("pdf") == ".pdf"


# ── Cross-figure tests ──────────────────────────────────────────


class TestPlotlyMultipleFigures:
    """Verify export works with different figure types."""

    def test_line_figure_png(self, simple_line_figure: go.Figure) -> None:
        """Line figure exports to PNG correctly."""
        data = plotly_download_bytes(simple_line_figure, "png")
        assert data[:4] == b"\x89PNG"

    def test_line_figure_svg(self, simple_line_figure: go.Figure) -> None:
        """Line figure exports to SVG correctly."""
        data = plotly_download_bytes(simple_line_figure, "svg")
        assert b"<svg" in data
