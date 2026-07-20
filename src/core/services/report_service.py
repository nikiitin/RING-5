"""Build bounded report content and reproducibility provenance."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any, cast

import pandas as pd

from src.core.models import EnvironmentMetadata
from src.core.models.data_models import ParseVariableConfig
from src.core.models.history_models import OperationRecord
from src.core.models.report_models import (
    AnalysisReport,
    ReportFigure,
    ReportNarrative,
    ReportProvenance,
    ReportTable,
)


def _cell_text(value: object) -> str:
    """Format one table cell deterministically without executable markup."""
    try:
        if bool(pd.isna(cast(Any, value))):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, float):
        return format(value, ".12g")
    return str(value)


class ReportService:
    """Create renderer-independent analysis report specifications."""

    @staticmethod
    def table_from_frame(title: str, data: pd.DataFrame, *, row_limit: int = 100) -> ReportTable:
        """Convert a DataFrame into a bounded immutable report table.

        Args:
            title: Human-readable table title.
            data: Source table; it is never mutated.
            row_limit: Maximum displayed rows, from 1 through 500.

        Returns:
            A report table that records whether rows were omitted.

        Raises:
            ValueError: The limit or table dimensions are unsupported.
        """
        if (
            isinstance(row_limit, bool)
            or not isinstance(row_limit, int)
            or not 1 <= row_limit <= 500
        ):
            raise ValueError("Report table row_limit must be from 1 through 500.")
        if len(data.columns) < 1 or len(data.columns) > 100:
            raise ValueError("Report tables need from 1 through 100 columns.")
        displayed = data.iloc[:row_limit]
        return ReportTable(
            title=title,
            columns=tuple(str(column) for column in data.columns),
            rows=tuple(
                tuple(_cell_text(value) for value in row)
                for row in displayed.itertuples(index=False, name=None)
            ),
            total_rows=len(data),
        )

    @staticmethod
    def capture_provenance(
        data: pd.DataFrame | None,
        *,
        use_parser: bool,
        csv_path: str | None,
        stats_path: str,
        stats_pattern: str,
        parse_variables: Sequence[ParseVariableConfig],
        history: Sequence[OperationRecord],
    ) -> ReportProvenance:
        # [impl->req~ring5.export.batch-reports~1]
        """Capture stable data origin, dimensions, digest, and operations.

        Args:
            data: Current workspace data, or ``None``.
            use_parser: Whether the active source is the simulator parser.
            csv_path: Original CSV path when loaded from a table.
            stats_path: Simulator-results root when parsed.
            stats_pattern: Simulator statistics file pattern.
            parse_variables: Configured parser variables.
            history: Ordered workspace operation history.

        Returns:
            Deterministic provenance suitable for both report formats.
        """
        if use_parser and stats_path:
            source_kind = "Simulator statistics"
            source_location = f"{stats_path} · pattern: {stats_pattern or 'stats.txt'}"
        elif csv_path:
            source_kind = "CSV"
            source_location = str(csv_path)
        else:
            source_kind = "In-memory workspace"
            source_location = "No file-backed source was recorded"

        if data is None:
            encoded = b""
            rows = 0
            columns: tuple[str, ...] = ()
        else:
            encoded = data.to_csv(index=False, lineterminator="\n").encode("utf-8")
            rows = len(data)
            columns = tuple(str(column) for column in data.columns)

        variables = tuple(
            str(variable.get("name", "")).strip()
            for variable in parse_variables
            if str(variable.get("name", "")).strip()
        )
        operations = tuple(
            str(record.get("operation", "")).strip()
            for record in history
            if str(record.get("operation", "")).strip()
        )
        return ReportProvenance(
            source_kind=source_kind,
            source_location=source_location,
            data_sha256=hashlib.sha256(encoded).hexdigest(),
            row_count=rows,
            column_count=len(columns),
            columns=columns,
            parser_variables=variables,
            operations=operations,
        )

    @staticmethod
    def create(
        title: str,
        figures: Sequence[ReportFigure],
        *,
        tables: Mapping[str, pd.DataFrame] | None,
        narrative: Mapping[str, str] | None,
        provenance: ReportProvenance,
        environment: EnvironmentMetadata,
        table_row_limit: int = 100,
    ) -> AnalysisReport:
        """Create a complete immutable report specification.

        Args:
            title: Report title.
            figures: Ordered individual or dashboard figure references.
            tables: Optional ordered title-to-DataFrame mapping.
            narrative: Optional ordered heading-to-plain-text mapping.
            provenance: Captured data provenance.
            environment: Captured runtime metadata.
            table_row_limit: Display limit applied independently to every table.

        Returns:
            Validated analysis report.
        """
        report_tables = tuple(
            ReportService.table_from_frame(name, frame, row_limit=table_row_limit)
            for name, frame in (tables or {}).items()
        )
        narrative_sections = tuple(
            ReportNarrative(heading, text) for heading, text in (narrative or {}).items()
        )
        return AnalysisReport(
            title=title,
            figures=tuple(figures),
            tables=report_tables,
            narrative=narrative_sections,
            provenance=provenance,
            environment=environment,
        )
