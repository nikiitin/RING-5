---
layout: default
title: Continuous Integration
parent: Development
grand_parent: Developer Guide
nav_order: 5
permalink: /developer-guide/development/ci-cd/
---

# Continuous integration

The CI workflow separates quality and package validation, non-browser tests, serial figure exports,
LaTeX exports, and Streamlit browser tests. The test matrix covers every Python version declared in
`pyproject.toml` (3.12–3.15); one job produces the coverage report. Python jobs install the
checked-in `uv.lock` with uv 0.13.5. An installed-wheel smoke job exercises a headless CSV-to-SVG
workflow and real process-lock exclusion on Linux, macOS, and Windows outside the source checkout.

Run the corresponding local targets before pushing:

```bash
make quality-gate
make docs-build docs-audit docs-security
make package-check
make test-ci
make test-export
make test-latex     # when XeLaTeX is installed
make test-e2e
```

The documentation CI job installs the locked root `Gemfile`, performs a Jekyll production build,
audits the locked gems against current advisories, then audits canonical routes, redirects, assets, and internal links in `_site/`. This catches theme
or plugin mismatches that a Markdown-only check cannot see. CodeQL runs separately on pushes, pull
requests, and its scheduled audit. GitHub Pages uses the same locked build and audit path, and
deploys only from `main`.

When CI differs from a local run, compare the Python version, optional system dependencies, test
markers, xdist mode, and generated fixtures. Reproduce the exact Make target before changing code.

## Dependency updates

Dependabot opens weekly uv, Bundler and GitHub Actions updates. The existing Python groups combine
patch/minor updates; major updates remain available for manual review. The dependency controller
reads the trusted default-branch configuration in `.github/dependency-automation.json`. The hosted
workflow runs only when the repository variable `DEPENDENCY_AUTOMATION_ENABLED` is exactly `true`.
The checked-in policy sends escalations to `nikiitin` and keeps major upgrades under human review.

For an eligible Dependabot pull request with verified signed commits targeting `main`, the controller
requests `copilot-pull-request-reviewer[bot]` through GitHub's review API. It waits for a formal
`APPROVED` review on the current head, no unresolved review threads or active change requests, and
successful current-head runs of
all 16 CI jobs plus CodeQL's `Python analysis`. Missing, skipped, cancelled, stale or failed jobs do
not satisfy the gate. The branch must contain current `main`; GitHub's native protections must also
allow the merge. A required merge queue is unsupported and keeps the controller blocked. Labels and
an approving sentence in a review comment do not authorize a merge.

The controller permits only its defined dependency-file and action-pin changes, keeps major updates
manual by default, and submits a squash merge with the exact reviewed head SHA. It cannot bypass
native rules or manufacture an approval. When a compatibility gap needs attention, it posts one
maintained escalation comment instead of repeatedly requesting a human review. The repository
variable `DEPENDENCY_AUTOMATION_REVIEWER` overrides the configured reviewer; the trusted repository
owner is the fallback when both are empty.

The privileged workflow checks out only the default branch with credentials persistence disabled.
It runs the standard-library controller, without installing pull request dependencies, executing
pull request code or downloading CI artifacts. Pull request opening/push events and associated
CI/CodeQL completions assess the affected updates immediately. The hourly pass at minute 17 catches
late approvals and recovers missed assessments; post-merge dispatch completions do not rescan all
open updates. Global concurrency keeps
controller runs from overlapping. The workflow does not subscribe to `pull_request_review`.

After a merge made with `GITHUB_TOKEN`, the controller explicitly dispatches `ci.yml`, `codeql.yml`
and `pages.yml` on literal `main`. GitHub normally suppresses new workflow runs caused by that
token's push events; the dispatches restore post-merge CI and documentation deployment. See
[GitHub's token event rules](https://docs.github.com/en/actions/concepts/security/github_token).

## Enable dependency automation

Activation requires repository administration. Keep the current branch protections and security
rules while completing these steps:

1. Merge the reviewed controller, policy, workflow and instructions into the default branch. Keep
   the enable variable unset until the read-only configuration check and manual Copilot setup pass.
2. In a repository ruleset applying to `main`, require all 17 contexts listed in
   `.github/dependency-automation.json`, enable strict up-to-date checks, require at least one
   approval and dismiss approvals after new pushes. Preserve existing classic branch protections,
   code-owner, security and conversation rules. The controller rejects missing required checks or non-strict protection;
   its own CI polling is an additional gate.
3. In repository Copilot code-review settings, enable both `Allow Copilot to approve pull requests`
   and `Allow Copilot approvals to count toward merge requirements`. Enterprise/organization policy
   and the repository's Copilot entitlement must permit this public-preview feature. Enable custom
   review instructions. Without a formal current-head approval, the controller keeps the update
   open. See [GitHub's Copilot configuration guide](https://docs.github.com/en/copilot/how-tos/copilot-on-github/set-up-copilot/configure-code-review).
4. Restrict the Copilot approval file paths to the dependency surfaces, one glob per line:

   ```text
   pyproject.toml
   uv.lock
   Gemfile
   Gemfile.lock
   .github/workflows/*.yml
   ```

   GitHub counts a scoped approval only when every changed file matches. The controller's diff
   policy remains narrower: matching a workflow glob does not permit changing commands, permissions
   or review controls. Copilot reads instructions from the pull request head, so dependency updates
   must not change those instructions. See [GitHub's review customization guide](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/use-code-review).
5. Allow the workflow's explicit token permissions: Actions dispatch, content merge, review requests
   and escalation comments. Ensure Actions permits this trusted `pull_request_target` workflow
   under the applicable event policy. Public repositories may have an evaluating default policy
   that blocks that trigger when enforced; check the repository's policy insights and
   [GitHub's event-policy guidance](https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target).
6. Optionally set `DEPENDENCY_AUTOMATION_REVIEWER` to the maintainer who should receive escalations.
   Run the read-only configuration command below. It reports active native protection gaps and
   the manual Copilot settings; exit status 1 means configuration is incomplete. Then inspect an
   actual pull request without `--apply`. A dry run checks readiness without requesting reviews,
   posting comments or merging. Once enabled, the hosted **Dependency automation** workflow also
   supports manual `dry_run=true` and optional `pr_number`.
7. Set `DEPENDENCY_AUTOMATION_ENABLED=true` after the dry run and setup checks pass. To disable
   processing, remove that variable or set it to `false`. Manual runs also honor this enable guard;
   use the trusted local command below to inspect the setup before enabling the hosted workflow.

Provide `GH_TOKEN` through the environment and inspect configuration from the trusted checkout:

```bash
python -m scripts.dependency_automation \
  --check-configuration --config .github/dependency-automation.json
```

This command never processes pull requests or mutates GitHub state, even if `--apply` is also
supplied. It reads active rulesets through GitHub's branch-rules API and reports the Copilot settings to check
manually. Classic branch protection alone does not satisfy this readiness check. The command does
not enable settings or remove existing protections. Merge queues remain unsupported.

A separate pull request inspection makes no changes unless `--apply` is supplied:

```bash
python -m scripts.dependency_automation \
  --config .github/dependency-automation.json --pr 123
```

After changing the CI matrix or job display names, update the required-workflow configuration and
native required contexts together. A successful job does not guarantee a
third-party coverage upload or an alert-free CodeQL result; investigate security findings directly.
