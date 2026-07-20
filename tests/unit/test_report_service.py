"""Tests for bounded report content and provenance."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from src.core.models import EnvironmentMetadata, ReportFigure
from src.core.services.report_service import ReportService


def _environment() -> EnvironmentMetadata:
    return EnvironmentMetadata(
        1,
        "1.0.0",
        "3.14.6",
        "CPython",
        "Linux 6.8",
        "x86_64",
        dependencies={"pandas": "3.0.3"},
        renderers={"matplotlib": "3.11.0"},
        external_tools={"chrome": None},
    )


def test_report_service_captures_stable_provenance_and_bounded_tables() -> None:
    # [test->req~ring5.export.batch-reports~1]
    data = pd.DataFrame(
        {
            "value": [1.23456789012345, float("nan"), 3.0],
            "time": [datetime(2026, 7, 20, 12), datetime(2026, 7, 21), datetime(2026, 7, 22)],
        }
    )
    provenance = ReportService.capture_provenance(
        data,
        use_parser=False,
        csv_path="results.csv",
        stats_path="",
        stats_pattern="stats.txt",
        parse_variables=[{"name": "ipc", "type": "scalar", "_id": "1"}],
        history=[
            {
                "source_columns": ["value"],
                "dest_columns": ["value"],
                "operation": "Normalize value",
                "timestamp": "2026-07-20T12:00:00",
            }
        ],
    )
    report = ReportService.create(
        "Performance review",
        [ReportFigure((1,), "IPC")],
        tables={"Measurements": data},
        narrative={"Finding": "IPC improved."},
        provenance=provenance,
        environment=_environment(),
        table_row_limit=2,
    )

    assert provenance.source_kind == "CSV"
    assert provenance.source_location == "results.csv"
    assert len(provenance.data_sha256) == 64
    assert provenance.parser_variables == ("ipc",)
    assert provenance.operations == ("Normalize value",)
    assert report.tables[0].rows == (
        ("1.23456789012", "2026-07-20T12:00:00"),
        ("", "2026-07-21T00:00:00"),
    )
    assert report.tables[0].truncated is True
    assert report.narrative[0].text == "IPC improved."


def test_simulator_and_in_memory_provenance_are_explicit() -> None:
    parsed = ReportService.capture_provenance(
        None,
        use_parser=True,
        csv_path=None,
        stats_path="/simulations/run-a",
        stats_pattern="stats*.txt",
        parse_variables=[],
        history=[],
    )
    memory = ReportService.capture_provenance(
        None,
        use_parser=False,
        csv_path=None,
        stats_path="",
        stats_pattern="",
        parse_variables=[],
        history=[],
    )

    assert parsed.source_kind == "Simulator statistics"
    assert "stats*.txt" in parsed.source_location
    assert memory.source_kind == "In-memory workspace"
    assert memory.row_count == 0


@pytest.mark.parametrize("limit", [0, 501, True])
def test_table_limits_are_typed_and_bounded(limit: object) -> None:
    with pytest.raises(ValueError, match="row_limit"):
        ReportService.table_from_frame(
            "Table", pd.DataFrame({"value": [1]}), row_limit=limit  # type: ignore[arg-type]
        )
