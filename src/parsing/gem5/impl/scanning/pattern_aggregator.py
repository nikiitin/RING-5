r"""
Pattern Aggregator
Consolidates repeated variables with numeric indices into regex pattern variables.

Example:
    system.cpu0.numCycles
    system.cpu1.numCycles
    system.cpu2.numCycles

    → system.cpu\d+.numCycles (vector suggestion with explicit source instances)
"""

import logging
import re

from src.core.models.parsing_models import ScannedVariable, SourceInstance
from functools import reduce
from src.core.models.source_evidence import (
    ResolvedSourceKind,
    intersect_source_kind_evidence,
)

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
            else:
                try:
                    aggregated_var = PatternAggregator._create_pattern_variable(
                        pattern_signature, instances
                    )
                except ValueError as exc:
                    if type(exc) is not ValueError:
                        raise
                    non_pattern_vars.extend(variable for _, variable in instances)
                else:
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
            Pattern with intersected evidence, source instances and printed labels
        """
        # Literal punctuation stays readable in the canonical pattern name. Matching escapes
        # it before expanding numeric placeholders; workers receive explicit source names.
        regex_pattern = pattern_signature.replace("{}", r"\d+")

        evidence = reduce(
            intersect_source_kind_evidence,
            (variable.source_evidence for _, variable in instances),
        )
        source_instances: list[SourceInstance] = []
        for numeric_id, variable in instances:
            if len(variable.instances) != 1 or variable.instances[0].source_name != variable.name:
                raise ValueError("Pattern aggregation requires explicit literal source instances.")
            source_instances.append(
                SourceInstance(variable.instances[0].source_name, tuple(numeric_id.split("_")))
            )
        result_type = (
            ("vector" if evidence.kind == "scalar" else evidence.kind)
            if type(evidence) is ResolvedSourceKind
            else None
        )
        result_entries = sorted({entry for _, var in instances for entry in var.entries})
        logger.info("Aggregated %d instances into pattern: %s", len(instances), regex_pattern)
        return ScannedVariable(
            name=regex_pattern,
            type=result_type,
            source_evidence=evidence,
            entries=result_entries,
            instances=tuple(source_instances),
        )
