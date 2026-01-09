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
        """
        # Basic Dimensions & Margins
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

        # Apply basic layout
        fig.update_layout(**layout_args)

        # Theme Backgrounds
        if config.get("plot_bgcolor"):
            fig.update_layout(plot_bgcolor=config["plot_bgcolor"])
        if config.get("paper_bgcolor"):
            fig.update_layout(paper_bgcolor=config["paper_bgcolor"])

        # Axis Settings
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

        # X-Axis Label Overrides
        # We skip this for grouped bar/stacked bar plots because they manage their own X-axis ticks (manual coordinates)
        if config.get("xaxis_labels") and self.plot_type not in [
            "grouped_stacked_bar",
            "grouped_bar",
        ]:
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
            ),
        }
        if config.get("yaxis_dtick"):
            yaxis_settings["dtick"] = config["yaxis_dtick"]

        # Axis Styling colors
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

        # Explicit Title Overrides
        if config.get("xaxis_title"):
            fig.update_xaxes(title_text=config["xaxis_title"])
        if config.get("yaxis_title"):
            fig.update_yaxes(title_text=config["yaxis_title"])

        fig.update_xaxes(**xaxis_settings)
        fig.update_yaxes(**yaxis_settings)

        # Legend
        if config.get("legend_title"):
            fig.update_layout(legend_title_text=config["legend_title"])

        fig.update_layout(
            title=dict(
                text=str(config.get("title") or "").replace("undefined", ""),
                font=dict(size=config.get("title_font_size", 18)),
            )
        )

        legend_update = {
            "orientation": config.get("legend_orientation", "v"),
            "x": config.get("legend_x", 1.02),
            "y": config.get("legend_y", 1.0),
        }

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

        # Handle Columns (Smart Wrap)
        if config.get("legend_ncols") and int(config["legend_ncols"]) > 0:
            ncols = int(config["legend_ncols"])
            legend_update["orientation"] = "h"
            legend_update["entrywidthmode"] = "fraction"
            legend_update["entrywidth"] = 1.0 / ncols
            # We might want to adjust x/y if it was default, but respecting user config is safer.
            # However, users often expect it to be centered below or above if "columns" is used?
            # For now, just controlling the wrapping width.
        else:
            # Fallback to manual entry width if no columns set
            if config.get("legend_entrywidth"):
                legend_update["entrywidth"] = int(config["legend_entrywidth"])
                legend_update["entrywidthmode"] = "pixels"

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

        # Per-Series Styling
        self._apply_series_styling(fig, config)

        # Annotations
        if config.get("shapes"):
            fig.update_layout(shapes=config["shapes"])

        return fig

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
