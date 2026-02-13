"""
Tests for VariableService new methods — extracted from UI layer to Layer B.

Tests find_entries_for_variable, update_scanned_entries, has_variable_with_name,
and build_statistics_list.
"""

from typing import Any, Dict, List

from src.core.services.data_services.variable_service import VariableService

# ─── find_entries_for_variable ───────────────────────────────────────────────


class TestFindEntriesForVariable:
    """Tests for finding entries across available/scanned variables."""

    def test_exact_match(self) -> None:
        avail = [
            {"name": "system.cpu.ipc", "entries": ["cpu0", "cpu1", "total"]},
            {"name": "system.mem.lat", "entries": ["bank0"]},
        ]
        result = VariableService.find_entries_for_variable(avail, "system.cpu.ipc")
        assert result == ["cpu0", "cpu1"]  # "total" filtered as internal stat

    def test_no_match(self) -> None:
        avail = [{"name": "system.cpu.ipc", "entries": ["cpu0"]}]
        result = VariableService.find_entries_for_variable(avail, "nonexistent")
        assert result == []

    def test_regex_pattern_match(self) -> None:
        avail = [
            {"name": "system.cpu0.ipc", "entries": ["e0", "e1"]},
            {"name": "system.cpu1.ipc", "entries": ["e2", "e3"]},
        ]
        result = VariableService.find_entries_for_variable(avail, r"system\.cpu\d+\.ipc")
        assert set(result) == {"e0", "e1", "e2", "e3"}

    def test_filters_internal_stats(self) -> None:
        avail = [
            {
                "name": "system.cpu.ipc",
                "entries": ["cpu0", "total", "mean", "stdev", "cpu1"],
            }
        ]
        result = VariableService.find_entries_for_variable(avail, "system.cpu.ipc")
        assert result == ["cpu0", "cpu1"]

    def test_empty_available(self) -> None:
        result = VariableService.find_entries_for_variable([], "any")
        assert result == []

    def test_variable_without_entries(self) -> None:
        avail = [{"name": "system.cpu.ipc"}]
        result = VariableService.find_entries_for_variable(avail, "system.cpu.ipc")
        assert result == []

    def test_aggregates_across_multiple_matches(self) -> None:
        avail = [
            {"name": "system.cpu.ipc", "entries": ["cpu0"]},
            {"name": "system.cpu.ipc", "entries": ["cpu1"]},
        ]
        result = VariableService.find_entries_for_variable(avail, "system.cpu.ipc")
        assert set(result) == {"cpu0", "cpu1"}


# ─── update_scanned_entries ──────────────────────────────────────────────────


class TestUpdateScannedEntries:
    """Tests for updating scanned variable entries."""

    def test_update_existing_variable(self) -> None:
        scanned = [
            {"name": "cpu.ipc", "type": "vector", "entries": ["old1", "old2"]},
        ]
        result = VariableService.update_scanned_entries(
            scanned, "cpu.ipc", ["new1", "new2", "new3"]
        )
        assert len(result) == 1
        assert result[0]["entries"] == ["new1", "new2", "new3"]

    def test_preserves_other_fields(self) -> None:
        """Fields like pattern_indices should be preserved."""
        scanned = [
            {
                "name": "cpu.ipc",
                "type": "vector",
                "entries": ["old"],
                "pattern_indices": {"0": ["0", "1"]},
            },
        ]
        result = VariableService.update_scanned_entries(scanned, "cpu.ipc", ["new"])
        assert result[0]["pattern_indices"] == {"0": ["0", "1"]}
        assert result[0]["entries"] == ["new"]

    def test_add_new_variable(self) -> None:
        scanned = [{"name": "existing", "type": "vector", "entries": ["e1"]}]
        result = VariableService.update_scanned_entries(scanned, "new.var", ["a", "b"])
        assert len(result) == 2
        assert result[1]["name"] == "new.var"
        assert result[1]["type"] == "vector"
        assert result[1]["entries"] == ["a", "b"]

    def test_does_not_mutate_original(self) -> None:
        scanned = [{"name": "cpu.ipc", "type": "vector", "entries": ["old"]}]
        result = VariableService.update_scanned_entries(scanned, "cpu.ipc", ["new"])
        # Original should be unchanged
        assert scanned[0]["entries"] == ["old"]
        assert result[0]["entries"] == ["new"]

    def test_empty_scanned_list(self) -> None:
        result = VariableService.update_scanned_entries([], "new.var", ["e1"])
        assert len(result) == 1
        assert result[0]["name"] == "new.var"


# ─── has_variable_with_name ──────────────────────────────────────────────────


class TestHasVariableWithName:
    """Tests for duplicate variable name detection."""

    def test_found(self) -> None:
        variables = [{"name": "cpu.ipc"}, {"name": "mem.lat"}]
        assert VariableService.has_variable_with_name(variables, "cpu.ipc") is True

    def test_not_found(self) -> None:
        variables = [{"name": "cpu.ipc"}]
        assert VariableService.has_variable_with_name(variables, "nonexistent") is False

    def test_empty_list(self) -> None:
        assert VariableService.has_variable_with_name([], "any") is False

    def test_variable_without_name_key(self) -> None:
        variables: List[Dict[str, Any]] = [{"type": "scalar"}]
        assert VariableService.has_variable_with_name(variables, "cpu.ipc") is False


# ─── build_statistics_list ───────────────────────────────────────────────────


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
