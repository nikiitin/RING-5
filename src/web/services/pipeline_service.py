import json
from typing import Any, Dict, List

import pandas as pd

from src.web.services.paths import PathService


class PipelineService:
    """Service to handle saving, loading, and managing pipelines."""

    @staticmethod
    def list_pipelines() -> List[str]:
        """List all available saved pipelines."""
        pipeline_dir = PathService.get_pipelines_dir()
        if not pipeline_dir.exists():
            return []

        return [p.stem for p in pipeline_dir.glob("*.json")]

    @staticmethod
    def save_pipeline(
        name: str, pipeline_config: List[Dict[str, Any]], description: str = ""
    ) -> None:
        """Save a pipeline configuration to disk."""
        if not name:
            raise ValueError("Pipeline name cannot be empty")

        data = {
            "name": name,
            "description": description,
            "pipeline": pipeline_config,
            "timestamp": pd.Timestamp.now().isoformat(),
        }

        save_path = PathService.get_pipelines_dir() / f"{name}.json"
        with open(save_path, "w") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def load_pipeline(name: str) -> Dict[str, Any]:
        """Load a pipeline configuration by name."""
        load_path = PathService.get_pipelines_dir() / f"{name}.json"

        if not load_path.exists():
            raise FileNotFoundError(f"Pipeline '{name}' not found")

        with open(load_path, "r") as f:
            return json.load(f)

    @staticmethod
    def delete_pipeline(name: str) -> None:
        """Delete a pipeline configuration."""
        path = PathService.get_pipelines_dir() / f"{name}.json"
        if path.exists():
            path.unlink()
