"""Immutable request facts associated explicitly with loaded workspace data."""

from dataclasses import dataclass

from src.core.common.safe_regex import MAX_INPUT_LENGTH
from src.core.common.security_limits import MAX_PARSE_RESULT_BYTES, MAX_PIPELINE_CONFIG_BYTES
from src.core.models.import_models import ImportOptions


@dataclass(frozen=True, slots=True)
class ParserSourceContext:
    """Actual resolved parser request, independent of mutable editor settings.

    An undeclared injected backend has no simulator identifier. A None scan_limit
    records a resolved submission that performed no discovery. JSON strings own
    variable and scanner metadata without exposing nested mutable dictionaries.

    Attributes:
        stats_path: Actual submitted simulator-results root.
        stats_pattern: Actual statistics filename pattern.
        strategy_type: Exact backend strategy identifier.
        variables_json: Current runnable StatConfig payload array as owned JSON.
        scanned_variables_json: Current resolved scanner metadata array as owned JSON.
        simulator: Declared backend identifier, or None for undeclared injection.
        parser_contract_version: Shared current parser semantic contract identifier.
        scan_limit: Actual discovery limit, or None when no discovery occurred.
        strict: Whether missing numeric variables reject public finalization.
    """

    stats_path: str
    stats_pattern: str
    strategy_type: str
    variables_json: str
    scanned_variables_json: str
    simulator: str | None
    parser_contract_version: str
    scan_limit: int | None
    strict: bool

    def __post_init__(self) -> None:
        for value in (
            self.stats_path,
            self.stats_pattern,
            self.strategy_type,
            self.parser_contract_version,
        ):
            if type(value) is not str or not value or len(value) > MAX_INPUT_LENGTH:
                raise ValueError("Parser source context requires bounded non-empty text.")
        if self.simulator is not None and (
            type(self.simulator) is not str or not self.simulator or len(self.simulator) > 80
        ):
            raise ValueError("Declared parser simulator must be bounded non-empty text.")
        if self.scan_limit is not None and (
            type(self.scan_limit) is not int or not 0 <= self.scan_limit <= 10_000
        ):
            raise ValueError(
                "Parser discovery limit must be None or an integer from 0 through 10000."
            )
        if type(self.strict) is not bool:
            raise TypeError("Parser strict policy must be a boolean.")
        for value in (self.variables_json, self.scanned_variables_json):
            if type(value) is not str or not value or len(value) > MAX_PARSE_RESULT_BYTES:
                raise ValueError("Parser source JSON must be bounded non-empty text.")


@dataclass(frozen=True, slots=True)
class InferredCsvPolicy:
    """Genuine CSV inference followed by exact configuration-column casts.

    Attributes:
        configuration_columns: Immutable unique names requested at ingestion.
            Missing columns are ignored by the existing CSV loader. Serialization
            budgets apply when persisting this policy, independently of loading.
    """

    configuration_columns: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.configuration_columns) is not tuple:
            raise TypeError("CSV configuration columns require an immutable tuple.")
        if any(
            type(name) is not str or not name or len(name) > MAX_INPUT_LENGTH
            for name in self.configuration_columns
        ):
            raise ValueError("CSV configuration columns require bounded non-empty names.")
        if len(set(self.configuration_columns)) != len(self.configuration_columns):
            raise ValueError("CSV configuration columns must be unique.")


@dataclass(frozen=True, slots=True)
class ReviewedCsvPolicy:
    """Requested reviewed-import options with the accepted-row exclusion policy."""

    options: ImportOptions

    def __post_init__(self) -> None:
        if type(self.options) is not ImportOptions:
            raise TypeError("Reviewed CSV policy requires immutable ImportOptions.")


CsvPolicy = InferredCsvPolicy | ReviewedCsvPolicy


@dataclass(frozen=True, slots=True)
class CsvSourceContext:
    """Actual CSV path and the explicit request policy used to ingest it."""

    path: str
    policy: CsvPolicy

    def __post_init__(self) -> None:
        if type(self.path) is not str or not self.path or len(self.path) > MAX_INPUT_LENGTH:
            raise ValueError("CSV source requires a bounded non-empty path.")
        if type(self.policy) not in (InferredCsvPolicy, ReviewedCsvPolicy):
            raise TypeError("CSV source requires a current CSV request policy.")


SourceContext = ParserSourceContext | CsvSourceContext


@dataclass(frozen=True, slots=True)
class LoadedDataOrigin:
    """Owned replay source and only the explicitly executed dataset-wide pipeline.

    Generic data edits clear this value. Completeness records whether the source
    request completed, independently of missing numeric simulator measurements.
    """

    source: SourceContext
    transformations_json: str = "[]"
    complete: bool = True

    def __post_init__(self) -> None:
        if type(self.source) not in (ParserSourceContext, CsvSourceContext):
            raise TypeError("Loaded origin requires an explicit current source context.")
        if (
            type(self.transformations_json) is not str
            or len(self.transformations_json) > MAX_PIPELINE_CONFIG_BYTES
        ):
            raise ValueError("Loaded transformations require bounded JSON text.")
        if type(self.complete) is not bool:
            raise TypeError("Loaded source completeness must be boolean.")
