"""Tests for the operation history system across all architecture layers.

Tests cover:
- OperationRecord model
- HistoryRepository (state layer)
- StateManager integration (protocol + concrete)
- ManagersAPI history methods (service layer)
- Portfolio persistence of history (data services layer)
"""

from typing import List

from src.core.models.history_models import OperationRecord
from src.core.state.repositories.history_repository import HistoryRepository

# =============================================================================
# Model Layer Tests
# =============================================================================


class TestOperationRecord:
    """Test the OperationRecord TypedDict structure."""

    def test_create_record(self) -> None:
        """Test creating a valid OperationRecord."""
        record: OperationRecord = {
            "source_columns": ["col_a", "col_b"],
            "dest_columns": ["col_c"],
            "operation": "Division",
            "timestamp": "2026-02-10T12:00:00+00:00",
        }
        assert record["source_columns"] == ["col_a", "col_b"]
        assert record["dest_columns"] == ["col_c"]
        assert record["operation"] == "Division"
        assert record["timestamp"] == "2026-02-10T12:00:00+00:00"

    def test_record_has_all_fields(self) -> None:
        """Test that OperationRecord has the expected fields."""
        record: OperationRecord = {
            "source_columns": [],
            "dest_columns": [],
            "operation": "",
            "timestamp": "",
        }
        assert "source_columns" in record
        assert "dest_columns" in record
        assert "operation" in record
        assert "timestamp" in record


# =============================================================================
# Repository Layer Tests
# =============================================================================


class TestHistoryRepository:
    """Test the HistoryRepository (state/repository layer)."""

    def test_initial_state_empty(self) -> None:
        """History starts empty."""
        repo = HistoryRepository()
        assert repo.get_manager_history() == []
        assert repo.get_portfolio_history() == []

    def test_add_manager_record(self) -> None:
        """Adding a record to manager history."""
        repo = HistoryRepository()
        record: OperationRecord = {
            "source_columns": ["a", "b"],
            "dest_columns": ["c"],
            "operation": "Sum",
            "timestamp": "2026-02-10T12:00:00+00:00",
        }
        repo.add_manager_record(record)
        history = repo.get_manager_history()
        assert len(history) == 1
        assert history[0] == record

    def test_add_portfolio_record(self) -> None:
        """Adding a record to portfolio history."""
        repo = HistoryRepository()
        record: OperationRecord = {
            "source_columns": ["x"],
            "dest_columns": ["y"],
            "operation": "Outlier Removal",
            "timestamp": "2026-02-10T12:00:00+00:00",
        }
        repo.add_portfolio_record(record)
        history = repo.get_portfolio_history()
        assert len(history) == 1
        assert history[0] == record

    def test_manager_history_max_20(self) -> None:
        """Manager history is capped at 20 entries (FIFO)."""
        repo = HistoryRepository()
        for i in range(25):
            repo.add_manager_record(
                {
                    "source_columns": [f"src_{i}"],
                    "dest_columns": [f"dst_{i}"],
                    "operation": f"op_{i}",
                    "timestamp": f"2026-02-10T12:{i:02d}:00+00:00",
                }
            )
        history = repo.get_manager_history()
        assert len(history) == 20
        # Oldest (0-4) should have been evicted; 5 is the oldest remaining
        assert history[0]["operation"] == "op_5"
        assert history[-1]["operation"] == "op_24"

    def test_portfolio_history_unlimited(self) -> None:
        """Portfolio history has no cap — it stores all operations."""
        repo = HistoryRepository()
        for i in range(50):
            repo.add_portfolio_record(
                {
                    "source_columns": [f"src_{i}"],
                    "dest_columns": [f"dst_{i}"],
                    "operation": f"op_{i}",
                    "timestamp": f"2026-02-10T12:{i:02d}:00+00:00",
                }
            )
        assert len(repo.get_portfolio_history()) == 50

    def test_manager_and_portfolio_are_independent(self) -> None:
        """Manager history and portfolio history are separate."""
        repo = HistoryRepository()
        repo.add_manager_record(
            {
                "source_columns": ["a"],
                "dest_columns": ["b"],
                "operation": "manager_op",
                "timestamp": "2026-02-10T12:00:00+00:00",
            }
        )
        repo.add_portfolio_record(
            {
                "source_columns": ["c"],
                "dest_columns": ["d"],
                "operation": "portfolio_op",
                "timestamp": "2026-02-10T12:01:00+00:00",
            }
        )
        assert len(repo.get_manager_history()) == 1
        assert len(repo.get_portfolio_history()) == 1
        assert repo.get_manager_history()[0]["operation"] == "manager_op"
        assert repo.get_portfolio_history()[0]["operation"] == "portfolio_op"

    def test_clear_manager_history(self) -> None:
        """Clearing manager history."""
        repo = HistoryRepository()
        repo.add_manager_record(
            {
                "source_columns": ["a"],
                "dest_columns": ["b"],
                "operation": "op",
                "timestamp": "2026-02-10T12:00:00+00:00",
            }
        )
        repo.clear_manager_history()
        assert repo.get_manager_history() == []

    def test_clear_portfolio_history(self) -> None:
        """Clearing portfolio history."""
        repo = HistoryRepository()
        repo.add_portfolio_record(
            {
                "source_columns": ["a"],
                "dest_columns": ["b"],
                "operation": "op",
                "timestamp": "2026-02-10T12:00:00+00:00",
            }
        )
        repo.clear_portfolio_history()
        assert repo.get_portfolio_history() == []

    def test_returns_copies(self) -> None:
        """get_ methods return copies so external mutation is safe."""
        repo = HistoryRepository()
        repo.add_manager_record(
            {
                "source_columns": ["a"],
                "dest_columns": ["b"],
                "operation": "op",
                "timestamp": "t",
            }
        )
        history = repo.get_manager_history()
        history.clear()  # Mutate the returned list
        assert len(repo.get_manager_history()) == 1  # Original unchanged

    def test_set_manager_history(self) -> None:
        """Bulk-setting manager history (for portfolio restore)."""
        repo = HistoryRepository()
        records: List[OperationRecord] = [
            {
                "source_columns": ["a"],
                "dest_columns": ["b"],
                "operation": "op1",
                "timestamp": "t1",
            },
            {
                "source_columns": ["c"],
                "dest_columns": ["d"],
                "operation": "op2",
                "timestamp": "t2",
            },
        ]
        repo.set_manager_history(records)
        assert len(repo.get_manager_history()) == 2
        assert repo.get_manager_history()[0]["operation"] == "op1"

    def test_set_portfolio_history(self) -> None:
        """Bulk-setting portfolio history (for portfolio restore)."""
        repo = HistoryRepository()
        records: List[OperationRecord] = [
            {
                "source_columns": ["a"],
                "dest_columns": ["b"],
                "operation": "op1",
                "timestamp": "t1",
            },
        ]
        repo.set_portfolio_history(records)
        assert len(repo.get_portfolio_history()) == 1

    def test_remove_manager_record(self) -> None:
        """Removing a specific record from manager history."""
        repo = HistoryRepository()
        record: OperationRecord = {
            "source_columns": ["a"],
            "dest_columns": ["b"],
            "operation": "op",
            "timestamp": "2026-02-10T12:00:00+00:00",
        }
        repo.add_manager_record(record)
        repo.remove_manager_record(record)
        assert repo.get_manager_history() == []

    def test_remove_portfolio_record(self) -> None:
        """Removing a specific record from portfolio history."""
        repo = HistoryRepository()
        record: OperationRecord = {
            "source_columns": ["a"],
            "dest_columns": ["b"],
            "operation": "op",
            "timestamp": "2026-02-10T12:00:00+00:00",
        }
        repo.add_portfolio_record(record)
        repo.remove_portfolio_record(record)
        assert repo.get_portfolio_history() == []

    def test_remove_nonexistent_record_no_error(self) -> None:
        """Removing a record that doesn't exist should not raise."""
        repo = HistoryRepository()
        record: OperationRecord = {
            "source_columns": ["a"],
            "dest_columns": ["b"],
            "operation": "op",
            "timestamp": "2026-02-10T12:00:00+00:00",
        }
        repo.remove_manager_record(record)
        repo.remove_portfolio_record(record)


# =============================================================================
# State Manager Integration Tests
# =============================================================================


class TestRepositoryStateManagerHistory:
    """Test history wiring through RepositoryStateManager."""

    def test_manager_history_methods_exist(self) -> None:
        """RepositoryStateManager exposes history methods."""
        from src.core.state.repository_state_manager import RepositoryStateManager

        rsm = RepositoryStateManager()
        assert hasattr(rsm, "add_manager_history_record")
        assert hasattr(rsm, "get_manager_history")
        assert hasattr(rsm, "add_portfolio_history_record")
        assert hasattr(rsm, "get_portfolio_history")

    def test_add_and_get_manager_history(self) -> None:
        """Round-trip through RepositoryStateManager for manager history."""
        from src.core.state.repository_state_manager import RepositoryStateManager

        rsm = RepositoryStateManager()
        record: OperationRecord = {
            "source_columns": ["x"],
            "dest_columns": ["y"],
            "operation": "Division",
            "timestamp": "2026-02-10T12:00:00+00:00",
        }
        rsm.add_manager_history_record(record)
        assert len(rsm.get_manager_history()) == 1

    def test_add_and_get_portfolio_history(self) -> None:
        """Round-trip through RepositoryStateManager for portfolio history."""
        from src.core.state.repository_state_manager import RepositoryStateManager

        rsm = RepositoryStateManager()
        record: OperationRecord = {
            "source_columns": ["a", "b"],
            "dest_columns": ["c"],
            "operation": "Seeds Reduction",
            "timestamp": "2026-02-10T12:00:00+00:00",
        }
        rsm.add_portfolio_history_record(record)
        assert len(rsm.get_portfolio_history()) == 1

    def test_clear_all_clears_history(self) -> None:
        """clear_all should clear history too."""
        from src.core.state.repository_state_manager import RepositoryStateManager

        rsm = RepositoryStateManager()
        rsm.add_manager_history_record(
            {
                "source_columns": ["a"],
                "dest_columns": ["b"],
                "operation": "op",
                "timestamp": "t",
            }
        )
        rsm.add_portfolio_history_record(
            {
                "source_columns": ["c"],
                "dest_columns": ["d"],
                "operation": "op2",
                "timestamp": "t2",
            }
        )
        rsm.clear_all()
        assert rsm.get_manager_history() == []
        assert rsm.get_portfolio_history() == []


# =============================================================================
# Portfolio Persistence Tests
# =============================================================================


class TestPortfolioHistoryPersistence:
    """Test that history is persisted/restored with portfolios."""

    def test_portfolio_data_has_history_fields(self) -> None:
        """PortfolioData TypedDict has history fields."""
        from src.core.models.portfolio_models import PortfolioData

        # Should be valid to construct with history fields
        data: PortfolioData = {
            "manager_history": [
                {
                    "source_columns": ["a"],
                    "dest_columns": ["b"],
                    "operation": "op",
                    "timestamp": "t",
                }
            ],
            "portfolio_history": [
                {
                    "source_columns": ["c"],
                    "dest_columns": ["d"],
                    "operation": "op2",
                    "timestamp": "t2",
                }
            ],
        }
        assert len(data["manager_history"]) == 1
        assert len(data["portfolio_history"]) == 1

    def test_session_restore_restores_history(self) -> None:
        """restore_session should restore history from portfolio data."""
        from src.core.models.portfolio_models import PortfolioData
        from src.core.state.repository_state_manager import RepositoryStateManager

        rsm = RepositoryStateManager()

        portfolio: PortfolioData = {
            "manager_history": [
                {
                    "source_columns": ["a"],
                    "dest_columns": ["b"],
                    "operation": "op",
                    "timestamp": "t",
                }
            ],
            "portfolio_history": [
                {
                    "source_columns": ["c"],
                    "dest_columns": ["d"],
                    "operation": "op2",
                    "timestamp": "t2",
                }
            ],
        }
        rsm.restore_session(portfolio)
        assert len(rsm.get_manager_history()) == 1
        assert rsm.get_manager_history()[0]["operation"] == "op"
        assert len(rsm.get_portfolio_history()) == 1
        assert rsm.get_portfolio_history()[0]["operation"] == "op2"
