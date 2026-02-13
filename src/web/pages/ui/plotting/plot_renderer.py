"""Plot rendering utilities with intelligent figure caching."""

import hashlib
import json
from typing import Any, Dict, Optional, Union

import pandas as pd
import streamlit as st

from src.core.performance import get_plot_cache, timed
from src.web.pages.ui.components.interactive_plot import interactive_plotly_chart
from src.web.pages.ui.plotting.export import LaTeXExportService
from src.web.pages.ui.plotting.export.presets.preset_schema import LaTeXPreset

from .base_plot import BasePlot


class PlotRenderer:
    """Handles rendering plots and their UI elements with intelligent caching."""

    @staticmethod
    def _compute_figure_cache_key(plot_id: int, config: Dict[str, Any], data_hash: str) -> str:
        """
        Compute stable cache key for plot figure.

        Uses config hash + data hash to detect when regeneration is needed.
        Ignores transient UI state (legend positions, etc.).

        Args:
            plot_id: Unique plot identifier
            config: Plot configuration dict
            data_hash: Hash of the processed data

        Returns:
            Cache key string
        """
        # Filter out transient config that shouldn't invalidate cache
        cache_relevant_config = {
            k: v
            for k, v in config.items()
            if k
            not in {
                "xaxis_range",
                "yaxis_range",  # User zoom/pan state
            }
        }

        # Create stable JSON representation of config
        config_json = json.dumps(cache_relevant_config, sort_keys=True, default=str)
        config_hash = hashlib.md5(config_json.encode(), usedforsecurity=False).hexdigest()[:8]

        return f"plot_{plot_id}_{config_hash}_{data_hash}"

    @staticmethod
    def _compute_data_hash(data: pd.DataFrame) -> str:
        """
        Compute fast hash of DataFrame for cache invalidation.

        Uses shape + first/last row hashes for speed.

        Args:
            data: DataFrame to hash

        Returns:
            Hash string
        """
        # Fast fingerprint: shape + sample of data
        shape_str = f"{data.shape[0]}x{data.shape[1]}"

        # Hash first and last rows for change detection
        if len(data) > 0:
            first_row = str(data.iloc[0].values.tolist())
            last_row = str(data.iloc[-1].values.tolist())
            columns = str(data.columns.tolist())

            content = f"{shape_str}|{columns}|{first_row}|{last_row}"
        else:
            content = shape_str

        return hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()[:12]

    @staticmethod
    def render_legend_customization(
        plot: BasePlot, data: pd.DataFrame, config: Dict[str, Any]
    ) -> Optional[Dict[str, str]]:
        """
        Render legend customization UI.

        Args:
            plot: Plot instance
            data: The data being plotted
            config: Current plot configuration

        Returns:
            Dictionary mapping original values to custom labels, or None
        """
        legend_col = plot.get_legend_column(config)

        if not legend_col:
            return None

        unique_vals = data[legend_col].unique().tolist()

        st.markdown("**Custom Legend Labels**")
        st.caption("Customize the legend labels for each value (leave blank to keep original)")

        # Initialize per-column legend mappings storage if not exists
        if not plot.legend_mappings_by_column:
            plot.legend_mappings_by_column = {}

        # Get existing mappings for this column
        existing_mappings = plot.legend_mappings_by_column.get(legend_col, {})
        legend_labels = {}

        # Create input fields for each unique value
        for val in unique_vals:
            default_value = existing_mappings.get(str(val), str(val))
            custom_label = st.text_input(
                f"Label for '{val}'",
                value=default_value,
                key=f"legend_label_{plot.plot_id}_{legend_col}_{val}",
                label_visibility="visible",
            )
            # Only add to mapping if user provided a value
            if custom_label and custom_label.strip():
                legend_labels[str(val)] = custom_label.strip()
            else:
                legend_labels[str(val)] = str(val)

        # Store mappings for THIS column specifically
        plot.legend_mappings_by_column[legend_col] = legend_labels

        # Also update the global legend_mappings for backward compatibility
        plot.legend_mappings = legend_labels

        return legend_labels

    @staticmethod
    @timed
    def render_plot(plot: BasePlot, should_generate: bool = False) -> None:
        """
        Render the plot visualization with intelligent figure caching.

        Performance: Uses config+data hash to cache generated figures.
        Only regenerates when config or data actually changes.

        Args:
            plot: Plot instance
            should_generate: Whether to force regeneration (bypasses cache)
        """
        if plot.processed_data is None:
            return

        # Compute cache key from config + data fingerprint
        data_hash = PlotRenderer._compute_data_hash(plot.processed_data)
        cache_key = PlotRenderer._compute_figure_cache_key(plot.plot_id, plot.config, data_hash)

        # Try cache first (unless forced regeneration)
        cache = get_plot_cache()
        if not should_generate and plot.last_generated_fig is None:
            cached_fig = cache.get(cache_key)
            if cached_fig is not None:
                plot.last_generated_fig = cached_fig

        # 1. Generate Figure if needed (Forced OR Cache Missing)
        if should_generate or plot.last_generated_fig is None:
            try:
                fig = plot.create_figure(plot.processed_data, plot.config)
                fig = plot.apply_common_layout(fig, plot.config)

                # Apply legend labels
                legend_labels = plot.config.get("legend_labels")
                if legend_labels:
                    fig = plot.apply_legend_labels(fig, legend_labels)

                # Store and cache the figure
                plot.last_generated_fig = fig
                cache.set(cache_key, fig)
            except Exception as e:
                st.error(f"Error generating plot: {e}")
                return

        # 2. Render if we have a figure
        if plot.last_generated_fig is not None:
            try:
                fig = plot.last_generated_fig

                # Reconstruct config for interactivity
                # Enforce editable=True (scoped) to allow legend dragging
                # but restrict other edits via 'edits' if needed in future
                plotly_config = {
                    "responsive": False,
                    "editable": True,  # Required for legend dragging
                    "edits": {
                        "legendPosition": True,
                        "titleText": False,
                        "axisTitleText": False,
                        "annotationText": False,
                        "colorbarTitleText": False,
                    },
                    "modeBarButtonsToAdd": [
                        "drawline",
                        "drawopenpath",
                        "drawclosedpath",
                        "drawcircle",
                        "drawrect",
                        "eraseshape",
                    ],
                    "toImageButtonOptions": {
                        "format": "svg",
                        "filename": f"{plot.name}_view",
                        "height": plot.config.get("height", 500),
                        "width": plot.config.get("width", 800),
                        "scale": plot.config.get("export_scale", 1),
                    },
                }

                relayout_data = interactive_plotly_chart(
                    fig, config=plotly_config, key=f"chart_{plot.plot_id}"
                )

                # Update backend config if user interacted
                if relayout_data:
                    # Prevent infinite loops by checking if we already processed this exact event
                    last_event_key = f"last_relayout_{plot.plot_id}"
                    last_event = st.session_state.get(last_event_key)

                    if relayout_data != last_event:
                        if plot.update_from_relayout(relayout_data):
                            st.session_state[last_event_key] = relayout_data
                            st.rerun()

                # Download button
                PlotRenderer._render_download_button(plot, fig)

            except Exception as e:
                st.error(f"Error generating plot: {e}")
                # Explicit error is better for debugging main loop

    @staticmethod
    def _render_download_button(plot: BasePlot, fig: Any) -> None:
        """
        Render export dialog for publication-quality LaTeX export.

        Provides dropdown selection for journal presets and format,
        then generates downloadable file using MatplotlibConverter.

        Args:
            plot: Plot instance
            fig: Plotly figure with user's interactive adjustments
        """
        with st.expander("📥 Export for LaTeX", expanded=False):
            st.markdown("**Publication-Quality Export**")
            st.caption(
                "Export to LaTeX-optimized formats. "
                "Preserves your legend positions, zoom, and layout adjustments."
            )

            # Initialize service
            service = LaTeXExportService()
            presets = service.list_presets()

            # UI for export settings
            col1, col2 = st.columns(2)

            with col1:
                # Load saved preset if available
                saved_preset_name = None
                if "export_preset" in plot.config:
                    # If it's a dict, try to identify which preset it came from
                    if isinstance(plot.config["export_preset"], dict):
                        # Use the saved preset directly
                        saved_preset_name = "custom"
                    else:
                        saved_preset_name = plot.config.get("export_preset")

                # Find index of saved preset or default to 0
                default_index = 0
                if saved_preset_name and saved_preset_name in presets:
                    default_index = presets.index(saved_preset_name)

                preset_name = st.selectbox(
                    "Journal Preset",
                    options=presets,
                    index=default_index,
                    help="Select journal/conference column width preset",
                    key=f"export_preset_{plot.plot_id}",
                )

            with col2:
                # Load saved format if available
                saved_format = plot.config.get("export_format", "pdf")
                format_index = (
                    ["pdf", "pgf", "eps"].index(saved_format)
                    if saved_format in ["pdf", "pgf", "eps"]
                    else 0
                )

                format_choice = st.selectbox(
                    "Export Format",
                    options=["pdf", "pgf", "eps"],
                    index=format_index,
                    help=(
                        "• PDF: Recommended for most use cases\n"
                        "• PGF: Best for direct LaTeX inclusion\n"
                        "• EPS: Legacy format"
                    ),
                    key=f"export_format_{plot.plot_id}",
                )

            # Load preset info for preview and advanced settings
            preset_info = service.get_preset_info(preset_name)

            # Merge saved export overrides (from portfolio) into preset defaults
            # so that sliders restore the user's previous customizations
            saved_export = plot.config.get("export_preset")
            if isinstance(saved_export, dict):
                effective_defaults: Dict[str, Any] = {**preset_info, **saved_export}
            else:
                effective_defaults = dict(preset_info)

            # Initialize preset to use (default to preset name)
            preset_to_use: Union[str, LaTeXPreset] = preset_name

            # Advanced settings for export dimensions
            with st.expander("📏 Advanced: Export Dimensions", expanded=False):
                st.caption("Override export figure size (optional)")

                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    export_width = st.slider(
                        "Width (inches)",
                        min_value=1.0,
                        max_value=12.0,
                        value=float(effective_defaults["width_inches"]),
                        step=0.25,
                        help="Figure width in inches for export",
                        key=f"export_width_{plot.plot_id}",
                    )
                with col_d2:
                    export_height = st.slider(
                        "Height (inches)",
                        min_value=1.0,
                        max_value=10.0,
                        value=float(effective_defaults["height_inches"]),
                        step=0.25,
                        help="Figure height in inches for export",
                        key=f"export_height_{plot.plot_id}",
                    )

                # Apply custom dimensions to preset
                if (
                    export_width != preset_info["width_inches"]
                    or export_height != preset_info["height_inches"]
                ):
                    if isinstance(preset_to_use, str):
                        preset_to_use = preset_info.copy()
                    else:
                        preset_to_use = preset_to_use.copy()
                    preset_to_use["width_inches"] = export_width
                    preset_to_use["height_inches"] = export_height
                    st.info("✏️ Using custom dimensions")

            # Advanced settings for legend spacing
            with st.expander("⚙️ Advanced: Legend Spacing", expanded=False):
                st.caption("Customize legend appearance (optional)")

                col_a, col_b = st.columns(2)
                with col_a:
                    col_spacing = st.slider(
                        "Column Spacing",
                        min_value=-1.0,
                        max_value=2.0,
                        value=effective_defaults["legend_columnspacing"],
                        step=0.1,
                        help="Space between legend columns (negative = overlap)",
                        key=f"legend_colspace_{plot.plot_id}",
                    )
                    label_spacing = st.slider(
                        "Item Spacing",
                        min_value=-0.5,
                        max_value=1.0,
                        value=effective_defaults["legend_labelspacing"],
                        step=0.05,
                        help="Vertical space between legend items (negative = tighter)",
                        key=f"legend_labelspace_{plot.plot_id}",
                    )
                    box_length = st.slider(
                        "Color Box Length",
                        min_value=0.5,
                        max_value=3.0,
                        value=effective_defaults["legend_handlelength"],
                        step=0.1,
                        help="Length of color indicator boxes",
                        key=f"legend_boxlen_{plot.plot_id}",
                    )

                with col_b:
                    text_pad = st.slider(
                        "Box-Text Spacing",
                        min_value=-0.5,
                        max_value=1.5,
                        value=effective_defaults["legend_handletextpad"],
                        step=0.05,
                        help="Space between color box and label text (negative = overlap)",
                        key=f"legend_textpad_{plot.plot_id}",
                    )
                    border_pad = st.slider(
                        "Border Padding",
                        min_value=-0.5,
                        max_value=1.0,
                        value=effective_defaults["legend_borderpad"],
                        step=0.05,
                        help="Space inside legend border (negative = tighter)",
                        key=f"legend_borderpad_{plot.plot_id}",
                    )
                    legend_ncol = st.slider(
                        "Legend Columns",
                        min_value=0,
                        max_value=6,
                        value=int(effective_defaults.get("legend_ncol", 0)),
                        step=1,
                        help="Number of columns in the export legend (0 = auto)",
                        key=f"legend_ncol_{plot.plot_id}",
                    )

                st.markdown("---")
                st.caption("Legend Position Override")
                legend_custom_pos = st.checkbox(
                    "Use custom legend position",
                    value=bool(effective_defaults.get("legend_custom_pos", False)),
                    help=(
                        "Enable to manually set legend X/Y coordinates. "
                        "When off, matplotlib places the legend automatically."
                    ),
                    key=f"legend_custom_pos_{plot.plot_id}",
                )
                if legend_custom_pos:
                    col_lp1, col_lp2 = st.columns(2)
                    with col_lp1:
                        legend_x_val = st.slider(
                            "Legend X Position",
                            min_value=-1.0,
                            max_value=1.3,
                            value=float(effective_defaults.get("legend_x", 0.0)),
                            step=0.05,
                            help="X position of legend (-1=far left, 0=left edge, 1=right edge)",
                            key=f"legend_x_{plot.plot_id}",
                        )
                    with col_lp2:
                        legend_y_val = st.slider(
                            "Legend Y Position",
                            min_value=-1.0,
                            max_value=1.3,
                            value=float(effective_defaults.get("legend_y", 1.0)),
                            step=0.05,
                            help="Y position of legend (0=bottom, 1=top)",
                            key=f"legend_y_{plot.plot_id}",
                        )
                else:
                    legend_x_val = 0.0
                    legend_y_val = 1.0

                # Apply custom spacing to preset
                if (
                    col_spacing != preset_info["legend_columnspacing"]
                    or text_pad != preset_info["legend_handletextpad"]
                    or label_spacing != preset_info["legend_labelspacing"]
                    or box_length != preset_info["legend_handlelength"]
                    or border_pad != preset_info["legend_borderpad"]
                    or legend_ncol != preset_info.get("legend_ncol", 0)
                    or legend_custom_pos != preset_info.get("legend_custom_pos", False)
                    or (
                        legend_custom_pos
                        and (
                            legend_x_val != preset_info.get("legend_x", 0.0)
                            or legend_y_val != preset_info.get("legend_y", 1.0)
                        )
                    )
                ):
                    # Create custom preset with user adjustments
                    if isinstance(preset_to_use, str):
                        custom_preset = preset_info.copy()
                    else:
                        custom_preset = preset_to_use.copy()
                    custom_preset["legend_columnspacing"] = col_spacing
                    custom_preset["legend_handletextpad"] = text_pad
                    custom_preset["legend_labelspacing"] = label_spacing
                    custom_preset["legend_handlelength"] = box_length
                    custom_preset["legend_borderpad"] = border_pad
                    custom_preset["legend_ncol"] = legend_ncol
                    custom_preset["legend_custom_pos"] = legend_custom_pos
                    custom_preset["legend_x"] = legend_x_val
                    custom_preset["legend_y"] = legend_y_val
                    preset_to_use = custom_preset
                    st.info("✏️ Using custom legend settings")

            # Advanced settings for font sizes
            with st.expander("🔤 Advanced: Font Sizes & Bold", expanded=False):
                st.caption("Customize font sizes and bold styling (optional)")

                col_f1, col_f2, col_f3 = st.columns(3)
                with col_f1:
                    font_title = st.slider(
                        "Title Font Size",
                        min_value=6,
                        max_value=18,
                        value=effective_defaults["font_size_title"],
                        step=1,
                        help="Title font size in points",
                        key=f"font_title_{plot.plot_id}",
                    )
                    font_xlabel = st.slider(
                        "X-Axis Label",
                        min_value=5,
                        max_value=14,
                        value=effective_defaults.get("font_size_xlabel", 9),
                        step=1,
                        help="X-axis label (benchmark names below axis)",
                        key=f"font_xlabel_{plot.plot_id}",
                    )
                    font_ylabel = st.slider(
                        "Y-Axis Label",
                        min_value=5,
                        max_value=14,
                        value=effective_defaults.get("font_size_ylabel", 9),
                        step=1,
                        help="Y-axis label (e.g., 'Normalized Performance')",
                        key=f"font_ylabel_{plot.plot_id}",
                    )

                with col_f2:
                    font_legend = st.slider(
                        "Legend",
                        min_value=4,
                        max_value=12,
                        value=effective_defaults.get("font_size_legend", 8),
                        step=1,
                        help="Legend text font size",
                        key=f"font_legend_{plot.plot_id}",
                    )
                    font_ticks = st.slider(
                        "X-Tick Labels",
                        min_value=4,
                        max_value=12,
                        value=effective_defaults["font_size_ticks"],
                        step=1,
                        help="X-axis tick labels (TS_RS, TS_LA, etc.)",
                        key=f"font_ticks_{plot.plot_id}",
                    )
                    font_yticks = st.slider(
                        "Y-Tick Labels",
                        min_value=4,
                        max_value=12,
                        value=effective_defaults.get(
                            "font_size_yticks", effective_defaults["font_size_ticks"]
                        ),
                        step=1,
                        help="Y-axis tick labels size",
                        key=f"font_yticks_{plot.plot_id}",
                    )
                    font_annotations = st.slider(
                        "Bar Values",
                        min_value=3,
                        max_value=10,
                        value=effective_defaults.get("font_size_annotations", 6),
                        step=1,
                        help="Font size for bar total values",
                        key=f"font_annot_{plot.plot_id}",
                    )

                with col_f3:
                    st.write("**Bold Styling:**")
                    bold_title = st.checkbox(
                        "Title",
                        value=effective_defaults.get("bold_title", False),
                        key=f"bold_title_{plot.plot_id}",
                    )
                    bold_xlabel = st.checkbox(
                        "X-Axis Label",
                        value=effective_defaults.get("bold_xlabel", False),
                        key=f"bold_xlabel_{plot.plot_id}",
                    )
                    bold_ylabel = st.checkbox(
                        "Y-Axis Label",
                        value=effective_defaults.get("bold_ylabel", False),
                        key=f"bold_ylabel_{plot.plot_id}",
                    )
                    bold_legend = st.checkbox(
                        "Legend",
                        value=effective_defaults.get("bold_legend", False),
                        key=f"bold_legend_{plot.plot_id}",
                    )
                    bold_ticks = st.checkbox(
                        "Tick Labels",
                        value=effective_defaults.get("bold_ticks", False),
                        key=f"bold_ticks_{plot.plot_id}",
                    )
                    bold_annotations = st.checkbox(
                        "Bar Values",
                        value=effective_defaults.get("bold_annotations", True),
                        help="Bar totals in bold (default: True)",
                        key=f"bold_annot_{plot.plot_id}",
                    )
                    bold_group_labels = st.checkbox(
                        "X-Groupings",
                        value=effective_defaults.get("bold_group_labels", True),
                        help="X-axis group labels in bold (default: True)",
                        key=f"bold_group_{plot.plot_id}",
                    )

                # Apply custom font sizes and bold to preset
                if (
                    font_title != preset_info["font_size_title"]
                    or font_xlabel != preset_info.get("font_size_xlabel", 9)
                    or font_ylabel != preset_info.get("font_size_ylabel", 9)
                    or font_legend != preset_info.get("font_size_legend", 8)
                    or font_ticks != preset_info["font_size_ticks"]
                    or font_yticks
                    != preset_info.get("font_size_yticks", preset_info["font_size_ticks"])
                    or font_annotations != preset_info.get("font_size_annotations", 6)
                    or bold_title != preset_info.get("bold_title", False)
                    or bold_xlabel != preset_info.get("bold_xlabel", False)
                    or bold_ylabel != preset_info.get("bold_ylabel", False)
                    or bold_legend != preset_info.get("bold_legend", False)
                    or bold_ticks != preset_info.get("bold_ticks", False)
                    or bold_annotations != preset_info.get("bold_annotations", True)
                    or bold_group_labels != preset_info.get("bold_group_labels", True)
                ):
                    # Ensure preset_to_use is a dict (not just a name)
                    if isinstance(preset_to_use, str):
                        preset_to_use = preset_info.copy()
                    else:
                        preset_to_use = preset_to_use.copy()
                    preset_to_use["font_size_title"] = font_title
                    preset_to_use["font_size_xlabel"] = font_xlabel
                    preset_to_use["font_size_ylabel"] = font_ylabel
                    preset_to_use["font_size_legend"] = font_legend
                    preset_to_use["font_size_ticks"] = font_ticks
                    preset_to_use["font_size_yticks"] = font_yticks
                    preset_to_use["font_size_annotations"] = font_annotations
                    preset_to_use["bold_title"] = bold_title
                    preset_to_use["bold_xlabel"] = bold_xlabel
                    preset_to_use["bold_ylabel"] = bold_ylabel
                    preset_to_use["bold_legend"] = bold_legend
                    preset_to_use["bold_ticks"] = bold_ticks
                    preset_to_use["bold_annotations"] = bold_annotations
                    preset_to_use["bold_group_labels"] = bold_group_labels
                    st.info("✏️ Using custom font sizes/bold styling")

            # Advanced settings for LaTeX preamble
            with st.expander("📦 Advanced: LaTeX Font Packages", expanded=False):
                st.caption(
                    "Extra LaTeX packages so matplotlib measures text with "
                    "the same fonts your document uses (e.g., acmart monospace)."
                )
                latex_extra_preamble = st.text_input(
                    "Extra LaTeX Preamble",
                    value=str(effective_defaults.get("latex_extra_preamble", "")),
                    help=(
                        r"LaTeX packages to append to the preamble. "
                        r"Example: \usepackage[varqu,scaled=0.95]{zi4} "
                        r"for ACM/acmart documents."
                    ),
                    key=f"latex_preamble_{plot.plot_id}",
                )
                if latex_extra_preamble != preset_info.get("latex_extra_preamble", ""):
                    if isinstance(preset_to_use, str):
                        preset_to_use = preset_info.copy()
                    else:
                        preset_to_use = preset_to_use.copy()
                    preset_to_use["latex_extra_preamble"] = latex_extra_preamble
                    st.info("✏️ Using custom LaTeX preamble")

            # Advanced settings for positioning
            with st.expander("📐 Advanced: Positioning", expanded=False):
                st.caption("Fine-tune element positions (optional)")

                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    ylabel_pad = st.slider(
                        "Y-Axis Label Distance",
                        min_value=0.0,
                        max_value=80.0,
                        value=float(effective_defaults.get("ylabel_pad", 10.0)),
                        step=2.0,
                        help=(
                            "Distance from Y-axis label to tick labels "
                            "(points). Higher = more space."
                        ),
                        key=f"ylabel_pad_{plot.plot_id}",
                    )
                    ylabel_y_position = st.slider(
                        "Y-Axis Label Vertical Position",
                        min_value=0.0,
                        max_value=1.0,
                        value=float(effective_defaults.get("ylabel_y_position", 0.5)),
                        step=0.05,
                        help=(
                            "Vertical position of Y-axis label along "
                            "the axis (0=bottom, 0.5=center, 1=top)"
                        ),
                        key=f"ylabel_y_position_{plot.plot_id}",
                    )
                    xtick_pad = st.slider(
                        "X-Tick Label Distance",
                        min_value=0.0,
                        max_value=20.0,
                        value=float(effective_defaults.get("xtick_pad", 5.0)),
                        step=0.5,
                        help="Distance from X-axis tick labels to axis (points)",
                        key=f"xtick_pad_{plot.plot_id}",
                    )
                    ytick_pad = st.slider(
                        "Y-Tick Label Distance",
                        min_value=0.0,
                        max_value=20.0,
                        value=float(effective_defaults.get("ytick_pad", 5.0)),
                        step=0.5,
                        help="Distance from Y-axis tick labels to axis (points)",
                        key=f"ytick_pad_{plot.plot_id}",
                    )

                with col_p2:
                    group_label_offset = st.slider(
                        "Group Label Position",
                        min_value=-0.25,
                        max_value=0.0,
                        value=float(effective_defaults.get("group_label_offset", -0.12)),
                        step=0.01,
                        help="Vertical position of grouping labels (genome, intruder, etc.)",
                        key=f"group_offset_{plot.plot_id}",
                    )
                    group_label_alternate = st.checkbox(
                        "Alternate Group Labels (up/down)",
                        value=bool(effective_defaults.get("group_label_alternate", True)),
                        help="Alternate grouping labels vertically to avoid overlap",
                        key=f"group_alt_{plot.plot_id}",
                    )
                    group_label_alt_spacing = st.slider(
                        "Up/Down Spacing",
                        min_value=0.0,
                        max_value=0.20,
                        value=float(effective_defaults.get("group_label_alt_spacing", 0.05)),
                        step=0.01,
                        help="Vertical distance between up and down label positions",
                        key=f"group_alt_spacing_{plot.plot_id}",
                        disabled=not group_label_alternate,
                    )

                st.markdown("---")
                st.caption("Axis & Bar Spacing")
                col_p3, col_p4 = st.columns(2)
                with col_p3:
                    xaxis_margin = st.slider(
                        "X-Axis Margin",
                        min_value=-0.05,
                        max_value=0.2,
                        value=float(effective_defaults.get("xaxis_margin", 0.02)),
                        step=0.01,
                        help="Left/right margin on X-axis (negative = use whitespace)",
                        key=f"xaxis_margin_{plot.plot_id}",
                    )
                    xtick_rotation = st.slider(
                        "X-Tick Rotation",
                        min_value=0.0,
                        max_value=90.0,
                        value=float(effective_defaults.get("xtick_rotation", 45.0)),
                        step=5.0,
                        help="Rotation angle for X-axis tick labels",
                        key=f"xtick_rotation_{plot.plot_id}",
                    )
                    xtick_offset = st.slider(
                        "X-Tick Horizontal Offset",
                        min_value=-20.0,
                        max_value=20.0,
                        value=float(effective_defaults.get("xtick_offset", 0.0)),
                        step=1.0,
                        help="Shift X-tick labels left (-) or right (+) in points",
                        key=f"xtick_offset_{plot.plot_id}",
                    )

                with col_p4:
                    bar_width_scale = st.slider(
                        "Bar Width Scale",
                        min_value=0.5,
                        max_value=1.5,
                        value=float(effective_defaults.get("bar_width_scale", 1.0)),
                        step=0.05,
                        help="Scale factor for bar widths (>1 = wider bars)",
                        key=f"bar_width_scale_{plot.plot_id}",
                    )
                    xtick_ha = st.selectbox(
                        "X-Tick Alignment",
                        options=["right", "center", "left"],
                        index=["right", "center", "left"].index(
                            effective_defaults.get("xtick_ha", "right")
                        ),
                        help="Horizontal alignment of X-tick labels",
                        key=f"xtick_ha_{plot.plot_id}",
                    )

                st.markdown("---")
                st.caption("Group Separator (for arithmetic mean)")
                col_sep1, col_sep2 = st.columns(2)
                with col_sep1:
                    group_separator = st.checkbox(
                        "Draw Separator Before Last Group",
                        value=bool(effective_defaults.get("group_separator", False)),
                        help="Draw a vertical line before the last group (e.g., arithmean)",
                        key=f"group_sep_{plot.plot_id}",
                    )
                with col_sep2:
                    group_separator_style = st.selectbox(
                        "Separator Style",
                        options=["dashed", "dotted", "solid", "dashdot"],
                        index=["dashed", "dotted", "solid", "dashdot"].index(
                            effective_defaults.get("group_separator_style", "dashed")
                        ),
                        help="Line style for the group separator",
                        key=f"group_sep_style_{plot.plot_id}",
                        disabled=not group_separator,
                    )
                    group_separator_color = st.color_picker(
                        "Separator Color",
                        value=effective_defaults.get("group_separator_color", "#808080"),
                        key=f"group_sep_color_{plot.plot_id}",
                        disabled=not group_separator,
                    )

                # Apply custom positioning to preset
                if (
                    ylabel_pad != preset_info.get("ylabel_pad", 10.0)
                    or ylabel_y_position != preset_info.get("ylabel_y_position", 0.5)
                    or xtick_pad != preset_info.get("xtick_pad", 5.0)
                    or ytick_pad != preset_info.get("ytick_pad", 5.0)
                    or group_label_offset != preset_info.get("group_label_offset", -0.12)
                    or group_label_alternate != preset_info.get("group_label_alternate", True)
                    or group_label_alt_spacing != preset_info.get("group_label_alt_spacing", 0.05)
                    or xaxis_margin != preset_info.get("xaxis_margin", 0.02)
                    or bar_width_scale != preset_info.get("bar_width_scale", 1.0)
                    or xtick_rotation != preset_info.get("xtick_rotation", 45.0)
                    or xtick_ha != preset_info.get("xtick_ha", "right")
                    or xtick_offset != preset_info.get("xtick_offset", 0.0)
                    or group_separator != preset_info.get("group_separator", False)
                    or group_separator_style != preset_info.get("group_separator_style", "dashed")
                    or group_separator_color != preset_info.get("group_separator_color", "#808080")
                ):
                    # Ensure preset_to_use is a dict
                    if isinstance(preset_to_use, str):
                        preset_to_use = preset_info.copy()
                    else:
                        preset_to_use = preset_to_use.copy()
                    preset_to_use["ylabel_pad"] = ylabel_pad
                    preset_to_use["ylabel_y_position"] = ylabel_y_position
                    preset_to_use["xtick_pad"] = xtick_pad
                    preset_to_use["ytick_pad"] = ytick_pad
                    preset_to_use["group_label_offset"] = group_label_offset
                    preset_to_use["group_label_alternate"] = group_label_alternate
                    preset_to_use["group_label_alt_spacing"] = group_label_alt_spacing
                    preset_to_use["xaxis_margin"] = xaxis_margin
                    preset_to_use["bar_width_scale"] = bar_width_scale
                    preset_to_use["xtick_rotation"] = xtick_rotation
                    preset_to_use["xtick_ha"] = xtick_ha
                    preset_to_use["xtick_offset"] = xtick_offset
                    preset_to_use["group_separator"] = group_separator
                    preset_to_use["group_separator_style"] = group_separator_style
                    preset_to_use["group_separator_color"] = group_separator_color
                    st.info("✏️ Using custom positioning")

            # Always persist export settings to plot.config so that
            # portfolio save captures all user customizations, not just
            # those saved on "Generate Export" click.
            plot.config["export_preset"] = (
                preset_to_use if isinstance(preset_to_use, dict) else preset_info
            )
            plot.config["export_format"] = format_choice

            # Preview button
            col_preview, col_export = st.columns(2)

            with col_preview:
                if st.button(
                    "🔍 Preview Export", use_container_width=True, key=f"preview_btn_{plot.plot_id}"
                ):
                    with st.spinner("Generating preview..."):
                        try:
                            preview_png = service.generate_preview(
                                fig, preset=preset_to_use, preview_dpi=100
                            )
                            st.image(preview_png, caption="Export Preview (scaled for display)")
                            # Show actual dimensions (may be user-overridden)
                            actual_preset = (
                                preset_to_use if isinstance(preset_to_use, dict) else preset_info
                            )
                            st.caption(
                                f"Actual export size: "
                                f"{actual_preset['width_inches']}\" × "
                                f"{actual_preset['height_inches']}\" @ "
                                f"{actual_preset['dpi']} DPI"
                            )
                        except Exception as e:
                            st.error(f"Preview failed: {e}")

            # Export button
            with col_export:
                if st.button(
                    "📥 Generate Export",
                    use_container_width=True,
                    type="primary",
                    key=f"export_btn_{plot.plot_id}",
                ):
                    # Save export preset to plot config for portfolio persistence
                    plot.config["export_preset"] = (
                        preset_to_use if isinstance(preset_to_use, dict) else preset_info
                    )
                    plot.config["export_format"] = format_choice

                    with st.spinner(f"Generating {format_choice.upper()}..."):
                        # Call service
                        result = service.export(fig, preset=preset_to_use, format=format_choice)

                        if result["success"] and result["data"] is not None:
                            # Success - provide download
                            file_extension = result["format"]
                            file_name = f"figure.{file_extension}"

                            st.download_button(
                                label=f"Download {file_extension.upper()}",
                                data=result["data"],  # Now guaranteed non-None
                                file_name=file_name,
                                mime=_get_mime_type(file_extension),
                                use_container_width=True,
                                key=f"download_btn_{plot.plot_id}",
                            )

                            st.success(
                                f"✓ Export successful " f"({len(result['data']) / 1024:.1f} KB)"
                            )
                        else:
                            # Error - show message
                            error_msg = result.get("error", "Unknown error")
                            st.error(f"Export failed: {error_msg}")
                            st.info(
                                "Tip: Ensure LaTeX is installed on your system "
                                "for PGF/EPS formats."
                            )


def _get_mime_type(file_extension: str) -> str:
    """Get MIME type for file extension."""
    mime_types = {
        "pdf": "application/pdf",
        "pgf": "application/x-tex",
        "eps": "application/postscript",
    }
    return mime_types.get(file_extension, "application/octet-stream")
