#!/usr/bin/env python3
"""Build the bundled synthetic tutorial portfolio with the current serializer.

Maintainers regenerate the asset explicitly::

    python -m scripts.generate_example_portfolio \\
        --output src/core/resources/example-portfolio.json.gz --force

Tutorial values and pipelines are deterministic. Save-time metadata records the
actual build environment, so intentionally regenerating the asset changes its bytes.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, cast

from src.core.common.runtime_limits import configure_native_thread_limits

configure_native_thread_limits()

import pandas as pd  # noqa: E402: limits must precede native imports

from ring5 import RenderError, Session  # noqa: E402
from src.core.models.data_models import PipelineStep  # noqa: E402
from src.core.models.plot_config import PlotConfig  # noqa: E402
from src.core.models.plot_protocol import PlotProtocol  # noqa: E402
from src.core.services.data_services.portfolio_service import PortfolioService  # noqa: E402
from src.core.services.data_services.portfolio_validation_service import (  # noqa: E402
    validate_portfolio_document,
)
from src.core.services.portfolio_integrity_service import PortfolioIntegrityService  # noqa: E402
from src.core.services.shapers.pipeline_service import PipelineService  # noqa: E402
from src.core.state.repository_state_manager import RepositoryStateManager  # noqa: E402
from src.web.pages.ui.plotting.base_plot import BasePlot  # noqa: E402
from src.web.pages.ui.plotting.plot_factory import PlotFactory  # noqa: E402
from src.web.rendering.config_builder import ConfigSpecBuilder  # noqa: E402

BENCHMARK_ORDER = ["blackscholes", "canneal", "ferret", "swaptions"]
CONFIGURATION_ORDER = ["Baseline", "Large L2", "Prefetch"]
HISTOGRAM_VARIABLE = "memory_latency"
HISTOGRAM_COLUMNS = [
    f"{HISTOGRAM_VARIABLE}..{bucket}"
    for bucket in ("[0,20)", "[20,40)", "[40,60)", "[60,80)", "[80,100)")
]
CACHE_CAPACITIES = [64, 128, 256]
TRAFFIC_CLASSES = ["Demand reads", "Writebacks", "Prefetches"]
CONTRIBUTION_ORDER = ["Baseline", "Large L2 saving", "Prefetch saving"]


def build_example_data() -> pd.DataFrame:
    """Build six labeled synthetic scenarios in one reproducible source table.

    Columns not applicable to a scenario are absent values. Each example starts
    by selecting its scenario and columns; those cells never become measurements.
    The dataset illustrates mechanisms and does not represent simulator results.
    """
    profiles = {
        "blackscholes": (1.55, 8.4, 0.075),
        "canneal": (1.10, 12.8, 0.142),
        "ferret": (1.82, 10.1, 0.098),
        "swaptions": (2.20, 7.3, 0.052),
    }
    factors = {
        "Baseline": (1.00, 1.00, 1.00, 1.00),
        "Large L2": (1.12, 0.94, 0.76, 0.82),
        "Prefetch": (1.21, 1.04, 0.64, 0.71),
    }
    bucket_counts = {
        "Baseline": (180, 300, 270, 170, 80),
        "Large L2": (250, 340, 240, 120, 50),
        "Prefetch": (320, 360, 200, 90, 30),
    }
    records: list[dict[str, str | int | float]] = []
    for index, benchmark in enumerate(BENCHMARK_ORDER):
        base_ipc, base_energy, base_miss = profiles[benchmark]
        for configuration in CONFIGURATION_ORDER:
            ipc_factor, energy_factor, miss_factor, _ = factors[configuration]
            ipc = base_ipc * ipc_factor
            cycles = round(1_000_000_000 / ipc)
            front_end = round(cycles * (0.21 + 0.01 * index))
            memory = round(cycles * min(0.42, 0.24 + base_miss))
            record: dict[str, str | int | float] = {
                "scenario": "summary",
                "benchmark": benchmark,
                "configuration": configuration,
                "sample_count": 3,
                "ipc": round(ipc, 4),
                "ipc.sd": round(ipc * 0.035, 4),
                "cycles": cycles,
                "instructions": 1_000_000_000,
                "energy_j": round(base_energy * energy_factor, 4),
                "energy_j.sd": round(base_energy * energy_factor * 0.025, 4),
                "l1_miss_rate": round(base_miss * miss_factor * 0.58, 5),
                "l2_miss_rate": round(base_miss * miss_factor, 5),
                "l2_miss_rate.sd": round(base_miss * miss_factor * 0.04, 5),
                "front_end_cycles": front_end,
                "execution_cycles": cycles - front_end - memory,
                "memory_cycles": memory,
                "latency_sample_count": 1000,
                **dict(zip(HISTOGRAM_COLUMNS, bucket_counts[configuration], strict=True)),
            }
            records.append(record)
        for capacity, improvement in zip(CACHE_CAPACITIES, (1.0, 1.08, 1.16), strict=True):
            records.append(
                {
                    "scenario": "cache_sweep",
                    "benchmark": benchmark,
                    "cache_kib": capacity,
                    "ipc": round(base_ipc * improvement, 4),
                }
            )

    # Twelve controlled synthetic observations per configuration, for one workload.
    variation = (0.90, 0.92, 0.94, 0.96, 0.98, 1.0, 1.0, 1.02, 1.04, 1.06, 1.08, 1.10)
    for configuration in CONFIGURATION_ORDER:
        ipc_factor, _, _, latency_factor = factors[configuration]
        for run, multiplier in enumerate(variation, start=1):
            records.append(
                {
                    "scenario": "repeated_runs",
                    "benchmark": "blackscholes",
                    "configuration": configuration,
                    "run": run,
                    "ipc": round(1.55 * ipc_factor * multiplier, 5),
                    "memory_latency_ns": round(24.0 * latency_factor * multiplier, 5),
                }
            )
    for epoch, counts in enumerate(((10, 2, 3), (14, 3, 3), (18, 4, 4), (16, 3, 4), (12, 2, 4))):
        for traffic_class, count in zip(TRAFFIC_CLASSES, counts, strict=True):
            records.append(
                {
                    "scenario": "traffic_series",
                    "epoch": epoch,
                    "traffic_class": traffic_class,
                    "traffic_requests": count,
                }
            )
    for source, target, count in (
        ("CPU 0", "L1", 100),
        ("CPU 1", "L1", 80),
        ("L1", "L2", 60),
        ("L1", "Memory", 120),
        ("L2", "Memory", 60),
    ):
        records.append(
            {
                "scenario": "request_flow",
                "source": source,
                "target": target,
                "traffic_requests": count,
                "flow_label": f"{source} → {target}",
            }
        )
    for contribution, delta in zip(CONTRIBUTION_ORDER, (10.0, -1.6, -1.2), strict=True):
        records.append(
            {
                "scenario": "energy_waterfall",
                "contribution": contribution,
                "energy_delta": delta,
            }
        )
    return pd.DataFrame.from_records(records)


def _pipeline_step(step_id: int, step_type: str, **config: Any) -> PipelineStep:
    """Build one current pipeline entry with its required discriminator."""
    return PipelineStep(id=step_id, type=step_type, config={"type": step_type, **config})


def _pipeline(
    scenario: str,
    columns: list[str],
    *operations: tuple[str, dict[str, Any]],
) -> list[PipelineStep]:
    """Select one scenario before applying its visible, reproducible operations."""
    configurations: list[tuple[str, dict[str, Any]]] = [
        ("itemSelector", {"column": "scenario", "strings": [scenario], "mode": "exact"}),
        ("columnSelector", {"columns": columns}),
        *operations,
    ]
    return [
        _pipeline_step(index, kind, **config) for index, (kind, config) in enumerate(configurations)
    ]


def _common_config(title: str, xlabel: str, ylabel: str) -> PlotConfig:
    """Return shared publication settings without assuming a particular X axis."""
    return cast(
        PlotConfig,
        {
            "engine": "plotly",
            "title": title,
            "xlabel": xlabel,
            "ylabel": ylabel,
            "width": 760,
            "height": 460,
            "color_palette": "wong",
            "show_grid": True,
            "show_legend": True,
            "legend_orientation": "horizontal",
            "paper_bgcolor": "#FFFFFF",
            "plot_bgcolor": "#FFFFFF",
        },
    )


def build_example_plots(data: pd.DataFrame) -> list[BasePlot]:
    """Build and validate every registered plot from the shared tutorial source."""
    summary_columns = [
        "benchmark",
        "configuration",
        "sample_count",
        "ipc",
        "ipc.sd",
        "cycles",
        "instructions",
        "energy_j",
        "energy_j.sd",
        "l1_miss_rate",
        "l2_miss_rate",
        "l2_miss_rate.sd",
        "front_end_cycles",
        "execution_cycles",
        "memory_cycles",
        "latency_sample_count",
        *HISTOGRAM_COLUMNS,
    ]
    sort = (
        "sort",
        {"order_dict": {"benchmark": BENCHMARK_ORDER, "configuration": CONFIGURATION_ORDER}},
    )
    summary = _pipeline("summary", summary_columns, sort)
    normalized = _pipeline(
        "summary",
        summary_columns,
        (
            "normalize",
            {
                "normalizeVars": ["ipc"],
                "normalizerVars": ["ipc"],
                "normalizerColumn": "configuration",
                "normalizerValue": "Baseline",
                "groupBy": ["benchmark"],
                "normalizeSd": True,
            },
        ),
        sort,
    )
    baseline = _pipeline(
        "summary",
        summary_columns,
        ("itemSelector", {"column": "configuration", "strings": ["Baseline"], "mode": "exact"}),
        sort,
    )
    repeated = _pipeline(
        "repeated_runs",
        ["benchmark", "configuration", "run", "ipc", "memory_latency_ns"],
        ("sort", {"order_dict": {"configuration": CONFIGURATION_ORDER, "run": list(range(1, 13))}}),
    )
    cycles = ["front_end_cycles", "execution_cycles", "memory_cycles"]
    cycle_labels = dict(zip(cycles, ("Front end", "Execution", "Memory"), strict=True))
    plots: list[BasePlot] = []

    def add(
        plot_type: str,
        name: str,
        title: str,
        xlabel: str,
        ylabel: str,
        config: dict[str, Any],
        pipeline: list[PipelineStep],
    ) -> None:
        combined = _common_config(title, xlabel, ylabel)
        combined.update(config)
        plot = PlotFactory.create_plot(plot_type, len(plots) + 1, name)
        plot.config = copy.deepcopy(combined)
        plot.pipeline = copy.deepcopy(pipeline)
        plot.pipeline_counter = len(pipeline)
        processed = PipelineService.process_pipeline(
            data, [step["config"] for step in pipeline], track_source_rows=True
        )
        plot.replace_pipeline_data(data, processed)
        plots.append(plot)

    add(
        "bar",
        "01 · Normalized IPC",
        "Normalized IPC by Configuration",
        "Benchmark",
        "IPC / Baseline",
        {"x": "benchmark", "y": "ipc", "color": "configuration", "xaxis_order": BENCHMARK_ORDER},
        normalized,
    )
    add(
        "line",
        "02 · Cache Capacity Sweep",
        "IPC Across an Ordered Cache-Capacity Sweep",
        "L2 capacity (KiB)",
        "IPC",
        {
            "x": "cache_kib",
            "y": "ipc",
            "color": "benchmark",
            "line_shape": "linear",
            "xaxis_order": CACHE_CAPACITIES,
        },
        _pipeline(
            "cache_sweep",
            ["benchmark", "cache_kib", "ipc"],
            ("sort", {"order_dict": {"benchmark": BENCHMARK_ORDER, "cache_kib": CACHE_CAPACITIES}}),
        ),
    )
    add(
        "scatter",
        "03 · IPC vs Energy",
        "Performance–Energy Trade-off",
        "IPC",
        "Energy (J)",
        {"x": "ipc", "y": "energy_j", "color": "configuration"},
        summary,
    )
    add(
        "grouped_bar",
        "04 · Grouped IPC",
        "IPC with Illustrative Summary Uncertainty",
        "Benchmark",
        "IPC",
        {
            "x": "benchmark",
            "y": "ipc",
            "group": "configuration",
            "group_order": CONFIGURATION_ORDER,
            "show_error_bars": True,
            "xaxis_order": BENCHMARK_ORDER,
        },
        summary,
    )
    add(
        "stacked_bar",
        "05 · Cycle Composition",
        "Baseline Cycle Composition",
        "Benchmark",
        "Cycles",
        {
            "x": "benchmark",
            "y_columns": cycles,
            "show_totals": True,
            "legend_labels": cycle_labels,
            "xaxis_order": BENCHMARK_ORDER,
        },
        baseline,
    )
    add(
        "grouped_stacked_bar",
        "06 · Grouped Cycle Composition",
        "Cycle Composition by Configuration",
        "Benchmark",
        "Cycles",
        {
            "x": "benchmark",
            "group": "configuration",
            "group_order": CONFIGURATION_ORDER,
            "y_columns": cycles,
            "show_totals": False,
            "legend_labels": cycle_labels,
            "xaxis_order": BENCHMARK_ORDER,
        },
        summary,
    )
    add(
        "histogram",
        "07 · Latency Histogram",
        "Synthetic Memory-Latency Bucket Counts",
        "Latency bucket (ns)",
        "Percent",
        {
            "histogram_variable": HISTOGRAM_VARIABLE,
            "group_by": "configuration",
            "normalization": "percent",
            "cumulative": False,
        },
        summary,
    )
    add(
        "heatmap",
        "08 · Cache Miss Rates",
        "L1 and L2 Miss Rates by Configuration",
        "Configuration",
        "Miss-rate metric",
        {
            "x": "configuration",
            "metric_columns": ["l1_miss_rate", "l2_miss_rate"],
            "metric_labels": {"l1_miss_rate": "L1 miss rate", "l2_miss_rate": "L2 miss rate"},
            "facet_col": "benchmark",
            "facet_order": BENCHMARK_ORDER,
            "aggregation": "mean",
            "show_values": True,
            "text_format": ".3g",
            "xaxis_order": CONFIGURATION_ORDER,
        },
        summary,
    )
    add(
        "dual_axis_bar_dot",
        "09 · IPC and Cache Misses",
        "IPC and L2 Miss Rate",
        "Benchmark",
        "IPC",
        {
            "x": "benchmark",
            "y_bar": "ipc",
            "y_dot": "l2_miss_rate",
            "color": "configuration",
            "y2label": "L2 miss rate",
            "show_lines": False,
            "show_error_bars": True,
            "dot_symbol": "diamond",
            "dot_size": 9,
            "line_width": 2,
            "legend_order": CONFIGURATION_ORDER,
            "xaxis_order": BENCHMARK_ORDER,
        },
        summary,
    )
    add(
        "area",
        "10 · Memory Traffic Over Time",
        "Additive Memory Traffic in Equal-Length Intervals",
        "Interval (1,000 cycles)",
        "Requests per interval",
        {
            "x": "epoch",
            "y": "traffic_requests",
            "color": "traffic_class",
            "area_mode": "stack",
            "area_missing": "gap",
            "legend_order": TRAFFIC_CLASSES,
            "xaxis_order": list(range(5)),
        },
        _pipeline(
            "traffic_series",
            ["epoch", "traffic_class", "traffic_requests"],
            ("sort", {"order_dict": {"traffic_class": TRAFFIC_CLASSES, "epoch": list(range(5))}}),
        ),
    )
    add(
        "box",
        "11 · Repeated-Run IPC",
        "Twelve Synthetic IPC Observations per Configuration",
        "Configuration",
        "IPC",
        {"x": "configuration", "y": "ipc", "xaxis_order": CONFIGURATION_ORDER},
        repeated,
    )
    add(
        "ecdf",
        "12 · Repeated-Run Latency ECDF",
        "Synthetic Repeated-Run Memory Latency",
        "Memory latency (ns)",
        "Proportion",
        {
            "x": "memory_latency_ns",
            "color": "configuration",
            "ecdf_markers": True,
            "legend_order": CONFIGURATION_ORDER,
        },
        repeated,
    )
    add(
        "parallel_coordinates",
        "13 · Design Space",
        "Configuration Design Space",
        "",
        "",
        {
            "parallel_dimensions": [
                "benchmark",
                "configuration",
                "ipc",
                "energy_j",
                "l2_miss_rate",
            ],
            "parallel_color": "ipc",
            "parallel_colorbar_title": "IPC",
        },
        summary,
    )
    add(
        "radar",
        "14 · Workload Profile",
        "IPC Profile by Workload",
        "Benchmark",
        "IPC",
        {
            "x": "benchmark",
            "y": "ipc",
            "color": "configuration",
            "legend_order": CONFIGURATION_ORDER,
            "radar_scale_mode": "zero",
            "xaxis_order": BENCHMARK_ORDER,
        },
        summary,
    )
    add(
        "sankey",
        "15 · Request Flow",
        "Conserved Synthetic Memory Requests",
        "",
        "",
        {
            "sankey_source": "source",
            "sankey_target": "target",
            "sankey_value": "traffic_requests",
            "sankey_label": "flow_label",
            "sankey_label_mode": "names",
        },
        _pipeline("request_flow", ["source", "target", "traffic_requests", "flow_label"]),
    )
    add(
        "violin",
        "16 · Repeated-Run Latency",
        "Twelve Synthetic Latency Observations per Configuration",
        "Configuration",
        "Memory latency (ns)",
        {
            "x": "configuration",
            "y": "memory_latency_ns",
            "xaxis_order": CONFIGURATION_ORDER,
            "summary_mode": "box+mean",
        },
        repeated,
    )
    add(
        "waterfall",
        "17 · Energy Savings",
        "Illustrative Energy Savings",
        "Contribution",
        "Energy (J)",
        {
            "x": "contribution",
            "y": "energy_delta",
            "xaxis_order": CONTRIBUTION_ORDER,
            "waterfall_absolute": ["Baseline"],
            "waterfall_total_label": "Optimized",
        },
        _pipeline(
            "energy_waterfall",
            ["contribution", "energy_delta"],
            ("sort", {"order_dict": {"contribution": CONTRIBUTION_ORDER}}),
        ),
    )

    expected = set(PlotFactory.get_available_plot_types())
    actual = {plot.plot_type for plot in plots}
    if actual != expected or len(plots) != len(expected):
        raise RuntimeError(
            f"Example plot coverage mismatch; missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )
    with Session() as session:
        for plot in plots:
            session.render(plot)
    return plots


def _build_figure_spec(config: dict[str, Any], plot_type: str) -> dict[str, Any]:
    """Serialize the same engine-neutral figure specification used by the UI."""
    return ConfigSpecBuilder.from_config(config, plot_type).to_dict()


def build_example_portfolio() -> bytes:
    # [impl->req~ring5.portfolio.example-catalog~1]
    """Serialize the canonical synthetic tutorial without writing user state.

    Returns:
        Integrity-checked current portfolio bytes with actual save-time metadata.

    Raises:
        RenderError: A configured example fails rendering validation.
        ValueError: The shared data or current serialized document is invalid.
    """
    data = build_example_data()
    plots = build_example_plots(data)
    state = RepositoryStateManager(plot_deserializer=PlotFactory.from_dict)
    state.set_data(data)
    state.set_plots(cast(list[PlotProtocol], plots))
    state.set_plot_counter(len(plots))
    state.set_current_plot_id(plots[0].plot_id)
    state.set_use_parser(False)
    state.set_stats_path("")
    state.set_stats_pattern("stats.txt")
    state.set_config(
        {
            "example_portfolio": True,
            "title": "RING-5 Example Portfolio",
            "description": (
                "Synthetic tutorial data: 17 plot types and reproducible pipelines. "
                "No simulator results."
            ),
            "data_provenance": (
                "Deterministic synthetic tutorial scenarios; "
                "not measured or parsed simulator data."
            ),
        }
    )
    payload = PortfolioService(state).serialize_workspace(
        data,
        cast(list[PlotProtocol], plots),
        state.get_config(),
        len(plots),
        csv_path=None,
        parse_variables=[],
        figure_spec_enricher=_build_figure_spec,
    )
    document = json.loads(payload)
    validate_portfolio_document(document)
    report = PortfolioIntegrityService.verify(document)
    PortfolioIntegrityService.require_restorable(report)
    restored = RepositoryStateManager(plot_deserializer=PlotFactory.from_dict)
    restore = restored.restore_session(document)
    if not restore.complete or restore.plots_restored != len(plots) or not restore.data_restored:
        raise ValueError("Example portfolio failed complete restore verification.")
    return payload


def generate_example_portfolio(output: Path, *, force: bool = False) -> Path:
    """Write the canonical gzip-compressed JSON asset to an explicit destination.

    Args:
        output: Destination ``.json.gz`` path; no application directory is chosen implicitly.
        force: Allow replacement of this exact file.

    Returns:
        Written destination path.

    Raises:
        FileExistsError: The destination exists and replacement was not requested.
        OSError: The explicitly selected destination cannot be written.
        RenderError: The catalog fails rendering validation.
        ValueError: The current portfolio cannot be built or restored completely.
    """
    output = output.resolve()
    if output.exists() and not force:
        raise FileExistsError(f"Portfolio already exists: {output}. Use --force to replace it.")
    payload = gzip.compress(build_example_portfolio(), mtime=0)
    output.parent.mkdir(parents=True, exist_ok=True)
    staged: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=output.parent, prefix=".ring5-example-", suffix=".tmp", delete=False
        ) as target:
            staged = Path(target.name)
            target.write(payload)
        staged.chmod(0o644)
        if force:
            os.replace(staged, output)
        else:
            os.link(staged, output)
    except FileExistsError as exc:
        raise FileExistsError(
            f"Portfolio already exists: {output}. Use --force to replace it."
        ) from exc
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)
    return output


def main(argv: list[str] | None = None) -> int:
    """Build the canonical tutorial asset at an explicitly selected path."""
    parser = argparse.ArgumentParser(description="Build the bundled synthetic tutorial portfolio.")
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Destination gzip-compressed portfolio JSON file (.json.gz).",
    )
    parser.add_argument(
        "--force", action="store_true", help="Replace that destination if it exists."
    )
    args = parser.parse_args(argv)
    try:
        output = generate_example_portfolio(args.output, force=args.force)
    except (OSError, RenderError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Generated synthetic portfolio: {output}")
    print(f"Examples: {len(PlotFactory.get_available_plot_types())} plot types")
    print(f"Rows: {len(build_example_data())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
