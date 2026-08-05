"""Tests for interactive_plotly_chart component wrapper.

Verifies:
    - Figure serialization to JSON
    - Config serialization
    - Component function delegation
    - Default return value handling
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import plotly.graph_objects as go

MODULE = "src.web.components.plotting.interactive_plot"


class TestInteractivePlotlyChart:
    """Tests for the interactive_plotly_chart function."""

    # [test->req~ring5.figure.interactive-editing~1]

    @patch(f"{MODULE}._component_func")
    def test_uses_standard_library_json_engine(self, mock_func: MagicMock) -> None:
        """Serialization must not lazily import a native JSON engine."""
        from src.web.components.plotting.interactive_plot import (
            interactive_plotly_chart,
        )

        fig = MagicMock(spec=go.Figure)
        fig.to_plotly_json.return_value = {"data": [], "layout": {}}

        interactive_plotly_chart(fig)

        fig.to_plotly_json.assert_called_once_with()
        fig.to_json.assert_not_called()

    @patch(f"{MODULE}._component_func")
    def test_basic_call_serializes_figure(self, mock_func: MagicMock) -> None:
        """Figure is serialized to JSON and passed to the component."""
        mock_func.return_value = None

        from src.web.components.plotting.interactive_plot import (
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

        from src.web.components.plotting.interactive_plot import (
            interactive_plotly_chart,
        )

        fig = go.Figure()
        config: dict[str, Any] = {"displayModeBar": False}
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

        from src.web.components.plotting.interactive_plot import (
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

        from src.web.components.plotting.interactive_plot import (
            interactive_plotly_chart,
        )

        fig = go.Figure()
        interactive_plotly_chart(fig, key="my_chart")

        call_kwargs = mock_func.call_args
        key_arg = call_kwargs.kwargs.get("key") or call_kwargs[1].get("key")
        assert key_arg == "my_chart"

    @patch(f"{MODULE}._component_func")
    def test_selection_capture_flag_is_forwarded(self, mock_func: MagicMock) -> None:
        """The browser bridge receives the opt-in selection flag."""
        mock_func.return_value = None

        from src.web.components.plotting.interactive_plot import (
            interactive_plotly_chart,
        )

        interactive_plotly_chart(go.Figure(), capture_selection=True)

        assert mock_func.call_args.kwargs["capture_selection"] is True

    @patch(f"{MODULE}._component_func")
    def test_drill_down_click_flag_is_forwarded(self, mock_func: MagicMock) -> None:
        """The browser bridge receives the opt-in point-click flag."""
        mock_func.return_value = None

        from src.web.components.plotting.interactive_plot import (
            interactive_plotly_chart,
        )

        interactive_plotly_chart(go.Figure(), capture_click=True)

        assert mock_func.call_args.kwargs["capture_click"] is True

    @patch(f"{MODULE}._component_func")
    def test_returns_component_value(self, mock_func: MagicMock) -> None:
        """Return value from the component function is passed through."""
        expected: dict[str, Any] = {"relayoutData": {"xaxis.range": [0, 10]}}
        mock_func.return_value = expected

        from src.web.components.plotting.interactive_plot import (
            interactive_plotly_chart,
        )

        fig = go.Figure()
        result = interactive_plotly_chart(fig)

        assert result == expected

    @patch(f"{MODULE}._component_func")
    def test_returns_none_by_default(self, mock_func: MagicMock) -> None:
        """When no interaction occurred, returns None."""
        mock_func.return_value = None

        from src.web.components.plotting.interactive_plot import (
            interactive_plotly_chart,
        )

        fig = go.Figure()
        result = interactive_plotly_chart(fig)

        assert result is None


def test_browser_component_sanitizes_plotly_click_payloads() -> None:
    """Keep click events bounded by the browser-side sanitizer."""
    html = (
        Path(__file__).parents[2] / "src/web/components/plotting/custom_plotly/index.html"
    ).read_text(encoding="utf-8")

    assert 'gd.on("plotly_click"' in html
    assert 'kind: "drill_down"' in html
    assert "ring5_drilldown" in html
