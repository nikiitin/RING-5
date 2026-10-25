"""Exact schema validation without mutation, inference, or format conversion."""

import copy

import pytest

from src.core.models.portfolio_contract import PortfolioVersionError, validate_portfolio_schema


@pytest.mark.parametrize("version", [None, 0, 1, 2, 3, 5, 99, "4", 4.0, True, False])
def test_unsupported_schema_is_rejected(version) -> None:
    # [test->req~ring5.portfolio.schema~1]
    with pytest.raises(PortfolioVersionError, match="Unsupported portfolio schema_version"):
        validate_portfolio_schema({"schema_version": version})


def test_current_schema_validation_preserves_input() -> None:
    value = {
        "schema_version": 4,
        "version": "4.0",
        "parser_strategy": "simple",
        "simulator": "gem5",
        "environment_metadata": {},
        "integrity_manifest": {},
    }
    before = copy.deepcopy(value)
    assert validate_portfolio_schema(value) is value
    assert value == before


@pytest.mark.parametrize(
    "field",
    ["version", "parser_strategy", "simulator", "environment_metadata", "integrity_manifest"],
)
def test_current_schema_requires_explicit_metadata(field: str) -> None:
    value = {
        "schema_version": 4,
        "version": "4.0",
        "parser_strategy": "simple",
        "simulator": "gem5",
        "environment_metadata": {},
        "integrity_manifest": {},
    }
    value.pop(field)
    with pytest.raises(ValueError):
        validate_portfolio_schema(value)
