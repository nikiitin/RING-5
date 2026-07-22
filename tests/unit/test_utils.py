"""
Tests for utility functions in src.core.common.utils.

Only tests the alive (non-dead) functions:
- checkFileExistsOrException
- sanitize_log_value, sanitize_filename, validate_path_within
- sanitize_glob_pattern, normalize_user_path
"""

import os
import tempfile
from pathlib import Path

import pytest

import src.core.common.utils as utils


class TestCheckFileExistsOrException:
    """Tests for checkFileExistsOrException function."""

    def test_existing_file_passes(self) -> None:
        """Test that existing file doesn't raise."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
        try:
            utils.checkFileExistsOrException(temp_path)  # Should not raise
        finally:
            os.unlink(temp_path)

    def test_missing_file_raises(self) -> None:
        """Test that missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="File does not exist"):
            utils.checkFileExistsOrException("/nonexistent/path/file.txt")

    def test_directory_raises(self) -> None:
        """Test that a directory path raises FileNotFoundError."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(FileNotFoundError):
                utils.checkFileExistsOrException(temp_dir)


class TestSanitizeLogValue:
    """Tests for sanitize_log_value function."""

    def test_normal_string(self) -> None:
        assert utils.sanitize_log_value("hello world") == "hello world"

    def test_newlines_escaped(self) -> None:
        assert utils.sanitize_log_value("line1\nline2") == "line1\\nline2"

    def test_carriage_return_escaped(self) -> None:
        assert utils.sanitize_log_value("line1\rline2") == "line1\\rline2"

    def test_control_chars_removed(self) -> None:
        result = utils.sanitize_log_value("hello\x00world")
        assert "\x00" not in result

    def test_tab_preserved(self) -> None:
        assert utils.sanitize_log_value("col1\tcol2") == "col1\tcol2"

    def test_non_string_converted(self) -> None:
        assert utils.sanitize_log_value(42) == "42"


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    # [test->req~ring5.quality.input-security~1]

    def test_normal_filename(self) -> None:
        assert utils.sanitize_filename("data.csv") == "data.csv"

    def test_path_separators_replaced(self) -> None:
        assert "/" not in utils.sanitize_filename("path/to/file.csv")
        assert "\\" not in utils.sanitize_filename("path\\to\\file.csv")

    def test_traversal_replaced(self) -> None:
        assert ".." not in utils.sanitize_filename("../../etc/passwd")

    def test_leading_dots_stripped(self) -> None:
        assert not utils.sanitize_filename(".hidden").startswith(".")

    def test_empty_returns_unnamed(self) -> None:
        assert utils.sanitize_filename("") == "unnamed"


class TestValidatePathWithin:
    """Tests for validate_path_within function."""

    def test_valid_path(self) -> None:
        with tempfile.TemporaryDirectory() as base:
            child = Path(base) / "subdir" / "file.txt"
            result = utils.validate_path_within(child, Path(base))
            assert str(result).startswith(str(Path(base).resolve()))

    def test_traversal_raises(self) -> None:
        with tempfile.TemporaryDirectory() as base:
            evil = Path(base) / ".." / ".." / "etc" / "passwd"
            with pytest.raises(ValueError, match="Path traversal"):
                utils.validate_path_within(evil, Path(base))

    def test_sibling_raises(self) -> None:
        with tempfile.TemporaryDirectory() as base:
            sibling = Path(str(base) + "_evil") / "file.txt"
            with pytest.raises(ValueError, match="Path traversal"):
                utils.validate_path_within(sibling, Path(base))


class TestSanitizeGlobPattern:
    """Tests for sanitize_glob_pattern function."""

    def test_valid_pattern(self) -> None:
        assert utils.sanitize_glob_pattern("stats.txt") == "stats.txt"

    def test_wildcard_pattern(self) -> None:
        assert utils.sanitize_glob_pattern("*.txt") == "*.txt"

    def test_empty_returns_default(self) -> None:
        assert utils.sanitize_glob_pattern("") == "stats.txt"

    def test_traversal_returns_default(self) -> None:
        assert utils.sanitize_glob_pattern("../etc/passwd") == "stats.txt"

    def test_path_separator_returns_default(self) -> None:
        assert utils.sanitize_glob_pattern("path/pattern") == "stats.txt"

    def test_unsafe_chars_returns_default(self) -> None:
        assert utils.sanitize_glob_pattern("$(cmd)") == "stats.txt"


class TestNormalizeUserPath:
    """Tests for normalize_user_path function."""

    def test_normal_path(self) -> None:
        result = utils.normalize_user_path("/tmp/data")
        assert isinstance(result, Path)

    def test_empty_returns_default(self) -> None:
        result = utils.normalize_user_path("")
        assert isinstance(result, Path)

    def test_traversal_raises(self) -> None:
        with pytest.raises(ValueError, match="Path traversal"):
            utils.normalize_user_path("../../etc/passwd")

    def test_redundant_separators_collapsed(self) -> None:
        result = utils.normalize_user_path("/tmp//data///file")
        assert "//" not in str(result)


class TestValidateWebStatsPath:
    # [test->req~ring5.quality.input-security~1]

    def test_default_root_is_launch_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("RING5_ALLOWED_STATS_ROOTS", raising=False)
        monkeypatch.chdir(tmp_path)

        assert utils.allowed_web_stats_roots() == (tmp_path.resolve(),)

    def test_allowed_root_accepts_child(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # [test->req~ring5.ingestion.web-path-authorization~1]
        allowed = tmp_path / "allowed"
        child = allowed / "run"
        child.mkdir(parents=True)
        monkeypatch.setenv("RING5_ALLOWED_STATS_ROOTS", str(allowed))

        assert utils.validate_web_stats_path(str(allowed)) == allowed.resolve()
        assert utils.validate_web_stats_path(str(child)) == child.resolve()

    def test_outside_root_is_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        allowed = tmp_path / "allowed"
        outside = tmp_path / "outside"
        allowed.mkdir()
        outside.mkdir()
        monkeypatch.setenv("RING5_ALLOWED_STATS_ROOTS", str(allowed))

        with pytest.raises(ValueError, match="outside the allowed web roots"):
            utils.validate_web_stats_path(str(outside))

    def test_sibling_with_allowed_prefix_is_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        allowed = tmp_path / "allowed"
        sibling = tmp_path / "allowed-export"
        allowed.mkdir()
        sibling.mkdir()
        monkeypatch.setenv("RING5_ALLOWED_STATS_ROOTS", str(allowed))

        with pytest.raises(ValueError, match="outside the allowed web roots"):
            utils.validate_web_stats_path(str(sibling))

    def test_symlink_escape_is_rejected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        allowed = tmp_path / "allowed"
        outside = tmp_path / "outside"
        allowed.mkdir()
        outside.mkdir()
        link = allowed / "linked-outside"
        link.symlink_to(outside, target_is_directory=True)
        monkeypatch.setenv("RING5_ALLOWED_STATS_ROOTS", str(allowed))

        with pytest.raises(ValueError, match="outside the allowed web roots"):
            utils.validate_web_stats_path(str(link))
