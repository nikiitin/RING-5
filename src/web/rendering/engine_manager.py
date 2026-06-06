"""
Engine state management for visualization rendering.

Manages the active rendering engine (Plotly or Matplotlib) in
Streamlit session state.  All engine queries and mutations flow
through :class:`EngineManager` so the rest of the codebase never
touches the raw session-state key directly.

Design Decisions:
    1. **Literal type** — ``EngineMode`` is ``Literal["plotly", "matplotlib"]``
       so mypy can catch invalid values at type-check time.
    2. **Namespaced key** — ``ring5_engine_mode`` avoids collisions with
       other Streamlit widgets or state managers.
    3. **Idempotent set** — ``set_engine()`` only writes when the value
       actually changes, avoiding unnecessary Streamlit reruns.
    4. **Static API** — No instance state; all methods are ``@staticmethod``
       operating on ``st.session_state``.

Usage::

    from src.web.rendering.engine_manager import EngineManager

    if EngineManager.is_plotly():
        render_plotly(fig)
    else:
        render_matplotlib(fig)
"""

from __future__ import annotations

from typing import cast

import streamlit as st

from src.core.models.visualization.engine import (
    DEFAULT_ENGINE,
    VALID_ENGINES,
    EngineMode,
)


class EngineManager:
    """Manages the visualization engine state in Streamlit session."""

    STATE_KEY: str = "ring5_engine_mode"

    @staticmethod
    def get_engine() -> EngineMode:
        """Return the current engine mode.

        Defaults to ``DEFAULT_ENGINE`` when no mode has been set yet.
        """
        mode: str = st.session_state.get(EngineManager.STATE_KEY, DEFAULT_ENGINE)
        if mode not in VALID_ENGINES:
            return DEFAULT_ENGINE
        # Safe cast — validated above.
        return cast(EngineMode, mode)

    @staticmethod
    def set_engine(mode: EngineMode) -> None:
        """Set the engine mode.

        Only writes to session state when the value actually changes,
        avoiding unnecessary Streamlit reruns.

        Raises:
            ValueError: If *mode* is not ``"plotly"`` or ``"matplotlib"``.
        """
        if mode not in VALID_ENGINES:
            raise ValueError(
                f"Invalid engine mode {mode!r}. " f"Expected one of {sorted(VALID_ENGINES)}."
            )
        current = EngineManager.get_engine()
        if current != mode:
            st.session_state[EngineManager.STATE_KEY] = mode

    @staticmethod
    def is_plotly() -> bool:
        """Return ``True`` when the active engine is Plotly."""
        return EngineManager.get_engine() == "plotly"

    @staticmethod
    def is_matplotlib() -> bool:
        """Return ``True`` when the active engine is Matplotlib."""
        return EngineManager.get_engine() == "matplotlib"
