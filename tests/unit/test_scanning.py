from unittest.mock import MagicMock, patch

from src.parsing.gem5.impl.scanning.gem5_scan_work import Gem5ScanWork


def test_stats_scan_work_success() -> None:
    work = Gem5ScanWork("test_file.txt")

    from src.core.models import ScannedVariable

    mock_vars = [
        ScannedVariable(name="var1", type="scalar"),
        ScannedVariable(name="var2", type="vector"),
    ]

    with patch(
        "src.parsing.gem5.impl.scanning.scanner.Gem5StatsScanner.get_instance"
    ) as mock_scanner_cls:
        mock_instance = MagicMock()
        mock_scanner_cls.return_value = mock_instance
        mock_instance.scan_file.return_value = mock_vars

        result = work()

        mock_instance.scan_file.assert_called_once()
        assert len(result.variables) == 2
        assert result.variables[0].name == "var1"
        assert result.ok


def test_stats_scan_work_failure() -> None:
    work = Gem5ScanWork("test_file.txt")

    with patch(
        "src.parsing.gem5.impl.scanning.scanner.Gem5StatsScanner.get_instance"
    ) as mock_scanner_cls:
        mock_instance = MagicMock()
        mock_scanner_cls.return_value = mock_instance
        mock_instance.scan_file.side_effect = RuntimeError("Scan error")

        # A fatal scan failure is reported as a failed ScanFileResult,
        # never masked as an empty success.
        result = work()
        assert not result.ok
        assert result.variables == []
        assert "Scan error" in (result.error or "")


def test_stats_scan_work_reports_os_error() -> None:
    work = Gem5ScanWork("test_file.txt")

    with patch(
        "src.parsing.gem5.impl.scanning.scanner.Gem5StatsScanner.get_instance"
    ) as mock_scanner_cls:
        mock_instance = MagicMock()
        mock_scanner_cls.return_value = mock_instance
        mock_instance.scan_file.side_effect = PermissionError("Permission denied")

        result = work()

        assert not result.ok
        assert result.error == "Permission denied"
