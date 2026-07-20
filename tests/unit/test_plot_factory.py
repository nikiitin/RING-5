"""Tests for PlotFactory metadata and registration hardening."""

import pytest

from src.web.pages.ui.plotting.plot_factory import PlotFactory, PlotTypeMetadata

EXPECTED_PLOT_TYPES = {
    "area",
    "bar",
    "box",
    "dual_axis_bar_dot",
    "ecdf",
    "grouped_bar",
    "heatmap",
    "stacked_bar",
    "grouped_stacked_bar",
    "histogram",
    "line",
    "radar",
    "scatter",
    "violin",
    "waterfall",
}

METADATA_REQUIRED_KEYS = {"display_name", "icon", "category"}


class TestPlotFactoryRegistration:
    """Tests for plot type registration."""

    # [test->req~ring5.extension.plot-registry~1]

    def test_all_plot_types_registered(self) -> None:
        """Every built-in plot type is registered in the factory."""
        available = PlotFactory.get_available_plot_types()
        assert len(available) == 15
        assert set(available) == EXPECTED_PLOT_TYPES

    def test_register_plot_type_rejects_non_baseplot_class(self) -> None:
        """register_plot_type raises ValueError for non-BasePlot classes."""

        class NotAPlot:
            pass

        with pytest.raises(ValueError, match="must be a subclass of BasePlot"):
            PlotFactory.register_plot_type("bad", NotAPlot)  # type: ignore[arg-type]


class TestPlotFactoryMetadata:
    """Tests for plot type metadata."""

    # [test->req~ring5.extension.plot-registry~1]

    def test_metadata_present_for_all_types(self) -> None:
        """Metadata is present for every registered plot type."""
        metadata = PlotFactory.get_plot_metadata()
        available = set(PlotFactory.get_available_plot_types())
        assert set(metadata.keys()) == available

    def test_get_plot_metadata_returns_dict(self) -> None:
        """get_plot_metadata returns a dict with correct structure."""
        metadata = PlotFactory.get_plot_metadata()
        assert isinstance(metadata, dict)
        assert len(metadata) == 15

    def test_each_metadata_entry_has_required_keys(self) -> None:
        """Each metadata entry contains display_name, icon, and category."""
        metadata = PlotFactory.get_plot_metadata()
        for plot_type, entry in metadata.items():
            assert METADATA_REQUIRED_KEYS <= set(entry.keys()), (
                f"Metadata for '{plot_type}' is missing keys: "
                f"{METADATA_REQUIRED_KEYS - set(entry.keys())}"
            )

    def test_metadata_values_are_strings(self) -> None:
        """All metadata values are non-empty strings."""
        metadata = PlotFactory.get_plot_metadata()
        for plot_type, entry in metadata.items():
            for key in METADATA_REQUIRED_KEYS:
                value = entry[key]  # type: ignore[literal-required]
                assert isinstance(
                    value, str
                ), f"Metadata '{key}' for '{plot_type}' should be str, got {type(value)}"
                assert len(value) > 0, f"Metadata '{key}' for '{plot_type}' should not be empty"

    def test_metadata_categories_are_valid(self) -> None:
        """All category values are one of the allowed categories."""
        valid_categories = {"basic", "comparison", "distribution"}
        metadata = PlotFactory.get_plot_metadata()
        for plot_type, entry in metadata.items():
            assert (
                entry["category"] in valid_categories
            ), f"'{plot_type}' has invalid category '{entry['category']}'"

    def test_get_plot_metadata_returns_copy(self) -> None:
        """get_plot_metadata returns a copy, not a reference to the internal dict."""
        metadata1 = PlotFactory.get_plot_metadata()
        metadata2 = PlotFactory.get_plot_metadata()
        assert metadata1 is not metadata2

    def test_register_plot_type_with_metadata(self) -> None:
        """register_plot_type stores metadata when provided."""
        # Find a concrete subclass to use for registration
        from src.web.pages.ui.plotting.types import BarPlot

        test_metadata: PlotTypeMetadata = {
            "display_name": "Test Plot",
            "icon": "test_icon",
            "category": "basic",
        }

        try:
            PlotFactory.register_plot_type("test_custom", BarPlot, metadata=test_metadata)
            result = PlotFactory.get_plot_metadata()
            assert "test_custom" in result
            assert result["test_custom"] == test_metadata
        finally:
            # Clean up: remove the test registration
            PlotFactory._plot_classes.pop("test_custom", None)
            PlotFactory._plot_metadata.pop("test_custom", None)
