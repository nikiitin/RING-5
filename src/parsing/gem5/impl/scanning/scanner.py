"""
Gem5 Stats Scanner Wrapper.

This module provides a secure Python interface to the Perl-based stats scanner.
It handles script execution, path validation, and result parsing following
the Fail-Fast principle.
"""

from __future__ import annotations

import json
import logging
import math
import os
import shutil
import subprocess
from pathlib import Path

from src.core.common.security_limits import MAX_SCAN_FILE_BYTES, MAX_SCAN_LINE_COUNT
from src.core.common.safe_regex import MAX_INPUT_LENGTH
from src.core.common.utils import sanitize_log_value
from src.core.models import ScannedVariable
from src.parsing.gem5.models import Gem5ScannedVariable
from src.parsing.gem5.types.type_mapper import TypeMapper

logger = logging.getLogger(__name__)


class Gem5StatsScanner:
    """
    Interface to the underlying Perl statistics scanner.

    Uses a singleton-like behavior via get_instance to manage Perl environment
    checks. Ensures that all scanning operations are deterministic and error-aware.
    """

    _instance: Gem5StatsScanner | None = None

    def __init__(self) -> None:
        """
        Initialize the scanner and verify environment dependencies.

        Raises:
            RuntimeError: If Perl is not found in the system PATH.
            FileNotFoundError: If the internal Perl scanner script is missing.
        """
        self._perl_exe = shutil.which("perl")
        if not self._perl_exe:
            raise RuntimeError("Perl executable not found in PATH")

        # Resolve script path relative to this file
        # gem5/impl/scanning/scanner.py -> gem5/perl/statsScanner.pl
        current_dir = Path(__file__).parent  # gem5/impl/scanning/
        gem5_dir = current_dir.parent.parent  # gem5/
        self._script_path = (gem5_dir / "perl" / "statsScanner.pl").resolve()

        if not self._script_path.exists():
            raise FileNotFoundError(f"Scanner backend script missing at {self._script_path}")

    @classmethod
    def get_instance(cls) -> Gem5StatsScanner:
        """
        Get the singleton scanner instance.

        Returns:
            The initialized Gem5StatsScanner.
        """
        if cls._instance is None:
            cls._instance = Gem5StatsScanner()
        return cls._instance

    def scan_file(
        self, file_path: Path, config_vars: list[str] | None = None
    ) -> list[ScannedVariable]:
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
        # [impl->req~ring5.ingestion.variable-scan~1]
        display_path = sanitize_log_value(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"SCANNER: File not found: {display_path}")
        file_size = file_path.stat().st_size
        if file_size > MAX_SCAN_FILE_BYTES:
            raise RuntimeError(
                f"Scanner input exceeds the {MAX_SCAN_FILE_BYTES // (1024 * 1024)} MiB limit: "
                f"{display_path}"
            )

        cmd = [str(self._perl_exe), str(self._script_path), str(file_path)]
        if config_vars:
            cmd.append(",".join(str(v) for v in config_vars))

        result: subprocess.CompletedProcess[str] | None = None
        try:
            # Command constructed from validated paths, shell=False enforced for safety
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                shell=False,
                timeout=15,
                env={**os.environ, "RING5_MAX_SCAN_LINES": str(MAX_SCAN_LINE_COUNT)},
            )

            if not result.stdout.strip():
                return []

            results = json.loads(result.stdout)
            if not isinstance(results, list):
                raise RuntimeError("Perl scanner produced a non-list JSON result.")

            variables: list[ScannedVariable] = []
            for index, item in enumerate(results):
                if not isinstance(item, dict):
                    raise RuntimeError(f"Perl scanner result {index} is not a variable object.")
                try:
                    name = item.get("name")
                    type_name = item.get("type")
                    entries = item.get("entries", [])
                    pattern_indices = item.get("pattern_indices", [])
                    if not isinstance(name, str) or not name:
                        raise ValueError("name must be a non-empty string")
                    if len(name) > MAX_INPUT_LENGTH:
                        raise ValueError("name exceeds the scanner string limit")
                    if type_name not in {
                        "configuration",
                        "distribution",
                        "histogram",
                        "scalar",
                        "vector",
                    }:
                        raise ValueError("type is not supported")
                    if not isinstance(entries, list) or any(
                        not isinstance(entry, str) or len(entry) > MAX_INPUT_LENGTH
                        for entry in entries
                    ):
                        raise ValueError("entries must be a list of bounded strings")
                    if not isinstance(pattern_indices, list) or any(
                        not isinstance(pattern_id, str) or len(pattern_id) > MAX_INPUT_LENGTH
                        for pattern_id in pattern_indices
                    ):
                        raise ValueError("pattern_indices must be a list of bounded strings")
                    for range_name in ("minimum", "maximum"):
                        range_value = item.get(range_name)
                        if range_value is not None and (
                            isinstance(range_value, bool)
                            or not isinstance(range_value, (int, float))
                            or not math.isfinite(range_value)
                        ):
                            raise ValueError(f"{range_name} must be a finite number")
                    mapped = TypeMapper.map_scan_result(item)
                    variables.append(Gem5ScannedVariable.from_dict(mapped))
                except (KeyError, TypeError, ValueError) as exc:
                    raise RuntimeError(
                        f"Perl scanner result {index} has an invalid variable schema."
                    ) from exc
            return variables

        except subprocess.TimeoutExpired as e:
            logger.error("SCANNER: Timeout scanning %s", display_path)
            raise RuntimeError(f"Scanner timed out on {display_path}") from e
        except subprocess.CalledProcessError as e:
            stderr = sanitize_log_value(str(e.stderr or "")[:1000])
            logger.error("SCANNER: Perl script failed: %s", stderr)
            raise RuntimeError(f"Perl scanner failed for {display_path}: {stderr}") from e
        except json.JSONDecodeError as e:
            raw_output = result.stdout[:200] if result is not None else "<no output>"
            logger.error(
                "SCANNER: Invalid JSON output from script: %s",
                sanitize_log_value(raw_output),
            )
            raise RuntimeError("Perl scanner produced corrupt JSON output.") from e
