"""
Tests for EngineManager — visualization engine state management.

Uses a mock session_state dictionary to validate get/set/toggle
behaviour without requiring the Streamlit runtime.
"""

from typing import Any
from unittest.mock import patch

import pytest

# Helper: Mock session_state


class MockSessionState(dict):
    """Dict subclass that behaves like ``st.session_state`` for testing."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


@pytest.fixture()
def mock_state() -> Any:
    """Provide a fresh mock session_state and patch ``st.session_state``."""
    state: MockSessionState = MockSessionState()
    with patch("src.web.rendering.engine_manager.st") as mock_st:
        mock_st.session_state = state
        yield state


# get_engine


class TestGetEngine:
    """Tests for ``EngineManager.get_engine()``."""

    def test_default_is_plotly(self, mock_state: MockSessionState) -> None:
        """When no key is present, default should be 'plotly'."""
        from src.web.rendering.engine_manager import EngineManager

        assert EngineManager.get_engine() == "plotly"

    def test_returns_stored_value(self, mock_state: MockSessionState) -> None:
        """When key exists, returns its value."""
        from src.web.rendering.engine_manager import EngineManager

        mock_state[EngineManager.STATE_KEY] = "matplotlib"
        assert EngineManager.get_engine() == "matplotlib"

    def test_invalid_value_falls_back_to_default(self, mock_state: MockSessionState) -> None:
        """If session state holds an invalid mode, fall back to default."""
        from src.web.rendering.engine_manager import EngineManager

        mock_state[EngineManager.STATE_KEY] = "d3js"
        assert EngineManager.get_engine() == "plotly"


# set_engine


class TestSetEngine:
    """Tests for ``EngineManager.set_engine()``."""

    def test_set_matplotlib(self, mock_state: MockSessionState) -> None:
        from src.web.rendering.engine_manager import EngineManager

        EngineManager.set_engine("matplotlib")
        assert mock_state[EngineManager.STATE_KEY] == "matplotlib"

    def test_set_plotly(self, mock_state: MockSessionState) -> None:
        from src.web.rendering.engine_manager import EngineManager

        mock_state[EngineManager.STATE_KEY] = "matplotlib"
        EngineManager.set_engine("plotly")
        assert mock_state[EngineManager.STATE_KEY] == "plotly"

    def test_idempotent_when_unchanged(self, mock_state: MockSessionState) -> None:
        """Setting the current mode leaves session state unchanged."""
        from src.web.rendering.engine_manager import EngineManager

        # Default is plotly, setting plotly should leave state empty.
        EngineManager.set_engine("plotly")
        assert EngineManager.STATE_KEY not in mock_state

    def test_invalid_mode_raises_value_error(self, mock_state: MockSessionState) -> None:
        from src.web.rendering.engine_manager import EngineManager

        with pytest.raises(ValueError, match="Invalid engine mode"):
            EngineManager.set_engine("d3js")  # type: ignore[arg-type]


# is_plotly / is_matplotlib


class TestConvenienceBooleans:
    """Tests for ``is_plotly()`` and ``is_matplotlib()``."""

    def test_is_plotly_default(self, mock_state: MockSessionState) -> None:
        from src.web.rendering.engine_manager import EngineManager

        assert EngineManager.is_plotly() is True
        assert EngineManager.is_matplotlib() is False

    def test_is_matplotlib_after_set(self, mock_state: MockSessionState) -> None:
        from src.web.rendering.engine_manager import EngineManager

        EngineManager.set_engine("matplotlib")
        assert EngineManager.is_matplotlib() is True
        assert EngineManager.is_plotly() is False

    def test_toggle_round_trip(self, mock_state: MockSessionState) -> None:
        """Toggle plotly → matplotlib → plotly preserves state."""
        from src.web.rendering.engine_manager import EngineManager

        assert EngineManager.is_plotly() is True
        EngineManager.set_engine("matplotlib")
        assert EngineManager.is_matplotlib() is True
        EngineManager.set_engine("plotly")
        assert EngineManager.is_plotly() is True


# STATE_KEY isolation


class TestStateKeyIsolation:
    """Verify the manager uses the correct namespaced key."""

    def test_key_value(self) -> None:
        from src.web.rendering.engine_manager import EngineManager

        assert EngineManager.STATE_KEY == "ring5_engine_mode"

    def test_key_not_colliding_with_other_state(self, mock_state: MockSessionState) -> None:
        """Other keys in session state are not affected."""
        from src.web.rendering.engine_manager import EngineManager

        mock_state["something_else"] = 42
        EngineManager.set_engine("matplotlib")
        assert mock_state["something_else"] == 42
