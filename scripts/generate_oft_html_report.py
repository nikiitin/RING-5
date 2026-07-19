#!/usr/bin/env python3
"""Add a feature summary and filters to a native OpenFastTrace HTML report."""

from __future__ import annotations

import argparse
from pathlib import Path

if __package__:
    from scripts.generate_oft_inventory import load_inventory, validate_inventory
    from scripts.oft_html_report import OftHtmlReportError, enhance_oft_html
else:
    from generate_oft_inventory import load_inventory, validate_inventory
    from oft_html_report import OftHtmlReportError, enhance_oft_html


def build_parser() -> argparse.ArgumentParser:
    """Build the report generator command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--oft-html", type=Path, required=True, help="native OFT HTML input")
    parser.add_argument("--output", type=Path, required=True, help="enhanced report output")
    parser.add_argument(
        "--inventory",
        type=Path,
        default=Path("spec/oft/inventory.json"),
        help="validated inventory used for human labels and filters",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Generate the enhanced report and return a process-style status code."""
    args = build_parser().parse_args(argv)
    try:
        inventory = load_inventory(args.inventory)
        validate_inventory(inventory)
        native_html = args.oft_html.read_text(encoding="utf-8")
        report = enhance_oft_html(native_html, inventory)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    except (OSError, OftHtmlReportError, ValueError) as exc:
        print(f"error: {exc}")
        return 2
    print(f"generated OFT HTML report at {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
