"""
Unit tests for the Simulator Registry.

Tests the registry pattern, auto-registration of gem5, and factory
instantiation of parser backends.
"""

import pytest

from src.parsing.parser_protocol import SimulationParser
from src.parsing.registry import (
    GEM5_INFO,
    ParsingStrategy,
    SimulatorInfo,
    SimulatorRegistry,
)


class TestSimulatorInfo:
    """Test SimulatorInfo dataclass."""

    def test_gem5_info_fields(self) -> None:
        assert GEM5_INFO.name == "gem5"
        assert GEM5_INFO.display_name == "gem5"
        assert GEM5_INFO.file_pattern == "stats.txt"
        assert "scalar" in GEM5_INFO.variable_types
        assert "vector" in GEM5_INFO.variable_types
        assert "distribution" in GEM5_INFO.variable_types
        assert "histogram" in GEM5_INFO.variable_types
        assert "configuration" in GEM5_INFO.variable_types

    def test_gem5_internal_stats(self) -> None:
        assert "total" in GEM5_INFO.internal_stats
        assert "mean" in GEM5_INFO.internal_stats
        assert "stdev" in GEM5_INFO.internal_stats
        assert "samples" in GEM5_INFO.internal_stats

    def test_custom_info(self) -> None:
        info = SimulatorInfo(
            name="test_sim",
            display_name="Test Simulator",
            description="A test simulator",
            file_pattern="*.log",
            variable_types=["counter", "gauge"],
            parsing_strategies=[
                ParsingStrategy(name="default", display_name="Default"),
            ],
        )
        assert info.name == "test_sim"
        assert info.file_pattern == "*.log"

    def test_gem5_parsing_strategies(self) -> None:
        """gem5 must declare at least one parsing strategy."""
        assert len(GEM5_INFO.parsing_strategies) >= 1
        strategy_names = [s.name for s in GEM5_INFO.parsing_strategies]
        assert "simple" in strategy_names
        assert "config_aware" in strategy_names

    def test_no_strategies_raises(self) -> None:
        """SimulatorInfo without strategies should raise ValueError."""
        with pytest.raises(ValueError, match="at least one parsing strategy"):
            SimulatorInfo(
                name="bad_sim",
                display_name="Bad Simulator",
                parsing_strategies=[],
            )


class TestSimulatorRegistry:
    """Test SimulatorRegistry class."""

    def test_gem5_auto_registered(self) -> None:
        """gem5 should be auto-registered on module import."""
        assert "gem5" in SimulatorRegistry.available_simulators()

    def test_available_simulators(self) -> None:
        sims = SimulatorRegistry.available_simulators()
        assert isinstance(sims, list)
        assert len(sims) >= 1
        assert sims == sorted(sims)  # Should be sorted

    def test_available_simulator_info(self) -> None:
        infos = SimulatorRegistry.available_simulator_info()
        assert len(infos) >= 1
        assert infos[0].name == "gem5"

    def test_get_info(self) -> None:
        info = SimulatorRegistry.get_info("gem5")
        assert info == GEM5_INFO

    def test_get_info_unknown(self) -> None:
        with pytest.raises(KeyError, match="Unknown simulator"):
            SimulatorRegistry.get_info("nonexistent")

    def test_get_parser_returns_simulation_parser(self) -> None:
        parser = SimulatorRegistry.get_parser("gem5")
        assert isinstance(parser, SimulationParser)

    def test_get_parser_caches_instance(self) -> None:
        parser1 = SimulatorRegistry.get_parser("gem5")
        parser2 = SimulatorRegistry.get_parser("gem5")
        assert parser1 is parser2

    def test_get_parser_unknown(self) -> None:
        with pytest.raises(KeyError, match="Unknown simulator"):
            SimulatorRegistry.get_parser("nonexistent")

    def test_duplicate_registration_raises(self) -> None:
        """Registering same name twice should raise."""
        info = SimulatorInfo(
            name="gem5",
            display_name="gem5 duplicate",
            parsing_strategies=[
                ParsingStrategy(name="simple", display_name="Simple"),
            ],
        )
        with pytest.raises(ValueError, match="already registered"):
            SimulatorRegistry.register(info, lambda: None)  # type: ignore[return-value]


class TestRegistryReset:
    """Test registry reset (for testing isolation)."""

    def test_reset_and_re_register(self) -> None:
        """_reset clears everything, then re-registering works."""
        # Reset
        SimulatorRegistry._reset()
        assert SimulatorRegistry.available_simulators() == []

        # Re-register gem5
        from src.parsing.registry import GEM5_INFO, _create_gem5_parser

        SimulatorRegistry.register(GEM5_INFO, _create_gem5_parser)
        assert "gem5" in SimulatorRegistry.available_simulators()

        # Verify the count matches (may have had extras before)
        assert len(SimulatorRegistry.available_simulators()) >= 1
