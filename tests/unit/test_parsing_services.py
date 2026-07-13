"""Unit tests for TypeMapper, ScannerService, ParseService, and PathService.

These are mid-layer modules that sit between raw parsing and the
ApplicationAPI facade.
"""

from collections.abc import Generator
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest

from src.core.models import ScanFileResult, ScannedVariable, StatConfig
from src.core.models.parsing_models import StatParamValue
from src.core.services.data_services.path_service import PathService
from src.parsing.gem5.models import Gem5ScannedVariable
from src.parsing.gem5.types.type_mapper import TypeMapper

# ===================================================================
# TypeMapper
# ===================================================================


class TestTypeMapper:
    """Tests for TypeMapper — stat type normalization and creation."""

    def test_normalize_type_lowercase(self) -> None:
        assert TypeMapper.normalize_type("SCALAR") == "scalar"
        assert TypeMapper.normalize_type("Vector") == "vector"
        assert TypeMapper.normalize_type("Histogram") == "histogram"

    def test_normalize_type_already_lowercase(self) -> None:
        assert TypeMapper.normalize_type("scalar") == "scalar"

    def test_map_scan_result_normalizes_type(self) -> None:
        result = {"name": "ipc", "type": "SCALAR", "entries": []}
        mapped = TypeMapper.map_scan_result(result)
        assert mapped["type"] == "scalar"

    def test_map_scan_result_no_type_key(self) -> None:
        result = {"name": "ipc"}
        mapped = TypeMapper.map_scan_result(result)
        assert mapped["type"] == ""

    @pytest.mark.parametrize(
        "type_name,expected",
        [
            ("vector", True),
            ("distribution", True),
            ("histogram", True),
            ("scalar", False),
            ("configuration", False),
            ("VECTOR", True),
        ],
    )
    def test_is_entry_type(self, type_name: str, expected: bool) -> None:
        assert TypeMapper.is_entry_type(type_name) is expected

    def test_create_stat_scalar(self) -> None:
        config = StatConfig(name="ipc", type="scalar")
        stat = TypeMapper.create_stat(config)
        assert stat is not None

    def test_create_stat_from_dict(self) -> None:
        config = cast(dict[str, StatParamValue], {"name": "ipc", "type": "scalar"})
        stat = TypeMapper.create_stat(config)
        assert stat is not None

    def test_create_stat_vector_with_entries(self) -> None:
        config = StatConfig(
            name="dcache.hits",
            type="vector",
            params={"entries": ["0", "1", "2"]},
        )
        stat = TypeMapper.create_stat(config)
        assert stat is not None

    def test_create_stat_distribution(self) -> None:
        config = {
            "type": "distribution",
            "name": "latency",
            "minimum": 0,
            "maximum": 200,
        }
        stat = TypeMapper.create_stat(config)
        assert stat is not None

    def test_create_stat_histogram(self) -> None:
        config = {
            "type": "histogram",
            "name": "mem_ctrl.readLatency",
            "bins": 5,
            "max_range": 200.0,
            "entries": ["0-39", "40-79", "80-119", "120-159", "160-199"],
        }
        stat = TypeMapper.create_stat(config)
        assert stat is not None

    def test_create_stat_configuration(self) -> None:
        config = StatConfig(name="benchmark_name", type="configuration")
        stat = TypeMapper.create_stat(config)
        assert stat is not None

    def test_create_stat_missing_type_raises(self) -> None:
        with pytest.raises(ValueError, match="type"):
            TypeMapper.create_stat({"name": "x"})

    def test_create_stat_empty_type_raises(self) -> None:
        with pytest.raises(ValueError, match="type"):
            TypeMapper.create_stat({"name": "x", "type": ""})


# ===================================================================
# ScannerService
# ===================================================================


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

    def test_aggregate_empty_results(self) -> None:
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ScannerService

        result = ScannerService.aggregate_scan_results([])
        assert result.variables == []
        assert result.failures == []

    def test_aggregate_single_file(self) -> None:
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ScannerService

        var = ScannedVariable(name="simTicks", type="scalar", entries=[])
        result = ScannerService.aggregate_scan_results([ScanFileResult("f0", [var])])
        assert len(result.variables) >= 1
        names = [v.name for v in result.variables]
        assert "simTicks" in names

    def test_aggregate_merges_vector_entries(self) -> None:
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ScannerService

        v1 = ScannedVariable(name="cpu.hits", type="vector", entries=["0", "1"])
        v2 = ScannedVariable(name="cpu.hits", type="vector", entries=["1", "2"])
        result = ScannerService.aggregate_scan_results(
            [ScanFileResult("f0", [v1]), ScanFileResult("f1", [v2])]
        )
        hit_var = next(v for v in result.variables if v.name == "cpu.hits")
        assert set(hit_var.entries) == {"0", "1", "2"}

    def test_aggregate_merges_distribution_range(self) -> None:
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ScannerService

        d1 = Gem5ScannedVariable(
            name="latency", type="distribution", entries=[], minimum=10, maximum=100
        )
        d2 = Gem5ScannedVariable(
            name="latency", type="distribution", entries=[], minimum=5, maximum=200
        )
        result = ScannerService.aggregate_scan_results(
            [ScanFileResult("f0", [d1]), ScanFileResult("f1", [d2])]
        )
        lat_var = next(v for v in result.variables if v.name == "latency")
        assert lat_var.minimum == 5  # type: ignore
        assert lat_var.maximum == 200  # type: ignore

    def test_merge_variable_model_input(self) -> None:
        """_merge_variable accepts ScannedVariable models."""
        from src.core.models.parsing_models import ScannedVariable
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser as ScannerService

        registry: dict[str, ScannedVariable] = {}
        var = ScannedVariable(name="ipc", type="scalar", entries=[])
        ScannerService._merge_variable(registry, var)
        assert "ipc" in registry
        assert registry["ipc"].type == "scalar"


# ===================================================================
# PathService
# ===================================================================


class TestPathService:
    """Tests for PathService — centralized path resolution."""

    @pytest.fixture(autouse=True)
    def reset_path_caches(self) -> Generator[None, None, None]:
        """Reset PathService class-level caches for test isolation."""
        PathService.reset_caches()
        yield
        PathService.reset_caches()

    def test_get_root_dir_returns_path(self) -> None:
        root = PathService.get_root_dir()
        assert isinstance(root, Path)
        assert root.exists()

    def test_get_data_dir_creates_directory(self, tmp_path: Path) -> None:
        with patch.object(PathService, "get_root_dir", return_value=tmp_path):
            data_dir = PathService.get_data_dir()
            assert data_dir.exists()
            assert data_dir == tmp_path / ".ring5"

    def test_get_portfolios_dir_creates_directory(self, tmp_path: Path) -> None:
        with patch.object(PathService, "get_root_dir", return_value=tmp_path):
            portfolios_dir = PathService.get_portfolios_dir()
            assert portfolios_dir.exists()
            assert portfolios_dir == tmp_path / ".ring5" / "portfolios"

    def test_directories_are_idempotent(self, tmp_path: Path) -> None:
        """Calling get_*_dir twice doesn't fail."""
        with patch.object(PathService, "get_root_dir", return_value=tmp_path):
            PathService.get_data_dir()
            PathService.get_data_dir()  # Second call should not raise


class TestDistributionRangeMerge:
    """_merge_variable must not discard a legitimate 0.0 minimum (falsy-or bug)."""

    def test_zero_minimum_survives_merge_with_none(self) -> None:
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser
        from src.parsing.gem5.models import Gem5ScannedVariable

        registry: dict = {}
        no_range = Gem5ScannedVariable(name="d", type="distribution")
        with_zero_min = Gem5ScannedVariable(name="d", type="distribution", minimum=0.0, maximum=5.0)

        # Order A: None-range first, 0.0 arrives as the incoming side
        Gem5Parser._merge_variable(registry, no_range)
        Gem5Parser._merge_variable(registry, with_zero_min)
        assert registry["d"].minimum == 0.0
        assert registry["d"].maximum == 5.0

        # Order B: reversed
        registry.clear()
        Gem5Parser._merge_variable(registry, with_zero_min)
        Gem5Parser._merge_variable(registry, no_range)
        assert registry["d"].minimum == 0.0
        assert registry["d"].maximum == 5.0
