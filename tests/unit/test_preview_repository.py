"""
Unit tests for PreviewRepository.

Tests the preview-commit pattern implementation without requiring actual Streamlit UI.
"""

import pandas as pd
import pytest
import streamlit as st

from src.web.repositories.preview_repository import PreviewRepository


@pytest.fixture
def test_dataframe():
    """Create a test DataFrame."""
    return pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9]})


@pytest.fixture
def clean_session_state():
    """Ensure clean session state before each test."""
    # Clear all preview keys
    PreviewRepository.clear_all_previews()
    yield
    # Cleanup after test
    PreviewRepository.clear_all_previews()


class TestPreviewRepositoryBasics:
    """Test basic preview operations."""

    def test_set_and_get_preview(self, test_dataframe, clean_session_state):
        """Test storing and retrieving preview."""
        PreviewRepository.set_preview("test_operation", test_dataframe)

        result = PreviewRepository.get_preview("test_operation")

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert result.equals(test_dataframe)

    def test_has_preview_exists(self, test_dataframe, clean_session_state):
        """Test has_preview returns True when preview exists."""
        assert not PreviewRepository.has_preview("test_op")

        PreviewRepository.set_preview("test_op", test_dataframe)

        assert PreviewRepository.has_preview("test_op")

    def test_has_preview_not_exists(self, clean_session_state):
        """Test has_preview returns False when preview doesn't exist."""
        assert not PreviewRepository.has_preview("nonexistent_operation")

    def test_get_preview_nonexistent(self, clean_session_state):
        """Test get_preview returns None for nonexistent operation."""
        result = PreviewRepository.get_preview("missing")

        assert result is None

    def test_clear_preview(self, test_dataframe, clean_session_state):
        """Test clearing preview."""
        PreviewRepository.set_preview("to_clear", test_dataframe)
        assert PreviewRepository.has_preview("to_clear")

        PreviewRepository.clear_preview("to_clear")

        assert not PreviewRepository.has_preview("to_clear")
        assert PreviewRepository.get_preview("to_clear") is None

    def test_clear_preview_nonexistent_is_safe(self, clean_session_state):
        """Test clearing nonexistent preview is idempotent."""
        # Should not raise exception
        PreviewRepository.clear_preview("nonexistent")

        # Still no preview
        assert not PreviewRepository.has_preview("nonexistent")


class TestPreviewRepositoryMultiple:
    """Test handling multiple previews."""

    def test_multiple_previews_independent(self, test_dataframe, clean_session_state):
        """Test multiple previews don't interfere with each other."""
        df1 = test_dataframe
        df2 = test_dataframe * 2
        df3 = test_dataframe * 3

        PreviewRepository.set_preview("op1", df1)
        PreviewRepository.set_preview("op2", df2)
        PreviewRepository.set_preview("op3", df3)

        # Each operation has independent state
        assert PreviewRepository.get_preview("op1").equals(df1)
        assert PreviewRepository.get_preview("op2").equals(df2)
        assert PreviewRepository.get_preview("op3").equals(df3)

    def test_clear_one_doesnt_affect_others(self, test_dataframe, clean_session_state):
        """Test clearing one preview doesn't affect others."""
        PreviewRepository.set_preview("keep1", test_dataframe)
        PreviewRepository.set_preview("remove", test_dataframe * 2)
        PreviewRepository.set_preview("keep2", test_dataframe * 3)

        PreviewRepository.clear_preview("remove")

        assert PreviewRepository.has_preview("keep1")
        assert not PreviewRepository.has_preview("remove")
        assert PreviewRepository.has_preview("keep2")

    def test_list_active_previews(self, test_dataframe, clean_session_state):
        """Test listing all active previews."""
        assert PreviewRepository.list_active_previews() == []

        PreviewRepository.set_preview("outlier_removal", test_dataframe)
        PreviewRepository.set_preview("mixer", test_dataframe)
        PreviewRepository.set_preview("seeds_reduction", test_dataframe)

        active = PreviewRepository.list_active_previews()

        assert len(active) == 3
        assert "outlier_removal" in active
        assert "mixer" in active
        assert "seeds_reduction" in active

    def test_clear_all_previews(self, test_dataframe, clean_session_state):
        """Test clearing all previews at once."""
        PreviewRepository.set_preview("op1", test_dataframe)
        PreviewRepository.set_preview("op2", test_dataframe)
        PreviewRepository.set_preview("op3", test_dataframe)

        count = PreviewRepository.clear_all_previews()

        assert count == 3
        assert PreviewRepository.list_active_previews() == []
        assert not PreviewRepository.has_preview("op1")
        assert not PreviewRepository.has_preview("op2")
        assert not PreviewRepository.has_preview("op3")


class TestPreviewRepositoryEdgeCases:
    """Test edge cases and error handling."""

    def test_set_preview_empty_name_raises(self, test_dataframe, clean_session_state):
        """Test setting preview with empty name raises error."""
        with pytest.raises(ValueError, match="Operation name cannot be empty"):
            PreviewRepository.set_preview("", test_dataframe)

    def test_set_preview_none_data_raises(self, clean_session_state):
        """Test setting preview with None data raises error."""
        with pytest.raises(ValueError, match="Preview data cannot be None"):
            PreviewRepository.set_preview("test_op", None)

    def test_get_preview_empty_name_returns_none(self, clean_session_state):
        """Test getting preview with empty name returns None."""
        result = PreviewRepository.get_preview("")

        assert result is None

    def test_has_preview_empty_name_returns_false(self, clean_session_state):
        """Test has_preview with empty name returns False."""
        assert not PreviewRepository.has_preview("")

    def test_clear_preview_empty_name_is_safe(self, clean_session_state):
        """Test clearing preview with empty name is safe."""
        # Should not raise exception
        PreviewRepository.clear_preview("")

    def test_overwrite_existing_preview(self, test_dataframe, clean_session_state):
        """Test overwriting existing preview replaces it."""
        df1 = test_dataframe
        df2 = test_dataframe * 10

        PreviewRepository.set_preview("overwrite", df1)
        original = PreviewRepository.get_preview("overwrite")
        assert original.equals(df1)

        # Overwrite
        PreviewRepository.set_preview("overwrite", df2)
        updated = PreviewRepository.get_preview("overwrite")

        assert updated.equals(df2)
        assert not updated.equals(df1)


class TestPreviewRepositoryDataIntegrity:
    """Test data integrity and isolation."""

    def test_preview_data_not_modified_by_external_changes(
        self, test_dataframe, clean_session_state
    ):
        """Test stored preview behavior with DataFrame references.

        Note: Streamlit session_state stores references, not deep copies.
        This test documents expected behavior - modifications to original
        DataFrame WILL affect stored preview since they share the same object.
        To avoid this, services should pass .copy() when storing previews.
        """
        df = test_dataframe.copy()
        PreviewRepository.set_preview("isolation_test", df)

        # Modify original DataFrame
        df.loc[0, "a"] = 999

        # Stored preview is a reference, so it WILL be modified
        stored = PreviewRepository.get_preview("isolation_test")
        assert stored.loc[0, "a"] == 999  # Reflects the change

        # To prevent this, services should store copies:
        df2 = test_dataframe.copy()
        PreviewRepository.set_preview("safe_test", df2.copy())  # Store a copy
        df2.loc[0, "a"] = 777

        # This preview is unaffected because we stored a copy
        safe_stored = PreviewRepository.get_preview("safe_test")
        assert safe_stored.loc[0, "a"] == 1  # Original value preserved

    def test_dataframe_types_preserved(self, clean_session_state):
        """Test DataFrame column types are preserved."""
        df = pd.DataFrame(
            {"int_col": [1, 2, 3], "float_col": [1.1, 2.2, 3.3], "str_col": ["a", "b", "c"]}
        )

        PreviewRepository.set_preview("types_test", df)
        result = PreviewRepository.get_preview("types_test")

        assert result["int_col"].dtype == df["int_col"].dtype
        assert result["float_col"].dtype == df["float_col"].dtype
        assert result["str_col"].dtype == df["str_col"].dtype

    def test_empty_dataframe_handled_correctly(self, clean_session_state):
        """Test empty DataFrame can be stored and retrieved."""
        empty_df = pd.DataFrame()

        PreviewRepository.set_preview("empty", empty_df)
        result = PreviewRepository.get_preview("empty")

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


class TestPreviewRepositoryNamingConventions:
    """Test naming convention enforcement."""

    def test_operation_names_with_special_chars(self, test_dataframe, clean_session_state):
        """Test operation names with underscores and hyphens work correctly."""
        names = [
            "outlier_removal",
            "seeds-reduction",
            "mixer_sum_operation",
            "preprocessing.step.1",
        ]

        for name in names:
            PreviewRepository.set_preview(name, test_dataframe)
            assert PreviewRepository.has_preview(name)
            assert PreviewRepository.get_preview(name) is not None

    def test_operation_names_are_case_sensitive(self, test_dataframe, clean_session_state):
        """Test operation names are case-sensitive."""
        PreviewRepository.set_preview("MixerOp", test_dataframe)

        assert PreviewRepository.has_preview("MixerOp")
        assert not PreviewRepository.has_preview("mixerop")
        assert not PreviewRepository.has_preview("MIXEROP")


class TestPreviewRepositorySessionIsolation:
    """Test isolation from non-preview session state."""

    def test_preview_keys_dont_collide_with_other_state(self, test_dataframe, clean_session_state):
        """Test preview keys don't interfere with other session state."""
        # Set some regular session state
        st.session_state["data"] = test_dataframe
        st.session_state["config"] = {"key": "value"}

        # Set preview
        PreviewRepository.set_preview("operation", test_dataframe)

        # Regular state should still exist
        assert "data" in st.session_state
        assert "config" in st.session_state

        # Clear previews shouldn't affect regular state
        PreviewRepository.clear_all_previews()

        assert "data" in st.session_state
        assert "config" in st.session_state

    def test_list_previews_only_returns_previews(self, test_dataframe, clean_session_state):
        """Test list_active_previews only returns preview keys."""
        # Add regular session state
        st.session_state["regular_key"] = test_dataframe
        st.session_state["another_key"] = "value"

        # Add previews
        PreviewRepository.set_preview("preview1", test_dataframe)
        PreviewRepository.set_preview("preview2", test_dataframe)

        active = PreviewRepository.list_active_previews()

        # Should only have preview operations
        assert len(active) == 2
        assert "preview1" in active
        assert "preview2" in active
        assert "regular_key" not in active
        assert "another_key" not in active
