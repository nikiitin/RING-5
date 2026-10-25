"""Typed access to namespaced, transient Streamlit session state."""

from typing import Any

import streamlit as st


class WidgetKeyBuilder:
    """Build consistent, namespaced session_state keys.

    Centralizes key construction so that all parts of the web layer
    produce collision-free, predictable key strings.

    Examples::

        WidgetKeyBuilder.plot_key(1, "widgets.auto_refresh")  # "plot.1.widgets.auto_refresh"
        WidgetKeyBuilder.manager_key("mixer", "mode")  # "manager.mixer.mode"
    """

    @staticmethod
    def plot_key(plot_id: int, *parts: str) -> str:
        """Build a namespaced key for plot-level state."""
        return f"plot.{plot_id}.{'_'.join(parts)}"

    @staticmethod
    def manager_key(manager: str, *parts: str) -> str:
        """Build a namespaced key for a data manager."""
        return f"manager.{manager}.{'_'.join(parts)}"


def _clear_keys(prefixes: tuple[str, ...]) -> None:
    """Remove only text keys within the given ownership boundaries."""
    for key in list(st.session_state):
        if isinstance(key, str) and key.startswith(prefixes):
            del st.session_state[key]


class _PlotUIState:
    """
    Typed accessors for plot-related UI state.

    Namespaced under ``plot.{plot_id}.*``.
    """

    def get_auto_refresh(self, plot_id: int) -> bool:
        """Get whether auto-refresh is enabled for a plot."""
        return bool(
            st.session_state.get(WidgetKeyBuilder.plot_key(plot_id, "widgets.auto_refresh"), True)
        )

    def reset_widgets(self, plot_id: int, *sections: str) -> None:
        """Reset this plot's controls, optionally within a named widget section.

        Native artifacts and transfer notices have separate ownership and remain intact.
        """
        prefix = WidgetKeyBuilder.plot_key(plot_id, "widgets") + "."
        if sections:
            prefix += ".".join(sections) + "."
        _clear_keys((prefix,))

    def cleanup(self, plot_id: int) -> None:
        """Remove this plot's transient state without touching another plot."""
        _clear_keys((f"plot.{plot_id}.",))


class _ManagerUIState:
    """
    Typed accessors for data manager UI state.

    Namespaced under ``manager.{manager_name}.*``.
    """

    def consume_load_trigger(self, manager_name: str) -> dict[str, Any] | None:
        """Get and clear a load trigger (atomic pop)."""
        result: dict[str, Any] | None = st.session_state.pop(
            WidgetKeyBuilder.manager_key(manager_name, "load_trigger"), None
        )
        return result


class _NavUIState:
    """
    Typed accessors for navigation state.

    Namespaced under ``nav.*``.
    """

    def get_current_page(self) -> str | None:
        """Get the currently active page name."""
        result: str | None = st.session_state.get("nav.current_page")
        return result

    def set_current_page(self, page: str) -> None:
        """Set the current page."""
        st.session_state["nav.current_page"] = page


class UIStateManager:
    """Own transient plot, manager and navigation state for this browser session."""

    def __init__(self) -> None:
        """Initialize sub-managers."""
        self.plot: _PlotUIState = _PlotUIState()
        self.manager: _ManagerUIState = _ManagerUIState()
        self.nav: _NavUIState = _NavUIState()

    def cleanup_all(self) -> None:
        """Clear workspace widget state, retaining global preferences and browser identity."""
        _clear_keys(("plot.", "manager.", "nav."))
