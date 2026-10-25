r"""
Pattern Index Service for RING-5.

Provides pure business logic for pattern variable index operations.
Pattern variables (e.g., system.ruby.l\d+_cntrl\d+.stat) contain regex
placeholders that match multiple hardware components. This service handles:
- Detection of pattern variables
- Extraction of position labels from pattern names
- Formatting entries for display

All functions are pure (no UI dependencies, no side effects).

Lives in the models layer (Layer A, the shared "common language") because it
is a pure, stateless algorithm with no domain/service collaborators — so both
parsing (Layer A) and the web layer use it without an upward dependency.

Usage Example:
    >>> from src.core.models.pattern_index_service import (
    ...     PatternIndexService,
    ... )
    >>> PatternIndexService.is_pattern_variable(r"system.ruby.l\\d+_cntrl\\d+.stat")
    True
    >>> PatternIndexService.extract_index_positions(r"system.ruby.l\\d+_cntrl\\d+.stat")
    ['l', 'cntrl']
"""


class PatternIndexService:
    r"""
    Pure business logic for pattern variable index operations.

    For patterns like system.ruby.l\d+_cntrl\d+.stat with entries like
    ["0_0", "0_1", "1_0", "1_1"], this service provides:
    - Index detection
    - Position extraction
    - Display formatting
    """

    # [impl->req~ring5.ingestion.pattern-index-selection~1]

    @staticmethod
    def is_pattern_variable(var_name: str) -> bool:
        r"""Check if variable name contains regex pattern (\d+).

        Args:
            var_name: Variable name to check

        Returns:
            True if the variable contains \\d+ pattern

        Examples:
            >>> PatternIndexService.is_pattern_variable(r"system.ruby.l\\d+.stat")
            True
            >>> PatternIndexService.is_pattern_variable("system.cpu.ipc")
            False
        """
        return r"\d+" in var_name

    @staticmethod
    def extract_index_positions(var_name: str) -> list[str]:
        r"""
        Extract position labels from pattern variable name.

        Finds all positions where \\d+ appears and extracts the preceding
        label (identifier). Uses string splitting instead of regex to avoid
        ReDoS on user input.

        Args:
            var_name: Pattern like r"system.ruby.l\\d+_cntrl\\d+.stat"

        Returns:
            List of position labels like ["l", "cntrl"]

        Examples:
            >>> PatternIndexService.extract_index_positions(
            ...     r"system.ruby.l\\d+_cntrl\\d+.stat"
            ... )
            ['l', 'cntrl']
            >>> PatternIndexService.extract_index_positions("system.cpu.ipc")
            []
        """
        cleaned: list[str] = []
        marker = r"\d+"
        parts = var_name.split(marker)
        # Each part (except the last) ends with the label before \d+
        for part in parts[:-1]:
            # Extract trailing identifier: letters/underscores before the split
            label = ""
            for ch in reversed(part):
                if ch.isalpha() or ch == "_":
                    label = ch + label
                else:
                    break
            # Remove leading underscores (e.g., "_cntrl" -> "cntrl")
            label = label.lstrip("_")
            if label:
                cleaned.append(label)

        return cleaned

    @staticmethod
    def format_entry_display(entry: str, positions: list[str]) -> str:
        """
        Format entry for display (e.g., "0_1" -> "l{0}_cntrl{1}").

        Args:
            entry: Entry like "0_1"
            positions: Position labels like ["l", "cntrl"]

        Returns:
            Formatted string for display

        Examples:
            >>> PatternIndexService.format_entry_display("0_1", ["l", "cntrl"])
            'l{0}_cntrl{1}'
            >>> PatternIndexService.format_entry_display("2", ["cpu"])
            'cpu{2}'
            >>> PatternIndexService.format_entry_display("0_1_2", ["l", "cntrl"])
            'l{0}_cntrl{1}_2'
        """
        parts = entry.split("_")
        formatted_parts: list[str] = []

        for i, part in enumerate(parts):
            if i < len(positions):
                formatted_parts.append(f"{positions[i]}{{{part}}}")
            else:
                formatted_parts.append(part)

        return "_".join(formatted_parts)
