"""
Plot Export Service
Handles exporting Plotly figures to static formats (PNG, PDF, SVG).
Encapsulates Kaleido dependency and Matplotlib fallback logic.
"""

import io
import logging
from typing import Any, Dict

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting plots to various formats."""

    @staticmethod
    def render_download_button(
        plot_name: str,
        plot_id: int,
        fig: go.Figure,
        config: Dict[str, Any],
        key_prefix: str = "dl_btn",
    ) -> None:
        """
        Render a Streamlit download button for the plot.

        Args:
            plot_name: Name of the plot (for filename)
            plot_id: ID of the plot (for unique keys)
            fig: Plotly figure to export
            config: Plot configuration
            key_prefix: Prefix for Streamlit widget keys
        """
        download_format = config.get("download_format", "html")

        if download_format == "html":
            ExportService._render_html_download(plot_name, fig)
        elif download_format in ["png", "pdf", "svg"]:
            ExportService._render_static_download(
                plot_name, plot_id, fig, config, download_format, key_prefix
            )

    @staticmethod
    def _render_html_download(plot_name: str, fig: go.Figure) -> None:
        """Render download button for HTML format."""
        html_str = pio.to_html(fig, include_plotlyjs=True)
        st.download_button(
            label="Download Interactive HTML",
            data=html_str,
            file_name=f"{plot_name}.html",
            mime="text/html",
        )

    @staticmethod
    def _render_static_download(
        plot_name: str,
        plot_id: int,
        fig: go.Figure,
        config: Dict[str, Any],
        fmt: str,
        key_prefix: str,
    ) -> None:
        """Render download button for static formats with fallback."""
        try:
            # Attempt High-Fidelity Export (Kaleido)
            buf = ExportService._export_with_kaleido(fig, fmt, config)
            mime = ExportService._get_mime_type(fmt)

            st.download_button(
                label=f"Download {fmt.upper()} (High Res)",
                data=buf,
                file_name=f"{plot_name}.{fmt}",
                mime=mime,
                key=f"{key_prefix}_{plot_id}_{fmt}_hires",
            )

        except Exception as e:
            # Fallback to Matplotlib
            _log_export_error(e)
            ExportService._render_matplotlib_fallback(
                plot_name, plot_id, fig, config, fmt, key_prefix
            )

    @staticmethod
    def _export_with_kaleido(fig: go.Figure, fmt: str, config: Dict[str, Any]) -> io.BytesIO:
        """Attempt export using Kaleido engine."""
        import kaleido  # noqa: F401

        buf = io.BytesIO()
        scale = config.get("export_scale", 1)
        fig.write_image(buf, format=fmt, scale=scale)
        buf.seek(0)
        return buf

    @staticmethod
    def _render_matplotlib_fallback(
        plot_name: str,
        plot_id: int,
        fig: go.Figure,
        config: Dict[str, Any],
        fmt: str,
        key_prefix: str,
    ) -> None:
        """Render download button using Matplotlib backup renderer."""
        st.warning("High-fidelity export failed, using fallback renderer.")

        try:
            buf = ExportService._convert_to_matplotlib(fig, config, fmt)
            mime = ExportService._get_mime_type(fmt)

            st.download_button(
                label=f"Download {fmt.upper()}",
                data=buf,
                file_name=f"{plot_name}.{fmt}",
                mime=mime,
                key=f"{key_prefix}_{plot_id}_{fmt}_fallback",
            )
        except Exception as e:
            st.error(f"Failed to generate {fmt.upper()}: {e}")
            st.info("HTML download is always available as a fallback")

    @staticmethod
    def _convert_to_matplotlib(fig: go.Figure, config: Dict[str, Any], fmt: str) -> io.BytesIO:
        """Convert Plotly figure to Matplotlib for backup export."""
        import matplotlib.pyplot as plt

        # Extract dimensions
        width_inches = config.get("width", 800) / 100
        height_inches = config.get("height", 500) / 100

        mpl_fig = plt.figure(figsize=(width_inches, height_inches))
        ax = mpl_fig.add_subplot(111)

        # Naive Trace Extraction (Fallback only)
        for trace in fig.data:
            if trace.type in ["bar", "scatter"]:
                x = trace.x
                y = trace.y
                label = trace.name or ""

                if trace.type == "bar":
                    if x is not None:
                        ax.bar(range(len(x)), y, label=label, alpha=0.7)
                else:  # scatter/line
                    ax.plot(x, y, label=label, marker="o")

        ax.set_title(config.get("title", ""))
        ax.set_xlabel(config.get("xlabel", ""))
        ax.set_ylabel(config.get("ylabel", ""))

        if len(fig.data) > 1:
            ax.legend()
        ax.grid(True, alpha=0.3)

        buf = io.BytesIO()
        if fmt == "png":
            mpl_fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        else:
            mpl_fig.savefig(buf, format="pdf", bbox_inches="tight")

        plt.close(mpl_fig)
        buf.seek(0)
        return buf

    @staticmethod
    def _get_mime_type(fmt: str) -> str:
        """Get MIME type for format."""
        mime_map = {
            "pdf": "application/pdf",
            "png": "image/png",
            "svg": "image/svg+xml",
        }
        return mime_map.get(fmt, "application/octet-stream")


def _log_export_error(e: Exception) -> None:
    """Log export failures appropriately."""
    if "kaleido" in str(e) or isinstance(e, ImportError):
        logger.warning(f"Kaleido export failed: {e}")
    else:
        logger.warning(f"High-fidelity export exception: {e}")
