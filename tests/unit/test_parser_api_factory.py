"""Tests for ParserAPIFactory — 0% coverage target."""

import pytest

from src.core.parsing.factory import ParserAPIFactory


class TestParserAPIFactory:
    """Tests for ParserAPIFactory.create and register."""

    def test_create_gem5_returns_parser_api(self) -> None:
        """Default 'gem5' returns Gem5ParserAPI."""
        api = ParserAPIFactory.create("gem5")
        assert hasattr(api, "submit_scan_async")
        assert hasattr(api, "aggregate_scan_results")
        assert hasattr(api, "submit_parse_async")
        assert hasattr(api, "finalize_parsing")

    def test_create_default_is_gem5(self) -> None:
        """No argument defaults to 'gem5'."""
        api = ParserAPIFactory.create()
        assert hasattr(api, "submit_scan_async")

    def test_create_unknown_raises_value_error(self) -> None:
        """Unknown simulator raises ValueError with available list."""
        with pytest.raises(ValueError, match="Unknown simulator.*'nope'"):
            ParserAPIFactory.create("nope")

    def test_register_and_create_custom(self) -> None:
        """Registered custom parser can be created."""

        class FakeParserAPI:
            def submit_scan_async(self, *a, **kw):  # type: ignore[override]
                return []

            def aggregate_scan_results(self, *a, **kw):  # type: ignore[override]
                return {}

            def submit_parse_async(self, *a, **kw):  # type: ignore[override]
                return []

            def finalize_parsing(self, *a, **kw):  # type: ignore[override]
                return ""

        try:
            ParserAPIFactory.register("fake_sim", FakeParserAPI)  # type: ignore[arg-type]
            api = ParserAPIFactory.create("fake_sim")
            assert isinstance(api, FakeParserAPI)
        finally:
            # Clean up registry
            ParserAPIFactory._registry.pop("fake_sim", None)

    def test_unknown_error_includes_custom_in_available(self) -> None:
        """Error message lists both 'gem5' and custom registered backends."""

        class Stub:
            def submit_scan_async(self, *a, **kw):  # type: ignore[override]
                return []

            def aggregate_scan_results(self, *a, **kw):  # type: ignore[override]
                return {}

            def submit_parse_async(self, *a, **kw):  # type: ignore[override]
                return []

            def finalize_parsing(self, *a, **kw):  # type: ignore[override]
                return ""

        try:
            ParserAPIFactory.register("zsim", Stub)
            with pytest.raises(ValueError, match="gem5.*zsim"):
                ParserAPIFactory.create("missing")
        finally:
            ParserAPIFactory._registry.pop("zsim", None)
