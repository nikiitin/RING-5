"""Unit tests for TypeMapper, ScannerService, ParseService, and PathService.

These are mid-layer modules that sit between raw parsing and the
ApplicationAPI facade.
"""

from src.core.models.source_evidence import ResolvedSourceKind


from collections.abc import Generator
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock, patch
import os

import pytest

from src.core.models.parsing_models import SourceInstance

from src.core.common.stat_config_codec import StatConfigCodec

from src.core.models.parsing_models import ScanFileResult, ScannedVariable, StatConfig
from src.core.models.parsing_models import StatParamValue
from src.core.services.data_services.path_service import PathService
from src.parsing.gem5.types.type_mapper import TypeMapper
from src.parsing.gem5.impl.source_bindings import resolve_sources

# TypeMapper


class TestTypeMapper:
    """Tests for TypeMapper — stat type normalization and creation."""

    def test_create_stat_scalar(self) -> None:
        config = StatConfig(name="ipc", type="scalar", params={"source_type": "scalar"})
        stat = TypeMapper.create_stat(resolve_sources([config], []).accumulators[0])
        assert stat is not None

    def test_create_stat_from_dict(self) -> None:
        config = cast(dict[str, StatParamValue], {"name": "ipc", "type": "scalar"})
        with pytest.raises(TypeError, match="AccumulatorSpec"):
            TypeMapper.create_stat(config)  # type: ignore[arg-type]

    def test_create_stat_vector_with_entries(self) -> None:
        config = StatConfig(
            name="dcache.hits",
            type="vector",
            params={"source_type": "vector", "entries": ["0", "1", "2"]},
        )
        stat = TypeMapper.create_stat(resolve_sources([config], []).accumulators[0])
        assert stat is not None

    def test_create_stat_distribution(self) -> None:
        config = StatConfig(
            name="latency",
            type="distribution",
            params={"source_type": "distribution", "minimum": 0, "maximum": 200},
        )
        stat = TypeMapper.create_stat(resolve_sources([config], []).accumulators[0])
        assert stat is not None

    def test_create_stat_histogram(self) -> None:
        config = StatConfig(
            name="mem_ctrl.readLatency",
            type="histogram",
            params={
                "source_type": "histogram",
                "bins": 5,
                "max_range": 200.0,
                "entries": ["0-39", "40-79", "80-119", "120-159", "160-199"],
            },
        )
        stat = TypeMapper.create_stat(resolve_sources([config], []).accumulators[0])
        assert stat is not None

    def test_create_stat_configuration(self) -> None:
        config = StatConfig(
            name="benchmark_name", type="configuration", params={"source_type": "configuration"}
        )
        stat = TypeMapper.create_stat(resolve_sources([config], []).accumulators[0])
        assert stat is not None

    def test_create_stat_missing_type_raises(self) -> None:
        with pytest.raises(ValueError, match="type"):
            StatConfigCodec.from_draft({"name": "x"})

    def test_create_stat_empty_type_raises(self) -> None:
        with pytest.raises(ValueError, match="type"):
            StatConfigCodec.from_draft({"name": "x", "type": ""})


# ScannerService


class TestScannerService:
    """Tests for ScannerService — async scan orchestration."""

    def test_submit_scan_nonexistent_raises(self) -> None:
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ScannerService

        with pytest.raises(FileNotFoundError):
            ScannerService.submit_scan_async("/nonexistent/path")

    def test_submit_scan_no_files_raises(self, tmp_path: Path) -> None:
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ScannerService

        with pytest.raises(FileNotFoundError, match="No files matching"):
            ScannerService.submit_scan_async(str(tmp_path), "stats.txt")

    def test_submit_scan_zero_preserves_exhaustive_discovery_contract(self, tmp_path: Path) -> None:
        # [test->req~ring5.ingestion.scan-limits~1]
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ScannerService

        paths = [str(tmp_path / f"run-{index:03d}" / "stats.txt") for index in range(257)]
        with (
            patch("src.parsing.gem5.impl.gem5_parser.find_stats_files", return_value=paths) as find,
            patch("src.parsing.gem5.impl.gem5_parser.WorkPool") as pool,
        ):
            pool.get_instance.return_value.submit_many.return_value = [MagicMock()] * 257
            futures = ScannerService.submit_scan_async(str(tmp_path), "stats.txt", limit=0)

        assert len(futures) == 257
        assert find.call_args.kwargs["limit"] == 0

    def test_submit_scan_rejects_limit_above_global_ceiling(self, tmp_path: Path) -> None:
        # [test->req~ring5.ingestion.scan-limits~1]
        from src.core.common.security_limits import MAX_DISCOVERED_FILES
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ScannerService

        with pytest.raises(ValueError, match="global safety ceiling"):
            ScannerService.submit_scan_async(
                str(tmp_path), "stats.txt", limit=MAX_DISCOVERED_FILES + 1
            )

    def test_aggregate_empty_results(self) -> None:
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ScannerService

        result = ScannerService.aggregate_scan_results([])
        assert result.variables == []
        assert result.failures == []
        assert result.scanned_files == 0
        assert result.successful_files == 0
        assert result.complete

    def test_aggregate_single_file(self) -> None:
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ScannerService

        var = ScannedVariable(
            name="simTicks",
            type="scalar",
            entries=[],
            source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
            instances=(SourceInstance("simTicks", ()),),
        )
        result = ScannerService.aggregate_scan_results([ScanFileResult("f0", [var])])
        assert len(result.variables) >= 1
        names = [v.name for v in result.variables]
        assert "simTicks" in names
        assert result.scanned_files == 1
        assert result.successful_files == 1
        assert result.complete

    def test_aggregate_preserves_partial_scan_metadata(self) -> None:
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ScannerService

        var = ScannedVariable(
            name="simTicks",
            type="scalar",
            entries=[],
            source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
            instances=(SourceInstance("simTicks", ()),),
        )
        result = ScannerService.aggregate_scan_results(
            [
                ScanFileResult("good", [var]),
                ScanFileResult("oversized", error="line limit exceeded"),
            ]
        )

        assert result.scanned_files == 2
        assert result.successful_files == 1
        assert not result.complete
        assert result.failures[0].file_path == "oversized"

    def test_aggregate_merges_vector_entries(self) -> None:
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ScannerService

        v1 = ScannedVariable(
            name="cpu.hits",
            type="vector",
            entries=["0", "1"],
            source_evidence=ResolvedSourceKind("vector", "backend_metadata"),
            instances=(SourceInstance("cpu.hits", ()),),
        )
        v2 = ScannedVariable(
            name="cpu.hits",
            type="vector",
            entries=["1", "2"],
            source_evidence=ResolvedSourceKind("vector", "backend_metadata"),
            instances=(SourceInstance("cpu.hits", ()),),
        )
        result = ScannerService.aggregate_scan_results(
            [ScanFileResult("f0", [v1]), ScanFileResult("f1", [v2])]
        )
        hit_var = next(v for v in result.variables if v.name == "cpu.hits")
        assert set(hit_var.entries) == {"0", "1", "2"}

    def test_aggregate_merges_distribution_observed_entries(self) -> None:
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ScannerService

        d1 = ScannedVariable(
            name="latency",
            type="distribution",
            entries=["10", "100"],
            source_evidence=ResolvedSourceKind("distribution", "backend_metadata"),
            instances=(SourceInstance("latency", ()),),
        )
        d2 = ScannedVariable(
            name="latency",
            type="distribution",
            entries=["5", "200"],
            source_evidence=ResolvedSourceKind("distribution", "backend_metadata"),
            instances=(SourceInstance("latency", ()),),
        )
        result = ScannerService.aggregate_scan_results(
            [ScanFileResult("f0", [d1]), ScanFileResult("f1", [d2])]
        )
        lat_var = next(v for v in result.variables if v.name == "latency")
        assert set(lat_var.entries) == {"5", "10", "100", "200"}
        assert "minimum" not in lat_var.to_dict() and "maximum" not in lat_var.to_dict()

    def test_merge_variable_model_input(self) -> None:
        """_merge_variable accepts ScannedVariable models."""
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ScannerService

        registry: dict[str, ScannedVariable] = {}
        var = ScannedVariable(
            name="ipc",
            type="scalar",
            entries=[],
            source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
            instances=(SourceInstance("ipc", ()),),
        )
        ScannerService._merge_variable(registry, var)
        assert "ipc" in registry
        assert registry["ipc"].type == "scalar"


# PathService


class TestPathService:
    """Tests for PathService — centralized path resolution."""

    @pytest.fixture(autouse=True)
    def reset_path_caches(self) -> Generator[None, None, None]:
        """Reset PathService class-level caches for test isolation."""
        with patch.dict(os.environ):
            os.environ.pop("RING5_DATA_DIR", None)
            PathService.reset_caches()
            yield
            PathService.reset_caches()

    def test_get_root_dir_returns_path(self) -> None:
        root = PathService.get_root_dir()
        assert isinstance(root, Path)
        assert root.exists()

    def test_get_data_dir_creates_directory(self, tmp_path: Path) -> None:
        # [test->req~ring5.workspace.application-data-directory~1]
        with patch.object(PathService, "get_root_dir", return_value=tmp_path):
            data_dir = PathService.get_data_dir()
            assert data_dir.exists()
            assert data_dir == tmp_path / ".ring5"

    def test_get_portfolios_dir_creates_directory(self, tmp_path: Path) -> None:
        with patch.object(PathService, "get_root_dir", return_value=tmp_path):
            portfolios_dir = PathService.get_portfolios_dir()
            assert portfolios_dir.exists()
            assert portfolios_dir == tmp_path / ".ring5" / "portfolios"

    def test_get_portfolio_revisions_dir_creates_directory(self, tmp_path: Path) -> None:
        with patch.object(PathService, "get_root_dir", return_value=tmp_path):
            revisions_dir = PathService.get_portfolio_revisions_dir()
            assert revisions_dir.exists()
            assert revisions_dir == tmp_path / ".ring5" / "portfolio_revisions"

    def test_get_dataset_snapshots_dir_creates_directory(self, tmp_path: Path) -> None:
        # [test->req~ring5.data.dataset-snapshots~1]
        with patch.object(PathService, "get_root_dir", return_value=tmp_path):
            snapshots_dir = PathService.get_dataset_snapshots_dir()
            assert snapshots_dir.exists()
            assert snapshots_dir == tmp_path / ".ring5" / "dataset_snapshots"

    def test_directories_are_idempotent(self, tmp_path: Path) -> None:
        """Calling get_*_dir twice doesn't fail."""
        with patch.object(PathService, "get_root_dir", return_value=tmp_path):
            PathService.get_data_dir()
            PathService.get_data_dir()  # Second call should not raise


class TestObservedEntryMerge:
    """An observed zero label remains data through either merge order."""

    def test_zero_label_survives_merge_with_empty_entries(self) -> None:
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        registry: dict = {}
        no_range = ScannedVariable(
            name="d",
            type="distribution",
            source_evidence=ResolvedSourceKind("distribution", "backend_metadata"),
            instances=(SourceInstance("d", ()),),
        )
        with_zero_min = ScannedVariable(
            name="d",
            type="distribution",
            entries=["0", "5"],
            source_evidence=ResolvedSourceKind("distribution", "backend_metadata"),
            instances=(SourceInstance("d", ()),),
        )

        # Order A: None-range first, 0.0 arrives as the incoming side
        Gem5Parser._merge_variable(registry, no_range)
        Gem5Parser._merge_variable(registry, with_zero_min)
        assert registry["d"].entries == ["0", "5"]
        assert "minimum" not in registry["d"].to_dict()

        # Order B: reversed
        registry.clear()
        Gem5Parser._merge_variable(registry, with_zero_min)
        Gem5Parser._merge_variable(registry, no_range)
        assert registry["d"].entries == ["0", "5"]
        assert "minimum" not in registry["d"].to_dict()
