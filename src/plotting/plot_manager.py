"""
PlotManager orchestrates plot generation with multiprocessing support.
"""

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from src.data_plotter.multiprocessing.plotWorkPool import PlotWorkPool
from src.plotting.factory.plot_factory import PlotFactory
from src.plotting.renderer.plot_renderer import PlotRenderer
from src.plotting.work.plot_work_impl import PlotWorkImpl


class PlotManager:
    """
    Manages plot generation from configurations.

    Supports both sequential and parallel (multithreaded) plot generation.
    Follows Facade Pattern: provides simple interface to complex subsystem.
    """

    def __init__(self, data_path: str, output_dir: str):
        """
        Initialize plot manager.

        Args:
            data_path: Path to CSV data file
            output_dir: Output directory for generated plots
        """
        self.data_path = Path(data_path)
        self.output_dir = Path(output_dir)

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Verify data file exists
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.data_path}")

    def generate_plots(
        self, plot_configs: List[Dict[str, Any]], use_multiprocessing: bool = True
    ) -> None:
        """
        Generate all plots from configurations.

        Args:
            plot_configs: List of plot configuration dictionaries
            use_multiprocessing: Whether to use multiprocessing for parallel generation
        """
        if not plot_configs:
            print("No plots to generate")
            return

        # Ensure all output paths are absolute and in output_dir
        normalized_configs = self._normalize_configs(plot_configs)

        if use_multiprocessing and len(normalized_configs) > 1:
            self._generate_parallel(normalized_configs)
        else:
            self._generate_sequential(normalized_configs)

        print(f"\n✓ All plots generated in: {self.output_dir}")

    def _normalize_configs(self, plot_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize plot configurations to ensure proper output paths.

        Args:
            plot_configs: Original configurations

        Returns:
            Normalized configurations with absolute output paths
        """
        normalized = []

        for config in plot_configs:
            # Deep copy to avoid modifying original
            normalized_config = config.copy()

            # Ensure output section exists
            if "output" not in normalized_config:
                normalized_config["output"] = {}

            # Normalize filename to absolute path in output_dir
            if "filename" in normalized_config["output"]:
                filename = normalized_config["output"]["filename"]
                # Remove extension if present (will be added by plot)
                filename_path = Path(filename)
                if filename_path.suffix:
                    filename = filename_path.stem

                # Make absolute path in output_dir
                normalized_config["output"]["filename"] = str(self.output_dir / filename)
            else:
                # Generate default filename
                plot_type = normalized_config.get("type", "plot")
                plot_num = len(normalized) + 1
                normalized_config["output"]["filename"] = str(
                    self.output_dir / f"{plot_type}_{plot_num}"
                )

            normalized.append(normalized_config)

        return normalized

    def _generate_sequential(self, plot_configs: List[Dict[str, Any]]) -> None:
        """
        Generate plots sequentially (single-threaded).

        Args:
            plot_configs: Normalized plot configurations
        """
        print(f"Generating {len(plot_configs)} plot(s) sequentially...")

        # Load data once
        try:
            data = pd.read_csv(self.data_path)
        except Exception:
            data = pd.read_csv(self.data_path, sep=r"\s+")

        renderer = PlotRenderer()

        for i, config in enumerate(plot_configs, 1):
            try:
                print(
                    f"  [{i}/{len(plot_configs)}] Generating {config.get('type', 'unknown')} "
                    "plot..."
                )

                # Create plot
                plot = PlotFactory.create_plot(data.copy(), config)

                # Render
                renderer.render(plot)

            except Exception as e:
                print(f"  ✗ Error generating plot {i}: {e}")
                import traceback

                traceback.print_exc()

    def _generate_parallel(self, plot_configs: List[Dict[str, Any]]) -> None:
        """
        Generate plots in parallel using multiprocessing pool.

        Args:
            plot_configs: Normalized plot configurations
        """
        print(f"Generating {len(plot_configs)} plot(s) in parallel...")

        # Get pool instance
        pool = PlotWorkPool.getInstance()
        pool.startPool()

        # Add all plots as work items
        for config in plot_configs:
            work = PlotWorkImpl(str(self.data_path), config)
            pool.addWork(work)

        # Signal completion and wait for all workers to finish
        pool.setFinishJob()
