"""Base plot class with common functionality."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


class BasePlot(ABC):
    """Abstract base class for all plot types."""
    
    def __init__(self, plot_id: int, name: str, plot_type: str):
        """
        Initialize base plot.
        
        Args:
            plot_id: Unique identifier for the plot
            name: Display name for the plot
            plot_type: Type of plot (bar, line, etc.)
        """
        self.plot_id = plot_id
        self.name = name
        self.plot_type = plot_type
        self.config: Dict[str, Any] = {}
        self.processed_data: Optional[pd.DataFrame] = None
        self.last_generated_fig: Optional[go.Figure] = None
        self.pipeline: List[Dict[str, Any]] = []
        self.pipeline_counter = 0
        self.legend_mappings_by_column: Dict[str, Dict[str, str]] = {}
        self.legend_mappings: Dict[str, str] = {}
    
    @abstractmethod
    def render_config_ui(self, data: pd.DataFrame, saved_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Render the configuration UI for this plot type.
        
        Args:
            data: The processed data to plot
            saved_config: Previously saved configuration
            
        Returns:
            Current configuration dictionary
        """
        pass
    
    @abstractmethod
    def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """
        Create the Plotly figure from data and configuration.
        
        Args:
            data: The data to plot
            config: Configuration dictionary
            
        Returns:
            Plotly Figure object
        """
        pass
    
    @abstractmethod
    def get_legend_column(self, config: Dict[str, Any]) -> Optional[str]:
        """
        Get the column name used for legend/color coding.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Column name or None
        """
        pass
    
    def apply_legend_labels(self, fig: go.Figure, legend_labels: Optional[Dict[str, str]]) -> go.Figure:
        """
        Apply custom legend labels to the figure.
        
        Args:
            fig: Plotly figure
            legend_labels: Mapping of original labels to custom labels
            
        Returns:
            Updated figure
        """
        if legend_labels:
            fig.for_each_trace(lambda t: t.update(name=legend_labels.get(t.name, t.name)))
        return fig
    
    def apply_common_layout(self, fig: go.Figure, config: Dict[str, Any]) -> go.Figure:
        """
        Apply common layout settings.
        
        Args:
            fig: Plotly figure
            config: Configuration dictionary
            
        Returns:
            Updated figure
        """
        fig.update_layout(
            width=config.get('width', 800),
            height=config.get('height', 500),
            hovermode='closest'
        )
        fig.update_traces(hovertemplate='<b>%{x}</b><br>%{y:.4f}<extra></extra>')
        
        if config.get('legend_title'):
            fig.update_layout(legend_title_text=config['legend_title'])
        
        return fig
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert plot to dictionary for serialization.
        
        Returns:
            Dictionary representation (without Figure objects)
        """
        return {
            'id': self.plot_id,
            'name': self.name,
            'plot_type': self.plot_type,
            'config': self.config,
            'processed_data': self.processed_data.to_csv(index=False) if isinstance(self.processed_data, pd.DataFrame) else None,
            'pipeline': self.pipeline,
            'pipeline_counter': self.pipeline_counter,
            'legend_mappings_by_column': self.legend_mappings_by_column,
            'legend_mappings': self.legend_mappings
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BasePlot':
        """
        Create plot instance from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            Plot instance
        """
        # Import here to avoid circular imports
        from .plot_factory import PlotFactory
        
        plot = PlotFactory.create_plot(
            plot_type=data['plot_type'],
            plot_id=data['id'],
            name=data['name']
        )
        
        plot.config = data.get('config', {})
        plot.pipeline = data.get('pipeline', [])
        plot.pipeline_counter = data.get('pipeline_counter', 0)
        plot.legend_mappings_by_column = data.get('legend_mappings_by_column', {})
        plot.legend_mappings = data.get('legend_mappings', {})
        
        # Deserialize processed_data if it exists
        if data.get('processed_data'):
            from io import StringIO
            plot.processed_data = pd.read_csv(StringIO(data['processed_data']))
        
        return plot
    
    def render_common_config(self, data: pd.DataFrame, saved_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Render common configuration options.
        
        Args:
            data: The data to plot
            saved_config: Previously saved configuration
            
        Returns:
            Configuration dictionary with common options
        """
        numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = data.select_dtypes(include=['object']).columns.tolist()
        
        col1, col2 = st.columns(2)
        
        with col1:
            # X-axis
            x_default_idx = 0
            if saved_config.get('x') and saved_config['x'] in (categorical_cols + numeric_cols):
                x_default_idx = (categorical_cols + numeric_cols).index(saved_config['x'])
            
            x_column = st.selectbox(
                "X-axis",
                options=categorical_cols + numeric_cols,
                index=x_default_idx,
                key=f"x_{self.plot_id}"
            )
            
            # Y-axis
            y_default_idx = 0
            if saved_config.get('y') and saved_config['y'] in numeric_cols:
                y_default_idx = numeric_cols.index(saved_config['y'])
            
            y_column = st.selectbox(
                "Y-axis",
                options=numeric_cols,
                index=y_default_idx,
                key=f"y_{self.plot_id}"
            )
        
        with col2:
            # Title
            default_title = saved_config.get('title', f"{y_column} by {x_column}")
            title = st.text_input(
                "Title",
                value=default_title,
                key=f"title_{self.plot_id}"
            )
            
            # X-label
            default_xlabel = saved_config.get('xlabel', x_column)
            xlabel = st.text_input(
                "X-label",
                value=default_xlabel,
                key=f"xlabel_{self.plot_id}"
            )
            
            # Y-label
            default_ylabel = saved_config.get('ylabel', y_column)
            ylabel = st.text_input(
                "Y-label",
                value=default_ylabel,
                key=f"ylabel_{self.plot_id}"
            )
        
        return {
            'x': x_column,
            'y': y_column,
            'title': title,
            'xlabel': xlabel,
            'ylabel': ylabel,
            'numeric_cols': numeric_cols,
            'categorical_cols': categorical_cols
        }
    
    def render_display_options(self, saved_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Render basic display options (size).
        
        Args:
            saved_config: Previously saved configuration
            
        Returns:
            Configuration dictionary with display options
        """
        st.markdown("**Plot Size**")
        col1, col2 = st.columns(2)
        
        with col1:
            width = st.slider(
                "Width (px)",
                min_value=400,
                max_value=1600,
                value=saved_config.get('width', 800),
                step=50,
                key=f"width_{self.plot_id}"
            )
        
        with col2:
            height = st.slider(
                "Height (px)",
                min_value=300,
                max_value=1200,
                value=saved_config.get('height', 500),
                step=50,
                key=f"height_{self.plot_id}"
            )
        
        return {
            'width': width,
            'height': height
        }
    
    def render_advanced_options(self, saved_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Render advanced options (legend, error bars, download format).
        Should be called within an expander.
        
        Args:
            saved_config: Previously saved configuration
            
        Returns:
            Configuration dictionary with advanced options
        """
        col1, col2 = st.columns(2)
        
        with col1:
            legend_title = st.text_input(
                "Legend Title",
                value=saved_config.get('legend_title', ''),
                key=f"legend_title_{self.plot_id}"
            )
            
            show_error_bars = st.checkbox(
                "Show Error Bars (if .sd columns exist)",
                value=saved_config.get('show_error_bars', False),
                key=f"error_bars_{self.plot_id}"
            )
        
        with col2:
            download_formats = ['html', 'png', 'pdf']
            default_format_idx = 0
            if saved_config.get('download_format') in download_formats:
                default_format_idx = download_formats.index(saved_config['download_format'])
            
            download_format = st.selectbox(
                "Download Format",
                options=download_formats,
                index=default_format_idx,
                key=f"download_fmt_{self.plot_id}"
            )
        
        return {
            'legend_title': legend_title,
            'show_error_bars': show_error_bars,
            'download_format': download_format
        }
