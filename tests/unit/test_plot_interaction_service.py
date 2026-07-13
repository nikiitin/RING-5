"""
Tests for plot_interaction_service — pure business logic for interactive plot state.

Extracted from BasePlot.update_from_relayout (93 line pure computation)
and render_reorderable_list sync logic to Layer B.
"""

from src.core.services.visualization.plot_interaction import (
    resolve_item_order,
    try_float,
    try_float_edit,
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
