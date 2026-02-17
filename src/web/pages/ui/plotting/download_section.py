"""Slim download helpers for both rendering engines.

Provides byte-producing functions that the UI download section
calls to generate downloadable files.

**Plotly path**: Uses Kaleido v1 (``fig.to_image()``) for PNG/SVG/PDF.
**Matplotlib path**: Uses ``savefig`` for PDF/PNG/SVG/PGF  (Step 19).
"""

from __future__ import annotations

import io
from typing import Literal

import matplotlib.pyplot as plt
import plotly.graph_objects as go
from matplotlib.figure import Figure as MplFigure

from src.core.visualization.figure_spec import FigureSpec

# ── Type aliases ─────────────────────────────────────────────────

PlotlyFormat = Literal["png", "svg", "pdf"]

_FORMAT_MIME = {
    "png": "image/png",
    "svg": "image/svg+xml",
    "pdf": "application/pdf",
}

_FORMAT_EXT = {
    "png": ".png",
    "svg": ".svg",
    "pdf": ".pdf",
}


# ── Plotly download (Kaleido v1) ─────────────────────────────────


def plotly_download_bytes(
    fig: go.Figure,
    fmt: PlotlyFormat,
    *,
    width: int = 700,
    height: int = 400,
    scale: int = 2,
) -> bytes:
    """Export a Plotly figure to image bytes via Kaleido.

    Args:
        fig: The Plotly figure to export.
        fmt: One of ``"png"``, ``"svg"``, ``"pdf"``.
        width: Image width in pixels (before scale).
        height: Image height in pixels (before scale).
        scale: Resolution multiplier (only affects raster formats).

    Returns:
        Raw bytes of the exported image.

    Raises:
        ValueError: If *fmt* is not a supported format.
    """
    if fmt not in _FORMAT_MIME:
        raise ValueError(
            f"Unsupported format {fmt!r}. " f"Choose from {list(_FORMAT_MIME.keys())}."
        )

    # For vector formats scale has no effect, but the API accepts it.
    raw: bytes = fig.to_image(
        format=fmt,
        width=width,
        height=height,
        scale=scale,
    )
    return raw


def get_plotly_mime(fmt: PlotlyFormat) -> str:
    """Return the MIME type for a Plotly export format."""
    return _FORMAT_MIME[fmt]


def get_plotly_extension(fmt: PlotlyFormat) -> str:
    """Return the file extension (with dot) for a Plotly export format."""
    return _FORMAT_EXT[fmt]


# ── Matplotlib download (savefig + PGF) ──────────────────────────

MatplotlibFormat = Literal["pdf", "pgf", "png", "svg"]

_MPL_FORMAT_MIME = {
    "pdf": "application/pdf",
    "pgf": "application/x-pgf",
    "png": "image/png",
    "svg": "image/svg+xml",
}

_MPL_FORMAT_EXT = {
    "pdf": ".pdf",
    "pgf": ".pgf",
    "png": ".png",
    "svg": ".svg",
}


def matplotlib_download_bytes(
    fig: MplFigure,
    fmt: MatplotlibFormat,
    *,
    dpi: int = 300,
    spec: FigureSpec | None = None,
) -> bytes:
    """Export a matplotlib Figure to image bytes via savefig.

    Args:
        fig: The matplotlib Figure to export.
        fmt: One of ``"pdf"``, ``"pgf"``, ``"png"``, ``"svg"``.
        dpi: Resolution for raster formats (PNG). Ignored by vector formats.
        spec: Optional FigureSpec for PGF preamble extraction.

    Returns:
        Raw bytes of the exported image.

    Raises:
        ValueError: If *fmt* is not a supported format.
    """
    if fmt not in _MPL_FORMAT_MIME:
        raise ValueError(
            f"Unsupported format {fmt!r}. " f"Choose from {list(_MPL_FORMAT_MIME.keys())}."
        )

    buf = io.BytesIO()

    if fmt == "pgf":
        preamble = spec.latex_extra_preamble if spec else ""
        with plt.rc_context(
            {
                "pgf.texsystem": "xelatex",
                "pgf.preamble": preamble,
                "pgf.rcfonts": True,
            }
        ):
            fig.savefig(buf, format="pgf", backend="pgf")
    elif fmt == "pdf":
        fig.savefig(buf, format="pdf", dpi=dpi, bbox_inches="tight")
    elif fmt == "png":
        # rc_context ensures usetex is off – dvipng may not be installed
        # and another caller may have turned it on globally.
        with plt.rc_context({"text.usetex": False}):
            fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", backend="agg")
    elif fmt == "svg":
        fig.savefig(buf, format="svg", bbox_inches="tight")

    buf.seek(0)
    return buf.read()


def get_matplotlib_mime(fmt: MatplotlibFormat) -> str:
    """Return the MIME type for a matplotlib export format."""
    return _MPL_FORMAT_MIME[fmt]


def get_matplotlib_extension(fmt: MatplotlibFormat) -> str:
    """Return the file extension (with dot) for a matplotlib export format."""
    return _MPL_FORMAT_EXT[fmt]
