"""Leaf hue/spinner tokens. Imported by import_boot and status_toasts (no cycle)."""
from __future__ import annotations

import re

from tauri_gate.scan import _strip_html_comments, _without_comments


def _hue_surface(text: str) -> str:
    return _without_comments(_strip_html_comments(text))


_HUE_AMBER = re.compile(r"\bamber-\d+")
_SPINNER_NAME = re.compile(
    r"("
    r"\bspinner\b"
    r"|boot-spinner"
    r"|loading-spinner"
    r"|data-boot-spinner"
    r"|data-spinner"
    r")",
    re.I,
)

__all__ = [
    "_hue_surface",
    "_HUE_AMBER",
    "_SPINNER_NAME",
]
