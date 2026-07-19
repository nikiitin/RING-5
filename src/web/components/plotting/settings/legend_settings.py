"""Legend settings component — primary, secondary, and tertiary legends.

Extracted from ``BasePlot._section_legends()`` and
``BaseStyleUI._render_legend_section()`` / sub-methods as a standalone
component following the component-only architecture (P1, P9).

The component renders a nested pills navigation for primary/secondary/
tertiary legends and delegates to position, appearance, and sizing
sub-renderers.

Usage::

    component = LegendSettingsComponent(plot_id=1, plot_type="bar")
    config = component.render(
        saved_config,
        has_secondary=True,
        has_tertiary=False,
    )
"""

import streamlit as st

from src.web.components.plotting.settings.widget_factory import (
    color_picker,
    numeric_input,
    select_option,
    toggle,
)
from src.web.models.plot_models import PlotConfig

# Canonical mapping of legend tier to config-key prefix.
_LEGEND_PREFIXES: dict[str, str] = {
    "primary": "legend_",
    "secondary": "legend2_",
    "tertiary": "legend3_",
}

# Mapping of legend tier to Streamlit widget-key prefix.
_LEGEND_KEY_PREFIXES: dict[str, str] = {
    "primary": "theme_",
    "secondary": "legend2_",
    "tertiary": "legend3_",
}


class LegendSettingsComponent:
    """Render legend configuration with multi-level pills navigation.

    Parameters
    ----------
    plot_id : int
        Unique plot identifier for Streamlit widget keys.
    plot_type : str
        Plot type identifier.
    """

    def __init__(self, plot_id: int, plot_type: str) -> None:
        self.plot_id = plot_id
        self.plot_type = plot_type

    def render(
        self,
        saved_config: PlotConfig,
        has_secondary: bool = False,
        has_tertiary: bool = False,
    ) -> PlotConfig:
        """Render legend pills navigation and settings.

        Parameters
        ----------
        saved_config : PlotConfig
            Current saved configuration.
        has_secondary : bool
            Whether to show a secondary legend pill.
        has_tertiary : bool
            Whether to show a tertiary legend pill.

        Returns
        -------
        PlotConfig
            Legend configuration keys (prefixed per legend level).
        """
        # [impl->req~ring5.figure.legends~1]
        _labels: dict[str, str] = {
            "primary": ":material/legend_toggle: Primary",
        }
        if has_secondary:
            _labels["secondary"] = ":material/legend_toggle: Secondary"
        if has_tertiary:
            _labels["tertiary"] = ":material/legend_toggle: Tertiary"

        legend_tab: str | None = st.pills(
            "Legend",
            options=list(_labels.keys()),
            format_func=lambda x: _labels.get(x, str(x)),
            selection_mode="single",
            key=f"legend_nav_{self.plot_id}",
            default="primary",
        )

        key_prefix = _LEGEND_KEY_PREFIXES.get(legend_tab or "primary", "theme_")

        # Render the active pill's widgets
        active_config = self._render_legend_section(saved_config, key_prefix)

        # Preserve inactive pills' config from saved_config so that
        # switching pills doesn't lose previously-set values.
        active_tab = legend_tab or "primary"

        preserved: PlotConfig = {}
        for level, cfg_prefix in _LEGEND_PREFIXES.items():
            if level == active_tab:
                continue
            # Only preserve if the level is available
            if level == "secondary" and not has_secondary:
                continue
            if level == "tertiary" and not has_tertiary:
                continue
            # Copy all keys with this prefix from saved_config
            for key, value in saved_config.items():
                if key.startswith(cfg_prefix):
                    preserved[key] = value

        return {**preserved, **active_config}

    # Legend section rendering

    def _render_legend_section(self, saved_config: PlotConfig, key_prefix: str) -> PlotConfig:
        """Render legend styling section for the selected prefix."""
        config_prefix = "legend_" if key_prefix == "theme_" else key_prefix
        is_heatmap = self.plot_type == "heatmap"

        if is_heatmap:
            st.markdown("#### Colorbar Styling")
            pos_config = self._render_legend_position(saved_config, key_prefix, config_prefix)
            app_config = self._render_legend_appearance(saved_config, key_prefix, config_prefix)
            cbar_config = self._render_colorbar_settings(saved_config, key_prefix, config_prefix)
            return {**pos_config, **app_config, **cbar_config}

        st.markdown("#### Legend Styling")

        pos_config = self._render_legend_position(saved_config, key_prefix, config_prefix)
        app_config = self._render_legend_appearance(saved_config, key_prefix, config_prefix)
        sz_config = self._render_legend_sizing(saved_config, key_prefix, config_prefix)

        return {**pos_config, **app_config, **sz_config}

    def _render_legend_position(
        self,
        saved_config: PlotConfig,
        key_prefix: str,
        config_prefix: str,
    ) -> PlotConfig:
        """Render legend position controls."""
        st.markdown("**Position**")
        pos_c1, pos_c2 = st.columns(2)

        with pos_c1:
            legend_x = numeric_input(
                "X Position",
                saved_config,
                f"{config_prefix}x",
                self.plot_id,
                widget_key=f"{key_prefix}leg_x_{self.plot_id}",
                default=1.02 if config_prefix == "legend_" else 1.0,
                step=0.05,
                format="%.2f",
                help=(
                    "Horizontal position on the plot area. "
                    "0.0 = left edge, 1.0 = right edge. "
                    "Values > 1.0 place the legend outside the plot."
                ),
            )

        with pos_c2:
            legend_y = numeric_input(
                "Y Position",
                saved_config,
                f"{config_prefix}y",
                self.plot_id,
                widget_key=f"{key_prefix}leg_y_{self.plot_id}",
                default=1.0,
                step=0.05,
                format="%.2f",
                help=(
                    "Vertical position on the plot area. "
                    "0.0 = bottom edge, 1.0 = top edge. "
                    "Values > 1.0 place the legend above the plot."
                ),
            )

        st.caption(
            "Position (0, 0) = bottom-left, (1, 1) = top-right. "
            "Values outside 0\u20131 place the legend outside the plot area."
        )

        orientation = select_option(
            "Orientation",
            ["vertical", "horizontal"],
            saved_config,
            f"{config_prefix}orientation",
            self.plot_id,
            widget_key=f"{key_prefix}leg_orient_{self.plot_id}",
            default="vertical",
        )

        return {
            f"{config_prefix}x": legend_x,
            f"{config_prefix}y": legend_y,
            f"{config_prefix}orientation": orientation,
        }

    def _render_legend_appearance(
        self,
        saved_config: PlotConfig,
        key_prefix: str,
        config_prefix: str,
    ) -> PlotConfig:
        """Render legend appearance controls (colors, border, fonts).

        For heatmap plots, only colorbar title controls are shown since
        heatmaps use a continuous colorbar instead of a discrete legend.
        """
        is_heatmap = self.plot_type == "heatmap"

        if is_heatmap:
            st.markdown("**Colorbar Title**")
            legend_title = st.text_area(
                "Title",
                value=saved_config.get(f"{config_prefix}title", ""),
                key=f"{key_prefix}leg_title_txt_{self.plot_id}",
                height=68,
            )
            t_c1, t_c2 = st.columns(2)
            with t_c1:
                legend_title_font_color = color_picker(
                    "Title Color",
                    saved_config,
                    f"{config_prefix}title_font_color",
                    self.plot_id,
                    widget_key=f"{key_prefix}leg_title_col_{self.plot_id}",
                )
            with t_c2:
                legend_title_font_size = numeric_input(
                    "Title Size",
                    saved_config,
                    f"{config_prefix}title_font_size",
                    self.plot_id,
                    widget_key=f"{key_prefix}leg_title_sz_{self.plot_id}",
                    default=14,
                    min_value=8,
                    max_value=100,
                )
            return {
                f"{config_prefix}title": legend_title,
                f"{config_prefix}title_font_color": legend_title_font_color,
                f"{config_prefix}title_font_size": legend_title_font_size,
            }

        st.markdown("**Appearance**")
        app_c1, app_c2 = st.columns(2)

        with app_c1:
            bg_col = saved_config.get(f"{config_prefix}bgcolor", "#ffffff")
            if str(bg_col).startswith("rgba"):
                bg_col = "#ffffff"

            transparent_legend = toggle(
                "Transparent Background",
                saved_config,
                f"{config_prefix}transparent",
                self.plot_id,
                widget_key=f"{key_prefix}trans_leg_{self.plot_id}",
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
            legend_border_color = color_picker(
                "Border Color",
                saved_config,
                f"{config_prefix}border_color",
                self.plot_id,
                widget_key=f"{key_prefix}leg_bord_col_{self.plot_id}",
            )
            legend_border_width = numeric_input(
                "Border Width",
                saved_config,
                f"{config_prefix}border_width",
                self.plot_id,
                widget_key=f"{key_prefix}leg_bord_wd_{self.plot_id}",
                default=0,
                min_value=0,
                max_value=5,
            )

        with app_c2:
            st.caption("Font")
            legend_font_color = color_picker(
                "Text Color",
                saved_config,
                f"{config_prefix}font_color",
                self.plot_id,
                widget_key=f"{key_prefix}leg_font_col_{self.plot_id}",
            )
            legend_font_size = numeric_input(
                "Font Size",
                saved_config,
                f"{config_prefix}font_size",
                self.plot_id,
                widget_key=f"{key_prefix}leg_font_sz_{self.plot_id}",
                default=12,
                min_value=8,
                max_value=100,
            )

            st.caption("Title Font")
            legend_title = st.text_input(
                "Legend Title",
                value=saved_config.get(f"{config_prefix}title", ""),
                key=f"{key_prefix}leg_title_txt_{self.plot_id}",
            )
            legend_title_font_color = color_picker(
                "Title Color",
                saved_config,
                f"{config_prefix}title_font_color",
                self.plot_id,
                widget_key=f"{key_prefix}leg_title_col_{self.plot_id}",
            )
            legend_title_font_size = numeric_input(
                "Title Size",
                saved_config,
                f"{config_prefix}title_font_size",
                self.plot_id,
                widget_key=f"{key_prefix}leg_title_sz_{self.plot_id}",
                default=14,
                min_value=8,
                max_value=100,
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
        self,
        saved_config: PlotConfig,
        key_prefix: str,
        config_prefix: str,
    ) -> PlotConfig:
        """Render legend sizing and spacing controls."""
        st.markdown("**Sizing & Spacing**")

        ncols = numeric_input(
            "Columns",
            saved_config,
            f"{config_prefix}ncols",
            self.plot_id,
            widget_key=f"{key_prefix}leg_ncols_{self.plot_id}",
            default=0,
            min_value=0,
            max_value=20,
            help=(
                "Number of legend columns. "
                "0 = single column (default). "
                "When > 1, entry width is auto-computed unless "
                "you set it manually below."
            ),
        )

        sz_c1, sz_c2 = st.columns(2)
        with sz_c1:
            tracegroupgap = numeric_input(
                "Item Spacing (px)",
                saved_config,
                f"{config_prefix}tracegroupgap",
                self.plot_id,
                widget_key=f"{key_prefix}leg_tracegap_{self.plot_id}",
                default=10,
                min_value=-20,
                max_value=200,
                help="Vertical spacing between legend items.",
            )
            column_spacing = numeric_input(
                "Column Spacing",
                saved_config,
                f"{config_prefix}column_spacing",
                self.plot_id,
                widget_key=f"{key_prefix}leg_colspace_{self.plot_id}",
                default=0.5,
                min_value=0.0,
                max_value=20.0,
                step=0.1,
                format="%.1f",
                help=(
                    "Space between legend columns "
                    "(in font-size multiples for Matplotlib). "
                    "0 = no extra spacing."
                ),
            )
        with sz_c2:
            item_width = numeric_input(
                "Stripe Length (px)",
                saved_config,
                f"{config_prefix}itemwidth",
                self.plot_id,
                widget_key=f"{key_prefix}leg_itemwidth_{self.plot_id}",
                default=30,
                min_value=0,
                max_value=200,
                help=(
                    "Width of the legend marker/stripe. "
                    "Plotly clamps to 30 minimum; Matplotlib converts "
                    "to font-size multiples. 0 = auto."
                ),
            )
            handletextpad = numeric_input(
                "Stripe-Text Gap",
                saved_config,
                f"{config_prefix}handletextpad",
                self.plot_id,
                widget_key=f"{key_prefix}leg_htpad_{self.plot_id}",
                default=0.3,
                min_value=0.0,
                max_value=20.0,
                step=0.1,
                format="%.1f",
                help=(
                    "Gap between the legend stripe/marker and its label "
                    "(in font-size multiples for Matplotlib)."
                ),
            )

        return {
            f"{config_prefix}ncols": ncols,
            f"{config_prefix}tracegroupgap": tracegroupgap,
            f"{config_prefix}column_spacing": column_spacing,
            f"{config_prefix}itemwidth": item_width,
            f"{config_prefix}handletextpad": handletextpad,
        }

    def _render_colorbar_settings(
        self,
        saved_config: PlotConfig,
        key_prefix: str,
        config_prefix: str,
    ) -> PlotConfig:
        """Render colorbar-specific controls for heatmap plots.

        Controls: shared toggle, range mode, zmin/zmax, tick count, tick decimals.
        """
        st.markdown("**Colorbar Range & Ticks**")

        shared = toggle(
            "Shared Colorbar",
            saved_config,
            f"{config_prefix}colorbar_shared",
            self.plot_id,
            widget_key=f"{key_prefix}cbar_shared_{self.plot_id}",
            default=True,
            help="Use a single colorbar for all subplots with a unified range.",
        )

        range_mode = st.radio(
            "Range Mode",
            options=["auto", "manual"],
            index=(
                1
                if saved_config.get(f"{config_prefix}colorbar_range_mode", "auto") == "manual"
                else 0
            ),
            horizontal=True,
            key=f"{key_prefix}cbar_range_mode_{self.plot_id}",
            help="Auto computes nice rounded boundaries; manual lets you set exact values.",
        )

        zmin: float | None = None
        zmax: float | None = None
        if range_mode == "manual":
            z_c1, z_c2 = st.columns(2)
            with z_c1:
                zmin = numeric_input(
                    "Min",
                    saved_config,
                    f"{config_prefix}colorbar_zmin",
                    self.plot_id,
                    widget_key=f"{key_prefix}cbar_zmin_{self.plot_id}",
                    default=0.0,
                    step=1.0,
                    format="%.2f",
                )
            with z_c2:
                zmax = numeric_input(
                    "Max",
                    saved_config,
                    f"{config_prefix}colorbar_zmax",
                    self.plot_id,
                    widget_key=f"{key_prefix}cbar_zmax_{self.plot_id}",
                    default=100.0,
                    step=1.0,
                    format="%.2f",
                )

        tick_c1, tick_c2 = st.columns(2)
        with tick_c1:
            nticks = numeric_input(
                "Tick Count",
                saved_config,
                f"{config_prefix}colorbar_nticks",
                self.plot_id,
                widget_key=f"{key_prefix}cbar_nticks_{self.plot_id}",
                default=5,
                min_value=2,
                max_value=20,
                help="Number of ticks on the colorbar.",
            )
        with tick_c2:
            tick_decimals = numeric_input(
                "Tick Decimals",
                saved_config,
                f"{config_prefix}colorbar_tick_decimals",
                self.plot_id,
                widget_key=f"{key_prefix}cbar_tick_dec_{self.plot_id}",
                default=2,
                min_value=0,
                max_value=6,
                help="Decimal places for colorbar tick labels.",
            )

        rot_c1, rot_c2 = st.columns(2)
        with rot_c1:
            tick_angle = numeric_input(
                "Tick Rotation",
                saved_config,
                f"{config_prefix}colorbar_tick_angle",
                self.plot_id,
                widget_key=f"{key_prefix}cbar_tick_angle_{self.plot_id}",
                default=0.0,
                min_value=-90.0,
                max_value=90.0,
                step=5.0,
                format="%.0f",
                help="Rotation angle for colorbar tick labels (degrees).",
            )
        with rot_c2:
            tick_side = select_option(
                "Tick Side",
                ["right", "left"],
                saved_config,
                f"{config_prefix}colorbar_tick_side",
                self.plot_id,
                widget_key=f"{key_prefix}cbar_tick_side_{self.plot_id}",
                default="right",
            )

        return {
            f"{config_prefix}colorbar_shared": shared,
            f"{config_prefix}colorbar_range_mode": range_mode,
            f"{config_prefix}colorbar_zmin": zmin,
            f"{config_prefix}colorbar_zmax": zmax,
            f"{config_prefix}colorbar_nticks": nticks,
            f"{config_prefix}colorbar_tick_decimals": tick_decimals,
            f"{config_prefix}colorbar_tick_angle": tick_angle,
            f"{config_prefix}colorbar_tick_side": tick_side,
        }
