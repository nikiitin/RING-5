"""
Compliance test for TDD Chapter 6 rules.
Demonstrates: Dynamic Fixture Parametrization, Request Introspection, and Marker usage.
"""

import pytest

# --- Fixtures ---


@pytest.fixture(params=["sqlite", "postgres"])
def db_driver(request: pytest.FixtureRequest) -> str:
    """
    Demonstrates Fixture Parametrization (Ch 6).
    This fixture will cause dependent tests to run twice:
    once for 'sqlite', once for 'postgres'.
    """
    driver_name = request.param
    return f"Driver: {driver_name}"


@pytest.fixture
def config_reader(request: pytest.FixtureRequest) -> dict[str, str]:
    """
    Demonstrates Introspection (Ch 6).
    Reads a marker 'data_value' from the calling test.
    """
    # Use get_closest_marker to safely access marker data
    marker = request.node.get_closest_marker("data_value")
    if marker:
        return {"value": marker.args[0]}
    return {"value": "default"}


# --- Tests ---


def test_driver_matrix(db_driver: str) -> None:
    """
    This test runs 2x (sqlite/postgres) because of the fixture.
    """
    assert "Driver: " in db_driver
    assert "sqlite" in db_driver or "postgres" in db_driver


@pytest.mark.data_value("injected_config")
def test_marker_introspection(config_reader: dict[str, str]) -> None:
    """
    Demonstrates how the fixture reads the marker @pytest.mark.data_value
    """
    assert config_reader["value"] == "injected_config"


def test_default_introspection(config_reader: dict[str, str]) -> None:
    """
    Demonstrates fallback when marker is absent.
    """
    assert config_reader["value"] == "default"
