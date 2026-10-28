"""
Unit tests for PreviewRepository.

Tests the preview-commit pattern implementation.
"""

from typing import Any

import pandas as pd
import pytest
from pandas import DataFrame

from src.core.state.repositories.preview_repository import PreviewRepository


@pytest.fixture
def test_dataframe() -> DataFrame:
    """Create a test DataFrame."""
    return pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9]})


@pytest.fixture
def preview_repo() -> PreviewRepository:
    """Create a fresh PreviewRepository for each test."""
    return PreviewRepository()


class TestPreviewRepositoryBasics:
    """Test basic preview operations."""

    def test_set_and_get_preview(
        self, test_dataframe: Any, preview_repo: Any, preview_context
    ) -> None:
        """Test storing and retrieving preview."""
        preview_repo.set_preview("test_operation", test_dataframe, context=preview_context)

        result = preview_repo.get_preview("test_operation")

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert result.equals(test_dataframe)

    def test_has_preview_exists(
        self, test_dataframe: Any, preview_repo: Any, preview_context
    ) -> None:
        """Test has_preview returns True when preview exists."""
        assert not preview_repo.has_preview("test_op")

        preview_repo.set_preview("test_op", test_dataframe, context=preview_context)

        assert preview_repo.has_preview("test_op")

    def test_has_preview_not_exists(self, preview_repo: Any) -> None:
        """Test has_preview returns False when preview doesn't exist."""
        assert not preview_repo.has_preview("nonexistent_operation")

    def test_get_preview_nonexistent(self, preview_repo: Any) -> None:
        """Test get_preview returns None for nonexistent operation."""
        result = preview_repo.get_preview("missing")

        assert result is None

    def test_clear_preview(self, test_dataframe: Any, preview_repo: Any, preview_context) -> None:
        """Test clearing preview."""
        preview_repo.set_preview("to_clear", test_dataframe, context=preview_context)
        assert preview_repo.has_preview("to_clear")

        preview_repo.clear_preview("to_clear")

        assert not preview_repo.has_preview("to_clear")
        assert preview_repo.get_preview("to_clear") is None

    def test_clear_preview_nonexistent_is_safe(self, preview_repo: Any) -> None:
        """Test clearing nonexistent preview is idempotent."""
        # Should not raise exception
        preview_repo.clear_preview("nonexistent")

        # Still no preview
        assert not preview_repo.has_preview("nonexistent")


class TestPreviewRepositoryMultiple:
    """Test handling multiple previews."""

    def test_multiple_previews_independent(
        self, test_dataframe: Any, preview_repo: Any, preview_context
    ) -> None:
        """Test multiple previews don't interfere with each other."""
        df1 = test_dataframe
        df2 = test_dataframe * 2
        df3 = test_dataframe * 3

        preview_repo.set_preview("op1", df1, context=preview_context)
        preview_repo.set_preview("op2", df2, context=preview_context)
        preview_repo.set_preview("op3", df3, context=preview_context)

        # Each operation has independent state
        assert preview_repo.get_preview("op1").equals(df1)
        assert preview_repo.get_preview("op2").equals(df2)
        assert preview_repo.get_preview("op3").equals(df3)

    def test_clear_one_doesnt_affect_others(
        self, test_dataframe: Any, preview_repo: Any, preview_context
    ) -> None:
        """Test clearing one preview doesn't affect others."""
        preview_repo.set_preview("keep1", test_dataframe, context=preview_context)
        preview_repo.set_preview("remove", test_dataframe * 2, context=preview_context)
        preview_repo.set_preview("keep2", test_dataframe * 3, context=preview_context)

        preview_repo.clear_preview("remove")

        assert preview_repo.has_preview("keep1")
        assert not preview_repo.has_preview("remove")
        assert preview_repo.has_preview("keep2")

    def test_clear_all_previews(
        self, test_dataframe: Any, preview_repo: Any, preview_context
    ) -> None:
        """Test clearing all previews at once."""
        preview_repo.set_preview("op1", test_dataframe, context=preview_context)
        preview_repo.set_preview("op2", test_dataframe, context=preview_context)
        preview_repo.set_preview("op3", test_dataframe, context=preview_context)

        count = preview_repo.clear_all_previews()

        assert count == 3
        assert not preview_repo.has_preview("op1")
        assert not preview_repo.has_preview("op2")
        assert not preview_repo.has_preview("op3")


class TestPreviewRepositoryEdgeCases:
    """Test edge cases and error handling."""

    def test_set_preview_empty_name_raises(
        self, test_dataframe: Any, preview_repo: Any, preview_context
    ) -> None:
        """Test setting preview with empty name raises error."""
        with pytest.raises(ValueError, match="Operation name cannot be empty"):
            preview_repo.set_preview("", test_dataframe, context=preview_context)

    def test_set_preview_none_data_raises(self, preview_repo: Any, preview_context) -> None:
        """Test setting preview with None data raises error."""
        with pytest.raises(ValueError, match="Preview data cannot be None"):
            preview_repo.set_preview("test_op", None, context=preview_context)

    def test_get_preview_empty_name_returns_none(self, preview_repo: Any) -> None:
        """Test getting preview with empty name returns None."""
        result = preview_repo.get_preview("")

        assert result is None

    def test_has_preview_empty_name_returns_false(self, preview_repo: Any) -> None:
        """Test has_preview with empty name returns False."""
        assert not preview_repo.has_preview("")

    def test_clear_preview_empty_name_is_safe(self, preview_repo: Any) -> None:
        """Test clearing preview with empty name is safe."""
        # Should not raise exception
        preview_repo.clear_preview("")

    def test_overwrite_existing_preview(
        self, test_dataframe: Any, preview_repo: Any, preview_context
    ) -> None:
        """Test overwriting existing preview replaces it."""
        df1 = test_dataframe
        df2 = test_dataframe * 10

        preview_repo.set_preview("overwrite", df1, context=preview_context)
        original = preview_repo.get_preview("overwrite")
        assert original.equals(df1)

        # Overwrite
        preview_repo.set_preview("overwrite", df2, context=preview_context)
        updated = preview_repo.get_preview("overwrite")

        assert updated.equals(df2)
        assert not updated.equals(df1)


class TestPreviewRepositoryDataIntegrity:
    """Test data integrity and isolation."""

    def test_preview_data_not_modified_by_external_changes(
        self, test_dataframe: Any, preview_repo: Any, preview_context
    ) -> None:
        """Stored previews own their data independently of caller mutations."""
        df = test_dataframe.copy()
        preview_repo.set_preview("isolation_test", df, context=preview_context)

        # Modify original DataFrame
        df.loc[0, "a"] = 999

        # Stored previews retain their owned copy.
        stored = preview_repo.get_preview("isolation_test")
        assert stored.loc[0, "a"] == 1

        # Explicit caller copies preserve the same ownership contract:
        df2 = test_dataframe.copy()
        preview_repo.set_preview("safe_test", df2.copy(), context=preview_context)  # Store a copy
        df2.loc[0, "a"] = 777

        # This preview is unaffected because we stored a copy
        safe_stored = preview_repo.get_preview("safe_test")
        assert safe_stored.loc[0, "a"] == 1  # Original value preserved

    def test_dataframe_types_preserved(self, preview_repo: Any, preview_context) -> None:
        """Test DataFrame column types are preserved."""
        df = pd.DataFrame(
            {"int_col": [1, 2, 3], "float_col": [1.1, 2.2, 3.3], "str_col": ["a", "b", "c"]}
        )

        preview_repo.set_preview("types_test", df, context=preview_context)
        result = preview_repo.get_preview("types_test")

        assert result["int_col"].dtype == df["int_col"].dtype
        assert result["float_col"].dtype == df["float_col"].dtype
        assert result["str_col"].dtype == df["str_col"].dtype

    def test_empty_dataframe_handled_correctly(self, preview_repo: Any, preview_context) -> None:
        """Test empty DataFrame can be stored and retrieved."""
        empty_df = pd.DataFrame()

        preview_repo.set_preview("empty", empty_df, context=preview_context)
        result = preview_repo.get_preview("empty")

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


class TestPreviewRepositoryNamingConventions:
    """Test naming convention enforcement."""

    def test_operation_names_with_special_chars(
        self, test_dataframe: Any, preview_repo: Any, preview_context
    ) -> None:
        """Test operation names with underscores and hyphens work correctly."""
        names = [
            "outlier_removal",
            "seeds-reduction",
            "mixer_sum_operation",
            "preprocessing.step.1",
        ]

        for name in names:
            preview_repo.set_preview(name, test_dataframe, context=preview_context)
            assert preview_repo.has_preview(name)
            assert preview_repo.get_preview(name) is not None

    def test_operation_names_are_case_sensitive(
        self, test_dataframe: Any, preview_repo: Any, preview_context
    ) -> None:
        """Test operation names are case-sensitive."""
        preview_repo.set_preview("MixerOp", test_dataframe, context=preview_context)

        assert preview_repo.has_preview("MixerOp")
        assert not preview_repo.has_preview("mixerop")
        assert not preview_repo.has_preview("MIXEROP")


class TestPreviewRepositorySessionIsolation:
    """Test isolation from non-preview session state."""

    def test_preview_keys_dont_collide_with_other_state(
        self, test_dataframe: Any, preview_repo: Any, preview_context
    ) -> None:
        """Test preview keys don't interfere with other session state.
        Note: PreviewRepository no longer uses st.session_state directly in memory mode.
        If it did, we'd mock st here. But validating it keeps its own dict is valuable.
        """
        # Set preview
        preview_repo.set_preview("operation", test_dataframe, context=preview_context)

        # It should be in repo
        assert preview_repo.has_preview("operation")
