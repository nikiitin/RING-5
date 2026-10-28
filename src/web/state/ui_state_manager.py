"""Typed access to namespaced, transient Streamlit session state."""

from dataclasses import dataclass
from typing import Any

import streamlit as st


@dataclass(frozen=True, slots=True)
class _WidgetGenerations:
    """Track the latest reset of each logical widget scope within one plot."""

    counter: int = 0
    scopes: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True, slots=True)
class ParseCompletionNotice:
    """Remember one consumed parse result within its browser session.

    Attributes:
        job_id: Identity of the successfully consumed attempt.
        message: Human-readable description of the loaded or reused result.
        partial: Whether the user explicitly loaded incomplete output.
    """

    job_id: str
    message: str
    partial: bool = False


class WidgetKeyBuilder:
    """Build consistent, namespaced session_state keys.

    Centralizes key construction so that all parts of the web layer
    produce collision-free, predictable key strings.

    Examples::

        WidgetKeyBuilder.plot_key(1, "widgets.auto_refresh")  # "plot.1.widgets.auto_refresh"
        WidgetKeyBuilder.manager_key("mixer", "mode")  # "manager.mixer.mode"
    """

    @staticmethod
    def plot_key(plot_id: int, *parts: str) -> str:
        """Build a plot key whose widget identity changes only after a scoped reset."""
        suffix = "_".join(parts)
        key = f"plot.{plot_id}.{suffix}"
        if suffix.startswith("widgets."):
            generations = st.session_state.get(f"plot.{plot_id}.widget_generations")
            if isinstance(generations, _WidgetGenerations):
                widget = suffix.removeprefix("widgets.")
                generation = max(
                    (
                        value
                        for scope, value in generations.scopes
                        if not scope or widget == scope or widget.startswith(scope + ".")
                    ),
                    default=0,
                )
                if generation:
                    key += f".__reset_{generation}"
        return key

    @staticmethod
    def manager_key(manager: str, *parts: str) -> str:
        """Build a namespaced key for a data manager."""
        return f"manager.{manager}.{'_'.join(parts)}"


def _clear_keys(prefixes: tuple[str, ...]) -> None:
    """Remove only text keys within the given ownership boundaries."""
    for key in list(st.session_state):
        if isinstance(key, str) and key.startswith(prefixes):
            del st.session_state[key]


class _PlotUIState:
    """
    Typed accessors for plot-related UI state.

    Namespaced under ``plot.{plot_id}.*``.
    """

    def get_auto_refresh(self, plot_id: int) -> bool:
        """Get whether auto-refresh is enabled for a plot."""
        return bool(
            st.session_state.get(WidgetKeyBuilder.plot_key(plot_id, "widgets.auto_refresh"), True)
        )

    def reset_widgets(self, plot_id: int, *sections: str) -> None:
        """Discard scoped values and give their next widgets fresh browser identities.

        Native artifacts and transfer notices have separate ownership and remain intact.
        A nested reset preserves sibling controls and the surrounding editor's draft.
        """
        scope = ".".join(sections)
        prefix = WidgetKeyBuilder.plot_key(plot_id, "widgets") + "."
        if scope:
            prefix += scope + "."
        _clear_keys((prefix,))

        state_key = WidgetKeyBuilder.plot_key(plot_id, "widget_generations")
        previous = st.session_state.get(state_key)
        if not isinstance(previous, _WidgetGenerations):
            previous = _WidgetGenerations()
        generation = previous.counter + 1
        # Parent resets supersede child scopes; later child resets remain monotonic.
        scopes = {
            name: value
            for name, value in previous.scopes
            if scope and name != scope and not name.startswith(scope + ".")
        }
        scopes[scope] = generation
        st.session_state[state_key] = _WidgetGenerations(generation, tuple(sorted(scopes.items())))

    def prepare_selector(self, plot_id: int) -> str:
        """Seed a missing plot selector so its current value reaches the browser."""
        key = WidgetKeyBuilder.plot_key(plot_id, "selector")
        if key not in st.session_state:
            st.session_state[key] = plot_id
        return key

    def forget_selector(self, plot_id: int) -> None:
        """Retire only the previous selector after a user changes the active plot."""
        st.session_state.pop(WidgetKeyBuilder.plot_key(plot_id, "selector"), None)

    def cleanup(self, plot_id: int) -> None:
        """Remove this plot's transient state without touching another plot."""
        _clear_keys((f"plot.{plot_id}.",))


class _ManagerUIState:
    """
    Typed accessors for data manager UI state.

    Namespaced under ``manager.{manager_name}.*``.
    """

    def consume_load_trigger(self, manager_name: str) -> dict[str, Any] | None:
        """Get and clear a load trigger (atomic pop)."""
        result: dict[str, Any] | None = st.session_state.pop(
            WidgetKeyBuilder.manager_key(manager_name, "load_trigger"), None
        )
        return result


class _NavUIState:
    """
    Typed accessors for navigation state.

    Namespaced under ``nav.*``.
    """

    def get_current_page(self) -> str | None:
        """Get the currently active page name."""
        result: str | None = st.session_state.get("nav.current_page")
        return result

    def set_current_page(self, page: str) -> None:
        """Set the current page."""
        st.session_state["nav.current_page"] = page


class _ParseUIState:
    """Own the active parse identity and last consumed notice under ``parse.*``."""

    def get_job_id(self) -> str | None:
        """Return the attempt exposed for progress or acknowledgement."""
        value = st.session_state.get("parse.active_job_id")
        return value if isinstance(value, str) else None

    def remember_job(self, job_id: str) -> None:
        """Expose accepted work and clear the previous completion notice."""
        st.session_state["parse.active_job_id"] = job_id
        st.session_state.pop("parse.completion", None)

    def forget_job(self, job_id: str) -> None:
        """Forget only the matching attempt, preserving independently exposed work."""
        if self.get_job_id() == job_id:
            st.session_state.pop("parse.active_job_id", None)

    def get_completion(self) -> ParseCompletionNotice | None:
        """Return the last consumed notice without consuming it on rerender."""
        value = st.session_state.get("parse.completion")
        return value if isinstance(value, ParseCompletionNotice) else None

    def complete_job(self, notice: ParseCompletionNotice) -> None:
        """Retain a consumed result and retire its matching progress identity."""
        self.forget_job(notice.job_id)
        st.session_state["parse.completion"] = notice


class UIStateManager:
    """Own transient plot, manager, navigation and parse state for this session."""

    def __init__(self) -> None:
        """Initialize sub-managers."""
        self.plot: _PlotUIState = _PlotUIState()
        self.manager: _ManagerUIState = _ManagerUIState()
        self.nav: _NavUIState = _NavUIState()
        self.parse: _ParseUIState = _ParseUIState()

    def cleanup_all(self) -> None:
        """Clear workspace widget state, retaining global preferences and browser identity."""
        _clear_keys(("plot.", "manager.", "nav.", "parse."))
