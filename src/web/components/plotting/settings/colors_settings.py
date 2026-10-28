"""Colors settings component — palettes, per-series overrides and backgrounds.

Usage::

    component = ColorsSettingsComponent(plot_id=1, plot_type="bar")
    config = component.render(saved_config, data=df)
"""

import copy
import json
from collections.abc import Callable
from typing import Any, cast

import pandas as pd
import streamlit as st
from matplotlib.colors import to_hex

from src.web.state.ui_state_manager import WidgetKeyBuilder

from src.core.services.visualization.palette_service import (
    get_palette_names,
    is_colorblind_safe,
    resolve_palette,
)
from src.core.services.visualization.accessibility_service import AccessibilityService
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
from src.core.models.plot_config import PlotConfig
from src.web.rendering._color_utils import css_color_to_matplotlib, picker_hex_color

PaletteValue = str | list[str] | tuple[str, ...]
_CUSTOM_PALETTE_LABEL = "Custom palette (saved)"


class ColorsSettingsComponent:
    """Render color palette, per-series overrides, and background settings.

    Parameters
    ----------
    plot_id : int
        Unique plot identifier for Streamlit widget keys.
    plot_type : str
        Plot type identifier (e.g. ``"bar"``, ``"line"``).
    """

    def __init__(
        self,
        plot_id: int,
        plot_type: str,
        *,
        series_renderer: Callable[[dict[str, Any], str], None] | None = None,
    ) -> None:
        self.plot_id = plot_id
        self.plot_type = plot_type
        self._series_renderer = series_renderer

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
        # [impl->req~ring5.figure.colors~1]
        # [impl->req~ring5.figure.accessible-themes~1]
        transition_key = WidgetKeyBuilder.plot_key(
            self.plot_id, "widgets.appearance._ring5_accessibility_mode_seen"
        )
        previous_accessibility_mode = bool(
            st.session_state.get(
                transition_key,
                saved_config.get("accessibility_mode", False),
            )
        )
        accessibility_mode = (
            toggle(
                "Accessible Theme",
                saved_config,
                "accessibility_mode",
                self.plot_id,
                widget_key=WidgetKeyBuilder.plot_key(
                    self.plot_id, "widgets.appearance.accessible_theme"
                ),
                help=(
                    "Use color-vision-safe defaults and add patterns or marker symbols so "
                    "series do not rely on color alone."
                ),
            )
            is True
        )
        accessibility_just_enabled = accessibility_mode and not previous_accessibility_mode
        st.session_state[transition_key] = accessibility_mode
        if accessibility_mode:
            st.info(
                "Accessible theme is active. Contrast and redundant encodings are checked below."
            )

        # Palette selector
        st.markdown("#### :material/palette: Color Palette")
        palette_names = get_palette_names()
        default_palette = "ring5_accessible" if accessibility_mode else "wong"
        palette_widget_key = WidgetKeyBuilder.plot_key(
            self.plot_id, "widgets.appearance.palette_select"
        )
        if accessibility_just_enabled:
            st.session_state[palette_widget_key] = default_palette
        saved_palette = (
            default_palette
            if accessibility_just_enabled
            else saved_config.get("color_palette", default_palette)
        )
        custom_palette = isinstance(saved_palette, (list, tuple))
        if not custom_palette and not isinstance(saved_palette, str):
            raise ValueError("A saved palette must be a name or an explicit color sequence.")
        current_palette = _CUSTOM_PALETTE_LABEL if custom_palette else saved_palette
        if current_palette not in palette_names:
            palette_names.insert(0, current_palette)
        palette_config = {**saved_config, "color_palette": current_palette}

        def _fmt_palette(name: str) -> str:
            label = name.replace("_", " ").title()
            if is_colorblind_safe(name):
                label = f"\u2713 {label}"
            return label

        selected_label = select_option(
            "Palette",
            palette_names,
            palette_config,
            "color_palette",
            self.plot_id,
            widget_key=palette_widget_key,
            default=current_palette,
            format_func=_fmt_palette,
            help=(
                "Palettes marked ✓ are color-vision-safe. RING-5 Accessible also meets the "
                "3:1 mark-contrast target on white."
            ),
        )

        selected_palette: PaletteValue = (
            copy.deepcopy(saved_palette) if selected_label == current_palette else selected_label
        )
        palette_colors = self._preview_palette(selected_palette)

        # Only projected hexadecimal colors enter inline CSS. Unsupported saved
        # literals remain editable without becoming additional CSS declarations.
        swatch_colors: list[str] = []
        for color in palette_colors:
            try:
                swatch_colors.append(to_hex(css_color_to_matplotlib(color), keep_alpha=True))
            except ValueError:
                st.text(f"Saved palette color (no swatch preview): {color}")
        swatch_html = " ".join(
            f'<span style="display:inline-block;width:20px;height:20px;'
            f"background:{color};border:1px solid #ccc;border-radius:3px;"
            f'margin-right:2px;"></span>'
            for color in swatch_colors
        )
        st.markdown(swatch_html, unsafe_allow_html=True)

        config: PlotConfig = {
            "color_palette": selected_palette,
            "accessibility_mode": accessibility_mode,
        }

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

        if accessibility_mode:
            config = AccessibilityService.apply_defaults(config, self.plot_type)
            series_count = max(
                1,
                len(self._get_unique_values(saved_config, data, items)),
            )
            report = AccessibilityService.audit(
                {**saved_config, **config},
                self.plot_type,
                series_count=series_count,
            )
            st.markdown("#### Accessibility Check")
            if report.passed:
                st.success(
                    "Accessibility check passed: palette, contrast, text, and non-color "
                    "encodings are ready."
                )
            else:
                st.error(f"Accessibility check found {report.issue_count} item(s) to resolve.")
            if report.findings:
                st.dataframe(report.to_frame(), width="stretch", hide_index=True)
        else:
            st.caption(
                "Turn on Accessible Theme to validate contrast and add redundant mark encodings."
            )

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
            key=WidgetKeyBuilder.plot_key(self.plot_id, "widgets.appearance.hm_rev_cs"),
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
        palette_name: PaletteValue | None = None,
    ) -> PlotConfig:
        """Render per-series colour pickers."""
        st.markdown("#### Series Colors")

        effective_palette = (
            palette_name if palette_name is not None else saved_config.get("color_palette", "wong")
        )

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
        current_palette: PaletteValue | None = None,
    ) -> dict[str, Any]:
        """Render colour pickers for each series item."""
        series_styles_raw = saved_config.get("series_styles", {})
        series_styles: dict[str, Any] = (
            copy.deepcopy(cast(dict[str, Any], series_styles_raw)) if series_styles_raw else {}
        )
        unique_vals = self._get_unique_values(saved_config, data, items)

        palette = (
            current_palette
            if current_palette is not None
            else saved_config.get("color_palette", "wong")
        )
        palette_colors = self._preview_palette(palette)
        if not palette_colors:
            return series_styles
        palette_key = (
            palette if isinstance(palette, str) else stable_widget_suffix(0, json.dumps(palette))
        )

        if unique_vals:
            for idx, val in enumerate(unique_vals):
                val_str = str(val)
                val_hash = stable_widget_suffix(idx, val_str)

                default_color = palette_colors[idx % len(palette_colors)]

                current_style = series_styles.get(val_str, {})

                c1, c2 = st.columns([1, 2])
                with c1:
                    st.markdown(f"**{val_str}**")
                with c2:
                    current_style = self._render_series_item(
                        default_color,
                        current_style,
                        val_hash,
                        key_prefix,
                        palette_key,
                    )

                series_styles[val_str] = current_style

        return series_styles

    def _render_series_item(
        self,
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

        picker_key = WidgetKeyBuilder.plot_key(
            self.plot_id, f"widgets.appearance.{key_prefix}color_{val_hash}_{palette_name}"
        )
        override_key = WidgetKeyBuilder.plot_key(
            self.plot_id, f"widgets.appearance.{key_prefix}use_col_{val_hash}"
        )

        with c2:
            color_picker(
                "Original",
                {"color": default_color},
                "color",
                self.plot_id,
                widget_key=WidgetKeyBuilder.plot_key(
                    self.plot_id,
                    f"widgets.appearance.{key_prefix}orig_col_{val_hash}_{palette_name}",
                ),
                disabled=True,
                label_visibility="collapsed",
            )
            st.caption(f"{default_color}")

            if st.button(
                "Rewind",
                key=WidgetKeyBuilder.plot_key(
                    self.plot_id, f"widgets.appearance.{key_prefix}rst_{val_hash}"
                ),
                help="Reset to palette color",
            ):
                current_style["use_color"] = False
                current_style["color"] = default_color

                try:
                    st.session_state[picker_key] = picker_hex_color(default_color)
                except ValueError:
                    st.session_state[f"{picker_key}.literal"] = default_color
                if override_key in st.session_state:
                    st.session_state[override_key] = False

                st.rerun()

        with c3:
            saved_col = current_style.get("color", default_color)
            new_color = color_picker(
                "Custom",
                {"color": saved_col},
                "color",
                self.plot_id,
                widget_key=picker_key,
                label_visibility="collapsed",
            )
            st.text(new_color)

            use_custom_raw = st.checkbox(
                "Override",
                value=current_style.get("use_color", False),
                key=override_key,
            )
            use_custom: bool = bool(use_custom_raw) if use_custom_raw is not None else False

            current_style["color"] = new_color
            current_style["use_color"] = use_custom
            if self._series_renderer is not None:
                self._series_renderer(current_style, val_hash)

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
            widget_key=WidgetKeyBuilder.plot_key(
                self.plot_id, f"widgets.appearance.{key_prefix}trans_bg"
            ),
            help="Make the plot background fully transparent.",
        )

        theme_cols1, theme_cols2 = st.columns(2)
        with theme_cols1:
            plot_bgcolor = color_picker(
                "Plot Background",
                saved_config,
                "plot_bgcolor",
                self.plot_id,
                widget_key=WidgetKeyBuilder.plot_key(
                    self.plot_id, f"widgets.appearance.{key_prefix}bg_plot"
                ),
                default="#ffffff",
                disabled=transparent_bg,
            )
            paper_bgcolor = color_picker(
                "Paper (Outer) Background",
                saved_config,
                "paper_bgcolor",
                self.plot_id,
                widget_key=WidgetKeyBuilder.plot_key(
                    self.plot_id, f"widgets.appearance.{key_prefix}bg_paper"
                ),
                default="#ffffff",
                disabled=transparent_bg,
            )

            grid_color = color_picker(
                "Grid Color",
                saved_config,
                "grid_color",
                self.plot_id,
                widget_key=WidgetKeyBuilder.plot_key(
                    self.plot_id, f"widgets.appearance.{key_prefix}grid_col"
                ),
                default="#e5e5e5",
            )

        with theme_cols2:
            axis_color = color_picker(
                "Axis Line/Tick Color",
                saved_config,
                "axis_color",
                self.plot_id,
                widget_key=WidgetKeyBuilder.plot_key(
                    self.plot_id, f"widgets.appearance.{key_prefix}axis_col"
                ),
                default="#444444",
            )
            axis_line_width = numeric_input(
                "Axis Line Width (px)",
                saved_config,
                "axis_line_width",
                self.plot_id,
                widget_key=WidgetKeyBuilder.plot_key(
                    self.plot_id, f"widgets.appearance.{key_prefix}axis_lw"
                ),
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
                    widget_key=WidgetKeyBuilder.plot_key(
                        self.plot_id, f"widgets.appearance.{key_prefix}stripes"
                    ),
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

    def _preview_palette(self, palette: PaletteValue) -> list[str]:
        """Preview a current palette without substituting for unavailable saved values."""
        if isinstance(palette, (list, tuple)):
            if palette and all(isinstance(color, str) and color.strip() for color in palette):
                return resolve_palette(palette)
        elif isinstance(palette, str) and any(
            name.lower() == palette.lower() for name in get_palette_names()
        ):
            return resolve_palette(palette)
        st.warning("The saved palette has no available preview. Choose a palette to replace it.")
        return []

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
