from __future__ import annotations

import logging
import os
from typing import List

from src.parsers.models import ScannedVariable
from src.parsers.workers.scan_work import ScanWork

logger = logging.getLogger(__name__)


class Gem5ScanWork(ScanWork):
    """
    Worker for scanning a single stats file for available variables.
    Executed in parallel.
    """

    def __init__(self, file_path: str) -> None:
        super().__init__()
        self.file_path = str(file_path)

    def __call__(self) -> List[ScannedVariable]:
        """
        Execute scanning using the Gem5StatsScanner.
        Returns full list of variables with types and entries.
        """
        from pathlib import Path

        from src.parsers.scanner import Gem5StatsScanner

        try:
            scanner = Gem5StatsScanner.get_instance()
            return scanner.scan_file(Path(self.file_path))
        except Exception as e:
            logger.error(f"SCANNER: Failed to scan {self.file_path}: {e}")
            return []

    def __str__(self) -> str:
        return f"Gem5ScanWork({os.path.basename(self.file_path)})"
