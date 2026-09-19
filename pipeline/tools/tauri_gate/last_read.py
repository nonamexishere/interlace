"""#369 — last-read resume marker (confirmed mix).

Wired immediately after assert_people_pin_key (#368 family).

Confirmed mix: last **selected** only (click + j/k). Store message_id in
localStorage `interlace.lastRead` `{ [archive_id]: { [personId: string]: number } }`
in PeoplePrefs (status.archive_id; leave on Switch; uncapped). Quiet t("lastTime")
on the matching data-tl-index wrapper, sibling of <article>, not caption-gated.
Find-row owned Button outline sm (not a Latest overlay). jumpToMessageId sibling
of jumpToLocalDay (prepend + jumpGen; hit = ensureTlIndexVisible). Reopen still
Latest. Filtered-out: hide row marker, keep Button, quiet stay. Not SQLite /
config.toml / iCloud / write_last_path. Not unread.

#311 / #313 / #224 / #113 / #310 / #368 stay as their own asserts.
Placeholders only (Ada / Berk).
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.find_in_conversation import _FIND_HOOK
from tauri_gate.import_boot_guards import _ls_pref_keys
from tauri_gate.jump_day_heading import _LOOP, _OLDER, _REPLACE, _SHORT, _TOAST
from tauri_gate.reopen_last_lib import _fn_body, _GETITEM, _SETITEM
from tauri_gate.scan import (
    _CONFIG_TOML,
    _LAST_PATH_API,
    _LS_BRACKET,
    _expand_fn_calls,
    _rust_fn_body,
    _svelte_markup,
    _web_logic,
    _without_comments,
)
from tauri_gate.scroll_to_latest import _find_row_span, _scroller_span
from tauri_gate.status_toasts_toast import _svelte_effect_args
from tauri_gate.timeline_rows_lib import _SEARCH_TYPE_DATE

_ISSUE = "#369"
_LAST_KEY = "interlace.lastRead"
_LAST_KEY_RX = re.compile(r"interlace\.lastRead")
_LAST_PREF_NAME = re.compile(
    r"\b(?:LAST_READ_PREF|LASTREAD_PREF|LAST_READ_KEY|LAST_READ_MAP)\b"
)
_READ_LAST = re.compile(
    r"\b(?:readLastReadPref|readLastRead|lastReadFor|lastReadForArchive|"
    r"lastReadMessageId|getLastRead)\b"
)
_WRITE_LAST = re.compile(
    r"\b(?:writeLastReadPref|writeLastRead|setLastRead|persistLastRead|"
    r"rememberLastRead|saveLastRead)\b"
)
_LAST_STATE = re.compile(
    r"\b(?:lastRead|lastReadId|lastReadMap|lastReadByPerson|storedLastRead)\b"
)
_LAST_TIME_T = re.compile(r"""t\(\s*["']lastTime["']\s*\)""")
_ARCHIVE_ID = re.compile(r"\barchive_id\b|\barchiveId\b")
_STATUS_ARCHIVE = re.compile(
    r"export\s+type\s+Status\s*=\s*\{[^}]*\barchive_id\s*\??\s*:",
    re.S,
)
_NESTED_MAP = re.compile(
    r"\[\s*archive_id[^\]]*\]\s*:\s*\{[\s\S]{0,120}\[\s*personId[^\]]*\]\s*:\s*number"
    r"|Record\s*<\s*string\s*,\s*Record\s*<\s*string\s*,\s*number"
)
_MESSAGE_ID = re.compile(r"\bmessage_id\b")
_JUMP_MSG = re.compile(r"\bjumpToMessageId\b")
_JUMP_DAY = re.compile(r"\bjumpToLocalDay\b")
_ENSURE = re.compile(r"\bensureTlIndexVisible\b")
_PIN_DAY = re.compile(r"\bpinDayAtTop\b")
_JUMP_GEN = re.compile(r"\b(?:jumpGen|jumpStale|currentGen)\b")
_TICK = re.compile(r"\bawait\s+tick\s*\(")
_CAP = re.compile(r"\bJUMP_DAY_PAGE_CAP\b|\bpages\s*<\s*80\b")
_BUTTON = re.compile(r"<Button\b")
_OUTLINE = re.compile(r"""variant\s*=\s*["']outline["']""")
_SIZE_SM = re.compile(r"""size\s*=\s*["']sm["']""")
_OWNED_BUTTON = re.compile(
    r"""import\s+\{[^}]*\bButton\b[^}]*\}\s+from\s+["']\$lib/components/ui/button"""
)
_REMOVE_ITEM = re.compile(r"\bremoveItem\s*\(")
_ICLOUD = re.compile(r"\biCloud\b|CloudKit|NSUbiquitous")
_LAST_IPC = re.compile(
    r"\b(?:last_read|set_last_read|write_last_read|person_last_read)(?:_cmd)?\b"
)
_LAST_SQL = re.compile(
    r"""
    \blast_read\b
    |\blastRead\b
    |\blast_read_message
    |ALTER\s+TABLE\s+\w+[\s\S]{0,200}\blast_read
    |CREATE\s+TABLE\s+\w*last_read
    """,
    re.I | re.X,
)
_LAST_CAP = re.compile(
    r"\b(?:MAX_LAST_READ|LAST_READ_CAP|maxLastRead|lastReadCap)\b"
)
_SMOOTH = re.compile(r"""behavior\s*:\s*["']smooth["']""")
_FADE = re.compile(r"\b(?:transition|in|out)\s*:\s*(?:fade|fly|slide)\b")
_BOUNCE = re.compile(r"\b(?:bounce|spring|elastic)\b", re.I)
_VISIBLE_FALLBACK = re.compile(
    r"fullyVisible|fully.?visible|lastFullyVisible|visibleFallback|"
    r"IntersectionObserver"
)
_SETTLE = re.compile(r"beforeunload|pagehide|scrollSettle|onScrollEnd")
_CLEAR_CHIPS = re.compile(
    r"""platformFilter\s*=\s*["']all["']|kindFilter\s*=\s*["']all["']"""
    r"""|attachKindFilter\s*=\s*["']all["']|fromMeFilter\s*=\s*["']all["']"""
    r"""|includeGroups\s*=\s*true"""
)
_GHOST_ROW = re.compile(
    r"""person\s*\$\{|message\s*\$\{|`person\s+\$\{|`message\s+\$\{"""
)
_UNREAD = re.compile(r"data-unread|\bunreadCount\b|\bunread-dot\b|\bunreadBadge\b")
_REMOUNT = re.compile(r"\{#key\b")
_VIRTUALIZE = re.compile(r"\bVIRTUALIZE_AFTER\s*=\s*250\b")
_EST = re.compile(r"\bESTIMATED_ROW_HEIGHT\s*=\s*88\b")
_PIN_KEY_RX = re.compile(r"interlace\.peoplePins")
_LATEST_T = re.compile(r"""t\(\s*["']latest["']\s*\)""")
_SEPARATOR = re.compile(r"<Separator\b")
_DAY_HEADING = re.compile(r"day-heading")
_FILTERED = re.compile(r"\bfilteredTimeline\b")
_TLINDEX_STORE = re.compile(
    r"setItem[\s\S]{0,220}\btlIndex\b|\blastRead\w*\s*=\s*tlIndex\b"
)
_EMPTY_ARCHIVE = re.compile(
    r"""!\s*archive_id|archive_id\s*===?\s*[\"']{2}|if\s*\(\s*!?\s*archive_id"""
)
_JUNK = re.compile(r"JSON\.parse|Array\.isArray|\|\|\s*\{\s*\}|\?\?\s*\{\s*\}")
_DOCS_LAST = re.compile(r"last time|last-read|last read|resume marker", re.I)
_DOCS_LOCAL = re.compile(
    r"(?:last time|last-read|last read).{0,240}(?:localStorage|local(?:ly)?)"
    r"|(?:localStorage|local(?:ly)?).{0,240}(?:last time|last-read|last read)",
    re.I | re.S,
)
_DOCS_NOT_ICLOUD = re.compile(
    r"(?:last time|last-read|last read).{0,240}not iCloud"
    r"|not iCloud.{0,240}(?:last time|last-read|last read)",
    re.I | re.S,
)
_DOCS_ARCHIVE = re.compile(
    r"(?:last time|last-read|last read).{0,200}(?:per[- ]archive|archive)"
    r"|archive.{0,200}(?:last time|last-read|last read)",
    re.I | re.S,
)
_DOCS_NOT_UNREAD = re.compile(
    r"(?:last time|last-read|last read).{0,200}not unread"
    r"|not unread.{0,200}(?:last time|last-read|last read)",
    re.I | re.S,
)
_DOCS_LATEST = re.compile(
    r"(?:last time|last-read|last read).{0,200}Latest"
    r"|Latest.{0,200}(?:last time|last-read|last read|newest)",
    re.I | re.S,
)
_SKIP = frozenset(
    "if for while switch catch function return typeof new await void "
    "String Number Boolean console tick Promise Math document".split()
)
_JUMP_FILES = (
    "jumpDay.ts",
    "lastRead.ts",
    "jumpToMessageId.ts",
    "TimelineJump.ts",
)


def _text(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


def _web_file(crate: Path, name: str) -> Path:
    return crate / "web" / "lib" / name


def _locale_keys(src: str) -> set[str]:
    return set(re.findall(r"(?m)^\s+([A-Za-z][A-Za-z0-9_]*)\s*:", src))


def _locale_value(src: str, key: str) -> str:
    m = re.search(rf'(?m)^\s+{re.escape(key)}\s*:\s*("(?:\\.|[^"\\])*")', src)
    return m.group(1) if m else ""


def _svelte_if_body(src: str, cond: str) -> str:
    m = re.search(rf"\{{#if\s+{cond}\}}", src)
    if not m:
        return ""
    start, depth, i = m.end(), 1, m.end()
    while i < len(src) and depth:
        nxt_if, nxt_end = src.find("{#if", i), src.find("{/if}", i)
        cands = [(p, k) for p, k in ((nxt_if, "if"), (nxt_end, "end")) if p >= 0]
        if not cands:
            break
        pos, kind = min(cands)
        if kind == "if":
            depth += 1
            i = pos + 4
        else:
            depth -= 1
            if depth == 0:
                return src[start:pos]
            i = pos + 5
    return ""


def _article_span(src: str) -> str:
    m = re.search(r"<article\b", src)
    if not m:
        return ""
    end = src.find("</article>", m.start())
    return src[m.start() : end + 10] if end >= 0 else src[m.start() : m.start() + 1800]


def _button_blocks(src: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for m in _BUTTON.finditer(src):
        gt = src.find(">", m.start())
        if gt < 0:
            continue
        open_tag = src[m.start() : gt + 1]
        if open_tag.rstrip().endswith("/>"):
            out.append((open_tag, ""))
            continue
        close = re.search(r"</Button\s*>", src[gt + 1 :], re.I)
        if not close:
            continue
        inner = src[gt + 1 : gt + 1 + close.start()]
        out.append((open_tag, inner))
    return out


def _reads_last(blob: str) -> bool:
    if _READ_LAST.search(blob) or _LAST_STATE.search(blob):
        return True
    if not (_GETITEM.search(blob) or _LS_BRACKET.search(blob)):
        return False
    return bool(_LAST_KEY_RX.search(blob) or _LAST_PREF_NAME.search(blob))


def _writes_last(blob: str) -> bool:
    if _WRITE_LAST.search(blob):
        return True
    if not _SETITEM.search(blob):
        return False
    return bool(_LAST_KEY_RX.search(blob) or _LAST_PREF_NAME.search(blob))


def _blob_does(src: str, blob: str, pred) -> bool:
    if pred(blob):
        return True
    seen: set[str] = set()
    for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", blob):
        if name in seen or name in _SKIP:
            continue
        seen.add(name)
        inner = _fn_body(src, name)
        if inner and pred(inner):
            return True
    return False


def _effect_writes(src: str) -> bool:
    for arg in _svelte_effect_args(src):
        if (_LAST_STATE.search(arg) or _LAST_KEY_RX.search(arg) or "tlIndex" in arg) and _writes_last(
            arg
        ):
            return True
    return False


def _jump_blob(crate: Path, pane: str) -> str:
    parts = [_text(_web_file(crate, n)) for n in _JUMP_FILES]
    src = _without_comments("\n".join(parts) + "\n" + pane)
    return src + "\n" + _fn_body(src, "jumpToMessageId")


def _core_blob(root: Path) -> str:
    parts: list[str] = []
    base = root / "crates" / "interlace-core" / "src"
    for rel in ("people.rs", "session.rs"):
        p = base / rel
        if p.is_file():
            parts.append(p.read_text())
    people_dir = base / "people"
    if people_dir.is_dir():
        for p in sorted(people_dir.glob("*.rs")):
            if p.name in {"identity.rs", "search.rs"}:
                continue
            parts.append(p.read_text())
    mig = root / "crates" / "interlace-core" / "migrations"
    if mig.is_dir():
        for p in sorted(mig.glob("*.sql")):
            parts.append(p.read_text())
    return "\n".join(parts)


def assert_last_read(crate: Path) -> None:
    """#369: last-selected message_id + Last time row marker + Find-row jump."""
    root = repo_root()
    rows_path = _web_file(crate, "TimelineRows.svelte")
    pane_path = _web_file(crate, "TimelinePane.svelte")
    list_path = _web_file(crate, "TimelineList.svelte")
    prefs_path = _web_file(crate, "PeoplePrefs.ts")
    if not rows_path.is_file():
        fail(f"{_ISSUE}: TimelineRows.svelte required (quiet Last time on the row)")
    if not pane_path.is_file():
        fail(f"{_ISSUE}: TimelinePane.svelte required (Find-row Last time Button)")
    if not list_path.is_file():
        fail(f"{_ISSUE}: TimelineList.svelte required (Latest overlay stays; no remount)")
    if not prefs_path.is_file():
        fail(f"{_ISSUE}: PeoplePrefs.ts required (interlace.lastRead helpers)")

    rows_raw, pane_raw, list_raw = rows_path.read_text(), pane_path.read_text(), list_path.read_text()
    rows, pane, lst = (_without_comments(rows_raw), _without_comments(pane_raw), _without_comments(list_raw))
    rows_m, pane_m, list_m = (
        _svelte_markup(rows_raw),
        _svelte_markup(pane_raw),
        _svelte_markup(list_raw),
    )
    prefs = _without_comments(prefs_path.read_text())
    app_path = crate / "web" / "App.svelte"
    app_raw = _text(app_path)
    app = _without_comments(app_raw)
    boot = _without_comments(_text(_web_file(crate, "PeopleBoot.ts")))
    shell = _without_comments(_text(_web_file(crate, "PeopleShell.svelte")))
    shell_m = _svelte_markup(_text(_web_file(crate, "PeopleShell.svelte")))
    keys_src = _without_comments(_text(_web_file(crate, "PeopleKeys.ts")))
    latest = _text(_web_file(crate, "TimelineLatest.svelte"))
    latest_m = _svelte_markup(latest)
    api = _without_comments(_text(_web_file(crate, "api.ts")))
    virt = _text(_web_file(crate, "TimelineVirtual.ts"))
    en = _text(_web_file(crate, "locales/en.ts"))
    tr = _text(_web_file(crate, "locales/tr.ts"))
    docs = _text(root / "docs" / "user" / "app.md")
    web = _without_comments(_web_logic(crate))
    combo = "\n".join((app, prefs, pane, lst, rows, shell, boot, keys_src))
    jump = _jump_blob(crate, pane)
    persist = "\n".join(
        (
            prefs,
            _fn_body(combo, "readLastReadPref"),
            _fn_body(combo, "writeLastReadPref"),
            _fn_body(combo, "readLastRead"),
            _fn_body(combo, "writeLastRead"),
            _fn_body(combo, "setLastRead"),
            _fn_body(combo, "lastReadFor"),
            _fn_body(combo, "lastReadForArchive"),
        )
    )
    sel = _fn_body(pane, "selectPerson") or _fn_body(pane_raw, "selectPerson")
    find_row = _find_row_span(pane_m)
    find_src = pane_m[find_row[0] : find_row[1]] if find_row else ""
    scroller = _scroller_span(list_m)

    # Keep #310 / #311 / #313 / #113 / #224 (pass today).
    if not _FIND_HOOK.search(pane_m):
        fail(f"{_ISSUE}: keep #310 find (data-tl-find / id=tl-find)")
    if not _SEARCH_TYPE_DATE.search(pane_m):
        fail(f"{_ISSUE}: keep #311 type=\"date\" next to find")
    if not _JUMP_DAY.search(pane + "\n" + _text(_web_file(crate, "jumpDay.ts"))):
        fail(f"{_ISSUE}: keep jumpToLocalDay (#311) — last-read is a sibling, not a rewrite")
    if not _LATEST_T.search(list_m) and not _LATEST_T.search(latest_m):
        fail(f"{_ISSUE}: keep #313 t(\"latest\") overlay")
    if find_src and _LATEST_T.search(find_src):
        fail(f"{_ISSUE}: Latest stays the overlay — not a Find-row t(\"latest\") button")
    if "applyOpenPersonWindow" not in sel:
        fail(f"{_ISSUE}: keep #113 applyOpenPersonWindow (non-append open still Latest)")
    if not _VIRTUALIZE.search(virt) and not _VIRTUALIZE.search(lst):
        fail(f"{_ISSUE}: keep #224 VIRTUALIZE_AFTER = 250")
    if not _EST.search(virt) and not _EST.search(lst):
        fail(f"{_ISSUE}: keep #224 ESTIMATED_ROW_HEIGHT = 88")
    if not _STATUS_ARCHIVE.search(api):
        fail(f"{_ISSUE}: keep Status.archive_id (#368) — last-read keys by it, not st.path")
    if not _PIN_KEY_RX.search(prefs):
        fail(f"{_ISSUE}: keep interlace.peoplePins (#368) — last-read is a different key")

    # 1) Primary red today: no Last time marker on the row.
    row_src = rows_m if _LAST_TIME_T.search(rows_m) else rows
    if not _LAST_TIME_T.search(row_src):
        fail(f"{_ISSUE}: matching data-tl-index wrapper needs a quiet t(\"lastTime\") marker")
    if "data-tl-index" not in rows_m and "data-tl-index" not in rows:
        fail(f"{_ISSUE}: keep data-tl-index on the bubble wrapper (#310 / #206)")
    mark_at = _LAST_TIME_T.search(row_src)
    around = row_src[max(0, mark_at.start() - 400) : mark_at.end() + 200] if mark_at else ""
    if "data-tl-index" not in row_src[max(0, (mark_at.start() if mark_at else 0) - 900) : (mark_at.end() if mark_at else 0) + 80]:
        fail(f"{_ISSUE}: t(\"lastTime\") sits on the matching data-tl-index wrapper")
    if _DAY_HEADING.search(around) or (
        mark_at and _DAY_HEADING.search(row_src[max(0, mark_at.start() - 80) : mark_at.end() + 40])
    ):
        fail(f"{_ISSUE}: Last time is not a .day-heading")
    if _SEPARATOR.search(around) or _SEPARATOR.search(row_src):
        fail(f"{_ISSUE}: Last time is not a Separator / extra virtualizer slot")
    article = _article_span(row_src)
    if mark_at and article and article.find(mark_at.group(0)) >= 0:
        fail(
            f"{_ISSUE}: t(\"lastTime\") is a sibling of <article> "
            "(not inside the bubble; grouped followers still mark)"
        )
    caption = _svelte_if_body(row_src, r"!isGroupedFollower[^}]*")
    if caption and _LAST_TIME_T.search(caption) and not (
        mark_at and caption.find(mark_at.group(0)) < 0
    ):
        fail(
            f"{_ISSUE}: Last time must still paint on a grouped follower "
            "(not caption-gated by !isGroupedFollower)"
        )
    if "data-bubble-body" in around:
        fail(f"{_ISSUE}: Last time stays outside data-bubble-body (bodies stay text / <mark>)")
    if not re.search(r"text-xs|text-muted-foreground|muted", around):
        fail(f"{_ISSUE}: Last time marker is quiet (text-xs / muted-foreground)")
    if _FADE.search(around):
        fail(f"{_ISSUE}: marker has no Svelte fade (this mix adds none)")
    if not (_MESSAGE_ID.search(around + "\n" + rows) and (
        _LAST_STATE.search(rows) or _READ_LAST.search(rows) or _LAST_KEY_RX.search(rows)
    )):
        fail(
            f"{_ISSUE}: paint Last time only when that message_id is in current filteredTimeline"
        )

    # 2) Find-row owned Button outline sm — not a Latest overlay.
    if not _OWNED_BUTTON.search(pane) and not _OWNED_BUTTON.search(pane_raw):
        fail(f"{_ISSUE}: Last time jump is an owned Button (not a new kit)")
    last_btns = [
        (tag, inner)
        for tag, inner in _button_blocks(pane_m) + _button_blocks(pane)
        if _LAST_TIME_T.search(tag + "\n" + inner)
    ]
    if not last_btns:
        fail(
            f"{_ISSUE}: Find / date / Media row needs an owned Button outline sm "
            'with t("lastTime") (outside #person-timeline)'
        )
    if not find_src or not _LAST_TIME_T.search(find_src):
        fail(
            f"{_ISSUE}: Last time Button sits on the #tl-find / date / Media row "
            "(outside #person-timeline — not a Latest overlay)"
        )
    if not any(_OUTLINE.search(tag) and _SIZE_SM.search(tag) for tag, _ in last_btns):
        fail(f'{_ISSUE}: Last time control is Button variant="outline" size="sm"')
    if scroller:
        for m in _LAST_TIME_T.finditer(list_m):
            if scroller[0] <= m.start() < scroller[1]:
                fail(f"{_ISSUE}: Last time Button is not inside #person-timeline")
    if _LAST_TIME_T.search(latest) or _LAST_TIME_T.search(latest_m):
        fail(f"{_ISSUE}: Last time is not inside TimelineLatest and not t(\"latest\")")
    if _LATEST_T.search("\n".join(tag + inner for tag, inner in last_btns)):
        fail(f"{_ISSUE}: Last time Button must not use t(\"latest\")")
    btn_around = find_src
    if re.search(r"\btlIndex\b", btn_around) and re.search(
        r"===?|!==?", btn_around
    ):
        fail(
            f"{_ISSUE}: leave the Find-row Button when the highlighted row already is "
            "that message (no hide-when-on-row reflow)"
        )
    if not (
        _LAST_STATE.search(pane)
        or _READ_LAST.search(pane)
        or _LAST_KEY_RX.search(pane)
        or _LAST_PREF_NAME.search(pane)
    ):
        fail(
            f"{_ISSUE}: Last time Button is visible when a stored id exists "
            "even if the row is not loaded"
        )

    # 3) interlace.lastRead = { [archive_id]: { [personId: string]: number } }.
    ls_keys = _ls_pref_keys(web + "\n" + prefs)
    if _LAST_KEY not in ls_keys and not _LAST_KEY_RX.search(prefs):
        fail(
            f"{_ISSUE}: persist last-read in namespaced localStorage "
            "(interlace.lastRead keyed by archive_id) — "
            "not write_last_path / config.toml / iCloud"
        )
    if not _SETITEM.search(persist):
        fail(
            f"{_ISSUE}: persist last-read with localStorage.setItem "
            "(interlace.lastRead; {{ [archive_id]: {{ [personId: string]: number }} }})"
        )
    if not _GETITEM.search(persist) and not _LS_BRACKET.search(persist):
        fail(f"{_ISSUE}: restore last-read from localStorage.getItem (same interlace.lastRead key)")
    if not _NESTED_MAP.search(persist + "\n" + prefs):
        fail(
            f"{_ISSUE}: interlace.lastRead is {{ [archive_id]: {{ [personId: string]: number }} }} "
            "(message_id — not a bare number, not tlIndex, not peoplePins number[])"
        )
    if not _MESSAGE_ID.search(persist + "\n" + pane + "\n" + lst):
        fail(f"{_ISSUE}: stored value is message_id, never tlIndex (prepend shifts indices)")
    if _TLINDEX_STORE.search(persist + "\n" + pane + "\n" + lst):
        fail(f"{_ISSUE}: do not persist tlIndex / data-tl-index as the last-read value")
    if not _ARCHIVE_ID.search(prefs) and not _ARCHIVE_ID.search(persist):
        fail(f"{_ISSUE}: key last-read by Status.archive_id, not a global person map")
    if re.search(r"\bpath\b", persist) and not _ARCHIVE_ID.search(persist):
        fail(f"{_ISSUE}: key last-read by Status.archive_id, not st.path")
    if not _EMPTY_ARCHIVE.search(persist + "\n" + prefs):
        fail(f"{_ISSUE}: empty archive_id → no read, no write")
    if not _JUNK.search(persist):
        fail(f"{_ISSUE}: missing / wiped / junk interlace.lastRead must be {{}}")
    if _LAST_CAP.search(prefs) or _LAST_CAP.search(persist) or _LAST_CAP.search(pane):
        fail(f"{_ISSUE}: last-read is uncapped (do not invent LAST_READ_CAP)")
    if _PIN_KEY_RX.search(persist) and not _LAST_KEY_RX.search(persist):
        fail(f"{_ISSUE}: do not reuse interlace.peoplePins for last-read")

    # 4) Write on user select only (click + j/k). Not auto-newest / snaps / fallback.
    on_sel = ""
    for m in re.finditer(r"onSelectIndex\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}", list_raw + "\n" + lst):
        on_sel += m.group(1) + "\n"
    on_sel += _fn_body(lst, "onSelectIndex") + "\n" + _fn_body(pane, "onSelectIndex")
    set_tl = ""
    for m in re.finditer(
        r"setTlIndex\s*:\s*(?:\(n\)\s*=>\s*)?\{([^}]*)\}|setTlIndex\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}",
        app_raw + "\n" + app + "\n" + keys_src,
    ):
        set_tl += (m.group(1) or m.group(2) or "") + "\n"
    jk = keys_src[max(0, keys_src.find('e.key === "j"') - 80) : keys_src.find('e.key === "j"') + 400] if 'e.key === "j"' in keys_src else keys_src
    if not _blob_does(combo, on_sel, _writes_last):
        fail(
            f"{_ISSUE}: article click onSelectIndex must persist that row's message_id "
            "(last selected only)"
        )
    if not _blob_does(combo, set_tl + "\n" + jk, _writes_last):
        fail(f"{_ISSUE}: j/k setTlIndex must persist that row's message_id (last selected only)")
    if _writes_last(sel) or _blob_does(combo, sel, _writes_last):
        fail(
            f"{_ISSUE}: do not persist last-read from selectPerson "
            "(auto-newest / Load older / chip reopen must not overwrite Ada's mid-thread id)"
        )
    if _effect_writes(pane) or _effect_writes(lst) or _effect_writes(app) or _effect_writes(shell):
        fail(
            f"{_ISSUE}: do not persist last-read from a bare $effect on tlIndex "
            "(would write Latest on every open)"
        )
    snap = "\n".join(
        (
            _fn_body(pane, "goToJumpDay"),
            _fn_body(jump, "jumpToLocalDay"),
            _fn_body(jump, "applyJumpScrollPos"),
            _fn_body(pane, "openPersonAtMessage"),
        )
    )
    if _writes_last(snap) or _blob_does(combo, snap, _writes_last):
        fail(f"{_ISSUE}: chip / find / day-jump tlIndex snaps must not write last-read")
    if _VISIBLE_FALLBACK.search(persist + "\n" + pane + "\n" + lst):
        fail(f"{_ISSUE}: remember last selected only — not last fully visible / IntersectionObserver")
    if _SETTLE.search(persist + "\n" + pane + "\n" + lst + "\n" + app):
        fail(f"{_ISSUE}: do not write last-read on scroll-settle / beforeunload")

    # 5) File → Open re-reads B; Switch leaves the key.
    derived = bool(
        re.search(r"\$derived", shell + "\n" + pane + "\n" + app)
        and _ARCHIVE_ID.search(shell + "\n" + pane + "\n" + app)
        and (_READ_LAST.search(shell + "\n" + pane + "\n" + app) or _LAST_KEY_RX.search(shell + "\n" + pane + "\n" + app) or _LAST_STATE.search(shell + "\n" + pane + "\n" + app))
    )
    apply_st = _fn_body(app, "applyStatus") or _fn_body(app_raw, "applyStatus")
    if not _blob_does(combo, apply_st, _reads_last) and not derived:
        fail(
            f"{_ISSUE}: File → Open / applyStatus must re-read last-read for B's archive_id "
            "(A's marker must not paint on B)"
        )
    switch = _fn_body(boot, "switchToSetup") or _fn_body(combo, "switchToSetup")
    for m in _REMOVE_ITEM.finditer(switch):
        window = switch[max(0, m.start() - 40) : m.end() + 80]
        if _LAST_KEY_RX.search(window) or _LAST_PREF_NAME.search(window):
            fail(
                f"{_ISSUE}: do not removeItem interlace.lastRead in switchToSetup "
                "(leave the pref; resolve against the next archive_id)"
            )

    # 6) jumpToMessageId sibling — prepend + jumpGen; hit = ensureTlIndexVisible.
    if not _JUMP_MSG.search(jump + "\n" + pane):
        fail(
            f"{_ISSUE}: jumpToMessageId sibling of jumpToLocalDay required "
            "(do not rewrite jumpToLocalDay)"
        )
    jmp = _fn_body(jump, "jumpToMessageId") or _fn_body(pane, "jumpToMessageId")
    jmp = _expand_fn_calls(jump + "\n" + pane, jmp, 3)
    if _JUMP_MSG.search(sel):
        fail(
            f"{_ISSUE}: reopen / non-append selectPerson still lands at Latest "
            "(do not auto-jump on open)"
        )
    if not _FILTERED.search(jmp) or not _MESSAGE_ID.search(jmp):
        fail(f"{_ISSUE}: jump seeks message_id in current filteredTimeline")
    if not _OLDER.search(jmp) or not _LOOP.search(jmp):
        fail(
            f"{_ISSUE}: an older last-read not in the loaded set must Load older "
            "(selectPerson(..., true) prepend) until the row exists or the thread starts"
        )
    if not _SHORT.search(jmp) and not _CAP.search(jmp):
        fail(f"{_ISSUE}: stop Load older on empty/short page or JUMP_DAY_PAGE_CAP")
    if not _TICK.search(jmp):
        fail(f"{_ISSUE}: await tick() after each last-read prepend (same as #311)")
    if not _JUMP_GEN.search(jmp + "\n" + pane):
        fail(f"{_ISSUE}: last-read jump cancels on person switch / later jump / find (jumpGen)")
    if _REPLACE.search(jmp):
        fail(f"{_ISSUE}: do not replace the window (openPersonAtMessage / timeline = loaded)")
    if _PIN_DAY.search(jmp):
        fail(f"{_ISSUE}: last-read hit uses ensureTlIndexVisible, not pinDayAtTop")
    if not _ENSURE.search(jmp + "\n" + pane):
        fail(f"{_ISSUE}: a hit sets tlIndex and ensureTlIndexVisible (unmounted rows remount)")
    if _TOAST.search(jmp):
        fail(f"{_ISSUE}: a miss stays quiet (no toast / showErr)")
    if _CLEAR_CHIPS.search(jmp) or _CLEAR_CHIPS.search(find_src):
        fail(f"{_ISSUE}: filtered-out last-read does not auto-clear chips / includeGroups")
    if _REMOUNT.search(pane_m + "\n" + list_m + "\n" + shell_m):
        fail(f"{_ISSUE}: no {{#key}} remount of #person-timeline / TimelinePane")

    # 7) Miss / ghost / tombstone / merge.
    if _GHOST_ROW.search(rows_m) or _GHOST_ROW.search(pane):
        fail(f"{_ISSUE}: do not invent a person ${{id}} / cloned TimelineRow for a stored id")
    merge = _text(_web_file(crate, "MergeDialog.svelte"))
    if _LAST_KEY_RX.search(merge) or _WRITE_LAST.search(merge) or _LAST_STATE.search(merge):
        fail(f"{_ISSUE}: merge does not transfer Ada's last-read onto Berk")
    sidebar = _text(_web_file(crate, "PeopleSidebar.svelte"))
    if _UNREAD.search(sidebar) or _LAST_KEY_RX.search(sidebar) or _LAST_TIME_T.search(sidebar):
        fail(f"{_ISSUE}: last-read is not unread and not a sidebar badge")

    # 8) Latest / motion stay newest; no bounce.
    if "scrollToLatest" not in lst and "scrollToLatest" not in keys_src:
        fail(f"{_ISSUE}: keep Latest / End → newest (#313)")
    motion_src = jmp + "\n" + around + "\n" + find_src
    if _SMOOTH.search(motion_src) or _BOUNCE.search(motion_src):
        fail(f'{_ISSUE}: no bounce / behavior: "smooth" on Last time (reduced motion is instant)')

    # 9) Not SQLite / config.toml / iCloud / IPC.
    if _LAST_PATH_API.search(persist) or _CONFIG_TOML.search(persist):
        fail(
            f"{_ISSUE}: do not persist last-read via write_last_path / "
            "read_last_path / config.toml (localStorage only)"
        )
    if _ICLOUD.search(persist):
        fail(f"{_ISSUE}: do not persist last-read to iCloud")
    session = _text(root / "crates" / "interlace-core" / "src" / "session.rs")
    wl = _rust_fn_body(_without_comments(session), "write_last_path")
    if re.search(r"last_read|lastRead", wl, re.I):
        fail(
            f"{_ISSUE}: do not rewrite session.rs write_last_path to dump last-read "
            "(config.toml is the last-archive pointer, not chrome prefs)"
        )
    if _LAST_SQL.search(_core_blob(root)):
        fail(f"{_ISSUE}: no SQLite last-read table (last-read is localStorage only)")
    tauri_blob = "\n".join(
        (
            _text(crate / "src" / "people_cmd.rs"),
            _text(crate / "src" / "main.rs"),
            _text(crate / "src" / "ipc.rs"),
            api,
        )
    )
    if _LAST_IPC.search(tauri_blob):
        fail(f"{_ISSUE}: no last-read IPC — last-read is localStorage only")

    # 10) en+tr lastTime; tr is not an English copy. D24.
    en_keys, tr_keys = _locale_keys(en), _locale_keys(tr)
    if "lastTime" not in en_keys or "lastTime" not in tr_keys:
        fail(
            f"{_ISSUE}: chrome key lastTime must exist in both "
            "locales/en.ts and locales/tr.ts"
        )
    ev, tv = _locale_value(en, "lastTime"), _locale_value(tr, "lastTime")
    if ev and "Last time" not in ev:
        fail(f'{_ISSUE}: en.ts lastTime is "Last time"')
    if ev and tv and ev == tv:
        fail(f"{_ISSUE}: tr.ts lastTime must not be an English copy (#131 / #278)")
    loc = crate / "web" / "lib" / "locales"
    extra = [
        p.name
        for p in loc.iterdir()
        if p.is_file() and p.suffix in {".ts", ".json"} and p.stem not in {"en", "tr"}
    ]
    if extra:
        fail(f"{_ISSUE}: no third locale pack ({', '.join(sorted(extra))})")
    if not docs.strip():
        fail(f"{_ISSUE}: docs/user/app.md required — Last time is local, per archive")
    if not _DOCS_LAST.search(docs):
        fail(f"{_ISSUE}: docs/user/app.md must say Last time / last-read on the person timeline")
    if not _DOCS_LOCAL.search(docs):
        fail(f"{_ISSUE}: docs/user/app.md must say last-read is local (localStorage)")
    if not _DOCS_NOT_ICLOUD.search(docs):
        fail(f"{_ISSUE}: docs/user/app.md must say last-read is not iCloud")
    if not _DOCS_ARCHIVE.search(docs):
        fail(f"{_ISSUE}: docs/user/app.md must say last-read is per archive")
    if not _DOCS_NOT_UNREAD.search(docs):
        fail(f"{_ISSUE}: docs/user/app.md must say last-read is not unread")
    if not _DOCS_LATEST.search(docs):
        fail(f"{_ISSUE}: docs/user/app.md must say Latest still goes to newest")
    if re.search(r"/Users/|/home/", pane + "\n" + rows + "\n" + persist):
        fail(f"{_ISSUE}: tests stay placeholders (Ada / Berk) — no real home paths")
