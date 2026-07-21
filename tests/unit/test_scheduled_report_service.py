"""Tests for durable stable-input scheduled report decisions."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from src.core.models import RecipeSource
from src.core.services.scheduled_report_service import (
    ScheduledReportError,
    ScheduledReportPublishError,
    ScheduledReportService,
)

_CONFIGURATION_FINGERPRINT = "sha256:" + "1" * 64


def _run(
    source: Path,
    report: Path,
    state: Path,
    *,
    stable_for: float,
    now: float,
    generate: object = lambda: b"report",
):
    return ScheduledReportService.run(
        recipe_name="Nightly",
        configuration_fingerprint=_CONFIGURATION_FINGERPRINT,
        resolve_source_files=lambda: [str(source)],
        report_path=str(report),
        state_path=str(state),
        stable_for_seconds=stable_for,
        generate=generate,  # type: ignore[arg-type]
        now=now,
    )


def test_stability_change_and_generated_state_survive_independent_ticks(tmp_path: Path) -> None:
    # [test->req~ring5.automation.scheduled-reporting~1]
    source = tmp_path / "results.csv"
    report = tmp_path / "reports" / "nightly.html"
    state = tmp_path / "state" / "nightly.json"
    source.write_text("value\n1\n")
    generated: list[bytes] = []

    def first_report() -> bytes:
        generated.append(b"first")
        return b"first report"

    observed = _run(source, report, state, stable_for=10, now=100, generate=first_report)
    waiting = _run(source, report, state, stable_for=10, now=105, generate=first_report)
    published = _run(source, report, state, stable_for=10, now=110, generate=first_report)
    unchanged = _run(
        source,
        report,
        state,
        stable_for=10,
        now=120,
        generate=lambda: pytest.fail("unchanged source regenerated"),
    )

    assert observed.outcome == waiting.outcome == "waiting_for_stability"
    assert published.outcome == "generated"
    assert published.generated is True
    assert unchanged.outcome == "unchanged"
    assert unchanged.generated is False
    assert generated == [b"first"]
    assert report.read_bytes() == b"first report"
    first_fingerprint = published.source_fingerprint
    saved = json.loads(state.read_text())
    assert saved["format"] == "ring5.scheduled-report-state"
    assert saved["schema_version"] == 1
    assert saved["generated_fingerprint"] == first_fingerprint

    source.write_text("value\n2\n")
    changed = _run(source, report, state, stable_for=10, now=121)
    clock_rollback = _run(source, report, state, stable_for=10, now=90)
    republished = _run(
        source,
        report,
        state,
        stable_for=10,
        now=100,
        generate=lambda: b"second report",
    )

    assert changed.outcome == clock_rollback.outcome == "waiting_for_stability"
    assert republished.outcome == "generated"
    assert republished.source_fingerprint != first_fingerprint
    assert report.read_bytes() == b"second report"


def test_change_during_generation_is_not_published(tmp_path: Path) -> None:
    source = tmp_path / "results.csv"
    report = tmp_path / "report.html"
    state = tmp_path / "state.json"
    source.write_text("value\n1\n")

    def changing_report() -> bytes:
        source.write_text("value\n2\n")
        return b"stale report"

    result = _run(source, report, state, stable_for=0, now=10, generate=changing_report)

    assert result.outcome == "waiting_for_stability"
    assert not report.exists()
    state_payload = json.loads(state.read_text())
    assert state_payload["observed_fingerprint"] == result.source_fingerprint
    assert state_payload["generated_fingerprint"] is None

    generated = _run(
        source,
        report,
        state,
        stable_for=0,
        now=11,
        generate=lambda: b"current report",
    )
    assert generated.outcome == "generated"
    assert report.read_bytes() == b"current report"


def test_file_set_changes_during_inspection_waits_without_running(tmp_path: Path) -> None:
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("one")
    second.write_text("two")
    calls = 0

    def changing_files() -> list[str]:
        nonlocal calls
        calls += 1
        return [str(first)] if calls == 1 else [str(first), str(second)]

    result = ScheduledReportService.run(
        recipe_name="Watch",
        configuration_fingerprint=_CONFIGURATION_FINGERPRINT,
        resolve_source_files=changing_files,
        report_path=str(tmp_path / "report.html"),
        state_path=str(tmp_path / "state.json"),
        stable_for_seconds=0,
        generate=lambda: pytest.fail("unstable file set generated a report"),
        now=1,
    )

    assert result.outcome == "waiting_for_stability"
    assert result.source_fingerprint is None
    assert result.source_files == (str(first.resolve()),)


def test_recipe_source_resolution_includes_config_aware_companions(tmp_path: Path) -> None:
    stats = tmp_path / "run" / "stats.txt"
    stats.parent.mkdir()
    stats.write_text("simTicks 1")

    def finder(root: str, pattern: str) -> list[str]:
        return [str(stats)]

    csv = ScheduledReportService.source_files(RecipeSource("csv", "results.csv"), finder)
    simple = ScheduledReportService.source_files(RecipeSource("parser", str(tmp_path)), finder)
    configured = ScheduledReportService.source_files(
        RecipeSource("parser", str(tmp_path), strategy="config_aware"),
        finder,
    )

    assert csv == ("results.csv",)
    assert simple == (str(stats),)
    assert configured == (str(stats), str(stats.parent / "config.ini"))
    with pytest.raises(ScheduledReportError, match="No files matching"):
        ScheduledReportService.source_files(
            RecipeSource("parser", str(tmp_path)),
            lambda root, pattern: [],
        )


def test_configuration_changes_and_missing_outputs_regenerate(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    report = tmp_path / "report.html"
    state = tmp_path / "state.json"
    source.write_text("value\n1\n")

    first = _run(source, report, state, stable_for=0, now=1)
    changed_configuration = ScheduledReportService.run(
        recipe_name="Nightly",
        configuration_fingerprint="sha256:" + "2" * 64,
        resolve_source_files=lambda: [str(source)],
        report_path=str(report),
        state_path=str(state),
        stable_for_seconds=0,
        generate=lambda: b"changed configuration",
        now=2,
    )
    report.unlink()
    missing_output = ScheduledReportService.run(
        recipe_name="Nightly",
        configuration_fingerprint="sha256:" + "2" * 64,
        resolve_source_files=lambda: [str(source)],
        report_path=str(report),
        state_path=str(state),
        stable_for_seconds=0,
        generate=lambda: b"restored output",
        now=3,
    )

    assert first.outcome == changed_configuration.outcome == missing_output.outcome == "generated"
    assert changed_configuration.configuration_fingerprint == "sha256:" + "2" * 64
    assert report.read_bytes() == b"restored output"


def test_report_configuration_fingerprint_covers_recipe_and_output_settings(tmp_path: Path) -> None:
    base = ScheduledReportService.report_configuration_fingerprint(
        b"recipe-a",
        report_path=str(tmp_path / "report.html"),
        title="Nightly",
        format="html",
    )
    same = ScheduledReportService.report_configuration_fingerprint(
        b"recipe-a",
        report_path=str(tmp_path / "report.html"),
        title="Nightly",
        format="html",
    )
    variants = {
        ScheduledReportService.report_configuration_fingerprint(
            recipe,
            report_path=str(tmp_path / path),
            title=title,
            format=format,
        )
        for recipe, path, title, format in (
            (b"recipe-b", "report.html", "Nightly", "html"),
            (b"recipe-a", "other.html", "Nightly", "html"),
            (b"recipe-a", "report.html", "Weekly", "html"),
            (b"recipe-a", "report.html", "Nightly", "pdf"),
        )
    }

    assert base == same
    assert base not in variants
    assert len(variants) == 4


@pytest.mark.parametrize("stable_for", [True, -1, float("nan"), 604801])
def test_invalid_stability_windows_are_rejected(tmp_path: Path, stable_for: object) -> None:
    source = tmp_path / "source"
    source.write_text("data")

    with pytest.raises(ScheduledReportError, match="stable_for_seconds"):
        _run(
            source,
            tmp_path / "report",
            tmp_path / "state",
            stable_for=stable_for,  # type: ignore[arg-type]
            now=0,
        )


def test_invalid_configuration_fingerprint_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("data")

    with pytest.raises(ScheduledReportError, match="configuration_fingerprint"):
        ScheduledReportService.run(
            recipe_name="Invalid",
            configuration_fingerprint="not-a-fingerprint",
            resolve_source_files=lambda: [str(source)],
            report_path=str(tmp_path / "report"),
            state_path=str(tmp_path / "state"),
            stable_for_seconds=0,
            generate=lambda: b"report",
            now=0,
        )


@pytest.mark.parametrize("now", [True, -1, float("inf")])
def test_invalid_timestamps_are_rejected(tmp_path: Path, now: object) -> None:
    source = tmp_path / "source"
    source.write_text("data")

    with pytest.raises(ScheduledReportError, match="timestamp"):
        _run(
            source,
            tmp_path / "report",
            tmp_path / "state",
            stable_for=0,
            now=now,  # type: ignore[arg-type]
        )


def test_source_and_destination_validation_is_non_destructive(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    source.write_text("original")
    other = tmp_path / "other"
    other.write_text("other")
    symlink = tmp_path / "source-link"
    symlink.symlink_to(source)

    invalid_resolvers = [
        lambda: [],
        lambda: [""],
        lambda: [str(tmp_path / "missing")],
        lambda: [str(tmp_path)],
        lambda: [str(symlink)],
        lambda: [str(source)] * 4097,
    ]
    for resolver in invalid_resolvers:
        with pytest.raises(ScheduledReportError):
            ScheduledReportService.run(
                recipe_name="Invalid",
                configuration_fingerprint=_CONFIGURATION_FINGERPRINT,
                resolve_source_files=resolver,
                report_path=str(tmp_path / "report"),
                state_path=str(tmp_path / "state"),
                stable_for_seconds=0,
                generate=lambda: b"report",
                now=0,
            )

    for report_path, state_path in ((source, other), (other, source), (other, other)):
        with pytest.raises(ScheduledReportError, match="paths must be different|replace source"):
            _run(source, report_path, state_path, stable_for=0, now=0)
    assert source.read_text() == "original"
    assert other.read_text() == "other"


@pytest.mark.parametrize(
    "state",
    [
        b"not json",
        b'{"format":"wrong","schema_version":1}',
        b'{"format":"ring5.scheduled-report-state","schema_version":2}',
        (
            b'{"format":"ring5.scheduled-report-state","schema_version":1,'
            b'"observed_fingerprint":"bad"}'
        ),
        (
            b'{"format":"ring5.scheduled-report-state","schema_version":1,'
            b'"observed_fingerprint":null,"generated_fingerprint":null,'
            b'"observed_at":-1,"generated_at":null}'
        ),
        b'{"format":"ring5.scheduled-report-state","schema_version":1,"observed_at":NaN}',
        b'{"format":"ring5.scheduled-report-state","schema_version":1}',
        (
            b'{"format":"ring5.scheduled-report-state","schema_version":1,'
            b'"observed_fingerprint":"sha256:'
            b'gggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggg",'
            b'"generated_fingerprint":null,"observed_at":1,"generated_at":null}'
        ),
        (
            b'{"format":"ring5.scheduled-report-state","schema_version":1,'
            b'"observed_fingerprint":null,"generated_fingerprint":null,'
            b'"observed_at":1,"generated_at":null}'
        ),
    ],
)
def test_invalid_durable_state_is_never_silently_replaced(tmp_path: Path, state: bytes) -> None:
    source = tmp_path / "source"
    source.write_text("data")
    state_path = tmp_path / "state.json"
    state_path.write_bytes(state)

    with pytest.raises(ScheduledReportError, match="state"):
        _run(source, tmp_path / "report", state_path, stable_for=0, now=0)
    assert state_path.read_bytes() == state


def test_oversized_state_and_publish_failures_are_explicit(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("data")
    state = tmp_path / "state"
    state.write_bytes(b"x" * (64 * 1024 + 1))
    with pytest.raises(ScheduledReportError, match="64 KiB"):
        _run(source, tmp_path / "report", state, stable_for=0, now=0)

    blocked = tmp_path / "blocked"
    blocked.write_text("file")
    with pytest.raises(ScheduledReportPublishError, match="Could not write"):
        _run(
            source,
            blocked / "report",
            tmp_path / "valid-state",
            stable_for=0,
            now=0,
        )
    with pytest.raises(ScheduledReportPublishError, match="no bytes"):
        _run(
            source,
            tmp_path / "report",
            tmp_path / "new-state",
            stable_for=0,
            now=0,
            generate=lambda: b"",
        )


def test_source_change_during_read_is_treated_as_unstable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    source.write_text("data")
    original_stat = Path.stat
    calls = 0

    def changing_stat(path: Path, *args: object, **kwargs: object):
        nonlocal calls
        result = original_stat(path, *args, **kwargs)
        if path == source and calls == 0:
            os.utime(source, ns=(result.st_atime_ns, result.st_mtime_ns + 1))
        if path == source:
            calls += 1
        return result

    monkeypatch.setattr(Path, "stat", changing_stat)
    result = _run(
        source,
        tmp_path / "report",
        tmp_path / "state",
        stable_for=0,
        now=0,
    )

    assert result.outcome == "waiting_for_stability"
    assert not (tmp_path / "report").exists()
