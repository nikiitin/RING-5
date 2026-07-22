"""Engine-independent validated Sankey diagram implementation."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Literal, cast, override

import numpy as np
import pandas as pd

from src.core.common.safe_format import safe_format_number
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import SankeyTraceConfig
from src.core.services.visualization.palette_service import resolve_palette
from src.web.components.plotting.config import sankey_config
from src.web.models.plot_models import PlotConfig
from src.web.pages.ui.plotting.base_plot import BasePlot

Arrangement = Literal["snap", "perpendicular", "freeform", "fixed"]
ColorMode = Literal["source", "target", "uniform"]
LabelMode = Literal["names", "names_with_totals", "hidden"]


def _ordered_nodes(sources: pd.Series, targets: pd.Series) -> list[str]:
    """Return stable first-appearance order across both flow endpoints."""
    return list(dict.fromkeys([*sources.astype(str).tolist(), *targets.astype(str).tolist()]))


def _validate_aliases(value: object) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict) or any(
        not isinstance(key, str) or not isinstance(label, str) for key, label in value.items()
    ):
        raise ValueError("Sankey node label aliases must map strings to strings.")
    return {key: label.strip() for key, label in value.items() if label.strip()}


def _layout_nodes(
    node_count: int,
    sources: list[int],
    targets: list[int],
) -> tuple[list[float], list[float]]:
    """Place an acyclic graph in deterministic left-to-right layers."""
    outgoing: dict[int, list[int]] = defaultdict(list)
    indegree = [0] * node_count
    for source, target in zip(sources, targets):
        outgoing[source].append(target)
        indegree[target] += 1
    queue = deque(index for index, degree in enumerate(indegree) if degree == 0)
    level = [0] * node_count
    visited = 0
    while queue:
        source = queue.popleft()
        visited += 1
        for target in outgoing[source]:
            level[target] = max(level[target], level[source] + 1)
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if visited != node_count:
        raise ValueError("Sankey links must form an acyclic flow; cycles are not supported.")

    maximum = max(level, default=0)
    x = [value / maximum if maximum else 0.5 for value in level]
    by_level: dict[int, list[int]] = defaultdict(list)
    for index, value in enumerate(level):
        by_level[value].append(index)
    y = [0.5] * node_count
    for indices in by_level.values():
        for position, node_index in enumerate(indices, start=1):
            y[node_index] = position / (len(indices) + 1)
    return x, y


def _fixed_positions(
    configured: object,
    nodes: list[str],
    default_x: list[float],
    default_y: list[float],
) -> tuple[list[float], list[float]]:
    if configured is None:
        return default_x, default_y
    if not isinstance(configured, dict):
        raise ValueError("Sankey fixed positions must map node names to [x, y].")
    x, y = list(default_x), list(default_y)
    for index, node in enumerate(nodes):
        position = configured.get(node)
        if position is None:
            continue
        if (
            not isinstance(position, (list, tuple))
            or len(position) != 2
            or any(not isinstance(value, (int, float)) for value in position)
        ):
            raise ValueError("Every Sankey fixed position must contain numeric x and y values.")
        px, py = float(position[0]), float(position[1])
        if not 0 <= px <= 1 or not 0 <= py <= 1:
            raise ValueError("Sankey fixed positions must stay between 0 and 1.")
        x[index], y[index] = px, py
    return x, y


class SankeyPlot(BasePlot):
    """Show validated weighted flow between named nodes."""

    def __init__(self, plot_id: int, name: str) -> None:
        super().__init__(plot_id, name, "sankey")

    @override
    def render_config_ui(self, data: pd.DataFrame, saved_config: PlotConfig) -> PlotConfig:
        """Render source, target, value, label, color, and arrangement controls."""
        return sankey_config.render(data, saved_config, self.plot_id)

    @override
    def create_traces(self, data: pd.DataFrame, config: PlotConfig) -> TraceBuildResult:
        # [impl->req~ring5.plot.sankey~1]
        """Aggregate duplicate links and precompute a deterministic flow layout."""
        source_col = str(config["sankey_source"])
        target_col = str(config["sankey_target"])
        value_col = str(config["sankey_value"])
        label_col = str(config["sankey_label"]) if config.get("sankey_label") else None
        required = [source_col, target_col, value_col]
        if any(column not in data for column in required):
            raise ValueError("Sankey source, target, and value columns must exist.")
        if label_col and label_col not in data:
            raise ValueError("Sankey link label column must exist.")
        if data[required].isna().any().any():
            raise ValueError("Sankey source, target, and value cells cannot be missing.")

        values = pd.to_numeric(data[value_col], errors="coerce")
        if values.isna().any() or not np.isfinite(values.to_numpy(dtype=float)).all():
            raise ValueError("Sankey values must be finite numbers.")
        if (values <= 0).any():
            raise ValueError("Sankey values must be greater than zero.")
        frame = pd.DataFrame(
            {
                "source": data[source_col].astype(str).str.strip(),
                "target": data[target_col].astype(str).str.strip(),
                "value": values.astype(float),
            }
        )
        if (frame["source"] == "").any() or (frame["target"] == "").any():
            raise ValueError("Sankey source and target labels cannot be empty.")
        frame["label"] = data[label_col].fillna("").astype(str) if label_col else ""

        grouped = (
            frame.groupby(["source", "target"], sort=False, as_index=False)
            .agg(
                value=("value", "sum"),
                label=("label", lambda labels: ", ".join(dict.fromkeys(filter(None, labels)))),
            )
            .reset_index(drop=True)
        )
        nodes = _ordered_nodes(frame["source"], frame["target"])
        node_index = {node: index for index, node in enumerate(nodes)}
        source_indices = [node_index[value] for value in grouped["source"]]
        target_indices = [node_index[value] for value in grouped["target"]]
        node_x, node_y = _layout_nodes(len(nodes), source_indices, target_indices)

        arrangement = cast(Arrangement, config.get("sankey_arrangement", "snap"))
        if arrangement not in ("snap", "perpendicular", "freeform", "fixed"):
            raise ValueError("Unknown Sankey arrangement.")
        if arrangement == "fixed":
            node_x, node_y = _fixed_positions(
                config.get("sankey_node_positions"), nodes, node_x, node_y
            )
        color_mode = cast(ColorMode, config.get("sankey_color_mode", "source"))
        if color_mode not in ("source", "target", "uniform"):
            raise ValueError("Unknown Sankey link color mode.")
        label_mode = cast(LabelMode, config.get("sankey_label_mode", "names"))
        if label_mode not in ("names", "names_with_totals", "hidden"):
            raise ValueError("Unknown Sankey node label mode.")

        node_pad = int(config.get("sankey_node_pad", 15))
        node_thickness = int(config.get("sankey_node_thickness", 20))
        node_line_width = float(config.get("sankey_node_line_width", 0.5))
        link_opacity = float(config.get("sankey_link_opacity", 0.35))
        if not 0 <= node_pad <= 100:
            raise ValueError("Sankey node padding must be between 0 and 100.")
        if not 5 <= node_thickness <= 100:
            raise ValueError("Sankey node thickness must be between 5 and 100.")
        if not 0 <= node_line_width <= 10:
            raise ValueError("Sankey node border width must be between 0 and 10.")
        if not 0.05 <= link_opacity <= 1:
            raise ValueError("Sankey link opacity must be between 0.05 and 1.")

        aliases = _validate_aliases(config.get("sankey_node_labels"))
        incoming: defaultdict[int, float] = defaultdict(float)
        outgoing: defaultdict[int, float] = defaultdict(float)
        for source, target, value in zip(source_indices, target_indices, grouped["value"]):
            outgoing[source] += float(value)
            incoming[target] += float(value)
        totals = {index: max(incoming[index], outgoing[index]) for index in range(len(nodes))}
        number_format = str(config.get("sankey_number_format", ".4g"))
        display_labels: list[str] = []
        for index, node in enumerate(nodes):
            label = aliases.get(node, node)
            if label_mode == "names_with_totals":
                label = (
                    f"{label} ({safe_format_number(totals[index], number_format, default='.4g')})"
                )
            elif label_mode == "hidden":
                label = ""
            display_labels.append(label)

        palette = resolve_palette(config.get("color_palette"))
        node_colors = [palette[index % len(palette)] for index in range(len(nodes))]
        uniform_color = str(config.get("sankey_link_color", "#7f7f7f"))
        link_colors = [
            (
                uniform_color
                if color_mode == "uniform"
                else node_colors[source if color_mode == "source" else target]
            )
            for source, target in zip(source_indices, target_indices)
        ]
        trace = SankeyTraceConfig(
            name=value_col,
            node_labels=display_labels,
            source_indices=source_indices,
            target_indices=target_indices,
            values=[float(value) for value in grouped["value"]],
            link_labels=grouped["label"].astype(str).tolist(),
            node_colors=node_colors,
            link_colors=link_colors,
            node_x=node_x,
            node_y=node_y,
            arrangement=arrangement,
            node_pad=node_pad,
            node_thickness=node_thickness,
            node_line_color=str(config.get("sankey_node_line_color", "#333333")),
            node_line_width=node_line_width,
            link_opacity=link_opacity,
            show_node_labels=label_mode != "hidden",
            show_link_labels=bool(config.get("sankey_show_link_labels", bool(label_col))),
            show_in_legend=False,
            custom_data={
                "drilldown": [
                    {source_col: source, target_col: target}
                    for source, target in zip(grouped["source"], grouped["target"])
                ]
            },
        )
        return TraceBuildResult(traces=[trace])

    @override
    def get_legend_column(self, config: PlotConfig) -> str | None:
        """Sankey link colors encode endpoint semantics rather than a data column."""
        return None


__all__ = ["SankeyPlot"]
