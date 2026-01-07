
import pytest
from src.web.services.plot_service import PlotService
from src.web.state_manager import StateManager
from src.plotting.base_plot import BasePlot

class TestPlotLifecycle:
    
    def setup_method(self):
        StateManager.initialize()
        # Ensure clean state
        StateManager.set_plots([])
        StateManager.set_plot_counter(0)

    def test_create_plot(self):
        plot = PlotService.create_plot("Test Plot", "bar")
        
        assert isinstance(plot, BasePlot)
        assert plot.name == "Test Plot"
        assert plot.plot_type == "bar"
        assert plot.plot_id == 0
        
        plots = StateManager.get_plots()
        assert len(plots) == 1
        assert plots[0] == plot
        assert StateManager.get_current_plot_id() == 0

    def test_duplicate_plot(self):
        plot1 = PlotService.create_plot("Original", "line")
        plot1.config = {"x": "my_col"}
        
        plot2 = PlotService.duplicate_plot(plot1)
        
        assert plot2.plot_id != plot1.plot_id
        assert plot2.name == "Original (copy)"
        assert plot2.plot_type == "line"
        assert plot2.config == {"x": "my_col"}
        
        plots = StateManager.get_plots()
        assert len(plots) == 2

    def test_change_plot_type(self):
        plot = PlotService.create_plot("My Plot", "bar")
        plot.config = {"some": "config"}
        
        new_plot = PlotService.change_plot_type(plot, "line")
        
        assert new_plot.plot_type == "line"
        assert new_plot.plot_id == plot.plot_id # ID should be preserved
        assert new_plot.name == "My Plot"
        assert new_plot.config == {} # Config resets on type change
        
        # Verify state is updated
        plots = StateManager.get_plots()
        current_plot = next(p for p in plots if p.plot_id == plot.plot_id)
        assert current_plot.plot_type == "line"

    def test_delete_plot(self):
        p1 = PlotService.create_plot("P1", "bar")
        p2 = PlotService.create_plot("P2", "bar")
        
        PlotService.delete_plot(p1.plot_id)
        
        plots = StateManager.get_plots()
        assert len(plots) == 1
        assert plots[0].plot_id == p2.plot_id
