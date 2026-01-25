"""
Gem5 Stats Scanner Wrapper.

This module provides a secure Python interface to the Perl-based stats scanner.
It handles script execution, path validation, and result parsing.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional


class Gem5StatsScanner:
    """
    Singleton scanner wrapper for gem5 statistics.
    Executes the underlying Perl script securely and returns structured data.
    """

    _instance: Optional["Gem5StatsScanner"] = None

    def __init__(self):
        self._perl_exe = shutil.which("perl")
        if not self._perl_exe:
            raise RuntimeError("Perl executable not found in PATH")

        # Resolve script path relative to this file
        # src/scanning/scanner.py -> src/scanning/perl/statsScanner.pl
        current_dir = Path(__file__).parent
        self._script_path = (current_dir / "perl" / "statsScanner.pl").resolve()

        if not self._script_path.exists():
            raise FileNotFoundError(f"Scanner script not found at {self._script_path}")

    @classmethod
    def get_instance(cls) -> "Gem5StatsScanner":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = Gem5StatsScanner()
        return cls._instance

    def scan_file(self, file_path: Path, config_vars: List[str] = None) -> List[Dict]:
        """
        Scan a single stats file for variables.

        Args:
            file_path: Path to the stats file.
            config_vars: Optional list of configuration variables to hint detection.

        Returns:
            List of variable definition dictionaries.
        """
        if not file_path.exists():
            return []

        # Securely construct command
        # Ensure all arguments are strings
        cmd = [str(self._perl_exe), str(self._script_path), str(file_path)]

        if config_vars:
            cmd.append(",".join(str(v) for v in config_vars))

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=False)
            results = json.loads(result.stdout)

            # Map types using TypeMapper
            from src.common.type_mapper import TypeMapper

            return [TypeMapper.map_scan_result(r) for r in results]
        except subprocess.CalledProcessError:
            # Script failed (e.g. file unreadable or parse error)
            return []
        except json.JSONDecodeError:
            # Output was not valid JSON
            return []
        except Exception:
            return []

    def scan_vector_entries(self, file_path: Path, vector_name: str) -> List[str]:
        """
        Scan a file specifically for entries of a given vector.

        Note: This reuses scan_file but processes the result.
        For extreme performance optimization on huge files, we could add a mode
        to the Perl script to only look for one variable, but full scan is usually fast.
        """
        all_vars = self.scan_file(file_path)
        for var in all_vars:
            if var["name"] == vector_name and var.get("type") == "vector":
                return var.get("entries", [])
        return []
