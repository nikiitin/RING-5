"""Shapes settings component — UI for adding/editing plot shapes.

Extracted from ``BasePlot._render_shapes_ui``.
"""

from typing import Any

import streamlit as st

from src.core.models.plot_config import ShapeConfig
from src.core.services.visualization.plot_interaction import (
    try_float,
    try_float_edit,
)


def render_shapes_ui(plot_id: int, saved_config: dict[str, Any]) -> list[ShapeConfig]:
    """Render shapes UI for adding/editing plot shapes.

    Args:
        plot_id: Plot identifier for unique widget keys.
        saved_config: Previously saved configuration.

    Returns:
        List of shape configuration dictionaries.
    """
    shapes: list[ShapeConfig] = saved_config.get("shapes", [])

    # Add new shape
    with st.expander("Add New Shape"):
        new_shape_type: str = st.selectbox(
            "Type",
            ["line", "circle", "rect"],
            key=f"new_shape_type_{plot_id}",
        )
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            x0: str = st.text_input("x0", key=f"s_x0_{plot_id}")
        with c2:
            y0: str = st.text_input("y0", key=f"s_y0_{plot_id}")
        with c3:
            x1: str = st.text_input("x1", key=f"s_x1_{plot_id}")
        with c4:
            y1: str = st.text_input("y1", key=f"s_y1_{plot_id}")

        c5, c6 = st.columns(2)
        with c5:
            s_color: str = st.color_picker("Color", "#000000", key=f"s_color_{plot_id}")
        with c6:
            s_width: int = st.number_input("Width", 1, 10, 2, key=f"s_width_{plot_id}")

        if st.button("Add Shape", key=f"add_shape_{plot_id}"):
            shapes.append(
                {
                    "type": new_shape_type,
                    "x0": try_float(x0),
                    "y0": try_float(y0),
                    "x1": try_float(x1),
                    "y1": try_float(y1),
                    "line": {"color": s_color, "width": s_width},
                }
            )
            st.rerun()

    # List existing shapes
    if shapes:
        st.markdown("**Existing Shapes (Edit to Resize):**")

        h1, h2, h3, h4, h5, h6 = st.columns([1, 1, 1, 1, 1, 0.5])
        with h1:
            st.caption("x0")
        with h2:
            st.caption("y0")
        with h3:
            st.caption("x1")
        with h4:
            st.caption("y1")
        with h5:
            st.caption("Type")

    if st.session_state.get(f"edit_shapes_{plot_id}", False):
        for i, shape in enumerate(shapes):
            c1, c2, c3, c4, c5, c6 = st.columns([1, 1, 1, 1, 1, 0.5])

            with c1:
                new_x0: str = st.text_input(
                    "x0",
                    value=str(shape["x0"]),
                    key=f"edit_x0_{i}_{plot_id}",
                    label_visibility="collapsed",
                )
            with c2:
                new_y0: str = st.text_input(
                    "y0",
                    value=str(shape["y0"]),
                    key=f"edit_y0_{i}_{plot_id}",
                    label_visibility="collapsed",
                )
            with c3:
                new_x1: str = st.text_input(
                    "x1",
                    value=str(shape["x1"]),
                    key=f"edit_x1_{i}_{plot_id}",
                    label_visibility="collapsed",
                )
            with c4:
                new_y1: str = st.text_input(
                    "y1",
                    value=str(shape["y1"]),
                    key=f"edit_y1_{i}_{plot_id}",
                    label_visibility="collapsed",
                )
            with c5:
                st.text(shape["type"])
            with c6:
                if st.button("🗑️", key=f"del_shape_{i}_{plot_id}"):
                    shapes.pop(i)
                    st.rerun()

            shape["x0"] = try_float_edit(new_x0)
            shape["y0"] = try_float_edit(new_y0)
            shape["x1"] = try_float_edit(new_x1)
            shape["y1"] = try_float_edit(new_y1)

    return shapes
