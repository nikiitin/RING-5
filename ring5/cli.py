"""The ``ring5`` command line — batch/CI access to the headless workflow.

Subcommands::

    ring5 doctor                          # dependency preflight
    ring5 parse DIR -v simTicks -o out.csv
    ring5 render PORTFOLIO -o figs/       # regenerate every figure
    ring5 recipe-matrix RECIPE -m MATRIX -o out/
    ring5 regression-gate BASE.csv CAND.csv -k benchmark -m ipc
    ring5 upgrade PORTFOLIO               # persist a portfolio at the
                                          # current schema version
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, NoReturn, cast

from ring5.errors import DataValidationError, ExportError, RecipeError, Ring5Error

from src.core.common.security_limits import MAX_ANALYSIS_RECIPE_MATRIX_BYTES

if TYPE_CHECKING:
    import pandas as pd

    from src.core.models import AnalysisRecipeMatrixResult


_INCOMPLETE_REGRESSION_OUTCOMES = frozenset(
    {"missing_baseline", "missing_candidate", "missing_value", "not_comparable"}
)


def _cmd_doctor(args: argparse.Namespace) -> int:
    from ring5._doctor import doctor

    report = doctor()
    print(report)
    # Only a missing required dependency (Perl) makes the command fail; Chrome and XeLaTeX
    # gate optional export formats and shouldn't fail a `ring5 doctor && ...` gate.
    return 0 if report.essential_found else 1


def _cmd_parse(args: argparse.Namespace) -> int:
    # [impl->req~ring5.cli.parse~1]
    from ring5._session import Session

    with Session() as session:
        result = session.parse(
            args.stats_path,
            variables=list(args.variables),
            pattern=args.pattern,
            strict=not args.lenient,
        )
        # Session-owned parse directories are deleted on context exit, so
        # materialize the requested output while the result still exists.
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(result.csv_path, target)
    print(f"wrote {target}")
    if result.missing_stats:
        print(f"warning: no values parsed for: {', '.join(result.missing_stats)}")
    return 0


def _cmd_render(args: argparse.Namespace) -> int:
    # [impl->req~ring5.portfolio.batch-replay~1]
    # [impl->req~ring5.cli.render~1]
    from ring5._portfolio import render_portfolio

    written = render_portfolio(
        args.portfolio,
        args.out_dir,
        engine=args.engine,
        fmt=args.format,
        deterministic=not args.no_deterministic,
    )
    for path in written:
        print(f"wrote {path}")
    return 0


def _cmd_upgrade(args: argparse.Namespace) -> int:
    # [impl->req~ring5.portfolio.upgrade-protection~1]
    from ring5._session import Session

    with Session() as session:
        report = session.load_portfolio(args.portfolio)
        if not report.complete:
            # Re-saving a partial restore would permanently destroy whatever
            # could not be loaded (data, plots, parse variables) — refuse.
            print(
                f"error: refusing to upgrade '{args.portfolio}' — the restore "
                "was incomplete and re-saving would permanently drop:",
                file=sys.stderr,
            )
            for reason in report.plots_skipped:
                print(f"  plot not restored — {reason}", file=sys.stderr)
            if report.data_error:
                print(f"  data not restored — {report.data_error}", file=sys.stderr)
            if report.parse_variables_skipped:
                print(
                    f"  {report.parse_variables_skipped} malformed parse-variable "
                    "entries would be dropped",
                    file=sys.stderr,
                )
            print("fix the portfolio (or this RING-5 version) first", file=sys.stderr)
            return 2
        session.save_portfolio(args.portfolio, overwrite=True)
    print(f"portfolio '{args.portfolio}' re-saved at the current schema version")
    return 0


def _cmd_recipe_matrix(args: argparse.Namespace) -> int:
    # [impl->req~ring5.automation.batch-matrices~1]
    from ring5._session import Session

    recipe_payload = _read_bounded_file(Path(args.recipe), "recipe")
    matrix_payload = _read_bounded_file(Path(args.matrix), "matrix")
    try:
        matrix = json.loads(
            matrix_payload.decode("utf-8"),
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise RecipeError("Recipe matrix must be valid finite UTF-8 JSON.") from exc
    with Session() as session:
        recipe = session.decode_analysis_recipe(recipe_payload)
        result = session.run_analysis_recipe_matrix(
            recipe,
            matrix,
            output_directory=args.output_dir,
            max_workers=args.workers,
        )
    print(json.dumps(_matrix_result_payload(result), indent=2, sort_keys=True))
    return 0 if result.complete else 1


def _read_bounded_file(path: Path, label: str) -> bytes:
    """Read one bounded recipe automation input or raise a public error."""
    try:
        if path.stat().st_size > MAX_ANALYSIS_RECIPE_MATRIX_BYTES:
            raise RecipeError(f"Recipe {label} exceeds the 512 KiB limit.")
        return path.read_bytes()
    except OSError as exc:
        raise RecipeError(f"Could not read recipe {label} {str(path)!r}: {exc}") from exc


def _reject_json_constant(value: str) -> NoReturn:
    raise ValueError(f"Invalid JSON constant {value!r}.")


def _matrix_result_payload(result: "AnalysisRecipeMatrixResult") -> dict[str, Any]:
    """Return the stable JSON summary emitted by the recipe-matrix command."""
    cases: list[dict[str, Any]] = []
    for case in result.cases:
        run = case.result
        cases.append(
            {
                "case_id": case.case_id,
                "status": "completed" if case.successful else "failed",
                "parameters": dict(case.parameter_values),
                "output_directory": case.output_directory,
                "rows": run.rows if run is not None else None,
                "columns": list(run.columns) if run is not None else [],
                "plots": list(run.plot_names) if run is not None else [],
                "exports": list(run.exported_paths) if run is not None else [],
                "error": case.error,
            }
        )
    return {
        "format": "ring5.analysis-recipe-matrix-result",
        "schema_version": 1,
        "recipe": result.recipe_name,
        "complete": result.complete,
        "completed_cases": result.completed_cases,
        "failed_cases": result.failed_cases,
        "max_workers": result.max_workers,
        "output_directory": result.output_directory,
        "cases": cases,
    }


def _cmd_regression_gate(args: argparse.Namespace) -> int:
    """Compare two CSV files and return a stable CI gate status."""
    # [impl->req~ring5.automation.ci-regression-gates~1]
    from ring5._session import Session

    metrics = list(args.metrics)
    directions, thresholds = _regression_gate_configuration(args, metrics)
    with Session() as session:
        baseline = session.load(args.baseline)
        candidate = session.load(args.candidate)
        comparison = cast(
            "pd.DataFrame",
            session.compare(
                baseline,
                candidate,
                list(args.keys),
                metrics,
                directions=directions,
                thresholds=thresholds,
                threshold_mode=args.threshold_mode,
                baseline_name=args.baseline_id or args.baseline,
                candidate_name=args.candidate_id or args.candidate,
            ),
        )
        payload = session.export_regression_results(comparison, args.format)

    _emit_regression_result(payload, args.output)
    outcomes = set(comparison["outcome"].astype(str))
    if outcomes & _INCOMPLETE_REGRESSION_OUTCOMES:
        return 3
    return 1 if "regression" in outcomes else 0


def _regression_gate_configuration(
    args: argparse.Namespace,
    metrics: list[str],
) -> tuple[dict[str, Literal["higher", "lower"]], dict[str, float]]:
    """Resolve global defaults and per-metric CLI assignments."""
    # [impl->req~ring5.automation.ci-regression-gates~1]
    direction_overrides = _metric_assignments(args.directions, metrics, "direction")
    invalid_directions = {
        metric: value
        for metric, value in direction_overrides.items()
        if value not in ("higher", "lower")
    }
    if invalid_directions:
        details = ", ".join(
            f"{metric}={value!r}" for metric, value in sorted(invalid_directions.items())
        )
        raise DataValidationError(f"Invalid metric directions: {details}.")

    threshold_overrides = _metric_assignments(args.thresholds, metrics, "threshold")
    raw_thresholds = {
        metric: threshold_overrides.get(metric, str(args.default_threshold)) for metric in metrics
    }
    try:
        thresholds = {metric: float(value) for metric, value in raw_thresholds.items()}
    except ValueError as exc:
        raise DataValidationError("Thresholds must be finite non-negative numbers.") from exc
    if any(not math.isfinite(value) or value < 0 for value in thresholds.values()):
        raise DataValidationError("Thresholds must be finite non-negative numbers.")

    directions: dict[str, Literal["higher", "lower"]] = {
        metric: cast(
            Literal["higher", "lower"],
            direction_overrides.get(metric, args.default_direction),
        )
        for metric in metrics
    }
    return directions, thresholds


def _metric_assignments(
    entries: list[str],
    metrics: list[str],
    label: str,
) -> dict[str, str]:
    """Parse repeatable ``METRIC=VALUE`` CLI assignments."""
    assignments: dict[str, str] = {}
    for entry in entries:
        metric, separator, value = entry.partition("=")
        if not separator or not metric or not value:
            raise DataValidationError(f"Every {label} override must use METRIC=VALUE.")
        if metric not in metrics:
            raise DataValidationError(f"{label.title()} references unknown metric {metric!r}.")
        if metric in assignments:
            raise DataValidationError(f"Duplicate {label} override for metric {metric!r}.")
        assignments[metric] = value
    return assignments


def _emit_regression_result(payload: bytes, output: str | None) -> None:
    """Write a gate document to stdout or one explicitly requested file."""
    if output is None:
        try:
            sys.stdout.write(payload.decode("utf-8"))
        except OSError as exc:
            raise ExportError(
                f"Could not write regression result to standard output: {exc}"
            ) from exc
        return
    target = Path(output)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    except OSError as exc:
        raise ExportError(f"Could not write regression result {str(target)!r}: {exc}") from exc
    print(f"wrote {target}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Returns:
        The configured top-level argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="ring5",
        description="RING-5 headless workflow: parse gem5 stats, regenerate figures.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    doctor_p = sub.add_parser("doctor", help="check external dependencies")
    doctor_p.set_defaults(func=_cmd_doctor)

    parse_p = sub.add_parser("parse", help="parse a stats tree to a CSV")
    parse_p.add_argument("stats_path", help="directory containing gem5 runs")
    parse_p.add_argument(
        "-v",
        "--variable",
        dest="variables",
        action="append",
        required=True,
        help="stat name to parse (repeatable)",
    )
    parse_p.add_argument("-o", "--output", required=True, help="output CSV path")
    parse_p.add_argument("--pattern", default="stats.txt", help="stats filename pattern")
    parse_p.add_argument(
        "--lenient",
        action="store_true",
        help="do not fail when a requested stat has no values (NaN column instead)",
    )
    parse_p.set_defaults(func=_cmd_parse)

    render_p = sub.add_parser("render", help="regenerate every figure from a saved portfolio")
    render_p.add_argument("portfolio", help="portfolio name (as saved in the app)")
    render_p.add_argument("-o", "--out-dir", required=True, help="output directory")
    render_p.add_argument(
        "--engine",
        choices=("plotly", "matplotlib"),
        default="matplotlib",
        help="rendering engine (default: matplotlib)",
    )
    render_p.add_argument(
        "--format",
        default=None,
        help="export format (default: pdf for matplotlib, html for plotly)",
    )
    render_p.add_argument(
        "--no-deterministic",
        action="store_true",
        help="skip the byte-stable output knobs",
    )
    render_p.set_defaults(func=_cmd_render)

    upgrade_p = sub.add_parser("upgrade", help="re-save a portfolio at the current schema version")
    upgrade_p.add_argument("portfolio", help="portfolio name")
    upgrade_p.set_defaults(func=_cmd_upgrade)

    matrix_p = sub.add_parser(
        "recipe-matrix",
        help="run a recipe across a bounded Cartesian parameter matrix",
    )
    matrix_p.add_argument("recipe", help="portable analysis-recipe JSON file")
    matrix_p.add_argument(
        "-m",
        "--matrix",
        required=True,
        help="JSON object mapping parameter names to ordered value arrays",
    )
    matrix_p.add_argument(
        "-o",
        "--output-dir",
        required=True,
        help="root for deterministic per-case output directories",
    )
    matrix_p.add_argument(
        "-j",
        "--workers",
        type=int,
        default=2,
        help="concurrent cases, from 1 through 8 (default: 2)",
    )
    matrix_p.set_defaults(func=_cmd_recipe_matrix)

    gate_p = sub.add_parser(
        "regression-gate",
        help="compare baseline and candidate CSV metrics for CI",
    )
    gate_p.add_argument("baseline", help="baseline CSV file")
    gate_p.add_argument("candidate", help="candidate CSV file")
    gate_p.add_argument(
        "-k",
        "--key",
        dest="keys",
        action="append",
        required=True,
        help="alignment key column (repeatable)",
    )
    gate_p.add_argument(
        "-m",
        "--metric",
        dest="metrics",
        action="append",
        required=True,
        help="numeric metric column (repeatable)",
    )
    gate_p.add_argument(
        "--default-direction",
        choices=("higher", "lower"),
        default="higher",
        help="preferred direction unless overridden (default: higher)",
    )
    gate_p.add_argument(
        "--direction",
        dest="directions",
        action="append",
        default=[],
        metavar="METRIC=DIRECTION",
        help="per-metric higher/lower override (repeatable)",
    )
    gate_p.add_argument(
        "--default-threshold",
        type=float,
        default=0.0,
        help="non-negative tolerance unless overridden (default: 0)",
    )
    gate_p.add_argument(
        "--threshold",
        dest="thresholds",
        action="append",
        default=[],
        metavar="METRIC=VALUE",
        help="per-metric non-negative tolerance override (repeatable)",
    )
    gate_p.add_argument(
        "--threshold-mode",
        choices=("percentage", "absolute"),
        default="percentage",
        help="unit for every configured threshold (default: percentage)",
    )
    gate_p.add_argument("--baseline-id", default=None, help="baseline source identifier")
    gate_p.add_argument("--candidate-id", default=None, help="candidate source identifier")
    gate_p.add_argument(
        "--format",
        choices=("json", "junit"),
        default="json",
        help="result document format (default: json)",
    )
    gate_p.add_argument("-o", "--output", default=None, help="result file (default: stdout)")
    gate_p.set_defaults(func=_cmd_regression_gate)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the command-line interface.

    Args:
        argv: Arguments without the executable name. Uses ``sys.argv`` when omitted.

    Returns:
        Process-style exit code. Regression gates use zero for a pass, one for
        regressions, two for configuration or execution errors, and three for
        incomplete comparison evidence. Other commands use zero for success,
        one for a negative result, and two for an operational error.
    """
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except Ring5Error as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
