"""Public scheduled-report coverage across durable process-style ticks."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import ring5

pytestmark = pytest.mark.public_api


def _recipe(source: Path, *, export_path: Path | None = None) -> ring5.AnalysisRecipe:
    exports = (
        (ring5.RecipeExport("IPC", str(export_path), format="pdf"),)
        if export_path is not None
        else ()
    )
    return ring5.AnalysisRecipe(
        name="Nightly performance",
        source=ring5.RecipeSource("csv", str(source)),
        plots=(
            ring5.RecipePlot(
                name="IPC",
                plot_type="bar",
                config={"x": "benchmark", "y": "ipc"},
            ),
        ),
        exports=exports,
    )


def test_scheduled_ticks_generate_wait_and_skip_durably(tmp_path: Path) -> None:
    # [test->req~ring5.automation.scheduled-reporting~1]
    source = tmp_path / "results.csv"
    report = tmp_path / "reports" / "nightly.html"
    side_export = tmp_path / "should-not-exist.pdf"
    pd.DataFrame({"benchmark": ["a", "b"], "ipc": [1.0, 1.2]}).to_csv(source, index=False)
    recipe = _recipe(source, export_path=side_export)

    with ring5.Session() as session:
        generated = session.run_scheduled_report(
            recipe,
            str(report),
            stable_for_seconds=0,
        )

    assert isinstance(generated, ring5.ScheduledReportResult)
    assert generated.outcome == "generated"
    assert generated.generated is True
    assert generated.source_fingerprint and generated.source_fingerprint.startswith("sha256:")
    assert generated.configuration_fingerprint.startswith("sha256:")
    assert generated.source_files == (str(source.resolve()),)
    assert generated.report_path == str(report)
    assert Path(generated.state_path).name == "nightly.html.ring5-state.json"
    assert report.read_bytes().startswith(b"<!doctype html>")
    assert b"Nightly performance" in report.read_bytes()
    assert not side_export.exists(), "scheduled report ran the recipe's side export"

    original_report = report.read_bytes()
    with ring5.Session() as session:
        unchanged = session.run_scheduled_report(
            recipe,
            str(report),
            stable_for_seconds=0,
        )
    assert unchanged.outcome == "unchanged"
    assert unchanged.generated is False
    assert report.read_bytes() == original_report

    with ring5.Session() as session:
        retitled = session.run_scheduled_report(
            recipe,
            str(report),
            stable_for_seconds=0,
            title="Retitled performance",
        )
    assert retitled.outcome == "generated"
    assert retitled.source_fingerprint == generated.source_fingerprint
    assert retitled.configuration_fingerprint != generated.configuration_fingerprint
    assert b"Retitled performance" in report.read_bytes()
    original_report = report.read_bytes()

    pd.DataFrame({"benchmark": ["a", "b"], "ipc": [1.1, 1.3]}).to_csv(source, index=False)
    state = generated.state_path
    with ring5.Session() as session:
        waiting = session.run_scheduled_report(
            recipe,
            str(report),
            state_path=state,
            stable_for_seconds=60,
        )
    assert waiting.outcome == "waiting_for_stability"
    assert report.read_bytes() == original_report

    with ring5.Session() as session:
        refreshed = session.run_scheduled_report(
            recipe,
            str(report),
            state_path=state,
            stable_for_seconds=0,
            title="Updated nightly report",
        )
    assert refreshed.outcome == "generated"
    assert refreshed.source_fingerprint != generated.source_fingerprint
    assert b"Updated nightly report" in report.read_bytes()


def test_scheduled_report_errors_remain_typed_and_do_not_publish(tmp_path: Path) -> None:
    source = tmp_path / "results.csv"
    pd.DataFrame({"benchmark": ["a"], "ipc": [1.0]}).to_csv(source, index=False)

    empty_recipe = ring5.AnalysisRecipe(
        name="No figures",
        source=ring5.RecipeSource("csv", str(source)),
    )
    with ring5.Session() as session:
        with pytest.raises(ring5.RecipeError, match="at least one plot"):
            session.run_scheduled_report(
                empty_recipe,
                str(tmp_path / "empty.html"),
                stable_for_seconds=0,
            )

    invalid_state = tmp_path / "invalid-state.json"
    invalid_state.write_text("not json")
    with ring5.Session() as session:
        with pytest.raises(ring5.RecipeError, match="state is invalid"):
            session.run_scheduled_report(
                _recipe(source),
                str(tmp_path / "invalid-state.html"),
                state_path=str(invalid_state),
                stable_for_seconds=0,
            )

    second_source = tmp_path / "second.csv"
    pd.DataFrame({"benchmark": ["b"], "ipc": [2.0]}).to_csv(second_source, index=False)
    with ring5.Session() as session:
        with pytest.raises(ring5.ExportError, match="analysis report"):
            session.run_scheduled_report(
                _recipe(second_source),
                str(tmp_path / "invalid-format.out"),
                stable_for_seconds=0,
                format="docx",  # type: ignore[arg-type]
            )

    blocked = tmp_path / "blocked"
    blocked.write_text("file")
    third_source = tmp_path / "third.csv"
    pd.DataFrame({"benchmark": ["c"], "ipc": [3.0]}).to_csv(third_source, index=False)
    with ring5.Session() as session:
        with pytest.raises(ring5.ExportError, match="Could not write scheduled report report"):
            session.run_scheduled_report(
                _recipe(third_source),
                str(blocked / "report.html"),
                state_path=str(tmp_path / "third-state.json"),
                stable_for_seconds=0,
            )
