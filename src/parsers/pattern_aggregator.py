"""
Pattern Aggregator
Consolidates repeated variables with numeric indices into regex pattern variables.

Example:
    system.cpu0.numCycles
    system.cpu1.numCycles
    system.cpu2.numCycles

    → system.cpu\\d+.numCycles (vector variable with entries: ["0", "1", "2"])
"""

import logging
import re
from typing import Any, Dict, List, Tuple

logger: logging.Logger = logging.getLogger(__name__)


class PatternAggregator:
    """
    Detects and aggregates repeated variable patterns.

    This class handles the common case in gem5 stats where statistics are
    repeated across multiple components with numeric indices
    (e.g., cpu0, cpu1, cpu2, or l0_cntrl0, l0_cntrl1, etc.).

    Instead of treating each as a separate variable, we create a single
    regex pattern variable that captures all instances.
    """

    @staticmethod
    def aggregate_patterns(variables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        r"""
        Aggregate variables with repeated numeric patterns into regex patterns.

        Args:
            variables: List of scanned variables (with name, type, entries, etc.)

        Returns:
            Aggregated list where repeated patterns are consolidated

        Example:
            Input:
                [
                    {"name": "system.cpu0.numCycles", "type": "scalar"},
                    {"name": "system.cpu1.numCycles", "type": "scalar"},
                    {"name": "system.cpu2.numCycles", "type": "scalar"}
                ]

            Output:
                [
                    {
                        "name": "system.cpu\\d+.numCycles",
                        "type": "vector",
                        "entries": ["0", "1", "2"]
                    }
                ]
        """
        # Group variables by their pattern signature
        pattern_groups: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
        non_pattern_vars: List[Dict[str, Any]] = []

        for var in variables:
            var_name: str = var["name"]

            # Try to extract numeric pattern
            pattern_info = PatternAggregator._extract_pattern(var_name)

            if pattern_info is None:
                # No numeric pattern found - keep as is
                non_pattern_vars.append(var)
            else:
                pattern_signature, numeric_id = pattern_info

                if pattern_signature not in pattern_groups:
                    pattern_groups[pattern_signature] = []

                pattern_groups[pattern_signature].append((numeric_id, var))

        # Convert pattern groups to aggregated variables
        aggregated_vars: List[Dict[str, Any]] = []

        for pattern_signature, instances in pattern_groups.items():
            if len(instances) == 1:
                # Only one instance - not a pattern, keep as is
                _, var = instances[0]
                non_pattern_vars.append(var)
            else:
                # Multiple instances - create pattern variable
                aggregated_var = PatternAggregator._create_pattern_variable(
                    pattern_signature, instances
                )
                aggregated_vars.append(aggregated_var)

        # Combine and sort
        result = non_pattern_vars + aggregated_vars
        return sorted(result, key=lambda x: x["name"])

    @staticmethod
    def _extract_pattern(var_name: str) -> Tuple[str, str] | None:
        """
        Extract numeric pattern from variable name.

        Handles cases like:
        - system.cpu0.stat → (system.cpu{}.stat, "0")
        - system.ruby.l0_cntrl1.stat → (system.ruby.l{}_cntrl{}.stat, "0_1")
        - board.xid2.value → (board.xid{}.value, "2")

        Args:
            var_name: Full variable name

        Returns:
            Tuple of (pattern_signature, numeric_id) or None if no pattern

        Note:
            The pattern_signature uses {} as placeholder for numeric parts.
            This allows grouping variables that differ only in numeric IDs.
        """
        # Find all numeric sequences in the name
        # Match numbers that follow letters or underscores (e.g., cpu0, cntrl1, xid2)
        matches = list(re.finditer(r"([a-zA-Z_]+)(\d+)", var_name))

        if not matches:
            return None

        # Build pattern signature by replacing numbers with {}
        pattern_signature = var_name
        numeric_parts: List[str] = []

        # Replace from right to left to maintain positions
        for match in reversed(matches):
            number = match.group(2)

            # Replace the number with placeholder
            start_pos = match.start(2)
            end_pos = match.end(2)
            pattern_signature = pattern_signature[:start_pos] + "{}" + pattern_signature[end_pos:]

            numeric_parts.insert(0, number)

        numeric_id = "_".join(numeric_parts)
        return (pattern_signature, numeric_id)

    @staticmethod
    def _create_pattern_variable(
        pattern_signature: str, instances: List[Tuple[str, Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Create a regex pattern variable from multiple instances.

        Args:
            pattern_signature: Pattern signature with {} placeholders
            instances: List of (numeric_id, var_dict) tuples

        Returns:
            Aggregated variable with regex pattern name and vector entries
        """
        # Convert pattern signature to regex pattern (replace {} with \d+)
        regex_pattern = pattern_signature.replace("{}", r"\d+")

        # Extract numeric IDs as entries
        entries: List[str] = sorted([numeric_id for numeric_id, _ in instances])

        # Get type from first instance (should be consistent)
        first_var = instances[0][1]
        base_type = first_var.get("type", "scalar")

        # If all instances are scalars, the pattern is a vector
        # If instances are already vectors, we need to keep pattern indices AND vector entries
        if base_type == "scalar":
            result_type = "vector"
            result_entries = entries
            # For scalars, store the actual matched variable names for proper reduction
            matched_names = [var["name"] for _, var in instances]
            pattern_indices = matched_names  # Store full variable names, not just numeric IDs
        else:
            # For vectors/histograms/distributions, we need BOTH:
            # - pattern_indices: numeric IDs from variable names (for pattern selection)
            # - entries: the actual vector/histogram entry names (after ::)
            result_type = base_type

            # Pattern indices (numeric IDs from variable names like "0_0", "1_0")
            pattern_indices = entries

            # Collect all unique vector/histogram entries from all instances
            all_entries: set[str] = set()
            for _, var in instances:
                if "entries" in var:
                    all_entries.update(var["entries"])

            result_entries = sorted(list(all_entries))

        result: Dict[str, Any] = {
            "name": regex_pattern,
            "type": result_type,
            "entries": result_entries,
        }

        # Add pattern indices for non-scalar patterns (vectors, histograms, distributions)
        if pattern_indices is not None:
            result["pattern_indices"] = pattern_indices

        # Handle distribution min/max if applicable
        if base_type == "distribution":
            min_val: float | None = None
            max_val: float | None = None

            for _, var in instances:
                if "minimum" in var:
                    var_min = var["minimum"]
                    min_val = var_min if min_val is None else min(min_val, var_min)
                if "maximum" in var:
                    var_max = var["maximum"]
                    max_val = var_max if max_val is None else max(max_val, var_max)

            if min_val is not None:
                result["minimum"] = min_val
            if max_val is not None:
                result["maximum"] = max_val

        logger.info(f"Aggregated {len(instances)} instances into pattern: {regex_pattern}")

        return result
