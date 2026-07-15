"""
Gem5 Scan Work - Parallel Variable Discovery Task.

Encapsulates the work of scanning a single gem5 stats file to discover
available variables and their properties. Executed in worker pool for
parallel discovery across multiple files and simulation outputs.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from src.core.common.utils import sanitize_log_value
from src.core.models import ScanFileResult
from src.parsing.gem5.impl.pool.scan_work import ScanWork
from src.parsing.gem5.impl.scanning.scanner import Gem5StatsScanner

logger = logging.getLogger(__name__)


class Gem5ScanWork(ScanWork):
    """
    Worker for scanning a single stats file for available variables.
    Executed in parallel.
    """

    def __init__(self, file_path: str) -> None:
        super().__init__()
        self.file_path = str(file_path)

    def __call__(self) -> ScanFileResult:
        """
        Execute scanning using the Gem5StatsScanner.

        Returns a ``ScanFileResult`` carrying the discovered variables on
        success, or the error message on a fatal scan failure (Perl crash,
        timeout, corrupt JSON, missing file) — never a silent empty list, so
        aggregation can tell "scanned: empty" apart from "scan failed".
        """
        try:
            scanner = Gem5StatsScanner.get_instance()
            variables = scanner.scan_file(Path(self.file_path))
            return ScanFileResult(file_path=self.file_path, variables=variables)
        except (OSError, RuntimeError) as e:
            logger.warning(
                "SCANNER: Failed to scan %s: %s",
                sanitize_log_value(self.file_path),
                sanitize_log_value(e),
            )
            return ScanFileResult(file_path=self.file_path, error=sanitize_log_value(e))

    def __str__(self) -> str:
        return f"Gem5ScanWork({os.path.basename(self.file_path)})"
