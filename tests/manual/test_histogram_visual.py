#!/usr/bin/env python3
"""
Manual visual test for histogram plot.

Run this script to generate a sample histogram plot and save it as HTML.
"""

import pandas as pd
from pathlib import Path

from src.plotting.plot_factory import PlotFactory


def main() -> None:
    """Generate sample histogram plot."""
    print("🎨 Generating sample histogram plot...")

    # Create synthetic histogram data
    data = pd.DataFrame(
        {
            "benchmark": ["A", "A", "B", "B"],
            "config": ["X", "Y", "X", "Y"],
            "latency..0-100": [5, 8, 3, 6],
            "latency..100-200": [10, 12, 9, 11],
            "latency..200-300": [15, 18, 13, 16],
            "latency..300-400": [8, 10, 7, 9],
            "latency..400-500": [3, 5, 2, 4],
            "latency..500-600": [1, 2, 1, 1],
        }
    )

    # Create histogram plot
    plot = PlotFactory.create_plot("histogram", plot_id=1, name="Sample Histogram")

    # Test 1: Single histogram
    print("\n📊 Test 1: Single histogram (ungrouped)")
    config_single = {
        "histogram_variable": "latency",
        "title": "Latency Distribution (Single)",
        "xlabel": "Latency (cycles)",
        "ylabel": "Count",
        "bucket_size": 100,
        "normalization": "count",
        "group_by": None,
        "cumulative": False,
    }

    fig1 = plot.create_figure(data, config_single)
    output_path1 = Path("histogram_single.html")
    fig1.write_html(str(output_path1))
    print(f"✅ Saved to: {output_path1.absolute()}")

    # Test 2: Grouped histogram
    print("\n📊 Test 2: Grouped histogram by benchmark")
    config_grouped = {
        "histogram_variable": "latency",
        "title": "Latency Distribution by Benchmark",
        "xlabel": "Latency (cycles)",
        "ylabel": "Count",
        "bucket_size": 100,
        "normalization": "count",
        "group_by": "benchmark",
        "cumulative": False,
    }

    fig2 = plot.create_figure(data, config_grouped)
    output_path2 = Path("histogram_grouped.html")
    fig2.write_html(str(output_path2))
    print(f"✅ Saved to: {output_path2.absolute()}")

    # Test 3: Normalized histogram
    print("\n📊 Test 3: Normalized histogram (probability)")
    config_normalized = {
        "histogram_variable": "latency",
        "title": "Latency Distribution (Normalized)",
        "xlabel": "Latency (cycles)",
        "ylabel": "Probability",
        "bucket_size": 100,
        "normalization": "probability",
        "group_by": "benchmark",
        "cumulative": False,
    }

    fig3 = plot.create_figure(data, config_normalized)
    output_path3 = Path("histogram_normalized.html")
    fig3.write_html(str(output_path3))
    print(f"✅ Saved to: {output_path3.absolute()}")

    # Test 4: Cumulative distribution
    print("\n📊 Test 4: Cumulative distribution")
    config_cumulative = {
        "histogram_variable": "latency",
        "title": "Cumulative Latency Distribution",
        "xlabel": "Latency (cycles)",
        "ylabel": "CDF",
        "bucket_size": 100,
        "normalization": "probability",
        "group_by": "benchmark",
        "cumulative": True,
    }

    fig4 = plot.create_figure(data, config_cumulative)
    output_path4 = Path("histogram_cumulative.html")
    fig4.write_html(str(output_path4))
    print(f"✅ Saved to: {output_path4.absolute()}")

    print("\n🎉 All histogram visualizations generated successfully!")
    print(f"\n📁 Files created:")
    print(f"   - {output_path1}")
    print(f"   - {output_path2}")
    print(f"   - {output_path3}")
    print(f"   - {output_path4}")


if __name__ == "__main__":
    main()
