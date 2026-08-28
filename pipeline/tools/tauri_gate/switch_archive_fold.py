"""#308 review-fold — PR #328 (stale peopleGen, leftover chrome,
dummy greps).

Additive checks for IN Do 1–4. Existing assert_switch_archive
keep-checks 1–12 stay (fail prefixes untouched). setSetup / named-reset
clears count; dummy void locals are not required. Placeholders
ArchiveA / ArchiveB / Ada.

Must-IDs: switch-bump-gen, switch-reset-chrome,
switch-ignore-view-on-setup, switch-no-dummy-greps.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.recent_archives import _named_bodies, _read
from tauri_gate.scan import (
    _call_arg,
    _match_closer,
    _tauri_rust_blob,
    _web_logic,
    _without_comments,
)
from tauri_gate.switch_archive import (
    _CLOSE_JS,
    _MENU_FNS,
    _js_body,
)

_PEOPLE_GEN_BUMP = re.compile(
    r"\+\+\s*peopleGen|\bpeopleGen\s*\+\+|\bpeopleGen\s*\+=\s*1\b"
    r"|\bpeopleGen\s*=\s*peopleGen\s*\+\s*1\b"
)
_ERR_CLEAR = re.compile(r"""\berr\s*=\s*["']{2}""")
_FILTER_CLEAR = re.compile(r"""\bfilter\s*=\s*["']{2}""")
_SEARCHQ_CLEAR = re.compile(r"""\bsearchQ\s*=\s*["']{2}""")
_SEED_CLEAR = re.compile(r"\bseedPerson\s*=\s*null\b")
_GROUPS_CLEAR = re.compile(r"\bincludeGroups\s*=\s*false\b")
_IDENT_CLEAR = re.compile(r"\bidentities\s*=\s*\[\s*\]")
_TITLE_CLEAR = re.compile(
    r"""\bpersonTitle\s*=\s*(?:["']Select a person["']|["']{2})"""
)
_VIEW_PEOPLE = re.compile(r"""\bview\s*=\s*["']people["']""")
_SETUP_TOKEN = re.compile(r"\b(?:ctx\.)?setup\b")
_JOIN_SWITCH = re.compile(
    r"""\[\s*["']menu["']\s*,\s*["']switch["']\s*,\s*["']archive["']\s*\]"""
    r"""\s*\.join\s*\(\s*["']-["']\s*\)"""
)
_LITERAL_LISTEN = re.compile(r"""listen\s*\(\s*["'`]menu-switch-archive["'`]""")
_VOID_BAIT = re.compile(
    r"void\s*\[\s*(?:people|selectedId|events|st|doctor)\b"
)
_SPEC_LET = re.compile(r"""let\s+_\s*=\s*(?:r#*)?["']""")
_TEXT_IMPORT = re.compile(r"""\.text\s*\(\s*["']menu-import["']""")
_TEXT_VIEW = re.compile(r"""\.text\s*\(\s*["']view-people["']""")
_ARCHIVE_FLAG = re.compile(r"\b(?:is_some|is_none|setup)\b")
_SKIP_CALLS = frozenset(
    {
        "if",
        "for",
        "while",
        "switch",
        "catch",
        "await",
        "void",
        "return",
        "listen",
        "api",
        "invoke",
        "removeItem",
        "String",
        "Error",
        "Promise",
        "console",
        "Math",
        "Number",
        "Boolean",
        "closeArchive",
        "showErr",
        "friendly",
        "tick",
        "setTimeout",
    }
)


def _reset_surface(web: str) -> str:
    """setSetup / switchToSetup / named-reset bodies plus one callee hop."""
    chunks: list[str] = []
    seen: set[str] = set()
    for name in _CLOSE_JS:
        body = _js_body(web, name)
        if body:
            chunks.append(body)
            seen.add(name)
    blob = "\n".join(chunks)
    for name in re.findall(r"\b([A-Za-z_]\w*)\s*\(", blob):
        if name in seen or name in _SKIP_CALLS:
            continue
        seen.add(name)
        inner = _js_body(web, name)
        if inner:
            chunks.append(inner)
    return "\n".join(chunks)


def _listen_for(src: str, event: str) -> str:
    chunks: list[str] = []
    needle = "listen"
    i = 0
    while True:
        at = src.find(needle, i)
        if at < 0:
            break
        j = at + len(needle)
        while j < len(src) and src[j].isspace():
            j += 1
        if j < len(src) and src[j] == "(":
            arg = _call_arg(src, j)
            head = arg[:120]
            if re.search(rf"""["'`]{re.escape(event)}["'`]""", head):
                chunks.append(arg)
        i = at + 1
    return "\n".join(chunks)


def _switch_arm(rust: str) -> str:
    m = re.search(r"""["']switch-archive["']\s*=>\s*\{""", rust)
    if not m:
        return ""
    open_b = rust.find("{", m.start())
    if open_b < 0:
        return ""
    close_b = _match_closer(rust, open_b)
    if close_b < 0:
        return rust[open_b + 1 :]
    return rust[open_b + 1 : close_b]


def _menu_disables_view_import(menu: str) -> bool:
    """True when Import + View items are disabled with no archive open."""
    if _TEXT_IMPORT.search(menu) or _TEXT_VIEW.search(menu):
        return False
    if not _ARCHIVE_FLAG.search(menu):
        return False
    has_import = bool(
        re.search(
            r"""with_id\s*\([^)]*["'](?:menu-import|Import)["']""",
            menu,
        )
        or re.search(
            r"""["']menu-import["'][^;]{0,160}\b(?:switch_on|chrome_on|open)\b""",
            menu,
        )
    )
    has_view = bool(
        re.search(r"""with_id\s*\([^)]*["']view-people["']""", menu)
        or re.search(
            r"""["']view-people["'][^;]{0,160}\b(?:switch_on|chrome_on|open)\b""",
            menu,
        )
    )
    return has_import and has_view


def _view_import_ignored_or_disabled(web: str, menu: str) -> bool:
    if _SETUP_TOKEN.search(_js_body(web, "setView")):
        return True
    view_l = _listen_for(web, "menu-view")
    import_l = _listen_for(web, "menu-import")
    if _SETUP_TOKEN.search(view_l) and _SETUP_TOKEN.search(import_l):
        return True
    return _menu_disables_view_import(menu)


def assert_switch_archive_fold(crate: Path) -> None:
    """#308 review-fold: bump peopleGen, reset chrome, ignore View on setup.

    Dummy join / void-locals / let _ spec strings are banned.
    """
    rust = _without_comments(_tauri_rust_blob(crate))
    web = _without_comments(_web_logic(crate))
    menu_rs = _without_comments(_read(crate / "src" / "menu.rs"))
    menu = _named_bodies(rust, _MENU_FNS) or menu_rs
    reset = _reset_surface(web)

    # 1) switch-bump-gen — Switch / setSetup(true) increments peopleGen,
    #    clears err, so a stale refreshPeople cannot paint setup.
    if not _PEOPLE_GEN_BUMP.search(reset):
        fail(
            "#308: Switch / setSetup(true) must increment peopleGen "
            "(stale refreshPeople after Open ArchiveA must not paint setup "
            "with the false import-running banner)"
        )
    if not _ERR_CLEAR.search(reset):
        fail(
            "#308: Switch / setSetup(true) must set err = \"\" "
            "(do not leave ArchiveA’s error / false import-running banner "
            "on setup)"
        )

    # 2) switch-reset-chrome — leftover filter / search / Review chrome.
    if not _FILTER_CLEAR.search(reset):
        fail(
            "#308: close-to-setup must reset filter = \"\" "
            "(Open ArchiveB must not inherit ArchiveA’s leftover filter)"
        )
    if not _SEARCHQ_CLEAR.search(reset):
        fail(
            "#308: close-to-setup must reset searchQ = \"\" "
            "(placeholders ArchiveA / ArchiveB / Ada)"
        )
    if not _SEED_CLEAR.search(reset):
        fail("#308: close-to-setup must reset seedPerson = null")
    if not _GROUPS_CLEAR.search(reset):
        fail("#308: close-to-setup must reset includeGroups = false")
    if not _IDENT_CLEAR.search(reset):
        fail("#308: close-to-setup must reset identities = []")
    if not _TITLE_CLEAR.search(reset):
        fail(
            "#308: close-to-setup must reset personTitle "
            "(Select a person / empty; do not leave ArchiveA’s title)"
        )
    if not _VIEW_PEOPLE.search(reset):
        fail(
            "#308: close-to-setup must set view = \"people\" "
            "(Open ArchiveB must not land on Review)"
        )

    # 3) switch-ignore-view-on-setup
    if not _view_import_ignored_or_disabled(web, menu):
        fail(
            "#308: View / Import menu listeners must not assign view while "
            "setup is true (or disable those items when no archive is open)"
        )

    # 4) switch-no-dummy-greps
    if not _LITERAL_LISTEN.search(web):
        fail(
            "#308: listen must use literal \"menu-switch-archive\" "
            "(not [\"menu\",\"switch\",\"archive\"].join(\"-\"))"
        )
    if _JOIN_SWITCH.search(web):
        fail(
            "#308: do not listen via [\"menu\",\"switch\",\"archive\"].join(\"-\") "
            "(use the literal event name)"
        )
    if _VOID_BAIT.search(web):
        fail(
            "#308: do not allocate unused void [people, …] bait in "
            "switchToSetup (real clears live in setSetup / a named reset)"
        )
    if _SPEC_LET.search(_switch_arm(rust)):
        fail(
            "#308: do not leave let _ = \"…\" spec-narration strings on the "
            "Switch menu arm"
        )
