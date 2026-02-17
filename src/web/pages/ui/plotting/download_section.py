"""Slim download helpers for both rendering engines.

Provides byte-producing functions that the UI download section
calls to generate downloadable files.

**Plotly path**: Uses Kaleido v1 (``fig.to_image()``) for PNG/SVG/PDF.
**Matplotlib path**: Uses ``savefig`` for PDF/PNG/SVG/PGF  (Step 19).
"""

from __future__ import annotations

from typing import Literal

import plotly.graph_objects as go

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
