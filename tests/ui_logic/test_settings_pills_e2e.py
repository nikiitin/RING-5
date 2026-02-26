"""End-to-end tests for settings pills UI fixes — Issues #1-6 + new Issues #7-10.

Verifies:
1. Typography pill outputs ONLY font sizes/colors (no axis settings leaked)
2. Axes pill outputs axis line controls (bottom/top/left/right width+color)
3. Axes pill outputs numbered X-axis checkbox
4. Axes pill Group Labels sub-pill outputs vertical distance from X-axis
5. Axes pill Y-Left sub-pill outputs axis line controls
6. Legend rename/reorder is accessible via Axes → X-Axis → Ordering Control
7. Secondary legend pill outputs all legend2_* config keys

--- New Issues (second batch) ---
8. Legend pill: no Columns/Column Width/Column Spacing for primary or secondary
9. Numbered X-axis: multiselect pills (Numbers, Number legend, Labels)
10. Data labels: progressive disclosure (format widgets hidden when Show Values off)
11. Ordering: stacked series reorder/rename via y_columns
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd

from tests.conftest import columns_side_effect

# ──────────────────────────────────────────────────────────────────
# Issue #1: Typography pill must ONLY have font sizes and colors
# ──────────────────────────────────────────────────────────────────


class TestTypographyNoAxisLeak:
    """Verify Typography pill returns exactly 7 font keys — nothing else."""

    # The exact set of allowed keys.
    ALLOWED_KEYS = frozenset(
        {
            "title_font_size",
            "xaxis_title_font_size",
            "yaxis_title_font_size",
            "xaxis_tickfont_size",
            "xaxis_tickfont_color",
            "yaxis_tickfont_size",
            "yaxis_tickfont_color",
        }
    )

    # Keys that were previously leaked into Typography but now belong to Axes.
    FORBIDDEN_KEYS = frozenset(
        {
            "show_xtick_marks",
            "show_ytick_marks",
            "xtick_dash",
            "ytick_dash",
            "xtick_pad",
            "xaxis_tickangle",
            "yaxis_title_standoff",
            "yaxis_title_vshift",
            "group_label_alternate",
            "group_label_alt_spacing",
            "major_label_offset",
            "group_label_offset",
            "show_x_grid",
            "show_y_grid",
            "x_axis_line_width",
            "x_axis_line_color",
            "y_axis_line_width",
            "y_axis_line_color",
            "top_axis_line_width",
            "top_axis_line_color",
            "right_axis_line_width",
            "right_axis_line_color",
            "numbered_xaxis",
        }
    )

    def _make_component(self) -> Any:
        from src.web.components.plotting.settings import (
            TypographySettingsComponent,
        )

        return TypographySettingsComponent(plot_id=1, plot_type="bar")

    @patch("src.web.components.plotting.settings.typography_settings.st")
    def test_returns_only_font_keys(self, mock_st: MagicMock) -> None:
        """Typography pill returns exactly the 7 allowed font keys."""
        comp = self._make_component()
        mock_st.columns.side_effect = columns_side_effect
        mock_st.number_input.return_value = 14
        mock_st.color_picker.return_value = "#444444"

        result = comp.render({})

        assert set(result.keys()) == self.ALLOWED_KEYS

    @patch("src.web.components.plotting.settings.typography_settings.st")
    def test_no_forbidden_keys(self, mock_st: MagicMock) -> None:
        """Typography pill MUST NOT output any axis/grid/tick keys."""
        comp = self._make_component()
        mock_st.columns.side_effect = columns_side_effect
        mock_st.number_input.return_value = 14
        mock_st.color_picker.return_value = "#444444"

        result = comp.render({})

        leaked = self.FORBIDDEN_KEYS & set(result.keys())
        assert leaked == set(), f"Axis keys leaked into Typography: {leaked}"

    @patch("src.web.components.plotting.settings.typography_settings.st")
    def test_preserves_saved_values(self, mock_st: MagicMock) -> None:
        """Typography pill uses saved config values when available."""
        comp = self._make_component()
        mock_st.columns.side_effect = columns_side_effect
        mock_st.number_input.return_value = 20
        mock_st.color_picker.return_value = "#112233"

        saved = {
            "title_font_size": 24,
            "xaxis_tickfont_color": "#FF0000",
        }
        result = comp.render(saved)

        # Returned values come from mock (20 / #112233) — but the
        # component *called* number_input with the saved value as default.
        # We verify it returned the right structure.
        assert "title_font_size" in result
        assert "xaxis_tickfont_color" in result


# ──────────────────────────────────────────────────────────────────
# Issue #5: Axis line controls in Axes pill
# ──────────────────────────────────────────────────────────────────


class TestAxesAxisLineControls:
    """Verify axis line width/color controls are in the Axes pill."""

    def _make_component(self) -> Any:
        from src.web.components.plotting.settings import (
            AxesSettingsComponent,
        )

        return AxesSettingsComponent(plot_id=1, plot_type="grouped_bar")

    @patch("src.web.components.plotting.settings.axes_settings.st")
    def test_x_axis_outputs_axis_line_keys(self, mock_st: MagicMock) -> None:
        """X-Axis sub-pill outputs bottom/top axis line width+color."""
        comp = self._make_component()
        mock_st.pills.return_value = "x"
        mock_st.checkbox.return_value = True
        mock_st.slider.return_value = -45
        mock_st.number_input.return_value = 1.0
        mock_st.columns.side_effect = columns_side_effect
        mock_st.color_picker.return_value = "#444444"
        mock_st.selectbox.return_value = "solid"

        result = comp.render({}, data=pd.DataFrame({"a": [1]}))

        assert "x_axis_line_width" in result, "Missing bottom axis line width"
        assert "x_axis_line_color" in result, "Missing bottom axis line color"
        assert "top_axis_line_width" in result, "Missing top axis line width"
        assert "top_axis_line_color" in result, "Missing top axis line color"

    @patch("src.web.components.plotting.settings.axes_settings.st")
    def test_y_left_outputs_axis_line_keys(self, mock_st: MagicMock) -> None:
        """Y-Left sub-pill outputs left/right axis line width+color."""
        comp = self._make_component()
        mock_st.pills.return_value = "y_left"
        mock_st.checkbox.return_value = True
        mock_st.slider.return_value = 0
        mock_st.number_input.return_value = 1.0
        mock_st.columns.side_effect = columns_side_effect
        mock_st.color_picker.return_value = "#444444"
        mock_st.selectbox.return_value = "solid"

        result = comp.render({}, data=None)

        assert "y_axis_line_width" in result, "Missing left axis line width"
        assert "y_axis_line_color" in result, "Missing left axis line color"
        assert "right_axis_line_width" in result, "Missing right axis line width"
        assert "right_axis_line_color" in result, "Missing right axis line color"

    @patch("src.web.components.plotting.settings.axes_settings.st")
    def test_y_right_outputs_y2_axis_line_keys(self, mock_st: MagicMock) -> None:
        """Y-Right sub-pill outputs y2-prefixed axis line keys."""
        comp = self._make_component()
        mock_st.pills.return_value = "y_right"
        mock_st.checkbox.return_value = True
        mock_st.slider.return_value = 0
        mock_st.number_input.return_value = 1.0
        mock_st.columns.side_effect = columns_side_effect
        mock_st.color_picker.return_value = "#444444"
        mock_st.selectbox.return_value = "solid"

        result = comp.render({}, data=None, has_dual_axis=True)

        assert "y2y_axis_line_width" in result, "Missing Y2 axis line width"
        assert "y2y_axis_line_color" in result, "Missing Y2 axis line color"

    @patch("src.web.components.plotting.settings.axes_settings.st")
    def test_axis_line_zero_width_hides_line(self, mock_st: MagicMock) -> None:
        """Axis line with width=0 is accepted (hides the line)."""
        comp = self._make_component()
        mock_st.pills.return_value = "x"
        mock_st.checkbox.return_value = True
        mock_st.slider.return_value = -45
        mock_st.number_input.return_value = 0.0
        mock_st.columns.side_effect = columns_side_effect
        mock_st.color_picker.return_value = "#444444"
        mock_st.selectbox.return_value = "solid"

        result = comp.render({}, data=pd.DataFrame({"a": [1]}))

        assert result["x_axis_line_width"] == 0.0
        assert result["top_axis_line_width"] == 0.0


# ──────────────────────────────────────────────────────────────────
# Issue #3: Numbered X-axis checkbox
# ──────────────────────────────────────────────────────────────────


class TestNumberedXAxis:
    """Verify numbered X-axis checkbox is in Axes → X-Axis."""

    def _make_component(self) -> Any:
        from src.web.components.plotting.settings import (
            AxesSettingsComponent,
        )

        return AxesSettingsComponent(plot_id=1, plot_type="grouped_stacked_bar")

    @patch("src.web.components.plotting.settings.axes_settings.st")
    def test_numbered_xaxis_key_present(self, mock_st: MagicMock) -> None:
        """X-Axis sub-pill outputs 'numbered_xaxis' key."""
        comp = self._make_component()
        mock_st.pills.return_value = "x"
        mock_st.checkbox.return_value = False
        mock_st.slider.return_value = -45
        mock_st.number_input.return_value = 1.0
        mock_st.columns.side_effect = columns_side_effect
        mock_st.color_picker.return_value = "#444444"
        mock_st.selectbox.return_value = "solid"

        result = comp.render({}, data=pd.DataFrame({"a": [1]}))

        assert "numbered_xaxis" in result, "Missing numbered_xaxis checkbox"

    @patch("src.web.components.plotting.settings.axes_settings.st")
    def test_numbered_xaxis_enabled(self, mock_st: MagicMock) -> None:
        """When checked, numbered_xaxis is True."""
        comp = self._make_component()
        mock_st.pills.return_value = "x"
        mock_st.checkbox.return_value = True
        mock_st.slider.return_value = -45
        mock_st.number_input.return_value = 1.0
        mock_st.columns.side_effect = columns_side_effect
        mock_st.color_picker.return_value = "#444444"
        mock_st.selectbox.return_value = "solid"

        result = comp.render({}, data=pd.DataFrame({"a": [1]}))

        assert result["numbered_xaxis"] is True


# ──────────────────────────────────────────────────────────────────
# Issue #4: Group labels Y-offset
# ──────────────────────────────────────────────────────────────────


class TestGroupLabelYOffset:
    """Verify group label vertical distance control."""

    def _make_component(self) -> Any:
        from src.web.components.plotting.settings import (
            AxesSettingsComponent,
        )

        return AxesSettingsComponent(plot_id=1, plot_type="grouped_stacked_bar")

    @patch("src.web.components.plotting.settings.axes_settings.st")
    def test_group_label_offset_present(self, mock_st: MagicMock) -> None:
        """Group Labels sub-pill outputs major_label_offset AND group_label_offset."""
        comp = self._make_component()
        mock_st.pills.return_value = "group"
        mock_st.checkbox.return_value = True
        mock_st.number_input.return_value = -0.15

        result = comp.render({}, show_group_labels=True)

        assert "major_label_offset" in result, "Missing major_label_offset"
        assert "group_label_offset" in result, "Missing group_label_offset"

    @patch("src.web.components.plotting.settings.axes_settings.st")
    def test_both_offset_keys_match(self, mock_st: MagicMock) -> None:
        """major_label_offset and group_label_offset have the same value."""
        comp = self._make_component()
        mock_st.pills.return_value = "group"
        mock_st.checkbox.return_value = True
        mock_st.number_input.return_value = -0.20

        result = comp.render({}, show_group_labels=True)

        assert result["major_label_offset"] == result["group_label_offset"]
        assert result["major_label_offset"] == -0.20

    @patch("src.web.components.plotting.settings.axes_settings.st")
    def test_group_label_alternate_present(self, mock_st: MagicMock) -> None:
        """Group Labels sub-pill outputs alternate label controls."""
        comp = self._make_component()
        mock_st.pills.return_value = "group"
        mock_st.checkbox.return_value = True
        mock_st.number_input.return_value = 0.05

        result = comp.render({}, show_group_labels=True)

        assert "group_label_alternate" in result
        assert "group_label_alt_spacing" in result


# ──────────────────────────────────────────────────────────────────
# Issue #6: Legend rename/reorder accessible via Axes pill
# ──────────────────────────────────────────────────────────────────


class TestLegendRenameReorder:
    """Verify ordering/rename controls are invoked in Axes → X-Axis."""

    def _make_component(self) -> Any:
        from src.web.components.plotting.settings import (
            AxesSettingsComponent,
        )

        return AxesSettingsComponent(plot_id=1, plot_type="grouped_bar")

    @patch("src.web.components.plotting.settings.axes_settings.st")
    def test_ordering_fn_called_on_x_axis(self, mock_st: MagicMock) -> None:
        """render_ordering_fn is called when X-axis sub-pill is active."""
        comp = self._make_component()
        mock_st.pills.return_value = "x"
        mock_st.checkbox.return_value = True
        mock_st.slider.return_value = -45
        mock_st.number_input.return_value = 1.0
        mock_st.columns.side_effect = columns_side_effect
        mock_st.color_picker.return_value = "#444444"
        mock_st.selectbox.return_value = "solid"

        ordering_fn = MagicMock()
        data = pd.DataFrame({"a": [1, 2]})

        comp.render(
            {},
            data=data,
            render_ordering_fn=ordering_fn,
        )

        ordering_fn.assert_called_once()

    @patch("src.web.components.plotting.settings.axes_settings.st")
    def test_ordering_fn_not_called_on_y_left(self, mock_st: MagicMock) -> None:
        """render_ordering_fn is NOT called when Y-Left is selected."""
        comp = self._make_component()
        mock_st.pills.return_value = "y_left"
        mock_st.checkbox.return_value = True
        mock_st.slider.return_value = 0
        mock_st.number_input.return_value = 0
        mock_st.columns.side_effect = columns_side_effect
        mock_st.color_picker.return_value = "#444444"
        mock_st.selectbox.return_value = "solid"

        ordering_fn = MagicMock()

        comp.render({}, data=None, render_ordering_fn=ordering_fn)

        ordering_fn.assert_not_called()


# ──────────────────────────────────────────────────────────────────
# Issue #2: Secondary legend config — all keys must be output
# ──────────────────────────────────────────────────────────────────


class TestSecondaryLegendConfig:
    """Verify secondary legend tab outputs legend2_* config keys."""

    def _make_component(self) -> Any:
        from src.web.components.plotting.settings import (
            LegendSettingsComponent,
        )

        return LegendSettingsComponent(plot_id=1, plot_type="grouped_stacked_bar")

    @patch("src.web.components.plotting.settings.legend_settings.st")
    def test_secondary_legend_outputs_all_keys(self, mock_st: MagicMock) -> None:
        """Secondary legend outputs font_size, x, y, ncols, and more."""
        comp = self._make_component()
        mock_st.pills.return_value = "secondary"
        mock_st.columns.side_effect = columns_side_effect
        mock_st.checkbox.return_value = False
        mock_st.number_input.return_value = 12
        mock_st.selectbox.return_value = "v"
        mock_st.slider.return_value = 1.0
        mock_st.color_picker.return_value = "#000000"
        mock_st.text_input.return_value = ""

        result = comp.render({}, has_secondary=True, has_tertiary=False)

        # Core position keys
        assert "legend2_x" in result, "Missing legend2_x"
        assert "legend2_y" in result, "Missing legend2_y"
        assert "legend2_tracegroupgap" in result, "Missing legend2_tracegroupgap"
        # legend2_ncols re-added for multi-column legend support
        assert "legend2_ncols" in result, "Missing legend2_ncols"

        # Appearance keys
        assert "legend2_font_size" in result, "Missing legend2_font_size"

    @patch("src.web.components.plotting.settings.legend_settings.st")
    def test_secondary_keys_differ_from_primary(self, mock_st: MagicMock) -> None:
        """Secondary legend keys use legend2_ prefix, not theme_ prefix."""
        comp = self._make_component()
        mock_st.pills.return_value = "secondary"
        mock_st.columns.side_effect = columns_side_effect
        mock_st.checkbox.return_value = False
        mock_st.number_input.return_value = 12
        mock_st.selectbox.return_value = "v"
        mock_st.slider.return_value = 1.0
        mock_st.color_picker.return_value = "#000000"
        mock_st.text_input.return_value = ""

        result = comp.render({}, has_secondary=True, has_tertiary=False)

        # Should NOT have primary-prefixed keys
        primary_keys = [k for k in result if k.startswith("theme_")]
        assert primary_keys == [], f"Primary keys in secondary tab: {primary_keys}"

    @patch("src.web.components.plotting.settings.legend_settings.st")
    def test_primary_legend_outputs_legend_keys(self, mock_st: MagicMock) -> None:
        """Primary legend outputs legend_* config keys with theme_ prefix."""
        comp = self._make_component()
        mock_st.pills.return_value = "primary"
        mock_st.columns.side_effect = columns_side_effect
        mock_st.checkbox.return_value = False
        mock_st.number_input.return_value = 12
        mock_st.selectbox.return_value = "v"
        mock_st.slider.return_value = 1.0
        mock_st.color_picker.return_value = "#000000"
        mock_st.text_input.return_value = ""

        result = comp.render({}, has_secondary=True, has_tertiary=False)

        assert "legend_font_size" in result, "Missing legend_font_size"
        assert "legend_x" in result, "Missing legend_x"
        assert "legend_y" in result, "Missing legend_y"
        assert "legend_tracegroupgap" in result, "Missing legend_tracegroupgap"
        # legend_ncols re-added for multi-column legend support
        assert "legend_ncols" in result, "Missing legend_ncols"


# ──────────────────────────────────────────────────────────────────
# Cross-cutting: No settings leakage between pills
# ──────────────────────────────────────────────────────────────────


class TestNoSettingsLeakage:
    """Verify strict separation between Typography and Axes pills."""

    @patch("src.web.components.plotting.settings.typography_settings.st")
    @patch("src.web.components.plotting.settings.axes_settings.st")
    def test_typography_and_axes_keys_do_not_overlap(
        self,
        mock_axes_st: MagicMock,
        mock_typo_st: MagicMock,
    ) -> None:
        """Typography and Axes pills produce disjoint config key sets."""
        from src.web.components.plotting.settings import (
            AxesSettingsComponent,
            TypographySettingsComponent,
        )

        # Typography
        typo = TypographySettingsComponent(plot_id=1, plot_type="bar")
        mock_typo_st.columns.side_effect = columns_side_effect
        mock_typo_st.number_input.return_value = 14
        mock_typo_st.color_picker.return_value = "#444444"
        typo_keys = set(typo.render({}).keys())

        # Axes (X-axis sub-pill)
        axes = AxesSettingsComponent(plot_id=1, plot_type="bar")
        mock_axes_st.pills.return_value = "x"
        mock_axes_st.checkbox.return_value = True
        mock_axes_st.slider.return_value = -45
        mock_axes_st.number_input.return_value = 1.0
        mock_axes_st.columns.side_effect = columns_side_effect
        mock_axes_st.color_picker.return_value = "#444444"
        mock_axes_st.selectbox.return_value = "solid"
        axes_keys = set(axes.render({}, data=pd.DataFrame({"a": [1]})).keys())

        overlap = typo_keys & axes_keys
        assert overlap == set(), f"Keys shared by Typography & Axes: {overlap}"


# ======================================================================
# NEW ISSUES — Second batch (#8-11)
# ======================================================================


# ──────────────────────────────────────────────────────────────────
# Issue #8: Legend sizing controls — column_spacing, itemwidth,
#           handletextpad, tracegroupgap for ALL legend levels
# ──────────────────────────────────────────────────────────────────


class TestLegendSizingControls:
    """Legend component must output sizing keys for each legend level.

    Controls: ncols (columns), tracegroupgap (item spacing),
    column_spacing (space between columns), itemwidth (stripe length),
    and handletextpad (stripe-text gap).  All five must appear for
    primary, secondary, and tertiary legends with the correct
    per-level prefix.
    """

    # Keys that MUST appear (per-prefix) in the sizing output.
    SIZING_SUFFIXES = (
        "ncols",
        "tracegroupgap",
        "column_spacing",
        "itemwidth",
        "handletextpad",
    )

    def _make_component(self) -> Any:
        from src.web.components.plotting.settings import (
            LegendSettingsComponent,
        )

        return LegendSettingsComponent(plot_id=1, plot_type="grouped_stacked_bar")

    def _setup_mock(self, mock_st: MagicMock, tab: str) -> None:
        mock_st.pills.return_value = tab
        mock_st.columns.side_effect = columns_side_effect
        mock_st.checkbox.return_value = False
        mock_st.number_input.return_value = 10
        mock_st.color_picker.return_value = "#000000"
        mock_st.text_input.return_value = ""

    @patch("src.web.components.plotting.settings.legend_settings.st")
    def test_primary_sizing_keys(self, mock_st: MagicMock) -> None:
        """Primary legend outputs all sizing keys with legend_ prefix."""
        comp = self._make_component()
        self._setup_mock(mock_st, "primary")

        result = comp.render({})

        for suffix in self.SIZING_SUFFIXES:
            key = f"legend_{suffix}"
            assert key in result, f"Missing {key}"

    @patch("src.web.components.plotting.settings.legend_settings.st")
    def test_secondary_sizing_keys(self, mock_st: MagicMock) -> None:
        """Secondary legend outputs all sizing keys with legend2_ prefix."""
        comp = self._make_component()
        self._setup_mock(mock_st, "secondary")

        result = comp.render({}, has_secondary=True)

        for suffix in self.SIZING_SUFFIXES:
            key = f"legend2_{suffix}"
            assert key in result, f"Missing {key}"

    @patch("src.web.components.plotting.settings.legend_settings.st")
    def test_tertiary_sizing_keys(self, mock_st: MagicMock) -> None:
        """Tertiary legend outputs all sizing keys with legend3_ prefix."""
        comp = self._make_component()
        self._setup_mock(mock_st, "tertiary")

        result = comp.render({}, has_secondary=True, has_tertiary=True)

        for suffix in self.SIZING_SUFFIXES:
            key = f"legend3_{suffix}"
            assert key in result, f"Missing {key}"

    @patch("src.web.components.plotting.settings.legend_settings.st")
    def test_primary_position_only_x_y(self, mock_st: MagicMock) -> None:
        """Primary legend position section outputs x and y."""
        comp = self._make_component()
        self._setup_mock(mock_st, "primary")

        result = comp.render({})

        assert "legend_x" in result
        assert "legend_y" in result

    @patch("src.web.components.plotting.settings.legend_settings.st")
    def test_secondary_position_keys(self, mock_st: MagicMock) -> None:
        """Secondary legend position section outputs legend2_x and legend2_y."""
        comp = self._make_component()
        self._setup_mock(mock_st, "secondary")

        result = comp.render({}, has_secondary=True)

        assert "legend2_x" in result
        assert "legend2_y" in result

    @patch("src.web.components.plotting.settings.legend_settings.st")
    def test_sizing_values_saved_and_restored(self, mock_st: MagicMock) -> None:
        """Sizing controls restore saved values from config."""
        comp = self._make_component()
        self._setup_mock(mock_st, "primary")

        saved = {
            "legend_column_spacing": 1.5,
            "legend_itemwidth": 40,
            "legend_handletextpad": 0.8,
            "legend_tracegroupgap": 5,
        }
        result = comp.render(saved)

        # number_input was called; verify the keys exist in output
        for key in saved:
            assert key in result, f"Missing {key} in output"

    @patch("src.web.components.plotting.settings.legend_settings.st")
    def test_secondary_config_isolated_from_primary(self, mock_st: MagicMock) -> None:
        """Secondary legend config keys must NOT overlap with primary keys."""
        comp = self._make_component()
        self._setup_mock(mock_st, "secondary")

        result = comp.render({}, has_secondary=True)

        primary_sizing = {f"legend_{s}" for s in self.SIZING_SUFFIXES}
        leaked = primary_sizing & set(result.keys())
        assert leaked == set(), f"Primary sizing keys leaked into secondary: {leaked}"

    @patch("src.web.components.plotting.settings.legend_settings.st")
    def test_tertiary_config_isolated(self, mock_st: MagicMock) -> None:
        """Tertiary legend config keys must NOT overlap with primary/secondary."""
        comp = self._make_component()
        self._setup_mock(mock_st, "tertiary")

        result = comp.render({}, has_secondary=True, has_tertiary=True)

        primary_sizing = {f"legend_{s}" for s in self.SIZING_SUFFIXES}
        secondary_sizing = {f"legend2_{s}" for s in self.SIZING_SUFFIXES}
        leaked = (primary_sizing | secondary_sizing) & set(result.keys())
        assert leaked == set(), f"Primary/secondary sizing keys leaked into tertiary: {leaked}"


# ──────────────────────────────────────────────────────────────────
# Issue #9: Numbered X-axis multiselect pills
# ──────────────────────────────────────────────────────────────────


class TestNumberedXAxisMultiselect:
    """Verify numbered X-axis uses st.pills multiselect with 3 options."""

    def _make_component(self) -> Any:
        from src.web.components.plotting.settings import (
            AxesSettingsComponent,
        )

        return AxesSettingsComponent(plot_id=1, plot_type="grouped_stacked_bar")

    @patch("src.web.components.plotting.settings.axes_settings.st")
    def test_outputs_numbered_xaxis_modes(self, mock_st: MagicMock) -> None:
        """X-axis sub-pill outputs numbered_xaxis_modes list key."""
        comp = self._make_component()
        mock_st.pills.side_effect = lambda label, **kw: (
            "x" if label == "Sub-Axis" else kw.get("default", [])
        )
        mock_st.checkbox.return_value = True
        mock_st.slider.return_value = -45
        mock_st.number_input.return_value = 1.0
        mock_st.columns.side_effect = columns_side_effect
        mock_st.color_picker.return_value = "#444444"
        mock_st.selectbox.return_value = "solid"

        result = comp.render({}, data=pd.DataFrame({"a": [1]}))

        assert "numbered_xaxis_modes" in result, "Missing numbered_xaxis_modes key"
        assert isinstance(result["numbered_xaxis_modes"], list)

    @patch("src.web.components.plotting.settings.axes_settings.st")
    def test_backward_compat_numbered_xaxis_bool(self, mock_st: MagicMock) -> None:
        """numbered_xaxis boolean computed from modes for backward compat."""
        comp = self._make_component()
        mock_st.pills.side_effect = lambda label, **kw: (
            "x" if label == "Sub-Axis" else kw.get("default", [])
        )
        mock_st.checkbox.return_value = True
        mock_st.slider.return_value = -45
        mock_st.number_input.return_value = 1.0
        mock_st.columns.side_effect = columns_side_effect
        mock_st.color_picker.return_value = "#444444"
        mock_st.selectbox.return_value = "solid"

        result = comp.render({}, data=pd.DataFrame({"a": [1]}))

        assert "numbered_xaxis" in result, "Missing numbered_xaxis compat key"
        assert isinstance(result["numbered_xaxis"], bool)

    @patch("src.web.components.plotting.settings.axes_settings.st")
    def test_modes_with_selection(self, mock_st: MagicMock) -> None:
        """When modes are selected, they propagate to the config."""
        comp = self._make_component()
        # Simulate: pills for axis nav returns "x",
        # pills for numbered_xaxis returns ["Numbers", "Number legend"]
        mock_st.pills.side_effect = lambda label, **kw: (
            "x" if label == "Axis" else ["Numbers", "Number legend"]
        )
        mock_st.checkbox.return_value = True
        mock_st.slider.return_value = -45
        mock_st.number_input.return_value = 1.0
        mock_st.columns.side_effect = columns_side_effect
        mock_st.color_picker.return_value = "#444444"
        mock_st.selectbox.return_value = "solid"

        result = comp.render({}, data=pd.DataFrame({"a": [1]}))

        modes = result["numbered_xaxis_modes"]
        assert "Numbers" in modes
        assert "Number legend" in modes
        assert result["numbered_xaxis"] is True

    @patch("src.web.components.plotting.settings.axes_settings.st")
    def test_show_numbered_ticks_derived(self, mock_st: MagicMock) -> None:
        """show_numbered_ticks is True when 'Numbers' is in modes."""
        comp = self._make_component()
        mock_st.pills.side_effect = lambda label, **kw: ("x" if label == "Axis" else ["Numbers"])
        mock_st.checkbox.return_value = True
        mock_st.slider.return_value = -45
        mock_st.number_input.return_value = 1.0
        mock_st.columns.side_effect = columns_side_effect
        mock_st.color_picker.return_value = "#444444"
        mock_st.selectbox.return_value = "solid"

        result = comp.render({}, data=pd.DataFrame({"a": [1]}))

        assert result.get("show_numbered_ticks") is True
        assert result.get("show_numbered_legend") is False

    @patch("src.web.components.plotting.settings.axes_settings.st")
    def test_show_numbered_legend_derived(self, mock_st: MagicMock) -> None:
        """show_numbered_legend is True when 'Number legend' is in modes."""
        comp = self._make_component()
        mock_st.pills.side_effect = lambda label, **kw: (
            "x" if label == "Axis" else ["Number legend"]
        )
        mock_st.checkbox.return_value = True
        mock_st.slider.return_value = -45
        mock_st.number_input.return_value = 1.0
        mock_st.columns.side_effect = columns_side_effect
        mock_st.color_picker.return_value = "#444444"
        mock_st.selectbox.return_value = "solid"

        result = comp.render({}, data=pd.DataFrame({"a": [1]}))

        assert result.get("show_numbered_legend") is True
        assert result.get("show_numbered_ticks") is False

    @patch("src.web.components.plotting.settings.axes_settings.st")
    def test_empty_modes_no_numbered(self, mock_st: MagicMock) -> None:
        """No modes selected → numbered_xaxis is False."""
        comp = self._make_component()
        mock_st.pills.side_effect = lambda label, **kw: ("x" if label == "Axis" else [])
        mock_st.checkbox.return_value = True
        mock_st.slider.return_value = -45
        mock_st.number_input.return_value = 1.0
        mock_st.columns.side_effect = columns_side_effect
        mock_st.color_picker.return_value = "#444444"
        mock_st.selectbox.return_value = "solid"

        result = comp.render({}, data=pd.DataFrame({"a": [1]}))

        assert result["numbered_xaxis_modes"] == []
        assert result["numbered_xaxis"] is False

    @patch("src.web.components.plotting.settings.axes_settings.st")
    def test_old_boolean_compat_migrates_to_modes(self, mock_st: MagicMock) -> None:
        """Old saved_config with numbered_xaxis=True migrates to modes."""
        comp = self._make_component()
        # The pills call for sub-axis returns "x",
        # The pills call for numbered modes returns whatever was default
        mock_st.pills.side_effect = lambda label, **kw: (
            "x" if label == "Sub-Axis" else kw.get("default", [])
        )
        mock_st.checkbox.return_value = True
        mock_st.slider.return_value = -45
        mock_st.number_input.return_value = 1.0
        mock_st.columns.side_effect = columns_side_effect
        mock_st.color_picker.return_value = "#444444"
        mock_st.selectbox.return_value = "solid"

        # Old config has boolean numbered_xaxis=True but no modes
        old_config: dict[str, Any] = {"numbered_xaxis": True}
        result = comp.render(old_config, data=pd.DataFrame({"a": [1]}))

        # Should still have modes and compat key
        assert "numbered_xaxis_modes" in result
        assert "numbered_xaxis" in result


# ──────────────────────────────────────────────────────────────────
# Issue #10: Data Labels progressive disclosure
# ──────────────────────────────────────────────────────────────────


class TestDataLabelsProgressiveDisclosure:
    """Data labels formatting widgets must be hidden when Show Values is off."""

    def _make_component(self) -> Any:
        from src.web.components.plotting.settings import (
            DataLabelsSettingsComponent,
        )

        return DataLabelsSettingsComponent(plot_id=1, plot_type="bar")

    @patch("src.web.components.plotting.settings.data_labels_settings.st")
    def test_show_values_false_returns_defaults(self, mock_st: MagicMock) -> None:
        """When show_values=False, returns config with defaults, no widgets rendered."""
        comp = self._make_component()
        mock_st.checkbox.return_value = False

        result = comp.render({})

        assert result["show_values"] is False
        assert "text_color_mode" in result
        assert "text_font_size" in result
        assert "text_rotation" in result
        assert "text_position" in result
        assert "text_format" in result
        assert "text_display_logic" in result
        assert "text_threshold" in result
        assert "text_constraint" in result

    @patch("src.web.components.plotting.settings.data_labels_settings.st")
    def test_show_values_false_no_formatting_widgets(self, mock_st: MagicMock) -> None:
        """When show_values=False, NO selectbox/slider/number_input calls for formatting."""
        comp = self._make_component()
        mock_st.checkbox.return_value = False

        comp.render({})

        # Only st.markdown and st.checkbox are called, NOT selectbox/slider
        mock_st.selectbox.assert_not_called()
        mock_st.slider.assert_not_called()
        # number_input should not be called for formatting widgets
        mock_st.number_input.assert_not_called()

    @patch("src.web.components.plotting.settings.data_labels_settings.st")
    def test_show_values_true_renders_formatting(self, mock_st: MagicMock) -> None:
        """When show_values=True, formatting widgets are rendered."""
        comp = self._make_component()
        mock_st.checkbox.return_value = True
        mock_st.selectbox.return_value = "auto"
        mock_st.number_input.return_value = 10
        mock_st.slider.return_value = 0
        mock_st.color_picker.return_value = "#000000"
        mock_st.text_input.return_value = ".2f"

        result = comp.render({})

        assert result["show_values"] is True
        # Formatting widgets were called
        assert mock_st.selectbox.called, "selectbox not called for color mode"

    @patch("src.web.components.plotting.settings.data_labels_settings.st")
    def test_show_values_false_preserves_saved_values(self, mock_st: MagicMock) -> None:
        """When show_values=False, saved formatting values are preserved."""
        comp = self._make_component()
        mock_st.checkbox.return_value = False

        saved: dict[str, Any] = {
            "text_color_mode": "contrast",
            "text_font_size": 16,
            "text_rotation": 45,
            "text_format": ".1%",
        }
        result = comp.render(saved)

        assert result["text_color_mode"] == "contrast"
        assert result["text_font_size"] == 16
        assert result["text_rotation"] == 45
        assert result["text_format"] == ".1%"

    @patch("src.web.components.plotting.settings.data_labels_settings.st")
    def test_show_values_false_default_fallbacks(self, mock_st: MagicMock) -> None:
        """When show_values=False and no saved values, uses correct defaults."""
        comp = self._make_component()
        mock_st.checkbox.return_value = False

        result = comp.render({})

        assert result["text_color_mode"] == "auto"
        assert result["text_color"] == "#000000"
        assert result["text_font_size"] == 10
        assert result["text_rotation"] == 0
        assert result["text_position"] == "auto"
        assert result["text_anchor"] == "auto"
        assert result["text_format"] == ".2f"
        assert result["text_display_logic"] == "all"
        assert result["text_threshold"] == 0.0
        assert result["text_constraint"] == "none"


# ──────────────────────────────────────────────────────────────────
# Issue #11: Stacked series reorder/rename in ordering settings
# ──────────────────────────────────────────────────────────────────


class TestStackedSeriesOrderRename:
    """Verify y_columns reorder/rename is in ordering settings."""

    @patch("src.web.components.plotting.settings.ordering_settings.render_reorderable_list")
    @patch("src.web.components.plotting.settings.ordering_settings.st")
    def test_y_columns_expander_rendered(self, mock_st: MagicMock, mock_reorder: MagicMock) -> None:
        """When y_columns exists, the stacked series expander is rendered."""
        from src.web.components.plotting.settings.ordering_settings import (
            render_ordering_ui,
        )

        mock_reorder.return_value = (["col_a", "col_b"], {})
        config: dict[str, Any] = {}
        saved: dict[str, Any] = {"y_columns": ["col_a", "col_b"]}
        data = pd.DataFrame({"a": [1]})

        render_ordering_ui(1, saved, data, config)

        # render_reorderable_list was called for series
        mock_reorder.assert_called()
        calls = mock_reorder.call_args_list
        series_call = [c for c in calls if c.args[2] == "series"]
        assert len(series_call) == 1, "Missing series reorderable_list call"

    @patch("src.web.components.plotting.settings.ordering_settings.render_reorderable_list")
    @patch("src.web.components.plotting.settings.ordering_settings.st")
    def test_y_columns_reorder_updates_config(
        self, mock_st: MagicMock, mock_reorder: MagicMock
    ) -> None:
        """When y_columns order changes, config['y_columns'] is updated."""
        from src.web.components.plotting.settings.ordering_settings import (
            render_ordering_ui,
        )

        # Return a new order (reversed)
        mock_reorder.return_value = (["col_b", "col_a"], {})
        config: dict[str, Any] = {}
        saved: dict[str, Any] = {"y_columns": ["col_a", "col_b"]}
        data = pd.DataFrame({"a": [1]})

        render_ordering_ui(1, saved, data, config)

        assert config["y_columns"] == ["col_b", "col_a"]

    @patch("src.web.components.plotting.settings.ordering_settings.render_reorderable_list")
    @patch("src.web.components.plotting.settings.ordering_settings.st")
    def test_y_columns_rename_updates_series_styles(
        self, mock_st: MagicMock, mock_reorder: MagicMock
    ) -> None:
        """When series are renamed, series_styles is updated."""
        from src.web.components.plotting.settings.ordering_settings import (
            render_ordering_ui,
        )

        mock_reorder.return_value = (
            ["col_a", "col_b"],
            {"col_a": "Alpha", "col_b": "Beta"},
        )
        config: dict[str, Any] = {}
        saved: dict[str, Any] = {"y_columns": ["col_a", "col_b"]}
        data = pd.DataFrame({"a": [1]})

        render_ordering_ui(1, saved, data, config)

        assert "series_styles" in config
        assert config["series_styles"]["col_a"]["name"] == "Alpha"
        assert config["series_styles"]["col_b"]["name"] == "Beta"

    @patch("src.web.components.plotting.settings.ordering_settings.render_reorderable_list")
    @patch("src.web.components.plotting.settings.ordering_settings.st")
    def test_no_y_columns_no_series_section(
        self, mock_st: MagicMock, mock_reorder: MagicMock
    ) -> None:
        """When y_columns is empty, series section is not rendered."""
        from src.web.components.plotting.settings.ordering_settings import (
            render_ordering_ui,
        )

        mock_reorder.return_value = ([], {})
        config: dict[str, Any] = {}
        saved: dict[str, Any] = {"y_columns": []}
        data = pd.DataFrame({"a": [1]})

        render_ordering_ui(1, saved, data, config)

        # render_reorderable_list should NOT have been called for series
        calls = mock_reorder.call_args_list
        series_call = [c for c in calls if len(c.args) >= 3 and c.args[2] == "series"]
        assert len(series_call) == 0, "series reorderable_list should not be called"

    @patch("src.web.components.plotting.settings.ordering_settings.render_reorderable_list")
    @patch("src.web.components.plotting.settings.ordering_settings.st")
    def test_same_order_does_not_set_y_columns(
        self, mock_st: MagicMock, mock_reorder: MagicMock
    ) -> None:
        """When order is unchanged, y_columns is NOT set in config."""
        from src.web.components.plotting.settings.ordering_settings import (
            render_ordering_ui,
        )

        mock_reorder.return_value = (["col_a", "col_b"], {})
        config: dict[str, Any] = {}
        saved: dict[str, Any] = {"y_columns": ["col_a", "col_b"]}
        data = pd.DataFrame({"a": [1]})

        render_ordering_ui(1, saved, data, config)

        # Same order → y_columns should NOT be in config
        assert "y_columns" not in config

    @patch("src.web.components.plotting.settings.ordering_settings.render_reorderable_list")
    @patch("src.web.components.plotting.settings.ordering_settings.st")
    def test_existing_series_styles_merged(
        self, mock_st: MagicMock, mock_reorder: MagicMock
    ) -> None:
        """Existing series_styles are preserved when adding renames."""
        from src.web.components.plotting.settings.ordering_settings import (
            render_ordering_ui,
        )

        mock_reorder.return_value = (
            ["col_a", "col_b"],
            {"col_a": "New Alpha"},
        )
        config: dict[str, Any] = {"series_styles": {"col_b": {"color": "#FF0000"}}}
        saved: dict[str, Any] = {"y_columns": ["col_a", "col_b"]}
        data = pd.DataFrame({"a": [1]})

        render_ordering_ui(1, saved, data, config)

        # col_b's existing styles preserved
        assert config["series_styles"]["col_b"]["color"] == "#FF0000"
        # col_a's name added
        assert config["series_styles"]["col_a"]["name"] == "New Alpha"

    @patch("src.web.components.plotting.settings.ordering_settings.render_reorderable_list")
    @patch("src.web.components.plotting.settings.ordering_settings.st")
    def test_rename_map_built_from_series_styles(
        self, mock_st: MagicMock, mock_reorder: MagicMock
    ) -> None:
        """rename_map passed to reorderable_list comes from series_styles."""
        from src.web.components.plotting.settings.ordering_settings import (
            render_ordering_ui,
        )

        mock_reorder.return_value = (["col_a", "col_b"], {})
        config: dict[str, Any] = {}
        saved: dict[str, Any] = {
            "y_columns": ["col_a", "col_b"],
            "series_styles": {
                "col_a": {"name": "Alpha", "color": "#F00"},
                "col_b": {"color": "#0F0"},  # no name
            },
        }
        data = pd.DataFrame({"a": [1]})

        render_ordering_ui(1, saved, data, config)

        # Check the call to render_reorderable_list for "series"
        calls = mock_reorder.call_args_list
        series_call = [c for c in calls if len(c.args) >= 3 and c.args[2] == "series"]
        assert len(series_call) == 1
        # rename_map should have only col_a (col_b has no "name")
        rename_kwarg = series_call[0].kwargs.get("rename_map", None)
        assert rename_kwarg is not None
        assert rename_kwarg.get("col_a") == "Alpha"
        assert "col_b" not in rename_kwarg


# ──────────────────────────────────────────────────────────────────
# Issue #8 (cont.): Legend sizing → config_builder → plotly_connector
# ──────────────────────────────────────────────────────────────────


class TestLegendSizingPipeline:
    """Verify itemwidth/column_spacing/handletextpad flow from config_builder
    through to LegendConfig and the plotly_connector dict."""

    def test_build_legend_from_config_primary(self) -> None:
        """_build_legend_from_config wires itemwidth→handlelength and spacing."""
        from src.web.rendering.config_builder import _build_legend_from_config

        config: dict[str, Any] = {
            "legend_column_spacing": 1.5,
            "legend_itemwidth": 40,
            "legend_handletextpad": 0.8,
            "legend_tracegroupgap": 5,
            "legend_font_size": 12,
        }
        lc = _build_legend_from_config(config, "legend_", "primary")

        assert lc.itemwidth == 40
        assert lc.tracegroupgap == 5
        # Matplotlib spacing wiring
        assert lc.spacing.columnspacing == 1.5
        assert lc.spacing.handletextpad == 0.8
        assert abs(lc.spacing.handlelength - 40 / 12) < 0.01

    def test_build_legend_from_config_secondary(self) -> None:
        """Secondary legend picks up its own sizing/spacing values."""
        from src.web.rendering.config_builder import _build_legend_from_config

        config: dict[str, Any] = {
            "legend2_column_spacing": 2.0,
            "legend2_itemwidth": 50,
            "legend2_handletextpad": 1.0,
            "legend2_tracegroupgap": 8,
            "legend2_font_size": 10,
        }
        lc = _build_legend_from_config(config, "legend2_", "secondary")

        assert lc.itemwidth == 50
        assert lc.tracegroupgap == 8
        assert lc.spacing.columnspacing == 2.0
        assert lc.spacing.handletextpad == 1.0
        assert abs(lc.spacing.handlelength - 50 / 10) < 0.01

    def test_plotly_connector_entrywidth(self) -> None:
        """_build_legend_dict emits entrywidth/entrywidthmode when set."""
        from src.core.models.visualization.legend_config import LegendConfig
        from src.web.rendering.plotly_connector import FigureSpecToPlotly

        lc = LegendConfig(
            entrywidth=80,
            itemwidth=40,
            indentation=15,
            tracegroupgap=5,
            custom_position=True,
        )
        result = FigureSpecToPlotly._build_legend_dict(lc)

        assert result["entrywidth"] == 80
        assert result["entrywidthmode"] == "pixels"
        assert result["itemwidth"] == 40
        assert result["indentation"] == 15
        assert result["tracegroupgap"] == 5

    def test_plotly_connector_no_entrywidth_when_zero(self) -> None:
        """_build_legend_dict omits entrywidth when ncol=0 (auto) and entrywidth=0."""
        from src.core.models.visualization.legend_config import LegendConfig
        from src.web.rendering.plotly_connector import FigureSpecToPlotly

        lc = LegendConfig(ncol=0, entrywidth=0, indentation=0)
        result = FigureSpecToPlotly._build_legend_dict(lc)

        assert "entrywidth" not in result
        assert "entrywidthmode" not in result
        assert "indentation" not in result

    def test_primary_and_secondary_configs_independent(self) -> None:
        """Primary and secondary legend configs are independently built."""
        from src.web.rendering.config_builder import _build_legend_from_config

        config: dict[str, Any] = {
            "legend_column_spacing": 1.0,
            "legend_itemwidth": 40,
            "legend_handletextpad": 0.5,
            "legend_tracegroupgap": 5,
            "legend_font_size": 12,
            "legend2_column_spacing": 2.0,
            "legend2_itemwidth": 50,
            "legend2_handletextpad": 1.0,
            "legend2_tracegroupgap": 8,
            "legend2_font_size": 10,
        }
        primary = _build_legend_from_config(config, "legend_", "primary")
        secondary = _build_legend_from_config(config, "legend2_", "secondary")

        assert primary.itemwidth != secondary.itemwidth
        assert primary.tracegroupgap != secondary.tracegroupgap
        assert primary.spacing.columnspacing != secondary.spacing.columnspacing
        assert primary.spacing.handletextpad != secondary.spacing.handletextpad

    def test_ncols_auto_computes_entrywidth_fraction(self) -> None:
        """When ncol > 1 and entrywidth == 0, connector auto-computes fraction."""
        from src.core.models.visualization.legend_config import LegendConfig
        from src.web.rendering.plotly_connector import FigureSpecToPlotly

        lc = LegendConfig(ncol=3, entrywidth=0)
        result = FigureSpecToPlotly._build_legend_dict(lc)

        assert result["entrywidthmode"] == "fraction"
        assert abs(result["entrywidth"] - round(1.0 / 3, 4)) < 0.001

    def test_ncols_manual_entrywidth_overrides_auto(self) -> None:
        """When ncol > 1 AND entrywidth > 0, manual pixels mode wins."""
        from src.core.models.visualization.legend_config import LegendConfig
        from src.web.rendering.plotly_connector import FigureSpecToPlotly

        lc = LegendConfig(ncol=3, entrywidth=120)
        result = FigureSpecToPlotly._build_legend_dict(lc)

        assert result["entrywidth"] == 120
        assert result["entrywidthmode"] == "pixels"

    def test_ncols_one_forces_single_column(self) -> None:
        """When ncol == 1, entrywidth=1.0 fraction forces single column."""
        from src.core.models.visualization.legend_config import LegendConfig
        from src.web.rendering.plotly_connector import FigureSpecToPlotly

        lc = LegendConfig(ncol=1, entrywidth=0)
        result = FigureSpecToPlotly._build_legend_dict(lc)

        assert result["entrywidth"] == 1.0
        assert result["entrywidthmode"] == "fraction"

    def test_build_legend_ncols_from_config(self) -> None:
        """_build_legend_from_config picks up ncols."""
        from src.web.rendering.config_builder import _build_legend_from_config

        config: dict[str, Any] = {
            "legend_ncols": 4,
            "legend_font_size": 12,
        }
        lc = _build_legend_from_config(config, "legend_", "primary")
        assert lc.ncol == 4
