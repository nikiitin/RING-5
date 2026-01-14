"""Shared utilities for grouped bar plots."""

from typing import Any, Dict, List


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
        cat_centers: List[tuple],
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
