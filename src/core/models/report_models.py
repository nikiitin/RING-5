"""Immutable contracts for deterministic analysis reports."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.models.environment_models import EnvironmentMetadata
from src.core.models.visualization.dashboard_spec import DashboardSpec


def _validate_text(value: str, name: str, maximum: int, *, allow_empty: bool = False) -> None:
    """Validate a bounded report string."""
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ValueError(f"Report {name} must be text{' or empty' if allow_empty else ''}.")
    if len(value) > maximum:
        raise ValueError(f"Report {name} cannot exceed {maximum} characters.")


@dataclass(frozen=True)
class ReportNarrative:
    """One ordered heading and plain-text narrative block."""

    heading: str
    text: str

    def __post_init__(self) -> None:
        """Reject empty or unbounded narrative content."""
        _validate_text(self.heading, "narrative heading", 200)
        _validate_text(self.text, "narrative text", 20_000)


@dataclass(frozen=True)
class ReportTable:
    """A bounded, immutable table ready for HTML and PDF rendering."""

    title: str
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    total_rows: int

    def __post_init__(self) -> None:
        """Validate table shape and bounded display content."""
        _validate_text(self.title, "table title", 200)
        if not self.columns or len(self.columns) > 100:
            raise ValueError("Report tables need from 1 through 100 columns.")
        if len(self.rows) > 500:
            raise ValueError("Report tables cannot contain more than 500 displayed rows.")
        if isinstance(self.total_rows, bool) or self.total_rows < len(self.rows):
            raise ValueError("Report table total_rows cannot be smaller than displayed rows.")
        for column in self.columns:
            _validate_text(column, "table column", 200)
        for row in self.rows:
            if len(row) != len(self.columns):
                raise ValueError("Every report table row must align with its columns.")
            for value in row:
                _validate_text(value, "table cell", 1_000, allow_empty=True)

    @property
    def truncated(self) -> bool:
        """Whether the source table had more rows than this report displays."""
        return self.total_rows > len(self.rows)


@dataclass(frozen=True)
class ReportProvenance:
    """Data origin and transformation facts carried into a report."""

    source_kind: str
    source_location: str
    data_sha256: str
    row_count: int
    column_count: int
    columns: tuple[str, ...]
    parser_variables: tuple[str, ...] = ()
    operations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate provenance fields before they reach an output document."""
        _validate_text(self.source_kind, "source kind", 100)
        _validate_text(self.source_location, "source location", 2_000)
        if len(self.data_sha256) != 64 or any(
            c not in "0123456789abcdef" for c in self.data_sha256
        ):
            raise ValueError("Report data_sha256 must be a lowercase SHA-256 digest.")
        if self.row_count < 0 or self.column_count < 0:
            raise ValueError("Report provenance dimensions cannot be negative.")
        if self.column_count != len(self.columns):
            raise ValueError("Report provenance column_count must match columns.")
        if len(self.parser_variables) > 500 or len(self.operations) > 1_000:
            raise ValueError("Report provenance contains too many parser variables or operations.")


@dataclass(frozen=True)
class ReportFigure:
    """One individual plot or composed dashboard in a report."""

    plot_ids: tuple[int, ...]
    title: str
    caption: str = ""
    dashboard: DashboardSpec | None = None

    def __post_init__(self) -> None:
        """Require an unambiguous individual-plot or dashboard reference."""
        _validate_text(self.title, "figure title", 200)
        _validate_text(self.caption, "figure caption", 2_000, allow_empty=True)
        if not self.plot_ids or len(self.plot_ids) > 50:
            raise ValueError("A report figure needs from 1 through 50 plot IDs.")
        if any(isinstance(value, bool) or not isinstance(value, int) for value in self.plot_ids):
            raise ValueError("Report figure plot IDs must be integers.")
        if self.dashboard is None and len(self.plot_ids) != 1:
            raise ValueError("An individual report figure must reference exactly one plot.")
        if self.dashboard is not None and self.plot_ids != self.dashboard.plot_ids:
            raise ValueError("A report dashboard must use the same ordered plot IDs as its figure.")


@dataclass(frozen=True)
class AnalysisReport:
    # [impl->req~ring5.export.batch-reports~1]
    """Complete deterministic report specification.

    Reports keep already-formatted bounded tables, exact live plot references,
    data provenance, and save-time environment metadata. Renderers therefore
    do not consult mutable global state beyond resolving the selected plots.
    """

    title: str
    figures: tuple[ReportFigure, ...]
    tables: tuple[ReportTable, ...]
    narrative: tuple[ReportNarrative, ...]
    provenance: ReportProvenance
    environment: EnvironmentMetadata

    def __post_init__(self) -> None:
        """Validate report size and required figure content."""
        _validate_text(self.title, "title", 200)
        if not self.figures or len(self.figures) > 20:
            raise ValueError("A report needs from 1 through 20 selected figures.")
        if len(self.tables) > 20 or len(self.narrative) > 20:
            raise ValueError("A report supports at most 20 tables and 20 narrative sections.")
