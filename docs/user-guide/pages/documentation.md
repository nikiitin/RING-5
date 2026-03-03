# Documentation Page

## Overview

RING-5 includes a built-in Documentation page that serves as a central hub for
all reference material. Rather than embedding lengthy guides directly into the
application, the page links out to detailed documentation files organized by
topic.

To open the Documentation page, click **Documentation** in the sidebar
navigation.


## What Is Available

The Documentation page is organized into three sections.

**WebApp Guide** -- Step-by-step instructions for each page in the RING-5 web
application. This includes a Quick Start guide, pages for Data Source, Manage
Plots, Data Managers, Plot Settings, Export and Download, and Portfolios, as
well as a First Analysis walkthrough.

**API Reference** -- Documentation for programmatic access to RING-5
capabilities. This covers the Backend Facade (ApplicationAPI), the Plotting
API, the Parsing API, and the Shaper API.

**Developer Guides** -- Resources for contributors and advanced users. This
includes the system architecture overview, a testing guide, development setup
instructions, and a guide for adding new plot types.

Each entry on the page shows a title, a brief description, and the path to the
corresponding documentation file. Entries for documentation that has not yet
been written are marked with "(coming soon)."


## Accessing Documentation

1. Click **Documentation** in the sidebar navigation.
2. You should see the Documentation hub with three sections displayed as
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
