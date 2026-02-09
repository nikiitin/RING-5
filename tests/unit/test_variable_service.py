"""
Unit tests for VariableService.
Tests CRUD operations, entry filtering, and aggregation logic.
"""

import pytest

from src.core.services.data_services.variable_service import VariableService


class TestGenerateVariableId:
    """Tests for generate_variable_id()."""

    def test_generates_non_empty_string(self) -> None:
        """Should generate a non-empty string."""
        var_id = VariableService.generate_variable_id()
        assert isinstance(var_id, str)
        assert len(var_id) > 0

    def test_generates_unique_ids(self) -> None:
        """Should generate unique IDs on successive calls."""
        id1 = VariableService.generate_variable_id()
        id2 = VariableService.generate_variable_id()
        id3 = VariableService.generate_variable_id()
        assert id1 != id2
        assert id2 != id3
        assert id1 != id3


class TestAddVariable:
    """Tests for add_variable()."""

    def test_add_to_empty_list(self) -> None:
        """Should add variable to empty list."""
        variables = []
        config = {"name": "system.cpu.ipc", "type": "scalar"}
        result = VariableService.add_variable(variables, config)

        assert len(result) == 1
        assert result[0]["name"] == "system.cpu.ipc"
        assert result[0]["type"] == "scalar"
        assert "_id" in result[0]

    def test_add_to_existing_list(self) -> None:
        """Should append to existing list."""
        variables = [{"name": "var1", "type": "scalar", "_id": "id1"}]
        config = {"name": "var2", "type": "vector"}
        result = VariableService.add_variable(variables, config)

        assert len(result) == 2
        assert result[0]["name"] == "var1"
        assert result[1]["name"] == "var2"

    def test_preserves_existing_id(self) -> None:
        """Should preserve _id if already present."""
        variables = []
        config = {"name": "var1", "type": "scalar", "_id": "custom_id"}
        result = VariableService.add_variable(variables, config)

        assert result[0]["_id"] == "custom_id"

    def test_generates_id_if_missing(self) -> None:
        """Should generate _id if not present."""
        variables = []
        config = {"name": "var1", "type": "scalar"}
        result = VariableService.add_variable(variables, config)

        assert "_id" in result[0]
        assert len(result[0]["_id"]) > 0

    def test_does_not_mutate_original_list(self) -> None:
        """Should not modify the original variables list."""
        variables = [{"name": "var1", "type": "scalar"}]
        config = {"name": "var2", "type": "vector"}
        result = VariableService.add_variable(variables, config)

        assert len(variables) == 1
        assert len(result) == 2


class TestUpdateVariable:
    """Tests for update_variable()."""

    def test_update_at_valid_index(self) -> None:
        """Should update variable at specified index."""
        variables = [
            {"name": "var1", "type": "scalar", "_id": "id1"},
            {"name": "var2", "type": "vector", "_id": "id2"},
        ]
        new_config = {"name": "updated_var", "type": "distribution", "_id": "id2"}
        result = VariableService.update_variable(variables, 1, new_config)

        assert len(result) == 2
        assert result[0]["name"] == "var1"
        assert result[1]["name"] == "updated_var"
        assert result[1]["type"] == "distribution"

    def test_update_at_index_zero(self) -> None:
        """Should update first variable."""
        variables = [{"name": "var1", "type": "scalar"}]
        new_config = {"name": "updated", "type": "vector"}
        result = VariableService.update_variable(variables, 0, new_config)

        assert result[0]["name"] == "updated"

    def test_raises_on_negative_index(self) -> None:
        """Should raise IndexError for negative index."""
        variables = [{"name": "var1"}]
        with pytest.raises(IndexError):
            VariableService.update_variable(variables, -1, {"name": "new"})

    def test_raises_on_out_of_bounds_index(self) -> None:
        """Should raise IndexError for index >= len."""
        variables = [{"name": "var1"}]
        with pytest.raises(IndexError):
            VariableService.update_variable(variables, 1, {"name": "new"})

    def test_does_not_mutate_original_list(self) -> None:
        """Should not modify the original variables list."""
        variables = [{"name": "var1", "type": "scalar"}]
        new_config = {"name": "updated", "type": "vector"}
        result = VariableService.update_variable(variables, 0, new_config)

        assert variables[0]["name"] == "var1"
        assert result[0]["name"] == "updated"


class TestDeleteVariable:
    """Tests for delete_variable()."""

    def test_delete_from_single_element_list(self) -> None:
        """Should delete the only element."""
        variables = [{"name": "var1"}]
        result = VariableService.delete_variable(variables, 0)

        assert len(result) == 0

    def test_delete_from_middle(self) -> None:
        """Should delete variable from middle of list."""
        variables = [
            {"name": "var1"},
            {"name": "var2"},
            {"name": "var3"},
        ]
        result = VariableService.delete_variable(variables, 1)

        assert len(result) == 2
        assert result[0]["name"] == "var1"
        assert result[1]["name"] == "var3"

    def test_delete_first_element(self) -> None:
        """Should delete first variable."""
        variables = [{"name": "var1"}, {"name": "var2"}]
        result = VariableService.delete_variable(variables, 0)

        assert len(result) == 1
        assert result[0]["name"] == "var2"

    def test_delete_last_element(self) -> None:
        """Should delete last variable."""
        variables = [{"name": "var1"}, {"name": "var2"}]
        result = VariableService.delete_variable(variables, 1)

        assert len(result) == 1
        assert result[0]["name"] == "var1"

    def test_raises_on_negative_index(self) -> None:
        """Should raise IndexError for negative index."""
        variables = [{"name": "var1"}]
        with pytest.raises(IndexError):
            VariableService.delete_variable(variables, -1)

    def test_raises_on_out_of_bounds_index(self) -> None:
        """Should raise IndexError for index >= len."""
        variables = [{"name": "var1"}]
        with pytest.raises(IndexError):
            VariableService.delete_variable(variables, 1)

    def test_does_not_mutate_original_list(self) -> None:
        """Should not modify the original variables list."""
        variables = [{"name": "var1"}, {"name": "var2"}]
        result = VariableService.delete_variable(variables, 0)

        assert len(variables) == 2
        assert len(result) == 1


class TestEnsureVariableIds:
    """Tests for ensure_variable_ids()."""

    def test_adds_ids_to_all_variables(self) -> None:
        """Should add _id to all variables without one."""
        variables = [
            {"name": "var1"},
            {"name": "var2"},
            {"name": "var3"},
        ]
        result = VariableService.ensure_variable_ids(variables)

        assert all("_id" in v for v in result)
        assert len(result) == 3

    def test_preserves_existing_ids(self) -> None:
        """Should preserve existing _id fields."""
        variables = [
            {"name": "var1", "_id": "custom_id_1"},
            {"name": "var2"},
            {"name": "var3", "_id": "custom_id_3"},
        ]
        result = VariableService.ensure_variable_ids(variables)

        assert result[0]["_id"] == "custom_id_1"
        assert "_id" in result[1]
        assert result[2]["_id"] == "custom_id_3"

    def test_empty_list(self) -> None:
        """Should handle empty list."""
        result = VariableService.ensure_variable_ids([])
        assert result == []

    def test_does_not_mutate_original_list(self) -> None:
        """Should not modify original variables list."""
        variables = [{"name": "var1"}]
        result = VariableService.ensure_variable_ids(variables)

        assert "_id" not in variables[0]
        assert "_id" in result[0]


class TestFilterInternalStats:
    """Tests for filter_internal_stats()."""

    def test_filters_all_internal_stats(self) -> None:
        """Should remove all internal gem5 statistics."""
        entries = ["cpu0", "total", "mean", "gmean", "stdev", "samples", "overflows", "underflows"]
        result = VariableService.filter_internal_stats(entries)

        assert result == ["cpu0"]

    def test_case_insensitive_filtering(self) -> None:
        """Should filter internal stats regardless of case."""
        entries = ["CPU0", "TOTAL", "Mean", "STDEV", "cpu1"]
        result = VariableService.filter_internal_stats(entries)

        assert "cpu1" in result
        assert "CPU0" in result
        assert "TOTAL" not in result
        assert "Mean" not in result

    def test_preserves_non_internal_entries(self) -> None:
        """Should keep all non-internal entries."""
        entries = ["cpu0", "cpu1", "bank0", "bank1"]
        result = VariableService.filter_internal_stats(entries)

        assert sorted(result) == ["bank0", "bank1", "cpu0", "cpu1"]

    def test_returns_sorted_list(self) -> None:
        """Should return alphabetically sorted list."""
        entries = ["cpu2", "cpu0", "cpu1"]
        result = VariableService.filter_internal_stats(entries)

        assert result == ["cpu0", "cpu1", "cpu2"]

    def test_empty_list(self) -> None:
        """Should handle empty list."""
        result = VariableService.filter_internal_stats([])
        assert result == []


class TestFindVariableByName:
    """Tests for find_variable_by_name()."""

    def test_exact_match_found(self) -> None:
        """Should find variable with exact name match."""
        variables = [
            {"name": "system.cpu.ipc", "type": "scalar"},
            {"name": "system.mem.bandwidth", "type": "vector"},
        ]
        result = VariableService.find_variable_by_name(variables, "system.cpu.ipc")

        assert result is not None
        assert result["type"] == "scalar"

    def test_exact_match_not_found(self) -> None:
        """Should return None if exact match not found."""
        variables = [{"name": "system.cpu.ipc", "type": "scalar"}]
        result = VariableService.find_variable_by_name(variables, "system.mem.bandwidth")

        assert result is None

    def test_regex_match_found(self) -> None:
        """Should find variable using regex pattern."""
        variables = [
            {"name": "system.cpu0.ipc", "type": "scalar"},
            {"name": "system.cpu1.ipc", "type": "scalar"},
        ]
        result = VariableService.find_variable_by_name(
            variables, r"system\.cpu\d+\.ipc", exact=False
        )

        assert result is not None
        assert "system.cpu" in result["name"]

    def test_regex_match_not_found(self) -> None:
        """Should return None if regex doesn't match."""
        variables = [{"name": "system.cpu.ipc", "type": "scalar"}]
        result = VariableService.find_variable_by_name(variables, r"system\.mem\..*", exact=False)

        assert result is None

    def test_invalid_regex_fallback_to_exact(self) -> None:
        """Should fall back to exact match on invalid regex."""
        variables = [{"name": "system[cpu", "type": "scalar"}]
        result = VariableService.find_variable_by_name(variables, "system[cpu", exact=False)

        assert result is not None

    def test_empty_list(self) -> None:
        """Should return None for empty list."""
        result = VariableService.find_variable_by_name([], "system.cpu.ipc")
        assert result is None


class TestAggregateDiscoveredEntries:
    """Tests for aggregate_discovered_entries()."""

    def test_aggregates_from_single_variable(self) -> None:
        """Should aggregate entries from one variable."""
        snapshot = [
            {"name": "system.cpu.vector", "entries": ["cpu0", "cpu1", "total"]},
        ]
        result = VariableService.aggregate_discovered_entries(snapshot, "system.cpu.vector")

        assert sorted(result) == ["cpu0", "cpu1"]

    def test_aggregates_from_multiple_variables(self) -> None:
        """Should aggregate entries from multiple matching variables."""
        snapshot = [
            {"name": "system.cpu0.vector", "entries": ["entry0", "total"]},
            {"name": "system.cpu1.vector", "entries": ["entry1", "mean"]},
            {"name": "system.cpu2.vector", "entries": ["entry2", "stdev"]},
        ]
        result = VariableService.aggregate_discovered_entries(snapshot, r"system\.cpu\d+\.vector")

        assert sorted(result) == ["entry0", "entry1", "entry2"]

    def test_removes_duplicates(self) -> None:
        """Should remove duplicate entries."""
        snapshot = [
            {"name": "system.var1", "entries": ["cpu0", "cpu1"]},
            {"name": "system.var2", "entries": ["cpu1", "cpu2"]},
        ]
        result = VariableService.aggregate_discovered_entries(snapshot, r"system\.var\d+")

        assert sorted(result) == ["cpu0", "cpu1", "cpu2"]

    def test_filters_internal_stats(self) -> None:
        """Should filter out internal statistics."""
        snapshot = [
            {"name": "system.vec", "entries": ["cpu0", "total", "mean", "gmean"]},
        ]
        result = VariableService.aggregate_discovered_entries(snapshot, "system.vec")

        assert result == ["cpu0"]

    def test_no_matching_variables(self) -> None:
        """Should return empty list if no matches."""
        snapshot = [
            {"name": "system.cpu", "entries": ["cpu0"]},
        ]
        result = VariableService.aggregate_discovered_entries(snapshot, "system.mem")

        assert result == []


class TestAggregateDistributionRange:
    """Tests for aggregate_distribution_range()."""

    def test_single_distribution(self) -> None:
        """Should extract range from single distribution."""
        snapshot = [
            {"name": "system.latency", "type": "distribution", "minimum": 10, "maximum": 100},
        ]
        min_val, max_val = VariableService.aggregate_distribution_range(snapshot, "system.latency")

        assert min_val == 10
        assert max_val == 100

    def test_multiple_distributions_find_global_range(self) -> None:
        """Should find global min/max across multiple distributions."""
        snapshot = [
            {"name": "system.latency", "type": "distribution", "minimum": 10, "maximum": 100},
            {"name": "system.latency", "type": "distribution", "minimum": 5, "maximum": 150},
            {"name": "system.latency", "type": "distribution", "minimum": 15, "maximum": 80},
        ]
        min_val, max_val = VariableService.aggregate_distribution_range(snapshot, "system.latency")

        assert min_val == 5
        assert max_val == 150

    def test_regex_pattern_matching(self) -> None:
        """Should match using regex patterns."""
        snapshot = [
            {"name": "system.cpu0.latency", "type": "distribution", "minimum": 10, "maximum": 100},
            {"name": "system.cpu1.latency", "type": "distribution", "minimum": 5, "maximum": 120},
        ]
        min_val, max_val = VariableService.aggregate_distribution_range(
            snapshot, r"system\.cpu\d+\.latency"
        )

        assert min_val == 5
        assert max_val == 120

    def test_no_matching_distributions(self) -> None:
        """Should return (None, None) if no matches."""
        snapshot = [
            {"name": "system.cpu", "type": "scalar", "value": 42},
        ]
        min_val, max_val = VariableService.aggregate_distribution_range(snapshot, "system.latency")

        assert min_val is None
        assert max_val is None

    def test_partial_range_data(self) -> None:
        """Should handle distributions with partial range data."""
        snapshot = [
            {"name": "system.latency", "type": "distribution", "minimum": 10},
            {"name": "system.latency", "type": "distribution", "maximum": 100},
        ]
        min_val, max_val = VariableService.aggregate_distribution_range(snapshot, "system.latency")

        assert min_val == 10
        assert max_val == 100


class TestParseCommaSeparatedEntries:
    """Tests for parse_comma_separated_entries()."""

    def test_basic_parsing(self) -> None:
        """Should parse comma-separated string."""
        result = VariableService.parse_comma_separated_entries("cpu0,cpu1,cpu2")
        assert result == ["cpu0", "cpu1", "cpu2"]

    def test_handles_whitespace(self) -> None:
        """Should trim whitespace from entries."""
        result = VariableService.parse_comma_separated_entries("cpu0, cpu1 ,  cpu2  ")
        assert result == ["cpu0", "cpu1", "cpu2"]

    def test_filters_empty_entries(self) -> None:
        """Should filter out empty entries."""
        result = VariableService.parse_comma_separated_entries("cpu0,,,cpu1, ,cpu2")
        assert result == ["cpu0", "cpu1", "cpu2"]

    def test_empty_string(self) -> None:
        """Should return empty list for empty string."""
        result = VariableService.parse_comma_separated_entries("")
        assert result == []

    def test_only_whitespace(self) -> None:
        """Should return empty list for whitespace-only string."""
        result = VariableService.parse_comma_separated_entries("  ,  ,  ")
        assert result == []


class TestFormatEntriesAsString:
    """Tests for format_entries_as_string()."""

    def test_basic_formatting(self) -> None:
        """Should format list as comma-separated string."""
        result = VariableService.format_entries_as_string(["cpu0", "cpu1", "cpu2"])
        assert result == "cpu0, cpu1, cpu2"

    def test_single_entry(self) -> None:
        """Should handle single entry."""
        result = VariableService.format_entries_as_string(["cpu0"])
        assert result == "cpu0"

    def test_empty_list(self) -> None:
        """Should return empty string for empty list."""
        result = VariableService.format_entries_as_string([])
        assert result == ""
