"""``ring5.Table`` — a small, opaque public data handle for figure scripts.

The goal is **self-containment**: a script imports only ``ring5`` and never ``pandas``.
``Table`` wraps a :class:`pandas.DataFrame` (this module lives in the ``ring5/`` composition
root, which is allowed to import pandas / ``src.*``) and exposes just the data operations the
publication figures need — CSV/round-trip I/O, row access as plain-Python dicts, a few
column transforms, running a RING-5 shaper, and extracting the value maps the over-cap
labels need.

Design notes:

* **Opaque to the caller.** Scripts treat a ``Table`` as a handle; figure-specific math
  (string concat, group-cardinality filters, baseline ratios) is done in *pure Python* over
  :meth:`Table.rows` (stdlib only — never pandas/numpy), then handed back via
  :meth:`Table.from_rows`.
* **Byte-identical by construction.** Every method that touches numbers delegates to the
  *exact* pandas operation the scripts used before this facade existed (e.g.
  :meth:`sum_map` calls ``df[cols].sum(axis=1)``), so migrated figures render identically.
* **Immutable-style.** Transforms return a *new* ``Table`` (RING-5 forbids ``inplace=True``);
  the wrapped frame is copied defensively on the way in and out.

``Session.create_plot`` and ``Session.reduce_seeds`` accept a ``Table`` directly (and
``reduce_seeds`` returns one), so a script never has to unwrap ``.frame`` by hand.
"""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd

__all__ = ["Table", "read_table"]

# A shaper is any callable that maps a DataFrame to a DataFrame (e.g. ``ring5.shapers.Mean``).
Shaper = Callable[[pd.DataFrame], pd.DataFrame]


def _to_py(value: Any) -> Any:
    """Coerce a pandas/numpy scalar to a native Python scalar (no numpy leaks to scripts)."""
    item = getattr(value, "item", None)
    return item() if callable(item) else value


class Table:
    """An opaque, immutable-style table of figure data (wraps a pandas DataFrame)."""

    __slots__ = ("_df",)

    def __init__(self, frame: pd.DataFrame) -> None:
        # Defensive copy so the Table owns its data and callers can't mutate it underneath.
        self._df = frame.copy()

    # ── constructors ─────────────────────────────────────────────────────
    @classmethod
    def from_csv(cls, path: str) -> "Table":
        """Read a CSV into a Table (same parse as the old ``pd.read_csv``)."""
        return cls(pd.read_csv(path))

    @classmethod
    def from_rows(cls, rows: list[dict[str, Any]]) -> "Table":
        """Build a Table from a list of row dicts (column order follows first-seen keys)."""
        return cls(pd.DataFrame(rows))

    # ── introspection ────────────────────────────────────────────────────
    @property
    def frame(self) -> pd.DataFrame:
        """The underlying DataFrame (a copy) — the engine handoff for ``create_plot``."""
        return self._df.copy()

    @property
    def is_empty(self) -> bool:
        return self._df.empty

    def __len__(self) -> int:
        return len(self._df)

    def columns(self) -> list[str]:
        return list(self._df.columns)

    def rows(self) -> list[dict[str, Any]]:
        """All rows as plain-Python dicts (numeric cells coerced to ``float``/``int``).

        This is the seam for figure-specific math: iterate these dicts with the stdlib and
        build new rows, then return them via :meth:`from_rows`. No pandas/numpy escapes.
        """
        return [{str(k): _to_py(v) for k, v in rec.items()} for rec in self._df.to_dict("records")]

    # ── I/O ──────────────────────────────────────────────────────────────
    def to_csv(self, path: str) -> str:
        """Write the table to ``path`` (no index column) and return ``path``."""
        self._df.to_csv(path, index=False)
        return path

    # ── transforms (return a new Table) ──────────────────────────────────
    def filter_eq(self, column: str, value: Any) -> "Table":
        """Rows where ``column == value`` (index reset)."""
        return Table(self._df[self._df[column] == value].reset_index(drop=True))

    def sort(self, by: list[str]) -> "Table":
        """Stable sort by the given columns (index reset)."""
        return Table(self._df.sort_values(by).reset_index(drop=True))

    def with_scalar_op(self, new_column: str, src_column: str, op: str, value: float) -> "Table":
        """Add ``new_column = src_column <op> value`` for op in ``+ - * /``.

        Delegates to the ``deriveColumn`` shaper so the column-scalar arithmetic lives in
        exactly one place (no drift between the Table facade and the shaper).
        """
        from src.core.services.shapers.impl.derive_column import DeriveColumn

        return self.apply(
            DeriveColumn(
                {
                    "type": "deriveColumn",
                    "op": "scalar",
                    "dest": new_column,
                    "sources": [src_column],
                    "scalar_op": op,
                    "scalar": value,
                }
            )
        )

    def apply(self, shaper: Shaper) -> "Table":
        """Run a RING-5 shaper (e.g. ``ring5.shapers.Mean(cfg)``) and return a new Table."""
        return Table(shaper(self._df))

    def concat(self, other: "Table") -> "Table":
        """Append another Table's rows (``pd.concat(..., ignore_index=True)``)."""
        return Table(pd.concat([self._df, other._df], ignore_index=True))

    # ── value extraction (for over-cap / dot labels) ─────────────────────
    def value_map(self, key_columns: list[str], value_column: str) -> dict[tuple, float]:
        """``{(key_columns…): float(value_column)}`` over every row."""
        cols = self._df
        return {
            tuple(cols[c].iloc[i] for c in key_columns): float(cols[value_column].iloc[i])
            for i in range(len(cols))
        }

    def sum_map(self, key_columns: list[str], sum_columns: list[str]) -> dict[tuple, float]:
        """``{(key_columns…): float(sum of sum_columns)}`` — the over-cap bar totals.

        Uses ``df[sum_columns].sum(axis=1)`` so totals match the pre-facade values exactly.
        """
        totals = self._df[sum_columns].sum(axis=1)
        cols = self._df
        return {
            tuple(cols[c].iloc[i] for c in key_columns): float(totals.iloc[i])
            for i in range(len(cols))
        }


def read_table(path: str) -> Table:
    """Read a CSV file into a :class:`Table` (the public entry point for figure data)."""
    return Table.from_csv(path)
