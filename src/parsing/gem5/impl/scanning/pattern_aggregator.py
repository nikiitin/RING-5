r"""
Pattern Aggregator
Consolidates repeated variables with numeric indices into regex pattern variables.

Example:
    system.cpu0.numCycles
    system.cpu1.numCycles
    system.cpu2.numCycles

    → system.cpu\d+.numCycles (vector variable with entries: ["0", "1", "2"])
"""

import logging
import re

from src.core.models.parsing_models import ScannedVariable, SourceInstance
from src.parsing.gem5.models import Gem5ScannedVariable

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
    def aggregate_patterns(variables: list[ScannedVariable]) -> list[ScannedVariable]:
        r"""
        Aggregate variables with repeated numeric patterns into regex patterns.

        Args:
            variables: List of scanned variable models.

        Returns:
            Aggregated list of variable models.

        Scalar families suggest vector output with no measurement entries. Their
        numeric labels and concrete source names live only in ``instances``;
        actual vector/frequency entries remain in ``entries``.
        """
        # Group variables by their pattern signature
        pattern_groups: dict[str, list[tuple[str, ScannedVariable]]] = {}
        non_pattern_vars: list[ScannedVariable] = []

        for var in variables:
            var_name: str = var.name

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
        aggregated_vars: list[ScannedVariable] = []

        for pattern_signature, instances in pattern_groups.items():
            if len(instances) == 1:
                # Only one instance - not a pattern, keep as is
                _, var = instances[0]
                non_pattern_vars.append(var)
            elif len({variable.source_type for _, variable in instances}) > 1:
                # Numeric name similarity does not make different raw stat families interchangeable.
                non_pattern_vars.extend(variable for _, variable in instances)
            else:
                # Multiple compatible instances form one explicit source family.
                aggregated_var = PatternAggregator._create_pattern_variable(
                    pattern_signature, instances
                )
                aggregated_vars.append(aggregated_var)

        # Combine and sort
        result = non_pattern_vars + aggregated_vars
        return sorted(result, key=lambda x: x.name)

    @staticmethod
    def _extract_pattern(var_name: str) -> tuple[str, str] | None:
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
        numeric_parts: list[str] = []

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
        pattern_signature: str, instances: list[tuple[str, ScannedVariable]]
    ) -> ScannedVariable:
        """
        Create a regex pattern variable from multiple instances.

        Args:
            pattern_signature: Pattern signature with {} placeholders
            instances: List of (numeric_id, var_dict) tuples

        Returns:
            Aggregated variable with regex pattern name and vector entries
        """
        # Convert the signature to the canonical, user-facing pattern name. Literal dots stay
        # readable here; safe_regex escapes them only when compiling or sending the filter to
        # Perl, so they never acquire wildcard semantics.
        regex_pattern = pattern_signature.replace("{}", r"\d+")

        # Extract numeric IDs as entries

        first_var = instances[0][1]
        base_type = first_var.source_type
        if any(var.source_type != base_type for _, var in instances):
            raise ValueError(f"Pattern {regex_pattern!r} contains mixed raw source types.")
        source_instances: list[SourceInstance] = []
        for numeric_id, variable in instances:
            if len(variable.instances) != 1 or variable.instances[0].source_name != variable.name:
                raise ValueError("Pattern aggregation requires explicit literal source instances.")
            source_instances.append(
                SourceInstance(variable.instances[0].source_name, tuple(numeric_id.split("_")))
            )
        result_type = "vector" if base_type == "scalar" else base_type
        # Scalar observations have no child entries; their display indices belong to instances.
        result_entries = sorted({entry for _, var in instances for entry in var.entries})

        # Handle distribution min/max if applicable
        kwargs: dict[str, float] = {}
        if base_type == "distribution":
            min_val: float | None = None
            max_val: float | None = None

            for _, var in instances:
                gem5_var = var if isinstance(var, Gem5ScannedVariable) else None
                if gem5_var is not None and gem5_var.minimum is not None:
                    var_min = gem5_var.minimum
                    min_val = var_min if min_val is None else min(min_val, var_min)
                if gem5_var is not None and gem5_var.maximum is not None:
                    var_max = gem5_var.maximum
                    max_val = var_max if max_val is None else max(max_val, var_max)

            if min_val is not None:
                kwargs["minimum"] = min_val
            if max_val is not None:
                kwargs["maximum"] = max_val

        logger.info(f"Aggregated {len(instances)} instances into pattern: {regex_pattern}")

        return Gem5ScannedVariable(
            name=regex_pattern,
            type=result_type,
            source_type=base_type,
            entries=result_entries,
            instances=tuple(source_instances),
            **kwargs,
        )
