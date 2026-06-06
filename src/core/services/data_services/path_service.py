"""
Path Service - Centralized File System Navigation.

Manages all file system paths for the application including root directory,
data directory, portfolio storage, and other critical paths. Provides
consistent, testable access to file system locations.
"""

from pathlib import Path


class PathService:
    # Cached directory paths — mkdir is called only once per process.
    _root_dir: Path | None = None
    _data_dir: Path | None = None
    _portfolios_dir: Path | None = None

    @staticmethod
    def reset_caches() -> None:
        """Reset all cached directory paths (for testing)."""
        PathService._root_dir = None
        PathService._data_dir = None
        PathService._portfolios_dir = None

    @staticmethod
    def get_root_dir() -> Path:
        """Get the project root directory."""
        if PathService._root_dir is None:
            # data_services/path_service.py -> data_services -> services -> core -> src -> root
            PathService._root_dir = Path(__file__).parent.parent.parent.parent.parent
        return PathService._root_dir

    @staticmethod
    def get_data_dir() -> Path:
        """Get the .ring5 data directory."""
        if PathService._data_dir is None:
            PathService._data_dir = PathService.get_root_dir() / ".ring5"
            PathService._data_dir.mkdir(parents=True, exist_ok=True)
        return PathService._data_dir

    @staticmethod
    def get_portfolios_dir() -> Path:
        """Get the portfolios directory."""
        if PathService._portfolios_dir is None:
            PathService._portfolios_dir = PathService.get_data_dir() / "portfolios"
            PathService._portfolios_dir.mkdir(parents=True, exist_ok=True)
        return PathService._portfolios_dir
