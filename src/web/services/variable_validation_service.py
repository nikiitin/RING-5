"""
Variable Validation Service for RING-5.

Centralizes all validation logic for gem5 variable configurations.
This service is stateless and UI-independent, enabling comprehensive unit testing.
"""

from typing import Any, Dict, List

import re


class VariableValidationService:
    """
    Service for validating gem5 variable configurations.

    This service provides centralized validation logic extracted from variable_editor.py.
    All methods are static and stateless, making them easily testable without UI dependencies.

    **Design Pattern**: Service Layer (stateless validation)

    **Usage Example**:
        ```python
        # Validate scalar
        errors = VariableValidationService.validate_variable({
            "name": "system.cpu.ipc",
            "type": "scalar"
        })
        if errors:
            for error in errors:
                print(f"Error: {error}")

        # Validate vector
        errors = VariableValidationService.validate_vector_config({
            "name": "system.cpu.dcache.miss_rate",
            "type": "vector",
            "entries": ["read", "write"]
        })
        ```

    **Validation Categories**:
    - Variable name format (gem5 path syntax)
    - Required fields by type
    - Entry selection for vectors/histograms
    - Range validity for distributions/histograms
    - Statistics selection
    """

    # gem5 internal statistics that should be filtered from entry lists
    INTERNAL_STATS: set[str] = {
        "total",
        "mean",
        "gmean",
        "stdev",
        "samples",
        "overflows",
        "underflows",
    }

    @staticmethod
    def validate_variable(var_config: Dict[str, Any]) -> List[str]:
        """
        Validate a variable configuration.

        Performs comprehensive validation based on variable type and checks for:
        - Required fields present
        - Name format validity
        - Type-specific requirements

        Args:
            var_config: Variable configuration dictionary with keys:
                - name (str): Variable name (required)
                - type (str): Variable type (required)
                - Additional type-specific fields

        Returns:
            List of error messages (empty if valid)

        Raises:
            None (returns errors as strings)

        Example:
            >>> config = {"name": "system.cpu.ipc", "type": "scalar"}
            >>> errors = VariableValidationService.validate_variable(config)
            >>> assert len(errors) == 0
        """
        errors: List[str] = []

        # Check required fields
        if not var_config.get("name"):
            errors.append("Variable name is required")
        if not var_config.get("type"):
            errors.append("Variable type is required")

        if errors:
            return errors

        var_name = var_config["name"]
        var_type = var_config["type"]

        # Validate name format
        name_errors = VariableValidationService.validate_variable_name(var_name)
        errors.extend(name_errors)

        # Type-specific validation
        if var_type == "vector":
            errors.extend(VariableValidationService.validate_vector_config(var_config))
        elif var_type == "histogram":
            errors.extend(VariableValidationService.validate_histogram_config(var_config))
        elif var_type == "distribution":
            errors.extend(VariableValidationService.validate_distribution_config(var_config))
        elif var_type == "configuration":
            errors.extend(VariableValidationService.validate_configuration_config(var_config))
        elif var_type != "scalar":
            errors.append(f"Unknown variable type: {var_type}")

        return errors

    @staticmethod
    def validate_variable_name(name: str) -> List[str]:
        """
        Validate variable name format.

        gem5 variable names should follow the pattern: system.component.stat
        Can include regex patterns for matching multiple variables.

        Args:
            name: Variable name to validate

        Returns:
            List of error messages (empty if valid)

        Example:
            >>> errors = VariableValidationService.validate_variable_name("system.cpu.ipc")
            >>> assert len(errors) == 0
            >>> errors = VariableValidationService.validate_variable_name("")
            >>> assert len(errors) > 0
        """
        errors: List[str] = []

        if not name:
            errors.append("Variable name cannot be empty")
            return errors

        # Check for invalid characters (allow regex patterns)
        # Valid: alphanumeric, underscore, dot, hyphen, regex metacharacters
        if not re.match(r"^[a-zA-Z0-9_.\-\[\](){}*+?\\^$|]+$", name):
            errors.append(
                f"Invalid variable name format: '{name}'. "
                "Use gem5 path syntax (e.g., system.cpu.ipc)"
            )

        return errors

    @staticmethod
    def validate_vector_config(var_config: Dict[str, Any]) -> List[str]:
        """
        Validate vector variable configuration.

        Vectors require either:
        - entries: List of specific entry names
        - useSpecialMembers: true with statistics selected

        Args:
            var_config: Vector configuration with keys:
                - name (str): Variable name
                - type (str): Must be "vector"
                - entries (List[str], optional): Entry names
                - useSpecialMembers (bool, optional): Use statistics instead
                - statistics (List[str], optional): Statistics to extract

        Returns:
            List of error messages (empty if valid)

        Example:
            >>> config = {
            ...     "name": "system.cpu.dcache.miss_rate",
            ...     "type": "vector",
            ...     "entries": ["read", "write"]
            ... }
            >>> errors = VariableValidationService.validate_vector_config(config)
            >>> assert len(errors) == 0
        """
        errors: List[str] = []

        # Check for entries or useSpecialMembers
        has_entries = "entries" in var_config and var_config.get("entries") is not None
        use_special = var_config.get("useSpecialMembers", False)

        if not has_entries and not use_special:
            errors.append(
                "Vector variables require either 'entries' or 'useSpecialMembers' to be set"
            )

        # If using special members, check statistics are selected
        if use_special:
            stats = var_config.get("statistics", [])
            if not stats:
                errors.append("When using special members, at least one statistic must be selected")

        # Validate entries if present
        if has_entries:
            entries = var_config.get("entries", [])
            if isinstance(entries, list):
                if len(entries) == 0:
                    errors.append("At least one entry must be selected for vector variables")
                # Filter out internal stats
                filtered = VariableValidationService.filter_internal_stats(entries)
                if len(filtered) == 0 and not use_special:
                    errors.append("No valid entries selected (only internal statistics found)")
            else:
                errors.append("Vector 'entries' must be a list")

        return errors

    @staticmethod
    def validate_histogram_config(var_config: Dict[str, Any]) -> List[str]:
        """
        Validate histogram variable configuration.

        Histograms require entries (bucket names) and optionally support rebinning.

        Args:
            var_config: Histogram configuration with keys:
                - name (str): Variable name
                - type (str): Must be "histogram"
                - entries (List[str], optional): Bucket names or statistics
                - useSpecialMembers (bool, optional): Use statistics
                - statistics (List[str], optional): Statistics to extract
                - enableRebin (bool, optional): Enable rebinning
                - bins (int, optional): Target number of bins for rebinning
                - max_range (float, optional): Maximum range for rebinning

        Returns:
            List of error messages (empty if valid)

        Example:
            >>> config = {
            ...     "name": "system.cpu.latency",
            ...     "type": "histogram",
            ...     "entries": ["0-10", "10-20", "20-30"],
            ...     "enableRebin": True,
            ...     "bins": 10,
            ...     "max_range": 100.0
            ... }
            >>> errors = VariableValidationService.validate_histogram_config(config)
            >>> assert len(errors) == 0
        """
        errors: List[str] = []

        # Histograms have similar requirements to vectors
        has_entries = "entries" in var_config and var_config.get("entries") is not None
        use_special = var_config.get("useSpecialMembers", False)

        if not has_entries and not use_special:
            errors.append(
                "Histogram variables require either 'entries' or 'useSpecialMembers' to be set"
            )

        # If using special members, check statistics
        if use_special:
            stats = var_config.get("statistics", [])
            if not stats:
                errors.append("When using special members, at least one statistic must be selected")

        # Validate entries if present
        if has_entries:
            entries = var_config.get("entries", [])
            if isinstance(entries, list):
                if len(entries) == 0:
                    errors.append("At least one entry must be selected for histogram variables")
            else:
                errors.append("Histogram 'entries' must be a list")

        # Validate rebinning configuration if enabled
        if var_config.get("enableRebin", False):
            bins = var_config.get("bins")
            max_range = var_config.get("max_range")

            if bins is None:
                errors.append("Rebinning requires 'bins' to be specified")
            elif not isinstance(bins, int) or bins < 1:
                errors.append("Rebinning 'bins' must be a positive integer")

            if max_range is None:
                errors.append("Rebinning requires 'max_range' to be specified")
            elif not isinstance(max_range, (int, float)) or max_range <= 0:
                errors.append("Rebinning 'max_range' must be a positive number")

        return errors

    @staticmethod
    def validate_distribution_config(var_config: Dict[str, Any]) -> List[str]:
        """
        Validate distribution variable configuration.

        Distributions require minimum and maximum range values.

        Args:
            var_config: Distribution configuration with keys:
                - name (str): Variable name
                - type (str): Must be "distribution"
                - minimum (float): Minimum bucket value
                - maximum (float): Maximum bucket value
                - statistics (List[str], optional): Additional statistics

        Returns:
            List of error messages (empty if valid)

        Example:
            >>> config = {
            ...     "name": "system.cpu.latency_dist",
            ...     "type": "distribution",
            ...     "minimum": 0,
            ...     "maximum": 1000
            ... }
            >>> errors = VariableValidationService.validate_distribution_config(config)
            >>> assert len(errors) == 0
        """
        errors: List[str] = []

        # Check for minimum and maximum
        if "minimum" not in var_config:
            errors.append("Distribution requires 'minimum' value")
        if "maximum" not in var_config:
            errors.append("Distribution requires 'maximum' value")

        if "minimum" in var_config and "maximum" in var_config:
            min_val = var_config["minimum"]
            max_val = var_config["maximum"]

            # Validate types
            if not isinstance(min_val, (int, float)):
                errors.append("Distribution 'minimum' must be a number")
            if not isinstance(max_val, (int, float)):
                errors.append("Distribution 'maximum' must be a number")

            # Validate range
            if isinstance(min_val, (int, float)) and isinstance(max_val, (int, float)):
                if min_val >= max_val:
                    errors.append(
                        f"Distribution 'minimum' ({min_val}) must be less than 'maximum' ({max_val})"  # noqa: E501
                    )

        return errors

    @staticmethod
    def validate_configuration_config(var_config: Dict[str, Any]) -> List[str]:
        """
        Validate configuration variable configuration.

        Configuration variables are simple key-value pairs from gem5 config.

        Args:
            var_config: Configuration with keys:
                - name (str): Configuration key name
                - type (str): Must be "configuration"
                - onEmpty (str, optional): Default value if not found

        Returns:
            List of error messages (empty if valid)

        Example:
            >>> config = {
            ...     "name": "system.cpu.clock",
            ...     "type": "configuration",
            ...     "onEmpty": "1GHz"
            ... }
            >>> errors = VariableValidationService.validate_configuration_config(config)
            >>> assert len(errors) == 0
        """
        # Configuration variables have minimal requirements
        # Just name validation (already done in validate_variable)
        return []

    @staticmethod
    def filter_internal_stats(entries: List[str]) -> List[str]:
        """
        Filter out gem5 internal statistics from entry list.

        gem5 provides special statistics like 'total', 'mean', 'stdev' that are
        extracted separately via the statistics checkboxes. This method removes
        them from entry lists to avoid duplication.

        Args:
            entries: List of entry names

        Returns:
            Filtered list with internal stats removed

        Example:
            >>> entries = ["read", "write", "total", "mean", "stdev"]
            >>> filtered = VariableValidationService.filter_internal_stats(entries)
            >>> assert filtered == ["read", "write"]
        """
        return [e for e in entries if e.lower() not in VariableValidationService.INTERNAL_STATS]

    @staticmethod
    def validate_statistics_selection(statistics: List[str]) -> List[str]:
        """
        Validate that selected statistics are valid gem5 statistics.

        Args:
            statistics: List of statistic names

        Returns:
            List of error messages (empty if valid)

        Example:
            >>> stats = ["mean", "stdev", "samples"]
            >>> errors = VariableValidationService.validate_statistics_selection(stats)
            >>> assert len(errors) == 0
        """
        errors: List[str] = []

        valid_stats = {"total", "mean", "gmean", "stdev", "samples", "overflows", "underflows"}

        for stat in statistics:
            if stat not in valid_stats:
                errors.append(
                    f"Invalid statistic: '{stat}'. Valid options: {', '.join(sorted(valid_stats))}"
                )

        return errors

    @staticmethod
    def validate_batch(var_configs: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Validate multiple variable configurations at once.

        Args:
            var_configs: List of variable configurations

        Returns:
            Dictionary mapping variable index to list of errors
            (only includes entries for variables with errors)

        Example:
            >>> configs = [
            ...     {"name": "system.cpu.ipc", "type": "scalar"},
            ...     {"name": "", "type": "vector"}  # Invalid
            ... ]
            >>> errors = VariableValidationService.validate_batch(configs)
            >>> assert 1 in errors  # Second variable has errors
            >>> assert 0 not in errors  # First variable is valid
        """
        results: Dict[str, List[str]] = {}

        for idx, var_config in enumerate(var_configs):
            errors = VariableValidationService.validate_variable(var_config)
            if errors:
                results[str(idx)] = errors

        return results
