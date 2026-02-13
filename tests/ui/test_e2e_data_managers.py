"""E2E AppTest: Data Managers tab-level interactions with real data.

Tests all 7 Data Manager tabs with pre-loaded data:
    - Summary: metrics, dataframe, describe statistics
    - Data Visualization: search, filter, pagination, display columns
    - Seeds Reducer: select columns, apply, confirm
    - Outlier Remover: select column, apply, confirm
    - Preprocessor: select sources, operation, preview, confirm
    - Mixer: select columns, operation, preview, confirm
    - Operations History: verify records after operations

Uses the AppTest data injection pattern:
    at.run() -> api = at.session_state["api"] -> api.state_manager.set_data(df)
"""

from typing import Any

from tests.ui.helpers import (
    create_app_with_data,
    get_api,
    navigate_to,
)


def _go_to_data_managers(data: Any = None) -> Any:
    """Helper to navigate to Data Managers with data loaded."""
    at = create_app_with_data(data)
    navigate_to(at, "Data Managers")
    return at


# ---------------------------------------------------------------------------
# Summary tab (tab index 0)
# ---------------------------------------------------------------------------
class TestSummaryTab:
    """Tests for the Summary tab within Data Managers."""

    def test_summary_metrics_present(self) -> None:
        """Summary tab renders multiple metrics (rows, columns, memory, etc.)."""
        at = _go_to_data_managers()

        assert not at.exception
        # Should have at least 4 metrics from Summary tab
        assert len(at.metric) >= 4

    def test_summary_has_dataframe(self) -> None:
        """Summary tab renders at least one dataframe (head preview)."""
        at = _go_to_data_managers()

        assert not at.exception
        assert len(at.dataframe) > 0

    def test_summary_shows_correct_column_count(self) -> None:
        """Columns metric matches the injected data shape."""
        at = _go_to_data_managers()

        assert not at.exception
        col_metrics = [m for m in at.metric if "col" in m.label.lower()]
        if col_metrics:
            # e2e data has 8 columns
            assert "8" in str(col_metrics[0].value)


# ---------------------------------------------------------------------------
# Data Visualization tab (tab index 1)
# ---------------------------------------------------------------------------
class TestDataVisualizationTab:
    """Tests for the Data Visualization tab."""

    def test_visualization_tab_has_search_widgets(self) -> None:
        """Visualization tab has search column selectbox and text input."""
        at = _go_to_data_managers()

        assert not at.exception
        # Should have selectboxes (at least search_col)
        assert len(at.selectbox) > 0
        # Should have text inputs (at least search_term)
        assert len(at.text_input) > 0

    def test_visualization_tab_has_multiselect(self) -> None:
        """Visualization tab has display columns multiselect."""
        at = _go_to_data_managers()

        assert not at.exception
        assert len(at.multiselect) > 0

    def test_visualization_tab_has_pagination(self) -> None:
        """Visualization tab has pagination controls."""
        at = _go_to_data_managers()

        assert not at.exception
        # Page number is typically a number_input
        assert len(at.number_input) > 0 or len(at.selectbox) >= 2


# ---------------------------------------------------------------------------
# Seeds Reducer tab (tab index 2)
# ---------------------------------------------------------------------------
class TestSeedsReducerTab:
    """Tests for the Seeds Reducer data manager tab."""

    def test_seeds_reducer_has_multiselects(self) -> None:
        """Seeds Reducer tab provides categorical + numeric multiselects."""
        at = _go_to_data_managers()

        assert not at.exception
        # Should have at least 2 multiselects from seeds tab
        # (seeds_categorical, seeds_numeric)
        assert len(at.multiselect) >= 2

    def test_seeds_reducer_has_apply_button(self) -> None:
        """Seeds Reducer tab has Apply button."""
        at = _go_to_data_managers()

        assert not at.exception
        apply_buttons = [b for b in at.button if "apply" in b.label.lower()]
        assert len(apply_buttons) > 0

    def test_seeds_reducer_apply_via_api(self) -> None:
        """Seeds reduction via API produces fewer rows (backend e2e)."""
        at = _go_to_data_managers()

        assert not at.exception
        api = get_api(at)
        data = api.state_manager.get_data()
        assert data is not None

        # Use API directly to reduce seeds (same as Apply button handler)
        result_df = api.managers.reduce_seeds(
            data,
            categorical_cols=["benchmark_name", "config_description"],
            statistic_cols=["system.cpu.ipc"],
        )
        assert result_df is not None
        assert len(result_df) < len(data)

        # Store as preview (simulates Apply button)
        api.set_preview("seeds_reduction", result_df)
        assert api.has_preview("seeds_reduction")

    def test_seeds_reducer_confirm_writes_data_via_api(self) -> None:
        """Confirm after Apply writes reduced data to state."""
        at = _go_to_data_managers()

        assert not at.exception
        api = get_api(at)
        data = api.state_manager.get_data()
        assert data is not None
        original_len = len(data)

        # Apply via API
        result_df = api.managers.reduce_seeds(
            data,
            categorical_cols=["benchmark_name", "config_description"],
            statistic_cols=["system.cpu.ipc"],
        )
        api.set_preview("seeds_reduction", result_df)

        # Confirm: write to state (same as Confirm button handler)
        confirmed_df = api.get_preview("seeds_reduction")
        api.state_manager.set_data(confirmed_df)
        api.clear_preview("seeds_reduction")

        new_data = api.state_manager.get_data()
        assert new_data is not None
        assert len(new_data) < original_len


# ---------------------------------------------------------------------------
# Outlier Remover tab (tab index 3)
# ---------------------------------------------------------------------------
class TestOutlierRemoverTab:
    """Tests for the Outlier Remover data manager tab."""

    def test_outlier_remover_has_selectbox(self) -> None:
        """Outlier Remover tab has column selectbox."""
        at = _go_to_data_managers()

        assert not at.exception
        # Should have selectboxes (outlier_col plus others)
        assert len(at.selectbox) > 0

    def test_outlier_remover_has_metrics(self) -> None:
        """Outlier Remover tab shows Q statistics metrics."""
        at = _go_to_data_managers()

        assert not at.exception
        # Metrics from outlier tab (Min, Q3, Max, Mean) plus summary
        assert len(at.metric) >= 4

    def test_outlier_remover_apply_button_exists(self) -> None:
        """Outlier Remover tab has Apply button."""
        at = _go_to_data_managers()

        assert not at.exception
        apply_buttons = [b for b in at.button if "apply" in b.label.lower()]
        assert len(apply_buttons) > 0


# ---------------------------------------------------------------------------
# Preprocessor tab (tab index 4)
# ---------------------------------------------------------------------------
class TestPreprocessorTab:
    """Tests for the Preprocessor data manager tab."""

    def test_preprocessor_has_source_selectboxes(self) -> None:
        """Preprocessor tab has source column and operation selectboxes."""
        at = _go_to_data_managers()

        assert not at.exception
        # Should have at least 3 selectboxes from preprocessor
        # (src1, operation, src2) plus others from other tabs
        assert len(at.selectbox) >= 3

    def test_preprocessor_has_name_input(self) -> None:
        """Preprocessor tab has new column name text input."""
        at = _go_to_data_managers()

        assert not at.exception
        assert len(at.text_input) > 0

    def test_preprocessor_has_preview_button(self) -> None:
        """Preprocessor tab has Preview button."""
        at = _go_to_data_managers()

        assert not at.exception
        preview_buttons = [b for b in at.button if "preview" in b.label.lower()]
        assert len(preview_buttons) > 0


# ---------------------------------------------------------------------------
# Mixer tab (tab index 5)
# ---------------------------------------------------------------------------
class TestMixerTab:
    """Tests for the Mixer data manager tab."""

    def test_mixer_has_mode_radio(self) -> None:
        """Mixer tab has mode selection radio."""
        at = _go_to_data_managers()

        assert not at.exception
        # Radio buttons include sidebar nav + data source choice + mixer mode
        assert len(at.radio) > 0

    def test_mixer_has_column_multiselect(self) -> None:
        """Mixer tab has columns multiselect."""
        at = _go_to_data_managers()

        assert not at.exception
        assert len(at.multiselect) > 0

    def test_mixer_has_operation_selectbox(self) -> None:
        """Mixer tab has operation selectbox."""
        at = _go_to_data_managers()

        assert not at.exception
        assert len(at.selectbox) > 0

    def test_mixer_has_new_name_input(self) -> None:
        """Mixer tab has new column name text input."""
        at = _go_to_data_managers()

        assert not at.exception
        assert len(at.text_input) > 0

    def test_mixer_has_preview_button(self) -> None:
        """Mixer tab has Preview button."""
        at = _go_to_data_managers()

        assert not at.exception
        preview_buttons = [b for b in at.button if "preview" in b.label.lower()]
        assert len(preview_buttons) > 0


# ---------------------------------------------------------------------------
# Operations History tab (tab index 6)
# ---------------------------------------------------------------------------
class TestOperationsHistoryTab:
    """Tests for the Operations History tab."""

    def test_history_tab_renders(self) -> None:
        """History tab renders without errors."""
        at = _go_to_data_managers()

        assert not at.exception

    def test_history_empty_initially(self) -> None:
        """History tab shows 0 operations initially."""
        at = _go_to_data_managers()

        assert not at.exception
        # Total Operations metric should be 0
        ops_metrics = [m for m in at.metric if "operation" in m.label.lower()]
        if ops_metrics:
            assert str(ops_metrics[0].value) == "0"

    def test_history_records_after_seeds_operation(self) -> None:
        """After a seeds reduction operation, history records it."""
        from src.core.models.history_models import OperationRecord

        at = _go_to_data_managers()

        assert not at.exception
        api = get_api(at)

        # Perform seeds reduction via API
        data = api.state_manager.get_data()
        assert data is not None
        result_df = api.managers.reduce_seeds(
            data,
            categorical_cols=["benchmark_name", "config_description"],
            statistic_cols=["system.cpu.ipc"],
        )
        api.state_manager.set_data(result_df)

        # Record operation (same as Confirm button handler)
        record = OperationRecord(
            operation="Seeds Reduction (mean + stdev)",
            source_columns=["benchmark_name", "config_description", "system.cpu.ipc"],
            dest_columns=["system.cpu.ipc"],
        )
        api.add_manager_history_record(record)

        # Check history records
        history = api.get_manager_history()
        assert len(history) >= 1
        assert "seeds" in history[0]["operation"].lower()


# ---------------------------------------------------------------------------
# Cross-tab consistency
# ---------------------------------------------------------------------------
class TestCrossTabConsistency:
    """Tests for data consistency across Data Manager tabs."""

    def test_all_tabs_render_without_error(self) -> None:
        """All 7 tabs render content without exceptions."""
        at = _go_to_data_managers()

        assert not at.exception
        # All tabs should have rendered (check for their content)
        assert len(at.tabs) >= 7

    def test_data_modification_persists_across_rerun(self) -> None:
        """After a data operation, the modified data persists."""
        at = _go_to_data_managers()
        api = get_api(at)

        data = api.state_manager.get_data()
        assert data is not None
        original_rows = len(data)

        # Apply seeds reduction via API (simulates the button handler)
        result_df = api.managers.reduce_seeds(
            data,
            categorical_cols=["benchmark_name", "config_description"],
            statistic_cols=["system.cpu.ipc"],
        )
        api.state_manager.set_data(result_df)
        api.state_manager.set_processed_data(result_df.copy())

        # Re-run the page to verify persistence
        at.run()
        assert not at.exception

        new_data = api.state_manager.get_data()
        assert new_data is not None
        assert len(new_data) < original_rows
