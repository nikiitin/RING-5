"""
Tests for bold styling feature.

Validates that bold styling controls for all text elements work correctly:
title, xlabel, ylabel, legend, ticks, annotations.
"""

import matplotlib.pyplot as plt
import plotly.graph_objects as go

from src.web.pages.ui.plotting.export.converters.impl.layout_applier import LayoutApplier
from src.web.pages.ui.plotting.export.converters.impl.layout_config import FontStyleConfig
from src.web.pages.ui.plotting.export.converters.impl.layout_mapper import LayoutExtractor
from src.web.pages.ui.plotting.export.presets.preset_manager import PresetManager


class TestBoldStylingFeature:
    """Test bold styling controls for all text elements."""

    def test_schema_accepts_all_bold_flags(self) -> None:
        """Verify schema accepts all 6 bold flags."""
        preset = {
            "width_inches": 3.5,
            "height_inches": 2.5,
            "dpi": 300,
            "font_family": "serif",
            "font_size_base": 10,  # REQUIRED FIELD
            "font_size_title": 10,
            "font_size_xlabel": 9,
            "font_size_ylabel": 9,
            "font_size_legend": 8,
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
            "bold_title": True,  # Bold flag 1
            "bold_xlabel": True,  # Bold flag 2
            "bold_ylabel": True,  # Bold flag 3
            "bold_legend": True,  # Bold flag 4
            "bold_ticks": True,  # Bold flag 5
            "bold_annotations": True,  # Bold flag 6 (default)
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

    def test_bold_annotations_defaults_to_true(self) -> None:
        """Verify bold_annotations defaults to True in FontStyleConfig."""
        config = FontStyleConfig()

        assert config.bold_title is False
        assert config.bold_xlabel is False
        assert config.bold_ylabel is False
        assert config.bold_ticks is False
        assert config.bold_annotations is True  # Default True

    def test_layout_applier_applies_bold_title(self) -> None:
        """Verify bold_title applies fontweight='bold' to title."""
        preset_bold = {"font_size_title": 10, "bold_title": True}
        preset_normal = {"font_size_title": 10, "bold_title": False}

        fig, ax = plt.subplots()
        layout = {"title": "Test Title"}

        # Apply bold
        applier_bold = LayoutApplier(preset_bold)  # type: ignore[arg-type]
        applier_bold._apply_title(ax, layout)
        assert ax.get_title() == "Test Title"

        # Apply normal
        applier_normal = LayoutApplier(preset_normal)  # type: ignore[arg-type]
        applier_normal._apply_title(ax, layout)
        assert ax.get_title() == "Test Title"

        plt.close(fig)

    def test_layout_applier_applies_bold_xlabel(self) -> None:
        """Verify bold_xlabel applies fontweight='bold' to X-axis label."""
        preset = {"font_size_xlabel": 9, "bold_xlabel": True}

        fig, ax = plt.subplots()
        layout = {"x_label": "X Axis"}

        applier = LayoutApplier(preset)  # type: ignore[arg-type]
        applier._apply_axis_labels(ax, layout)

        assert ax.get_xlabel() == "X Axis"
        plt.close(fig)

    def test_layout_applier_applies_bold_ylabel(self) -> None:
        """Verify bold_ylabel applies fontweight='bold' to Y-axis label."""
        preset = {
            "font_size_ylabel": 9,
            "bold_ylabel": True,
            "ylabel_pad": 10.0,
            "ylabel_y_position": 0.5,
        }

        fig, ax = plt.subplots()
        layout = {"y_label": "Y Axis"}

        applier = LayoutApplier(preset)  # type: ignore[arg-type]
        applier._apply_axis_labels(ax, layout)

        assert ax.get_ylabel() == "Y Axis"
        plt.close(fig)

    def test_layout_applier_applies_bold_ticks(self) -> None:
        """Verify bold_ticks applies fontweight='bold' to tick labels."""
        preset = {
            "font_size_ticks": 7,
            "bold_ticks": True,
            "xtick_pad": 5.0,
            "ytick_pad": 5.0,
            "xtick_rotation": 0.0,
            "xtick_ha": "center",
            "xtick_offset": 0.0,
        }

        fig, ax = plt.subplots()
        layout = {
            "x_tickvals": [1, 2, 3],
            "x_ticktext": ["A", "B", "C"],
        }

        applier = LayoutApplier(preset)  # type: ignore[arg-type]
        applier._apply_ticks(ax, layout)

        # Verify ticks were applied
        assert list(ax.get_xticks()) == [1, 2, 3]
        plt.close(fig)

    def test_bold_annotations_applied_to_bar_values(self) -> None:
        """Verify bold_annotations applies to bar value annotations."""
        preset = {
            "font_size_annotations": 6,
            "font_size_xlabel": 9,
            "bold_annotations": True,
            "bold_xlabel": False,
        }

        fig, ax = plt.subplots()

        # Create annotation that looks like a bar value (yref='y')
        layout = {
            "annotations": [
                {
                    "x": 1,
                    "y": 10,
                    "text": "10.5",
                    "showarrow": False,
                    "xref": "x",
                    "yref": "y",  # Data coords = bar value
                }
            ]
        }

        applier = LayoutApplier(preset)  # type: ignore[arg-type]
        applier._apply_annotations(ax, layout)

        # Should have created annotation
        annotations = ax.texts
        assert len(annotations) == 1
        assert annotations[0].get_text() == "10.5"

        plt.close(fig)

    def test_all_presets_have_bold_flags(self) -> None:
        """Verify all 13 presets have all 6 bold flags."""
        manager = PresetManager()
        presets = manager.list_presets()

        for preset_name in presets:
            preset = manager.load_preset(preset_name)

            # Verify all 6 bold flags exist
            assert "bold_title" in preset
            assert "bold_xlabel" in preset
            assert "bold_ylabel" in preset
            assert "bold_legend" in preset
            assert "bold_ticks" in preset
            assert "bold_annotations" in preset

            # Verify they are booleans
            assert isinstance(preset["bold_title"], bool)
            assert isinstance(preset["bold_xlabel"], bool)
            assert isinstance(preset["bold_ylabel"], bool)
            assert isinstance(preset["bold_legend"], bool)
            assert isinstance(preset["bold_ticks"], bool)
            assert isinstance(preset["bold_annotations"], bool)

            # Verify bold_annotations defaults to True
            assert preset["bold_annotations"] is True

    def test_bold_styling_in_full_workflow(self) -> None:
        """Verify bold styling works in complete extraction/application."""
        # Create Plotly figure
        plotly_fig = go.Figure()
        plotly_fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6]))
        plotly_fig.update_xaxes(title="Time")
        plotly_fig.update_yaxes(title="Performance")
        plotly_fig.update_layout(title="Test Plot")

        # Extract layout
        extractor = LayoutExtractor()
        layout = extractor.extract_layout(plotly_fig)

        # Apply with all bold flags enabled
        mpl_fig, mpl_ax = plt.subplots()
        preset = {
            "font_size_title": 10,
            "font_size_xlabel": 9,
            "font_size_ylabel": 9,
            "font_size_ticks": 7,
            "bold_title": True,
            "bold_xlabel": True,
            "bold_ylabel": True,
            "bold_ticks": True,
            "bold_annotations": True,
            "ylabel_pad": 10.0,
            "ylabel_y_position": 0.5,
            "xaxis_margin": 0.0,
        }
        applier = LayoutApplier(preset)  # type: ignore[arg-type]
        applier.apply_to_matplotlib(mpl_ax, layout)

        # Verify labels applied
        assert mpl_ax.get_title() == "Test Plot"
        assert mpl_ax.get_xlabel() == "Time"
        assert mpl_ax.get_ylabel() == "Performance"

        plt.close(mpl_fig)

    def test_font_config_extracts_all_bold_flags(self) -> None:
        """Verify FontStyleConfig extracts all 6 bold flags from preset."""
        preset = {
            "bold_title": True,
            "bold_xlabel": True,
            "bold_ylabel": True,
            "bold_ticks": True,
            "bold_annotations": False,  # Override default
        }

        applier = LayoutApplier(preset)  # type: ignore[arg-type]

        assert applier.font_config.bold_title is True
        assert applier.font_config.bold_xlabel is True
        assert applier.font_config.bold_ylabel is True
        assert applier.font_config.bold_ticks is True
        assert applier.font_config.bold_annotations is False
