"""Tests for the Plotly download path (Kaleido v1).

Validates that ``plotly_download_bytes`` produces valid image bytes
with correct headers/magic bytes for PNG, SVG, and PDF formats.
"""

from __future__ import annotations

import plotly.graph_objects as go
import pytest

from src.web.rendering.figure_export import (
    get_plotly_extension,
    get_plotly_mime,
    plotly_download_bytes,
)

pytestmark = pytest.mark.serial

# Fixtures


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


# HTML tests


class TestPlotlyHTML:
    # [test->req~ring5.export.plotly-html~1]
    """Verify self-contained HTML export without Kaleido."""

    def test_html_is_self_contained_and_does_not_invoke_kaleido(
        self, simple_bar_figure: go.Figure
    ) -> None:
        """HTML embeds Plotly and does not require a browser executable."""
        from unittest.mock import patch

        with patch("src.web.rendering.figure_export.kaleido.calc_fig_sync") as mock_calc:
            data = plotly_download_bytes(simple_bar_figure, "html")

        text = data.decode("utf-8")
        assert "<html" in text
        assert "Plotly.newPlot" in text
        assert "plotly.js" in text
        mock_calc.assert_not_called()


# PNG tests


class TestPlotlyPNG:
    # [test->req~ring5.export.plotly-static~1]
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


# SVG tests


class TestPlotlySVG:
    # [test->req~ring5.export.plotly-static~1]
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


# PDF tests


class TestPlotlyPDF:
    # [test->req~ring5.export.plotly-static~1]
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


# Error handling


class TestPlotlyDownloadErrors:
    """Verify error handling."""

    def test_invalid_format_raises(self, simple_bar_figure: go.Figure) -> None:
        """Unsupported format raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported format"):
            plotly_download_bytes(simple_bar_figure, "tiff")  # type: ignore[arg-type]


# Helper functions


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


# Cross-figure tests


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


# Dependency-failure behavior


class TestChromeNotFound:
    # [test->req~ring5.export.plotly-static~1]
    """A missing browser must fail fast with the actionable upstream error."""

    def test_chrome_not_found_propagates_without_retry(self, simple_bar_figure: go.Figure) -> None:
        """ChromeNotFoundError carries install instructions; retrying cannot
        help and wrapping it as a generic RuntimeError buries the fix."""
        from unittest.mock import patch

        from kaleido.errors import ChromeNotFoundError

        with patch(
            "src.web.rendering.figure_export.kaleido.calc_fig_sync",
            side_effect=ChromeNotFoundError("Chrome not found — run kaleido_get_chrome"),
        ) as mock_calc:
            with pytest.raises(ChromeNotFoundError):
                plotly_download_bytes(simple_bar_figure, "png")
            mock_calc.assert_called_once()  # no pointless retries

    def test_transient_failures_still_retry(self, simple_bar_figure: go.Figure) -> None:
        """Non-Chrome failures keep the bounded retry-then-RuntimeError contract."""
        from unittest.mock import patch

        with patch(
            "src.web.rendering.figure_export.kaleido.calc_fig_sync",
            side_effect=TimeoutError("stalled"),
        ) as mock_calc:
            with pytest.raises(RuntimeError, match="after 3 attempts"):
                plotly_download_bytes(simple_bar_figure, "png")
            assert mock_calc.call_count == 3


# Deterministic exports


class TestDeterministicSvg:
    # [test->req~ring5.export.deterministic~1]
    """deterministic=True must yield byte-identical SVG re-exports."""

    def test_bar_svg_deterministic(self, simple_bar_figure: go.Figure) -> None:
        a = plotly_download_bytes(simple_bar_figure, "svg", deterministic=True)
        b = plotly_download_bytes(simple_bar_figure, "svg", deterministic=True)
        assert a == b

    def test_colorbar_heatmap_svg_deterministic(self) -> None:
        """Colorbar gradients embed a SECOND random id (g<uid>-<8hex>) that
        the normalizer must remap — a single-uid replace is not enough."""
        fig = go.Figure(data=go.Heatmap(z=[[1, 2], [3, 4]], showscale=True))
        a = plotly_download_bytes(fig, "svg", deterministic=True)
        b = plotly_download_bytes(fig, "svg", deterministic=True)
        assert a == b

    def test_heatmap_base64_raster_not_corrupted(self) -> None:
        """The uid rewrite is anchored to id contexts, so the base64-embedded
        raster must decode identically with and without normalization."""
        import base64
        import re as _re

        fig = go.Figure(data=go.Heatmap(z=[[i * j for j in range(8)] for i in range(8)]))
        raw = plotly_download_bytes(fig, "svg", deterministic=False)
        norm = plotly_download_bytes(fig, "svg", deterministic=True)

        def _raster(svg: bytes) -> bytes:
            m = _re.search(rb"base64,([A-Za-z0-9+/=]+)", svg)
            assert m is not None, "expected an embedded raster"
            return base64.b64decode(m.group(1))

        # Both exports rasterize the same z-matrix — the PNG payload must
        # be a valid, identical image (normalization never touches it).
        assert _raster(norm) == _raster(raw)
