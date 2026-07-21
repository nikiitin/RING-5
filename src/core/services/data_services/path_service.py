"""Centralized paths for persistent application data."""

import os
from pathlib import Path


class PathService:
    """Resolve and cache repository and application-data directories."""

    # Cached directory paths — mkdir is called only once per process.
    _root_dir: Path | None = None
    _data_dir: Path | None = None
    _portfolios_dir: Path | None = None
    _dataset_snapshots_dir: Path | None = None
    _analysis_recipes_dir: Path | None = None

    @staticmethod
    def reset_caches() -> None:
        """Reset all cached directory paths (for testing)."""
        PathService._root_dir = None
        PathService._data_dir = None
        PathService._portfolios_dir = None
        PathService._dataset_snapshots_dir = None
        PathService._analysis_recipes_dir = None

    @staticmethod
    def get_root_dir() -> Path:
        """Get the project root directory."""
        if PathService._root_dir is None:
            # data_services/path_service.py -> data_services -> services -> core -> src -> root
            PathService._root_dir = Path(__file__).parent.parent.parent.parent.parent
        return PathService._root_dir

    @staticmethod
    def get_data_dir() -> Path:
        """Get the app data directory (pool, portfolios, configs).

        Defaults to ``<repo>/.ring5`` but honours the ``RING5_DATA_DIR``
        environment variable when set, so tests (and sandboxes) can redirect all
        app data to an isolated location instead of the shared repo ``.ring5``.
        """
        # [impl->req~ring5.workspace.application-data-directory~1]
        if PathService._data_dir is None:
            override = os.environ.get("RING5_DATA_DIR")
            PathService._data_dir = (
                Path(override) if override else PathService.get_root_dir() / ".ring5"
            )
            PathService._data_dir.mkdir(parents=True, exist_ok=True)
        return PathService._data_dir

    @staticmethod
    def get_portfolios_dir() -> Path:
        """Get the portfolios directory."""
        if PathService._portfolios_dir is None:
            PathService._portfolios_dir = PathService.get_data_dir() / "portfolios"
            PathService._portfolios_dir.mkdir(parents=True, exist_ok=True)
        return PathService._portfolios_dir

    @staticmethod
    def get_dataset_snapshots_dir() -> Path:
        """Get the persistent reusable-dataset snapshot directory."""
        # [impl->req~ring5.data.dataset-snapshots~1]
        if PathService._dataset_snapshots_dir is None:
            PathService._dataset_snapshots_dir = PathService.get_data_dir() / "dataset_snapshots"
            PathService._dataset_snapshots_dir.mkdir(parents=True, exist_ok=True)
        return PathService._dataset_snapshots_dir

    @staticmethod
    def get_analysis_recipes_dir() -> Path:
        """Get the persistent analysis-recipe directory."""
        if PathService._analysis_recipes_dir is None:
            PathService._analysis_recipes_dir = PathService.get_data_dir() / "analysis_recipes"
            PathService._analysis_recipes_dir.mkdir(parents=True, exist_ok=True)
        return PathService._analysis_recipes_dir
