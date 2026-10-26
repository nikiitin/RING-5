"""Owned heatmap colorbar outputs and allocation-safe native reprojection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast

import matplotlib as mpl
from matplotlib.collections import QuadMesh
from matplotlib.ticker import FormatStrFormatter, MaxNLocator

if TYPE_CHECKING:
    from matplotlib.typing import RcKeyType
    from matplotlib.colorbar import Colorbar

from src.core.models.visualization.figure_config import FigureConfig
from src.web.rendering._render_result import (
    MatplotlibFigureResult,
    MatplotlibRenderResult,
    MatplotlibTraceBinding,
    _ColorbarAllocation,
    _ColorbarOutput,
)


class _ColorbarBacklink(Protocol):
    """Mappable fields created and consumed by the current native Colorbar owner."""

    colorbar: Colorbar | None
    colorbar_cid: int


@dataclass(frozen=True, eq=False)
class _Request:
    source: MatplotlibTraceBinding
    mappable: QuadMesh
    panels: tuple[MatplotlibRenderResult, ...]
    spec: FigureConfig

    @property
    def orientation(self) -> str:
        return self.spec.legends[0].orientation if self.spec.legends else "vertical"

    @property
    def visible(self) -> bool:
        return self.spec.legends[0].visible if self.spec.legends else True


@dataclass(frozen=True)
class ColorbarPlan:
    """One preflighted native operation, spanning teardown and post-style projection."""

    rendered: MatplotlibFigureResult
    requests: tuple[_Request, ...]
    retire: tuple[_ColorbarOutput, ...]


def _requests(
    rendered: MatplotlibFigureResult, specs: tuple[FigureConfig, ...]
) -> tuple[_Request, ...]:
    if len(specs) != len(rendered.panels):
        raise ValueError("Colorbar projection requires every actual panel specification.")
    groups: list[tuple[tuple[MatplotlibRenderResult, ...], FigureConfig]] = []
    facets = len(rendered.panels) > 1 and all(
        panel.title_source is not None for panel in rendered.panels
    )
    if facets:
        spec = specs[0]
        shared = spec.legends[0].colorbar.shared if spec.legends else True
        if type(shared) is not bool:
            raise ValueError("Colorbar shared must be a boolean.")
        groups = (
            [(rendered.panels, spec)] if shared else [((panel,), spec) for panel in rendered.panels]
        )
    else:
        groups = [((panel,), spec) for panel, spec in zip(rendered.panels, specs, strict=True)]
    requests = []
    for panels, spec in groups:
        if spec.legends and (
            spec.legends[0].orientation not in ("horizontal", "vertical")
            or type(spec.legends[0].visible) is not bool
        ):
            raise ValueError("Colorbar orientation/visibility must use the current typed values.")
        candidates = [
            (panel, panel.heatmap_image) for panel in panels if panel.heatmap_image is not None
        ]
        if not candidates:
            continue
        panel, image = candidates[-1]
        source = next(
            binding
            for binding in panel.bindings
            if binding.family == "heatmap" and any(image is item for item in binding.owned_data)
        )
        if any(
            participant.primary_axes.figure is not panels[0].primary_axes.figure
            for participant in panels
        ):
            raise ValueError("A shared colorbar requires one explicit native layout parent.")
        requests.append(_Request(source, image, panels, spec))
    return tuple(requests)


def _matches(output: _ColorbarOutput, request: _Request) -> bool:
    return (
        output.source is request.source
        and output.colorbar.orientation == request.orientation
        and len(output.panels) == len(request.panels)
        and all(left is right for left, right in zip(output.panels, request.panels, strict=True))
    )


def prepare_colorbars(
    rendered: MatplotlibFigureResult,
    specs: tuple[FigureConfig, ...],
    *,
    layout_change: bool = False,
) -> ColorbarPlan:
    """Validate the complete output generation before any native style mutation.

    Structural replacement requires the original callback and allocation still owned.
    Unchanged topology permits foreign outputs while reusing only our actual colorbars.
    """
    rendered.validate()
    requests = _requests(rendered, specs)
    retire = tuple(
        output
        for output in rendered.native_outputs.colorbars
        if layout_change or not any(_matches(output, request) for request in requests)
    )
    for output in retire:
        # Colorbar creates these attributes on the actual supplied mappable;
        # its supported remove() operation consumes the same native fields.
        image = cast(_ColorbarBacklink, output.colorbar.mappable)
        if (
            image.colorbar is not output.colorbar
            or image.colorbar_cid != output.callback_id
            or output.colorbar.ax.get_subplotspec() is not output.parent
            or rendered.figure.get_layout_engine() is not output.layout_engine
        ):
            raise ValueError(
                "Colorbar allocation ownership changed; supply a fresh explicit generation."
            )
        for allocation in output.allocation:
            axes = allocation.axes
            automatic = output.layout_engine is not None and allocation.allocated_parent is not None
            if (
                axes.get_subplotspec() is not allocation.allocated_parent
                or axes.get_anchor() != allocation.allocated_anchor
                or (
                    not automatic
                    and axes.get_position(original=True).bounds != allocation.allocated_box.bounds
                )
            ):
                raise ValueError(
                    "Colorbar allocation layout changed; supply a fresh explicit generation."
                )
    return ColorbarPlan(rendered, requests, retire)


def retire_colorbars(plan: ColorbarPlan) -> None:
    """Release only preflighted outputs and their exact native allocation effects."""
    for output in plan.retire:
        # The plan checked current backlink/CID ownership before this native remove.
        gridspec_restored = output.colorbar.ax.get_subplotspec() is not None
        output.colorbar.remove()
        for allocation in output.allocation:
            axes = allocation.axes
            if allocation.parent is not None and axes.get_subplotspec() is not allocation.parent:
                axes.set_subplotspec(allocation.parent)
            automatic = output.layout_engine is not None and allocation.parent is not None
            if not automatic and not gridspec_restored:
                axes.set_position(allocation.original_box)
            axes.set_anchor(allocation.anchor)
        plan.rendered.native_outputs.colorbars = tuple(
            item for item in plan.rendered.native_outputs.colorbars if item is not output
        )


def _create(plan: ColorbarPlan, request: _Request) -> _ColorbarOutput:
    axes = tuple(
        axis
        for panel in request.panels
        for axis in (panel.primary_axes, panel.secondary_axes)
        if axis is not None
    )
    before = [
        (axis, axis.get_subplotspec(), axis.get_position(original=True).frozen(), axis.get_anchor())
        for axis in axes
    ]
    image = request.mappable
    parent = request.panels[0].primary_axes.figure
    primary_axes = [panel.primary_axes for panel in request.panels]
    options: dict[str, Any] = {"orientation": request.orientation}
    if len(primary_axes) > 1:
        options.update(ax=primary_axes, shrink=0.8)
    else:
        options["ax"] = primary_axes[0]
    font_rc: dict[RcKeyType, Any] = (
        {"font.family": request.spec.font_family} if request.spec.font_family else {}
    )
    with mpl.rc_context(font_rc):
        native = parent.colorbar(image, **options)
    allocation = tuple(
        _ColorbarAllocation(
            axis,
            subplot,
            box,
            anchor,
            axis.get_subplotspec(),
            axis.get_position(original=True).frozen(),
            axis.get_anchor(),
        )
        for axis, subplot, box, anchor in before
    )
    return _ColorbarOutput(
        native,
        request.source,
        request.panels,
        cast(_ColorbarBacklink, image).colorbar_cid,
        allocation,
        plan.rendered.figure.get_layout_engine(),
        native.ax.get_subplotspec(),
        native.ax.get_position(original=True).frozen(),
        native.ax.get_in_layout(),
    )


def _style(output: _ColorbarOutput, request: _Request) -> None:
    native, spec = output.colorbar, request.spec
    primary = spec.legends[0] if spec.legends else None
    cfg = primary.colorbar if primary is not None else None
    horizontal = native.orientation == "horizontal"
    native.ax.set_visible(request.visible)
    kwargs: dict[str, Any] = {}
    if primary is not None:
        if primary.title_font_size > 0:
            kwargs["fontsize"] = primary.title_font_size
        if primary.title_font_color:
            kwargs["color"] = primary.title_font_color
    native.ax.set_title(primary.title if primary is not None else "", **kwargs)
    native.locator = MaxNLocator(nbins=cfg.nticks if cfg is not None else 5)
    native.formatter = FormatStrFormatter(f"%.{cfg.tick_decimals if cfg is not None else 2}f")
    native.update_ticks()
    if horizontal:
        native.ax.xaxis.tick_bottom()
        native.ax.xaxis.set_label_position("bottom")
    elif cfg is not None and cfg.tick_side == "left":
        native.ax.yaxis.tick_left()
        native.ax.yaxis.set_label_position("left")
    else:
        native.ax.yaxis.tick_right()
        native.ax.yaxis.set_label_position("right")
    labels = native.ax.get_xticklabels() if horizontal else native.ax.get_yticklabels()
    for label in labels:
        label.set_rotation(cfg.tick_angle if cfg is not None else 0.0)
    if spec.font_family:
        import matplotlib.text

        for text in native.ax.findobj(matplotlib.text.Text):
            text.set_fontfamily(spec.font_family)
    native.ax.set_position(output.default_box)
    native.ax.set_in_layout(output.default_in_layout)
    if (
        primary is not None
        and primary.custom_position
        and primary.position_x >= 0
        and primary.position_y >= 0
    ):
        position = native.ax.get_position()
        native.ax.set_position(
            (
                primary.position_x - position.width / 2,
                primary.position_y - position.height / 2,
                position.width,
                position.height,
            )
        )


def apply_colorbars(plan: ColorbarPlan) -> None:
    """Reuse current outputs or allocate the requested new owned topology once."""
    if any(
        any(output is item for item in plan.rendered.native_outputs.colorbars)
        for output in plan.retire
    ):
        raise ValueError("Colorbar teardown must complete before native projection.")
    for request in plan.requests:
        output = next(
            (item for item in plan.rendered.native_outputs.colorbars if _matches(item, request)),
            None,
        )
        if output is None:
            if not request.visible:
                continue
            output = _create(plan, request)
            plan.rendered.native_outputs.colorbars += (output,)
        _style(output, request)
