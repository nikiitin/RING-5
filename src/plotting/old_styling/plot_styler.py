"""
Handles plot styling and theme management.
Follows Single Responsibility Principle: only manages visual styling.
"""
import seaborn as sns
import matplotlib.pyplot as plt
from typing import Dict, Any, Optional


class PlotStyler:
    """
    Manages plot styling, themes, and visual configuration.
    
    Separates styling logic from plot rendering logic.
    """
    
    THEMES = {
        'default': 'default',
        'whitegrid': 'whitegrid',
        'darkgrid': 'darkgrid',
        'white': 'white',
        'dark': 'dark',
        'ticks': 'ticks'
    }
    
    @staticmethod
    def apply_theme(theme: str = 'default') -> None:
        """
        Apply seaborn theme globally.
        
        Args:
            theme: Theme name from THEMES dict
        """
        if theme == 'default':
            sns.set_theme()
        elif theme in PlotStyler.THEMES:
            sns.set_style(theme)
        else:
            raise ValueError(f"Unknown theme: {theme}. Available: {list(PlotStyler.THEMES.keys())}")
    
    @staticmethod
    def configure_axes(ax: plt.Axes, style_config: Dict[str, Any]) -> None:
        """
        Configure axes appearance based on style configuration.
        
        Args:
            ax: Matplotlib axes object
            style_config: Style configuration dictionary
        """
        # Title
        if 'title' in style_config and style_config['title']:
            title_fontsize = style_config.get('title_fontsize', 14)
            ax.set_title(style_config['title'], fontsize=title_fontsize, fontweight='bold')
        
        # Axis labels
        if 'xlabel' in style_config and style_config['xlabel']:
            label_fontsize = style_config.get('label_fontsize', 12)
            ax.set_xlabel(style_config['xlabel'], fontsize=label_fontsize)
        
        if 'ylabel' in style_config and style_config['ylabel']:
            label_fontsize = style_config.get('label_fontsize', 12)
            ax.set_ylabel(style_config['ylabel'], fontsize=label_fontsize)
        
        # Axis limits
        if 'xlim' in style_config:
            ax.set_xlim(style_config['xlim'])
        
        if 'ylim' in style_config:
            ax.set_ylim(style_config['ylim'])
        
        # Grid
        if style_config.get('grid', False):
            grid_alpha = style_config.get('grid_alpha', 0.3)
            ax.grid(True, alpha=grid_alpha)
        
        # X-axis rotation
        if 'rotation' in style_config:
            rotation = style_config['rotation']
            ha = style_config.get('ha', 'right') if rotation != 0 else 'center'
            plt.xticks(rotation=rotation, ha=ha)
        
        # Legend
        PlotStyler._configure_legend(ax, style_config)
    
    @staticmethod
    def _configure_legend(ax: plt.Axes, style_config: Dict[str, Any]) -> None:
        """
        Configure legend appearance.
        
        Args:
            ax: Matplotlib axes object
            style_config: Style configuration dictionary
        """
        if 'legend' in style_config:
            legend_cfg = style_config['legend']
            
            if not legend_cfg.get('show', True):
                # Hide legend
                legend = ax.get_legend()
                if legend:
                    legend.remove()
            else:
                # Configure legend
                legend_kwargs = {
                    'loc': legend_cfg.get('location', 'best'),
                    'frameon': legend_cfg.get('frameon', True)
                }
                
                if 'title' in legend_cfg and legend_cfg['title']:
                    legend_kwargs['title'] = legend_cfg['title']
                
                if 'ncol' in legend_cfg:
                    legend_kwargs['ncol'] = legend_cfg['ncol']
                
                ax.legend(**legend_kwargs)
