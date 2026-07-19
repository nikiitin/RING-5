"""Tests for pills-driven settings navigation — Steps 24-26, 29, 31."""

from contextlib import ExitStack
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd

from tests.conftest import columns_side_effect


class TestRenderSettingsPills:
    """Verify render_settings_pills filters sections by advanced flag."""

    @patch("src.web.pages.ui.plotting.settings_pills.st")
    def test_basic_only_shows_three(self, mock_st: MagicMock) -> None:
        """When show_advanced=False, only 3 basic sections are offered."""
        # [test->req~ring5.figure.advanced-disclosure~1]
        from src.web.pages.ui.plotting.settings_pills import render_settings_pills

        mock_st.pills.return_value = "layout"
        render_settings_pills(show_advanced=False)

        call_args = mock_st.pills.call_args
        options = call_args.kwargs.get("options") or call_args[1].get("options")
        assert options == ["layout", "typography", "legends"]

    @patch("src.web.pages.ui.plotting.settings_pills.st")
    def test_advanced_shows_all_seven(self, mock_st: MagicMock) -> None:
        """When show_advanced=True, all 7 sections are offered."""
        # [test->req~ring5.figure.advanced-disclosure~1]
        from src.web.pages.ui.plotting.settings_pills import render_settings_pills

        mock_st.pills.return_value = "axes"
        render_settings_pills(show_advanced=True)

        call_args = mock_st.pills.call_args
        options = call_args.kwargs.get("options") or call_args[1].get("options")
        assert len(options) == 7
        assert "axes" in options
        assert "data_labels" in options
        assert "colors" in options
        assert "advanced" in options

    @patch("src.web.pages.ui.plotting.settings_pills.st")
    def test_returns_selected_key(self, mock_st: MagicMock) -> None:
        """Return value matches st.pills selection."""
        from src.web.pages.ui.plotting.settings_pills import render_settings_pills

        mock_st.pills.return_value = "typography"
        result = render_settings_pills(show_advanced=False)
        assert result == "typography"

    @patch("src.web.pages.ui.plotting.settings_pills.st")
    def test_returns_none_when_nothing_selected(self, mock_st: MagicMock) -> None:
        """Return None when st.pills returns None (no selection)."""
        from src.web.pages.ui.plotting.settings_pills import render_settings_pills

        mock_st.pills.return_value = None
        result = render_settings_pills(show_advanced=True)
        assert result is None


class TestSectionDispatch:
    """Verify render_settings_section dispatches to correct handler."""

    def _make_plot(self) -> MagicMock:
        """Create a mock BasePlot with render_settings_section from real class."""
        from src.web.pages.ui.plotting.base_plot import BasePlot

        plot = MagicMock(spec=BasePlot)
        plot.plot_id = 1
        plot.plot_type = "grouped_bar"

        # Wire the real dispatch method
        plot.render_settings_section = BasePlot.render_settings_section.__get__(plot, type(plot))
        return plot

    def test_none_returns_empty(self) -> None:
        """None section returns empty dict."""
        plot = self._make_plot()
        result = plot.render_settings_section(None, {}, None)
        assert result == {}

    def test_unknown_section_returns_empty(self) -> None:
        """Unknown section key returns empty dict."""
        plot = self._make_plot()
        result = plot.render_settings_section("nonexistent", {}, None)
        assert result == {}

    def test_layout_dispatches_to_component(self) -> None:
        """'layout' creates LayoutSettingsComponent and calls render."""
        plot = self._make_plot()
        with patch("src.web.pages.ui.plotting.plot_config_ui.LayoutSettingsComponent") as MockComp:
            MockComp.return_value.render.return_value = {"width": 800}
            result = plot.render_settings_section("layout", {"x": "a"}, None)
            assert result == {"width": 800}
            MockComp.assert_called_once_with(1, "grouped_bar")

    def test_all_sections_are_handled(self) -> None:
        """Every defined section key has a handler."""
        from src.web.pages.ui.plotting.settings_pills import SETTINGS_SECTIONS

        plot = self._make_plot()
        # Mock all component classes used by render_settings_section
        comp_patches = [
            "src.web.pages.ui.plotting.plot_config_ui.LayoutSettingsComponent",
            "src.web.pages.ui.plotting.plot_config_ui.TypographySettingsComponent",
            "src.web.pages.ui.plotting.plot_config_ui.LegendSettingsComponent",
            "src.web.pages.ui.plotting.plot_config_ui.AxesSettingsComponent",
            "src.web.pages.ui.plotting.plot_config_ui.DataLabelsSettingsComponent",
            "src.web.pages.ui.plotting.plot_config_ui.ColorsSettingsComponent",
            "src.web.pages.ui.plotting.plot_config_ui.AdvancedSettingsComponent",
        ]
        with ExitStack() as stack:
            for p in comp_patches:
                m = stack.enter_context(patch(p))
                m.return_value.render.return_value = {}
            for section in SETTINGS_SECTIONS:
                result = plot.render_settings_section(section.key, {}, None)
                assert isinstance(result, dict), f"Section {section.key} didn't return dict"


class TestLegendSubPills:
    """Verify legend sub-pills use the correct state-key prefixes."""

    def _make_component(self) -> Any:
        from src.web.components.plotting.settings import (
            LegendSettingsComponent,
        )

        return LegendSettingsComponent(plot_id=1, plot_type="grouped_bar")

    @patch("src.web.components.plotting.settings.legend_settings.st")
    def test_primary_uses_theme_prefix(self, mock_st: MagicMock) -> None:
        """Primary legend pill uses 'theme_' prefix."""
        comp = self._make_component()
        mock_st.pills.return_value = "primary"
        mock_st.columns.side_effect = columns_side_effect
        mock_st.checkbox.return_value = True
        mock_st.number_input.return_value = 12
        mock_st.selectbox.return_value = "v"
        mock_st.slider.return_value = 1.0
        mock_st.color_picker.return_value = "#000000"

        with patch.object(comp, "_render_legend_section", wraps=comp._render_legend_section) as spy:
            comp.render({}, has_secondary=True, has_tertiary=True)
            spy.assert_called_once_with({}, "theme_")

    @patch("src.web.components.plotting.settings.legend_settings.st")
    def test_secondary_uses_legend2_prefix(self, mock_st: MagicMock) -> None:
        """Secondary legend pill uses 'legend2_' prefix."""
        comp = self._make_component()
        mock_st.pills.return_value = "secondary"
        mock_st.columns.side_effect = columns_side_effect
        mock_st.checkbox.return_value = True
        mock_st.number_input.return_value = 12
        mock_st.selectbox.return_value = "v"
        mock_st.slider.return_value = 1.0
        mock_st.color_picker.return_value = "#000000"

        with patch.object(comp, "_render_legend_section", wraps=comp._render_legend_section) as spy:
            comp.render({}, has_secondary=True, has_tertiary=True)
            spy.assert_called_once_with({}, "legend2_")

    @patch("src.web.components.plotting.settings.legend_settings.st")
    def test_tertiary_uses_legend3_prefix(self, mock_st: MagicMock) -> None:
        """Tertiary legend pill uses 'legend3_' prefix."""
        comp = self._make_component()
        mock_st.pills.return_value = "tertiary"
        mock_st.columns.side_effect = columns_side_effect
        mock_st.checkbox.return_value = True
        mock_st.number_input.return_value = 12
        mock_st.selectbox.return_value = "v"
        mock_st.slider.return_value = 1.0
        mock_st.color_picker.return_value = "#000000"

        with patch.object(comp, "_render_legend_section", wraps=comp._render_legend_section) as spy:
            comp.render({}, has_secondary=True, has_tertiary=True)
            spy.assert_called_once_with({}, "legend3_")


class TestAxesSubPills:
    """Verify axis sub-pills route to the correct settings component."""

    def _make_component(self) -> Any:
        """Create an AxesSettingsComponent for testing."""
        from src.web.components.plotting.settings import (
            AxesSettingsComponent,
        )

        return AxesSettingsComponent(plot_id=1, plot_type="grouped_bar")

    @patch("src.web.components.plotting.settings.axes_settings.st")
    def test_x_axis_renders_x_axis_settings(self, mock_st: MagicMock) -> None:
        """X-axis sub-pill renders X-axis settings + ordering."""
        comp = self._make_component()
        mock_st.pills.return_value = "x"
        mock_st.checkbox.return_value = True
        mock_st.slider.return_value = -45
        mock_st.columns.side_effect = columns_side_effect
        mock_st.color_picker.return_value = "#444444"
        mock_st.number_input.return_value = 0
        data = pd.DataFrame({"a": [1]})

        specific_fn = MagicMock(return_value={})
        ordering_fn = MagicMock()

        result = comp.render(
            {},
            data=data,
            render_specific_fn=specific_fn,
            render_ordering_fn=ordering_fn,
        )
        # X-axis settings should produce show_x_grid and xaxis_tickangle
        assert "show_x_grid" in result
        assert "xaxis_tickangle" in result

    @patch("src.web.components.plotting.settings.axes_settings.st")
    def test_y_left_renders_y_settings(self, mock_st: MagicMock) -> None:
        """Y-Left sub-pill renders Y-axis settings with empty prefix."""
        comp = self._make_component()
        mock_st.pills.return_value = "y_left"
        mock_st.checkbox.return_value = True
        mock_st.slider.return_value = 0
        mock_st.number_input.return_value = 0
        mock_st.columns.side_effect = columns_side_effect
        mock_st.color_picker.return_value = "#444444"
        mock_st.selectbox.return_value = "solid"

        with patch.object(
            comp, "_render_y_axis_settings", wraps=comp._render_y_axis_settings
        ) as spy:
            comp.render({}, data=None)
            spy.assert_called_once()
            call_kwargs = spy.call_args[1]
            assert call_kwargs.get("prefix") == ""

    @patch("src.web.components.plotting.settings.axes_settings.st")
    def test_y_right_renders_y2_settings(self, mock_st: MagicMock) -> None:
        """Y-Right sub-pill renders Y-axis settings with 'y2' prefix."""
        comp = self._make_component()
        mock_st.pills.return_value = "y_right"
        mock_st.checkbox.return_value = True
        mock_st.slider.return_value = 0
        mock_st.number_input.return_value = 0
        mock_st.columns.side_effect = columns_side_effect
        mock_st.color_picker.return_value = "#444444"
        mock_st.selectbox.return_value = "solid"

        with patch.object(
            comp, "_render_y_axis_settings", wraps=comp._render_y_axis_settings
        ) as spy:
            comp.render({}, data=None, has_dual_axis=True)
            spy.assert_called_once()
            call_kwargs = spy.call_args[1]
            assert call_kwargs.get("prefix") == "y2"
