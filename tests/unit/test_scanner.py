"""Unit tests for Gem5StatsScanner — Perl-based scanner wrapper."""

import json
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from src.core.models import ScannedVariable


class TestGem5StatsScanner:
    """Tests for Gem5StatsScanner singleton and scan_file."""

    @patch("src.core.parsing.scanner.shutil.which", return_value=None)
    def test_init_raises_without_perl(self, mock_which: MagicMock) -> None:
        """Raises RuntimeError if perl is not in PATH."""
        from src.core.parsing.scanner import Gem5StatsScanner

        # Reset singleton to force re-init
        Gem5StatsScanner._instance = None
        with pytest.raises(RuntimeError, match="Perl executable not found"):
            Gem5StatsScanner()

    @patch("src.core.parsing.scanner.shutil.which", return_value="/usr/bin/perl")
    def test_init_raises_without_script(self, mock_which: MagicMock, tmp_path: Path) -> None:
        """Raises FileNotFoundError if scanner script is missing."""
        from src.core.parsing.scanner import Gem5StatsScanner

        Gem5StatsScanner._instance = None
        with patch.object(Path, "exists", return_value=False):
            with pytest.raises(FileNotFoundError, match="Scanner backend script missing"):
                Gem5StatsScanner()

    @patch("src.core.parsing.scanner.shutil.which", return_value="/usr/bin/perl")
    def test_get_instance_creates_singleton(self, mock_which: MagicMock) -> None:
        """get_instance returns the same object."""
        from src.core.parsing.scanner import Gem5StatsScanner

        Gem5StatsScanner._instance = None
        with patch.object(Path, "exists", return_value=True):
            a = Gem5StatsScanner.get_instance()
            b = Gem5StatsScanner.get_instance()
            assert a is b
            Gem5StatsScanner._instance = None  # cleanup

    @patch("src.core.parsing.scanner.shutil.which", return_value="/usr/bin/perl")
    def test_scan_file_raises_on_missing_file(self, mock_which: MagicMock) -> None:
        """scan_file raises FileNotFoundError for nonexistent file."""
        from src.core.parsing.scanner import Gem5StatsScanner

        Gem5StatsScanner._instance = None
        with patch.object(Path, "exists", return_value=True):
            scanner = Gem5StatsScanner()
        with pytest.raises(FileNotFoundError, match="File not found"):
            scanner.scan_file(Path("/nonexistent/stats.txt"))
        Gem5StatsScanner._instance = None

    @patch("src.core.parsing.scanner.subprocess.run")
    @patch("src.core.parsing.scanner.shutil.which", return_value="/usr/bin/perl")
    def test_scan_file_parses_json(
        self, mock_which: MagicMock, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """scan_file parses JSON output into ScannedVariable list."""
        from src.core.parsing.scanner import Gem5StatsScanner

        Gem5StatsScanner._instance = None
        with patch.object(Path, "exists", return_value=True):
            scanner = Gem5StatsScanner()

        stats_file = tmp_path / "stats.txt"
        stats_file.write_text("dummy")

        mock_run.return_value = MagicMock(
            stdout=json.dumps(
                [
                    {"name": "simTicks", "type": "Scalar"},
                    {"name": "system.cpu.ipc", "type": "Scalar"},
                ]
            ),
            returncode=0,
        )

        results: List[ScannedVariable] = scanner.scan_file(stats_file)

        assert len(results) == 2
        assert results[0].name == "simTicks"
        Gem5StatsScanner._instance = None

    @patch("src.core.parsing.scanner.subprocess.run")
    @patch("src.core.parsing.scanner.shutil.which", return_value="/usr/bin/perl")
    def test_scan_file_empty_output(
        self, mock_which: MagicMock, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """scan_file returns empty list for empty stdout."""
        from src.core.parsing.scanner import Gem5StatsScanner

        Gem5StatsScanner._instance = None
        with patch.object(Path, "exists", return_value=True):
            scanner = Gem5StatsScanner()

        stats_file = tmp_path / "stats.txt"
        stats_file.write_text("dummy")
        mock_run.return_value = MagicMock(stdout="", returncode=0)

        assert scanner.scan_file(stats_file) == []
        Gem5StatsScanner._instance = None

    @patch("src.core.parsing.scanner.subprocess.run")
    @patch("src.core.parsing.scanner.shutil.which", return_value="/usr/bin/perl")
    def test_scan_file_handles_timeout(
        self, mock_which: MagicMock, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """scan_file wraps TimeoutExpired in RuntimeError."""
        import subprocess

        from src.core.parsing.scanner import Gem5StatsScanner

        Gem5StatsScanner._instance = None
        with patch.object(Path, "exists", return_value=True):
            scanner = Gem5StatsScanner()

        stats_file = tmp_path / "stats.txt"
        stats_file.write_text("dummy")
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="perl", timeout=60)

        with pytest.raises(RuntimeError, match="timed out"):
            scanner.scan_file(stats_file)
        Gem5StatsScanner._instance = None

    @patch("src.core.parsing.scanner.subprocess.run")
    @patch("src.core.parsing.scanner.shutil.which", return_value="/usr/bin/perl")
    def test_scan_file_handles_process_error(
        self, mock_which: MagicMock, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """scan_file wraps CalledProcessError in RuntimeError."""
        import subprocess

        from src.core.parsing.scanner import Gem5StatsScanner

        Gem5StatsScanner._instance = None
        with patch.object(Path, "exists", return_value=True):
            scanner = Gem5StatsScanner()

        stats_file = tmp_path / "stats.txt"
        stats_file.write_text("dummy")
        mock_run.side_effect = subprocess.CalledProcessError(1, "perl", stderr="parse error")

        with pytest.raises(RuntimeError, match="Perl scanner failed"):
            scanner.scan_file(stats_file)
        Gem5StatsScanner._instance = None

    @patch("src.core.parsing.scanner.subprocess.run")
    @patch("src.core.parsing.scanner.shutil.which", return_value="/usr/bin/perl")
    def test_scan_file_handles_bad_json(
        self, mock_which: MagicMock, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """scan_file wraps JSONDecodeError in RuntimeError."""
        from src.core.parsing.scanner import Gem5StatsScanner

        Gem5StatsScanner._instance = None
        with patch.object(Path, "exists", return_value=True):
            scanner = Gem5StatsScanner()

        stats_file = tmp_path / "stats.txt"
        stats_file.write_text("dummy")
        mock_run.return_value = MagicMock(stdout="not json!", returncode=0)

        with pytest.raises(RuntimeError, match="corrupt JSON"):
            scanner.scan_file(stats_file)
        Gem5StatsScanner._instance = None
