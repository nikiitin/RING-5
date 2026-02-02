"""
Pattern Index Selector Component
Allows users to select specific indices from pattern variables (e.g., l{0,1}_cntrl{1,2,3})
"""

import re
from typing import Dict, List, Optional, Tuple

import streamlit as st


class PatternIndexSelector:
    r"""
    Component for selecting specific indices from pattern variables.

    For patterns like system.ruby.l\d+_cntrl\d+.stat with entries like ["0_0", "0_1", "1_0", "1_1"],
    this allows users to select:
    - All indices: l{all}_cntrl{all} → ["0_0", "0_1", "1_0", "1_1"]
    - Specific first index: l{0}_cntrl{all} → ["0_0", "0_1"]
    - Specific both: l{1}_cntrl{0,1} → ["1_0", "1_1"]
    """

    @staticmethod
    def is_pattern_variable(var_name: str) -> bool:
        r"""Check if variable name contains regex pattern (\d+)."""
        return r"\d+" in var_name

    @staticmethod
    def extract_index_positions(var_name: str) -> List[str]:
        r"""
        Extract position labels from pattern variable name.

        Args:
            var_name: Pattern like r"system.ruby.l\d+_cntrl\d+.stat"

        Returns:
            List of position labels like ["l", "cntrl"]
        """
        # Find all pattern positions with their context
        # Look for word\d+ pattern (not including preceding underscore)
        # We want to match: word characters followed by \d+, but not including leading _
        pattern = r"(?:^|\.)([a-zA-Z][a-zA-Z0-9_]*)\\d\+"
        matches = re.findall(pattern, var_name)

        # Also check for underscore-prefixed patterns like _cntrl\d+
        pattern_with_underscore = r"_([a-zA-Z][a-zA-Z0-9_]*)\\d\+"
        matches.extend(re.findall(pattern_with_underscore, var_name))

        return matches

    @staticmethod
    def parse_entry_indices(entries: List[str]) -> Dict[int, set[str]]:
        """
        Parse entries to extract unique indices at each position.

        Args:
            entries: List like ["0_0", "0_1", "1_0", "1_1", "2_0"]

        Returns:
            Dict mapping position index to set of values:
            {0: {"0", "1", "2"}, 1: {"0", "1"}}
        """
        if not entries:
            return {}

        # Parse first entry to determine structure
        first_entry = entries[0]
        parts = first_entry.split("_")
        num_positions = len(parts)

        # Collect all values at each position
        position_values: Dict[int, set[str]] = {i: set() for i in range(num_positions)}

        for entry in entries:
            parts = entry.split("_")
            for i, part in enumerate(parts):
                position_values[i].add(part)

        return position_values

    @classmethod
    def render_selector(
        cls,
        var_name: str,
        entries: List[str],
        var_id: str,
        current_selection: Optional[Dict[int, List[str]]] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Render pattern index selector UI.

        Args:
            var_name: Pattern variable name
            entries: All available entries (e.g., ["0_0", "0_1", "1_0"])
            var_id: Unique ID for UI components
            current_selection: Previously selected indices per position

        Returns:
            Tuple of (use_filter, filtered_entries)
            - use_filter: True if user wants to filter indices
            - filtered_entries: Entries matching the selection
        """
        if not cls.is_pattern_variable(var_name):
            return False, entries

        # Extract position info
        positions = cls.extract_index_positions(var_name)
        position_values = cls.parse_entry_indices(entries)

        if not positions or not position_values:
            return False, entries

        st.markdown("**🎯 Pattern Index Selection:**")
        st.caption(f"Variable: `{var_name}`")

        # Option to use all entries or filter
        use_filter = st.checkbox(
            "Select specific indices",
            value=current_selection is not None,
            key=f"use_pattern_filter_{var_id}",
            help="Filter which pattern indices to parse (e.g., only L0 caches, specific controllers)",
        )

        if not use_filter:
            st.info(f"📦 Will parse ALL {len(entries)} matching instances")
            return False, entries

        # Render selection for each position
        st.markdown("**Select which indices to include:**")

        selections: Dict[int, List[str]] = {}

        for pos_idx, pos_label in enumerate(positions):
            if pos_idx not in position_values:
                continue

            available = sorted(
                list(position_values[pos_idx]), key=lambda x: int(x) if x.isdigit() else x
            )

            # Determine defaults
            if current_selection and pos_idx in current_selection:
                defaults = [v for v in current_selection[pos_idx] if v in available]
            else:
                defaults = available  # All by default

            col1, col2 = st.columns([1, 4])

            with col1:
                st.markdown(f"**`{pos_label}{{...}}`**")

            with col2:
                selected = st.multiselect(
                    f"Indices for {pos_label}",
                    options=available,
                    default=defaults,
                    key=f"pattern_pos_{pos_idx}_{var_id}",
                    label_visibility="collapsed",
                    help=f"Select which {pos_label} indices to parse",
                )

                if not selected:
                    st.warning(f"⚠️ No {pos_label} indices selected!")
                else:
                    st.caption(f"✓ Selected {len(selected)}/{len(available)} indices")

                selections[pos_idx] = selected

        # Filter entries based on selections
        filtered_entries = cls._filter_entries(entries, selections)

        # Show summary
        if filtered_entries:
            st.success(f"✅ Will parse {len(filtered_entries)}/{len(entries)} instances")

            # Show examples
            if len(filtered_entries) <= 10:
                examples = filtered_entries
            else:
                examples = filtered_entries[:5] + ["..."] + filtered_entries[-2:]

            with st.expander("📋 Show selected instances"):
                for entry in examples:
                    if entry != "...":
                        formatted = cls._format_entry_display(entry, positions)
                        st.code(formatted, language="")
        else:
            st.error("❌ No instances match the current selection!")

        return use_filter, filtered_entries

    @staticmethod
    def _filter_entries(entries: List[str], selections: Dict[int, List[str]]) -> List[str]:
        """
        Filter entries based on selected indices.

        Args:
            entries: All available entries (e.g., ["0_0", "0_1", "1_0"])
            selections: Selected indices per position {0: ["0"], 1: ["0", "1"]}

        Returns:
            Filtered entries matching the selection
        """
        filtered = []

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
    def _format_entry_display(entry: str, positions: List[str]) -> str:
        """
        Format entry for display (e.g., "0_1" → "l{0}_cntrl{1}").

        Args:
            entry: Entry like "0_1"
            positions: Position labels like ["l", "cntrl"]

        Returns:
            Formatted string for display
        """
        parts = entry.split("_")
        formatted_parts = []

        for i, part in enumerate(parts):
            if i < len(positions):
                formatted_parts.append(f"{positions[i]}{{{part}}}")
            else:
                formatted_parts.append(part)

        return "_".join(formatted_parts)
