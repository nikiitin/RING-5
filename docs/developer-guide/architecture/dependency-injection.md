---
layout: default
title: Dependency Injection
parent: Architecture
grand_parent: Developer Guide
nav_order: 4
permalink: /developer-guide/architecture/dependency-injection/
---

# Dependency injection

RING-5 uses explicit constructor injection and small protocols. It does not use a dependency
injection framework.

`app.py` creates one `ApplicationAPI` per browser session and passes it into page functions or page
objects. The Manage Plots page constructs lifecycle, registry, and pipeline adapters, then injects
them into focused controllers. Tests replace those protocols with fakes or mocks without starting a
Streamlit server.

`ring5.Session` constructs the same application facade with a plot deserializer and optional parser.
Passing a `SimulationParser` to the constructor is the supported test seam for parser composition.

## Add a dependency

1. Define the narrow behavior the consumer needs, normally as a protocol near the consuming layer.
2. Accept it in the consumer constructor.
3. Build the concrete object in `app.py`, `ring5/`, or the closest page composition function.
4. Pass a focused fake in unit tests.

Do not add a global service locator or let a component construct persistent repositories. Process
singletons are reserved for explicitly thread-safe worker pools and follow their shutdown contract.
