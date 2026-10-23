"""
Filtered selector components for large option lists.

Wraps ``st.selectbox`` and ``st.multiselect`` with server-side text filtering
so that at most ``MAX_DISPLAYED`` options are sent to the browser DOM.  Below
configurable thresholds the standard Streamlit widgets are used unchanged.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

# Thresholds — below these, the standard Streamlit widget is used as-is.
SELECTBOX_THRESHOLD = 200
MULTISELECT_THRESHOLD = 100
MAX_DISPLAYED = 50


# filtered_selectbox
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


# filtered_multiselect
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
    persist_key = f"{key}__selections"
    visible_key = f"{key}__visible"
    reseed_key = f"{key}__reseed"
    options_set = set(options)
    persistent = set(st.session_state.get(persist_key, default or [])) & options_set
    previous_visible = set(st.session_state.get(visible_key, []))
    reseed = bool(st.session_state.pop(reseed_key, False))
    if key in st.session_state and not reseed:
        incoming = set(st.session_state[key]) & options_set
        persistent = (persistent - previous_visible) | incoming

    filtered = options
    large = len(options) > MULTISELECT_THRESHOLD
    if large:
        query = (
            st.text_input(
                f"Filter ({len(options)} entries, {len(persistent)} selected)",
                key=f"{key}__search",
                placeholder="Type to filter...",
                help=help,
            )
            .strip()
            .lower()
        )
        if query:
            filtered = [option for option in options if query in option.lower()]
    displayed = filtered[:MAX_DISPLAYED] if large else filtered
    displayed_set = set(displayed)
    widget_default = [option for option in displayed if option in persistent]
    if key in st.session_state and (previous_visible != displayed_set or reseed):
        st.session_state[key] = widget_default
    st.session_state[visible_key] = list(displayed)
    widget_kwargs = dict(kwargs)
    if large:
        widget_kwargs["label_visibility"] = "collapsed"
        if not displayed:
            st.caption("No matches found.")
        elif len(filtered) > MAX_DISPLAYED:
            st.caption(
                f"Showing first {MAX_DISPLAYED} of {len(filtered)} matches — refine your search."
            )
    visible_selection = st.multiselect(
        label,
        options=displayed,
        default=widget_default if key not in st.session_state else None,
        key=key,
        help=help,
        **widget_kwargs,
    )
    persistent = (persistent - displayed_set) | set(visible_selection)
    st.session_state[persist_key] = persistent

    if large:
        col_all, col_clear, col_count = st.columns([1, 1, 2])
        with col_all:
            if st.button("Select all matching", key=f"{key}__sel_all", type="tertiary"):
                st.session_state[persist_key] = persistent | set(filtered)
                st.session_state[reseed_key] = True
                st.rerun()
        with col_clear:
            if st.button("Clear all", key=f"{key}__clear", type="tertiary"):
                st.session_state[persist_key] = set()
                st.session_state[reseed_key] = True
                st.rerun()
        with col_count:
            st.caption(f"{len(st.session_state[persist_key])} of {len(options)} selected")
    return [option for option in options if option in st.session_state[persist_key]]
