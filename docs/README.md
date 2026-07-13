# RING-5 Documentation

Documentation source for **RING-5** — published via GitHub Pages with the
[just-the-docs](https://just-the-docs.com/) theme at
**<https://nikiitin.github.io/RING-5/>**.

This folder is organized into three trees (each is a section in the published site's sidebar):

| Tree | Audience | Entry point |
| ---- | -------- | ----------- |
| [`user-guide/`](user-guide/index.md) | Researchers using the app | `getting-started/installation.md`, `getting-started/first-steps.md` |
| [`developer-guide/`](developer-guide/index.md) | Contributors & maintainers | `architecture/overview.md`, `development/setup.md` |
| [`engineering-reference/`](engineering-reference/index.md) | Maintainers needing concise reference material | `architecture/system-overview.md`, `quick-reference/file-locations.md` |

`index.md` is the site landing page; `_config.yml` holds the Jekyll/just-the-docs configuration.

## Editing

- Each page carries just-the-docs nav front-matter (`title`, `parent`, `grand_parent`, `nav_order`,
  `has_children`). Keep `parent`/`grand_parent` values matching the exact section/tree page titles.
- Building locally (optional): `gem install bundler jekyll`, add a `Gemfile` with
  `gem "just-the-docs"` + `gem "jekyll-redirect-from"`, then `bundle exec jekyll serve`. The
  GitHub Pages workflow (`.github/workflows/pages.yml`) builds and deploys on push.

Repository contribution rules are in [`/AGENTS.md`](../AGENTS.md), with task recipes under
[`/.agents/skills/`](../.agents/skills/).
