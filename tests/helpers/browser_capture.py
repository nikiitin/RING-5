"""One trace owner for shared browser setup and per-test failure artifacts."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest
from playwright.sync_api import BrowserContext, Page, TimeoutError as PlaywrightTimeoutError

from tests.helpers.streamlit_server import artifact_stem


@dataclass
class _SharedPageCapture:
    """Retain the class setup chunk until a function capture takes ownership."""

    page: Page
    tracing: bool = False
    chunk_active: bool = False
    setup_failure_saved: bool = False


_SHARED_PAGE_CAPTURE = pytest.StashKey[_SharedPageCapture]()


def _shared_capture_for_node(node: pytest.Collector | pytest.Item) -> _SharedPageCapture | None:
    """Find only an explicitly registered ancestor's shared-page capture."""
    for owner in reversed(node.listchain()):
        capture = owner.stash.get(_SHARED_PAGE_CAPTURE, None)
        if capture is not None:
            return capture
    return None


def _tracing_enabled() -> bool:
    """Read the browser runner's existing tracing switch."""
    return os.environ.get("TRACING", "").lower() in ("1", "true", "yes")


@contextmanager
def shared_page_capture(
    context: BrowserContext, node: pytest.Collector | pytest.Item
) -> Iterator[Page]:
    """Own one class page, its setup trace, and context teardown."""
    try:
        page = context.new_page()
        capture = _SharedPageCapture(page)
        node.stash[_SHARED_PAGE_CAPTURE] = capture
        try:
            if _tracing_enabled():
                context.tracing.start(screenshots=True, snapshots=True, sources=True)
                capture.tracing = True
                capture.chunk_active = True
            yield page
        finally:
            try:
                if capture.tracing:
                    context.tracing.stop()
            finally:
                del node.stash[_SHARED_PAGE_CAPTURE]
    finally:
        context.close()


def _save_failure_screenshot(page: Page, nodeid: str, artifacts_dir: Path) -> str:
    """Save the existing page without extending the screenshot deadline."""
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    name = artifact_stem(nodeid, os.environ.get("PYTEST_XDIST_WORKER", "main"))
    if not page.is_closed():
        try:
            page.screenshot(
                path=str(artifacts_dir / f"{name}_failure.png"),
                full_page=True,
                timeout=10_000,
            )
        except PlaywrightTimeoutError:
            # Diagnostics must not hold the browser job open.
            pass
    return name


def _stop_shared_chunk(capture: _SharedPageCapture, path: Path | None = None) -> None:
    """Release chunk ownership even when saving its trace fails."""
    try:
        capture.page.context.tracing.stop_chunk(path=path)
    finally:
        capture.chunk_active = False


@contextmanager
def capture_failure_artifacts(
    request: pytest.FixtureRequest, artifacts_dir: Path
) -> Iterator[None]:
    """Capture the active page's setup/call failure without creating another page."""
    if "page" in request.fixturenames:
        page: Page = request.getfixturevalue("page")
    elif "shared_page" in request.fixturenames:
        page = request.getfixturevalue("shared_page")
    else:
        yield
        return

    context = page.context
    shared_capture = _shared_capture_for_node(request.node)
    if shared_capture is not None and shared_capture.page.context is not context:
        # Autouse app setup may own another context than an explicit component page.
        shared_capture = None
    tracing = _tracing_enabled()
    if tracing:
        if shared_capture is not None:
            if shared_capture.chunk_active:
                _stop_shared_chunk(shared_capture)
            context.tracing.start_chunk()
            shared_capture.chunk_active = True
        else:
            context.tracing.start(screenshots=True, snapshots=True, sources=True)

    try:
        yield
    finally:
        trace_path = None
        try:
            reports = [getattr(request.node, name, None) for name in ("rep_setup", "rep_call")]
            if any(report is not None and report.failed for report in reports):
                name = _save_failure_screenshot(page, request.node.nodeid, artifacts_dir)
                trace_path = artifacts_dir / f"{name}_trace.zip"
        finally:
            if tracing:
                if shared_capture is not None:
                    _stop_shared_chunk(shared_capture, trace_path)
                else:
                    context.tracing.stop(path=trace_path)


def save_setup_failure(item: pytest.Item, report: pytest.TestReport, artifacts_dir: Path) -> None:
    """Retain the first class setup failure before function capture can run."""
    if report.when != "setup" or not report.failed:
        return
    capture = _shared_capture_for_node(item)
    if (
        capture is None
        or "_capture_failure_artifacts" in cast(pytest.Function, item).funcargs
        or capture.setup_failure_saved
    ):
        return

    # Cached setup errors must not replace the original failed state.
    capture.setup_failure_saved = True
    try:
        name = _save_failure_screenshot(capture.page, item.nodeid, artifacts_dir)
        details = [report.longreprtext]
        details.extend(f"{title}\n{text}" for title, text in report.sections)
        (artifacts_dir / f"{name}_setup.txt").write_text("\n\n".join(details), encoding="utf-8")
    finally:
        if capture.tracing and capture.chunk_active:
            name = artifact_stem(item.nodeid, os.environ.get("PYTEST_XDIST_WORKER", "main"))
            _stop_shared_chunk(capture, artifacts_dir / f"{name}_trace.zip")
