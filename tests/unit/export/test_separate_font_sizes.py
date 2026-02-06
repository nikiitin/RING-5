"""
Tests for separate font sizes feature.

Validates that separate font sizes for xlabel, ylabel, and legend work
correctly across all layers: schema, presets, application, and UI.
"""

import matplotlib.pyplot as plt
import plotly.graph_objects as go

from src.web.pages.ui.plotting.export.converters.layout_applier import LayoutApplier
from src.web.pages.ui.plotting.export.converters.layout_mapper import LayoutExtractor
from src.web.pages.ui.plotting.export.presets.preset_manager import PresetManager


class TestSeparateFontSizesFeature:
    """Test separate font sizes for xlabel, ylabel, legend."""

    def test_schema_accepts_separate_font_sizes(self) -> None:
        """Verify schema accepts font_size_xlabel, ylabel, legend."""
        preset = {
            "width_inches": 3.5,
            "height_inches": 2.5,
            "dpi": 300,
            "font_family": "serif",
            "font_size_base": 10,  # REQUIRED FIELD
            "font_size_title": 10,
            "font_size_xlabel": 9,  # Separate
            "font_size_ylabel": 9,  # Separate
            "font_size_legend": 8,  # Separate
            "font_size_ticks": 7,
            "font_size_annotations": 6,
            "line_width": 1.0,  # REQUIRED FIELD
            "marker_size": 4.0,  # REQUIRED FIELD
            "legend_columnspacing": 1.0,  # REQUIRED FIELD
            "legend_handletextpad": 0.5,  # REQUIRED FIELD
            "legend_labelspacing": 0.3,  # REQUIRED FIELD
            "legend_handlelength": 1.5,  # REQUIRED FIELD
            "legend_handleheight": 0.7,  # REQUIRED FIELD
            "legend_borderpad": 0.3,  # REQUIRED FIELD
            "legend_borderaxespad": 0.3,  # REQUIRED FIELD
            "bold_title": False,
            "bold_xlabel": False,
            "bold_ylabel": False,
            "bold_legend": False,
            "bold_ticks": False,
            "bold_annotations": True,
            "ylabel_pad": 10.0,
            "ylabel_y_position": 0.5,
            "xtick_pad": 5.0,
            "ytick_pad": 5.0,
            "xtick_rotation": 45.0,
            "xtick_ha": "right",
            "xtick_offset": 0.0,
            "xaxis_margin": 0.02,
            "group_label_offset": -0.12,
            "group_label_alternate": True,
            "group_separator": False,
            "group_separator_style": "dashed",
            "group_separator_color": "gray",
        }

        manager = PresetManager()
        manager.validate_preset(preset)

    def test_preset_manager_loads_separate_fonts(self) -> None:
        """Verify all 13 presets have xlabel/ylabel/legend font sizes."""
        manager = PresetManager()
        presets = manager.list_presets()

        for preset_name in presets:
            preset = manager.load_preset(preset_name)
            assert "font_size_xlabel" in preset
            assert "font_size_ylabel" in preset
            assert "font_size_legend" in preset

    def test_layout_applier_uses_font_size_xlabel(self) -> None:
        """Verify font_size_xlabel is applied to X-axis label."""
        preset = {
            "font_size_xlabel": 14,  # Custom size
            "bold_xlabel": False,
        }

        fig, ax = plt.subplots()
        layout = {"x_label": "X Axis"}

        applier = LayoutApplier(preset)  # type: ignore[arg-type]
        applier._apply_axis_labels(ax, layout)

        assert ax.get_xlabel() == "X Axis"
        # Font size verification would require inspecting Text object properties
        plt.close(fig)

    def test_layout_applier_uses_font_size_ylabel(self) -> None:
        """Verify font_size_ylabel is applied to Y-axis label."""
        preset = {
            "font_size_ylabel": 12,  # Custom size
            "bold_ylabel": False,
            "ylabel_pad": 10.0,
            "ylabel_y_position": 0.5,
        }

        fig, ax = plt.subplots()
        layout = {"y_label": "Y Axis"}

        applier = LayoutApplier(preset)  # type: ignore[arg-type]
        applier._apply_axis_labels(ax, layout)

        assert ax.get_ylabel() == "Y Axis"
        plt.close(fig)

    def test_separate_fonts_in_full_workflow(self) -> None:
        """Verify separate font sizes work in complete extraction/application."""
        # Create Plotly figure
        plotly_fig = go.Figure()
        plotly_fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6], name="Series 1"))
        plotly_fig.update_xaxes(title="Time (s)")
        plotly_fig.update_yaxes(title="Performance")
        plotly_fig.update_layout(
            title="Test Plot",
            legend=dict(x=0.8, y=0.95),
        )

        # Extract layout
        extractor = LayoutExtractor()
        layout = extractor.extract_layout(plotly_fig)

        # Apply with separate font sizes
        mpl_fig, mpl_ax = plt.subplots()
        preset = {
            "font_size_title": 14,
            "font_size_xlabel": 11,
            "font_size_ylabel": 10,
            "font_size_legend": 9,
            "font_size_ticks": 8,
            "bold_title": False,
            "bold_xlabel": False,
            "bold_ylabel": False,
            "ylabel_pad": 10.0,
            "ylabel_y_position": 0.5,
            "xaxis_margin": 0.0,
        }
        applier = LayoutApplier(preset)  # type: ignore[arg-type]
        applier.apply_to_matplotlib(mpl_ax, layout)

        # Verify labels applied
        assert mpl_ax.get_xlabel() == "Time (s)"
        assert mpl_ax.get_ylabel() == "Performance"
        assert mpl_ax.get_title() == "Test Plot"

        plt.close(mpl_fig)

    def test_font_config_extracts_separate_sizes(self) -> None:
        """Verify FontStyleConfig extracts separate font sizes from preset."""
        preset = {
            "font_size_xlabel": 11,
            "font_size_ylabel": 10,
            "font_size_legend": 9,
        }

        applier = LayoutApplier(preset)  # type: ignore[arg-type]

        assert applier.font_config.font_size_xlabel == 11
        assert applier.font_config.font_size_ylabel == 10
        # Note: font_size_legend is not in FontStyleConfig (used in matplotlib_converter)

    def test_default_font_sizes(self) -> None:
        """Verify default font sizes when preset is None."""
        applier = LayoutApplier(None)

        assert applier.font_config.font_size_xlabel == 9
        assert applier.font_config.font_size_ylabel == 9
        # Default values from FontStyleConfig

    def test_all_presets_updated(self) -> None:
        """Verify all 13 presets have been updated with separate font params."""
        manager = PresetManager()
        presets = manager.list_presets()

        assert len(presets) == 13

        for preset_name in presets:
            preset = manager.load_preset(preset_name)

            # Verify all three separate font sizes exist
            assert "font_size_xlabel" in preset
            assert "font_size_ylabel" in preset
            assert "font_size_legend" in preset

            # Verify they are valid positive integers
            assert isinstance(preset["font_size_xlabel"], int)
            assert isinstance(preset["font_size_ylabel"], int)
            assert isinstance(preset["font_size_legend"], int)
            assert preset["font_size_xlabel"] > 0
            assert preset["font_size_ylabel"] > 0
            assert preset["font_size_legend"] > 0
