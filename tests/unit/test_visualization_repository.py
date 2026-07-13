"""
Unit tests for VisualizationRepository.

Validates CRUD operations, isolation, and clear semantics for the
per-plot FigureConfig storage repository.
"""

from typing import Dict, Optional

import pytest

from src.core.models.visualization.figure_config import FigureConfig
from src.core.state.repositories.visualization_repository import VisualizationRepository


class TestVisualizationRepository:
    """Tests for VisualizationRepository."""

    # ── Fixtures ────────────────────────────────────────────────────

    @pytest.fixture()
    def repo(self) -> VisualizationRepository:
        return VisualizationRepository()

    @pytest.fixture()
    def sample_config(self) -> FigureConfig:
        return FigureConfig(title="Sample Plot")

    # ── Basic CRUD ──────────────────────────────────────────────────

    def test_get_returns_none_when_empty(self, repo: VisualizationRepository) -> None:
        assert repo.get_config(1) is None

    def test_set_and_get(self, repo: VisualizationRepository, sample_config: FigureConfig) -> None:
        repo.set_config(1, sample_config)
        result: Optional[FigureConfig] = repo.get_config(1)
        assert result is not None
        assert result.title == "Sample Plot"

    def test_has_config(self, repo: VisualizationRepository, sample_config: FigureConfig) -> None:
        assert repo.has_config(1) is False
        repo.set_config(1, sample_config)
        assert repo.has_config(1) is True

    def test_remove_config(
        self, repo: VisualizationRepository, sample_config: FigureConfig
    ) -> None:
        repo.set_config(1, sample_config)
        repo.remove_config(1)
        assert repo.get_config(1) is None
        assert repo.has_config(1) is False

    def test_remove_nonexistent_is_noop(self, repo: VisualizationRepository) -> None:
        repo.remove_config(999)  # should not raise

    def test_overwrite(self, repo: VisualizationRepository, sample_config: FigureConfig) -> None:
        repo.set_config(1, sample_config)
        updated: FigureConfig = FigureConfig(title="Updated")
        repo.set_config(1, updated)
        result: Optional[FigureConfig] = repo.get_config(1)
        assert result is not None
        assert result.title == "Updated"

    # ── Bulk / clear ────────────────────────────────────────────────

    def test_get_all_returns_shallow_copy(self, repo: VisualizationRepository) -> None:
        c1: FigureConfig = FigureConfig(title="A")
        c2: FigureConfig = FigureConfig(title="B")
        repo.set_config(1, c1)
        repo.set_config(2, c2)

        all_configs: Dict[int, FigureConfig] = repo.get_all()
        assert len(all_configs) == 2
        assert all_configs[1].title == "A"
        assert all_configs[2].title == "B"

        # Mutating the returned dict should not affect the repository
        all_configs[3] = FigureConfig(title="C")
        assert repo.has_config(3) is False

    def test_clear(self, repo: VisualizationRepository, sample_config: FigureConfig) -> None:
        repo.set_config(1, sample_config)
        repo.set_config(2, sample_config)
        repo.clear()
        assert repo.get_all() == {}
        assert repo.get_config(1) is None

    # ── Isolation between plot IDs ──────────────────────────────────

    def test_independent_plots(self, repo: VisualizationRepository) -> None:
        c1: FigureConfig = FigureConfig(title="Plot 1")
        c2: FigureConfig = FigureConfig(title="Plot 2")
        repo.set_config(1, c1)
        repo.set_config(2, c2)

        repo.remove_config(1)
        assert repo.get_config(1) is None
        assert repo.get_config(2) is not None
        assert repo.get_config(2).title == "Plot 2"  # type: ignore[union-attr]
