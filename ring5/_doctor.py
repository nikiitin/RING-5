"""Dependency preflight — which external binaries are available?

RING-5's optional features need three external binaries; everything else
works with the pip install alone. The probes are instant (no subprocess):

- ``perl``    → stats scanning + parsing
- a Chrome-family browser → plotly png/svg/pdf export (Kaleido)
- ``xelatex`` → matplotlib PGF export

Zero-dependency paths: plotly HTML export and matplotlib png/svg/pdf.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass


@dataclass(frozen=True)
class DependencyStatus:
    """One binary's availability."""

    name: str
    found: bool
    path: str | None
    needed_for: str
    install_hint: str


@dataclass(frozen=True)
class DoctorReport:
    """Result of :func:`doctor` — one status per external dependency."""

    perl: DependencyStatus
    chrome: DependencyStatus
    xelatex: DependencyStatus

    @property
    def all_found(self) -> bool:
        """Whether every optional and required external dependency is available."""
        return self.perl.found and self.chrome.found and self.xelatex.found

    @property
    def essential_found(self) -> bool:
        """Only the dependency required for core parse/render — ``perl``.

        chrome/xelatex gate *optional* export formats, so a CLI exit gate should not fail
        merely because they are absent.
        """
        return self.perl.found

    def __str__(self) -> str:
        lines = ["RING-5 dependency check:"]
        for dep in (self.perl, self.chrome, self.xelatex):
            mark = "✓" if dep.found else "✗"
            where = dep.path or "not found"
            lines.append(f"  {mark} {dep.name:<8} {where}  ({dep.needed_for})")
            if not dep.found:
                lines.append(f"      → {dep.install_hint}")
        lines.append(
            "  Always available: plotly HTML export, matplotlib png/svg/pdf export, "
            "shapers, portfolios."
        )
        return "\n".join(lines)


def _find_chrome() -> str | None:
    """Locate a Chrome-family browser the way Kaleido will.

    Kaleido v1 resolves its browser through choreographer: a previously
    downloaded local Chrome, the ``BROWSER_PATH`` override, PATH, then the
    usual install locations. ``find_browser`` performs that exact lookup
    instantly (no subprocess).
    """
    try:
        from choreographer.browsers.chromium import Chromium

        found = Chromium.find_browser(skip_local=False)
        return str(found) if found else None
    except Exception:
        # choreographer internals moved — fall back to a PATH sweep over the
        # same executable names it checks.
        for name in ("chrome", "chromium", "chromium-browser", "google-chrome"):
            path = shutil.which(name)
            if path:
                return path
        return None


def doctor() -> DoctorReport:
    """Run the three instant dependency probes and return a report.

    ``print(ring5.doctor())`` gives the human-readable summary.
    """
    perl_path = shutil.which("perl")
    chrome_path = _find_chrome()
    xelatex_path = shutil.which("xelatex")

    return DoctorReport(
        perl=DependencyStatus(
            name="perl",
            found=perl_path is not None,
            path=perl_path,
            needed_for="stats scanning + parsing",
            install_hint="Install perl via your distro package manager.",
        ),
        chrome=DependencyStatus(
            name="chrome",
            found=chrome_path is not None,
            path=chrome_path,
            needed_for="plotly png/svg/pdf export",
            install_hint="Run `kaleido_get_chrome` or set BROWSER_PATH.",
        ),
        xelatex=DependencyStatus(
            name="xelatex",
            found=xelatex_path is not None,
            path=xelatex_path,
            needed_for="matplotlib PGF (LaTeX) export",
            install_hint="Install TeX (e.g. `make install-latex` or texlive-xetex).",
        ),
    )
