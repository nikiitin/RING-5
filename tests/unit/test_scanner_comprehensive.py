"""
Comprehensive tests for Gem5StatsScanner.

Following Rule 004 (QA Testing Mastery):
- Fixture-first design with tmp_path
- AAA pattern (Arrange-Act-Assert)
- Monkeypatch for subprocess and path mocking
- Testing all error paths and edge cases
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.core.parsing.models import ScannedVariable
from src.core.parsing.scanner import Gem5StatsScanner


@pytest.fixture
def mock_perl_available(monkeypatch):
    """Mock Perl as available in PATH."""
    monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/perl" if x == "perl" else None)


@pytest.fixture
def mock_scanner_script_exists(monkeypatch):
    """Mock scanner script as existing."""

    def mock_exists(self):
        return True

    monkeypatch.setattr(Path, "exists", mock_exists)


@pytest.fixture
def clean_scanner():
    """Reset scanner singleton before each test."""
    Gem5StatsScanner._instance = None
    yield
    Gem5StatsScanner._instance = None


class TestScannerInitialization:
    """Test Gem5StatsScanner initialization."""

    def test_init_without_perl_raises(self, monkeypatch, clean_scanner):
        # Arrange - Perl not available
        monkeypatch.setattr("shutil.which", lambda x: None)

        # Act & Assert
        with pytest.raises(RuntimeError, match="Perl executable not found"):
            Gem5StatsScanner()

    def test_init_without_scanner_script_raises(
        self, mock_perl_available, monkeypatch, clean_scanner
    ):
        # Arrange - Script missing
        def mock_exists(self):
            return False

        monkeypatch.setattr(Path, "exists", mock_exists)

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="Scanner backend script missing"):
            Gem5StatsScanner()

    def test_init_with_valid_environment(
        self, mock_perl_available, mock_scanner_script_exists, clean_scanner
    ):
        # Arrange & Act
        scanner = Gem5StatsScanner()

        # Assert
        assert scanner._perl_exe == "/usr/bin/perl"
        assert "statsScanner.pl" in str(scanner._script_path)

    def test_get_instance_returns_singleton(
        self, mock_perl_available, mock_scanner_script_exists, clean_scanner
    ):
        # Arrange & Act
        scanner1 = Gem5StatsScanner.get_instance()
        scanner2 = Gem5StatsScanner.get_instance()

        # Assert
        assert scanner1 is scanner2

    def test_get_instance_creates_on_first_call(
        self, mock_perl_available, mock_scanner_script_exists, clean_scanner
    ):
        # Arrange
        assert Gem5StatsScanner._instance is None

        # Act
        scanner = Gem5StatsScanner.get_instance()

        # Assert
        assert scanner is not None
        assert Gem5StatsScanner._instance is scanner

    def test_script_path_resolution(
        self, mock_perl_available, mock_scanner_script_exists, clean_scanner
    ):
        # Arrange & Act
        scanner = Gem5StatsScanner()

        # Assert
        assert scanner._script_path.name == "statsScanner.pl"
        assert "perl" in str(scanner._script_path.parent)


class TestScanFileScanFile:
    """Test Gem5StatsScanner.scan_file method."""

    @pytest.fixture
    def scanner(self, mock_perl_available, clean_scanner, monkeypatch):
        """Create a scanner instance with selective path mocking."""
        # Only mock the scanner script to exist, not all paths
        original_exists = Path.exists

        def selective_exists(self):
            if "statsScanner.pl" in str(self):
                return True
            return original_exists(self)

        monkeypatch.setattr(Path, "exists", selective_exists)
        return Gem5StatsScanner()

    def test_scan_file_with_missing_file_raises(self, scanner, tmp_path):
        # Arrange
        missing_file = tmp_path / "nonexistent.txt"
        # Real file doesn't exist, Python-level check should catch it

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="File not found"):
            scanner.scan_file(missing_file)

    def test_scan_file_calls_perl_subprocess(self, scanner, tmp_path, monkeypatch):
        # Arrange
        test_file = tmp_path / "stats.txt"
        test_file.write_text("dummy")

        mock_run = Mock(return_value=Mock(stdout="[]", stderr=""))
        monkeypatch.setattr("subprocess.run", mock_run)

        # Act
        scanner.scan_file(test_file)

        # Assert
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "/usr/bin/perl"
        assert "statsScanner.pl" in args[1]
        assert str(test_file) in args[2]

    def test_scan_file_returns_scanned_variables(self, scanner, tmp_path, monkeypatch):
        # Arrange
        test_file = tmp_path / "stats.txt"
        test_file.write_text("dummy")

        perl_output = json.dumps(
            [
                {"name": "simTicks", "type": "scalar"},
                {"name": "cpu.ipc", "type": "scalar"},
            ]
        )
        mock_run = Mock(return_value=Mock(stdout=perl_output, stderr=""))
        monkeypatch.setattr("subprocess.run", mock_run)

        # Act
        result = scanner.scan_file(test_file)

        # Assert
        assert len(result) == 2
        assert all(isinstance(v, ScannedVariable) for v in result)

    def test_scan_file_with_config_vars(self, scanner, tmp_path, monkeypatch):
        # Arrange
        test_file = tmp_path / "stats.txt"
        test_file.write_text("dummy")

        mock_run = Mock(return_value=Mock(stdout="[]", stderr=""))
        monkeypatch.setattr("subprocess.run", mock_run)

        # Act
        scanner.scan_file(test_file, config_vars=["benchmark", "seed"])

        # Assert
        args = mock_run.call_args[0][0]
        assert "benchmark,seed" in args

    def test_scan_file_with_empty_output(self, scanner, tmp_path, monkeypatch):
        # Arrange
        test_file = tmp_path / "stats.txt"
        test_file.write_text("dummy")

        mock_run = Mock(return_value=Mock(stdout="", stderr=""))
        monkeypatch.setattr("subprocess.run", mock_run)

        # Act
        result = scanner.scan_file(test_file)

        # Assert
        assert result == []

    def test_scan_file_with_whitespace_only_output(self, scanner, tmp_path, monkeypatch):
        # Arrange
        test_file = tmp_path / "stats.txt"
        test_file.write_text("dummy")

        mock_run = Mock(return_value=Mock(stdout="   \n  \t  ", stderr=""))
        monkeypatch.setattr("subprocess.run", mock_run)

        # Act
        result = scanner.scan_file(test_file)

        # Assert
        assert result == []

    def test_scan_file_with_timeout_raises(self, scanner, tmp_path, monkeypatch):
        # Arrange
        test_file = tmp_path / "stats.txt"
        test_file.write_text("dummy")

        mock_run = Mock(side_effect=subprocess.TimeoutExpired("perl", 60))
        monkeypatch.setattr("subprocess.run", mock_run)

        # Act & Assert
        with pytest.raises(RuntimeError, match="timed out"):
            scanner.scan_file(test_file)

    def test_scan_file_with_perl_error_raises(self, scanner, tmp_path, monkeypatch):
        # Arrange
        test_file = tmp_path / "stats.txt"
        test_file.write_text("dummy")

        mock_run = Mock(side_effect=subprocess.CalledProcessError(1, "perl", stderr="Perl error"))
        monkeypatch.setattr("subprocess.run", mock_run)

        # Act & Assert
        with pytest.raises(RuntimeError, match="Perl scanner failed"):
            scanner.scan_file(test_file)

    def test_scan_file_with_invalid_json_raises(self, scanner, tmp_path, monkeypatch):
        # Arrange
        test_file = tmp_path / "stats.txt"
        test_file.write_text("dummy")

        mock_run = Mock(return_value=Mock(stdout="not valid json{", stderr=""))
        monkeypatch.setattr("subprocess.run", mock_run)

        # Act & Assert
        with pytest.raises(RuntimeError, match="corrupt JSON"):
            scanner.scan_file(test_file)

    def test_scan_file_enforces_shell_false(self, scanner, tmp_path, monkeypatch):
        # Arrange
        test_file = tmp_path / "stats.txt"
        test_file.write_text("dummy")

        mock_run = Mock(return_value=Mock(stdout="[]", stderr=""))
        monkeypatch.setattr("subprocess.run", mock_run)

        # Act
        scanner.scan_file(test_file)

        # Assert
        assert mock_run.call_args[1]["shell"] is False

    def test_scan_file_enforces_timeout(self, scanner, tmp_path, monkeypatch):
        # Arrange
        test_file = tmp_path / "stats.txt"
        test_file.write_text("dummy")

        mock_run = Mock(return_value=Mock(stdout="[]", stderr=""))
        monkeypatch.setattr("subprocess.run", mock_run)

        # Act
        scanner.scan_file(test_file)

        # Assert
        assert mock_run.call_args[1]["timeout"] == 60


class TestScanEntriesForVariable:
    """Test scan_entries_for_variable method."""

    @pytest.fixture
    def scanner(self, mock_perl_available, mock_scanner_script_exists, clean_scanner):
        """Create a scanner instance."""
        return Gem5StatsScanner()

    def test_scan_entries_for_vector_variable(self, scanner, tmp_path, monkeypatch):
        # Arrange
        test_file = tmp_path / "stats.txt"
        test_file.write_text("dummy")

        perl_output = json.dumps(
            [
                {"name": "cpu_vec", "type": "vector", "entries": ["0", "1", "2"]},
                {"name": "other", "type": "scalar"},
            ]
        )
        mock_run = Mock(return_value=Mock(stdout=perl_output, stderr=""))
        monkeypatch.setattr("subprocess.run", mock_run)

        # Act
        result = scanner.scan_entries_for_variable(test_file, "cpu_vec")

        # Assert
        assert result == ["0", "1", "2"]

    def test_scan_entries_for_histogram_variable(self, scanner, tmp_path, monkeypatch):
        # Arrange
        test_file = tmp_path / "stats.txt"
        test_file.write_text("dummy")

        perl_output = json.dumps(
            [
                {"name": "hist", "type": "histogram", "entries": ["bucket0", "bucket1"]},
            ]
        )
        mock_run = Mock(return_value=Mock(stdout=perl_output, stderr=""))
        monkeypatch.setattr("subprocess.run", mock_run)

        # Act
        result = scanner.scan_entries_for_variable(test_file, "hist")

        # Assert
        assert result == ["bucket0", "bucket1"]

    def test_scan_entries_for_scalar_variable_returns_empty(self, scanner, tmp_path, monkeypatch):
        # Arrange
        test_file = tmp_path / "stats.txt"
        test_file.write_text("dummy")

        perl_output = json.dumps(
            [
                {"name": "scalar_var", "type": "scalar"},
            ]
        )
        mock_run = Mock(return_value=Mock(stdout=perl_output, stderr=""))
        monkeypatch.setattr("subprocess.run", mock_run)

        # Act
        result = scanner.scan_entries_for_variable(test_file, "scalar_var")

        # Assert
        assert result == []

    def test_scan_entries_for_missing_variable_returns_empty(self, scanner, tmp_path, monkeypatch):
        # Arrange
        test_file = tmp_path / "stats.txt"
        test_file.write_text("dummy")

        perl_output = json.dumps(
            [
                {"name": "other_var", "type": "vector", "entries": ["0"]},
            ]
        )
        mock_run = Mock(return_value=Mock(stdout=perl_output, stderr=""))
        monkeypatch.setattr("subprocess.run", mock_run)

        # Act
        result = scanner.scan_entries_for_variable(test_file, "missing_var")

        # Assert
        assert result == []

    def test_scan_entries_with_non_list_entries_returns_empty(self, scanner, tmp_path, monkeypatch):
        # Arrange
        test_file = tmp_path / "stats.txt"
        test_file.write_text("dummy")

        # Malformed entries (not a list)
        perl_output = json.dumps(
            [
                {"name": "bad_vec", "type": "vector", "entries": "not_a_list"},
            ]
        )
        mock_run = Mock(return_value=Mock(stdout=perl_output, stderr=""))
        monkeypatch.setattr("subprocess.run", mock_run)

        # Act
        result = scanner.scan_entries_for_variable(test_file, "bad_vec")

        # Assert
        assert result == []


class TestScanVectorEntriesAlias:
    """Test scan_vector_entries backward compatibility alias."""

    @pytest.fixture
    def scanner(self, mock_perl_available, mock_scanner_script_exists, clean_scanner):
        """Create a scanner instance."""
        return Gem5StatsScanner()

    def test_scan_vector_entries_delegates_to_scan_entries_for_variable(
        self, scanner, tmp_path, monkeypatch
    ):
        # Arrange
        test_file = tmp_path / "stats.txt"
        test_file.write_text("dummy")

        perl_output = json.dumps(
            [
                {"name": "vec", "type": "vector", "entries": ["a", "b"]},
            ]
        )
        mock_run = Mock(return_value=Mock(stdout=perl_output, stderr=""))
        monkeypatch.setattr("subprocess.run", mock_run)

        # Act
        result = scanner.scan_vector_entries(test_file, "vec")

        # Assert
        assert result == ["a", "b"]

    def test_scan_vector_entries_same_as_scan_entries_for_variable(
        self, scanner, tmp_path, monkeypatch
    ):
        # Arrange
        test_file = tmp_path / "stats.txt"
        test_file.write_text("dummy")

        perl_output = json.dumps(
            [
                {"name": "test_vec", "type": "vector", "entries": ["0", "1", "2"]},
            ]
        )
        mock_run = Mock(return_value=Mock(stdout=perl_output, stderr=""))
        monkeypatch.setattr("subprocess.run", mock_run)

        # Act
        result1 = scanner.scan_vector_entries(test_file, "test_vec")
        result2 = scanner.scan_entries_for_variable(test_file, "test_vec")

        # Assert
        assert result1 == result2
