"""Isolate AppTest session resources and persistent application storage."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
import streamlit as st

from src.core.services.data_services.path_service import PathService


@pytest.fixture(autouse=True)
def _isolate_apptest_session_resources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[None, None, None]:
    """Give each synthetic session private storage and release its resources.

    Streamlit's AppTest runner reuses one synthetic session identity within a
    pytest worker. Session-scoped cached resources would therefore leak an
    ``ApplicationAPI`` between otherwise independent AppTest instances unless
    the harness explicitly ends that synthetic session. Clearing the resource
    cache also invokes the API's ``on_release`` callback, exercising the same
    cleanup path used when a browser session disconnects.
    """
    st.cache_resource.clear()
    PathService.reset_caches()
    monkeypatch.setenv("RING5_DATA_DIR", str(tmp_path / "ring5-data"))
    try:
        yield
    finally:
        st.cache_resource.clear()
        PathService.reset_caches()
