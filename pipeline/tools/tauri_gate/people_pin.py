"""#368 — pin people to the top of the sidebar (confirmed mix).

Wired immediately after assert_people_rename_notes (#213 / #366 / #367 family).
assert_people_pin_icon follows assert_people_pin.

Confirmed mix: row pin + localStorage `interlace.peoplePins`
`{ [archive_id]: number[] }` (pin-time, first pinned first) in PeoplePrefs.
Status.archive_id from existing status JSON (no new IPC). Quiet t("pinned")
heading + one `{#each filtered}` (matching pins first, then Recent | A–Z).
Hide heading when empty or collapsed. Ghost Pin/Unpin on the expanded row.
`/` filters pinned and the rest; tombstone / missing id is not a ghost;
File → Open / applyStatus re-reads. Not SQLite, not config.toml, not iCloud.
No pins on Search hits or merge picker. Uncapped.

#368-icon fold: expanded-row control is a Lucide Pin / PinOff icon
(owned ghost Button size="icon"), not visible Pin / Unpin text.
t("pinPerson") / t("unpinPerson") stay the accessible name (aria-label,
with #184 display_name + humanTime). Do not delete #368 / #184.

#138 / #212 / #213 / #184 / #366 / #367 stay as their own asserts.
Placeholders only (Ada / Berk).
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.a11y_lib import _people_each_block
from tauri_gate.import_boot_guards import _ls_pref_keys
from tauri_gate.people_filter import (
    _PEOPLE_FILTER_IDENTITIES_FIELD,
    _PEOPLE_FILTER_IDENTITY_TOKENS,
    _attr_brace_values,
    _people_filter_window,
)
from tauri_gate.reopen_last_lib import _fn_body, _GETITEM, _SETITEM
from tauri_gate.scan import (
    _CONFIG_TOML,
    _LAST_PATH_API,
    _LS_BRACKET,
    _rust_fn_body,
    _svelte_markup,
    _web_logic,
    _without_comments,
)
from tauri_gate.status_toasts_chrome import _PEOPLE_EACH
from tauri_gate.status_toasts_toast import _svelte_effect_args

_ISSUE = "#368"
_ICON_ISSUE = "#368-icon"
_PIN_KEY = "interlace.peoplePins"
_PIN_KEY_RX = re.compile(r"interlace\.peoplePins")
_PIN_PREF_NAME = re.compile(
    r"\b(?:PEOPLE_PINS_PREF|PINS_PREF|PEOPLE_PINS_KEY|PIN_PREF)\b"
)
_READ_PINS = re.compile(
    r"\b(?:readPeoplePinsPref|readPinsPref|readPeoplePins|pinsFor|pinsForArchive)\b"
)
_WRITE_PINS = re.compile(
    r"\b(?:writePeoplePinsPref|writePinsPref|writePeoplePins|persistPeoplePins|"
    r"togglePersonPin|togglePin|pinPerson|unpinPerson)\b"
)
_PIN_STATE = re.compile(
    r"\b(?:peoplePins|pinnedIds|pinIds|pinnedMatching|storedPins)\b"
)
_ARCHIVE_ID = re.compile(r"\barchive_id\b|\barchiveId\b")
_STATUS_ARCHIVE = re.compile(
    r"export\s+type\s+Status\s*=\s*\{[^}]*\barchive_id\s*\??\s*:",
    re.S,
)
_PIN_LABEL = re.compile(
    r"""
    t\(\s*["'](?:pinPerson|unpinPerson|pin|unpin)["']
    |data-person-pin
    |>\s*Pin\s*<
    |>\s*Unpin\s*<
    """,
    re.I | re.X,
)
_PINNED_T = re.compile(r"""t\(\s*["']pinned["']\s*\)""")
_GHOST = re.compile(r"""variant\s*=\s*["']ghost["']""")
_BUTTON = re.compile(r"<Button\b")
_OWNED_BUTTON = re.compile(
    r"""import\s+\{[^}]*\bButton\b[^}]*\}\s+from\s+["']\$lib/components/ui/button"""
)
_CONCAT = re.compile(
    r"""
    \[\s*\.\.\.\s*\w*[Pp]in\w*\s*,
    |\w*[Pp]in\w*\s*\.\s*concat\s*\(
    |\w*[Pp]in\w*\s*\+\s*\w*(?:rest|other|unpinned|sorted)
    """,
    re.X,
)
_PIN_WALK = re.compile(
    r"""
    (?:pinIds|pinnedIds|pin_ids|pins|storedPins|peoplePins)
    \s*\.\s*(?:map|flatMap|reduce)
    |
    for\s*\(\s*const\s+\w+\s+of\s+
    (?:pinIds|pinnedIds|pin_ids|pins|storedPins)
    |
    (?:readPeoplePinsPref|readPeoplePins|readPinsPref|pinsFor|pinsForArchive)
    \s*\([^)]*\)[\s\S]{0,240}\.map\s*\(
    """,
    re.X,
)
_DEDUP = re.compile(
    r"""
    !\s*(?:pinSet|pinnedSet|pins|pinnedIds|pinned)\s*\.\s*has
    |!\s*isPinned
    |(?:pinSet|pinnedSet|pins)\s*\.\s*has\s*\(\s*\w+\.id
    """,
    re.X,
)
_LIVE_JOIN = re.compile(
    r"""
    people\s*\.\s*(?:some|find|filter|map)
    |\.get\s*\(
    |(?:byId|liveById|personById)\b
    """,
    re.X,
)
_REMOVE_ITEM = re.compile(r"\bremoveItem\s*\(")
_ICLOUD = re.compile(r"\biCloud\b|CloudKit|NSUbiquitous")
_PIN_IPC = re.compile(
    r"\b(?:people_pin|pin_person|set_person_pin|person_pin)(?:_cmd)?\b"
)
_PIN_SQL = re.compile(
    r"""
    \bpeople_pins\b
    |\bpinned_at\b
    |\bpersons\.pinned\b
    |ALTER\s+TABLE\s+persons[\s\S]{0,200}\bpinned\b
    |CREATE\s+TABLE\s+\w*pin
    """,
    re.I | re.X,
)
_PIN_CAP = re.compile(
    r"\b(?:MAX_PINS|PIN_CAP|maxPins|pinCap|MAX_PEOPLE_PINS)\b"
)
_AZ_RAIL = re.compile(r"data-az-rail|az-jump-rail|#376")
_LOCALE_COMPARE = re.compile(r"\blocaleCompare\s*\(")
_RECENT_LABEL = re.compile(r"\bRecent\b")
_AZ_LABEL = re.compile(r"A\s*[–-]\s*Z")
_PERSON_FILTER = re.compile(r"""id\s*=\s*["']person-filter["']""")
_FILTERED_IDS = re.compile(
    r"filteredIds[\s\S]{0,200}filtered\s*\.\s*map"
)
_GHOST_ROW = re.compile(
    r"""person\s*\$\{|\bperson\s*\+\s*|`person\s+\$\{"""
)
_DOCS_PEOPLE_PIN = re.compile(
    r"("
    r"(?:people|person|sidebar).{0,100}pin"
    r"|pin.{0,100}(?:people|person|sidebar)"
    r"|Pinned.{0,80}(?:block|list|people|heading)"
    r")",
    re.I | re.S,
)
_DOCS_LOCAL = re.compile(
    r"("
    r"(?:pin(?:ned)?|Pinned).{0,240}(?:localStorage|local(?:ly)?)"
    r"|(?:localStorage|local(?:ly)?).{0,240}(?:pin(?:ned)?|Pinned)"
    r")",
    re.I | re.S,
)
_DOCS_NOT_ICLOUD = re.compile(
    r"("
    r"(?:pin(?:ned)?|Pinned).{0,240}not iCloud"
    r"|not iCloud.{0,240}(?:pin(?:ned)?|Pinned)"
    r")",
    re.I | re.S,
)
_DOCS_SLASH = re.compile(
    r"("
    r"(?:pin(?:ned)?|Pinned).{0,200}(?:/|filter)"
    r"|(?:/|filter).{0,200}(?:pin(?:ned)?|Pinned)"
    r")",
    re.I | re.S,
)
_DOCS_ARCHIVE = re.compile(
    r"("
    r"(?:pin(?:ned)?|Pinned).{0,200}(?:per[- ]archive|archive)"
    r"|archive.{0,200}(?:pin(?:ned)?|Pinned)"
    r")",
    re.I | re.S,
)
_HEADING_LEN = re.compile(
    r"\b(?:pinnedMatching|hasPinned|pinnedIds|pinIds|pins)\b"
    r"|\.length"
)
_COLLAPSED = re.compile(r"\b(?:sidebarCollapsed|collapsed)\b")
_SKIP = frozenset(
    "if for while switch catch function return typeof new await void "
    "String Number Boolean toLowerCase console people filter map sort "
    "toSorted localeCompare concat".split()
)
_LOCALE_KEYS = ("pinned", "pinPerson", "unpinPerson")
_SIZE_ICON = re.compile(r"""size\s*=\s*["']icon["']""")
_T_PIN_KEY = re.compile(r"""t\(\s*["'](?:pinPerson|unpinPerson)["']\s*\)""")
_T_PIN_PERSON = re.compile(r"""t\(\s*["']pinPerson["']\s*\)""")
_T_UNPIN_PERSON = re.compile(r"""t\(\s*["']unpinPerson["']\s*\)""")
_PIN_TAG = re.compile(r"<Pin\b")
_PIN_OFF_TAG = re.compile(r"<PinOff\b")
_VISIBLE_PIN_WORD = re.compile(r"(?:>|\A)\s*(?:Pin|Unpin)\s*(?:<|\Z)")
_LUCIDE_PIN_DEFAULT = re.compile(
    r"""import\s+(\w+)\s+from\s+["'](?:@lucide/svelte/icons|lucide-svelte/icons)/pin["']"""
)
_LUCIDE_PIN_OFF_DEFAULT = re.compile(
    r"""import\s+(\w+)\s+from\s+["'](?:@lucide/svelte/icons|lucide-svelte/icons)/pin-off["']"""
)
_LUCIDE_NAMED_BLOCK = re.compile(
    r"""import\s+\{([^}]+)\}\s+from\s+["'](?:@lucide/svelte|lucide-svelte)["']"""
)
_ATTR_ASSIGN = re.compile(
    r"""
    \b[\w:-]+\s*=\s*
    (?:
        "[^"]*"
        |'[^']*'
        |\{(?:[^{}]|\{[^{}]*\})*\}
    )
    """,
    re.X,
)
_A11Y_NAME = re.compile(r"display_name|displayName|personLabel|personName")
_A11Y_TIME = re.compile(
    r"[A-Za-z_]\w*\s*\([^)]*\blast_activity_at\b|\bhumanTime\s*\("
)
_NO_PIN_SURFACES = (
    "SearchHits.svelte",
    "SearchPane.svelte",
    "MergeDialog.svelte",
    "CommandPalette.svelte",
)


def _text(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


def _web_file(crate: Path, name: str) -> Path:
    return crate / "web" / "lib" / name


def _if_else_blocks(src: str, cond: str) -> tuple[str, str]:
    m = re.search(rf"\{{#if\s+{cond}\}}", src)
    if not m:
        return "", ""
    start = m.end()
    depth = 1
    i = start
    else_at = -1
    while i < len(src) and depth:
        nxt_if = src.find("{#if", i)
        nxt_else = src.find("{:else", i)
        nxt_end = src.find("{/if}", i)
        cands = [(p, k) for p, k in ((nxt_if, "if"), (nxt_else, "else"), (nxt_end, "end")) if p >= 0]
        if not cands:
            break
        pos, kind = min(cands)
        if kind == "if":
            depth += 1
            i = pos + 4
        elif kind == "else" and depth == 1 and else_at < 0:
            else_at = pos
            i = pos + 6
        elif kind == "end":
            depth -= 1
            if depth == 0:
                mid = else_at if else_at >= 0 else pos
                then = src[start:mid]
                els = src[else_at + 6 : pos] if else_at >= 0 else ""
                return then, els
            i = pos + 5
        else:
            i = pos + 6
    return "", ""


def _locale_keys(src: str) -> set[str]:
    return set(re.findall(r"(?m)^\s+([A-Za-z][A-Za-z0-9_]*)\s*:", src))


def _locale_value(src: str, key: str) -> str:
    m = re.search(rf'(?m)^\s+{re.escape(key)}\s*:\s*("(?:\\.|[^"\\])*")', src)
    return m.group(1) if m else ""


def _expanded_row(each: str) -> str:
    collapsed, expanded = _if_else_blocks(each, r"sidebarCollapsed")
    not_col, _ = _if_else_blocks(each, r"!sidebarCollapsed")
    return "\n".join((expanded, not_col))


def _collapsed_row(each: str) -> str:
    collapsed, _ = _if_else_blocks(each, r"sidebarCollapsed")
    return collapsed


def _has_ghost_pin(block: str) -> bool:
    for m in _PIN_LABEL.finditer(block):
        window = block[max(0, m.start() - 280) : m.end() + 80]
        if _BUTTON.search(window) and _GHOST.search(window):
            return True
    return False


def _pin_icon_locals(src: str) -> tuple[set[str], set[str]]:
    pins: set[str] = set()
    offs: set[str] = set()
    for m in _LUCIDE_PIN_DEFAULT.finditer(src):
        pins.add(m.group(1))
    for m in _LUCIDE_PIN_OFF_DEFAULT.finditer(src):
        offs.add(m.group(1))
    for m in _LUCIDE_NAMED_BLOCK.finditer(src):
        for part in m.group(1).split(","):
            part = part.strip()
            if not part:
                continue
            bits = re.split(r"\s+as\s+", part)
            export = bits[0].strip()
            local = bits[-1].strip()
            if export == "Pin":
                pins.add(local)
            elif export == "PinOff":
                offs.add(local)
    return pins, offs


def _surface_has_pin_icons(src: str, surface: str) -> bool:
    pins, offs = _pin_icon_locals(src)
    used_pin = any(re.search(rf"<{re.escape(n)}\b", surface) for n in pins) or bool(
        _PIN_TAG.search(surface)
    )
    used_off = any(re.search(rf"<{re.escape(n)}\b", surface) for n in offs) or bool(
        _PIN_OFF_TAG.search(surface)
    )
    return used_pin and used_off


def _strip_tag_attrs(html: str) -> str:
    return _ATTR_ASSIGN.sub("", html)


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


def _pin_button_blocks(block: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for open_tag, inner in _button_blocks(block):
        blob = open_tag + "\n" + inner
        if (
            _PIN_LABEL.search(blob)
            or _PIN_TAG.search(inner)
            or _PIN_OFF_TAG.search(inner)
            or _T_PIN_KEY.search(blob)
        ):
            found.append((open_tag, inner))
    return found


def _visible_pin_text(inner: str) -> bool:
    visible = _strip_tag_attrs(inner)
    return bool(_T_PIN_KEY.search(visible) or _VISIBLE_PIN_WORD.search(visible))


def _reads_pin_pref(blob: str) -> bool:
    if _READ_PINS.search(blob):
        return True
    if not (_GETITEM.search(blob) or _LS_BRACKET.search(blob)):
        return False
    return bool(_PIN_KEY_RX.search(blob) or _PIN_PREF_NAME.search(blob))


def _writes_pin_pref(blob: str) -> bool:
    if _WRITE_PINS.search(blob):
        return True
    if not _SETITEM.search(blob):
        return False
    return bool(_PIN_KEY_RX.search(blob) or _PIN_PREF_NAME.search(blob))


def _blob_reads_pins(src: str, blob: str) -> bool:
    if _reads_pin_pref(blob):
        return True
    seen: set[str] = set()
    for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", blob):
        if name in seen or name in _SKIP:
            continue
        seen.add(name)
        inner = _fn_body(src, name)
        if inner and _reads_pin_pref(inner):
            return True
    return False


def _pin_effect_writes(src: str) -> bool:
    for arg in _svelte_effect_args(src):
        if (_PIN_STATE.search(arg) or _PIN_KEY_RX.search(arg)) and _writes_pin_pref(arg):
            return True
    return False


def _has_pin_time_walk(filt: str) -> bool:
    if _PIN_WALK.search(filt):
        return True
    for m in re.finditer(r"for\s*\(\s*const\s+(\w+)\s+of\s+(\w+)", filt):
        src_name = m.group(2)
        window = filt[max(0, m.start() - 400) : m.end() + 220]
        if re.search(
            r"peoplePins|readPeoplePins|readPinsPref|pinsFor|pinIds|pinnedIds|storedPins",
            window,
        ) and re.search(rf"\b{re.escape(src_name)}\b", window):
            return True
    return False


def _heading_window(sidebar: str) -> str:
    filt = _PERSON_FILTER.search(sidebar)
    each = _PEOPLE_EACH.search(sidebar)
    if not filt or not each or each.start() <= filt.start():
        return ""
    return sidebar[filt.start() : each.start()]


def _core_people_blob(root: Path) -> str:
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


def assert_people_pin(crate: Path) -> None:
    """#368: row pin + peoplePins[archive_id] + pins-first filtered."""
    root = repo_root()
    side_path = _web_file(crate, "PeopleSidebar.svelte")
    shell_path = _web_file(crate, "PeopleShell.svelte")
    prefs_path = _web_file(crate, "PeoplePrefs.ts")
    app_path = crate / "web" / "App.svelte"
    api_path = _web_file(crate, "api.ts")
    boot_path = _web_file(crate, "PeopleBoot.ts")
    if not side_path.is_file():
        fail(f"{_ISSUE}: PeopleSidebar.svelte required (row Pin / Unpin + Pinned heading)")
    if not shell_path.is_file():
        fail(f"{_ISSUE}: PeopleShell.svelte required (filtered pins-first)")
    if not prefs_path.is_file():
        fail(f"{_ISSUE}: PeoplePrefs.ts required (interlace.peoplePins helpers)")
    if not app_path.is_file():
        fail(f"{_ISSUE}: App.svelte required (applyStatus re-reads pins)")

    sidebar_raw = side_path.read_text()
    sidebar = _without_comments(sidebar_raw)
    sidebar_mark = _svelte_markup(sidebar_raw)
    shell = _without_comments(shell_path.read_text())
    prefs = _without_comments(prefs_path.read_text())
    app_raw = app_path.read_text()
    app = _without_comments(app_raw)
    api = _without_comments(_text(api_path))
    boot = _without_comments(_text(boot_path))
    en = _text(_web_file(crate, "locales/en.ts"))
    tr = _text(_web_file(crate, "locales/tr.ts"))
    docs = _text(root / "docs" / "user" / "app.md")
    web = _without_comments(_web_logic(crate))
    combo = "\n".join((app, prefs, sidebar, shell, boot))
    keys_src = _without_comments(_text(_web_file(crate, "PeopleKeys.ts")))

    # Keep {#each filtered} + #person-filter + Recent | A–Z (pass today).
    if not _PEOPLE_EACH.search(sidebar_mark) and not _PEOPLE_EACH.search(sidebar):
        fail(f"{_ISSUE}: keep {{#each filtered}} as the one people list (#138 / #312)")
    if not _PERSON_FILTER.search(sidebar_mark) and not _PERSON_FILTER.search(sidebar):
        fail(f"{_ISSUE}: keep id=person-filter (#138)")
    near = ""
    fm = _PERSON_FILTER.search(sidebar)
    if fm:
        near = sidebar[max(0, fm.start() - 500) : fm.end() + 500]
    if not (_RECENT_LABEL.search(near) and _AZ_LABEL.search(near)):
        fail(f"{_ISSUE}: keep compact Recent | A–Z next to #person-filter (#312)")

    each = _people_each_block(sidebar_mark) or _people_each_block(sidebar)
    if not each.strip():
        fail(f"{_ISSUE}: people list {{#each filtered}} body missing")

    # 1) Primary red today: no pin on the expanded row.
    expanded = _expanded_row(each)
    pin_surface = expanded if _PIN_LABEL.search(expanded) else each
    if not _PIN_LABEL.search(pin_surface):
        fail(f"{_ISSUE}: expanded people row needs a quiet ghost Pin / Unpin")
    if not _OWNED_BUTTON.search(sidebar) and not _OWNED_BUTTON.search(sidebar_raw):
        fail(f"{_ISSUE}: Pin / Unpin is an owned ghost Button (not a new kit)")
    if not _has_ghost_pin(pin_surface) and not _has_ghost_pin(each):
        fail(
            f"{_ISSUE}: Pin / Unpin on the expanded row must be a quiet ghost Button "
            '(variant="ghost"; t("pinPerson") / t("unpinPerson"))'
        )
    collapsed = _collapsed_row(each)
    if collapsed and _PIN_LABEL.search(collapsed):
        fail(f"{_ISSUE}: collapsed rail must not host Pin / Unpin (glyphs only)")

    # 2) interlace.peoplePins = { [archive_id]: number[] } in PeoplePrefs.
    ls_keys = _ls_pref_keys(web + "\n" + prefs)
    if _PIN_KEY not in ls_keys and not _PIN_KEY_RX.search(prefs):
        fail(
            f"{_ISSUE}: persist pins in namespaced localStorage "
            "(interlace.peoplePins keyed by archive_id) — "
            "not write_last_path / config.toml / iCloud"
        )
    persist = "\n".join(
        (
            prefs,
            _fn_body(combo, "readPeoplePinsPref"),
            _fn_body(combo, "writePeoplePinsPref"),
            _fn_body(combo, "readPeoplePins"),
            _fn_body(combo, "writePeoplePins"),
            _fn_body(combo, "togglePersonPin"),
            _fn_body(combo, "togglePin"),
        )
    )
    if not _SETITEM.search(persist):
        fail(
            f"{_ISSUE}: persist pins with localStorage.setItem "
            "(interlace.peoplePins; {{ [archive_id]: number[] }})"
        )
    if not _GETITEM.search(persist) and not _LS_BRACKET.search(persist):
        fail(
            f"{_ISSUE}: restore pins from localStorage.getItem "
            "(same interlace.peoplePins key)"
        )
    if not _ARCHIVE_ID.search(prefs) and not _ARCHIVE_ID.search(persist):
        fail(
            f"{_ISSUE}: peoplePins is {{ [archive_id]: number[] }} "
            "(archive id + person id — not a bare number[], not display_name)"
        )
    if re.search(r"\bpath\b", persist) and not _ARCHIVE_ID.search(persist):
        fail(f"{_ISSUE}: key pins by Status.archive_id, not st.path")
    if not re.search(r"number\s*\[\s*\]", persist + "\n" + prefs):
        fail(
            f"{_ISSUE}: each archive's pins are number[] in pin-time order "
            "(first pinned first)"
        )
    if not re.search(
        r"JSON\.parse|Array\.isArray|\|\|\s*\[\]|\?\?\s*\[\]|\{\s*\}",
        persist,
    ):
        fail(
            f"{_ISSUE}: missing / wiped / junk interlace.peoplePins must be no pins"
        )
    if _PIN_CAP.search(prefs) or _PIN_CAP.search(persist) or _PIN_CAP.search(shell):
        fail(f"{_ISSUE}: pins are uncapped (do not invent MAX_PINS / PIN_CAP)")

    # 3) Status.archive_id from existing status JSON; no new IPC.
    if not _STATUS_ARCHIVE.search(api):
        fail(
            f"{_ISSUE}: TS Status must expose archive_id "
            "(already on Archive::status JSON; no new IPC)"
        )
    open_rs = _text(root / "crates" / "interlace-core" / "src" / "db" / "open.rs")
    if '"archive_id"' not in open_rs:
        fail(
            f"{_ISSUE}: status JSON must keep archive_id "
            "(TS Status exposes it; do not add pin IPC)"
        )
    tauri_blob = "\n".join(
        (
            _text(crate / "src" / "people_cmd.rs"),
            _text(crate / "src" / "main.rs"),
            _text(crate / "src" / "ipc.rs"),
            api,
        )
    )
    if _PIN_IPC.search(tauri_blob):
        fail(f"{_ISSUE}: no pin IPC — pins are localStorage only")

    # 4) Quiet t("pinned") heading above {#each filtered}; hide empty / collapsed.
    if not _PINNED_T.search(sidebar_mark) and not _PINNED_T.search(sidebar):
        fail(f"{_ISSUE}: quiet t(\"pinned\") heading required above the people list")
    head = _heading_window(sidebar_mark) or _heading_window(sidebar)
    if not _PINNED_T.search(head):
        fail(
            f"{_ISSUE}: Pinned heading sits below #person-filter / Recent | A–Z "
            "and above {{#each filtered}} (not a toolbar label, not a second listbox)"
        )
    if _PINNED_T.search(each):
        fail(f"{_ISSUE}: t(\"pinned\") is a presentation heading, not a person option")
    pin_head = _PINNED_T.search(sidebar_mark) or _PINNED_T.search(sidebar)
    head_src = sidebar_mark if _PINNED_T.search(sidebar_mark) else sidebar
    if pin_head:
        around = head_src[max(0, pin_head.start() - 280) : pin_head.end() + 120]
        if not _HEADING_LEN.search(around):
            fail(
                f"{_ISSUE}: hide the Pinned heading when the filtered pin list is empty"
            )
        if not _COLLAPSED.search(around) and not _COLLAPSED.search(head):
            fail(
                f"{_ISSUE}: hide the Pinned heading when the sidebar is collapsed"
            )
        if not re.search(r"text-xs|text-muted-foreground|muted", around):
            fail(
                f"{_ISSUE}: Pinned heading is quiet "
                "(text-xs / text-muted-foreground — not a second toolbar)"
            )

    # 5) filtered = haystack, then matching pins first, then the rest.
    filt = _people_filter_window(web) or _people_filter_window(shell)
    if not filt.strip():
        fail(f"{_ISSUE}: PeopleShell `filtered` derivation required (pins-first)")
    has_identity = bool(_PEOPLE_FILTER_IDENTITY_TOKENS.search(filt)) or bool(
        _PEOPLE_FILTER_IDENTITIES_FIELD.search(filt)
    )
    if not has_identity:
        fail(
            f"{_ISSUE}: keep #138 identity haystack "
            "(identity_values on the loaded list) — `/` runs before the pin split"
        )
    if "display_name" not in filt and "displayName" not in filt:
        fail(f"{_ISSUE}: keep #138 people filter matching display_name")
    if not (
        _PIN_STATE.search(filt)
        or _READ_PINS.search(filt)
        or _PIN_KEY_RX.search(filt)
        or re.search(r"\bpinned\b|\bisPinned\b", filt)
    ):
        fail(
            f"{_ISSUE}: `filtered` must list matching pins first, then the rest "
            "(Ada stays at the top after A–Z)"
        )
    if not _CONCAT.search(filt):
        fail(
            f"{_ISSUE}: `filtered` is one array — pinned-matching then rest-matching "
            "(keep a single {{#each filtered}})"
        )
    if not _has_pin_time_walk(filt):
        fail(
            f"{_ISSUE}: pinned segment follows stored pin-time order "
            "(walk the archive's number[]; do not re-sort pins by name / recent)"
        )
    if not _DEDUP.search(filt):
        fail(
            f"{_ISSUE}: a visible pin must not be repeated under Recent | A–Z"
        )
    if not _LIVE_JOIN.search(filt) and not _LIVE_JOIN.search(shell):
        fail(
            f"{_ISSUE}: join pins against live people[] "
            "(tombstoned / missing id is not a ghost row)"
        )
    if _GHOST_ROW.search(each) or _GHOST_ROW.search(sidebar_mark):
        fail(f"{_ISSUE}: do not render person ${{id}} for a stored pin with no live row")
    if not _LOCALE_COMPARE.search(filt):
        fail(
            f"{_ISSUE}: keep A–Z localeCompare on the unpinned remainder "
            "(Recent | A–Z still sorts the rest)"
        )
    if not _FILTERED_IDS.search(shell) and not _FILTERED_IDS.search(keys_src):
        fail(
            f"{_ISSUE}: filteredIds() stays filtered.map "
            "(ArrowUp/Down is pinned-then-rest; do not start #376)"
        )
    if _AZ_RAIL.search(sidebar) or _AZ_RAIL.search(shell):
        fail(f"{_ISSUE}: do not start #376 A–Z jump rail")

    # 6) Write on pin / unpin only; re-read on applyStatus / File → Open.
    if not _blob_reads_pins(combo, sidebar) and not _WRITE_PINS.search(sidebar):
        fail(f"{_ISSUE}: toggling Pin / Unpin must write this archive's peoplePins array")
    if _pin_effect_writes(app) or _pin_effect_writes(shell):
        fail(
            f"{_ISSUE}: do not persist peoplePins from a bare $effect "
            "(write on Pin / Unpin only)"
        )
    apply_st = _fn_body(app, "applyStatus") or _fn_body(app_raw, "applyStatus")
    derived_pins = bool(
        re.search(r"\$derived", shell + "\n" + app)
        and _ARCHIVE_ID.search(shell + "\n" + app)
        and (
            _READ_PINS.search(shell + "\n" + app)
            or _PIN_KEY_RX.search(shell + "\n" + app)
            or _PIN_STATE.search(shell + "\n" + app)
        )
    )
    if not _blob_reads_pins(combo, apply_st) and not derived_pins:
        fail(
            f"{_ISSUE}: File → Open / applyStatus must re-read pins for B's archive_id "
            "(A's ids must not paint on B)"
        )
    if not _ARCHIVE_ID.search(shell + "\n" + app + "\n" + prefs):
        fail(f"{_ISSUE}: pin read/write must use Status.archive_id")
    switch = _fn_body(boot, "switchToSetup") or _fn_body(combo, "switchToSetup")
    for m in _REMOVE_ITEM.finditer(switch):
        window = switch[max(0, m.start() - 40) : m.end() + 80]
        if _PIN_KEY_RX.search(window) or _PIN_PREF_NAME.search(window):
            fail(
                f"{_ISSUE}: do not removeItem interlace.peoplePins in switchToSetup "
                "(leave the pref; resolve against the next archive_id)"
            )

    # 7) Not SQLite / config.toml / iCloud.
    if _LAST_PATH_API.search(persist) or _CONFIG_TOML.search(persist):
        fail(
            f"{_ISSUE}: do not persist pins via write_last_path / "
            "read_last_path / config.toml (localStorage only)"
        )
    if _ICLOUD.search(persist):
        fail(f"{_ISSUE}: do not persist pins to iCloud")
    session = _text(root / "crates" / "interlace-core" / "src" / "session.rs")
    wl = _rust_fn_body(_without_comments(session), "write_last_path")
    if re.search(r"people_pins|peoplePins|people_pin", wl, re.I):
        fail(
            f"{_ISSUE}: do not rewrite session.rs write_last_path to dump pins "
            "(config.toml is the last-archive pointer, not chrome prefs)"
        )
    core_blob = _core_people_blob(root)
    if _PIN_SQL.search(core_blob):
        fail(
            f"{_ISSUE}: no SQLite pin table / persons.pinned column "
            "(pins are localStorage only)"
        )

    # 8) No pins on Search / merge / palette.
    for name in _NO_PIN_SURFACES:
        src = _text(_web_file(crate, name))
        if _PIN_LABEL.search(src) or _PINNED_T.search(src) or _PIN_KEY_RX.search(src):
            fail(f"{_ISSUE}: no pin control / Pinned block on {name}")

    # 9) en+tr pinned / pinPerson / unpinPerson; tr is not an English copy.
    en_keys = _locale_keys(en)
    tr_keys = _locale_keys(tr)
    for key in _LOCALE_KEYS:
        if key not in en_keys or key not in tr_keys:
            fail(
                f"{_ISSUE}: chrome key {key} must exist in both "
                "locales/en.ts and locales/tr.ts"
            )
        ev, tv = _locale_value(en, key), _locale_value(tr, key)
        if ev and tv and ev == tv:
            fail(f"{_ISSUE}: tr.ts {key} must not be an English copy (#131 / #278)")

    # 10) D24 — local Pinned block, per archive, not iCloud; `/` still filters.
    if not docs.strip():
        fail(f"{_ISSUE}: docs/user/app.md required — local Pinned block above the people list")
    if not _DOCS_PEOPLE_PIN.search(docs):
        fail(
            f"{_ISSUE}: docs/user/app.md must say you can pin people "
            "to a Pinned block on the list"
        )
    if not _DOCS_LOCAL.search(docs):
        fail(
            f"{_ISSUE}: docs/user/app.md must say pins are local (localStorage)"
        )
    if not _DOCS_NOT_ICLOUD.search(docs):
        fail(f"{_ISSUE}: docs/user/app.md must say pins are not iCloud")
    if not _DOCS_ARCHIVE.search(docs):
        fail(f"{_ISSUE}: docs/user/app.md must say pins are per archive")
    if not _DOCS_SLASH.search(docs):
        fail(f"{_ISSUE}: docs/user/app.md must say / still filters the Pinned block")

    # 11) Keep #212 / #213 / #366 / #367 surfaces (do not delete those asserts).
    if not re.search(r"\bdata-people-sidebar\b", sidebar_mark):
        fail(f"{_ISSUE}: keep data-people-sidebar (#212)")
    inspector = _text(_web_file(crate, "PeopleInspector.svelte"))
    if not re.search(r"\bdata-person-inspector\b", inspector):
        fail(f"{_ISSUE}: keep data-person-inspector (#213)")
    if "PersonAvatar" not in sidebar_mark and "PersonAvatar" not in sidebar:
        fail(f"{_ISSUE}: keep PersonAvatar on the people row (#366)")
    if not re.search(r"\bpersonName\b|\bnameDraft\b|<Input\b", inspector):
        fail(f"{_ISSUE}: keep inspector rename Input (#367)")
    empty = re.search(r"filtered\.length\s*===?\s*0", sidebar)
    if not empty:
        fail(
            f"{_ISSUE}: EmptyState / No match still keys off filtered.length "
            "(a pinned-only match must not look empty)"
        )


def assert_people_pin_icon(crate: Path) -> None:
    """#368-icon: expanded-row pin is Lucide Pin / PinOff, not visible Pin text."""
    side_path = _web_file(crate, "PeopleSidebar.svelte")
    if not side_path.is_file():
        fail(f"{_ICON_ISSUE}: PeopleSidebar.svelte required (icon pin on the expanded row)")
    sidebar_raw = side_path.read_text()
    sidebar = _without_comments(sidebar_raw)
    sidebar_mark = _svelte_markup(sidebar_raw)
    each = _people_each_block(sidebar_mark) or _people_each_block(sidebar)
    if not each.strip():
        fail(f"{_ICON_ISSUE}: people list {{#each filtered}} body missing")
    expanded = _expanded_row(each)
    pin_surface = expanded if (_PIN_LABEL.search(expanded) or _PIN_TAG.search(expanded) or _PIN_OFF_TAG.search(expanded)) else each
    src = sidebar_raw + "\n" + sidebar
    pin_btns = _pin_button_blocks(pin_surface) or _pin_button_blocks(each)
    has_icons = _surface_has_pin_icons(src, pin_surface)
    has_text = any(_visible_pin_text(inner) for _, inner in pin_btns) if pin_btns else True
    if not has_icons or has_text:
        fail(
            f"{_ICON_ISSUE}: expanded-row pin control must be a Lucide Pin / PinOff "
            "icon (import Pin / PinOff from lucide, or <Pin / <PinOff in markup), "
            'not {t("pinPerson")} / {t("unpinPerson")} as the Button\'s visible child text'
        )
    if not pin_btns:
        fail(f"{_ICON_ISSUE}: expanded-row pin control missing (ghost Button + Pin / PinOff)")
    if not any(_SIZE_ICON.search(open_tag) for open_tag, _ in pin_btns):
        fail(f'{_ICON_ISSUE}: pin control is an owned ghost Button size="icon"')
    a11y: list[str] = []
    pin_labels: list[str] = []
    for open_tag, _ in pin_btns:
        a11y.extend(_attr_brace_values(open_tag, "aria-label"))
        a11y.extend(_attr_brace_values(open_tag, "title"))
        pin_labels.extend(_attr_brace_values(open_tag, "aria-label"))
    a11y_blob = "\n".join(a11y)
    if not _T_PIN_PERSON.search(a11y_blob) or not _T_UNPIN_PERSON.search(a11y_blob):
        fail(
            f'{_ICON_ISSUE}: t("pinPerson") / t("unpinPerson") must remain the '
            "accessible name (aria-label)"
        )
    if not pin_labels:
        fail(
            f"{_ICON_ISSUE}: pin Button aria-label must keep #184 name + short time "
            "(do not use a pin-only accessible name)"
        )
    for lab in pin_labels:
        if not _A11Y_NAME.search(lab):
            fail(
                f"{_ICON_ISSUE}: pin aria-label must include display_name "
                "(#184 — every aria-label inside {{#each filtered}})"
            )
        if not _A11Y_TIME.search(lab):
            fail(
                f"{_ICON_ISSUE}: pin aria-label must include humanTime(p.last_activity_at) "
                '(#184 — a pin-only aria-label={t("pinPerson")} fails #184)'
            )
    collapsed = _collapsed_row(each)
    if collapsed and (
        _PIN_TAG.search(collapsed)
        or _PIN_OFF_TAG.search(collapsed)
        or _surface_has_pin_icons(src, collapsed)
    ):
        fail(f"{_ICON_ISSUE}: collapsed rail must not host the pin icon (glyphs only)")
