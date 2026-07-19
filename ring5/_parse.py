"""Parse orchestration for the public API — jobs carry their own context.

The core async contract takes ``strategy_type`` on BOTH submit and finalize
and requires shuttling ``var_names``/``output_dir`` between the two calls —
two ergonomics traps for scripts. :class:`ParseJob` captures all of it at
submit time, so finalize is just ``job.finalize()``, and cancellation is
handle-based (the job owns its futures).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pandas as pd

from src.core.common.security_limits import PARSE_BATCH_TIMEOUT_SECONDS
from src.core.models import StatConfig

from ring5._scan import ScanJob
from ring5.errors import MissingStatError, ParseError, ScanError

if TYPE_CHECKING:
    from concurrent.futures import Future

    from src.core.application_api import ApplicationAPI


@dataclass(frozen=True)
class ParseResult:
    """Outcome of a finalized parse.

    Attributes:
        csv_path: The assembled CSV.
        missing_stats: Requested variables that produced no value in any
            file (the parser writes NaN for these — never a fabricated 0).
    """

    csv_path: str
    missing_stats: list[str] = field(default_factory=list)


@dataclass
class ParseJob:
    """A submitted parse batch — everything finalize needs, in one handle."""

    # [impl->req~ring5.ingestion.async-parse~1]

    api: "ApplicationAPI"
    futures: list["Future[dict[str, Any]]"]
    var_names: list[str]
    output_dir: str
    strategy: str
    stats_path: str
    stats_pattern: str

    def cancel(self) -> None:
        """Cancel this job's pending work (only this job's — handle-based)."""
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
            csv_path = self.api.finalize_parsing(
                self.output_dir,
                results,
                strategy_type=self.strategy,
                var_names=self.var_names,
            )
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            raise ParseError(f"Could not assemble parser output: {exc}") from exc
        if csv_path is None:
            raise ParseError(
                f"Parsing '{self.stats_pattern}' under {self.stats_path} produced no CSV."
            )

        try:
            missing = _find_missing_stats(csv_path, self.var_names)
        except (OSError, ValueError, UnicodeError) as exc:
            raise ParseError(f"Could not validate parser output {csv_path!r}: {exc}") from exc
        if missing and strict:
            raise MissingStatError(missing)
        return ParseResult(csv_path=csv_path, missing_stats=missing)


def _find_missing_stats(csv_path: str, var_names: list[str]) -> list[str]:
    """Variables whose columns are absent or carry no value in any row.

    A variable's values land either in a column named exactly after it or
    in entry columns prefixed with it (``var.entry``); a variable with no
    such column, or whose columns are all-missing, was never matched.
    """
    # The parser CSV contract is comma-separated (construct_final_csv).
    # No sep=None sniffing: it breaks on single-column files (the sniffer
    # picks a letter as the delimiter). The MISSING_VALUE sentinel is the
    # literal "NaN", which read_csv already parses as NaN — no extra pass.
    df = pd.read_csv(csv_path)

    missing: list[str] = []
    for name in var_names:
        cols = [c for c in df.columns if c == name or c.startswith(f"{name}.")]
        if not cols or bool(df[cols].isna().all().all()):
            missing.append(name)
    return missing


def build_stat_configs(
    api: "ApplicationAPI",
    stats_path: str,
    variables: list[str | StatConfig],
    *,
    pattern: str = "stats.txt",
    scan_limit: int = 10,
) -> tuple[list[StatConfig | dict[str, Any]], list[Any]]:
    """Resolve variable names against a scan of the tree.

    Plain string names are looked up in the scan result and converted to
    the same variable dicts the web UI submits — carrying the scanned
    metadata the parser needs (vector/histogram ``entries``, distribution
    ``minimum``/``maximum``) and the pattern-variable flag. A bare
    name+type config would crash vectors and silently parse distributions
    with a fabricated default range.

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
    configs: list[StatConfig | dict[str, Any]] = []
    unknown: list[str] = []
    for var in variables:
        if isinstance(var, StatConfig):
            if not var.is_regex and PatternIndexService.is_pattern_variable(var.name):
                var = dc_replace(var, is_regex=True)
            configs.append(var)
            continue
        found = by_name.get(var)
        if found is None:
            unknown.append(var)
            continue
        # The dict shape the web UI submits — ApplicationAPI's conversion
        # carries every key into StatConfig.params, where TypeMapper reads
        # entries (vector/histogram) and minimum/maximum (distribution).
        config: dict[str, Any] = {"name": found.name, "type": found.type}
        entries = getattr(found, "entries", None)
        if entries:
            config["entries"] = list(entries)
        minimum = getattr(found, "minimum", None)
        if minimum is not None:
            config["minimum"] = minimum
        maximum = getattr(found, "maximum", None)
        if maximum is not None:
            config["maximum"] = maximum
        configs.append(config)

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
