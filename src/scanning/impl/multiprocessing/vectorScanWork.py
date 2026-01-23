import json
import os
import subprocess  # nosec
from typing import List

from src.scanning.impl.multiprocessing.scanWork import ScanWork


class VectorScanWork(ScanWork):
    """
    Worker for scanning a single stats file for entries of a specific vector.
    Executed in parallel.
    Includes Python-side optimization to avoid spawning Perl if variable is missing.
    """

    def __init__(self, file_path: str, vector_name: str, perl_exe: str, script_path: str) -> None:
        super().__init__()
        self.file_path = str(file_path)
        self.vector_name = vector_name
        self.perl_exe = perl_exe
        self.script_path = str(script_path)

    def __call__(self) -> List[str]:
        """
        Scans file for vector entries.
        Returns list of entry names found.
        """
        try:
            import re

            # Optimization: Fast pre-check using Python reads before spawning Perl process
            # Use regex search to handle patterns like 'system.ruby.l\d+_cntrl\d+'
            with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                try:
                    if not re.search(self.vector_name, content):
                        return []
                except re.error:
                    # If invalid regex, try literal search as fallback
                    if self.vector_name not in content:
                        return []

            # If found, use Perl script to parse structure accurately
            cmd = [self.perl_exe, self.script_path, self.file_path]
            result = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)  # nosec
            file_vars = json.loads(result)

            entries = []
            for var in file_vars:
                # Check for name match using regex or literal
                name_match = False
                try:
                    if re.fullmatch(self.vector_name, var["name"]):
                        name_match = True
                except re.error:
                    if var["name"] == self.vector_name:
                        name_match = True

                if name_match and "entries" in var:
                    entries.extend(var["entries"])

            return entries

        except Exception:
            return []

    def __str__(self) -> str:
        return f"VectorScanWork({os.path.basename(self.file_path)})"
