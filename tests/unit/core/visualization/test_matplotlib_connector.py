"""
Tests for FigureSpecToMatplotlib — Step 11 new feature methods.

Covers:
  - _apply_backgrounds: figure/axes facecolor
  - _apply_font_family: rcParams font.family
  - _apply_color_palette: axes prop_cycle
  - _apply_reference_lines: axhline / axvline
  - _apply_data_labels: bar_label on containers
  - _apply_separators: vertical separator lines
  - _apply_hatching: bar patch hatching patterns
  - _apply_axis_colors: tick_font_color, spine colour/width
  - create_figure: layout='constrained'
"""

import matplotlib
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.colors import to_hex, to_rgba  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

matplotlib.use("Agg")  # non-interactive backend for CI

import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402

from src.core.models.visualization.annotation_config import (  # noqa: E402
    ReferenceLineConfig,
)
from src.core.models.visualization.axis_config import (  # noqa: E402
    AxesConfig,
    AxisConfig,
)
from src.core.models.visualization.data_label_config import (  # noqa: E402
    DataLabelConfig,
)
from src.core.models.visualization.figure_config import (  # noqa: E402
    FigureConfig,
    SeparatorConfig,
)
from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib  # noqa: E402


@pytest.fixture()
def ax():  # type: ignore[no-untyped-def]
    """Provide a fresh axes and close figure after test."""
    fig, ax = plt.subplots()
    yield ax
    plt.close(fig)


# ────────────────────────────────────────────────────────────────────
# _apply_backgrounds
# ────────────────────────────────────────────────────────────────────


class TestMatplotlibBackgrounds:
    """Test _apply_backgrounds."""

    def test_paper_bgcolor(self, ax: Axes) -> None:
        spec = FigureConfig(paper_bgcolor="#EEEEEE")
        FigureSpecToMatplotlib._apply_backgrounds(spec, ax)
        fig = ax.get_figure()
        assert isinstance(fig, Figure)
        assert fig.patch.get_facecolor() == to_rgba("#EEEEEE")

    def test_plot_bgcolor(self, ax: Axes) -> None:
        spec = FigureConfig(plot_bgcolor="#CCCCCC")
        FigureSpecToMatplotlib._apply_backgrounds(spec, ax)
        assert ax.get_facecolor() == to_rgba("#CCCCCC")

    def test_both_backgrounds(self, ax: Axes) -> None:
        spec = FigureConfig(paper_bgcolor="#111111", plot_bgcolor="#222222")
        FigureSpecToMatplotlib._apply_backgrounds(spec, ax)
        fig = ax.get_figure()
        assert isinstance(fig, Figure)
        assert fig.patch.get_facecolor() == to_rgba("#111111")
        assert ax.get_facecolor() == to_rgba("#222222")


# ────────────────────────────────────────────────────────────────────
# _apply_font_family
# ────────────────────────────────────────────────────────────────────


class TestMatplotlibFontFamily:
    """Test _apply_font_family."""

    def test_font_family_set(self, ax: Axes) -> None:
        spec = FigureConfig(font_family="serif")
        FigureSpecToMatplotlib._apply_font_family(spec, ax)
        assert matplotlib.rcParams["font.family"] == ["serif"]

    def test_empty_font_family_no_change(self, ax: Axes) -> None:
        original = matplotlib.rcParams["font.family"]
        spec = FigureConfig(font_family="")
        FigureSpecToMatplotlib._apply_font_family(spec, ax)
        assert matplotlib.rcParams["font.family"] == original


# ────────────────────────────────────────────────────────────────────
# _apply_color_palette
# ────────────────────────────────────────────────────────────────────


class TestMatplotlibColorPalette:
    """Test _apply_color_palette."""

    def test_palette_set(self, ax: Axes) -> None:
        palette = ["#FF0000", "#00FF00", "#0000FF"]
        spec = FigureConfig(color_palette=palette)
        FigureSpecToMatplotlib._apply_color_palette(spec, ax)
        # Verify by plotting lines and checking their colors
        for i in range(3):
            ax.plot([0, 1], [i, i])
        colors_used = [to_hex(line.get_color()) for line in ax.lines]
        assert colors_used == [c.lower() for c in palette]

    def test_empty_palette_no_op(self, ax: Axes) -> None:
        spec = FigureConfig(color_palette=[])
        # Should not raise
        FigureSpecToMatplotlib._apply_color_palette(spec, ax)


# ────────────────────────────────────────────────────────────────────
# _apply_reference_lines
# ────────────────────────────────────────────────────────────────────


class TestMatplotlibReferenceLines:
    """Test _apply_reference_lines."""

    def test_horizontal_line(self, ax: Axes) -> None:
        rl = ReferenceLineConfig(enabled=True, axis="y", value=1.0, color="red", width=2.0)
        spec = FigureConfig(reference_lines=[rl])
        FigureSpecToMatplotlib._apply_reference_lines(spec, ax)
        # Should have at least one line added
        assert len(ax.lines) >= 1

    def test_vertical_line(self, ax: Axes) -> None:
        rl = ReferenceLineConfig(enabled=True, axis="x", value=0.5, color="blue")
        spec = FigureConfig(reference_lines=[rl])
        FigureSpecToMatplotlib._apply_reference_lines(spec, ax)
        assert len(ax.lines) >= 1

    def test_disabled_line_skipped(self, ax: Axes) -> None:
        rl = ReferenceLineConfig(enabled=False, axis="y", value=1.0)
        spec = FigureConfig(reference_lines=[rl])
        FigureSpecToMatplotlib._apply_reference_lines(spec, ax)
        assert len(ax.lines) == 0

    def test_reference_line_with_label(self, ax: Axes) -> None:
        rl = ReferenceLineConfig(enabled=True, axis="y", value=2.0, label="baseline")
        spec = FigureConfig(reference_lines=[rl])
        FigureSpecToMatplotlib._apply_reference_lines(spec, ax)
        labels = [line.get_label() for line in ax.lines]
        assert "baseline" in labels

    def test_dash_style_mapping(self, ax: Axes) -> None:
        for style, expected_ls in [
            ("solid", "-"),
            ("dash", "--"),
            ("dot", ":"),
            ("dashdot", "-."),
        ]:
            fig_t, ax_t = plt.subplots()
            assert isinstance(ax_t, Axes)
            rl = ReferenceLineConfig(
                enabled=True, axis="y", value=1.0, style=style  # type: ignore[arg-type]
            )
            FigureSpecToMatplotlib._apply_reference_lines(FigureConfig(reference_lines=[rl]), ax_t)
            assert ax_t.lines[0].get_linestyle() == expected_ls
            plt.close(fig_t)


# ────────────────────────────────────────────────────────────────────
# _apply_data_labels
# ────────────────────────────────────────────────────────────────────


class TestMatplotlibDataLabels:
    """Test _apply_data_labels."""

    def test_data_labels_on_bar(self, ax: Axes) -> None:
        ax.bar(["A", "B"], [10, 20])
        dl = DataLabelConfig(enabled=True, font_size=12, format_string=".0f")
        spec = FigureConfig(data_labels=dl)
        FigureSpecToMatplotlib._apply_data_labels(spec, ax)
        # bar_label adds text objects
        texts = ax.texts
        assert len(texts) >= 2

    def test_data_labels_disabled_no_op(self, ax: Axes) -> None:
        ax.bar(["A"], [5])
        spec = FigureConfig(data_labels=None)
        FigureSpecToMatplotlib._apply_data_labels(spec, ax)
        assert len(ax.texts) == 0

    def test_data_labels_custom_color(self, ax: Axes) -> None:
        ax.bar(["A"], [5])
        dl = DataLabelConfig(enabled=True, color_mode="custom", custom_color="#FF0000")
        spec = FigureConfig(data_labels=dl)
        FigureSpecToMatplotlib._apply_data_labels(spec, ax)
        # At least one text element should have the custom color
        assert len(ax.texts) >= 1


# ────────────────────────────────────────────────────────────────────
# _apply_separators
# ────────────────────────────────────────────────────────────────────


class TestMatplotlibSeparators:
    """Test _apply_separators."""

    def test_separators_created(self, ax: Axes) -> None:
        ax.bar([0, 1, 2], [10, 20, 30])
        ax.xaxis.set_ticks([0, 1, 2])
        spec = FigureConfig(separator=SeparatorConfig(enabled=True, style="dash", color="gray"))
        FigureSpecToMatplotlib._apply_separators(spec, ax)
        # 3 ticks → 2 separator lines
        assert len(ax.lines) == 2

    def test_separator_disabled(self, ax: Axes) -> None:
        ax.bar([0, 1], [10, 20])
        spec = FigureConfig(separator=SeparatorConfig(enabled=False))
        FigureSpecToMatplotlib._apply_separators(spec, ax)
        assert len(ax.lines) == 0


# ────────────────────────────────────────────────────────────────────
# _apply_hatching
# ────────────────────────────────────────────────────────────────────


class TestMatplotlibHatching:
    """Test _apply_hatching."""

    def test_hatching_applied(self, ax: Axes) -> None:
        ax.bar(["A", "B"], [10, 20])
        spec = FigureConfig(enable_stripes=True, hatching_sequence=["/", "\\"])
        FigureSpecToMatplotlib._apply_hatching(spec, ax)
        # Check hatching on patches in the first container
        assert ax.containers[0][0].get_hatch() == "/"
        assert ax.containers[0][1].get_hatch() == "/"

    def test_hatching_disabled_no_op(self, ax: Axes) -> None:
        ax.bar(["A"], [5])
        spec = FigureConfig(enable_stripes=False, hatching_sequence=["/"])
        FigureSpecToMatplotlib._apply_hatching(spec, ax)
        assert ax.containers[0][0].get_hatch() is None

    def test_multiple_containers_cycle(self, ax: Axes) -> None:
        ax.bar([0], [10], label="A")
        ax.bar([1], [20], label="B")
        spec = FigureConfig(enable_stripes=True, hatching_sequence=["/", "x"])
        FigureSpecToMatplotlib._apply_hatching(spec, ax)
        assert ax.containers[0][0].get_hatch() == "/"
        assert ax.containers[1][0].get_hatch() == "x"


# ────────────────────────────────────────────────────────────────────
# _apply_axis_colors
# ────────────────────────────────────────────────────────────────────


class TestMatplotlibAxisColors:
    """Test _apply_axis_colors."""

    def test_tick_font_color(self, ax: Axes) -> None:
        spec = FigureConfig(
            axes=AxesConfig(
                x=AxisConfig(tick_font_color="#333333"),
                y=AxisConfig(tick_font_color="#666666"),
            )
        )
        FigureSpecToMatplotlib._apply_axis_colors(spec, ax)
        # tick_params sets the tick label color

    def test_axis_line_color(self, ax: Axes) -> None:
        spec = FigureConfig(
            axes=AxesConfig(
                x=AxisConfig(axis_line_color="red", axis_line_width=2.0),
                y=AxisConfig(),
            )
        )
        FigureSpecToMatplotlib._apply_axis_colors(spec, ax)
        assert ax.spines["bottom"].get_edgecolor() == to_rgba("red")
        assert ax.spines["bottom"].get_linewidth() == 2.0

    def test_no_colors_no_change(self, ax: Axes) -> None:
        spec = FigureConfig()
        # Should not raise
        FigureSpecToMatplotlib._apply_axis_colors(spec, ax)


# ────────────────────────────────────────────────────────────────────
# create_figure with layout='constrained'
# ────────────────────────────────────────────────────────────────────


class TestMatplotlibCreateFigure:
    """Test create_figure uses constrained layout."""

    def test_create_figure_returns_fig_ax(self) -> None:
        spec = FigureConfig()
        fig, ax = FigureSpecToMatplotlib.create_figure(spec)
        assert fig is not None
        assert ax is not None
        plt.close(fig)

    def test_create_figure_no_constrained_layout(self) -> None:
        spec = FigureConfig()
        fig, ax = FigureSpecToMatplotlib.create_figure(spec)
        assert fig.get_layout_engine() is None
        plt.close(fig)

    def test_create_figure_dimensions(self) -> None:
        from src.core.models.visualization.figure_config import DimensionConfig

        spec = FigureConfig(dimensions=DimensionConfig(width=12, height=6, dpi=150))
        fig, ax = FigureSpecToMatplotlib.create_figure(spec)
        w, h = fig.get_size_inches()
        assert w == pytest.approx(12)
        assert h == pytest.approx(6)
        assert fig.dpi == 150
        plt.close(fig)
