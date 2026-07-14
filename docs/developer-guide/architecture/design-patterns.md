---
layout: default
title: Design Patterns
parent: Architecture
grand_parent: Developer Guide
nav_order: 5
permalink: /developer-guide/architecture/design-patterns/
---

# Design patterns

Use the patterns already carrying compatibility or ownership boundaries. Do not add pattern layers
only to rename a direct call.

## Facade and protocols

`ApplicationAPI` is the web facade for services and state. `ring5.Session` is the supported user
facade. Protocols such as `SimulationParser`, data-service APIs, manager APIs, state contracts, and
plot-controller dependencies isolate consumers from implementations.

## Repository

The state manager delegates persistent workspace concerns to repositories. UI-only widget state has
a separate manager. Add state to the narrow repository that owns its lifecycle; do not add arbitrary
keys to Streamlit session state from domain code.

## Registry and factory

Simulator, parser-strategy, plot, and shaper registries map stable identifiers to implementations.
Factories validate identifiers and construct the selected behavior. Registry identifiers stored in
portfolios or pipelines require migrations when renamed.

## Strategy and pipeline

Parser strategies and shapers provide replaceable algorithms behind common contracts. The shaper
pipeline applies strategies in order and reports the failing step. Preserve input immutability and
validate a strategy's configuration before expensive work.

## Adapter and connector

Web adapters satisfy controller protocols around existing plot and pipeline services. Rendering
connectors translate engine-independent traces and configuration into Plotly or Matplotlib objects.
Keep backend imports on the rendering side of this boundary.

Choose the smallest existing pattern that preserves dependency direction. A direct function is
preferable when no interchangeability, compatibility, or test seam is required.
