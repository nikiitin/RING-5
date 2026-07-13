"""Tests for the Matplotlib download path (savefig + PGF).

Validates that ``matplotlib_download_bytes`` produces valid image bytes
with correct headers/magic bytes for PDF, PNG, SVG, and PGF formats.
"""

from __future__ import annotations

from collections.abc import Iterator

import matplotlib
import matplotlib.pyplot as plt
import pytest
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from src.core.models.visualization.figure_config import FigureConfig
from src.web.rendering.figure_export import (
    get_matplotlib_extension,
    get_matplotlib_mime,
    matplotlib_download_bytes,
)

matplotlib.use("Agg")


# Fixtures


@pytest.fixture(autouse=True)
def _ensure_agg_backend() -> Iterator[None]:
    """Force Agg backend, disable usetex, and clean up figures.

    Prevents xdist cross-test pollution from changing the backend,
    enabling LaTeX rendering (dvipng not available in CI), or
    leaving stale figures open.
    """
    plt.switch_backend("Agg")
    matplotlib.rcParams["text.usetex"] = False
    yield
    plt.close("all")


@pytest.fixture()
def simple_mpl_figure() -> Figure:
    """A minimal matplotlib figure for export tests."""
    fig, ax = plt.subplots(figsize=(4, 3))
    assert isinstance(ax, Axes)
    ax.bar(["A", "B", "C"], [1, 3, 2])
    ax.set_title("Test")
    assert isinstance(fig, Figure)
    return fig


@pytest.fixture()
def line_mpl_figure() -> Figure:
    """A minimal matplotlib line figure."""
    fig, ax = plt.subplots(figsize=(4, 3))
    assert isinstance(ax, Axes)
    ax.plot([1, 2, 3], [10, 20, 15], label="line")
    assert isinstance(fig, Figure)
    return fig


# PDF tests


class TestMatplotlibPDF:
    """Verify PDF export via savefig."""

    def test_pdf_magic_bytes(self, simple_mpl_figure: Figure) -> None:
        """PDF output starts with %PDF-."""
        data = matplotlib_download_bytes(simple_mpl_figure, "pdf")
        assert data[:5] == b"%PDF-"

    def test_pdf_returns_bytes(self, simple_mpl_figure: Figure) -> None:
        """Return type is bytes, not empty."""
        data = matplotlib_download_bytes(simple_mpl_figure, "pdf")
        assert isinstance(data, bytes)
        assert len(data) > 100


# PNG tests


class TestMatplotlibPNG:
    """Verify PNG export via savefig."""

    def test_png_magic_bytes(self, simple_mpl_figure: Figure) -> None:
        """PNG output starts with the PNG magic header."""
        data = matplotlib_download_bytes(simple_mpl_figure, "png")
        assert data[:4] == b"\x89PNG"

    def test_png_returns_bytes(self, simple_mpl_figure: Figure) -> None:
        """Return type is bytes, not empty."""
        data = matplotlib_download_bytes(simple_mpl_figure, "png")
        assert isinstance(data, bytes)
        assert len(data) > 100

    def test_png_higher_dpi_larger(self, simple_mpl_figure: Figure) -> None:
        """Higher DPI produces more bytes (higher res)."""
        low = matplotlib_download_bytes(simple_mpl_figure, "png", dpi=72)
        high = matplotlib_download_bytes(simple_mpl_figure, "png", dpi=300)
        assert len(high) > len(low)


# SVG tests


class TestMatplotlibSVG:
    """Verify SVG export via savefig."""

    def test_svg_contains_svg_tag(self, simple_mpl_figure: Figure) -> None:
        """SVG output contains <svg."""
        data = matplotlib_download_bytes(simple_mpl_figure, "svg")
        assert b"<svg" in data

    def test_svg_returns_bytes(self, simple_mpl_figure: Figure) -> None:
        """Return type is bytes, not empty."""
        data = matplotlib_download_bytes(simple_mpl_figure, "svg")
        assert isinstance(data, bytes)
        assert len(data) > 100


# PGF tests


@pytest.mark.requires_latex
class TestMatplotlibPGF:
    """Verify PGF export via savefig with PGF backend."""

    def test_pgf_contains_begin_pgfpicture(self, simple_mpl_figure: Figure) -> None:
        r"""PGF output contains \begin{pgfpicture}."""
        data = matplotlib_download_bytes(simple_mpl_figure, "pgf")
        assert b"\\begin{pgfpicture}" in data

    def test_pgf_returns_bytes(self, simple_mpl_figure: Figure) -> None:
        """Return type is bytes, not empty."""
        data = matplotlib_download_bytes(simple_mpl_figure, "pgf")
        assert isinstance(data, bytes)
        assert len(data) > 100

    def test_pgf_with_spec_preamble(self, simple_mpl_figure: Figure) -> None:
        """PGF export uses LaTeX preamble from FigureConfig."""
        spec = FigureConfig(
            latex_extra_preamble="\\usepackage{times}",
        )
        data = matplotlib_download_bytes(simple_mpl_figure, "pgf", spec=spec)
        # Should still produce valid PGF output
        assert b"\\begin{pgfpicture}" in data

    def test_pgf_without_spec(self, simple_mpl_figure: Figure) -> None:
        """PGF export works without a FigureConfig (empty preamble)."""
        data = matplotlib_download_bytes(simple_mpl_figure, "pgf", spec=None)
        assert b"\\begin{pgfpicture}" in data


# Error handling


class TestMatplotlibDownloadErrors:
    """Verify error handling."""

    def test_invalid_format_raises(self, simple_mpl_figure: Figure) -> None:
        """Unsupported format raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported format"):
            matplotlib_download_bytes(simple_mpl_figure, "tiff")  # type: ignore[arg-type]


# Helper functions


class TestMatplotlibHelpers:
    """Verify MIME and extension helpers."""

    def test_mime_pdf(self) -> None:
        assert get_matplotlib_mime("pdf") == "application/pdf"

    def test_mime_pgf(self) -> None:
        assert get_matplotlib_mime("pgf") == "application/x-pgf"

    def test_mime_png(self) -> None:
        assert get_matplotlib_mime("png") == "image/png"

    def test_mime_svg(self) -> None:
        assert get_matplotlib_mime("svg") == "image/svg+xml"

    def test_extension_pdf(self) -> None:
        assert get_matplotlib_extension("pdf") == ".pdf"

    def test_extension_pgf(self) -> None:
        assert get_matplotlib_extension("pgf") == ".pgf"

    def test_extension_png(self) -> None:
        assert get_matplotlib_extension("png") == ".png"

    def test_extension_svg(self) -> None:
        assert get_matplotlib_extension("svg") == ".svg"


# Cross-figure tests


class TestMatplotlibMultipleFigures:
    """Verify export works with different figure types."""

    def test_line_figure_pdf(self, line_mpl_figure: Figure) -> None:
        """Line figure exports to PDF correctly."""
        data = matplotlib_download_bytes(line_mpl_figure, "pdf")
        assert data[:5] == b"%PDF-"

    def test_line_figure_png(self, line_mpl_figure: Figure) -> None:
        """Line figure exports to PNG correctly."""
        data = matplotlib_download_bytes(line_mpl_figure, "png")
        assert data[:4] == b"\x89PNG"
