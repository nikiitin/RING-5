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

        prefix_map = {
            "primary": "theme_",
            "secondary": "legend2_",
            "tertiary": "legend3_",
        }
        key_prefix = prefix_map.get(legend_tab or "primary", "theme_")

        return self._render_legend_section(saved_config, key_prefix)

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
        """Render legend position and orientation controls."""
        st.markdown("**Position & Orientation**")
        pos_c1, pos_c2 = st.columns(2)

        with pos_c1:
            legend_orientation = st.selectbox(
                "Orientation",
                options=["v", "h"],
                format_func=lambda x: ("Vertical" if x == "v" else "Horizontal"),
                index=(0 if saved_config.get(f"{config_prefix}orientation", "v") == "v" else 1),
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
                help=("Space between color marker and text" " (Matplotlib handletextpad)."),
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
                help=("Space between columns in the legend" " (Matplotlib columnspacing)."),
            )

        return {
            f"{config_prefix}itemsizing": itemsizing,
            f"{config_prefix}itemwidth": itemwidth,
            f"{config_prefix}tracegroupgap": tracegroupgap,
            f"{config_prefix}column_spacing": column_spacing,
            f"{config_prefix}marker_text_spacing": marker_text_spacing,
        }
