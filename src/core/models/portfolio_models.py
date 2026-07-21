"""
Portfolio data models.

Defines the PortfolioData TypedDict used for session serialization
and restoration across all layers, plus the RestoreReport returned by
``restore_session`` so callers can see what was (and wasn't) restored.
"""

from dataclasses import dataclass, field
from typing import Any, TypedDict

from src.core.models.data_models import ParseVariableConfig, ScannedVariableDict
from src.core.models.history_models import OperationRecord
from src.core.models.shaper_models import ShaperStepConfig


@dataclass(frozen=True)
class RestoreReport:
    # [impl->req~ring5.portfolio.partial-report~1]
    """Outcome of a portfolio restore.

    A restore is best-effort per item (a portfolio with one corrupt plot
    still restores everything else), so callers — especially scripts —
    need a structured account of what was skipped instead of log lines.

    Attributes:
        data_restored: Whether the session DataFrame was restored.
        data_error: Error message when the data CSV failed to load.
        plots_restored: Number of plots successfully rebuilt.
        plots_skipped: One human-readable reason per skipped plot.
        parse_variables_skipped: Count of malformed parse-variable entries
            dropped (portfolio JSON is untrusted input).
    """

    data_restored: bool = False
    data_error: str | None = None
    plots_restored: int = 0
    plots_skipped: list[str] = field(default_factory=list)
    parse_variables_skipped: int = 0

    @property
    def complete(self) -> bool:
        # [impl->req~ring5.portfolio.upgrade-protection~1]
        """True when nothing was skipped or lost."""
        return (
            self.data_error is None and not self.plots_skipped and self.parse_variables_skipped == 0
        )


class PortfolioData(TypedDict, total=False):
    """
    Type definition for portfolio restoration data.

    Attributes:
        schema_version: Integer migration version.
        version: Human-readable portfolio format version.
        timestamp: Save time in ISO 8601 form.
        parse_variables: List of parser variable configurations
        stats_path: Base path to simulator stats files
        stats_pattern: Pattern for stats file naming
        csv_path: Path to processed CSV data
        use_parser: Whether parser mode is enabled
        scanned_variables: List of variables discovered by scanner
        data_csv: CSV string representation of data
        data_semantics: Semantic labels and units retained with data
        environment_metadata: Save-time runtime and dependency versions
        integrity_manifest: Checksums and optional HMAC signature for saved content
        plots: List of plot configurations
        plot_counter: Current plot ID counter
        config: Application configuration dictionary
        manager_history: Rolling list of last 10 manager operations
        portfolio_history: Full list of operations performed in this portfolio
    """

    schema_version: int
    version: str
    timestamp: str
    parse_variables: list[ParseVariableConfig]
    stats_path: str
    stats_pattern: str
    csv_path: str
    use_parser: bool
    scanned_variables: list[ScannedVariableDict]
    data_csv: str
    data_semantics: dict[str, dict[str, str]]
    environment_metadata: dict[str, Any] | None
    integrity_manifest: dict[str, Any] | None
    plots: list[dict[str, Any]]
    plot_counter: int
    config: dict[str, Any]
    shapers: list[ShaperStepConfig]
    manager_history: list[OperationRecord]
    portfolio_history: list[OperationRecord]
