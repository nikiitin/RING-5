"""Owned Streamlit subprocesses and collision-free browser diagnostics."""

from __future__ import annotations

import hashlib
import os
import re
import socket
import subprocess
import sys
import time
import uuid
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


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
        startup_timeout: Maximum seconds to wait for the owned health endpoint.

    Yields:
        Server URL under an invocation-specific path after it becomes healthy.

    Raises:
        RuntimeError: The port is occupied or the server exits during startup.
        TimeoutError: Startup exceeds the deadline.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reservation:
        try:
            reservation.bind(("127.0.0.1", port))
        except OSError as exc:
            raise RuntimeError(f"Streamlit test port {port} is already occupied.") from exc
    # A fresh base path distinguishes this invocation even if another listener
    # wins the small bind-to-launch race after the availability check.
    base_path = f"_ring5_test_{uuid.uuid4().hex}"
    url = f"http://127.0.0.1:{port}/{base_path}"
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
            "--server.baseUrlPath",
            base_path,
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
                with urlopen(url + "/_stcore/health", timeout=0.5) as response:
                    healthy = response.status == 200 and response.read(16) == b"ok"
                if healthy and process.poll() is None:
                    break
            except (OSError, URLError):
                pass
            if time.monotonic() >= deadline:
                raise TimeoutError("Streamlit did not start before the deadline.")
            time.sleep(0.1)
        yield url
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
