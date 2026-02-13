"""Tests for interactive_plotly_chart component wrapper.

Verifies:
    - Figure serialization to JSON
    - Config serialization
    - Component function delegation
    - Default return value handling
"""

import json
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import plotly.graph_objects as go

MODULE = "src.web.pages.ui.components.interactive_plot"


class TestInteractivePlotlyChart:
    """Tests for the interactive_plotly_chart function."""

    @patch(f"{MODULE}._component_func")
    def test_basic_call_serializes_figure(self, mock_func: MagicMock) -> None:
        """Figure is serialized to JSON and passed to the component."""
        mock_func.return_value = None

        from src.web.pages.ui.components.interactive_plot import (
            interactive_plotly_chart,
        )

        fig = go.Figure(data=[go.Bar(x=[1, 2], y=[3, 4])])
        interactive_plotly_chart(fig)

        mock_func.assert_called_once()
        call_kwargs = mock_func.call_args
        # The spec argument should be valid JSON
        spec_json: str = call_kwargs.kwargs.get("spec") or call_kwargs[1].get(
            "spec", call_kwargs[0][0] if call_kwargs[0] else ""
        )
        assert isinstance(spec_json, str)
        parsed = json.loads(spec_json)
        assert "data" in parsed

    @patch(f"{MODULE}._component_func")
    def test_config_serialized(self, mock_func: MagicMock) -> None:
        """Config dict is JSON-serialized when provided."""
        mock_func.return_value = None

        from src.web.pages.ui.components.interactive_plot import (
            interactive_plotly_chart,
        )

        fig = go.Figure()
        config: Dict[str, Any] = {"displayModeBar": False}
        interactive_plotly_chart(fig, config=config)

        call_kwargs = mock_func.call_args
        config_arg = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config", "")
        # Config should be JSON string, not dict
        assert isinstance(config_arg, str)
        parsed = json.loads(config_arg)
        assert parsed["displayModeBar"] is False

    @patch(f"{MODULE}._component_func")
    def test_no_config_passes_empty_json(self, mock_func: MagicMock) -> None:
        """When config is None, empty JSON object '{}' is passed."""
        mock_func.return_value = None

        from src.web.pages.ui.components.interactive_plot import (
            interactive_plotly_chart,
        )

        fig = go.Figure()
        interactive_plotly_chart(fig)

        call_kwargs = mock_func.call_args
        config_arg = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config", "")
        assert config_arg == "{}"

    @patch(f"{MODULE}._component_func")
    def test_key_passed_through(self, mock_func: MagicMock) -> None:
        """The key parameter is forwarded to the component."""
        mock_func.return_value = None

        from src.web.pages.ui.components.interactive_plot import (
            interactive_plotly_chart,
        )

        fig = go.Figure()
        interactive_plotly_chart(fig, key="my_chart")

        call_kwargs = mock_func.call_args
        key_arg = call_kwargs.kwargs.get("key") or call_kwargs[1].get("key")
        assert key_arg == "my_chart"

    @patch(f"{MODULE}._component_func")
    def test_returns_component_value(self, mock_func: MagicMock) -> None:
        """Return value from the component function is passed through."""
        expected: Dict[str, Any] = {"relayoutData": {"xaxis.range": [0, 10]}}
        mock_func.return_value = expected

        from src.web.pages.ui.components.interactive_plot import (
            interactive_plotly_chart,
        )

        fig = go.Figure()
        result = interactive_plotly_chart(fig)

        assert result == expected

    @patch(f"{MODULE}._component_func")
    def test_returns_none_by_default(self, mock_func: MagicMock) -> None:
        """When no interaction occurred, returns None."""
        mock_func.return_value = None

        from src.web.pages.ui.components.interactive_plot import (
            interactive_plotly_chart,
        )

        fig = go.Figure()
        result = interactive_plotly_chart(fig)

        assert result is None
