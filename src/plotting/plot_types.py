"""Concrete plot implementations."""
from typing import Dict, Any, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from .base_plot import BasePlot


class BarPlot(BasePlot):
    """Simple bar plot."""
    
    def __init__(self, plot_id: int, name: str):
        super().__init__(plot_id, name, 'bar')
    
    def render_config_ui(self, data: pd.DataFrame, saved_config: Dict[str, Any]) -> Dict[str, Any]:
        """Render configuration UI for bar plot."""
        # Common config (x, y, title, labels)
        config = self.render_common_config(data, saved_config)
        
        # Color option
        color_options = [None] + config['categorical_cols']
        color_default_idx = 0
        if saved_config.get('color') and saved_config['color'] in config['categorical_cols']:
            color_default_idx = color_options.index(saved_config['color'])
        
        color_column = st.selectbox(
            "Color by (optional)",
            options=color_options,
            index=color_default_idx,
            key=f"color_{self.plot_id}"
        )
        
        # Display options
        display_config = self.render_display_options(saved_config)
        
        return {**config, 'color': color_column, **display_config}
    
    def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """Create bar plot figure."""
        y_error = None
        if config.get('show_error_bars'):
            sd_col = f"{config['y']}.sd"
            if sd_col in data.columns:
                y_error = sd_col
        
        fig = px.bar(
            data,
            x=config['x'],
            y=config['y'],
            color=config.get('color'),
            error_y=y_error,
            title=config['title'],
            labels={config['x']: config['xlabel'], config['y']: config['ylabel']}
        )
        
        return fig
    
    def get_legend_column(self, config: Dict[str, Any]) -> Optional[str]:
        """Get legend column for bar plot."""
        return config.get('color')


class GroupedBarPlot(BasePlot):
    """Grouped bar plot."""
    
    def __init__(self, plot_id: int, name: str):
        super().__init__(plot_id, name, 'grouped_bar')
    
    def render_config_ui(self, data: pd.DataFrame, saved_config: Dict[str, Any]) -> Dict[str, Any]:
        """Render configuration UI for grouped bar plot."""
        # Common config
        config = self.render_common_config(data, saved_config)
        
        # Group by option
        group_default_idx = 0
        if saved_config.get('group') and saved_config['group'] in config['categorical_cols']:
            group_default_idx = config['categorical_cols'].index(saved_config['group'])
        
        group_column = st.selectbox(
            "Group by",
            options=config['categorical_cols'],
            index=group_default_idx,
            key=f"group_{self.plot_id}"
        )
        
        # Display options
        display_config = self.render_display_options(saved_config)
        
        return {**config, 'group': group_column, 'color': None, **display_config, '_needs_advanced': True}
    
    def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """Create grouped bar plot figure."""
        y_error = None
        if config.get('show_error_bars'):
            sd_col = f"{config['y']}.sd"
            if sd_col in data.columns:
                y_error = sd_col
        
        fig = px.bar(
            data,
            x=config['x'],
            y=config['y'],
            color=config['group'],
            error_y=y_error,
            barmode='group',
            title=config['title'],
            labels={config['x']: config['xlabel'], config['y']: config['ylabel']}
        )
        
        return fig
    
    def get_legend_column(self, config: Dict[str, Any]) -> Optional[str]:
        """Get legend column for grouped bar plot."""
        return config.get('group')


class GroupedStackedBarPlot(BasePlot):
    """Grouped stacked bar plot."""
    
    def __init__(self, plot_id: int, name: str):
        super().__init__(plot_id, name, 'grouped_stacked_bar')
    
    def render_config_ui(self, data: pd.DataFrame, saved_config: Dict[str, Any]) -> Dict[str, Any]:
        """Render configuration UI for grouped stacked bar plot."""
        # Common config
        config = self.render_common_config(data, saved_config)
        
        # Group by option
        group_default_idx = 0
        if saved_config.get('group') and saved_config['group'] in config['categorical_cols']:
            group_default_idx = config['categorical_cols'].index(saved_config['group'])
        
        group_column = st.selectbox(
            "Group by (x-axis groups)",
            options=config['categorical_cols'],
            index=group_default_idx,
            key=f"group_{self.plot_id}"
        )
        
        # Stack by option
        stack_default_idx = 0
        if saved_config.get('stack') and saved_config['stack'] in config['categorical_cols']:
            stack_default_idx = config['categorical_cols'].index(saved_config['stack'])
        
        stack_column = st.selectbox(
            "Stack by (within groups)",
            options=config['categorical_cols'],
            index=stack_default_idx,
            key=f"stack_{self.plot_id}"
        )
        
        # Display options
        display_config = self.render_display_options(saved_config)
        
        return {**config, 'group': group_column, 'stack': stack_column, 'color': None, **display_config, '_needs_advanced': True}
    
    def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """Create grouped stacked bar plot figure."""
        y_error = None
        if config.get('show_error_bars'):
            sd_col = f"{config['y']}.sd"
            if sd_col in data.columns:
                y_error = sd_col
        
        fig = px.bar(
            data,
            x=config['group'],
            y=config['y'],
            color=config['stack'],
            error_y=y_error,
            barmode='group',
            title=config['title'],
            labels={config['group']: config['xlabel'], config['y']: config['ylabel']},
            facet_col=config['x'] if config['x'] != config['group'] else None
        )
        
        return fig
    
    def get_legend_column(self, config: Dict[str, Any]) -> Optional[str]:
        """Get legend column for grouped stacked bar plot."""
        return config.get('stack')


class LinePlot(BasePlot):
    """Line plot."""
    
    def __init__(self, plot_id: int, name: str):
        super().__init__(plot_id, name, 'line')
    
    def render_config_ui(self, data: pd.DataFrame, saved_config: Dict[str, Any]) -> Dict[str, Any]:
        """Render configuration UI for line plot."""
        # Common config
        config = self.render_common_config(data, saved_config)
        
        # Color option
        color_options = [None] + config['categorical_cols']
        color_default_idx = 0
        if saved_config.get('color') and saved_config['color'] in config['categorical_cols']:
            color_default_idx = color_options.index(saved_config['color'])
        
        color_column = st.selectbox(
            "Color by (optional)",
            options=color_options,
            index=color_default_idx,
            key=f"color_{self.plot_id}"
        )
        
        # Display options
        display_config = self.render_display_options(saved_config)
        
        return {**config, 'color': color_column, **display_config}
    
    def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """Create line plot figure."""
        y_error = None
        if config.get('show_error_bars'):
            sd_col = f"{config['y']}.sd"
            if sd_col in data.columns:
                y_error = sd_col
        
        fig = px.line(
            data,
            x=config['x'],
            y=config['y'],
            color=config.get('color'),
            error_y=y_error,
            title=config['title'],
            labels={config['x']: config['xlabel'], config['y']: config['ylabel']}
        )
        
        return fig
    
    def get_legend_column(self, config: Dict[str, Any]) -> Optional[str]:
        """Get legend column for line plot."""
        return config.get('color')


class ScatterPlot(BasePlot):
    """Scatter plot."""
    
    def __init__(self, plot_id: int, name: str):
        super().__init__(plot_id, name, 'scatter')
    
    def render_config_ui(self, data: pd.DataFrame, saved_config: Dict[str, Any]) -> Dict[str, Any]:
        """Render configuration UI for scatter plot."""
        # Common config
        config = self.render_common_config(data, saved_config)
        
        # Color option
        color_options = [None] + config['categorical_cols']
        color_default_idx = 0
        if saved_config.get('color') and saved_config['color'] in config['categorical_cols']:
            color_default_idx = color_options.index(saved_config['color'])
        
        color_column = st.selectbox(
            "Color by (optional)",
            options=color_options,
            index=color_default_idx,
            key=f"color_{self.plot_id}"
        )
        
        # Display options
        display_config = self.render_display_options(saved_config)
        
        return {**config, 'color': color_column, **display_config}
    
    def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """Create scatter plot figure."""
        y_error = None
        if config.get('show_error_bars'):
            sd_col = f"{config['y']}.sd"
            if sd_col in data.columns:
                y_error = sd_col
        
        fig = px.scatter(
            data,
            x=config['x'],
            y=config['y'],
            color=config.get('color'),
            error_y=y_error,
            title=config['title'],
            labels={config['x']: config['xlabel'], config['y']: config['ylabel']}
        )
        
        return fig
    
    def get_legend_column(self, config: Dict[str, Any]) -> Optional[str]:
        """Get legend column for scatter plot."""
        return config.get('color')
