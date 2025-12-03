"""
PlotWork implementation for multithreaded plotting.
Integrates plotting system with existing multiprocessing infrastructure.
"""
import pandas as pd
from pathlib import Path
from typing import Dict, Any

from src.data_plotter.multiprocessing.plotWork import PlotWork
from src.plotting.factory.plot_factory import PlotFactory
from src.plotting.renderer.plot_renderer import PlotRenderer


class PlotWorkImpl(PlotWork):
    """
    Concrete implementation of PlotWork for multithreaded plot generation.
    
    Follows Dependency Inversion Principle: depends on abstractions (PlotWork, Plot).
    Integrates new plotting architecture with existing multiprocessing pool.
    """
    
    def __init__(self, data_path: str, plot_config: Dict[str, Any]):
        """
        Initialize plot work.
        
        Args:
            data_path: Path to CSV data file
            plot_config: Complete plot configuration dictionary
        """
        super().__init__()
        self.data_path = data_path
        self.plot_config = plot_config
        self.renderer = PlotRenderer(dpi=plot_config.get('output', {}).get('dpi', 300))
    
    def __call__(self) -> None:
        """
        Execute plot generation.
        
        This method is called by the worker process.
        """
        # Load data (happens in worker process)
        # Detect separator automatically or use whitespace
        try:
            data = pd.read_csv(self.data_path)
        except:
            # Try with whitespace separator
            data = pd.read_csv(self.data_path, sep=r'\s+')
        
        # Create plot using factory
        plot = PlotFactory.create_plot(data, self.plot_config)
        
        # Render plot
        self.renderer.render(plot)
    
    def __str__(self) -> str:
        """String representation for debugging."""
        output_file = self.plot_config.get('output', {}).get('filename', 'unknown')
        plot_type = self.plot_config.get('type', 'unknown')
        return f"PlotWork(type={plot_type}, output={output_file})"
