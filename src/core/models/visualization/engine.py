"""Canonical rendering-engine vocabulary — the single source of truth.

The engine names, the valid-engine set, and the default engine live here
(Layer A, models) so that both the core domain (e.g. portfolio migration)
and the web rendering layer (``EngineManager``) share one definition with
zero duplication.

Only the *vocabulary* lives here. Session-state management of the active
engine remains a web concern (``src.web.rendering.engine_manager``).
"""

from __future__ import annotations

from typing import Literal

EngineMode = Literal["plotly", "matplotlib"]

VALID_ENGINES: frozenset[str] = frozenset({"plotly", "matplotlib"})

DEFAULT_ENGINE: EngineMode = "plotly"
