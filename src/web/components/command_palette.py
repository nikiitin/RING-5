"""Human-first command palette and keyboard shortcut bridge."""

from __future__ import annotations

import json

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.core.models import WorkspaceCommand

_NAVIGATION_PAGES = frozenset(
    {"Data Source", "Data Managers", "Manage Plots", "Save/Load Portfolio", "Documentation"}
)
_NAVIGATION_SHORTCUTS = {
    "1": "Data Source",
    "2": "Data Managers",
    "3": "Manage Plots",
    "4": "Save/Load Portfolio",
    "5": "Documentation",
}


class CommandPaletteComponent:
    """Render safe registered commands and install their visible shortcuts."""

    @classmethod
    def render(cls, api: ApplicationAPI) -> None:
        """Render the palette launcher and the application shortcut bridge."""
        # [impl->req~ring5.workspace.command-palette~1]
        if st.button(
            "Command palette",
            key="_open_command_palette",
            width="stretch",
            type="tertiary",
            help="Search commands · Ctrl/⌘+K",
        ):
            st.session_state["_command_palette_focus_pending"] = True
            cls._open_dialog(api)
        focus_search = bool(st.session_state.pop("_workspace_search_focus_pending", False))
        focus_palette = bool(st.session_state.pop("_command_palette_focus_pending", False))
        cls._install_shortcut_bridge(
            focus_search=focus_search,
            focus_palette=focus_palette,
        )

    @classmethod
    def _open_dialog(cls, api: ApplicationAPI) -> None:
        @st.dialog("Command palette", width="large")
        def _dialog() -> None:
            cls.render_dialog(api)

        _dialog()

    @classmethod
    def render_dialog(cls, api: ApplicationAPI) -> None:
        """Render searchable command results inside an open dialog."""
        query = st.text_input(
            "Search commands",
            key="_command_palette_query",
            placeholder="Type a task or destination…",
        )
        try:
            response = api.search_workspace_commands(query, limit=20)
        except (TypeError, ValueError) as exc:
            st.error(f"Commands are unavailable: {exc}")
            return

        if not response.commands:
            st.info("No matching commands. Try a page name or task such as plot, data, or help.")
        else:
            match_label = "command" if response.total_matches == 1 else "commands"
            st.caption(f"{response.total_matches} {match_label}")
            for command in response.commands:
                shortcut = f" · {', '.join(command.shortcuts)}" if command.shortcuts else ""
                if st.button(
                    f"{command.title}{shortcut}",
                    key=f"command_palette_{command.command_id}",
                    width="stretch",
                    type="tertiary",
                    help=command.description,
                ):
                    cls.activate(command)
                    st.rerun()
                st.caption(command.description)

        with st.expander("Keyboard shortcuts"):
            st.markdown("""
- **Ctrl/⌘+K** — open this command palette
- **/** — focus workspace search when you are not typing
- **Alt+1 … Alt+5** — open the five sidebar pages in order
- **Esc** — close the palette
""")

    @staticmethod
    def activate(command: WorkspaceCommand) -> None:
        """Apply one validated command to Streamlit session state."""
        # [impl->req~ring5.workspace.command-palette~1]
        if not isinstance(command, WorkspaceCommand):
            raise TypeError("Command palette entries must be WorkspaceCommand instances.")
        if command.action == "navigate":
            if command.destination not in _NAVIGATION_PAGES:
                raise ValueError(f"Unsupported workspace destination {command.destination!r}.")
            st.session_state["_nav_page"] = command.destination
            return
        if command.action == "focus_workspace_search":
            st.session_state["_workspace_search_requested"] = True
            st.session_state["_workspace_search_focus_pending"] = True
            return
        raise ValueError(f"Unsupported workspace command action {command.action!r}.")

    @staticmethod
    def _install_shortcut_bridge(*, focus_search: bool, focus_palette: bool) -> None:
        """Install one parent-document handler from the trusted application shell."""
        # [impl->req~ring5.workspace.command-palette~1]
        payload = json.dumps(_NAVIGATION_SHORTCUTS, sort_keys=True)
        st.iframe(
            f"""
<script>
(() => {{
  const host = window.parent;
  const doc = host.document;
  const navigation = {payload};
  const buttonNamed = (label) => Array.from(doc.querySelectorAll("button"))
    .find((button) => button.innerText.trim() === label);
  const retryFocus = (selector, attempts = 20) => {{
    const input = doc.querySelector(selector);
    if (input && input.getClientRects().length > 0) {{
      input.focus();
      if (doc.activeElement === input) return;
    }}
    if (attempts > 0) host.setTimeout(() => retryFocus(selector, attempts - 1), 50);
  }};
  const focusSearch = () => {{
    const expander = Array.from(doc.querySelectorAll('[data-testid="stExpander"]'))
      .find((item) => item.innerText.includes("Search workspace"));
    if (expander && !expander.hasAttribute("open")) expander.querySelector("summary")?.click();
    retryFocus('input[placeholder="Type two or more letters…"]');
  }};
  const openPalette = () => {{
    buttonNamed("Command palette")?.click();
    retryFocus('input[placeholder="Type a task or destination…"]');
  }};
  if (host.__ring5ShortcutHandler) {{
    doc.removeEventListener("keydown", host.__ring5ShortcutHandler, true);
  }}
  host.__ring5ShortcutHandler = (event) => {{
    const key = event.key.toLowerCase();
    const active = doc.activeElement;
    const isTyping = active && (
      active.tagName === "INPUT" || active.tagName === "TEXTAREA" ||
      active.tagName === "SELECT" || active.isContentEditable
    );
    if ((event.ctrlKey || event.metaKey) && key === "k") {{
      event.preventDefault();
      event.stopPropagation();
      openPalette();
      return;
    }}
    if (isTyping) return;
    if (!event.ctrlKey && !event.metaKey && !event.altKey && key === "/") {{
      event.preventDefault();
      focusSearch();
      return;
    }}
    if (event.altKey && !event.ctrlKey && !event.metaKey && navigation[key]) {{
      event.preventDefault();
      buttonNamed(navigation[key])?.click();
    }}
  }};
  doc.addEventListener("keydown", host.__ring5ShortcutHandler, true);
  if ({str(focus_search).lower()}) host.setTimeout(focusSearch, 50);
  if ({str(focus_palette).lower()}) host.setTimeout(
    () => retryFocus('input[placeholder="Type a task or destination…"]'), 50
  );
}})();
</script>
""",
            height=1,
        )
