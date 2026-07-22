---
layout: default
title: Review an Analysis Together
parent: Workflows
grand_parent: User Guide
nav_order: 8
permalink: /user-guide/workflows/collaborative-review/
---

# Review an analysis together

<!--
`uman~ring5.workspace.collaborative-review.documentation~1`

Covers:
- req~ring5.workspace.collaborative-review~1

-->

RING-5 keeps review conversations with the analysis instead of leaving them in a separate
chat or document. A review update always records:

- the exact plot or saved portfolio version being discussed;
- a stable author identifier;
- an automatic UTC timestamp;
- an optional comment; and
- the resulting review status.

Review history is append-only. A later approval does not erase an earlier request for changes.

## Add a review update

1. Create the plot you want to discuss, or save a portfolio to create an immutable saved version.
2. Open **Analysis review** in the sidebar.
3. Choose the review subject. Portfolio versions are identified by their exact retained revision,
   not only by the reusable portfolio name.
4. Enter your **Author ID**. Use a stable name, email address, or team service identity.
5. Choose **Not reviewed**, **In review**, **Changes requested**, or **Approved**.
6. Add a comment, change the status, or do both, then select **Add review update**.

The panel shows the newest ten updates while retaining the complete bounded history. Imported
review history remains visible even if its saved portfolio revision is not available on the local
machine; RING-5 labels that condition and prevents new updates to the missing target.

## Make the review portable

Review updates first belong to the current workspace. Save or overwrite a portfolio after adding
them. The review log then becomes part of the portfolio configuration, so it is:

- covered by the portfolio integrity manifest;
- retained in immutable portfolio revisions;
- included in `.ring5-bundle` exports; and
- restored with the analysis on another machine.

If you add another review update later, save the portfolio again to produce a new portable version.

## Use reviews from Python

The public API uses the same validation and persistence path as the web interface:

```python
import ring5
import pandas as pd

with ring5.Session() as session:
    plot = session.create_plot(
        "bar",
        data=pd.DataFrame({"benchmark": ["a", "b"], "ipc": [1.0, 1.2]}),
        config={"x": "benchmark", "y": "ipc"},
        name="IPC comparison",
    )
    session.record_analysis_review(
        "plot",
        str(plot.plot_id),
        author_id="alice@example.org",
        comment="Please verify the baseline before publication.",
        status="in-review",
    )
    session.save_portfolio("paper-review")

    reviews = session.list_analysis_reviews(status="in-review")
```

For a saved portfolio version, use `list_analysis_review_targets()` to obtain its exact revision ID,
then pass `kind="portfolio_revision"` and its `portfolio_name` to `record_analysis_review()`.
