---
title: "Documentation Page"
parent: Page Guides
grand_parent: User Guide
nav_order: 5
---

# Documentation Page

## Overview

RING-5 includes a built-in Documentation page that serves as a central hub for
all reference material. Rather than embedding lengthy guides directly into the
application, the page links out to detailed documentation files organized by
topic.

To open the Documentation page, click **Documentation** in the sidebar
navigation.


## What Is Available

The Documentation page is organized into six sections.

**Getting Started** -- Installation instructions, key concepts, a first-steps
walkthrough, and the FAQ.

**Page Guides** -- Detailed walkthroughs for every page in the application:
Data Source, Data Managers, Manage Plots, and Portfolio.

**Features Reference** -- In-depth reference for plot types, shapers, settings
pills, export presets, the dual rendering engine, and the portfolio system.

**Tutorials** -- Hands-on guides for common workflows: loading data, creating
bar charts, normalizing metrics, publication-ready export, multi-seed
comparison, and custom styling.

**Developer Guide** -- Architecture, API reference, extension guides, and
development workflow for contributors.

**Quick Reference** -- Supported input and export formats, and keyboard
shortcuts.

Each entry on the page shows a title, a brief description, and the path to the
corresponding documentation file. Entries for documentation that has not yet
been written are marked with "(coming soon)."


## Accessing Documentation

1. Click **Documentation** in the sidebar navigation.
2. You should see the Documentation hub with six sections displayed as
   two-column grids of link cards.
3. Find the topic you are interested in and note the file path shown on the
   card.

The documentation files themselves are Markdown files located in the `docs/`
directory of the project. You can open them in any text editor or Markdown
viewer.


## Using Documentation Alongside Your Work

You can keep the Documentation page open in a separate browser tab for
reference while working on another page. Open a second tab pointed to your
RING-5 instance, navigate to the Documentation page there, and switch between
that tab and your working tab as needed.

Because the Documentation page does not read or modify any application state,
opening it in a separate tab has no effect on your current analysis session.
