---
layout: default
title: Registries and Factories
parent: Stable Interfaces
grand_parent: Developer Guide
nav_order: 6
permalink: /developer-guide/api-reference/registries-and-factories/
redirect_from:
  - /engineering-reference/reference/factory-registry/
---

# Registries and factories

Registries turn serialized or user-selected identifiers into implementations. The source registry,
not documentation, is the current inventory.

| Registry | Identifier contract | Discovery |
| --- | --- | --- |
| Simulator registry | Simulator name and metadata | `ApplicationAPI.available_simulators()` |
| Strategy factory | Backend-specific strategy name | Simulator metadata |
| Plot factory | Snake-case plot identifier | `ring5.available_plot_types()` |
| Shaper factory | Serialized camel-case or legacy identifier | Web **Add transformation** selector |
| Stat type registry | Backend variable-type string | Simulator metadata |

Factories reject unknown identifiers and report available choices at the relevant boundary. Display
names are presentation metadata and must map back to one identifier.

Before renaming or removing an identifier, find portfolio, pipeline, CLI, and public API consumers.
Add migration or alias handling and a fixture that proves older serialized content still loads.
