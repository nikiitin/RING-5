"""
Tests for AxisSpec and AxesSpec — construction, serialization, round-trip.

Covers:
  - Default construction with sensible defaults
  - New Step 7 fields: tick_font_color, label_standoff, title_vshift,
    axis_line_color, axis_line_width
  - Round-trip fidelity via to_dict()/from_dict()
  - AxesSpec group label fields
  - Sentinel values for new fields
"""

from src.core.visualization.axis_spec import AxesSpec, AxisSpec


class TestAxisSpecDefaults:
    """Test default values for all AxisSpec fields."""

    def test_default_label_fields(self) -> None:
        spec = AxisSpec()
        assert spec.label == ""
        assert spec.label_pad == 10.0
        assert spec.label_position == 0.5
        assert spec.label_standoff == -1  # sentinel
        assert spec.title_vshift == 0.0

    def test_default_tick_fields(self) -> None:
        spec = AxisSpec()
        assert spec.tick_angle == 0.0
        assert spec.tick_pad == 5.0
        assert spec.tick_ha == "center"
        assert spec.tick_offset == 0.0
        assert spec.tick_values is None
        assert spec.tick_text is None
        assert spec.tick_font_color == ""
        assert spec.show_tick_labels is True
        assert spec.dtick is None

    def test_default_grid_fields(self) -> None:
        spec = AxisSpec()
        assert spec.show_grid is True
        assert spec.grid_color == "#E5E5E5"
        assert spec.grid_width == 1.0
        assert spec.axis_color == "#444"
        assert spec.axis_line_color == ""
        assert spec.axis_line_width == 1.0

    def test_default_range_fields(self) -> None:
        spec = AxisSpec()
        assert spec.range is None
        assert spec.scale == "linear"
        assert spec.margin == 0.02
        assert spec.automargin is True


class TestAxisSpecStep7Fields:
    """Test the 5 new fields added in Step 7."""

    def test_tick_font_color_custom(self) -> None:
        spec = AxisSpec(tick_font_color="#FF0000")
        assert spec.tick_font_color == "#FF0000"

    def test_label_standoff_custom(self) -> None:
        spec = AxisSpec(label_standoff=20)
        assert spec.label_standoff == 20

    def test_label_standoff_sentinel(self) -> None:
        """Sentinel -1 means 'auto/inherit'."""
        spec = AxisSpec()
        assert spec.label_standoff == -1

    def test_title_vshift_custom(self) -> None:
        spec = AxisSpec(title_vshift=-0.05)
        assert spec.title_vshift == -0.05

    def test_axis_line_color_custom(self) -> None:
        spec = AxisSpec(axis_line_color="#000000")
        assert spec.axis_line_color == "#000000"

    def test_axis_line_width_custom(self) -> None:
        spec = AxisSpec(axis_line_width=2.5)
        assert spec.axis_line_width == 2.5


class TestAxisSpecRoundTrip:
    """Test to_dict/from_dict round-trip for AxisSpec."""

    def test_default_round_trip(self) -> None:
        spec = AxisSpec()
        restored = AxisSpec.from_dict(spec.to_dict())
        assert restored.label == spec.label
        assert restored.tick_font_color == spec.tick_font_color
        assert restored.label_standoff == spec.label_standoff
        assert restored.title_vshift == spec.title_vshift
        assert restored.axis_line_color == spec.axis_line_color
        assert restored.axis_line_width == spec.axis_line_width

    def test_custom_round_trip(self) -> None:
        spec = AxisSpec(
            label="Benchmark",
            tick_angle=45.0,
            tick_font_color="#333",
            label_standoff=15,
            title_vshift=-0.03,
            axis_line_color="blue",
            axis_line_width=2.0,
            dtick=0.5,
            scale="log",
        )
        restored = AxisSpec.from_dict(spec.to_dict())
        assert restored.label == "Benchmark"
        assert restored.tick_angle == 45.0
        assert restored.tick_font_color == "#333"
        assert restored.label_standoff == 15
        assert restored.title_vshift == -0.03
        assert restored.axis_line_color == "blue"
        assert restored.axis_line_width == 2.0
        assert restored.dtick == 0.5
        assert restored.scale == "log"

    def test_unknown_keys_ignored(self) -> None:
        """from_dict should ignore keys not in the dataclass."""
        data = {"label": "X", "unknown_field": True, "another": 42}
        spec = AxisSpec.from_dict(data)
        assert spec.label == "X"


class TestAxesSpecDefaults:
    """Test AxesSpec container defaults."""

    def test_default_construction(self) -> None:
        axes = AxesSpec()
        assert isinstance(axes.x, AxisSpec)
        assert isinstance(axes.y, AxisSpec)
        assert axes.y2 is None

    def test_group_label_defaults(self) -> None:
        axes = AxesSpec()
        assert axes.group_label_offset == -0.12
        assert axes.group_label_alternate is True
        assert axes.group_label_alt_spacing == 0.05
        assert axes.group_order is None


class TestAxesSpecRoundTrip:
    """Test AxesSpec round-trip with new AxisSpec fields."""

    def test_round_trip_with_step7_fields(self) -> None:
        axes = AxesSpec(
            x=AxisSpec(
                label="Benchmarks",
                tick_font_color="#444",
                label_standoff=10,
                title_vshift=-0.02,
            ),
            y=AxisSpec(
                label="Speedup",
                axis_line_color="black",
                axis_line_width=1.5,
            ),
            y2=AxisSpec(
                label="IPC",
                tick_font_color="#888",
            ),
        )
        data = axes.to_dict()
        restored = AxesSpec.from_dict(data)

        assert restored.x.label == "Benchmarks"
        assert restored.x.tick_font_color == "#444"
        assert restored.x.label_standoff == 10
        assert restored.x.title_vshift == -0.02
        assert restored.y.axis_line_color == "black"
        assert restored.y.axis_line_width == 1.5
        assert restored.y2 is not None
        assert restored.y2.label == "IPC"
        assert restored.y2.tick_font_color == "#888"

    def test_round_trip_without_y2(self) -> None:
        axes = AxesSpec(
            x=AxisSpec(label="X"),
            y=AxisSpec(label="Y"),
        )
        data = axes.to_dict()
        restored = AxesSpec.from_dict(data)
        assert restored.y2 is None
        assert restored.x.label == "X"

    def test_group_order_round_trip(self) -> None:
        axes = AxesSpec(group_order=["A", "B", "C"])
        data = axes.to_dict()
        restored = AxesSpec.from_dict(data)
        assert restored.group_order == ["A", "B", "C"]
