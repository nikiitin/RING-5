"""Owned Streamlit subprocesses and collision-free browser diagnostics."""

from __future__ import annotations

import hashlib
import os
import re
import socket
import subprocess
import sys
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path


def free_loopback_port() -> int:
    """Return an available IPv4 loopback port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.bind(("127.0.0.1", 0))
        return int(connection.getsockname()[1])


def artifact_stem(nodeid: str, worker: str = "main") -> str:
    """Return a bounded diagnostic name unique to a test and worker.

    Args:
        nodeid: Complete pytest node identity, including its class and parameters.
        worker: Worker identity for concurrent browser runs.
    """
    digest = hashlib.sha256(nodeid.encode("utf-8")).hexdigest()[:16]
    label = re.sub(r"[^A-Za-z0-9._-]+", "_", nodeid)[-100:]
    worker_label = re.sub(r"[^A-Za-z0-9._-]+", "_", worker)[:32]
    return f"{worker_label}_{label}_{digest}"


@contextmanager
def running_streamlit(
    script: Path,
    *,
    port: int,
    environment: Mapping[str, str] | None = None,
    startup_timeout: float = 30.0,
) -> Iterator[str]:
    """Run a loopback-only server and always reap its process.

    Output inherits the runner streams so full log pipes cannot block the server.

    Args:
        script: Application entry point.
        port: Selected loopback port.
        environment: Environment overrides added to the caller's environment.
        startup_timeout: Maximum seconds to wait for the listening socket.

    Yields:
        Server base URL after its socket becomes reachable.

    Raises:
        RuntimeError: The server exits before becoming reachable.
        TimeoutError: Startup exceeds the deadline.
    """
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(script),
            "--server.port",
            str(port),
            "--server.address",
            "127.0.0.1",
            "--server.headless",
            "true",
            "--server.fileWatcherType",
            "none",
            "--browser.gatherUsageStats",
            "false",
        ],
        cwd=script.parent,
        env={**os.environ, **(environment or {})},
    )
    try:
        deadline = time.monotonic() + startup_timeout
        while True:
            if process.poll() is not None:
                raise RuntimeError(f"Streamlit exited during startup: {process.returncode}")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                    break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Streamlit did not start before the deadline.")
                time.sleep(0.1)
        yield f"http://127.0.0.1:{port}"
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
