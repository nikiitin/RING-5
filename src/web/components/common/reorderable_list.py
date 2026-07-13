"""Reorderable list component — drag-free up/down list with optional rename.

This is a self-contained UI component extracted from ``BasePlot``.
Used by ordering sections, advanced options, and grouped stacked bar plot.
"""

import streamlit as st

from src.core.services.visualization.plot_interaction import resolve_item_order


def render_reorderable_list(
    label: str,
    items: list[str],
    key_prefix: str,
    plot_id: int,
    legend_labels: dict[str, str] | None = None,
    default_order: list[str] | None = None,
    enable_rename: bool = False,
    rename_map: dict[str, str] | None = None,
) -> list[str] | tuple[list[str], dict[str, str]]:
    """
    Render a list that can be reordered using up/down buttons.

    When *enable_rename* is ``True`` the item label is rendered as
    an editable text input and the method returns a tuple
    ``(order, renames)`` instead of just the order list.

    Args:
        label: Display label for the list.
        items: List of items to reorder.
        key_prefix: Prefix for session state keys.
        plot_id: Plot identifier for unique widget keys.
        legend_labels: Optional mapping of item values to display labels.
        default_order: Optional default ordering.
        enable_rename: If True, allow inline renaming.
        rename_map: Existing rename mapping to pre-fill inputs.

    Returns:
        Reordered list of items, or ``(order, renames)`` when
        *enable_rename* is True.
    """
    st.markdown(f"**{label}**")

    # Initialize in session state if needed
    ss_key: str = f"{key_prefix}_order_{plot_id}"
    if ss_key not in st.session_state:
        st.session_state[ss_key] = resolve_item_order(items, default_order=default_order)

    # Sync if items changed (e.g. data update)
    current_items: list[str] = st.session_state[ss_key]
    if set(current_items) != set(items):
        current_items = resolve_item_order(items, current_order=current_items)
        st.session_state[ss_key] = current_items

    renames: dict[str, str] = dict(rename_map) if rename_map else {}

    # Display items with reordering controls
    for i, item in enumerate(current_items):
        c1, c2, c3 = st.columns([6, 1, 1])
        with c1:
            if enable_rename:
                rename_value = renames.get(str(item), "")
                if rename_value == str(item):
                    rename_value = ""  # treat identity rename as "no rename"
                # Key is item-name-based (not position-based) so that rename
                # values persist correctly when items are reordered.
                _safe_item_key = str(item).replace(" ", "_")
                new_name: str = st.text_input(
                    str(item),
                    value=rename_value,
                    key=f"{key_prefix}_rename_{_safe_item_key}_{plot_id}",
                    label_visibility="collapsed",
                    placeholder=str(item),
                )
                if new_name and new_name != str(item):
                    renames[str(item)] = new_name
                elif str(item) in renames:
                    renames.pop(str(item), None)
            else:
                display_text: str = str(item)
                if legend_labels and str(item) in legend_labels:
                    display_text = f"{legend_labels[str(item)]} ({item})"
                st.text(display_text)
        with c2:
            if i > 0:
                if st.button("↑", key=f"{key_prefix}_up_{i}_{plot_id}"):
                    current_items[i], current_items[i - 1] = (
                        current_items[i - 1],
                        current_items[i],
                    )
                    st.session_state[ss_key] = current_items
                    st.rerun()
        with c3:
            if i < len(current_items) - 1:
                if st.button("↓", key=f"{key_prefix}_down_{i}_{plot_id}"):
                    current_items[i], current_items[i + 1] = (
                        current_items[i + 1],
                        current_items[i],
                    )
                    st.session_state[ss_key] = current_items
                    st.rerun()

    if enable_rename:
        return current_items, renames
    return current_items
