"""
Tests for plot_interaction_service — pure business logic for interactive plot state.

Extracted from BasePlot.update_from_relayout (93 line pure computation)
and render_reorderable_list sync logic to Layer B.
"""

from src.core.services.plot_interaction_service import (
    resolve_item_order,
    try_float,
    try_float_edit,
    update_config_from_relayout,
)

# ─── try_float ───────────────────────────────────────────────────────────────


class TestTryFloat:
    """Tests for string-to-float conversion."""

    def test_valid_float(self) -> None:
        assert try_float("3.14") == 3.14

    def test_valid_integer(self) -> None:
        assert try_float("42") == 42.0

    def test_negative_number(self) -> None:
        assert try_float("-1.5") == -1.5

    def test_non_numeric_string(self) -> None:
        assert try_float("category_a") == "category_a"

    def test_empty_string(self) -> None:
        assert try_float("") == ""

    def test_scientific_notation(self) -> None:
        result = try_float("1e3")
        assert result == 1000.0


class TestTryFloatEdit:
    """Tests for any-type-to-float conversion."""

    def test_integer_input(self) -> None:
        assert try_float_edit(42) == 42.0

    def test_float_input(self) -> None:
        assert try_float_edit(3.14) == 3.14

    def test_string_number(self) -> None:
        assert try_float_edit("7.5") == 7.5

    def test_non_numeric_string(self) -> None:
        assert try_float_edit("hello") == "hello"

    def test_none_input(self) -> None:
        assert try_float_edit(None) == "None"


# ─── update_config_from_relayout ─────────────────────────────────────────────


class TestUpdateConfigFromRelayout:
    """Tests for relayout event processing."""

    def test_empty_relayout_returns_unchanged(self) -> None:
        config = {"range_x": [0, 10]}
        new_config, changed = update_config_from_relayout(config, {})
        assert changed is False
        assert new_config == config

    def test_none_relayout_returns_unchanged(self) -> None:
        config = {"range_x": None}
        new_config, changed = update_config_from_relayout(config, {})
        assert changed is False

    def test_xaxis_zoom_range_bracket(self) -> None:
        config = {"range_x": None}
        relayout = {"xaxis.range[0]": 0, "xaxis.range[1]": 10}
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is True
        assert new_config["range_x"] == [0, 10]

    def test_xaxis_zoom_range_direct(self) -> None:
        config = {"range_x": None}
        relayout = {"xaxis.range": [5, 15]}
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is True
        assert new_config["range_x"] == [5, 15]

    def test_yaxis_zoom_range_bracket(self) -> None:
        config = {"range_y": None}
        relayout = {"yaxis.range[0]": -5, "yaxis.range[1]": 5}
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is True
        assert new_config["range_y"] == [-5, 5]

    def test_autorange_resets_x(self) -> None:
        config = {"range_x": [0, 10], "range_y": [0, 5]}
        relayout = {"xaxis.autorange": True}
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is True
        assert new_config["range_x"] is None
        assert new_config["range_y"] == [0, 5]  # Unchanged

    def test_autorange_resets_y(self) -> None:
        config = {"range_y": [0, 5]}
        relayout = {"yaxis.autorange": True}
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is True
        assert new_config["range_y"] is None

    def test_autorange_no_change_when_already_none(self) -> None:
        config = {"range_x": None}
        relayout = {"xaxis.autorange": True}
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is False

    def test_legend_drag_position(self) -> None:
        config = {}
        relayout = {"legend.x": 0.5, "legend.y": 0.9}
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is True
        assert new_config["legend_x"] == 0.5
        assert new_config["legend_y"] == 0.9
        assert new_config["legend_xanchor"] == "left"
        assert new_config["legend_yanchor"] == "top"

    def test_legend2_drag_position(self) -> None:
        config = {}
        relayout = {"legend2.x": 0.3, "legend2.y": 0.7}
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is True
        assert new_config["legend2_x"] == 0.3
        assert new_config["legend2_y"] == 0.7

    def test_legend_anchor(self) -> None:
        config = {}
        relayout = {"legend.xanchor": "right"}
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is True
        assert new_config["legend_xanchor"] == "right"

    def test_legend_title_text(self) -> None:
        config = {"legend_title": "Old Title"}
        relayout = {"legend.title.text": "New Title"}
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is True
        assert new_config["legend_title"] == "New Title"

    def test_same_value_no_change(self) -> None:
        config = {"range_x": [0, 10]}
        relayout = {"xaxis.range[0]": 0, "xaxis.range[1]": 10}
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is False

    def test_float_close_no_change(self) -> None:
        """Values within floating point tolerance should not trigger change."""
        config = {"range_x": [5.0, 10.0]}
        relayout = {
            "xaxis.range[0]": 5.0 + 5e-12,
            "xaxis.range[1]": 10.0 - 1e-11,
        }
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is False

    def test_does_not_mutate_original_config(self) -> None:
        config = {"range_x": None}
        relayout = {"xaxis.range[0]": 0, "xaxis.range[1]": 10}
        new_config, changed = update_config_from_relayout(config, relayout)
        assert config["range_x"] is None  # Original unchanged
        assert new_config["range_x"] == [0, 10]

    def test_ignores_non_legend_keys(self) -> None:
        config = {}
        relayout = {"some_other_key": 42}
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is False

    def test_ignores_legend_key_without_dot(self) -> None:
        config = {}
        relayout = {"legend": True}  # No dot-separated property
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is False

    def test_combined_zoom_and_legend(self) -> None:
        config = {"range_x": None, "legend_x": None}
        relayout = {
            "xaxis.range[0]": 1,
            "xaxis.range[1]": 5,
            "legend.x": 0.8,
        }
        new_config, changed = update_config_from_relayout(config, relayout)
        assert changed is True
        assert new_config["range_x"] == [1, 5]
        assert new_config["legend_x"] == 0.8


# ─── resolve_item_order ─────────────────────────────────────────────────────


class TestResolveItemOrder:
    """Tests for reorderable list synchronization."""

    def test_natural_order_no_defaults(self) -> None:
        result = resolve_item_order(["a", "b", "c"])
        assert result == ["a", "b", "c"]

    def test_with_default_order(self) -> None:
        result = resolve_item_order(["a", "b", "c"], default_order=["c", "b", "a"])
        assert result == ["c", "b", "a"]

    def test_default_order_filters_missing(self) -> None:
        """Default order items not in items list should be excluded."""
        result = resolve_item_order(["a", "c"], default_order=["c", "b", "a"])
        assert result == ["c", "a"]

    def test_default_order_appends_new(self) -> None:
        """Items not in default_order should be appended."""
        result = resolve_item_order(["a", "b", "c", "d"], default_order=["c", "b", "a"])
        assert result == ["c", "b", "a", "d"]

    def test_current_order_unchanged(self) -> None:
        """If items match current_order exactly, return as-is."""
        result = resolve_item_order(["a", "b", "c"], current_order=["c", "b", "a"])
        assert result == ["c", "b", "a"]

    def test_current_order_removes_deleted(self) -> None:
        result = resolve_item_order(["a", "c"], current_order=["c", "b", "a"])
        assert result == ["c", "a"]

    def test_current_order_appends_new(self) -> None:
        result = resolve_item_order(["a", "b", "c", "d"], current_order=["c", "b", "a"])
        assert result == ["c", "b", "a", "d"]

    def test_empty_items(self) -> None:
        result = resolve_item_order([])
        assert result == []

    def test_empty_items_with_current_order(self) -> None:
        result = resolve_item_order([], current_order=["a", "b"])
        assert result == []

    def test_current_order_takes_precedence_over_default(self) -> None:
        """current_order should be used instead of default_order if provided."""
        result = resolve_item_order(
            ["a", "b"],
            default_order=["b", "a"],
            current_order=["a", "b"],
        )
        assert result == ["a", "b"]
