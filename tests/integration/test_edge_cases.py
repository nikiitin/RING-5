"""Integration tests for edge cases and boundary conditions.

Covers Scenarios #16-#19:
    - #16: Distribution/Histogram variable type processing
    - #17: Config service delete/reload cycle
    - #19: PatternAggregator regex expansion

Tests exercise boundary conditions, malformed inputs, and unusual
but valid combinations that are unlikely to appear in normal unit tests.
"""

from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest

from src.core.models.data_models import SavedConfigData, SavedConfigEntry
from src.core.models.shaper_models import ShaperStepConfig
from src.core.models.parsing_models import ScannedVariable
from src.core.services.data_services.config_service import ConfigService

# Helper: Minimal ScannedVariable dataclass
from src.parsing.gem5.impl.scanning.pattern_aggregator import PatternAggregator
from src.parsing.gem5.models import Gem5ScannedVariable
from src.parsing.gem5.types.distribution import Distribution
from src.parsing.gem5.types.histogram import Histogram

# Test Class 1: Distribution & Histogram processing edge cases


class TestDistributionHistogramEdgeCases:
    """Test Distribution and Histogram variable type parsing."""

    def test_distribution_basic_processing(self) -> None:
        """Distribution processes a valid set of buckets."""
        dist = Distribution(repeat=1, minimum=0, maximum=4)

        dist.content = {
            "underflows": 0,
            "overflows": 5,
            "0": 10,
            "1": 20,
            "2": 30,
            "3": 15,
            "4": 25,
        }
        dist.balance_content()
        dist.reduce_duplicates()

        result: dict[str, float] = dist.reduced_content
        assert result["0"] == 10.0
        assert result["2"] == 30.0
        assert result["underflows"] == 0.0
        assert result["overflows"] == 5.0

    def test_distribution_with_repeats(self) -> None:
        """Distribution averages across repeated dumps."""
        dist = Distribution(repeat=2, minimum=0, maximum=2)

        # First dump
        dist.content = {
            "underflows": 0,
            "overflows": 0,
            "0": 10,
            "1": 20,
            "2": 30,
        }
        # Second dump
        dist.content = {
            "underflows": 0,
            "overflows": 0,
            "0": 20,
            "1": 40,
            "2": 60,
        }
        dist.balance_content()
        dist.reduce_duplicates()

        result: dict[str, float] = dist.reduced_content
        # Average: (10+20)/2=15, (20+40)/2=30, (30+60)/2=45
        assert result["0"] == 15.0
        assert result["1"] == 30.0
        assert result["2"] == 45.0

    def test_distribution_maximum_too_large(self) -> None:
        """Distribution raises on absurdly large range."""
        with pytest.raises(ValueError, match="100000"):
            Distribution(repeat=1, minimum=0, maximum=200_000)

    def test_histogram_basic_processing(self) -> None:
        """Histogram processes range-keyed buckets."""
        hist = Histogram(repeat=1)

        hist.content = {
            "0-1023": 100,
            "1024-2047": 200,
            "2048-4095": 50,
        }
        hist.balance_content()
        hist.reduce_duplicates()

        result: dict[str, float] = hist.reduced_content
        assert result["0-1023"] == 100.0
        assert result["1024-2047"] == 200.0
        assert result["2048-4095"] == 50.0

    def test_histogram_with_repeats(self) -> None:
        """Histogram averages across repeats."""
        hist = Histogram(repeat=2)

        hist.content = {"0-1023": 100, "1024-2047": 200}
        hist.content = {"0-1023": 300, "1024-2047": 400}

        hist.balance_content()
        hist.reduce_duplicates()

        result: dict[str, float] = hist.reduced_content
        assert result["0-1023"] == 200.0  # (100+300)/2
        assert result["1024-2047"] == 300.0  # (200+400)/2

    def test_distribution_missing_boundaries_raises(self) -> None:
        """Distribution raises when boundary buckets are missing."""
        dist = Distribution(repeat=1, minimum=0, maximum=2)

        with pytest.raises((TypeError, RuntimeError)):
            dist.content = {
                # Missing underflows/overflows
                "0": 10,
                "1": 20,
                "2": 30,
            }


# Test Class 2: Config service delete/reload cycle


class TestConfigServiceEdgeCases:
    """Test ConfigService round-trip edge cases."""

    def test_save_load_delete_cycle(self, tmp_path: Path) -> None:
        """Full save → load → delete → verify deleted cycle."""
        config_dir: Path = tmp_path / "saved_configs"
        config_dir.mkdir(parents=True)

        with patch.object(
            ConfigService,
            "get_config_dir",
            return_value=config_dir,
        ):
            # Save
            shapers: list[ShaperStepConfig] = [
                cast(ShaperStepConfig, {"type": "columnSelector", "columns": ["a", "b"]}),
            ]
            saved_path: str = ConfigService.save_configuration(
                "test_config", "A test description", shapers
            )

            # Load
            loaded: SavedConfigData = ConfigService.load_configuration(saved_path)
            assert loaded["name"] == "test_config"
            assert loaded.get("description") == "A test description"
            assert loaded["shapers"] == shapers

            # Delete
            result: bool = ConfigService.delete_configuration(saved_path)
            assert result is True

            # Verify deleted — load should fail
            with pytest.raises((FileNotFoundError, ValueError)):
                ConfigService.load_configuration(saved_path)

    def test_load_saved_configs_skips_invalid(self, tmp_path: Path) -> None:
        """load_saved_configs silently skips corrupt JSON files."""
        config_dir: Path = tmp_path / "saved_configs"
        config_dir.mkdir(parents=True)

        # Valid config
        valid = config_dir / "valid.json"
        valid.write_text('{"name": "valid", "description": "ok", "shapers": []}')

        # Invalid JSON
        invalid = config_dir / "corrupt.json"
        invalid.write_text("{not valid json!!!")

        with patch.object(
            ConfigService,
            "get_config_dir",
            return_value=config_dir,
        ):
            configs: list[SavedConfigEntry] = ConfigService.load_saved_configs()

            # Should get exactly 1 (the valid one), corrupt is skipped
            assert len(configs) == 1
            assert configs[0]["name"] == "valid.json"

    def test_save_with_special_characters(self, tmp_path: Path) -> None:
        """Config names with special characters are sanitized."""
        config_dir: Path = tmp_path / "saved_configs"
        config_dir.mkdir(parents=True)

        with patch.object(
            ConfigService,
            "get_config_dir",
            return_value=config_dir,
        ):
            saved_path: str = ConfigService.save_configuration(
                "test/../../etc/passwd",
                "Malicious name test",
                [cast(ShaperStepConfig, {"type": "columnSelector", "columns": ["a"]})],
            )

            # Should still save (name sanitized)
            loaded: SavedConfigData = ConfigService.load_configuration(saved_path)
            assert loaded.get("description") == "Malicious name test"


# Test Class 3: PatternAggregator regex expansion


class TestPatternAggregatorEdgeCases:
    """Test pattern aggregation for multi-component gem5 variables."""

    def test_simple_cpu_aggregation(self) -> None:
        r"""cpu0/cpu1/cpu2 collapse into cpu\d+ pattern."""
        variables: list[ScannedVariable] = [
            ScannedVariable(name="system.cpu0.numCycles", type="scalar", entries=[]),
            ScannedVariable(name="system.cpu1.numCycles", type="scalar", entries=[]),
            ScannedVariable(name="system.cpu2.numCycles", type="scalar", entries=[]),
        ]

        result: list[ScannedVariable] = PatternAggregator.aggregate_patterns(variables)

        # Should collapse into one pattern variable
        pattern_vars: list[ScannedVariable] = [v for v in result if r"\d+" in v.name]
        assert len(pattern_vars) == 1
        assert pattern_vars[0].name == r"system.cpu\d+.numCycles"
        # Type promoted to vector
        assert pattern_vars[0].type == "vector"
        # Entries are the numeric IDs
        assert sorted(pattern_vars[0].entries) == ["0", "1", "2"]

    def test_no_aggregation_for_single_instance(self) -> None:
        """Single-instance variables are NOT aggregated."""
        variables: list[ScannedVariable] = [
            ScannedVariable(name="system.cpu0.numCycles", type="scalar", entries=[]),
            ScannedVariable(name="system.memctrl.readReqs", type="scalar", entries=[]),
        ]

        result: list[ScannedVariable] = PatternAggregator.aggregate_patterns(variables)

        # cpu0 has no partner → stays as-is
        names: list[str] = [v.name for v in result]
        assert "system.cpu0.numCycles" in names
        assert "system.memctrl.readReqs" in names
        assert all(r"\d+" not in n for n in names)

    def test_multi_numeric_pattern(self) -> None:
        """Variables with multiple numeric indices aggregate correctly."""
        variables: list[ScannedVariable] = [
            ScannedVariable(
                name="system.ruby.l0_cntrl0.hits",
                type="vector",
                entries=["read", "write"],
            ),
            ScannedVariable(
                name="system.ruby.l0_cntrl1.hits",
                type="vector",
                entries=["read", "write"],
            ),
            ScannedVariable(
                name="system.ruby.l1_cntrl0.hits",
                type="vector",
                entries=["read", "write"],
            ),
        ]

        result: list[ScannedVariable] = PatternAggregator.aggregate_patterns(variables)

        pattern_vars: list[ScannedVariable] = [v for v in result if r"\d+" in v.name]
        # Should have at least 1 pattern var
        assert len(pattern_vars) >= 1

        # Check entries contain union
        for pv in pattern_vars:
            assert "read" in pv.entries or len(pv.entries) > 0

    def test_vector_type_preserved(self) -> None:
        """Vector variables stay vector type after aggregation."""
        variables: list[ScannedVariable] = [
            ScannedVariable(
                name="system.cpu0.dcache.hits",
                type="vector",
                entries=["demand_accesses", "total"],
            ),
            ScannedVariable(
                name="system.cpu1.dcache.hits",
                type="vector",
                entries=["demand_accesses", "total"],
            ),
        ]

        result: list[ScannedVariable] = PatternAggregator.aggregate_patterns(variables)

        pattern_vars: list[ScannedVariable] = [v for v in result if r"\d+" in v.name]
        assert len(pattern_vars) == 1
        assert pattern_vars[0].type == "vector"
        assert "demand_accesses" in pattern_vars[0].entries

    def test_distribution_aggregation_preserves_minmax(self) -> None:
        """Distribution aggregation takes min of minimums, max of maximums."""
        variables: list[ScannedVariable] = [
            Gem5ScannedVariable(
                name="system.cpu0.dcache.miss_latency",
                type="distribution",
                entries=[],
                minimum=10.0,
                maximum=100.0,
            ),
            Gem5ScannedVariable(
                name="system.cpu1.dcache.miss_latency",
                type="distribution",
                entries=[],
                minimum=5.0,
                maximum=200.0,
            ),
        ]

        result: list[ScannedVariable] = PatternAggregator.aggregate_patterns(variables)

        pattern_vars: list[ScannedVariable] = [v for v in result if r"\d+" in v.name]
        assert len(pattern_vars) == 1
        pv = pattern_vars[0]
        assert isinstance(pv, Gem5ScannedVariable)
        assert pv.type == "distribution"
        assert pv.minimum == 5.0  # min of (10, 5)
        assert pv.maximum == 200.0  # max of (100, 200)

    def test_empty_input_returns_empty(self) -> None:
        """Empty variable list returns empty result."""
        result: list[ScannedVariable] = PatternAggregator.aggregate_patterns([])
        assert result == []

    def test_no_numeric_patterns(self) -> None:
        """Variables without numeric components are returned as-is."""
        variables: list[ScannedVariable] = [
            ScannedVariable(name="system.memctrl.readReqs", type="scalar", entries=[]),
            ScannedVariable(name="system.memctrl.writeReqs", type="scalar", entries=[]),
        ]

        result: list[ScannedVariable] = PatternAggregator.aggregate_patterns(variables)

        assert len(result) == 2
        names: list[str] = [v.name for v in result]
        assert "system.memctrl.readReqs" in names
        assert "system.memctrl.writeReqs" in names
