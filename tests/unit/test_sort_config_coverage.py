"""Tests for SortConfig shaper UI component — branch coverage."""

from unittest.mock import MagicMock, patch

import pandas as pd

from src.web.pages.ui.components.shapers.sort_config import SortConfig


def _columns_side_effect(n: "int | list[int]") -> "list[MagicMock]":
    count = len(n) if isinstance(n, list) else n
    cols = []
    for _ in range(count):
        m = MagicMock()
        m.__enter__ = MagicMock(return_value=m)
        m.__exit__ = MagicMock(return_value=False)
        cols.append(m)
    return cols


class TestSortConfigRender:
    """Test SortConfig.render method."""

    @patch("src.web.pages.ui.components.shapers.sort_config.st")
    def test_no_categorical_columns(self, mock_st: MagicMock) -> None:
        data = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        result = SortConfig.render(data, {}, "pfx_", "s1")
        mock_st.warning.assert_called_once()
        assert result == {"type": "sort", "order_dict": {}}

    @patch("src.web.pages.ui.components.shapers.sort_config.st")
    def test_with_categorical_no_selection(self, mock_st: MagicMock) -> None:
        data = pd.DataFrame({"cat": ["a", "b", "c"], "val": [1, 2, 3]})
        mock_st.multiselect.return_value = []  # no columns selected

        result = SortConfig.render(data, {}, "pfx_", "s1")
        assert result["type"] == "sort"
        assert result["order_dict"] == {}

    @patch("src.web.pages.ui.components.shapers.sort_config.st")
    def test_with_selected_column_small_cardinality(self, mock_st: MagicMock) -> None:
        data = pd.DataFrame({"cat": ["a", "b", "c"], "val": [1, 2, 3]})
        mock_st.multiselect.side_effect = [
            ["cat"],  # sort_columns selection
            ["c", "b", "a"],  # reordered values for "cat"
        ]
        exp = MagicMock()
        exp.__enter__ = MagicMock(return_value=exp)
        exp.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp

        result = SortConfig.render(data, {}, "pfx_", "s1")
        assert result["order_dict"]["cat"] == ["c", "b", "a"]

    @patch("src.web.pages.ui.components.shapers.sort_config.st")
    def test_with_high_cardinality(self, mock_st: MagicMock) -> None:
        vals = [f"v{i}" for i in range(25)]  # > 20
        data = pd.DataFrame({"cat": vals, "val": range(25)})
        mock_st.multiselect.side_effect = [
            ["cat"],  # sort_columns
            # NO second multiselect call — high cardinality shows text input instead
        ]
        exp = MagicMock()
        exp.__enter__ = MagicMock(return_value=exp)
        exp.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp

        result = SortConfig.render(data, {}, "pfx_", "s1")
        assert "cat" in result["order_dict"]
        mock_st.info.assert_called()

    @patch("src.web.pages.ui.components.shapers.sort_config.st")
    def test_restore_previous_order(self, mock_st: MagicMock) -> None:
        data = pd.DataFrame({"cat": ["a", "b", "c"], "val": [1, 2, 3]})
        existing = {"order_dict": {"cat": ["c", "a"]}}

        mock_st.multiselect.side_effect = [
            ["cat"],  # should default to ["cat"] since it's in existing
            ["c", "a", "b"],  # restored order + new "b"
        ]
        exp = MagicMock()
        exp.__enter__ = MagicMock(return_value=exp)
        exp.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp

        result = SortConfig.render(data, existing, "pfx_", "s1")
        assert result["order_dict"]["cat"] == ["c", "a", "b"]

    @patch("src.web.pages.ui.components.shapers.sort_config.st")
    def test_empty_multiselect_falls_back_to_default(self, mock_st: MagicMock) -> None:
        data = pd.DataFrame({"cat": ["a", "b"], "val": [1, 2]})
        mock_st.multiselect.side_effect = [
            ["cat"],  # sort_columns
            [],  # empty reorder → fall back to default_order
        ]
        exp = MagicMock()
        exp.__enter__ = MagicMock(return_value=exp)
        exp.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp

        result = SortConfig.render(data, {}, "pfx_", "s1")
        # Should use default_order = sorted unique values
        assert result["order_dict"]["cat"] == ["a", "b"]
