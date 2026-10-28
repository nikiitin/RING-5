"""
Variable Service for RING-5.
Handles CRUD operations for parser variables
(scalar, vector, distribution, histogram, configuration).
Provides business logic for variable management without UI dependencies.
"""

import uuid

from src.core.common.variable_identity import normalize_variable_ids

from src.core.common.safe_regex import (
    BoundedPattern,
    SafeRegexError,
    compile_bounded_regex,
    fullmatch_bounded_regex,
)
from src.core.models.data_models import ParseVariableConfig, ScannedVariableDict


def _compile_safe_pattern(pattern: str) -> BoundedPattern | None:
    """Compile a regex pattern with safety checks against ReDoS/injection.

    Validates the pattern length, character allowlist, and syntax before
    compiling.  Returns None if the pattern is invalid, too long, or
    contains characters outside the allowlist.

    Args:
        pattern: The regex pattern string to compile.

    Returns:
        Compiled regex pattern, or None if unsafe/invalid.
    """
    try:
        return compile_bounded_regex(pattern)
    except SafeRegexError:
        return None


def _safe_fullmatch(pattern: BoundedPattern, value: str) -> bool:
    """Return a timeout-bounded full-match result."""
    try:
        return bool(fullmatch_bounded_regex(pattern, value))
    except SafeRegexError:
        return False


class VariableService:
    """Service for managing parser variables with CRUD operations."""

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
        cls, variables: list[ParseVariableConfig], var_config: ParseVariableConfig
    ) -> list[ParseVariableConfig]:
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
        cls, variables: list[ParseVariableConfig], index: int, var_config: ParseVariableConfig
    ) -> list[ParseVariableConfig]:
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
            >>> vars = service.update_variable(
            ...     vars, 0, {"name": "new", "type": "vector", "_id": "123"}
            ... )
            >>> vars[0]["name"]
            'new'
        """
        if index < 0 or index >= len(variables):
            raise IndexError(f"Index {index} out of bounds for list of {len(variables)} variables")

        updated_vars = variables.copy()
        updated_vars[index] = var_config
        return updated_vars

    @classmethod
    def delete_variable(
        cls, variables: list[ParseVariableConfig], index: int
    ) -> list[ParseVariableConfig]:
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
    def ensure_variable_ids(cls, variables: list[ParseVariableConfig]) -> list[ParseVariableConfig]:
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
        return normalize_variable_ids(variables)

    @classmethod
    def filter_internal_stats(
        cls,
        entries: list[str],
        internal_stats: frozenset[str],
    ) -> list[str]:
        """
        Filter out internal simulator statistics from entry list.

        Args:
            entries: List of entry names to filter
            internal_stats: Exact case-sensitive summary names from the selected SimulatorInfo.

        Returns:
            Filtered list with internal stats removed, sorted alphabetically

        Examples:
            >>> service = VariableService()
            >>> entries = ["cpu0", "total", "mean", "cpu1", "stdev"]
            >>> internal = frozenset({"total", "mean", "stdev"})
            >>> filtered = service.filter_internal_stats(entries, internal)
            >>> filtered
            ['cpu0', 'cpu1']
        """
        filtered = [entry for entry in entries if entry not in internal_stats]
        return sorted(filtered)

    @classmethod
    def aggregate_discovered_entries(
        cls, snapshot: list[ScannedVariableDict], var_name: str, internal_stats: frozenset[str]
    ) -> list[str]:
        r"""
        Aggregate all discovered entries for a variable across scanned files.

        Args:
            snapshot: List of scanned variable results from multiple files
            var_name: Variable name to aggregate entries for (supports regex)
            internal_stats: Explicit summary names from the selected simulator.

        Returns:
            Sorted list of unique entries with internal stats filtered out

        Examples:
            >>> service = VariableService()
            >>> snapshot = [
            ...     {"name": "system.cpu0.ipc", "entries": ["cpu0", "total"]},
            ...     {"name": "system.cpu1.ipc", "entries": ["cpu1", "mean"]}
            ... ]
            >>> entries = service.aggregate_discovered_entries(
            ...     snapshot, r"system\.cpu\d+\.ipc", frozenset({"total", "mean"}))
            >>> entries
            ['cpu0', 'cpu1']
        """
        found_entries: set[str] = set()
        for var in snapshot:
            name = var.get("name", "")
            entries = var.get("entries", [])

            var_name_match = name == var_name
            if not var_name_match:
                compiled = _compile_safe_pattern(var_name)
                if compiled is not None:
                    var_name_match = _safe_fullmatch(compiled, name)

            if var_name_match and entries:
                found_entries.update(entries)

        return cls.filter_internal_stats(list(found_entries), internal_stats)

    @classmethod
    def parse_comma_separated_entries(cls, entries_str: str) -> list[str]:
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
    def format_entries_as_string(cls, entries: list[str]) -> str:
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

    @classmethod
    def has_variable_with_name(
        cls,
        variables: list[ParseVariableConfig],
        name: str,
    ) -> bool:
        """
        Check if a variable with the given name already exists.

        Args:
            variables: List of variable configurations to check.
            name: Variable name to look for.

        Returns:
            True if a variable with this name exists.

        Examples:
            >>> service = VariableService()
            >>> vars = [{"name": "cpu.ipc"}, {"name": "mem.lat"}]
            >>> service.has_variable_with_name(vars, "cpu.ipc")
            True
            >>> service.has_variable_with_name(vars, "nonexistent")
            False
        """
        return any(v.get("name") == name for v in variables)
