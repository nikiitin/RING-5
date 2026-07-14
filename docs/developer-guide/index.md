---
layout: default
title: Developer Guide
nav_order: 3
has_children: true
permalink: /developer-guide/
redirect_from:
  - /engineering-reference/
---

# Developer Guide

This guide is for contributors who need to locate a change, preserve RING-5's boundaries, and
verify the result.

## Read by task

- [Architecture](architecture/) explains composition roots, dependency direction, and data flow.
- [Development](development/) covers setup, the contribution loop, tests, quality checks, CI, and
  debugging. Begin with [Development Setup](development/setup/).
- [Subsystems](subsystems/) describes parsing, core services and state, visualization, the web
  application, and portfolios.
- [Extension Guides](extension-guides/) give checklists for parsers, plots, shapers, renderers,
  managers, and settings panels.
- [Stable Interfaces](api-reference/) records the supported `ring5` surface and selected internal
  protocols used across boundaries.

The repository-level invariants in [`AGENTS.md`](../../AGENTS.md) are authoritative. Run
`make arch-check` after a structural change and keep user scripts on the `ring5` public package.
