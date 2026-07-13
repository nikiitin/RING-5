---
title: "API Reference"
parent: Developer Guide
nav_order: 30
has_children: true
---

# API Reference

Guides in this section are listed in the sidebar.

The **public, supported entry point for scripts** is the top-level `ring5`
package (`import ring5` → `Session`, `render_portfolio`, `doctor`, the typed
error hierarchy) and the `ring5` CLI — see the
[Scripting & Headless Use](../../user-guide/features/scripting.md) guide.
The pages here document the internal facade (`ApplicationAPI`) and services
the `ring5` package composes.
