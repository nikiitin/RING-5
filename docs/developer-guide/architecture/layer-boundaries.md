---
layout: default
title: Layer Boundaries
parent: Architecture
grand_parent: Developer Guide
nav_order: 3
permalink: /developer-guide/architecture/layer-boundaries/
redirect_from:
  - /engineering-reference/architecture/layer-boundaries/
---

# Layer boundaries

The automated architecture check enforces the principal import and syntax rules, while code review
enforces ownership and public API intent.

## Enforced rules

<!--
`uman~ring5.quality.architecture-boundaries.documentation~1`

Covers:
- req~ring5.quality.architecture-boundaries~1

-->

- `src/core/` and `src/parsing/` do not import Streamlit, access `st.session_state`, or import
  `src.web`.
- `src/core/models/` and `src/parsing/` do not import `src.core.services`.
- `src/web/` does not import the concrete `RepositoryStateManager`; it works through facades and
  protocols.
- Production code does not use bare `except`, `eval`, `exec`, ellipsis statements, or
  `inplace=True`.

Run:

```bash
make arch-check
```

## Direction of calls

Web components call controllers or `ApplicationAPI`. Controllers depend on protocols and adapters,
then invoke core services or plot models. Core services depend on models, repositories, and parser
protocols. Parser implementations produce the shared CSV and parsing models.

The `ring5` package is allowed to compose core and rendering because it is a composition root. That
does not make `src.web` a valid dependency for core code.

## Where a change belongs

- Put simulator-specific scanning and parsing in `src/parsing/<simulator>/`.
- Put UI-independent data rules in `src/core/services/` and shared types in `src/core/models/`.
- Put persistent workspace state behind `src/core/state/` repositories.
- Put Streamlit rendering in `src/web/components/` and page orchestration in controllers.
- Put backend translation and export in `src/web/rendering/`.
- Put supported scripting behavior and typed boundary errors in `ring5/`.

When a proposed feature requires core to import the web layer, move the shared contract downward or
inject a callback/protocol from a composition root.
