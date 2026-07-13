"""
Filtered selector components for large option lists.

Wraps ``st.selectbox`` and ``st.multiselect`` with server-side text filtering
so that at most ``MAX_DISPLAYED`` options are sent to the browser DOM.  Below
configurable thresholds the standard Streamlit widgets are used unchanged.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

# ---------------------------------------------------------------------------
# Thresholds — below these, the standard Streamlit widget is used as-is.
# ---------------------------------------------------------------------------
SELECTBOX_THRESHOLD = 200
MULTISELECT_THRESHOLD = 100
MAX_DISPLAYED = 50


# ---------------------------------------------------------------------------
# filtered_selectbox
# ---------------------------------------------------------------------------
def filtered_selectbox(
    label: str,
    options: list[str],
    *,
    key: str,
    help: str | None = None,
    placeholder: str = "Type to search...",
) -> str | None:
    """Server-side filtered ``st.selectbox`` for large option lists.

    When *options* has fewer than ``SELECTBOX_THRESHOLD`` items the call is
    forwarded directly to ``st.selectbox`` (identical behaviour).  Above the
    threshold a ``st.text_input`` is rendered for searching and only the top
    ``MAX_DISPLAYED`` matches are shown in the dropdown.

    Returns the selected option string, or ``None`` if nothing is selected.
    """
    if len(options) <= SELECTBOX_THRESHOLD:
        result = st.selectbox(
            label,
            options=[""] + options,
            key=key,
            help=help,
        )
        return result if result else None

    # -- Filtered path --
    search_key = f"{key}__search"
    query: str = st.text_input(
        f"Search ({len(options)} available)",
        key=search_key,
        placeholder=placeholder,
        help=help,
    )

    if query.strip():
        q = query.strip().lower()
        filtered = [o for o in options if q in o.lower()]
    else:
        filtered = options

    displayed = filtered[:MAX_DISPLAYED]

    if not displayed:
        st.caption("No matches found.")
        return None

    if len(filtered) > MAX_DISPLAYED:
        st.caption(
            f"Showing first {MAX_DISPLAYED} of {len(filtered)} matches — refine your search."
        )
    elif query.strip():
        st.caption(f"{len(filtered)} matches.")

    result = st.selectbox(
        label,
        options=[""] + displayed,
        key=key,
        label_visibility="collapsed",
    )
    return result if result else None


# ---------------------------------------------------------------------------
# filtered_multiselect
# ---------------------------------------------------------------------------
def filtered_multiselect(
    label: str,
    options: list[str],
    *,
    key: str,
    default: list[str] | None = None,
    help: str | None = None,
    **kwargs: Any,
) -> list[str]:
    """Server-side filtered ``st.multiselect`` for large option lists.

    When *options* has fewer than ``MULTISELECT_THRESHOLD`` items the call is
    forwarded directly to ``st.multiselect`` (identical behaviour).  Above the
    threshold a ``st.text_input`` is rendered for searching and selections are
    persisted across filter changes via ``st.session_state``.

    Returns the list of selected options (in the order they appear in *options*).
    """
    if len(options) <= MULTISELECT_THRESHOLD:
        result: list[str] = st.multiselect(
            label,
            options=options,
            default=default,
            key=key,
            help=help,
            **kwargs,
        )
        return result

    # -- Filtered path --
    persist_key = f"{key}__selections"
    search_key = f"{key}__search"
    options_set = set(options)

    # Initialise persistent selection on first render.
    if persist_key not in st.session_state:
        st.session_state[persist_key] = set(default or [])
    # Prune stale entries that are no longer in the option list.
    persistent: set[str] = st.session_state[persist_key] & options_set

    # Search input
    query: str = st.text_input(
        f"Filter ({len(options)} entries, {len(persistent)} selected)",
        key=search_key,
        placeholder="Type to filter...",
        help=help,
    )

    if query.strip():
        q = query.strip().lower()
        filtered = [o for o in options if q in o.lower()]
    else:
        filtered = options

    displayed = filtered[:MAX_DISPLAYED]
    displayed_set = set(displayed)

    if not displayed:
        st.caption("No matches found.")
    elif len(filtered) > MAX_DISPLAYED:
        st.caption(
            f"Showing first {MAX_DISPLAYED} of {len(filtered)} matches — refine your search."
        )

    # Pre-set widget value to the intersection of persistent selection and
    # currently visible options.  This avoids Streamlit errors about values
    # not being in the option list.
    widget_default = [o for o in displayed if o in persistent]
    st.session_state[key] = widget_default

    visible_selection: list[str] = st.multiselect(
        label,
        options=displayed,
        key=key,
        label_visibility="collapsed",
    )

    # Merge back: keep selections not currently visible, update visible ones.
    new_persistent = {e for e in persistent if e not in displayed_set}
    new_persistent |= set(visible_selection)
    st.session_state[persist_key] = new_persistent

    # Bulk actions
    col_a, col_b, col_c = st.columns([1, 1, 2])
    with col_a:
        if st.button("Select all matching", key=f"{key}__sel_all", type="tertiary"):
            st.session_state[persist_key] = new_persistent | set(filtered)
            st.rerun()
    with col_b:
        if st.button("Clear all", key=f"{key}__clear", type="tertiary"):
            st.session_state[persist_key] = set()
            st.rerun()
    with col_c:
        total_selected = len(st.session_state[persist_key])
        if total_selected > 0:
            st.caption(f"{total_selected} of {len(options)} selected")

    # Return in original option order.
    final_persistent = st.session_state[persist_key]
    return [o for o in options if o in final_persistent]
