from unittest.mock import MagicMock, patch

import pytest

from src.parsers.workers import Gem5ParseWork


class MockType:
    def __init__(self, type_name):
        self._type_name = type_name
        self.content = None
        self.entries = []
        self.onEmpty = None


# Mocking type(var).__name__ requires the class name to match
class Scalar:
    def __init__(self):
        self.content = None


class Vector:
    def __init__(self):
        self.content = None
        self.entries = []


class Distribution:
    def __init__(self):
        self.content = None
        self.entries = []


class Configuration:
    def __init__(self):
        self.content = None
        self.onEmpty = None


@pytest.fixture
def parser():
    vars_to_parse = {"scalar_var": Scalar(), "vector_var": Vector(), "dist_var": Distribution()}
    # Mock file existence check if needed, but __init__ doesn't check it (checkFile is in __call__)
    return Gem5ParseWork("dummy.txt", vars_to_parse)


def test_init_empty_vars():
    with pytest.raises(RuntimeError):
        Gem5ParseWork("file", {})


def test_process_line_scalar(parser):
    line = "scalar/scalar_var/123"
    parser._processLine(line, parser._varsToParse)
    assert parser._varsToParse["scalar_var"].content == "123"


def test_process_line_vector(parser):
    # Vector comes as Vector/ID::key/value
    line1 = "vector/vector_var::0/10"
    line2 = "vector/vector_var::1/20"

    # Initialize buffer (new unified approach)
    parser._entryBuffer = {}

    parser._processLine(line1, parser._varsToParse)
    parser._processLine(line2, parser._varsToParse)

    assert parser._entryBuffer["vector_var"]["0"] == ["10"]
    assert parser._entryBuffer["vector_var"]["1"] == ["20"]


def test_process_output_full_flow(parser):
    output = """scalar/scalar_var/99
vector/vector_var::0/100
vector/vector_var::0/101
distribution/dist_var::min/5
distribution/dist_var::max/15
"""
    # Verify vector_var entries are populated if needed?
    # Logic in _addBufferedVars copies from dict to var.content

    parsed = parser._processOutput(output, parser._varsToParse)

    assert parsed["scalar_var"].content == "99"

    # Check Vector
    # _processVector appends to list: _vectorDict[varID][varKey].append(varValue)
    # output had two values for vector_var::0 => ["100", "101"]
    v_content = parsed["vector_var"].content
    assert v_content["0"] == ["100", "101"]

    # Check Dist
    d_content = parsed["dist_var"].content
    assert d_content["min"] == ["5"]
    assert d_content["max"] == ["15"]


def test_validate_vars_missing_content(parser):
    # Scalar var content remains None
    # WITH FIX: Should default to "0" instead of raising error
    parser._validateVars(parser._varsToParse)
    assert parser._varsToParse["scalar_var"].content == "0"


def test_process_output_empty_returns_defaults(parser):
    # Empty output should result in defaults being populated
    output = ""
    parsed = parser._processOutput(output, parser._varsToParse)
    assert parsed is not None
    assert parsed["scalar_var"].content == "0"


def test_validate_vars_config_default():
    vars_map = {"config_var": Configuration()}
    vars_map["config_var"].onEmpty = "Default"
    # Content must not be None to pass first check, but empty to trigger default logic
    vars_map["config_var"].content = []

    work = Gem5ParseWork("f", vars_map)
    validated = work._validateVars(vars_map)

    assert validated["config_var"].content == "Default"


def test_validate_vars_config_no_default_fail():
    vars_map = {"config_var": Configuration()}
    vars_map["config_var"].onEmpty = None
    vars_map["config_var"].content = []

    work = Gem5ParseWork("f", vars_map)

    # WITH FIX: Should default to "None" instead of raising error
    work._validateVars(vars_map)
    assert vars_map["config_var"].content == "None"


def test_call_subprocess(parser):
    # Test __call__ flow mocking subprocess.run
    # Note: We must patch where it is USED, i.e., in the worker module
    with patch("src.parsers.workers.gem5_parse_work.subprocess.run") as mock_run:
        with patch("src.utils.utils.checkFileExistsOrException"):
            # Success Case
            mock_result = MagicMock()
            mock_result.stdout = (
                "scalar/scalar_var/10\n"
                "vector/vector_var::0/20\n"
                "distribution/dist_var::min/5\n"
            )
            mock_run.return_value = mock_result

            result = parser()

            assert result["scalar_var"].content == "10"
            assert result["vector_var"].content["0"] == ["20"]


def test_distribution_with_stats(parser):
    # Test processing distribution with stats entries (mean, samples)
    # Mock variables first
    from src.parsers.types import StatTypeRegistry

    # Use small range to satisfy validation of all buckets
    # Initialize with configured statistics to pass validation
    dist_var = StatTypeRegistry.create(
        "distribution",
        minimum=0,
        maximum=1,
        statistics=["samples", "mean", "underflows", "overflows"],
    )
    parser._varsToParse = {"dist_var": dist_var}
    parser._entryBuffer = {}

    # Simulate lines from scanner (now scanner sends 'distribution' for these)
    output = (
        "distribution/dist_var::0/10\n"
        "distribution/dist_var::1/20\n"
        "distribution/dist_var::underflows/0\n"
        "distribution/dist_var::overflows/0\n"
        "distribution/dist_var::samples/100\n"
        "distribution/dist_var::mean/5.5"
    )

    parser._processOutput(output, parser._varsToParse)

    assert dist_var.content["0"] == [10.0]
    assert dist_var.content["1"] == [20.0]
    assert dist_var.content["samples"] == [100.0]
    assert dist_var.content["mean"] == [5.5]
