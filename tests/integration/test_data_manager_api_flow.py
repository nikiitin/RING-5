"""Integration tests for data management through ApplicationAPI.

Covers Scenarios #3 (History lifecycle), #5 (Preview lifecycle),
and #6 (ManagersAPI through ApplicationAPI).

Tests:
    - Data loading → state population → column info extraction
    - History recording, retrieval, and removal cycle
    - Preview set/get/has/clear lifecycle
    - Apply shapers pipeline through API
    - Session reset clears all state
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from src.core.application_api import ApplicationAPI
from src.core.models.history_models import OperationRecord

# ===========================================================================
# Test Class 1: Data loading and state management
# ===========================================================================


class TestDataLoadingFlow:
    """Test data loading through ApplicationAPI and state transitions."""

    def test_load_csv_sets_data_in_state(
        self,
        facade: ApplicationAPI,
        rich_sample_data: pd.DataFrame,
        tmp_path: Path,
    ) -> None:
        """Loading CSV populates state_manager.get_data()."""
        # Write sample data to CSV
        csv_path: Path = tmp_path / "test_data.csv"
        rich_sample_data.to_csv(csv_path, index=False)

        # Load through API
        facade.load_data(str(csv_path))

        # Verify state
        loaded: pd.DataFrame = facade.state_manager.get_data()
        assert loaded is not None
        assert len(loaded) == len(rich_sample_data)
        assert set(loaded.columns) == set(rich_sample_data.columns)

    def test_load_data_clears_processed_data(
        self,
        facade: ApplicationAPI,
        rich_sample_data: pd.DataFrame,
        tmp_path: Path,
    ) -> None:
        """Loading new data resets processed_data to None."""
        # Pre-populate processed data
        facade.state_manager.set_processed_data(rich_sample_data)
        assert facade.state_manager.get_processed_data() is not None

        # Load new data
        csv_path: Path = tmp_path / "new_data.csv"
        rich_sample_data.to_csv(csv_path, index=False)
        facade.load_data(str(csv_path))

        # processed_data should be reset
        assert facade.state_manager.get_processed_data() is None

    def test_get_column_info_with_data(
        self,
        loaded_facade: ApplicationAPI,
    ) -> None:
        """get_column_info returns correct breakdown of numeric/categorical."""
        data: pd.DataFrame = loaded_facade.state_manager.get_data()
        info: Dict[str, Any] = loaded_facade.get_column_info(data)

        assert info["total_rows"] == 9  # rich_sample_data has 9 rows
        assert info["total_columns"] == 5
        assert "benchmark_name" in info["categorical_columns"]
        assert "system.cpu.ipc" in info["numeric_columns"]

    def test_get_column_info_with_none(
        self,
        facade: ApplicationAPI,
    ) -> None:
        """get_column_info with None returns zero-count dict."""
        info: Dict[str, Any] = facade.get_column_info(None)

        assert info["total_columns"] == 0
        assert info["total_rows"] == 0
        assert info["numeric_columns"] == []
        assert info["categorical_columns"] == []


# ===========================================================================
# Test Class 2: History lifecycle
# ===========================================================================


class TestHistoryLifecycle:
    """Test history recording, retrieval, and removal via ApplicationAPI."""

    def _make_record(self, operation: str) -> OperationRecord:
        """Create a test OperationRecord."""
        return OperationRecord(
            source_columns=["simTicks"],
            dest_columns=["simTicks_normalized"],
            operation=operation,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def test_add_and_get_history(self, facade: ApplicationAPI) -> None:
        """Adding records populates both manager and portfolio history."""
        record: OperationRecord = self._make_record("Normalize simTicks")
        facade.add_manager_history_record(record)

        manager_hist: List[OperationRecord] = facade.get_manager_history()
        portfolio_hist: List[OperationRecord] = facade.get_portfolio_history()

        assert len(manager_hist) >= 1
        assert len(portfolio_hist) >= 1
        assert manager_hist[-1]["operation"] == "Normalize simTicks"
        assert portfolio_hist[-1]["operation"] == "Normalize simTicks"

    def test_multiple_records_accumulate(self, facade: ApplicationAPI) -> None:
        """Multiple records accumulate in history."""
        for i in range(5):
            record: OperationRecord = self._make_record(f"Operation {i}")
            facade.add_manager_history_record(record)

        manager_hist: List[OperationRecord] = facade.get_manager_history()
        assert len(manager_hist) >= 5

    def test_remove_history_record(self, facade: ApplicationAPI) -> None:
        """Removing a record removes it from both manager and portfolio."""
        record: OperationRecord = self._make_record("To Remove")
        facade.add_manager_history_record(record)

        # Verify it's there
        assert any(r["operation"] == "To Remove" for r in facade.get_manager_history())

        # Remove
        facade.remove_manager_history_record(record)

        # Verify removed
        assert not any(r["operation"] == "To Remove" for r in facade.get_manager_history())
        assert not any(r["operation"] == "To Remove" for r in facade.get_portfolio_history())

    def test_history_empty_on_fresh_api(self, facade: ApplicationAPI) -> None:
        """Fresh API has empty history."""
        assert facade.get_manager_history() == []
        assert facade.get_portfolio_history() == []


# ===========================================================================
# Test Class 3: Preview lifecycle
# ===========================================================================


class TestPreviewLifecycle:
    """Test preview set/get/has/clear through ApplicationAPI."""

    def test_set_and_get_preview(
        self,
        facade: ApplicationAPI,
        rich_sample_data: pd.DataFrame,
    ) -> None:
        """set_preview stores data, get_preview retrieves it."""
        facade.set_preview("normalize", rich_sample_data)

        result: pd.DataFrame = facade.get_preview("normalize")
        assert result is not None
        pd.testing.assert_frame_equal(result, rich_sample_data)

    def test_has_preview(
        self,
        facade: ApplicationAPI,
        rich_sample_data: pd.DataFrame,
    ) -> None:
        """has_preview returns True after set, False before."""
        assert facade.has_preview("test_op") is False
        facade.set_preview("test_op", rich_sample_data)
        assert facade.has_preview("test_op") is True

    def test_clear_preview(
        self,
        facade: ApplicationAPI,
        rich_sample_data: pd.DataFrame,
    ) -> None:
        """clear_preview removes the stored preview."""
        facade.set_preview("to_clear", rich_sample_data)
        assert facade.has_preview("to_clear") is True

        facade.clear_preview("to_clear")
        assert facade.has_preview("to_clear") is False

    def test_multiple_previews_independent(
        self,
        facade: ApplicationAPI,
        rich_sample_data: pd.DataFrame,
    ) -> None:
        """Different operation names store independent previews."""
        subset: pd.DataFrame = rich_sample_data[["benchmark_name", "system.cpu.ipc"]]

        facade.set_preview("op_a", rich_sample_data)
        facade.set_preview("op_b", subset)

        result_a: pd.DataFrame = facade.get_preview("op_a")
        result_b: pd.DataFrame = facade.get_preview("op_b")

        assert len(result_a.columns) == 5
        assert len(result_b.columns) == 2

    def test_clear_one_preview_keeps_others(
        self,
        facade: ApplicationAPI,
        rich_sample_data: pd.DataFrame,
    ) -> None:
        """Clearing one preview does not affect others."""
        facade.set_preview("keep", rich_sample_data)
        facade.set_preview("remove", rich_sample_data)

        facade.clear_preview("remove")

        assert facade.has_preview("keep") is True
        assert facade.has_preview("remove") is False


# ===========================================================================
# Test Class 4: Apply shapers pipeline through API
# ===========================================================================


class TestApplyShapersPipeline:
    """Test apply_shapers through ApplicationAPI."""

    def test_column_selector_pipeline(
        self,
        loaded_facade: ApplicationAPI,
    ) -> None:
        """Apply columnSelector shaper through API pipeline."""
        data: pd.DataFrame = loaded_facade.state_manager.get_data()

        pipeline: List[Dict[str, Any]] = [
            {
                "type": "columnSelector",
                "columns": ["benchmark_name", "system.cpu.ipc"],
            },
        ]

        result: pd.DataFrame = loaded_facade.apply_shapers(data, pipeline)

        assert list(result.columns) == ["benchmark_name", "system.cpu.ipc"]
        assert len(result) == 9

    def test_multi_step_pipeline(
        self,
        loaded_facade: ApplicationAPI,
    ) -> None:
        """Apply multiple shapers: columnSelector → sort sequentially."""
        data: pd.DataFrame = loaded_facade.state_manager.get_data()

        pipeline: List[Dict[str, Any]] = [
            {
                "type": "columnSelector",
                "columns": [
                    "benchmark_name",
                    "config_description",
                    "system.cpu.ipc",
                ],
            },
            {
                "type": "sort",
                "order_dict": {
                    "benchmark_name": ["xalancbmk", "omnetpp", "mcf"],
                },
            },
        ]

        result: pd.DataFrame = loaded_facade.apply_shapers(data, pipeline)

        assert list(result.columns) == [
            "benchmark_name",
            "config_description",
            "system.cpu.ipc",
        ]
        # Verify sort order
        benchmarks = result["benchmark_name"].unique().tolist()
        assert benchmarks == ["xalancbmk", "omnetpp", "mcf"]

    def test_normalize_pipeline(
        self,
        loaded_facade: ApplicationAPI,
    ) -> None:
        """Apply normalize shaper through pipeline API."""
        data: pd.DataFrame = loaded_facade.state_manager.get_data()

        pipeline: List[Dict[str, Any]] = [
            {
                "type": "columnSelector",
                "columns": [
                    "benchmark_name",
                    "config_description",
                    "system.cpu.ipc",
                ],
            },
            {
                "type": "normalize",
                "normalizeVars": ["system.cpu.ipc"],
                "normalizerColumn": "config_description",
                "normalizerValue": "baseline",
                "groupBy": ["benchmark_name"],
            },
        ]

        result: pd.DataFrame = loaded_facade.apply_shapers(data, pipeline)

        # Baseline rows should be exactly 1.0
        baseline_rows = result[result["config_description"] == "baseline"]
        for val in baseline_rows["system.cpu.ipc"]:
            assert abs(val - 1.0) < 1e-6


# ===========================================================================
# Test Class 5: Session reset
# ===========================================================================


class TestSessionReset:
    """Test that session reset clears all state."""

    def test_reset_clears_data_and_history(
        self,
        loaded_facade: ApplicationAPI,
    ) -> None:
        """reset clears data and history (previews are independent)."""
        api: ApplicationAPI = loaded_facade

        # Populate some state
        record: OperationRecord = OperationRecord(
            source_columns=["a"],
            dest_columns=["b"],
            operation="test",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        api.add_manager_history_record(record)

        # Verify populated
        assert api.state_manager.get_data() is not None
        assert len(api.get_manager_history()) > 0

        # Reset
        api.state_manager.clear_all()

        # Verify cleared
        assert api.state_manager.get_data() is None
        assert api.get_manager_history() == []
