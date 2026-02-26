"""Theme UI components for GroupedStackedBarPlot.

Extracted from GroupedStackedBarPlot to reduce class size.
Renders stack total options and grouped-stacked-bar-specific theme controls.
"""

from typing import Any

import streamlit as st


def render_stack_total_options(
    saved_config: dict[str, Any], config: dict[str, Any], plot_id: int
) -> None:
    """Render options for Stack Totals.

    Args:
        saved_config: Previously saved configuration.
        config: Current configuration dict to update in-place.
        plot_id: Plot identifier for unique widget keys.
    """
    st.markdown("**Stack Totals**")
    c1, c2 = st.columns(2)
    with c1:
        config["show_totals"] = st.checkbox(
            "Show Stack Totals",
            value=saved_config.get("show_totals", False),
            key=f"show_tot_{plot_id}",
        )
    with c2:
        if config["show_totals"]:
            config["net_total_format"] = st.text_input(
                "Format",
                value=saved_config.get("net_total_format", ".2f"),
                help="Python format string (e.g. .2f)",
                key=f"tot_fmt_{plot_id}",
            )

    if config["show_totals"]:
        c3, c4 = st.columns(2)
        with c3:
            config["total_font_size"] = st.number_input(
                "Font Size",
                value=saved_config.get("total_font_size", 12),
                min_value=8,
                max_value=30,
                key=f"tot_sz_{plot_id}",
            )
            config["total_font_color"] = st.color_picker(
                "Font Color",
                value=saved_config.get("total_font_color", "#000000"),
                key=f"tot_col_{plot_id}",
            )
        with c4:
            config["total_position"] = st.selectbox(
                "Position",
                options=["Outside", "Inside"],
                index=["Outside", "Inside"].index(saved_config.get("total_position", "Outside")),
                key=f"tot_pos_{plot_id}",
                help="Outside: Always on top. Inside: Configurable anchor.",
            )

            if config["total_position"] == "Inside":
                config["total_anchor"] = st.selectbox(
                    "Anchor (Inside)",
                    options=["Start", "Middle", "End"],
                    index=["Start", "Middle", "End"].index(saved_config.get("total_anchor", "End")),
                    key=f"tot_anc_{plot_id}",
                    help="Start=Bottom, End=Top",
                )

    if config["show_totals"]:
        c5, c6 = st.columns(2)
        with c5:
            config["total_offset"] = st.number_input(
                "Vertical Offset (px)",
                value=saved_config.get("total_offset", 0),
                step=1,
                key=f"tot_off_{plot_id}",
                help="Adjustment in pixels (positive = up, negative = down)",
            )
        with c6:
            config["total_rotation"] = st.number_input(
                "Rotation",
                value=int(saved_config.get("total_rotation", 0)),
                step=45,
                min_value=-360,
                max_value=360,
                key=f"tot_rot_{plot_id}",
            )

    if config["show_totals"]:
        config["total_threshold"] = st.number_input(
            "Minimum Threshold",
            value=float(saved_config.get("total_threshold", 0.0)),
            step=0.1,
            key=f"tot_thresh_{plot_id}",
            help="Only show totals greater than this value.",
        )


def render_grouped_theme_extras(
    saved_config: dict[str, Any], config: dict[str, Any], plot_id: int
) -> None:
    """Render grouped-stacked-bar-specific theme options.

    This covers major group styling, visual distinction, summary group
    isolation, and numbered X-axis labels.

    Args:
        saved_config: Previously saved configuration.
        config: Current configuration dict to update in-place.
        plot_id: Plot identifier for unique widget keys.
    """
    # Major Group Styling
    st.markdown("#### Major Group Styling")
    c1, c2, c3 = st.columns(3)
    with c1:
        config["major_label_size"] = st.number_input(
            "Major Label Font Size",
            value=saved_config.get("major_label_size", 14),
            key=f"maj_sz_th_{plot_id}",
        )
    with c2:
        config["major_label_color"] = st.color_picker(
            "Major Label Font Color",
            value=saved_config.get("major_label_color", "#000000"),
            key=f"maj_col_th_{plot_id}",
        )
    with c3:
        config["major_label_offset"] = st.number_input(
            "Vertical Offset",
            value=float(saved_config.get("major_label_offset", -0.15)),
            step=0.05,
            max_value=0.0,
            min_value=-1.0,
            format="%.2f",
            key=f"maj_off_th_{plot_id}",
            help="Adjust vertical position of Major Group labels (negative values move down)",
        )

    # Group label alternation
    alt1, alt2 = st.columns(2)
    with alt1:
        config["group_label_alternate"] = st.checkbox(
            "Alternate Group Labels",
            value=saved_config.get("group_label_alternate", True),
            key=f"grp_alt_{plot_id}",
            help="Stagger odd-indexed major group labels to avoid overlap.",
        )
    with alt2:
        if config["group_label_alternate"]:
            config["group_label_alt_spacing"] = st.number_input(
                "Alternation Spacing",
                value=float(saved_config.get("group_label_alt_spacing", 0.05)),
                step=0.01,
                min_value=0.0,
                max_value=0.3,
                format="%.2f",
                key=f"grp_alt_sp_{plot_id}",
                help="Extra vertical offset for staggered labels.",
            )

    # Stack Totals
    render_stack_total_options(saved_config, config, plot_id)

    # Visual Distinction
    st.markdown("**Visual Distinction**")
    d1, d2 = st.columns(2)
    with d1:
        config["show_separators"] = st.checkbox(
            "Show Vertical Separators",
            value=saved_config.get("show_separators", True),
            key=f"show_sep_{plot_id}",
        )
        config["separator_color"] = st.color_picker(
            "Separator Color",
            value=saved_config.get("separator_color", "#E0E0E0"),
            key=f"sep_col_{plot_id}",
        )
    with d2:
        config["shade_alternate"] = st.checkbox(
            "Shade Alternate Groups",
            value=saved_config.get("shade_alternate", False),
            key=f"shade_alt_{plot_id}",
        )
        config["shade_color"] = st.color_picker(
            "Shade Color",
            value=saved_config.get("shade_color", "#F5F5F5"),
            key=f"shade_col_{plot_id}",
        )

    # Summary Group Isolation
    st.markdown("**Summary Group Isolation (Last Group)**")
    d3, d4 = st.columns(2)
    with d3:
        config["isolate_last_group"] = st.checkbox(
            "Isolate Last Group",
            value=saved_config.get("isolate_last_group", False),
            key=f"iso_last_{plot_id}",
            help="Adds extra space and a distinct separator before the last major group.",
        )
    with d4:
        if config["isolate_last_group"]:
            config["isolation_gap"] = st.number_input(
                "Isolation Gap Size",
                value=float(saved_config.get("isolation_gap", 0.5)),
                min_value=0.0,
                step=0.1,
                key=f"iso_gap_{plot_id}",
            )

    # Numbered X-axis annotation legend formatting
    # (Enable/disable is controlled by the multiselect pills
    #  in Axes → X-Axis → Numbered X-Axis Labels.)
    _modes: list[str] = saved_config.get("numbered_xaxis_modes", [])
    _has_legend_mode: bool = "Number legend" in _modes or saved_config.get("numbered_xaxis", False)
    if _has_legend_mode:
        st.markdown("**Number Legend Formatting**")
        f1, f2 = st.columns(2)
        with f1:
            config["numbered_legend_size"] = st.number_input(
                "Legend Font Size",
                value=int(saved_config.get("numbered_legend_size", 10)),
                min_value=6,
                max_value=24,
                key=f"num_leg_sz_{plot_id}",
            )
        with f2:
            config["numbered_legend_bgcolor"] = st.color_picker(
                "Legend Background",
                value=saved_config.get("numbered_legend_bgcolor", "#FFFFFF"),
                key=f"num_leg_bg_{plot_id}",
            )
        e3, e4 = st.columns(2)
        with e3:
            config["numbered_legend_x"] = st.number_input(
                "Legend X Position",
                value=float(saved_config.get("numbered_legend_x", 1.02)),
                step=0.05,
                min_value=-0.5,
                max_value=2.0,
                format="%.2f",
                key=f"num_leg_x_{plot_id}",
                help="Horizontal position (0=left, 1=right edge, >1=outside right)",
            )
        with e4:
            config["numbered_legend_y"] = st.number_input(
                "Legend Y Position",
                value=float(saved_config.get("numbered_legend_y", 0.5)),
                step=0.05,
                min_value=-1.0,
                max_value=2.0,
                format="%.2f",
                key=f"num_leg_y_{plot_id}",
                help="Vertical position (0=bottom, 1=top, <0=below plot)",
            )
        e5, _ = st.columns(2)
        with e5:
            config["numbered_legend_columns"] = st.number_input(
                "Columns",
                value=int(saved_config.get("numbered_legend_columns", 1)),
                min_value=1,
                max_value=10,
                key=f"num_leg_cols_{plot_id}",
                help="Number of columns inside the legend box",
            )
