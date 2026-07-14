---
layout: default
title: Web Application
parent: Subsystems
grand_parent: Developer Guide
nav_order: 4
permalink: /developer-guide/subsystems/web/
---

# Web application

`app.py` creates one `ApplicationAPI` per Streamlit browser session, renders sidebar navigation, and
loads only the active page. Page modules compose components, controllers, adapters, and state.

## Components and controllers

Components under `src/web/components/` own `st.*` calls and return user intent as plain values.
Plot controllers under `src/web/controllers/plot/` handle creation, pipeline edits, and rendering.
They depend on protocols in `src/web/models/plot_protocols.py`; adapters in
`src/web/pages/plot_adapters.py` connect current plot services to those protocols.

`src/web/state/ui_state_manager.py` owns transient widget and interaction state. Persistent data,
plots, parser configuration, and history go through `ApplicationAPI` and the core state manager.

## Streamlit rules

- Give widgets stable, per-object keys.
- Use a form when several inputs should commit together and a fragment when a local rerun is safe.
- Use `st.rerun()` after state mutations that must rebuild sibling components.
- Do not cache a mutable per-session API globally.
- Keep business validation in core or parsing services and present typed failures in the component.

Browser workflows belong in `tests/e2e/`; component behavior belongs in `tests/ui_unit/` or
`tests/ui_logic/` when it can be separated from rendering.
