"""Pills-driven settings navigation for plot styling.

Provides a declarative data structure (``SettingsSection``) and a renderer
(``render_settings_pills``) that together power the top-level pills
navigation used in the plot-styling sidebar.

Sections are split into *basic* (always visible) and *advanced* (hidden
behind a progressive-disclosure toggle), keeping the UI clean for common
workflows while still exposing every knob when needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import streamlit as st


@dataclass(frozen=True)
class SettingsSection:
    """A settings section accessible via pills navigation.

    Attributes
    ----------
    key : str
        Machine-readable identifier used as the pills option value and
        for session-state routing.
    label : str
        Human-readable display name shown in the pill.
    icon : str
        Material-icon name (without the ``material/`` prefix).
    advanced : bool
        When ``True`` the section is hidden unless the user explicitly
        enables advanced mode (progressive disclosure).
    """

    key: str
    label: str
    icon: str
    advanced: bool = False


# ------------------------------------------------------------------
# Top-level navigation sections
# ------------------------------------------------------------------

SETTINGS_SECTIONS: List[SettingsSection] = [
    # Basic sections — always visible
    SettingsSection("layout", "Layout", "dashboard"),
    SettingsSection("typography", "Typography", "text_fields"),
    SettingsSection("legends", "Legends", "legend_toggle"),
    # Advanced sections — hidden by default
    SettingsSection("axes", "Axes", "straighten", advanced=True),
    SettingsSection("data_labels", "Data Labels", "label", advanced=True),
    SettingsSection("colors", "Colors", "palette", advanced=True),
    SettingsSection("advanced", "Advanced", "tune", advanced=True),
]


def render_settings_pills(show_advanced: bool = False) -> Optional[str]:
    """Render the top-level pills navigation and return the selected key.

    Parameters
    ----------
    show_advanced : bool
        When ``True``, include sections marked ``advanced=True``.

    Returns
    -------
    Optional[str]
        The ``key`` of the currently selected section, or ``None``
        if nothing is selected.
    """
    visible: List[SettingsSection] = [
        s for s in SETTINGS_SECTIONS if not s.advanced or show_advanced
    ]
    options: List[str] = [s.key for s in visible]
    labels: dict[str, str] = {s.key: f":material/{s.icon}: {s.label}" for s in visible}

    selected: Optional[str] = st.pills(
        "Settings",
        options=options,
        format_func=lambda x: labels[x],
        selection_mode="single",
        key="settings_nav",
    )
    return selected
