"""Select concrete source identities while displaying their numeric coordinates."""

import streamlit as st

from src.core.models.data_models import SourceInstanceDict
from src.core.models.parsing_models import SourceInstance
from src.core.models.pattern_index_service import PatternIndexService
from src.web.components.common.filtered_selector import filtered_multiselect


class PatternIndexSelector:
    """Render the single current concrete-source selection contract."""

    @staticmethod
    def render_selector(
        var_name: str,
        instances: list[SourceInstanceDict],
        var_id: str,
        current_selection: list[str] | None = None,
    ) -> tuple[bool, list[str]]:
        """Show numeric labels without using them as source identifiers.

        Args:
            var_name: Scanner-generated numeric pattern used for display labels.
            instances: Explicit concrete source records from current scan metadata.
            var_id: Stable UI identifier.
            current_selection: Selected concrete source names, or all sources when omitted.

        Returns:
            Whether a selection is active and its exact concrete source names.

        Raises:
            TypeError: A selection uses a retired or incorrectly typed representation.
            ValueError: Source records are malformed or duplicated.
        """
        # [impl->req~ring5.ingestion.pattern-index-selection~1]
        records = [SourceInstance.from_dict(value) for value in instances]
        by_name = {record.source_name: record for record in records}
        if len(by_name) != len(records):
            raise ValueError("Pattern source records must have unique concrete names.")
        if current_selection is not None and (
            not isinstance(current_selection, list)
            or any(not isinstance(value, str) for value in current_selection)
        ):
            raise TypeError("Pattern selections must be concrete source name lists.")
        sources = list(by_name)
        st.markdown("**Pattern Instance Selection:**")
        use_filter = st.checkbox(
            "Select specific instances",
            value=current_selection is not None,
            key=f"use_pattern_filter_{var_id}",
        )
        if not use_filter:
            st.info(f"Will parse all {len(sources)} matching source instances")
            return False, sources
        if current_selection is not None and set(current_selection) - set(sources):
            st.error("Some selected concrete sources are absent from the current scan metadata.")
            return True, list(current_selection)
        positions = PatternIndexService.extract_index_positions(var_name)

        def display(source_name: str) -> str:
            indices = "_".join(by_name[source_name].indices)
            label = PatternIndexService.format_entry_display(indices, positions)
            return f"{label} ({source_name})"

        selected = filtered_multiselect(
            "Instances to include",
            options=sources,
            default=sources if current_selection is None else current_selection,
            key=f"pattern_entries_{var_id}",
            format_func=display,
        )
        if selected:
            st.success(f"Will parse {len(selected)}/{len(sources)} concrete source instances")
        else:
            st.error("Select at least one concrete source instance before parsing.")
        return True, selected
