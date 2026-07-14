---
layout: default
title: State Manager
parent: Stable Interfaces
grand_parent: Developer Guide
nav_order: 5
permalink: /developer-guide/api-reference/state-manager/
redirect_from:
  - /developer-guide/core/state-management/
  - /engineering-reference/reference/state-keys/
---

# State manager

`StateManager` defines workspace state operations. `RepositoryStateManager` implements them by
delegating to focused repositories rather than storing a single untyped mapping.

State covers loaded data and source path, parser configuration and scan results, plots and plot
counters, previews, visualization configuration, and operation history. Web-only widget state
belongs to `UIStateManager` and is not part of the core contract.

## Restore

`restore_session` accepts migrated portfolio data and restores independent items. It returns
`RestoreReport` so callers can distinguish restored data, skipped plots, malformed parse variables,
and data errors. A restore never claims completeness when content was dropped.

## Add state

1. Choose the repository that owns the lifecycle or add a focused repository.
2. Extend the state protocol and repository-backed implementation.
3. Decide whether reset, portfolio save, migration, and restore include the field.
4. Keep values JSON-compatible when persisted.
5. Add isolation and round-trip tests.

Do not access the concrete repository state manager from `src/web`, and do not access
`st.session_state` from core or parsing code.
