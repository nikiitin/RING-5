"""Shapes settings component — UI for adding/editing plot shapes.

Renders shape annotations for the selected plot.
"""

from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import math
from typing import Literal

import streamlit as st

from src.web.state.ui_state_manager import UIStateManager, WidgetKeyBuilder

from src.core.models.plot_config import ShapeConfig
from src.core.models.plot_config import PlotConfig

_CoordinateName = Literal["x0", "y0", "x1", "y1"]
_COORDINATES: tuple[_CoordinateName, ...] = ("x0", "y0", "x1", "y1")


def _coordinate_input(
    label: str,
    value: float | str,
    key: str,
    *,
    label_visibility: Literal["visible", "collapsed"] = "visible",
) -> tuple[str, bool]:
    """Render a coordinate with an explicit numeric or literal interpretation."""
    text = st.text_input(label, value=str(value), key=key, label_visibility=label_visibility)
    text_mode = st.checkbox(
        "Text",
        value=isinstance(value, str),
        key=f"{key}.text_mode",
        help="Keep an exact category label or text value. Clear Text to enter a number.",
    )
    return text, text_mode


def _decode_coordinate(text: str, text_mode: bool, original: float | str) -> float | str:
    """Decode the chosen kind without guessing numeric meaning from literal text.

    Raises:
        ValueError: A Number is invalid, non-finite, or underflows to zero.
    """
    if text_mode:
        return text
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError("Enter a finite Number, or select Text for a literal coordinate.") from exc
    if not number.is_finite():
        raise ValueError("Number coordinates must be finite.")
    if not isinstance(original, str) and text == str(original):
        return original
    try:
        numeric = float(number)
    except (OverflowError, ValueError) as exc:
        raise ValueError("Number coordinates must be finite.") from exc
    if not math.isfinite(numeric):
        raise ValueError("Number coordinates must be finite.")
    if numeric == 0.0 and not number.is_zero():
        raise ValueError(
            "Number coordinate is too small to represent; select Text to keep it literal."
        )
    return numeric


@dataclass(frozen=True, slots=True)
class _ShapeDraft:
    """Keep an owned edit list paired with its published configuration baseline."""

    source: list[ShapeConfig]
    edited: list[ShapeConfig]
    reset_rows: bool = False


class ShapesSettingsComponent:
    """Render shapes UI for adding/editing plot shapes.

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

    def render(self, saved_config: PlotConfig) -> list[ShapeConfig]:
        """Render shapes UI for adding/editing plot shapes.

        Args:
            saved_config: Previously saved configuration.

        Returns:
            A NEW list of shape configuration dictionaries. The caller's
            ``saved_config`` is never mutated — edits are returned and
            committed through the normal config change-detection path.
        """
        # [impl->req~ring5.figure.shapes-annotations~1]
        draft_key = WidgetKeyBuilder.plot_key(self.plot_id, "widgets.appearance.shape_editor")
        source = saved_config.get("shapes", [])
        draft = st.session_state.get(draft_key)
        if draft is not None and not isinstance(draft, _ShapeDraft):
            raise TypeError("Shape editor state must use its current typed draft.")
        if draft is None:
            UIStateManager().plot.reset_widgets(self.plot_id, "appearance", "shape_rows")
            draft = _ShapeDraft(deepcopy(source), deepcopy(source))
        elif draft.source != source:
            if draft.edited != source:
                UIStateManager().plot.reset_widgets(self.plot_id, "appearance", "shape_rows")
                draft = _ShapeDraft(deepcopy(source), deepcopy(source))
            else:
                # Publishing this draft acknowledges its values without discarding a new click.
                draft = _ShapeDraft(deepcopy(source), deepcopy(source), draft.reset_rows)
        if draft.reset_rows:
            UIStateManager().plot.reset_widgets(self.plot_id, "appearance", "shape_rows")
        # Independent copy: never mutate the caller's (live) config in place.
        shapes = deepcopy(draft.edited)
        reset_rows = False

        # Add new shape
        with st.expander("Add New Shape"):
            new_shape_type: str = st.selectbox(
                "Type",
                ["line", "circle", "rect"],
                key=WidgetKeyBuilder.plot_key(self.plot_id, "widgets.appearance.new_shape_type"),
            )
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                x0, x0_text = _coordinate_input(
                    "x0", 0.0, WidgetKeyBuilder.plot_key(self.plot_id, "widgets.appearance.s_x0")
                )
            with c2:
                y0, y0_text = _coordinate_input(
                    "y0", 0.0, WidgetKeyBuilder.plot_key(self.plot_id, "widgets.appearance.s_y0")
                )
            with c3:
                x1, x1_text = _coordinate_input(
                    "x1", 0.0, WidgetKeyBuilder.plot_key(self.plot_id, "widgets.appearance.s_x1")
                )
            with c4:
                y1, y1_text = _coordinate_input(
                    "y1", 0.0, WidgetKeyBuilder.plot_key(self.plot_id, "widgets.appearance.s_y1")
                )

            c5, c6 = st.columns(2)
            with c5:
                s_color: str = st.color_picker(
                    "Color",
                    "#000000",
                    key=WidgetKeyBuilder.plot_key(self.plot_id, "widgets.appearance.s_color"),
                )
            with c6:
                s_width: int = st.number_input(
                    "Width",
                    1,
                    10,
                    2,
                    key=WidgetKeyBuilder.plot_key(self.plot_id, "widgets.appearance.s_width"),
                )

            if st.button(
                "Add Shape",
                key=WidgetKeyBuilder.plot_key(self.plot_id, "widgets.appearance.add_shape"),
            ):
                try:
                    added: ShapeConfig = {
                        "type": new_shape_type,
                        "x0": _decode_coordinate(x0, x0_text, 0.0),
                        "y0": _decode_coordinate(y0, y0_text, 0.0),
                        "x1": _decode_coordinate(x1, x1_text, 0.0),
                        "y1": _decode_coordinate(y1, y1_text, 0.0),
                        "line": {"color": s_color, "width": s_width},
                    }
                except ValueError as exc:
                    st.error(f"Cannot add shape: {exc}")
                else:
                    shapes.append(added)

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

            delete_index: int | None = None
            row_edits: list[dict[_CoordinateName, tuple[str, bool, float | str]]] = []
            for i, shape in enumerate(shapes):
                columns = st.columns([1, 1, 1, 1, 1, 0.5])
                edits: dict[_CoordinateName, tuple[str, bool, float | str]] = {}
                for field, column in zip(_COORDINATES, columns[:4], strict=True):
                    with column:
                        original = shape.get(field)
                        if original is None:
                            st.caption("Default")
                        else:
                            text, text_mode = _coordinate_input(
                                field,
                                original,
                                WidgetKeyBuilder.plot_key(
                                    self.plot_id,
                                    f"widgets.appearance.shape_rows.edit_{field}_{i}",
                                ),
                                label_visibility="collapsed",
                            )
                            edits[field] = (text, text_mode, original)
                row_edits.append(edits)
                with columns[4]:
                    st.text(shape.get("type") or "Default")
                with columns[5]:
                    if st.button(
                        "\U0001f5d1\ufe0f",
                        key=WidgetKeyBuilder.plot_key(
                            self.plot_id, f"widgets.appearance.shape_rows.del_shape_{i}"
                        ),
                    ):
                        delete_index = i

            for i, (shape, edits) in enumerate(zip(shapes, row_edits, strict=True)):
                if i == delete_index:
                    continue
                for field, (text, text_mode, original) in edits.items():
                    try:
                        shape[field] = _decode_coordinate(text, text_mode, original)
                    except ValueError as exc:
                        raise ValueError(f"Shape {i + 1} {field}: {exc}") from exc

            if delete_index is not None:
                # The next render resets shifted rows before creating their widgets.
                reset_rows = True
                shapes = [s for j, s in enumerate(shapes) if j != delete_index]

        st.session_state[draft_key] = _ShapeDraft(
            deepcopy(source), deepcopy(shapes), reset_rows=reset_rows
        )
        if reset_rows:
            st.rerun()
        return shapes
