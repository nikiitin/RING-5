"""Unit tests for major-group (category) label rotation."""

from __future__ import annotations

from src.web.pages.ui.plotting.utils import GroupedBarUtils
from src.web.pages.ui.plotting.utils.grouped_stacked_bar_helpers import (
    build_category_annotations,
)


class TestCategoryLabelRotation:
    """GroupedBarUtils.build_category_annotations emits a textangle + matching anchor."""

    def test_default_is_horizontal(self) -> None:
        anns = GroupedBarUtils.build_category_annotations([(0.5, "mcf")])
        assert anns[0]["textangle"] == 0
        assert anns[0]["xanchor"] == "center"

    def test_rotation_sets_textangle_and_right_anchor(self) -> None:
        anns = GroupedBarUtils.build_category_annotations([(0.5, "mcf")], rotation=30)
        assert anns[0]["textangle"] == 30
        assert anns[0]["xanchor"] == "right"

    def test_helper_passes_major_label_rotation_from_config(self) -> None:
        anns = build_category_annotations(
            [(0.5, "mcf"), (2.5, "omnetpp")],
            {"major_label_rotation": 45, "group_label_alternate": False},
        )
        assert all(a["textangle"] == 45 for a in anns)
        assert all(a["xanchor"] == "right" for a in anns)

    def test_helper_default_no_rotation(self) -> None:
        anns = build_category_annotations([(0.5, "mcf")], {"group_label_alternate": False})
        assert anns[0]["textangle"] == 0
