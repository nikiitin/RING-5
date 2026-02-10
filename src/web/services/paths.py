from pathlib import Path


class PathService:
    @staticmethod
    def get_root_dir() -> Path:
        """Get the project root directory."""
        # Assuming src/web/services/paths.py -> src/web/services -> src/web -> src -> root
        return Path(__file__).parent.parent.parent.parent

    @staticmethod
    def get_data_dir() -> Path:
        """Get the .ring5 data directory."""
        data_dir = PathService.get_root_dir() / ".ring5"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    @staticmethod
    def get_pipelines_dir() -> Path:
        """Get the pipelines directory."""
        pipelines_dir = PathService.get_data_dir() / "pipelines"
        pipelines_dir.mkdir(parents=True, exist_ok=True)
        return pipelines_dir

    @staticmethod
    def get_portfolios_dir() -> Path:
        """Get the portfolios directory."""
        portfolios_dir = PathService.get_data_dir() / "portfolios"
        portfolios_dir.mkdir(parents=True, exist_ok=True)
        return portfolios_dir
