"""
Tests for LegendConfig — uniform legend model for primary/secondary/boxed.

Covers:
  - Default construction and role assignment
  - LegendSpacingConfig construction and serialization
  - to_dict/from_dict round-trip
  - All three roles (primary, secondary, boxed)
"""

from src.core.models.visualization.legend_config import (
    LegendConfig,
    LegendSpacingConfig,
)


class TestLegendSpacingSpec:
    """Test LegendSpacingConfig independently."""

    def test_defaults(self) -> None:
        spacing = LegendSpacingConfig()
        assert spacing.columnspacing == 0.5
        assert spacing.handletextpad == 0.3
        assert spacing.labelspacing == 0.2
        assert spacing.handlelength == 1.0
        assert spacing.handleheight == 0.7
        assert spacing.borderpad == 0.2
        assert spacing.borderaxespad == 0.5

    def test_custom_values(self) -> None:
        spacing = LegendSpacingConfig(
            columnspacing=2.0,
            handletextpad=0.5,
            borderpad=1.0,
        )
        assert spacing.columnspacing == 2.0
        assert spacing.handletextpad == 0.5
        assert spacing.borderpad == 1.0

    def test_to_dict(self) -> None:
        spacing = LegendSpacingConfig(columnspacing=1.5)
        d = spacing.to_dict()
        assert d["columnspacing"] == 1.5
        assert isinstance(d, dict)

    def test_from_dict(self) -> None:
        data = {"columnspacing": 2.0, "borderpad": 0.8}
        spacing = LegendSpacingConfig.from_dict(data)
        assert spacing.columnspacing == 2.0
        assert spacing.borderpad == 0.8
        # Underscore defaults preserved
        assert spacing.handletextpad == 0.3

    def test_from_dict_ignores_unknown_keys(self) -> None:
        data = {"columnspacing": 1.0, "unknown_key": 99}
        spacing = LegendSpacingConfig.from_dict(data)
        assert spacing.columnspacing == 1.0


class TestLegendSpec:
    """Test LegendConfig construction and serialization."""

    def test_default_primary(self) -> None:
        legend = LegendConfig()
        assert legend.role == "primary"
        assert legend.visible is True
        assert legend.font_size == 8
        assert legend.bold is False
        assert legend.ncol == 1
        assert legend.orientation == "vertical"

    def test_secondary_legend(self) -> None:
        legend = LegendConfig(role="secondary", font_size=-1)
        assert legend.role == "secondary"
        assert legend.font_size == -1

    def test_boxed_legend(self) -> None:
        legend = LegendConfig(
            role="boxed",
            font_size=-1,
            number_fontsize=-1,
            text_fontsize=-1,
        )
        assert legend.role == "boxed"
        assert legend.number_fontsize == -1
        assert legend.text_fontsize == -1

    def test_custom_position(self) -> None:
        legend = LegendConfig(
            custom_position=True,
            position_x=0.8,
            position_y=0.95,
            anchor_x="right",
            anchor_y="top",
        )
        assert legend.custom_position is True
        assert legend.position_x == 0.8
        assert legend.anchor_x == "right"

    def test_to_dict(self) -> None:
        legend = LegendConfig(
            role="primary",
            font_size=12,
            bold=True,
            spacing=LegendSpacingConfig(columnspacing=2.0),
        )
        d = legend.to_dict()

        assert d["role"] == "primary"
        assert d["font_size"] == 12
        assert d["bold"] is True
        assert isinstance(d["spacing"], dict)
        assert d["spacing"]["columnspacing"] == 2.0

    def test_from_dict(self) -> None:
        data = {
            "role": "secondary",
            "font_size": 10,
            "bold": False,
            "spacing": {"columnspacing": 1.5, "borderpad": 0.4},
            "position_x": 0.5,
        }
        legend = LegendConfig.from_dict(data)

        assert legend.role == "secondary"
        assert legend.font_size == 10
        assert legend.spacing.columnspacing == 1.5
        assert legend.spacing.borderpad == 0.4
        assert legend.position_x == 0.5

    def test_round_trip(self) -> None:
        """to_dict then from_dict should preserve all values."""
        original = LegendConfig(
            role="boxed",
            font_size=14,
            bold=True,
            ncol=2,
            orientation="horizontal",
            custom_position=True,
            position_x=0.3,
            position_y=0.7,
            anchor_x="center",
            anchor_y="top",
            bgcolor="#FFFFFF",
            border_width=1.5,
            number_fontsize=10,
            text_fontsize=12,
            spacing=LegendSpacingConfig(
                columnspacing=2.0,
                handletextpad=0.5,
            ),
        )

        data = original.to_dict()
        restored = LegendConfig.from_dict(data)

        assert restored.role == "boxed"
        assert restored.font_size == 14
        assert restored.bold is True
        assert restored.ncol == 2
        assert restored.orientation == "horizontal"
        assert restored.custom_position is True
        assert restored.position_x == 0.3
        assert restored.number_fontsize == 10
        assert restored.text_fontsize == 12
        assert restored.spacing.columnspacing == 2.0
        assert restored.spacing.handletextpad == 0.5

    def test_spacing_isolation(self) -> None:
        """Two LegendSpecs should have independent spacing."""
        legend1 = LegendConfig(spacing=LegendSpacingConfig(columnspacing=1.0))
        legend2 = LegendConfig(spacing=LegendSpacingConfig(columnspacing=2.0))

        assert legend1.spacing.columnspacing == 1.0
        assert legend2.spacing.columnspacing == 2.0

        # Modify one — the other should be unaffected
        legend1.spacing.columnspacing = 99.0
        assert legend2.spacing.columnspacing == 2.0


# ────────────────────────────────────────────────────────────────────
# Step 8 — col_width, order, trace_distribution
# ────────────────────────────────────────────────────────────────────


class TestLegendSpecStep8Fields:
    """Test the 3 new fields added in Step 8."""

    def test_col_width_default_sentinel(self) -> None:
        """Sentinel -1.0 means 'auto column width'."""
        spec = LegendConfig()
        assert spec.col_width == -1.0

    def test_col_width_custom(self) -> None:
        spec = LegendConfig(col_width=120.0)
        assert spec.col_width == 120.0

    def test_order_default_normal(self) -> None:
        spec = LegendConfig()
        assert spec.order == "normal"

    def test_order_reversed(self) -> None:
        spec = LegendConfig(order="reversed")
        assert spec.order == "reversed"

    def test_trace_distribution_empty_default(self) -> None:
        spec = LegendConfig()
        assert spec.trace_distribution == ""

    def test_trace_distribution_custom(self) -> None:
        spec = LegendConfig(trace_distribution="0,1,2")
        assert spec.trace_distribution == "0,1,2"

    def test_step8_fields_in_to_dict(self) -> None:
        spec = LegendConfig(col_width=100.0, order="reversed", trace_distribution="1,3")
        d = spec.to_dict()
        assert d["col_width"] == 100.0
        assert d["order"] == "reversed"
        assert d["trace_distribution"] == "1,3"

    def test_step8_round_trip(self) -> None:
        spec = LegendConfig(
            role="primary",
            col_width=80.0,
            order="reversed",
            trace_distribution="0,2,4",
            ncol=3,
        )
        data = spec.to_dict()
        restored = LegendConfig.from_dict(data)
        assert restored.col_width == 80.0
        assert restored.order == "reversed"
        assert restored.trace_distribution == "0,2,4"
        assert restored.ncol == 3
