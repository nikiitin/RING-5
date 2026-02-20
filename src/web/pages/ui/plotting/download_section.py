"""Download helpers and UI for both rendering engines.

Byte-producing functions + a thin ``render_download_section()`` that
wires format selection and ``st.download_button`` for the active engine.

**Plotly path**: Uses Kaleido v1 (``fig.to_image()``) for PNG/SVG/PDF.
**Matplotlib path**: Uses ``savefig`` for PDF/PNG/SVG/PGF  (Step 19).
"""

from __future__ import annotations

import io
from typing import Literal, cast

import matplotlib.pyplot as plt
import plotly.graph_objects as go
import streamlit as st
from matplotlib.figure import Figure as MplFigure

from src.core.models.visualization.figure_config import FigureConfig
from src.web.rendering.engine_manager import EngineManager

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
    spec: FigureConfig | None = None,
) -> bytes:
    """Export a matplotlib Figure to image bytes via savefig.

    Args:
        fig: The matplotlib Figure to export.
        fmt: One of ``"pdf"``, ``"pgf"``, ``"png"``, ``"svg"``.
        dpi: Resolution for raster formats (PNG). Ignored by vector formats.
        spec: Optional FigureConfig for PGF preamble extraction.

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


# ── UI download section ──────────────────────────────────────────


def render_download_section(
    plot_id: int,
    plot_name: str,
    fig: go.Figure,
) -> None:
    """Engine-aware download controls.

    Shows format pills and a download button appropriate for the
    active rendering engine.

    - **Plotly** → PNG / SVG / PDF via Kaleido.
    - **Matplotlib** → PDF / PGF / PNG / SVG via savefig.

    Args:
        plot_id: Unique plot identifier (used for widget keys).
        plot_name: Human-readable name used as download filename stem.
        fig: The Plotly figure (used directly for Plotly exports).
    """
    with st.expander("📥 Download", expanded=False):
        if EngineManager.is_matplotlib():
            _render_mpl_download(plot_id, plot_name)
        else:
            _render_plotly_download(plot_id, plot_name, fig)


def _render_plotly_download(
    plot_id: int,
    plot_name: str,
    fig: go.Figure,
) -> None:
    """Format pills + download button for the Plotly/Kaleido path."""
    fmt = st.pills(
        "Format",
        options=["png", "svg", "pdf"],
        default="pdf",
        key=f"dl_fmt_{plot_id}",
    )
    if fmt is None:
        return

    fmt_typed = cast(PlotlyFormat, fmt)
    data = plotly_download_bytes(fig, fmt_typed)
    st.download_button(
        label=f"Download {fmt.upper()}",
        data=data,
        file_name=f"{plot_name}{get_plotly_extension(fmt_typed)}",
        mime=get_plotly_mime(fmt_typed),
        use_container_width=True,
        key=f"dl_btn_{plot_id}",
    )


def _render_mpl_download(plot_id: int, plot_name: str) -> None:
    """Format pills + download button for the Matplotlib path."""
    mpl_fig: MplFigure | None = st.session_state.get(f"plot.{plot_id}.mpl_fig")
    if mpl_fig is None:
        st.warning("No matplotlib figure available for download.")
        return

    fmt = st.pills(
        "Format",
        options=["pdf", "pgf", "png", "svg"],
        default="pdf",
        key=f"dl_fmt_{plot_id}",
    )
    if fmt is None:
        return

    fmt_typed = cast(MatplotlibFormat, fmt)
    data = matplotlib_download_bytes(mpl_fig, fmt_typed)
    st.download_button(
        label=f"Download {fmt.upper()}",
        data=data,
        file_name=f"{plot_name}{get_matplotlib_extension(fmt_typed)}",
        mime=get_matplotlib_mime(fmt_typed),
        use_container_width=True,
        key=f"dl_btn_{plot_id}",
    )
