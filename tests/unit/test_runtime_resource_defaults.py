"""Regression tests for resource-safe runtime defaults."""

from __future__ import annotations

import os
import subprocess
import tomllib
from pathlib import Path

import pytest

from src.core.common.runtime_limits import (
    NATIVE_THREAD_ENV_VARS,
    configure_native_thread_limits,
)
from src.parsing.framework.work_pool import DEFAULT_WORKERS, _default_workers
from src.parsing.gem5.impl.strategies.perl_worker_pool import (
    DEFAULT_PERL_WORKERS,
    _default_pool_size,
)


def test_streamlit_uses_polling_file_watcher() -> None:
    """Keep ``make run`` away from watchdog's thread-per-directory mode."""
    repository_root = Path(__file__).resolve().parents[2]
    config_path = repository_root / ".streamlit" / "config.toml"
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))

    assert config["server"]["fileWatcherType"] == "poll"


def test_security_audit_resolves_project_dependencies() -> None:
    """Audit declared dependencies instead of unrelated host-site packages."""
    repository_root = Path(__file__).resolve().parents[2]
    makefile = (repository_root / "Makefile").read_text(encoding="utf-8")

    assert "pip-audit --strict --progress-spinner off ." in makefile


def test_default_browser_gate_is_serial() -> None:
    """Keep the standard E2E target from multiplying server and browser processes."""
    repository_root = Path(__file__).resolve().parents[2]
    makefile = (repository_root / "Makefile").read_text(encoding="utf-8")
    target = makefile.split("test-e2e:", maxsplit=1)[1].split("test-visual:", maxsplit=1)[0]

    assert "-n 0" in target
    assert "-n 2" not in target


def test_make_virtual_environment_override_accepts_absolute_paths() -> None:
    """Keep Make targets usable with an externally managed virtual environment."""
    repository_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            "make",
            "--no-print-directory",
            "--just-print",
            "run",
            "VENV_NAME=/tmp/ring5-review-env",
        ],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "/tmp/ring5-review-env/bin/streamlit run app.py"


def test_native_thread_defaults_preserve_explicit_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Apply two-thread defaults while leaving deployment choices authoritative."""
    for variable in NATIVE_THREAD_ENV_VARS:
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("OMP_NUM_THREADS", "1")

    configure_native_thread_limits()

    assert {variable: os.environ[variable] for variable in NATIVE_THREAD_ENV_VARS} == {
        variable: ("1" if variable == "OMP_NUM_THREADS" else "2")
        for variable in NATIVE_THREAD_ENV_VARS
    }


def test_parser_worker_defaults_and_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep both parser concurrency layers at two unless explicitly overridden."""
    monkeypatch.delenv("RING5_WORK_POOL_SIZE", raising=False)
    monkeypatch.delenv("RING5_PERL_POOL_SIZE", raising=False)
    assert _default_workers() == DEFAULT_WORKERS == 2
    assert _default_pool_size() == DEFAULT_PERL_WORKERS == 2

    monkeypatch.setenv("RING5_WORK_POOL_SIZE", "1")
    monkeypatch.setenv("RING5_PERL_POOL_SIZE", "3")
    assert _default_workers() == 1
    assert _default_pool_size() == 3


@pytest.mark.parametrize("value", ["", "invalid", "0", "-1"])
def test_invalid_work_pool_overrides_are_reported(
    value: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Reject invalid worker limits visibly and retain the safe default."""
    monkeypatch.setenv("RING5_WORK_POOL_SIZE", value)

    assert _default_workers() == DEFAULT_WORKERS
    assert "RING5_WORK_POOL_SIZE" in caplog.text


@pytest.mark.parametrize("value", ["", "invalid", "0", "-1"])
def test_invalid_perl_pool_overrides_are_reported(
    value: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Reject invalid Perl process limits visibly and retain the safe default."""
    monkeypatch.setenv("RING5_PERL_POOL_SIZE", value)

    assert _default_pool_size() == DEFAULT_PERL_WORKERS
    assert "RING5_PERL_POOL_SIZE" in caplog.text
