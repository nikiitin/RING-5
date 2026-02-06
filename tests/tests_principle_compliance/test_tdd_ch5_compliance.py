"""
Compliance test for TDD Chapter 5 rules.
Demonstrates: Yield Fixtures (Teardown), Scope Isolation, and Fixture Injection.
"""

from pathlib import Path
from typing import Generator

import pytest

# --- Fixtures ---


@pytest.fixture(scope="function")
def database_connection(tmp_path: Path) -> Generator[Path, None, None]:
    """
    Demonstrates Yield Fixture (Ch 5).
    Setup: Create DB file.
    Yield: Pass to test.
    Teardown: Verify file exists (sanity) and clean up.
    """
    db_file = tmp_path / "test.db"
    db_file.write_text("CONNECTED")  # Setup

    yield db_file

    # Teardown
    assert db_file.exists(), "DB file missing during teardown!"
    db_file.unlink()


@pytest.fixture(scope="session")
def expensive_resource() -> str:
    """Demonstrates Session Scope (Ch 5)."""
    return "Loaded 500MB Model"


# --- Tests ---


def test_yield_teardown(database_connection: Path) -> None:
    """Demonstrates using a yield fixture for resource management."""
    # Act
    content = database_connection.read_text()

    # Assert
    assert content == "CONNECTED"
    # Teardown logic runs after this function returns


def test_scope_isolation(expensive_resource: str) -> None:
    """Demonstrates access to higher-scope fixtures."""
    # Act & Assert
    assert expensive_resource == "Loaded 500MB Model"


@pytest.mark.parametrize("i", [1, 2, 3])
def test_autouse_caution(i: int) -> None:
    """
    Demonstrates Iteration.
    Rule 004 cautions against autouse=True, so we strictly inject what we need.
    """
    assert i > 0
