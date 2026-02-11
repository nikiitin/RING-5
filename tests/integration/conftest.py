"""Conftest for tests/integration/ — integration tests.

Provides fixtures that wrap the synthetic gem5 data with ready-to-use
ApplicationAPI and ParseService instances. Synthetic gem5 data fixtures
are registered via ``tests/helpers/gem5_fixtures.py`` in the root conftest.
"""

from pathlib import Path

import pytest

from src.core.application_api import ApplicationAPI

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def facade() -> ApplicationAPI:
    """Create a fresh ApplicationAPI instance for each test."""
    return ApplicationAPI()


@pytest.fixture
def integration_output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory for parse results."""
    out = tmp_path / "integration_output"
    out.mkdir()
    return out
