"""Root conftest.py — shared test utilities available to ALL tests.

Provides common helper functions and fixtures used across multiple
test directories (unit, ui_unit, integration).
"""

from typing import Any, List, Union
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Shared Helpers
# ---------------------------------------------------------------------------


def columns_side_effect(
    spec: Union[int, list[Any], tuple[Any, ...]], **kwargs: Any
) -> List[MagicMock]:
    """Mock st.columns() behavior — returns a list of MagicMock column objects.

    Mimics Streamlit's columns() API which accepts either an int (number
    of equal-width columns) or a list/tuple (relative widths).

    Args:
        spec: Number of columns (int) or list/tuple of relative widths.
        **kwargs: Absorbed — matches st.columns(gap=..., vertical_alignment=...).

    Returns:
        List of MagicMock objects, one per column.
    """
    if isinstance(spec, int):
        return [MagicMock() for _ in range(spec)]
    elif isinstance(spec, (list, tuple)):
        return [MagicMock() for _ in range(len(spec))]
    return [MagicMock()]


# ---------------------------------------------------------------------------
# Shared Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_api() -> MagicMock:
    """Basic mock ApplicationAPI with state_manager.

    Provides the minimal mock structure used by most UI tests.
    Override in individual test files when extended wiring is needed
    (e.g., api.backend, api.portfolio, api.data_services).
    """
    api = MagicMock()
    api.state_manager = MagicMock()
    return api
