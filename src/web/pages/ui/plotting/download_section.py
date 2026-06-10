"""Download UI for both rendering engines.

Format pills + ``st.download_button`` wiring for the active engine. The
byte-producing export functions live in the UI-free
``src.web.rendering.figure_export`` module (shared with the public ``ring5``
package); this module is exclusively the Streamlit presentation around them.
"""

from __future__ import annotations

import logging
from typing import cast

import plotly.graph_objects as go
import streamlit as st
from kaleido.errors import ChromeNotFoundError
from matplotlib.figure import Figure as MplFigure

from src.web.rendering.engine_manager import EngineManager
from src.web.rendering.figure_export import (
    MatplotlibFormat,
    PlotlyFormat,
    get_matplotlib_extension,
    get_matplotlib_mime,
    get_plotly_extension,
    get_plotly_mime,
    matplotlib_download_bytes,
    plotly_download_bytes,
)

logger = logging.getLogger(__name__)


# ── UI download section ──────────────────────────────────────────


def render_download_section(
    plot_id: int,
    plot_name: str,
    fig: go.Figure,
) -> None:
    """Engine-aware download controls.

    Shows format pills and a download button appropriate for the
    active rendering engine.

    - **Plotly** → HTML / PNG / SVG / PDF via Kaleido + to_html.
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
        options=["html", "png", "svg", "pdf"],
        default="html",
        key=f"dl_fmt_{plot_id}",
    )
    if fmt is None:
        return

    fmt_typed = cast(PlotlyFormat, fmt)
    try:
        data = plotly_download_bytes(fig, fmt_typed)
    except ChromeNotFoundError as exc:
        logger.error("Plotly %s export failed — no browser for Kaleido: %s", fmt, exc)
        st.warning(
            f"Could not generate the {fmt.upper()} export: no Chrome-family browser "
            "was found for the image renderer. Install one with `kaleido_get_chrome` "
            "(or set BROWSER_PATH), or use the HTML format."
        )
        return
    except Exception as exc:  # never let a download-export failure kill the chart
        logger.error("Plotly %s export failed: %s", fmt, exc)
        st.warning(
            f"Could not generate the {fmt.upper()} export (the image renderer "
            "timed out). Please try again, or use the HTML format."
        )
        return
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

    # Resolved FigureConfig cached by the chart display — PGF reads the
    # user's LaTeX preamble (latex_extra_preamble) from it.
    spec = st.session_state.get(f"plot.{plot_id}.mpl_spec")

    fmt = st.pills(
        "Format",
        options=["pdf", "pgf", "png", "svg"],
        default="pdf",
        key=f"dl_fmt_{plot_id}",
    )
    if fmt is None:
        return

    fmt_typed = cast(MatplotlibFormat, fmt)
    try:
        data = matplotlib_download_bytes(mpl_fig, fmt_typed, spec=spec)
    except ValueError as exc:
        if "raster" in str(exc).lower() and fmt_typed == "pgf":
            st.warning(
                "PGF format does not support raster graphics (e.g. heatmaps). "
                "Falling back to PDF with LaTeX rendering."
            )
            fmt_typed = "pdf"
            data = matplotlib_download_bytes(mpl_fig, fmt_typed, spec=spec)
        else:
            raise
    st.download_button(
        label=f"Download {fmt.upper()}",
        data=data,
        file_name=f"{plot_name}{get_matplotlib_extension(fmt_typed)}",
        mime=get_matplotlib_mime(fmt_typed),
        use_container_width=True,
        key=f"dl_btn_{plot_id}",
    )
