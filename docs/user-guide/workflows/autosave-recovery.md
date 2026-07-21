---
layout: default
title: Recover an Interrupted Workspace
parent: Workflows
grand_parent: User Guide
nav_order: 9
permalink: /user-guide/workflows/autosave-recovery/
---

# Recover an interrupted workspace

<!--
`uman~ring5.workspace.autosave-recovery.documentation~1`

Covers:
- req~ring5.workspace.autosave-recovery~1

-->

RING-5 keeps bounded local recovery drafts while you work. If a browser tab disconnects, expires,
or is replaced by a new session, the same browser can explicitly restore its most recent analysis
state.

## What autosave does

- Captures the first meaningful workspace and checks again at most once per minute on app reruns.
- Uses the same versioned JSON, integrity manifest, and restore validation as a portfolio.
- Keeps at most five drafts for one browser and deduplicates unchanged workspace content.
- Limits each draft to 64 MiB and applies both per-browser and server-wide count and byte limits.
- Writes atomically with owner directories and files restricted to the server account.

An empty default workspace does not create a draft. Autosave is a recovery aid, not a replacement
for a named portfolio: retention limits may remove older drafts, while portfolios remain under your
explicit management.

## Recover or delete a draft

1. Open **Autosave & recovery** in the sidebar.
2. Choose a timestamped **Recovery point**.
3. Select **Recover**. RING-5 verifies the size, portfolio checksum, integrity sections, and schema
   before changing the current workspace.
4. Review any incomplete-restore warning. A draft with an invalid checksum is never restored.
5. Select **Delete draft** when a recovery point is no longer needed.

Use **Save recovery draft now** before a risky edit when you want an immediate checkpoint. RING-5
does not restore automatically: the current session changes only after you choose **Recover**.

## Browser privacy boundary

Draft ownership is derived from a browser-held secret. RING-5 converts the normal Streamlit cookie
into a one-way recovery token, places that token in the page URL so it survives a replaced session,
and hashes it again for the local directory name. When the cookie is unavailable, RING-5 creates a
random URL token instead. Keep that URL private: anyone who possesses the token can address the
same local recovery namespace on that server.

Drafts stay on the RING-5 server; they are not uploaded to a remote service. Different browsers do
not see each other's draft lists, even when they use the same application instance.

## Use recovery from Python

Python callers supply and retain their own secret namespace key:

```python
import ring5

owner_key = "use-a-secret-from-your-credential-store"

with ring5.Session() as session:
    captured = session.create_recovery_draft(owner_key)
    if captured is not None:
        print(captured.draft.created_at, captured.created)

with ring5.Session() as replacement:
    drafts = replacement.list_recovery_drafts(owner_key)
    if drafts:
        report = replacement.restore_recovery_draft(owner_key, drafts[0].draft_id)
        print(report.complete)
```

Use `delete_recovery_draft()` for explicit cleanup. The owner key is a namespace capability, not
encryption; protect it as you would a private recovery link.
