"""#317 fold — clamp CasAttach [data-reveal-menu] inside the window.

Typed-open locks live in open_cas_attachment.py. This sibling only
locks the right-edge clip: openRevealMenu must keep Open / Reveal
on-screen via innerWidth / innerHeight and/or getBoundingClientRect.

Must-IDs: open-cas-menu-clamp.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.open_cas_attachment import _fn
from tauri_gate.scan import _without_comments

_ISSUE = "#317"
_RAW_CLICK = re.compile(
    r"revealMenu\s*=\s*\{\s*x\s*:\s*e\.clientX\s*,\s*y\s*:\s*e\.clientY"
)
_VIEW = re.compile(r"\binnerWidth\b|\binnerHeight\b")
_BOX = re.compile(r"\bgetBoundingClientRect\s*\(")
_MENU_HOOK = re.compile(r"data-reveal-menu|revealMenu")
_ADJ = re.compile(
    r"(?:"
    r"(?:style\.)?(?:left|top)\s*="
    r"|revealMenu\.(?:x|y)\s*="
    r"|\b(?:x|y)\s*=\s*(?:Math\.(?:min|max)|[^;\n]{0,80}inner(?:Width|Height))"
    r"|Math\.(?:min|max)\s*\("
    r"|innerWidth\s*-"
    r"|innerHeight\s*-"
    r")"
)


def _windows_around(src: str, rx: re.Pattern[str], before: int = 200, after: int = 280) -> str:
    bits: list[str] = []
    for m in rx.finditer(src):
        bits.append(src[max(0, m.start() - before) : m.end() + after])
    return "\n".join(bits)


def _clamp_blob(cas: str) -> str:
    parts = [_fn(cas, "openRevealMenu")]
    for name in (
        "clampRevealMenu",
        "placeRevealMenu",
        "positionRevealMenu",
        "clampMenu",
        "fitRevealMenu",
    ):
        parts.append(_fn(cas, name))
    for rx in (_VIEW, _BOX, _MENU_HOOK):
        for m in rx.finditer(cas):
            win = cas[max(0, m.start() - 220) : m.end() + 260]
            if _MENU_HOOK.search(win) or re.search(r"clientX|clientY", win):
                parts.append(win)
    return "\n".join(p for p in parts if p)


def _has_menu_clamp(cas: str) -> bool:
    blob = _clamp_blob(cas)
    has_view = bool(_VIEW.search(blob))
    has_box = bool(_BOX.search(blob) and _MENU_HOOK.search(blob))
    if not has_view and not has_box:
        return False
    return bool(_ADJ.search(blob))


def assert_open_cas_menu_clamp(crate: Path) -> None:
    """#317 fold: keep [data-reveal-menu] fully inside the window."""
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    if not cas_path.is_file():
        fail(f"{_ISSUE}: CasAttach.svelte required (clamp data-reveal-menu)")
    cas_raw = cas_path.read_text()
    cas = _without_comments(cas_raw)
    opener = _fn(cas, "openRevealMenu") or _fn(cas_raw, "openRevealMenu")
    if not opener.strip():
        fail(
            f"{_ISSUE}: openRevealMenu required "
            "(clamp [data-reveal-menu] so Open / Reveal stay on-screen)"
        )
    if _RAW_CLICK.search(opener) and not _has_menu_clamp(cas):
        fail(
            f"{_ISSUE}: openRevealMenu must clamp [data-reveal-menu] "
            "inside the window (innerWidth / innerHeight and/or "
            "getBoundingClientRect) — do not pin at clientX/clientY"
        )
    if not _has_menu_clamp(cas):
        fail(
            f"{_ISSUE}: [data-reveal-menu] left/top (or x/y) must stay "
            "inside the window — measure innerWidth / innerHeight "
            "and/or getBoundingClientRect and adjust when the click "
            "is near the right (or bottom) edge"
        )
    if "data-reveal-menu" not in cas_raw:
        fail(f"{_ISSUE}: keep data-reveal-menu (clamp is additive)")
    style_win = _windows_around(
        cas_raw, re.compile(r"data-reveal-menu"), before=280, after=80
    )
    if not re.search(r"\bleft\b|\btop\b|revealMenu\.(?:x|y)", style_win):
        fail(
            f"{_ISSUE}: [data-reveal-menu] must still position with "
            "left/top (or x/y) — clamp that box, do not drop the menu"
        )
