"""Post-render figure decorations — engine-encapsulated, scripts stay matplotlib-free.

These helpers take the **figure returned by** :meth:`ring5.Session.render` (currently a
matplotlib ``Figure`` for the matplotlib engine) and apply the small layout tweaks that
publication figures need but that aren't (yet) first-class spec features: clamping the
x-limits to the bars, tightening y-tick spacing, hiding spines, nudging a label,
value-labelling over-cap bars/dots, and the numbered-bar callout arrows.

The point of this module is **encapsulation**: a user script imports only ``ring5`` and
calls e.g. ``ring5.FigureDecorations.clamp_bar_xlim(fig)`` — it never imports matplotlib
or touches an ``Axes`` directly. All matplotlib access lives here.

Coordinates for the bar/dot helpers come from :func:`ring5.grouped_bar_coordinates`
(the engine-agnostic ``coord_map``). The matplotlib engine stores the dual (right) axis
as ``ax._ring5_twin``; helpers that need it find it themselves.
"""

from __future__ import annotations

import math
from typing import Any

Figure = Any  # a matplotlib Figure at runtime; kept loose so importing ring5 is cheap


def _primary_axes(fig: Figure) -> Any:
    """The main data Axes of a RING-5-rendered matplotlib figure."""
    return fig.axes[0]


def _twin_axes(ax: Any) -> Any:
    """The dual (right) Axes RING-5 attaches as ``ax._ring5_twin`` (or None)."""
    return getattr(ax, "_ring5_twin", None)


class FigureDecorations:
    # [impl->req~ring5.api.figure-decorations~1]
    """Stateless post-render tweaks for a RING-5 matplotlib figure.

    Every method takes the figure from ``Session.render(..., engine="matplotlib")`` and
    mutates it in place. They are deliberately small and composable.
    """

    # axes-level tweaks
    @staticmethod
    def axis_below(fig: Figure) -> None:
        """Draw grid lines behind the bars.

        Args:
            fig: Matplotlib figure returned by :meth:`ring5.Session.render`.
        """
        _primary_axes(fig).set_axisbelow(True)

    @staticmethod
    def tighten_y_ticks(fig: Figure, pad: float = 1.5, twin_pad: float | None = None) -> None:
        """Reduce the gap between y tick labels and the axis (RING-5 has no flat key).

        ``twin_pad`` (if given) does the same for the dual right axis.

        Args:
            fig: Matplotlib figure returned by :meth:`ring5.Session.render`.
            pad: Left-axis tick-label padding.
            twin_pad: Optional right-axis tick-label padding.
        """
        ax = _primary_axes(fig)
        ax.tick_params(axis="y", pad=pad)
        if twin_pad is not None:
            twin = _twin_axes(ax)
            if twin is not None:
                twin.tick_params(axis="y", pad=twin_pad)

    @staticmethod
    def set_ylabel_y(fig: Figure, y: float) -> None:
        """Move the (rotated) left y-title's vertical anchor (``label.set_y``).

        matplotlib keeps this y and recomputes x from labelpad, so the horizontal
        position is unaffected — used to un-clip a long title at the figure top.

        Args:
            fig: Matplotlib figure returned by :meth:`ring5.Session.render`.
            y: Vertical label anchor in axes coordinates.
        """
        _primary_axes(fig).yaxis.label.set_y(y)

    @staticmethod
    def set_twin_ylabel_pad(fig: Figure, pad: float) -> None:
        """Set the right-axis title padding.

        Args:
            fig: Matplotlib figure returned by :meth:`ring5.Session.render`.
            pad: Label padding in points.
        """
        twin = _twin_axes(_primary_axes(fig))
        if twin is not None:
            twin.yaxis.labelpad = pad

    @staticmethod
    def set_legends_opaque(
        fig: Figure, *, facecolor: str = "white", alpha: float = 1.0, zorder: int = 10
    ) -> None:
        """Force every legend frame opaque and on top.

        Prefer the native ``bgalpha`` legend config; use this when you also need the
        legend lifted above other artists (matplotlib legends default to ``framealpha``
        0.8 and a low z-order, so tall bars/labels can show through or over them).

        Args:
            fig: Matplotlib figure returned by :meth:`ring5.Session.render`.
            facecolor: Legend frame color.
            alpha: Legend frame opacity.
            zorder: Legend drawing order.
        """
        import matplotlib.legend as mlegend

        for leg in fig.findobj(mlegend.Legend):
            frame = leg.get_frame()
            frame.set_alpha(alpha)
            frame.set_facecolor(facecolor)
            leg.set_zorder(zorder)

    @staticmethod
    def log_xaxis(
        fig: Figure,
        *,
        ticks: list[float],
        labels: list[str] | None = None,
        xlim: tuple[float, float] | None = None,
        base: float = 2,
    ) -> None:
        """Put the primary x-axis on a log scale with fixed ticks (and optional limits).

        Order matters: the scale is set first so the explicit ``ticks`` install a fixed
        locator that survives (matplotlib's ``set_xscale`` resets locators). ``labels``
        defaults to ``str(t)`` for each tick; ``xlim`` clamps the visible range. ``base``
        only affects unlabelled minor ticks — fixed major-tick *positions* are
        base-independent on a log axis.

        Args:
            fig: Matplotlib figure returned by :meth:`ring5.Session.render`.
            ticks: Major tick positions.
            labels: Optional labels corresponding to ``ticks``.
            xlim: Optional visible x-axis range.
            base: Logarithm base.
        """
        ax = _primary_axes(fig)
        ax.set_xscale("log", base=base)
        ax.set_xticks(list(ticks))
        ax.set_xticklabels([str(t) for t in (labels if labels is not None else ticks)])
        if xlim is not None:
            ax.set_xlim(*xlim)

    @staticmethod
    def hide_spines(fig: Figure, *sides: str, include_twin: bool = True) -> None:
        """Hide named axes spines.

        Args:
            fig: Matplotlib figure returned by :meth:`ring5.Session.render`.
            *sides: Spine names such as ``"top"`` or ``"right"``.
            include_twin: Apply the same change to a secondary axis.
        """
        ax = _primary_axes(fig)
        for s in sides:
            if s in ax.spines:
                ax.spines[s].set_visible(False)
        if include_twin:
            twin = _twin_axes(ax)
            if twin is not None:
                for s in sides:
                    if s in twin.spines:
                        twin.spines[s].set_visible(False)

    @staticmethod
    def clamp_bar_xlim(fig: Figure, left: float = 0.18, right: float = 0.08) -> None:
        """Clamp the x-limits to the actual bar extents so bars fill edge-to-edge.

        matplotlib autoscales ~half a group of side padding; this removes it (with a
        small ``left``/``right`` margin in data units). The dual axis shares x, so it's
        clamped too.

        Args:
            fig: Matplotlib figure returned by :meth:`ring5.Session.render`.
            left: Margin before the first bar in data units.
            right: Margin after the last bar in data units.
        """
        import matplotlib.patches as mpatches

        ax = _primary_axes(fig)
        bars = [p for p in ax.patches if isinstance(p, mpatches.Rectangle)]
        if not bars:
            return
        lo = min(p.get_x() for p in bars)
        hi = max(p.get_x() + p.get_width() for p in bars)
        ax.set_xlim(lo - left, hi + right)
        twin = _twin_axes(ax)
        if twin is not None:
            twin.set_xlim(ax.get_xlim())

    @staticmethod
    def nudge_text(fig: Figure, text: str, dx: float, dy: float = 0.0) -> None:
        """Find a text artist by exact content and shift it by ``(dx, dy)`` (data coords).

        Used to nudge the angled ``arithmean`` tick label right of the STAMP block.

        Args:
            fig: Matplotlib figure returned by :meth:`ring5.Session.render`.
            text: Exact artist text to find.
            dx: Horizontal offset in data coordinates.
            dy: Vertical offset in data coordinates.
        """
        ax = _primary_axes(fig)
        for t in ax.texts:
            if t.get_text() == text:
                x, y = t.get_position()
                t.set_position((x + dx, y + dy))

    # value labels
    @staticmethod
    def over_cap_labels(
        fig: Figure,
        coord_map: dict[Any, float],
        totals: dict[Any, float],
        cap: float,
        *,
        fontsize: float = 6.0,
        color: str = "0.1",
        y_offset: float = 0.03,
    ) -> None:
        """Label bars whose true total exceeds the left-axis ``cap`` (clipped bars).

        ``coord_map`` maps ``(category, group) -> x`` (from
        :func:`ring5.grouped_bar_coordinates`); ``totals`` maps the same keys to the true
        (un-clipped) value. Labels sit just above the cap line (left-axis data coords).

        Args:
            fig: Matplotlib figure returned by :meth:`ring5.Session.render`.
            coord_map: Composite bar keys mapped to x positions.
            totals: Composite bar keys mapped to unclipped totals.
            cap: Visible upper limit of the left axis.
            fontsize: Label font size.
            color: Label color.
            y_offset: Vertical offset above ``cap`` in data coordinates.
        """
        ax = _primary_axes(fig)
        for key, tot in totals.items():
            if tot > cap + 1e-6:
                x = coord_map.get(key)
                if x is not None:
                    ax.annotate(
                        f"{tot:.1f}",
                        (x, cap + y_offset),
                        ha="center",
                        va="bottom",
                        fontsize=fontsize,
                        color=color,
                        clip_on=False,
                        zorder=8,
                        annotation_clip=False,
                    )

    @staticmethod
    def staggered_over_cap_labels(
        fig: Figure,
        coord_map: dict[Any, float],
        values: dict[Any, float],
        cap: float,
        *,
        lbl_dx: float = 1.8,
        y0: float = 1.05,
        dy: float = 0.05,
        fontsize: float = 4.5,
        color: str = "#7a5c00",
    ) -> None:
        """Label dual-axis (dot) values that exceed the right-axis cap, staggered.

        For a second-axis series clipped at the top: each over-cap value is written above
        the plot at the dot's x (axes-fraction y via the x-axis transform). A greedy pass
        bumps labels that are within ``lbl_dx`` (data units) of an already-placed one at
        the same level up to the next level (``y0 + level*dy``) — different heights, no
        overlap.

        Args:
            fig: Matplotlib figure returned by :meth:`ring5.Session.render`.
            coord_map: Composite point keys mapped to x positions.
            values: Composite point keys mapped to unclipped values.
            cap: Visible upper limit of the right axis.
            lbl_dx: Minimum horizontal distance between labels at one level.
            y0: First label level in axes coordinates.
            dy: Vertical spacing between label levels.
            fontsize: Label font size.
            color: Label color.
        """
        ax = _primary_axes(fig)
        over = sorted(
            (coord_map[k], v)
            for k, v in values.items()
            if k in coord_map and not math.isnan(v) and v > cap + 1e-9
        )
        xtrans = ax.get_xaxis_transform()  # x in data coords, y in axes fraction
        placed: list[tuple[float, int]] = []
        for x, v in over:
            level = 0
            while any(lvl == level and abs(x - px) < lbl_dx for px, lvl in placed):
                level += 1
            placed.append((x, level))
            ax.annotate(
                f"{v:.1f}",
                xy=(x, y0 + level * dy),
                xycoords=xtrans,
                ha="center",
                va="bottom",
                fontsize=fontsize,
                color=color,
                clip_on=False,
                annotation_clip=False,
                zorder=8,
            )

    @staticmethod
    def numbered_bar_arrows(
        fig: Figure,
        coord_map: dict[Any, float],
        first_category: str,
        groups: list[str],
        totals: dict[Any, float],
        cap: float,
        *,
        gap: float = 0.17,
        arrow_dy: float = 0.01,
        label: str = "legend\n no.",
        label_dx: float = 0.0,
        label_dy: float = 0.15,
    ) -> None:
        """Draw ``1/2/3/4`` callout arrows over the first category's sub-bars.

        Makes explicit that the numbered-legend order is the sub-bar order within every
        group. ``totals`` gives each bar's height (clamped to ``cap``); ``label`` is the
        small caption placed at ``(center+label_dx, ytxt+label_dy)``. ``gap`` sets the
        arrow-tail height above the tallest bar; ``arrow_dy`` nudges each arrow head.

        Args:
            fig: Matplotlib figure returned by :meth:`ring5.Session.render`.
            coord_map: Composite bar keys mapped to x positions.
            first_category: Category whose bars receive callouts.
            groups: Groups in numbered-legend order.
            totals: Composite bar keys mapped to bar heights.
            cap: Visible upper limit of the left axis.
            gap: Vertical gap above the tallest bar.
            arrow_dy: Vertical offset applied between arrow heads.
            label: Caption placed above the callouts.
            label_dx: Horizontal caption offset.
            label_dy: Vertical caption offset.
        """
        ax = _primary_axes(fig)
        if not groups:
            return
        tops = [min(totals.get((first_category, g), 0.0), cap) for g in groups]
        ytxt = max(tops) + gap
        placed_x: list[float] = []
        for j, top in enumerate(tops):
            x = coord_map.get((first_category, groups[j]))
            if x is None:
                continue
            placed_x.append(x)
            ax.annotate(
                str(j + 1),
                xy=(x, top + arrow_dy),
                xytext=(x, ytxt),
                ha="center",
                va="bottom",
                fontsize=7.5,
                fontweight="bold",
                color="0.1",
                arrowprops=dict(arrowstyle="->", lw=0.7, color="0.3", shrinkA=2, shrinkB=1),
                clip_on=False,
                zorder=9,
                annotation_clip=False,
            )
        if not placed_x:
            return
        # Center the caption over the bars actually drawn (avoids a hard KeyError if the
        # first/last group key is missing from coord_map).
        xc = (placed_x[0] + placed_x[-1]) / 2
        ax.annotate(
            label,
            xy=(0, 0),
            xytext=(xc + label_dx, ytxt + label_dy),
            ha="center",
            va="bottom",
            fontsize=7.0,
            fontweight="semibold",
            color="0.2",
            clip_on=False,
            annotation_clip=False,
        )
