"""Tests for the supported table, geometry, and figure-decoration helpers."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pytest

import ring5
import ring5.shapers as shapers

pytestmark = pytest.mark.public_api


class TestTable:
    """The public table wrapper keeps common scripts pandas-independent."""

    def test_construction_introspection_and_copy_isolation(self) -> None:
        source = pd.DataFrame({"group": ["b", "a"], "value": [2, 1]})
        table = ring5.Table(source)
        source.loc[0, "value"] = 99

        assert len(table) == 2
        assert table.columns() == ["group", "value"]
        assert table.rows() == [{"group": "b", "value": 2}, {"group": "a", "value": 1}]
        assert not table.is_empty
        assert ring5.Table.from_rows([]).is_empty

        exposed = table.frame
        exposed.loc[0, "value"] = 100
        assert table.rows()[0]["value"] == 2

    def test_transforms_and_value_maps(self) -> None:
        table = ring5.Table.from_rows(
            [
                {"group": "b", "item": "x", "left": 2.0, "right": 3.0},
                {"group": "a", "item": "y", "left": 4.0, "right": 5.0},
            ]
        )

        filtered = table.filter_eq("group", "a")
        sorted_table = table.sort(["group"])
        derived = table.with_scalar_op("double", "left", "*", 2.0)
        applied = table.apply(lambda frame: frame.assign(total=frame["left"] + frame["right"]))
        combined = filtered.concat(filtered)

        assert filtered.rows()[0]["item"] == "y"
        assert sorted_table.rows()[0]["group"] == "a"
        assert derived.rows()[0]["double"] == pytest.approx(4.0)
        assert applied.rows()[1]["total"] == pytest.approx(9.0)
        assert len(combined) == 2
        assert table.value_map(["group", "item"], "left") == {
            ("b", "x"): 2.0,
            ("a", "y"): 4.0,
        }
        assert table.sum_map(["group"], ["left", "right"]) == {
            ("b",): 5.0,
            ("a",): 9.0,
        }

    def test_csv_round_trip(self, tmp_path: Path) -> None:
        table = ring5.Table.from_rows([{"name": "a", "value": 1.5}])
        destination = tmp_path / "table.csv"

        assert table.to_csv(str(destination)) == str(destination)
        assert ring5.read_table(str(destination)).rows() == [{"name": "a", "value": 1.5}]
        assert ring5.Table.from_csv(str(destination)).columns() == ["name", "value"]


def test_grouped_bar_coordinates_public_wrapper() -> None:
    geometry = ring5.grouped_bar_coordinates(
        ["a", "b"], ["base", "opt"], {"bargroupgap": 0.5, "bargap": 0.2}
    )

    assert set(geometry["coord_map"]) == {
        ("a", "base"),
        ("a", "opt"),
        ("b", "base"),
        ("b", "opt"),
    }
    assert geometry["bar_width"] == pytest.approx(0.8)


def test_shapers_are_available_from_the_supported_module() -> None:
    expected = {
        "Mean",
        "Normalize",
        "Selector",
        "ColumnSelector",
        "ConditionSelector",
        "ItemSelector",
        "Sort",
        "SplitApply",
        "Transformer",
        "PivotLonger",
        "PivotWider",
        "DeriveColumn",
        "GroupCardinalitySelector",
        "GroupPredicateSelector",
        "available_shaper_types",
    }

    assert expected == set(shapers.__all__)
    assert all(hasattr(shapers, name) for name in expected)


class TestFigureDecorations:
    """Figure helpers apply their documented Matplotlib changes."""

    def test_axis_legend_and_scale_helpers(self) -> None:
        fig, ax = plt.subplots()
        twin = ax.twinx()
        setattr(ax, "_ring5_twin", twin)
        ax.set_ylabel("left")
        twin.set_ylabel("right")
        ax.plot([1, 2, 4], [1, 2, 3], label="series")
        legend = ax.legend()

        ring5.FigureDecorations.axis_below(fig)
        ring5.FigureDecorations.tighten_y_ticks(fig, pad=2.0, twin_pad=3.0)
        ring5.FigureDecorations.set_ylabel_y(fig, 0.75)
        ring5.FigureDecorations.set_twin_ylabel_pad(fig, 12.0)
        ring5.FigureDecorations.set_legends_opaque(fig, facecolor="red", alpha=1.0, zorder=20)
        ring5.FigureDecorations.log_xaxis(
            fig, ticks=[1, 2, 4], labels=["one", "two", "four"], xlim=(1, 4)
        )
        ring5.FigureDecorations.hide_spines(fig, "top", "right")

        assert ax.get_axisbelow()
        assert ax.yaxis.label.get_position()[1] == pytest.approx(0.75)
        assert twin.yaxis.labelpad == pytest.approx(12.0)
        assert legend.get_frame().get_alpha() == pytest.approx(1.0)
        assert legend.get_zorder() == 20
        assert ax.get_xscale() == "log"
        assert [tick.get_text() for tick in ax.get_xticklabels()] == ["one", "two", "four"]
        assert ax.get_xlim() == pytest.approx((1, 4))
        assert not ax.spines["top"].get_visible()
        assert not twin.spines["right"].get_visible()
        plt.close(fig)

    def test_bar_limits_text_and_value_labels(self) -> None:
        fig, ax = plt.subplots()
        twin = ax.twinx()
        setattr(ax, "_ring5_twin", twin)
        ax.bar([0, 1], [1.0, 2.0], width=0.5)
        label = ax.text(0.0, 0.5, "target")

        ring5.FigureDecorations.clamp_bar_xlim(fig, left=0.1, right=0.2)
        ring5.FigureDecorations.nudge_text(fig, "target", dx=0.25, dy=0.5)
        ring5.FigureDecorations.over_cap_labels(
            fig,
            {("a", "base"): 0.0, ("a", "opt"): 1.0},
            {("a", "base"): 3.0, ("a", "opt"): 1.0},
            cap=2.0,
        )
        ring5.FigureDecorations.staggered_over_cap_labels(
            fig,
            {"a": 0.0, "b": 0.5, "c": 2.0},
            {"a": 4.0, "b": 5.0, "c": float("nan")},
            cap=3.0,
            lbl_dx=1.0,
        )

        assert ax.get_xlim() == pytest.approx((-0.35, 1.45))
        assert twin.get_xlim() == pytest.approx(ax.get_xlim())
        assert label.get_position() == pytest.approx((0.25, 1.0))
        texts = {text.get_text() for text in ax.texts}
        assert {"3.0", "4.0", "5.0"} <= texts
        plt.close(fig)

    def test_numbered_arrows_handle_missing_groups(self) -> None:
        fig, ax = plt.subplots()

        ring5.FigureDecorations.numbered_bar_arrows(
            fig,
            {("a", "base"): 0.0, ("a", "opt"): 1.0},
            "a",
            ["base", "missing", "opt"],
            {("a", "base"): 1.0, ("a", "opt"): 4.0},
            cap=3.0,
            label="order",
        )
        ring5.FigureDecorations.numbered_bar_arrows(fig, {}, "a", [], {}, cap=1.0)

        texts = {text.get_text() for text in ax.texts}
        assert {"1", "3", "order"} <= texts
        plt.close(fig)

    def test_noop_branches_accept_figures_without_optional_artists(self) -> None:
        fig, ax = plt.subplots()

        ring5.FigureDecorations.clamp_bar_xlim(fig)
        ring5.FigureDecorations.tighten_y_ticks(fig, twin_pad=2.0)
        ring5.FigureDecorations.set_twin_ylabel_pad(fig, 2.0)
        ring5.FigureDecorations.hide_spines(fig, "not-a-spine", include_twin=False)
        ring5.FigureDecorations.nudge_text(fig, "missing", dx=1.0)
        ring5.FigureDecorations.numbered_bar_arrows(fig, {}, "a", ["missing"], {}, cap=1.0)

        assert ax.get_xlim() == pytest.approx((0.0, 1.0))
        plt.close(fig)
