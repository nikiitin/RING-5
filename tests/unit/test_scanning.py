from unittest.mock import MagicMock, patch

import pytest

from src.parsers.workers.gem5_scan_work import Gem5ScanWork
from src.parsers.workers.pool import ScanWorkPool


def test_stats_scan_work_success():
    work = Gem5ScanWork("test_file.txt")

    mock_vars = [{"name": "var1", "type": "scalar"}, {"name": "var2", "type": "vector"}]

    with patch("src.parsers.scanner.Gem5StatsScanner.get_instance") as mock_scanner_cls:
        mock_instance = MagicMock()
        mock_scanner_cls.return_value = mock_instance
        mock_instance.scan_file.return_value = mock_vars

        result = work()

        mock_instance.scan_file.assert_called_once()
        assert len(result) == 2
        assert result[0]["name"] == "var1"


def test_stats_scan_work_failure():
    work = Gem5ScanWork("test_file.txt")

    with patch("src.parsers.scanner.Gem5StatsScanner.get_instance") as mock_scanner_cls:
        mock_instance = MagicMock()
        mock_scanner_cls.return_value = mock_instance
        mock_instance.scan_file.side_effect = Exception("Scan error")

        # Should handle exception and return empty
        result = work()
        assert result == []


# --- ScanWorkPool Tests ---
# Note: Testing singletons and pools can be tricky. We'll mock the internal WorkPool.


@pytest.fixture
def clean_pool_singleton():
    ScanWorkPool._singleton = None
    yield
    ScanWorkPool._singleton = None


def test_scan_work_pool_singleton(clean_pool_singleton):
    pool1 = ScanWorkPool.get_instance()
    pool2 = ScanWorkPool.get_instance()
    assert pool1 is pool2


def test_scan_work_pool_add_work(clean_pool_singleton):
    with patch("src.core.multiprocessing.pool.WorkPool.get_instance") as mock_wp_cls:
        mock_internal_pool = MagicMock()
        mock_wp_cls.return_value = mock_internal_pool

        scan_pool = ScanWorkPool.get_instance()
        work = Gem5ScanWork("f")

        scan_pool.add_work(work)

        mock_internal_pool.submit.assert_called_once_with(work)
        assert len(scan_pool._futures) == 1


def test_scan_work_pool_get_results(clean_pool_singleton):
    with patch("src.core.multiprocessing.pool.WorkPool.get_instance"):
        scan_pool = ScanWorkPool.get_instance()

        # Mock futures
        mock_future1 = MagicMock()
        mock_future1.result.return_value = "res1"

        mock_future2 = MagicMock()
        mock_future2.result.return_value = "res2"

        scan_pool._futures = [mock_future1, mock_future2]

        results = scan_pool.get_results()

        assert results == ["res1", "res2"]
        # Futures should be cleared
        assert len(scan_pool._futures) == 0
