"""
UI State Manager — Centralized, Typed Session State Access.

Replaces all scattered ``st.session_state["key"]`` access in the web layer
with a single, namespaced, typed manager. Every piece of transient UI state
flows through this class.

Key Design Decisions:
    1. **Namespaced keys**: ``plot.{id}.auto_refresh`` instead of ``auto_{id}``.
       Prevents collisions and enables scoped cleanup.
    2. **Typed accessors**: ``get_auto_refresh(plot_id) -> bool`` instead of
       ``st.session_state.get(f"auto_{plot_id}", True)``.
    3. **Scoped cleanup**: ``cleanup_plot(plot_id)`` removes all keys for
       a deleted plot, preventing state leak.
    4. **Single source of truth**: All UI state (not domain state!) lives here.
       Domain state stays in ApplicationAPI / RepositoryStateManager.

Boundary:
    - UIStateManager owns **transient UI state** (dialog flags, auto-refresh,
      ordering widgets, pending relayout updates).
    - ApplicationAPI.state_manager owns **persistent domain state** (data,
      plots, config, history).

Usage in Controllers:
    ``ui_state = UIStateManager()``
    ``if ui_state.plot.get_auto_refresh(plot_id): ...``
    ``ui_state.plot.set_dialog_visible(plot_id, "save", True)``
"""

from typing import Any, Dict, List, Optional

import streamlit as st


class _PlotUIState:
    """
    Typed accessors for plot-related UI state.

    Namespaced under ``plot.{plot_id}.*``.
    """

    # ─── Key Builders ────────────────────────────────────────────────────

    @staticmethod
    def _key(plot_id: int, suffix: str) -> str:
        """Build a namespaced session_state key for a plot."""
        return f"plot.{plot_id}.{suffix}"

    # ─── Auto Refresh ────────────────────────────────────────────────────

    def get_auto_refresh(self, plot_id: int) -> bool:
        """Get whether auto-refresh is enabled for a plot."""
        return bool(st.session_state.get(self._key(plot_id, "auto_refresh"), True))

    def set_auto_refresh(self, plot_id: int, value: bool) -> None:
        """Set auto-refresh state for a plot."""
        st.session_state[self._key(plot_id, "auto_refresh")] = value

    # ─── Dialog Visibility ───────────────────────────────────────────────

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

    # ─── Ordering State ──────────────────────────────────────────────────

    def get_order(self, plot_id: int, order_type: str) -> Optional[List[Any]]:
        """Get custom ordering for a dimension (xaxis, group, legend)."""
        key: str = self._key(plot_id, f"order.{order_type}")
        result: Optional[List[Any]] = st.session_state.get(key)
        return result

    def set_order(self, plot_id: int, order_type: str, order: List[Any]) -> None:
        """Set custom ordering for a dimension."""
        st.session_state[self._key(plot_id, f"order.{order_type}")] = order

    # ─── Shape Editing ───────────────────────────────────────────────────

    def is_editing_shapes(self, plot_id: int) -> bool:
        """Check if shape editing mode is active for a plot."""
        return bool(st.session_state.get(self._key(plot_id, "edit_shapes"), False))

    def set_editing_shapes(self, plot_id: int, editing: bool) -> None:
        """Toggle shape editing mode for a plot."""
        st.session_state[self._key(plot_id, "edit_shapes")] = editing

    # ─── Pending Relayout Updates ────────────────────────────────────────

    def get_pending_updates(self) -> Optional[Dict[str, Any]]:
        """Get pending widget updates from a previous relayout event."""
        result: Optional[Dict[str, Any]] = st.session_state.get("plot.pending_updates")
        return result

    def set_pending_updates(self, updates: Dict[str, Any]) -> None:
        """Store pending widget updates for the next rerun."""
        st.session_state["plot.pending_updates"] = updates

    def consume_pending_updates(self) -> Optional[Dict[str, Any]]:
        """Get and clear pending updates (atomic pop)."""
        result: Optional[Dict[str, Any]] = st.session_state.pop("plot.pending_updates", None)
        return result

    # ─── Scoped Cleanup ──────────────────────────────────────────────────

    def cleanup(self, plot_id: int) -> None:
        """
        Remove ALL session_state keys associated with a plot.

        Must be called when a plot is deleted to prevent state leaks.
        Cleans both new namespaced keys and legacy keys for backward compat.
        """
        prefix: str = f"plot.{plot_id}."
        legacy_prefixes: List[str] = [
            f"auto_{plot_id}",
            f"show_save_for_plot_{plot_id}",
            f"show_load_for_plot_{plot_id}",
            f"edit_shapes_{plot_id}",
            f"auto_t_{plot_id}",
        ]

        keys_to_remove: List[str] = []
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
        return f"manager.{manager_name}.{suffix}"

    # ─── Load Triggers ───────────────────────────────────────────────────

    def get_load_trigger(self, manager_name: str) -> Optional[Dict[str, Any]]:
        """Get a pending load-from-history trigger for a manager."""
        result: Optional[Dict[str, Any]] = st.session_state.get(
            self._key(manager_name, "load_trigger")
        )
        return result

    def set_load_trigger(self, manager_name: str, record: Dict[str, Any]) -> None:
        """Set a load-from-history trigger for a manager."""
        st.session_state[self._key(manager_name, "load_trigger")] = record

    def consume_load_trigger(self, manager_name: str) -> Optional[Dict[str, Any]]:
        """Get and clear a load trigger (atomic pop)."""
        result: Optional[Dict[str, Any]] = st.session_state.pop(
            self._key(manager_name, "load_trigger"), None
        )
        return result

    # ─── Form Values ─────────────────────────────────────────────────────

    def set_form_value(self, manager_name: str, field: str, value: Any) -> None:
        """Set a form field value for a manager."""
        st.session_state[self._key(manager_name, f"form.{field}")] = value

    def get_form_value(self, manager_name: str, field: str) -> Optional[Any]:
        """Get a form field value for a manager."""
        return st.session_state.get(self._key(manager_name, f"form.{field}"))

    # ─── Scoped Cleanup ──────────────────────────────────────────────────

    def cleanup(self, manager_name: str) -> None:
        """Remove all session_state keys for a manager."""
        prefix: str = f"manager.{manager_name}."
        keys_to_remove: List[str] = [
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

    def get_current_page(self) -> Optional[str]:
        """Get the currently active page name."""
        result: Optional[str] = st.session_state.get("nav.current_page")
        return result

    def set_current_page(self, page: str) -> None:
        """Set the current page."""
        st.session_state["nav.current_page"] = page

    def get_current_tab(self) -> Optional[str]:
        """Get the current tab within a page."""
        result: Optional[str] = st.session_state.get("nav.current_tab")
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
    """
    Centralized, typed access to all UI-related session state.

    This is the **single entry point** for all transient UI state in the
    web layer. It replaces scattered ``st.session_state["key"]`` accesses
    with namespaced, typed sub-managers.

    Sub-managers:
        - ``plot``: Plot auto-refresh, dialog visibility, ordering, shapes
        - ``manager``: Data manager load triggers, form values
        - ``nav``: Current page, current tab
        - ``export``: Export paths and settings

    Example::

        ui = UIStateManager()
        if ui.plot.get_auto_refresh(plot_id):
            figure = plot.generate_figure()

        ui.plot.set_dialog_visible(plot_id, "save", True)
        ui.plot.cleanup(plot_id)  # On plot deletion
    """

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
        prefixes: List[str] = ["plot.", "manager.", "nav.", "export."]
        keys_to_remove: List[str] = [
            key
            for key in list(st.session_state.keys())
            if isinstance(key, str) and any(key.startswith(p) for p in prefixes)
        ]
        for key in keys_to_remove:
            del st.session_state[key]

    def get_all_keys(self) -> List[str]:
        """
        Get all namespaced UI state keys (for debugging/performance page).

        Returns:
            List of all session_state keys managed by UIStateManager.
        """
        prefixes: List[str] = ["plot.", "manager.", "nav.", "export."]
        return [
            key
            for key in st.session_state.keys()
            if isinstance(key, str) and any(key.startswith(p) for p in prefixes)
        ]
