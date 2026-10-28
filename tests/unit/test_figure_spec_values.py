"""Direct immutable figure specifications retain publication settings."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ring5.figure_spec import FigureSpec, LegendOpts, ReferenceLineOpts

pytestmark = pytest.mark.public_api


class TestFigureSpecValues:
    # [test->req~ring5.api.figure-spec~1]
    def test_constructor_is_immutable(self) -> None:
        spec = FigureSpec(x="a", width=10, palette="Set2")
        with pytest.raises(FrozenInstanceError):
            spec.width = 20

    def test_publication_settings_emit_their_canonical_configuration(self) -> None:
        spec = FigureSpec(
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
        config = spec.to_config()
        assert config["x"] == "benchmark"
        assert config["y_columns"] == ["A", "B"]
        assert config["width"] == 820 and config["height"] == 372
        assert config["margin_t"] == 28 and config["margin_l"] == 58
        assert config["range_y"] == [0.0, 1.4]
        assert config["legend_ncols"] == 3 and config["legend2_ncols"] == 2
        assert config["reference_line_y"] == 1.0
        assert config["major_label_rotation"] == 30
        assert config["numbered_xaxis_modes"] == ["Number legend"]

    def test_unset_groups_keep_defaults(self) -> None:
        spec = FigureSpec(x="b", y_columns=["v"])
        assert spec.font_family == "serif"
        assert spec.barmode == "group"
        assert spec.legend == LegendOpts()

    def test_numbered_xaxis_multiple_modes(self) -> None:
        spec = FigureSpec(numbered_xaxis_modes=["Numbers", "Number legend"])
        assert tuple(spec.numbered_xaxis_modes) == ("Numbers", "Number legend")

    def test_extra_has_one_owned_mapping(self) -> None:
        spec = FigureSpec(extra={"foo": 1, "bar": 2})
        assert spec.extra == {"foo": 1, "bar": 2}

    def test_constructor_validates(self) -> None:
        with pytest.raises(ValueError, match="numbered_xaxis_modes"):
            FigureSpec(numbered_xaxis_modes=["Bogus"])

    def test_partial_configuration_preserves_defaults(self) -> None:
        spec = FigureSpec(y_grid_alpha=0.5)
        assert spec.y_grid_alpha == 0.5
        assert spec.y_grid_dash == "dash"
        assert spec.show_y_grid is True
