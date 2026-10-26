"""gem5 parser backend for parallel scanning, parsing, and CSV assembly."""

import logging
import os
import time
from concurrent.futures import Future
from dataclasses import replace
from pathlib import Path

from src.core.common.input_identity import fingerprint_inputs
from src.core.models.parsed_output_models import ParsedFileResult, ParsedOutput
from src.core.common.parsed_output import ParsedOutputIO
from src.core.common.utils import normalize_user_path
from src.core.common.security_limits import (
    MAX_DISCOVERED_FILES,
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
from src.parsing.framework.file_discovery import find_stats_files
from src.parsing.framework.incremental_cache import (
    DEFAULT_CACHE_NAME,
    configuration_hash,
    encode_cache,
    load_cache,
    write_cache,
)
from src.parsing.framework.work_pool import WorkPool
from src.parsing.framework.result_admission import AdmittedParseWork, ResultAdmission
from src.parsing.gem5.impl.scanning.gem5_scan_work import Gem5ScanWork
from src.parsing.gem5.impl.source_bindings import resolve_sources
from src.parsing.gem5.impl.scanning.pattern_aggregator import PatternAggregator
from src.parsing.gem5.impl.strategies.factory import StrategyFactory
from src.parsing.gem5.models import Gem5ScannedVariable
from src.parsing.parser_protocol import ParseWorkItem, SimulationParser

logger = logging.getLogger(__name__)


class Gem5Parser(SimulationParser):
    """The gem5 simulation backend — parsing, scanning, and CSV assembly.

    The single class the registry instantiates for ``"gem5"``; implements the
    ``SimulationParser`` protocol. Methods are static (no instance state — the
    pools are singletons), so they are callable both on the class and on the
    instance the registry hands to ``ApplicationAPI``.
    """

    # [impl->req~ring5.ingestion.gem5-backend~1]

    @staticmethod
    def _prepare_work_items(
        stats_path: str,
        stats_pattern: str,
        variables: list[StatConfig],
        strategy_type: str,
        scanned_vars: list[ScannedVariable] | None,
        *,
        file_paths: list[str] | None,
    ) -> tuple[tuple[str, ...], tuple[ParseWorkItem, ...]]:
        """Resolve one source plan and independent work without submitting Futures."""
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

        return tuple(spec.output_name for spec in plan.accumulators), tuple(batch_work)

    @staticmethod
    def _submit_admitted_work(
        work: tuple[ParseWorkItem, ...], admission: ResultAdmission
    ) -> tuple[Future[ParsedFileResult], ...]:
        """Share exactly one source-owned result quota across this batch's Futures."""
        if not work:
            return ()
        tasks = tuple(AdmittedParseWork(item, admission) for item in work)
        return tuple(WorkPool.get_instance().submit_many(tasks))

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
        """Submit typed file work under one exact source plan and retained-result quota."""
        output_root = str(normalize_user_path(output_dir))
        var_names, work = Gem5Parser._prepare_work_items(
            stats_path, stats_pattern, variables, strategy_type, scanned_vars, file_paths=file_paths
        )
        source_paths = tuple(item.source_path for item in work)
        Gem5Parser._admit_target_paths(
            Path(output_root) / "results.csv", source_paths, strategy_type
        )
        admission = ResultAdmission(source_paths)
        futures = Gem5Parser._submit_admitted_work(work, admission)
        return ParseBatchResult(futures, var_names, source_paths, output_root, strategy_type)

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
        Gem5Parser._admit_target_paths(
            Path(output_dir) / "results.csv",
            tuple(source_path for source_path, _ in fingerprints),
            strategy_type,
            resolved_cache,
        )
        reuse = load_cache(resolved_cache, config_hash, fingerprints)
        cached_results = reuse.results
        reused_paths = {result.source_path for result in cached_results}
        changed_files = tuple(path for path, _ in fingerprints if path not in reused_paths)
        var_names = reuse.var_names
        work: tuple[ParseWorkItem, ...] = ()
        if changed_files:
            var_names, work = Gem5Parser._prepare_work_items(
                stats_path,
                stats_pattern,
                variables,
                strategy_type,
                scanned_vars,
                file_paths=list(changed_files),
            )
        futures = Gem5Parser._submit_admitted_work(work, reuse.admission)
        removed_files = reuse.removed_files
        if not var_names:
            raise RuntimeError("PARSER: incremental parse has no resolved variable names.")

        logger.info(
            "PARSER: incremental plan has %d changed, %d reused, and %d removed files",
            len(changed_files),
            len(cached_results),
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
            cached_results=tuple(cached_results),
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
        var_names, work = Gem5Parser._prepare_work_items(
            stats_path,
            stats_pattern,
            variables,
            strategy_type,
            scanned_vars,
            file_paths=list(sampled_files),
        )
        sampled_files = tuple(item.source_path for item in work)
        admission = ResultAdmission(sampled_files)
        futures = Gem5Parser._submit_admitted_work(work, admission)
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
            futures=futures,
            var_names=var_names,
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
    def _admit_target_paths(
        output_path: Path,
        source_paths: tuple[str, ...],
        strategy_type: str,
        cache_path: Path | None = None,
    ) -> Path:
        """Keep parser publication and cache records separate from planned simulator inputs."""
        target = output_path.expanduser().resolve()
        planned_inputs = tuple(Path(path).expanduser() for path in source_paths)
        inputs = {path.resolve() for path in planned_inputs}
        if strategy_type == "config_aware":
            # Companion ownership follows the work item's planned source path;
            # resolve its actual target just as output/cache targets are resolved.
            inputs.update((path.parent / "config.ini").resolve() for path in planned_inputs)
        cache = cache_path.expanduser().resolve() if cache_path is not None else None
        if target in inputs or cache in inputs or cache == target:
            raise ValueError(
                "PARSER: output and cache targets must not replace simulator inputs or each other."
            )
        return target

    @staticmethod
    def finalize_parsing(
        batch: ParseBatchResult,
        results: list[ParsedFileResult],
        *,
        complete: bool = True,
    ) -> ParsedOutput:
        """Resolve the required source plan and atomically publish finalized typed rows.

        Args:
            batch: Submitted immutable source, variable, output and strategy context.
            results: Successful typed file results owned by this exact batch.
            complete: Require every planned source. False permits non-empty partial output.

        Returns:
            The typed-content descriptor for the successfully published CSV.
        """
        # [impl->req~ring5.ingestion.parse-integrity~1]
        if type(batch) is not ParseBatchResult:
            raise TypeError("Full parsing requires its exact ParseBatchResult context.")
        StrategyFactory.create(batch.strategy_type)
        target = Gem5Parser._admit_target_paths(
            Path(batch.output_dir) / "results.csv", batch.source_paths, batch.strategy_type
        )
        table = ParsedOutputIO.resolve(
            results, batch.var_names, batch.source_paths, complete=complete
        )
        return ParsedOutputIO.publish(target, table)

    @staticmethod
    def finalize_incremental_parsing(
        batch: IncrementalParseBatchResult,
        results: list[ParsedFileResult],
        *,
        complete: bool = True,
    ) -> IncrementalParseResult:
        # [impl->req~ring5.ingestion.incremental-parsing~1]
        """Publish planned typed rows; promote prepared cache bytes only for complete work."""
        if type(batch) is not IncrementalParseBatchResult:
            raise TypeError("Incremental parsing requires its exact submitted context.")
        StrategyFactory.create(batch.strategy_type)
        if type(complete) is not bool:
            raise TypeError("Incremental completion mode must be a boolean.")
        if len(results) > len(batch.changed_files):
            raise ValueError(
                "Incremental finalization received more results than planned changed sources."
            )
        paths = tuple(source_path for source_path, _ in batch.fingerprints)
        cache = Path(batch.cache_path)
        target = Gem5Parser._admit_target_paths(
            Path(batch.output_dir) / "results.csv", paths, batch.strategy_type, cache
        )
        if fingerprint_inputs(paths, batch.strategy_type) != batch.fingerprints:
            raise RuntimeError(
                "PARSER: simulator inputs changed during incremental parsing; submit again."
            )
        combined = (*batch.cached_results, *results)
        table = ParsedOutputIO.resolve(combined, batch.var_names, paths, complete=complete)
        encoded = (
            encode_cache(batch.configuration_hash, batch.var_names, batch.fingerprints, combined)
            if complete
            else None
        )
        output = ParsedOutputIO.publish(
            target,
            table,
            after_publish=(lambda _: write_cache(cache, encoded)) if encoded is not None else None,
        )
        return IncrementalParseResult(
            output,
            len(results),
            len(batch.cached_results),
            batch.removed_file_count,
            batch.total_file_count,
        )

    @staticmethod
    def finalize_parser_playground(
        batch: ParserPlaygroundBatchResult,
        results: list[ParsedFileResult],
    ) -> ParserPlaygroundResult:
        # [impl->req~ring5.ingestion.parser-playground~1]
        """Resolve literal text and numeric preview values without creating a CSV."""
        if type(batch) is not ParserPlaygroundBatchResult:
            raise TypeError("Parser playground requires its exact submitted context.")
        StrategyFactory.create(batch.strategy_type)
        table = ParsedOutputIO.resolve(results, batch.var_names, batch.sampled_files)
        if len(table.schema.columns) * len(table.rows) > MAX_PARSER_PLAYGROUND_CELLS:
            raise ValueError("PARSER: configuration preview exceeds the matrix cell limit.")
        diagnostics = list(batch.diagnostics)
        if table.missing_variables:
            diagnostics.append(
                "No sampled value was produced for: " + ", ".join(table.missing_variables) + "."
            )
        ready = not table.missing_variables and batch.matched_file_count <= MAX_PARSE_FILES
        if ready:
            diagnostics.append("The sampled configuration is ready for a full parse.")
        return ParserPlaygroundResult(
            batch.matched_file_count,
            table.source_paths,
            tuple(column.name for column in table.schema.columns),
            table.rows,
            table.missing_variables,
            tuple(diagnostics),
            ready,
        )
