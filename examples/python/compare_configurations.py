"""Reduce repeated observations, plot baseline ratios, and replay a portfolio."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Literal

import ring5

DEFAULT_INPUT = Path(__file__).resolve().parents[1] / "data" / "repeated_runs.csv"


def run(input_csv: Path, output_dir: Path, *, replace_portfolio: bool = False) -> dict:
    """Write comparison tables, two figure formats, and a replayed portfolio."""
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("RING5_DATA_DIR", str(output_dir / "workspace"))
    portfolio_name = "Documentation IPC comparison"
    with ring5.Session() as session:
        raw = session.load(str(input_csv.resolve()))
        reduced = session.reduce_seeds(
            raw,
            categorical_cols=["benchmark", "configuration"],
            statistic_cols=["ipc"],
        )
        normalized = session.shape(
            reduced,
            [
                {
                    "type": "normalize",
                    "normalizeVars": ["ipc"],
                    "normalizerVars": ["ipc"],
                    "normalizerColumn": "configuration",
                    "normalizerValue": "baseline",
                    "groupBy": ["benchmark"],
                    "normalizeSd": True,
                }
            ],
        )
        reduced.to_csv(str(output_dir / "reduced.csv"))
        normalized.to_csv(str(output_dir / "normalized.csv"))
        plot = session.create_plot(
            "grouped_bar",
            data=normalized,
            name="IPC relative to baseline",
            config=ring5.FigureSpec(
                x="benchmark",
                group="configuration",
                y_columns=["ipc"],
                title="Synthetic repeated-run comparison",
                ylabel="IPC / baseline (higher is better)",
                extra={"show_error_bars": True},
            ),
        )
        written = []
        formats: tuple[tuple[Literal["matplotlib", "plotly"], str], ...] = (
            ("matplotlib", "pdf"),
            ("plotly", "html"),
        )
        for engine, extension in formats:
            figure = session.render(plot, engine=engine)
            written.append(
                session.export(
                    figure,
                    str(output_dir / f"ipc-normalized.{extension}"),
                    deterministic=True,
                )
            )
        session.save_portfolio(portfolio_name, overwrite=replace_portfolio)
        summary = {
            "raw_rows": len(raw),
            "reduced_rows": len(reduced),
            "normalized_rows": normalized.rows(),
            "portfolio": portfolio_name,
            "exports": written,
        }
    summary["replayed"] = ring5.render_portfolio(
        portfolio_name, str(output_dir / "replayed"), engine="matplotlib", fmt="pdf"
    )
    (output_dir / "analysis.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return summary


def main() -> int:
    """Run the example with caller-selected paths."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=Path("example-output/comparison"))
    parser.add_argument(
        "--replace-portfolio", action="store_true", help="Replace this example's saved portfolio."
    )
    args = parser.parse_args()
    try:
        summary = run(args.input, args.output_dir, replace_portfolio=args.replace_portfolio)
    except (ring5.Ring5Error, OSError) as exc:
        print(f"Comparison failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
