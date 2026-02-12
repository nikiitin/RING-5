"""Conftest for tests/unit/export/ — LaTeX export tests."""

import shutil

import pytest

has_xelatex = shutil.which("xelatex") is not None
requires_xelatex = pytest.mark.skipif(not has_xelatex, reason="XeLaTeX not found")
