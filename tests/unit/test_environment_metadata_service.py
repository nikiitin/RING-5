"""Tests for privacy-conscious execution-environment provenance."""

from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace
from typing import Any

import pytest

from src.core.models import EnvironmentMetadata
from src.core.services.environment_metadata_service import (
    EnvironmentMetadataService,
    _capture_environment,
    _chrome_path,
    _run_version,
)


@pytest.fixture(autouse=True)
def _clear_environment_cache() -> Any:
    """Keep patched capture values local to each test."""
    _capture_environment.cache_clear()
    yield
    _capture_environment.cache_clear()


def _metadata(
    *,
    ring5_version: str = "1.0.0",
    dependencies: dict[str, str | None] | None = None,
    external_tools: dict[str, str | None] | None = None,
) -> EnvironmentMetadata:
    return EnvironmentMetadata(
        format_version=1,
        ring5_version=ring5_version,
        python_version="3.12.9",
        python_implementation="CPython",
        operating_system="Linux 6.8",
        architecture="x86_64",
        dependencies=dependencies or {"pandas": "3.0.3"},
        renderers={"matplotlib": "3.11.0", "plotly": "6.9.0"},
        external_tools=external_tools or {"chrome": None, "perl": "v5.40.0"},
    )


def test_capture_is_complete_stable_and_privacy_conscious(monkeypatch: pytest.MonkeyPatch) -> None:
    # [test->req~ring5.portfolio.environment-metadata~1]
    monkeypatch.setattr(
        "src.core.services.environment_metadata_service._package_version",
        lambda name: {"ring5": "1.2.3", "plotly": "6.9.0", "matplotlib": "3.11.0"}.get(name, "9.0"),
    )
    monkeypatch.setattr(
        "src.core.services.environment_metadata_service._external_tool_versions",
        lambda: {"chrome": "Chromium 130", "perl": "v5.40.0", "xelatex": None},
    )
    monkeypatch.setattr(
        "src.core.services.environment_metadata_service.platform.python_version",
        lambda: "3.12.9",
    )
    monkeypatch.setattr(
        "src.core.services.environment_metadata_service.platform.python_implementation",
        lambda: "CPython",
    )
    monkeypatch.setattr(
        "src.core.services.environment_metadata_service.platform.system", lambda: "Linux"
    )
    monkeypatch.setattr(
        "src.core.services.environment_metadata_service.platform.release", lambda: "6.8"
    )
    monkeypatch.setattr(
        "src.core.services.environment_metadata_service.platform.machine", lambda: "x86_64"
    )

    captured = EnvironmentMetadataService.capture(refresh=True)
    restored = EnvironmentMetadata.from_dict(captured.to_dict())

    assert restored == captured
    assert captured.ring5_version == "1.2.3"
    assert captured.dependencies["python-multipart"] == "9.0"
    assert captured.renderers == {"matplotlib": "3.11.0", "plotly": "6.9.0"}
    assert captured.external_tools["xelatex"] is None
    payload = json.dumps(captured.to_dict()).lower()
    assert "hostname" not in payload
    assert "username" not in payload
    assert "browser_path" not in payload


def test_compare_distinguishes_changes_unavailable_and_unrecorded() -> None:
    recorded = _metadata(dependencies={"numpy": "2.5.0"}, external_tools={"chrome": None})
    current = _metadata(
        ring5_version="1.1.0",
        dependencies={"numpy": "2.5.1", "scipy": "1.18.0"},
        external_tools={"chrome": None},
    )

    comparison = EnvironmentMetadataService.compare(recorded, current=current)
    by_component = {(item.section, item.component): item for item in comparison.differences}

    assert comparison.recorded_available is True
    assert comparison.exact_match is False
    assert comparison.changed_count == 2
    assert comparison.review_count == 3
    assert by_component[("Runtime", "RING-5")].status == "changed"
    assert by_component[("Dependency", "numpy")].status == "changed"
    assert by_component[("Dependency", "scipy")].status == "not-recorded"
    assert by_component[("External tool", "chrome")].status == "unavailable"

    legacy = EnvironmentMetadataService.compare(None, current=current)
    assert legacy.recorded_available is False
    assert legacy.exact_match is False
    assert {item.status for item in legacy.differences} == {"not-recorded"}


def test_external_tool_probes_are_bounded_and_failure_safe(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _run_version(None, ("--version",)) is None
    monkeypatch.setattr(
        "src.core.services.environment_metadata_service.subprocess.run",
        lambda *_args, **_kwargs: SimpleNamespace(
            stdout="\n  Chromium   130  \nignored", stderr=""
        ),
    )
    assert _run_version("/resolved/chrome", ("--version",)) == "Chromium 130"

    def time_out(*_args: Any, **_kwargs: Any) -> Any:
        raise subprocess.TimeoutExpired("tool", 2)

    monkeypatch.setattr("src.core.services.environment_metadata_service.subprocess.run", time_out)
    assert _run_version("/resolved/tool", ("--version",)) is None

    configured = tmp_path / "chrome"
    configured.touch()
    monkeypatch.setenv("BROWSER_PATH", str(configured))
    assert _chrome_path() == str(configured)

    monkeypatch.delenv("BROWSER_PATH")
    monkeypatch.setattr(
        "src.core.services.environment_metadata_service.shutil.which",
        lambda name: "/usr/bin/chromium" if name == "chromium" else None,
    )
    assert _chrome_path() == "/usr/bin/chromium"


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"format_version": 2},
        {
            "format_version": 1,
            "ring5_version": "1",
            "python_version": "3",
            "python_implementation": "CPython",
            "operating_system": "Linux",
            "architecture": "x86_64",
            "dependencies": [],
            "renderers": {},
            "external_tools": {},
        },
    ],
)
def test_untrusted_environment_payload_is_validated(payload: Any) -> None:
    with pytest.raises(ValueError, match="environment|Environment|Unsupported"):
        EnvironmentMetadataService.from_payload(payload)
