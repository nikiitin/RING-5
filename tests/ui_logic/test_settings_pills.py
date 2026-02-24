"""Tests for pills-driven settings navigation — Steps 24-26, 29, 31."""

from unittest.mock import MagicMock, patch

import pandas as pd


class TestRenderSettingsPills:
    """Verify render_settings_pills filters sections by advanced flag."""

    @patch("src.web.pages.ui.plotting.settings_pills.st")
    def test_basic_only_shows_three(self, mock_st: MagicMock) -> None:
        """When show_advanced=False, only 3 basic sections are offered."""
        from src.web.pages.ui.plotting.settings_pills import render_settings_pills

        mock_st.pills.return_value = "layout"
        render_settings_pills(show_advanced=False)

        call_args = mock_st.pills.call_args
        options = call_args.kwargs.get("options") or call_args[1].get("options")
        assert options == ["layout", "typography", "legends"]

    @patch("src.web.pages.ui.plotting.settings_pills.st")
    def test_advanced_shows_all_eight(self, mock_st: MagicMock) -> None:
        """When show_advanced=True, all 8 sections are offered."""
        from src.web.pages.ui.plotting.settings_pills import render_settings_pills

        mock_st.pills.return_value = "axes"
        render_settings_pills(show_advanced=True)

        call_args = mock_st.pills.call_args
        options = call_args.kwargs.get("options") or call_args[1].get("options")
        assert len(options) == 8
        assert "axes" in options
        assert "data_labels" in options
        assert "colors" in options
        assert "customization" in options
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

    def test_layout_dispatches_to_render_display(self) -> None:
        """'layout' calls render_display_options."""
        plot = self._make_plot()
        plot.render_display_options = MagicMock(return_value={"width": 800})
        plot._section_layout = MagicMock(return_value={"width": 800})
        result = plot.render_settings_section("layout", {"x": "a"}, None)
        assert result == {"width": 800}

    def test_all_sections_are_handled(self) -> None:
        """Every defined section key has a handler."""
        from src.web.pages.ui.plotting.settings_pills import SETTINGS_SECTIONS

        plot = self._make_plot()
        # Set up mock handlers for ALL sections
        for section in SETTINGS_SECTIONS:
            handler_name = f"_section_{section.key}"
            setattr(plot, handler_name, MagicMock(return_value={}))

        for section in SETTINGS_SECTIONS:
            result = plot.render_settings_section(section.key, {}, None)
            assert isinstance(result, dict), f"Section {section.key} didn't return dict"


class TestLegendSubPills:
    """Verify legend sub-pills use correct key prefixes (Step 25)."""

    def _make_plot(self) -> MagicMock:
        """Create a mock with real _section_legends bound."""
        from src.web.pages.ui.plotting.base_plot import BasePlot

        plot = MagicMock()
        plot.plot_id = 1
        plot.plot_type = "grouped_bar"
        plot.style_manager = MagicMock()
        plot.style_manager.ui_manager._render_legend_section.return_value = {}
        # Bind the real method
        plot._section_legends = BasePlot._section_legends.__get__(plot, type(plot))
        return plot

    @patch("src.web.pages.ui.plotting.base_plot.st")
    def test_primary_uses_theme_prefix(self, mock_st: MagicMock) -> None:
        """Primary legend pill uses 'theme_' prefix."""
        plot = self._make_plot()
        mock_st.pills.return_value = "primary"
        plot._section_legends({}, None)
        plot.style_manager.ui_manager._render_legend_section.assert_called_once_with(
            {}, key_prefix="theme_"
        )

    @patch("src.web.pages.ui.plotting.base_plot.st")
    def test_secondary_uses_legend2_prefix(self, mock_st: MagicMock) -> None:
        """Secondary legend pill uses 'legend2_' prefix."""
        plot = self._make_plot()
        mock_st.pills.return_value = "secondary"
        plot._section_legends({}, None)
        plot.style_manager.ui_manager._render_legend_section.assert_called_once_with(
            {}, key_prefix="legend2_"
        )

    @patch("src.web.pages.ui.plotting.base_plot.st")
    def test_boxed_uses_legend3_prefix(self, mock_st: MagicMock) -> None:
        """Boxed legend pill uses 'legend3_' prefix."""
        plot = self._make_plot()
        mock_st.pills.return_value = "boxed"
        plot._section_legends({}, None)
        plot.style_manager.ui_manager._render_legend_section.assert_called_once_with(
            {}, key_prefix="legend3_"
        )


class TestAxesSubPills:
    """Verify axes sub-pills route to correct settings (Step 26)."""

    def _make_plot(self) -> MagicMock:
        """Create a mock with real _section_axes bound."""
        from src.web.pages.ui.plotting.base_plot import BasePlot

        plot = MagicMock()
        plot.plot_id = 1
        plot.plot_type = "grouped_bar"
        plot.style_manager = MagicMock()
        plot.style_manager.render_xaxis_labels_ui.return_value = {}
        plot._render_x_axis_settings = MagicMock()
        plot.render_specific_advanced_options = MagicMock(return_value={})
        plot._render_ordering_ui = MagicMock()
        plot._render_y_axis_settings = MagicMock()
        # Bind real methods
        plot._section_axes = BasePlot._section_axes.__get__(plot, type(plot))
        return plot

    @patch("src.web.pages.ui.plotting.base_plot.st")
    def test_x_axis_renders_x_axis_settings(self, mock_st: MagicMock) -> None:
        """X-axis sub-pill renders X-axis settings + ordering."""
        plot = self._make_plot()
        mock_st.pills.return_value = "x"
        data = pd.DataFrame({"a": [1]})
        plot._section_axes({}, data)
        plot._render_x_axis_settings.assert_called_once()

    @patch("src.web.pages.ui.plotting.base_plot.st")
    def test_y_left_renders_y_settings(self, mock_st: MagicMock) -> None:
        """Y-Left sub-pill renders Y-axis settings with empty prefix."""
        plot = self._make_plot()
        mock_st.pills.return_value = "y_left"
        plot._section_axes({}, None)
        plot._render_y_axis_settings.assert_called_once()
        call_kwargs = plot._render_y_axis_settings.call_args[1]
        assert call_kwargs.get("prefix") == ""

    @patch("src.web.pages.ui.plotting.base_plot.st")
    def test_y_right_renders_y2_settings(self, mock_st: MagicMock) -> None:
        """Y-Right sub-pill renders Y-axis settings with 'y2' prefix."""
        plot = self._make_plot()
        mock_st.pills.return_value = "y_right"
        plot._section_axes({}, None)
        plot._render_y_axis_settings.assert_called_once()
        call_kwargs = plot._render_y_axis_settings.call_args[1]
        assert call_kwargs.get("prefix") == "y2"


class TestPresetPills:
    """Verify preset selector pills logic (Step 29)."""

    @patch("src.web.pages.ui.plotting.settings_pills.PresetManager")
    @patch("src.web.pages.ui.plotting.settings_pills.st")
    def test_none_selection_returns_none(self, mock_st: MagicMock, mock_pm: MagicMock) -> None:
        """Selecting 'none' returns None."""
        from src.web.pages.ui.plotting.settings_pills import render_preset_pills

        mock_pm.list_presets.return_value = ["isca", "micro"]
        mock_st.pills.return_value = "none"
        result = render_preset_pills(plot_id=1)
        assert result is None

    @patch("src.web.pages.ui.plotting.settings_pills.PresetManager")
    @patch("src.web.pages.ui.plotting.settings_pills.st")
    def test_selecting_preset_returns_name(self, mock_st: MagicMock, mock_pm: MagicMock) -> None:
        """Selecting a preset returns the preset name."""
        from src.web.pages.ui.plotting.settings_pills import render_preset_pills

        mock_pm.list_presets.return_value = ["isca", "micro", "nature"]
        mock_st.pills.return_value = "isca"
        result = render_preset_pills(plot_id=1)
        assert result == "isca"

    @patch("src.web.pages.ui.plotting.settings_pills.PresetManager")
    @patch("src.web.pages.ui.plotting.settings_pills.st")
    def test_options_include_none_and_presets(self, mock_st: MagicMock, mock_pm: MagicMock) -> None:
        """Options list starts with 'none' followed by preset names."""
        from src.web.pages.ui.plotting.settings_pills import render_preset_pills

        mock_pm.list_presets.return_value = ["isca", "micro"]
        mock_st.pills.return_value = "none"
        render_preset_pills(plot_id=5)

        call_args = mock_st.pills.call_args
        options = call_args.kwargs.get("options") or call_args[1].get("options")
        assert options == ["none", "isca", "micro"]

    @patch("src.web.pages.ui.plotting.settings_pills.PresetManager")
    @patch("src.web.pages.ui.plotting.settings_pills.st")
    def test_widget_key_includes_plot_id(self, mock_st: MagicMock, mock_pm: MagicMock) -> None:
        """Widget key is unique per plot."""
        from src.web.pages.ui.plotting.settings_pills import render_preset_pills

        mock_pm.list_presets.return_value = ["isca"]
        mock_st.pills.return_value = "none"
        render_preset_pills(plot_id=42)

        call_args = mock_st.pills.call_args
        key = call_args.kwargs.get("key") or call_args[1].get("key")
        assert key == "preset_selector_42"

    @patch("src.web.pages.ui.plotting.settings_pills.PresetManager")
    @patch("src.web.pages.ui.plotting.settings_pills.st")
    def test_pills_none_returns_none(self, mock_st: MagicMock, mock_pm: MagicMock) -> None:
        """When st.pills returns None (nothing selected), result is None."""
        from src.web.pages.ui.plotting.settings_pills import render_preset_pills

        mock_pm.list_presets.return_value = ["isca"]
        mock_st.pills.return_value = None
        result = render_preset_pills(plot_id=1)
        assert result is None
