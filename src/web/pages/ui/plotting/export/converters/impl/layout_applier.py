"""
Layout applier for applying extracted layout to Matplotlib axes.

Implements the application side of layout preservation, breaking down the
monolithic apply_to_matplotlib() into focused, testable methods.
"""

import re
from typing import Any, Dict, Literal, Optional, cast

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.transforms import ScaledTranslation, blended_transform_factory

from src.web.pages.ui.plotting.export.presets.preset_schema import LaTeXPreset

from .layout_config import FontStyleConfig, LegendSpacingConfig, PositioningConfig, SeparatorConfig


class LayoutApplier:
    """
    Applies extracted layout properties to Matplotlib axes.

    Breaks down layout application into focused methods for better maintainability
    and testability. Each method handles a specific category of layout properties.
    """

    def __init__(self, preset: Optional[LaTeXPreset] = None):
        """
        Initialize layout applier with preset configuration.

        Args:
            preset: LaTeX preset dictionary with formatting parameters
        """
        self.font_config = self._build_font_config(preset)
        self.pos_config = self._build_positioning_config(preset)
        self.sep_config = self._build_separator_config(preset)
        self.legend_spacing = self._build_legend_spacing_config(preset)

    def _build_font_config(self, preset: Optional[LaTeXPreset]) -> FontStyleConfig:
        """
        Build font configuration from preset.

        Args:
            preset: LaTeX preset dictionary

        Returns:
            FontStyleConfig with font sizes and bold flags
        """
        if not preset:
            return FontStyleConfig()

        return FontStyleConfig(
            font_size_title=preset.get("font_size_title", 10),
            font_size_xlabel=preset.get("font_size_xlabel", 9),
            font_size_ylabel=preset.get("font_size_ylabel", 9),
            font_size_ticks=preset.get("font_size_ticks", 7),
            font_size_yticks=preset.get("font_size_yticks", preset.get("font_size_ticks", 7)),
            font_size_annotations=preset.get("font_size_annotations", 6),
            font_size_legend=preset.get("font_size_legend", 8),
            bold_title=preset.get("bold_title", False),
            bold_xlabel=preset.get("bold_xlabel", False),
            bold_ylabel=preset.get("bold_ylabel", False),
            bold_ticks=preset.get("bold_ticks", False),
            bold_annotations=preset.get("bold_annotations", True),
            bold_group_labels=preset.get("bold_group_labels", True),
            bold_legend=preset.get("bold_legend", False),
        )

    def _build_positioning_config(self, preset: Optional[LaTeXPreset]) -> PositioningConfig:
        """
        Build positioning configuration from preset.

        Args:
            preset: LaTeX preset dictionary

        Returns:
            PositioningConfig with padding and positioning parameters
        """
        if not preset:
            return PositioningConfig()

        # Get xtick_ha with type narrowing
        xtick_ha_value = preset.get("xtick_ha", "right")
        if xtick_ha_value not in ("left", "center", "right"):
            xtick_ha_value = "right"

        return PositioningConfig(
            ylabel_pad=preset.get("ylabel_pad", 10.0),
            ylabel_y_position=preset.get("ylabel_y_position", 0.5),
            xtick_pad=preset.get("xtick_pad", 5.0),
            ytick_pad=preset.get("ytick_pad", 5.0),
            xtick_rotation=preset.get("xtick_rotation", 45.0),
            xtick_ha=cast(Literal["left", "center", "right"], xtick_ha_value),
            xtick_offset=preset.get("xtick_offset", 0.0),
            xaxis_margin=preset.get("xaxis_margin", 0.02),
            group_label_offset=preset.get("group_label_offset", -0.12),
            group_label_alternate=preset.get("group_label_alternate", True),
            group_label_alt_spacing=preset.get("group_label_alt_spacing", 0.05),
            legend_x=preset.get("legend_x", -1.0),
            legend_y=preset.get("legend_y", -1.0),
        )

    def _build_separator_config(self, preset: Optional[LaTeXPreset]) -> SeparatorConfig:
        """
        Build separator configuration from preset.

        Args:
            preset: LaTeX preset dictionary

        Returns:
            SeparatorConfig with separator line parameters
        """
        if not preset:
            return SeparatorConfig()

        # Get style with type narrowing
        style_value = preset.get("group_separator_style", "dashed")
        if style_value not in ("solid", "dashed", "dotted", "dashdot"):
            style_value = "dashed"

        return SeparatorConfig(
            enabled=preset.get("group_separator", False),
            style=cast(Literal["solid", "dashed", "dotted", "dashdot"], style_value),
            color=preset.get("group_separator_color", "#808080"),
        )

    def _build_legend_spacing_config(self, preset: Optional[LaTeXPreset]) -> LegendSpacingConfig:
        """
        Build legend spacing configuration from preset.

        These values are used by _render_boxed_annotation() to ensure the
        numbered-legend box uses the same spacing as the main legend.

        Args:
            preset: LaTeX preset dictionary

        Returns:
            LegendSpacingConfig with spacing parameters
        """
        if not preset:
            return LegendSpacingConfig()

        return LegendSpacingConfig(
            columnspacing=preset.get("legend_columnspacing", 0.5),
            handletextpad=preset.get("legend_handletextpad", 0.3),
            labelspacing=preset.get("legend_labelspacing", 0.2),
            handlelength=preset.get("legend_handlelength", 1.0),
            handleheight=preset.get("legend_handleheight", 0.7),
            borderpad=preset.get("legend_borderpad", 0.2),
            borderaxespad=preset.get("legend_borderaxespad", 0.5),
        )

    def apply_to_matplotlib(self, ax: Axes, layout: Dict[str, Any]) -> None:
        """
        Apply extracted layout to Matplotlib axes.

        Main orchestrator that delegates to specialized application methods.

        Args:
            ax: Matplotlib axes to modify
            layout: Layout dictionary from extract_layout()
        """
        self._apply_axis_ranges(ax, layout)
        self._apply_axis_labels(ax, layout)
        self._apply_title(ax, layout)
        self._apply_axis_scales_and_grids(ax, layout)
        self._apply_ticks(ax, layout)
        self._apply_legend(ax, layout)
        self._apply_annotations(ax, layout)

    def _apply_axis_ranges(self, ax: Axes, layout: Dict[str, Any]) -> None:
        """
        Apply X/Y axis ranges with configurable margins.

        Args:
            ax: Matplotlib axes
            layout: Layout dictionary
        """
        if "x_range" in layout:
            x_min, x_max = layout["x_range"]
            x_span = x_max - x_min
            # Apply margin to compress whitespace
            margin = self.pos_config.xaxis_margin
            ax.set_xlim(x_min - x_span * margin, x_max + x_span * margin)
        else:
            # If no explicit range, tighten the margins
            ax.margins(x=self.pos_config.xaxis_margin)

        if "y_range" in layout:
            ax.set_ylim(layout["y_range"])

    def _apply_axis_labels(self, ax: Axes, layout: Dict[str, Any]) -> None:
        """
        Apply X/Y axis labels with font styling and positioning.

        Args:
            ax: Matplotlib axes
            layout: Layout dictionary
        """
        if "x_label" in layout and layout["x_label"]:
            ax.set_xlabel(
                self._escape_latex(layout["x_label"]),
                fontsize=self.font_config.font_size_xlabel,
                fontweight="bold" if self.font_config.bold_xlabel else "normal",
            )

        if "y_label" in layout and layout["y_label"]:
            y_label = self._escape_latex(layout["y_label"])
            ax.set_ylabel(
                y_label,
                fontsize=self.font_config.font_size_ylabel,
                fontweight="bold" if self.font_config.bold_ylabel else "normal",
                rotation=90,
                labelpad=self.pos_config.ylabel_pad,
                y=self.pos_config.ylabel_y_position,
            )

    def _apply_title(self, ax: Axes, layout: Dict[str, Any]) -> None:
        """
        Apply figure title with font styling.

        Args:
            ax: Matplotlib axes
            layout: Layout dictionary
        """
        if "title" in layout and layout["title"]:
            ax.set_title(
                self._escape_latex(layout["title"]),
                fontsize=self.font_config.font_size_title,
                fontweight="bold" if self.font_config.bold_title else "normal",
            )

    def _apply_axis_scales_and_grids(self, ax: Axes, layout: Dict[str, Any]) -> None:
        """
        Apply axis scales (log/linear) and grid visibility.

        Args:
            ax: Matplotlib axes
            layout: Layout dictionary
        """
        # Apply axis scales
        if "x_type" in layout and layout["x_type"] == "log":
            ax.set_xscale("log")
        if "y_type" in layout and layout["y_type"] == "log":
            ax.set_yscale("log")

        # Apply grid settings
        if "x_grid" in layout:
            ax.xaxis.grid(layout["x_grid"])
        if "y_grid" in layout:
            ax.yaxis.grid(layout["y_grid"])

    def _apply_ticks(self, ax: Axes, layout: Dict[str, Any]) -> None:
        """
        Apply tick positions, labels, and styling.

        Handles custom tick values/labels, rotation, alignment, offset,
        and font styling.

        Args:
            ax: Matplotlib axes
            layout: Layout dictionary
        """
        # Apply tick padding and Y-tick label size
        ax.tick_params(axis="x", pad=self.pos_config.xtick_pad)
        ax.tick_params(
            axis="y",
            pad=self.pos_config.ytick_pad,
            labelsize=self.font_config.font_size_yticks,
        )

        # When X-tick labels are explicitly hidden (e.g. numbered X-axis mode),
        # remove tick labels and tick marks entirely.
        if layout.get("x_showticklabels") is False:
            ax.set_xticklabels([])
            ax.tick_params(axis="x", length=0)
            return

        # Apply custom X tick positions and labels
        if "x_tickvals" in layout and "x_ticktext" in layout:
            ax.set_xticks(layout["x_tickvals"])
            escaped_labels = [self._escape_latex(str(label)) for label in layout["x_ticktext"]]
            ax.set_xticklabels(
                escaped_labels,
                rotation=self.pos_config.xtick_rotation,
                ha=self.pos_config.xtick_ha,
                fontsize=self.font_config.font_size_ticks,
                fontweight="bold" if self.font_config.bold_ticks else "normal",
            )

            # Apply horizontal offset if specified
            if self.pos_config.xtick_offset != 0.0:
                dx = self.pos_config.xtick_offset / 72.0  # Points to inches
                offset_transform = ScaledTranslation(dx, 0, ax.figure.dpi_scale_trans)
                for label in ax.get_xticklabels():
                    label.set_transform(label.get_transform() + offset_transform)

        # Apply custom Y tick positions and labels
        if "y_tickvals" in layout and "y_ticktext" in layout:
            ax.set_yticks(layout["y_tickvals"])
            escaped_labels = [self._escape_latex(str(label)) for label in layout["y_ticktext"]]
            ax.set_yticklabels(
                escaped_labels,
                fontsize=self.font_config.font_size_yticks,
                fontweight="bold" if self.font_config.bold_ticks else "normal",
            )

    def _apply_legend(self, ax: Axes, layout: Dict[str, Any]) -> None:
        """
        Apply legend positioning.

        Args:
            ax: Matplotlib axes
            layout: Layout dictionary
        """
        if "legend" in layout:
            legend_config = layout["legend"]
            if "x" in legend_config and "y" in legend_config:
                # Only create legend if there are labeled artists
                handles, labels = ax.get_legend_handles_labels()
                if handles:
                    ax.legend(
                        bbox_to_anchor=(legend_config["x"], legend_config["y"]),
                        loc="upper left",
                    )

    def _apply_annotations(self, ax: Axes, layout: Dict[str, Any]) -> None:
        """
        Apply all annotations with proper coordinate transformations.

        Handles bar value annotations, grouping labels, boxed legend-style
        annotations, and general annotations.
        Applies group separators if enabled.

        Args:
            ax: Matplotlib axes
            layout: Layout dictionary
        """
        if "annotations" not in layout:
            return

        grouping_label_index = 0

        for ann in layout["annotations"]:
            # Clean and escape text
            text = self._clean_html_tags(ann["text"])
            text = self._escape_latex(text)

            # Detect boxed annotations (legend-style, e.g., numbered x-axis legend)
            is_boxed = ann.get("borderwidth", 0) > 0

            if is_boxed:
                self._render_boxed_annotation(ax, ann, text)
                continue

            # Determine annotation type and font properties
            xref = ann.get("xref", "x")
            yref = ann.get("yref", "y")
            is_bar_total = yref != "paper" and xref != "paper"
            # Grouping labels use data-x (xref="x") + paper-y below axis.
            # Annotations with xref="paper" (e.g., numbered legends) are
            # general annotations and must keep their own position.
            is_grouping_label = yref == "paper" and xref != "paper" and ann["y"] < 0

            font_props = self._determine_annotation_font(is_bar_total, is_grouping_label)

            # Apply color if present
            if "font" in ann and "color" in ann["font"]:
                font_props["color"] = ann["font"]["color"]

            # Calculate position
            y_pos, grouping_label_index = self._calculate_annotation_position(
                ann, is_grouping_label, grouping_label_index
            )

            # Determine coordinate system
            xycoords = self._determine_xycoords(xref, yref)

            # Build annotation kwargs
            ann_kwargs = self._build_matplotlib_annotation(ann, text, y_pos, xycoords, font_props)

            ax.annotate(text, **ann_kwargs)

        # Draw group separators if enabled
        if self.sep_config.enabled:
            self._draw_group_separators(ax, layout)

    def _render_boxed_annotation(
        self,
        ax: Axes,
        ann: Dict[str, Any],
        text: str,
    ) -> None:
        """
        Render a boxed (legend-style) annotation with border and background.

        Uses the same font settings as the main legend from the preset to
        ensure visual consistency across the exported figure.

        When LaTeX text rendering is active (``text.usetex=True``), wraps each
        line in ``\\texttt{...}`` with spaces replaced by ``\\phantom{0}`` so
        that column alignment is preserved.  Without LaTeX the standard
        monospace ``FontProperties`` handles alignment.

        Args:
            ax: Matplotlib axes
            ann: Annotation dictionary with border/box properties
            text: Cleaned and LaTeX-escaped text content
        """
        from matplotlib.font_manager import FontProperties

        # Use legend font settings from preset for consistency
        fontsize: int = self.font_config.font_size_legend
        weight: str = "bold" if self.font_config.bold_legend else "normal"

        # Use monospace font for boxed annotations so column entries align
        font_props = FontProperties(
            family="monospace",
            size=fontsize,
            weight=weight,
        )

        # When LaTeX is rendering text, FontProperties(family="monospace") is
        # ignored because LaTeX handles all typesetting.  Wrap each line in
        # \texttt{} and replace spaces with ~ (non-breaking) so that LaTeX
        # preserves column alignment produced by ljust() padding.
        usetex: bool = plt.rcParams.get("text.usetex", False)
        if usetex:
            # Add one space on each side of every line as horizontal padding.
            # _wrap_texttt converts these to \phantom{0}, which LatexManager
            # measures — expanding the bbox by one character width per side.
            # Without this, the text fills the content area edge-to-edge and
            # any font-metric discrepancy between the measurement subprocess
            # and the host document can cause the text to overflow the box.
            padded_lines = [f" {ln} " for ln in text.split("\n")]
            text = "\n".join(padded_lines)
            text = self._wrap_texttt(text, bold=(weight == "bold"))

        # Determine coordinate system and alignment
        xref = ann.get("xref", "paper")
        yref = ann.get("yref", "paper")
        xycoords = self._determine_xycoords(xref, yref)

        # Anchors
        xanchor = ann.get("xanchor", "left")
        yanchor = ann.get("yanchor", "middle")
        ha = {"left": "left", "right": "right"}.get(xanchor, "center")
        va_map = {"top": "top", "bottom": "bottom", "middle": "center"}
        va = va_map.get(yanchor, "center")

        # Build bbox matching the standard legend style.
        # Use the preset borderpad for the box padding, converting points → inches.
        box_pad: float = self.legend_spacing.borderpad
        bbox_props = dict(
            boxstyle=f"round,pad={box_pad:.3f}",
            facecolor=ann.get("bgcolor", "white"),
            edgecolor=ann.get("bordercolor", "black"),
            linewidth=ann.get("borderwidth", 1),
            alpha=1.0,
        )

        # Legend spacing from preset (reuse same values as the main legend).
        # labelspacing controls vertical distance between entries, converted
        # to matplotlib linespacing (proportion of font size).
        linespacing: float = 1.0 + self.legend_spacing.labelspacing * 2.0

        ann_kwargs: Dict[str, Any] = {
            "xy": (ann["x"], ann["y"]),
            "xycoords": xycoords,
            "ha": ha,
            "va": va,
            "fontproperties": font_props,
            "bbox": bbox_props,
            "linespacing": linespacing,
            "zorder": 6,  # Above main legend (zorder=5)
        }

        ax.annotate(text, **ann_kwargs)

    @staticmethod
    def _wrap_texttt(text: str, bold: bool = False) -> str:
        """Wrap each line in LaTeX ``\\texttt{}`` for monospace rendering.

        When ``text.usetex`` is ``True``, matplotlib delegates all text
        rendering to LaTeX which ignores ``FontProperties(family="monospace")``.
        This helper wraps every line in ``\\texttt{…}`` and replaces spaces
        with ``\\phantom{0}`` so that the column alignment produced by
        ``ljust()`` padding is preserved in the final PDF/PGF output.

        **Why ``\\phantom{0}`` instead of ``~``?**
        TeX collapses consecutive ``~`` (non-breaking spaces) into a single
        interword space, destroying the padding that ``ljust()`` inserted.
        ``\\phantom{0}`` creates an *invisible box* with exactly one character
        width that is never collapsed, guaranteeing perfect column alignment.

        Args:
            text: Multi-line text (lines separated by ``\\n``).
            bold: If ``True``, additionally wrap content in ``\\textbf{}``.

        Returns:
            Text with each line wrapped in LaTeX monospace commands.
        """
        lines = text.split("\n")
        wrapped: list[str] = []
        for line in lines:
            # Replace spaces with \phantom{0} (invisible character-width box)
            # so LaTeX preserves the exact character-based padding.
            # Unlike ~, \phantom{0} is never collapsed when consecutive.
            mono = line.replace(" ", r"\phantom{0}")
            if bold:
                mono = rf"\texttt{{\textbf{{{mono}}}}}"
            else:
                mono = rf"\texttt{{{mono}}}"
            wrapped.append(mono)
        return "\n".join(wrapped)

    def _clean_html_tags(self, text: str) -> str:
        """
        Remove HTML tags from annotation text.

        Converts HTML entities and tags to plain text equivalents:
        - ``<b>``/``<i>`` tags are unwrapped
        - ``<br>`` becomes newline
        - ``&nbsp;`` becomes regular space

        Args:
            text: Text potentially containing HTML tags

        Returns:
            Text with HTML tags removed
        """
        text = re.sub(r"<b>(.*?)</b>", r"\1", text)
        text = re.sub(r"<i>(.*?)</i>", r"\1", text)
        text = re.sub(r"<br\s*/?>", "\n", text)
        text = text.replace("&nbsp;", " ")
        return text

    def _determine_annotation_font(
        self, is_bar_total: bool, is_grouping_label: bool
    ) -> Dict[str, Any]:
        """
        Determine font properties based on annotation type.

        Args:
            is_bar_total: Whether annotation is a bar value
            is_grouping_label: Whether annotation is a grouping label

        Returns:
            Dictionary with fontsize and weight
        """
        if is_bar_total:
            return {
                "fontsize": self.font_config.font_size_annotations,
                "weight": "bold" if self.font_config.bold_annotations else "normal",
            }
        elif is_grouping_label:
            return {
                "fontsize": self.font_config.font_size_xlabel,
                "weight": "bold" if self.font_config.bold_group_labels else "normal",
            }
        else:
            return {
                "fontsize": self.font_config.font_size_annotations,
                "weight": "bold" if self.font_config.bold_annotations else "normal",
            }

    def _calculate_annotation_position(
        self,
        ann: Dict[str, Any],
        is_grouping_label: bool,
        grouping_label_index: int,
    ) -> tuple[float, int]:
        """
        Calculate annotation Y position with alternation for grouping labels.

        Args:
            ann: Annotation dictionary
            is_grouping_label: Whether annotation is a grouping label
            grouping_label_index: Current grouping label index

        Returns:
            Tuple of (y_position, updated_index)
        """
        y_pos = ann["y"]

        if is_grouping_label:
            y_pos = self.pos_config.group_label_offset
            if self.pos_config.group_label_alternate:
                if grouping_label_index % 2 == 1:
                    y_pos = (
                        self.pos_config.group_label_offset - self.pos_config.group_label_alt_spacing
                    )
                grouping_label_index += 1

        return y_pos, grouping_label_index

    def _determine_xycoords(self, xref: str, yref: str) -> str | tuple[str, str]:
        """
        Map Plotly coordinate references to Matplotlib xycoords.

        Args:
            xref: Plotly x coordinate reference
            yref: Plotly y coordinate reference

        Returns:
            Matplotlib xycoords specification
        """
        if xref == "paper" and yref == "paper":
            return "axes fraction"
        elif xref == "paper":
            return ("axes fraction", "data")
        elif yref == "paper":
            return ("data", "axes fraction")
        else:
            return "data"

    def _build_matplotlib_annotation(
        self,
        ann: Dict[str, Any],
        text: str,
        y_pos: float,
        xycoords: str | tuple[str, str],
        font_props: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build matplotlib annotation kwargs dictionary.

        Args:
            ann: Annotation dictionary
            text: Escaped annotation text
            y_pos: Calculated Y position
            xycoords: Coordinate system specification
            font_props: Font properties dictionary

        Returns:
            Complete annotation kwargs
        """
        # Determine vertical alignment
        yanchor = ann.get("yanchor", "auto")
        yref = ann.get("yref", "y")
        if yanchor == "top":
            va = "top"
        elif yanchor == "bottom":
            va = "bottom"
        elif yanchor == "middle":
            va = "center"
        else:
            # Auto: if y < 0 (below axis), use top; else bottom
            if yref == "paper" and ann["y"] < 0:
                va = "top"
            else:
                va = "bottom"

        # Determine horizontal alignment
        xanchor = ann.get("xanchor", "center")
        if xanchor == "left":
            ha = "left"
        elif xanchor == "right":
            ha = "right"
        else:
            ha = "center"

        ann_kwargs: Dict[str, Any] = {
            "xy": (ann["x"], y_pos),
            "xycoords": xycoords,
            "ha": ha,
            "va": va,
        }

        # Add rotation if present
        if "textangle" in ann:
            ann_kwargs["rotation"] = -ann["textangle"]

        # Add font properties
        ann_kwargs.update(font_props)

        return ann_kwargs

    def _draw_group_separators(self, ax: Axes, layout: Dict[str, Any]) -> None:
        """
        Draw vertical separator lines between groups.

        Args:
            ax: Matplotlib axes
            layout: Layout dictionary
        """
        # Collect grouping label x positions
        grouping_positions = []
        for ann in layout["annotations"]:
            xref = ann.get("xref", "x")
            yref = ann.get("yref", "y")
            if yref == "paper" and ann["y"] < 0 and xref == "x":
                grouping_positions.append(ann["x"])

        # Draw separator before last group if we have 2+ groups
        if len(grouping_positions) >= 2:
            grouping_positions.sort()
            last_pos = grouping_positions[-1]
            second_last_pos = grouping_positions[-2]
            separator_x = (second_last_pos + last_pos) / 2

            # Map line style
            linestyle_map = {
                "dashed": "--",
                "dotted": ":",
                "solid": "-",
                "dashdot": "-.",
            }
            ls = linestyle_map.get(self.sep_config.style, "--")

            # Draw vertical line
            trans = blended_transform_factory(ax.transData, ax.transAxes)
            ax.plot(
                [separator_x, separator_x],
                [0, 1],
                transform=trans,
                linestyle=ls,
                color=self.sep_config.color,
                linewidth=0.8,
                alpha=0.6,
                clip_on=False,
            )

    @staticmethod
    def _escape_latex(text: str) -> str:
        """
        Escape special LaTeX characters in text.

        Args:
            text: Text to escape

        Returns:
            Text with LaTeX special characters escaped
        """
        # Step 1: Escape backslashes using a placeholder
        text = text.replace("\\", "<<<BACKSLASH>>>")

        # Step 2: Escape curly braces
        text = text.replace("{", r"\{")
        text = text.replace("}", r"\}")

        # Step 3: Replace backslash placeholder
        text = text.replace("<<<BACKSLASH>>>", r"\textbackslash{}")

        # Step 4: Escape remaining characters
        replacements = {
            "_": r"\_",
            "%": r"\%",
            "&": r"\&",
            "$": r"\$",
            "#": r"\#",
            "~": r"\textasciitilde{}",
            "^": r"\^{}",
        }
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        return text
