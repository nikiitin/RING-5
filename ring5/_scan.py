"""Handle-based scanning for the public API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.core.common.security_limits import SCAN_BATCH_TIMEOUT_SECONDS
from src.core.models import ScanFileResult, ScanResult

from ring5.errors import ScanError

if TYPE_CHECKING:
    from concurrent.futures import Future

    from src.core.application_api import ApplicationAPI


@dataclass
class ScanJob:
    """A submitted scan batch whose handle owns its futures and context."""

    # [impl->req~ring5.ingestion.async-scan~1]

    api: "ApplicationAPI"
    futures: list["Future[ScanFileResult]"]
    stats_path: str
    stats_pattern: str

    def cancel(self) -> None:
        """Cancel only work belonging to this scan job."""
        for future in self.futures:
            future.cancel()

    def finalize(self, *, strict: bool = True) -> ScanResult:
        """Wait for discovery and aggregate its per-file results.

        Args:
            strict: Raise :class:`ScanError` if any selected file failed.
                With ``False``, return the partial result with ``failures``.
        """
        from concurrent.futures import wait

        _done, pending = wait(self.futures, timeout=SCAN_BATCH_TIMEOUT_SECONDS)
        if pending:
            cancelled = sum(future.cancel() for future in pending)
            raise ScanError(
                f"Scan batch exceeded {SCAN_BATCH_TIMEOUT_SECONDS:g} seconds; "
                f"{len(pending)} file(s) remained unfinished and cancellation "
                f"succeeded for {cancelled} not-yet-running file(s)."
            )

        try:
            result = self.api.finalize_scan([future.result() for future in self.futures])
        except Exception as exc:
            raise ScanError(f"Scan worker failed: {exc}") from exc

        if strict and result.failures:
            first = result.failures[0]
            raise ScanError(
                f"Scanning was incomplete: {len(result.failures)} of "
                f"{result.scanned_files or len(self.futures)} file(s) failed "
                f"(first error in {first.file_path}: {first.error}). "
                "Is perl installed and the stats path correct?"
            )

        state = self.api.state_manager
        state.set_stats_path(self.stats_path)
        state.set_stats_pattern(self.stats_pattern)
        state.set_scanned_variables([variable.to_dict() for variable in result.variables])
        return result
