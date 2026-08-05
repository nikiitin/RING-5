#!/usr/bin/env python3
"""Generate a self-contained RING-5 portfolio with representative examples.

Run from the repository root:

    python scripts/generate_example_portfolio.py

The resulting portfolio appears on the application's Save/Load Portfolio
page. Use ``--output-dir`` to generate into an isolated directory instead.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, cast

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.common.runtime_limits import configure_native_thread_limits  # noqa: E402

configure_native_thread_limits()

import pandas as pd  # noqa: E402: limits must precede native imports

from src.core.common.utils import sanitize_filename  # noqa: E402
from src.core.models import PlotProtocol  # noqa: E402
from src.core.models.data_models import PipelineStep, ShaperStepConfig  # noqa: E402
from src.core.services.data_services.path_service import PathService  # noqa: E402
from src.core.services.data_services.portfolio_service import PortfolioService  # noqa: E402
from src.core.services.shapers.pipeline_service import PipelineService  # noqa: E402
from src.core.state.repository_state_manager import RepositoryStateManager  # noqa: E402
from src.web.models.plot_models import PlotConfig  # noqa: E402
from src.web.pages.ui.plotting.base_plot import BasePlot  # noqa: E402
from src.web.pages.ui.plotting.plot_factory import PlotFactory  # noqa: E402
from src.web.rendering.config_builder import ConfigSpecBuilder  # noqa: E402

DEFAULT_PORTFOLIO_NAME = "RING5_Example_Cases"
BENCHMARK_ORDER = ["blackscholes", "canneal", "ferret", "swaptions"]
CONFIGURATION_ORDER = ["Baseline", "Large L2", "Prefetch"]
HISTOGRAM_VARIABLE = "memory_latency"


def build_example_data() -> pd.DataFrame:
    """Build a deterministic summary dataset for all example plots."""
    benchmark_profiles = {
        "blackscholes": (1.55, 8.4, 24.0, 0.075),
        "canneal": (1.10, 12.8, 38.0, 0.142),
        "ferret": (1.82, 10.1, 29.0, 0.098),
        "swaptions": (2.20, 7.3, 18.0, 0.052),
    }
    configuration_profiles = {
        "Baseline": (1.00, 1.00, 1.00, 1.00),
        "Large L2": (1.12, 0.94, 0.76, 0.82),
        "Prefetch": (1.21, 1.04, 0.64, 0.71),
    }
    bucket_weights = {
        "Baseline": (0.18, 0.30, 0.27, 0.17, 0.08),
        "Large L2": (0.25, 0.34, 0.24, 0.12, 0.05),
        "Prefetch": (0.32, 0.36, 0.20, 0.09, 0.03),
    }
    bucket_names = ["0-20", "20-40", "40-60", "60-80", "80-100"]

    records: list[dict[str, str | int | float]] = []
    for benchmark_index, benchmark in enumerate(BENCHMARK_ORDER):
        base_ipc, base_energy, base_latency, base_l2_miss = benchmark_profiles[benchmark]
        for configuration_index, configuration in enumerate(CONFIGURATION_ORDER):
            ipc_factor, energy_factor, miss_factor, latency_factor = configuration_profiles[
                configuration
            ]
            ipc = base_ipc * ipc_factor
            cycles = 1_000_000_000 / ipc
            memory_share = min(0.42, 0.24 + base_l2_miss)
            front_end_share = 0.21 + (0.01 * benchmark_index)
            execution_share = 1.0 - front_end_share - memory_share
            sample_count = 900 + (benchmark_index * 120) + (configuration_index * 40)

            record: dict[str, str | int | float] = {
                "benchmark": benchmark,
                "configuration": configuration,
                "sample_count": 3,
                "ipc": round(ipc, 4),
                "ipc.sd": round(ipc * 0.035, 4),
                "cycles": round(cycles),
                "instructions": 1_000_000_000,
                "energy_j": round(base_energy * energy_factor, 4),
                "energy_j.sd": round(base_energy * energy_factor * 0.025, 4),
                "memory_latency_ns": round(base_latency * latency_factor, 4),
                "l1_miss_rate": round(base_l2_miss * miss_factor * 0.58, 5),
                "l2_miss_rate": round(base_l2_miss * miss_factor, 5),
                "l2_miss_rate.sd": round(base_l2_miss * miss_factor * 0.04, 5),
                "front_end_cycles": round(cycles * front_end_share),
                "execution_cycles": round(cycles * execution_share),
                "memory_cycles": round(cycles * memory_share),
            }
            for bucket_name, weight in zip(
                bucket_names,
                bucket_weights[configuration],
                strict=True,
            ):
                record[f"{HISTOGRAM_VARIABLE}..{bucket_name}"] = round(sample_count * weight)
            records.append(record)

    return pd.DataFrame.from_records(records)


def _pipeline_step(step_id: int, step_type: str, **config: Any) -> PipelineStep:
    """Build one nested pipeline step with the required type marker."""
    typed_config = cast(ShaperStepConfig, {"type": step_type, **config})
    return PipelineStep(id=step_id, type=step_type, config=typed_config)


def _common_config(title: str, xlabel: str, ylabel: str) -> PlotConfig:
    """Return shared publication-friendly plot settings."""
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
            "legend_orientation": "h",
            "paper_bgcolor": "#FFFFFF",
            "plot_bgcolor": "#FFFFFF",
            "xaxis_order": BENCHMARK_ORDER,
        },
    )


def _make_plot(
    plot_id: int,
    plot_type: str,
    name: str,
    data: pd.DataFrame,
    config: PlotConfig,
    pipeline: list[PipelineStep] | None = None,
) -> BasePlot:
    """Create a fully configured, renderable plot."""
    plot = PlotFactory.create_plot(plot_type, plot_id, name)
    plot.config = config
    plot.processed_data = data.copy()
    plot.pipeline = pipeline or []
    plot.pipeline_counter = len(plot.pipeline)
    # Validate the example at generation time instead of writing broken state.
    plot.generate_figure()
    return plot


def build_example_plots(data: pd.DataFrame) -> list[BasePlot]:
    """Create one validated example for every registered plot type."""
    sort_pipeline = [
        _pipeline_step(
            0,
            "sort",
            order_dict={
                "benchmark": BENCHMARK_ORDER,
                "configuration": CONFIGURATION_ORDER,
            },
        )
    ]

    normalized_pipeline = [
        _pipeline_step(
            0,
            "normalize",
            normalizeVars=["ipc"],
            normalizerVars=["ipc"],
            normalizerColumn="configuration",
            normalizerValue="Baseline",
            groupBy=["benchmark"],
            normalizeSd=True,
        ),
        _pipeline_step(
            1,
            "sort",
            order_dict={
                "benchmark": BENCHMARK_ORDER,
                "configuration": CONFIGURATION_ORDER,
            },
        ),
    ]
    normalized_data = PipelineService.process_pipeline(
        data,
        [step["config"] for step in normalized_pipeline],
    )

    baseline_pipeline = [
        _pipeline_step(
            0,
            "itemSelector",
            column="configuration",
            strings=["Baseline"],
            mode="exact",
        ),
        _pipeline_step(1, "sort", order_dict={"benchmark": BENCHMARK_ORDER}),
    ]
    baseline_data = PipelineService.process_pipeline(
        data,
        [step["config"] for step in baseline_pipeline],
    )

    plots: list[BasePlot] = []

    config = _common_config("Normalized IPC by Configuration", "Benchmark", "IPC / Baseline")
    config.update({"x": "benchmark", "y": "ipc", "color": "configuration"})
    plots.append(
        _make_plot(
            1,
            "bar",
            "01 · Normalized IPC",
            normalized_data,
            config,
            normalized_pipeline,
        )
    )

    config = _common_config("Energy Across Workloads", "Benchmark", "Energy (J)")
    config.update(
        {
            "x": "benchmark",
            "y": "energy_j",
            "color": "configuration",
            "line_shape": "spline",
        }
    )
    plots.append(_make_plot(2, "line", "02 · Energy Trend", data, config, sort_pipeline))

    config = _common_config("Performance–Energy Trade-off", "IPC", "Energy (J)")
    config.update({"x": "ipc", "y": "energy_j", "color": "configuration"})
    plots.append(_make_plot(3, "scatter", "03 · IPC vs Energy", data, config))

    config = _common_config("IPC with Run-to-Run Variation", "Benchmark", "IPC")
    config.update(
        {
            "x": "benchmark",
            "y": "ipc",
            "group": "configuration",
            "group_order": CONFIGURATION_ORDER,
            "show_error_bars": True,
        }
    )
    plots.append(_make_plot(4, "grouped_bar", "04 · Grouped IPC", data, config, sort_pipeline))

    config = _common_config("Baseline Cycle Composition", "Benchmark", "Cycles")
    config.update(
        {
            "x": "benchmark",
            "y_columns": ["front_end_cycles", "execution_cycles", "memory_cycles"],
            "show_totals": True,
            "series_styles": {
                "front_end_cycles": {"name": "Front end"},
                "execution_cycles": {"name": "Execution"},
                "memory_cycles": {"name": "Memory"},
            },
        }
    )
    plots.append(
        _make_plot(
            5,
            "stacked_bar",
            "05 · Cycle Composition",
            baseline_data,
            config,
            baseline_pipeline,
        )
    )

    config = _common_config("Cycle Composition by Configuration", "Benchmark", "Cycles")
    config.update(
        {
            "x": "benchmark",
            "group": "configuration",
            "group_order": CONFIGURATION_ORDER,
            "y_columns": ["front_end_cycles", "execution_cycles", "memory_cycles"],
            "show_totals": False,
            "series_styles": {
                "front_end_cycles": {"name": "Front end"},
                "execution_cycles": {"name": "Execution"},
                "memory_cycles": {"name": "Memory"},
            },
        }
    )
    plots.append(
        _make_plot(
            6,
            "grouped_stacked_bar",
            "06 · Grouped Cycle Composition",
            data,
            config,
            sort_pipeline,
        )
    )

    config = _common_config("Memory-Latency Distribution", "Latency bucket (ns)", "Percent")
    config.update(
        {
            "histogram_variable": HISTOGRAM_VARIABLE,
            "group_by": "configuration",
            "normalization": "percent",
            "cumulative": False,
        }
    )
    plots.append(_make_plot(7, "histogram", "07 · Latency Histogram", data, config, sort_pipeline))

    config = _common_config("Metric Overview", "Configuration", "Metric")
    config.update(
        {
            "x": "configuration",
            "metric_columns": ["ipc", "energy_j", "l2_miss_rate"],
            "metric_labels": {
                "ipc": "IPC",
                "energy_j": "Energy (J)",
                "l2_miss_rate": "L2 miss rate",
            },
            "facet_col": "benchmark",
            "facet_order": BENCHMARK_ORDER,
            "aggregation": "mean",
            "show_values": True,
            "text_format": ".3g",
            "xaxis_order": CONFIGURATION_ORDER,
        }
    )
    plots.append(_make_plot(8, "heatmap", "08 · Faceted Metric Heatmap", data, config))

    config = _common_config("IPC and L2 Miss Rate", "Benchmark", "IPC")
    config.update(
        {
            "x": "benchmark",
            "y_bar": "ipc",
            "y_dot": "l2_miss_rate",
            "color": "configuration",
            "y2label": "L2 miss rate",
            "show_lines": True,
            "show_error_bars": True,
            "dot_symbol": "diamond",
            "dot_size": 9,
            "line_width": 2,
            "legend_order": CONFIGURATION_ORDER,
        }
    )
    plots.append(
        _make_plot(
            9,
            "dual_axis_bar_dot",
            "09 · IPC and Cache Misses",
            data,
            config,
            sort_pipeline,
        )
    )

    config = _common_config("Cumulative IPC Across Workloads", "Benchmark", "IPC")
    config.update(
        {
            "x": "benchmark",
            "y": "ipc",
            "color": "configuration",
            "area_mode": "stack",
            "legend_order": CONFIGURATION_ORDER,
        }
    )
    plots.append(_make_plot(10, "area", "10 · Cumulative IPC", data, config, sort_pipeline))

    config = _common_config("IPC Distribution by Configuration", "Configuration", "IPC")
    config.update({"x": "configuration", "y": "ipc", "xaxis_order": CONFIGURATION_ORDER})
    plots.append(_make_plot(11, "box", "11 · IPC Distribution", data, config))

    config = _common_config("Cumulative Memory Latency", "Memory latency (ns)", "Proportion")
    config.update(
        {
            "x": "memory_latency_ns",
            "color": "configuration",
            "ecdf_markers": True,
            "legend_order": CONFIGURATION_ORDER,
        }
    )
    plots.append(_make_plot(12, "ecdf", "12 · Memory-Latency ECDF", data, config))

    config = _common_config("Configuration Design Space", "", "")
    config.update(
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
        }
    )
    plots.append(_make_plot(13, "parallel_coordinates", "13 · Design Space", data, config))

    config = _common_config("IPC Profile by Workload", "Benchmark", "IPC")
    config.update(
        {
            "x": "benchmark",
            "y": "ipc",
            "color": "configuration",
            "legend_order": CONFIGURATION_ORDER,
            "radar_scale_mode": "zero",
        }
    )
    plots.append(_make_plot(14, "radar", "14 · Workload Profile", data, config))

    sankey_data = data.assign(
        source="Workload · " + data["benchmark"].astype(str),
        target="Configuration · " + data["configuration"].astype(str),
        flow=data["ipc"] * 100,
        flow_label=data["benchmark"].astype(str) + " → " + data["configuration"].astype(str),
    )
    config = _common_config("Workload-to-Configuration Performance Flow", "", "")
    config.update(
        {
            "sankey_source": "source",
            "sankey_target": "target",
            "sankey_value": "flow",
            "sankey_label": "flow_label",
            "sankey_label_mode": "names",
        }
    )
    plots.append(_make_plot(15, "sankey", "15 · Performance Flow", sankey_data, config))

    config = _common_config("Latency Distribution by Configuration", "Configuration", "Latency")
    config.update(
        {
            "x": "configuration",
            "y": "memory_latency_ns",
            "xaxis_order": CONFIGURATION_ORDER,
            "summary_mode": "box+mean",
        }
    )
    plots.append(_make_plot(16, "violin", "16 · Latency Distribution", data, config))

    waterfall_data = pd.DataFrame(
        {
            "contribution": ["Baseline", "Large L2 saving", "Prefetch saving"],
            "energy_delta": [10.0, -1.6, -1.2],
        }
    )
    config = _common_config("Illustrative Energy Savings", "Contribution", "Energy (J)")
    config.update(
        {
            "x": "contribution",
            "y": "energy_delta",
            "xaxis_order": waterfall_data["contribution"].tolist(),
            "waterfall_absolute": ["Baseline"],
            "waterfall_total_label": "Optimized",
        }
    )
    plots.append(_make_plot(17, "waterfall", "17 · Energy Savings", waterfall_data, config))

    expected_types = set(PlotFactory.get_available_plot_types())
    generated_types = {plot.plot_type for plot in plots}
    if generated_types != expected_types:
        missing = sorted(expected_types - generated_types)
        extra = sorted(generated_types - expected_types)
        raise RuntimeError(f"Example plot coverage mismatch; missing={missing}, extra={extra}")
    return plots


def _build_figure_spec(config: dict[str, Any], plot_type: str) -> dict[str, Any]:
    """Serialize the same engine-neutral figure spec used by the UI."""
    return ConfigSpecBuilder.from_config(config, plot_type).to_dict()


def generate_example_portfolio(
    name: str = DEFAULT_PORTFOLIO_NAME,
    *,
    output_dir: Path | None = None,
    force: bool = False,
) -> Path:
    # [impl->req~ring5.portfolio.example-catalog~1]
    """Generate, validate, save, reload, and return an example portfolio path."""
    portfolios_dir = (
        output_dir.resolve() if output_dir is not None else PathService.get_portfolios_dir()
    )
    portfolios_dir.mkdir(parents=True, exist_ok=True)
    output_path = portfolios_dir / f"{sanitize_filename(name)}.json"
    if output_path.exists() and not force:
        raise FileExistsError(
            f"Portfolio already exists: {output_path}. Use --force to replace it."
        )

    data = build_example_data()
    plots = build_example_plots(data)
    portfolio_plots: list[PlotProtocol] = list(plots)
    state_manager = RepositoryStateManager(plot_deserializer=PlotFactory.from_dict)
    state_manager.set_data(data)
    state_manager.set_plots(portfolio_plots)
    state_manager.set_plot_counter(len(plots))
    state_manager.set_current_plot_id(plots[0].plot_id)
    state_manager.set_use_parser(False)
    state_manager.set_stats_path("examples/generated")
    state_manager.set_stats_pattern("stats.txt")
    state_manager.set_config(
        {
            "example_portfolio": True,
            "description": "Representative RING-5 plot and pipeline examples",
        }
    )

    service = PortfolioService(state_manager, portfolios_dir=portfolios_dir)
    service.save_portfolio(
        name=name,
        data=data,
        plots=portfolio_plots,
        config=state_manager.get_config(),
        plot_counter=state_manager.get_plot_counter(),
        csv_path=None,
        parse_variables=[],
        figure_spec_enricher=_build_figure_spec,
        overwrite=force,
    )

    # Verify the exact artifact through the public loader and restoration path.
    loaded = service.load_portfolio(name)
    restored = RepositoryStateManager(plot_deserializer=PlotFactory.from_dict)
    restored.restore_session(loaded)
    restored_plots = restored.get_plots()
    if len(restored_plots) != len(plots) or restored.get_data() is None:
        raise RuntimeError("Generated portfolio failed its restore verification")
    for restored_plot in restored_plots:
        cast(BasePlot, restored_plot).generate_figure()

    return output_path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments without mutating generator state."""
    parser = argparse.ArgumentParser(
        description="Generate a self-contained RING-5 portfolio with all plot examples."
    )
    parser.add_argument(
        "--name",
        default=DEFAULT_PORTFOLIO_NAME,
        help=f"Portfolio name (default: {DEFAULT_PORTFOLIO_NAME})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Destination directory (default: .ring5/portfolios)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing portfolio with the same sanitized name.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    args = _parse_args(argv)
    try:
        output_path = generate_example_portfolio(
            args.name,
            output_dir=args.output_dir,
            force=args.force,
        )
    except (FileExistsError, OSError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Generated portfolio: {output_path}")
    print(f"Examples: {len(PlotFactory.get_available_plot_types())} plot types")
    print(f"Rows: {len(build_example_data())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
