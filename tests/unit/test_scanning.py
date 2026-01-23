import json
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.scanning.impl.multiprocessing.scanWorkPool import ScanWorkPool
from src.scanning.impl.multiprocessing.statsScanWork import StatsScanWork
from src.scanning.impl.multiprocessing.vectorScanWork import VectorScanWork

# --- StatsScanWork Tests ---


def test_stats_scan_work_success():
    work = StatsScanWork("test_file.txt", "perl", "script.pl")

    mock_vars = [{"name": "var1", "type": "scalar"}, {"name": "var2", "type": "vector"}]
    mock_output = json.dumps(mock_vars).encode("utf-8")

    with patch("subprocess.check_output", return_value=mock_output) as mock_run:
        result = work()

        mock_run.assert_called_once()
        assert len(result) == 2
        assert result[0]["name"] == "var1"


def test_stats_scan_work_failure():
    work = StatsScanWork("test_file.txt", "perl", "script.pl")

    with patch("subprocess.check_output", side_effect=Exception("Perl error")):
        result = work()
        assert result == []


# --- VectorScanWork Tests ---


def test_vector_scan_work_quick_skip():
    """Test that it returns empty list quickly if variable name not in file content"""
    work = VectorScanWork("test_file.txt", "my_vector", "perl", "script.pl")

    with patch("builtins.open", mock_open(read_data="other_var 10\n")):
        with patch("subprocess.check_output") as mock_run:
            result = work()

            # Should NOT call subprocess because "my_vector" is absent
            mock_run.assert_not_called()
            assert result == []


def test_vector_scan_work_success():
    work = VectorScanWork("test_file.txt", "my_vector", "perl", "script.pl")

    file_content = "my_vector::0 10\nmy_vector::1 20"
    mock_vars = [
        {"name": "my_vector", "entries": ["entry1", "entry2"]},
        {"name": "other_vector", "entries": ["x"]},
    ]
    mock_output = json.dumps(mock_vars).encode("utf-8")

    with patch("builtins.open", mock_open(read_data=file_content)):
        with patch("subprocess.check_output", return_value=mock_output) as mock_run:
            result = work()

            mock_run.assert_called_once()
            # Should only return entries for "my_vector"
            assert result == ["entry1", "entry2"]


def test_vector_scan_work_with_regex():
    """Test using a regex pattern clearly shows failure of simpler string check"""
    # Pattern includes regex syntax
    work = VectorScanWork("test_file.txt", r"system\.ruby\.l\d+_cntrl\d+", "perl", "script.pl")

    # File content matches the regex, but not the literal string
    file_content = "system.ruby.l0_cntrl0::entry 10"

    mock_vars = [{"name": "system.ruby.l0_cntrl0", "entries": ["entry"]}]
    mock_output = json.dumps(mock_vars).encode("utf-8")

    with patch("builtins.open", mock_open(read_data=file_content)):
        with patch("subprocess.check_output", return_value=mock_output) as mock_run:
            result = work()

            # With the fix, this should call subprocess because regex matches
            mock_run.assert_called_once()
            assert result == ["entry"]


# --- ScanWorkPool Tests ---
# Note: Testing singletons and pools can be tricky. We'll mock the internal WorkPool.


@pytest.fixture
def clean_pool_singleton():
    ScanWorkPool._singleton = None
    yield
    ScanWorkPool._singleton = None


def test_scan_work_pool_singleton(clean_pool_singleton):
    pool1 = ScanWorkPool.getInstance()
    pool2 = ScanWorkPool.getInstance()
    assert pool1 is pool2


def test_scan_work_pool_add_work(clean_pool_singleton):
    with patch("src.core.multiprocessing.pool.WorkPool.get_instance") as mock_wp_cls:
        mock_internal_pool = MagicMock()
        mock_wp_cls.return_value = mock_internal_pool

        scan_pool = ScanWorkPool.getInstance()
        work = StatsScanWork("f", "p", "s")

        scan_pool.addWork(work)

        mock_internal_pool.submit.assert_called_once_with(work)
        assert len(scan_pool._futures) == 1


def test_scan_work_pool_get_results(clean_pool_singleton):
    with patch("src.core.multiprocessing.pool.WorkPool.get_instance"):
        scan_pool = ScanWorkPool.getInstance()

        # Mock futures
        mock_future1 = MagicMock()
        mock_future1.result.return_value = "res1"

        mock_future2 = MagicMock()
        mock_future2.result.return_value = "res2"

        scan_pool._futures = [mock_future1, mock_future2]

        results = scan_pool.getResults()

        assert results == ["res1", "res2"]
        # Futures should be cleared
        assert len(scan_pool._futures) == 0
