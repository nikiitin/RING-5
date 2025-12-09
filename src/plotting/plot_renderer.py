"""Plot rendering utilities."""
from typing import Dict, Any, Optional
import streamlit as st
import pandas as pd
import plotly.io as pio

from .base_plot import BasePlot


class PlotRenderer:
    """Handles rendering plots and their UI elements."""
    
    @staticmethod
    def render_legend_customization(plot: BasePlot, data: pd.DataFrame, config: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        Render legend customization UI.
        
        Args:
            plot: Plot instance
            data: The data being plotted
            config: Current plot configuration
            
        Returns:
            Dictionary mapping original values to custom labels, or None
        """
        legend_col = plot.get_legend_column(config)
        
        if not legend_col:
            return None
        
        unique_vals = data[legend_col].unique().tolist()
        
        st.markdown("**Custom Legend Labels**")
        st.caption("Customize the legend labels for each value (leave blank to keep original)")
        
        # Initialize per-column legend mappings storage if not exists
        if not plot.legend_mappings_by_column:
            plot.legend_mappings_by_column = {}
        
        # Get existing mappings for this column
        existing_mappings = plot.legend_mappings_by_column.get(legend_col, {})
        legend_labels = {}
        
        # Create input fields for each unique value
        for val in unique_vals:
            default_value = existing_mappings.get(str(val), str(val))
            custom_label = st.text_input(
                f"Label for '{val}'",
                value=default_value,
                key=f"legend_label_{plot.plot_id}_{legend_col}_{val}",
                label_visibility="visible"
            )
            # Only add to mapping if user provided a value
            if custom_label and custom_label.strip():
                legend_labels[str(val)] = custom_label.strip()
            else:
                legend_labels[str(val)] = str(val)
        
        # Store mappings for THIS column specifically
        plot.legend_mappings_by_column[legend_col] = legend_labels
        
        # Also update the global legend_mappings for backward compatibility
        plot.legend_mappings = legend_labels
        
        return legend_labels
    
    @staticmethod
    def render_plot(plot: BasePlot, should_generate: bool = False) -> None:
        """
        Render the plot visualization.
        
        Args:
            plot: Plot instance
            should_generate: Whether to regenerate the figure
        """
        if should_generate or plot.last_generated_fig is not None:
            try:
                # Only regenerate if needed
                if should_generate:
                    fig = plot.create_figure(plot.processed_data, plot.config)
                    fig = plot.apply_common_layout(fig, plot.config)
                    
                    # Apply legend labels
                    legend_labels = plot.config.get('legend_labels')
                    if legend_labels:
                        fig = plot.apply_legend_labels(fig, legend_labels)
                    
                    # Store the figure
                    plot.last_generated_fig = fig
                else:
                    # Use cached figure
                    fig = plot.last_generated_fig
                
                # Display the plot
                st.plotly_chart(fig)
                
                # Download button
                PlotRenderer._render_download_button(plot, fig)
                
            except Exception as e:
                st.error(f"Error generating plot: {e}")
    
    @staticmethod
    def _render_download_button(plot: BasePlot, fig) -> None:
        """
        Render download button for the plot.
        
        Args:
            plot: Plot instance
            fig: Plotly figure
        """
        download_format = plot.config.get('download_format', 'html')
        
        if download_format == 'html':
            # Export as interactive HTML
            html_str = pio.to_html(fig, include_plotlyjs=True)
            st.download_button(
                label="Download Interactive HTML",
                data=html_str,
                file_name=f"{plot.name}.html",
                mime="text/html"
            )
        elif download_format in ['png', 'pdf']:
            try:
                # Convert plotly figure to static image using matplotlib backend
                import matplotlib.pyplot as plt
                import matplotlib.backends.backend_pdf as pdf_backend
                import io
                
                # Extract data from plotly figure
                fig_data = fig.to_dict()
                
                width_inches = plot.config.get('width', 800) / 100
                height_inches = plot.config.get('height', 500) / 100
                
                mpl_fig = plt.figure(figsize=(width_inches, height_inches))
                ax = mpl_fig.add_subplot(111)
                
                # Simple conversion - just plot the data
                for trace in fig_data.get('data', []):
                    if trace.get('type') in ['bar', 'scatter']:
                        x_data = trace.get('x', [])
                        y_data = trace.get('y', [])
                        label = trace.get('name', '')
                        
                        if trace.get('type') == 'bar':
                            ax.bar(range(len(x_data)), y_data, label=label, alpha=0.7)
                        else:
                            ax.plot(x_data, y_data, label=label, marker='o')
                
                ax.set_title(plot.config.get('title', ''))
                ax.set_xlabel(plot.config.get('xlabel', ''))
                ax.set_ylabel(plot.config.get('ylabel', ''))
                if len(fig_data.get('data', [])) > 1:
                    ax.legend()
                ax.grid(True, alpha=0.3)
                
                # Save to bytes
                buf = io.BytesIO()
                if download_format == 'png':
                    mpl_fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
                    mime = 'image/png'
                else:
                    mpl_fig.savefig(buf, format='pdf', bbox_inches='tight')
                    mime = 'application/pdf'
                
                plt.close(mpl_fig)
                buf.seek(0)
                
                st.download_button(
                    label=f"Download {download_format.upper()}",
                    data=buf,
                    file_name=f"{plot.name}.{download_format}",
                    mime=mime
                )
            except Exception as e:
                st.error(f"Failed to generate {download_format.upper()}: {e}")
                st.info("HTML download is always available as a fallback")
