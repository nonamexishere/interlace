"""#315 — ⌘C / Ctrl+C copies the selected timeline bubble.

PeopleKeys binds meta/ctrl+c to TimelineList.copySelected. Same End-style
focus. Same plain payload as Copy text. Fields keep native copy.

Must-IDs: copy-selected-cmd, copy-same-as-menu, copy-field-native,
copy-keep-215, copy-keep-135, copy-fail-toast, copy-keep-132,
copy-not-html, copy-not-multi, copy-d24.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.import_boot_guards import _input_guard_span
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.palette_lib import (
    _CLIPBOARD_PLUGIN,
    _KEY_CMD_V,
    _KEY_CMD_X,
    _PALETTE_READ_TEXT,
)
from tauri_gate.scan import (
    _expand_fn_calls,
    _function_body,
    _ts_fn_body,
    _without_comments,
)
from tauri_gate.status_toasts_chrome import _WRITE_TEXT
from tauri_gate.status_toasts_extra2 import _toast_args_include_body

_ISSUE = "#315"
_KEY_C = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']c[\"']"
    r"|[\"']c[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*===?\s*[\"']C[\"']"
    r"|[\"']C[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*\.\s*toLowerCase\s*\(\s*\)\s*===?\s*[\"']c[\"']"
    r"|(?:e\.)?code\s*===?\s*[\"']KeyC[\"']"
)
_COPY_SEL = re.compile(r"\bcopySelected\s*\(|\.copySelected\b")
_MOD = re.compile(r"\b(?:(?:e\.)?metaKey|(?:e\.)?ctrlKey|\bmod\b)")
_NO_ALT = re.compile(r"\bmod\b|!\s*(?:e\.)?altKey")
_END = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']End[\"']|[\"']End[\"']\s*===?\s*(?:e\.)?key"
)
_HOME = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']Home[\"']"
    r"|[\"']Home[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?code\s*===?\s*[\"']Home[\"']"
)
_ARROW_UP = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']ArrowUp[\"']"
    r"|[\"']ArrowUp[\"']\s*===?\s*(?:e\.)?key"
)
_KEY_J = re.compile(r"(?:e\.)?key\s*===?\s*[\"']j[\"']|[\"']j[\"']\s*===?\s*(?:e\.)?key")
_KEY_K = re.compile(r"(?:e\.)?key\s*===?\s*[\"']k[\"']|[\"']k[\"']\s*===?\s*(?:e\.)?key")
_WALK = re.compile(r"\b(?:setTlIndex|ensureTlIndexVisible|visibleTlIndices)\b")
_PREPEND = re.compile(r"\b(?:prependOlder|loadOlder|onPrepend)\s*\(")
_PIN = re.compile(r"\b(?:scrollToLatest|pinTimelineLatest)\b")
_PAYLOAD = re.compile(
    r"body_text\s*\|\|[\s\S]{0,40}subject\s*\|\|\s*[\"']{2}"
    r"|body_text\s*\|\|\s*(?:[\w.]+)?subject"
)
_SKIP_EMPTY = re.compile(
    r"if\s*\(\s*!\s*(?:text|body|plain|s|payload)\s*\)\s*return"
    r"|if\s*\(\s*(?:text|body|plain|s|payload)\s*===?\s*[\"']{2}"
)
_NO_ROW = re.compile(
    r"tlIndex\s*<\s*0"
    r"|!\s*(?:row|item|hit|entry|found|cur)"
    r"|===\s*(?:undefined|null)"
    r"|==\s*null"
)
_MULTI = re.compile(
    r"\.forEach\s*\("
    r"|for\s*\(\s*(?:const|let|var)\b"
    r"|for\s*\(\s*\w+\s+of\b"
    r"|selectedIds|tlIndexes|selectedRows"
)
_HTML = re.compile(r"text/html|ClipboardItem|\binnerHTML\b|clipboard\.write\s*\(")
_DOM = re.compile(r"\binnerText\b|\btextContent\b")
_EXTRA_ID = re.compile(r"#tl-find|data-tl-find|data-chrome-search")
_COPY_EVT = re.compile(r"addEventListener\s*\(\s*[\"']copy[\"']")
_T_CALL = re.compile(r"""\bt\s*\(\s*["']([A-Za-z_][\w]*)["']""")
_DOCS_CMD = re.compile(
    r"(?:⌘\s*C|⌘C|Cmd\s*\+\s*C|Ctrl\s*\+\s*C).{0,220}"
    r"(?:highlighted|selected|bubble|plain)"
    r"|(?:highlighted|selected)\s+bubble.{0,220}"
    r"(?:⌘\s*C|⌘C|Ctrl\s*\+\s*C|copy)",
    re.I | re.S,
)
_DOCS_PLAIN = re.compile(r"plain(?:\s+text|\s+body)|body(?:'s)?\s+plain", re.I)
_DOCS_FIELD = re.compile(
    r"(?:#q|people filter|#person-filter|person-filter).{0,200}"
    r"(?:native|field|still cop)"
    r"|(?:native|field).{0,200}"
    r"(?:#q|people filter|#person-filter|person-filter)",
    re.I | re.S,
)


def _fn(src: str, name: str) -> str:
    return _ts_fn_body(src, name) or _function_body(src, name) or ""


def _near(src: str, m: re.Match[str], before: int = 200, after: int = 420) -> str:
    return src[max(0, m.start() - before) : m.end() + after]


def _is_mod_c(src: str, m: re.Match[str]) -> bool:
    window = _near(src, m, 160, 160)
    if not _MOD.search(window):
        return False
    return bool(_NO_ALT.search(window) or re.search(r"\bctrlKey\b", window))


def _c_hits(src: str) -> list[re.Match[str]]:
    return [m for m in _KEY_C.finditer(src) if _is_mod_c(src, m)]


def _people_gated(src: str, pos: int) -> bool:
    head = src[:pos]
    if re.search(r"view\s*!==?\s*[\"']people[\"']", head):
        return True
    return bool(re.search(r"view\s*===?\s*[\"']people[\"']", src[max(0, pos - 400) : pos + 80]))


def _after_guard(src: str, pos: int) -> bool:
    guard = _input_guard_span(src)
    return bool(guard and guard[0] < pos and guard[1] <= pos)


def _steal_has_c(src: str) -> bool:
    guard = _input_guard_span(src)
    return bool(guard and _KEY_C.search(src[guard[0] : guard[1]]))


def _on_fail_only_catch(blob: str) -> bool:
    for m in re.finditer(r"\bonCopyFail\s*\(", blob):
        if not re.search(r"\bcatch\b", blob[max(0, m.start() - 160) : m.start()]):
            return False
    return bool(re.search(r"\bonCopyFail\s*\(", blob))


def assert_copy_selected_bubble(crate: Path) -> None:
    """#315: ⌘C copies the highlighted bubble; fields keep native copy."""
    keys_path = crate / "web" / "lib" / "PeopleKeys.ts"
    app_path = crate / "web" / "App.svelte"
    list_path = crate / "web" / "lib" / "TimelineList.svelte"
    pane_path = crate / "web" / "lib" / "TimelinePane.svelte"
    shell_path = crate / "web" / "lib" / "PeopleShell.svelte"
    menu_path = crate / "web" / "lib" / "TimelineCopyMenu.svelte"
    pal_path = crate / "web" / "lib" / "CommandPalette.svelte"
    mail_path = crate / "web" / "lib" / "TimelineMail.ts"
    if not keys_path.is_file():
        fail(f"{_ISSUE}: PeopleKeys.ts required (⌘C / Ctrl+C → copySelected)")
    if not app_path.is_file():
        fail(f"{_ISSUE}: App.svelte required (wire copySelected on the key ctx)")
    if not list_path.is_file():
        fail(f"{_ISSUE}: TimelineList.svelte required (export copySelected)")
    if not pane_path.is_file():
        fail(f"{_ISSUE}: TimelinePane.svelte required (export copySelected)")
    if not shell_path.is_file():
        fail(f"{_ISSUE}: PeopleShell.svelte required (onCopyFail + pane type)")

    keys_c = _without_comments(keys_path.read_text())
    app_c = _without_comments(app_path.read_text())
    list_c = _without_comments(list_path.read_text())
    pane_c = _without_comments(pane_path.read_text())
    shell_c = _without_comments(shell_path.read_text())
    mail_c = _without_comments(mail_path.read_text()) if mail_path.is_file() else ""
    handle = _fn(keys_c, "handleAppKey") or keys_c
    handle_x = _expand_fn_calls(keys_c, handle, 2)
    on_key = _fn(app_c, "onKey") or app_c
    home_fn = _fn(keys_c, "preventNativeHomeScroll")
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) copy-selected-cmd — fail-today: no key === "c" / KeyC in PeopleKeys.
    hits = _c_hits(handle_x)
    if not hits or not any(_COPY_SEL.search(_near(handle_x, m, 80, 360)) for m in hits):
        fail(
            f"{_ISSUE}: PeopleKeys must bind ⌘C / Ctrl+C "
            "(metaKey or ctrlKey without alt + c/C) to copySelected when a "
            "timeline bubble is highlighted"
        )
    if not _c_hits(handle) and not _c_hits(keys_c):
        fail(
            f"{_ISSUE}: ⌘C / Ctrl+C must live on the PeopleKeys window "
            "handler (handleAppKey — not App.svelte-only, not capture-phase)"
        )
    if _KEY_C.search(home_fn) or _COPY_SEL.search(home_fn):
        fail(
            f"{_ISSUE}: preventNativeHomeScroll stays Home / ⌘↑ only "
            "(do not bind capture-phase ⌘C)"
        )
    if _COPY_EVT.search(keys_c) or _COPY_EVT.search(list_c):
        fail(
            f"{_ISSUE}: bind ⌘C on PeopleKeys keydown, not a window copy event"
        )
    for m in re.finditer(r"addEventListener\s*\(\s*[\"']keydown[\"']", app_c):
        window = app_c[m.start() : m.end() + 120]
        if not re.search(r",\s*true\b", window):
            continue
        if "preventNativeHomeScroll" in window:
            continue
        if _KEY_C.search(window) or _COPY_SEL.search(window):
            fail(f"{_ISSUE}: ⌘C is not capture-phase")

    sel = _fn(list_c, "copySelected")
    if not sel:
        fail(
            f"{_ISSUE}: TimelineList must export copySelected "
            "(in-memory tlIndex row → same plain string as Copy text)"
        )
    exp = _expand_fn_calls(list_c + "\n" + mail_c, sel, 3)
    key_blob = "\n".join(_near(handle_x, m, 80, 360) for m in hits)

    # 2) End-style focus: people view, person open, not a field, !inPeopleList.
    pal_at = handle.find("data-command-palette")
    view_at = re.search(r"view\s*!==?\s*[\"']people[\"']", handle)
    for m in hits:
        if not _people_gated(handle_x, m.start()):
            fail(
                f"{_ISSUE}: ⌘C uses the same End-style focus "
                "(people view, selectedId, not a field, not the people listbox)"
            )
        if not re.search(r"\bselectedId\b", _near(handle_x, m, 360, 200)):
            fail(
                f"{_ISSUE}: ⌘C uses the same End-style focus "
                "(people view, selectedId, not a field, not the people listbox)"
            )
        if not re.search(r"\binPeopleList\b", _near(handle_x, m, 360, 240) + handle):
            fail(
                f"{_ISSUE}: ⌘C uses the same End-style focus "
                "(!inPeopleList — same as End)"
            )
        if not _after_guard(handle, m.start()) and not _after_guard(handle_x, m.start()):
            fail(
                f"{_ISSUE}: ⌘C must run after the INPUT / TEXTAREA / SELECT "
                "return (do not steal native copy from a field)"
            )
        if pal_at >= 0 and m.start() < pal_at:
            fail(
                f"{_ISSUE}: ⌘C must run after the palette-target return "
                "(CommandPalette keeps its own ⌘C)"
            )
        if view_at and m.start() < view_at.start():
            fail(
                f"{_ISSUE}: ⌘C is people-view only "
                "(after the view !== \"people\" return)"
            )
        if not re.search(r"preventDefault\s*\(", _near(handle_x, m, 80, 360)):
            fail(f"{_ISSUE}: ⌘C must preventDefault when it copies the bubble")
        if _EXTRA_ID.search(_near(handle_x, m, 80, 360)):
            fail(
                f"{_ISSUE}: #tl-find / jump date / chrome search are INPUT — "
                "native copy; no extra ids"
            )
        if re.search(r"\bgetSelection\s*\(", _near(handle_x, m, 80, 360)):
            fail(
                f"{_ISSUE}: no getSelection() rule — ⌘C copies the whole "
                "highlighted body unless a field is focused"
            )

    # 3) copy-same-as-menu / copy-not-html / copy-not-multi / virtualizer.
    if not re.search(r"\btlIndex\b", sel):
        fail(
            f"{_ISSUE}: copySelected looks up the in-memory tlIndex row "
            "(not article innerText / innerHTML)"
        )
    if not re.search(r"\bfilteredTimeline\b|\btimeline\s*\[", sel):
        fail(
            f"{_ISSUE}: copySelected reads filteredTimeline / timeline[tlIndex] "
            "in memory (virtualizer may unmount the article)"
        )
    if _DOM.search(sel) or re.search(r"querySelector(?:All)?\s*\(\s*[\"'][^\"']*article", sel):
        fail(
            f"{_ISSUE}: in-memory row, not article innerText / querySelector"
        )
    if not re.search(r"\bdisplayBody\s*\(", exp):
        fail(
            f"{_ISSUE}: the key path uses displayBody(...) "
            "(same source as Copy text)"
        )
    if not re.search(r"\bbody_text\b", exp) or not re.search(r"\bsubject\b", exp):
        fail(
            f"{_ISSUE}: copySelected writes displayBody(row.body_text || "
            "row.subject || \"\") — same as openCopyMenu / Copy text"
        )
    if not _PAYLOAD.search(exp) and not _PAYLOAD.search(sel):
        fail(
            f"{_ISSUE}: payload is body_text || subject || \"\" "
            "(not subject+body concat)"
        )
    if re.search(r"subject\s*\+|body_text\s*\+", exp):
        fail(f"{_ISSUE}: not subject+body concat — one of body_text || subject")
    if not _WRITE_TEXT.search(exp):
        fail(
            f"{_ISSUE}: copySelected writes via navigator.clipboard.writeText "
            "(same as Copy text)"
        )
    if _HTML.search(exp) or _HTML.search(sel):
        fail(
            f"{_ISSUE}: writeText of the plain displayBody string — "
            "not text/html / innerHTML"
        )
    if _MULTI.search(sel):
        fail(f"{_ISSUE}: copy one tlIndex row only — not several bubbles")
    if re.search(r"\bgetSelection\s*\(", sel):
        fail(
            f"{_ISSUE}: no getSelection() rule — copy the highlighted body"
        )

    # 4) SPEC_GAP:empty — empty displayBody still writeText(""); no row no-op.
    if not _NO_ROW.search(sel):
        fail(
            f"{_ISSUE}: no row / tlIndex < 0 is a no-op "
            "(do not toast; do not invent a row)"
        )
    if _SKIP_EMPTY.search(sel) or _SKIP_EMPTY.search(exp):
        fail(
            f"{_ISSUE}: empty displayBody still writeText(\"\") like the menu "
            "(no extra toast)"
        )

    # 5) copy-field-native — do not add "c" to the field-steal list.
    if _steal_has_c(handle) or _steal_has_c(on_key):
        fail(
            f"{_ISSUE}: do not add \"c\" to the ⌘F/⌘K/digits field-steal list "
            "(#q / #person-filter keep native copy)"
        )
    if re.search(r"preventDefault\s*\(", key_blob) and not _after_guard(handle, hits[0].start()):
        fail(
            f"{_ISSUE}: typing in #q / #person-filter, ⌘C must not "
            "preventDefault or call copySelected"
        )

    # 6) copy-fail-toast — catch reuses onCopyFail; chrome copy only.
    if not _on_fail_only_catch(exp):
        fail(
            f"{_ISSUE}: keyboard write catch reuses onCopyFail "
            "(only on writeText failure; no extra toast)"
        )
    if "Could not copy" not in shell_c and "onCopyFail" not in shell_c:
        fail(f"{_ISSUE}: keep PeopleShell onCopyFail chrome toast")
    if _toast_args_include_body(shell_c + "\n" + exp + "\n" + sel):
        fail(
            f"{_ISSUE}: toast is chrome copy only "
            "(no body_text in the toast)"
        )

    # 7) copy-keep-135 — menu Copy text + copyText name stay.
    if not menu_path.is_file():
        fail(f"{_ISSUE}: keep TimelineCopyMenu.svelte (right-click Copy text)")
    menu = menu_path.read_text()
    if not re.search(r"""t\s*\(\s*["']copyText["']""", menu):
        fail(f"{_ISSUE}: keep right-click Copy text (t(\"copyText\"))")
    if "data-copy-menu" not in menu and "data-context-menu" not in menu:
        fail(f"{_ISSUE}: keep the bubble context menu (#135)")
    if not _fn(list_c, "copyText"):
        fail(
            f"{_ISSUE}: keep the menu function named copyText "
            "(#204 _copy_fail_blob still finds it)"
        )
    opened = _fn(list_c, "openCopyMenu")
    if not re.search(r"\bbody_text\b", opened) or not re.search(r"\bsubject\b", opened):
        fail(
            f"{_ISSUE}: openCopyMenu still stores body_text || subject || \"\""
        )

    # 8) copy-keep-215 — palette field still owns ⌘C/X/V; no plugin.
    if not pal_path.is_file():
        fail(f"{_ISSUE}: keep CommandPalette.svelte (palette field ⌘C/X/V)")
    pal = _without_comments(pal_path.read_text())
    if not _KEY_C.search(pal) or not _WRITE_TEXT.search(pal):
        fail(
            f"{_ISSUE}: keep palette field ⌘C via navigator.clipboard (#215)"
        )
    if not _KEY_CMD_X.search(pal) or not _WRITE_TEXT.search(pal):
        fail(f"{_ISSUE}: keep palette field ⌘X cut via navigator.clipboard")
    if not _KEY_CMD_V.search(pal) or not _PALETTE_READ_TEXT.search(pal):
        fail(f"{_ISSUE}: keep palette field ⌘V paste via clipboard.readText")
    pkg = (crate / "package.json").read_text() if (crate / "package.json").is_file() else ""
    toml = (crate / "Cargo.toml").read_text() if (crate / "Cargo.toml").is_file() else ""
    if _CLIPBOARD_PLUGIN.search(pkg) or _CLIPBOARD_PLUGIN.search(toml):
        fail(
            f"{_ISSUE}: do not add a clipboard plugin "
            "(navigator.clipboard only)"
        )

    # 9) copy-keep-132 — INPUT guard, j/k, End, Home/⌘↑ unchanged.
    if not re.search(r"tagName\s*===?\s*[\"']INPUT[\"']", handle):
        fail(
            f"{_ISSUE}: letter shortcuts still sit behind the "
            "INPUT/TEXTAREA/SELECT guard"
        )
    if not _KEY_J.search(keys_c) or not _KEY_K.search(keys_c):
        fail(f"{_ISSUE}: keep j/k — they still only walk visibleTlIndices")
    if not re.search(r"\bvisibleTlIndices\b", keys_c):
        fail(f"{_ISSUE}: keep j/k walking visibleTlIndices")
    for rx in (_KEY_J, _KEY_K):
        jm = rx.search(keys_c)
        if jm and _PREPEND.search(_near(keys_c, jm, 80, 220)):
            fail(f"{_ISSUE}: j/k still only walk visibleTlIndices")
        if jm and not _WALK.search(_near(keys_c, jm, 80, 220) + keys_c):
            fail(f"{_ISSUE}: j/k still only walk visibleTlIndices")
    end_m = _END.search(keys_c)
    if not end_m or not _PIN.search(_near(keys_c, end_m, 80, 240)):
        fail(f"{_ISSUE}: keep End → Latest (scrollToLatest)")
    if end_m and _COPY_SEL.search(_near(keys_c, end_m, 40, 160)):
        fail(f"{_ISSUE}: do not steal End for copy")
    home_m = _HOME.search(keys_c)
    if not home_m or not _PREPEND.search(_near(keys_c, home_m, 80, 360) + keys_c):
        fail(f"{_ISSUE}: keep Home Load older (prependOlder)")
    up_ok = False
    for m in _ARROW_UP.finditer(keys_c):
        w = _near(keys_c, m, 160, 240)
        if _MOD.search(w) and _PREPEND.search(w + keys_c):
            up_ok = True
            break
    if not up_ok:
        fail(f"{_ISSUE}: keep ⌘↑ Load older (prependOlder)")

    # 10) Wire squeeze + locale (no new t()).
    if not re.search(r"\bcopySelected\b", keys_c):
        fail(f"{_ISSUE}: PeopleKeyCtx must include copySelected")
    if not re.search(r"\bcopySelected\b", app_c):
        fail(f"{_ISSUE}: squeeze copySelected onto the App handleAppKey ctx")
    if not re.search(r"\bcopySelected\b", pane_c):
        fail(f"{_ISSUE}: squeeze copySelected onto the TimelinePane export")
    if not re.search(r"\bcopySelected\b", shell_c):
        fail(f"{_ISSUE}: squeeze copySelected onto the PeopleShell pane type")
    if _T_CALL.search(sel) or _T_CALL.search(key_blob):
        fail(f"{_ISSUE}: no new t() key on the keyboard copy path")
    en_p = crate / "web" / "lib" / "locales" / "en.ts"
    if en_p.is_file():
        extra = [
            k
            for k in _chrome_pack_entries(en_p.read_text())
            if re.search(r"copy", k, re.I) and k != "copyText"
        ]
        if extra:
            fail(
                f"{_ISSUE}: no new t() key "
                f"({', '.join(sorted(extra))} — keep copyText only)"
            )

    # 11) copy-d24
    if not dtxt.strip():
        fail(
            f"{_ISSUE}: docs/user/app.md required — highlighted bubble, "
            "⌘C (Ctrl+C) copies that body's plain text"
        )
    if not _DOCS_CMD.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say ⌘C / Ctrl+C copies the "
            "highlighted bubble"
        )
    if not _DOCS_PLAIN.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say ⌘C copies that body's "
            "plain text (not HTML)"
        )
    if not _DOCS_FIELD.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say #q / people filter keep "
            "native copy"
        )
    if re.search(r"/Users/|/home/", keys_c + "\n" + sel):
        fail(f"{_ISSUE}: tests stay placeholders (Ada) — no real home paths")
