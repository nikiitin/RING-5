"""
Pattern Index Selector Component
Allows users to select specific indices from pattern variables (e.g., l{0,1}_cntrl{1,2,3})

UI-only thin wrapper around PatternIndexService (Layer B).
"""

import streamlit as st

from src.core.models.pattern_index_service import PatternIndexService
from src.web.components.common.filtered_selector import filtered_multiselect


class PatternIndexSelector:
    r"""
    UI component for selecting specific indices from pattern variables.

    Delegates all pure logic to PatternIndexService (Layer B).
    For patterns like system.ruby.l\d+_cntrl\d+.stat with entries like ["0_0", "0_1", "1_0", "1_1"],
    this allows users to select:
    - All indices: l{all}_cntrl{all} → ["0_0", "0_1", "1_0", "1_1"]
    - Specific first index: l{0}_cntrl{all} → ["0_0", "0_1"]
    - Specific both: l{1}_cntrl{0,1} → ["1_0", "1_1"]
    """

    @staticmethod
    def is_pattern_variable(var_name: str) -> bool:
        r"""Check if variable name contains regex pattern (\d+). Delegates to service."""
        return PatternIndexService.is_pattern_variable(var_name)

    @staticmethod
    def extract_index_positions(var_name: str) -> list[str]:
        r"""Extract position labels from pattern variable name. Delegates to service."""
        return PatternIndexService.extract_index_positions(var_name)

    @staticmethod
    def parse_entry_indices(entries: list[str]) -> dict[int, set[str]]:
        """Parse entries to extract unique indices at each position. Delegates to service."""
        return PatternIndexService.parse_entry_indices(entries)

    @classmethod
    def render_selector(
        cls,
        var_name: str,
        entries: list[str],
        var_id: str,
        current_selection: list[str] | dict[int, list[str]] | None = None,
    ) -> tuple[bool, list[str]]:
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
        # [impl->req~ring5.ingestion.pattern-index-selection~1]
        if not cls.is_pattern_variable(var_name):
            return False, entries

        # Extract position info (delegated to service)
        positions = PatternIndexService.extract_index_positions(var_name)
        position_values = PatternIndexService.parse_entry_indices(entries)

        if not positions or not position_values:
            return False, entries

        st.markdown("**Pattern Index Selection:**")
        st.caption(f"Variable: `{var_name}`")

        # Option to use all entries or filter
        use_filter = st.checkbox(
            "Select specific indices",
            value=current_selection is not None,
            key=f"use_pattern_filter_{var_id}",
            help=(
                "Filter which pattern indices to parse "
                "(e.g., only L0 caches, specific controllers)"
            ),
        )

        if not use_filter:
            st.info(f"Will parse ALL {len(entries)} matching instances")
            return False, entries

        # Persist concrete entries so correlated multi-position selections remain exact.
        if isinstance(current_selection, list):
            defaults = [entry for entry in current_selection if entry in entries]
        elif isinstance(current_selection, dict):
            selections = {int(position): values for position, values in current_selection.items()}
            defaults = PatternIndexService.filter_entries(entries, selections)
        else:
            defaults = entries
        filtered_entries = filtered_multiselect(
            "Instances to include",
            options=entries,
            default=defaults,
            key=f"pattern_entries_{var_id}",
            format_func=lambda entry: PatternIndexService.format_entry_display(entry, positions),
            help="Select exact instances and preserve correlated choices across index positions.",
        )

        # Show summary
        if filtered_entries:
            st.success(f"✅ Will parse {len(filtered_entries)}/{len(entries)} instances")

            # Show examples
            if len(filtered_entries) <= 10:
                examples = filtered_entries
            else:
                examples = filtered_entries[:5] + ["..."] + filtered_entries[-2:]

            with st.expander("Show selected instances"):
                for entry in examples:
                    if entry != "...":
                        formatted = PatternIndexService.format_entry_display(entry, positions)
                        st.code(formatted, language="")
        else:
            st.error("❌ No instances match the current selection!")

        return use_filter, filtered_entries

    @staticmethod
    def _filter_entries(entries: list[str], selections: dict[int, list[str]]) -> list[str]:
        """Filter entries based on selected indices. Delegates to service."""
        return PatternIndexService.filter_entries(entries, selections)

    @staticmethod
    def _format_entry_display(entry: str, positions: list[str]) -> str:
        """Format entry for display. Delegates to service."""
        return PatternIndexService.format_entry_display(entry, positions)
