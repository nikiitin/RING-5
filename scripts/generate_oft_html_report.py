#!/usr/bin/env python3
"""Add a feature summary and filters to a native OpenFastTrace HTML report."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import json
from pathlib import Path
from typing import Any, cast

if __package__:
    from scripts.generate_oft_inventory import load_inventory, validate_inventory
    from scripts.oft_evidence import collect_evidence_markers
    from scripts.oft_html_report import OftHtmlReportError, enhance_oft_html
else:
    from generate_oft_inventory import load_inventory, validate_inventory
    from oft_evidence import collect_evidence_markers
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
    parser.add_argument(
        "--execution-results",
        type=Path,
        help="optional per-requirement passed, failed, or not-run JSON results",
    )
    return parser


def load_execution_results(path: Path, inventory: Mapping[str, Any]) -> dict[str, str]:
    """Load a bounded, versioned per-requirement execution result document."""
    # [impl->req~ring5.trace.readiness-checklist~1]
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not load execution results {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise ValueError("Execution results must contain a JSON object.")
    if document.get("format") != "ring5.oft-execution-results":
        raise ValueError("Execution results use an unsupported format.")
    if document.get("schema_version") != 1:
        raise ValueError("Execution results use an unsupported schema version.")
    results = document.get("requirements")
    if not isinstance(results, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in results.items()
    ):
        raise ValueError("Execution requirements must map IDs to string statuses.")
    result_map = cast(dict[str, str], results)
    allowed = {"passed", "failed", "not-run"}
    invalid = sorted(key for key, value in result_map.items() if value not in allowed)
    if invalid:
        raise ValueError("Invalid execution statuses for: " + ", ".join(invalid))
    features = cast(list[dict[str, Any]], inventory["features"])
    unexpected = sorted(set(result_map) - {str(feature["id"]) for feature in features})
    if unexpected:
        raise ValueError("Unknown execution requirement IDs: " + ", ".join(unexpected))
    return dict(sorted(result_map.items()))


def main(argv: list[str] | None = None) -> int:
    """Generate the enhanced report and return a process-style status code."""
    # [impl->req~ring5.trace.human-html-report~1]
    args = build_parser().parse_args(argv)
    try:
        inventory = load_inventory(args.inventory)
        validate_inventory(inventory)
        execution_results = (
            load_execution_results(args.execution_results, inventory)
            if args.execution_results
            else {}
        )
        native_html = args.oft_html.read_text(encoding="utf-8")
        repository_root = args.inventory.resolve().parents[2]
        evidence_markers = collect_evidence_markers(repository_root)
        report = enhance_oft_html(
            native_html,
            inventory,
            evidence_markers,
            execution_results,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    except (OSError, OftHtmlReportError, ValueError) as exc:
        print(f"error: {exc}")
        return 2
    print(f"generated OFT HTML report at {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
