"""
Bar plot implementation.
"""
import seaborn as sns
import matplotlib.pyplot as plt
from typing import Optional

from src.plotting.base.plot import Plot


class BarPlot(Plot):
    """
    Bar plot implementation using seaborn.
    
    Supports grouped bars with hue parameter.
    """
    
    def _validate_config(self) -> None:
        """Validate required configuration fields."""
        if 'x' not in self.data_config:
            raise ValueError("Bar plot requires 'x' field in data config")
        if 'y' not in self.data_config:
            raise ValueError("Bar plot requires 'y' field in data config")
        if 'filename' not in self.output_config:
            raise ValueError("Bar plot requires 'filename' in output config")
    
    def render(self, ax: plt.Axes) -> None:
        """Render bar plot on axes."""
        x = self.data_config['x']
        y = self.data_config['y']
        hue = self.data_config.get('hue')
        
        # Check for error bars
        errorbar = 'sd' if f'{y}_sd' in self.data.columns else None
        
        sns.barplot(
            data=self.data,
            x=x,
            y=y,
            hue=hue,
            ax=ax,
            errorbar=errorbar
        )
