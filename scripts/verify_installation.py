#!/usr/bin/env python3
"""Check the installed public API and report optional export dependencies."""

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import ring5


def _verify_chrome_publication(directory: Path) -> None:
    """Check native exclusive publication with tiny inert directories only."""
    from ring5._chrome_install import _publish_noreplace

    source = directory / "publication-source"
    source.mkdir()
    (source / "inert.txt").write_text("inert publication fixture", encoding="utf-8")
    published = directory / "publication-success"
    _publish_noreplace(source, published)
    foreign = directory / "publication-foreign"
    foreign.mkdir()
    original = foreign.stat()
    try:
        _publish_noreplace(published, foreign)
    except FileExistsError:
        pass
    else:
        raise ring5.Ring5Error("Exclusive Chrome publication replaced a foreign directory.")
    current = foreign.stat()
    if (current.st_dev, current.st_ino) != (original.st_dev, original.st_ino) or list(
        foreign.iterdir()
    ):
        raise ring5.Ring5Error("Exclusive Chrome publication changed a foreign directory.")
    if (published / "inert.txt").read_text(encoding="utf-8") != "inert publication fixture":
        raise ring5.Ring5Error("Exclusive Chrome publication did not preserve its source.")


def main() -> int:
    """Exercise a headless CSV workflow and return its process exit status."""
    print(ring5.doctor())
    try:
        from ring5._chrome_install import _load_manifest

        # The wheel must carry the same reviewed installer inputs as a checkout.
        _load_manifest()
        with TemporaryDirectory(prefix="ring5-check-") as directory, ring5.Session() as session:
            _verify_chrome_publication(Path(directory))
            csv_path = Path(directory) / "input.csv"
            csv_path.write_text("benchmark,ipc\nexample,1.5\n", encoding="utf-8")
            table = session.load(str(csv_path))
            figure = session.plot(
                "bar",
                data=table,
                config=ring5.FigureSpec(x="benchmark", y_columns=["ipc"]),
                engine="matplotlib",
            )
            result = session.export_bytes(figure, "svg")
            if b"<svg" not in result:
                print("SVG export did not contain a figure.", file=sys.stderr)
                return 1
    except (ring5.Ring5Error, OSError, ValueError, TypeError) as exc:
        print(f"Installation check failed: {exc}", file=sys.stderr)
        return 1
    print("Public CSV, plotting, and SVG export workflow passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
