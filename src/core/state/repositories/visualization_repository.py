"""
Visualization Repository
Manages per-plot FigureConfig storage.

Each plot has an associated FigureConfig that controls its rendering.
This repository provides typed, centralized access to those configurations
without any UI or engine-specific dependencies.
"""

from __future__ import annotations

import logging

from src.core.models.visualization.figure_config import FigureConfig

logger = logging.getLogger(__name__)


class VisualizationRepository:
    """
    Repository for managing per-plot visualization configurations.

    Stores ``FigureConfig`` instances keyed by plot ID.  No Streamlit or
    engine-specific imports — pure Python state management.
    """

    def __init__(self) -> None:
        self._configs: dict[int, FigureConfig] = {}

    def get_config(self, plot_id: int) -> FigureConfig | None:
        """Return the FigureConfig for *plot_id*, or ``None``."""
        return self._configs.get(plot_id)

    def set_config(self, plot_id: int, config: FigureConfig) -> None:
        """Store or replace the FigureConfig for *plot_id*."""
        self._configs[plot_id] = config
        logger.debug("VIZ_REPO: Set config for plot %d", plot_id)

    def remove_config(self, plot_id: int) -> None:
        """Remove the FigureConfig for *plot_id* (no-op if absent)."""
        removed = self._configs.pop(plot_id, None)
        if removed is not None:
            logger.debug("VIZ_REPO: Removed config for plot %d", plot_id)

    def has_config(self, plot_id: int) -> bool:
        """Check whether a config exists for *plot_id*."""
        return plot_id in self._configs

    def get_all(self) -> dict[int, FigureConfig]:
        """Return a shallow copy of the entire config map."""
        return dict(self._configs)

    def clear(self) -> None:
        """Remove all stored configurations."""
        count = len(self._configs)
        self._configs.clear()
        logger.debug("VIZ_REPO: Cleared %d configs", count)
