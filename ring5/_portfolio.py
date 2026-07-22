"""Portfolio replay — regenerate every figure from a saved snapshot.

The reproducibility workflow: a portfolio carries the data and full plot
configs, so a single call (or ``ring5 render`` from the shell) rebuilds
every figure file headlessly, years later, without the web app.
"""

from __future__ import annotations

from pathlib import Path

from src.core.common.utils import sanitize_filename
from src.core.models.visualization.engine import EngineMode

from ring5._session import Session
from ring5.errors import PortfolioError, Ring5Error

_DEFAULT_FMT: dict[str, str] = {"plotly": "html", "matplotlib": "pdf"}


def render_portfolio(
    name: str,
    out_dir: str,
    *,
    engine: EngineMode = "matplotlib",
    fmt: str | None = None,
    deterministic: bool = True,
) -> list[str]:
    # [impl->req~ring5.portfolio.batch-replay~1]
    """Restore portfolio *name* and export every plot to *out_dir*.

    Args:
        name: Portfolio name (as saved from the app or a Session).
        out_dir: Output directory (created if needed).
        engine: Rendering engine; matplotlib is the publication default.
        fmt: Export format; defaults per engine (matplotlib → ``pdf``,
            plotly → ``html`` — the zero-dependency formats).
        deterministic: Byte-stable exports (CI/regression friendly).

    Returns:
        The written file paths, one per restored plot.

    Raises:
        PortfolioError: Portfolio missing, no plots restored, or a plot
            failed to render/export (with the plot name in the message).
        PortfolioVersionError: Written by a newer RING-5.
    """
    # Validate the engine up front (typed error, before the expensive load) rather than
    # letting a bad key raise a raw KeyError on the _DEFAULT_FMT subscript below.
    if engine not in _DEFAULT_FMT:
        raise PortfolioError(f"Unknown engine {engine!r}; choose from {sorted(_DEFAULT_FMT)}.")
    with Session() as session:
        report = session.load_portfolio(name)

        plots = session.plots
        if not plots:
            skipped = "; ".join(report.plots_skipped) or "portfolio contains no plots"
            raise PortfolioError(f"No plots restored from '{name}': {skipped}")

        effective_fmt = fmt or _DEFAULT_FMT[engine]
        out = Path(out_dir)
        written: list[str] = []
        used_names: set[str] = set()
        for plot in plots:
            # Plot names are free-form and may collide after sanitization —
            # disambiguate with the (unique) plot id instead of overwriting.
            stem = sanitize_filename(plot.name)
            if stem in used_names:
                stem = f"{stem}_{plot.plot_id}"
            used_names.add(stem)
            target = out / f"{stem}.{effective_fmt}"
            try:
                fig = session.render(plot, engine=engine)
                written.append(session.export(fig, str(target), deterministic=deterministic))
            except (OSError, ValueError, Ring5Error) as exc:
                raise PortfolioError(
                    f"Rendering plot '{plot.name}' from portfolio '{name}' failed: {exc}"
                ) from exc
        return written
