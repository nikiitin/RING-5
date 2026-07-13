"""Conftest for UI AppTest tests.

Streamlit 1.53.1 had a bug where ``ButtonGroup.indices`` iterated over the
characters of a single-selection string value instead of treating it as one
item, which previously required a monkey-patch here. That bug was fixed
upstream in Streamlit 1.58 (``indices`` now derives from ``formatted_values``),
so the patch is obsolete and has been removed. This file is kept as the
package marker for the UI test suite.
"""

from __future__ import annotations
