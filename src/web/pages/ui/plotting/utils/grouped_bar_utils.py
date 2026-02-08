"""Shared utilities for grouped bar plots."""

from typing import Any, Dict, List, Optional


class GroupedBarUtils:
    """Utility functions for grouped bar coordinate mapping and shapes."""

    @staticmethod
    def create_shade_shape(
        x0: float, x1: float, shade_color: str = "#F5F5F5", opacity: float = 0.5
    ) -> Dict[str, Any]:
        """
        Create a shading rectangle shape for alternating categories.

        Args:
            x0: Left x coordinate
            x1: Right x coordinate
            shade_color: Fill color
            opacity: Opacity level

        Returns:
            Plotly shape dict
        """
        return dict(
            type="rect",
            xref="x",
            yref="paper",
            x0=x0,
            x1=x1,
            y0=0,
            y1=1,
            fillcolor=shade_color,
            opacity=opacity,
            layer="below",
            line_width=0,
        )

    @staticmethod
    def create_separator_shape(
        sep_x: float,
        sep_color: str = "#E0E0E0",
        dash: str = "dash",
        width: int = 1,
    ) -> Dict[str, Any]:
        """
        Create a dashed separator line shape between categories.

        Args:
            sep_x: X coordinate for the separator
            sep_color: Line color
            dash: Dash style ("dash", "solid", etc.)
            width: Line width

        Returns:
            Plotly shape dict
        """
        return dict(
            type="line",
            xref="x",
            yref="paper",
            x0=sep_x,
            x1=sep_x,
            y0=0,
            y1=1,
            line=dict(color=sep_color, width=width, dash=dash),
            layer="below",
        )

    @staticmethod
    def create_isolation_separator(sep_x: float) -> Dict[str, Any]:
        """
        Create a solid isolation separator line (thicker, solid).

        Args:
            sep_x: X coordinate for the separator

        Returns:
            Plotly shape dict
        """
        return dict(
            type="line",
            xref="x",
            yref="paper",
            x0=sep_x,
            x1=sep_x,
            y0=0,
            y1=1,
            line=dict(color="#333333", width=2, dash="solid"),
            layer="below",
        )

    @staticmethod
    def build_category_annotations(
        cat_centers: List[tuple[float, str]],
        font_size: int = 14,
        font_color: str = "#000000",
        y_offset: float = -0.15,
    ) -> List[Dict[str, Any]]:
        """
        Build annotations for category labels below the plot.

        Args:
            cat_centers: List of (x_position, label) tuples
            font_size: Font size for labels
            font_color: Font color
            y_offset: Y position offset (negative = below axis)

        Returns:
            List of Plotly annotation dicts
        """
        annotations = []
        for center, label in cat_centers:
            annotations.append(
                dict(
                    x=center,
                    y=y_offset,
                    xref="x",
                    yref="paper",
                    text=f"<b>{label}</b>",
                    showarrow=False,
                    font=dict(size=font_size, color=font_color),
                    yanchor="top",
                )
            )
        return annotations

    @staticmethod
    def calculate_grouped_coordinates(
        categories: List[str],
        groups: List[str],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
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
            - shapes: List of separator/shading shapes
            - bar_width: Width of each bar
        """
        bargroupgap = config.get("bargroupgap", 0.0)
        # In grouped bar, groups are iterator. In stacked, groups are clustered.
        # This logic handles the clustered grouping (GroupedStacked or GroupedBar).

        # Determine strict bar width based on gaps
        # If groups is empty (simple bar), treat as single group
        actual_groups: List[Optional[str]]
        if groups:
            actual_groups = list(groups)  # Copy to satisfy variance
        else:
            actual_groups = [None]

        # Each bar occupies 1.0 unit of width in the 'simulation' space.

        coord_map = {}
        tick_vals = []
        tick_text = []
        cat_centers = []
        shapes = []

        show_separators = config.get("show_separators", False)
        sep_color = config.get("separator_color", "#E0E0E0")
        shade_alternate = config.get("shade_alternate", False)
        shade_color = config.get("shade_color", "#F5F5F5")
        isolate_last = config.get("isolate_last_group", False)
        isolation_gap = config.get("isolation_gap", 0.5)

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
                    # If no groups, tick text is the category itself (handled by caller usually, but okay)  # noqa: E501
                    tick_text.append(str(cat))

                current_x += 1.0

            # Calculate center of this major category cluster
            # (start + end - 1) / 2
            # end is current_x (which is one step past last bar)
            center = (start_x + (current_x - 1.0)) / 2.0
            cat_centers.append((center, cat))

            # Visual Distinctions (Shading)
            if shade_alternate and (i % 2 == 1):
                # Account for bargroupgap in the shade boundaries.
                x0 = start_x - 0.5 - (bargroupgap / 2.0)
                x1 = (current_x - 1.0) + 0.5 + (bargroupgap / 2.0)
                shapes.append(GroupedBarUtils.create_shade_shape(x0, x1, shade_color))

            # Separators (Vertical Lines)
            next_is_last_isolated = isolate_last and (i == len(categories) - 2)

            # Add Inter-Category Spacing (bargroupgap)
            current_x += bargroupgap

            # Draw Separator in the gap
            if show_separators and i < len(categories) - 1:
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
                    shapes.append(GroupedBarUtils.create_separator_shape(sep_x, sep_color))

            # Isolation Gap (Extra spacing for last group)
            if next_is_last_isolated:
                current_x += isolation_gap

                # Draw Thick Separator in the middle of total gap
                # total gap = bargroupgap + isolation_gap
                # center of gap relative to now:
                # start of gap = current_x - gap_total
                gap_total = bargroupgap + isolation_gap
                sep_x = current_x - 0.5 - (gap_total / 2.0)
                shapes.append(GroupedBarUtils.create_isolation_separator(sep_x))

        return {
            "coord_map": coord_map,
            "tick_vals": tick_vals,
            "tick_text": tick_text,
            "cat_centers": cat_centers,
            "shapes": shapes,
            "bar_width": 1.0 - config.get("bargap", 0.2),  # Approximation
        }
