from typing import Any, Dict, List, Optional
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

class StyleManager:
    """
    Manages style and theme configurations for plots.
    Encapsulates UI rendering and style application logic.
    """

    def __init__(self, plot_id: int, plot_type: str):
        """
        Initialize StyleManager.

        Args:
            plot_id: Unique identifier for the plot (for widget keys)
            plot_type: Type of the plot (bar, line, etc.) used for conditional logic
        """
        self.plot_id = plot_id
        self.plot_type = plot_type

    def get_legend_column(self, config: Dict[str, Any]) -> Optional[str]:
        """
        Helper to get legend/color column from config.
        Ideally this logic should stay in Plot, but we might need it for per-series checking.
        """
        # Common keys usually used for grouping/coloring
        return config.get("color") or config.get("group")

        return {"width": width, "height": height}

    def render_layout_options(self, saved_config: Dict[str, Any]) -> Dict[str, Any]:
        """Render layout sizing, margins, and spacing options."""
        st.markdown("**Dimensions & Margins**")
        
        # Dimensions
        c1, c2 = st.columns(2)
        with c1:
            width = st.slider(
                "Width (px)", 400, 1600, saved_config.get("width", 800), 50, key=f"w_{self.plot_id}"
            )
        with c2:
            height = st.slider(
                "Height (px)", 300, 1200, saved_config.get("height", 500), 50, key=f"h_{self.plot_id}"
            )

        # Margins expander
        with st.expander("Margins & Spacing"):
            m1, m2 = st.columns(2)
            with m1:
                margin_l = st.number_input("Left", 0, 500, saved_config.get("margin_l", 80), key=f"ml_{self.plot_id}")
                margin_r = st.number_input("Right", 0, 500, saved_config.get("margin_r", 80), key=f"mr_{self.plot_id}")
                margin_pad = st.number_input("Padding (px)", 0, 100, saved_config.get("margin_pad", 0), key=f"mp_{self.plot_id}", help="Space between axis and labels")
            with m2:
                margin_t = st.number_input("Top", 0, 500, saved_config.get("margin_t", 80), key=f"mt_{self.plot_id}")
                margin_b = st.number_input("Bottom", 0, 500, saved_config.get("margin_b", 100), key=f"mb_{self.plot_id}")
                automargin = st.checkbox("Auto-Marg (Prevents Cutoff)", value=saved_config.get("automargin", True), key=f"am_{self.plot_id}")

        return {
            "width": width, 
            "height": height,
            "margin_l": margin_l,
            "margin_r": margin_r,
            "margin_t": margin_t,
            "margin_b": margin_b,
            "margin_pad": margin_pad,
            "automargin": automargin
        }

    def render_theme_options(self, saved_config: Dict[str, Any], data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Render theme and style configuration options.
        
        Args:
            saved_config: Previously saved configuration
            data: Dataframe used for extracting unique legend items for per-series styling
            
        Returns:
            Configuration dictionary with theme options
        """
        st.markdown("#### Color Palette")
        
        # Get available qualitative palettes
        available_palettes = ["Plotly", "G10", "T10", "Alphabet", "Dark24", "Light24", 
                            "Pastel", "Set1", "Set2", "Set3", "Tableau", "Safe", "Vivid"]
                            
        current_palette = saved_config.get("color_palette", "Plotly")
        if current_palette not in available_palettes:
            current_palette = "Plotly"
            
        color_palette = st.selectbox(
            "Select Color Palette",
            options=available_palettes,
            index=available_palettes.index(current_palette),
            key=f"palette_{self.plot_id}",
            help="Choose a color scheme for the plot series/groups."
        )

        st.markdown("#### Backgrounds & Grid")
        
        transparent_bg = st.checkbox(
            "Transparent Background",
            value=saved_config.get("transparent_bg", False),
            key=f"trans_bg_{self.plot_id}",
            help="Make the plot background fully transparent.",
        )

        theme_cols1, theme_cols2 = st.columns(2)
        with theme_cols1:
            if not transparent_bg:
                plot_bgcolor = st.color_picker(
                    "Plot Background",
                    saved_config.get("plot_bgcolor", "#ffffff"),
                    key=f"bg_plot_{self.plot_id}",
                )
                paper_bgcolor = st.color_picker(
                    "Paper (Outer) Background",
                    saved_config.get("paper_bgcolor", "#ffffff"),
                    key=f"bg_paper_{self.plot_id}",
                )
            else:
                plot_bgcolor = "rgba(0,0,0,0)"
                paper_bgcolor = "rgba(0,0,0,0)"

            grid_color = st.color_picker(
                "Grid Color",
                saved_config.get("grid_color", "#e5e5e5"),
                key=f"grid_col_{self.plot_id}",
            )

        with theme_cols2:
            axis_color = st.color_picker(
                "Axis Line/Tick Color",
                saved_config.get("axis_color", "#444444"),
                key=f"axis_col_{self.plot_id}",
            )

            if "bar" in self.plot_type:
                enable_stripes = st.checkbox(
                    "Enable Bar Stripes",
                    value=saved_config.get("enable_stripes", False),
                    key=f"stripes_{self.plot_id}",
                    help="Adds a diagonal pattern to bars for better differentiation.",
                )
            else:
                enable_stripes = False

        st.markdown("#### Legend Styling")
        leg_c1, leg_c2 = st.columns(2)
        with leg_c1:
            legend_font_color = st.color_picker(
                "Legend Text Color",
                saved_config.get("legend_font_color", "#000000"),
                key=f"leg_font_col_{self.plot_id}",
            )
            legend_font_size = st.number_input(
                "Legend Font Size",
                min_value=8,
                max_value=24,
                value=saved_config.get("legend_font_size", 12),
                key=f"leg_font_sz_{self.plot_id}",
            )
            legend_title_font_color = st.color_picker(
                "Legend Title Color",
                saved_config.get("legend_title_font_color", "#000000"),
                key=f"leg_title_col_{self.plot_id}",
            )
            legend_title_font_size = st.number_input(
                "Legend Title Font Size",
                min_value=8,
                max_value=28,
                value=saved_config.get("legend_title_font_size", 14),
                key=f"leg_title_sz_{self.plot_id}",
            )

        with leg_c2:
            # Ensure color is hex
            bg_col = saved_config.get("legend_bgcolor", "#ffffff")
            if str(bg_col).startswith("rgba"):
                bg_col = "#ffffff"

            transparent_legend = st.checkbox(
                "Transparent Legend",
                value=saved_config.get("transparent_legend", False),
                key=f"trans_leg_{self.plot_id}"
            )
            
            if not transparent_legend:
                legend_bgcolor = st.color_picker(
                    "Legend Background",
                    bg_col,
                    key=f"leg_bg_col_{self.plot_id}",
                )
            else:
                legend_bgcolor = "rgba(0,0,0,0)"
            legend_border_color = st.color_picker(
                "Legend Border Color",
                saved_config.get("legend_border_color", "#000000"),
                key=f"leg_bord_col_{self.plot_id}",
            )
            legend_border_width = st.number_input(
                "Legend Border Width",
                min_value=0,
                max_value=5,
                value=saved_config.get("legend_border_width", 0),
                key=f"leg_bord_wd_{self.plot_id}",
            )

        theme_config = {
            "color_palette": color_palette,
            "transparent_bg": transparent_bg,
            "plot_bgcolor": plot_bgcolor,
            "paper_bgcolor": paper_bgcolor,
            "grid_color": grid_color,
            "axis_color": axis_color,
            "enable_stripes": enable_stripes,
            "legend_font_color": legend_font_color,
            "legend_font_size": legend_font_size,
            "legend_title_font_color": legend_title_font_color,
            "legend_title_font_size": legend_title_font_size,
            "transparent_legend": transparent_legend,
            "legend_bgcolor": legend_bgcolor,
            "legend_border_color": legend_border_color,
            "legend_border_width": legend_border_width,
        }

        # Per-Series Styling
        if data is not None:
            # Attempt to find the legend/color column.
            # Stategy: check for 'color' or 'group' in saved_config
            legend_col = saved_config.get("color") or saved_config.get("group")
            
            series_styles = saved_config.get("series_styles", {})
            
            if legend_col and legend_col in data.columns:
                st.markdown("#### Per-Series Styling")
                with st.expander("Configure Color, Shape & Pattern by Series"):
                    unique_vals = sorted(data[legend_col].unique().astype(str).tolist())
                    
                    for val in unique_vals:
                        st.markdown(f"**{val}**")
                        c1, c2, c3 = st.columns(3)
                        
                        current_style = series_styles.get(val, {})
                        
                        with c1:
                            # Color override
                            new_color = st.color_picker(
                                "Color",
                                current_style.get("color", "#000000"),
                                key=f"color_{self.plot_id}_{val}",
                                help="Pick a specific color for this item."
                            )
                            use_custom_color = st.checkbox(
                                "Apply Color", 
                                value=current_style.get("use_color", False),
                                key=f"use_col_{self.plot_id}_{val}"
                            )

                        with c2:
                            # Symbol (for lines/scatter)
                            if "line" in self.plot_type or "scatter" in self.plot_type:
                                symbols = ["circle", "square", "diamond", "cross", "x", "triangle-up", "triangle-down"]
                                new_symbol = st.selectbox(
                                    "Marker Symbol",
                                    options=symbols,
                                    index=symbols.index(current_style.get("symbol", "circle")) if current_style.get("symbol") in symbols else 0,
                                    key=f"sym_{self.plot_id}_{val}"
                                )
                                current_style["symbol"] = new_symbol
                        
                        with c3:
                            # Pattern (for bars)
                            if "bar" in self.plot_type:
                                patterns = ["", "/", "\\", "x", "-", "|", "+", "."]
                                new_pattern = st.selectbox(
                                    "Pattern",
                                    options=patterns,
                                    index=patterns.index(current_style.get("pattern", "")) if current_style.get("pattern") in patterns else 0,
                                    key=f"pat_{self.plot_id}_{val}",
                                    format_func=lambda x: "Solid" if x == "" else x
                                )
                                current_style["pattern"] = new_pattern

                        # Update config
                        if use_custom_color:
                            current_style["color"] = new_color
                            current_style["use_color"] = True
                        else:
                            current_style.pop("color", None)
                            current_style["use_color"] = False
                            
                        series_styles[val] = current_style

            theme_config["series_styles"] = series_styles
            
        return theme_config

    def apply_styles(self, fig: go.Figure, config: Dict[str, Any]) -> go.Figure:
        """
        Apply common layout, theme, and styling settings to the figure.
        Refactored from BasePlot.apply_common_layout.
        """
        # 1. Basic Dimensions & Margins
        layout_args = {
            "width": config.get("width", 800),
            "height": config.get("height", 500),
            "hovermode": "closest",
            "margin": dict(
                b=config.get("margin_b", 100),
                l=config.get("margin_l", 80),
                r=config.get("margin_r", 80),
                t=config.get("margin_t", 80),
                pad=config.get("margin_pad", 0),
            ),
            "legend": dict(
                orientation=config.get("legend_orientation", "v"),
                x=config.get("legend_x", 1.02),
                y=config.get("legend_y", 1.0),
            ),
        }

        # Bar speifics
        if "bar" in self.plot_type:
            layout_args["bargap"] = config.get("bargap", 0.2)
            if "grouped" in self.plot_type:
                layout_args["bargroupgap"] = config.get("bargroupgap", 0.0)

        # Apply basic layout
        fig.update_layout(**layout_args)

        # 2. Theme Backgrounds
        if config.get("plot_bgcolor"):
            fig.update_layout(plot_bgcolor=config["plot_bgcolor"])
        if config.get("paper_bgcolor"):
            fig.update_layout(paper_bgcolor=config["paper_bgcolor"])

        # 3. Axis Settings (Ticks, Logic)
        xaxis_settings = {
            "tickangle": config.get("xaxis_tickangle", -45),
            "tickfont": dict(size=config.get("xaxis_tickfont_size", 12)),
            "automargin": config.get("automargin", True),
        }
        if config.get("xaxis_order"):
            xaxis_settings["categoryorder"] = "array"
            xaxis_settings["categoryarray"] = config["xaxis_order"]

        yaxis_settings = {}
        if config.get("yaxis_dtick"):
            yaxis_settings["dtick"] = config["yaxis_dtick"]

        # 4. Axis Styling (Colors, Grids)
        axis_color = config.get("axis_color")
        grid_color = config.get("grid_color")
        
        if axis_color or grid_color:
             axis_update = {}
             if axis_color:
                 axis_update.update(dict(
                     linecolor=axis_color,
                     tickcolor=axis_color,
                     tickfont=dict(color=axis_color),
                     title_font=dict(color=axis_color)
                 ))
             if grid_color:
                 axis_update.update(dict(
                     gridcolor=grid_color,
                     zerolinecolor=grid_color
                 ))
             fig.update_xaxes(**axis_update)
             fig.update_yaxes(**axis_update)

        fig.update_xaxes(**xaxis_settings)
        fig.update_yaxes(**yaxis_settings)

        # 5. Legend Styling & Title
        if config.get("legend_title"):
            fig.update_layout(legend_title_text=config["legend_title"])

        legend_update = {}
        if config.get("legend_font_color"):
             legend_update["font"] = dict(color=config["legend_font_color"], size=config.get("legend_font_size", 12))
        if config.get("legend_title_font_color") or config.get("legend_title_font_size"):
             legend_update["title"] = dict(
                 font=dict(
                     color=config.get("legend_title_font_color", "#000000"),
                     size=config.get("legend_title_font_size", 14)
                 )
             )
        if config.get("legend_bgcolor"):
             legend_update["bgcolor"] = config["legend_bgcolor"]
        if config.get("legend_border_width", 0) > 0:
             legend_update["bordercolor"] = config.get("legend_border_color", "#000000")
             legend_update["borderwidth"] = config["legend_border_width"]
        if legend_update:
            fig.update_layout(legend=legend_update)

        # 6. Global Trace Updates (Hover, Borders)
        if config.get("bar_border_width", 0) > 0:
            fig.update_traces(
                marker=dict(line=dict(width=config["bar_border_width"], color="white"))
            )
        fig.update_traces(hovertemplate="<b>%{x}</b><br>%{y:.4f}<extra></extra>")

        # 7. Color Palette & Per-Series Styling
        self._apply_series_styling(fig, config)

        # 8. Annotations (Shapes)
        if config.get("shapes"):
            fig.update_layout(shapes=config["shapes"])
            
        return fig

    def _apply_series_styling(self, fig: go.Figure, config: Dict[str, Any]):
        """
        Internal method to iterate traces and apply palette/custom styles.
        """
        series_styles = config.get("series_styles", {})
        
        # Resolve palette colors
        palette_colors = None
        if config.get("color_palette") and config["color_palette"] != "Plotly":
             import plotly.express as px
             palette_map = {
                "G10": px.colors.qualitative.G10,
                "T10": px.colors.qualitative.T10,
                "Tableau": px.colors.qualitative.T10,
                "Alphabet": px.colors.qualitative.Alphabet,
                "Dark24": px.colors.qualitative.Dark24,
                "Light24": px.colors.qualitative.Light24,
                "Pastel": px.colors.qualitative.Pastel,
                "Set1": px.colors.qualitative.Set1,
                "Set2": px.colors.qualitative.Set2,
                "Set3": px.colors.qualitative.Set3,
                "Safe": px.colors.qualitative.Safe,
                "Vivid": px.colors.qualitative.Vivid,
             }
             palette_colors = palette_map.get(config["color_palette"])
        
        # Iterate traces
        for i, trace in enumerate(fig.data):
             t_name = str(getattr(trace, "name", ""))
             style = series_styles.get(t_name, {})
             
             # Color Priority: Custom > Palette > Default
             if style.get("use_color") and style.get("color"):
                 trace.update(marker=dict(color=style["color"]))
                 # Only update line color for scatter/line traces (not bar)
                 if hasattr(trace, 'line') and trace.type in ['scatter', 'scattergl']:
                     trace.update(line=dict(color=style["color"]))
             elif palette_colors:
                 col = palette_colors[i % len(palette_colors)]
                 trace.update(marker=dict(color=col))
                 if hasattr(trace, 'line') and trace.type in ['scatter', 'scattergl']:
                     trace.update(line=dict(color=col))
                 
             # Symbol
             if style.get("symbol"):
                 trace.update(marker=dict(symbol=style["symbol"]))
                 
             # Pattern
             if style.get("pattern"):
                  trace.update(marker=dict(pattern=dict(shape=style["pattern"], fillmode="replace")))
             elif config.get("enable_stripes") and "bar" in self.plot_type:
                  trace.update(marker=dict(pattern=dict(shape="/", fillmode="replace")))
