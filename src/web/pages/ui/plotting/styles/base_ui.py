"""
Base Style UI - Abstract Plot Style Configuration Logic.

Abstract base for plot type-specific style managers. Handles configuration
of visual parameters: colors, fonts, layouts, legends, and styling options
through Streamlit UI components.
"""

import hashlib
from typing import Any, cast

import pandas as pd
import streamlit as st

from src.core.models.visualization.palettes import resolve_palette
from src.web.pages.ui.plotting.styles.colors import to_hex
from src.web.rendering.widgets import WidgetRenderer


class BaseStyleUI:
    """
    Base Strategy Logic for generic UI rendering.

    Uses ``WidgetRenderer`` for declarative sections where possible,
    falling back to hand-coded widgets for sections requiring column
    layouts or conditional rendering.
    """

    def __init__(self, plot_id: int, plot_type: str):
        self.plot_id = plot_id
        self.plot_type = plot_type
        self._renderer = WidgetRenderer(key_prefix=f"p{plot_id}_")

    def render_layout_options(self, saved_config: dict[str, Any]) -> dict[str, Any]:
        """Render layout sizing options."""
        st.markdown("**Dimensions**")

        preset_options: dict[str, float] = {
            "Single Column (~3.5in)": 3.5,
            "Double Column (~7.0in)": 7.0,
            "Custom": 0.0,  # sentinel — uses manual width
        }

        default_preset = saved_config.get("document_width_preset", "Double Column (~7.0in)")
        preset_idx = (
            list(preset_options.keys()).index(default_preset)
            if default_preset in preset_options
            else 1
        )

        preset = st.selectbox(
            "Document Size Preset",
            list(preset_options.keys()),
            index=preset_idx,
            key=f"col_preset_{self.plot_id}",
        )

        c1, c2 = st.columns(2)
        with c1:
            if preset == "Custom":
                width_inches = st.number_input(
                    "Width (inches)",
                    min_value=1.0,
                    max_value=30.0,
                    value=float(saved_config.get("width_inches", 7.0)),
                    step=0.5,
                    key=f"wi_{self.plot_id}",
                )
            else:
                width_inches = preset_options[preset]
                st.number_input(
                    "Width (inches)",
                    value=width_inches,
                    disabled=True,
                    key=f"wi_disabled_{self.plot_id}",
                )

        with c2:
            height_inches = st.number_input(
                "Height (inches)",
                min_value=1.0,
                max_value=30.0,
                value=float(saved_config.get("height_inches", 3.5)),
                step=0.5,
                key=f"hi_{self.plot_id}",
            )

        # Plotly expects pixels. We'll scale 1 inch to 100 pixels for the frontend preview.
        # Exporting backend will use width_inches and height_inches natively or scale down.
        width = int(width_inches * 100)
        height = int(height_inches * 100)

        return {
            "document_width_preset": preset,
            "width_inches": width_inches,
            "height_inches": height_inches,
            "width": width,
            "height": height,
            "margin_l": 0,
            "margin_r": 0,
            "margin_t": 0,
            "margin_b": 0,
            "margin_pad": 0,
            "automargin": True,
        }

    def render_style_ui(
        self,
        saved_config: dict[str, Any],
        data: pd.DataFrame | None = None,
        items: list[str] | None = None,
        key_prefix: str = "",
    ) -> dict[str, Any]:
        """
        Render style configurator UI (Theme, Colors, Fonts).
        Delegates to specific render methods for each section.
        """
        # 1. Series Colors (palette comes from saved_config; _section_colors owns the dropdown)
        series_config = self._render_series_section(
            saved_config,
            data,
            items,
            key_prefix,
            palette_name=saved_config.get("color_palette"),
        )

        st.markdown("---")

        # 2. Data Labels
        data_labels_config = self.render_data_labels_ui(saved_config, key_prefix)

        st.markdown("---")

        # 3. Backgrounds & Grid
        bg_config = self._render_backgrounds_section(saved_config, key_prefix)

        # 4. Legend Styling
        legend_config = self._render_legend_section(saved_config, key_prefix)

        # 5. Typography (Titles & Labels)
        typography_config = self._render_typography_section(saved_config, key_prefix)

        # Merge all configs
        theme_config = {
            **series_config,
            **bg_config,
            **legend_config,
            **typography_config,
            "show_values": data_labels_config.get("show_values", False),
            "text_color_mode": data_labels_config.get("text_color_mode"),
            "text_color": data_labels_config.get("text_color"),
            "text_font_size": data_labels_config.get("text_font_size"),
            "text_rotation": data_labels_config.get("text_rotation"),
            "text_position": data_labels_config.get("text_position"),
            "text_anchor": data_labels_config.get("text_anchor"),
            "text_format": data_labels_config.get("text_format"),
            "text_display_logic": data_labels_config.get("text_display_logic"),
            "text_threshold": data_labels_config.get("text_threshold"),
            "text_constraint": data_labels_config.get("text_constraint"),
        }

        return theme_config

    def _render_series_section(
        self,
        saved_config: dict[str, Any],
        data: pd.DataFrame | None,
        items: list[str] | None,
        key_prefix: str,
        palette_name: str | None = None,
    ) -> dict[str, Any]:
        """Render per-series color overrides.

        The palette dropdown has been consolidated into
        ``BasePlot._section_colors``.  This method only renders the
        individual colour pickers for each series/group.

        Args:
            saved_config: Current saved configuration.
            data: DataFrame for column discovery.
            items: Explicit series/group names (optional).
            key_prefix: Streamlit widget key prefix.
            palette_name: Active palette name (resolved upstream).

        Returns:
            Dict with ``series_styles`` key only.
        """
        st.markdown("#### Series Colors")

        effective_palette = palette_name or saved_config.get("color_palette", "wong")

        series_styles = self.render_series_colors_ui(
            saved_config,
            data,
            items=items,
            key_prefix=key_prefix,
            current_palette=effective_palette,
        )

        st.markdown("---")

        return {"series_styles": series_styles}

    def _render_backgrounds_section(
        self, saved_config: dict[str, Any], key_prefix: str
    ) -> dict[str, Any]:
        """Render backgrounds and grid section."""
        st.markdown("#### Backgrounds & Grid")

        transparent_bg = st.checkbox(
            "Transparent Background",
            value=saved_config.get("transparent_bg", False),
            key=f"{key_prefix}trans_bg_{self.plot_id}",
            help="Make the plot background fully transparent.",
        )

        theme_cols1, theme_cols2 = st.columns(2)
        with theme_cols1:
            if not transparent_bg:
                curr_plot_bg = saved_config.get("plot_bgcolor", "#ffffff")
                if not curr_plot_bg.startswith("#"):
                    curr_plot_bg = "#ffffff"

                curr_paper_bg = saved_config.get("paper_bgcolor", "#ffffff")
                if not curr_paper_bg.startswith("#"):
                    curr_paper_bg = "#ffffff"

                plot_bgcolor = st.color_picker(
                    "Plot Background",
                    curr_plot_bg,
                    key=f"{key_prefix}bg_plot_{self.plot_id}",
                )
                paper_bgcolor = st.color_picker(
                    "Paper (Outer) Background",
                    curr_paper_bg,
                    key=f"{key_prefix}bg_paper_{self.plot_id}",
                )
            else:
                plot_bgcolor = "rgba(0,0,0,0)"
                paper_bgcolor = "rgba(0,0,0,0)"

            grid_color = st.color_picker(
                "Grid Color",
                saved_config.get("grid_color", "#e5e5e5"),
                key=f"{key_prefix}grid_col_{self.plot_id}",
            )

        with theme_cols2:
            axis_color = st.color_picker(
                "Axis Line/Tick Color",
                saved_config.get("axis_color", "#444444"),
                key=f"{key_prefix}axis_col_{self.plot_id}",
            )
            axis_line_width = st.number_input(
                "Axis Line Width (px)",
                min_value=0.0,
                max_value=10.0,
                value=float(saved_config.get("axis_line_width", 1.0)),
                step=0.5,
                key=f"{key_prefix}axis_lw_{self.plot_id}",
                help="Width of the axis border lines.",
            )

            if "bar" in self.plot_type and "grouped_stacked" not in self.plot_type:
                enable_stripes = st.checkbox(
                    "Enable Bar Stripes",
                    value=saved_config.get("enable_stripes", False),
                    key=f"{key_prefix}stripes_{self.plot_id}",
                    help="Adds a diagonal pattern to bars for better differentiation.",
                )
            else:
                enable_stripes = False

        return {
            "transparent_bg": transparent_bg,
            "plot_bgcolor": plot_bgcolor,
            "paper_bgcolor": paper_bgcolor,
            "grid_color": grid_color,
            "axis_color": axis_color,
            "axis_line_width": axis_line_width,
            "enable_stripes": enable_stripes,
        }

    def _render_legend_section(
        self, saved_config: dict[str, Any], key_prefix: str
    ) -> dict[str, Any]:
        """Render legend styling section."""
        # Determine the correct prefix for config dictionary:
        # primary ('theme_') uses 'legend_', others ('legend2_') use 'legend2_'
        config_prefix = "legend_" if key_prefix == "theme_" else key_prefix
        st.markdown("#### Legend Styling")

        # Position & Orientation
        pos_config = self._render_legend_position(saved_config, key_prefix, config_prefix)

        # Appearance
        app_config = self._render_legend_appearance(saved_config, key_prefix, config_prefix)

        # Sizing & Spacing
        sz_config = self._render_legend_sizing(saved_config, key_prefix, config_prefix)

        return {**pos_config, **app_config, **sz_config}

    def _render_legend_position(
        self, saved_config: dict[str, Any], key_prefix: str, config_prefix: str
    ) -> dict[str, Any]:
        """Render legend position and orientation controls."""
        st.markdown("**Position & Orientation**")
        pos_c1, pos_c2 = st.columns(2)

        with pos_c1:
            legend_orientation = st.selectbox(
                "Orientation",
                options=["v", "h"],
                format_func=lambda x: "Vertical" if x == "v" else "Horizontal",
                index=0 if saved_config.get(f"{config_prefix}orientation", "v") == "v" else 1,
                key=f"{key_prefix}leg_orient_{self.plot_id}",
            )

            legend_ncols = st.number_input(
                "Columns",
                min_value=0,
                max_value=10,
                value=int(saved_config.get(f"{config_prefix}ncols", 0)),
                key=f"{key_prefix}leg_cols_{self.plot_id}",
                help=(
                    "Number of legend columns. Uses multiple"
                    " legend objects positioned side-by-side."
                    " 0 = Auto (single column)."
                ),
            )

            legend_x = st.number_input(
                "X Position",
                value=float(
                    saved_config.get(
                        f"{config_prefix}x",
                        1.02 if config_prefix == "legend_" else 1.0,
                    )
                ),
                step=0.05,
                key=f"{key_prefix}leg_x_{self.plot_id}",
            )
            legend_xanchor = st.selectbox(
                "X Anchor",
                options=["auto", "left", "center", "right"],
                index=["auto", "left", "center", "right"].index(
                    saved_config.get(f"{config_prefix}xanchor", "auto")
                ),
                key=f"{key_prefix}leg_xanc_{self.plot_id}",
            )

        with pos_c2:
            legend_col_width = st.number_input(
                "Column Width (px)",
                min_value=0,
                max_value=500,
                value=int(saved_config.get(f"{config_prefix}col_width", 150)),
                key=f"{key_prefix}leg_col_width_{self.plot_id}",
                help="Width of each legend column in pixels.",
            )

            legend_valign = st.selectbox(
                "Vertical Align",
                options=["middle", "top", "bottom"],
                index=(
                    ["middle", "top", "bottom"].index(
                        saved_config.get(f"{config_prefix}valign", "middle")
                    )
                    if saved_config.get(f"{config_prefix}valign", "middle")
                    in ["middle", "top", "bottom"]
                    else 0
                ),
                key=f"{key_prefix}leg_valign_{self.plot_id}",
            )

            legend_y = st.number_input(
                "Y Position",
                value=float(saved_config.get(f"{config_prefix}y", 1.0)),
                step=0.05,
                key=f"{key_prefix}leg_y_{self.plot_id}",
            )
            legend_yanchor = st.selectbox(
                "Y Anchor",
                options=["auto", "top", "middle", "bottom"],
                index=["auto", "top", "middle", "bottom"].index(
                    saved_config.get(f"{config_prefix}yanchor", "auto")
                ),
                key=f"{key_prefix}leg_yanc_{self.plot_id}",
            )

        return {
            f"{config_prefix}orientation": legend_orientation,
            f"{config_prefix}ncols": legend_ncols,
            f"{config_prefix}col_width": legend_col_width,
            f"{config_prefix}valign": legend_valign,
            f"{config_prefix}x": legend_x,
            f"{config_prefix}y": legend_y,
            f"{config_prefix}xanchor": legend_xanchor,
            f"{config_prefix}yanchor": legend_yanchor,
        }

    def _render_legend_appearance(
        self, saved_config: dict[str, Any], key_prefix: str, config_prefix: str
    ) -> dict[str, Any]:
        """Render legend appearance controls (colors, border, fonts)."""
        st.markdown("**Appearance**")
        app_c1, app_c2 = st.columns(2)

        with app_c1:
            bg_col = saved_config.get(f"{config_prefix}bgcolor", "#ffffff")
            if str(bg_col).startswith("rgba"):
                bg_col = "#ffffff"

            transparent_legend = st.checkbox(
                "Transparent Background",
                value=saved_config.get(f"{config_prefix}transparent", False),
                key=f"{key_prefix}trans_leg_{self.plot_id}",
            )

            if not transparent_legend:
                legend_bgcolor = st.color_picker(
                    "Background Color",
                    bg_col,
                    key=f"{key_prefix}leg_bg_col_{self.plot_id}",
                )
            else:
                legend_bgcolor = "rgba(0,0,0,0)"

            st.caption("Border")
            legend_border_color = st.color_picker(
                "Border Color",
                saved_config.get(f"{config_prefix}border_color", "#000000"),
                key=f"{key_prefix}leg_bord_col_{self.plot_id}",
            )
            legend_border_width = st.number_input(
                "Border Width",
                min_value=0,
                max_value=5,
                value=int(saved_config.get(f"{config_prefix}border_width", 0)),
                key=f"{key_prefix}leg_bord_wd_{self.plot_id}",
            )

        with app_c2:
            st.caption("Font")
            legend_font_color = st.color_picker(
                "Text Color",
                saved_config.get(f"{config_prefix}font_color", "#000000"),
                key=f"{key_prefix}leg_font_col_{self.plot_id}",
            )
            legend_font_size = st.number_input(
                "Font Size",
                min_value=8,
                max_value=100,
                value=int(saved_config.get(f"{config_prefix}font_size", 12)),
                key=f"{key_prefix}leg_font_sz_{self.plot_id}",
            )

            st.caption("Title Font")
            legend_title = st.text_input(
                "Legend Title",
                value=saved_config.get(f"{config_prefix}title", ""),
                key=f"{key_prefix}leg_title_txt_{self.plot_id}",
            )
            legend_title_font_color = st.color_picker(
                "Title Color",
                saved_config.get(f"{config_prefix}title_font_color", "#000000"),
                key=f"{key_prefix}leg_title_col_{self.plot_id}",
            )
            legend_title_font_size = st.number_input(
                "Title Size",
                min_value=8,
                max_value=100,
                value=int(saved_config.get(f"{config_prefix}title_font_size", 14)),
                key=f"{key_prefix}leg_title_sz_{self.plot_id}",
            )

        return {
            f"{config_prefix}transparent": transparent_legend,
            f"{config_prefix}bgcolor": legend_bgcolor,
            f"{config_prefix}border_color": legend_border_color,
            f"{config_prefix}border_width": legend_border_width,
            f"{config_prefix}font_color": legend_font_color,
            f"{config_prefix}font_size": legend_font_size,
            f"{config_prefix}title": legend_title,
            f"{config_prefix}title_font_color": legend_title_font_color,
            f"{config_prefix}title_font_size": legend_title_font_size,
        }

    def _render_legend_sizing(
        self, saved_config: dict[str, Any], key_prefix: str, config_prefix: str
    ) -> dict[str, Any]:
        """Render legend sizing and spacing controls (declarative)."""
        st.markdown("**Sizing & Spacing**")
        sz_c1, sz_c2 = st.columns(2)
        with sz_c1:
            itemsizing = st.selectbox(
                "Marker Scale",
                options=["constant", "trace"],
                index=["constant", "trace"].index(
                    saved_config.get(f"{config_prefix}itemsizing", "constant")
                ),
                key=f"{key_prefix}leg_itemsz_{self.plot_id}",
            )
            itemwidth = st.number_input(
                "Marker Width (px) [Min: 30]",
                min_value=30,
                max_value=120,
                value=int(saved_config.get(f"{config_prefix}itemwidth", 30)),
                key=f"{key_prefix}leg_itemw_{self.plot_id}",
                help="Width of legend items. Plotly requires minimum 30px.",
            )
            marker_text_spacing = st.number_input(
                "Marker-Text Space",
                min_value=0.0,
                max_value=10.0,
                value=float(saved_config.get(f"{config_prefix}marker_text_spacing", 0.5)),
                step=0.1,
                key=f"{key_prefix}leg_mtspace_{self.plot_id}",
                help="Space between color marker and text (Matplotlib handletextpad).",
            )
        with sz_c2:
            tracegroupgap = st.number_input(
                "Item Spacing (px)",
                min_value=0,
                max_value=100,
                value=int(saved_config.get(f"{config_prefix}tracegroupgap", 10)),
                key=f"{key_prefix}leg_tracegap_{self.plot_id}",
                help="Vertical spacing between legend items.",
            )
            column_spacing = st.number_input(
                "Column Spacing",
                min_value=0.0,
                max_value=10.0,
                value=float(saved_config.get(f"{config_prefix}column_spacing", 1.0)),
                step=0.5,
                key=f"{key_prefix}leg_colspace_{self.plot_id}",
                help="Space between columns in the legend (Matplotlib columnspacing).",
            )

        return {
            f"{config_prefix}itemsizing": itemsizing,
            f"{config_prefix}itemwidth": itemwidth,
            f"{config_prefix}tracegroupgap": tracegroupgap,
            f"{config_prefix}column_spacing": column_spacing,
            f"{config_prefix}marker_text_spacing": marker_text_spacing,
        }

    def _render_typography_section(
        self, saved_config: dict[str, Any], key_prefix: str
    ) -> dict[str, Any]:
        """Render typography section (font sizes and colors).

        Note: Title text inputs (Main Title, X-label, Y-label) are in
        the plot config UI (render_config_ui). This section only controls
        font sizes, colors, and axis label appearance.
        """
        st.markdown("#### Typography (Font Sizes & Colors)")
        typo_c1, typo_c2 = st.columns(2)

        with typo_c1:
            st.markdown("**Title Font Sizes**")
            title_font_size = st.number_input(
                "Plot Title Font Size",
                min_value=8,
                max_value=100,
                value=saved_config.get("title_font_size", 18),
                key=f"{key_prefix}title_sz_{self.plot_id}",
            )

            xaxis_title_font_size = st.number_input(
                "X-Axis Title Font Size",
                min_value=8,
                max_value=100,
                value=saved_config.get("xaxis_title_font_size", 14),
                key=f"{key_prefix}xaxis_title_sz_{self.plot_id}",
            )

            yaxis_title_font_size = st.number_input(
                "Y-Axis Title Font Size",
                min_value=8,
                max_value=100,
                value=saved_config.get("yaxis_title_font_size", 14),
                key=f"{key_prefix}yaxis_title_sz_{self.plot_id}",
            )

            st.markdown("**Y-Axis Title Position**")
            yaxis_title_standoff = st.slider(
                "Y-Axis Title Standoff (Spacing)",
                min_value=0,
                max_value=100,
                value=saved_config.get("yaxis_title_standoff", 0),
                key=f"{key_prefix}yaxis_title_standoff_{self.plot_id}",
                help="Distance between Y-axis ticks and the title.",
            )

            yaxis_title_vshift = st.slider(
                "Y-Axis Title Vertical Shift",
                min_value=-300,
                max_value=300,
                value=saved_config.get("yaxis_title_vshift", 0),
                key=f"{key_prefix}yaxis_title_vshift_{self.plot_id}",
                help=(
                    "Move title up (+) or down (-) along"
                    " the axis. Note: Disables native"
                    " auto-margins for title."
                ),
            )

        with typo_c2:
            st.markdown("**Tick Label Sizes & Colors**")
            xaxis_tickfont_size = st.number_input(
                "X-Axis Label (Tick) Size",
                min_value=8,
                max_value=100,
                value=saved_config.get("xaxis_tickfont_size", 12),
                key=f"{key_prefix}xaxis_tick_sz_{self.plot_id}",
                help="Overwrites the basic X-axis font size in Advanced Options",
            )
            xaxis_tickfont_color = st.color_picker(
                "X-Axis Label Color",
                saved_config.get("xaxis_tickfont_color", "#444444"),
                key=f"{key_prefix}xaxis_tick_col_{self.plot_id}",
            )

            yaxis_tickfont_size = st.number_input(
                "Y-Axis Label (Tick) Size",
                min_value=8,
                max_value=100,
                value=saved_config.get("yaxis_tickfont_size", 12),
                key=f"{key_prefix}yaxis_tick_sz_{self.plot_id}",
            )
            yaxis_tickfont_color = st.color_picker(
                "Y-Axis Label Color",
                saved_config.get("yaxis_tickfont_color", "#444444"),
                key=f"{key_prefix}yaxis_tick_col_{self.plot_id}",
            )

            st.markdown("**Tick Marks & Grid Lines**")
            show_xtick_marks = st.checkbox(
                "Show X-Axis Tick Marks",
                value=saved_config.get("show_xtick_marks", True),
                key=f"{key_prefix}x_show_ticks_{self.plot_id}",
            )
            dash_options = ["solid", "dot", "dash", "longdash", "dashdot", "longdashdot"]
            xtick_dash_idx = 0
            if saved_config.get("xtick_dash", "solid") in dash_options:
                xtick_dash_idx = dash_options.index(saved_config.get("xtick_dash", "solid"))

            xtick_dash: str = "solid"
            if show_xtick_marks:
                xtick_dash = st.selectbox(
                    "X-Axis Grid Dash Style",
                    options=dash_options,
                    index=xtick_dash_idx,
                    key=f"{key_prefix}x_tickdash_{self.plot_id}",
                )

            show_ytick_marks = st.checkbox(
                "Show Y-Axis Tick Marks",
                value=saved_config.get("show_ytick_marks", True),
                key=f"{key_prefix}y_show_ticks_{self.plot_id}",
            )
            ytick_dash_idx = 0
            if saved_config.get("ytick_dash", "solid") in dash_options:
                ytick_dash_idx = dash_options.index(saved_config.get("ytick_dash", "solid"))

            ytick_dash: str = "solid"
            if show_ytick_marks:
                ytick_dash = st.selectbox(
                    "Y-Axis Grid Dash Style",
                    options=dash_options,
                    index=ytick_dash_idx,
                    key=f"{key_prefix}y_tickdash_{self.plot_id}",
                )

            st.markdown("**Label Spacing & Alternating**")
            xtick_pad = st.number_input(
                "X-Axis Tick Label Distance (px)",
                min_value=0.0,
                max_value=50.0,
                value=float(saved_config.get("xtick_pad", 5.0)),
                step=1.0,
                key=f"{key_prefix}xtick_pad_{self.plot_id}",
                help="Distance between X-axis tick marks and their labels.",
            )
            group_label_alternate = st.checkbox(
                "Alternate Group Labels (up/down)",
                value=saved_config.get("group_label_alternate", True),
                key=f"{key_prefix}grp_alt_{self.plot_id}",
                help="Stagger group labels to avoid overlap.",
            )
            group_label_alt_spacing = st.number_input(
                "Alt. Label Row Spacing",
                min_value=0.0,
                max_value=0.5,
                value=float(
                    saved_config.get("group_label_alt_spacing", 0.05)
                ),
                step=0.01,
                key=f"{key_prefix}grp_alt_sp_{self.plot_id}",
                help="Vertical distance between alternating label rows.",
            )

        return {
            "title_font_size": title_font_size,
            "xaxis_title_font_size": xaxis_title_font_size,
            "yaxis_title_font_size": yaxis_title_font_size,
            "yaxis_title_standoff": yaxis_title_standoff,
            "yaxis_title_vshift": yaxis_title_vshift,
            "xaxis_tickfont_size": xaxis_tickfont_size,
            "xaxis_tickfont_color": xaxis_tickfont_color,
            "yaxis_tickfont_size": yaxis_tickfont_size,
            "yaxis_tickfont_color": yaxis_tickfont_color,
            "show_xtick_marks": show_xtick_marks,
            "xtick_dash": xtick_dash,
            "show_ytick_marks": show_ytick_marks,
            "ytick_dash": ytick_dash,
            "xtick_pad": xtick_pad,
            "group_label_alternate": group_label_alternate,
            "group_label_alt_spacing": group_label_alt_spacing,
        }

    def render_series_colors_ui(
        self,
        saved_config: dict[str, Any],
        data: pd.DataFrame | None = None,
        items: list[str] | None = None,
        key_prefix: str = "",
        current_palette: str | None = None,
    ) -> dict[str, Any]:
        """
        Render UI for per-series coloring.
        """
        series_styles_raw = saved_config.get("series_styles", {})
        series_styles: dict[str, Any] = (
            cast(dict[str, Any], series_styles_raw) if series_styles_raw else {}
        )
        unique_vals = self._get_unique_values(saved_config, data, items)

        # Use current selection if available, else saved config
        palette_name = current_palette or saved_config.get("color_palette", "plotly")

        palette_colors = resolve_palette(palette_name)

        if unique_vals:
            for idx, val in enumerate(unique_vals):
                val_str = str(val)
                val_hash = hashlib.md5(val_str.encode(), usedforsecurity=False).hexdigest()[:8]

                raw_color = palette_colors[idx % len(palette_colors)]
                default_color = to_hex(raw_color)

                current_style = series_styles.get(val_str, {})

                c1, c2 = st.columns([1, 2])
                with c1:
                    st.markdown(f"**{val_str}**")

                with c2:
                    # Pass palette name to trigger key reset on palette change
                    current_style = self._render_series_item(
                        val_str, default_color, current_style, val_hash, key_prefix, palette_name
                    )

                series_styles[val_str] = current_style

        return series_styles

    def _render_series_item(
        self,
        val_str: str,
        default_color: str,
        current_style: dict[str, Any],
        val_hash: str,
        key_prefix: str = "",
        palette_name: str = "",
    ) -> dict[str, Any]:
        c2, c3 = st.columns([1, 2])

        # Keys for widgets — include palette_name so Streamlit resets
        # the color picker widget value when the user changes the palette.
        picker_key = f"{key_prefix}color_{self.plot_id}_{val_hash}_{palette_name}"
        override_key = f"{key_prefix}use_col_{self.plot_id}_{val_hash}"

        with c2:
            st.color_picker(
                "Original",
                default_color,
                key=f"{key_prefix}orig_col_{self.plot_id}_{val_hash}_{palette_name}",
                disabled=True,
                label_visibility="collapsed",
            )
            st.caption(f"{default_color}")

            # Reset Button
            if st.button(
                "Rewind",
                key=f"{key_prefix}rst_{self.plot_id}_{val_hash}",
                help="Reset to palette color",
            ):
                current_style["use_color"] = False
                current_style["color"] = default_color

                # Force update session state to reflect change immediately
                if picker_key in st.session_state:
                    st.session_state[picker_key] = default_color
                if override_key in st.session_state:
                    st.session_state[override_key] = False

                st.rerun()

        with c3:
            saved_col = current_style.get("color", default_color)
            new_color_raw = st.color_picker(
                "Custom", saved_col, key=picker_key, label_visibility="collapsed"
            )
            new_color: str = str(new_color_raw) if new_color_raw is not None else default_color
            st.caption(f"{new_color}")

            use_custom_raw = st.checkbox(
                "Override", value=current_style.get("use_color", False), key=override_key
            )
            use_custom: bool = bool(use_custom_raw) if use_custom_raw is not None else False

            current_style["color"] = new_color
            current_style["use_color"] = use_custom

            # specific visuals (Symbols, Patterns, etc)
            self._render_specific_series_visuals(current_style, val_hash, key_prefix=key_prefix)

        return current_style

    def _render_specific_series_visuals(
        self, current_style: dict[str, Any], key_suffix: str, key_prefix: str = ""
    ) -> None:
        """Hook for subclasses to render specific style options."""

    def render_series_renaming_ui(
        self,
        saved_config: dict[str, Any],
        data: pd.DataFrame | None = None,
        items: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Render UI for per-series renaming.
        """
        series_styles_raw = saved_config.get("series_styles", {})
        series_styles: dict[str, Any] = (
            cast(dict[str, Any], series_styles_raw) if series_styles_raw else {}
        )
        unique_vals = self._get_unique_values(saved_config, data, items)

        if unique_vals:
            for val in unique_vals:
                val_str = str(val)
                val_hash = hashlib.md5(val_str.encode(), usedforsecurity=False).hexdigest()[:8]

                current_style = series_styles.get(val_str, {})

                c1, c2 = st.columns([1, 2])
                with c1:
                    st.markdown(f"**{val_str}**")
                with c2:
                    new_name_raw = st.text_input(
                        "Display Name",
                        value=current_style.get("name", val_str),
                        key=f"name_{self.plot_id}_{val_hash}",
                        label_visibility="collapsed",
                        placeholder=val_str,
                    )
                    new_name: str = str(new_name_raw) if new_name_raw is not None else val_str
                    current_style["name"] = new_name

                series_styles[val_str] = current_style

        return series_styles

    def render_xaxis_labels_ui(
        self,
        saved_config: dict[str, Any],
        data: pd.DataFrame | None = None,
        key_prefix: str = "xlabel",
    ) -> dict[str, str]:
        """
        Render UI for X-Axis label renaming.
        """
        xaxis_labels_raw = saved_config.get("xaxis_labels", {})
        xaxis_labels: dict[str, str] = (
            cast(dict[str, str], xaxis_labels_raw) if xaxis_labels_raw else {}
        )
        x_col = saved_config.get("x")

        if data is not None and x_col and x_col in data.columns:
            # Removed markdown title

            with st.expander("Rename X-Axis Labels"):
                unique_x_raw = data[x_col].unique()
                unique_x = sorted(unique_x_raw, key=str)

                if len(unique_x) > 50:
                    st.warning("Too many X-axis values to list all. Showing first 50.")
                    unique_x = unique_x[:50]

                for val in unique_x:
                    s_val = str(val)
                    val_hash = hashlib.md5(s_val.encode(), usedforsecurity=False).hexdigest()[:8]

                    col_l, col_r = st.columns([1, 2])
                    with col_l:
                        st.markdown(f"**{val}**")
                    with col_r:
                        new_label_raw = st.text_input(
                            "Display As",
                            value=xaxis_labels.get(s_val, ""),
                            key=f"{key_prefix}_{self.plot_id}_{val_hash}",
                            label_visibility="collapsed",
                            placeholder=s_val,
                        )
                        new_label: str = str(new_label_raw) if new_label_raw is not None else ""
                        if new_label and new_label != s_val:
                            xaxis_labels[s_val] = new_label
                        elif s_val in xaxis_labels:
                            del xaxis_labels[s_val]

        return xaxis_labels

    def _get_unique_values(
        self, saved_config: dict[str, Any], data: pd.DataFrame | None, items: list[str] | None
    ) -> list[str]:
        """Helper to determine series items."""
        unique_vals: list[str] = []
        if items is not None:
            unique_vals = sorted([str(i) for i in items])
        elif data is not None:
            legend_col = saved_config.get("color") or saved_config.get("group")
            y_cols = saved_config.get("y_columns", [])

            if legend_col and legend_col in data.columns:
                unique_vals = sorted(data[legend_col].unique().astype(str).tolist())
            elif y_cols:
                unique_vals = sorted([str(c) for c in y_cols])
        return unique_vals

    def render_data_labels_ui(
        self, saved_config: dict[str, Any], key_prefix: str = ""
    ) -> dict[str, Any]:
        """
        Render UI for Data Values/Labels.
        """
        st.markdown("#### Data Labels")

        show_values = st.checkbox(
            "Show Values",
            value=saved_config.get("show_values", False),
            key=f"{key_prefix}show_val_{self.plot_id}",
        )

        text_color_mode = st.selectbox(
            "Value Color Mode",
            options=["auto", "contrast", "custom"],
            index=(
                ["auto", "contrast", "custom"].index(saved_config.get("text_color_mode", "auto"))
                if saved_config.get("text_color_mode", "auto") in ["auto", "contrast", "custom"]
                else 0
            ),
            key=f"{key_prefix}tx_col_mode_{self.plot_id}",
            help=(
                "Auto: uses theme default. Contrast:"
                " white on dark, black on light."
                " Custom: fixed color."
            ),
        )

        text_color = "#000000"
        if text_color_mode == "custom":
            text_color = st.color_picker(
                "Value Color",
                saved_config.get("text_color", "#000000"),
                key=f"{key_prefix}tx_col_{self.plot_id}",
            )

        text_font_size = st.number_input(
            "Value Font Size",
            min_value=6,
            max_value=40,
            value=saved_config.get("text_font_size", 10),
            key=f"{key_prefix}tx_font_sz_{self.plot_id}",
        )

        text_rotation = st.slider(
            "Value Rotation",
            -90,
            90,
            saved_config.get("text_rotation", 0),
            15,
            key=f"{key_prefix}tx_rot_{self.plot_id}",
        )

        text_position = st.selectbox(
            "Value Position",
            options=["auto", "inside", "outside"],
            index=(
                ["auto", "inside", "outside"].index(saved_config.get("text_position", "auto"))
                if saved_config.get("text_position", "auto") in ["auto", "inside", "outside"]
                else 0
            ),
            key=f"{key_prefix}tx_pos_{self.plot_id}",
        )

        text_anchor = st.selectbox(
            "Value Anchor",
            options=["auto", "top", "middle", "bottom"],
            index=(
                ["auto", "top", "middle", "bottom"].index(saved_config.get("text_anchor", "auto"))
                if saved_config.get("text_anchor", "auto") in ["auto", "top", "middle", "bottom"]
                else 0
            ),
            key=f"{key_prefix}tx_anc_{self.plot_id}",
        )

        text_format = st.text_input(
            "Value Number Format (d3-format)",
            value=saved_config.get("text_format", ".2f"),
            key=f"{key_prefix}tx_fmt_{self.plot_id}",
            help="e.g. .2f for 2 decimals, .2s for scientific suffix, .1% for percentage.",
        )

        st.caption("Display Thresholds")
        text_display_logic = st.selectbox(
            "Display Logic",
            options=["all", "above_threshold", "below_threshold"],
            index=(
                ["all", "above_threshold", "below_threshold"].index(
                    saved_config.get("text_display_logic", "all")
                )
                if saved_config.get("text_display_logic", "all")
                in ["all", "above_threshold", "below_threshold"]
                else 0
            ),
            key=f"{key_prefix}tx_logic_{self.plot_id}",
        )

        text_threshold = 0.0
        if text_display_logic != "all":
            text_threshold = st.number_input(
                "Threshold Value",
                value=float(saved_config.get("text_threshold", 0.0)),
                key=f"{key_prefix}tx_thresh_{self.plot_id}",
            )

        text_constraint = st.selectbox(
            "Size Constraint",
            options=["none", "inside"],
            index=(
                ["none", "inside"].index(saved_config.get("text_constraint", "none"))
                if saved_config.get("text_constraint", "none") in ["none", "inside"]
                else 0
            ),
            key=f"{key_prefix}tx_const_{self.plot_id}",
            help="If inside, text will be resized or hidden to fit within the bars.",
        )

        return {
            "show_values": show_values,
            "text_color_mode": text_color_mode,
            "text_color": text_color,
            "text_font_size": text_font_size,
            "text_rotation": text_rotation,
            "text_position": text_position,
            "text_anchor": text_anchor,
            "text_format": text_format,
            "text_display_logic": text_display_logic,
            "text_threshold": text_threshold,
            "text_constraint": text_constraint,
        }
