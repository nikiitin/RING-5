---
description: Streamlit engineering, state management, and high-performance UI.
globs: src/web/**/*.py
---

# 006-streamlit-engineering.md

## 1. The Frontend Architect

You treat Streamlit not just as a scripting tool, but as a React-like reactive application framework. You design for performance, user experience, and determinism. You use principles from "Web App Development Made Simple with Streamlit" and "Streamlit for Data Science".

## 2. Streamlit Best Practices (Book-Driven)

As mandated by **"Streamlit for Data Science"** and **"Web App Development Made Simple with Streamlit"**, Streamlit must be treated as a reactive, state-driven framework, not a top-down script.

### 2.0 Fragment Identity Mastery (Critical)

- **The Nested Fragment Anti-Pattern:** NEVER define a `@st.fragment` function _inside_ a parent render function or loop. Streamlit identifies fragments by their internal function ID and module path. If a fragment is dynamically created inside another function during a rerun, Streamlit sees it as a completely new component, destroying its state isolation and triggering full-app reruns.
- **The Fix:** Always define `@st.fragment` functions at the **module level** (outside of classes and page render functions), passing any required state (like `current_plot` or `api`) explicitly as arguments.

### 2.1 State Management (The Foundation)

- **Session State:** Use `st.session_state` strictly for variables that must cross re-runs (e.g., selected plots, active tab).
- **Initialization:** Always initialize state at the top of your controller/page to prevent KeyErrors on first load:
  ```python
  if "current_view" not in st.session_state:
      st.session_state.current_view = "dashboard"
  ```
- **Callbacks over Manual Checks:** Prefer using `on_change` and `args/kwargs` in widgets rather than checking boolean returns. This avoids the "double re-run" problem commonly faced in simple scripts.
- **Hydrate-then-Render Pattern:** As documented in **"Streamlit for Data Science"**, separates data loading/hydration logic from the UI layout. The pattern ensures that `st.session_state` is fully populated _before_ the first widget is drawn, preventing layout shifts.

### 2.2 Performance & Caching

- **st.cache_data:** Use for ANY function returning a DataFrame, heavily processed data, or API calls. The return object MUST be safe to serialize/deserialize.
- **st.cache_resource:** Use for global objects like database connections, ML models, or large configuration dicts that should be shared across sessions.
- **Mutation Warning:** Never mutate objects returned by `st.cache_data`. If you must mutate a Dataframe, `.copy()` it first to avoid corrupting the cache.
- **Cache Invalidation:** Ensure that source files (e.g., `stats.txt`) or parsed times act as hashing arguments to trigger cache invalidation efficiently.

### 2.3 Layout & UX

- **Containerization:** Always group related widgets inside `st.container()`. This ensures structural integrity.
- **Columns:** Use `st.columns()` effectively for horizontal alignment. Do not over-nest columns unless necessary as it impacts mobile responsive behavior.
- **Fragments:** Use `@st.fragment` (or `st.experimental_fragment`) for isolated components (like complex forms or specific charts) that should re-render independently without refreshing the whole page. This is critical for highly interactive plots.
- **Dynamic Overlays:** Use `st.empty()` placeholders for high-performance updates like real-time progress bars or status messages during long-running parsing tasks, a technique emphasized in **"Web App Development Made Simple with Streamlit"**.
- **Empty States:** Always provide `st.info()` or `st.warning()` for empty states when visualizations lack data. Never show an empty or broken plot.

### 2.4 Separation of Concerns (UI vs Logic)

- **No Heavy Lifting in Pages:** Your `app.py` or page scripts (`manage_plots.py`) should only handle `st.xxx()` calls and routing. All data filtering, computation, and statistical functions MUST reside in `src/domain/` or `src/core/`.
- **UI Components:** Extract repeated widget groups into functions inside `src/web/components/`. Keep Presenters isolated from actual Business Logic APIs.
- **The Presenter-Controller Decoupling:** Every complex page (`src/web/pages/*.py`) must behave like a Controller that delegates UI construction to Presenters (`src/web/presenters/`). This follows the architectural advice of **"Clean Architecture with Python"** to keep the framework (Streamlit) from leaking into the domain logic.

---

**Status:** ✅ Active
**Priority:** HIGH
**Acknowledgement:** ✅ **Acknowledged Rule 006**
