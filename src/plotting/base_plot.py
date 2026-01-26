"""Base plot class with common functionality."""

import math
from abc import ABC, abstractmethod
from io import StringIO
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.plotting.styles import StyleManager
from src.web.ui.components.plot_config_components import PlotConfigComponents


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

        # Initialize Style Manager
        self.style_manager = StyleManager(self.plot_id, self.plot_type)

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

    def update_from_relayout(self, relayout_data: Dict[str, Any]) -> bool:
        """
        Update config from client-side relayout data (zoom/pan, legend drag).
        Returns True if config changed.
        """
        changed = False

        if not relayout_data:
            return False

        # Helper to safely update
        def update_if_new(key, val):
            current = self.config.get(key)
            # Check for float equality if both are lists of numbers (ranges)

            def is_close(a, b):
                try:
                    return math.isclose(float(a), float(b), rel_tol=1e-9)
                except (ValueError, TypeError):
                    return a == b

            if isinstance(current, list) and isinstance(val, list) and len(current) == len(val):
                if all(is_close(c, v) for c, v in zip(current, val)):
                    return False

            # Simple equality check for non-lists or different lengths
            if current != val:
                if is_close(current, val):
                    return False

                self.config[key] = val
                return True
            return False

        # 1. Custom Range (Zoom)
        # Plotly sends ranges as array [min, max]
        # x-axis
        if "xaxis.range[0]" in relayout_data and "xaxis.range[1]" in relayout_data:
            new_range = [relayout_data["xaxis.range[0]"], relayout_data["xaxis.range[1]"]]
            if update_if_new("range_x", new_range):
                changed = True
        elif "xaxis.range" in relayout_data:
            if update_if_new("range_x", relayout_data["xaxis.range"]):
                changed = True

        # y-axis
        if "yaxis.range[0]" in relayout_data and "yaxis.range[1]" in relayout_data:
            new_range = [relayout_data["yaxis.range[0]"], relayout_data["yaxis.range[1]"]]
            if update_if_new("range_y", new_range):
                changed = True
        elif "yaxis.range" in relayout_data:
            if update_if_new("range_y", relayout_data["yaxis.range"]):
                changed = True

        # Autosize / Reset Zoom
        if "xaxis.autorange" in relayout_data and relayout_data["xaxis.autorange"]:
            if self.config.get("range_x") is not None:
                self.config["range_x"] = None
                changed = True

        if "yaxis.autorange" in relayout_data and relayout_data["yaxis.autorange"]:
            if self.config.get("range_y") is not None:
                self.config["range_y"] = None
                changed = True

        # 2. Legend Position (Drag)
        # Track each legend position independently (legend, legend2, legend3, etc.)
        # Users can position each column separately

        # Check for any legend drag events
        for key, val in relayout_data.items():
            if not key.startswith("legend"):
                continue

            parts = key.split(".")
            if len(parts) != 2:
                continue

            legend_name = parts[0]  # "legend" or "legend2", etc.
            prop = parts[1]  # "x", "y", "xanchor", etc.

            # Build config key: legend.x -> legend_x, legend2.x -> legend2_x
            if legend_name == "legend":
                config_key = f"legend_{prop}"
            else:
                config_key = f"{legend_name}_{prop}"

            if prop in ("x", "y"):
                if update_if_new(config_key, val):
                    changed = True
                    # Also set anchor when position changes
                    if prop == "x":
                        anchor_key = config_key.replace("_x", "_xanchor")
                        self.config[anchor_key] = "left"
                    elif prop == "y":
                        anchor_key = config_key.replace("_y", "_yanchor")
                        self.config[anchor_key] = "top"
            elif prop in ("xanchor", "yanchor"):
                if update_if_new(config_key, val):
                    changed = True

        # 3. Legend Title (Edit)
        if "legend.title.text" in relayout_data:
            if update_if_new("legend_title", relayout_data["legend.title.text"]):
                changed = True

        # Invalidate cache if changed so next render uses new config
        if changed:
            self.last_generated_fig = None

        return changed

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
        Delegates to StyleManager.
        """
        return self.style_manager.apply_styles(fig, config)

    def generate_figure(self) -> go.Figure:
        """
        Generate and cache the final Plotly figure.
        Applies creation, layout, and legend labels.
        """
        if self.processed_data is None:
            raise ValueError(f"Plot '{self.name}' has no processed data.")

        fig = self.create_figure(self.processed_data, self.config)
        fig = self.apply_common_layout(fig, self.config)

        # Apply legend labels
        legend_labels = self.config.get("legend_labels")
        if legend_labels:
            fig = self.apply_legend_labels(fig, legend_labels)

        self.last_generated_fig = fig
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
        categorical_cols = data.select_dtypes(include=["object", "category"]).columns.tolist()

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
            # Title & Labels
            default_title = saved_config.get("title", f"{y_column} by {x_column}")
            default_xlabel = saved_config.get("xlabel", x_column)
            default_ylabel = saved_config.get("ylabel", y_column)
            default_legend_title = saved_config.get("legend_title", "")

            label_config = PlotConfigComponents.render_title_labels_section(
                saved_config=saved_config,
                plot_id=self.plot_id,
                default_title=default_title,
                default_xlabel=default_xlabel,
                default_ylabel=default_ylabel,
                include_legend_title=True,
                default_legend_title=default_legend_title,
            )
            title = label_config["title"]
            xlabel = label_config["xlabel"]
            ylabel = label_config["ylabel"]
            legend_title = label_config["legend_title"]

        return {
            "x": x_column,
            "y": y_column,
            "title": title,
            "xlabel": xlabel,
            "ylabel": ylabel,
            "legend_title": legend_title,
            "numeric_cols": numeric_cols,
            "categorical_cols": categorical_cols,
        }

    def render_display_options(self, saved_config: Dict[str, Any]) -> Dict[str, Any]:
        """Render sizing and layout options via StyleManager."""
        return self.style_manager.render_layout_options(saved_config)

    def render_theme_options(
        self, saved_config: Dict[str, Any], items: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Render theme options via StyleManager."""
        # Pass data for potential data-dependent theming (e.g. series colors)
        # Use a prefix to distinguish from advanced options
        return self.style_manager.render_theme_options(
            saved_config, self.processed_data, items=items, key_prefix="theme_"
        )

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
        config = {}

        # 1. General & Axis Settings
        self._render_general_settings(saved_config, config)

        # 2. Specific Settings (Plot Type Specific)
        specific_config = self.render_specific_advanced_options(saved_config, data)
        config.update(specific_config)

        # 3. Label Renaming (Generic X-axis renames mostly)
        config["xaxis_labels"] = self.style_manager.render_xaxis_labels_ui(saved_config, data)

        # 4. Ordering Control
        if data is not None:
            self._render_ordering_ui(saved_config, data, config)

        # 5. Legend & Interactivity
        st.markdown("#### Legend & Interactivity")
        config["enable_editable"] = st.checkbox(
            "Enable Interactive Editing",
            value=saved_config.get("enable_editable", False),
            key=f"editable_{self.plot_id}",
            help="Allows you to drag the legend/title and click to edit text directly on the plot.",
        )

        # 6. Series Styling (Color, Shape, Pattern, Name)
        if st.checkbox(
            "Show Series Renaming", value=False, key=f"show_series_style_{self.plot_id}"
        ):
            st.markdown("#### Rename Series")
            with st.expander("Rename Items", expanded=True):
                # Colors are now handled in Style & Theme, so we only do Renaming here.
                renaming_styles = self.style_manager.render_series_renaming_ui(saved_config, data)
                # Merge with existing styles (which might have colors from Style Menu)
                if "series_styles" not in config:
                    config["series_styles"] = {}

                # Deep update of series styles
                # series_styles is Dict[str, Dict].
                for k, v in renaming_styles.items():
                    if k not in config["series_styles"]:
                        config["series_styles"][k] = v
                    else:
                        config["series_styles"][k].update(v)
        else:
            # Preserve existing series styles if UI is hidden
            if "series_styles" not in config:
                config["series_styles"] = saved_config.get("series_styles", {})

        # 7. Annotations
        st.markdown("#### Annotations (Shapes)")
        config["shapes"] = self._render_shapes_ui(saved_config)

        return config

    def render_specific_advanced_options(
        self, saved_config: Dict[str, Any], data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Hook for subclasses to render plot-specific advanced options.
        Default implementation renders Bar settings if plot_type contains 'bar'.
        """
        config = {}
        if "bar" in self.plot_type:
            st.markdown("#### Bar Settings")
            col_bar1, col_bar2 = st.columns(2)
            with col_bar1:
                config["bargap"] = st.slider(
                    "Spacing between Bars (Gap)",
                    min_value=0.0,
                    max_value=1.0,
                    value=saved_config.get("bargap", 0.2),
                    step=0.05,
                    key=f"bargap_{self.plot_id}",
                )

            with col_bar2:
                if "grouped" in self.plot_type:
                    config["bargroupgap"] = st.slider(
                        "Spacing between Groups",
                        min_value=0.0,
                        max_value=1.0,
                        value=saved_config.get("bargroupgap", 0.0),
                        step=0.05,
                        key=f"bargroupgap_{self.plot_id}",
                    )

                if "stacked" in self.plot_type:
                    config["bar_border_width"] = st.slider(
                        "Spacing between Stacked Items (Border)",
                        min_value=0.0,
                        max_value=5.0,
                        value=saved_config.get("bar_border_width", 0.0),
                        step=0.5,
                        key=f"bar_border_{self.plot_id}",
                        help="Adds a white border to separate stacked segments.",
                    )
        return config

    def _render_general_settings(self, saved_config: Dict[str, Any], config: Dict[str, Any]):
        """Helper to render general settings."""
        st.markdown("#### General & Axis")
        col1, col2 = st.columns(2)
        with col1:
            config["show_error_bars"] = st.checkbox(
                "Show Error Bars (if .sd columns exist)",
                value=saved_config.get("show_error_bars", False),
                key=f"error_bars_{self.plot_id}",
            )

            # Y-axis Stepping
            dtick = st.number_input(
                "Y-axis Step Size (0 for auto)",
                min_value=0.0,
                value=float(saved_config.get("yaxis_dtick") or 0.0),
                key=f"ydtick_{self.plot_id}",
            )
            if dtick > 0:
                config["yaxis_dtick"] = dtick

        with col2:
            download_formats = ["html", "png", "pdf", "svg"]
            default_fmt_idx = 0
            if saved_config.get("download_format") in download_formats:
                default_fmt_idx = download_formats.index(saved_config["download_format"])

            config["download_format"] = st.selectbox(
                "Default Download Format",
                options=download_formats,
                index=default_fmt_idx,
                key=f"download_fmt_{self.plot_id}",
            )

            # Export Scale
            config["export_scale"] = st.selectbox(
                "Export Scale (Resolution)",
                options=[1, 2, 3],
                index=[1, 2, 3].index(saved_config.get("export_scale", 1)),
                key=f"exp_scale_{self.plot_id}",
                help="1x = Screen Resolution (WYSIWYG). 3x = High Res (Publication).",
            )

            # Dimension Preview
            w = saved_config.get("width", 800)
            h = saved_config.get("height", 500)
            s = config["export_scale"]
            st.caption(f"Export Size: {w * s} x {h * s} px")
            st.caption("Change base dimensions in 'Theme & Style' -> 'Dimensions'.")

            config["xaxis_tickangle"] = st.slider(
                "X-axis Label Rotation",
                min_value=-90,
                max_value=90,
                value=saved_config.get("xaxis_tickangle", -45),
                step=15,
                key=f"xaxis_angle_{self.plot_id}",
                help="Rotate X-axis labels to prevent overlap",
            )

    def _render_ordering_ui(
        self, saved_config: Dict[str, Any], data: pd.DataFrame, config: Dict[str, Any]
    ):
        """Helper to render ordering UI."""
        st.markdown("#### Ordering Control")

        # X-axis Order
        if saved_config.get("x") and saved_config["x"] in data.columns:
            with st.expander("Reorder X-axis Labels"):
                unique_x = sorted(data[saved_config["x"]].unique().tolist())
                config["xaxis_order"] = self.render_reorderable_list(
                    "X-axis Order", unique_x, "xaxis", default_order=saved_config.get("xaxis_order")
                )

        # Group Order
        if saved_config.get("group") and saved_config["group"] in data.columns:
            with st.expander("Reorder Groups"):
                unique_g = sorted(data[saved_config["group"]].unique().tolist())
                config["group_order"] = self.render_reorderable_list(
                    "Group Order",
                    unique_g,
                    "group",
                    legend_labels=saved_config.get("legend_labels"),
                    default_order=saved_config.get("group_order"),
                )

        # Legend Order (Color)
        if saved_config.get("color") and saved_config["color"] in data.columns:
            with st.expander("Reorder Legend Items"):
                unique_c = sorted(data[saved_config["color"]].unique().tolist())
                config["legend_order"] = self.render_reorderable_list(
                    "Legend Order",
                    unique_c,
                    "legend",
                    legend_labels=saved_config.get("legend_labels"),
                    default_order=saved_config.get("legend_order"),
                )

    def _render_shapes_ui(self, saved_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Helper to render Shapes UI."""
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
            st.markdown("**Existing Shapes (Edit to Resize):**")

            h1, h2, h3, h4, h5, h6 = st.columns([1, 1, 1, 1, 1, 0.5])
            with h1:
                st.caption("x0")
            with h2:
                st.caption("y0")
            with h3:
                st.caption("x1")
            with h4:
                st.caption("y1")
            with h5:
                st.caption("Type")

            for i, shape in enumerate(shapes):
                c1, c2, c3, c4, c5, c6 = st.columns([1, 1, 1, 1, 1, 0.5])

                def try_float(v):
                    try:
                        return float(v)
                    except (ValueError, TypeError):
                        return v

                with c1:
                    new_x0 = st.text_input(
                        "x0",
                        value=str(shape["x0"]),
                        key=f"edit_x0_{i}_{self.plot_id}",
                        label_visibility="collapsed",
                    )
                with c2:
                    new_y0 = st.text_input(
                        "y0",
                        value=str(shape["y0"]),
                        key=f"edit_y0_{i}_{self.plot_id}",
                        label_visibility="collapsed",
                    )
                with c3:
                    new_x1 = st.text_input(
                        "x1",
                        value=str(shape["x1"]),
                        key=f"edit_x1_{i}_{self.plot_id}",
                        label_visibility="collapsed",
                    )
                with c4:
                    new_y1 = st.text_input(
                        "y1",
                        value=str(shape["y1"]),
                        key=f"edit_y1_{i}_{self.plot_id}",
                        label_visibility="collapsed",
                    )
                with c5:
                    st.text(shape["type"])
                with c6:
                    if st.button("🗑️", key=f"del_shape_{i}_{self.plot_id}"):
                        shapes.pop(i)
                        st.rerun()

                shape["x0"] = try_float(new_x0)
                shape["y0"] = try_float(new_y0)
                shape["x1"] = try_float(new_x1)
                shape["y1"] = try_float(new_y1)

        return shapes

    def render_reorderable_list(
        self,
        label: str,
        items: List[Any],
        key_prefix: str,
        legend_labels: Optional[Dict[str, str]] = None,
        default_order: Optional[List[Any]] = None,
    ) -> List[Any]:
        """
        Render a list that can be reordered using up/down buttons.
        """
        st.markdown(f"**{label}**")

        # Initialize in session state if needed
        ss_key = f"{key_prefix}_order_{self.plot_id}"
        if ss_key not in st.session_state:
            # Use default_order if provided, but validate against current items
            if default_order:
                # Filter default_order to only include items currently in data
                valid_defaults = [x for x in default_order if x in items]
                # Append any new items from data that weren't in default_order
                missing_items = [x for x in items if x not in valid_defaults]
                st.session_state[ss_key] = valid_defaults + missing_items
            else:
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
                display_text = str(item)
                if legend_labels and str(item) in legend_labels:
                    display_text = f"{legend_labels[str(item)]} ({item})"
                st.text(display_text)
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
