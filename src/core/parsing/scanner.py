"""
Gem5 Stats Scanner Wrapper.

This module provides a secure Python interface to the Perl-based stats scanner.
It handles script execution, path validation, and result parsing following
the Fail-Fast principle.
"""

import json
import logging
import shutil
import subprocess  # nosec B404 - Required for gem5 Perl parser execution
from pathlib import Path
from typing import List, Optional

from src.core.models import ScannedVariable
from src.core.parsing.gem5.types.type_mapper import TypeMapper

logger = logging.getLogger(__name__)


class Gem5StatsScanner:
    """
    Interface to the underlying Perl statistics scanner.

    Uses a singleton-like behavior via get_instance to manage Perl environment
    checks. Ensures that all scanning operations are deterministic and error-aware.
    """

    _instance: Optional["Gem5StatsScanner"] = None

    def __init__(self) -> None:
        """
        Initialize the scanner and verify environment dependencies.

        Raises:
            RuntimeError: If Perl is not found in the system PATH.
            FileNotFoundError: If the internal Perl scanner script is missing.
        """
        self._perl_exe = shutil.which("perl")
        if not self._perl_exe:
            raise RuntimeError("CRITICAL: Perl executable not found in PATH.")

        # Resolve script path relative to this file
        # src/scanning/scanner.py -> src.core.parsing/perl/statsScanner.pl
        current_dir = Path(__file__).parent  # src/core/parsing/
        self._script_path = (current_dir / "perl" / "statsScanner.pl").resolve()

        if not self._script_path.exists():
            raise FileNotFoundError(
                f"CRITICAL: Scanner backend script missing at {self._script_path}"
            )

    @classmethod
    def get_instance(cls) -> "Gem5StatsScanner":
        """
        Get the singleton scanner instance.

        Returns:
            The initialized Gem5StatsScanner.
        """
        if cls._instance is None:
            cls._instance = Gem5StatsScanner()
        return cls._instance

    def scan_file(
        self, file_path: Path, config_vars: Optional[List[str]] = None
    ) -> List[ScannedVariable]:
        """
        Scan a single stats file to discover variable schemas.

        Args:
            file_path: Absolute path to the gem5 stats.txt file.
            config_vars: Optional list of regex hints for variable detection.

        Returns:
            List of dictionaries, each defining a discovered variable and its type.

        Raises:
            FileNotFoundError: If the target stats file does not exist.
            RuntimeError: If the Perl scanner returns invalid output or crashes.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"SCANNER: File not found: {file_path}")

        cmd = [str(self._perl_exe), str(self._script_path), str(file_path)]
        if config_vars:
            cmd.append(",".join(str(v) for v in config_vars))

        try:
            # Command constructed from validated paths, shell=False enforced for safety
            result = subprocess.run(  # nosec B603 - Validated perl script path
                cmd, capture_output=True, text=True, check=True, shell=False, timeout=60
            )

            if not result.stdout.strip():
                return []

            results = json.loads(result.stdout)

            return [ScannedVariable.from_dict(TypeMapper.map_scan_result(r)) for r in results]

        except subprocess.TimeoutExpired as e:
            logger.error(f"SCANNER: Timeout scanning {file_path}")
            raise RuntimeError(f"Scanner timed out on {file_path}") from e
        except subprocess.CalledProcessError as e:
            logger.error(f"SCANNER: Perl script failed: {e.stderr}")
            raise RuntimeError(f"Perl scanner failed for {file_path}: {e.stderr}") from e
        except json.JSONDecodeError as e:
            logger.error(f"SCANNER: Invalid JSON output from script: {result.stdout[:200]}")
            raise RuntimeError("Perl scanner produced corrupt JSON output.") from e
