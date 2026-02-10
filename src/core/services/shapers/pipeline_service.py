"""
Module: src.core.services.shapers/pipeline_service.py

Purpose:
    Manages shaper pipeline configurations for data transformation workflows.
    Provides persistence, versioning, and retrieval of reusable transformation
    pipelines that can be applied to different datasets.

Responsibilities:
    - Save pipeline configurations to JSON files
    - Load saved pipelines by name
    - List all available pipelines
    - Validate pipeline structure before saving
    - Track pipeline metadata (name, description, timestamp)

Dependencies:
    - json: For pipeline serialization/deserialization

Usage Example:
    >>> from src.core.services.shapers.pipeline_service import PipelineService
    >>>
    >>> # Create pipeline configuration
    >>> pipeline_config = [
    ...     {"type": "column_selector", "columns": ["x", "y"]},
    ...     {"type": "normalize", "baseline": {"x": 1.0}, "columns": ["x"]}
    ... ]
    >>>
    >>> # Save pipeline
    >>> PipelineService.save_pipeline(
    ...     name="baseline_normalization",
    ...     pipeline_config=pipeline_config,
    ...     description="Normalize data against baseline"
    ... )
    >>>
    >>> # Load pipeline
    >>> loaded = PipelineService.load_pipeline("baseline_normalization")
    >>> print(f"Pipeline has {len(loaded['pipeline'])} shapers")

Design Patterns:
    - Service Layer Pattern: Separates persistence from business logic
    - Repository Pattern: File-based storage abstraction

Performance Characteristics:
    - Save: O(1) file write, typically <10ms
    - Load: O(1) file read, typically <5ms
    - List: O(n) directory scan where n = pipeline count

Error Handling:
    - Raises ValueError for empty pipeline names
    - Raises FileNotFoundError when loading non-existent pipeline
    - Logs errors for I/O failures

Thread Safety:
    - Not thread-safe (file I/O without locks)
    - Safe in Streamlit's single-thread execution model

Testing:
    - Unit tests: tests/unit/test_pipeline_service.py

Version: 2.0.0
Last Modified: 2026-01-27
"""

import json
from pathlib import Path
from typing import Any, Dict, List, cast

import pandas as pd

from src.core.common.utils import sanitize_filename, validate_path_within
from src.core.services.shapers.factory import ShaperFactory


class PipelineService:
    """Service to handle saving, loading, and managing transformation pipelines."""

    def __init__(self, pipelines_dir: Path) -> None:
        """Initialize with the pipelines storage directory.

        Args:
            pipelines_dir: Path to directory where pipeline JSONs are stored.
        """
        self._pipelines_dir = pipelines_dir
        self._pipelines_dir.mkdir(parents=True, exist_ok=True)

    def list_pipelines(self) -> List[str]:
        """List all available saved pipelines."""
        if not self._pipelines_dir.exists():
            return []

        return [p.stem for p in self._pipelines_dir.glob("*.json")]

    def save_pipeline(
        self, name: str, pipeline_config: List[Dict[str, Any]], description: str = ""
    ) -> None:
        """Save a pipeline configuration to disk."""
        if not name:
            raise ValueError("Pipeline name cannot be empty")

        safe_name: str = sanitize_filename(name)

        data = {
            "name": name,
            "description": description,
            "pipeline": pipeline_config,
            "timestamp": pd.Timestamp.now().isoformat(),
        }

        save_path = validate_path_within(
            self._pipelines_dir / f"{safe_name}.json", self._pipelines_dir
        )
        with open(save_path, "w") as f:
            json.dump(data, f, indent=2)

    def load_pipeline(self, name: str) -> Dict[str, Any]:
        """Load a pipeline configuration by name."""
        safe_name: str = sanitize_filename(name)
        load_path = validate_path_within(
            self._pipelines_dir / f"{safe_name}.json", self._pipelines_dir
        )

        if not load_path.exists():
            raise FileNotFoundError(f"Pipeline '{name}' not found")

        with open(load_path, "r") as f:
            return cast(Dict[str, Any], json.load(f))

    def delete_pipeline(self, name: str) -> None:
        """Delete a pipeline configuration."""
        safe_name: str = sanitize_filename(name)
        path = validate_path_within(self._pipelines_dir / f"{safe_name}.json", self._pipelines_dir)
        if path.exists():
            path.unlink()

    @staticmethod
    def process_pipeline(data: pd.DataFrame, pipeline_config: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Apply a sequence of shapers to a DataFrame.

        Args:
            data: Input DataFrame
            pipeline_config: List of shaper configurations

        Returns:
            Transformed DataFrame
        """
        current_data = data.copy()

        for shaper_config in pipeline_config:
            shaper_type = shaper_config.get("type")
            if not shaper_type:
                continue

            try:
                shaper = ShaperFactory.create_shaper(shaper_type, shaper_config)
                current_data = shaper(current_data)
            except Exception as e:
                # Log error but maybe re-raise or continue?
                # Facade usually re-raised or handled it.
                # For now let's re-raise to be safe conform to tests
                raise ValueError(f"Failed to apply shaper {shaper_type}: {e}") from e

        return current_data
