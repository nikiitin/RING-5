"""Tests for PipelineService."""

import json
from pathlib import Path

import pytest

from src.core.services.shapers.pipeline_service import PipelineService


class TestPipelineService:
    """Tests for PipelineService."""

    def test_list_pipelines_empty(self, tmp_path: Path) -> None:
        """Test listing pipelines when none exist."""
        service = PipelineService(tmp_path)
        pipelines = service.list_pipelines()
        assert pipelines == []

    def test_list_pipelines_non_existent_dir(self, tmp_path: Path) -> None:
        """Test listing pipelines when directory doesn't exist."""
        non_existent = tmp_path / "nonexistent"
        service = PipelineService(non_existent)
        pipelines = service.list_pipelines()
        assert pipelines == []

    def test_list_pipelines_with_files(self, tmp_path: Path) -> None:
        """Test listing pipelines when some exist."""
        (tmp_path / "pipeline1.json").touch()
        (tmp_path / "pipeline2.json").touch()
        (tmp_path / "not_json.txt").touch()

        service = PipelineService(tmp_path)
        pipelines = service.list_pipelines()
        assert len(pipelines) == 2
        assert "pipeline1" in pipelines
        assert "pipeline2" in pipelines

    def test_save_pipeline(self, tmp_path: Path) -> None:
        """Test saving a pipeline."""
        service = PipelineService(tmp_path)
        config = [{"type": "columnSelector", "columns": ["a"]}]
        service.save_pipeline("test_pipeline", config, "Test description")

        saved_path = tmp_path / "test_pipeline.json"
        assert saved_path.exists()

        with open(saved_path) as f:
            data = json.load(f)
        assert data["name"] == "test_pipeline"
        assert data["description"] == "Test description"
        assert data["pipeline"] == config

    def test_save_pipeline_empty_name_raises(self, tmp_path: Path) -> None:
        """Test that saving with empty name raises."""
        service = PipelineService(tmp_path)
        with pytest.raises(ValueError, match="empty"):
            service.save_pipeline("", [])

    def test_load_pipeline(self, tmp_path: Path) -> None:
        """Test loading a pipeline."""
        test_data = {"name": "test", "pipeline": [{"type": "test"}]}
        (tmp_path / "mytest.json").write_text(json.dumps(test_data))

        service = PipelineService(tmp_path)
        loaded = service.load_pipeline("mytest")
        assert loaded["name"] == "test"

    def test_load_pipeline_not_found(self, tmp_path: Path) -> None:
        """Test loading non-existent pipeline raises."""
        service = PipelineService(tmp_path)
        with pytest.raises(FileNotFoundError, match="not found"):
            service.load_pipeline("nonexistent")

    def test_delete_pipeline(self, tmp_path: Path) -> None:
        """Test deleting a pipeline."""
        pipeline_file = tmp_path / "to_delete.json"
        pipeline_file.touch()
        assert pipeline_file.exists()

        service = PipelineService(tmp_path)
        service.delete_pipeline("to_delete")
        assert not pipeline_file.exists()

    def test_delete_pipeline_non_existent(self, tmp_path: Path) -> None:
        """Test deleting non-existent pipeline doesn't raise."""
        service = PipelineService(tmp_path)
        # Should not raise
        service.delete_pipeline("nonexistent")
