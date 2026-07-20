"""Human-first controls for exploring rows behind a plotted value."""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.core.models.visualization.drill_down_result import DrillDownResult


class DrillDownPanel:
    """Render opt-in drill-down controls and a reversible source-row view."""

    @staticmethod
    def render_toggle(plot_id: int) -> bool:
        """Return whether point-click exploration is enabled for this plot."""
        return st.toggle(
            "Explore source rows",
            value=False,
            key=f"plot.{plot_id}.drill_down.enabled",
            help="Click a plotted value to inspect the source rows that contribute to it.",
        )

    @staticmethod
    def render_result(result: DrillDownResult, point_label: str) -> bool:
        # [impl->req~ring5.plots.drill-down~1]
        """Render a source-row snapshot and return whether the user closes it."""
        with st.container(border=True):
            title = point_label or "Selected plot value"
            st.markdown("#### Source rows")
            st.caption(title)
            if result.filters:
                dimensions = " · ".join(f"{column} = {value}" for column, value in result.filters)
                st.caption(f"Matched dimensions: {dimensions}")
            else:
                st.caption("This aggregate uses all source rows in the plot snapshot.")
            st.metric("Matching rows", result.row_count)
            st.dataframe(
                result.rows,
                width="stretch",
                height=min(520, 90 + max(1, result.row_count) * 35),
            )
            st.caption(
                "This is a read-only snapshot. The source dataset and active figure settings "
                "remain unchanged."
            )
            return st.button(
                ":material/arrow_back: Back to full plot",
                key=f"plot.{result.plot_id}.drill_down.close",
            )

    @staticmethod
    def render_error(error: Exception) -> None:
        """Show a recoverable drill-down resolution error."""
        st.error(f"Could not inspect source rows: {error}")


def point_label(event: dict[str, Any]) -> str:
    """Build a compact, escaped-by-Streamlit label from a sanitized click."""
    trace_name = str(event.get("traceName") or "").strip()
    x_value = event.get("x")
    y_value = event.get("y")
    coordinates = f"x={x_value}, y={y_value}"
    return f"{trace_name} · {coordinates}" if trace_name else coordinates


__all__ = ["DrillDownPanel", "point_label"]
