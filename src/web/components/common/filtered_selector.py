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

    The current selection stays available across searches, including no matches.
    The blank option clears it; removal from the source options invalidates it.

    Returns the selected option string, or ``None`` if nothing is selected.
    """
    selection_key = f"{key}__selection"
    visible_key = f"{key}__visible"
    available = set(options)
    selected = st.session_state.get(selection_key)
    if not isinstance(selected, str) or selected not in available:
        selected = None
    if key in st.session_state:
        incoming = st.session_state[key]
        if incoming in available:
            selected = incoming
        elif incoming is None or incoming == "":
            selected = None

    large = len(options) > SELECTBOX_THRESHOLD
    filtered = options
    if large:
        query = (
            st.text_input(
                f"Search ({len(options)} available)",
                key=f"{key}__search",
                placeholder=placeholder,
                help=help,
            )
            .strip()
            .lower()
        )
        if query:
            filtered = [option for option in options if query in option.lower()]
        # The blank clear option and a retained selection count toward the DOM cap.
        limit = MAX_DISPLAYED - 1
        displayed = filtered[:limit]
        if selected is not None and selected not in displayed:
            displayed = [selected, *displayed[: max(0, limit - 1)]]
            st.caption("The current selection is retained while filtering.")
        if not filtered:
            st.caption("No matches found.")
        elif len(filtered) > limit:
            st.caption(f"Showing {len(displayed)} of {len(filtered)} matches — refine your search.")
    else:
        displayed = options

    widget_options = ["", *displayed]
    if key in st.session_state and (
        st.session_state.get(visible_key) != widget_options
        or st.session_state[key] not in widget_options
    ):
        st.session_state[key] = selected or ""
    selected_index = widget_options.index(selected) if selected in widget_options else 0
    result = st.selectbox(
        label,
        options=widget_options,
        index=None if key in st.session_state else selected_index,
        key=key,
        help=help,
        label_visibility="collapsed" if large else "visible",
    )
    st.session_state[visible_key] = widget_options
    st.session_state[selection_key] = result if result in available else None
    return result if result in available else None


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
        persistent = (
            (persistent - previous_visible) | incoming
            if visible_key in st.session_state
            else incoming
        )

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
        widget_kwargs.setdefault("label_visibility", "collapsed")
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
