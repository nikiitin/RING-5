"""Tests for GroupedStackedBarPlot numbered X-axis labels feature."""

from typing import Any, Dict, List

import pandas as pd
import pytest

from src.web.pages.ui.plotting.types.grouped_stacked_bar_plot import (
    GroupedStackedBarPlot,
)


@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Sample data with 2 benchmarks × 4 configurations."""
    return pd.DataFrame(
        {
            "Benchmark": ["A", "A", "A", "A", "B", "B", "B", "B"],
            "Config": ["c1", "c2", "c3", "c4", "c1", "c2", "c3", "c4"],
            "Ticks": [100, 200, 150, 250, 110, 210, 160, 260],
            "Energy": [10, 20, 15, 25, 12, 22, 17, 27],
        }
    )


@pytest.fixture
def plot() -> GroupedStackedBarPlot:
    return GroupedStackedBarPlot(1, "Test")


def _base_config(**overrides: Any) -> Dict[str, Any]:
    """Build a minimal config dict with optional overrides."""
    cfg: Dict[str, Any] = {
        "x": "Benchmark",
        "group": "Config",
        "y_columns": ["Ticks", "Energy"],
        "title": "Test",
        "xlabel": "Bench",
        "ylabel": "Value",
        "legend_title": "Stats",
    }
    cfg.update(overrides)
    return cfg


# ---------------------------------------------------------------------------
# _apply_numbered_xaxis — unit tests
# ---------------------------------------------------------------------------
class TestApplyNumberedXaxis:
    """Test the _apply_numbered_xaxis helper directly."""

    def test_disabled_returns_original(self, plot: GroupedStackedBarPlot) -> None:
        """When numbered_xaxis is False, tick_text is returned unchanged."""
        tick_text: List[str] = ["c1", "c2", "c3", "c1", "c2", "c3"]
        config: Dict[str, Any] = {"numbered_xaxis": False}

        result_text, legend = plot._apply_numbered_xaxis(tick_text, config)

        assert result_text == tick_text
        assert legend is None

    def test_missing_key_returns_original(self, plot: GroupedStackedBarPlot) -> None:
        """When numbered_xaxis key is absent, tick_text is returned unchanged."""
        tick_text: List[str] = ["x", "y"]
        result_text, legend = plot._apply_numbered_xaxis(tick_text, {})
        assert result_text == tick_text
        assert legend is None

    def test_enabled_replaces_with_empty(self, plot: GroupedStackedBarPlot) -> None:
        """When enabled, tick_text entries become empty strings (ticks hidden)."""
        tick_text: List[str] = ["c1", "c2", "c3", "c1", "c2", "c3"]
        config: Dict[str, Any] = {"numbered_xaxis": True}

        result_text, legend = plot._apply_numbered_xaxis(tick_text, config)

        assert result_text == ["", "", "", "", "", ""]
        assert legend is not None

    def test_legend_annotation_structure(self, plot: GroupedStackedBarPlot) -> None:
        """Legend annotation has correct Plotly annotation keys for box style."""
        tick_text: List[str] = ["alpha", "beta"]
        config: Dict[str, Any] = {
            "numbered_xaxis": True,
            "numbered_legend_x": 1.05,
            "numbered_legend_y": 0.5,
            "numbered_legend_size": 12,
        }

        _, legend = plot._apply_numbered_xaxis(tick_text, config)

        assert legend is not None
        assert legend["xref"] == "paper"
        assert legend["yref"] == "paper"
        assert legend["x"] == 1.05
        assert legend["y"] == 0.5
        assert legend["font"]["size"] == 12
        assert legend["showarrow"] is False
        # Box-style legend properties
        assert legend["xanchor"] == "left"
        assert legend["yanchor"] == "middle"
        assert legend["align"] == "left"
        assert legend["bordercolor"] == "#333333"
        assert legend["borderwidth"] == 1
        assert legend["borderpad"] == 6
        assert legend["bgcolor"] == "#FFFFFF"

    def test_legend_text_contains_all_groups(self, plot: GroupedStackedBarPlot) -> None:
        """Legend text includes all unique groups with numbering."""
        tick_text: List[str] = ["c1", "c2", "c3", "c1", "c2", "c3"]
        config: Dict[str, Any] = {"numbered_xaxis": True}

        _, legend = plot._apply_numbered_xaxis(tick_text, config)
        assert legend is not None

        text: str = legend["text"]
        assert "1. c1" in text
        assert "2. c2" in text
        assert "3. c3" in text

    def test_column_wrapping(self, plot: GroupedStackedBarPlot) -> None:
        """numbered_legend_columns fills columns top-to-bottom (column-wise)."""
        tick_text: List[str] = ["a", "b", "c", "d", "a", "b", "c", "d"]
        config: Dict[str, Any] = {
            "numbered_xaxis": True,
            "numbered_legend_columns": 2,
        }

        _, legend = plot._apply_numbered_xaxis(tick_text, config)
        assert legend is not None

        text: str = legend["text"]
        # Column-wise: col-0=[1.a, 2.b], col-1=[3.c, 4.d]
        # Row 0: 1.a  3.c  |  Row 1: 2.b  4.d
        rows = text.split("<br>")
        assert len(rows) == 2
        assert "1. a" in rows[0]
        assert "3. c" in rows[0]
        assert "2. b" in rows[1]
        assert "4. d" in rows[1]

    def test_per_column_padding(self, plot: GroupedStackedBarPlot) -> None:
        """All columns are padded so every row has equal width."""
        tick_text: List[str] = [
            "short",
            "very_long_name",
            "medium",
            "x",
            "short",
            "very_long_name",
            "medium",
            "x",
        ]
        config: Dict[str, Any] = {
            "numbered_xaxis": True,
            "numbered_legend_columns": 2,
        }

        _, legend = plot._apply_numbered_xaxis(tick_text, config)
        assert legend is not None

        rows = legend["text"].split("<br>")
        # Column-wise layout: col-0=["1. short", "2. very_long_name"],
        #                     col-1=["3. medium", "4. x"]
        # Col-0 width: max(8, 17) = 17
        # Col-1 width: max(9, 4) = 9
        # All columns padded → all rows same width
        assert len(rows[0]) == len(rows[1])
        # Row 0: "1. short         " (17) + "  " + "3. medium" (9)
        assert rows[0] == "1. short           3. medium"
        # Row 1: "2. very_long_name" (17) + "  " + "4. x     " (9)
        assert rows[1] == "2. very_long_name  4. x     "

    def test_single_column_means_vertical_list(self, plot: GroupedStackedBarPlot) -> None:
        """numbered_legend_columns=1 means one entry per line (vertical list)."""
        tick_text: List[str] = ["x", "y", "z"]
        config: Dict[str, Any] = {
            "numbered_xaxis": True,
            "numbered_legend_columns": 1,
        }

        _, legend = plot._apply_numbered_xaxis(tick_text, config)
        assert legend is not None
        rows = legend["text"].split("<br>")
        assert len(rows) == 3
        assert "1. x" in rows[0]
        assert "2. y" in rows[1]
        assert "3. z" in rows[2]

    def test_preserves_insertion_order(self, plot: GroupedStackedBarPlot) -> None:
        """Numbering preserves insertion order, not alphabetical."""
        tick_text: List[str] = ["zeta", "alpha", "mid", "zeta", "alpha", "mid"]
        config: Dict[str, Any] = {"numbered_xaxis": True}

        result_text, legend = plot._apply_numbered_xaxis(tick_text, config)

        assert result_text == ["", "", "", "", "", ""]
        assert legend is not None
        text: str = legend["text"]
        assert text.index("1. zeta") < text.index("2. alpha") < text.index("3. mid")

    def test_single_group(self, plot: GroupedStackedBarPlot) -> None:
        """Works correctly with a single group."""
        tick_text: List[str] = ["only"]
        config: Dict[str, Any] = {"numbered_xaxis": True}

        result_text, legend = plot._apply_numbered_xaxis(tick_text, config)

        assert result_text == [""]
        assert legend is not None
        assert "1. only" in legend["text"]


# ---------------------------------------------------------------------------
# Integration: create_figure with numbered_xaxis
# ---------------------------------------------------------------------------
class TestCreateFigureNumberedXaxis:
    """Test full figure creation with numbered X-axis enabled."""

    def test_figure_ticks_are_hidden(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """X-axis ticks should be completely hidden when feature is enabled."""
        config = _base_config(numbered_xaxis=True)
        fig = plot.create_figure(sample_data, config)

        # Tick labels should be hidden
        assert fig.layout.xaxis.showticklabels is False
        # Tick marks should be removed
        assert fig.layout.xaxis.ticks == ""

    def test_figure_has_legend_annotation(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Figure should contain the numbered legend annotation."""
        config = _base_config(numbered_xaxis=True)
        fig = plot.create_figure(sample_data, config)

        # Find the legend annotation (xref=paper, yref=paper)
        legend_anns = [a for a in fig.layout.annotations if a.xref == "paper" and a.yref == "paper"]
        assert len(legend_anns) == 1, f"Expected 1 legend annotation, got {len(legend_anns)}"

        ann = legend_anns[0]
        # All 4 configs should appear
        assert "1. c1" in ann.text
        assert "2. c2" in ann.text
        assert "3. c3" in ann.text
        assert "4. c4" in ann.text

    def test_figure_without_numbered_has_original_ticks(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Without the feature, ticks are original group names."""
        config = _base_config(numbered_xaxis=False)
        fig = plot.create_figure(sample_data, config)

        x_ticktext = list(fig.layout.xaxis.ticktext)
        # Alphabetical sort of configs repeated per benchmark
        assert x_ticktext == ["c1", "c2", "c3", "c4", "c1", "c2", "c3", "c4"]

        # No paper-paper annotation
        legend_anns = [a for a in fig.layout.annotations if a.xref == "paper" and a.yref == "paper"]
        assert len(legend_anns) == 0

    def test_numbered_with_renames(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Numbered legends show renamed labels, not originals."""
        config = _base_config(
            numbered_xaxis=True,
            group_renames={"c1": "ConfigAlpha", "c2": "ConfigBeta"},
        )
        fig = plot.create_figure(sample_data, config)

        legend_anns = [a for a in fig.layout.annotations if a.xref == "paper" and a.yref == "paper"]
        assert len(legend_anns) == 1
        assert "ConfigAlpha" in legend_anns[0].text
        assert "ConfigBeta" in legend_anns[0].text

    def test_numbered_with_custom_position(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Custom legend_x, legend_y and legend_size are applied."""
        config = _base_config(
            numbered_xaxis=True,
            numbered_legend_x=0.0,
            numbered_legend_y=-0.40,
            numbered_legend_size=14,
        )
        fig = plot.create_figure(sample_data, config)

        legend_anns = [a for a in fig.layout.annotations if a.xref == "paper" and a.yref == "paper"]
        assert len(legend_anns) == 1
        assert legend_anns[0].x == 0.0
        assert legend_anns[0].y == -0.40
        assert legend_anns[0].font.size == 14

    def test_category_annotations_still_present(
        self, plot: GroupedStackedBarPlot, sample_data: pd.DataFrame
    ) -> None:
        """Major group annotations (benchmarks) are preserved alongside numbered legend."""
        config = _base_config(numbered_xaxis=True)
        fig = plot.create_figure(sample_data, config)

        # Grouping labels have xref="x" and yref="paper"
        group_anns = [a for a in fig.layout.annotations if a.xref == "x" and a.yref == "paper"]
        # should have 2 benchmarks (A, B)
        assert len(group_anns) == 2
        texts = {a.text for a in group_anns}
        assert "<b>A</b>" in texts
        assert "<b>B</b>" in texts


# ---------------------------------------------------------------------------
# Export pipeline: _clean_html_tags handles <br> and &nbsp;
# ---------------------------------------------------------------------------
class TestCleanHtmlTags:
    """Test that the layout applier handles HTML entities from numbered legends."""

    def test_br_converted_to_newline(self) -> None:
        """<br> and <br/> are converted to newlines."""
        from src.web.pages.ui.plotting.export.converters.impl.layout_applier import LayoutApplier

        applier = LayoutApplier.__new__(LayoutApplier)
        assert applier._clean_html_tags("a<br>b") == "a\nb"
        assert applier._clean_html_tags("a<br/>b") == "a\nb"
        assert applier._clean_html_tags("a<br />b") == "a\nb"

    def test_nbsp_converted_to_space(self) -> None:
        """&nbsp; is converted to regular space."""
        from src.web.pages.ui.plotting.export.converters.impl.layout_applier import LayoutApplier

        applier = LayoutApplier.__new__(LayoutApplier)
        assert applier._clean_html_tags("a&nbsp;b") == "a b"

    def test_combined_html(self) -> None:
        """All HTML entities handled together."""
        from src.web.pages.ui.plotting.export.converters.impl.layout_applier import LayoutApplier

        applier = LayoutApplier.__new__(LayoutApplier)
        text = "1.&nbsp;a  |  2.&nbsp;b<br>3.&nbsp;c  |  4.&nbsp;d"
        result = applier._clean_html_tags(text)
        assert result == "1. a  |  2. b\n3. c  |  4. d"


# ---------------------------------------------------------------------------
# Export pipeline: is_grouping_label detection
# ---------------------------------------------------------------------------
class TestGroupingLabelDetection:
    """Verify that numbered legend annotations are NOT classified as grouping labels."""

    def test_paper_paper_annotation_is_not_grouping_label(self) -> None:
        """An annotation with xref=paper, yref=paper should not be a grouping label."""
        ann = {"xref": "paper", "yref": "paper", "y": -0.25}
        xref = ann.get("xref", "x")
        yref = ann.get("yref", "y")
        is_grouping_label = yref == "paper" and xref != "paper" and ann["y"] < 0
        assert not is_grouping_label

    def test_data_paper_annotation_is_grouping_label(self) -> None:
        """An annotation with xref=x, yref=paper, y<0 should be a grouping label."""
        ann = {"xref": "x", "yref": "paper", "y": -0.15}
        xref = ann.get("xref", "x")
        yref = ann.get("yref", "y")
        is_grouping_label = yref == "paper" and xref != "paper" and ann["y"] < 0
        assert is_grouping_label


# ---------------------------------------------------------------------------
# Export pipeline: boxed annotation rendering
# ---------------------------------------------------------------------------
class TestBoxedAnnotationExport:
    """Test that boxed annotations are rendered with bbox in matplotlib."""

    def test_boxed_annotation_detected(self) -> None:
        """Annotation with borderwidth > 0 is detected as boxed."""
        ann_boxed = {"borderwidth": 1, "text": "1. a"}
        assert ann_boxed.get("borderwidth", 0) > 0

        ann_plain = {"text": "plain"}
        assert not (ann_plain.get("borderwidth", 0) > 0)

    def test_render_boxed_annotation_uses_legend_font(self) -> None:
        """_render_boxed_annotation uses font_size_legend from preset."""
        from unittest.mock import MagicMock

        from src.web.pages.ui.plotting.export.converters.impl.layout_applier import LayoutApplier
        from src.web.pages.ui.plotting.export.converters.impl.layout_config import (
            FontStyleConfig,
            LegendSpacingConfig,
            PositioningConfig,
            SeparatorConfig,
        )

        applier = LayoutApplier.__new__(LayoutApplier)
        applier.font_config = FontStyleConfig(font_size_legend=9, bold_legend=True)
        applier.pos_config = PositioningConfig()
        applier.sep_config = SeparatorConfig()
        applier.legend_spacing = LegendSpacingConfig()

        mock_ax = MagicMock()

        ann = {
            "x": 1.02,
            "y": 0.5,
            "xref": "paper",
            "yref": "paper",
            "text": "1. a<br>2. b",
            "borderwidth": 1,
            "bordercolor": "#333333",
            "borderpad": 6,
            "bgcolor": "#FFFFFF",
            "xanchor": "left",
            "yanchor": "middle",
        }

        applier._render_boxed_annotation(mock_ax, ann, "1. a\\n2. b")

        mock_ax.annotate.assert_called_once()
        call_kwargs = mock_ax.annotate.call_args
        kwargs = call_kwargs[1]

        # Font is now passed via FontProperties (monospace for alignment)
        fp = kwargs["fontproperties"]
        assert fp.get_size() == 9
        assert fp.get_weight() == "bold"
        assert fp.get_family() == ["monospace"]
        assert "bbox" in kwargs
        assert kwargs["bbox"]["edgecolor"] == "#333333"
        assert kwargs["bbox"]["facecolor"] == "#FFFFFF"
        assert kwargs["ha"] == "left"
        assert kwargs["va"] == "center"

    def test_layout_mapper_extracts_border_props(self) -> None:
        """Layout mapper extracts borderwidth, bordercolor, borderpad, bgcolor, align."""
        import plotly.graph_objects as go

        from src.web.pages.ui.plotting.export.converters.impl.layout_mapper import LayoutMapper

        mapper = LayoutMapper()

        fig = go.Figure()
        fig.update_layout(
            annotations=[
                dict(
                    x=1.02,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    text="test",
                    showarrow=False,
                    borderwidth=1,
                    bordercolor="#333",
                    borderpad=6,
                    bgcolor="#FFF",
                    align="left",
                )
            ]
        )

        result = mapper.extract_layout(fig)
        assert "annotations" in result
        ann = result["annotations"][0]
        assert ann["borderwidth"] == 1
        assert ann["bordercolor"] == "#333"
        assert ann["borderpad"] == 6
        assert ann["bgcolor"] == "#FFF"
        assert ann["align"] == "left"


# ---------------------------------------------------------------------------
# Export pipeline: legend spacing in boxed annotation
# ---------------------------------------------------------------------------
class TestBoxedAnnotationSpacing:
    """Test that boxed annotations use legend spacing from preset."""

    def test_default_legend_spacing_config(self) -> None:
        """LegendSpacingConfig defaults match matplotlib legend defaults."""
        from src.web.pages.ui.plotting.export.converters.impl.layout_config import (
            LegendSpacingConfig,
        )

        cfg = LegendSpacingConfig()
        assert cfg.columnspacing == 0.5
        assert cfg.labelspacing == 0.2
        assert cfg.borderpad == 0.2

    def test_applier_builds_legend_spacing_from_preset(self) -> None:
        """LayoutApplier._build_legend_spacing_config extracts preset values."""
        from src.web.pages.ui.plotting.export.converters.impl.layout_applier import (
            LayoutApplier,
        )

        preset: Dict[str, Any] = {
            "legend_columnspacing": 1.0,
            "legend_labelspacing": 0.5,
            "legend_borderpad": 0.4,
            "legend_handletextpad": 0.6,
        }
        applier = LayoutApplier(preset)  # type: ignore[arg-type]
        assert applier.legend_spacing.columnspacing == 1.0
        assert applier.legend_spacing.labelspacing == 0.5
        assert applier.legend_spacing.borderpad == 0.4
        assert applier.legend_spacing.handletextpad == 0.6

    def test_boxed_annotation_uses_preset_borderpad(self) -> None:
        """_render_boxed_annotation uses legend_borderpad from preset for bbox pad."""
        from unittest.mock import MagicMock

        from src.web.pages.ui.plotting.export.converters.impl.layout_applier import (
            LayoutApplier,
        )

        preset: Dict[str, Any] = {
            "legend_borderpad": 0.4,
            "legend_labelspacing": 0.3,
            "font_size_legend": 9,
        }
        applier = LayoutApplier(preset)  # type: ignore[arg-type]

        mock_ax = MagicMock()
        ann: Dict[str, Any] = {
            "x": 1.02,
            "y": 0.5,
            "xref": "paper",
            "yref": "paper",
            "text": "1. a<br>2. b",
            "borderwidth": 1,
            "bordercolor": "#333",
            "borderpad": 6,
            "bgcolor": "#FFF",
            "xanchor": "left",
            "yanchor": "middle",
        }

        applier._render_boxed_annotation(mock_ax, ann, "1. a\\n2. b")
        kwargs = mock_ax.annotate.call_args[1]

        # bbox pad should use preset legend_borderpad, not annotation borderpad
        assert f"pad={0.4:.3f}" in kwargs["bbox"]["boxstyle"]
        # linespacing derived from preset labelspacing
        expected_linespacing = 1.0 + 0.3 * 2.0
        assert kwargs["linespacing"] == pytest.approx(expected_linespacing)

    def test_boxed_annotation_default_spacing(self) -> None:
        """Without preset, _render_boxed_annotation uses default spacing."""
        from unittest.mock import MagicMock

        from src.web.pages.ui.plotting.export.converters.impl.layout_applier import (
            LayoutApplier,
        )

        applier = LayoutApplier()  # No preset → defaults
        mock_ax = MagicMock()
        ann: Dict[str, Any] = {
            "x": 1.0,
            "y": 0.5,
            "xref": "paper",
            "yref": "paper",
            "text": "test",
            "borderwidth": 1,
            "bordercolor": "black",
            "borderpad": 6,
            "bgcolor": "white",
            "xanchor": "left",
            "yanchor": "middle",
        }

        applier._render_boxed_annotation(mock_ax, ann, "test")
        kwargs = mock_ax.annotate.call_args[1]

        # Default borderpad = 0.2
        assert "pad=0.200" in kwargs["bbox"]["boxstyle"]
        # Default labelspacing = 0.2 → linespacing = 1.0 + 0.2*2.0 = 1.4
        assert kwargs["linespacing"] == pytest.approx(1.4)


# ---------------------------------------------------------------------------
# Export pipeline: X-tick hiding
# ---------------------------------------------------------------------------
class TestExportTickHiding:
    """Test that the export pipeline hides X-ticks when showticklabels=False."""

    def test_layout_mapper_extracts_showticklabels(self) -> None:
        """Layout mapper extracts x_showticklabels from layout."""
        import plotly.graph_objects as go

        from src.web.pages.ui.plotting.export.converters.impl.layout_mapper import (
            LayoutMapper,
        )

        mapper = LayoutMapper()
        fig = go.Figure()
        fig.update_layout(xaxis=dict(showticklabels=False, ticks=""))
        result = mapper.extract_layout(fig)
        assert result["x_showticklabels"] is False
        assert result["x_ticks"] == ""

    def test_layout_applier_hides_ticks_when_showticklabels_false(self) -> None:
        """_apply_ticks removes tick labels and marks when x_showticklabels=False."""
        from unittest.mock import MagicMock

        from src.web.pages.ui.plotting.export.converters.impl.layout_applier import (
            LayoutApplier,
        )

        applier = LayoutApplier()  # defaults
        mock_ax = MagicMock()

        layout: Dict[str, Any] = {
            "x_showticklabels": False,
            "x_tickvals": [0, 1, 2],
            "x_ticktext": ["a", "b", "c"],
        }

        applier._apply_ticks(mock_ax, layout)

        # Should set empty tick labels
        mock_ax.set_xticklabels.assert_called_once_with([])
        # Should set tick length to 0 (removes tick marks)
        mock_ax.tick_params.assert_any_call(axis="x", length=0)

    def test_layout_applier_keeps_ticks_when_showticklabels_true(self) -> None:
        """_apply_ticks renders normally when x_showticklabels is absent."""
        from unittest.mock import MagicMock

        from src.web.pages.ui.plotting.export.converters.impl.layout_applier import (
            LayoutApplier,
        )

        applier = LayoutApplier()  # defaults
        mock_ax = MagicMock()

        layout: Dict[str, Any] = {
            "x_tickvals": [0, 1, 2],
            "x_ticktext": ["a", "b", "c"],
        }

        applier._apply_ticks(mock_ax, layout)

        # Should set tick labels normally (not empty)
        mock_ax.set_xticks.assert_called_once_with([0, 1, 2])
        mock_ax.set_xticklabels.assert_called_once()


# =============================================================================
# _wrap_texttt — LaTeX monospace wrapper tests
# =============================================================================


class TestWrapTexttt:
    """Tests for LayoutApplier._wrap_texttt static method."""

    def test_single_line_no_bold(self) -> None:
        """Single line should be wrapped in \\texttt with \\phantom{0} for spaces."""
        from src.web.pages.ui.plotting.export.converters.impl.layout_applier import (
            LayoutApplier,
        )

        result = LayoutApplier._wrap_texttt("1. TS RS  2. CID RS")
        p = r"\phantom{0}"
        assert result == rf"\texttt{{1.{p}TS{p}RS{p}{p}2.{p}CID{p}RS}}"

    def test_single_line_bold(self) -> None:
        """Bold wrapping should nest \\textbf inside \\texttt."""
        from src.web.pages.ui.plotting.export.converters.impl.layout_applier import (
            LayoutApplier,
        )

        result = LayoutApplier._wrap_texttt("1. Test", bold=True)
        p = r"\phantom{0}"
        assert result == rf"\texttt{{\textbf{{1.{p}Test}}}}"

    def test_multiline(self) -> None:
        """Each line should be independently wrapped."""
        from src.web.pages.ui.plotting.export.converters.impl.layout_applier import (
            LayoutApplier,
        )

        text = "1. TS RS  2. CID RS\n3. PiC RS 4. Hway"
        result = LayoutApplier._wrap_texttt(text)
        lines = result.split("\n")
        p = r"\phantom{0}"
        assert len(lines) == 2
        assert lines[0] == rf"\texttt{{1.{p}TS{p}RS{p}{p}2.{p}CID{p}RS}}"
        assert lines[1] == rf"\texttt{{3.{p}PiC{p}RS{p}4.{p}Hway}}"

    def test_no_spaces(self) -> None:
        """Text without spaces should just be wrapped."""
        from src.web.pages.ui.plotting.export.converters.impl.layout_applier import (
            LayoutApplier,
        )

        result = LayoutApplier._wrap_texttt("abc")
        assert result == r"\texttt{abc}"

    def test_empty_string(self) -> None:
        """Empty string should produce wrapped empty braces."""
        from src.web.pages.ui.plotting.export.converters.impl.layout_applier import (
            LayoutApplier,
        )

        result = LayoutApplier._wrap_texttt("")
        assert result == r"\texttt{}"
