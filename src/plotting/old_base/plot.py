"""
Abstract base class for all plot types.
Defines the contract that all plots must follow.
"""
from abc import ABC, abstractmethod
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, Any, Tuple


class Plot(ABC):
    """
    Abstract base class for all plot types.
    
    Follows Single Responsibility Principle: each plot type handles its own rendering logic.
    """
    
    def __init__(self, data: pd.DataFrame, config: Dict[str, Any]):
        """
        Initialize plot with data and configuration.
        
        Args:
            data: DataFrame containing plot data
            config: Plot configuration dictionary with 'data', 'style', 'output' sections
        """
        self.data = data
        self.config = config
        self.data_config = config.get('data', {})
        self.style_config = config.get('style', {})
        self.output_config = config.get('output', {})
        
        # Validate configuration
        self._validate_config()
    
    @abstractmethod
    def _validate_config(self) -> None:
        """
        Validate plot configuration.
        Subclasses should check for required fields.
        
        Raises:
            ValueError: If configuration is invalid
        """
        pass
    
    @abstractmethod
    def render(self, ax: plt.Axes) -> None:
        """
        Render the plot on the given axes.
        
        This is the core method that each plot type must implement.
        It should use the matplotlib/seaborn API to draw on the axes.
        
        Args:
            ax: Matplotlib axes to render on
        """
        pass
    
    def get_figure_size(self) -> Tuple[float, float]:
        """
        Get figure size from configuration or use defaults.
        
        Returns:
            Tuple of (width, height) in inches
        """
        width = self.style_config.get('width', 10)
        height = self.style_config.get('height', 6)
        return (width, height)
    
    def get_output_path(self) -> str:
        """
        Get the output file path including format extension.
        
        Returns:
            Full path to output file
        """
        filename = self.output_config['filename']
        format_type = self.output_config.get('format', 'png')
        return f"{filename}.{format_type}"
    
    def __str__(self) -> str:
        """String representation for debugging."""
        return f"{self.__class__.__name__}(output={self.get_output_path()})"
