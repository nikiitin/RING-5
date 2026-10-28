"""Extended tests for ShaperFactory and DataParserFactory registries."""

from typing import Any, Literal, Required, TypedDict, cast

import pandas as pd
import pytest

from src.core.services.shapers.definition import ShaperDefinition
from src.core.services.shapers.factory import ShaperFactory


class TestShaperFactoryRegistry:
    """Tests for ShaperFactory registry functionality."""

    # [test->req~ring5.extension.shaper-registry~1]

    def test_get_available_types(self) -> None:
        """Test getting available shaper types."""
        types = ShaperFactory.get_available_types()
        assert isinstance(types, list)
        assert "mean" in types
        assert "columnSelector" in types
        assert "normalize" in types
        assert "sort" in types

    def test_create_unknown_shaper_raises(self) -> None:
        """Test creating unknown shaper type raises ValueError with helpful message."""
        with pytest.raises(ValueError) as exc_info:
            ShaperFactory.create_shaper("nonexistent", cast(Any, {}))

        assert "nonexistent" in str(exc_info.value)
        # Message format might vary slightly after transformation
        assert "Available" in str(exc_info.value)

    def test_register_custom_shaper(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test registering a custom shaper type."""
        from src.core.services.shapers.shaper import Shaper

        class CustomShaper(Shaper):
            def __call__(self, df: Any) -> pd.DataFrame:

                return df

        class CustomConfig(TypedDict):
            type: Required[Literal["customTest"]]

        monkeypatch.setattr(ShaperFactory, "_definitions", dict(ShaperFactory._definitions))
        ShaperFactory.register(
            ShaperDefinition(
                "customTest", CustomShaper, "Custom test", CustomConfig, lambda config: None
            )
        )

        # Verify it's available
        assert "customTest" in ShaperFactory.get_available_types()

        # Create instance
        shaper = ShaperFactory.create_shaper("customTest", cast(Any, {}))
        assert isinstance(shaper, CustomShaper)
