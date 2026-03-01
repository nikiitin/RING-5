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

from typing import Any

import streamlit as st

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
        saved_config: dict[str, Any],
        has_secondary: bool = False,
        has_tertiary: bool = False,
    ) -> dict[str, Any]:
        """Render legend pills navigation and settings.

        Parameters
        ----------
        saved_config : dict[str, Any]
            Current saved configuration.
        has_secondary : bool
            Whether to show a secondary legend pill.
        has_tertiary : bool
            Whether to show a tertiary legend pill.

        Returns
        -------
        dict[str, Any]
            Legend configuration keys (prefixed per legend level).
        """
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

        preserved: dict[str, Any] = {}
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

    # ------------------------------------------------------------------
    # Legend section rendering
    # ------------------------------------------------------------------

    def _render_legend_section(
        self, saved_config: dict[str, Any], key_prefix: str
    ) -> dict[str, Any]:
        """Render legend styling section for the selected prefix."""
        config_prefix = "legend_" if key_prefix == "theme_" else key_prefix
        st.markdown("#### Legend Styling")

        pos_config = self._render_legend_position(saved_config, key_prefix, config_prefix)
        app_config = self._render_legend_appearance(saved_config, key_prefix, config_prefix)
        sz_config = self._render_legend_sizing(saved_config, key_prefix, config_prefix)

        return {**pos_config, **app_config, **sz_config}

    def _render_legend_position(
        self,
        saved_config: dict[str, Any],
        key_prefix: str,
        config_prefix: str,
    ) -> dict[str, Any]:
        """Render legend position controls."""
        st.markdown("**Position**")
        pos_c1, pos_c2 = st.columns(2)

        with pos_c1:
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

        with pos_c2:
            legend_y = st.number_input(
                "Y Position",
                value=float(saved_config.get(f"{config_prefix}y", 1.0)),
                step=0.05,
                key=f"{key_prefix}leg_y_{self.plot_id}",
            )

        return {
            f"{config_prefix}x": legend_x,
            f"{config_prefix}y": legend_y,
        }

    def _render_legend_appearance(
        self,
        saved_config: dict[str, Any],
        key_prefix: str,
        config_prefix: str,
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
        self,
        saved_config: dict[str, Any],
        key_prefix: str,
        config_prefix: str,
    ) -> dict[str, Any]:
        """Render legend sizing and spacing controls."""
        st.markdown("**Sizing & Spacing**")

        ncols = st.number_input(
            "Columns",
            min_value=0,
            max_value=20,
            value=int(saved_config.get(f"{config_prefix}ncols", 0)),
            key=f"{key_prefix}leg_ncols_{self.plot_id}",
            help=(
                "Number of legend columns. "
                "0 = single column (default). "
                "When > 1, entry width is auto-computed unless "
                "you set it manually below."
            ),
        )

        sz_c1, sz_c2 = st.columns(2)
        with sz_c1:
            tracegroupgap = st.number_input(
                "Item Spacing (px)",
                min_value=-20,
                max_value=200,
                value=int(saved_config.get(f"{config_prefix}tracegroupgap", 10)),
                key=f"{key_prefix}leg_tracegap_{self.plot_id}",
                help="Vertical spacing between legend items.",
            )
            column_spacing = st.number_input(
                "Column Spacing",
                min_value=0.0,
                max_value=20.0,
                value=float(saved_config.get(f"{config_prefix}column_spacing", 0.5)),
                step=0.1,
                format="%.1f",
                key=f"{key_prefix}leg_colspace_{self.plot_id}",
                help=(
                    "Space between legend columns "
                    "(in font-size multiples for Matplotlib). "
                    "0 = no extra spacing."
                ),
            )
        with sz_c2:
            item_width = st.number_input(
                "Stripe Length (px)",
                min_value=0,
                max_value=200,
                value=int(saved_config.get(f"{config_prefix}itemwidth", 30)),
                key=f"{key_prefix}leg_itemwidth_{self.plot_id}",
                help=(
                    "Width of the legend marker/stripe. "
                    "Plotly clamps to 30 minimum; Matplotlib converts "
                    "to font-size multiples. 0 = auto."
                ),
            )
            handletextpad = st.number_input(
                "Stripe-Text Gap",
                min_value=0.0,
                max_value=20.0,
                value=float(saved_config.get(f"{config_prefix}handletextpad", 0.3)),
                step=0.1,
                format="%.1f",
                key=f"{key_prefix}leg_htpad_{self.plot_id}",
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
