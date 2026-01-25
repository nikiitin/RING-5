import os
from typing import Any, Dict, List

from src.scanning.workers.scan_work import ScanWork


class Gem5ScanWork(ScanWork):
    """
    Worker for scanning a single stats file for available variables.
    Executed in parallel.
    """

    def __init__(self, file_path: str) -> None:
        super().__init__()
        self.file_path = str(file_path)

    def __call__(self) -> List[Dict[str, Any]]:
        """
        Execute scanning using the Gem5StatsScanner.
        Returns full list of variables with types and entries.
        """
        from pathlib import Path

        from src.scanning.scanner import Gem5StatsScanner

        try:
            scanner = Gem5StatsScanner.get_instance()
            return scanner.scan_file(Path(self.file_path))
        except Exception:
            return []

    def __str__(self) -> str:
        return f"Gem5ScanWork({os.path.basename(self.file_path)})"
