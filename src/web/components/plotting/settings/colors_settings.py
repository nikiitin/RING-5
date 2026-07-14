"""Colors settings component — palette, per-series overrides, backgrounds.

Extracted from ``BasePlot._section_colors()`` and
``BaseStyleUI._render_series_section()`` / ``_render_backgrounds_section()``
as a standalone component following the component-only architecture (P1, P9).

Usage::

    component = ColorsSettingsComponent(plot_id=1, plot_type="bar")
    config = component.render(saved_config, data=df)
"""

from typing import Any, cast

import pandas as pd
import streamlit as st

from src.core.models.visualization.palettes import PALETTE_REGISTRY
from src.core.services.visualization.palette_service import (
    get_palette_names,
    is_colorblind_safe,
    resolve_palette,
)
from src.web.components.common.bounded_options import (
    bounded_unique_strings,
    stable_widget_suffix,
)
from src.web.components.plotting.settings.widget_factory import (
    color_picker,
    numeric_input,
    select_option,
    toggle,
)
from src.web.models.plot_models import PlotConfig


class ColorsSettingsComponent:
    """Render color palette, per-series overrides, and background settings.

    Parameters
    ----------
    plot_id : int
        Unique plot identifier for Streamlit widget keys.
    plot_type : str
        Plot type identifier (e.g. ``"bar"``, ``"line"``).
    """

    def __init__(self, plot_id: int, plot_type: str) -> None:
        self.plot_id = plot_id
        self.plot_type = plot_type

    def render(
        self,
        saved_config: PlotConfig,
        data: pd.DataFrame | None = None,
        items: list[str] | None = None,
    ) -> PlotConfig:
        """Render palette selector, series colors, and backgrounds.

        Parameters
        ----------
        saved_config : PlotConfig
            Current saved configuration.
        data : pd.DataFrame | None
            Processed DataFrame for column discovery.
        items : list[str] | None
            Explicit series item names (optional).

        Returns
        -------
        PlotConfig
            Configuration dict with palette, series_styles, and background
            keys.
        """
        # Palette selector
        st.markdown("#### :material/palette: Color Palette")
        palette_names = get_palette_names()
        saved_palette = saved_config.get("color_palette", "wong")
        if isinstance(saved_palette, list):
            current_palette = next(
                (name for name, colors in PALETTE_REGISTRY.items() if colors == saved_palette),
                "wong",
            )
        elif isinstance(saved_palette, str):
            current_palette = saved_palette
        else:
            current_palette = "wong"
        palette_config = {**saved_config, "color_palette": current_palette}

        def _fmt_palette(name: str) -> str:
            label = name.replace("_", " ").title()
            if is_colorblind_safe(name):
                label = f"\u2713 {label}"
            return label

        selected_palette: str = select_option(
            "Palette",
            palette_names,
            palette_config,
            "color_palette",
            self.plot_id,
            widget_key=f"palette_select_{self.plot_id}",
            default="wong",
            format_func=_fmt_palette,
            help=("Palettes marked \u2713 are colorblind-safe." " Wong (default) is recommended."),
        )

        palette_colors = resolve_palette(selected_palette)

        # Preview swatches
        swatch_html = " ".join(
            f'<span style="display:inline-block;width:20px;height:20px;'
            f"background:{c};border:1px solid #ccc;border-radius:3px;"
            f'margin-right:2px;"></span>'
            for c in palette_colors
        )
        st.markdown(swatch_html, unsafe_allow_html=True)

        config: PlotConfig = {"color_palette": selected_palette}

        st.markdown("---")

        # Heatmap colorscale (only for heatmap plots)
        if self.plot_type == "heatmap":
            hm_config = self._render_heatmap_colorscale(saved_config)
            config.update(hm_config)
            st.markdown("---")

        # Series color overrides
        series_config = self._render_series_section(
            saved_config,
            data,
            items,
            key_prefix="theme_",
            palette_name=selected_palette,
        )
        config.update(series_config)

        st.markdown("---")

        # Backgrounds & Grid
        bg_config = self._render_backgrounds_section(saved_config, key_prefix="theme_")
        config.update(bg_config)

        return config

    # Heatmap colorscale

    def _render_heatmap_colorscale(self, saved_config: PlotConfig) -> PlotConfig:
        """Render heatmap-specific reverse colorscale toggle.

        The colorscale is derived from the selected palette (above).
        """
        st.markdown("#### Heatmap Color Scale")
        st.caption("The heatmap color scale is derived from the selected palette above.")

        reverse_colorscale: bool = st.checkbox(
            "Reverse Color Scale",
            value=saved_config.get("reverse_colorscale", False),
            key=f"hm_rev_cs_{self.plot_id}",
            help="Reverse the direction of the color scale.",
        )

        return {"reverse_colorscale": reverse_colorscale}

    # Series colors

    def _render_series_section(
        self,
        saved_config: PlotConfig,
        data: pd.DataFrame | None,
        items: list[str] | None,
        key_prefix: str,
        palette_name: str | None = None,
    ) -> PlotConfig:
        """Render per-series colour pickers."""
        st.markdown("#### Series Colors")

        effective_palette = palette_name or saved_config.get("color_palette", "wong")

        series_styles = self._render_series_colors(
            saved_config,
            data,
            items=items,
            key_prefix=key_prefix,
            current_palette=effective_palette,
        )

        st.markdown("---")
        return {"series_styles": series_styles}

    def _render_series_colors(
        self,
        saved_config: PlotConfig,
        data: pd.DataFrame | None = None,
        items: list[str] | None = None,
        key_prefix: str = "",
        current_palette: str | None = None,
    ) -> dict[str, Any]:
        """Render colour pickers for each series item."""
        series_styles_raw = saved_config.get("series_styles", {})
        series_styles: dict[str, Any] = (
            cast(dict[str, Any], series_styles_raw) if series_styles_raw else {}
        )
        unique_vals = self._get_unique_values(saved_config, data, items)

        palette_name = current_palette or saved_config.get("color_palette", "plotly")
        palette_colors = resolve_palette(palette_name)

        if unique_vals:
            for idx, val in enumerate(unique_vals):
                val_str = str(val)
                val_hash = stable_widget_suffix(idx, val_str)

                raw_color = palette_colors[idx % len(palette_colors)]
                # Lazy import to avoid circular dependency with styles package
                from src.web.pages.ui.plotting.styles.colors import to_hex

                default_color = to_hex(raw_color)

                current_style = series_styles.get(val_str, {})

                c1, c2 = st.columns([1, 2])
                with c1:
                    st.markdown(f"**{val_str}**")
                with c2:
                    current_style = self._render_series_item(
                        val_str,
                        default_color,
                        current_style,
                        val_hash,
                        key_prefix,
                        palette_name,
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
        """Render colour picker + override for one series item.

        Note: This method uses raw ``st.color_picker`` / ``st.checkbox``
        calls because each series item has dynamically computed widget keys
        that include content hashes — not suitable for the widget_factory
        which expects static config keys.
        """
        c2, c3 = st.columns([1, 2])

        picker_key = f"{key_prefix}color_{self.plot_id}_{val_hash}_{palette_name}"
        override_key = f"{key_prefix}use_col_{self.plot_id}_{val_hash}"

        with c2:
            st.color_picker(
                "Original",
                default_color,
                key=(f"{key_prefix}orig_col_{self.plot_id}" f"_{val_hash}_{palette_name}"),
                disabled=True,
                label_visibility="collapsed",
            )
            st.caption(f"{default_color}")

            if st.button(
                "Rewind",
                key=f"{key_prefix}rst_{self.plot_id}_{val_hash}",
                help="Reset to palette color",
            ):
                current_style["use_color"] = False
                current_style["color"] = default_color

                if picker_key in st.session_state:
                    st.session_state[picker_key] = default_color
                if override_key in st.session_state:
                    st.session_state[override_key] = False

                st.rerun()

        with c3:
            saved_col = current_style.get("color", default_color)
            new_color_raw = st.color_picker(
                "Custom",
                saved_col,
                key=picker_key,
                label_visibility="collapsed",
            )
            new_color: str = str(new_color_raw) if new_color_raw is not None else default_color
            st.caption(f"{new_color}")

            use_custom_raw = st.checkbox(
                "Override",
                value=current_style.get("use_color", False),
                key=override_key,
            )
            use_custom: bool = bool(use_custom_raw) if use_custom_raw is not None else False

            current_style["color"] = new_color
            current_style["use_color"] = use_custom

        return current_style

    # Backgrounds & Grid

    def _render_backgrounds_section(self, saved_config: PlotConfig, key_prefix: str) -> PlotConfig:
        """Render backgrounds and grid section."""
        st.markdown("#### Backgrounds & Grid")

        transparent_bg = toggle(
            "Transparent Background",
            saved_config,
            "transparent_bg",
            self.plot_id,
            widget_key=f"{key_prefix}trans_bg_{self.plot_id}",
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

            grid_color = color_picker(
                "Grid Color",
                saved_config,
                "grid_color",
                self.plot_id,
                widget_key=f"{key_prefix}grid_col_{self.plot_id}",
                default="#e5e5e5",
            )

        with theme_cols2:
            axis_color = color_picker(
                "Axis Line/Tick Color",
                saved_config,
                "axis_color",
                self.plot_id,
                widget_key=f"{key_prefix}axis_col_{self.plot_id}",
                default="#444444",
            )
            axis_line_width = numeric_input(
                "Axis Line Width (px)",
                saved_config,
                "axis_line_width",
                self.plot_id,
                widget_key=f"{key_prefix}axis_lw_{self.plot_id}",
                default=1.0,
                min_value=0.0,
                max_value=10.0,
                step=0.5,
                help="Width of the axis border lines.",
            )

            if "bar" in self.plot_type and "grouped_stacked" not in self.plot_type:
                enable_stripes = toggle(
                    "Enable Bar Stripes",
                    saved_config,
                    "enable_stripes",
                    self.plot_id,
                    widget_key=f"{key_prefix}stripes_{self.plot_id}",
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

    # Helpers

    def _get_unique_values(
        self,
        saved_config: PlotConfig,
        data: pd.DataFrame | None,
        items: list[str] | None,
    ) -> list[str]:
        """Determine series items for colour picker rendering."""
        unique_vals: list[str] = []
        if items is not None:
            unique_vals, _ = bounded_unique_strings(items)
        elif data is not None:
            legend_col = saved_config.get("color") or saved_config.get("group")
            y_cols = saved_config.get("y_columns", [])

            if legend_col and legend_col in data.columns:
                unique_vals, _ = bounded_unique_strings(data[legend_col])
            elif y_cols:
                unique_vals, _ = bounded_unique_strings(y_cols)
        return unique_vals
