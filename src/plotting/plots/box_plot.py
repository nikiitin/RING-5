"""
Box plot implementation.
"""
import seaborn as sns
import matplotlib.pyplot as plt

from src.plotting.base.plot import Plot


class BoxPlot(Plot):
    """Box plot implementation using seaborn."""
    
    def _validate_config(self) -> None:
        """Validate required configuration fields."""
        if 'x' not in self.data_config:
            raise ValueError("Box plot requires 'x' field in data config")
        if 'y' not in self.data_config:
            raise ValueError("Box plot requires 'y' field in data config")
        if 'filename' not in self.output_config:
            raise ValueError("Box plot requires 'filename' in output config")
    
    def render(self, ax: plt.Axes) -> None:
        """Render box plot on axes."""
        x = self.data_config['x']
        y = self.data_config['y']
        hue = self.data_config.get('hue')
        
        sns.boxplot(
            data=self.data,
            x=x,
            y=y,
            hue=hue,
            ax=ax
        )
