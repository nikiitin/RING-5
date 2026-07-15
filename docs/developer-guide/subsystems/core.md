---
layout: default
title: Core Services and State
parent: Subsystems
grand_parent: Developer Guide
nav_order: 2
permalink: /developer-guide/subsystems/core/
---

# Core services and state

The core layer owns UI-independent models, data rules, and workspace state.

## Models

`src/core/models/` contains dataclasses, typed mappings, and protocols shared across boundaries.
Parsing models carry scan and parse results. Data and portfolio models define serialized state.
Visualization models describe traces and figure configuration without importing a rendering engine.

Add a model when several layers need a stable data contract. Keep service calls and environment
access out of model modules.

## Services

`src/core/services/` groups:

- data services for CSV pools, saved configuration, variables, and portfolios;
- managers for seed reduction, outlier removal, arithmetic, and column mixing;
- shapers and their ordered pipeline executor;
- visualization services such as configuration resolution and palettes.

Services validate arguments and return new objects. They do not render widgets or read Streamlit
state. Protocol modules state the behavior used by facades and tests.

## State

`src/core/state/repository_state_manager.py` implements the state boundary by delegating to focused
repositories. `src/core/state/state_manager.py` defines the contract used by services and
composition. Repository state belongs to one application or headless session unless a service
explicitly documents process-wide behavior.

`src/core/application_api.py` composes services and state for the web application. Prefer a focused
sub-API or method over exposing a repository implementation to callers.

## Change checklist

- Put shared types in models and behavior in services.
- Preserve DataFrame input immutability.
- Add typed public errors at the `ring5` boundary.
- Add repository methods for state with a clear lifecycle.
- Run `make arch-check` after moving imports.
