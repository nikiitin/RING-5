"""gem5 parser backend for parallel scanning, parsing, and CSV assembly."""

import csv
import logging
import math
import os
import tempfile
import time
from concurrent.futures import Future
from dataclasses import replace
from pathlib import Path
from typing import Any

from src.core.common.input_identity import fingerprint_inputs
from src.core.common.utils import normalize_user_path
from src.core.common.security_limits import (
    MAX_DISCOVERED_FILES,
    MAX_INCREMENTAL_CACHE_COLUMNS,
    MAX_PARSE_FILES,
    MAX_PARSER_PLAYGROUND_CELLS,
    MAX_PARSER_PLAYGROUND_FILES,
    MAX_PARSER_PLAYGROUND_VARIABLES,
)
from src.core.models.parsing_models import (
    IncrementalParseBatchResult,
    IncrementalParseResult,
    ParseBatchResult,
    ParserPlaygroundBatchResult,
    ParserPlaygroundResult,
    ScanFileResult,
    ScannedVariable,
    ScanResult,
    StatConfig,
)
from src.core.models.csv_contract import MISSING_VALUE, validate_parser_csv
from src.parsing.framework.file_discovery import find_stats_files
from src.parsing.framework.incremental_cache import (
    DEFAULT_CACHE_NAME,
    configuration_hash,
    load_cache,
    write_cache,
)
from src.parsing.framework.work_pool import WorkPool
from src.parsing.gem5.impl.scanning.gem5_scan_work import Gem5ScanWork
from src.parsing.gem5.impl.source_bindings import resolve_sources
from src.parsing.gem5.impl.scanning.pattern_aggregator import PatternAggregator
from src.parsing.gem5.impl.strategies.factory import StrategyFactory
from src.parsing.gem5.impl.strategies.file_parser_strategy import INTERNAL_SIM_PATH_KEY
from src.parsing.gem5.models import Gem5ScannedVariable
from src.parsing.parser_protocol import SimulationParser

logger = logging.getLogger(__name__)


def _render_value(val: Any) -> str:
    """Render a reduced stat value for the CSV, mapping missing → MISSING_VALUE.

    A missing/unmeasured numeric value (None, NaN, or the legacy ``"NA"``
    sentinel) is written as the canonical ``MISSING_VALUE`` so it is never
    confused with a measured 0 (hard rule 6).
    """
    if val is None or val == "NA":
        return MISSING_VALUE
    if isinstance(val, float) and math.isnan(val):
        return MISSING_VALUE
    return str(val)


def _flatten_result(result: dict[str, Any], var_names: list[str]) -> dict[str, str]:
    """Reduce one result into named scalar cells before publishing output."""
    extras = sorted(
        name
        for name, value in result.items()
        if name not in var_names and not hasattr(value, "balance_content")
    )
    ordered_names = list(dict.fromkeys([*var_names, *extras]))
    row: dict[str, str] = {}
    for name in ordered_names:
        if name not in result:
            continue
        value = result[name]
        if hasattr(value, "balance_content"):
            value.balance_content()
            value.reduce_duplicates()
            reduced = value.reduced_content
            entries = value.entries
            if entries:
                if not isinstance(reduced, dict):
                    raise RuntimeError(
                        f"PARSER: entry statistic {name!r} did not reduce to a mapping."
                    )
                cells = {f"{name}..{entry}": _render_value(reduced.get(entry)) for entry in entries}
            elif isinstance(reduced, dict):
                cells = {}  # An unobserved dynamic histogram has no known bucket schema.
            else:
                cells = {name: _render_value(reduced)}
        else:
            cells = {name: str(value)}
        if row.keys() & cells.keys():
            raise RuntimeError(f"PARSER: duplicate output column for {name!r}.")
        row.update(cells)
        if len(row) > MAX_INCREMENTAL_CACHE_COLUMNS:
            raise RuntimeError(
                f"PARSER: output exceeds the {MAX_INCREMENTAL_CACHE_COLUMNS}-column limit."
            )
    return row


def _csv_columns(rows: list[dict[str, str]], var_names: list[str]) -> list[str]:
    """Resolve an order-independent schema without rescanning every cell per variable."""
    names = set(var_names)
    schemas: dict[str, set[tuple[str, ...]]] = {name: set() for name in names}
    extras: set[str] = set()
    for row in rows:
        grouped: dict[str, list[str]] = {}
        for column in row:
            candidate = column
            owners: list[str] = []
            while True:
                if candidate in names:
                    owners.append(candidate)
                if ".." not in candidate:
                    break
                candidate = candidate.rsplit("..", 1)[0]
            if len(owners) > 1:
                raise RuntimeError(f"PARSER: ambiguous output column {column!r}.")
            if owners:
                grouped.setdefault(owners[0], []).append(column)
            else:
                extras.add(column)
        for name, schema_columns in grouped.items():
            schemas[name].add(tuple(schema_columns))

    columns: list[str] = []
    for name in dict.fromkeys(var_names):
        matching = list(
            dict.fromkeys(column for schema in sorted(schemas[name]) for column in schema)
        )
        if name in matching and any(column != name for column in matching):
            raise RuntimeError(f"PARSER: inconsistent scalar/entry output shape for {name!r}.")
        columns.extend(matching or [name])
    columns.extend(sorted(extras))
    if len(columns) > MAX_INCREMENTAL_CACHE_COLUMNS:
        raise RuntimeError(
            f"PARSER: output exceeds the {MAX_INCREMENTAL_CACHE_COLUMNS}-column limit."
        )
    return columns


class Gem5Parser(SimulationParser):
    """The gem5 simulation backend — parsing, scanning, and CSV assembly.

    The single class the registry instantiates for ``"gem5"``; implements the
    ``SimulationParser`` protocol. Methods are static (no instance state — the
    pools are singletons), so they are callable both on the class and on the
    instance the registry hands to ``ApplicationAPI``.
    """

    # [impl->req~ring5.ingestion.gem5-backend~1]

    @staticmethod
    def submit_parse_async(
        stats_path: str,
        stats_pattern: str,
        variables: list[StatConfig],
        output_dir: str,
        strategy_type: str = "simple",
        scanned_vars: list[ScannedVariable] | None = None,
        *,
        file_paths: list[str] | None = None,
    ) -> ParseBatchResult:
        """Submit async parsing job and return a ParseBatchResult."""
        t_start = time.perf_counter()
        safe_path: str = os.path.normpath(stats_path) if stats_path else "."
        search_path = normalize_user_path(safe_path)
        if not search_path.exists():
            raise FileNotFoundError(f"Stats path does not exist: {stats_path}")

        t_regex_start = time.perf_counter()
        plan = resolve_sources(variables, scanned_vars)
        logger.info(
            "PERF: Source binding resolution took %.4fs", time.perf_counter() - t_regex_start
        )

        # 2. Resolve strategy via factory
        strategy = StrategyFactory.create(strategy_type)

        # 3. Get work items from strategy
        t_work_start = time.perf_counter()
        selected_paths: list[str] | None = None
        if file_paths is not None:
            requested_paths = {str(Path(path).resolve(strict=True)) for path in file_paths}
            discovered_paths = {
                str(Path(path).resolve(strict=True))
                for path in find_stats_files(
                    stats_path,
                    stats_pattern,
                    sort=True,
                    raise_if_empty=True,
                )
            }
            unknown_paths = requested_paths - discovered_paths
            if unknown_paths:
                raise ValueError(
                    "PARSER: incremental selection contains files outside the discovered batch: "
                    + ", ".join(sorted(unknown_paths))
                )
            selected_paths = sorted(requested_paths)
        batch_work = strategy.get_work_items(
            stats_path,
            stats_pattern,
            plan,
            file_paths=selected_paths,
        )
        t_work_end = time.perf_counter()
        logger.info(f"PERF: Work item generation took {t_work_end - t_work_start:.4f}s")

        if not batch_work:
            # Strategies raise on zero matching files; an empty work list here
            # means a custom strategy produced nothing — fail loudly rather
            # than letting the parse "succeed" while producing no CSV.
            raise FileNotFoundError(
                f"No parse work generated for pattern '{stats_pattern}' under: {stats_path}"
            )

        var_names: list[str] = [spec.output_name for spec in plan.accumulators]

        pool = WorkPool.get_instance()
        futures = pool.submit_many(batch_work)

        t_total = time.perf_counter() - t_start
        logger.info(f"PERF: submit_parse_async total (pre-pool) took {t_total:.4f}s")
        return ParseBatchResult(futures=futures, var_names=var_names)

    @staticmethod
    def submit_incremental_parse_async(
        stats_path: str,
        stats_pattern: str,
        variables: list[StatConfig],
        output_dir: str,
        strategy_type: str = "simple",
        scanned_vars: list[ScannedVariable] | None = None,
        cache_path: str | None = None,
    ) -> IncrementalParseBatchResult:
        # [impl->req~ring5.ingestion.incremental-parsing~1]
        """Fingerprint a parse tree and submit workers only for new or changed files."""
        files = find_stats_files(stats_path, stats_pattern, sort=True, raise_if_empty=True)
        fingerprints = fingerprint_inputs(files, strategy_type)
        config_hash = configuration_hash(
            stats_pattern,
            strategy_type,
            variables,
            scanned_vars,
        )
        resolved_cache = (
            Path(cache_path).expanduser().resolve()
            if cache_path
            else Path(output_dir).expanduser().resolve() / DEFAULT_CACHE_NAME
        )
        protected_paths = {Path(source_path) for source_path, _fingerprint in fingerprints}
        if strategy_type == "config_aware":
            protected_paths.update(path.parent / "config.ini" for path in tuple(protected_paths))
        output_path = Path(output_dir).expanduser().resolve() / "results.csv"
        if (
            resolved_cache == output_path
            or resolved_cache in protected_paths
            or output_path in protected_paths
        ):
            raise ValueError(
                "PARSER: incremental output or cache path must not replace results.csv or a "
                "simulator input."
            )
        cached_var_names, cached_files = load_cache(resolved_cache, config_hash)
        current_fingerprints = dict(fingerprints)

        cached_rows: list[tuple[str, tuple[tuple[str, str], ...]]] = []
        changed_files: list[str] = []
        for source_path, fingerprint in fingerprints:
            cached = cached_files.get(source_path)
            if cached is not None and cached[0] == fingerprint:
                cached_rows.append((source_path, tuple(cached[1].items())))
            else:
                changed_files.append(source_path)

        removed_files = tuple(sorted(set(cached_files) - set(current_fingerprints)))
        futures: list[Future[dict[str, Any]]] = []
        var_names = cached_var_names
        if changed_files:
            changed_batch = Gem5Parser.submit_parse_async(
                stats_path,
                stats_pattern,
                variables,
                output_dir,
                strategy_type,
                scanned_vars,
                file_paths=changed_files,
            )
            futures = list(changed_batch.futures)
            var_names = list(changed_batch.var_names)
        if not var_names:
            raise RuntimeError("PARSER: incremental parse has no resolved variable names.")

        logger.info(
            "PARSER: incremental plan has %d changed, %d reused, and %d removed files",
            len(changed_files),
            len(cached_rows),
            len(removed_files),
        )
        return IncrementalParseBatchResult(
            futures=futures,
            var_names=var_names,
            output_dir=str(Path(output_dir).expanduser().resolve()),
            strategy_type=strategy_type,
            cache_path=str(resolved_cache),
            configuration_hash=config_hash,
            fingerprints=fingerprints,
            cached_rows=tuple(cached_rows),
            changed_files=tuple(changed_files),
            removed_files=removed_files,
        )

    @staticmethod
    def submit_parser_playground_async(
        stats_path: str,
        stats_pattern: str,
        variables: list[StatConfig],
        output_dir: str,
        strategy_type: str = "simple",
        scanned_vars: list[ScannedVariable] | None = None,
    ) -> ParserPlaygroundBatchResult:
        # [impl->req~ring5.ingestion.parser-playground~1]
        """Submit the real parser for a deterministic, bounded sample of matching files."""
        if not variables:
            raise ValueError("PARSER: add at least one variable before testing the configuration.")
        if len(variables) > MAX_PARSER_PLAYGROUND_VARIABLES:
            raise ValueError(
                "PARSER: configuration tests accept at most "
                f"{MAX_PARSER_PLAYGROUND_VARIABLES} variables; narrow the test first."
            )
        files = find_stats_files(stats_path, stats_pattern, sort=True, raise_if_empty=True)
        sampled_files = tuple(files[:MAX_PARSER_PLAYGROUND_FILES])
        parse_batch = Gem5Parser.submit_parse_async(
            stats_path,
            stats_pattern,
            variables,
            output_dir,
            strategy_type,
            scanned_vars,
            file_paths=list(sampled_files),
        )
        diagnostics: list[str] = []
        if len(files) > len(sampled_files):
            diagnostics.append(
                f"Previewed {len(sampled_files)} of {len(files)} matching files in lexical order."
            )
        if len(files) > MAX_PARSE_FILES:
            diagnostics.append(
                f"A full parse would exceed the {MAX_PARSE_FILES}-file safety limit."
            )
        return ParserPlaygroundBatchResult(
            futures=list(parse_batch.futures),
            var_names=list(parse_batch.var_names),
            output_dir=str(Path(output_dir).expanduser().resolve()),
            strategy_type=strategy_type,
            matched_file_count=len(files),
            sampled_files=sampled_files,
            diagnostics=tuple(diagnostics),
        )

    # ------------------------------------------------------------------ scanning

    @staticmethod
    def submit_scan_async(
        stats_path: str, stats_pattern: str = "stats.txt", limit: int = 5
    ) -> list[Future[ScanFileResult]]:
        """
        Submit async scan job and return futures.

        Args:
            stats_path: Base directory to search for stats files
            stats_pattern: Filename pattern to match (default: "stats.txt")
            limit: Maximum number of files to scan. Non-positive values scan
                every matching file up to the global discovery safety ceiling.

        Returns:
            List of Future objects that each resolve to a ``ScanFileResult``

        Raises:
            FileNotFoundError: If stats_path doesn't exist or no files found
        """
        if limit > MAX_DISCOVERED_FILES:
            raise ValueError(
                f"Scan limit {limit} exceeds the global safety ceiling of "
                f"{MAX_DISCOVERED_FILES} files."
            )
        effective_limit = 0 if limit <= 0 else limit
        files = find_stats_files(
            stats_path,
            stats_pattern,
            limit=effective_limit,
            sort=True,
            raise_if_empty=True,
        )
        pool = WorkPool.get_instance()
        batch_work: list[Gem5ScanWork] = [Gem5ScanWork(f) for f in files]
        return pool.submit_many(batch_work)

    @staticmethod
    def aggregate_scan_results(results: list[ScanFileResult]) -> ScanResult:
        """
        Aggregate per-file scan results into a unified outcome.

        Successful files are merged and deduplicated into one variable list;
        failed files are collected separately so the caller can surface them
        instead of silently treating a failed scan as "no variables".

        Args:
            results: Per-file ``ScanFileResult`` objects from the workers.

        Returns:
            ``ScanResult`` with the merged variables and the list of failures.
        """
        # [impl->req~ring5.ingestion.variable-scan~1]
        failures: list[ScanFileResult] = [r for r in results if not r.ok]

        merged_registry: dict[str, ScannedVariable] = {}
        for file_result in results:
            for var in file_result.variables:
                Gem5Parser._merge_variable(merged_registry, var)

        merged_vars = sorted(list(merged_registry.values()), key=lambda x: x.name)

        # Apply pattern aggregation to consolidate repeated numeric patterns
        aggregated_vars = PatternAggregator.aggregate_patterns(merged_vars)

        return ScanResult(
            variables=aggregated_vars,
            failures=failures,
            scanned_files=len(results),
        )

    @staticmethod
    def _merge_variable(registry: dict[str, ScannedVariable], var: ScannedVariable) -> None:
        """
        Merge a single variable into the registry.

        Handles deduplication and merging of:
        - Vector/histogram entries (union of all entries)
        - Distribution min/max ranges (expanded to include all values)

        Args:
            registry: Mutable registry dict to update
            var: ScannedVariable to merge in
        """

        name: str = var.name
        if name not in registry:
            registry[name] = var
        else:
            existing = registry[name]
            if existing.source_type != var.source_type or existing.type != var.type:
                raise ValueError(f"Scanned source {name!r} has incompatible source kinds.")
            if existing.instances != var.instances:
                raise ValueError(f"Scanned source {name!r} has inconsistent source instances.")
            if var.type in ("vector", "histogram"):
                new_entries = sorted(list(set(existing.entries) | set(var.entries)))
                # Retain explicit source identity while merging measurement entries.
                registry[name] = replace(existing, entries=new_entries)

            elif var.type == "distribution":
                # Handle distribution range merging (gem5-specific min/max)
                gem5_existing = existing if isinstance(existing, Gem5ScannedVariable) else None
                gem5_var = var if isinstance(var, Gem5ScannedVariable) else None

                cur_min = gem5_existing.minimum if gem5_existing else None
                cur_max = gem5_existing.maximum if gem5_existing else None
                var_min = gem5_var.minimum if gem5_var else None
                var_max = gem5_var.maximum if gem5_var else None

                # Explicit None guards — `var_min or cur_min` would discard a
                # legitimate scanned minimum of 0.0 (falsy), losing the range.
                new_min: float | None
                new_max: float | None
                if cur_min is not None and var_min is not None:
                    new_min = min(cur_min, var_min)
                else:
                    new_min = var_min if var_min is not None else cur_min
                if cur_max is not None and var_max is not None:
                    new_max = max(cur_max, var_max)
                else:
                    new_max = var_max if var_max is not None else cur_max

                registry[name] = Gem5ScannedVariable(
                    name=existing.name,
                    type=existing.type,
                    entries=existing.entries,
                    source_type=existing.source_type,
                    instances=existing.instances,
                    minimum=new_min,
                    maximum=new_max,
                )

    # ----------------------------------------------------------------- finalize

    @staticmethod
    def finalize_parsing(
        output_dir: str,
        results: list[dict[str, Any]],
        strategy_type: str = "simple",
        var_names: list[str] | None = None,
    ) -> str | None:
        """
        Post-process and aggregate provided results into final CSV.
        """
        # [impl->req~ring5.ingestion.parse-integrity~1]
        t_start = time.perf_counter()
        if not results:
            logger.warning("PARSER: No results to persist.")
            return None

        # Resolve strategy via factory for post-processing
        strategy = StrategyFactory.create(strategy_type)

        t_post_start = time.perf_counter()
        processed_results = strategy.post_process(results)
        t_post_end = time.perf_counter()
        logger.info(f"PERF: Strategy post-processing took {t_post_end - t_post_start:.4f}s")

        csv_path = Gem5Parser.construct_final_csv(
            output_dir, processed_results, var_names=var_names
        )

        # Enforce the inter-layer CSV contract (logged, non-fatal).
        if csv_path and Path(csv_path).exists():
            for warning in validate_parser_csv(Path(csv_path)):
                logger.warning("CSV contract: %s", warning)

        t_total = time.perf_counter() - t_start
        logger.info(f"PERF: finalize_parsing total took {t_total:.4f}s")
        return csv_path

    @staticmethod
    def _flatten_incremental_result(
        result: dict[str, Any],
        strategy_type: str,
        var_names: list[str],
    ) -> tuple[str, dict[str, str]]:
        """Reduce one worker result into safe JSON/CSV scalar cells."""
        source_value = result.get(INTERNAL_SIM_PATH_KEY)
        if not isinstance(source_value, str) or not source_value:
            raise RuntimeError("PARSER: incremental result is missing simulation provenance.")
        source_path = str(Path(source_value).resolve(strict=True))
        processed = StrategyFactory.create(strategy_type).post_process([result])
        if len(processed) != 1:
            raise RuntimeError("PARSER: incremental strategy changed the per-file row count.")

        return source_path, _flatten_result(processed[0], var_names)

    @staticmethod
    def finalize_incremental_parsing(
        batch: IncrementalParseBatchResult,
        results: list[dict[str, Any]],
        *,
        complete: bool = True,
    ) -> IncrementalParseResult:
        # [impl->req~ring5.ingestion.incremental-parsing~1]
        """Publish valid incremental rows and promote the cache only for complete work.

        Args:
            batch: Reviewed input fingerprints, changed files and reusable rows.
            results: Successful changed-file results with exact provenance.
            complete: Require all planned rows and replace the success cache.
                False retains accepted cached and changed rows without cache promotion.

        Returns:
            Published CSV, accepted changed/reused counts and the planned file total.

        Raises:
            TypeError: The completion mode is not a boolean.
            RuntimeError: Provenance is invalid, inputs changed, or no partial rows are usable.
        """
        if type(complete) is not bool:
            raise TypeError("Incremental completion mode must be a boolean.")
        current_paths, rows = Gem5Parser._prepare_incremental_rows(
            batch, results, require_complete=complete
        )
        output_path = Gem5Parser._write_incremental_csv(batch, current_paths, rows)
        if complete:
            write_cache(
                Path(batch.cache_path),
                batch.configuration_hash,
                batch.var_names,
                batch.fingerprints,
                rows,
            )
        return IncrementalParseResult(
            csv_path=str(output_path),
            parsed_files=len(results),
            reused_files=batch.reused_file_count,
            removed_files=batch.removed_file_count,
            total_files=batch.total_file_count,
        )

    @staticmethod
    def _prepare_incremental_rows(
        batch: IncrementalParseBatchResult,
        results: list[dict[str, Any]],
        *,
        require_complete: bool,
    ) -> tuple[list[str], dict[str, dict[str, str]]]:
        """Validate worker provenance and combine it with reusable scalar rows."""
        current_fingerprints = fingerprint_inputs(
            [source_path for source_path, _fingerprint in batch.fingerprints],
            batch.strategy_type,
        )
        if current_fingerprints != batch.fingerprints:
            raise RuntimeError(
                "PARSER: simulator inputs changed during incremental parsing; submit again "
                "before finalizing incremental output."
            )
        expected_changed = set(batch.changed_files)
        if require_complete and len(results) != len(expected_changed):
            raise RuntimeError(
                "PARSER: incremental finalization received "
                f"{len(results)} results for {len(expected_changed)} changed files."
            )
        if len(results) > len(expected_changed):
            raise RuntimeError(
                "PARSER: incremental partial finalization received more results than changed files."
            )

        rows = {source_path: dict(cells) for source_path, cells in batch.cached_rows}
        for result in results:
            source_path, row = Gem5Parser._flatten_incremental_result(
                result,
                batch.strategy_type,
                batch.var_names,
            )
            if source_path not in expected_changed:
                raise RuntimeError(
                    f"PARSER: incremental worker returned an unplanned file: {source_path}"
                )
            if source_path in rows:
                raise RuntimeError(
                    f"PARSER: incremental worker returned duplicate provenance: {source_path}"
                )
            rows[source_path] = row

        current_paths = [source_path for source_path, _fingerprint in batch.fingerprints]
        if require_complete and set(rows) != set(current_paths):
            missing_paths = sorted(set(current_paths) - set(rows))
            raise RuntimeError(
                "PARSER: incremental finalization is missing rows for: " + ", ".join(missing_paths)
            )
        if not require_complete:
            current_paths = [source_path for source_path in current_paths if source_path in rows]
            if not current_paths:
                raise RuntimeError("PARSER: incremental partial finalization has no usable rows.")
        return current_paths, rows

    @staticmethod
    def _write_incremental_csv(
        batch: IncrementalParseBatchResult,
        current_paths: list[str],
        rows: dict[str, dict[str, str]],
    ) -> Path:
        """Atomically write ordered incremental rows to the attempt CSV."""
        columns = _csv_columns(
            [rows[source_path] for source_path in current_paths], batch.var_names
        )

        output_dir = Path(batch.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "results.csv"
        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="",
                prefix=".results.",
                suffix=".csv.tmp",
                dir=output_dir,
                delete=False,
            ) as handle:
                temporary_name = handle.name
                writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="raise")
                writer.writeheader()
                for source_path in current_paths:
                    writer.writerow(
                        {column: rows[source_path].get(column, MISSING_VALUE) for column in columns}
                    )
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, output_path)
            temporary_name = None
        finally:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)

        for warning in validate_parser_csv(output_path):
            logger.warning("CSV contract: %s", warning)
        return output_path

    @staticmethod
    def finalize_parser_playground(
        batch: ParserPlaygroundBatchResult,
        results: list[dict[str, Any]],
    ) -> ParserPlaygroundResult:
        # [impl->req~ring5.ingestion.parser-playground~1]
        """Finalize a bounded dry run into cells and diagnostics without retaining a CSV."""
        if len(results) != len(batch.sampled_files):
            raise RuntimeError(
                "PARSER: configuration test received "
                f"{len(results)} results for {len(batch.sampled_files)} sampled files."
            )

        output_dir = Path(batch.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="ring5-playground-", dir=output_dir) as scratch:
            csv_path = Gem5Parser.finalize_parsing(
                scratch,
                results,
                strategy_type=batch.strategy_type,
                var_names=batch.var_names,
            )
            if csv_path is None:
                raise RuntimeError("PARSER: configuration test produced no preview table.")
            with Path(csv_path).open("r", encoding="utf-8", newline="") as handle:
                reader = csv.reader(handle)
                try:
                    columns = tuple(next(reader))
                except StopIteration as exc:
                    raise RuntimeError("PARSER: configuration test produced an empty CSV.") from exc
                rows = tuple(tuple(value for value in row) for row in reader)

        if len(columns) * max(len(rows), 1) > MAX_PARSER_PLAYGROUND_CELLS:
            raise RuntimeError(
                "PARSER: configuration preview exceeds the "
                f"{MAX_PARSER_PLAYGROUND_CELLS}-cell limit."
            )
        missing_variables: list[str] = []
        for variable in batch.var_names:
            indices = [
                index
                for index, column in enumerate(columns)
                if column == variable or column.startswith(f"{variable}..")
            ]
            if not indices or all(
                not row[index] or row[index] == MISSING_VALUE for row in rows for index in indices
            ):
                missing_variables.append(variable)

        diagnostics = list(batch.diagnostics)
        if missing_variables:
            diagnostics.append(
                "No sampled value was produced for: " + ", ".join(missing_variables) + "."
            )
        ready = not missing_variables and batch.matched_file_count <= MAX_PARSE_FILES
        if ready:
            diagnostics.append("The sampled configuration is ready for a full parse.")
        return ParserPlaygroundResult(
            matched_file_count=batch.matched_file_count,
            sampled_files=batch.sampled_files,
            columns=columns,
            rows=rows,
            missing_variables=tuple(missing_variables),
            diagnostics=tuple(diagnostics),
            ready_for_full_parse=ready,
        )

    @staticmethod
    def construct_final_csv(
        output_dir: str,
        results: list[dict[str, Any]],
        var_names: list[str] | None = None,
    ) -> str | None:
        """
        Aggregate provided results and save to CSV.
        """
        # [impl->req~ring5.ingestion.pattern-index-selection~1]
        t_start = time.perf_counter()
        if not results:
            return None
        logger.info(f"PERF: Starting construct_final_csv for {len(results)} files")

        ordered_names = list(var_names) if var_names else list(results[0])
        if not var_names:
            ordered_names.extend(
                sorted({name for result in results for name in result if name not in ordered_names})
            )
        rows = [_flatten_result(result, ordered_names) for result in results]
        columns = _csv_columns(rows, ordered_names)
        output_root = Path(normalize_user_path(output_dir))
        output_root.mkdir(parents=True, exist_ok=True)
        output_path = output_root / "results.csv"

        t_write_start = time.perf_counter()
        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="",
                dir=output_root,
                prefix=".results-",
                suffix=".csv",
                delete=False,
            ) as stream:
                temporary_name = stream.name
                writer = csv.writer(stream, quoting=csv.QUOTE_MINIMAL)
                writer.writerow(columns)
                for row in rows:
                    writer.writerow([row.get(column, MISSING_VALUE) for column in columns])
            os.replace(temporary_name, output_path)
            temporary_name = None
        finally:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)
        t_write_end = time.perf_counter()
        logger.info(f"PERF: CSV writing loop took {t_write_end - t_write_start:.4f}s")

        t_total = time.perf_counter() - t_start
        logger.info(f"PERF: construct_final_csv total took {t_total:.4f}s")
        return str(output_path)
