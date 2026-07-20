"""Human-first controls for copying plot settings and pipelines."""

from __future__ import annotations

import copy
from collections.abc import Sequence
from typing import Any, Protocol

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.core.models.visualization.plot_transfer_result import PlotTransferMode


class _TransferPlot(Protocol):
    plot_id: int
    name: str
    plot_type: str
    config: dict[str, Any]


_MODE_LABELS: dict[PlotTransferMode, str] = {
    "settings": "Selected figure settings",
    "configuration": "Complete plot configuration",
    "pipeline": "Shaping pipeline",
}
_SECTION_LABELS: dict[str, str] = {
    "labels": "Titles and labels",
    "layout": "Layout and dimensions",
    "typography": "Typography",
    "axes": "Axes and ordering",
    "legends": "Legends",
    "colors": "Colors and series styles",
    "annotations": "Annotations and data labels",
}


class PlotTransferPanel:
    """Render an explicit source-to-current-plot copy workflow."""

    def __init__(self, api: ApplicationAPI) -> None:
        self._api = api

    @staticmethod
    def _reset_target_widgets(plot_id: int) -> None:
        """Drop stale widget values so copied configuration becomes the next default."""
        suffix = f"_{plot_id}"
        prefix = f"plot.{plot_id}."
        for key in list(st.session_state):
            if isinstance(key, str) and (key.endswith(suffix) or key.startswith(prefix)):
                st.session_state.pop(key, None)

    @staticmethod
    def apply_pending_widget_reset(plot_id: int) -> None:
        """Apply a reset requested by the previous transfer-button rerun."""
        reset_key = f"plot_transfer_reset_{plot_id}"
        copied_config = st.session_state.pop(reset_key, None)
        if not isinstance(copied_config, dict):
            return
        PlotTransferPanel._reset_target_widgets(plot_id)
        for config_key in ("title", "xlabel", "ylabel", "legend_title", "x", "y", "color"):
            if config_key in copied_config:
                st.session_state[f"{config_key}_{plot_id}"] = copy.deepcopy(
                    copied_config[config_key]
                )

    def render(self, target: _TransferPlot, plots: Sequence[_TransferPlot]) -> None:
        # [impl->req~ring5.plots.copy-settings-pipeline~1]
        """Offer compatible transfer modes when another plot is available."""
        with st.expander(":material/content_copy: Copy from another plot", expanded=False):
            notice_key = f"plot_transfer_notice_{target.plot_id}"
            notice = st.session_state.pop(notice_key, None)
            if notice:
                st.success(str(notice))
            sources = [plot for plot in plots if plot.plot_id != target.plot_id]
            if not sources:
                st.info("Create another plot before copying settings or a pipeline.")
                return

            by_id = {plot.plot_id: plot for plot in sources}
            source_id = st.selectbox(
                "Copy from",
                options=list(by_id),
                format_func=lambda value: f"{by_id[value].name} ({by_id[value].plot_type})",
                key=f"plot_transfer_source_{target.plot_id}",
            )
            mode_label = st.radio(
                "What to copy",
                options=list(_MODE_LABELS.values()),
                horizontal=True,
                key=f"plot_transfer_mode_{target.plot_id}",
            )
            mode = next(key for key, label in _MODE_LABELS.items() if label == mode_label)
            sections: list[str] = []
            if mode == "settings":
                selected_labels = st.multiselect(
                    "Figure sections",
                    options=list(_SECTION_LABELS.values()),
                    default=["Titles and labels", "Typography", "Colors and series styles"],
                    key=f"plot_transfer_sections_{target.plot_id}",
                )
                sections = [
                    key for key, label in _SECTION_LABELS.items() if label in selected_labels
                ]
                st.caption("Data columns and plot type are never changed by a selective copy.")
            elif mode == "configuration":
                st.caption("Available only between the same plot type with compatible columns.")
            else:
                st.caption(
                    "The destination will need Finalize Pipeline for Plotting before it can render."
                )

            if st.button(
                "Copy into current plot",
                type="primary",
                key=f"plot_transfer_apply_{target.plot_id}",
            ):
                try:
                    result = self._api.copy_plot_content(
                        int(source_id), target.plot_id, mode, sections=sections
                    )
                except (TypeError, ValueError) as exc:
                    st.error(str(exc))
                    return
                if result.requires_finalize:
                    notice = (
                        f"Copied {result.pipeline_steps} pipeline steps. "
                        "Finalize the pipeline next."
                    )
                else:
                    notice = f"Copied {len(result.copied_keys)} configuration values."
                st.session_state[notice_key] = notice
                st.session_state[f"plot_transfer_reset_{target.plot_id}"] = copy.deepcopy(
                    target.config
                )
                st.rerun()


__all__ = ["PlotTransferPanel"]
