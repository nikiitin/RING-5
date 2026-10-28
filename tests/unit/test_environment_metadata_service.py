"""Tests for privacy-conscious execution-environment provenance."""

from __future__ import annotations

import json
import subprocess
import sys
from types import SimpleNamespace
from typing import Any

import pytest

from src.core.models.environment_models import EnvironmentMetadata
from src.core.common.browser_selection import BrowserSelection
from src.core.services.environment_metadata_service import (
    EnvironmentMetadataService,
    _capture_environment,
    _external_tool_versions,
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
    assert {"streamlit", "starlette"} <= captured.dependencies.keys()
    assert not {"gitpython", "tornado"} & captured.dependencies.keys()
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

    assert comparison.recorded == recorded
    assert comparison.exact_match is False
    assert comparison.changed_count == 2
    assert comparison.review_count == 3
    assert by_component[("Runtime", "RING-5")].status == "changed"
    assert by_component[("Dependency", "numpy")].status == "changed"
    assert by_component[("Dependency", "scipy")].status == "not-recorded"
    assert by_component[("External tool", "chrome")].status == "unavailable"

    with pytest.raises(ValueError, match="must be an object"):
        EnvironmentMetadataService.from_payload(None)


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


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_real_non_utf8_version_output_is_unavailable(
    stream: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.core.services import environment_metadata_service as service

    run = subprocess.run
    program = f"import sys;sys.{stream}.buffer.write(bytes([255]))"
    commands: list[list[str]] = []

    def python_only(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert command == [sys.executable, "-c", program]
        commands.append(command)
        assert kwargs == {"check": False, "capture_output": True, "text": True, "timeout": 2}
        # Exercise a real decode failure independently of the host's default codec.
        return run(command, encoding="utf-8", **kwargs)

    monkeypatch.setattr(service.subprocess, "run", python_only)
    assert _run_version(sys.executable, ("-c", program)) is None
    assert commands == [[sys.executable, "-c", program]]


def test_metadata_probes_selected_executable_and_every_supported_compiler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.core.services import environment_metadata_service as service
    from src.core.models.visualization.export_options import TEX_SYSTEMS

    monkeypatch.setattr(service, "select_browser", lambda: BrowserSelection("chosen", "/chosen"))
    monkeypatch.setattr(service.shutil, "which", lambda name: f"/tools/{name}")
    calls: list[str | None] = []

    def version(path: str | None, arguments: Any) -> str:
        calls.append(path)
        return f"version:{path}"

    monkeypatch.setattr(service, "_run_version", version)
    versions = _external_tool_versions()
    assert calls == ["/chosen", "/tools/perl", *(f"/tools/{name}" for name in TEX_SYSTEMS)]
    assert versions["chrome"] == "version:/chosen"
    assert set(versions) == {"chrome", "perl", *TEX_SYSTEMS}
    for compiler in TEX_SYSTEMS:
        assert versions[compiler] == f"version:/tools/{compiler}"


def test_unavailable_browser_never_probes_the_selected_literal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.core.services import environment_metadata_service as service

    monkeypatch.setattr(service, "select_browser", lambda: BrowserSelection("invalid", None))
    monkeypatch.setattr(service.shutil, "which", lambda name: None)

    def no_process(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Unavailable tools must not run.")

    monkeypatch.setattr(service.subprocess, "run", no_process)
    assert set(_external_tool_versions().values()) == {None}


@pytest.mark.parametrize("compiler", ["xelatex", "pdflatex", "lualatex"])
def test_saved_environment_detects_each_compiler_version_change(compiler: str) -> None:
    recorded = _metadata(external_tools={compiler: "before"})
    current = _metadata(external_tools={compiler: "after"})
    comparison = EnvironmentMetadataService.compare(recorded, current=current)
    difference = next(item for item in comparison.differences if item.component == compiler)
    assert difference.status == "changed"


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
