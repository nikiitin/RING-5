"""
Unit tests for VariableValidationService.

Tests comprehensive validation logic for gem5 variable configurations.
"""

import pytest
from src.web.services.variable_validation_service import VariableValidationService


class TestVariableNameValidation:
    """Test variable name validation."""

    def test_valid_simple_name(self) -> None:
        """Test validation of simple valid name."""
        errors = VariableValidationService.validate_variable_name("system.cpu.ipc")
        assert len(errors) == 0

    def test_valid_complex_name(self) -> None:
        """Test validation of complex valid name."""
        errors = VariableValidationService.validate_variable_name(
            "system.cpu0.dcache.overall_miss_rate"
        )
        assert len(errors) == 0

    def test_valid_regex_pattern(self) -> None:
        """Test validation of regex pattern."""
        errors = VariableValidationService.validate_variable_name(r"system.cpu\d+.ipc")
        assert len(errors) == 0

    def test_empty_name(self) -> None:
        """Test validation fails for empty name."""
        errors = VariableValidationService.validate_variable_name("")
        assert len(errors) == 1
        assert "empty" in errors[0].lower()

    def test_invalid_characters(self) -> None:
        """Test validation fails for invalid characters."""
        errors = VariableValidationService.validate_variable_name("system cpu ipc")
        assert len(errors) == 1
        assert "invalid" in errors[0].lower()


class TestScalarValidation:
    """Test scalar variable validation."""

    def test_valid_scalar(self) -> None:
        """Test validation of valid scalar."""
        config = {"name": "system.cpu.ipc", "type": "scalar"}
        errors = VariableValidationService.validate_variable(config)
        assert len(errors) == 0

    def test_scalar_with_alias(self) -> None:
        """Test validation of scalar with alias."""
        config = {"name": "system.cpu.ipc", "type": "scalar", "alias": "IPC"}
        errors = VariableValidationService.validate_variable(config)
        assert len(errors) == 0

    def test_missing_name(self) -> None:
        """Test validation fails when name is missing."""
        config = {"type": "scalar"}
        errors = VariableValidationService.validate_variable(config)
        assert len(errors) >= 1
        assert any("name" in e.lower() and "required" in e.lower() for e in errors)

    def test_missing_type(self) -> None:
        """Test validation fails when type is missing."""
        config = {"name": "system.cpu.ipc"}
        errors = VariableValidationService.validate_variable(config)
        assert len(errors) >= 1
        assert any("type" in e.lower() and "required" in e.lower() for e in errors)


class TestVectorValidation:
    """Test vector variable validation."""

    def test_valid_vector_with_entries(self) -> None:
        """Test validation of vector with entries."""
        config = {
            "name": "system.cpu.dcache.miss_rate",
            "type": "vector",
            "entries": ["read", "write"],
        }
        errors = VariableValidationService.validate_variable(config)
        assert len(errors) == 0

    def test_valid_vector_with_statistics(self) -> None:
        """Test validation of vector with useSpecialMembers."""
        config = {
            "name": "system.cpu.dcache.miss_rate",
            "type": "vector",
            "useSpecialMembers": True,
            "statistics": ["mean", "stdev"],
        }
        errors = VariableValidationService.validate_variable(config)
        assert len(errors) == 0

    def test_vector_missing_entries_and_special(self) -> None:
        """Test validation fails when vector has no entries or special members."""
        config = {"name": "system.cpu.dcache.miss_rate", "type": "vector"}
        errors = VariableValidationService.validate_variable(config)
        assert len(errors) >= 1
        assert any("entries" in e.lower() or "usespecialmembers" in e.lower() for e in errors)

    def test_vector_empty_entries(self) -> None:
        """Test validation fails when vector has empty entries list."""
        config = {"name": "system.cpu.dcache.miss_rate", "type": "vector", "entries": []}
        errors = VariableValidationService.validate_variable(config)
        assert len(errors) >= 1
        assert any("at least one entry" in e.lower() for e in errors)

    def test_vector_special_members_no_statistics(self) -> None:
        """Test validation fails when useSpecialMembers but no statistics."""
        config = {
            "name": "system.cpu.dcache.miss_rate",
            "type": "vector",
            "useSpecialMembers": True,
        }
        errors = VariableValidationService.validate_variable(config)
        assert len(errors) >= 1
        assert any("statistic" in e.lower() for e in errors)

    def test_vector_entries_not_list(self) -> None:
        """Test validation fails when entries is not a list."""
        config = {"name": "system.cpu.dcache.miss_rate", "type": "vector", "entries": "read,write"}
        errors = VariableValidationService.validate_variable(config)
        assert len(errors) >= 1
        assert any("must be a list" in e.lower() for e in errors)


class TestHistogramValidation:
    """Test histogram variable validation."""

    def test_valid_histogram_with_entries(self) -> None:
        """Test validation of histogram with entries."""
        config = {
            "name": "system.cpu.latency",
            "type": "histogram",
            "entries": ["0-10", "10-20", "20-30"],
        }
        errors = VariableValidationService.validate_variable(config)
        assert len(errors) == 0

    def test_valid_histogram_with_rebinning(self) -> None:
        """Test validation of histogram with rebinning enabled."""
        config = {
            "name": "system.cpu.latency",
            "type": "histogram",
            "entries": ["0-10", "10-20"],
            "enableRebin": True,
            "bins": 10,
            "max_range": 100.0,
        }
        errors = VariableValidationService.validate_variable(config)
        assert len(errors) == 0

    def test_histogram_missing_entries(self) -> None:
        """Test validation fails when histogram has no entries."""
        config = {"name": "system.cpu.latency", "type": "histogram"}
        errors = VariableValidationService.validate_variable(config)
        assert len(errors) >= 1
        assert any("entries" in e.lower() or "usespecialmembers" in e.lower() for e in errors)

    def test_histogram_rebin_missing_bins(self) -> None:
        """Test validation fails when rebinning enabled but bins missing."""
        config = {
            "name": "system.cpu.latency",
            "type": "histogram",
            "entries": ["0-10"],
            "enableRebin": True,
            "max_range": 100.0,
        }
        errors = VariableValidationService.validate_variable(config)
        assert len(errors) >= 1
        assert any("bins" in e.lower() for e in errors)

    def test_histogram_rebin_missing_max_range(self) -> None:
        """Test validation fails when rebinning enabled but max_range missing."""
        config = {
            "name": "system.cpu.latency",
            "type": "histogram",
            "entries": ["0-10"],
            "enableRebin": True,
            "bins": 10,
        }
        errors = VariableValidationService.validate_variable(config)
        assert len(errors) >= 1
        assert any("max_range" in e.lower() for e in errors)

    def test_histogram_rebin_invalid_bins(self) -> None:
        """Test validation fails when bins is not positive integer."""
        config = {
            "name": "system.cpu.latency",
            "type": "histogram",
            "entries": ["0-10"],
            "enableRebin": True,
            "bins": 0,
            "max_range": 100.0,
        }
        errors = VariableValidationService.validate_variable(config)
        assert len(errors) >= 1
        assert any("bins" in e.lower() and "positive" in e.lower() for e in errors)

    def test_histogram_rebin_invalid_max_range(self) -> None:
        """Test validation fails when max_range is not positive."""
        config = {
            "name": "system.cpu.latency",
            "type": "histogram",
            "entries": ["0-10"],
            "enableRebin": True,
            "bins": 10,
            "max_range": -100.0,
        }
        errors = VariableValidationService.validate_variable(config)
        assert len(errors) >= 1
        assert any("max_range" in e.lower() and "positive" in e.lower() for e in errors)


class TestDistributionValidation:
    """Test distribution variable validation."""

    def test_valid_distribution(self) -> None:
        """Test validation of valid distribution."""
        config = {
            "name": "system.cpu.latency_dist",
            "type": "distribution",
            "minimum": 0,
            "maximum": 1000,
        }
        errors = VariableValidationService.validate_variable(config)
        assert len(errors) == 0

    def test_distribution_with_statistics(self) -> None:
        """Test validation of distribution with statistics."""
        config = {
            "name": "system.cpu.latency_dist",
            "type": "distribution",
            "minimum": 0,
            "maximum": 1000,
            "statistics": ["mean", "stdev", "samples"],
        }
        errors = VariableValidationService.validate_variable(config)
        assert len(errors) == 0

    def test_distribution_missing_minimum(self) -> None:
        """Test validation fails when minimum is missing."""
        config = {"name": "system.cpu.latency_dist", "type": "distribution", "maximum": 1000}
        errors = VariableValidationService.validate_variable(config)
        assert len(errors) >= 1
        assert any("minimum" in e.lower() for e in errors)

    def test_distribution_missing_maximum(self) -> None:
        """Test validation fails when maximum is missing."""
        config = {"name": "system.cpu.latency_dist", "type": "distribution", "minimum": 0}
        errors = VariableValidationService.validate_variable(config)
        assert len(errors) >= 1
        assert any("maximum" in e.lower() for e in errors)

    def test_distribution_invalid_range(self) -> None:
        """Test validation fails when minimum >= maximum."""
        config = {
            "name": "system.cpu.latency_dist",
            "type": "distribution",
            "minimum": 1000,
            "maximum": 0,
        }
        errors = VariableValidationService.validate_variable(config)
        assert len(errors) >= 1
        assert any("less than" in e.lower() for e in errors)

    def test_distribution_non_numeric_minimum(self) -> None:
        """Test validation fails when minimum is not numeric."""
        config = {
            "name": "system.cpu.latency_dist",
            "type": "distribution",
            "minimum": "zero",
            "maximum": 1000,
        }
        errors = VariableValidationService.validate_variable(config)
        assert len(errors) >= 1
        assert any("minimum" in e.lower() and "number" in e.lower() for e in errors)


class TestConfigurationValidation:
    """Test configuration variable validation."""

    def test_valid_configuration(self) -> None:
        """Test validation of valid configuration."""
        config = {"name": "system.cpu.clock", "type": "configuration"}
        errors = VariableValidationService.validate_variable(config)
        assert len(errors) == 0

    def test_configuration_with_on_empty(self) -> None:
        """Test validation of configuration with onEmpty."""
        config = {"name": "system.cpu.clock", "type": "configuration", "onEmpty": "1GHz"}
        errors = VariableValidationService.validate_variable(config)
        assert len(errors) == 0


class TestInternalStatsFiltering:
    """Test filtering of internal gem5 statistics."""

    def test_filter_internal_stats(self) -> None:
        """Test filtering removes internal stats."""
        entries = ["read", "write", "total", "mean", "stdev"]
        filtered = VariableValidationService.filter_internal_stats(entries)
        assert filtered == ["read", "write"]

    def test_filter_all_internal(self) -> None:
        """Test filtering when all are internal stats."""
        entries = ["total", "mean", "gmean", "stdev", "samples"]
        filtered = VariableValidationService.filter_internal_stats(entries)
        assert len(filtered) == 0

    def test_filter_no_internal(self) -> None:
        """Test filtering when no internal stats."""
        entries = ["read", "write", "execute"]
        filtered = VariableValidationService.filter_internal_stats(entries)
        assert filtered == entries

    def test_filter_case_insensitive(self) -> None:
        """Test filtering is case-insensitive."""
        entries = ["read", "TOTAL", "Mean", "write"]
        filtered = VariableValidationService.filter_internal_stats(entries)
        assert filtered == ["read", "write"]


class TestStatisticsValidation:
    """Test statistics selection validation."""

    def test_valid_statistics(self) -> None:
        """Test validation of valid statistics."""
        stats = ["mean", "stdev", "samples"]
        errors = VariableValidationService.validate_statistics_selection(stats)
        assert len(errors) == 0

    def test_all_valid_statistics(self) -> None:
        """Test validation of all valid statistics."""
        stats = ["total", "mean", "gmean", "stdev", "samples", "overflows", "underflows"]
        errors = VariableValidationService.validate_statistics_selection(stats)
        assert len(errors) == 0

    def test_invalid_statistic(self) -> None:
        """Test validation fails for invalid statistic."""
        stats = ["mean", "invalid_stat", "stdev"]
        errors = VariableValidationService.validate_statistics_selection(stats)
        assert len(errors) >= 1
        assert any("invalid_stat" in e.lower() for e in errors)

    def test_empty_statistics(self) -> None:
        """Test validation passes for empty list."""
        stats: list[str] = []
        errors = VariableValidationService.validate_statistics_selection(stats)
        assert len(errors) == 0


class TestBatchValidation:
    """Test batch validation of multiple variables."""

    def test_batch_all_valid(self) -> None:
        """Test batch validation when all variables valid."""
        configs = [
            {"name": "system.cpu.ipc", "type": "scalar"},
            {"name": "system.cpu.dcache.miss_rate", "type": "vector", "entries": ["read"]},
            {"name": "system.cpu.latency", "type": "distribution", "minimum": 0, "maximum": 100},
        ]
        errors = VariableValidationService.validate_batch(configs)
        assert len(errors) == 0

    def test_batch_some_invalid(self) -> None:
        """Test batch validation when some variables invalid."""
        configs = [
            {"name": "system.cpu.ipc", "type": "scalar"},  # Valid
            {"name": "", "type": "vector"},  # Invalid: empty name
            {
                "name": "system.cpu.latency",
                "type": "distribution",
                "minimum": 100,
                "maximum": 0,
            },  # Invalid: bad range
        ]
        errors = VariableValidationService.validate_batch(configs)
        assert "0" not in errors  # First variable is valid
        assert "1" in errors  # Second variable has errors
        assert "2" in errors  # Third variable has errors

    def test_batch_empty_list(self) -> None:
        """Test batch validation with empty list."""
        configs: list[dict[str, str]] = []
        errors = VariableValidationService.validate_batch(configs)
        assert len(errors) == 0


class TestUnknownVariableType:
    """Test handling of unknown variable types."""

    def test_unknown_type(self) -> None:
        """Test validation fails for unknown type."""
        config = {"name": "system.cpu.something", "type": "unknown_type"}
        errors = VariableValidationService.validate_variable(config)
        assert len(errors) >= 1
        assert any("unknown" in e.lower() and "type" in e.lower() for e in errors)
