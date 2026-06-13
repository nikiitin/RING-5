"""Category super-groups: bold boundary separators + group labels.

Covers GroupedBarUtils.calculate_grouped_coordinates' `category_groups`
handling, the group-label annotation builder, and the FigureSpec/Builder
surface that emits the flat config keys.
"""

import pytest

from src.web.pages.ui.plotting.utils.grouped_bar_utils import GroupedBarUtils
from ring5.figure_spec import FigureSpec, FigureSpecBuilder

CATS = ["a", "b", "c"]
GROUPS = {"a": "G1", "b": "G1", "c": "G2"}


def _coords(config):
    base = {"bargroupgap": 0.5}
    base.update(config)
    return GroupedBarUtils.calculate_grouped_coordinates(CATS, ["p"], base)


class TestGroupSeparators:
    def test_boundary_gets_bold_separator_and_within_group_stays_faint(self):
        res = _coords({"show_separators": True, "category_groups": GROUPS})
        seps = res["separator_lines"]
        assert len(seps) == 2
        faint, bold = seps
        assert faint.color == "#E0E0E0" and faint.width == 1.0 and faint.dash == "dash"
        assert bold.color == "#444444" and bold.width == 1.6 and bold.dash == "solid"
        # gap midpoints for centers 0/1.5/3.0 with bargroupgap=0.5
        assert faint.x == pytest.approx(0.75)
        assert bold.x == pytest.approx(2.25)

    def test_boundary_drawn_even_without_show_separators(self):
        res = _coords({"show_separators": False, "category_groups": GROUPS})
        seps = res["separator_lines"]
        assert len(seps) == 1
        assert seps[0].color == "#444444" and seps[0].x == pytest.approx(2.25)

    def test_separator_style_overrides(self):
        res = _coords(
            {
                "category_groups": GROUPS,
                "category_group_separator_color": "#111111",
                "category_group_separator_width": 2.5,
                "category_group_separator_dash": "dot",
            }
        )
        sep = res["separator_lines"][0]
        assert (sep.color, sep.width, sep.dash) == ("#111111", 2.5, "dot")

    def test_isolated_last_group_keeps_isolation_separator(self):
        # label change at the isolation boundary -> only the thick #333 isolation line
        res = _coords({"category_groups": GROUPS, "isolate_last_group": True, "isolation_gap": 0.5})
        assert [s.color for s in res["separator_lines"]] == ["#333333"]

    def test_no_category_groups_unchanged(self):
        res = _coords({"show_separators": True})
        assert res["category_group_centers"] == []
        assert all(s.color == "#E0E0E0" for s in res["separator_lines"])


class TestGroupCenters:
    def test_centers_are_run_means(self):
        res = _coords({"category_groups": GROUPS})
        assert res["category_group_centers"] == [
            (pytest.approx(0.75), "G1"),  # mean of centers 0 and 1.5
            (pytest.approx(3.0), "G2"),
        ]

    def test_unmapped_categories_get_no_label_but_make_a_boundary(self):
        res = _coords({"category_groups": {"a": "G1", "b": "G1"}})  # "c" unmapped
        assert res["category_group_centers"] == [(pytest.approx(0.75), "G1")]
        assert len(res["separator_lines"]) == 1  # G1 -> unmapped boundary


class TestGroupRules:
    def test_rules_span_each_run_with_inset(self):
        res = _coords({"category_groups": GROUPS})
        rules = res["category_group_rules"]
        assert len(rules) == 2
        g1, g2 = rules
        # cluster edges a..b = [-0.5, 2.0], c = [2.5, 3.5]; default inset 0.35
        assert g1.x0 == pytest.approx(-0.15) and g1.x1 == pytest.approx(1.65)
        assert g2.x0 == pytest.approx(2.85) and g2.x1 == pytest.approx(3.15)
        # default y sits just above the label offset (-0.28 + 0.025)
        assert g1.y == pytest.approx(-0.255)
        assert g1.color == "#444444" and g1.width == 1.0

    def test_rule_style_and_position_overrides(self):
        res = _coords(
            {
                "category_groups": GROUPS,
                "category_group_rule_color": "#999999",
                "category_group_rule_width": 1.5,
                "category_group_rule_y": -0.4,
                "category_group_rule_inset": 0.0,
            }
        )
        rule = res["category_group_rules"][0]
        assert (rule.color, rule.width, rule.y) == ("#999999", 1.5, -0.4)
        assert rule.x0 == pytest.approx(-0.5) and rule.x1 == pytest.approx(2.0)

    def test_rules_disabled(self):
        res = _coords({"category_groups": GROUPS, "category_group_rule": False})
        assert res["category_group_rules"] == []
        assert len(res["category_group_centers"]) == 2  # labels unaffected

    def test_matplotlib_draws_rules_unclipped(self):
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        from src.core.models.visualization.trace_build_result import RuleLine
        from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib

        fig, ax = plt.subplots()
        before = len(ax.lines)
        FigureSpecToMatplotlib.draw_layout_shapes(
            ax, [], [], [RuleLine(x0=0.0, x1=2.0, y=-0.2, color="#444444", width=1.0)]
        )
        rules = ax.lines[before:]
        assert len(rules) == 1
        assert rules[0].get_clip_on() is False
        assert rules[0].get_color() == "#444444"
        plt.close(fig)

    def test_plotly_emits_rule_shape(self):
        from src.core.models.visualization.trace_build_result import RuleLine, TraceBuildResult
        from src.web.rendering.trace_to_plotly import traces_to_plotly

        result = TraceBuildResult(rule_lines=[RuleLine(x0=0.0, x1=2.0, y=-0.2)])
        fig = traces_to_plotly(result)
        shapes = fig.layout.shapes
        assert len(shapes) == 1
        assert shapes[0].type == "line" and shapes[0].yref == "paper"
        assert shapes[0].y0 == -0.2 and shapes[0].y1 == -0.2


class TestGroupAnnotations:
    def test_annotation_content(self):
        anns = GroupedBarUtils.build_category_group_annotations(
            [(1.0, "G1")], font_size=9, font_color="#222222", y_offset=-0.3
        )
        (ann,) = anns
        assert ann["text"] == "<b>G1</b>"
        assert ann["x"] == 1.0 and ann["y"] == -0.3
        assert ann["xref"] == "x" and ann["yref"] == "paper"
        assert ann["xanchor"] == "center" and ann["yanchor"] == "top"
        assert ann["font"] == {"size": 9, "color": "#222222"}
        assert ann["textangle"] == 0


class TestMajorLabelRotationOverrides:
    def test_per_label_rotation_override(self):
        anns = GroupedBarUtils.build_category_annotations(
            [(0.0, "a"), (1.0, "mean")], rotation=30.0, rotation_overrides={"mean": 90.0}
        )
        assert [a["textangle"] for a in anns] == [30.0, 90.0]
        assert [a["xanchor"] for a in anns] == ["right", "right"]

    def test_override_to_horizontal_recenters(self):
        anns = GroupedBarUtils.build_category_annotations(
            [(0.0, "a"), (1.0, "mean")], rotation=30.0, rotation_overrides={"mean": 0.0}
        )
        assert anns[1]["textangle"] == 0.0 and anns[1]["xanchor"] == "center"

    def test_spec_emits_overrides(self):
        cfg = FigureSpec(major_label_rotation_overrides={"mean": 90}).to_config()
        assert cfg["major_label_rotation_overrides"] == {"mean": 90}
        assert "major_label_rotation_overrides" not in FigureSpec().to_config()

    def test_builder(self):
        spec = FigureSpecBuilder().category_labels(rotation_overrides={"mean": 90}).build()
        assert spec.major_label_rotation_overrides == {"mean": 90}


class TestFigureSpecSurface:
    def test_spec_emits_flat_keys(self):
        cfg = FigureSpec(category_groups={"a": "G1"}, category_group_label_size=9).to_config()
        assert cfg["category_groups"] == {"a": "G1"}
        assert cfg["category_group_label_size"] == 9
        assert cfg["category_group_separator_color"] == "#444444"

    def test_spec_omits_keys_when_unset(self):
        cfg = FigureSpec().to_config()
        assert "category_groups" not in cfg
        assert "category_group_label_size" not in cfg

    def test_spec_emits_rule_keys(self):
        cfg = FigureSpec(category_groups={"a": "G1"}, category_group_rule_width=1.4).to_config()
        assert cfg["category_group_rule"] is True
        assert cfg["category_group_rule_width"] == 1.4
        assert cfg["category_group_rule_inset"] == 0.35
        assert "category_group_rule_y" not in cfg  # auto unless set
        cfg = FigureSpec(category_groups={"a": "G1"}, category_group_rule_y=-0.4).to_config()
        assert cfg["category_group_rule_y"] == -0.4

    def test_builder_method(self):
        spec = (
            FigureSpecBuilder()
            .category_groups(
                {"a": "G1"}, separator_width=2.0, label_offset=-0.3, rule=False, rule_width=1.2
            )
            .build()
        )
        assert spec.category_groups == {"a": "G1"}
        assert spec.category_group_separator_width == 2.0
        assert spec.category_group_label_offset == -0.3
        assert spec.category_group_label_size == 12  # untouched default
        assert spec.category_group_rule is False
        assert spec.category_group_rule_width == 1.2
