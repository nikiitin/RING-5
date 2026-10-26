"""Dependency preflight — which external binaries are available?

RING-5's optional features need three external binaries; everything else
works with the pip install alone. The probes are instant (no subprocess):

- ``perl``    → stats scanning + parsing
- a Chrome-family browser → plotly png/svg/pdf export (Kaleido)
- the selected TeX compiler → matplotlib PGF export

Zero-dependency paths: plotly HTML export and matplotlib png/svg/pdf.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass

from ring5.errors import ExportError
from src.core.common.browser_selection import select_browser
from src.core.models.visualization.export_options import TexSystem, validate_tex_system


@dataclass(frozen=True)
class DependencyStatus:
    """One binary's executable availability and selected path.

    An unavailable explicit browser selection retains its requested path.
    """

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
    tex_compiler: DependencyStatus

    @property
    def all_found(self) -> bool:
        """Whether every optional and required external dependency is available."""
        return self.perl.found and self.chrome.found and self.tex_compiler.found

    @property
    def essential_found(self) -> bool:
        # [impl->req~ring5.api.doctor~2]
        """Only the dependency required for core parse/render — ``perl``.

        Browser/compiler availability gates optional export formats, so a CLI exit gate
        should not fail merely because they are absent.
        """
        return self.perl.found

    def __str__(self) -> str:
        """Return the diagnostic summary with portable ASCII status and hint labels."""
        lines = ["RING-5 dependency check:"]
        for dep in (self.perl, self.chrome, self.tex_compiler):
            mark = "OK" if dep.found else "MISSING"
            where = dep.path if dep.path is not None else "not found"
            if where == "":
                where = "empty BROWSER_PATH"
            lines.append(f"  [{mark}] {dep.name:<8} {where}  ({dep.needed_for})")
            if not dep.found:
                lines.append(f"      hint: {dep.install_hint}")
        lines.append(
            "  Always available: plotly HTML export, matplotlib png/svg/pdf export, "
            "shapers, portfolios."
        )
        return "\n".join(lines)


def doctor(*, tex_system: TexSystem = "xelatex") -> DoctorReport:
    # [impl->req~ring5.api.doctor~2]
    """Check required Perl and optional browser/selected-compiler availability.

    Args:
        tex_system: PGF compiler: ``xelatex``, ``pdflatex`` or ``lualatex``.

    Returns:
        Availability report without launching a browser, compiler or version probe.

    Raises:
        ExportError: The requested compiler identifier is unsupported.
    """
    try:
        compiler = validate_tex_system(tex_system)
    except ValueError as exc:
        raise ExportError(str(exc)) from exc
    perl_path = shutil.which("perl")
    browser = select_browser()
    compiler_path = shutil.which(compiler)

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
            found=browser.executable_path is not None,
            path=browser.executable_path or browser.selected_path,
            needed_for="plotly png/svg/pdf export",
            install_hint=(
                "Fix or unset an invalid BROWSER_PATH; "
                "run `ring5 install-chrome` and set BROWSER_PATH to its printed path."
            ),
        ),
        tex_compiler=DependencyStatus(
            name=compiler,
            found=compiler_path is not None,
            path=compiler_path,
            needed_for="matplotlib PGF (LaTeX) export",
            install_hint=f"Install a TeX distribution that provides {compiler}.",
        ),
    )
