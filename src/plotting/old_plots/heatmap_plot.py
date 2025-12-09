"""
Heatmap plot implementation.
"""
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd

from src.plotting.base.plot import Plot


class HeatmapPlot(Plot):
    """Heatmap plot implementation using seaborn."""
    
    def _validate_config(self) -> None:
        """Validate required configuration fields."""
        if 'x' not in self.data_config:
            raise ValueError("Heatmap requires 'x' field in data config")
        if 'y' not in self.data_config:
            raise ValueError("Heatmap requires 'y' field in data config")
        if 'filename' not in self.output_config:
            raise ValueError("Heatmap requires 'filename' in output config")
    
    def render(self, ax: plt.Axes) -> None:
        """Render heatmap on axes."""
        x = self.data_config['x']
        y = self.data_config['y']
        value = self.data_config.get('value', self.data_config['y'])
        
        # Pivot data for heatmap
        pivot_data = self.data.pivot(index=y, columns=x, values=value)
        
        # Heatmap parameters
        annot = self.data_config.get('annot', True)
        fmt = self.data_config.get('fmt', '.2f')
        cmap = self.data_config.get('cmap', 'YlOrRd')
        cbar_label = self.data_config.get('cbar_label', value)
        
        sns.heatmap(
            pivot_data,
            annot=annot,
            fmt=fmt,
            cmap=cmap,
            ax=ax,
            cbar_kws={'label': cbar_label}
        )
