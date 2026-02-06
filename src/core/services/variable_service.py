"""
Variable Service for RING-5.
Handles CRUD operations for parser variables (scalar, vector, distribution, histogram, configuration).  # noqa: E501
Provides business logic for variable management without UI dependencies.
"""

import re
import uuid
from typing import Any, Dict, List, Optional, Set


class VariableService:
    """Service for managing parser variables with CRUD operations."""

    # Scientific filter: Internal gem5 statistics that should not appear as regular entries
    INTERNAL_STATS: Set[str] = {
        "total",
        "mean",
        "gmean",
        "stdev",
        "samples",
        "overflows",
        "underflows",
    }

    @staticmethod
    def generate_variable_id() -> str:
        """
        Generate a unique ID for a variable.

        Returns:
            Unique identifier string (UUID4)
        """
        return str(uuid.uuid4())

    @classmethod
    def add_variable(
        cls, variables: List[Dict[str, Any]], var_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Add a new variable to the list.

        Args:
            variables: Current list of variable configurations
            var_config: Configuration dict for the new variable

        Returns:
            Updated list with new variable added (includes generated _id)

        Examples:
            >>> service = VariableService()
            >>> vars = []
            >>> vars = service.add_variable(vars, {"name": "system.cpu.ipc", "type": "scalar"})
            >>> len(vars)
            1
            >>> "_id" in vars[0]
            True
        """
        updated_vars = variables.copy()
        var_with_id = var_config.copy()

        # Generate ID if not present
        if "_id" not in var_with_id:
            var_with_id["_id"] = cls.generate_variable_id()

        updated_vars.append(var_with_id)
        return updated_vars

    @classmethod
    def update_variable(
        cls, variables: List[Dict[str, Any]], index: int, var_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Update an existing variable at the specified index.

        Args:
            variables: Current list of variable configurations
            index: Index of variable to update
            var_config: New configuration dict for the variable

        Returns:
            Updated list with modified variable

        Raises:
            IndexError: If index is out of bounds

        Examples:
            >>> service = VariableService()
            >>> vars = [{"name": "old", "type": "scalar", "_id": "123"}]
            >>> vars = service.update_variable(vars, 0, {"name": "new", "type": "vector", "_id": "123"})  # noqa: E501
            >>> vars[0]["name"]
            'new'
        """
        if index < 0 or index >= len(variables):
            raise IndexError(f"Index {index} out of bounds for list of {len(variables)} variables")

        updated_vars = variables.copy()
        updated_vars[index] = var_config
        return updated_vars

    @classmethod
    def delete_variable(cls, variables: List[Dict[str, Any]], index: int) -> List[Dict[str, Any]]:
        """
        Delete a variable at the specified index.

        Args:
            variables: Current list of variable configurations
            index: Index of variable to delete

        Returns:
            Updated list with variable removed

        Raises:
            IndexError: If index is out of bounds

        Examples:
            >>> service = VariableService()
            >>> vars = [{"name": "var1"}, {"name": "var2"}, {"name": "var3"}]
            >>> vars = service.delete_variable(vars, 1)
            >>> len(vars)
            2
            >>> vars[1]["name"]
            'var3'
        """
        if index < 0 or index >= len(variables):
            raise IndexError(f"Index {index} out of bounds for list of {len(variables)} variables")

        updated_vars = variables.copy()
        del updated_vars[index]
        return updated_vars

    @classmethod
    def ensure_variable_ids(cls, variables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Ensure all variables have unique IDs, generating them if missing.

        Args:
            variables: List of variable configurations

        Returns:
            Updated list with all variables having _id field

        Examples:
            >>> service = VariableService()
            >>> vars = [{"name": "var1"}, {"name": "var2"}]
            >>> vars = service.ensure_variable_ids(vars)
            >>> all("_id" in v for v in vars)
            True
        """
        updated_vars = []
        for var in variables:
            var_copy = var.copy()
            if "_id" not in var_copy:
                var_copy["_id"] = cls.generate_variable_id()
            updated_vars.append(var_copy)
        return updated_vars

    @classmethod
    def filter_internal_stats(cls, entries: List[str]) -> List[str]:
        """
        Filter out internal gem5 statistics from entry list.

        Args:
            entries: List of entry names to filter

        Returns:
            Filtered list with internal stats removed, sorted alphabetically

        Examples:
            >>> service = VariableService()
            >>> entries = ["cpu0", "total", "mean", "cpu1", "stdev"]
            >>> filtered = service.filter_internal_stats(entries)
            >>> filtered
            ['cpu0', 'cpu1']
        """
        filtered = [e for e in entries if e.lower() not in cls.INTERNAL_STATS]
        return sorted(filtered)

    @classmethod
    def find_variable_by_name(
        cls, variables: List[Dict[str, Any]], name: str, exact: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Find a variable by name in the list.

        Args:
            variables: List of variable configurations
            name: Variable name to search for
            exact: If True, use exact match; if False, use regex pattern matching

        Returns:
            First matching variable dict, or None if not found

        Examples:
            >>> service = VariableService()
            >>> vars = [{"name": "system.cpu.ipc", "type": "scalar"}]
            >>> var = service.find_variable_by_name(vars, "system.cpu.ipc")
            >>> var["type"]
            'scalar'
            >>> service.find_variable_by_name(vars, "nonexistent") is None
            True
        """
        for var in variables:
            var_name = var.get("name", "")
            if exact:
                if var_name == name:
                    return var
            else:
                # Regex pattern matching
                try:
                    if re.fullmatch(name, var_name):
                        return var
                except re.error:
                    # Invalid regex, fall back to exact match
                    if var_name == name:
                        return var
        return None

    @classmethod
    def aggregate_discovered_entries(
        cls, snapshot: List[Dict[str, Any]], var_name: str
    ) -> List[str]:
        r"""
        Aggregate all discovered entries for a variable across scanned files.

        Args:
            snapshot: List of scanned variable results from multiple files
            var_name: Variable name to aggregate entries for (supports regex)

        Returns:
            Sorted list of unique entries with internal stats filtered out

        Examples:
            >>> service = VariableService()
            >>> snapshot = [
            ...     {"name": "system.cpu0.ipc", "entries": ["cpu0", "total"]},
            ...     {"name": "system.cpu1.ipc", "entries": ["cpu1", "mean"]}
            ... ]
            >>> entries = service.aggregate_discovered_entries(snapshot, r"system\.cpu\d+\.ipc")
            >>> entries
            ['cpu0', 'cpu1']
        """
        found_entries: Set[str] = set()
        for var in snapshot:
            # Handle both ScannedVariable models and legacy dicts
            name = var.name if hasattr(var, "name") else var.get("name", "")
            entries = var.entries if hasattr(var, "entries") else var.get("entries", [])

            var_name_match = name == var_name
            try:
                var_name_match = var_name_match or bool(re.fullmatch(var_name, name))
            except re.error:
                pass

            if var_name_match and entries:
                found_entries.update(entries)

        return cls.filter_internal_stats(list(found_entries))

    @classmethod
    def aggregate_distribution_range(
        cls, snapshot: List[Dict[str, Any]], var_name: str
    ) -> tuple[Optional[float], Optional[float]]:
        """
        Aggregate min/max range for a distribution variable across scanned files.

        Args:
            snapshot: List of scanned variable results from multiple files
            var_name: Variable name to aggregate range for (supports regex)

        Returns:
            Tuple of (global_min, global_max) or (None, None) if not found

        Examples:
            >>> service = VariableService()
            >>> snapshot = [
            ...     {"name": "system.latency", "type": "distribution", "minimum": 10, "maximum": 100},  # noqa: E501
            ...     {"name": "system.latency", "type": "distribution", "minimum": 5, "maximum": 150}
            ... ]
            >>> min_val, max_val = service.aggregate_distribution_range(snapshot, "system.latency")
            >>> (min_val, max_val)
            (5, 150)
        """
        global_min: Optional[float] = None
        global_max: Optional[float] = None

        for var in snapshot:
            # Handle both ScannedVariable models and legacy dicts
            name = var.name if hasattr(var, "name") else var.get("name", "")
            v_type = var.type if hasattr(var, "type") else var.get("type", "")
            v_min = var.minimum if hasattr(var, "minimum") else var.get("minimum")
            v_max = var.maximum if hasattr(var, "maximum") else var.get("maximum")

            var_name_match = name == var_name
            try:
                var_name_match = var_name_match or bool(re.fullmatch(var_name, name))
            except re.error:
                pass

            if var_name_match and v_type == "distribution":
                if v_min is not None:
                    global_min = min(global_min, v_min) if global_min is not None else v_min
                if v_max is not None:
                    global_max = max(global_max, v_max) if global_max is not None else v_max

        return global_min, global_max

    @classmethod
    def parse_comma_separated_entries(cls, entries_str: str) -> List[str]:
        """
        Parse comma-separated entry string into list.

        Args:
            entries_str: Comma-separated entry names

        Returns:
            List of trimmed, non-empty entry names

        Examples:
            >>> service = VariableService()
            >>> entries = service.parse_comma_separated_entries("cpu0, cpu1,  cpu2  , ")
            >>> entries
            ['cpu0', 'cpu1', 'cpu2']
        """
        return [e.strip() for e in entries_str.split(",") if e.strip()]

    @classmethod
    def format_entries_as_string(cls, entries: List[str]) -> str:
        """
        Format list of entries as comma-separated string.

        Args:
            entries: List of entry names

        Returns:
            Comma-separated string

        Examples:
            >>> service = VariableService()
            >>> service.format_entries_as_string(["cpu0", "cpu1", "cpu2"])
            'cpu0, cpu1, cpu2'
        """
        return ", ".join(entries)
