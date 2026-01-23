import json
import os
import subprocess  # nosec
from typing import Any, Dict, List

from src.scanning.impl.multiprocessing.scanWork import ScanWork


class StatsScanWork(ScanWork):
    """
    Worker for scanning a single stats file for available variables.
    Executed in parallel.
    """

    def __init__(self, file_path: str, perl_exe: str, script_path: str) -> None:
        super().__init__()
        self.file_path = str(file_path)
        self.perl_exe = perl_exe
        self.script_path = str(script_path)

    def __call__(self) -> List[Dict[str, Any]]:
        """
        Executes the perl scanner script on the file.
        Returns a list of variable definitions found in this file.
        """
        try:
            cmd = [self.perl_exe, self.script_path, self.file_path]
            # Capture output
            result = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)  # nosec

            # Parse JSON result
            file_vars = json.loads(result)
            return file_vars

        except Exception:
            # If a file fails, we return empty list so it doesn't break everything
            # print(f"Error scanning file {self.file_path}: {e}")
            return []

    def __str__(self) -> str:
        return f"StatsScanWork({os.path.basename(self.file_path)})"
