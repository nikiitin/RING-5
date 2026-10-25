---
layout: default
title: Registries and Factories
parent: Stable Interfaces
grand_parent: Developer Guide
nav_order: 6
permalink: /developer-guide/api-reference/registries-and-factories/
---

# Registries and factories

Registries turn serialized or user-selected identifiers into implementations. The source registry,
not documentation, is the current inventory.

| Registry | Identifier contract | Discovery |
| --- | --- | --- |
| Simulator registry | Simulator name and metadata | `ApplicationAPI.available_simulators()` |
| Strategy factory | Backend-specific strategy name | Simulator metadata |
| Plot factory | Snake-case plot identifier | `ring5.available_plot_types()` |
| Shaper definitions | Exact registered identifier and required Literal discriminator | `ring5.shapers.available_shaper_types()` |
| Stat type registry | Backend variable-type string | Simulator metadata |

Factories reject unknown identifiers and report available choices at the relevant boundary. Display
names are presentation metadata and must map back to one identifier.

Before renaming or removing an identifier, find portfolio, pipeline, CLI, and public API consumers.
Replace those callers together. Test the current contract and clear rejection of retired names;
do not add migration or alias handling.

Shapers register through `ring5.shapers.register_shaper(ShaperDefinition(...))`. The definition owns
its implementation, exact TypedDict configuration, semantic validator and display metadata.
Constructors, factory creation, pipeline execution and pipeline import use this one validator.
Built-ins retain separate explicit discovery and editor ordering. Plugins default to API-only;
a web editor requires its own configuration renderer. See [Add a shaper](../extension-guides/adding-a-shaper.md).
