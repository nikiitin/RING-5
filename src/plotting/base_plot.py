"""Base plot class with common functionality."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

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

    def apply_legend_labels(
        self, fig: go.Figure, legend_labels: Optional[Dict[str, str]]
    ) -> go.Figure:
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
        # Basic layout
        layout_args = {
            "width": config.get("width", 800),
            "height": config.get("height", 500),
            "hovermode": "closest",
            "margin": dict(b=config.get("margin_b", 100)),
            "legend": dict(
                orientation=config.get("legend_orientation", "v"),
                x=config.get("legend_x", 1.02),
                y=config.get("legend_y", 1.0),
            ),
        }

        # Bar settings
        if "bar" in self.plot_type:
            layout_args["bargap"] = config.get("bargap", 0.2)
            if "grouped" in self.plot_type:
                layout_args["bargroupgap"] = config.get("bargroupgap", 0.0)

        # Axis settings
        xaxis_settings = {
            "tickangle": config.get("xaxis_tickangle", -45),
            "tickfont": dict(size=config.get("xaxis_tickfont_size", 12)),
            "automargin": config.get("automargin", True),
        }

        # Apply X-axis ordering
        if config.get("xaxis_order"):
            xaxis_settings["categoryorder"] = "array"
            xaxis_settings["categoryarray"] = config["xaxis_order"]

        # Apply Y-axis stepping
        yaxis_settings = {}
        if config.get("yaxis_dtick"):
            yaxis_settings["dtick"] = config["yaxis_dtick"]

        # Update layout
        fig.update_layout(**layout_args)
        fig.update_xaxes(**xaxis_settings)
        fig.update_yaxes(**yaxis_settings)

        # Apply Shapes
        if config.get("shapes"):
            fig.update_layout(shapes=config["shapes"])

        # Apply Legend/Group Order (Reorder traces)
        trace_order = config.get("legend_order") or config.get("group_order")
        if trace_order:
            # Create a map of name to index
            order_map = {str(name): i for i, name in enumerate(trace_order)}
            # Sort traces based on map, putting unknown ones at the end
            fig.data = tuple(
                sorted(fig.data, key=lambda t: order_map.get(str(getattr(t, "name", "")), 9999))
            )

        # Update traces for border if needed
        if config.get("bar_border_width", 0) > 0:
            fig.update_traces(
                marker=dict(line=dict(width=config["bar_border_width"], color="white"))
            )

        fig.update_traces(hovertemplate="<b>%{x}</b><br>%{y:.4f}<extra></extra>")

        if config.get("legend_title"):
            fig.update_layout(legend_title_text=config["legend_title"])

        return fig

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert plot to dictionary for serialization.

        Returns:
            Dictionary representation (without Figure objects)
        """
        return {
            "id": self.plot_id,
            "name": self.name,
            "plot_type": self.plot_type,
            "config": self.config,
            "processed_data": (
                self.processed_data.to_csv(index=False)
                if isinstance(self.processed_data, pd.DataFrame)
                else None
            ),
            "pipeline": self.pipeline,
            "pipeline_counter": self.pipeline_counter,
            "legend_mappings_by_column": self.legend_mappings_by_column,
            "legend_mappings": self.legend_mappings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BasePlot":
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
            plot_type=data["plot_type"], plot_id=data["id"], name=data["name"]
        )

        plot.config = data.get("config", {})
        plot.pipeline = data.get("pipeline", [])
        plot.pipeline_counter = data.get("pipeline_counter", 0)
        plot.legend_mappings_by_column = data.get("legend_mappings_by_column", {})
        plot.legend_mappings = data.get("legend_mappings", {})

        # Deserialize processed_data if it exists
        if data.get("processed_data"):
            from io import StringIO

            plot.processed_data = pd.read_csv(StringIO(data["processed_data"]))

        return plot

    def render_common_config(
        self, data: pd.DataFrame, saved_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Render common configuration options.

        Args:
            data: The data to plot
            saved_config: Previously saved configuration

        Returns:
            Configuration dictionary with common options
        """
        numeric_cols = data.select_dtypes(include=["number"]).columns.tolist()
        categorical_cols = data.select_dtypes(include=["object"]).columns.tolist()

        col1, col2 = st.columns(2)

        with col1:
            # X-axis
            x_default_idx = 0
            if saved_config.get("x") and saved_config["x"] in (categorical_cols + numeric_cols):
                x_default_idx = (categorical_cols + numeric_cols).index(saved_config["x"])

            x_column = st.selectbox(
                "X-axis",
                options=categorical_cols + numeric_cols,
                index=x_default_idx,
                key=f"x_{self.plot_id}",
            )

            # Y-axis
            y_default_idx = 0
            if saved_config.get("y") and saved_config["y"] in numeric_cols:
                y_default_idx = numeric_cols.index(saved_config["y"])

            y_column = st.selectbox(
                "Y-axis", options=numeric_cols, index=y_default_idx, key=f"y_{self.plot_id}"
            )

        with col2:
            # Title
            default_title = saved_config.get("title", f"{y_column} by {x_column}")
            title = st.text_input("Title", value=default_title, key=f"title_{self.plot_id}")

            # X-label
            default_xlabel = saved_config.get("xlabel", x_column)
            xlabel = st.text_input("X-label", value=default_xlabel, key=f"xlabel_{self.plot_id}")

            # Y-label
            default_ylabel = saved_config.get("ylabel", y_column)
            ylabel = st.text_input("Y-label", value=default_ylabel, key=f"ylabel_{self.plot_id}")

        return {
            "x": x_column,
            "y": y_column,
            "title": title,
            "xlabel": xlabel,
            "ylabel": ylabel,
            "numeric_cols": numeric_cols,
            "categorical_cols": categorical_cols,
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
                value=saved_config.get("width", 800),
                step=50,
                key=f"width_{self.plot_id}",
            )

        with col2:
            height = st.slider(
                "Height (px)",
                min_value=300,
                max_value=1200,
                value=saved_config.get("height", 500),
                step=50,
                key=f"height_{self.plot_id}",
            )

        return {"width": width, "height": height}

    def render_advanced_options(
        self, saved_config: Dict[str, Any], data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Render advanced options (legend, error bars, download format, axis settings).
        Should be called within an expander.

        Args:
            saved_config: Previously saved configuration
            data: The data being plotted (optional, needed for ordering options)

        Returns:
            Configuration dictionary with advanced options
        """
        st.markdown("#### General Settings")
        col1, col2 = st.columns(2)

        with col1:
            legend_title = st.text_input(
                "Legend Title",
                value=saved_config.get("legend_title", ""),
                key=f"legend_title_{self.plot_id}",
            )

            show_error_bars = st.checkbox(
                "Show Error Bars (if .sd columns exist)",
                value=saved_config.get("show_error_bars", False),
                key=f"error_bars_{self.plot_id}",
            )

        with col2:
            download_formats = ["html", "png", "pdf"]
            default_format_idx = 0
            if saved_config.get("download_format") in download_formats:
                default_format_idx = download_formats.index(saved_config["download_format"])

            download_format = st.selectbox(
                "Download Format",
                options=download_formats,
                index=default_format_idx,
                key=f"download_fmt_{self.plot_id}",
            )

        st.markdown("#### Axis Settings")
        col3, col4 = st.columns(2)
        with col3:
            xaxis_tickangle = st.slider(
                "X-axis Label Rotation",
                min_value=-90,
                max_value=90,
                value=saved_config.get("xaxis_tickangle", -45),
                step=15,
                key=f"xaxis_angle_{self.plot_id}",
                help="Rotate X-axis labels to prevent overlap",
            )

            xaxis_tickfont_size = st.number_input(
                "X-axis Font Size",
                min_value=8,
                max_value=24,
                value=saved_config.get("xaxis_tickfont_size", 12),
                key=f"xaxis_font_{self.plot_id}",
            )

            # Y-axis Stepping
            yaxis_dtick = st.number_input(
                "Y-axis Step Size (0 for auto)",
                min_value=0.0,
                value=float(saved_config.get("yaxis_dtick") or 0.0),
                key=f"ydtick_{self.plot_id}",
            )

        with col4:
            automargin = st.checkbox(
                "Auto Margins",
                value=saved_config.get("automargin", True),
                key=f"automargin_{self.plot_id}",
                help="Automatically adjust margins to fit labels",
            )

            bottom_margin = st.number_input(
                "Bottom Margin (px)",
                min_value=0,
                max_value=500,
                value=saved_config.get("margin_b", 100),
                key=f"margin_b_{self.plot_id}",
                help="Increase this if labels are cut off",
            )

        # Ordering Options
        xaxis_order = None
        group_order = None
        legend_order = None

        if data is not None:
            st.markdown("#### Ordering Control")

            # X-axis Order
            if saved_config.get("x") and saved_config["x"] in data.columns:
                with st.expander("Reorder X-axis Labels"):
                    unique_x = sorted(data[saved_config["x"]].unique().tolist())
                    xaxis_order = self.render_reorderable_list("X-axis Order", unique_x, "xaxis")

            # Group Order
            if saved_config.get("group") and saved_config["group"] in data.columns:
                with st.expander("Reorder Groups"):
                    unique_g = sorted(data[saved_config["group"]].unique().tolist())
                    group_order = self.render_reorderable_list("Group Order", unique_g, "group")

            # Legend Order (Color)
            if saved_config.get("color") and saved_config["color"] in data.columns:
                with st.expander("Reorder Legend Items"):
                    unique_c = sorted(data[saved_config["color"]].unique().tolist())
                    legend_order = self.render_reorderable_list("Legend Order", unique_c, "legend")

        # Bar Settings
        bargap = 0.2
        bargroupgap = 0.0
        bar_border_width = 0.0
        if "bar" in self.plot_type:
            st.markdown("#### Bar Settings")
            col_bar1, col_bar2 = st.columns(2)
            with col_bar1:
                bargap = st.slider(
                    "Spacing between Bars (Gap)",
                    min_value=0.0,
                    max_value=1.0,
                    value=saved_config.get("bargap", 0.2),
                    step=0.05,
                    key=f"bargap_{self.plot_id}",
                )

            with col_bar2:
                if "grouped" in self.plot_type:
                    bargroupgap = st.slider(
                        "Spacing between Groups",
                        min_value=0.0,
                        max_value=1.0,
                        value=saved_config.get("bargroupgap", 0.0),
                        step=0.05,
                        key=f"bargroupgap_{self.plot_id}",
                    )

                if "stacked" in self.plot_type:
                    bar_border_width = st.slider(
                        "Spacing between Stacked Items (Border)",
                        min_value=0.0,
                        max_value=5.0,
                        value=saved_config.get("bar_border_width", 0.0),
                        step=0.5,
                        key=f"bar_border_{self.plot_id}",
                        help="Adds a white border to separate stacked segments.",
                    )

        # Legend Settings
        st.markdown("#### Legend Settings")
        col_leg1, col_leg2 = st.columns(2)
        with col_leg1:
            legend_orientation = st.selectbox(
                "Legend Orientation",
                options=["v", "h"],
                format_func=lambda x: "Vertical" if x == "v" else "Horizontal",
                index=0 if saved_config.get("legend_orientation", "v") == "v" else 1,
                key=f"leg_orient_{self.plot_id}",
            )

            enable_editable = st.checkbox(
                "Enable Drag & Drop (Move Legend)",
                value=saved_config.get("enable_editable", False),
                key=f"editable_{self.plot_id}",
                help="Allows you to drag the legend and title around the plot.",
            )

        with col_leg2:
            legend_x = st.number_input(
                "Legend X Position",
                value=saved_config.get("legend_x", 1.02),
                step=0.05,
                key=f"leg_x_{self.plot_id}",
            )
            legend_y = st.number_input(
                "Legend Y Position",
                value=saved_config.get("legend_y", 1.0),
                step=0.05,
                key=f"leg_y_{self.plot_id}",
            )

        # Shapes (Annotations)
        st.markdown("#### Annotations (Shapes)")
        shapes = saved_config.get("shapes", [])

        # Add new shape
        with st.expander("Add New Shape"):
            new_shape_type = st.selectbox(
                "Type", ["line", "circle", "rect"], key=f"new_shape_type_{self.plot_id}"
            )
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                x0 = st.text_input("x0", key=f"s_x0_{self.plot_id}")
            with c2:
                y0 = st.text_input("y0", key=f"s_y0_{self.plot_id}")
            with c3:
                x1 = st.text_input("x1", key=f"s_x1_{self.plot_id}")
            with c4:
                y1 = st.text_input("y1", key=f"s_y1_{self.plot_id}")

            c5, c6 = st.columns(2)
            with c5:
                s_color = st.color_picker("Color", "#000000", key=f"s_color_{self.plot_id}")
            with c6:
                s_width = st.number_input("Width", 1, 10, 2, key=f"s_width_{self.plot_id}")

            if st.button("Add Shape", key=f"add_shape_{self.plot_id}"):
                # Try to convert to float if possible, else keep as string
                def try_float(v):
                    try:
                        return float(v)
                    except ValueError:
                        return v

                shapes.append(
                    {
                        "type": new_shape_type,
                        "x0": try_float(x0),
                        "y0": try_float(y0),
                        "x1": try_float(x1),
                        "y1": try_float(y1),
                        "line": {"color": s_color, "width": s_width},
                    }
                )
                st.rerun()

        # List existing shapes
        if shapes:
            st.markdown("Existing Shapes:")
            for i, shape in enumerate(shapes):
                col_s1, col_s2 = st.columns([4, 1])
                with col_s1:
                    st.text(
                        f"{shape['type']}: ({shape['x0']},{shape['y0']}) -> "
                        f"({shape['x1']},{shape['y1']})"
                    )
                with col_s2:
                    if st.button("🗑️", key=f"del_shape_{i}_{self.plot_id}"):
                        shapes.pop(i)
                        st.rerun()

        return {
            "legend_title": legend_title,
            "show_error_bars": show_error_bars,
            "download_format": download_format,
            "xaxis_tickangle": xaxis_tickangle,
            "xaxis_tickfont_size": xaxis_tickfont_size,
            "yaxis_dtick": yaxis_dtick if yaxis_dtick > 0 else None,
            "automargin": automargin,
            "margin_b": bottom_margin,
            "bargap": bargap,
            "bargroupgap": bargroupgap,
            "bar_border_width": bar_border_width if "stacked" in self.plot_type else 0.0,
            "legend_orientation": legend_orientation,
            "enable_editable": enable_editable,
            "legend_x": legend_x,
            "legend_y": legend_y,
            "xaxis_order": xaxis_order,
            "group_order": group_order,
            "legend_order": legend_order,
            "shapes": shapes,
        }

    def render_reorderable_list(self, label: str, items: List[Any], key_prefix: str) -> List[Any]:
        """
        Render a list that can be reordered using up/down buttons.
        """
        st.markdown(f"**{label}**")

        # Initialize in session state if needed
        ss_key = f"{key_prefix}_order_{self.plot_id}"
        if ss_key not in st.session_state:
            st.session_state[ss_key] = list(items)

        # Sync if items changed (e.g. data update) but keep existing order for common items
        current_items = st.session_state[ss_key]
        if set(current_items) != set(items):
            # Keep existing items in order, append new ones
            new_items = [x for x in current_items if x in items]
            new_items.extend([x for x in items if x not in current_items])
            st.session_state[ss_key] = new_items
            current_items = new_items

        # Display items with reordering controls
        for i, item in enumerate(current_items):
            c1, c2, c3 = st.columns([6, 1, 1])
            with c1:
                st.text(str(item))
            with c2:
                if i > 0:
                    if st.button("↑", key=f"{key_prefix}_up_{i}_{self.plot_id}"):
                        current_items[i], current_items[i - 1] = (
                            current_items[i - 1],
                            current_items[i],
                        )
                        st.session_state[ss_key] = current_items
                        st.rerun()
            with c3:
                if i < len(current_items) - 1:
                    if st.button("↓", key=f"{key_prefix}_down_{i}_{self.plot_id}"):
                        current_items[i], current_items[i + 1] = (
                            current_items[i + 1],
                            current_items[i],
                        )
                        st.session_state[ss_key] = current_items
                        st.rerun()

        return current_items
