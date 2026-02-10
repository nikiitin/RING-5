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
from typing import List

from src.core.models import ScannedVariable
from src.core.parsing.gem5.impl.pool.scan_work import ScanWork
from src.core.parsing.gem5.impl.scanning.scanner import Gem5StatsScanner

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
        try:
            scanner = Gem5StatsScanner.get_instance()
            return scanner.scan_file(Path(self.file_path))
        except Exception as e:
            logger.error(f"SCANNER: Failed to scan {self.file_path}: {e}")
            return []

    def __str__(self) -> str:
        return f"Gem5ScanWork({os.path.basename(self.file_path)})"
