"""Unit tests for the typed FigureSpec -> flat-config mapping."""

from __future__ import annotations

import pytest

from ring5.figure_spec import FigureSpec, LegendOpts, ReferenceLineOpts

pytestmark = pytest.mark.public_api


class TestFigureSpecToConfig:
    """FigureSpec.to_config emits the flat keys the renderer expects."""

    def test_data_mapping_keys(self) -> None:
        cfg = FigureSpec(x="bench", group="policy", y_columns=["A", "B", "C"]).to_config()
        assert cfg["x"] == "bench"
        assert cfg["group"] == "policy"
        assert cfg["y_columns"] == ["A", "B", "C"]
        assert cfg["y"] == "A"  # simple-bar path reads config["y"]

    def test_palette_accepts_name_or_list(self) -> None:
        assert FigureSpec(palette="Set2").to_config()["color_palette"] == "Set2"
        hexes = ["#66c2a5", "#fc8d62"]
        assert FigureSpec(palette=hexes).to_config()["color_palette"] == hexes

    def test_reference_line(self) -> None:
        cfg = FigureSpec(reference_line=ReferenceLineOpts(y=1.0, color="red")).to_config()
        assert cfg["reference_line_enabled"] is True
        assert cfg["reference_line_y"] == 1.0
        assert cfg["reference_line_color"] == "red"

    def test_no_reference_line_by_default(self) -> None:
        assert "reference_line_enabled" not in FigureSpec().to_config()

    def test_margins_unpacked(self) -> None:
        cfg = FigureSpec(margins=(10, 20, 30, 40)).to_config()
        assert (cfg["margin_t"], cfg["margin_b"], cfg["margin_l"], cfg["margin_r"]) == (
            10,
            20,
            30,
            40,
        )

    def test_y_range_and_dtick(self) -> None:
        cfg = FigureSpec(y_range=(0.0, 1.4), y_dtick=0.2).to_config()
        assert cfg["range_y"] == [0.0, 1.4]
        assert cfg["yaxis_dtick"] == 0.2

    def test_legend_anchor_key_asymmetry(self) -> None:
        """Primary legend uses anchor_x/anchor_y; the number box uses xanchor/yanchor."""
        spec = FigureSpec(
            legend=LegendOpts(position=(0.6, 0.99), anchor=("left", "top"), ncols=3, item_width=6),
            number_legend=LegendOpts(position=(0.6, 0.8), anchor=("left", "top"), ncols=2),
        )
        cfg = spec.to_config()
        # primary
        assert cfg["legend_x"] == 0.6
        assert cfg["legend_anchor_x"] == "left"
        assert cfg["legend_anchor_y"] == "top"
        assert cfg["legend_ncols"] == 3
        assert cfg["legend_itemwidth"] == 6
        # numbered box
        assert cfg["legend2_x"] == 0.6
        assert cfg["legend2_xanchor"] == "left"
        assert cfg["legend2_yanchor"] == "top"
        assert cfg["legend2_ncols"] == 2
        # the asymmetric keys must NOT cross over
        assert "legend_xanchor" not in cfg
        assert "legend2_anchor_x" not in cfg

    def test_unset_legend_fields_omitted(self) -> None:
        cfg = FigureSpec().to_config()
        assert "legend_x" not in cfg  # default LegendOpts has no position
        assert "legend_ncols" not in cfg

    def test_extra_overrides(self) -> None:
        cfg = FigureSpec(title="orig", extra={"title": "override", "custom_key": 7}).to_config()
        assert cfg["title"] == "override"
        assert cfg["custom_key"] == 7


class TestFigureSpecValidation:
    """__post_init__ light validation."""

    def test_bad_margins(self) -> None:
        with pytest.raises(ValueError, match="margins"):
            FigureSpec(margins=(1, 2, 3))  # type: ignore[arg-type]

    def test_bad_y_range(self) -> None:
        with pytest.raises(ValueError, match="y_range"):
            FigureSpec(y_range=(1.0, 2.0, 3.0))  # type: ignore[arg-type]

    def test_bad_numbered_mode(self) -> None:
        with pytest.raises(ValueError, match="numbered_xaxis_modes"):
            FigureSpec(numbered_xaxis_modes=["Bogus"])

    def test_valid_numbered_modes(self) -> None:
        cfg = FigureSpec(numbered_xaxis_modes=["Numbers", "Number legend"]).to_config()
        assert cfg["numbered_xaxis_modes"] == ["Numbers", "Number legend"]
