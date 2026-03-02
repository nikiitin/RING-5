# Step 08 — Web Pages & Navigation Flow Analysis

> **Objective**: Document every Streamlit page, its purpose, its UI layout, its state
> interactions, the navigation model, and the complete user journey through the application.

---

## Scope

This step maps the **entire web application surface** — every page a user can visit,
what they see, and what they can do.

---

## Files to Analyze

### Main Entry Point
```
app.py                                             (Streamlit app configuration, page routing)
```

### Page Definitions
```
src/web/pages/__init__.py
src/web/pages/data_source.py                       (data loading page)
src/web/pages/data_managers.py                     (data transformation page)
src/web/pages/manage_plots.py                      (plot creation/management page)
src/web/pages/portfolio.py                         (portfolio save/load page)
src/web/pages/documentation.py                     (in-app documentation)
src/web/pages/plot_adapters.py                     (plot adapter utilities)
```

### Plot UI Pages
```
src/web/pages/ui/plotting/__init__.py
src/web/pages/ui/plotting/base_plot.py             (base plot page)
src/web/pages/ui/plotting/plot_config_ui.py        (plot configuration UI)
src/web/pages/ui/plotting/plot_factory.py          (plot factory for page creation)
src/web/pages/ui/plotting/plot_renderer.py         (plot rendering orchestration)
src/web/pages/ui/plotting/plot_service.py          (plot service layer)
src/web/pages/ui/plotting/download_section.py      (export/download UI)
src/web/pages/ui/plotting/settings_pills.py        (settings pill navigation)
```

### Plot Type Pages
```
src/web/pages/ui/plotting/types/__init__.py
src/web/pages/ui/plotting/types/bar_plot.py
src/web/pages/ui/plotting/types/dual_axis_bar_dot_plot.py
src/web/pages/ui/plotting/types/grouped_bar_plot.py
src/web/pages/ui/plotting/types/grouped_stacked_bar_plot.py
src/web/pages/ui/plotting/types/heatmap_plot.py
src/web/pages/ui/plotting/types/histogram_plot.py
src/web/pages/ui/plotting/types/line_plot.py
src/web/pages/ui/plotting/types/scatter_plot.py
src/web/pages/ui/plotting/types/stacked_bar_plot.py
src/web/pages/ui/plotting/types/_trace_helpers.py
```

### Style UIs
```
src/web/pages/ui/plotting/styles/__init__.py
src/web/pages/ui/plotting/styles/applicator.py
src/web/pages/ui/plotting/styles/bar_ui.py
src/web/pages/ui/plotting/styles/base_ui.py
src/web/pages/ui/plotting/styles/colors.py
src/web/pages/ui/plotting/styles/factory.py
src/web/pages/ui/plotting/styles/line_ui.py
```

### Data Manager UI
```
src/web/pages/ui/data_managers/                   (all files in directory)
```

### Shaper Config UI
```
src/web/pages/ui/shaper_config.py
```

---

## Questions to Answer

### Application Structure:
- [ ] How does `app.py` configure the Streamlit application?
- [ ] What is the page routing mechanism? (st.navigation? multipage?)
- [ ] What pages are registered and in what order?
- [ ] Is there a sidebar navigation? How is it structured?
- [ ] What global state is initialized on app startup?

### For Each Page:
- [ ] What is its entry function?
- [ ] What URL/route does it live at?
- [ ] What is the page layout? (wide? centered? sidebar?)
- [ ] What Streamlit components does it use? (columns, tabs, expanders, forms?)
- [ ] What state does it read from repositories?
- [ ] What state does it write to repositories?
- [ ] What services does it call?
- [ ] What user interactions are available?
- [ ] Are there fragments? What do they do?
- [ ] What callbacks are registered?

### User Journeys:
- [ ] What is the typical user flow? (data source → manage plots → portfolio)
- [ ] What are the prerequisites for each page? (e.g., must have data before plotting)
- [ ] How does the user navigate between pages?
- [ ] What happens if the user visits a page without prerequisites?

### Plot Configuration UI:
- [ ] How does the plot config UI work?
- [ ] What is the settings pill system?
- [ ] How are plot-type-specific settings rendered?
- [ ] How does the style system work?
- [ ] How is the download section integrated?

### Plot Types:
- [ ] How does each plot type page differ from the base?
- [ ] What type-specific configuration does each plot need?
- [ ] How is the plot type selected and instantiated?
- [ ] What is the _trace_helpers module doing?

---

## Information to Extract

### Page Catalog

For each page:
```
### PageName
- **File**: src/web/pages/xxx.py:NN
- **Route**: /page_name
- **Purpose**: [what the user does here]
- **Layout**: [wide/centered, sidebar usage]
- **Components Used**: [list of Streamlit components]
- **State Read**: [which repositories/session_state keys]
- **State Written**: [which repositories/session_state keys]
- **Services Called**: [which service methods]
- **User Actions**: [what can the user do]
- **Fragments**: [any @st.fragment decorators]
- **Prerequisites**: [what must exist before this page works]
```

### Navigation Map
```
[Diagram showing page → page navigation flows]
```

### User Journey Map
```
[Step-by-step typical user workflow across pages]
```

---

## Output Template

### 1. Application Configuration
```
[To be filled: How app.py sets up the Streamlit app]
```

### 2. Page Catalog
```
[To be filled: Every page with full documentation]
```

### 3. Navigation Map
```
[To be filled: How pages link to each other]
```

### 4. User Journey Documentation
```
[To be filled: Typical workflows across pages]
```

### 5. Plot Configuration UI Flow
```
[To be filled: How plot settings are configured]
```

### 6. Plot Type Catalog
```
[To be filled: Every plot type page with its specifics]
```

---

## Downstream Dependencies

This analysis feeds into:
- `DEVELOPER_GUIDE_PLAN.md` → `web/pages-and-navigation.md`
- `USER_GUIDE_PLAN.md` → `webapp/web-interface-overview.md` and all webapp pages
- Step 12 (settings pills) — needs page context for settings
- Step 18 (data flow) — needs to know how pages trigger data flow
