"""Conftest for UI AppTest tests.

Streamlit 1.53.1 had a bug where ``ButtonGroup.indices`` iterated over the
characters of a single-selection string value instead of treating it as one
item, which previously required a monkey-patch here. That bug was fixed
upstream in Streamlit 1.58 (``indices`` now derives from ``formatted_values``),
so the patch is obsolete and has been removed. This file is kept as the
package marker for the UI test suite.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
import streamlit as st


@pytest.fixture(autouse=True)
def _isolate_apptest_session_resources() -> Generator[None, None, None]:
    """Release AppTest resources between tests.

    Streamlit's AppTest runner reuses one synthetic session identity within a
    pytest worker. Session-scoped cached resources would therefore leak an
    ``ApplicationAPI`` between otherwise independent AppTest instances unless
    the harness explicitly ends that synthetic session. Clearing the resource
    cache also invokes the API's ``on_release`` callback, exercising the same
    cleanup path used when a browser session disconnects.
    """
    st.cache_resource.clear()
    try:
        yield
    finally:
        st.cache_resource.clear()
