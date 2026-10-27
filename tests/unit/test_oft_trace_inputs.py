"""Native OFT receives exact current source argv through one canonical wrapper."""

from pathlib import Path
import re
import subprocess

import pytest

from scripts import trace_oft_inventory


@pytest.mark.parametrize("mode", ["approved", "all", "html"])
def test_native_modes_pass_current_paths_as_single_argv_and_preserve_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    """Spaces and metacharacters remain literal file arguments, without a shell."""
    root = tmp_path / "source tree"
    source = root / "src" / "module ; literal.py"
    source.parent.mkdir(parents=True)
    source.write_text("")
    diagnostics = root / "tests" / "visual" / "artifacts"
    diagnostics.mkdir(parents=True)
    (diagnostics / "old.py").write_text("invalid snapshot!")
    (diagnostics / "trace.zip").write_bytes(b"not a source input")
    monkeypatch.setattr(trace_oft_inventory, "ROOT", root)
    calls: list[tuple[list[str], Path, bool]] = []

    def run(command: list[str], *, cwd: Path, check: bool) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd, check))
        return subprocess.CompletedProcess(command, 7)

    monkeypatch.setattr(trace_oft_inventory.subprocess, "run", run)
    jar = tmp_path / "native OFT.jar"
    output = tmp_path / "native report.html"
    arguments = ["--jar", str(jar), "--mode", mode]
    if mode == "html":
        arguments.extend(("--output-file", str(output)))

    assert trace_oft_inventory.main(arguments) == 7
    assert len(calls) == 1
    command, cwd, check = calls[0]
    assert command[:4] == ["java", "-jar", str(jar), "trace"]
    expected_flags = {
        "approved": ["-w", "approved", "--v", "summary"],
        "all": ["--v", "summary"],
        "html": [
            "--output-format",
            "html",
            "--report-verbosity",
            "all",
            "--details-section-display",
            "collapse",
            "--output-file",
            str(output),
        ],
    }
    assert command[4:] == expected_flags[mode] + [
        "spec/oft/generated/features.md",
        "spec/oft/generated/requirements.md",
        "src/module ; literal.py",
    ]
    assert cwd == root and check is False


@pytest.mark.parametrize("status, expected", [(0, 0), (-15, 143)])
def test_native_success_and_signal_status_are_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: int, expected: int
) -> None:
    monkeypatch.setattr(trace_oft_inventory, "ROOT", tmp_path)

    def run(command: list[str], *, cwd: Path, check: bool) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, status)

    monkeypatch.setattr(trace_oft_inventory.subprocess, "run", run)
    assert trace_oft_inventory.main(["--jar", "oft.jar", "--mode", "all"]) == expected


@pytest.mark.parametrize(
    "arguments",
    [["--mode", "html"], ["--mode", "all", "--output-file", "unused.html"]],
)
def test_invalid_native_output_modes_fail_before_java(
    arguments: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("Invalid arguments must not launch Java")

    monkeypatch.setattr(trace_oft_inventory.subprocess, "run", forbidden)
    with pytest.raises(SystemExit) as error:
        trace_oft_inventory.main(["--jar", "oft.jar", *arguments])
    assert error.value.code == 2


@pytest.mark.parametrize(
    "target, mode", [("oft-trace", "approved"), ("oft-trace-all", "all"), ("oft-report", "html")]
)
def test_make_native_targets_share_the_current_source_wrapper(target: str, mode: str) -> None:
    makefile = (Path(__file__).resolve().parents[2] / "Makefile").read_text()
    match = re.search(r"^" + re.escape(target) + r":[^\n]*\n(?:\t[^\n]*\n|\n)*", makefile, re.M)
    assert match is not None
    body = match.group()
    assert body.count("-m scripts.trace_oft_inventory") == 1
    assert f"--mode {mode}" in body
    assert "java -jar" not in body
    assert "OFT_SOURCES" not in makefile
