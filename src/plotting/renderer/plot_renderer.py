"""
PlotRenderer handles the actual rendering pipeline.
Follows Single Responsibility Principle: manages the rendering workflow.
"""
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for multiprocessing
import matplotlib.pyplot as plt
from typing import Optional
from pathlib import Path

from src.plotting.base.plot import Plot
from src.plotting.styling.plot_styler import PlotStyler


class PlotRenderer:
    """
    Handles the plot rendering pipeline.
    
    Separates rendering concerns from plot creation logic.
    Responsible for:
    - Creating figure and axes
    - Applying themes
    - Calling plot's render() method
    - Applying styling
    - Saving to file
    """
    
    def __init__(self, dpi: int = 300):
        """
        Initialize renderer.
        
        Args:
            dpi: Dots per inch for saved figures
        """
        self.dpi = dpi
    
    def render(self, plot: Plot) -> None:
        """
        Render a plot and save to file.
        
        This is the main entry point for rendering any plot type.
        
        Args:
            plot: Plot instance to render
        """
        # Get theme
        theme = plot.style_config.get('theme', 'default')
        PlotStyler.apply_theme(theme)
        
        # Create figure and axes
        fig, ax = plt.subplots(figsize=plot.get_figure_size())
        
        try:
            # Let the plot render itself
            plot.render(ax)
            
            # Apply styling to axes
            PlotStyler.configure_axes(ax, plot.style_config)
            
            # Save figure
            output_path = plot.get_output_path()
            self._save_figure(fig, output_path)
            
            print(f"Plot saved to: {output_path}")
            
        finally:
            # Always close figure to free memory
            plt.close(fig)
    
    def _save_figure(self, fig: plt.Figure, output_path: str) -> None:
        """
        Save figure to file.
        
        Args:
            fig: Matplotlib figure
            output_path: Full path including extension
        """
        # Ensure output directory exists
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Get DPI from plot config if available, otherwise use default
        dpi = self.dpi
        
        # Save with tight bounding box to avoid clipping
        fig.savefig(output_path, dpi=dpi, bbox_inches='tight')
