---
layout: default
title: User Guide
nav_order: 2
has_children: true
permalink: /user-guide/
---

# User Guide

Use RING-5 to parse gem5 statistics or open a CSV, prepare the resulting table, render plots, and
save enough state to reproduce the work later. You can use the Streamlit application for
interactive work and the `ring5` API or CLI for scripts and continuous integration.

## Start here

1. [Install RING-5](getting-started/installation/).
2. Read the [core concepts](getting-started/concepts/).
3. Complete [First Steps](getting-started/first-steps/).

## Find a task

- [Workflows](workflows/) cover loading and parsing, dataset operations, plotting, portfolios, and
  scripting.
- [Analysis Guides](guides/) apply those workflows to configuration comparison and publication
  export.
- [Reference](reference/) describes plot selection, shapers, settings, rendering and export, plus
  troubleshooting.

Examples use gem5 names such as `simTicks` where the parser provides them, but RING-5 does not
require a fixed CSV schema. Any non-empty CSV with a header can be loaded; individual operations
validate the columns and data types they need.
