"""Executable external-backend example using only the public ring5 SDK and stdlib."""

from __future__ import annotations

import hashlib
import json
import sys
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

import ring5


class ExampleParser:
    """Own asynchronous commands and publish the single current typed result format."""

    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=2)
        self.scans = 0

    def close(self) -> None:
        """Drain only this backend's owned executor."""
        self._executor.shutdown(wait=True)

    @staticmethod
    def _parse(path: str, variables: list[ring5.StatConfig]) -> ring5.ParsedFileResult:
        variables_out: list[ring5.ParsedVariableResult] = []
        for variable in variables:
            if variable.type == "configuration":
                fallback = variable.params["on_empty"]
                if not isinstance(fallback, str):
                    raise TypeError("Example configuration fallback requires text.")
                cell = ring5.ParsedCell(variable.name, "text", fallback)
                variables_out.append(
                    ring5.ParsedVariableResult(variable.name, "text", "scalar", (cell,))
                )
            else:
                value = float(Path(path).read_text(encoding="utf-8"))
                cell = ring5.ParsedCell(variable.name, "number", value)
                variables_out.append(
                    ring5.ParsedVariableResult(variable.name, "number", "scalar", (cell,))
                )
        return ring5.ParsedFileResult(path, tuple(variables_out))

    def submit_parse_async(
        self,
        stats_path: str,
        stats_pattern: str,
        variables: list[ring5.StatConfig],
        output_dir: str,
        strategy_type: str = "simple",
        scanned_vars: list[ring5.ScannedVariable] | None = None,
        *,
        file_paths: list[str] | None = None,
    ) -> ring5.ParseBatchResult:
        paths = tuple(
            file_paths
            if file_paths is not None
            else (str(path) for path in sorted(Path(stats_path).glob(stats_pattern)))
        )
        return ring5.ParseBatchResult(
            tuple(self._executor.submit(self._parse, path, variables) for path in paths),
            tuple(variable.name for variable in variables),
            paths,
            output_dir,
            strategy_type,
        )

    def finalize_parsing(
        self,
        batch: ring5.ParseBatchResult,
        results: list[ring5.ParsedFileResult],
        *,
        complete: bool = True,
    ) -> ring5.ParsedOutput:
        resolved = ring5.resolve_parsed_output(
            results, batch.var_names, batch.source_paths, complete=complete
        )
        return ring5.publish_parsed_output(resolved, Path(batch.output_dir) / "results.csv")

    def submit_incremental_parse_async(
        self,
        stats_path: str,
        stats_pattern: str,
        variables: list[ring5.StatConfig],
        output_dir: str,
        strategy_type: str = "simple",
        scanned_vars: list[ring5.ScannedVariable] | None = None,
        cache_path: str | None = None,
    ) -> ring5.IncrementalParseBatchResult:
        # This example declares every current input changed; a real cache owner may
        # supply unchanged typed records in cached_results under the same contract.
        batch = self.submit_parse_async(
            stats_path, stats_pattern, variables, output_dir, strategy_type, scanned_vars
        )
        return ring5.IncrementalParseBatchResult(
            futures=batch.futures,
            var_names=batch.var_names,
            output_dir=output_dir,
            strategy_type=strategy_type,
            cache_path=cache_path or str(Path(output_dir) / "cache.json"),
            configuration_hash=hashlib.sha256(b"example-current-config").hexdigest(),
            fingerprints=tuple(
                (path, hashlib.sha256(Path(path).read_bytes()).hexdigest())
                for path in batch.source_paths
            ),
            cached_results=(),
            changed_files=batch.source_paths,
            removed_files=(),
        )

    def finalize_incremental_parsing(
        self,
        batch: ring5.IncrementalParseBatchResult,
        results: list[ring5.ParsedFileResult],
        *,
        complete: bool = True,
    ) -> ring5.IncrementalParseResult:
        resolved = ring5.resolve_parsed_output(
            (*batch.cached_results, *results),
            batch.var_names,
            tuple(path for path, _ in batch.fingerprints),
            complete=complete,
        )
        output = ring5.publish_parsed_output(resolved, Path(batch.output_dir) / "results.csv")
        return ring5.IncrementalParseResult(
            output,
            len(results),
            len(batch.cached_results),
            len(batch.removed_files),
            batch.total_file_count,
        )

    def submit_parser_playground_async(
        self,
        stats_path: str,
        stats_pattern: str,
        variables: list[ring5.StatConfig],
        output_dir: str,
        strategy_type: str = "simple",
        scanned_vars: list[ring5.ScannedVariable] | None = None,
    ) -> ring5.ParserPlaygroundBatchResult:
        paths = [str(path) for path in sorted(Path(stats_path).glob(stats_pattern))]
        batch = self.submit_parse_async(
            stats_path,
            stats_pattern,
            variables,
            output_dir,
            strategy_type,
            scanned_vars,
            file_paths=paths[:3],
        )
        return ring5.ParserPlaygroundBatchResult(
            batch.futures,
            batch.var_names,
            output_dir,
            strategy_type,
            len(paths),
            batch.source_paths,
        )

    def finalize_parser_playground(
        self,
        batch: ring5.ParserPlaygroundBatchResult,
        results: list[ring5.ParsedFileResult],
    ) -> ring5.ParserPlaygroundResult:
        resolved = ring5.resolve_parsed_output(results, batch.var_names, batch.sampled_files)
        return ring5.ParserPlaygroundResult(
            batch.matched_file_count,
            resolved.source_paths,
            tuple(column.name for column in resolved.schema.columns),
            resolved.rows,
            resolved.missing_variables,
            (),
            not resolved.missing_variables,
        )

    def submit_scan_async(
        self,
        stats_path: str,
        stats_pattern: str = "stats.txt",
        limit: int = 5,
    ) -> list[Future[ring5.ScanFileResult]]:
        self.scans += 1
        paths = sorted(Path(stats_path).glob(stats_pattern))
        selected = paths if limit == 0 else paths[:limit]
        return [self._executor.submit(self._scan, str(path)) for path in selected]

    @staticmethod
    def _scan(path: str) -> ring5.ScanFileResult:
        return ring5.ScanFileResult(
            path,
            [
                ring5.ScannedVariable(
                    "value",
                    "scalar",
                    source_evidence=ring5.ResolvedSourceKind("scalar", "backend_metadata"),
                    instances=(ring5.SourceInstance("value", ()),),
                )
            ],
        )

    def aggregate_scan_results(self, results: list[ring5.ScanFileResult]) -> ring5.ScanResult:
        failures = [result for result in results if not result.ok]
        values = {variable.name: variable for result in results for variable in result.variables}
        return ring5.ScanResult(list(values.values()), failures, len(results))


def main(root: Path) -> None:
    """Exercise full, incremental, preview, partial and explicit-source replay paths."""
    inputs = root / "inputs"
    inputs.mkdir(parents=True)
    (inputs / "a.txt").write_text("1.25", encoding="utf-8")
    (inputs / "b.txt").write_text("2.5", encoding="utf-8")
    variables = [
        ring5.StatConfig("value", "scalar", params={"source_type": "scalar"}),
        ring5.StatConfig(
            "label", "configuration", params={"source_type": "configuration", "on_empty": "NA"}
        ),
    ]
    backend = ExampleParser()
    protocol: ring5.SimulationParser = backend
    try:
        with ring5.Session(parser=protocol) as session:
            result = session.parse(
                str(inputs), variables, pattern="*.txt", output_dir=str(root / "full")
            )
            assert session.load(result).rows() == [
                {"value": 1.25, "label": "NA"},
                {"value": 2.5, "label": "NA"},
            ]
            assert result.source_context.simulator is None
            try:
                session.capture_analysis_recipe("undeclared")
            except ring5.RecipeError:
                pass
            else:
                raise AssertionError("Undeclared backend was given inferred replay provenance")
            source = ring5.RecipeSource(
                "parser",
                str(inputs),
                pattern="*.txt",
                variables=tuple(
                    {
                        "name": v.name,
                        "type": v.type,
                        "repeat": v.repeat,
                        "params": v.params,
                        "statistics_only": v.statistics_only,
                        "is_regex": v.is_regex,
                        "keep_indices": v.keep_indices,
                        "source_name": v.source_name,
                    }
                    for v in variables
                ),
                simulator="example",
                scan_limit=None,
            )
            explicit = session.capture_analysis_recipe("explicit", source=source)
            before_scans = backend.scans
            session.run_analysis_recipe(explicit)
            assert backend.scans == before_scans
            incremental = session.parse(
                str(inputs),
                variables,
                pattern="*.txt",
                incremental=True,
                output_dir=str(root / "incremental"),
            )
            assert session.load(incremental).rows()[0]["label"] == "NA"
            preview = session.parser_playground_submit(
                str(inputs), variables, pattern="*.txt"
            ).finalize()
            assert preview.rows == ((1.25, "NA"), (2.5, "NA"))
            batch = backend.submit_parse_async(
                str(inputs), "*.txt", variables, str(root / "partial")
            )
            values = [future.result() for future in batch.futures]
            try:
                backend.finalize_parsing(batch, values[:1])
            except ring5.ParseError:
                pass
            else:
                raise AssertionError("Incomplete output passed complete finalization")
            partial = backend.finalize_parsing(batch, values[:1], complete=False)
            assert partial.schema == result.output.schema
            print(json.dumps({"rows": session.load(result).rows(), "partial": partial.csv_path}))
    finally:
        backend.close()


if __name__ == "__main__":
    main(Path(sys.argv[1]))
