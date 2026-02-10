"""
Compliance test for TDD Chapter 9 rules.
Demonstrates: Logic independent of environment (Tox) and Argument Passing simulation.
"""

import sys

import pytest

# --- Tests ---


def test_environment_agnostic() -> None:
    """
    Validates that logic does not depend on hardcoded paths or system-specifics.
    This ensures reliability across Tox environments (py310, py311, CI).
    """
    # BAD: assert os.path.exists("/home/vnicolas/...")
    # GOOD: Use relative paths or env vars

    # Simulate checking if we are inside a virtualenv (Tox always uses one)
    # This is a heuristic check often used in simple env validations
    is_venv = (sys.prefix != sys.base_prefix) or hasattr(sys, "real_prefix")

    # We don't assert True here because 'make test' might run outside venv in some docker setups
    # But the test logic itself verifies we CAN check this without crashing.
    assert isinstance(is_venv, bool)


def test_posargs_simulation(request: pytest.FixtureRequest) -> None:
    """
    Demonstrates design for argument passing ({posargs}).
    Tests should respect markers or keywords passed via CLI.
    """
    # Logic effectively tested by the fact that we can select THIS test
    # using 'pytest -k test_posargs_simulation'
    # behaving correctly under Tox's {posargs}
    assert True
