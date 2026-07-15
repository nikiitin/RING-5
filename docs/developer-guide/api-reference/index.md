---
layout: default
title: Stable Interfaces
parent: Developer Guide
nav_order: 6
has_children: true
permalink: /developer-guide/api-reference/
redirect_from:
  - /engineering-reference/reference/
  - /engineering-reference/quick-reference/error-patterns/
---

# Stable interfaces

The supported user API is the `ring5` package. Internal protocols documented here are stable enough
to coordinate layers and extensions, but they are not a compatibility promise for third-party
scripts.

- [Public Python API](public-python-api/) covers sessions, tables, figure specifications, portfolio
  replay, dependency checks, and typed errors.
- [Application API](application-api/) describes the web facade and async work contracts.
- [Service Protocols](services-api/) identifies the UI-independent service boundaries.
- [Models and Protocols](models-and-protocols/) explains cross-layer data contracts.
- [State Manager](state-manager/) records repository and restoration semantics.
- [Registries and Factories](registries-and-factories/) records identifier compatibility.

User scripts should follow [Automate with Python and the CLI](../../user-guide/workflows/scripting/)
and never import `src.*`.
