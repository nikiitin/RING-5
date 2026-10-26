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

from src.web.state.ui_state_manager import WidgetKeyBuilder
from kaleido.errors import ChromeNotFoundError
from matplotlib.figure import Figure as MplFigure

from src.web.models.render_artifact import RenderArtifact
from src.core.models.visualization.export_options import validate_tex_system
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


def _mark_guided_analysis_exported() -> None:
    """Record a real figure-download action for the sidebar workflow."""
    from src.web.components.guided_analysis import GuidedAnalysisComponent

    GuidedAnalysisComponent.mark_exported()


def _record_reported_download(clicked: bool) -> None:
    """Record a click when Streamlit reports it without running the callback."""
    if clicked:
        _mark_guided_analysis_exported()


# UI download section


def render_download_section(
    plot_id: int,
    plot_name: str,
    artifact: RenderArtifact,
) -> None:
    # [impl->req~ring5.workspace.guided-analysis~1]
    # [impl->req~ring5.export.web-download~1]
    """Engine-aware download controls.

    Shows format pills and a download button appropriate for the
    active rendering engine.

    - **Plotly** → HTML / PNG / SVG / PDF via Kaleido + to_html.
    - **Matplotlib** → PDF / PGF / PNG / SVG via savefig.

    Args:
        plot_id: Unique plot identifier (used for widget keys).
        plot_name: Human-readable name used as download filename stem.
        artifact: Published native figure, exact configuration and owned source rows.
    """
    with st.expander("📥 Download", expanded=False):
        if isinstance(artifact.figure, MplFigure):
            _render_mpl_download(plot_id, plot_name, artifact)
        elif isinstance(artifact.figure, go.Figure):
            _render_plotly_download(plot_id, plot_name, artifact)
        else:
            raise TypeError("Downloads require a complete published native artifact.")


def _render_plotly_download(
    plot_id: int,
    plot_name: str,
    artifact: RenderArtifact,
) -> None:
    # [impl->req~ring5.export.plotly-html-source-data~1]
    # [impl->req~ring5.export.web-download~1]
    """Format pills + a deferred download for the Plotly/Kaleido path.

    Image generation is delayed until the user clicks the download button.
    Kaleido can take several seconds to start, so running it during every
    Streamlit rerun would make unrelated controls, such as the engine selector,
    appear unresponsive.
    """
    fig = artifact.figure
    if not isinstance(fig, go.Figure):
        raise TypeError("Plotly downloads require the published Plotly artifact.")
    fmt = st.pills(
        "Format",
        options=["html", "png", "svg", "pdf"],
        default="html",
        key=WidgetKeyBuilder.plot_key(plot_id, "widgets.dl_fmt"),
    )
    if fmt is None:
        return

    fmt_typed = cast(PlotlyFormat, fmt)
    # Honor the figure's configured size (Kaleido's defaults otherwise override
    # fig.layout.width/height, exporting every download at 700x400).
    width = int(fig.layout.width) if fig.layout.width else 700
    height = int(fig.layout.height) if fig.layout.height else 400

    def generate_download() -> bytes:
        """Generate the selected export in Streamlit's download worker."""
        try:
            return plotly_download_bytes(
                fig,
                fmt_typed,
                width=width,
                height=height,
                scale=artifact.config.get("export_scale", 1),
                source_data=artifact.source_data,
            )
        except ChromeNotFoundError as exc:
            logger.error("Plotly %s export failed — no browser for Kaleido: %s", fmt, exc)
            raise RuntimeError(
                f"Could not generate the {fmt.upper()} export because no Chrome-family "
                "browser was found. Run `ring5 install-chrome` and set "
                "BROWSER_PATH to its printed path, or use the HTML format."
            ) from exc
        except Exception as exc:
            logger.error("Plotly %s export failed: %s", fmt, exc)
            raise RuntimeError(
                f"Could not generate the {fmt.upper()} export. Please try again or use "
                "the HTML format."
            ) from exc

    downloaded = st.download_button(
        label=f"Download {fmt.upper()}",
        data=generate_download,
        file_name=f"{plot_name}{get_plotly_extension(fmt_typed)}",
        mime=get_plotly_mime(fmt_typed),
        on_click=_mark_guided_analysis_exported,
        width="stretch",
        key=WidgetKeyBuilder.plot_key(plot_id, "widgets.dl_btn"),
    )
    _record_reported_download(downloaded)


def _render_mpl_download(plot_id: int, plot_name: str, artifact: RenderArtifact) -> None:
    # [impl->req~ring5.export.matplotlib-pgf~1]
    # [impl->req~ring5.export.web-download~1]
    """Format pills + download button for the Matplotlib path."""
    mpl_fig = artifact.figure
    if not isinstance(mpl_fig, MplFigure):
        raise TypeError("Matplotlib downloads require the published native artifact.")
    compiler = validate_tex_system(artifact.config.get("tex_system", "xelatex"))

    fmt = st.pills(
        "Format",
        options=["pdf", "pgf", "png", "svg"],
        default="pdf",
        key=WidgetKeyBuilder.plot_key(plot_id, "widgets.dl_fmt"),
    )
    if fmt is None:
        return

    fmt_typed = cast(MatplotlibFormat, fmt)
    try:
        data = matplotlib_download_bytes(mpl_fig, fmt_typed, tex_system=compiler)
    except ValueError as exc:
        if "raster" in str(exc).lower() and fmt_typed == "pgf":
            st.warning(
                "PGF format does not support raster graphics (e.g. heatmaps). "
                "Falling back to PDF."
            )
            fmt_typed = "pdf"
            data = matplotlib_download_bytes(mpl_fig, fmt_typed, tex_system=compiler)
        else:
            raise
    downloaded = st.download_button(
        label=f"Download {fmt_typed.upper()}",
        data=data,
        file_name=f"{plot_name}{get_matplotlib_extension(fmt_typed)}",
        mime=get_matplotlib_mime(fmt_typed),
        on_click=_mark_guided_analysis_exported,
        width="stretch",
        key=WidgetKeyBuilder.plot_key(plot_id, "widgets.dl_btn"),
    )
    _record_reported_download(downloaded)
