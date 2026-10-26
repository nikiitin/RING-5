"""Repository and user hints delegate to the installed-wheel Chrome CLI."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]  # The locked CI environment omits PyYAML stubs.

from ring5 import _doctor
from scripts.check_package_contents import RUNTIME_FILES

ROOT = Path(__file__).resolve().parents[2]


def test_packaging_gate_requires_the_installer_manifest() -> None:
    assert "ring5/resources/chrome-for-testing.json" in RUNTIME_FILES


def test_make_uses_the_packaged_cli_and_supports_interpreter_override() -> None:
    makefile = (ROOT / "Makefile").read_text()
    command = makefile.split("chrome-install:\n", 1)[1].split("\n\n", 1)[0]
    assert command == "\t$(PYTHON) -m ring5.cli install-chrome"


@pytest.mark.skipif(os.name == "nt", reason="The Linux export job uses a POSIX shell.")
def test_ci_captures_literal_installer_output_for_later_exports(tmp_path: Path) -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    steps = workflow["jobs"]["exports"]["steps"]
    step = next(step for step in steps if step["name"] == "Install Chrome for Kaleido")
    executable = "/task cache/Zoë/Google Chrome for Testing"
    fake_python = tmp_path / "python_venv/bin/python"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text(
        '#!/bin/sh\n[ "$*" = "-m ring5.cli install-chrome" ] || exit 42\n'
        f"printf '%s\\n' '{executable}'\n"
    )
    fake_python.chmod(0o755)
    env_file = tmp_path / "github-env"
    result = subprocess.run(
        ["/bin/sh", "-eu", "-c", step["run"]],
        cwd=tmp_path,
        env={**os.environ, "GITHUB_ENV": str(env_file)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert env_file.read_text() == f"BROWSER_PATH={executable}\n"
    assert next(i for i, item in enumerate(steps) if item is step) < next(
        i for i, item in enumerate(steps) if item["name"] == "Run serial export tests"
    )


def test_installation_hints_use_one_cli_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BROWSER_PATH", "")
    report = _doctor.doctor()
    assert "ring5 install-chrome" in report.chrome.install_hint
    assert "BROWSER_PATH" in report.chrome.install_hint
    for owner in (
        "ring5/_doctor.py",
        "ring5/_export.py",
        "src/web/rendering/figure_export.py",
        "src/web/pages/ui/plotting/download_section.py",
    ):
        source = (ROOT / owner).read_text()
        assert "ring5 install-chrome" in source
        assert "kaleido_get_chrome" not in source
