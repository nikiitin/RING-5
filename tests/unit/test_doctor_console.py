"""Public diagnostics remain printable on strict legacy console encodings."""

from __future__ import annotations

import io
from contextlib import redirect_stderr, redirect_stdout
from typing import cast

import pytest

import ring5
from ring5 import DependencyStatus, DoctorReport, cli
from scripts import verify_installation

pytestmark = pytest.mark.public_api


def _report(found: tuple[bool, bool, bool]) -> DoctorReport:
    statuses = [
        DependencyStatus(
            name=name,
            found=available,
            path=f"C:/tools/{name}.exe" if available else None,
            needed_for=feature,
            install_hint=f"Install {name}.",
        )
        for name, available, feature in zip(
            ("perl", "chrome", "xelatex"),
            found,
            ("stats parsing", "Plotly static exports", "LaTeX exports"),
        )
    ]
    return DoctorReport(*statuses)


def _stream(encoding: str) -> io.TextIOWrapper:
    return io.TextIOWrapper(io.BytesIO(), encoding=encoding, errors="strict", newline="\n")


def _text(stream: io.TextIOWrapper) -> str:
    stream.flush()
    return cast(io.BytesIO, stream.buffer).getvalue().decode(stream.encoding)


@pytest.mark.parametrize("encoding", ["ascii", "cp1252"])
@pytest.mark.parametrize("found", [(True, True, True), (False, False, False), (True, False, False)])
def test_public_report_prints_found_missing_and_hint_lines(
    encoding: str, found: tuple[bool, bool, bool]
) -> None:
    """Status decoration cannot prevent reports from reaching legacy output streams."""
    report = _report(found)
    output = _stream(encoding)
    print(report, file=output)
    text = _text(output)
    assert "RING-5 dependency check:" in text
    assert text.count("[OK]") == sum(found)
    assert text.count("[MISSING]") == len(found) - sum(found)
    assert text.count("hint:") == len(found) - sum(found)
    for status in (report.perl, report.chrome, report.xelatex):
        assert status.name in text
        assert (status.path or "not found") in text
        assert status.needed_for in text
        assert (status.install_hint in text) is (not status.found)
    assert report.essential_found is found[0]
    assert report.all_found is all(found)


@pytest.mark.parametrize("encoding", ["ascii", "cp1252"])
@pytest.mark.parametrize("perl_found", [True, False])
def test_public_doctor_cli_preserves_required_dependency_exit_status(
    monkeypatch: pytest.MonkeyPatch, encoding: str, perl_found: bool
) -> None:
    """The CLI reports missing optional tools without concealing missing Perl."""
    from ring5 import _doctor

    report = _report((perl_found, False, False))
    monkeypatch.setattr(_doctor, "doctor", lambda: report)
    output = _stream(encoding)
    with redirect_stdout(output):
        result = cli.main(["doctor"])
    assert result == (0 if perl_found else 1)
    text = _text(output)
    assert "Install chrome." in text
    assert "Install xelatex." in text
    assert ("Install perl." in text) is (not perl_found)


@pytest.mark.parametrize("encoding", ["ascii", "cp1252"])
def test_installation_verifier_reaches_real_csv_plot_and_svg_export(
    monkeypatch: pytest.MonkeyPatch, encoding: str
) -> None:
    """Missing optional tools do not block the installed-wheel headless workflow."""
    monkeypatch.setattr(ring5, "doctor", lambda: _report((False, False, False)))
    output = _stream(encoding)
    with redirect_stdout(output):
        result = verify_installation.main()
    assert result == 0
    text = _text(output)
    assert text.count("[MISSING]") == 3
    assert "Public CSV, plotting, and SVG export workflow passed." in text


@pytest.mark.parametrize("encoding", ["ascii", "cp1252"])
def test_installation_verifier_keeps_real_export_failures_visible(
    monkeypatch: pytest.MonkeyPatch, encoding: str
) -> None:
    """Portable diagnostics leave the verifier's actual failure contract intact."""
    monkeypatch.setattr(ring5, "doctor", lambda: _report((True, False, False)))

    def fail_export(*args: object, **kwargs: object) -> bytes:
        raise ring5.ExportError("export regression")

    monkeypatch.setattr(ring5.Session, "export_bytes", fail_export)
    output, errors = _stream(encoding), _stream(encoding)
    with redirect_stdout(output), redirect_stderr(errors):
        result = verify_installation.main()
    assert result == 1
    assert "Installation check failed: export regression" in _text(errors)
    assert "workflow passed" not in _text(output)


def test_report_keeps_dependency_details_and_unicode_paths_unchanged() -> None:
    """ASCII labels do not rewrite the actual dependency information."""
    dependency = DependencyStatus("perl", True, "C:/Users/Zoë/工具/perl.exe", "stats parsing", "")
    report = DoctorReport(dependency, dependency, dependency)
    assert dependency.path is not None
    assert dependency.path in str(report)
    assert report.perl.path == dependency.path
