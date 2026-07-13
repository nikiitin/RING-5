"""Typed access to namespaced, transient Streamlit session state."""

from typing import Any

import streamlit as st


class WidgetKeyBuilder:
    """Build consistent, namespaced session_state keys.

    Centralizes key construction so that all parts of the web layer
    produce collision-free, predictable key strings.

    Examples::

        WidgetKeyBuilder.plot_key(1, "auto_refresh")  # "plot.1.auto_refresh"
        WidgetKeyBuilder.manager_key("mixer", "mode")  # "manager.mixer.mode"
        WidgetKeyBuilder.global_key("theme")            # "g.theme"
    """

    @staticmethod
    def plot_key(plot_id: int, *parts: str) -> str:
        """Build a namespaced key for plot-level state."""
        return f"plot.{plot_id}.{'_'.join(parts)}"

    @staticmethod
    def manager_key(manager: str, *parts: str) -> str:
        """Build a namespaced key for a data manager."""
        return f"manager.{manager}.{'_'.join(parts)}"

    @staticmethod
    def global_key(*parts: str) -> str:
        """Build a namespaced key for global UI state."""
        return f"g.{'_'.join(parts)}"


class _PlotUIState:
    """
    Typed accessors for plot-related UI state.

    Namespaced under ``plot.{plot_id}.*``.
    """

    # Key Builders
    @staticmethod
    def _key(plot_id: int, suffix: str) -> str:
        """Build a namespaced session_state key for a plot."""
        return WidgetKeyBuilder.plot_key(plot_id, suffix)

    # Auto Refresh
    def get_auto_refresh(self, plot_id: int) -> bool:
        """Get whether auto-refresh is enabled for a plot."""
        return bool(st.session_state.get(self._key(plot_id, "auto_refresh"), True))

    def set_auto_refresh(self, plot_id: int, value: bool) -> None:
        """Set auto-refresh state for a plot."""
        st.session_state[self._key(plot_id, "auto_refresh")] = value

    # Dialog Visibility
    def is_dialog_visible(self, plot_id: int, dialog: str) -> bool:
        """Check if a dialog (save/load) is visible for a plot."""
        return bool(st.session_state.get(self._key(plot_id, f"dialog.{dialog}"), False))

    def set_dialog_visible(self, plot_id: int, dialog: str, visible: bool) -> None:
        """Show/hide a dialog for a plot."""
        st.session_state[self._key(plot_id, f"dialog.{dialog}")] = visible

    def hide_all_dialogs(self, plot_id: int) -> None:
        """Hide all dialogs for a plot."""
        for dialog in ("save", "load"):
            self.set_dialog_visible(plot_id, dialog, False)

    # Ordering State
    def get_order(self, plot_id: int, order_type: str) -> list[Any] | None:
        """Get custom ordering for a dimension (xaxis, group, legend)."""
        key: str = self._key(plot_id, f"order.{order_type}")
        result: list[Any] | None = st.session_state.get(key)
        return result

    def set_order(self, plot_id: int, order_type: str, order: list[Any]) -> None:
        """Set custom ordering for a dimension."""
        st.session_state[self._key(plot_id, f"order.{order_type}")] = order

    # Shape Editing
    def is_editing_shapes(self, plot_id: int) -> bool:
        """Check if shape editing mode is active for a plot."""
        return bool(st.session_state.get(self._key(plot_id, "edit_shapes"), False))

    def set_editing_shapes(self, plot_id: int, editing: bool) -> None:
        """Toggle shape editing mode for a plot."""
        st.session_state[self._key(plot_id, "edit_shapes")] = editing

    # Pending Relayout Updates
    def get_pending_updates(self) -> dict[str, Any] | None:
        """Get pending widget updates from a previous relayout event."""
        result: dict[str, Any] | None = st.session_state.get("plot.pending_updates")
        return result

    def set_pending_updates(self, updates: dict[str, Any]) -> None:
        """Store pending widget updates for the next rerun."""
        st.session_state["plot.pending_updates"] = updates

    def consume_pending_updates(self) -> dict[str, Any] | None:
        """Get and clear pending updates (atomic pop)."""
        result: dict[str, Any] | None = st.session_state.pop("plot.pending_updates", None)
        return result

    # Scoped Cleanup
    def cleanup(self, plot_id: int) -> None:
        """
        Remove ALL session_state keys associated with a plot.

        Must be called when a plot is deleted to prevent state leaks.
        Cleans both new namespaced keys and legacy keys for backward compat.
        """
        prefix: str = f"plot.{plot_id}."
        legacy_prefixes: list[str] = [
            f"auto_{plot_id}",
            f"show_save_for_plot_{plot_id}",
            f"show_load_for_plot_{plot_id}",
            f"edit_shapes_{plot_id}",
            f"auto_t_{plot_id}",
        ]

        keys_to_remove: list[str] = []
        for key in list(st.session_state.keys()):
            if isinstance(key, str) and (key.startswith(prefix) or key in legacy_prefixes):
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del st.session_state[key]


class _ManagerUIState:
    """
    Typed accessors for data manager UI state.

    Namespaced under ``manager.{manager_name}.*``.
    """

    @staticmethod
    def _key(manager_name: str, suffix: str) -> str:
        """Build a namespaced key for a data manager."""
        return WidgetKeyBuilder.manager_key(manager_name, suffix)

    # Load Triggers
    def get_load_trigger(self, manager_name: str) -> dict[str, Any] | None:
        """Get a pending load-from-history trigger for a manager."""
        result: dict[str, Any] | None = st.session_state.get(
            self._key(manager_name, "load_trigger")
        )
        return result

    def set_load_trigger(self, manager_name: str, record: dict[str, Any]) -> None:
        """Set a load-from-history trigger for a manager."""
        st.session_state[self._key(manager_name, "load_trigger")] = record

    def consume_load_trigger(self, manager_name: str) -> dict[str, Any] | None:
        """Get and clear a load trigger (atomic pop)."""
        result: dict[str, Any] | None = st.session_state.pop(
            self._key(manager_name, "load_trigger"), None
        )
        return result

    # Form Values
    def set_form_value(self, manager_name: str, field: str, value: Any) -> None:
        """Set a form field value for a manager."""
        st.session_state[self._key(manager_name, f"form.{field}")] = value

    def get_form_value(self, manager_name: str, field: str) -> Any | None:
        """Get a form field value for a manager."""
        return st.session_state.get(self._key(manager_name, f"form.{field}"))

    # Scoped Cleanup
    def cleanup(self, manager_name: str) -> None:
        """Remove all session_state keys for a manager."""
        prefix: str = f"manager.{manager_name}."
        keys_to_remove: list[str] = [
            key
            for key in st.session_state.keys()
            if isinstance(key, str) and key.startswith(prefix)
        ]
        for key in keys_to_remove:
            del st.session_state[key]


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

    def get_current_tab(self) -> str | None:
        """Get the current tab within a page."""
        result: str | None = st.session_state.get("nav.current_tab")
        return result

    def set_current_tab(self, tab: str) -> None:
        """Set the current tab."""
        st.session_state["nav.current_tab"] = tab


class _ExportUIState:
    """
    Typed accessors for export-related UI state.

    Namespaced under ``export.*``.
    """

    def get_last_export_path(self) -> str:
        """Get the last used export path."""
        result: str = st.session_state.get("export.last_path", "")
        return result

    def set_last_export_path(self, path: str) -> None:
        """Set the last used export path."""
        st.session_state["export.last_path"] = path


class UIStateManager:
    """Expose typed sub-managers for plot, manager, navigation, and export state."""

    def __init__(self) -> None:
        """Initialize sub-managers."""
        self.plot: _PlotUIState = _PlotUIState()
        self.manager: _ManagerUIState = _ManagerUIState()
        self.nav: _NavUIState = _NavUIState()
        self.export: _ExportUIState = _ExportUIState()

    def cleanup_all(self) -> None:
        """
        Remove all UI state keys (full reset).

        Removes all namespaced keys (``plot.*``, ``manager.*``, ``nav.*``,
        ``export.*``) from session_state.
        """
        prefixes: list[str] = ["plot.", "manager.", "nav.", "export."]
        keys_to_remove: list[str] = [
            key
            for key in list(st.session_state.keys())
            if isinstance(key, str) and any(key.startswith(p) for p in prefixes)
        ]
        for key in keys_to_remove:
            del st.session_state[key]

    def get_all_keys(self) -> list[str]:
        """
        Get all namespaced UI state keys (for debugging).

        Returns:
            List of all session_state keys managed by UIStateManager.
        """
        prefixes: list[str] = ["plot.", "manager.", "nav.", "export."]
        return [
            key
            for key in st.session_state.keys()
            if isinstance(key, str) and any(key.startswith(p) for p in prefixes)
        ]
