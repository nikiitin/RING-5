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

        # Margins expanded by default for better discoverability
        with st.expander("Margins & Spacing", expanded=True):
            m1, m2 = st.columns(2)
            with m1:
                margin_l = st.number_input("Left", 0, 1000, saved_config.get("margin_l", 100), key=f"ml_{self.plot_id}")
                margin_r = st.number_input("Right", 0, 1000, saved_config.get("margin_r", 100), key=f"mr_{self.plot_id}")
                margin_pad = st.number_input("Padding (px)", 0, 200, saved_config.get("margin_pad", 0), key=f"mp_{self.plot_id}", help="Space between axis and labels")
            with m2:
                margin_t = st.number_input("Top", 0, 1000, saved_config.get("margin_t", 80), key=f"mt_{self.plot_id}")
                margin_b = st.number_input("Bottom", 0, 1000, saved_config.get("margin_b", 120), key=f"mb_{self.plot_id}")
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
        leg_cfg1, leg_cfg2 = st.columns(2)
        with leg_cfg1:
            legend_orientation = st.selectbox(
                "Legend Orientation",
                options=["v", "h"],
                format_func=lambda x: "Vertical" if x == "v" else "Horizontal",
                index=0 if saved_config.get("legend_orientation", "v") == "v" else 1,
                key=f"leg_orient_{self.plot_id}",
            )
            legend_x = st.number_input(
                "Legend X Pos",
                value=float(saved_config.get("legend_x", 1.02)),
                step=0.05,
                key=f"leg_x_sm_{self.plot_id}",
            )
            legend_y = st.number_input(
                "Legend Y Pos",
                value=float(saved_config.get("legend_y", 1.0)),
                step=0.05,
                key=f"leg_y_sm_{self.plot_id}",
            )

        with leg_cfg2:
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

        leg_c1, leg_c2 = st.columns(2)
        with leg_c1:
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
            legend_itemsizing = st.selectbox(
                "Legend Marker Scale",
                options=["constant", "trace"],
                index=0 if saved_config.get("legend_itemsizing", "constant") == "constant" else 1,
                key=f"leg_item_sz_{self.plot_id}",
                help="Constant: markers are equal size. Trace: markers match plot size."
            )
            legend_entrywidthmode = st.selectbox(
                "Legend Width Mode",
                options=["pixels", "fraction"],
                index=0 if saved_config.get("legend_entrywidthmode", "pixels") == "pixels" else 1,
                key=f"leg_width_mode_{self.plot_id}",
                help="How to interpret the entry width value."
            )
            legend_entrywidth = st.number_input(
                "Legend Entry Fixed Width (px)",
                min_value=0,
                max_value=1200,
                value=int(saved_config.get("legend_entrywidth")) if saved_config.get("legend_entrywidth") is not None else 0,
                key=f"leg_entry_wd_{self.plot_id}",
                help="Set a fixed width (e.g. 200) to prevent text cropping. Leave at 0 for Plotly default behavior."
            )
            
            legend_tracegroupgap = st.number_input(
                "Legend Item Spacing (px)",
                min_value=0,
                max_value=100,
                value=saved_config.get("legend_tracegroupgap", 10),
                key=f"leg_gap_{self.plot_id}",
                help="Vertical spacing between legend items."
            )

            legend_itemwidth = st.number_input(
                "Legend Item/Marker Width (px)",
                min_value=0,
                max_value=120,
                value=saved_config.get("legend_itemwidth") if saved_config.get("legend_itemwidth") is not None else 30,
                key=f"leg_item_wd_{self.plot_id}",
                help="Width of the legend items (default 30). Set to 0 for auto."
            )

            legend_valign = st.selectbox(
                "Vertical Alignment",
                options=["middle", "top", "bottom"],
                index=["middle", "top", "bottom"].index(saved_config.get("legend_valign", "middle")),
                key=f"leg_valign_{self.plot_id}"
            )

            leg_anchor_col1, leg_anchor_col2 = st.columns(2)
            with leg_anchor_col1:
                legend_xanchor = st.selectbox(
                    "X Anchor",
                    options=["auto", "left", "center", "right"],
                    index=["auto", "left", "center", "right"].index(saved_config.get("legend_xanchor", "auto")),
                    key=f"leg_xanc_{self.plot_id}"
                )
            with leg_anchor_col2:
                legend_yanchor = st.selectbox(
                    "Y Anchor",
                    options=["auto", "top", "middle", "bottom"],
                    index=["auto", "top", "middle", "bottom"].index(saved_config.get("legend_yanchor", "auto")),
                    key=f"leg_yanc_{self.plot_id}"
                )

        st.markdown("#### Typography (Titles & Labels)")
        typo_c1, typo_c2 = st.columns(2)
        with typo_c1:
            # Main Title
            plot_title = st.text_input(
                "Main Plot Title",
                value=saved_config.get("title", ""),
                key=f"plot_title_{self.plot_id}"
            )
            title_font_size = st.number_input(
                "Plot Title Font Size",
                min_value=8,
                max_value=48,
                value=saved_config.get("title_font_size", 18),
                key=f"title_sz_{self.plot_id}",
            )
            
            # X-Axis Title
            xaxis_title = st.text_input(
                "X-Axis Title",
                value=saved_config.get("xaxis_title", ""),
                key=f"xaxis_title_{self.plot_id}"
            )
            xaxis_title_font_size = st.number_input(
                "X-Axis Title Font Size",
                min_value=8,
                max_value=32,
                value=saved_config.get("xaxis_title_font_size", 14),
                key=f"xaxis_title_sz_{self.plot_id}",
            )

            # Y-Axis Title
            yaxis_title = st.text_input(
                "Y-Axis Title",
                value=saved_config.get("yaxis_title", ""),
                key=f"yaxis_title_{self.plot_id}"
            )
            yaxis_title_font_size = st.number_input(
                "Y-Axis Title Font Size",
                min_value=8,
                max_value=32,
                value=saved_config.get("yaxis_title_font_size", 14),
                key=f"yaxis_title_sz_{self.plot_id}",
            )

        with typo_c2:
            xaxis_tickfont_size = st.number_input(
                "X-Axis Label (Tick) Size",
                min_value=8,
                max_value=24,
                value=saved_config.get("xaxis_tickfont_size", 12),
                key=f"xaxis_tick_sz_{self.plot_id}",
                help="Overwrites the basic X-axis font size in Advanced Options"
            )
            yaxis_tickfont_size = st.number_input(
                "Y-Axis Label (Tick) Size",
                min_value=8,
                max_value=24,
                value=saved_config.get("yaxis_tickfont_size", 12),
                key=f"yaxis_tick_sz_{self.plot_id}",
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
            "legend_itemsizing": legend_itemsizing,
            "legend_entrywidth": legend_entrywidth if (legend_entrywidth is not None and legend_entrywidth > 0) else None,
            "legend_entrywidthmode": legend_entrywidthmode,
            "legend_tracegroupgap": legend_tracegroupgap,
            "legend_itemwidth": legend_itemwidth if (legend_itemwidth is not None and legend_itemwidth > 0) else None,
            "legend_valign": legend_valign,
            "legend_xanchor": legend_xanchor,
            "legend_yanchor": legend_yanchor,
            "legend_orientation": legend_orientation,
            "legend_x": legend_x,
            "legend_y": legend_y,
            "title": plot_title,
            "title_font_size": title_font_size,
            "xaxis_title": xaxis_title,
            "xaxis_title_font_size": xaxis_title_font_size,
            "yaxis_title": yaxis_title,
            "yaxis_title_font_size": yaxis_title_font_size,
            "xaxis_tickfont_size": xaxis_tickfont_size,
            "yaxis_tickfont_size": yaxis_tickfont_size,
        }

        return theme_config

    def render_series_styling_ui(self, saved_config: Dict[str, Any], data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Render UI for per-series styling (color, shape, pattern).
        
        Args:
            saved_config: Current configuration
            data: Dataframe containing the series data
            
        Returns:
            Dictionary mapping series names to style configurations
        """
        series_styles = saved_config.get("series_styles", {})
        
        if data is not None:
            # Attempt to find the legend/color column.
            legend_col = saved_config.get("color") or saved_config.get("group")
            
            if legend_col and legend_col in data.columns:
                unique_vals = sorted(data[legend_col].unique().astype(str).tolist())
                
                for val in unique_vals:
                    val_str = str(val)
                    # Create safe short key for Streamlit widgets using hash
                    import hashlib
                    val_hash = hashlib.md5(val_str.encode()).hexdigest()[:8]
                    
                    st.markdown(f"**{val_str}**")
                    c1, c2, c3 = st.columns(3)
                    
                    current_style = series_styles.get(val_str, {})
                    
                    with c1:
                        # Display Name (Renaming)
                        new_name = st.text_input(
                            "Display Name",
                            value=current_style.get("name", val_str),
                            key=f"name_{self.plot_id}_{val_hash}",
                            help="Rename this item in the legend."
                        )
                        current_style["name"] = new_name

                        # Color override
                        new_color = st.color_picker(
                            "Color",
                            current_style.get("color", "#000000"),
                            key=f"color_{self.plot_id}_{val_hash}",
                            help="Pick a specific color for this item."
                        )
                        use_custom_color = st.checkbox(
                            "Apply Color", 
                            value=current_style.get("use_color", False),
                            key=f"use_col_{self.plot_id}_{val_hash}"
                        )

                    with c2:
                        # Symbol (for lines/scatter)
                        if "line" in self.plot_type or "scatter" in self.plot_type:
                            symbols = ["circle", "square", "diamond", "cross", "x", "triangle-up", "triangle-down"]
                            new_symbol = st.selectbox(
                                "Marker Symbol",
                                options=symbols,
                                index=symbols.index(current_style.get("symbol", "circle")) if current_style.get("symbol") in symbols else 0,
                                key=f"sym_{self.plot_id}_{val_hash}"
                            )
                            current_style["symbol"] = new_symbol
                            
                            # Marker Size
                            marker_size = st.number_input(
                                "Marker Size",
                                min_value=0,
                                max_value=50,
                                value=current_style.get("marker_size", 8),
                                key=f"msize_{self.plot_id}_{val_hash}"
                            )
                            current_style["marker_size"] = marker_size

                            # Line Width
                            line_width = st.number_input(
                                "Line Width",
                                min_value=1,
                                max_value=20,
                                value=current_style.get("line_width", 2),
                                key=f"lwidth_{self.plot_id}_{val_hash}"
                            )
                            current_style["line_width"] = line_width
                    
                    with c3:
                        # Pattern (for bars)
                        if "bar" in self.plot_type:
                            patterns = ["", "/", "\\", "x", "-", "|", "+", "."]
                            new_pattern = st.selectbox(
                                "Pattern",
                                options=patterns,
                                index=patterns.index(current_style.get("pattern", "")) if current_style.get("pattern") in patterns else 0,
                                key=f"pat_{self.plot_id}_{val_hash}",
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
                        
                    # Force string key for matching with string trace names
                    series_styles[str(val)] = current_style
        
        return series_styles

    def render_xaxis_labels_ui(self, saved_config: Dict[str, Any], data: Optional[pd.DataFrame] = None) -> Dict[str, str]:
        """
        Render UI for X-Axis label renaming.
        
        Args:
            saved_config: Current configuration
            data: Dataframe containing the data (for x-column values)
            
        Returns:
            Dictionary mapping original X values to custom labels
        """
        xaxis_labels = saved_config.get("xaxis_labels", {})
        x_col = saved_config.get("x")
        
        if data is not None and x_col and x_col in data.columns:
            st.markdown("#### X-Axis Label Overrides")
            with st.expander("Rename X-Axis Labels"):
                # Collect unique vals
                unique_x_raw = data[x_col].unique()
                unique_x = sorted(unique_x_raw, key=lambda x: str(x))
                
                if len(unique_x) > 50:
                    st.warning("Too many X-axis values to list all. Showing first 50.")
                    unique_x = unique_x[:50]
                
                for val in unique_x:
                     s_val = str(val)
                     # Use hash for safe keys
                     import hashlib
                     val_hash = hashlib.md5(s_val.encode()).hexdigest()[:8]
                     
                     col_l, col_r = st.columns([1, 2])
                     with col_l:
                          st.markdown(f"**{val}**")
                     with col_r:
                          new_label = st.text_input(
                              "Display As",
                              value=xaxis_labels.get(s_val, ""),
                              key=f"xlabel_{self.plot_id}_{val_hash}",
                              label_visibility="collapsed",
                              placeholder=s_val
                          )
                          if new_label:
                              xaxis_labels[s_val] = new_label
                          elif s_val in xaxis_labels:
                              # If cleared, remove from config
                              del xaxis_labels[s_val]
        
        return xaxis_labels

    def apply_styles(self, fig: go.Figure, config: Dict[str, Any]) -> go.Figure:
        """
        Apply common layout, theme, and styling settings to the figure.
        Refactored from BasePlot.apply_common_layout.
        """
        # 1. Basic Dimensions & Margins
        layout_args = {
            "width": config.get("width", 800),
            "height": config.get("height", 500),
            "font": {"family": "Arial"},  # Enforce consistent font for consistent export metrics
            "hovermode": "closest",
            "margin": dict(
                b=config.get("margin_b", 120),
                l=config.get("margin_l", 100),
                r=config.get("margin_r", 100),
                t=config.get("margin_t", 80),
                pad=config.get("margin_pad", 0),
                autoexpand=config.get("automargin", True),
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
            "title": dict(
                text=str(config.get("xaxis_title") or config.get("xlabel") or "").replace("undefined", ""),
                font=dict(size=config.get("xaxis_title_font_size", 14))
            ),
            "automargin": config.get("automargin", True),
        }
        if config.get("xaxis_order"):
            xaxis_settings["categoryorder"] = "array"
            xaxis_settings["categoryarray"] = config["xaxis_order"]

        # X-Axis Label Overrides (Applied via tickvals/ticktext)
        if config.get("xaxis_labels"):
            mapping = config["xaxis_labels"]
            # Collect unique X values preserving type
            unique_vals = set()
            for trace in fig.data:
                if trace.x is not None:
                    for x_val in trace.x:
                        unique_vals.add(x_val)
            
            # Sort values
            try:
                # Try sorting as is (works for all num or all str)
                sorted_x = sorted(list(unique_vals))
            except:
                # Fallback: sort by string representation
                sorted_x = sorted(list(unique_vals), key=str)

            # Filter/Order if specific order exists
            if config.get("xaxis_order"):
                # config order is strings, we need to match back to values
                val_map = {str(v): v for v in sorted_x}
                ordered_x = []
                for k in config["xaxis_order"]:
                    if str(k) in val_map:
                        ordered_x.append(val_map[str(k)])
                
                # Add remaining items
                remaining = [v for v in sorted_x if v not in ordered_x]
                final_x = ordered_x + remaining
            else:
                final_x = sorted_x
            
            xaxis_settings["tickmode"] = "array"
            xaxis_settings["tickvals"] = final_x
            xaxis_settings["ticktext"] = [mapping.get(str(x), str(x)) for x in final_x]


        yaxis_settings = {
            "tickfont": dict(size=config.get("yaxis_tickfont_size", 12)),
            "title": dict(
                text=str(config.get("yaxis_title") or config.get("ylabel") or "").replace("undefined", ""),
                font=dict(size=config.get("yaxis_title_font_size", 14))
            ),
        }
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
             fig.update_yaxes(**axis_update)

        # 4b. Explicit Title Overrides (Stronger Application)
        # We re-apply titles here to ensure they override any 'labels' dict from px
        if config.get("xaxis_title"):
             fig.update_xaxes(title_text=config["xaxis_title"])
        if config.get("yaxis_title"):
             fig.update_yaxes(title_text=config["yaxis_title"])

        fig.update_xaxes(**xaxis_settings)
        fig.update_yaxes(**yaxis_settings)

        # 5. Legend Styling & Title
        if config.get("legend_title"):
            fig.update_layout(legend_title_text=config["legend_title"])
       
        # Title Font Size
        fig.update_layout(title=dict(
            text=str(config.get("title") or "").replace("undefined", ""),
            font=dict(size=config.get("title_font_size", 18))
        ))

        legend_update = {
            "orientation": config.get("legend_orientation", "v"),
            "x": config.get("legend_x", 1.02),
            "y": config.get("legend_y", 1.0),
        }
        
        # Handle anchors
        x_anc = config.get("legend_xanchor", "auto")
        if x_anc == "auto":
            legend_update["xanchor"] = "left" if legend_update["x"] > 0.5 else "right"
        else:
            legend_update["xanchor"] = x_anc
            
        y_anc = config.get("legend_yanchor", "auto")
        if y_anc == "auto":
            legend_update["yanchor"] = "top" if legend_update["y"] > 0.5 else "bottom"
        else:
            legend_update["yanchor"] = y_anc
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
        
        if config.get("legend_itemsizing"):
            legend_update["itemsizing"] = config["legend_itemsizing"]
        
        if config.get("legend_entrywidth"):
            legend_update["entrywidth"] = int(config["legend_entrywidth"])
            legend_update["entrywidthmode"] = "pixels"  # Force pixels to ensure behavior

        if config.get("legend_tracegroupgap"):
            legend_update["tracegroupgap"] = config["legend_tracegroupgap"]

        if config.get("legend_itemwidth"):
            legend_update["itemwidth"] = config["legend_itemwidth"]

        if config.get("legend_valign"):
            legend_update["valign"] = config["legend_valign"]

        if legend_update:
            fig.update_layout(legend=legend_update)

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
             if style.get("name"):
                 trace.name = style["name"]

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
                 
             # Marker Size & Line Width
             if style.get("marker_size"):
                 trace.update(marker=dict(size=style["marker_size"]))

             if style.get("line_width"):
                 trace.update(line=dict(width=style["line_width"]))

             # Pattern
             if style.get("pattern"):
                  trace.update(marker=dict(pattern=dict(shape=style["pattern"], fillmode="replace")))
             elif config.get("enable_stripes") and "bar" in self.plot_type:
                  trace.update(marker=dict(pattern=dict(shape="/", fillmode="replace")))
