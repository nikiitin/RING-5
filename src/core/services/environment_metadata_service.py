"""Capture and compare the runtime needed to reproduce a saved analysis."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version as distribution_version
from pathlib import Path
from typing import Any

from src.core.models.environment_models import (
    EnvironmentComparison,
    EnvironmentDifference,
    EnvironmentMatchStatus,
    EnvironmentMetadata,
)

_RUNTIME_DEPENDENCIES = (
    "choreographer",
    "click",
    "gitpython",
    "kaleido",
    "matplotlib",
    "numpy",
    "openpyxl",
    "pandas",
    "pillow",
    "plotly",
    "regex",
    "scipy",
    "starlette",
    "streamlit",
    "tornado",
)
_RENDERERS = ("matplotlib", "plotly")


def _package_version(name: str) -> str | None:
    """Return an installed distribution version without importing it."""
    try:
        return distribution_version(name)
    except PackageNotFoundError:
        return None


def _first_line(value: str) -> str | None:
    """Return one bounded version line suitable for a JSON document."""
    for line in value.splitlines():
        normalized = " ".join(line.split())
        if normalized:
            return normalized[:500]
    return None


def _run_version(executable: str | None, arguments: Sequence[str]) -> str | None:
    """Run one resolved executable with a short, non-interactive timeout."""
    if executable is None:
        return None
    try:
        result = subprocess.run(
            [executable, *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return _first_line(result.stdout) or _first_line(result.stderr)


def _chrome_path() -> str | None:
    """Resolve a configured or PATH-visible Chrome-family executable."""
    configured = os.environ.get("BROWSER_PATH")
    if configured:
        candidate = Path(configured)
        if candidate.is_file():
            return str(candidate)
    for name in ("chrome", "chromium", "chromium-browser", "google-chrome"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _external_tool_versions() -> dict[str, str | None]:
    """Return version strings for every external tool RING-5 can use."""
    return {
        "chrome": _run_version(_chrome_path(), ("--version",)),
        "perl": _run_version(shutil.which("perl"), ("-e", "print $^V")),
        "xelatex": _run_version(shutil.which("xelatex"), ("--version",)),
    }


@lru_cache(maxsize=1)
def _capture_environment() -> EnvironmentMetadata:
    """Capture immutable process-level metadata once per Python process."""
    return EnvironmentMetadata(
        format_version=1,
        ring5_version=_package_version("ring5") or "source checkout",
        python_version=platform.python_version(),
        python_implementation=platform.python_implementation(),
        operating_system=f"{platform.system()} {platform.release()}".strip(),
        architecture=platform.machine() or "unknown",
        dependencies={name: _package_version(name) for name in _RUNTIME_DEPENDENCIES},
        renderers={name: _package_version(name) for name in _RENDERERS},
        external_tools=_external_tool_versions(),
    )


def _metadata_rows(metadata: EnvironmentMetadata) -> dict[tuple[str, str], str | None]:
    """Flatten metadata into stable comparison rows."""
    rows: dict[tuple[str, str], str | None] = {
        ("Runtime", "RING-5"): metadata.ring5_version,
        ("Runtime", "Python"): metadata.python_version,
        ("Runtime", "Python implementation"): metadata.python_implementation,
        ("Platform", "Operating system"): metadata.operating_system,
        ("Platform", "Architecture"): metadata.architecture,
    }
    rows.update((("Dependency", name), value) for name, value in metadata.dependencies.items())
    rows.update((("Renderer", name), value) for name, value in metadata.renderers.items())
    rows.update((("External tool", name), value) for name, value in metadata.external_tools.items())
    return rows


class EnvironmentMetadataService:
    """Capture, validate, and compare reproducibility metadata."""

    @staticmethod
    def capture(*, refresh: bool = False) -> EnvironmentMetadata:
        # [impl->req~ring5.portfolio.environment-metadata~1]
        """Capture the current RING-5 execution environment.

        Args:
            refresh: Discard the process cache before probing versions.

        Returns:
            Privacy-conscious version metadata for the current runtime.
        """
        if refresh:
            _capture_environment.cache_clear()
        return _capture_environment()

    @staticmethod
    def from_payload(value: object) -> EnvironmentMetadata | None:
        """Validate optional environment metadata from portfolio JSON.

        Args:
            value: Raw ``environment_metadata`` portfolio value.

        Returns:
            Validated metadata, or ``None`` for an older portfolio.

        Raises:
            ValueError: A present payload is malformed.
        """
        if value is None:
            return None
        if not isinstance(value, Mapping):
            raise ValueError("Portfolio environment metadata must be an object or null.")
        return EnvironmentMetadata.from_dict(value)

    @staticmethod
    def compare(
        recorded: EnvironmentMetadata | Mapping[str, Any] | None,
        *,
        current: EnvironmentMetadata | None = None,
    ) -> EnvironmentComparison:
        # [impl->req~ring5.portfolio.environment-metadata~1]
        """Compare recorded portfolio metadata with the current runtime.

        Args:
            recorded: Validated metadata, raw portfolio mapping, or ``None``.
            current: Optional deterministic current-runtime value for callers/tests.

        Returns:
            Stable component-level differences. This reports exact equality,
            not a claim that differing versions are necessarily incompatible.
        """
        saved = (
            EnvironmentMetadataService.from_payload(recorded)
            if not isinstance(recorded, EnvironmentMetadata)
            else recorded
        )
        live = current or EnvironmentMetadataService.capture()
        live_rows = _metadata_rows(live)
        saved_rows = _metadata_rows(saved) if saved is not None else {}
        differences: list[EnvironmentDifference] = []
        for section, component in sorted(set(live_rows) | set(saved_rows)):
            key = (section, component)
            recorded_value = saved_rows.get(key)
            current_value = live_rows.get(key)
            status: EnvironmentMatchStatus
            if key not in saved_rows:
                status = "not-recorded"
            elif recorded_value is None and current_value is None:
                status = "unavailable"
            elif recorded_value == current_value:
                status = "match"
            else:
                status = "changed"
            differences.append(
                EnvironmentDifference(
                    section=section,
                    component=component,
                    recorded=recorded_value,
                    current=current_value,
                    status=status,
                )
            )
        return EnvironmentComparison(saved, live, tuple(differences))
