from src.core.state.repository_state_manager import RepositoryStateManager
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.plot_service import PlotService


class TestPlotLifecycle:

    def setup_method(self):
        self.state_manager = RepositoryStateManager()
        # Ensure clean state
        self.state_manager.clear_all()

    def test_create_plot(self):
        plot = PlotService.create_plot("Test Plot", "bar", self.state_manager)

        assert isinstance(plot, BasePlot)
        assert plot.name == "Test Plot"
        assert plot.plot_type == "bar"
        assert plot.plot_id == 0

        plots = self.state_manager.get_plots()
        assert len(plots) == 1
        assert plots[0] == plot
        assert self.state_manager.get_current_plot_id() == 0

    def test_duplicate_plot(self):
        plot1 = PlotService.create_plot("Original", "line", self.state_manager)
        plot1.config = {"x": "my_col"}

        plot2 = PlotService.duplicate_plot(plot1, self.state_manager)

        assert plot2.plot_id != plot1.plot_id
        assert plot2.name == "Original (copy)"
        assert plot2.plot_type == "line"
        assert plot2.config == {"x": "my_col"}

        plots = self.state_manager.get_plots()
        assert len(plots) == 2

    def test_change_plot_type(self):
        plot = PlotService.create_plot("My Plot", "bar", self.state_manager)
        plot.config = {"some": "config"}

        new_plot = PlotService.change_plot_type(plot, "line", self.state_manager)

        assert new_plot.plot_type == "line"
        assert new_plot.plot_id == plot.plot_id  # ID should be preserved
        assert new_plot.name == "My Plot"
        assert new_plot.config == {}  # Config resets on type change

        # Verify state is updated
        plots = self.state_manager.get_plots()
        current_plot = next(p for p in plots if p.plot_id == plot.plot_id)
        assert current_plot.plot_type == "line"

    def test_delete_plot(self):
        p1 = PlotService.create_plot("P1", "bar", self.state_manager)
        p2 = PlotService.create_plot("P2", "bar", self.state_manager)

        PlotService.delete_plot(p1.plot_id, self.state_manager)

        plots = self.state_manager.get_plots()
        assert len(plots) == 1
        assert plots[0].plot_id == p2.plot_id
