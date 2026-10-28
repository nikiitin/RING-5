"""Parse a gem5 results tree while retaining typed output and source provenance."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import ring5

DEFAULT_STATS = Path(__file__).resolve().parents[1] / "data" / "gem5"


def run(stats_path: Path, variables: list[str], output_dir: Path, *, strategy: str) -> dict:
    """Parse requested statistics and write their public table representation."""
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("RING5_DATA_DIR", str(output_dir / "workspace"))
    with ring5.Session() as session:
        result = session.parse(
            str(stats_path.resolve()),
            variables=variables,
            strategy=strategy,
            scan_limit=0,
            output_dir=str(output_dir / "parsed"),
        )
        data = session.load(result)
        data.to_csv(str(output_dir / "measurements.csv"))
        summary = {
            "parsed_files": result.parsed_files,
            "missing_stats": list(result.missing_stats),
            "columns": data.columns(),
            "rows": data.rows(),
            "parser_csv": result.csv_path,
        }
    (output_dir / "analysis.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return summary


def main() -> int:
    """Run the parser example; Perl is required."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stats_path", type=Path, nargs="?", default=DEFAULT_STATS)
    parser.add_argument("--variable", action="append", dest="variables")
    parser.add_argument("--strategy", choices=("simple", "config_aware"), default="simple")
    parser.add_argument("--output-dir", type=Path, default=Path("example-output/parser"))
    args = parser.parse_args()
    try:
        summary = run(
            args.stats_path,
            args.variables or ["simTicks", "system.cpu.ipc"],
            args.output_dir,
            strategy=args.strategy,
        )
    except (ring5.Ring5Error, OSError) as exc:
        print(f"Parsing failed: {exc}", file=sys.stderr)
        return 1
    finally:
        ring5.shutdown()
    print(json.dumps(summary, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
