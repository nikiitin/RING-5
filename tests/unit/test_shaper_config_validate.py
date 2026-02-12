"""
Tests for shaper_config.py: validate_shaper_config and apply_shapers.

Covers:
- validate_shaper_config: all shaper types, missing fields, empty fields
- apply_shapers: successful pipeline, incomplete config skip, errors
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.web.pages.ui.shaper_config import apply_shapers, validate_shaper_config


class TestValidateShaperConfig:
    """Tests for validate_shaper_config pure logic function."""

    def test_normalize_all_present_valid(self) -> None:
        config = {
            "normalizeVars": ["ipc"],
            "normalizerColumn": "config",
            "normalizerValue": "baseline",
            "groupBy": ["benchmark"],
        }
        is_valid, missing = validate_shaper_config("normalize", config)
        assert is_valid is True
        assert missing is None

    def test_normalize_missing_fields(self) -> None:
        config = {"normalizeVars": ["ipc"]}
        is_valid, missing = validate_shaper_config("normalize", config)
        assert is_valid is False
        assert missing is not None
        assert "normalizerColumn" in missing
        assert "normalizerValue" in missing
        assert "groupBy" in missing

    def test_normalize_empty_list_field(self) -> None:
        config = {
            "normalizeVars": [],  # empty list → missing
            "normalizerColumn": "config",
            "normalizerValue": "baseline",
            "groupBy": ["benchmark"],
        }
        is_valid, missing = validate_shaper_config("normalize", config)
        assert is_valid is False
        assert "normalizeVars" in missing

    def test_normalize_empty_string_field(self) -> None:
        config = {
            "normalizeVars": ["ipc"],
            "normalizerColumn": "",  # empty string → missing
            "normalizerValue": "baseline",
            "groupBy": ["benchmark"],
        }
        is_valid, missing = validate_shaper_config("normalize", config)
        assert is_valid is False
        assert "normalizerColumn" in missing

    def test_normalize_none_field(self) -> None:
        config = {
            "normalizeVars": ["ipc"],
            "normalizerColumn": None,
            "normalizerValue": "baseline",
            "groupBy": ["benchmark"],
        }
        is_valid, missing = validate_shaper_config("normalize", config)
        assert is_valid is False
        assert "normalizerColumn" in missing

    def test_mean_valid(self) -> None:
        config = {
            "groupingColumns": ["benchmark", "config"],
            "meanVars": ["ipc", "cycles"],
        }
        is_valid, missing = validate_shaper_config("mean", config)
        assert is_valid is True
        assert missing is None

    def test_mean_missing_fields(self) -> None:
        config = {}
        is_valid, missing = validate_shaper_config("mean", config)
        assert is_valid is False
        assert "groupingColumns" in missing
        assert "meanVars" in missing

    def test_column_selector_valid(self) -> None:
        config = {"columns": ["a", "b"]}
        is_valid, missing = validate_shaper_config("columnSelector", config)
        assert is_valid is True

    def test_column_selector_empty_columns(self) -> None:
        config = {"columns": []}
        is_valid, missing = validate_shaper_config("columnSelector", config)
        assert is_valid is False
        assert "columns" in missing

    def test_condition_selector_valid(self) -> None:
        config = {"column": "status"}
        is_valid, missing = validate_shaper_config("conditionSelector", config)
        assert is_valid is True

    def test_transformer_valid(self) -> None:
        config = {"column": "value"}
        is_valid, missing = validate_shaper_config("transformer", config)
        assert is_valid is True

    def test_sort_valid(self) -> None:
        config = {"order_dict": {"col": True}}
        is_valid, missing = validate_shaper_config("sort", config)
        assert is_valid is True

    def test_unknown_type_no_required_params(self) -> None:
        """Unknown shaper types have no required params → always valid."""
        config = {"anything": "goes"}
        is_valid, missing = validate_shaper_config("unknown_type", config)
        assert is_valid is True
        assert missing is None


class TestApplyShapers:
    """Tests for apply_shapers pipeline execution."""

    def test_empty_pipeline(self) -> None:
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = apply_shapers(df, [])
        assert len(result) == 3
        assert list(result.columns) == ["a"]

    def test_none_data_raises(self) -> None:
        with pytest.raises(ValueError, match="Cannot apply shapers to None"):
            apply_shapers(None, [])

    @patch("src.web.pages.ui.shaper_config.st")
    def test_skips_shaper_with_no_type(self, mock_st: MagicMock) -> None:
        df = pd.DataFrame({"a": [1, 2]})
        result = apply_shapers(df, [{"some": "config"}])
        assert len(result) == 2  # data unchanged

    @patch("src.web.pages.ui.shaper_config.st")
    def test_skips_incomplete_config(self, mock_st: MagicMock) -> None:
        """Incomplete config should show warning and skip."""
        df = pd.DataFrame({"a": [1, 2]})
        config = [{"type": "normalize", "normalizeVars": ["a"]}]  # missing fields
        result = apply_shapers(df, config)
        assert len(result) == 2  # data unchanged
        mock_st.warning.assert_called_once()

    @patch("src.web.pages.ui.shaper_config.st")
    @patch("src.web.pages.ui.shaper_config.ShaperFactory")
    def test_successful_shaper_execution(self, mock_factory: MagicMock, mock_st: MagicMock) -> None:
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        transformed = pd.DataFrame({"a": [1, 2], "b": [4, 5]})

        mock_shaper = MagicMock(return_value=transformed)
        mock_factory.create_shaper.return_value = mock_shaper

        config = [{"type": "columnSelector", "columns": ["a", "b"]}]
        result = apply_shapers(df, config)

        assert len(result) == 2
        mock_factory.create_shaper.assert_called_once_with("columnSelector", config[0])

    @patch("src.web.pages.ui.shaper_config.st")
    @patch("src.web.pages.ui.shaper_config.ShaperFactory")
    def test_value_error_in_shaper(self, mock_factory: MagicMock, mock_st: MagicMock) -> None:
        mock_factory.create_shaper.side_effect = ValueError("bad config")

        df = pd.DataFrame({"a": [1]})
        config = [{"type": "columnSelector", "columns": ["a"]}]

        with pytest.raises(ValueError, match="Configuration error"):
            apply_shapers(df, config)
        mock_st.error.assert_called_once()

    @patch("src.web.pages.ui.shaper_config.st")
    @patch("src.web.pages.ui.shaper_config.ShaperFactory")
    def test_key_error_in_shaper(self, mock_factory: MagicMock, mock_st: MagicMock) -> None:
        mock_shaper = MagicMock(side_effect=KeyError("missing_col"))
        mock_factory.create_shaper.return_value = mock_shaper

        df = pd.DataFrame({"a": [1]})
        config = [{"type": "columnSelector", "columns": ["a"]}]

        with pytest.raises(KeyError, match="Missing required column"):
            apply_shapers(df, config)
        mock_st.error.assert_called_once()

    @patch("src.web.pages.ui.shaper_config.st")
    @patch("src.web.pages.ui.shaper_config.ShaperFactory")
    def test_generic_exception_in_shaper(self, mock_factory: MagicMock, mock_st: MagicMock) -> None:
        mock_shaper = MagicMock(side_effect=RuntimeError("unexpected"))
        mock_factory.create_shaper.return_value = mock_shaper

        df = pd.DataFrame({"a": [1]})
        config = [{"type": "columnSelector", "columns": ["a"]}]

        with pytest.raises(RuntimeError):
            apply_shapers(df, config)
        mock_st.error.assert_called_once()

    def test_does_not_mutate_original_data(self) -> None:
        """apply_shapers should call .copy() on the input."""
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = apply_shapers(df, [])
        assert result is not df
