from typing import Any, Dict

import plotly.graph_objects as go


class StyleApplicator:
    """
    Handles application of styles, themes, and layouts to Plotly figures.
    Decoupled from UI rendering.
    """

    def __init__(self, plot_type: str):
        self.plot_type = plot_type

    def apply_styles(self, fig: go.Figure, config: Dict[str, Any]) -> go.Figure:
        """
        Apply common layout, theme, and styling settings to the figure.
        Delegates to specialized methods for cleaner code organization.
        """
        # Apply styling in logical phases
        fig = self._apply_dimensions_and_margins(fig, config)
        fig = self._apply_backgrounds(fig, config)
        fig = self._apply_axes_styling(fig, config)
        legend_update = self._build_legend_config(config)
        fig = self._apply_titles(fig, config)

        # Data labels (show values)
        if config.get("show_values"):
            fig = self._apply_data_labels(fig, config)

        # Per-Series Styling
        self._apply_series_styling(fig, config)

        # Handle Columns (Strict Mode vs Standard)
        self._apply_legend_layout(fig, config, legend_update)

        # Annotations/Shapes
        if config.get("shapes"):
            fig.update_layout(shapes=config["shapes"])

        return fig

    def _apply_dimensions_and_margins(self, fig: go.Figure, config: Dict[str, Any]) -> go.Figure:
        """Apply basic dimensions, margins, and bar-specific settings."""
        layout_args = {
            "width": config.get("width", 800),
            "height": config.get("height", 500),
            "font": {"family": "Arial"},
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

        # Bar specifics
        if "bar" in self.plot_type:
            layout_args["bargap"] = config.get("bargap", 0.2)
            if "grouped" in self.plot_type:
                layout_args["bargroupgap"] = config.get("bargroupgap", 0.0)

        fig.update_layout(**layout_args)
        return fig

    def _apply_backgrounds(self, fig: go.Figure, config: Dict[str, Any]) -> go.Figure:
        """Apply theme backgrounds (plot and paper colors)."""
        if config.get("plot_bgcolor"):
            fig.update_layout(plot_bgcolor=config["plot_bgcolor"])
        if config.get("paper_bgcolor"):
            fig.update_layout(paper_bgcolor=config["paper_bgcolor"])
        return fig

    def _apply_axes_styling(self, fig: go.Figure, config: Dict[str, Any]) -> go.Figure:
        """Apply axis settings including ticks, colors, and label overrides."""
        xaxis_settings = {
            "tickangle": config.get("xaxis_tickangle", -45),
            "tickfont": dict(
                size=config.get("xaxis_tickfont_size", 12),
                color=config.get("xaxis_tickfont_color", "#444444"),
            ),
            "title": dict(
                text=str(config.get("xaxis_title") or config.get("xlabel") or "").replace(
                    "undefined", ""
                ),
                font=dict(size=config.get("xaxis_title_font_size", 14)),
            ),
            "automargin": config.get("automargin", True),
        }

        if config.get("xaxis_order"):
            xaxis_settings["categoryorder"] = "array"
            xaxis_settings["categoryarray"] = config["xaxis_order"]

        # Range overrides (Zoom)
        if config.get("range_x"):
            xaxis_settings["range"] = config["range_x"]
            xaxis_settings["autorange"] = False

        # X-Axis Label Overrides (skip for grouped bar types)
        if config.get("xaxis_labels") and self.plot_type not in [
            "grouped_stacked_bar",
            "grouped_bar",
        ]:
            xaxis_settings = self._apply_xaxis_label_overrides(fig, config, xaxis_settings)

        yaxis_settings = {
            "tickfont": dict(
                size=config.get("yaxis_tickfont_size", 12),
                color=config.get("yaxis_tickfont_color", "#444444"),
            ),
            "title": dict(
                text=str(config.get("yaxis_title") or config.get("ylabel") or "").replace(
                    "undefined", ""
                ),
                font=dict(size=config.get("yaxis_title_font_size", 14)),
                standoff=config.get("yaxis_title_standoff", 0),
            ),
        }
        if config.get("yaxis_dtick"):
            yaxis_settings["dtick"] = config["yaxis_dtick"]

        if config.get("range_y"):
            yaxis_settings["range"] = config["range_y"]
            yaxis_settings["autorange"] = False

        # Axis color styling
        self._apply_axis_colors(fig, config)

        # Explicit Title Overrides
        if config.get("xaxis_title"):
            fig.update_xaxes(title_text=config["xaxis_title"])

        # Y-Axis Title Logic (Native vs Annotation)
        y_title_text = yaxis_settings["title"]["text"]
        y_vshift = int(config.get("yaxis_title_vshift") or 0)

        if y_title_text:
            if y_vshift != 0:
                # Manual Mode (Annotation)
                self._apply_yaxis_title_annotation(fig, config, y_title_text, y_vshift)
                # Hide native title in settings so it doesn't get reapplied
                yaxis_settings["title"]["text"] = ""

        fig.update_xaxes(**xaxis_settings)
        fig.update_yaxes(**yaxis_settings)
        return fig

    def _apply_xaxis_label_overrides(
        self, fig: go.Figure, config: Dict[str, Any], xaxis_settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply X-axis label override mapping."""
        mapping = config["xaxis_labels"]
        unique_vals = set()
        for trace in fig.data:
            if trace.x is not None:
                for x_val in trace.x:
                    unique_vals.add(x_val)

        try:
            sorted_x = sorted(list(unique_vals))
        except Exception:
            sorted_x = sorted(list(unique_vals), key=str)

        if config.get("xaxis_order"):
            val_map = {str(v): v for v in sorted_x}
            ordered_x = []
            for k in config["xaxis_order"]:
                if str(k) in val_map:
                    ordered_x.append(val_map[str(k)])
            remaining = [v for v in sorted_x if v not in ordered_x]
            final_x = ordered_x + remaining
        else:
            final_x = sorted_x

        xaxis_settings["tickmode"] = "array"
        xaxis_settings["tickvals"] = final_x
        xaxis_settings["ticktext"] = [mapping.get(str(x), str(x)) for x in final_x]
        return xaxis_settings

    def _apply_axis_colors(self, fig: go.Figure, config: Dict[str, Any]) -> None:
        """Apply axis and grid colors."""
        axis_color = config.get("axis_color")
        grid_color = config.get("grid_color")

        if axis_color or grid_color:
            axis_update = {}
            if axis_color:
                axis_update.update(
                    dict(
                        linecolor=axis_color,
                        tickcolor=axis_color,
                        tickfont=dict(color=axis_color),
                        title_font=dict(color=axis_color),
                    )
                )
            if grid_color:
                axis_update.update(dict(gridcolor=grid_color, zerolinecolor=grid_color))
            fig.update_yaxes(**axis_update)

    def _build_legend_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Build legend configuration dictionary."""
        legend_update = {
            "orientation": config.get("legend_orientation", "v"),
            "x": config.get("legend_x", 1.02),
            "y": config.get("legend_y", 1.0),
        }

        x_anc = config.get("legend_xanchor", "auto")
        if x_anc == "auto":
            # If x is on the left (<=0.5), anchor left (grow right).
            # If x is on the right (>0.5), anchor right (grow left) to prevent overflow.
            legend_update["xanchor"] = "left" if legend_update["x"] <= 0.5 else "right"
        else:
            legend_update["xanchor"] = x_anc

        y_anc = config.get("legend_yanchor", "auto")
        if y_anc == "auto":
            legend_update["yanchor"] = "top" if legend_update["y"] > 0.5 else "bottom"
        else:
            legend_update["yanchor"] = y_anc

        if config.get("legend_font_color"):
            legend_update["font"] = dict(
                color=config["legend_font_color"], size=config.get("legend_font_size", 12)
            )

        if config.get("legend_title_font_color") or config.get("legend_title_font_size"):
            legend_update["title"] = dict(
                font=dict(
                    color=config.get("legend_title_font_color", "#000000"),
                    size=config.get("legend_title_font_size", 14),
                )
            )

        if config.get("legend_bgcolor"):
            legend_update["bgcolor"] = config["legend_bgcolor"]

        if config.get("legend_border_width", 0) > 0:
            legend_update["bordercolor"] = config.get("legend_border_color", "#000000")
            legend_update["borderwidth"] = config["legend_border_width"]

        if config.get("legend_itemsizing"):
            legend_update["itemsizing"] = config["legend_itemsizing"]

        return legend_update

    def _apply_titles(self, fig: go.Figure, config: Dict[str, Any]) -> go.Figure:
        """Apply title and legend title."""
        if config.get("legend_title"):
            fig.update_layout(legend_title_text=config["legend_title"])

        fig.update_layout(
            title=dict(
                text=str(config.get("title") or "").replace("undefined", ""),
                font=dict(size=config.get("title_font_size", 18)),
            )
        )
        return fig

    def _apply_data_labels(self, fig: go.Figure, config: Dict[str, Any]) -> go.Figure:
        """Apply data labels (text values on bars/points) with validation."""
        # Safe extraction with type coercion and validation
        text_fmt = config.get("text_format") or "%{y:.2f}"
        text_pos = config.get("text_position") or "auto"
        if text_pos not in ["auto", "inside", "outside"]:
            text_pos = "auto"

        text_col_mode = config.get("text_color_mode") or "Custom"
        text_col = config.get("text_color")

        # Ensure rotation is a valid number
        try:
            text_rot = int(config.get("text_rotation") or 0)
            text_rot = max(-360, min(360, text_rot))  # Clamp to valid range
        except (ValueError, TypeError):
            text_rot = 0

        text_anc = config.get("text_anchor")
        if text_anc and text_anc not in ["auto", "start", "middle", "end"]:
            text_anc = None

        # Clip on axis logic
        should_clip = text_anc in ["start", "middle"]

        # Constraint Logic
        should_constrain = bool(config.get("text_constraint", False))
        if should_constrain:
            text_pos = "inside"
            constraint_val = "inside"
            if not text_anc or text_anc == "auto":
                text_anc = "middle"
        else:
            constraint_val = "none"

        trace_update = dict(
            texttemplate=text_fmt,
            textposition=text_pos,
            textangle=text_rot,
            cliponaxis=should_clip,
            constraintext=constraint_val,
        )

        # Font size with validation
        try:
            text_font_size = int(config.get("text_font_size") or 12)
            text_font_size = max(6, min(100, text_font_size))
        except (ValueError, TypeError):
            text_font_size = 12

        # Apply text font
        if text_col_mode == "Custom" and text_col:
            trace_update["textfont"] = dict(color=text_col, size=text_font_size)
        else:
            trace_update["textfont"] = dict(size=text_font_size)

        # Inside text anchor
        if text_pos == "inside" and text_anc and text_anc != "auto":
            trace_update["insidetextanchor"] = text_anc

        # Conditional display logic
        display_logic = config.get("text_display_logic") or "Always Show"
        try:
            threshold = float(config.get("text_threshold") or 0.0)
        except (ValueError, TypeError):
            threshold = 0.0

        if display_logic == "If > Threshold":
            self._apply_conditional_labels(
                fig, config, trace_update, text_fmt, text_pos, text_anc, text_rot, threshold
            )
        else:
            fig.update_traces(**trace_update)

        # Apply uniformtext for constraint
        if should_constrain:
            min_size = max(6, text_font_size - 4)
            fig.update_layout(uniformtext_minsize=min_size, uniformtext_mode="hide")

        # Auto Contrast post-processing
        if text_col_mode == "Auto Contrast":
            self._apply_auto_contrast(fig)

        return fig

    def _apply_conditional_labels(
        self,
        fig: go.Figure,
        config: Dict[str, Any],
        trace_update: Dict[str, Any],
        text_fmt: str,
        text_pos: str,
        text_anc: str,
        text_rot: int,
        threshold: float,
    ) -> None:
        """Apply conditional data labels (only show if value > threshold)."""
        if "texttemplate" in trace_update:
            del trace_update["texttemplate"]

        py_fmt = "{:.2f}"
        if text_fmt.startswith("%{y:") and text_fmt.endswith("}"):
            fmt_spec = text_fmt[4:-1]
            py_fmt = "{:" + fmt_spec + "}"

        for trace in fig.data:
            if getattr(trace, "y", None) is not None:
                text_values = []
                for y_val in trace.y:
                    if y_val is None:
                        text_values.append("")
                    elif y_val > threshold:
                        try:
                            text_values.append(py_fmt.format(y_val))
                        except ValueError:
                            text_values.append(str(y_val))
                    else:
                        text_values.append("")

                trace.text = text_values
                trace.texttemplate = None
                trace.textposition = text_pos
                if text_pos == "inside" and text_anc and text_anc != "auto":
                    trace.insidetextanchor = text_anc
                trace.textangle = text_rot
                trace.cliponaxis = text_anc in ["start", "middle"]
                trace.constraintext = "none"

        fig.update_traces(**trace_update)

    def _apply_auto_contrast(self, fig: go.Figure) -> None:
        """Apply auto-contrast text color based on marker color."""
        for trace in fig.data:
            marker = getattr(trace, "marker", None)
            if marker:
                color = None
                if isinstance(marker.color, str):
                    color = marker.color
                elif isinstance(marker, dict) and "color" in marker:
                    color = marker["color"]

                if color and isinstance(color, str):
                    contrast_col = self._get_contrast_color(color)
                    trace.textfont = dict(color=contrast_col)

    def _get_contrast_color(self, hex_color: str) -> str:
        """
        Determine black or white contrast for a given color.
        Simple luminance formula.
        """
        if not hex_color or not isinstance(hex_color, str):
            return "#000000"

        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            # Luminance
            lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return "#000000" if lum > 0.5 else "#FFFFFF"
        return "#000000"

    def _apply_legend_layout(
        self,
        fig: go.Figure,
        config: Dict[str, Any],
        base_legend_update: Dict[str, Any],
    ):
        """
        Apply legend layout logic.
        When ncols > 1, create multiple legend objects for true column layout.
        """
        try:
            ncols = int(config.get("legend_ncols") or 0)
        except (ValueError, TypeError):
            ncols = 0

        col_width = config.get("legend_col_width", 150)

        # Get base position
        base_x = base_legend_update.get("x", 1.02)
        base_y = base_legend_update.get("y", 1.0)
        x_anchor = base_legend_update.get("xanchor", "left")

        if ncols > 1:
            # Multi-legend approach for true column control
            num_traces = len(fig.data)
            if num_traces == 0:
                fig.update_layout(legend=base_legend_update)
                return

            # Calculate items per column (distribute evenly, fill columns top-to-bottom)
            items_per_col = (num_traces + ncols - 1) // ncols  # ceiling division

            # Convert col_width to fraction of plot (assuming ~1000px plot width)
            plot_width = config.get("width", 1000)
            col_width_frac = col_width / plot_width

            # Create legend config for each column
            legend_configs = {}
            for col_idx in range(ncols):
                legend_name = "legend" if col_idx == 0 else f"legend{col_idx + 1}"

                # Get position for this legend column
                # Check if there's a stored position for this legend, otherwise calculate
                if col_idx == 0:
                    # Primary legend uses base position
                    col_x = config.get("legend_x", base_x)
                    col_y = config.get("legend_y", base_y)
                    col_xanchor = config.get("legend_xanchor", x_anchor)
                    col_yanchor = config.get("legend_yanchor", "top")
                else:
                    # Secondary legends (legend2, legend3, etc.)
                    stored_x = config.get(f"legend{col_idx + 1}_x")
                    stored_y = config.get(f"legend{col_idx + 1}_y")

                    if stored_x is not None:
                        col_x = stored_x
                    else:
                        # Calculate initial position side by side
                        if x_anchor == "left":
                            col_x = base_x + (col_idx * col_width_frac)
                        elif x_anchor == "right":
                            col_x = base_x - ((ncols - 1 - col_idx) * col_width_frac)
                        else:  # center
                            offset = (col_idx - (ncols - 1) / 2) * col_width_frac
                            col_x = base_x + offset

                    col_y = stored_y if stored_y is not None else base_y
                    col_xanchor = config.get(f"legend{col_idx + 1}_xanchor", x_anchor)
                    col_yanchor = config.get(f"legend{col_idx + 1}_yanchor", "top")

                # Build legend config for this column
                # NOTE: No borders on individual columns to avoid "double border" appearance
                legend_config = {
                    "title": base_legend_update.get("title") if col_idx == 0 else {"text": ""},
                    "font": base_legend_update.get("font", {}),
                    "bgcolor": base_legend_update.get("bgcolor", "#ffffff"),
                    "bordercolor": "rgba(0,0,0,0)",  # Transparent border
                    "borderwidth": 0,  # No border on individual columns
                    "orientation": "v",  # Vertical for column layout
                    "x": col_x,
                    "y": col_y,
                    "xanchor": col_xanchor,
                    "yanchor": col_yanchor,
                    "itemsizing": base_legend_update.get("itemsizing", "constant"),
                    "valign": base_legend_update.get("valign", "middle"),
                }

                legend_configs[legend_name] = legend_config

            # Apply all legend configs to layout
            fig.update_layout(**legend_configs)

            # Assign traces to their respective legend columns
            for trace_idx, trace in enumerate(fig.data):
                col_idx = trace_idx // items_per_col
                col_idx = min(col_idx, ncols - 1)  # Clamp to last column
                legend_name = "legend" if col_idx == 0 else f"legend{col_idx + 1}"
                trace.update(legend=legend_name)

        else:
            # Single legend (default behavior)
            fig.update_layout(legend=base_legend_update)

    def _apply_series_styling(self, fig: go.Figure, config: Dict[str, Any]):
        """
        Apply per-series styling (colors, symbols, etc.)
        """
        series_styles = config.get("series_styles", {})

        palette_colors = None
        if config.get("color_palette"):
            from src.plotting.styles.colors import get_palette_colors

            palette_colors = get_palette_colors(config["color_palette"])

        for i, trace in enumerate(fig.data):
            t_name = str(getattr(trace, "name", ""))
            style = series_styles.get(t_name, {})

            if style.get("name"):
                trace.name = style["name"]

            if style.get("use_color") and style.get("color"):
                trace.update(marker=dict(color=style["color"]))
                if hasattr(trace, "line") and trace.type in ["scatter", "scattergl"]:
                    trace.update(line=dict(color=style["color"]))
            elif palette_colors:
                col = palette_colors[i % len(palette_colors)]
                trace.update(marker=dict(color=col))
                if hasattr(trace, "line") and trace.type in ["scatter", "scattergl"]:
                    trace.update(line=dict(color=col))

            if style.get("symbol"):
                trace.update(marker=dict(symbol=style["symbol"]))

            if style.get("marker_size"):
                trace.update(marker=dict(size=style["marker_size"]))

            if style.get("line_width"):
                trace.update(line=dict(width=style["line_width"]))

            if style.get("pattern"):
                trace.update(marker=dict(pattern=dict(shape=style["pattern"], fillmode="replace")))
            elif config.get("enable_stripes") and "bar" in self.plot_type:
                trace.update(marker=dict(pattern=dict(shape="/", fillmode="replace")))

    def _apply_yaxis_title_annotation(
        self, fig: go.Figure, config: Dict[str, Any], text: str, vshift: int
    ) -> None:
        """
        Apply Y-axis title as an annotation to support vertical shifting.
        """
        standoff = int(config.get("yaxis_title_standoff") or 0)
        font_size = int(config.get("yaxis_title_font_size", 14))
        # Default color matches simple axis color logic or black
        font_color = config.get("axis_color", "#444444")

        # Simulate standoff with xshift
        # Clear enough space (annotations don't reserve margin automatically)
        # -40 is a heuristic for tick labels space since we are at x=0 (paper)
        xaxis_title_standoff = -(standoff + 40)
        textangle = -90

        fig.add_annotation(
            text=text,
            x=0,
            y=0.5,
            xref="paper",
            yref="paper",
            xanchor="right",
            yanchor="middle",
            textangle=textangle,
            yshift=vshift,
            xshift=xaxis_title_standoff,
            showarrow=False,
            font=dict(size=font_size, color=font_color),
        )

