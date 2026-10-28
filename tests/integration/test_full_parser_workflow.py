"""
Integration Test: Full Parser Workflow

Tests the complete end-to-end parsing workflow:
1. Scan stats files for available variables
2. Select variables to parse
3. Parse variables using worker pool
4. Construct final CSV
5. Load CSV into dataframe
6. Verify data integrity

This test validates the entire parsing pipeline from raw gem5 stats to usable dataframe.
"""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from src.core.application_api import ApplicationAPI
from src.core.common.parsed_output import ParsedOutputIO
from src.core.models.parsing_models import StatConfig
from src.core.services.data_services.csv_pool_service import CsvPoolService
from src.parsing.gem5.impl.gem5_parser import Gem5Parser


@pytest.fixture
def facade() -> Generator[ApplicationAPI, None, None]:
    """Release the facade's owned parser work after each workflow."""
    api = ApplicationAPI()
    try:
        yield api
    finally:
        api.close(wait=True)


@pytest.fixture
def sample_stats_dir(tmp_path: Path) -> Path:
    """
    Create a sample gem5 stats directory with multiple stats files.
    """
    stats_dir = tmp_path / "gem5_output"
    stats_dir.mkdir()

    # Create multiple benchmark stats files
    benchmarks = ["mcf", "omnetpp", "xalancbmk"]

    for bench in benchmarks:
        bench_dir = stats_dir / bench / "baseline"
        bench_dir.mkdir(parents=True)

        stats_file = bench_dir / "stats.txt"
        stats_content = """
---------- Begin Simulation Statistics ----------
simSeconds                                   0.100000                       # Number of seconds simulated  # noqa: E501
system.cpu.numCycles                          100000                       # number of cpu cycles simulated  # noqa: E501
system.cpu.ipc                                  1.50                       # IPC: instructions per cycle  # noqa: E501
system.cpu.dcache.overall_miss_rate::total     0.0234                       # miss rate for overall accesses  # noqa: E501
system.cpu.icache.overall_miss_rate::total     0.0156                       # miss rate for overall accesses  # noqa: E501
---------- End Simulation Statistics   ----------
"""
        stats_file.write_text(stats_content)

    return stats_dir


class TestFullParserWorkflow:
    """Integration tests for complete parsing workflow."""

    def test_scan_select_parse_load_workflow(self, sample_stats_dir: Path) -> None:
        """
        Test complete workflow from scanning to loading data.

        Validates:
        1. Scanner discovers variables correctly
        2. Parser processes variables asynchronously
        3. CSV construction aggregates results
        4. Data loading produces correct dataframe
        """
        # [test->req~ring5.ingestion.parse-output-provenance~1]
        # Step 1: Scan for available variables
        scan_futures = Gem5Parser.submit_scan_async(
            stats_path=str(sample_stats_dir), stats_pattern="stats.txt", limit=10
        )

        scan_results = [f.result() for f in scan_futures]
        scanned_vars = Gem5Parser.aggregate_scan_results(scan_results).variables

        # Verify scanning found expected variables
        assert len(scanned_vars) > 0
        var_names = [v.name for v in scanned_vars]
        assert "system.cpu.ipc" in var_names
        assert "system.cpu.numCycles" in var_names

        # Step 2: Select variables to parse
        variables = [
            StatConfig(name="system.cpu.ipc", type="scalar", params={"source_type": "scalar"}),
            StatConfig(
                name="system.cpu.numCycles", type="scalar", params={"source_type": "scalar"}
            ),
        ]

        # Step 3: Parse variables asynchronously
        with tempfile.TemporaryDirectory() as output_dir:
            batch = Gem5Parser.submit_parse_async(
                stats_path=str(sample_stats_dir),
                stats_pattern="stats.txt",
                variables=variables,
                output_dir=output_dir,
            )

            parse_results = [f.result() for f in batch.futures]

            # Step 4: Construct final CSV
            parsed_output = Gem5Parser.finalize_parsing(batch, parse_results)
            csv_path = parsed_output.csv_path

            assert csv_path is not None
            assert Path(csv_path).exists()

            # Step 5: Load CSV into dataframe
            data = ParsedOutputIO.to_frame(parsed_output)

            # Step 6: Verify data integrity
            assert not data.empty
            # Note: Column names may be normalized by parser (e.g., dots removed)
            # Check that IPC-like column exists
            ipc_cols = [col for col in data.columns if "ipc" in col.lower()]
            assert len(ipc_cols) > 0, f"No IPC column found in {data.columns.tolist()}"

            # Verify we have expected number of rows
            assert len(data) >= 3  # At least 3 benchmarks

    def test_facade_integration_workflow(
        self,
        sample_stats_dir: Path,
        facade: ApplicationAPI,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Test workflow using ApplicationAPI (user-facing API).

        This simulates the actual user workflow through the Streamlit UI.
        """
        pool = tmp_path / "recent"
        pool.mkdir()
        monkeypatch.setattr(CsvPoolService, "_pool_dir", pool)

        # Step 1: Find stats files
        stats_files = facade.find_stats_files(str(sample_stats_dir), "stats.txt")
        assert len(stats_files) == 3

        # Step 2: Scan for variables
        scan_futures = facade.submit_scan_async(
            stats_path=str(sample_stats_dir), stats_pattern="stats.txt", limit=5
        )

        scan_results = [f.result() for f in scan_futures]
        scanned_vars = facade.finalize_scan(scan_results).variables

        assert len(scanned_vars) > 0

        # Step 3: Parse selected variables
        variables = [
            StatConfig(name="system.cpu.ipc", type="scalar", params={"source_type": "scalar"}),
        ]

        with tempfile.TemporaryDirectory() as output_dir:
            batch = facade.submit_parse_async(
                stats_path=str(sample_stats_dir),
                stats_pattern="stats.txt",
                variables=variables,
                output_dir=output_dir,
            )

            parse_results = [f.result() for f in batch.futures]
            parsed_output = facade.finalize_parsing(batch, parse_results)
            csv_path = parsed_output.csv_path

            assert csv_path is not None

            # Step 4: Load into CSV pool
            pooled_path = facade.data_services.add_to_csv_pool(csv_path)
            assert Path(pooled_path).parent == pool

            # Step 5: Retrieve from pool (load directly from file)
            loaded_data = facade.data_services.load_csv_file(pooled_path)

            assert loaded_data is not None
            assert not loaded_data.empty
            # Column names may be normalized - check for IPC-like column
            ipc_cols = [col for col in loaded_data.columns if "ipc" in col.lower()]
            assert len(ipc_cols) > 0

    def test_error_handling_in_workflow(self, tmp_path: Path) -> None:
        """
        Test error handling at various stages of the workflow.
        """
        # Test with non-existent stats directory
        with pytest.raises((FileNotFoundError, ValueError)):
            Gem5Parser.submit_scan_async(
                stats_path="/nonexistent/path", stats_pattern="stats.txt", limit=10
            )

        (tmp_path / "stats.txt").write_text("invalid.var 1\n", encoding="utf-8")
        invalid_variables = [
            StatConfig(
                name="invalid.var", type="unknown_type", params={"source_type": "unknown_type"}
            )
        ]
        with pytest.raises(ValueError, match="Unknown stat type: 'unknown_type'"):
            Gem5Parser.submit_parse_async(
                stats_path=str(tmp_path),
                stats_pattern="stats.txt",
                variables=invalid_variables,
                output_dir=str(tmp_path / "output"),
                scanned_vars=[],
            )
