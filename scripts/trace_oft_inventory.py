"""Run native OpenFastTrace over the same current files used for source evidence."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
import subprocess

from scripts.oft_evidence import evidence_source_paths

ROOT = Path(__file__).resolve().parents[1]


def main(argv: Sequence[str] | None = None) -> int:
    """Pass exact current file arguments to Java and return its native exit status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jar", type=Path, required=True, help="Verified native OFT JAR")
    parser.add_argument("--mode", choices=("approved", "all", "html"), required=True)
    parser.add_argument("--output-file", type=Path)
    arguments = parser.parse_args(argv)
    if arguments.mode == "html" and arguments.output_file is None:
        parser.error("--output-file is required for html mode")
    if arguments.mode != "html" and arguments.output_file is not None:
        parser.error("--output-file is only supported in html mode")

    command = ["java", "-jar", str(arguments.jar), "trace"]
    if arguments.mode == "approved":
        command.extend(("-w", "approved", "--v", "summary"))
    elif arguments.mode == "all":
        command.extend(("--v", "summary"))
    else:
        command.extend(
            (
                "--output-format",
                "html",
                "--report-verbosity",
                "all",
                "--details-section-display",
                "collapse",
                "--output-file",
                str(arguments.output_file),
            )
        )
    specifications = (
        ROOT / "spec" / "oft" / "generated" / "features.md",
        ROOT / "spec" / "oft" / "generated" / "requirements.md",
    )
    command.extend(path.relative_to(ROOT).as_posix() for path in specifications)
    command.extend(path.relative_to(ROOT).as_posix() for path in evidence_source_paths(ROOT))
    status = subprocess.run(command, cwd=ROOT, check=False).returncode
    return status if status >= 0 else 128 - status


if __name__ == "__main__":
    raise SystemExit(main())
