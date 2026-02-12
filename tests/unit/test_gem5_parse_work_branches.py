"""
Additional tests for Gem5ParseWork targeting uncovered branches.

Covers:
- __str__ (L52)
- _processEntryType: histogram→vector, vector→histogram resolution (L138-154)
- _processSummary: standalone summary, entry-style summary (L156-185)
- _processLine: configuration type, unknown type (L215, L222)
- _runPerlScript: timeout error, general error (L297-298, L313-318)
- _processLine: unknown variable skip for entry types
"""

from unittest.mock import MagicMock, patch

import pytest

from src.core.parsing.gem5.impl.strategies.gem5_parse_work import Gem5ParseWork


class Scalar:
    def __init__(self) -> None:
        self.content = None


class Vector:
    def __init__(self) -> None:
        self.content = None
        self.entries: list = []


class Distribution:
    def __init__(self) -> None:
        self.content = None
        self.entries: list = []


class Histogram:
    def __init__(self) -> None:
        self.content = None
        self.entries: list = []


class Configuration:
    def __init__(self) -> None:
        self.content = None
        self.onEmpty = None


class Summary:
    def __init__(self) -> None:
        self.content = None


class TestStr:
    """Tests for __str__ method."""

    def test_str_representation(self) -> None:
        work = Gem5ParseWork("path/to/stats.txt", {"var": Scalar()})
        assert str(work) == "Gem5ParseWork(path/to/stats.txt)"


class TestProcessEntryTypeResolution:
    """Tests for _processEntryType type resolution branches."""

    def test_histogram_to_vector_resolution(self) -> None:
        """When target expects vector but Perl says histogram, resolve to vector."""
        vars_map = {"myvar": Vector()}
        work = Gem5ParseWork("f", vars_map)
        work._entryBuffer = {}

        result = work._processEntryType("Histogram", "myvar::0", "100", vars_map)
        assert result == "vector"

    def test_histogram_to_distribution_resolution(self) -> None:
        """When target expects distribution but Perl says histogram, resolve to distribution."""
        vars_map = {"myvar": Distribution()}
        work = Gem5ParseWork("f", vars_map)
        work._entryBuffer = {}

        result = work._processEntryType("Histogram", "myvar::0", "50", vars_map)
        assert result == "distribution"

    def test_histogram_to_histogram_resolution(self) -> None:
        """When target expects histogram and Perl says histogram."""
        vars_map = {"myvar": Histogram()}
        work = Gem5ParseWork("f", vars_map)
        work._entryBuffer = {}

        result = work._processEntryType("Histogram", "myvar::0", "50", vars_map)
        assert result == "histogram"

    def test_vector_to_distribution_resolution(self) -> None:
        """When target expects distribution but Perl says vector, resolve to distribution."""
        vars_map = {"myvar": Distribution()}
        work = Gem5ParseWork("f", vars_map)
        work._entryBuffer = {}

        result = work._processEntryType("Vector", "myvar::samples", "100", vars_map)
        assert result == "distribution"

    def test_vector_to_histogram_resolution(self) -> None:
        """When target expects histogram but Perl says vector, resolve to histogram."""
        vars_map = {"myvar": Histogram()}
        work = Gem5ParseWork("f", vars_map)
        work._entryBuffer = {}

        result = work._processEntryType("Vector", "myvar::samples", "100", vars_map)
        assert result == "histogram"

    def test_unknown_variable_returns_none(self) -> None:
        """When baseID not in varsToParse, should return None."""
        vars_map = {"known": Vector()}
        work = Gem5ParseWork("f", vars_map)
        work._entryBuffer = {}

        result = work._processEntryType("Vector", "unknown::0", "10", vars_map)
        assert result is None

    def test_entry_buffered_after_processing(self) -> None:
        """Entry should be buffered after type resolution."""
        vars_map = {"myvar": Vector()}
        work = Gem5ParseWork("f", vars_map)
        work._entryBuffer = {}

        work._processEntryType("Vector", "myvar::key1", "42", vars_map)
        assert "myvar" in work._entryBuffer
        assert work._entryBuffer["myvar"]["key1"] == ["42"]


class TestProcessSummary:
    """Tests for _processSummary method."""

    def test_standalone_summary(self) -> None:
        """Standalone summary via __get_summary should populate content."""
        vars_map = {"myvar__get_summary": Summary()}
        work = Gem5ParseWork("f", vars_map)

        work._processSummary("myvar", "42.5", vars_map)
        assert vars_map["myvar__get_summary"].content == "42.5"

    def test_entry_style_summary(self) -> None:
        """Entry-style summary (e.g., var::total) should be buffered."""
        vars_map = {"myvar": Distribution()}
        work = Gem5ParseWork("f", vars_map)
        work._entryBuffer = {}

        work._processSummary("myvar::total", "999", vars_map)
        assert work._entryBuffer["myvar"]["total"] == ["999"]

    def test_summary_unknown_var_no_crash(self) -> None:
        """Summary for unknown variable should not crash."""
        vars_map = {"other": Scalar()}
        work = Gem5ParseWork("f", vars_map)
        work._entryBuffer = {}

        # Should not raise
        work._processSummary("unknown_var", "123", vars_map)

    def test_summary_entry_style_non_entry_type(self) -> None:
        """Summary with :: but target is scalar (not entry type) should try standalone."""
        vars_map = {"myvar": Scalar(), "myvar__get_summary": Summary()}
        work = Gem5ParseWork("f", vars_map)
        work._entryBuffer = {}

        work._processSummary("myvar::total", "999", vars_map)
        # Scalar is not an entry type, so it should fall through to standalone check


class TestProcessLineEdgeCases:
    """Tests for _processLine edge cases."""

    def test_configuration_type(self) -> None:
        """Configuration type should set content directly."""
        vars_map = {"config_var": Configuration()}
        work = Gem5ParseWork("f", vars_map)

        work._processLine("Configuration/config_var/my_benchmark", vars_map)
        assert vars_map["config_var"].content == "my_benchmark"

    def test_unknown_type_raises(self) -> None:
        """Unknown type in Perl output should raise RuntimeError."""
        vars_map = {"var": Scalar()}
        work = Gem5ParseWork("f", vars_map)

        with pytest.raises(RuntimeError, match="Unknown variable type"):
            work._processLine("WeirdType/var/123", vars_map)

    def test_scalar_unknown_variable_skipped(self) -> None:
        """Scalar line with unknown variable ID should be skipped."""
        vars_map = {"known": Scalar()}
        work = Gem5ParseWork("f", vars_map)

        # Should not crash — unknown variable is skipped
        work._processLine("scalar/unknown_var/100", vars_map)
        assert vars_map["known"].content is None

    def test_summary_line(self) -> None:
        """Summary type line should be dispatched to _processSummary."""
        vars_map = {"myvar__get_summary": Summary()}
        work = Gem5ParseWork("f", vars_map)

        work._processLine("Summary/myvar/42", vars_map)
        assert vars_map["myvar__get_summary"].content == "42"

    def test_entry_type_unknown_variable_skipped(self) -> None:
        """Entry type with unknown baseID should be skipped silently."""
        vars_map = {"known": Vector()}
        work = Gem5ParseWork("f", vars_map)
        work._entryBuffer = {}

        # Should not crash
        work._processLine("vector/unknown_var::0/10", vars_map)


class TestRunPerlScriptErrors:
    """Tests for _runPerlScript error handling."""

    @patch("src.core.parsing.gem5.impl.strategies.gem5_parse_work.get_worker_pool")
    @patch("src.core.common.utils.checkFileExistsOrException")
    def test_timeout_error(self, mock_check: MagicMock, mock_pool_fn: MagicMock) -> None:
        """TimeoutError should be wrapped in RuntimeError."""
        mock_pool = MagicMock()
        mock_pool.parse_file.side_effect = TimeoutError("timed out")
        mock_pool_fn.return_value = mock_pool

        work = Gem5ParseWork("stats.txt", {"var": Scalar()})

        with pytest.raises(RuntimeError, match="Parser timeout"):
            work._runPerlScript()

    @patch("src.core.parsing.gem5.impl.strategies.gem5_parse_work.get_worker_pool")
    @patch("src.core.common.utils.checkFileExistsOrException")
    def test_generic_exception(self, mock_check: MagicMock, mock_pool_fn: MagicMock) -> None:
        """Generic exception should be wrapped in RuntimeError."""
        mock_pool = MagicMock()
        mock_pool.parse_file.side_effect = OSError("connection failed")
        mock_pool_fn.return_value = mock_pool

        work = Gem5ParseWork("stats.txt", {"var": Scalar()})

        with pytest.raises(RuntimeError, match="Worker pool parse failed"):
            work._runPerlScript()

    @patch("src.core.parsing.gem5.impl.strategies.gem5_parse_work.get_worker_pool")
    @patch("src.core.common.utils.checkFileExistsOrException")
    def test_unsafe_key_skipped(self, mock_check: MagicMock, mock_pool_fn: MagicMock) -> None:
        """Keys starting with '-' should be skipped for safety."""
        mock_pool = MagicMock()
        mock_pool.parse_file.return_value = []
        mock_pool_fn.return_value = mock_pool

        # Create a var with a key starting with '-' (flag injection)
        vars_map = {"-dangerous_key": Scalar(), "safe_key": Scalar()}
        work = Gem5ParseWork("stats.txt", vars_map)

        work._runPerlScript()

        # pool.parse_file should be called with safe_keys only
        call_args = mock_pool.parse_file.call_args
        keys_passed = call_args[0][1]  # second positional arg
        assert "-dangerous_key" not in keys_passed
        assert "safe_key" in keys_passed
