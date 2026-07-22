"""Pills-driven settings navigation for plot styling.

Provides a declarative data structure (``SettingsSection``) and a renderer
(``render_settings_pills``) that together power the top-level pills
navigation used in the plot-styling sidebar.

Layout, typography, and legend settings are always visible. The advanced
toggle reveals axes, data labels, colors, and other specialized controls.
"""

from __future__ import annotations

from dataclasses import dataclass

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

    # [impl->req~ring5.extension.settings-panel~1]

    key: str
    label: str
    icon: str
    advanced: bool = False


# Top-level navigation sections

SETTINGS_SECTIONS: list[SettingsSection] = [
    # Basic sections — always visible
    SettingsSection("layout", "Layout", "dashboard"),
    SettingsSection("themes", "Themes", "style"),
    SettingsSection("typography", "Typography", "text_fields"),
    SettingsSection("legends", "Legends", "legend_toggle"),
    # Advanced sections — hidden by default
    SettingsSection("axes", "Axes", "straighten", advanced=True),
    SettingsSection("data_labels", "Data Labels", "label", advanced=True),
    SettingsSection("colors", "Colors", "palette", advanced=True),
    SettingsSection("advanced", "Advanced", "settings", advanced=True),
]


def render_settings_pills(show_advanced: bool = False) -> str | None:
    """Render the top-level pills navigation and return the selected key.

    Parameters
    ----------
    show_advanced : bool
        When ``True``, include sections marked ``advanced=True``.

    Returns
    -------
    str | None
        The ``key`` of the currently selected section, or ``None``
        if nothing is selected.
    """
    # [impl->req~ring5.figure.advanced-disclosure~1]
    # [impl->req~ring5.extension.settings-panel~1]
    # [impl->req~ring5.figure.theme-presets~1]
    visible: list[SettingsSection] = [
        s for s in SETTINGS_SECTIONS if not s.advanced or show_advanced
    ]
    options: list[str] = [s.key for s in visible]
    labels: dict[str, str] = {s.key: f":material/{s.icon}: {s.label}" for s in visible}

    selected: str | None = st.pills(
        "Settings",
        options=options,
        format_func=lambda x: labels[x],
        selection_mode="single",
        key="settings_nav",
    )
    return selected
