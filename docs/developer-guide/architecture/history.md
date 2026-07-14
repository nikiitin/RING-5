---
layout: default
title: Architecture History
parent: Architecture
grand_parent: Developer Guide
nav_order: 9
permalink: /developer-guide/architecture/history/
---

# Architecture history

This page records removed designs. Use [Architecture Overview](overview/) for current code.

## Engine-independent configuration

An earlier visualization stack routed figure creation through a `FigureEngine`, figure creator,
styler, and configuration bridge. That work established engine-independent figure configuration but
left unnecessary indirection.

The current design keeps pure visualization configuration in `src/core/models/visualization/` and
puts Plotly and Matplotlib translation in `src/web/rendering/`. Plot implementations build typed
traces directly; rendering connectors consume those traces.

## Components and controllers

The web application moved from large page functions and presenter-like indirection to components
that render widgets plus controllers that orchestrate plot creation, pipelines, and rendering. Core
services absorbed duplicated web-service logic. There is no current presenter layer.

## Repository state

Application state moved from broad Streamlit access to a repository-backed state manager. Web-only
interaction state remains separate, allowing `ring5.Session` to compose the same core workflow
without Streamlit session state.

## Public headless surface

The `ring5` package became the supported scripting composition root. Earlier examples that imported
`src.*` were internal and are not compatibility promises. Current scripts use `ring5.Session`, typed
figure configuration, portfolio replay, and typed errors.
