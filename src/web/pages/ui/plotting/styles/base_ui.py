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

from src.core.services.visualization.palette_service import resolve_palette
from src.web.components.plotting.settings import (
    DataLabelsSettingsComponent,
    LayoutSettingsComponent,
    LegendSettingsComponent,
    TypographySettingsComponent,
)
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
        """Render layout sizing options.

        Delegates to :class:`LayoutSettingsComponent`.
        """
        component = LayoutSettingsComponent(self.plot_id, self.plot_type)
        return component.render(saved_config)

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
        """Render legend styling section.

        Delegates to :class:`LegendSettingsComponent`.
        """
        component = LegendSettingsComponent(self.plot_id, self.plot_type)
        return component._render_legend_section(saved_config, key_prefix)

    def _render_legend_position(
        self, saved_config: dict[str, Any], key_prefix: str, config_prefix: str
    ) -> dict[str, Any]:
        """Render legend position and orientation controls.

        Delegates to :class:`LegendSettingsComponent`.
        """
        component = LegendSettingsComponent(self.plot_id, self.plot_type)
        return component._render_legend_position(saved_config, key_prefix, config_prefix)

    def _render_legend_appearance(
        self, saved_config: dict[str, Any], key_prefix: str, config_prefix: str
    ) -> dict[str, Any]:
        """Render legend appearance controls (colors, border, fonts).

        Delegates to :class:`LegendSettingsComponent`.
        """
        component = LegendSettingsComponent(self.plot_id, self.plot_type)
        return component._render_legend_appearance(saved_config, key_prefix, config_prefix)

    def _render_legend_sizing(
        self, saved_config: dict[str, Any], key_prefix: str, config_prefix: str
    ) -> dict[str, Any]:
        """Render legend sizing and spacing controls.

        Delegates to :class:`LegendSettingsComponent`.
        """
        component = LegendSettingsComponent(self.plot_id, self.plot_type)
        return component._render_legend_sizing(saved_config, key_prefix, config_prefix)

    def _render_typography_section(
        self, saved_config: dict[str, Any], key_prefix: str
    ) -> dict[str, Any]:
        """Render typography section (font sizes and colors).

        Delegates to :class:`TypographySettingsComponent`.
        """
        component = TypographySettingsComponent(self.plot_id, self.plot_type)
        return component.render(saved_config, key_prefix=key_prefix)

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
        """Render UI for Data Values/Labels.

        Delegates to :class:`DataLabelsSettingsComponent`.
        """
        component = DataLabelsSettingsComponent(self.plot_id, self.plot_type)
        return component.render(saved_config, key_prefix=key_prefix)
