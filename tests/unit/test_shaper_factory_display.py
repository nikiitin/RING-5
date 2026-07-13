"""
Tests for ShaperFactory display name methods.

Tests the business logic in Layer B shaper factory.
"""

from src.core.services.shapers.factory import ShaperFactory

# ShaperFactory Display Names


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
        for _display_name, type_id in display_map.items():
            assert type_id in registered_types

    def test_roundtrip_display_to_type(self) -> None:
        """Display name → type_id → display name roundtrip."""
        display_map = ShaperFactory.get_display_name_map()
        for display_name, type_id in display_map.items():
            assert ShaperFactory.get_display_name(type_id) == display_name
