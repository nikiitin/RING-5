"""In-memory operation history for managers and portfolios."""

from contextlib import suppress
import logging

from src.core.models.history_models import OperationRecord

logger = logging.getLogger(__name__)

_MANAGER_HISTORY_MAX: int = 10


class HistoryRepository:
    """Store bounded manager history and unbounded portfolio history."""

    def __init__(self) -> None:
        """Initialize empty history lists."""
        self._manager_history: list[OperationRecord] = []
        self._portfolio_history: list[OperationRecord] = []

    # ==================== Manager History ====================

    def get_manager_history(self) -> list[OperationRecord]:
        """Return a copy of the manager history list."""
        return list(self._manager_history)

    def add_manager_record(self, record: OperationRecord) -> None:
        """Append a record and evict oldest if cap exceeded."""
        self._manager_history.append(record)
        if len(self._manager_history) > _MANAGER_HISTORY_MAX:
            self._manager_history = self._manager_history[-_MANAGER_HISTORY_MAX:]
        logger.debug(
            "HISTORY_REPO: Manager record added (%s), total=%d",
            record["operation"],
            len(self._manager_history),
        )

    def set_manager_history(self, records: list[OperationRecord]) -> None:
        """Bulk-set manager history (used for portfolio restore)."""
        self._manager_history = list(records)

    def clear_manager_history(self) -> None:
        """Clear all manager history."""
        self._manager_history.clear()

    # ==================== Portfolio History ====================

    def get_portfolio_history(self) -> list[OperationRecord]:
        """Return a copy of the portfolio history list."""
        return list(self._portfolio_history)

    def add_portfolio_record(self, record: OperationRecord) -> None:
        """Append a record to portfolio history (no cap)."""
        self._portfolio_history.append(record)
        logger.debug(
            "HISTORY_REPO: Portfolio record added (%s), total=%d",
            record["operation"],
            len(self._portfolio_history),
        )

    def set_portfolio_history(self, records: list[OperationRecord]) -> None:
        """Bulk-set portfolio history (used for portfolio restore)."""
        self._portfolio_history = list(records)

    def clear_portfolio_history(self) -> None:
        """Clear all portfolio history."""
        self._portfolio_history.clear()

    # ==================== Removal ====================

    def remove_manager_record(self, record: OperationRecord) -> None:
        """Remove first matching record from manager history."""
        with suppress(ValueError):
            self._manager_history.remove(record)

    def remove_portfolio_record(self, record: OperationRecord) -> None:
        """Remove first matching record from portfolio history."""
        with suppress(ValueError):
            self._portfolio_history.remove(record)

    # ==================== Lifecycle ======================================

    def clear_all(self) -> None:
        """Clear both history lists."""
        self.clear_manager_history()
        self.clear_portfolio_history()
        logger.info("HISTORY_REPO: All history cleared")
