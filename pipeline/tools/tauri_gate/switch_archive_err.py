"""#308 err-fold — PR #328 review 2 (boot err wiped, leftover
view writers, confirm survives Switch).

Additive checks for IN Do 1–3. Existing assert_switch_archive
keep-checks 1–12 and review-fold 1–4 stay (fail prefixes
untouched). setSetup must not wipe err; switchToSetup (or a
named helper) still clears after a successful close. Placeholders
ArchiveA / ArchiveB / Ada.

Must-IDs: switch-keep-boot-err, switch-guard-view-writers,
switch-dismiss-confirm.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.scan import _web_logic, _without_comments
from tauri_gate.switch_archive import _js_body
from tauri_gate.switch_archive_fold import (
    _ERR_CLEAR,
    _PEOPLE_GEN_BUMP,
    _SETUP_TOKEN,
    _SKIP_CALLS,
    _reset_surface,
)

_CONFIRM_OPEN_CLEAR = re.compile(r"\bconfirmOpen\s*=\s*false\b")
_CONFIRM_RUN_CLEAR = re.compile(r"\bconfirmRun\s*=\s*null\b")
_VIEW_ASSIGN = re.compile(
    r"""\bview\s*=\s*(?:["'](?:people|search|review|import|doctor)["']|\w+)"""
)
_SET_VIEW_CALL = re.compile(r"\bsetView\s*\(")
_SETUP_GUARD = re.compile(
    r"\bif\s*\(\s*(?:ctx\.)?setup\s*\)\s*return"
    r"|\bif\s*\(\s*!\s*(?:ctx\.)?setup\s*\)"
)
_SHOWERR_THEN_SETUP = re.compile(
    r"(?:ctx\.)?showErr\s*\(\s*\w+\s*\)\s*;\s*(?:ctx\.)?setSetup\s*\(\s*true\s*\)"
)
_VIEW_WRITERS = ("whenSearchPaneReady", "runCommandView", "importDroppedPaths")


def _named_plus_callees(web: str, name: str, skip: frozenset[str] | None = None) -> str:
    """Named function / object-method body plus one callee hop."""
    chunks: list[str] = []
    seen: set[str] = set(skip or ())
    seen.add(name)
    body = _js_body(web, name)
    if body:
        chunks.append(body)
    for callee in re.findall(r"\b([A-Za-z_]\w*)\s*\(", body):
        if callee in seen or callee in _SKIP_CALLS:
            continue
        seen.add(callee)
        inner = _js_body(web, callee)
        if inner:
            chunks.append(inner)
    return "\n".join(chunks)


def _set_view_guarded(web: str) -> bool:
    return bool(_SETUP_TOKEN.search(_js_body(web, "setView")))


def _consults_setup_before_view(web: str, name: str) -> bool:
    """True when `name` consults setup before assigning view, or calls guarded setView."""
    body = _js_body(web, name)
    if not body:
        return False
    setup_m = _SETUP_GUARD.search(body) or _SETUP_TOKEN.search(body)
    view_m = _VIEW_ASSIGN.search(body)
    uses_set_view = bool(_SET_VIEW_CALL.search(body)) and _set_view_guarded(web)
    if view_m is None:
        return bool(setup_m) or uses_set_view
    if setup_m and setup_m.start() < view_m.start():
        return True
    return False


def assert_switch_archive_err(crate: Path) -> None:
    """#308 err-fold: keep boot err, guard leftover view writers, dismiss confirm."""
    web = _without_comments(_web_logic(crate))
    setup_surface = _named_plus_callees(web, "setSetup")
    switch_surface = _named_plus_callees(web, "switchToSetup", frozenset({"setSetup"}))
    reset = _reset_surface(web)

    # 1) switch-keep-boot-err — setSetup must not wipe the last-archive banner.
    if _ERR_CLEAR.search(setup_surface):
        fail(
            "#308: setSetup must not set err = \"\" "
            "(boot showErr then setSetup(true) must keep the last-archive fail, "
            "including the lock-holder path)"
        )
    if not _ERR_CLEAR.search(switch_surface):
        fail(
            "#308: switchToSetup (or a named helper it calls) must set "
            "err = \"\" after a successful close "
            "(Switch itself is a clean setup; do not leave ArchiveA’s error banner)"
        )
    if not _PEOPLE_GEN_BUMP.search(reset):
        fail(
            "#308: peopleGen increment must stay on the Switch / setSetup / "
            "named-reset path (stale People load after Open ArchiveA must not "
            "paint setup with the false import-running banner)"
        )
    if not _SHOWERR_THEN_SETUP.search(_js_body(web, "startPeopleBoot")):
        fail(
            "#308: boot last-archive fail must showErr then setSetup(true) "
            "(lock-holder banner must remain on setup)"
        )

    # 2) switch-guard-view-writers — leftover view = after Switch.
    for name in _VIEW_WRITERS:
        if not _consults_setup_before_view(web, name):
            fail(
                f"#308: {name} must consult setup before assigning view "
                "(or call the guarded setView) so ⌘F / palette / drop after "
                "Switch does not leave Search / Import as the next view after "
                "Open ArchiveB"
            )

    # 3) switch-dismiss-confirm — App-level ConfirmDialog survives Switch.
    if not _CONFIRM_OPEN_CLEAR.search(reset):
        fail(
            "#308: close-to-setup / setSetup(true) must set confirmOpen = false "
            "(App-level ConfirmDialog must not survive Switch onto ArchiveB)"
        )
    if not _CONFIRM_RUN_CLEAR.search(reset):
        fail(
            "#308: close-to-setup / setSetup(true) must set confirmRun = null "
            "(open-link / merge / unlink / undo must not run against ArchiveB’s ids)"
        )
