"""Gate Dependabot merges on native approval, compatibility CI and GitHub rules.

Run from a trusted default-branch checkout with ``python -m
scripts.dependency_automation``. The default mode reads repository state only;
``--apply`` permits review requests, escalation comments and guarded merges.
Pull request files are parsed as data and are never installed or executed.
"""

from __future__ import annotations

import argparse
import base64
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
import html
import json
import os
from pathlib import Path
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from scripts.dependency_update_policy import assess_changes

COPILOT_REQUEST_LOGIN = "copilot-pull-request-reviewer[bot]"
COPILOT_USER_ID = 175728472
COPILOT_NODE_ID = "BOT_kgDOCnlnWA"
DEPENDABOT = "dependabot[bot]"
SHA = re.compile(r"[0-9a-f]{40}")
REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
LOGIN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?")
REVIEW_WAIT_LIMIT = timedelta(hours=24)


class ApiError(RuntimeError):
    """A GitHub request or response cannot be safely used."""


@dataclass(frozen=True)
class _ReviewerIdentity:
    """Stable identifiers of the authoritative native review bot."""

    user_id: int
    node_id: str

    def matches(self, actor: Any) -> bool:
        """Require the bot type and both immutable identifiers, independent of login."""
        return (
            isinstance(actor, dict)
            and actor.get("type") == "Bot"
            and type(actor.get("id")) is int
            and actor["id"] == self.user_id
            and actor.get("node_id") == self.node_id
        )


class _RequestState(StrEnum):
    """Durable request intent and confirmed acceptance or pending observation."""

    INTENT = "intent"
    ACCEPTED = "accepted"
    OBSERVED = "observed"


@dataclass(frozen=True)
class _ReviewRequestReceipt:
    """A workflow-authored request state dated by the GitHub comment server."""

    comment_id: int
    created_at: datetime
    state: _RequestState


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, req: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        """Reject redirects before authenticated headers can be forwarded."""
        raise ApiError("GitHub API redirects are not followed with credentials")


class GitHubClient:
    """Access the GitHub API with bounded responses and pagination."""

    def __init__(self, token: str) -> None:
        self.token = token
        self._copilot_identity: _ReviewerIdentity | None = None
        self._copilot_receipts: dict[tuple[str, int, str], _ReviewRequestReceipt] = {}

    def copilot_identity(self) -> _ReviewerIdentity:
        """Resolve and cache the pinned native review bot through its request alias."""
        if self._copilot_identity is None:
            actor = self.request("GET", f"/users/{quote(COPILOT_REQUEST_LOGIN, safe='')}")
            identity = _ReviewerIdentity(COPILOT_USER_ID, COPILOT_NODE_ID)
            if not identity.matches(actor):
                raise ApiError("The native review request alias did not resolve to the pinned bot")
            self._copilot_identity = identity
        return self._copilot_identity

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        """Send a request to the fixed GitHub API origin without logging credentials."""
        if not path.startswith("/") or path.startswith("//"):
            raise ApiError("Invalid GitHub API path")
        data = None if payload is None else json.dumps(payload).encode()
        request = Request(
            "https://api.github.com" + path,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
            },
        )
        try:
            with build_opener(_NoRedirect()).open(request, timeout=30) as response:
                body = response.read(8_000_001)
        except HTTPError as error:
            raise ApiError(f"GitHub {method} request failed with HTTP {error.code}") from error
        except (URLError, TimeoutError, OSError) as error:
            raise ApiError("GitHub API request did not complete") from error
        if len(body) > 8_000_000:
            raise ApiError("GitHub response exceeds the controller limit")
        try:
            return json.loads(body) if body else None
        except (ValueError, UnicodeError) as error:
            raise ApiError("GitHub returned invalid JSON") from error

    def paginate(self, path: str, key: str | None = None) -> list[dict[str, Any]]:
        """Read a complete bounded collection; never accept a truncated page set."""
        items: list[dict[str, Any]] = []
        separator = "&" if "?" in path else "?"
        for page in range(1, 11):
            result = self.request("GET", f"{path}{separator}per_page=100&page={page}")
            batch = result if key is None else result[key]
            if not isinstance(batch, list) or any(not isinstance(item, dict) for item in batch):
                raise ApiError("Unexpected GitHub collection shape")
            items.extend(batch)
            if len(batch) < 100:
                return items
        raise ApiError("GitHub collection exceeds the controller pagination limit")


@dataclass(frozen=True)
class Outcome:
    """A decision bound to a specific pull request head."""

    number: int
    head: str
    state: str
    reasons: tuple[str, ...]


def _sha(value: Any) -> str:
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise ApiError("Expected a complete commit SHA")
    return value


def _repo_path(repository: str) -> str:
    if not REPOSITORY.fullmatch(repository):
        raise ValueError("Expected an owner/repository name")
    return f"/repos/{repository}"


def _eligible(pr: dict[str, Any], repository: str, config: dict[str, Any]) -> bool:
    return (
        pr["state"] == "open"
        and not pr.get("draft")
        and pr["user"].get("login") == DEPENDABOT
        and pr["user"].get("type") == "Bot"
        and pr["base"]["ref"] == config["base_branch"]
        and (pr["base"].get("repo") or {}).get("full_name") == repository
        and (pr["head"].get("repo") or {}).get("full_name") == repository
        and pr["head"]["ref"].startswith("dependabot/")
    )


def _content(client: GitHubClient, root: str, path: str, ref: str) -> str:
    result = client.request("GET", f"{root}/contents/{quote(path, safe='/')}?ref={_sha(ref)}")
    if result.get("type") != "file" or result.get("encoding") != "base64":
        raise ApiError("Expected a regular, base64-encoded repository file")
    if result.get("size", 1_000_001) > 1_000_000:
        raise ApiError("Dependency manifest exceeds the review size limit")
    try:
        return base64.b64decode(result["content"].replace("\n", ""), validate=True).decode()
    except (ValueError, UnicodeError) as error:
        raise ApiError("Cannot decode dependency manifest") from error


def protection_problems(client: GitHubClient, root: str, config: dict[str, Any]) -> list[str]:
    """Require native stale-review and strict CI protection before unattended merges."""
    rules = client.request("GET", f"{root}/rules/branches/{quote(config['base_branch'], safe='')}")
    contexts = {
        job for workflow in config["required_workflows"].values() for job in workflow["jobs"]
    }
    strict_contexts: set[str] = set()
    review_protected = False
    for rule in rules:
        parameters = rule.get("parameters") or {}
        if (
            rule["type"] == "required_status_checks"
            and parameters.get("strict_required_status_checks_policy") is True
        ):
            strict_contexts.update(
                check["context"] for check in parameters["required_status_checks"]
            )
        if rule["type"] == "pull_request":
            review_protected |= (
                parameters.get("required_approving_review_count", 0) >= 1
                and parameters.get("dismiss_stale_reviews_on_push") is True
            )
    problems = []
    if contexts - strict_contexts:
        problems.append("Main must require every configured CI context and an up-to-date branch")
    if not review_protected:
        problems.append("Main must require an approval and dismiss stale approvals on new pushes")
    if any(rule["type"] == "merge_queue" for rule in rules):
        problems.append("The configured merge queue needs a separate supported queue integration")
    return problems


def _action_provenance(client: GitHubClient, updates: Any) -> None:
    for update in updates:
        if update.ecosystem != "github-actions":
            continue
        repository = update.action_repository
        if not isinstance(repository, str) or not REPOSITORY.fullmatch(repository):
            raise ApiError("Cannot identify the updated Action repository")
        tag = quote(update.new_tag, safe="")
        result = client.request("GET", f"/repos/{repository}/git/ref/tags/{tag}")["object"]
        for _ in range(5):
            if result["type"] == "commit":
                if _sha(result["sha"]) != update.new_ref:
                    raise ApiError("Updated Action pin does not match its upstream release tag")
                break
            if result["type"] != "tag":
                raise ApiError("Unsupported Action release reference")
            result = client.request("GET", f"/repos/{repository}/git/tags/{_sha(result['sha'])}")[
                "object"
            ]
        else:
            raise ApiError("Action release tag indirection exceeds the verification limit")


def _ci_state(
    client: GitHubClient, root: str, pr: dict[str, Any], config: dict[str, Any], base: str
) -> tuple[list[str], list[str]]:
    pending: list[str] = []
    failed: list[str] = []
    head = _sha(pr["head"]["sha"])
    for name, workflow in config["required_workflows"].items():
        workflow_id = quote(workflow["path"].split("/")[-1], safe="")
        runs = client.paginate(
            f"{root}/actions/workflows/{workflow_id}/runs?"
            + urlencode({"head_sha": head, "event": "pull_request"}),
            "workflow_runs",
        )
        runs = [
            run
            for run in runs
            if run.get("head_sha") == head
            and run.get("event") == "pull_request"
            and isinstance(run.get("path"), str)
            and run["path"].count("@") <= 1
            and run["path"].split("@", 1)[0] == workflow["path"]
            and run.get("head_repository", {}).get("full_name") == pr["head"]["repo"]["full_name"]
            and any(
                entry.get("number") == pr["number"]
                and entry.get("head", {}).get("sha") == head
                and entry.get("base", {}).get("sha") == base
                for entry in run.get("pull_requests", [])
            )
        ]
        if not runs:
            pending.append(f"{name}: no pull-request run for the current head and main commit")
            continue
        run = max(runs, key=lambda item: (item["id"], item.get("run_attempt", 1)))
        if run.get("status") != "completed":
            pending.append(f"{name}: checks are still running")
            continue
        if run.get("conclusion") != "success":
            failed.append(f"{name}: workflow did not succeed ({run['html_url']})")
            continue
        jobs = client.paginate(f"{root}/actions/runs/{run['id']}/jobs?filter=latest", "jobs")
        for expected in workflow["jobs"]:
            matches = [job for job in jobs if job.get("name") == expected]
            if len(matches) != 1 or matches[0].get("conclusion") != "success":
                failed.append(f"{name}: required job {expected} is missing or did not succeed")
    return pending, failed


def _review_state(
    client: GitHubClient, root: str, pr: dict[str, Any], repository: str
) -> tuple[bool, list[str]]:
    identity = client.copilot_identity()
    copilot_key = ("bot", identity.node_id)
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for review in sorted(
        client.paginate(f"{root}/pulls/{pr['number']}/reviews"), key=lambda item: item["id"]
    ):
        if review.get("state") != "PENDING":
            actor = review["user"]
            key = copilot_key if identity.matches(actor) else ("login", actor["login"])
            latest[key] = review
    copilot = latest.get(copilot_key)
    approved = bool(
        copilot
        and identity.matches(copilot["user"])
        and copilot.get("commit_id") == pr["head"]["sha"]
        and copilot.get("state") == "APPROVED"
    )
    blocked = [
        "A reviewer has an active changes-requested review"
        for review in latest.values()
        if review.get("state") == "CHANGES_REQUESTED"
    ]
    if copilot and copilot.get("commit_id") == pr["head"]["sha"] and not approved:
        blocked.append(
            "Copilot did not approve this head; inspect its findings or approval settings"
        )
    owner, name = repository.split("/")
    cursor = None
    for _ in range(10):
        data = client.request(
            "POST",
            "/graphql",
            {
                "query": "query($owner:String!,$name:String!,$number:Int!,$cursor:String){"
                "repository(owner:$owner,name:$name){pullRequest(number:$number){headRefOid "
                "reviewDecision reviewThreads(first:100,after:$cursor){nodes{isResolved} "
                "pageInfo{hasNextPage endCursor}}}}}",
                "variables": {
                    "owner": owner,
                    "name": name,
                    "number": pr["number"],
                    "cursor": cursor,
                },
            },
        )
        if data.get("errors"):
            raise ApiError("Cannot verify review threads and native review requirements")
        result = data["data"]["repository"]["pullRequest"]
        if result["headRefOid"] != pr["head"]["sha"]:
            raise ApiError("Pull request changed during review verification")
        if approved and result["reviewDecision"] != "APPROVED":
            blocked.append("GitHub required reviews are not satisfied by the current approvals")
        threads = result["reviewThreads"]
        if any(thread.get("isResolved") is not True for thread in threads["nodes"]):
            blocked.append("Unresolved review threads require attention")
        if not threads["pageInfo"]["hasNextPage"]:
            return approved, list(dict.fromkeys(blocked))
        cursor = threads["pageInfo"]["endCursor"]
    raise ApiError("Review thread pagination exceeds the controller limit")


def _receipt_marker(head: str) -> str:
    """Bind an acceptance receipt to one complete pull request commit identity."""
    return f"<!-- ring5-native-review-request:{_sha(head)} -->"


def _parse_receipt(comment: dict[str, Any], head: str) -> _ReviewRequestReceipt | None:
    """Accept only workflow-bot receipts with a server timestamp and exact head marker."""
    author = comment.get("user") or {}
    body = comment.get("body")
    if (
        not isinstance(author, dict)
        or author.get("login") != "github-actions[bot]"
        or author.get("type") != "Bot"
        or not isinstance(body, str)
    ):
        return None
    lines = body.splitlines()
    if not lines or lines[0] != _receipt_marker(head):
        return None
    if type(comment.get("id")) is not int or comment["id"] <= 0:
        raise ApiError("The native review receipt has no valid server comment identity")
    try:
        created_at = datetime.fromisoformat(comment["created_at"])
    except (KeyError, TypeError, ValueError) as error:
        raise ApiError("The native review receipt has no valid server timestamp") from error
    if created_at.utcoffset() is None:
        raise ApiError("The native review receipt timestamp must include its timezone")
    try:
        state_line = lines[1]
        if not state_line.startswith("State: "):
            raise ValueError("Missing workflow state label")
        state = _RequestState(state_line.removeprefix("State: "))
    except (IndexError, ValueError) as error:
        raise ApiError("The native review receipt has no recognized workflow state") from error
    return _ReviewRequestReceipt(comment["id"], created_at, state)


def _request_receipt(
    client: GitHubClient, root: str, pr: dict[str, Any]
) -> _ReviewRequestReceipt | None:
    """Read and cache a durable receipt without caching the absence of one."""
    head = _sha(pr["head"]["sha"])
    key = (root, pr["number"], head)
    if key not in client._copilot_receipts:
        receipts = [
            receipt
            for comment in client.paginate(f"{root}/issues/{pr['number']}/comments")
            if (receipt := _parse_receipt(comment, head)) is not None
        ]
        if receipts:
            client._copilot_receipts[key] = min(receipts, key=lambda item: item.created_at)
    return client._copilot_receipts.get(key)


def _write_receipt(
    client: GitHubClient,
    root: str,
    pr: dict[str, Any],
    state: _RequestState,
    previous: _ReviewRequestReceipt | None = None,
) -> _ReviewRequestReceipt:
    """Persist and verify a state transition before trusting it or making a paid call."""
    head = _sha(pr["head"]["sha"])
    descriptions = {
        _RequestState.INTENT: "Native review request intent recorded while assessing commit ",
        _RequestState.ACCEPTED: "Native review request accepted while assessing commit ",
        _RequestState.OBSERVED: (
            "A pending native review request was observed while this commit was current: "
        ),
    }
    path = (
        f"{root}/issues/comments/{previous.comment_id}"
        if previous is not None
        else f"{root}/issues/{pr['number']}/comments"
    )
    comment = client.request(
        "PATCH" if previous is not None else "POST",
        path,
        {
            "body": _receipt_marker(head)
            + f"\nState: {state.value}\n"
            + descriptions[state]
            + head
            + ". This receipt does not indicate that a review is queued or running "
            "for this commit."
        },
    )
    if not isinstance(comment, dict) or (receipt := _parse_receipt(comment, head)) is None:
        raise ApiError("GitHub did not return a trusted native review acceptance receipt")
    if (
        receipt.state != state
        or previous is not None
        and (receipt.comment_id != previous.comment_id or receipt.created_at != previous.created_at)
    ):
        raise ApiError("GitHub did not preserve the native review receipt transition")
    client._copilot_receipts[(root, pr["number"], head)] = receipt
    return receipt


def _request_copilot(client: GitHubClient, root: str, pr: dict[str, Any]) -> _ReviewRequestReceipt:
    """Make at most one paid attempt after persisting an immutable-head intent."""
    identity = client.copilot_identity()
    receipt = _request_receipt(client, root, pr)
    if receipt is not None:
        return receipt
    if any(identity.matches(user) for user in pr.get("requested_reviewers", [])):
        return _write_receipt(client, root, pr, _RequestState.OBSERVED)
    intent = _write_receipt(client, root, pr, _RequestState.INTENT)
    client.request(
        "POST",
        f"{root}/pulls/{pr['number']}/requested_reviewers",
        {"reviewers": [COPILOT_REQUEST_LOGIN]},
    )
    return _write_receipt(client, root, pr, _RequestState.ACCEPTED, previous=intent)


def _escalate(
    client: GitHubClient,
    root: str,
    pr: dict[str, Any],
    reviewer: str,
    reasons: list[str],
    *,
    request_reviews: bool = True,
    request_copilot: bool = True,
) -> None:
    marker = f"<!-- ring5-dependency-automation:{pr['head']['sha']} -->"
    comments = client.paginate(f"{root}/issues/{pr['number']}/comments")
    existing = next(
        (
            comment
            for comment in comments
            if comment["user"]["login"] == "github-actions[bot]"
            and comment["user"].get("type") == "Bot"
            and marker in (comment.get("body") or "")
        ),
        None,
    )
    guidance = (
        "Copilot's review must identify affected APIs and scientific behavior, link upstream "
        "release or migration notes, and propose the source changes and regression tests needed "
        "to support this version. Inspect its review and the linked CI logs before deciding. "
        "Use **Fix with Copilot** to prepare an adaptation when appropriate. "
        if request_reviews and request_copilot
        else "Inspect the dependency changes, upstream migration notes "
        "and linked CI logs manually. "
    )
    body = (
        marker
        + f"\n@{reviewer}, this dependency update needs your attention.\n\n"
        + "\n".join(
            f"- {html.escape(reason).replace('@', '＠').replace('`', chr(39))}"
            for reason in reasons
        )
        + "\n\n"
        + guidance
        + "Source adaptations require human review. No approval or branch protection is bypassed.\n"
    )
    if existing is None:
        client.request("POST", f"{root}/issues/{pr['number']}/comments", {"body": body})
    elif existing.get("body") != body:
        client.request("PATCH", f"{root}/issues/comments/{existing['id']}", {"body": body})
    if request_reviews:
        reviews = client.paginate(f"{root}/pulls/{pr['number']}/reviews")
        completed = {
            review["user"]["login"]
            for review in reviews
            if review.get("commit_id") == pr["head"]["sha"] and review.get("state") != "PENDING"
        }
        if request_copilot:
            try:
                identity = client.copilot_identity()
                if not any(
                    identity.matches(review["user"])
                    and review.get("commit_id") == pr["head"]["sha"]
                    and review.get("state") != "PENDING"
                    for review in reviews
                ):
                    _request_copilot(client, root, pr)
            except ApiError:
                # Keep the notification visible while a later run retries unavailable review.
                pass
        if reviewer not in completed and not any(
            user["login"] == reviewer for user in pr.get("requested_reviewers", [])
        ):
            try:
                client.request(
                    "POST",
                    f"{root}/pulls/{pr['number']}/requested_reviewers",
                    {"reviewers": [reviewer]},
                )
            except ApiError:
                pass


def evaluate_pr(
    client: GitHubClient,
    repository: str,
    number: int,
    config: dict[str, Any],
    *,
    apply: bool = False,
    reviewer: str = "",
    now: datetime | None = None,
) -> Outcome:
    """Assess and optionally process one authenticated, dependency-only pull request."""
    root = _repo_path(repository)
    checked_at = now if now is not None else datetime.now(UTC)
    if checked_at.utcoffset() is None:
        raise ValueError("The review clock must include its timezone")
    pr = client.request("GET", f"{root}/pulls/{number}")
    head = _sha(pr["head"]["sha"])
    reviewer = reviewer or config.get("default_reviewer") or repository.split("/")[0]
    if not LOGIN.fullmatch(reviewer):
        raise ValueError("The escalation reviewer must be a GitHub user login")
    if not _eligible(pr, repository, config):
        return Outcome(number, head, "ignored", ("Not an eligible same-repository Dependabot PR",))

    def blocked(reasons: list[str], *, request_copilot: bool = True) -> Outcome:
        if apply:
            fresh = client.request("GET", f"{root}/pulls/{number}")
            if fresh["head"]["sha"] != head or not _eligible(fresh, repository, config):
                return Outcome(number, head, "waiting", ("PR changed before escalation",))
            _escalate(client, root, fresh, reviewer, reasons, request_copilot=request_copilot)
        return Outcome(number, head, "needs_review", tuple(reasons))

    commits = client.paginate(f"{root}/pulls/{number}/commits")
    if not commits or any(
        (commit.get("author") or {}).get("login") != DEPENDABOT
        or commit["commit"].get("verification", {}).get("verified") is not True
        for commit in commits
    ):
        return blocked(["Every PR commit must be signed and authored by Dependabot"])
    files = client.paginate(f"{root}/pulls/{number}/files")
    if len(files) != pr["changed_files"] or not files or len(files) > 10:
        return blocked(["The complete dependency diff is unavailable or exceeds the policy limit"])
    if any(file["status"] != "modified" or file.get("previous_filename") for file in files):
        return blocked(["Added, removed or renamed files require human review"])
    allowed = (
        {"pyproject.toml", "uv.lock", "Gemfile", "Gemfile.lock"}
        | {workflow["path"] for workflow in config["required_workflows"].values()}
        | {".github/workflows/pages.yml"}
    )
    if any(file["filename"] not in allowed for file in files):
        return blocked(["The PR changes files outside the dependency update allowlist"])
    base = _sha(client.request("GET", f"{root}/branches/{config['base_branch']}")["commit"]["sha"])
    comparison = client.request("GET", f"{root}/compare/{base}...{head}")
    if comparison.get("behind_by") != 0 or comparison.get("status") != "ahead":
        return Outcome(
            number,
            head,
            "waiting_update",
            ("Waiting for Dependabot to rebase onto current main and rerun compatibility CI",),
        )
    changes = {
        file["filename"]: (
            _content(client, root, file["filename"], pr["base"]["sha"]),
            _content(client, root, file["filename"], head),
        )
        for file in files
    }
    policy = assess_changes(changes, allow_major=config["allow_major"])
    if not policy.eligible:
        return blocked(
            list(policy.reasons),
            request_copilot=policy.native_reviewable,
        )
    _action_provenance(client, policy.updates)
    protection = protection_problems(client, root, config)
    if protection:
        return blocked(protection)
    pending, failed = _ci_state(client, root, pr, config, base)
    approved, review_problems = _review_state(client, root, pr, repository)
    if failed or review_problems:
        return blocked(failed + review_problems)
    if not approved:
        try:
            receipt = (
                _request_copilot(client, root, pr) if apply else _request_receipt(client, root, pr)
            )
        except ApiError:
            return blocked(
                ["The native review request or acceptance receipt could not be verified"],
                request_copilot=False,
            )
        if receipt is not None and receipt.state == _RequestState.INTENT:
            return blocked(
                [
                    "A durable native review intent has unconfirmed completion; automatic retry "
                    "is suppressed to avoid duplicate charges. "
                    "Inspect the existing request manually"
                ],
                request_copilot=False,
            )
        if receipt is not None and checked_at - receipt.created_at >= REVIEW_WAIT_LIMIT:
            return blocked(
                [
                    "No qualifying current-head native review was recorded within 24 hours of "
                    "the workflow receipt; inspect review availability and repository policy"
                ],
                request_copilot=False,
            )
        return Outcome(
            number, head, "waiting_copilot", ("Waiting for Copilot approval of this head",)
        )
    if pending:
        return Outcome(number, head, "waiting_checks", tuple(pending))
    fresh = client.request("GET", f"{root}/pulls/{number}")
    fresh_base = client.request("GET", f"{root}/branches/{config['base_branch']}")["commit"]["sha"]
    if (
        fresh["head"]["sha"] != head
        or fresh_base != base
        or fresh["base"]["sha"] != base
        or not _eligible(fresh, repository, config)
    ):
        return Outcome(
            number, head, "waiting", ("Head or main changed; a fresh evaluation is required",)
        )
    if (
        fresh.get("state") != "open"
        or fresh.get("draft")
        or fresh.get("mergeable_state") != "clean"
    ):
        return blocked(["GitHub merge protections or mergeability are not satisfied"])
    if not apply:
        return Outcome(number, head, "ready", ("All policy, review and CI gates pass",))
    try:
        result = client.request(
            "PUT", f"{root}/pulls/{number}/merge", {"sha": head, "merge_method": "squash"}
        )
    except ApiError:
        # A disconnected response does not imply that the server rejected the merge.
        reconciled = client.request("GET", f"{root}/pulls/{number}")
        if not (
            reconciled.get("merged") is True
            and reconciled.get("state") == "closed"
            and reconciled["head"]["sha"] == head
            and (reconciled["head"].get("repo") or {}).get("full_name") == repository
            and reconciled["base"]["ref"] == config["base_branch"]
            and (reconciled["base"].get("repo") or {}).get("full_name") == repository
        ):
            raise
        result = {"merged": True}
    if result.get("merged") is not True:
        return blocked(["GitHub refused the guarded merge; no protection bypass was attempted"])
    dispatch_failures = []
    for workflow in config["dispatch_after_merge"]:
        try:
            client.request(
                "POST",
                f"{root}/actions/workflows/{workflow}/dispatches",
                {"ref": config["base_branch"]},
            )
        except ApiError:
            dispatch_failures.append(workflow)
    if dispatch_failures:
        _escalate(
            client,
            root,
            pr,
            reviewer,
            [
                "The guarded merge succeeded; manually dispatch post-merge workflows: "
                + ", ".join(dispatch_failures)
            ],
            request_reviews=False,
        )
        return Outcome(number, head, "merged_dispatch_failed", tuple(dispatch_failures))
    return Outcome(
        number, head, "merged", ("Merged the reviewed head and dispatched main workflows",)
    )


def main() -> int:
    """Run in dry-run mode unless explicitly authorized by the trusted workflow."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(".github/dependency-automation.json"))
    parser.add_argument("--pr", type=int)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--check-configuration",
        action="store_true",
        help="Inspect native rules without processing PRs",
    )
    args = parser.parse_args()
    repository = os.environ["GITHUB_REPOSITORY"]
    root = _repo_path(repository)
    config = json.loads(args.config.read_text())
    if config["base_branch"] != "main" or type(config["allow_major"]) is not bool:
        raise ValueError("Only the explicit main-branch dependency policy is supported")
    if set(config["dispatch_after_merge"]) != {"ci.yml", "codeql.yml", "pages.yml"}:
        raise ValueError("Unexpected post-merge workflow configuration")
    client = GitHubClient(os.environ["GH_TOKEN"])
    if args.check_configuration:
        problems = protection_problems(client, root, config)
        print(
            json.dumps(
                {
                    "repository": repository,
                    "native_protection_problems": problems,
                    "required_contexts": [
                        job
                        for workflow in config["required_workflows"].values()
                        for job in workflow["jobs"]
                    ],
                    "copilot_setup": (
                        "Enable Copilot approving reviews and count approvals toward "
                        "merge requirements. Limit approval paths to the dependency allowlist. "
                        "A real current-head approval "
                        "and GitHub reviewDecision=APPROVED are verified for every merge."
                    ),
                    "mutations_performed": False,
                },
                indent=2,
            )
        )
        return int(bool(problems))
    if args.pr is not None:
        if args.pr <= 0:
            parser.error("--pr must be positive")
        numbers = [args.pr]
    else:
        event_name = os.environ.get("GITHUB_EVENT_NAME", "")
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        if event_name == "pull_request_target":
            numbers = [int(event["pull_request"]["number"])]
        elif event_name == "workflow_run":
            run = event["workflow_run"]
            numbers = (
                sorted({int(pr["number"]) for pr in run.get("pull_requests", [])})
                if run.get("event") == "pull_request"
                else []
            )
        else:
            prs = client.paginate(f"{root}/pulls?state=open&base=main")
            numbers = [pr["number"] for pr in prs if pr["user"]["login"] == DEPENDABOT]
            if len(numbers) > config["max_open_prs"]:
                raise ApiError("Open Dependabot PRs exceed the configured processing limit")
    outcomes = []
    for number in numbers:
        try:
            outcome = evaluate_pr(
                client,
                repository,
                number,
                config,
                apply=args.apply,
                reviewer=os.environ.get("DEPENDENCY_AUTOMATION_REVIEWER", ""),
            )
        except (ApiError, KeyError, TypeError, ValueError) as error:
            outcome = Outcome(number, "", "error", (f"Controller failed closed: {error}",))
            if args.apply:
                try:
                    fresh = client.request("GET", f"{root}/pulls/{number}")
                    if _eligible(fresh, repository, config):
                        reviewer = (
                            os.environ.get("DEPENDENCY_AUTOMATION_REVIEWER")
                            or config.get("default_reviewer")
                            or repository.split("/")[0]
                        )
                        if not LOGIN.fullmatch(reviewer):
                            raise ValueError("Invalid escalation reviewer")
                        _sha(fresh["head"]["sha"])
                        _escalate(client, root, fresh, reviewer, list(outcome.reasons))
                except (ApiError, KeyError, TypeError, ValueError):
                    # A failed job remains visible if GitHub also rejects the notification.
                    pass
        outcomes.append(asdict(outcome))
    report = json.dumps({"apply": args.apply, "outcomes": outcomes}, indent=2)
    print(report)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(summary).open("a") as stream:
            stream.write("## Dependency automation\n\n```json\n" + report + "\n```\n")
    return int(any(outcome["state"] in {"error", "merged_dispatch_failed"} for outcome in outcomes))


if __name__ == "__main__":
    raise SystemExit(main())
