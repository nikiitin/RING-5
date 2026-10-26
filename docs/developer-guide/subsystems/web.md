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
loads only the active page. The four destinations are Data Source, Data Managers, Manage Plots,
and Save/Load Portfolio. Navigation tests activate their sidebar buttons and verify the selected
destination. Page modules compose components, controllers, adapters, and state.

## Components and controllers

Components under `src/web/components/` own `st.*` calls and return user intent as plain values.
Plot controllers under `src/web/controllers/plot/` handle creation, pipeline edits, and rendering.
They depend on protocols in `src/web/models/plot_protocols.py`; adapters in
`src/web/pages/plot_adapters.py` connect current plot services to those protocols.

Editable `PlotConfig` mappings live in `src/core/models/plot_config.py` and accept registered
plot-specific fields. Rendering resolves them into the typed `FigureConfig` and visualization
submodels in core. The web models package owns structural interaction protocols.

`src/web/state/ui_state_manager.py` owns transient widget and interaction state. Persistent data,
plots, parser configuration, and history go through `ApplicationAPI` and the core state manager.

`WidgetKeyBuilder.plot_key` constructs `plot.<id>.*` keys. Plot controls and pipeline editors use
`plot.<id>.widgets.*`; appearance controls use `plot.<id>.widgets.appearance.*`. Theme exchange
controls stay in `widgets.theme.*`, so applying a theme resets appearance without clearing the
controls handling that action. Nested pipeline editors retain their shaper and group identities
within the owning plot's namespace.

`UIStateManager.plot.reset_widgets` clears one plot's widgets or a named widget section. Copying
configuration schedules this reset before the destination's next controls render; the updated plot
configuration supplies their defaults. Shape edits retain one typed UI draft against the published
shape list, so adding, deleting or resizing a shape survives manual-refresh mode and settings
navigation. Deletion resets shifted row controls before their next render. Plot deletion uses
`plot.cleanup`, while workspace reset and restoration use `cleanup_all`.
These operations preserve other plots and global preferences within their defined scope. Native
figure disposal belongs to the render owner. Navigation uses `nav.current_page` through the typed
navigation accessor; data-manager history requests use `manager.<name>.load_trigger`.

## Native artifact ownership

The controller collects a detached configuration candidate and chooses the engine before checking
its reuse identity. A cache hit displays the published artifact without preparing, building or
resolving it again. Manual refresh forces one new build. Successful publication installs effective
configuration, native figure, real preparation metadata and key together; failures preserve the
previous generation. Composite artifacts retain the actual preparation of every facet panel.

Chart display and downloads consume that same artifact. Matplotlib figures and specifications are
not duplicated in session state. Downloads use the artifact's engine and configured export scale.
Plot configuration reads are defensive snapshots; configuration changes use complete assignment.

Native Matplotlib builds, panel composition, reports, export snapshots and byte exports share one
reentrant operation lock. It protects temporary global settings, including fonts and the PGF
compiler, until each operation restores them. Direct connector entry points use the same lock;
background exports wait for active native work before saving.

## Plot settings

Plot configuration has two entry points: `render_config_ui` selects data mappings, and
`render_settings_section` dispatches the active settings pill to its component under
`src/web/components/plotting/settings/`. Plot-specific advanced controls use
`render_specific_advanced_options`. Components return a fresh configuration fragment; they must not
mutate the saved configuration or its nested series styles.

Plot-specific option controls share `saved_option_label` from `settings/widget_factory.py` to
resolve a display label from a stored value. Each control supplies its own labels and default;
the shared lookup preserves the serialized value and chooses the first matching label.

Each control has one owner. Layout owns grouped-bar separators, shading, and isolation spacing;
Typography owns fonts; Axes owns placement, ordering, and right-axis trace controls; Legends owns
trace and numbered-legend tiers; Data Labels owns value labels and independent totals; Colors owns
series styling. The style classes expose only `render_series_visuals` and their type-specific
marker or pattern hook.

`numbered_xaxis_modes` is the shared numbered-axis representation. Its value is a list of unique
strings chosen from `Numbers`, `Number legend`, and `Labels`. An absent key leaves the setting
unspecified; an empty list explicitly disables numbering. Public figure configuration, saved-plot
restoration, and widgets validate the same contract in `src/core/common/numbered_axis.py`. Numbered
annotation font sizes use the typed figure builder and common inheritance resolver before either
renderer receives them.

The numbered-axis widget appears only for grouped-stacked bars. Public requests for other built-in
families reject a nonempty mode list before registering a plot; absent and empty lists remain valid
generic defaults. Runtime plot registration retains its own configuration behavior.

The Matplotlib trace result carries raw categorical bar positions separately from displayed tick
labels. Annotation placement uses those positions, so ordering and display aliases cannot detach a
stack total from its bar. Explicit category orders retain unlisted categories in encounter order.

## Streamlit rules

- Give widgets stable, per-object keys.
- Read auto-refresh from its actual toggle; do not assign to its widget key after rendering it.
- Use a form when several inputs should commit together and a fragment when a local rerun is safe.
- Use `st.rerun()` after state mutations that must rebuild sibling components.
- Do not cache a mutable per-session API globally.
- Keep business validation in core or parsing services and present typed failures in the component.

Browser workflows belong in `tests/e2e/`; component behavior belongs in `tests/ui_unit/` or
`tests/ui_logic/` when it can be separated from rendering.
