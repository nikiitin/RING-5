"""Tests for gem5 entry processing, summaries, and Perl failures."""

from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from src.parsing.gem5.impl.strategies.gem5_parse_work import (
    Gem5ParseWork,
    VarsDictType,
)


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


class TestStr:
    """Tests for __str__ method."""

    def test_str_representation(self) -> None:
        work = Gem5ParseWork("path/to/stats.txt", cast(VarsDictType, {"var": Scalar()}))
        assert str(work) == "Gem5ParseWork(path/to/stats.txt)"


class TestProcessEntryTypeResolution:
    """Tests for _processEntryType type resolution branches."""

    def test_histogram_to_vector_resolution(self) -> None:
        """When target expects vector but Perl says histogram, resolve to vector."""
        vars_map = cast(VarsDictType, {"myvar": Vector()})
        work = Gem5ParseWork("f", vars_map)
        work._entryBuffer = {}

        result = work._processEntryType("Histogram", "myvar::0", "100", vars_map)
        assert result == "vector"

    def test_histogram_to_distribution_resolution(self) -> None:
        """When target expects distribution but Perl says histogram, resolve to distribution."""
        vars_map = cast(VarsDictType, {"myvar": Distribution()})
        work = Gem5ParseWork("f", vars_map)
        work._entryBuffer = {}

        result = work._processEntryType("Histogram", "myvar::0", "50", vars_map)
        assert result == "distribution"

    def test_histogram_to_histogram_resolution(self) -> None:
        """When target expects histogram and Perl says histogram."""
        vars_map = cast(VarsDictType, {"myvar": Histogram()})
        work = Gem5ParseWork("f", vars_map)
        work._entryBuffer = {}

        result = work._processEntryType("Histogram", "myvar::0", "50", vars_map)
        assert result == "histogram"

    def test_vector_to_distribution_resolution(self) -> None:
        """When target expects distribution but Perl says vector, resolve to distribution."""
        vars_map = cast(VarsDictType, {"myvar": Distribution()})
        work = Gem5ParseWork("f", vars_map)
        work._entryBuffer = {}

        result = work._processEntryType("Vector", "myvar::samples", "100", vars_map)
        assert result == "distribution"

    def test_vector_to_histogram_resolution(self) -> None:
        """When target expects histogram but Perl says vector, resolve to histogram."""
        vars_map = cast(VarsDictType, {"myvar": Histogram()})
        work = Gem5ParseWork("f", vars_map)
        work._entryBuffer = {}

        result = work._processEntryType("Vector", "myvar::samples", "100", vars_map)
        assert result == "histogram"

    def test_unknown_variable_returns_none(self) -> None:
        """When baseID not in varsToParse, should return None."""
        vars_map = cast(VarsDictType, {"known": Vector()})
        work = Gem5ParseWork("f", vars_map)
        work._entryBuffer = {}

        result = work._processEntryType("Vector", "unknown::0", "10", vars_map)
        assert result is None

    def test_entry_buffered_after_processing(self) -> None:
        """Entry should be buffered after type resolution."""
        vars_map = cast(VarsDictType, {"myvar": Vector()})
        work = Gem5ParseWork("f", vars_map)
        work._entryBuffer = {}

        work._processEntryType("Vector", "myvar::key1", "42", vars_map)
        assert "myvar" in work._entryBuffer
        assert work._entryBuffer["myvar"]["key1"] == ["42"]


class TestProcessLineEdgeCases:
    """Tests for _processLine edge cases."""

    def test_configuration_type(self) -> None:
        """Configuration type should set content directly."""
        vars_map = cast(VarsDictType, {"config_var": Configuration()})
        work = Gem5ParseWork("f", vars_map)

        work._processLine("Configuration/config_var/my_benchmark", vars_map)
        assert vars_map["config_var"].content == "my_benchmark"

    @pytest.mark.parametrize("wire_type", ["WeirdType", "summary"])
    def test_unknown_type_raises(self, wire_type: str) -> None:
        """Unknown type in Perl output should raise RuntimeError."""
        vars_map = cast(VarsDictType, {"var": Scalar()})
        work = Gem5ParseWork("f", vars_map)

        with pytest.raises(RuntimeError, match="Unknown variable type"):
            work._processLine(f"{wire_type}/var/123", vars_map)

    def test_scalar_unknown_variable_skipped(self) -> None:
        """Scalar line with unknown variable ID should be skipped."""
        vars_map = cast(VarsDictType, {"known": Scalar()})
        work = Gem5ParseWork("f", vars_map)

        # Should not crash — unknown variable is skipped
        work._processLine("scalar/unknown_var/100", vars_map)
        assert vars_map["known"].content is None

    def test_entry_type_unknown_variable_skipped(self) -> None:
        """Entry type with unknown baseID should be skipped silently."""
        vars_map = cast(VarsDictType, {"known": Vector()})
        work = Gem5ParseWork("f", vars_map)
        work._entryBuffer = {}

        # Should not crash
        work._processLine("vector/unknown_var::0/10", vars_map)


class TestRunPerlScriptErrors:
    """Tests for _runPerlScript error handling."""

    @patch("src.core.common.utils.checkFileExistsOrException")
    def test_empty_variable_map_is_rejected(self, mock_check: MagicMock) -> None:
        work = Gem5ParseWork("stats.txt", cast(VarsDictType, {"var": Scalar()}))
        work._varsToParse.clear()

        with pytest.raises(RuntimeError, match="No variable filters"):
            work._runPerlScript()

    @patch("src.parsing.gem5.impl.strategies.gem5_parse_work.get_worker_pool")
    @patch("src.core.common.utils.checkFileExistsOrException")
    def test_timeout_error(self, mock_check: MagicMock, mock_pool_fn: MagicMock) -> None:
        """TimeoutError should be wrapped in RuntimeError."""
        mock_pool = MagicMock()
        mock_pool.parse_file.side_effect = TimeoutError("timed out")
        mock_pool_fn.return_value = mock_pool

        work = Gem5ParseWork("stats.txt", cast(VarsDictType, {"var": Scalar()}))

        with pytest.raises(RuntimeError, match="Parser timeout"):
            work._runPerlScript()

    @patch("src.parsing.gem5.impl.strategies.gem5_parse_work.get_worker_pool")
    @patch("src.core.common.utils.checkFileExistsOrException")
    def test_generic_exception(self, mock_check: MagicMock, mock_pool_fn: MagicMock) -> None:
        """Generic exception should be wrapped in RuntimeError."""
        mock_pool = MagicMock()
        mock_pool.parse_file.side_effect = OSError("connection failed")
        mock_pool_fn.return_value = mock_pool

        work = Gem5ParseWork("stats.txt", cast(VarsDictType, {"var": Scalar()}))

        with pytest.raises(RuntimeError, match="Worker pool parse failed"):
            work._runPerlScript()

    @patch("src.parsing.gem5.impl.strategies.gem5_parse_work.get_worker_pool")
    @patch("src.core.common.utils.checkFileExistsOrException")
    def test_unsafe_key_fails_visibly(self, mock_check: MagicMock, mock_pool_fn: MagicMock) -> None:
        """An unsafe requested key must not produce silently partial output."""
        mock_pool = MagicMock()
        mock_pool.parse_file.return_value = []
        mock_pool_fn.return_value = mock_pool

        # Create a var with a key starting with '-' (flag injection)
        vars_map = cast(VarsDictType, {"-dangerous_key": Scalar(), "safe_key": Scalar()})
        work = Gem5ParseWork("stats.txt", vars_map)

        with pytest.raises(RuntimeError, match="Unsafe parser stat filter"):
            work._runPerlScript()

        mock_pool.parse_file.assert_not_called()
