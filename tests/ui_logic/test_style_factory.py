"""Tests for StyleUIFactory — dispatching to type-specific style UIs.

Verifies that the factory returns the correct style UI class
for each plot type, including edge cases and fallback behavior.
"""


class TestStyleUIFactory:
    """Verify factory dispatches to correct style UI implementation."""

    def test_bar_type_returns_bar_ui(self) -> None:
        """'bar' plot type returns BarStyleUI."""
        from src.web.pages.ui.plotting.styles.bar_ui import BarStyleUI
        from src.web.pages.ui.plotting.styles.factory import StyleUIFactory

        result = StyleUIFactory.get_strategy(1, "bar")
        assert isinstance(result, BarStyleUI)

    def test_grouped_bar_returns_bar_ui(self) -> None:
        """'grouped_bar' contains 'bar' → BarStyleUI."""
        from src.web.pages.ui.plotting.styles.bar_ui import BarStyleUI
        from src.web.pages.ui.plotting.styles.factory import StyleUIFactory

        result = StyleUIFactory.get_strategy(1, "grouped_bar")
        assert isinstance(result, BarStyleUI)

    def test_stacked_bar_returns_bar_ui(self) -> None:
        """'stacked_bar' contains 'bar' → BarStyleUI."""
        from src.web.pages.ui.plotting.styles.bar_ui import BarStyleUI
        from src.web.pages.ui.plotting.styles.factory import StyleUIFactory

        result = StyleUIFactory.get_strategy(1, "stacked_bar")
        assert isinstance(result, BarStyleUI)

    def test_grouped_stacked_bar_returns_bar_ui(self) -> None:
        """'grouped_stacked_bar' contains 'bar' → BarStyleUI."""
        from src.web.pages.ui.plotting.styles.bar_ui import BarStyleUI
        from src.web.pages.ui.plotting.styles.factory import StyleUIFactory

        result = StyleUIFactory.get_strategy(1, "grouped_stacked_bar")
        assert isinstance(result, BarStyleUI)

    def test_line_returns_line_ui(self) -> None:
        """'line' plot type returns LineStyleUI."""
        from src.web.pages.ui.plotting.styles.factory import StyleUIFactory
        from src.web.pages.ui.plotting.styles.line_ui import LineStyleUI

        result = StyleUIFactory.get_strategy(1, "line")
        assert isinstance(result, LineStyleUI)

    def test_scatter_returns_scatter_ui(self) -> None:
        """'scatter' plot type returns ScatterStyleUI."""
        from src.web.pages.ui.plotting.styles.factory import StyleUIFactory
        from src.web.pages.ui.plotting.styles.line_ui import ScatterStyleUI

        result = StyleUIFactory.get_strategy(1, "scatter")
        assert isinstance(result, ScatterStyleUI)

    def test_dual_axis_returns_base_ui(self) -> None:
        """'dual_axis_bar_dot' returns BaseStyleUI (combines bar + scatter)."""
        from src.web.pages.ui.plotting.styles.base_ui import BaseStyleUI
        from src.web.pages.ui.plotting.styles.factory import StyleUIFactory

        result = StyleUIFactory.get_strategy(1, "dual_axis_bar_dot")
        assert isinstance(result, BaseStyleUI)
        # Assert it is NOT BarStyleUI (exact BaseStyleUI)
        from src.web.pages.ui.plotting.styles.bar_ui import BarStyleUI

        assert not isinstance(result, BarStyleUI)

    def test_unknown_type_returns_base_ui(self) -> None:
        """Unknown plot types fall back to BaseStyleUI."""
        from src.web.pages.ui.plotting.styles.base_ui import BaseStyleUI
        from src.web.pages.ui.plotting.styles.factory import StyleUIFactory

        result = StyleUIFactory.get_strategy(1, "heatmap_custom")
        assert isinstance(result, BaseStyleUI)

    def test_histogram_returns_base_ui(self) -> None:
        """'histogram' doesn't match bar/line/scatter → BaseStyleUI."""
        from src.web.pages.ui.plotting.styles.base_ui import BaseStyleUI
        from src.web.pages.ui.plotting.styles.factory import StyleUIFactory

        result = StyleUIFactory.get_strategy(1, "histogram")
        assert isinstance(result, BaseStyleUI)

    def test_plot_id_passed_to_instance(self) -> None:
        """Strategy receives correct plot_id."""
        from src.web.pages.ui.plotting.styles.factory import StyleUIFactory

        result = StyleUIFactory.get_strategy(42, "bar")
        assert result.plot_id == 42

    def test_plot_type_passed_to_instance(self) -> None:
        """Strategy receives correct plot_type."""
        from src.web.pages.ui.plotting.styles.factory import StyleUIFactory

        result = StyleUIFactory.get_strategy(1, "grouped_bar")
        assert result.plot_type == "grouped_bar"
