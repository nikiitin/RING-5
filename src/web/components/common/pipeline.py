"""Pipeline component — renders the shaper pipeline editor UI."""

import re
from collections.abc import Callable
from typing import Any, TypedDict

import streamlit as st

from src.core.services.shapers.factory import ShaperFactory


class PipelineExchangeResult(TypedDict):
    """User intent returned by the pipeline exchange controls."""

    import_clicked: bool
    payload: bytes | None
    conflict: str


class PipelineComponent:
    """Renders the data processing pipeline editor.

    Responsible for:
        - "Add transformation" selector + button
        - Reorder (up/down) and delete buttons
        - "Finalize Pipeline" button

    Does NOT apply shapers, modify pipeline state, or trigger reruns.
    """

    # Single source of truth: delegate to ShaperFactory
    SHAPER_DISPLAY_MAP: dict[str, str] = ShaperFactory.get_display_name_map()
    REVERSE_MAP: dict[str, str] = {v: k for k, v in SHAPER_DISPLAY_MAP.items()}

    @staticmethod
    def render_section_header() -> None:
        """Render the pipeline section header."""
        st.markdown("### Data Processing Pipeline")

    @staticmethod
    def render_no_data_warning() -> None:
        """Render a warning when no data is uploaded yet."""
        st.warning("Please upload data first!")

    @staticmethod
    def render_pipeline_label() -> None:
        """Render the 'Current Pipeline' label."""
        st.markdown("**Current Pipeline:**")

    @staticmethod
    def render_exchange(
        plot_id: int,
        default_name: str,
        export_fn: Callable[[str, str], bytes],
    ) -> PipelineExchangeResult:
        """Render human-first versioned pipeline import/export controls.

        Args:
            plot_id: Plot ID for widget key uniqueness.
            default_name: Initial portable configuration name.
            export_fn: Core-facade callback that validates and serializes the
                current pipeline for the chosen name and description.

        Returns:
            Uploaded payload, selected conflict policy, and import intent.
        """
        # [impl->req~ring5.shaping.config-import-export~1]
        with st.expander("Import or export pipeline", expanded=False):
            st.caption(
                "Share this pipeline as a versioned JSON file. Imports are validated before "
                "they are saved or loaded into the editor."
            )
            export_name = st.text_input(
                "Configuration name",
                value=default_name,
                max_chars=80,
                key=f"pipeline_export_name_{plot_id}",
            )
            description = st.text_area(
                "Description",
                value="",
                max_chars=500,
                key=f"pipeline_export_description_{plot_id}",
            )
            try:
                payload = export_fn(export_name, description)
                st.download_button(
                    "Download pipeline configuration",
                    data=payload,
                    file_name=PipelineComponent._download_name(export_name),
                    mime="application/json",
                    key=f"pipeline_export_{plot_id}",
                )
            except (TypeError, ValueError) as exc:
                st.info(f"Complete the pipeline before exporting it: {exc}")

            st.markdown("#### Import")
            uploaded = st.file_uploader(
                "Pipeline configuration JSON",
                type=["json"],
                key=f"pipeline_import_{plot_id}",
                help=(
                    "Accepts RING-5 versioned files and legacy saved configurations "
                    "up to 256 KiB."
                ),
            )
            conflict_options: list[str] = ["error", "rename", "replace"]
            conflict_labels = {
                "error": "Stop and keep both unchanged",
                "rename": "Save as a numbered copy",
                "replace": "Replace the saved configuration",
            }
            conflict: str | None = st.selectbox(
                "If that name already exists",
                conflict_options,
                format_func=lambda value: conflict_labels[value],
                key=f"pipeline_import_conflict_{plot_id}",
            )
            import_clicked = st.button(
                "Import, save, and use",
                disabled=uploaded is None,
                type="primary",
                key=f"pipeline_import_apply_{plot_id}",
            )
        return {
            "import_clicked": import_clicked,
            "payload": uploaded.getvalue() if uploaded is not None else None,
            "conflict": conflict or "error",
        }

    @staticmethod
    def render_import_success(name: str, *, migrated: bool, resolution: str) -> None:
        """Show a concise import result with migration and conflict details."""
        details: list[str] = []
        if migrated:
            details.append("legacy format migrated")
        if resolution != "none":
            details.append(f"name conflict {resolution}")
        suffix = f" ({'; '.join(details)})" if details else ""
        st.success(f"Imported and loaded {name}{suffix}. Finalize to update the plot.")

    @staticmethod
    def render_import_error(message: str) -> None:
        """Show a pipeline import failure without changing the active pipeline."""
        st.error(message)

    @staticmethod
    def _download_name(name: str) -> str:
        """Return a safe, recognizable browser download name."""
        stem = re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip()).strip("-._")
        return f"{stem or 'pipeline'}.ring5-pipeline.json"

    @staticmethod
    def render_add_shaper(plot_id: int) -> dict[str, Any]:
        """Render the 'Add transformation' selector and Add button.

        Args:
            plot_id: Plot ID for widget key uniqueness.

        Returns:
            Dict with ``add_clicked`` and ``shaper_type``.
        """
        col1, col2 = st.columns([3, 1])
        with col1:
            display_type: str | None = st.selectbox(
                "Add transformation",
                list(PipelineComponent.SHAPER_DISPLAY_MAP.keys()),
                key=f"shaper_add_{plot_id}",
            )
        with col2:
            add_clicked: bool = st.button(
                "Add to Pipeline",
                width="stretch",
                key=f"add_shaper_btn_{plot_id}",
            )

        shaper_type: str = PipelineComponent.SHAPER_DISPLAY_MAP.get(
            display_type or "", "columnSelector"
        )
        return {"add_clicked": add_clicked, "shaper_type": shaper_type}

    @staticmethod
    def render_shaper_controls(
        plot_id: int,
        idx: int,
        shaper_type: str,
        is_first: bool,
        is_last: bool,
    ) -> dict[str, bool]:
        """Render up/down/delete controls for a single shaper step.

        Args:
            plot_id: Plot ID for key uniqueness.
            idx: Step index in the pipeline.
            shaper_type: Internal shaper type key.
            is_first: Whether this is the first step.
            is_last: Whether this is the last step.

        Returns:
            Dict with ``move_up``, ``move_down``, ``delete``.
        """
        result: dict[str, bool] = {
            "move_up": False,
            "move_down": False,
            "delete": False,
        }

        c2, c3, c4 = st.columns([1, 1, 1])
        with c2:
            if not is_first:
                result["move_up"] = st.button("Up", key=f"up_{plot_id}_{idx}", type="tertiary")
        with c3:
            if not is_last:
                result["move_down"] = st.button(
                    "Down", key=f"down_{plot_id}_{idx}", type="tertiary"
                )
        with c4:
            result["delete"] = st.button("Del", key=f"del_{plot_id}_{idx}", type="tertiary")

        return result

    @staticmethod
    def render_finalize_button(plot_id: int) -> bool:
        """Render the 'Finalize Pipeline for Plotting' button.

        Args:
            plot_id: Plot ID for key uniqueness.

        Returns:
            True if button was clicked.
        """
        clicked: bool = st.button(
            "Finalize Pipeline for Plotting",
            type="primary",
            width="stretch",
            key=f"finalize_{plot_id}",
        )
        return clicked
