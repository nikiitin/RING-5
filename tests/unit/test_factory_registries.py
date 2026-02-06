"""Extended tests for ShaperFactory and DataParserFactory registries."""

import pytest

from src.core.services.shapers.factory import ShaperFactory


class TestShaperFactoryRegistry:
    """Tests for ShaperFactory registry functionality."""

    def test_get_available_types(self):
        """Test getting available shaper types."""
        types = ShaperFactory.get_available_types()
        assert isinstance(types, list)
        assert "mean" in types
        assert "columnSelector" in types
        assert "normalize" in types
        assert "sort" in types

    def test_create_unknown_shaper_raises(self):
        """Test creating unknown shaper type raises ValueError with helpful message."""
        with pytest.raises(ValueError) as exc_info:
            ShaperFactory.create_shaper("nonexistent", {})

        assert "nonexistent" in str(exc_info.value)
        # Message format might vary slightly after transformation
        assert "Available" in str(exc_info.value)

    def test_register_custom_shaper(self):
        """Test registering a custom shaper type."""
        from src.core.services.shapers.base_shaper import Shaper

        class CustomShaper(Shaper):
            def _verify_params(self):
                return True

            def __call__(self, df):
                return df

        # Register custom shaper
        ShaperFactory.register("customTest", CustomShaper)

        # Verify it's available
        assert "customTest" in ShaperFactory.get_available_types()

        # Create instance
        shaper = ShaperFactory.create_shaper("customTest", {})
        assert isinstance(shaper, CustomShaper)

        # Cleanup - remove from registry
        del ShaperFactory._registry["customTest"]
