"""
Gem5 Stats Scanner Wrapper.

This module provides a secure Python interface to the Perl-based stats scanner.
It handles script execution, path validation, and result parsing following
the Fail-Fast principle.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from typing import cast
from pathlib import Path

from src.core.common.security_limits import (
    MAX_SCAN_FILE_BYTES,
    MAX_SCAN_LINE_COUNT,
    MAX_PARSE_RESULT_BYTES,
)
from src.core.common.utils import sanitize_log_value
from src.core.common.parsed_output_codec import unique_json_object
from src.core.models.parsing_models import ScannedVariable, ScanFileResult
from src.core.models.data_models import ScannedVariableDict

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

    def scan_file(self, file_path: Path) -> ScanFileResult:
        """
        Scan a single stats file to discover variable schemas.

        Args:
            file_path: Absolute path to the gem5 stats.txt file.

        Returns:
            Current source catalog and any bounded source-local error.

        Raises:
            FileNotFoundError: If the target stats file does not exist.
            RuntimeError: If the Perl scanner returns invalid output or crashes.
        """
        # [impl->req~ring5.ingestion.variable-scan~2]
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

        result: subprocess.CompletedProcess[str] | None = None
        try:
            # Command constructed from validated paths, shell=False enforced for safety
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
                check=True,
                shell=False,
                timeout=15,
                env={
                    **os.environ,
                    "RING5_MAX_SCAN_LINES": str(MAX_SCAN_LINE_COUNT),
                    "RING5_MAX_SOURCE_BYTES": str(MAX_PARSE_RESULT_BYTES),
                },
            )

            if len(result.stdout.encode("utf-8")) > MAX_PARSE_RESULT_BYTES:
                raise RuntimeError("Perl scanner catalog exceeds its byte limit.")
            payload = json.loads(result.stdout, object_pairs_hook=unique_json_object)
            if type(payload) is not dict or set(payload) != {"variables", "error"}:
                raise RuntimeError("Perl scanner requires its current catalog outcome.")
            results, error = payload["variables"], payload["error"]
            if type(results) is not list or (
                error is not None and (type(error) is not str or len(error) > 1000)
            ):
                raise RuntimeError("Perl scanner catalog outcome is invalid.")
            variables: list[ScannedVariable] = []
            for index, item in enumerate(results):
                try:
                    variable = ScannedVariable.from_dict(cast(ScannedVariableDict, item))
                    if (
                        len(variable.instances) != 1
                        or variable.instances[0].source_name != variable.name
                        or variable.instances[0].indices
                    ):
                        raise ValueError("Raw scan metadata must identify one literal source.")
                    variables.append(variable)
                except (KeyError, TypeError, ValueError) as exc:
                    raise RuntimeError(
                        f"Perl scanner result {index} has an invalid variable schema."
                    ) from exc
            return ScanFileResult(str(file_path), variables, error)

        except subprocess.TimeoutExpired as e:
            logger.error("SCANNER: Timeout scanning %s", display_path)
            raise RuntimeError(f"Scanner timed out on {display_path}") from e
        except subprocess.CalledProcessError as e:
            stderr = sanitize_log_value(str(e.stderr or "")[:1000])
            logger.error("SCANNER: Perl script failed: %s", stderr)
            raise RuntimeError(f"Perl scanner failed for {display_path}: {stderr}") from e
        except (ValueError, RecursionError) as e:
            if type(e) not in (ValueError, json.JSONDecodeError, RecursionError):
                raise
            raw_output = result.stdout[:200] if result is not None else "<no output>"
            logger.error(
                "SCANNER: Invalid JSON output from script: %s",
                sanitize_log_value(raw_output),
            )
            raise RuntimeError("Perl scanner produced corrupt JSON output.") from e
