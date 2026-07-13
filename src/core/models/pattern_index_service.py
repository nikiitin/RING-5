r"""
Pattern Index Service for RING-5.

Provides pure business logic for pattern variable index operations.
Pattern variables (e.g., system.ruby.l\d+_cntrl\d+.stat) contain regex
placeholders that match multiple hardware components. This service handles:
- Detection of pattern variables
- Extraction of position labels from pattern names
- Parsing of entry indices into structured position→value mappings
- Filtering entries based on user selections
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
    - Entry filtering by selected indices
    - Display formatting
    """

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
    def parse_entry_indices(entries: list[str]) -> dict[int, set[str]]:
        """
        Parse entries to extract unique indices at each position.

        Args:
            entries: List like ["0_0", "0_1", "1_0", "1_1", "2_0"]

        Returns:
            Dict mapping position index to set of values:
            {0: {"0", "1", "2"}, 1: {"0", "1"}}

        Examples:
            >>> result = PatternIndexService.parse_entry_indices(
            ...     ["0_0", "0_1", "1_0"]
            ... )
            >>> result[0] == {"0", "1"}
            True
            >>> result[1] == {"0", "1"}
            True
            >>> PatternIndexService.parse_entry_indices([])
            {}
        """
        if not entries:
            return {}

        # Parse first entry to determine structure
        first_entry = entries[0]
        parts = first_entry.split("_")
        num_positions = len(parts)

        # Collect all values at each position
        position_values: dict[int, set[str]] = {i: set() for i in range(num_positions)}

        for entry in entries:
            parts = entry.split("_")
            # Handle entries with different numbers of parts
            for i, part in enumerate(parts):
                if i not in position_values:
                    position_values[i] = set()
                position_values[i].add(part)

        return position_values

    @staticmethod
    def filter_entries(entries: list[str], selections: dict[int, list[str]]) -> list[str]:
        """
        Filter entries based on selected indices at each position.

        Args:
            entries: All available entries (e.g., ["0_0", "0_1", "1_0"])
            selections: Selected indices per position
                        {0: ["0"], 1: ["0", "1"]}

        Returns:
            Filtered entries matching the selection

        Examples:
            >>> PatternIndexService.filter_entries(
            ...     ["0_0", "0_1", "1_0", "1_1"],
            ...     {0: ["0"], 1: ["0", "1"]}
            ... )
            ['0_0', '0_1']
            >>> PatternIndexService.filter_entries(
            ...     ["0_0", "0_1", "1_0"],
            ...     {0: []}
            ... )
            []
        """
        filtered: list[str] = []

        for entry in entries:
            parts = entry.split("_")

            # Check if entry matches all position selections
            matches = True
            for pos_idx, selected_values in selections.items():
                if not selected_values:  # No selection means exclude all
                    matches = False
                    break

                if pos_idx < len(parts):
                    if parts[pos_idx] not in selected_values:
                        matches = False
                        break

            if matches:
                filtered.append(entry)

        return filtered

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

    @staticmethod
    def reconstruct_concrete_name(pattern_name: str, numeric_id: str) -> str:
        r"""
        Reconstruct a concrete variable name from a regex pattern and numeric ID.

        Inverse of ``PatternAggregator._extract_pattern``: replaces each
        ``\d+`` placeholder in the pattern with the corresponding number
        from the numeric ID (underscore-separated).

        Args:
            pattern_name: Regex pattern (e.g., ``system.cpu\d+.ipc`` or
                          ``system.ruby.l\d+_cntrl\d+.stat``).
            numeric_id: Underscore-separated numeric parts (e.g., ``"3"``
                        or ``"0_1"``).

        Returns:
            Concrete variable name with numbers substituted in.

        Raises:
            ValueError: If the number of ``\d+`` placeholders does not match
                        the number of parts in *numeric_id*.

        Examples:
            >>> PatternIndexService.reconstruct_concrete_name(
            ...     r"system.cpu\d+.ipc", "3"
            ... )
            'system.cpu3.ipc'
            >>> PatternIndexService.reconstruct_concrete_name(
            ...     r"system.ruby.l\d+_cntrl\d+.stat", "0_1"
            ... )
            'system.ruby.l0_cntrl1.stat'
        """
        parts = numeric_id.split("_")
        marker = r"\d+"
        segments = pattern_name.split(marker)

        if len(segments) - 1 != len(parts):
            raise ValueError(
                f"Pattern '{pattern_name}' has {len(segments) - 1} placeholder(s) "
                f"but numeric_id '{numeric_id}' has {len(parts)} part(s)."
            )

        result: list[str] = []
        for i, seg in enumerate(segments):
            result.append(seg)
            if i < len(parts):
                result.append(parts[i])

        return "".join(result)
