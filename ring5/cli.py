"""The ``ring5`` command line — batch/CI access to the headless workflow.

Subcommands::

    ring5 doctor                          # dependency preflight
    ring5 parse DIR -v simTicks -o out.csv
    ring5 render PORTFOLIO -o figs/       # regenerate every figure
    ring5 upgrade PORTFOLIO               # persist a portfolio at the
                                          # current schema version
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from ring5.errors import Ring5Error


def _cmd_doctor(args: argparse.Namespace) -> int:
    from ring5._doctor import doctor

    report = doctor()
    print(report)
    # Exit non-zero only when an ESSENTIAL dependency (perl) is missing; chrome/xelatex
    # gate optional export formats and shouldn't fail a `ring5 doctor && ...` gate.
    return 0 if report.essential_found else 1


def _cmd_parse(args: argparse.Namespace) -> int:
    from ring5._session import Session

    with Session() as session:
        result = session.parse(
            args.stats_path,
            variables=list(args.variables),
            pattern=args.pattern,
            strict=not args.lenient,
        )
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(result.csv_path, target)
    print(f"wrote {target}")
    if result.missing_stats:
        print(f"warning: no values parsed for: {', '.join(result.missing_stats)}")
    return 0


def _cmd_render(args: argparse.Namespace) -> int:
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


def build_parser() -> argparse.ArgumentParser:
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

    return parser


def main(argv: list[str] | None = None) -> int:
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
