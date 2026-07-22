---
layout: default
title: Monitor Background Jobs
parent: Workflows
grand_parent: User Guide
nav_order: 2.7
permalink: /user-guide/workflows/background-jobs/
---

# Monitor background jobs

<!--
`uman~ring5.workspace.background-jobs.documentation~1`

Covers:
- req~ring5.workspace.background-jobs~1

-->

Expand **Background jobs** in the sidebar to see work attached to the current browser session.
RING-5 automatically adds file scans, full and incremental parses, and parser configuration tests.
Each card names the operation and shows its type, state, completed work, total work, and attempt.
The expander opens automatically while work is active.

**Cancel** requests cancellation of work that has not started. Already-running work may need to
settle first, so its card says **Cancelling** rather than claiming it stopped immediately. **Retry**
appears only when RING-5 captured everything required to repeat the complete operation. Scan and
parse results stay on their original handles and are not retryable from the job center; this avoids
silently rerunning only part of a parser workflow.

A failed card shows short, single-line error details without a traceback. The session retains at
most 100 jobs, 20 error entries per job, and 1,000 characters per error. **Clear finished** removes
completed, cancelled, and failed cards and releases results retained by the center. Active cards
are never removed. Clearing or closing the session requests cancellation of active work. Job
history is intentionally session-only; it is not a durable scheduler or an audit log.

## Submit transformations and exports from Python

`shape_submit` and `export_submit` copy their inputs and return immediately with an immutable
`BackgroundJobInfo`. Poll by the stable job ID, then retrieve the result only after the job is
complete:

```python
import time

import pandas as pd
import ring5


def wait_for(session, submitted):
    while True:
        current = next(
            job for job in session.background_jobs() if job.job_id == submitted.job_id
        )
        if current.terminal:
            return current
        time.sleep(0.05)


with ring5.Session() as session:
    data = pd.DataFrame({"benchmark": ["a", "b"], "ipc": [1.1, 1.4]})
    shaped_job = session.shape_submit(
        data,
        [{"type": "columnSelector", "columns": ["benchmark", "ipc"]}],
        label="Prepare IPC table",
    )
    shaped = session.background_job_result(wait_for(session, shaped_job))

    figure = session.plot(
        "bar",
        data=shaped,
        config={"x": "benchmark", "y": "ipc"},
    )
    export_job = session.export_submit(figure, "figures/ipc.html")
    exported_path = session.background_job_result(wait_for(session, export_job))
```

If a job fails, inspect `job.errors` and call `retry_background_job(job)` when
`job.retryable` is true. `cancel_background_job`, `retry_background_job`, and
`background_job_result` raise `JobError` for invalid lifecycle operations instead of exposing
executor exceptions. Call `dismiss_finished_background_jobs()` when a script no longer needs the
records or retained transformation/export results.

Resetting the workspace clears jobs that are already finished. Work still settling after a
cancellation request remains visible until it reaches a terminal state, so the interface never
hides work that may still be running.
