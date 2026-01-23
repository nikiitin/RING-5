import hashlib
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st


class BaseStyleUI:
    """
    Base Strategy Logic for generic UI rendering.
    """

    def __init__(self, plot_id: int, plot_type: str):
        self.plot_id = plot_id
        self.plot_type = plot_type

    def render_layout_options(self, saved_config: Dict[str, Any]) -> Dict[str, Any]:
        """Render layout sizing, margins, and spacing options."""
        st.markdown("**Dimensions & Margins**")

        c1, c2 = st.columns(2)
        with c1:
            width = st.slider(
                "Width (px)", 400, 1600, saved_config.get("width", 800), 50, key=f"w_{self.plot_id}"
            )
        with c2:
            height = st.slider(
                "Height (px)",
                300,
                1200,
                saved_config.get("height", 500),
                50,
                key=f"h_{self.plot_id}",
            )

        with st.expander("Margins & Spacing", expanded=True):
            m1, m2 = st.columns(2)
            with m1:
                margin_l = st.number_input(
                    "Left", 0, 1000, saved_config.get("margin_l", 100), key=f"ml_{self.plot_id}"
                )
                margin_r = st.number_input(
                    "Right", 0, 1000, saved_config.get("margin_r", 100), key=f"mr_{self.plot_id}"
                )
                margin_pad = st.number_input(
                    "Padding (px)",
                    0,
                    200,
                    saved_config.get("margin_pad", 0),
                    key=f"mp_{self.plot_id}",
                    help="Space between axis and labels",
                )
            with m2:
                margin_t = st.number_input(
                    "Top", 0, 1000, saved_config.get("margin_t", 80), key=f"mt_{self.plot_id}"
                )
                margin_b = st.number_input(
                    "Bottom", 0, 1000, saved_config.get("margin_b", 120), key=f"mb_{self.plot_id}"
                )
                automargin = st.checkbox(
                    "Auto-Marg (Prevents Cutoff)",
                    value=saved_config.get("automargin", True),
                    key=f"am_{self.plot_id}",
                )

        return {
            "width": width,
            "height": height,
            "margin_l": margin_l,
            "margin_r": margin_r,
            "margin_t": margin_t,
            "margin_b": margin_b,
            "margin_pad": margin_pad,
            "automargin": automargin,
        }

    def render_style_ui(
        self,
        saved_config: Dict[str, Any],
        data: Optional[pd.DataFrame] = None,
        items: Optional[List[str]] = None,
        key_prefix: str = "",
    ) -> Dict[str, Any]:
        """
        Render style configurator UI (Theme, Colors, Fonts).
        Delegates to specific render methods for each section.
        """
        # 1. Series Colors
        series_config = self._render_series_section(saved_config, data, items, key_prefix)

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
        saved_config: Dict[str, Any],
        data: Optional[pd.DataFrame],
        items: Optional[List[str]],
        key_prefix: str,
    ) -> Dict[str, Any]:
        """Render series colors section."""
        st.markdown("#### Series Colors")

        available_palettes = [
            "Plotly",
            "G10",
            "T10",
            "Alphabet",
            "Dark24",
            "Light24",
            "Pastel",
            "Set1",
            "Set2",
            "Set3",
            "Tableau",
            "Safe",
            "Vivid",
        ]

        current_palette = saved_config.get("color_palette", "Plotly")
        if current_palette not in available_palettes:
            current_palette = "Plotly"

        color_palette = st.selectbox(
            "Select Color Palette",
            options=available_palettes,
            index=available_palettes.index(current_palette),
            key=f"{key_prefix}palette_{self.plot_id}",
            help="Choose a color scheme for the plot series/groups.",
        )

        series_styles = self.render_series_colors_ui(
            saved_config, data, items=items, key_prefix=key_prefix, current_palette=color_palette
        )

        st.markdown("---")

        return {"color_palette": color_palette, "series_styles": series_styles}

    def _render_backgrounds_section(
        self, saved_config: Dict[str, Any], key_prefix: str
    ) -> Dict[str, Any]:
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
            "enable_stripes": enable_stripes,
        }

    def _render_legend_section(
        self, saved_config: Dict[str, Any], key_prefix: str
    ) -> Dict[str, Any]:
        """Render legend styling section."""
        st.markdown("#### Legend Styling")

        # Position & Orientation
        pos_config = self._render_legend_position(saved_config, key_prefix)

        # Appearance
        app_config = self._render_legend_appearance(saved_config, key_prefix)

        # Sizing & Spacing
        sz_config = self._render_legend_sizing(saved_config, key_prefix)

        return {**pos_config, **app_config, **sz_config}

    def _render_legend_position(
        self, saved_config: Dict[str, Any], key_prefix: str
    ) -> Dict[str, Any]:
        """Render legend position and orientation controls."""
        st.markdown("**Position & Orientation**")
        pos_c1, pos_c2, pos_c3 = st.columns(3)

        with pos_c1:
            legend_orientation = st.selectbox(
                "Orientation",
                options=["v", "h"],
                format_func=lambda x: "Vertical" if x == "v" else "Horizontal",
                index=0 if saved_config.get("legend_orientation", "v") == "v" else 1,
                key=f"{key_prefix}leg_orient_{self.plot_id}",
            )

            legend_ncols = st.number_input(
                "Columns",
                min_value=0,
                max_value=10,
                value=saved_config.get("legend_ncols", 0),
                key=f"{key_prefix}leg_cols_{self.plot_id}",
                help="Number of legend columns. Uses multiple legend objects positioned side-by-side. 0 = Auto (single column).",
            )

            legend_col_width = st.number_input(
                "Column Width (px)",
                min_value=0,
                max_value=500,
                value=saved_config.get("legend_col_width", 150),
                key=f"{key_prefix}leg_col_width_{self.plot_id}",
                help="Width of each legend column in pixels.",
            )

            legend_valign = st.selectbox(
                "Vertical Align",
                options=["middle", "top", "bottom"],
                index=["middle", "top", "bottom"].index(
                    saved_config.get("legend_valign", "middle")
                ),
                key=f"{key_prefix}leg_valign_{self.plot_id}",
            )

        with pos_c2:
            legend_x = st.number_input(
                "X Pos",
                value=float(saved_config.get("legend_x", 1.02)),
                step=0.05,
                key=f"{key_prefix}leg_x_sm_{self.plot_id}",
            )
            legend_xanchor = st.selectbox(
                "X Anchor",
                options=["auto", "left", "center", "right"],
                index=["auto", "left", "center", "right"].index(
                    saved_config.get("legend_xanchor", "auto")
                ),
                key=f"{key_prefix}leg_xanc_{self.plot_id}",
            )

        with pos_c3:
            legend_y = st.number_input(
                "Y Pos",
                value=float(saved_config.get("legend_y", 1.0)),
                step=0.05,
                key=f"{key_prefix}leg_y_sm_{self.plot_id}",
            )
            legend_yanchor = st.selectbox(
                "Y Anchor",
                options=["auto", "top", "middle", "bottom"],
                index=["auto", "top", "middle", "bottom"].index(
                    saved_config.get("legend_yanchor", "auto")
                ),
                key=f"{key_prefix}leg_yanc_{self.plot_id}",
            )

        return {
            "legend_orientation": legend_orientation,
            "legend_ncols": legend_ncols,
            "legend_col_width": legend_col_width,
            "legend_valign": legend_valign,
            "legend_x": legend_x,
            "legend_xanchor": legend_xanchor,
            "legend_y": legend_y,
            "legend_yanchor": legend_yanchor,
        }

    def _render_legend_appearance(
        self, saved_config: Dict[str, Any], key_prefix: str
    ) -> Dict[str, Any]:
        """Render legend appearance controls (colors, border, fonts)."""
        st.markdown("**Appearance**")
        app_c1, app_c2 = st.columns(2)

        with app_c1:
            bg_col = saved_config.get("legend_bgcolor", "#ffffff")
            if str(bg_col).startswith("rgba"):
                bg_col = "#ffffff"

            transparent_legend = st.checkbox(
                "Transparent Background",
                value=saved_config.get("transparent_legend", False),
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
                saved_config.get("legend_border_color", "#000000"),
                key=f"{key_prefix}leg_bord_col_{self.plot_id}",
            )
            legend_border_width = st.number_input(
                "Border Width",
                min_value=0,
                max_value=5,
                value=saved_config.get("legend_border_width", 0),
                key=f"{key_prefix}leg_bord_wd_{self.plot_id}",
            )

        with app_c2:
            st.caption("Font")
            legend_font_color = st.color_picker(
                "Text Color",
                saved_config.get("legend_font_color", "#000000"),
                key=f"{key_prefix}leg_font_col_{self.plot_id}",
            )
            legend_font_size = st.number_input(
                "Font Size",
                min_value=8,
                max_value=100,
                value=saved_config.get("legend_font_size", 12),
                key=f"{key_prefix}leg_font_sz_{self.plot_id}",
            )

            st.caption("Title Font")
            legend_title_font_color = st.color_picker(
                "Title Color",
                saved_config.get("legend_title_font_color", "#000000"),
                key=f"{key_prefix}leg_title_col_{self.plot_id}",
            )
            legend_title_font_size = st.number_input(
                "Title Size",
                min_value=8,
                max_value=100,
                value=saved_config.get("legend_title_font_size", 14),
                key=f"{key_prefix}leg_title_sz_{self.plot_id}",
            )

        return {
            "transparent_legend": transparent_legend,
            "legend_bgcolor": legend_bgcolor,
            "legend_border_color": legend_border_color,
            "legend_border_width": legend_border_width,
            "legend_font_color": legend_font_color,
            "legend_font_size": legend_font_size,
            "legend_title_font_color": legend_title_font_color,
            "legend_title_font_size": legend_title_font_size,
        }

    def _render_legend_sizing(
        self, saved_config: Dict[str, Any], key_prefix: str
    ) -> Dict[str, Any]:
        """Render legend sizing and spacing controls."""
        st.markdown("**Sizing & Spacing**")
        sz_c1, sz_c2 = st.columns(2)

        with sz_c1:
            legend_itemsizing = st.selectbox(
                "Marker Scale",
                options=["constant", "trace"],
                index=0 if saved_config.get("legend_itemsizing", "constant") == "constant" else 1,
                key=f"{key_prefix}leg_item_sz_{self.plot_id}",
                help="Constant: markers are equal size. Trace: markers match plot size.",
            )
            legend_itemwidth = st.number_input(
                "Marker Width (px)",
                min_value=0,
                max_value=120,
                value=(
                    saved_config.get("legend_itemwidth")
                    if saved_config.get("legend_itemwidth") is not None
                    else 30
                ),
                key=f"{key_prefix}leg_item_wd_{self.plot_id}",
                help="Width of the legend items (default 30). Set to 0 for auto.",
            )
            legend_tracegroupgap = st.number_input(
                "Item Spacing (px)",
                min_value=0,
                max_value=100,
                value=saved_config.get("legend_tracegroupgap", 10),
                key=f"{key_prefix}leg_gap_{self.plot_id}",
                help="Vertical spacing between legend items.",
            )

        return {
            "legend_itemsizing": legend_itemsizing,
            "legend_itemwidth": (
                legend_itemwidth
                if (legend_itemwidth is not None and legend_itemwidth > 0)
                else None
            ),
            "legend_tracegroupgap": legend_tracegroupgap,
        }

    def _render_typography_section(
        self, saved_config: Dict[str, Any], key_prefix: str
    ) -> Dict[str, Any]:
        """Render typography section (titles and labels)."""
        st.markdown("#### Typography (Titles & Labels)")
        typo_c1, typo_c2 = st.columns(2)

        with typo_c1:
            plot_title = st.text_input(
                "Main Plot Title",
                value=saved_config.get("title", ""),
                key=f"{key_prefix}plot_title_{self.plot_id}",
            )
            title_font_size = st.number_input(
                "Plot Title Font Size",
                min_value=8,
                max_value=100,
                value=saved_config.get("title_font_size", 18),
                key=f"{key_prefix}title_sz_{self.plot_id}",
            )

            xaxis_title = st.text_input(
                "X-Axis Title",
                value=saved_config.get("xaxis_title", ""),
                key=f"{key_prefix}xaxis_title_{self.plot_id}",
            )
            xaxis_title_font_size = st.number_input(
                "X-Axis Title Font Size",
                min_value=8,
                max_value=100,
                value=saved_config.get("xaxis_title_font_size", 14),
                key=f"{key_prefix}xaxis_title_sz_{self.plot_id}",
            )

            yaxis_title = st.text_input(
                "Y-Axis Title",
                value=saved_config.get("yaxis_title", ""),
                key=f"{key_prefix}yaxis_title_{self.plot_id}",
            )
            yaxis_title_font_size = st.number_input(
                "Y-Axis Title Font Size",
                min_value=8,
                max_value=100,
                value=saved_config.get("yaxis_title_font_size", 14),
                key=f"{key_prefix}yaxis_title_sz_{self.plot_id}",
            )

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
                help="Move title up (+) or down (-) along the axis. Note: Disables native auto-margins for title.",
            )

        with typo_c2:
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

        return {
            "title": plot_title,
            "title_font_size": title_font_size,
            "xaxis_title": xaxis_title,
            "xaxis_title_font_size": xaxis_title_font_size,
            "yaxis_title": yaxis_title,
            "yaxis_title_font_size": yaxis_title_font_size,
            "yaxis_title_standoff": yaxis_title_standoff,
            "yaxis_title_vshift": yaxis_title_vshift,
            "xaxis_tickfont_size": xaxis_tickfont_size,
            "xaxis_tickfont_color": xaxis_tickfont_color,
            "yaxis_tickfont_size": yaxis_tickfont_size,
            "yaxis_tickfont_color": yaxis_tickfont_color,
        }

    def render_series_colors_ui(
        self,
        saved_config: Dict[str, Any],
        data: Optional[pd.DataFrame] = None,
        items: Optional[List[str]] = None,
        key_prefix: str = "",
        current_palette: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Render UI for per-series coloring.
        """
        series_styles = saved_config.get("series_styles", {})
        unique_vals = self._get_unique_values(saved_config, data, items)

        # Use current selection if available, else saved config
        palette_name = current_palette or saved_config.get("color_palette", "plotly")

        from src.plotting.styles.colors import get_palette_colors, to_hex

        palette_colors = get_palette_colors(palette_name)

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
        current_style: Dict[str, Any],
        val_hash: str,
        key_prefix: str = "",
        palette_context: str = "",
    ):
        c2, c3 = st.columns([1, 2])

        # Keys for widgets
        picker_key = f"{key_prefix}color_{self.plot_id}_{val_hash}"
        override_key = f"{key_prefix}use_col_{self.plot_id}_{val_hash}"

        with c2:
            st.color_picker(
                "Original",
                default_color,
                key=f"{key_prefix}orig_col_{self.plot_id}_{val_hash}_{palette_context}",
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
            new_color = st.color_picker(
                "Custom", saved_col, key=picker_key, label_visibility="collapsed"
            )
            st.caption(f"{new_color}")

            use_custom = st.checkbox(
                "Override", value=current_style.get("use_color", False), key=override_key
            )

            current_style["color"] = new_color
            current_style["use_color"] = use_custom

            # specific visuals (Symbols, Patterns, etc)
            self._render_specific_series_visuals(current_style, val_hash, key_prefix=key_prefix)

        return current_style

    def _render_specific_series_visuals(
        self, current_style: Dict[str, Any], key_suffix: str, key_prefix: str = ""
    ):
        """Hook for subclasses to render specific style options."""
        pass

    def render_series_renaming_ui(
        self,
        saved_config: Dict[str, Any],
        data: Optional[pd.DataFrame] = None,
        items: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Render UI for per-series renaming.
        """
        series_styles = saved_config.get("series_styles", {})
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
                    new_name = st.text_input(
                        "Display Name",
                        value=current_style.get("name", val_str),
                        key=f"name_{self.plot_id}_{val_hash}",
                        label_visibility="collapsed",
                        placeholder=val_str,
                    )
                    current_style["name"] = new_name

                series_styles[val_str] = current_style

        return series_styles

    def render_xaxis_labels_ui(
        self,
        saved_config: Dict[str, Any],
        data: Optional[pd.DataFrame] = None,
        key_prefix: str = "xlabel",
    ) -> Dict[str, str]:
        """
        Render UI for X-Axis label renaming.
        """
        xaxis_labels = saved_config.get("xaxis_labels", {})
        x_col = saved_config.get("x")

        if data is not None and x_col and x_col in data.columns:
            st.markdown("#### X-Axis Label Overrides")
            with st.expander("Rename X-Axis Labels"):
                unique_x_raw = data[x_col].unique()
                unique_x = sorted(unique_x_raw, key=lambda x: str(x))

                if len(unique_x) > 50:
                    st.warning("Too many X-axis values to list all. Showing first 50.")
                    unique_x = unique_x[:50]

                for val in unique_x:
                    s_val = str(val)
                    import hashlib

                    val_hash = hashlib.md5(s_val.encode(), usedforsecurity=False).hexdigest()[:8]

                    col_l, col_r = st.columns([1, 2])
                    with col_l:
                        st.markdown(f"**{val}**")
                    with col_r:
                        new_label = st.text_input(
                            "Display As",
                            value=xaxis_labels.get(s_val, ""),
                            key=f"{key_prefix}_{self.plot_id}_{val_hash}",
                            label_visibility="collapsed",
                            placeholder=s_val,
                        )
                        if new_label and new_label != s_val:
                            xaxis_labels[s_val] = new_label
                        elif s_val in xaxis_labels:
                            del xaxis_labels[s_val]

        return xaxis_labels

    def _get_unique_values(self, saved_config, data, items) -> List[Any]:
        """Helper to determine series items."""
        unique_vals = []
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
        self, saved_config: Dict[str, Any], key_prefix: str = ""
    ) -> Dict[str, Any]:
        """
        Render UI for Data Values/Labels.
        """
        st.markdown("#### Data Labels")

        show_values = st.checkbox(
            "Show Values",
            value=saved_config.get("show_values", False),
            key=f"{key_prefix}show_vals_{self.plot_id}",
            help="Display data values on the bars/points.",
        )

        config_update = {"show_values": show_values}

        if show_values:
            c1, c2 = st.columns(2)
            with c1:
                text_position = st.selectbox(
                    "Position",
                    options=["auto", "inside", "outside"],
                    index=["auto", "inside", "outside"].index(
                        saved_config.get("text_position") or "auto"
                    ),
                    key=f"{key_prefix}txt_pos_{self.plot_id}",
                )

                # Show Anchor only if inside
                if text_position == "inside":
                    text_anchor = st.selectbox(
                        "Anchor (Inside)",
                        options=["auto", "start", "middle", "end"],
                        index=["auto", "start", "middle", "end"].index(
                            saved_config.get("text_anchor") or "auto"
                        ),
                        key=f"{key_prefix}txt_anc_{self.plot_id}",
                        help="Start=Bottom/Left, End=Top/Right",
                    )
                else:
                    text_anchor = None

            with c2:
                # Text Color Mode
                color_mode = st.radio(
                    "Color Mode",
                    options=["Custom", "Auto Contrast"],
                    index=0 if saved_config.get("text_color_mode", "Custom") == "Custom" else 1,
                    horizontal=True,
                    key=f"{key_prefix}txt_mode_{self.plot_id}",
                    help="Auto Contrast flips text color (black/white) based on bar brightness.",
                )

                if color_mode == "Custom":
                    text_color = st.color_picker(
                        "Text Color",
                        saved_config.get("text_color", "#000000"),
                        key=f"{key_prefix}txt_col_{self.plot_id}",
                    )
                else:
                    text_color = None  # handled in applicator

                text_font_size = st.number_input(
                    "Font Size",
                    value=int(saved_config.get("text_font_size") or 12),
                    min_value=6,
                    max_value=100,
                    step=1,
                    key=f"{key_prefix}txt_fs_{self.plot_id}",
                )

                text_rotation = st.number_input(
                    "Rotation",
                    value=int(saved_config.get("text_rotation") or 0),
                    min_value=-360,
                    max_value=360,
                    step=90,
                    key=f"{key_prefix}txt_rot_{self.plot_id}",
                )

                text_format = st.text_input(
                    "Format Template",
                    value=saved_config.get("text_format", "%{y:.2f}"),
                    key=f"{key_prefix}txt_fmt_{self.plot_id}",
                    help="Plotly d3 formatting. e.g. %{y:.2f} for 2 decimals.",
                )

                # Conditional Display
                display_logic = st.selectbox(
                    "Display Logic",
                    options=["Always Show", "If > Threshold"],
                    index=["Always Show", "If > Threshold"].index(
                        saved_config.get("text_display_logic") or "Always Show"
                    ),
                    key=f"{key_prefix}txt_logic_{self.plot_id}",
                )

                threshold = 0.0
                if display_logic == "If > Threshold":
                    threshold = st.number_input(
                        "Threshold Value",
                        value=float(saved_config.get("text_threshold") or 0.0),
                        key=f"{key_prefix}txt_thresh_{self.plot_id}",
                    )

                text_constraint = st.checkbox(
                    "Constrain to Bar",
                    value=saved_config.get("text_constraint", False),
                    key=f"{key_prefix}txt_constrain_{self.plot_id}",
                    help="Force text to fit inside the bar (prevents overlap).",
                )

            config_update.update(
                {
                    "text_position": text_position,
                    "text_anchor": text_anchor,
                    "text_color_mode": color_mode,
                    "text_color": text_color,
                    "text_font_size": text_font_size,
                    "text_rotation": text_rotation,
                    "text_format": text_format,
                    "text_display_logic": display_logic,
                    "text_threshold": threshold,
                    "text_constraint": text_constraint,
                }
            )

        return config_update
