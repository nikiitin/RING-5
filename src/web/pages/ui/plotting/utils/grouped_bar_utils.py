"""Shared utilities for grouped bar plots."""

from typing import Any, Literal

from src.core.models.visualization.trace_build_result import RuleLine, SeparatorLine, ShadedRegion


class GroupedBarUtils:
    """Utility functions for grouped bar coordinate mapping and shapes."""

    @staticmethod
    def create_shade_shape(
        x0: float, x1: float, shade_color: str = "#F5F5F5", opacity: float = 0.5
    ) -> ShadedRegion:
        """Create an engine-agnostic shading band for alternating categories."""
        return ShadedRegion(x0=x0, x1=x1, color=shade_color, opacity=opacity)

    @staticmethod
    def create_separator_shape(
        sep_x: float,
        sep_color: str = "#E0E0E0",
        dash: Literal["solid", "dash", "dot", "dashdot"] = "dash",
        width: float = 1.0,
    ) -> SeparatorLine:
        """Create an engine-agnostic dashed separator line between categories."""
        return SeparatorLine(x=sep_x, color=sep_color, dash=dash, width=width)

    @staticmethod
    def create_isolation_separator(sep_x: float) -> SeparatorLine:
        """Create an engine-agnostic solid isolation separator (thicker, solid)."""
        return SeparatorLine(x=sep_x, color="#333333", dash="solid", width=2.0)

    @staticmethod
    def build_category_annotations(
        cat_centers: list[tuple[float, str]],
        font_size: int = 14,
        font_color: str = "#000000",
        y_offset: float = -0.15,
        stagger_dy: float = 0.0,
        rotation: float = 0.0,
        rotation_overrides: dict[str, float] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Build annotations for category labels below the plot.

        Args:
            cat_centers: List of (x_position, label) tuples
            font_size: Font size for labels
            font_color: Font color
            y_offset: Y position offset (negative = below axis)
            stagger_dy: Extra y-offset to apply to odd-indexed labels
            rotation: Label rotation in degrees (0 = horizontal). Non-zero
                rotations right-anchor the label so it reads cleanly at an
                angle, like rotated x-tick labels.
            rotation_overrides: Per-label rotation, keyed by the displayed
                (post-rename) category label — e.g. make a mean category
                vertical while the rest stay at the base rotation.

        Returns:
            List of Plotly annotation dicts
        """
        annotations = []
        overrides = rotation_overrides or {}
        for i, (center, label) in enumerate(cat_centers):
            rot = overrides.get(label, rotation)
            current_y = y_offset - (stagger_dy if i % 2 == 1 else 0.0)
            annotations.append(
                dict(
                    x=center,
                    y=current_y,
                    xref="x",
                    yref="paper",
                    text=f"<b>{label}</b>",
                    showarrow=False,
                    font=dict(size=font_size, color=font_color),
                    yanchor="top",
                    xanchor="right" if rot else "center",
                    textangle=rot,
                )
            )
        return annotations

    @staticmethod
    def build_category_group_annotations(
        group_centers: list[tuple[float, str]],
        font_size: int = 12,
        font_color: str = "#000000",
        y_offset: float = -0.28,
    ) -> list[dict[str, Any]]:
        """
        Build annotations for category super-group labels, one per
        contiguous run of categories sharing a ``category_groups`` label,
        centered under the run and below the category labels.

        Args:
            group_centers: List of (x_position, label) tuples (from
                ``calculate_grouped_coordinates``'s ``category_group_centers``)
            font_size: Font size for labels
            font_color: Font color
            y_offset: Y position offset (negative = below axis; should sit
                below ``major_label_offset``)

        Returns:
            List of Plotly annotation dicts
        """
        return [
            dict(
                x=center,
                y=y_offset,
                xref="x",
                yref="paper",
                text=f"<b>{label}</b>",
                showarrow=False,
                font=dict(size=font_size, color=font_color),
                yanchor="top",
                xanchor="center",
                textangle=0,
            )
            for center, label in group_centers
        ]

    @staticmethod
    def calculate_grouped_coordinates(
        categories: list[str],
        groups: list[str],
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Calculate manual X-axis coordinates for grouped bar plots.

        Args:
            categories: Ordered list of Major Groups (X-axis categories)
            groups: Ordered list of Minor Groups (Sub-groups)
            config: Plot configuration containing spacing settings

        Returns:
            Dictionary containing:
            - coord_map: Dict[(category, group), x_coord]
            - tick_vals: List of x coordinates for ticks
            - tick_text: List of labels for ticks
            - cat_centers: List of (center_x, label) for major labels
            - category_group_centers: List of (center_x, label) for super-group labels
            - category_group_rules: List of RuleLine span rules, one per super-group run
            - shapes: List of separator/shading shapes
            - bar_width: Width of each bar
        """
        bargroupgap = config.get("bargroupgap", 0.0)
        # In grouped bar, groups are iterator. In stacked, groups are clustered.
        # This logic handles the clustered grouping (GroupedStacked or GroupedBar).

        # Determine strict bar width based on gaps
        # If groups is empty (simple bar), treat as single group
        actual_groups: list[str | None]
        if groups:
            actual_groups = list(groups)  # Copy to satisfy variance
        else:
            actual_groups = [None]

        # Each bar occupies 1.0 unit of width in the 'simulation' space.

        coord_map = {}
        tick_vals = []
        tick_text = []
        cat_centers = []
        cat_extents: list[tuple[float, float]] = []
        separator_lines: list[SeparatorLine] = []
        shaded_regions: list[ShadedRegion] = []

        show_separators = config.get("show_separators", False)
        sep_color = config.get("separator_color", "#E0E0E0")
        shade_alternate = config.get("shade_alternate", False)
        shade_color = config.get("shade_color", "#F5F5F5")
        isolate_last = config.get("isolate_last_group", False)
        isolation_gap = config.get("isolation_gap", 0.5)

        # category -> super-group label; boundaries between different labels
        # get a bolder separator (drawn even when show_separators is off)
        category_groups: dict[str, str] = config.get("category_groups") or {}
        grp_sep_color = config.get("category_group_separator_color", "#444444")
        grp_sep_width = float(config.get("category_group_separator_width", 1.6))
        grp_sep_dash_raw = config.get("category_group_separator_dash", "solid")
        grp_sep_dash: Literal["solid", "dash", "dot", "dashdot"] = (
            grp_sep_dash_raw if grp_sep_dash_raw in ("solid", "dash", "dot", "dashdot") else "solid"
        )

        current_x = 0.0

        for i, cat in enumerate(categories):
            start_x = current_x

            for grp in actual_groups:
                # Store coordinate
                key = (cat, grp) if grp is not None else cat
                coord_map[key] = current_x

                # Ticks mimic the bars
                tick_vals.append(current_x)
                if grp:
                    tick_text.append(str(grp))
                else:
                    # If no groups, tick text is the category
                    # itself (handled by caller usually,
                    # but okay)
                    tick_text.append(str(cat))

                current_x += 1.0

            # Calculate center of this major category cluster
            # (start + end - 1) / 2
            # end is current_x (which is one step past last bar)
            center = (start_x + (current_x - 1.0)) / 2.0
            cat_centers.append((center, cat))
            # Outer bar edges of this cluster (for super-group span rules)
            cat_extents.append((start_x - 0.5, (current_x - 1.0) + 0.5))

            # Visual Distinctions (Shading)
            if shade_alternate and (i % 2 == 1):
                # Account for bargroupgap in the shade boundaries.
                x0 = start_x - 0.5 - (bargroupgap / 2.0)
                x1 = (current_x - 1.0) + 0.5 + (bargroupgap / 2.0)
                shaded_regions.append(GroupedBarUtils.create_shade_shape(x0, x1, shade_color))

            # Separators (Vertical Lines)
            next_is_last_isolated = isolate_last and (i == len(categories) - 2)

            # Add Inter-Category Spacing (bargroupgap)
            current_x += bargroupgap

            # Super-group boundary? (label change between this category and the next)
            is_group_boundary = (
                bool(category_groups)
                and i < len(categories) - 1
                and (category_groups.get(cat) != category_groups.get(categories[i + 1]))
            )

            # Draw Separator in the gap
            if (show_separators or is_group_boundary) and i < len(categories) - 1:
                if not next_is_last_isolated:
                    # Midpoint of the gap we just added
                    # gap starts at (current_x - bargroupgap)
                    # gap ends at current_x

                    # Consistent Logic:
                    # Coordinate system: Centers are integers 0, 1, 2...
                    # Bar width 0.8 means -0.4 to +0.4 relative to center.
                    # Here we increment by 1.0, so centers are 0.0, 1.0, 2.0
                    # Edge is +0.5.

                    # Sep Position:

                    sep_x = (current_x - bargroupgap) - 0.5 + (bargroupgap / 2.0)
                    if is_group_boundary:
                        separator_lines.append(
                            GroupedBarUtils.create_separator_shape(
                                sep_x, grp_sep_color, dash=grp_sep_dash, width=grp_sep_width
                            )
                        )
                    else:
                        separator_lines.append(
                            GroupedBarUtils.create_separator_shape(sep_x, sep_color)
                        )

            # Isolation Gap (Extra spacing for last group)
            if next_is_last_isolated:
                current_x += isolation_gap

                # Draw Thick Separator in the middle of total gap
                # total gap = bargroupgap + isolation_gap
                # center of gap relative to now:
                # start of gap = current_x - gap_total
                gap_total = bargroupgap + isolation_gap
                sep_x = current_x - 0.5 - (gap_total / 2.0)
                separator_lines.append(GroupedBarUtils.create_isolation_separator(sep_x))

        # Super-group labels + span rules: one per contiguous run of equal labels
        category_group_centers: list[tuple[float, str]] = []
        category_group_rules: list[RuleLine] = []
        if category_groups:
            rule_enabled = bool(config.get("category_group_rule", True))
            rule_color = config.get("category_group_rule_color", "#444444")
            rule_width = float(config.get("category_group_rule_width", 1.0))
            rule_inset = float(config.get("category_group_rule_inset", 0.35))
            label_offset = float(config.get("category_group_label_offset", -0.28))
            rule_y_raw = config.get("category_group_rule_y")
            # default: just above the label text (the \cmidrule position)
            rule_y = float(rule_y_raw) if rule_y_raw is not None else label_offset + 0.025

            def _flush(label: str, centers: list[float], x0: float, x1: float) -> None:
                category_group_centers.append((sum(centers) / len(centers), label))
                if rule_enabled:
                    category_group_rules.append(
                        RuleLine(x0 + rule_inset, x1 - rule_inset, rule_y, rule_color, rule_width)
                    )

            run_label: str | None = None
            run_centers: list[float] = []
            run_x0 = run_x1 = 0.0
            for (center, cat), (ext0, ext1) in zip(cat_centers, cat_extents):
                label = category_groups.get(cat)
                if label != run_label:
                    if run_label is not None:
                        _flush(run_label, run_centers, run_x0, run_x1)
                    run_label, run_centers, run_x0 = label, [], ext0
                run_centers.append(center)
                run_x1 = ext1
            if run_label is not None:
                _flush(run_label, run_centers, run_x0, run_x1)

        return {
            "coord_map": coord_map,
            "tick_vals": tick_vals,
            "tick_text": tick_text,
            "cat_centers": cat_centers,
            "category_group_centers": category_group_centers,
            "category_group_rules": category_group_rules,
            "separator_lines": separator_lines,
            "shaded_regions": shaded_regions,
            "bar_width": 1.0 - config.get("bargap", 0.2),  # Approximation
        }
