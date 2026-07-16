"""Unit tests for the fluent FigureSpecBuilder."""

from __future__ import annotations

import pytest

from ring5.figure_spec import (
    FigureSpec,
    FigureSpecBuilder,
    LegendOpts,
    ReferenceLineOpts,
)

pytestmark = pytest.mark.public_api


class TestFigureSpecBuilder:
    def test_chaining_returns_self(self) -> None:
        b = FigureSpecBuilder()
        assert b.data(x="a") is b
        assert b.size(width=10) is b
        assert b.palette("Set2") is b

    def test_builds_equivalent_to_direct_construction(self) -> None:
        built = (
            FigureSpecBuilder()
            .data(x="benchmark", group="policy", y_columns=["A", "B"])
            .size(width=820, height=372, margins=(28, 50, 58, 14))
            .palette("Set2")
            .axes(ylabel="Cycles", y_range=(0.0, 1.4), y_dtick=0.2)
            .grid(dash="dash", alpha=0.3)
            .tick_marks(x=False)
            .separators(show=True, isolate_last=True)
            .category_labels(rotation=30, alternate=False)
            .numbered_xaxis("Number legend")
            .legend(position=(0.61, 1.0), anchor=("left", "top"), ncols=3, item_width=5)
            .number_legend(position=(0.62, 0.84), anchor=("left", "top"), ncols=2)
            .reference_line(y=1.0)
            .build()
        )
        direct = FigureSpec(
            x="benchmark",
            group="policy",
            y_columns=["A", "B"],
            width=820,
            height=372,
            margins=(28, 50, 58, 14),
            palette="Set2",
            ylabel="Cycles",
            y_range=(0.0, 1.4),
            y_dtick=0.2,
            y_grid_dash="dash",
            y_grid_alpha=0.3,
            show_x_tick_marks=False,
            show_separators=True,
            isolate_last_group=True,
            major_label_rotation=30,
            group_label_alternate=False,
            numbered_xaxis_modes=["Number legend"],
            legend=LegendOpts(position=(0.61, 1.0), anchor=("left", "top"), ncols=3, item_width=5),
            number_legend=LegendOpts(position=(0.62, 0.84), anchor=("left", "top"), ncols=2),
            reference_line=ReferenceLineOpts(y=1.0),
        )
        # Same emitted flat config => same figure.
        assert built.to_config() == direct.to_config()

    def test_unset_groups_keep_defaults(self) -> None:
        spec = FigureSpecBuilder().data(x="b", y_columns=["v"]).build()
        assert spec.font_family == "serif"  # untouched default
        assert spec.barmode == "group"
        assert spec.legend == LegendOpts()  # default, nothing set

    def test_numbered_xaxis_multiple_modes(self) -> None:
        spec = FigureSpecBuilder().numbered_xaxis("Numbers", "Number legend").build()
        assert spec.numbered_xaxis_modes == ["Numbers", "Number legend"]

    def test_extra_accumulates(self) -> None:
        spec = FigureSpecBuilder().extra(foo=1).extra(bar=2).build()
        assert spec.extra == {"foo": 1, "bar": 2}

    def test_build_validates(self) -> None:
        with pytest.raises(ValueError, match="numbered_xaxis_modes"):
            FigureSpecBuilder().numbered_xaxis("Bogus").build()

    def test_partial_setters_only_apply_passed_args(self) -> None:
        # passing only alpha must not clobber the default dash/color
        spec = FigureSpecBuilder().grid(alpha=0.5).build()
        assert spec.y_grid_alpha == 0.5
        assert spec.y_grid_dash == "dash"  # FigureSpec default preserved
        assert spec.show_y_grid is True
