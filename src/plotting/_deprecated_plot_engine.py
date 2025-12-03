"""
Python-based plotting module using matplotlib and seaborn.
Replaces R-based plotting system with a simpler, pure-Python implementation.
"""
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for multiprocessing
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import warnings
import os


class PlotStyle:
    """Manages plot styling and themes."""
    
    THEMES = {
        'default': 'default',
        'whitegrid': 'whitegrid',
        'darkgrid': 'darkgrid',
        'white': 'white',
        'dark': 'dark',
        'ticks': 'ticks'
    }
    
    @staticmethod
    def apply_theme(theme: str = 'default'):
        """Apply seaborn theme."""
        if theme == 'default':
            sns.set_theme()
        else:
            sns.set_style(theme)
    
    @staticmethod
    def configure_plot(ax, style_config: Dict[str, Any]):
        """
        Configure plot appearance.
        
        Args:
            ax: Matplotlib axes object
            style_config: Style configuration dictionary
        """
        # Set title and labels
        if 'title' in style_config and style_config['title']:
            ax.set_title(style_config['title'], fontsize=14, fontweight='bold')
        
        if 'xlabel' in style_config and style_config['xlabel']:
            ax.set_xlabel(style_config['xlabel'], fontsize=12)
        
        if 'ylabel' in style_config and style_config['ylabel']:
            ax.set_ylabel(style_config['ylabel'], fontsize=12)
        
        # Set limits
        if 'xlim' in style_config:
            ax.set_xlim(style_config['xlim'])
        
        if 'ylim' in style_config:
            ax.set_ylim(style_config['ylim'])
        
        # Grid
        if style_config.get('grid', False):
            ax.grid(True, alpha=0.3)
        
        # Legend
        if 'legend' in style_config:
            legend_cfg = style_config['legend']
            if legend_cfg.get('show', True):
                legend_kwargs = {'loc': legend_cfg.get('location', 'best')}
                if 'title' in legend_cfg and legend_cfg['title']:
                    legend_kwargs['title'] = legend_cfg['title']
                ax.legend(**legend_kwargs)
            else:
                if ax.get_legend():
                    ax.get_legend().remove()


class DataProcessor:
    """Processes data before plotting."""
    
    @staticmethod
    def filter_data(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        """
        Filter dataframe based on conditions.
        
        Args:
            df: Input dataframe
            filters: Dictionary of column: value(s) to filter
            
        Returns:
            Filtered dataframe
        """
        filtered_df = df.copy()
        
        for column, values in filters.items():
            if column not in filtered_df.columns:
                warnings.warn(f"Filter column '{column}' not found in dataframe")
                continue
            
            if isinstance(values, list):
                filtered_df = filtered_df[filtered_df[column].isin(values)]
            else:
                filtered_df = filtered_df[filtered_df[column] == values]
        
        return filtered_df
    
    @staticmethod
    def aggregate_data(
        df: pd.DataFrame,
        method: str,
        group_by: List[str],
        value_cols: List[str]
    ) -> pd.DataFrame:
        """
        Aggregate data using specified method.
        
        Args:
            df: Input dataframe
            method: Aggregation method (mean, median, sum, geomean)
            group_by: Columns to group by
            value_cols: Columns to aggregate
            
        Returns:
            Aggregated dataframe
        """
        if method == 'mean':
            return df.groupby(group_by)[value_cols].mean().reset_index()
        elif method == 'median':
            return df.groupby(group_by)[value_cols].median().reset_index()
        elif method == 'sum':
            return df.groupby(group_by)[value_cols].sum().reset_index()
        elif method == 'geomean':
            # Geometric mean
            grouped = df.groupby(group_by)[value_cols]
            result = grouped.apply(lambda x: np.exp(np.log(x + 1e-10).mean())).reset_index()
            return result
        else:
            raise ValueError(f"Unknown aggregation method: {method}")


class PlotGenerator:
    """Generates different types of plots."""
    
    def __init__(self, data: pd.DataFrame, plot_config: Dict[str, Any]):
        """
        Initialize plot generator.
        
        Args:
            data: DataFrame containing plot data
            plot_config: Plot configuration dictionary
        """
        self.data = data
        self.config = plot_config
        self.data_config = plot_config.get('data', {})
        self.style_config = plot_config.get('style', {})
        self.output_config = plot_config.get('output', {})
        
        # Process data
        self._process_data()
    
    def _process_data(self):
        """Process data according to configuration."""
        # Apply filters
        if 'filters' in self.data_config:
            self.data = DataProcessor.filter_data(
                self.data,
                self.data_config['filters']
            )
        
        # Apply aggregation
        if 'aggregate' in self.data_config:
            agg_config = self.data_config['aggregate']
            value_cols = [self.data_config['y']] if isinstance(
                self.data_config['y'], str
            ) else self.data_config['y']
            
            self.data = DataProcessor.aggregate_data(
                self.data,
                agg_config.get('method', 'mean'),
                agg_config.get('groupBy', []),
                value_cols
            )
    
    def _get_figure_size(self) -> tuple:
        """Get figure size from configuration."""
        width = self.style_config.get('width', 10)
        height = self.style_config.get('height', 6)
        return (width, height)
    
    def _save_figure(self, fig):
        """Save figure to file."""
        filename = self.output_config['filename']
        format_type = self.output_config.get('format', 'png')
        dpi = self.output_config.get('dpi', 300)
        
        output_path = f"{filename}.{format_type}"
        fig.savefig(output_path, dpi=dpi, bbox_inches='tight')
        plt.close(fig)
        
        print(f"Plot saved to: {output_path}")
    
    def generate(self):
        """Generate plot based on type."""
        plot_type = self.config['type']
        
        # Apply theme
        theme = self.style_config.get('theme', 'default')
        PlotStyle.apply_theme(theme)
        
        # Generate plot
        if plot_type == 'bar':
            self._generate_bar_plot()
        elif plot_type == 'line':
            self._generate_line_plot()
        elif plot_type == 'heatmap':
            self._generate_heatmap()
        elif plot_type == 'grouped_bar':
            self._generate_grouped_bar()
        elif plot_type == 'stacked_bar':
            self._generate_stacked_bar()
        elif plot_type == 'box':
            self._generate_box_plot()
        elif plot_type == 'violin':
            self._generate_violin_plot()
        elif plot_type == 'scatter':
            self._generate_scatter_plot()
        else:
            raise ValueError(f"Unknown plot type: {plot_type}")
    
    def _generate_bar_plot(self):
        """Generate bar plot."""
        fig, ax = plt.subplots(figsize=self._get_figure_size())
        
        x = self.data_config['x']
        y = self.data_config['y']
        hue = self.data_config.get('hue')
        
        sns.barplot(
            data=self.data,
            x=x,
            y=y,
            hue=hue,
            ax=ax,
            errorbar='sd' if f'{y}.sd' in self.data.columns else None
        )
        
        # Rotate x labels if needed
        plt.xticks(rotation=45, ha='right')
        
        PlotStyle.configure_plot(ax, self.style_config)
        self._save_figure(fig)
    
    def _generate_line_plot(self):
        """Generate line plot."""
        fig, ax = plt.subplots(figsize=self._get_figure_size())
        
        x = self.data_config['x']
        y = self.data_config['y']
        hue = self.data_config.get('hue')
        
        sns.lineplot(
            data=self.data,
            x=x,
            y=y,
            hue=hue,
            ax=ax,
            marker='o'
        )
        
        PlotStyle.configure_plot(ax, self.style_config)
        self._save_figure(fig)
    
    def _generate_heatmap(self):
        """Generate heatmap."""
        fig, ax = plt.subplots(figsize=self._get_figure_size())
        
        # Pivot data for heatmap
        x = self.data_config['x']
        y = self.data_config['y']
        value = self.data_config.get('value', self.data_config['y'])
        
        pivot_data = self.data.pivot(index=y, columns=x, values=value)
        
        sns.heatmap(
            pivot_data,
            annot=True,
            fmt='.2f',
            cmap='YlOrRd',
            ax=ax,
            cbar_kws={'label': value}
        )
        
        PlotStyle.configure_plot(ax, self.style_config)
        self._save_figure(fig)
    
    def _generate_grouped_bar(self):
        """Generate grouped bar plot."""
        # Similar to bar plot but with different seaborn parameters
        self._generate_bar_plot()
    
    def _generate_stacked_bar(self):
        """Generate stacked bar plot."""
        fig, ax = plt.subplots(figsize=self._get_figure_size())
        
        x = self.data_config['x']
        y_vars = self.data_config['y']
        
        if isinstance(y_vars, str):
            y_vars = [y_vars]
        
        # Pivot for stacked bar
        plot_data = self.data.set_index(x)[y_vars]
        plot_data.plot(kind='bar', stacked=True, ax=ax)
        
        plt.xticks(rotation=45, ha='right')
        PlotStyle.configure_plot(ax, self.style_config)
        self._save_figure(fig)
    
    def _generate_box_plot(self):
        """Generate box plot."""
        fig, ax = plt.subplots(figsize=self._get_figure_size())
        
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
        
        plt.xticks(rotation=45, ha='right')
        PlotStyle.configure_plot(ax, self.style_config)
        self._save_figure(fig)
    
    def _generate_violin_plot(self):
        """Generate violin plot."""
        fig, ax = plt.subplots(figsize=self._get_figure_size())
        
        x = self.data_config['x']
        y = self.data_config['y']
        hue = self.data_config.get('hue')
        
        sns.violinplot(
            data=self.data,
            x=x,
            y=y,
            hue=hue,
            ax=ax
        )
        
        plt.xticks(rotation=45, ha='right')
        PlotStyle.configure_plot(ax, self.style_config)
        self._save_figure(fig)
    
    def _generate_scatter_plot(self):
        """Generate scatter plot."""
        fig, ax = plt.subplots(figsize=self._get_figure_size())
        
        x = self.data_config['x']
        y = self.data_config['y']
        hue = self.data_config.get('hue')
        
        sns.scatterplot(
            data=self.data,
            x=x,
            y=y,
            hue=hue,
            ax=ax,
            s=100,
            alpha=0.7
        )
        
        PlotStyle.configure_plot(ax, self.style_config)
        self._save_figure(fig)


class PlotManager:
    """Manages multiple plots from configuration - with multiprocessing support."""
    
    def __init__(self, data_path: str, output_dir: str):
        """
        Initialize plot manager.
        
        Args:
            data_path: Path to CSV data file
            output_dir: Output directory for plots
        """
        self.data_path = data_path
        self.data = pd.read_csv(data_path)  # Use default separator (comma)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_plots(self, plot_configs: List[Dict[str, Any]], use_multiprocessing: bool = True):
        """
        Generate all plots from configurations.
        
        Args:
            plot_configs: List of plot configuration dictionaries
            use_multiprocessing: Whether to use multiprocessing for parallel plot generation
        """
        if use_multiprocessing and len(plot_configs) > 1:
            self._generate_plots_parallel(plot_configs)
        else:
            self._generate_plots_sequential(plot_configs)
        
        print(f"\nAll plots generated in: {self.output_dir}")
    
    def _generate_plots_sequential(self, plot_configs: List[Dict[str, Any]]):
        """Generate plots sequentially (no multiprocessing)."""
        for i, plot_config in enumerate(plot_configs):
            try:
                print(f"\nGenerating plot {i+1}/{len(plot_configs)}...")
                
                # Update output path
                if 'output' in plot_config:
                    filename = plot_config['output']['filename']
                    plot_config['output']['filename'] = str(
                        self.output_dir / filename
                    )
                
                # Generate plot
                generator = PlotGenerator(self.data.copy(), plot_config)
                generator.generate()
                
            except Exception as e:
                print(f"Error generating plot {i+1}: {e}")
                import traceback
                traceback.print_exc()
    
    def _generate_plots_parallel(self, plot_configs: List[Dict[str, Any]]):
        """Generate plots in parallel using multiprocessing."""
        from src.data_plotter.multiprocessing.plotWorkPool import PlotWorkPool
        from src.data_plotter.multiprocessing.plotWork import PlotWork
        
        # Create plot work items
        class PlotWorkItem(PlotWork):
            def __init__(self, data_path: str, output_dir: str, plot_config: Dict[str, Any]):
                super().__init__()
                self.data_path = data_path
                self.output_dir = output_dir
                self.plot_config = plot_config
            
            def __call__(self):
                # Load data in worker process
                data = pd.read_csv(self.data_path, sep=r'\s+')
                
                # Update output path
                if 'output' in self.plot_config:
                    filename = self.plot_config['output']['filename']
                    self.plot_config['output']['filename'] = str(
                        Path(self.output_dir) / filename
                    )
                
                # Generate plot
                generator = PlotGenerator(data, self.plot_config)
                generator.generate()
            
            def __str__(self):
                return f"PlotWork({self.plot_config.get('output', {}).get('filename', 'unknown')})"
        
        # Get pool instance
        pool = PlotWorkPool.getInstance()
        pool.startPool()
        
        # Add all plots as work items
        for plot_config in plot_configs:
            work = PlotWorkItem(self.data_path, str(self.output_dir), plot_config)
            pool.addWork(work)
        
        # Signal completion and wait
        pool.setFinishJob()
