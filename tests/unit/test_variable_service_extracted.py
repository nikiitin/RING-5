"""
Tests for VariableService new methods — extracted from UI layer to Layer B.

Tests find_entries_for_variable, has_variable_with_name,
and build_statistics_list.
"""

from typing import cast

from src.parsing.registry import SimulatorRegistry

from src.core.models.data_models import ParseVariableConfig, ScannedVariableDict
from src.core.services.data_services.variable_service import VariableService

# find_entries_for_variable


class TestFindEntriesForVariable:
    """Tests for finding entries across available/scanned variables."""

    def test_exact_match(self) -> None:
        avail = cast(
            list[ScannedVariableDict],
            [
                {"name": "system.cpu.ipc", "entries": ["cpu0", "cpu1", "total"]},
                {"name": "system.mem.lat", "entries": ["bank0"]},
            ],
        )
        result = VariableService.find_entries_for_variable(
            avail,
            "system.cpu.ipc",
            internal_stats=SimulatorRegistry.get_info("gem5").internal_stats,
        )
        assert result == ["cpu0", "cpu1"]  # "total" filtered as internal stat

    def test_no_match(self) -> None:
        avail = cast(list[ScannedVariableDict], [{"name": "system.cpu.ipc", "entries": ["cpu0"]}])
        result = VariableService.find_entries_for_variable(
            avail, "nonexistent", internal_stats=SimulatorRegistry.get_info("gem5").internal_stats
        )
        assert result == []

    def test_regex_pattern_match(self) -> None:
        avail = cast(
            list[ScannedVariableDict],
            [
                {"name": "system.cpu0.ipc", "entries": ["e0", "e1"]},
                {"name": "system.cpu1.ipc", "entries": ["e2", "e3"]},
            ],
        )
        result = VariableService.find_entries_for_variable(
            avail,
            r"system\.cpu\d+\.ipc",
            internal_stats=SimulatorRegistry.get_info("gem5").internal_stats,
        )
        assert set(result) == {"e0", "e1", "e2", "e3"}

    def test_filters_internal_stats(self) -> None:
        avail = cast(
            list[ScannedVariableDict],
            [
                {
                    "name": "system.cpu.ipc",
                    "entries": ["cpu0", "total", "mean", "stdev", "cpu1"],
                }
            ],
        )
        result = VariableService.find_entries_for_variable(
            avail,
            "system.cpu.ipc",
            internal_stats=SimulatorRegistry.get_info("gem5").internal_stats,
        )
        assert result == ["cpu0", "cpu1"]

    def test_empty_available(self) -> None:
        result = VariableService.find_entries_for_variable(
            [], "any", internal_stats=SimulatorRegistry.get_info("gem5").internal_stats
        )
        assert result == []

    def test_variable_without_entries(self) -> None:
        avail = cast(list[ScannedVariableDict], [{"name": "system.cpu.ipc"}])
        result = VariableService.find_entries_for_variable(
            avail,
            "system.cpu.ipc",
            internal_stats=SimulatorRegistry.get_info("gem5").internal_stats,
        )
        assert result == []

    def test_aggregates_across_multiple_matches(self) -> None:
        avail = cast(
            list[ScannedVariableDict],
            [
                {"name": "system.cpu.ipc", "entries": ["cpu0"]},
                {"name": "system.cpu.ipc", "entries": ["cpu1"]},
            ],
        )
        result = VariableService.find_entries_for_variable(
            avail,
            "system.cpu.ipc",
            internal_stats=SimulatorRegistry.get_info("gem5").internal_stats,
        )
        assert set(result) == {"cpu0", "cpu1"}


# has_variable_with_name


class TestHasVariableWithName:
    """Tests for duplicate variable name detection."""

    def test_found(self) -> None:
        variables = cast(list[ParseVariableConfig], [{"name": "cpu.ipc"}, {"name": "mem.lat"}])
        assert VariableService.has_variable_with_name(variables, "cpu.ipc") is True

    def test_not_found(self) -> None:
        variables = cast(list[ParseVariableConfig], [{"name": "cpu.ipc"}])
        assert VariableService.has_variable_with_name(variables, "nonexistent") is False

    def test_empty_list(self) -> None:
        assert VariableService.has_variable_with_name([], "any") is False

    def test_variable_without_name_key(self) -> None:
        variables = cast(list[ParseVariableConfig], [{"type": "scalar"}])
        assert VariableService.has_variable_with_name(variables, "cpu.ipc") is False


# build_statistics_list


class TestBuildStatisticsList:
    """Tests for building statistics list from boolean mapping."""

    def test_all_selected(self) -> None:
        selected = {"total": True, "mean": True, "stdev": True}
        result = VariableService.build_statistics_list(selected)
        assert result == ["total", "mean", "stdev"]

    def test_none_selected(self) -> None:
        selected = {"total": False, "mean": False}
        result = VariableService.build_statistics_list(selected)
        assert result == []

    def test_mixed_selection(self) -> None:
        selected = {"total": True, "mean": False, "stdev": True, "gmean": False}
        result = VariableService.build_statistics_list(selected)
        assert result == ["total", "stdev"]

    def test_empty_dict(self) -> None:
        result = VariableService.build_statistics_list({})
        assert result == []

    def test_preserves_insertion_order(self) -> None:
        selected = {"stdev": True, "mean": True, "total": True}
        result = VariableService.build_statistics_list(selected)
        assert result == ["stdev", "mean", "total"]
