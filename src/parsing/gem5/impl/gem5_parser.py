"""gem5 parser backend for parallel scanning, parsing, and CSV assembly."""

import logging
import os
from concurrent.futures import Future
from dataclasses import replace
from pathlib import Path

from src.core.common.input_identity import fingerprint_inputs
from src.core.common.source_context_codec import encode_source_json
from src.core.models.source_evidence import ResolvedSourceKind, intersect_source_kind_evidence
from src.core.models.parsed_output_models import ParsedFileResult, ParsedOutput
from src.core.common.parsed_output import ParsedOutputIO
from src.core.common.utils import normalize_user_path
from src.core.common.security_limits import (
    MAX_DISCOVERED_FILES,
    MAX_PARSE_RESULT_BYTES,
    MAX_PARSE_FILES,
    MAX_PARSE_FILE_BYTES,
    MAX_PARSE_TOTAL_BYTES,
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
from src.parsing.gem5.impl.source_bindings import SourcePlan, resolve_sources
from src.parsing.gem5.impl.strategies.file_parser_strategy import FileParserStrategy
from src.parsing.gem5.impl.scanning.pattern_aggregator import PatternAggregator
from src.parsing.gem5.impl.strategies.factory import StrategyFactory
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
    def _select_files(
        stats_path: str,
        stats_pattern: str,
        *,
        file_paths: list[str] | None = None,
        preview_limit: int | None = None,
    ) -> tuple[int, tuple[str, ...]]:
        """Discover once and admit only the actual source selection before planning."""
        discovered = find_stats_files(stats_path, stats_pattern, sort=True, raise_if_empty=True)
        if file_paths is not None:
            requested = {str(Path(path).resolve(strict=True)) for path in file_paths}
            available = {str(Path(path).resolve(strict=True)) for path in discovered}
            unknown = requested - available
            if unknown:
                raise ValueError(
                    "PARSER: selection contains files outside the discovered batch: "
                    + ", ".join(sorted(unknown))
                )
            files = tuple(sorted(requested))
        else:
            files = (
                tuple(
                    sorted(
                        {
                            str(Path(path).resolve(strict=True))
                            for path in discovered[:preview_limit]
                        }
                    )
                )
                if preview_limit is not None
                else tuple(discovered)
            )
        if not files:
            raise FileNotFoundError("PARSER: the selected batch contains no statistics sources.")
        if len(files) > MAX_PARSE_FILES:
            raise RuntimeError(
                f"PARSER: {len(files)} files exceed the {MAX_PARSE_FILES}-file parse limit."
            )
        total_bytes = 0
        for file_path in files:
            file_size = os.path.getsize(file_path)
            if file_size > MAX_PARSE_FILE_BYTES:
                raise RuntimeError(f"PARSER: input exceeds the per-file byte limit: {file_path}")
            total_bytes += file_size
            if total_bytes > MAX_PARSE_TOTAL_BYTES:
                raise RuntimeError("PARSER: selected inputs exceed the aggregate byte limit.")
        return len(discovered), files

    @staticmethod
    def _prepare_source_plan(
        variables: list[StatConfig],
        strategy_type: str,
        scanned_vars: list[ScannedVariable] | None,
        selected_files: tuple[str, ...],
    ) -> tuple[SourcePlan, FileParserStrategy]:
        """Admit all selected physical columns and declarations before templates or cache."""
        strategy = StrategyFactory.create(strategy_type)
        plan = resolve_sources(
            variables,
            scanned_vars,
            file_count=len(selected_files),
            metadata_columns=strategy.metadata_columns,
        )
        return plan, strategy

    @staticmethod
    def _build_work_items(
        files: tuple[str, ...],
        plan: SourcePlan,
        strategy: FileParserStrategy,
    ) -> tuple[ParseWorkItem, ...]:
        """Build owned tasks using the already selected sources and admitted plan."""
        work = tuple(strategy.get_work_items(files, plan))
        if not work:
            raise FileNotFoundError("PARSER: the strategy generated no work for selected sources.")
        if tuple(item.source_path for item in work) != files:
            raise ValueError("PARSER: strategy work must preserve the exact selected source tuple.")
        return work

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
        _, files = Gem5Parser._select_files(stats_path, stats_pattern, file_paths=file_paths)
        plan, strategy = Gem5Parser._prepare_source_plan(
            variables, strategy_type, scanned_vars, files
        )
        var_names = tuple(spec.output_name for spec in plan.accumulators)
        work = Gem5Parser._build_work_items(files, plan, strategy)
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
        _, files = Gem5Parser._select_files(stats_path, stats_pattern)
        plan, strategy = Gem5Parser._prepare_source_plan(
            variables, strategy_type, scanned_vars, files
        )
        fingerprints = fingerprint_inputs(list(files), strategy_type)
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
        reuse = load_cache(
            resolved_cache,
            config_hash,
            fingerprints,
            layout_declarations={spec.output_name: spec.layout for spec in plan.accumulators},
        )
        cached_results = reuse.results
        reused_paths = {result.source_path for result in cached_results}
        changed_files = tuple(path for path, _ in fingerprints if path not in reused_paths)
        var_names = tuple(spec.output_name for spec in plan.accumulators)
        work: tuple[ParseWorkItem, ...] = ()
        if changed_files:
            work = Gem5Parser._build_work_items(changed_files, plan, strategy)
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
        matched_count, sampled_files = Gem5Parser._select_files(
            stats_path,
            stats_pattern,
            preview_limit=MAX_PARSER_PLAYGROUND_FILES,
        )
        plan, strategy = Gem5Parser._prepare_source_plan(
            variables,
            strategy_type,
            scanned_vars,
            sampled_files,
        )
        var_names = tuple(spec.output_name for spec in plan.accumulators)
        work = Gem5Parser._build_work_items(sampled_files, plan, strategy)
        sampled_files = tuple(item.source_path for item in work)
        admission = ResultAdmission(sampled_files)
        futures = Gem5Parser._submit_admitted_work(work, admission)
        diagnostics: list[str] = []
        if matched_count > len(sampled_files):
            diagnostics.append(
                f"Previewed {len(sampled_files)} of {matched_count} matching files "
                "in lexical order."
            )
        if matched_count > MAX_PARSE_FILES:
            diagnostics.append(
                f"A full parse would exceed the {MAX_PARSE_FILES}-file safety limit."
            )
        return ParserPlaygroundBatchResult(
            futures=futures,
            var_names=var_names,
            output_dir=str(Path(output_dir).expanduser().resolve()),
            strategy_type=strategy_type,
            matched_file_count=matched_count,
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

        Valid sources are retained even from partially rejected files. Conflicting
        sources are excluded while per-file failures remain visible to the caller.

        Args:
            results: Per-file ``ScanFileResult`` objects from the workers.

        Returns:
            ``ScanResult`` with the merged variables and the list of failures.
        """
        # [impl->req~ring5.ingestion.variable-scan~2]
        failures = {result.file_path: result for result in results if not result.ok}
        registry: dict[str, ScannedVariable] = {}
        owners: dict[str, set[str]] = {}
        rejected: set[str] = set()
        sizes: dict[str, int] = {}
        catalog_bytes = 2

        def reject(paths: set[str], name: str) -> None:
            for path in paths:
                previous = failures.get(path)
                message = f"Source {name!r} has contradictory scan observations."
                if previous is not None and previous.error:
                    message = f"{previous.error}; {message}"[:1000]
                failures[path] = ScanFileResult(path, error=message)

        for result in results:
            for variable in result.variables:
                name = variable.name
                if name in rejected:
                    reject({result.file_path}, name)
                    continue
                owners.setdefault(name, set()).add(result.file_path)
                try:
                    Gem5Parser._merge_variable(registry, variable)
                except ValueError as exc:
                    if type(exc) is not ValueError:
                        raise
                    rejected.add(name)
                    registry.pop(name, None)
                    reject(owners[name], name)
                    removed = sizes.pop(name, 0)
                    catalog_bytes -= removed + (1 if removed and sizes else 0)
                else:
                    previous_size = sizes.get(name, 0)
                    size = len(
                        encode_source_json(
                            registry[name].to_dict(), byte_limit=MAX_PARSE_RESULT_BYTES
                        ).encode("utf-8")
                    )
                    candidate_bytes = catalog_bytes - previous_size + size
                    if not previous_size and sizes:
                        candidate_bytes += 1
                    if candidate_bytes > MAX_PARSE_RESULT_BYTES:
                        raise ValueError("Merged scanner catalog exceeds its byte budget.")
                    catalog_bytes = candidate_bytes
                    sizes[name] = size
        aggregated = PatternAggregator.aggregate_patterns(
            sorted(registry.values(), key=lambda v: v.name)
        )
        return ScanResult(aggregated, list(failures.values()), len(results))

    @staticmethod
    def _merge_variable(registry: dict[str, ScannedVariable], var: ScannedVariable) -> None:
        """Intersect source contracts while retaining actual printed entry labels."""
        existing = registry.get(var.name)
        if existing is None:
            registry[var.name] = var
            return
        if existing.instances != var.instances:
            raise ValueError("Scanned source instances disagree.")
        evidence = intersect_source_kind_evidence(existing.source_evidence, var.source_evidence)
        suggestion = evidence.kind if type(evidence) is ResolvedSourceKind else None
        registry[var.name] = replace(
            existing,
            type=suggestion,
            source_evidence=evidence,
            entries=sorted(set(existing.entries) | set(var.entries)),
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
