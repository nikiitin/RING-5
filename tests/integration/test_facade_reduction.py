"""Async facade reductions preserve spatial and temporal observations in CSV."""

import csv
import os
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from src.core.application_api import ApplicationAPI
from src.core.common.parsed_output import ParsedOutputIO
from src.core.models.parsing_models import StatConfig
from src.core.models.source_evidence import AmbiguousSourceKind

pytestmark = pytest.mark.xdist_group("perl_pool")


class TestFacadeReduction:
    @pytest.fixture
    def facade(self) -> Generator[ApplicationAPI, None, None]:
        """Release the scans and jobs owned by each facade instance."""
        api = ApplicationAPI()
        try:
            yield api
        finally:
            api.close()

    @pytest.fixture
    def temp_dirs(self, tmp_path: Any) -> Any:

        # Create temp dirs for stats and output
        stats_dir = tmp_path / "stats"
        output_dir = tmp_path / "output"
        stats_dir.mkdir()
        output_dir.mkdir()

        # Create dummy stats files
        # File 1: cpu0=10, cpu1=20
        # File 2: cpu0=10, cpu1=30

        stats_file = stats_dir / "stats.txt"
        with open(stats_file, "w") as f:
            f.write("---------- Begin Simulation Statistics ----------\n")
            f.write(
                "system.cpu0.ipc                                      10.000000                       # IPC\n"  # noqa: E501
            )
            f.write(
                "system.cpu1.ipc                                      20.000000                       # IPC\n"  # noqa: E501
            )
            f.write("---------- End Simulation Statistics   ----------\n")

        stats_bak = stats_dir / "stats.txt.bak"
        with open(stats_bak, "w") as f:
            f.write("---------- Begin Simulation Statistics ----------\n")
            f.write(
                "system.cpu0.ipc                                      10.000000                       # IPC\n"  # noqa: E501
            )
            f.write(
                "system.cpu1.ipc                                      30.000000                       # IPC\n"  # noqa: E501
            )
            f.write("---------- End Simulation Statistics   ----------\n")

        return str(stats_dir), str(output_dir)

    def test_reduction_end_to_end(self, facade: Any, temp_dirs: Any) -> None:

        stats_path, output_dir = temp_dirs

        # Define variable with Regex Pattern
        variables = [
            {"name": "system.cpu\\d+.ipc", "type": "scalar", "params": {"source_type": "scalar"}}
        ]

        # Scan the concrete source records before compiling numeric bindings
        scan_futures = facade.submit_scan_async(stats_path, "stats.txt*", limit=10)

        # Wait for scan completion
        scan_results = [future.result(timeout=5) for future in scan_futures]

        scanned_vars = facade.finalize_scan(scan_results).variables

        # Run Facade Parse
        batch = facade.submit_parse_async(
            stats_path=stats_path,
            stats_pattern="stats.txt*",
            variables=facade.compile_parse_variables(variables),
            output_dir=output_dir,
            scanned_vars=scanned_vars,
        )

        # Wait for parsing
        parse_results = [future.result(timeout=10) for future in batch.futures]

        parsed_output = facade.finalize_parsing(batch, parse_results)
        csv_path = parsed_output.csv_path

        assert csv_path is not None
        assert os.path.exists(csv_path)

        # Verify Results
        # Parser outputs CSV.
        df = ParsedOutputIO.to_frame(parsed_output)

        # Expectation:
        # Col "system.cpu\d+.ipc" should exist
        # Row 1 (stats.txt): (10+20)/2 = 15
        # Row 2 (stats.txt.bak): (10+30)/2 = 20
        # Note: Order of rows depends on file system order, but values should be 15 and 20.

        target_col = "system.cpu\\d+.ipc"
        assert target_col in df.columns

        values = sorted(df[target_col].tolist())
        assert values == [15.0, 20.0]

    def test_vector_reduction(self, facade: ApplicationAPI, tmp_path: Path) -> None:
        """Average genuine vector entries across CPUs/dumps without filling missing data."""
        # [test->req~ring5.ingestion.vector~1]
        stats_dir = tmp_path / "stats"
        output_dir = tmp_path / "output"
        stats_dir.mkdir()
        output_dir.mkdir()

        def dump(before: int, after: int, values: tuple[int | None, int | None] | None) -> str:
            lines = ["---------- Begin Simulation Statistics ----------", f"before {before}"]
            if values is not None:
                for cpu, value in enumerate(values):
                    lines.append(f"system.cpu{cpu}.counts::0 0")
                    if value is not None:
                        lines.append(f"system.cpu{cpu}.counts::1 {value}")
            lines.extend([f"after {after}", "---------- End Simulation Statistics ----------"])
            return "\n".join(lines) + "\n"

        files = {
            "stats.txt": dump(100, 1000, (2, 6)) + dump(300, 1400, (10, 14)),
            "stats.txt.partial": dump(400, 2000, (22, 26)) + dump(600, 2400, (30, None)),
            "stats.txt.absent": dump(700, 3000, None) + dump(900, 3400, None),
        }
        for name, text in files.items():
            (stats_dir / name).write_text(text, encoding="utf-8")

        scanned = facade.finalize_scan(
            [
                future.result(timeout=30)
                for future in facade.submit_scan_async(str(stats_dir), "stats.txt*")
            ]
        )
        assert scanned.failures == []
        vector = next(
            variable for variable in scanned.variables if variable.name.endswith(".counts")
        )
        assert vector.name == r"system.cpu\d+.counts"
        # Coincident entry/CPU IDs must not turn a genuine vector into scalar-instance columns.
        assert vector.type is None
        assert vector.source_evidence == AmbiguousSourceKind(("distribution", "vector"))
        assert vector.entries == ["0", "1"]
        assert [(record.source_name, record.indices) for record in vector.instances] == [
            ("system.cpu0.counts", ("0",)),
            ("system.cpu1.counts", ("1",)),
        ]

        batch = facade.submit_parse_async(
            str(stats_dir),
            "stats.txt*",
            [
                StatConfig("before", "scalar", repeat=2, params={"source_type": "scalar"}),
                StatConfig(
                    "V",
                    "vector",
                    repeat=2,
                    source_name=vector.name,
                    is_regex=True,
                    params={"entries": vector.entries, "source_type": "vector"},
                ),
                StatConfig("after", "scalar", repeat=2, params={"source_type": "scalar"}),
            ],
            str(output_dir),
            scanned_vars=scanned.variables,
        )
        assert len(batch.futures) == len(files)
        parsed_output = facade.finalize_parsing(
            batch, [future.result(timeout=30) for future in batch.futures]
        )
        csv_path = parsed_output.csv_path
        assert csv_path is not None
        with Path(csv_path).open(encoding="utf-8", newline="") as stream:
            header, *rows = csv.reader(stream)
        assert header == ["before", "V..0", "V..1", "after"]
        assert sorted(rows, key=lambda row: float(row[0])) == [
            ["200.0", "0.0", "8.0", "1200.0"],
            ["500.0", "0.0", "NaN", "2200.0"],
            ["800.0", "NaN", "NaN", "3200.0"],
        ]
