"""Public parse handles own their typed batch and exact submitted request context."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from concurrent.futures import Future
from typing import TYPE_CHECKING


from src.core.common.security_limits import (
    PARSE_BATCH_TIMEOUT_SECONDS,
    PARSER_PLAYGROUND_TIMEOUT_SECONDS,
)
from src.core.common.stat_config_codec import StatConfigCodec
from src.core.models.parsing_models import (
    IncrementalParseBatchResult,
    ParseBatchResult,
    ScannedVariable,
    StatConfig,
)
from src.core.models.parsed_output_models import ParsedFileResult, ParsedOutput
from src.core.models.source_context_models import ParserSourceContext
from src.core.common.parsed_output import ParsedOutputIO

from ring5._scan import ScanJob
from ring5.errors import MissingStatError, ParseError, ScanError

if TYPE_CHECKING:
    from src.core.application_api import ApplicationAPI
    from src.core.models.parsing_models import (
        ParserPlaygroundBatchResult,
        ParserPlaygroundResult,
    )


@dataclass(frozen=True)
class ParseResult:
    """Outcome of a finalized parse.

    Attributes:
        output: Explicit schema, schema-bound digest, and CSV exchange location.
        source_context: Exact owned request used to produce the finalized rows.
        csv_path: Derived CSV exchange path; pass this ParseResult to Session.load
            to preserve declared cell types and replay provenance.
        missing_stats: Requested variables that produced no value in any
            file (the parser writes NaN for these — never a fabricated 0).
        parsed_files: Number of files parsed by workers.
        reused_files: Unchanged finalized rows reused by incremental mode.
        removed_files: Cached source rows removed because their inputs disappeared.
    """

    output: ParsedOutput
    source_context: ParserSourceContext
    missing_stats: tuple[str, ...] = field(default_factory=tuple)
    parsed_files: int = field(kw_only=True)
    reused_files: int = 0
    removed_files: int = 0

    def __post_init__(self) -> None:
        if (
            type(self.output) is not ParsedOutput
            or type(self.source_context) is not ParserSourceContext
        ):
            raise TypeError("ParseResult requires typed output and explicit source context.")
        if type(self.missing_stats) is not tuple or any(
            type(name) is not str for name in self.missing_stats
        ):
            raise TypeError("Missing statistics must be an immutable tuple of text names.")
        for value in (self.parsed_files, self.reused_files, self.removed_files):
            if type(value) is not int or value < 0:
                raise ValueError("Parse result counts must be non-negative integers.")

    @property
    def csv_path(self) -> str:
        """Return the external CSV exchange path from the typed descriptor."""
        return self.output.csv_path


@dataclass(frozen=True)
class ParseJob:
    """A submitted parse batch — everything finalize needs, in one handle."""

    # [impl->req~ring5.ingestion.async-parse~1]

    api: "ApplicationAPI"
    batch: ParseBatchResult | IncrementalParseBatchResult
    source_context: ParserSourceContext

    @property
    def futures(self) -> tuple[Future[ParsedFileResult], ...]:
        """Return this batch's caller-owned futures."""
        return self.batch.futures

    @property
    def output_dir(self) -> str:
        """Return this batch's output directory."""
        return self.batch.output_dir

    def cancel(self) -> None:
        """Cancel this job's pending work (only this job's — handle-based)."""
        # [impl->req~ring5.quality.async-ownership~1]
        for future in self.futures:
            future.cancel()

    def finalize(self, *, strict: bool = True) -> ParseResult:
        """Collect results and assemble the CSV.

        Args:
            strict: Raise :class:`MissingStatError` when a requested
                variable produced no value in any file (almost always a
                typoed stat name). With ``strict=False`` the missing names
                are reported on the result instead.

        Raises:
            ParseError: A worker failed, or no CSV was produced.
            MissingStatError: See ``strict``.
        """
        # [impl->req~ring5.ingestion.parse-integrity~1]
        from concurrent.futures import wait

        if type(strict) is not bool:
            raise ParseError("Parse strict policy must be a boolean.")
        _done, pending = wait(self.futures, timeout=PARSE_BATCH_TIMEOUT_SECONDS)
        if pending:
            cancelled = sum(future.cancel() for future in pending)
            raise ParseError(
                f"Parse batch exceeded {PARSE_BATCH_TIMEOUT_SECONDS:g} seconds; "
                f"{len(pending)} file(s) remained unfinished and cancellation "
                f"succeeded for {cancelled} not-yet-running file(s)."
            )

        try:
            results = [f.result() for f in self.futures]
        except Exception as exc:
            raise ParseError(f"Parse worker failed: {exc}") from exc

        try:
            if isinstance(self.batch, IncrementalParseBatchResult):
                incremental = self.api.finalize_incremental_parsing(self.batch, results)
                output = incremental.output
                parsed_files = incremental.parsed_files
                reused_files = incremental.reused_files
                removed_files = incremental.removed_files
            else:
                output = self.api.finalize_parsing(self.batch, results)
                parsed_files = len(results)
                reused_files = 0
                removed_files = 0
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            raise ParseError(f"Could not assemble parser output: {exc}") from exc
        if type(output) is not ParsedOutput:
            raise ParseError("Parser finalization requires a ParsedOutput descriptor.")
        try:
            missing = ParsedOutputIO.read(output).missing_variables
        except (OSError, ValueError, UnicodeError) as exc:
            raise ParseError(
                f"Could not validate parser output {output.csv_path!r}: {exc}"
            ) from exc
        if missing and strict:
            raise MissingStatError(list(missing))
        return ParseResult(
            output=output,
            source_context=replace(self.source_context, strict=strict),
            missing_stats=missing,
            parsed_files=parsed_files,
            reused_files=reused_files,
            removed_files=removed_files,
        )


@dataclass(frozen=True)
class ParserPlaygroundJob:
    """Owned asynchronous dry run for a bounded parser configuration sample."""

    # [impl->req~ring5.ingestion.parser-playground~1]

    api: "ApplicationAPI"
    batch: "ParserPlaygroundBatchResult"

    @property
    def futures(self) -> tuple[Future[ParsedFileResult], ...]:
        """Return this preview batch's owned futures."""
        return self.batch.futures

    @property
    def output_dir(self) -> str:
        """Return the preview's declared output directory."""
        return self.batch.output_dir

    def cancel(self) -> None:
        """Cancel only this configuration test's pending work."""
        for future in self.futures:
            future.cancel()

    def finalize(self) -> "ParserPlaygroundResult":
        """Collect the bounded sample and return an immutable parser preview.

        Returns:
            The sampled rows, matching-file context, and readiness diagnostics.

        Raises:
            ParseError: A worker failed, timed out, or produced invalid preview output.
        """
        from concurrent.futures import wait

        _done, pending = wait(self.futures, timeout=PARSER_PLAYGROUND_TIMEOUT_SECONDS)
        if pending:
            cancelled = sum(future.cancel() for future in pending)
            raise ParseError(
                "Parser configuration test exceeded "
                f"{PARSER_PLAYGROUND_TIMEOUT_SECONDS:g} seconds; {len(pending)} file(s) "
                f"remained unfinished and {cancelled} pending file(s) were cancelled."
            )
        try:
            results = [future.result() for future in self.futures]
        except Exception as exc:
            raise ParseError(f"Parser configuration test worker failed: {exc}") from exc
        try:
            return self.api.finalize_parser_playground(self.batch, results)
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            raise ParseError(f"Parser configuration test failed: {exc}") from exc


def build_stat_configs(
    api: "ApplicationAPI",
    stats_path: str,
    variables: Sequence[str | StatConfig],
    *,
    pattern: str = "stats.txt",
    scan_limit: int = 10,
) -> tuple[list[StatConfig], list[ScannedVariable]]:
    """Resolve variable names against a scan of the tree.

    Plain string names are looked up in the scan result and converted to
    runnable StatConfig values through the current codec. Ambiguous sources
    require an explicit StatConfig declaring the source/output contract and
    any required geometry; observed entry labels do not configure a grid.

    ``StatConfig`` objects pass through (the power-user path); when the
    scan identifies their name as a pattern variable, ``is_regex`` is
    enabled so the regex actually expands.

    Args:
        api: Application facade that owns scan operations.
        stats_path: Root directory containing simulator statistics.
        variables: Statistic names or explicit statistic configurations.
        pattern: Statistics filename pattern.
        scan_limit: Maximum files to scan; zero scans every matching file
            up to the global discovery ceiling.

    Returns:
        ``(variable_configs, scanned_variables)`` — the latter must be
        passed to ``submit_parse_async`` so regex/pattern names resolve.

    Raises:
        ValueError: A source is ambiguous or an explicit configuration is invalid.
        ScanError: The stats path has no matching files, the scan failed
            for any selected file, or a requested name was not found by the scan.
    """
    from dataclasses import replace as dc_replace

    from src.core.models.pattern_index_service import PatternIndexService

    try:
        futures = api.submit_scan_async(stats_path, pattern, limit=scan_limit)
        scan = ScanJob(api, list(futures), stats_path, pattern).finalize()
    except ScanError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        raise ScanError(str(exc)) from exc

    by_name = {v.name: v for v in scan.variables}
    configs: list[StatConfig] = []
    unknown: list[str] = []
    for var in variables:
        if isinstance(var, StatConfig):
            if not var.is_regex and PatternIndexService.is_pattern_variable(var.name):
                var = dc_replace(var, is_regex=True)
            configs.append(StatConfigCodec.validate(var))
            continue
        found = by_name.get(var)
        if found is None:
            unknown.append(var)
            continue
        if found.type is None:
            raise ValueError(
                f"Scanned source {found.name!r} has no unique runnable contract. "
                "Supply an explicit StatConfig choosing the output type and params.source_type, "
                "plus any geometry that output requires; labels do not declare a grid."
            )
        configs.append(StatConfigCodec.from_draft(api.draft_from_scanned_variable(found.to_dict())))

    if unknown:
        sample = ", ".join(sorted(by_name)[:8])
        scanned_files = scan.scanned_files or len(futures)
        requested_scope = "all matching files" if scan_limit <= 0 else f"up to {scan_limit} files"
        raise ScanError(
            f"Variables not found by the scan: {', '.join(unknown)}. "
            f"Scanned {scanned_files} file(s) ({requested_scope}) and found "
            f"{len(by_name)} variables (e.g. {sample}…). A stat present only in unsampled files "
            "needs a deeper scan: pass scan_limit=0 (all files). "
            "For regex patterns, pass a StatConfig."
        )

    return configs, list(scan.variables)
