# RING-5 documentation source

The published documentation is at <https://nikiitin.github.io/RING-5/>. The source is split by
audience:

- [`user-guide/`](user-guide/index.md) helps researchers install RING-5 and complete analysis
  tasks in the web application, Python API, or CLI.
- [`developer-guide/`](developer-guide/index.md) explains the architecture, contributor workflow,
  subsystems, extension points, and stable interfaces.

`index.md` is the site landing page and `_config.yml` configures Jekyll and Just the Docs.

## Editorial rules

Write for readers who understand gem5 but have not used RING-5.

- Lead with the reader's task or the observable result.
- Use active voice, present tense, and direct instructions.
- Explain a term where the reader first needs it. Use the same term in the UI, API, and docs.
- Keep procedures short. Prefer a realistic command, configuration, or Mermaid flow over UI
  narration.
- State requirements and limitations without promotional language or decorative filler.
- Do not publish component totals or inventories that will drift. Point to a registry or discovery
  command when the software can answer the question.
- Verify commands with executable `--help` output. Verify UI labels, API calls, registry names, and
  formats against source or tests.
- Use repository-relative links for source files and site-relative links for published pages.
- Add `redirect_from` entries when a page moves or several pages merge. A redirect must name the
  old published route, including its leading and trailing slash.
- Do not add screenshots for procedures that change frequently. Use text, code, or diagrams.

## Page structure

Every published Markdown page starts with YAML front matter. Use a unique `title`, set `parent` and
`grand_parent` to exact page titles, and use `nav_order` for stable navigation. Directory index
pages use an explicit `permalink` ending in `/` and set `has_children: true` when applicable.

Run the documentation checks before committing:

```bash
make docs-check
make docs-build
```

Do not commit the generated `_site/` directory. Repository-wide contribution rules are in
[`AGENTS.md`](../AGENTS.md).
