"""
Tests for ShaperFactory display name methods and PipelineService.prepare_loaded_pipeline.

Tests the business logic extracted from plot_manager_components.py to Layer B.
"""

from src.core.services.shapers.factory import ShaperFactory
from src.core.services.shapers.pipeline_service import PipelineService

# ─── ShaperFactory Display Names ─────────────────────────────────────────────


class TestShaperFactoryDisplayNames:
    """Tests for shaper display name mapping."""

    def test_get_display_name_map_returns_dict(self) -> None:
        result = ShaperFactory.get_display_name_map()
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_display_name_map_keys_are_human_readable(self) -> None:
        result = ShaperFactory.get_display_name_map()
        assert "Column Selector" in result
        assert "Sort" in result
        assert "Mean Calculator" in result
        assert "Normalize" in result
        assert "Filter" in result
        assert "Transformer" in result

    def test_display_name_map_values_are_type_ids(self) -> None:
        result = ShaperFactory.get_display_name_map()
        assert result["Column Selector"] == "columnSelector"
        assert result["Sort"] == "sort"
        assert result["Mean Calculator"] == "mean"
        assert result["Normalize"] == "normalize"
        assert result["Filter"] == "conditionSelector"
        assert result["Transformer"] == "transformer"

    def test_get_display_name_existing(self) -> None:
        assert ShaperFactory.get_display_name("sort") == "Sort"
        assert ShaperFactory.get_display_name("mean") == "Mean Calculator"
        assert ShaperFactory.get_display_name("columnSelector") == "Column Selector"

    def test_get_display_name_unknown_returns_type_id(self) -> None:
        assert ShaperFactory.get_display_name("unknownType") == "unknownType"

    def test_display_name_map_only_includes_registered_types(self) -> None:
        """Display names for unregistered types should not appear."""
        display_map = ShaperFactory.get_display_name_map()
        registered_types = ShaperFactory.get_available_types()
        for display_name, type_id in display_map.items():
            assert type_id in registered_types

    def test_roundtrip_display_to_type(self) -> None:
        """Display name → type_id → display name roundtrip."""
        display_map = ShaperFactory.get_display_name_map()
        for display_name, type_id in display_map.items():
            assert ShaperFactory.get_display_name(type_id) == display_name


# ─── PipelineService.prepare_loaded_pipeline ─────────────────────────────────


class TestPrepareLoadedPipeline:
    """Tests for prepare_loaded_pipeline business logic."""

    def test_basic_pipeline(self) -> None:
        data = {
            "pipeline": [
                {"id": 0, "type": "sort", "config": {}},
                {"id": 1, "type": "mean", "config": {}},
            ]
        }
        steps, counter = PipelineService.prepare_loaded_pipeline(data)
        assert len(steps) == 2
        assert counter == 2

    def test_non_sequential_ids(self) -> None:
        data = {
            "pipeline": [
                {"id": 0, "type": "sort", "config": {}},
                {"id": 5, "type": "mean", "config": {}},
            ]
        }
        steps, counter = PipelineService.prepare_loaded_pipeline(data)
        assert counter == 6  # max_id (5) + 1

    def test_empty_pipeline(self) -> None:
        data = {"pipeline": []}
        steps, counter = PipelineService.prepare_loaded_pipeline(data)
        assert steps == []
        assert counter == 0

    def test_missing_pipeline_key(self) -> None:
        data = {}
        steps, counter = PipelineService.prepare_loaded_pipeline(data)
        assert steps == []
        assert counter == 0

    def test_deep_copy_independence(self) -> None:
        """Steps should be deep-copied, not sharing references."""
        original_pipeline = [{"id": 0, "type": "sort", "config": {"key": "value"}}]
        data = {"pipeline": original_pipeline}
        steps, counter = PipelineService.prepare_loaded_pipeline(data)

        # Mutating returned steps should not affect original
        steps[0]["config"]["key"] = "modified"
        assert original_pipeline[0]["config"]["key"] == "value"

    def test_steps_without_id_field(self) -> None:
        """Steps missing id field should default to -1."""
        data = {
            "pipeline": [
                {"type": "sort", "config": {}},
                {"type": "mean", "config": {}},
            ]
        }
        steps, counter = PipelineService.prepare_loaded_pipeline(data)
        assert counter == 0  # max(-1, -1) + 1 = 0

    def test_single_step(self) -> None:
        data = {"pipeline": [{"id": 3, "type": "normalize", "config": {}}]}
        steps, counter = PipelineService.prepare_loaded_pipeline(data)
        assert len(steps) == 1
        assert counter == 4
