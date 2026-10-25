"""Exact schema validation without mutation, inference, or format conversion."""

import copy

import pytest

from src.core.models.portfolio_contract import (
    CURRENT_PORTFOLIO_SCHEMA_VERSION,
    CURRENT_PORTFOLIO_VERSION,
    PortfolioVersionError,
    validate_portfolio_schema,
)


@pytest.mark.parametrize(
    "version",
    [
        None,
        -1,
        *range(CURRENT_PORTFOLIO_SCHEMA_VERSION),
        CURRENT_PORTFOLIO_SCHEMA_VERSION + 1,
        CURRENT_PORTFOLIO_SCHEMA_VERSION + 100,
        str(CURRENT_PORTFOLIO_SCHEMA_VERSION),
        float(CURRENT_PORTFOLIO_SCHEMA_VERSION),
        True,
        False,
    ],
)
def test_unsupported_schema_is_rejected(version) -> None:
    # [test->req~ring5.portfolio.schema~1]
    with pytest.raises(PortfolioVersionError, match="Unsupported portfolio schema_version"):
        validate_portfolio_schema({"schema_version": version})


def test_current_schema_validation_preserves_input() -> None:
    value = {
        "schema_version": CURRENT_PORTFOLIO_SCHEMA_VERSION,
        "version": CURRENT_PORTFOLIO_VERSION,
        "parser_strategy": "simple",
        "simulator": "gem5",
        "environment_metadata": {},
        "integrity_manifest": {},
        "parse_variables": [],
        "scanned_variables": [],
    }
    before = copy.deepcopy(value)
    assert validate_portfolio_schema(value) is value
    assert value == before


@pytest.mark.parametrize(
    "field",
    [
        "version",
        "parser_strategy",
        "simulator",
        "environment_metadata",
        "integrity_manifest",
        "scanned_variables",
    ],
)
def test_current_schema_requires_explicit_metadata(field: str) -> None:
    value = {
        "schema_version": CURRENT_PORTFOLIO_SCHEMA_VERSION,
        "version": CURRENT_PORTFOLIO_VERSION,
        "parser_strategy": "simple",
        "simulator": "gem5",
        "environment_metadata": {},
        "integrity_manifest": {},
        "parse_variables": [],
        "scanned_variables": [],
    }
    value.pop(field)
    with pytest.raises(ValueError):
        validate_portfolio_schema(value)


@pytest.mark.parametrize("missing", ["source_type", "instances"])
def test_current_portfolio_rejects_incomplete_scan_metadata(missing) -> None:
    record = {
        "name": "ipc",
        "type": "scalar",
        "entries": [],
        "source_type": "scalar",
        "instances": [{"source_name": "ipc", "indices": []}],
    }
    record.pop(missing)
    value = {
        "schema_version": CURRENT_PORTFOLIO_SCHEMA_VERSION,
        "version": CURRENT_PORTFOLIO_VERSION,
        "parser_strategy": "simple",
        "simulator": "gem5",
        "environment_metadata": {},
        "integrity_manifest": {},
        "parse_variables": [],
        "scanned_variables": [record],
    }
    before = copy.deepcopy(value)
    with pytest.raises(ValueError, match="Missing required scanned variable fields"):
        validate_portfolio_schema(value)
    assert value == before
