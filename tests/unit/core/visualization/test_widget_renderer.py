"""
Tests for WidgetRenderer — uses mocked Streamlit to test widget generation.

The renderer lazily imports ``streamlit`` inside each method, so we patch
``sys.modules["streamlit"]`` with a MagicMock before each test.
"""

from __future__ import annotations

import sys
from typing import Any, Dict, Generator
from unittest.mock import MagicMock

import pytest

from src.core.visualization.widgets.widget_def import (
    CheckboxWidgetDef,
    ColorWidgetDef,
    NumberWidgetDef,
    SelectWidgetDef,
    SliderWidgetDef,
    TextWidgetDef,
    WidgetSection,
)
from src.core.visualization.widgets.widget_renderer import WidgetRenderer


@pytest.fixture(autouse=True)
def mock_st() -> Generator[MagicMock, None, None]:
    """Inject a mock ``streamlit`` into ``sys.modules`` for the test scope."""
    fake_st = MagicMock()
    fake_st.number_input.return_value = 42
    fake_st.slider.return_value = 500
    fake_st.selectbox.return_value = "v"
    fake_st.checkbox.return_value = True
    fake_st.color_picker.return_value = "#FF0000"
    fake_st.text_input.return_value = "hello"
    # expander context-manager
    fake_st.expander.return_value.__enter__ = MagicMock(return_value=None)
    fake_st.expander.return_value.__exit__ = MagicMock(return_value=False)

    original = sys.modules.get("streamlit")
    sys.modules["streamlit"] = fake_st
    yield fake_st
    # Restore
    if original is not None:
        sys.modules["streamlit"] = original
    else:
        sys.modules.pop("streamlit", None)


class TestWidgetRendererKey:
    """Test widget key generation."""

    def test_key_with_prefix(self) -> None:
        renderer = WidgetRenderer(key_prefix="p3_")
        assert renderer._widget_key("margin_l") == "p3_margin_l"

    def test_key_without_prefix(self) -> None:
        renderer = WidgetRenderer()
        assert renderer._widget_key("margin_l") == "margin_l"


class TestWidgetRendering:
    """Test individual widget rendering via mocked Streamlit."""

    def test_render_number_widget(self, mock_st: MagicMock) -> None:
        mock_st.number_input.return_value = 42
        renderer = WidgetRenderer(key_prefix="p1_")
        widget = NumberWidgetDef(
            key="margin_l",
            label="Left",
            default=100,
            min_value=0,
            max_value=400,
            step=5,
        )
        saved: Dict[str, Any] = {"margin_l": 150}

        result = renderer._render_widget(widget, saved)

        assert result == 42
        mock_st.number_input.assert_called_once_with(
            label="Left",
            value=150,
            min_value=0,
            max_value=400,
            step=5,
            key="p1_margin_l",
            help=None,
        )

    def test_render_float_number_widget(self, mock_st: MagicMock) -> None:
        mock_st.number_input.return_value = 0.5
        renderer = WidgetRenderer()
        widget = NumberWidgetDef(
            key="opacity",
            label="Opacity",
            default=1.0,
            min_value=0.0,
            max_value=1.0,
            step=0.1,
            as_int=False,
        )
        result = renderer._render_widget(widget, {})
        assert result == 0.5
        mock_st.number_input.assert_called_once()

    def test_render_slider_widget(self, mock_st: MagicMock) -> None:
        mock_st.slider.return_value = 500
        renderer = WidgetRenderer()
        widget = SliderWidgetDef(
            key="width",
            label="Width",
            default=700,
            min_value=200,
            max_value=2000,
            step=10,
        )
        result = renderer._render_widget(widget, {"width": 800})
        assert result == 500

    def test_render_select_widget(self, mock_st: MagicMock) -> None:
        mock_st.selectbox.return_value = "h"
        renderer = WidgetRenderer()
        widget = SelectWidgetDef(
            key="orient",
            label="Orient",
            default="v",
            options=("v", "h"),
        )
        result = renderer._render_widget(widget, {})
        assert result == "h"
        mock_st.selectbox.assert_called_once_with(
            label="Orient",
            options=["v", "h"],
            index=0,
            key="orient",
            help=None,
        )

    def test_render_checkbox_widget(self, mock_st: MagicMock) -> None:
        mock_st.checkbox.return_value = True
        renderer = WidgetRenderer()
        widget = CheckboxWidgetDef(
            key="toggle",
            label="Enable",
            default=False,
        )
        result = renderer._render_widget(widget, {})
        assert result is True

    def test_render_color_widget(self, mock_st: MagicMock) -> None:
        mock_st.color_picker.return_value = "#00FF00"
        renderer = WidgetRenderer()
        widget = ColorWidgetDef(
            key="bg",
            label="Background",
            default="#FFFFFF",
        )
        result = renderer._render_widget(widget, {"bg": "#AAAAAA"})
        assert result == "#00FF00"

    def test_render_text_widget(self, mock_st: MagicMock) -> None:
        mock_st.text_input.return_value = "world"
        renderer = WidgetRenderer()
        widget = TextWidgetDef(
            key="name",
            label="Name",
            default="hello",
            max_chars=50,
        )
        result = renderer._render_widget(widget, {})
        assert result == "world"


class TestSectionRendering:
    """Test section-level rendering."""

    def test_render_section_with_expander(self, mock_st: MagicMock) -> None:
        mock_st.number_input.side_effect = [10, 20]

        section = WidgetSection(
            id="test",
            label="Test",
            widgets=(
                NumberWidgetDef(key="a", label="A", default=1),
                NumberWidgetDef(key="b", label="B", default=2),
            ),
        )
        renderer = WidgetRenderer()
        result = renderer.render_section(section, {})

        assert result == {"a": 10, "b": 20}
        mock_st.expander.assert_called_once()

    def test_render_section_no_expander(self, mock_st: MagicMock) -> None:
        mock_st.checkbox.return_value = True
        section = WidgetSection(
            id="flags",
            label="Flags",
            widgets=(CheckboxWidgetDef(key="f1", label="Flag1", default=False),),
        )
        renderer = WidgetRenderer()
        result = renderer.render_section(section, {}, use_expander=False)

        assert result == {"f1": True}
        mock_st.expander.assert_not_called()

    def test_render_sections_merge(self, mock_st: MagicMock) -> None:
        mock_st.number_input.return_value = 99
        mock_st.checkbox.return_value = False

        s1 = WidgetSection(
            id="s1",
            label="S1",
            widgets=(NumberWidgetDef(key="x", label="X", default=0),),
        )
        s2 = WidgetSection(
            id="s2",
            label="S2",
            widgets=(CheckboxWidgetDef(key="y", label="Y"),),
        )

        renderer = WidgetRenderer(key_prefix="t_")
        result = renderer.render_sections([s1, s2], {})

        assert "x" in result
        assert "y" in result

    def test_render_section_with_icon(self, mock_st: MagicMock) -> None:
        mock_st.checkbox.return_value = False
        section = WidgetSection(
            id="flags",
            label="Flags",
            icon="🎨",
            widgets=(CheckboxWidgetDef(key="f1", label="Flag1", default=False),),
        )
        renderer = WidgetRenderer()
        renderer.render_section(section, {})

        # expander label should include the icon
        call_args = mock_st.expander.call_args
        assert "🎨" in call_args[0][0]


class TestWidgetDefaults:
    """Test that saved config values override widget defaults."""

    def test_saved_config_used_as_default(self, mock_st: MagicMock) -> None:
        """Widget should use saved_config value as its default/value."""
        mock_st.number_input.return_value = 200
        renderer = WidgetRenderer()
        widget = NumberWidgetDef(
            key="margin_l",
            label="Left",
            default=100,
            min_value=0,
            max_value=400,
        )

        renderer._render_widget(widget, {"margin_l": 200})

        # Check that value=200 (from saved_config) was passed
        call_args = mock_st.number_input.call_args
        assert call_args[1]["value"] == 200

    def test_missing_saved_config_uses_default(self, mock_st: MagicMock) -> None:
        """Widget should fall back to WidgetDef.default if not in saved_config."""
        mock_st.number_input.return_value = 100
        renderer = WidgetRenderer()
        widget = NumberWidgetDef(
            key="margin_l",
            label="Left",
            default=100,
            min_value=0,
            max_value=400,
        )

        renderer._render_widget(widget, {})

        call_args = mock_st.number_input.call_args
        assert call_args[1]["value"] == 100

    def test_select_with_saved_value(self, mock_st: MagicMock) -> None:
        """Selectbox should find saved value's index in options."""
        mock_st.selectbox.return_value = "h"
        renderer = WidgetRenderer()
        widget = SelectWidgetDef(
            key="orient",
            label="Orient",
            default="v",
            options=("v", "h"),
        )

        renderer._render_widget(widget, {"orient": "h"})

        call_args = mock_st.selectbox.call_args
        assert call_args[1]["index"] == 1  # "h" is at index 1

    def test_select_with_unknown_saved_value_defaults_to_zero(self, mock_st: MagicMock) -> None:
        """If saved value not in options, index should default to 0."""
        mock_st.selectbox.return_value = "v"
        renderer = WidgetRenderer()
        widget = SelectWidgetDef(
            key="orient",
            label="Orient",
            default="v",
            options=("v", "h"),
        )

        renderer._render_widget(widget, {"orient": "UNKNOWN"})

        call_args = mock_st.selectbox.call_args
        assert call_args[1]["index"] == 0
