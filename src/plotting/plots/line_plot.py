"""
Line plot implementation.
"""
import seaborn as sns
import matplotlib.pyplot as plt

from src.plotting.base.plot import Plot


class LinePlot(Plot):
    """Line plot implementation using seaborn."""
    
    def _validate_config(self) -> None:
        """Validate required configuration fields."""
        if 'x' not in self.data_config:
            raise ValueError("Line plot requires 'x' field in data config")
        if 'y' not in self.data_config:
            raise ValueError("Line plot requires 'y' field in data config")
        if 'filename' not in self.output_config:
            raise ValueError("Line plot requires 'filename' in output config")
    
    def render(self, ax: plt.Axes) -> None:
        """Render line plot on axes."""
        x = self.data_config['x']
        y = self.data_config['y']
        hue = self.data_config.get('hue')
        style = self.data_config.get('style')
        marker = self.data_config.get('marker', 'o')
        
        sns.lineplot(
            data=self.data,
            x=x,
            y=y,
            hue=hue,
            style=style,
            ax=ax,
            marker=marker
        )
