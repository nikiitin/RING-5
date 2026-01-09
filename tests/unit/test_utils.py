"""
Comprehensive tests for utility functions.
"""

import enum
import os
import tempfile

import pytest

import src.utils.utils as utils


class TestGetElementValue:
    """Tests for getElementValue function."""

    def test_get_existing_key(self):
        """Test getting an existing key."""
        data = {"name": "test", "value": 42}
        assert utils.getElementValue(data, "name") == "test"
        assert utils.getElementValue(data, "value") == 42

    def test_get_missing_key_raises(self):
        """Test that missing key raises exception."""
        data = {"name": "test"}
        with pytest.raises(Exception, match="Key not found"):
            utils.getElementValue(data, "missing")

    def test_get_none_value_optional(self):
        """Test getting None value with optional=True."""
        data = {"name": None}
        result = utils.getElementValue(data, "name", optional=True)
        assert result is None

    def test_get_none_value_not_optional(self):
        """Test getting None value with optional=False raises."""
        data = {"name": None}
        with pytest.raises(Exception, match="not optional"):
            utils.getElementValue(data, "name", optional=False)

    def test_get_list_value(self):
        """Test getting a list value."""
        data = {"items": [1, 2, 3]}
        result = utils.getElementValue(data, "items")
        assert result == [1, 2, 3]

    def test_get_dict_value(self):
        """Test getting a dict value."""
        data = {"nested": {"a": 1, "b": 2}}
        result = utils.getElementValue(data, "nested")
        assert result == {"a": 1, "b": 2}


class TestCheckElementExists:
    """Tests for checkElementExists function."""

    def test_existing_key_passes(self):
        """Test that existing key doesn't raise."""
        data = {"key": "value"}
        utils.checkElementExists(data, "key")  # Should not raise

    def test_missing_key_raises(self):
        """Test that missing key raises."""
        data = {"key": "value"}
        with pytest.raises(Exception, match="Key not found"):
            utils.checkElementExists(data, "missing")


class TestCheckElementExistNoException:
    """Tests for checkElementExistNoException function."""

    def test_existing_key_returns_true(self):
        """Test existing key returns True."""
        data = {"key": "value"}
        assert utils.checkElementExistNoException(data, "key") is True

    def test_missing_key_returns_false(self):
        """Test missing key returns False."""
        data = {"key": "value"}
        assert utils.checkElementExistNoException(data, "missing") is False


class TestEnumFunctions:
    """Tests for enum-related functions."""

    class SampleEnum(enum.Enum):
        """Sample enum for testing (not a test class)."""

        OPTION_A = "option_a"
        OPTION_B = "option_b"
        OPTION_C = "option_c"

    def test_check_enum_exists_true(self):
        """Test finding existing enum member."""
        data = {"OPTION_A": "value"}
        assert utils.checkEnumExistsNoException(data, self.SampleEnum) is True

    def test_check_enum_exists_false(self):
        """Test not finding enum member."""
        data = {"OTHER": "value"}
        assert utils.checkEnumExistsNoException(data, self.SampleEnum) is False

    def test_get_enum_value_found(self):
        """Test getting enum value when found."""
        data = {"option_a": "value"}
        result = utils.getEnumValue(data, self.SampleEnum)
        assert result == "option_a"

    def test_get_enum_value_not_found(self):
        """Test getting enum value when not found."""
        data = {"other": "value"}
        result = utils.getEnumValue(data, self.SampleEnum)
        assert result is None


class TestFileOperations:
    """Tests for file operation functions."""

    def test_check_file_exists_true(self):
        """Test checkFileExists with existing file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
        try:
            assert utils.checkFileExists(temp_path) is True
        finally:
            os.unlink(temp_path)

    def test_check_file_exists_false(self):
        """Test checkFileExists with non-existing file."""
        assert utils.checkFileExists("/nonexistent/path/file.txt") is False

    def test_check_file_exists_or_exception_existing(self):
        """Test checkFileExistsOrException with existing file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
        try:
            utils.checkFileExistsOrException(temp_path)  # Should not raise
        finally:
            os.unlink(temp_path)

    def test_check_file_exists_or_exception_missing(self):
        """Test checkFileExistsOrException with missing file."""
        with pytest.raises(Exception, match="File does not exist"):
            utils.checkFileExistsOrException("/nonexistent/path/file.txt")

    def test_check_files_exist_all_present(self):
        """Test checkFilesExistOrException with all files present."""
        files = []
        try:
            for _ in range(3):
                f = tempfile.NamedTemporaryFile(delete=False)
                files.append(f.name)
                f.close()
            utils.checkFilesExistOrException(files)  # Should not raise
        finally:
            for f in files:
                os.unlink(f)

    def test_check_files_exist_one_missing(self):
        """Test checkFilesExistOrException with one missing file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
        try:
            with pytest.raises(Exception, match="File does not exist"):
                utils.checkFilesExistOrException([temp_path, "/nonexistent"])
        finally:
            os.unlink(temp_path)


class TestDirectoryOperations:
    """Tests for directory operation functions."""

    def test_check_dir_exists_true(self):
        """Test checkDirExists with existing directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            assert utils.checkDirExists(temp_dir) is True

    def test_check_dir_exists_false(self):
        """Test checkDirExists with non-existing directory."""
        assert utils.checkDirExists("/nonexistent/directory") is False

    def test_check_dir_exists_or_exception_existing(self):
        """Test checkDirExistsOrException with existing directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            utils.checkDirExistsOrException(temp_dir)  # Should not raise

    def test_check_dir_exists_or_exception_missing(self):
        """Test checkDirExistsOrException with missing directory."""
        with pytest.raises(Exception, match="Directory does not exist"):
            utils.checkDirExistsOrException("/nonexistent/directory")

    def test_create_dir_new(self):
        """Test creating a new directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = os.path.join(temp_dir, "new_subdir")
            utils.createDir(new_dir)
            assert os.path.isdir(new_dir)

    def test_create_dir_existing(self, capsys):
        """Test creating an existing directory prints message."""
        with tempfile.TemporaryDirectory() as temp_dir:
            utils.createDir(temp_dir)  # Already exists
            captured = capsys.readouterr()
            assert "already exists" in captured.out


class TestTempFile:
    """Tests for temporary file functions."""

    def test_create_tmp_file(self):
        """Test creating a temporary file."""
        temp_path = utils.createTmpFile()
        try:
            assert os.path.exists(temp_path)
            assert os.path.isfile(temp_path)
        finally:
            os.unlink(temp_path)





class TestVarTypeCheck:
    """Tests for checkVarType function."""

    def test_correct_type_string(self):
        """Test correct string type."""
        utils.checkVarType("hello", str)  # Should not raise

    def test_correct_type_int(self):
        """Test correct int type."""
        utils.checkVarType(42, int)  # Should not raise

    def test_correct_type_list(self):
        """Test correct list type."""
        utils.checkVarType([1, 2, 3], list)  # Should not raise

    def test_correct_type_dict(self):
        """Test correct dict type."""
        utils.checkVarType({"a": 1}, dict)  # Should not raise

    def test_wrong_type_raises(self):
        """Test wrong type raises exception."""
        with pytest.raises(Exception, match="not of type"):
            utils.checkVarType("hello", int)

    def test_none_vs_any_type(self):
        """Test None value check."""
        with pytest.raises(Exception, match="not of type"):
            utils.checkVarType(None, str)
