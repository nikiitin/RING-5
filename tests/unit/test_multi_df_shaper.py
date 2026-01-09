"""Tests for MultiDfShaper class."""

import pandas as pd
import pytest

from src.web.services.shapers.multi_df_shaper import MultiDfShaper


class TestMultiDfShaper:
    """Tests for MultiDfShaper validation."""

    def test_none_input_raises(self):
        """Test that None input raises ValueError."""
        shaper = MultiDfShaper({})

        with pytest.raises(ValueError, match="None"):
            shaper(None)

    def test_non_list_input_raises(self):
        """Test that non-list input raises ValueError."""
        shaper = MultiDfShaper({})

        with pytest.raises(ValueError, match="not a list"):
            shaper(pd.DataFrame({"a": [1, 2, 3]}))

    def test_non_dataframe_in_list_raises(self):
        """Test that list with non-DataFrame raises ValueError."""
        shaper = MultiDfShaper({})

        with pytest.raises(ValueError, match="not a pandas dataframe"):
            shaper([pd.DataFrame({"a": [1]}), "not a dataframe"])

    def test_valid_list_passes_validation(self):
        """Test that valid list of DataFrames passes validation phase."""
        shaper = MultiDfShaper({})
        dfs = [pd.DataFrame({"a": [1, 2]}), pd.DataFrame({"b": [3, 4]})]

        # Parent class has incompatible __call__ (expects single DataFrame)
        # This tests that validation passes and parent is called
        with pytest.raises(AttributeError):
            shaper(dfs)

    def test_empty_list_passes_validation(self):
        """Test that empty list passes validation phase."""
        shaper = MultiDfShaper({})

        # Empty list passes validation (vacuously true that all items are DataFrames)
        with pytest.raises(AttributeError):
            shaper([])

