"""
Tests for UIStateManager (Layer 4).

Uses a mock session_state dictionary to validate typed accessors,
namespaced keys, and scoped cleanup without requiring Streamlit runtime.
"""

from typing import Any, Dict, List
from unittest.mock import patch

import pytest

# ─── Helper: Mock session_state ──────────────────────────────────────────────


class MockSessionState(dict):
    """Dict subclass that behaves like st.session_state for testing."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def pop(self, key: str, *args: Any) -> Any:
        return super().pop(key, *args)


@pytest.fixture
def mock_state() -> MockSessionState:
    """Provide a fresh mock session_state and patch st.session_state."""
    state = MockSessionState()
    with patch("src.web.state.ui_state_manager.st") as mock_st:
        mock_st.session_state = state
        yield state


@pytest.fixture
def ui_state(mock_state: MockSessionState) -> Any:
    """Provide an initialized UIStateManager with mock state."""
    from src.web.state.ui_state_manager import UIStateManager

    return UIStateManager()


# ─── Plot UI State ───────────────────────────────────────────────────────────


class TestPlotUIState:
    """Tests for _PlotUIState accessors."""

    def test_auto_refresh_default_true(self, ui_state: Any, mock_state: MockSessionState) -> None:
        """Auto-refresh should default to True for new plots."""
        assert ui_state.plot.get_auto_refresh(1) is True

    def test_auto_refresh_set_and_get(self, ui_state: Any, mock_state: MockSessionState) -> None:
        ui_state.plot.set_auto_refresh(1, False)
        assert ui_state.plot.get_auto_refresh(1) is False
        assert mock_state["plot.1.auto_refresh"] is False

    def test_auto_refresh_per_plot_isolation(
        self, ui_state: Any, mock_state: MockSessionState
    ) -> None:
        """Each plot has independent auto-refresh state."""
        ui_state.plot.set_auto_refresh(1, False)
        ui_state.plot.set_auto_refresh(2, True)
        assert ui_state.plot.get_auto_refresh(1) is False
        assert ui_state.plot.get_auto_refresh(2) is True

    def test_dialog_visibility_default_false(
        self, ui_state: Any, mock_state: MockSessionState
    ) -> None:
        assert ui_state.plot.is_dialog_visible(1, "save") is False
        assert ui_state.plot.is_dialog_visible(1, "load") is False

    def test_dialog_visibility_set_and_get(
        self, ui_state: Any, mock_state: MockSessionState
    ) -> None:
        ui_state.plot.set_dialog_visible(1, "save", True)
        assert ui_state.plot.is_dialog_visible(1, "save") is True
        assert mock_state["plot.1.dialog.save"] is True

    def test_hide_all_dialogs(self, ui_state: Any, mock_state: MockSessionState) -> None:
        ui_state.plot.set_dialog_visible(1, "save", True)
        ui_state.plot.set_dialog_visible(1, "load", True)
        ui_state.plot.hide_all_dialogs(1)
        assert ui_state.plot.is_dialog_visible(1, "save") is False
        assert ui_state.plot.is_dialog_visible(1, "load") is False

    def test_dialog_namespacing_key_format(
        self, ui_state: Any, mock_state: MockSessionState
    ) -> None:
        """Verify the actual key format in session_state."""
        ui_state.plot.set_dialog_visible(42, "save", True)
        assert "plot.42.dialog.save" in mock_state

    def test_ordering_default_none(self, ui_state: Any, mock_state: MockSessionState) -> None:
        assert ui_state.plot.get_order(1, "xaxis") is None

    def test_ordering_set_and_get(self, ui_state: Any, mock_state: MockSessionState) -> None:
        order: List[str] = ["bench_a", "bench_c", "bench_b"]
        ui_state.plot.set_order(1, "xaxis", order)
        assert ui_state.plot.get_order(1, "xaxis") == order

    def test_editing_shapes_default_false(
        self, ui_state: Any, mock_state: MockSessionState
    ) -> None:
        assert ui_state.plot.is_editing_shapes(1) is False

    def test_editing_shapes_toggle(self, ui_state: Any, mock_state: MockSessionState) -> None:
        ui_state.plot.set_editing_shapes(1, True)
        assert ui_state.plot.is_editing_shapes(1) is True
        ui_state.plot.set_editing_shapes(1, False)
        assert ui_state.plot.is_editing_shapes(1) is False

    def test_pending_updates_default_none(
        self, ui_state: Any, mock_state: MockSessionState
    ) -> None:
        assert ui_state.plot.get_pending_updates() is None

    def test_pending_updates_set_and_get(self, ui_state: Any, mock_state: MockSessionState) -> None:
        updates: Dict[str, Any] = {"x_1": [0.5, 10.5]}
        ui_state.plot.set_pending_updates(updates)
        assert ui_state.plot.get_pending_updates() == updates

    def test_pending_updates_consume(self, ui_state: Any, mock_state: MockSessionState) -> None:
        """consume_pending_updates should return and clear."""
        updates: Dict[str, Any] = {"auto_1": True}
        ui_state.plot.set_pending_updates(updates)
        consumed = ui_state.plot.consume_pending_updates()
        assert consumed == updates
        assert ui_state.plot.get_pending_updates() is None

    def test_consume_when_empty(self, ui_state: Any, mock_state: MockSessionState) -> None:
        assert ui_state.plot.consume_pending_updates() is None


class TestPlotUIStateCleanup:
    """Tests for scoped cleanup on plot deletion."""

    def test_cleanup_removes_namespaced_keys(
        self, ui_state: Any, mock_state: MockSessionState
    ) -> None:
        """cleanup(plot_id) should remove all plot.{id}.* keys."""
        ui_state.plot.set_auto_refresh(1, False)
        ui_state.plot.set_dialog_visible(1, "save", True)
        ui_state.plot.set_dialog_visible(1, "load", True)
        ui_state.plot.set_order(1, "xaxis", ["a", "b"])
        ui_state.plot.set_editing_shapes(1, True)

        # Verify keys exist
        plot_keys = [k for k in mock_state if isinstance(k, str) and k.startswith("plot.1.")]
        assert len(plot_keys) >= 4

        # Cleanup
        ui_state.plot.cleanup(1)

        # All plot.1.* keys should be gone
        remaining = [k for k in mock_state if isinstance(k, str) and k.startswith("plot.1.")]
        assert remaining == []

    def test_cleanup_preserves_other_plots(
        self, ui_state: Any, mock_state: MockSessionState
    ) -> None:
        """cleanup(1) should NOT touch plot.2.* keys."""
        ui_state.plot.set_auto_refresh(1, False)
        ui_state.plot.set_auto_refresh(2, True)

        ui_state.plot.cleanup(1)

        assert ui_state.plot.get_auto_refresh(2) is True
        assert "plot.2.auto_refresh" in mock_state

    def test_cleanup_removes_legacy_keys(self, ui_state: Any, mock_state: MockSessionState) -> None:
        """cleanup should also remove legacy (un-namespaced) keys."""
        mock_state["auto_5"] = True
        mock_state["show_save_for_plot_5"] = True
        mock_state["show_load_for_plot_5"] = False
        mock_state["edit_shapes_5"] = True

        ui_state.plot.cleanup(5)

        assert "auto_5" not in mock_state
        assert "show_save_for_plot_5" not in mock_state
        assert "show_load_for_plot_5" not in mock_state
        assert "edit_shapes_5" not in mock_state


# ─── Manager UI State ────────────────────────────────────────────────────────


class TestManagerUIState:
    """Tests for _ManagerUIState accessors."""

    def test_load_trigger_default_none(self, ui_state: Any, mock_state: MockSessionState) -> None:
        assert ui_state.manager.get_load_trigger("seeds_reducer") is None

    def test_load_trigger_set_and_get(self, ui_state: Any, mock_state: MockSessionState) -> None:
        record: Dict[str, Any] = {
            "manager_name": "Seeds Reducer",
            "source_columns": ["benchmark", "config"],
            "dest_columns": ["ipc"],
        }
        ui_state.manager.set_load_trigger("seeds_reducer", record)
        assert ui_state.manager.get_load_trigger("seeds_reducer") == record

    def test_load_trigger_consume(self, ui_state: Any, mock_state: MockSessionState) -> None:
        record: Dict[str, Any] = {"manager_name": "Outlier Remover"}
        ui_state.manager.set_load_trigger("outlier_remover", record)

        consumed = ui_state.manager.consume_load_trigger("outlier_remover")
        assert consumed == record
        assert ui_state.manager.get_load_trigger("outlier_remover") is None

    def test_form_values(self, ui_state: Any, mock_state: MockSessionState) -> None:
        ui_state.manager.set_form_value("preprocessor", "op", "multiply")
        ui_state.manager.set_form_value("preprocessor", "src1", "col_a")

        assert ui_state.manager.get_form_value("preprocessor", "op") == "multiply"
        assert ui_state.manager.get_form_value("preprocessor", "src1") == "col_a"

    def test_form_value_default_none(self, ui_state: Any, mock_state: MockSessionState) -> None:
        assert ui_state.manager.get_form_value("preprocessor", "nonexistent") is None

    def test_manager_namespacing(self, ui_state: Any, mock_state: MockSessionState) -> None:
        """Verify actual key format."""
        ui_state.manager.set_form_value("mixer", "mode", "merge")
        assert "manager.mixer.form.mode" in mock_state

    def test_cleanup_removes_all_manager_keys(
        self, ui_state: Any, mock_state: MockSessionState
    ) -> None:
        ui_state.manager.set_load_trigger("seeds", {"data": "test"})
        ui_state.manager.set_form_value("seeds", "col", "benchmark")
        ui_state.manager.set_form_value("seeds", "numeric", "ipc")

        ui_state.manager.cleanup("seeds")

        remaining = [k for k in mock_state if isinstance(k, str) and k.startswith("manager.seeds.")]
        assert remaining == []

    def test_cleanup_preserves_other_managers(
        self, ui_state: Any, mock_state: MockSessionState
    ) -> None:
        ui_state.manager.set_form_value("seeds", "col", "a")
        ui_state.manager.set_form_value("mixer", "col", "b")

        ui_state.manager.cleanup("seeds")

        assert ui_state.manager.get_form_value("mixer", "col") == "b"


# ─── Navigation UI State ────────────────────────────────────────────────────


class TestNavUIState:
    """Tests for _NavUIState accessors."""

    def test_current_page_default_none(self, ui_state: Any, mock_state: MockSessionState) -> None:
        assert ui_state.nav.get_current_page() is None

    def test_current_page_set_and_get(self, ui_state: Any, mock_state: MockSessionState) -> None:
        ui_state.nav.set_current_page("Manage Plots")
        assert ui_state.nav.get_current_page() == "Manage Plots"

    def test_current_tab_default_none(self, ui_state: Any, mock_state: MockSessionState) -> None:
        assert ui_state.nav.get_current_tab() is None

    def test_current_tab_set_and_get(self, ui_state: Any, mock_state: MockSessionState) -> None:
        ui_state.nav.set_current_tab("Seeds Reducer")
        assert ui_state.nav.get_current_tab() == "Seeds Reducer"


# ─── Export UI State ─────────────────────────────────────────────────────────


class TestExportUIState:
    """Tests for _ExportUIState accessors."""

    def test_last_export_path_default_empty(
        self, ui_state: Any, mock_state: MockSessionState
    ) -> None:
        assert ui_state.export.get_last_export_path() == ""

    def test_last_export_path_set_and_get(
        self, ui_state: Any, mock_state: MockSessionState
    ) -> None:
        ui_state.export.set_last_export_path("/home/user/papers/figures")
        assert ui_state.export.get_last_export_path() == "/home/user/papers/figures"

    def test_export_key_format(self, ui_state: Any, mock_state: MockSessionState) -> None:
        ui_state.export.set_last_export_path("/tmp/export")
        assert "export.last_path" in mock_state


# ─── UIStateManager (Top Level) ──────────────────────────────────────────────


class TestUIStateManager:
    """Tests for the top-level UIStateManager."""

    def test_sub_managers_accessible(self, ui_state: Any) -> None:
        assert ui_state.plot is not None
        assert ui_state.manager is not None
        assert ui_state.nav is not None
        assert ui_state.export is not None

    def test_cleanup_all(self, ui_state: Any, mock_state: MockSessionState) -> None:
        """cleanup_all should remove all namespaced keys."""
        ui_state.plot.set_auto_refresh(1, False)
        ui_state.plot.set_dialog_visible(2, "save", True)
        ui_state.manager.set_form_value("seeds", "col", "x")
        ui_state.nav.set_current_page("Data Source")
        ui_state.export.set_last_export_path("/tmp")

        # Also add a non-managed key
        mock_state["unrelated_key"] = "should_stay"

        ui_state.cleanup_all()

        # All managed keys gone
        assert "plot.1.auto_refresh" not in mock_state
        assert "plot.2.dialog.save" not in mock_state
        assert "manager.seeds.form.col" not in mock_state
        assert "nav.current_page" not in mock_state
        assert "export.last_path" not in mock_state

        # Non-managed key preserved
        assert mock_state["unrelated_key"] == "should_stay"

    def test_get_all_keys(self, ui_state: Any, mock_state: MockSessionState) -> None:
        ui_state.plot.set_auto_refresh(1, False)
        ui_state.manager.set_form_value("seeds", "col", "x")
        ui_state.nav.set_current_page("Data Source")
        mock_state["unrelated"] = True

        keys = ui_state.get_all_keys()
        assert "plot.1.auto_refresh" in keys
        assert "manager.seeds.form.col" in keys
        assert "nav.current_page" in keys
        assert "unrelated" not in keys

    def test_get_all_keys_empty(self, ui_state: Any, mock_state: MockSessionState) -> None:
        assert ui_state.get_all_keys() == []


# ─── Integration: Multiple Plots Lifecycle ───────────────────────────────────


class TestMultiPlotLifecycle:
    """Integration tests simulating a multi-plot workflow."""

    def test_create_configure_delete(self, ui_state: Any, mock_state: MockSessionState) -> None:
        """Simulate creating 3 plots, configuring them, then deleting one."""
        # Create 3 plots
        for pid in [1, 2, 3]:
            ui_state.plot.set_auto_refresh(pid, True)
            ui_state.plot.set_order(pid, "xaxis", ["a", "b", "c"])

        # Configure plot 2 with dialogs
        ui_state.plot.set_dialog_visible(2, "save", True)
        ui_state.plot.set_editing_shapes(2, True)

        # Delete plot 2
        ui_state.plot.cleanup(2)

        # Plot 2 keys all gone
        assert ui_state.plot.get_order(2, "xaxis") is None
        assert ui_state.plot.is_dialog_visible(2, "save") is False

        # Plots 1 and 3 untouched
        assert ui_state.plot.get_auto_refresh(1) is True
        assert ui_state.plot.get_order(3, "xaxis") == ["a", "b", "c"]

    def test_pending_updates_across_reruns(
        self, ui_state: Any, mock_state: MockSessionState
    ) -> None:
        """Simulate relayout event → store → consume on next rerun."""
        # Relayout event produces updates
        updates = {"x_1": [0, 10], "y_1": [0.5, 1.5]}
        ui_state.plot.set_pending_updates(updates)

        # "Next rerun" — consume
        consumed = ui_state.plot.consume_pending_updates()
        assert consumed == updates

        # Nothing left
        assert ui_state.plot.consume_pending_updates() is None
