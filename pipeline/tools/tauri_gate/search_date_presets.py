"""#319 — compact Search date presets (7d / 30d / this year / Any).

Confirmed mix: owned `type="button"` chips next to `#from` / `#to` inside
`data-search-filters`. Fill host-local `YYYY-MM-DD` via `getFullYear` /
`getMonth` / `getDate` (never `toISOString` / `getUTC*` / `Date.UTC`).
Windows: 7d = today−6→today; 30d = today−29→today; year = `{year}-01-01`
→today; Any/Clear = both `""`. `run()` sends date-only `to` inclusive
(`T23:59:59` on the send string). Click fills then `run()` /
`cancelDebounce`. No from/to `$effect`. Highlight is derived. en+tr
same ChromeKeys. Keep #209 / #268 / #270 / #318. D24. Not a calendar.

Must-IDs: preset-chrome, preset-clear, preset-fill-local, preset-7d,
preset-30d, preset-year, preset-send, preset-invalid, preset-custom,
preset-empty-q, preset-pressed, preset-i18n, preset-keep-209,
preset-keep-268, preset-keep-270, preset-keep-318, preset-d24,
preset-share-window.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.import_boot_guards import _ls_pref_keys
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.reopen_last_lib import _GETITEM, _SETITEM
from tauri_gate.scan import (
    _CONFIG_TOML,
    _expand_fn_calls,
    _function_body,
    _match_closer,
    _svelte_markup,
    _ts_fn_body,
    _web_logic,
    _without_comments,
)
from tauri_gate.search_field_keys import _API_SEARCH_CALL, _has_search_as_you_type
from tauri_gate.search_picker_lib import (
    _SEARCH_API_PLATFORM_ARG,
    _SEARCH_CDN,
    _SEARCH_DATE_CMP,
    _SEARCH_DATE_ERROR_SET,
    _SEARCH_DATE_PARSE,
    _SEARCH_DATEPICKER_PKG,
    _SEARCH_FILTERS_HOOK,
    _SEARCH_FROM_EMPTY_ANY,
    _SEARCH_Q_ID,
    _date_input_bound,
    _hook_element_blocks,
    _search_run_surface,
)
from tauri_gate.status_toasts_chrome import _claim_without_negation, _windows_around
from tauri_gate.status_toasts_toast import _svelte_effect_args

_ISSUE = "#319"

_BTN_BLOCK = re.compile(
    r"<(?:Button|button)\b[^>]*>[\s\S]{0,500}?</(?:Button|button)>",
    re.I,
)
_BTN_OPEN = re.compile(r"<(?:Button|button)\b[^>]*>", re.I)
_TYPE_SUBMIT = re.compile(r"""type\s*=\s*["']submit["']""", re.I)
_TYPE_BUTTON = re.compile(r"""type\s*=\s*["']button["']""", re.I)
_NATIVE_BUTTON = re.compile(r"<button\b", re.I)
_OWNED_BUTTON = re.compile(r"<Button\b")
_SIZE_SM = re.compile(r"""size\s*=\s*["']sm["']""", re.I)
_COMPACT = re.compile(r"\b(?:text-xs|h-8|size\s*=\s*[\"']sm[\"'])", re.I)
_SELECT = re.compile(r"<select\b", re.I)
_CALENDAR_WIDGET = re.compile(
    r"("
    r"<Calendar\b"
    r"|<DatePicker\b"
    r"|<DateRange\b"
    r"|daterangepicker"
    r"|flatpickr"
    r"|litepicker"
    r"|data-calendar"
    r")",
    re.I,
)
_PERSON_CLEAR = re.compile(r"\bclearPerson\b")
_PERSON_PICKER = re.compile(r"data-person-picker")
_OPTION_ANY = re.compile(r"<option\b[^>]*>\s*Any\s*</option>", re.I)

_LAB_7 = re.compile(
    r"("
    r"7\s*days?"
    r"|last\s*7"
    r"|7\s*gün"
    r"|son\s*7"
    r"|search(?:Date|Preset|Last)?7"
    r"|[\"']7d[\"']"
    r")",
    re.I,
)
_LAB_30 = re.compile(
    r"("
    r"30\s*days?"
    r"|last\s*30"
    r"|30\s*gün"
    r"|son\s*30"
    r"|search(?:Date|Preset|Last)?30"
    r"|[\"']30d[\"']"
    r")",
    re.I,
)
_LAB_YEAR = re.compile(
    r"("
    r"this\s*year"
    r"|bu\s*y[ıi]l"
    r"|search(?:Date|Preset)?(?:This)?Year"
    r"|[\"']year[\"']"
    r"|[\"']thisYear[\"']"
    r")",
    re.I,
)
_LAB_ANY = re.compile(
    r"("
    r"\bAny\b"
    r"|\bClear\b"
    r"|tümü"
    r"|temizle"
    r"|search(?:Date|Preset)?(?:Any|Clear)"
    r"|[\"']any[\"']"
    r"|[\"']clear[\"']"
    r")",
    re.I,
)
_T_CALL = re.compile(r"""\bt\s*\(\s*["']([A-Za-z_][A-Za-z0-9_]*)["']\s*\)""")
_EXISTING_DATE_KEYS = frozenset(
    {
        "searchFrom",
        "searchTo",
        "searchDateInvalid",
        "searchFilters",
        "typeAQuery",
        "noHits",
        "search",
        "searchPlaceholder",
        "cancel",
    }
)

_FROM_ASSIGN = re.compile(r"\bfrom\s*=\s*")
_TO_ASSIGN = re.compile(r"\bto\s*=\s*")
_STATE_INIT = re.compile(r"\$state")
_EMPTY_ASSIGN = re.compile(
    r"\bfrom\s*=\s*(?:\"\"|''|``)\s*;[\s\S]{0,80}\bto\s*=\s*(?:\"\"|''|``)"
    r"|\bto\s*=\s*(?:\"\"|''|``)\s*;[\s\S]{0,80}\bfrom\s*=\s*(?:\"\"|''|``)"
)
_LOCAL_Y = re.compile(r"\bgetFullYear\s*\(")
_LOCAL_M = re.compile(r"\bgetMonth\s*\(")
_LOCAL_D = re.compile(r"\bgetDate\s*\(")
_UTC_FILL = re.compile(
    r"("
    r"\btoISOString\s*\("
    r"|\bgetUTC(?:FullYear|Month|Date|Hours|Minutes|Seconds|Day)\s*\("
    r"|\bDate\.UTC\s*\("
    r")",
)
_LOCAL_DAY = re.compile(r"\blocalDay\s*\(|\bformatTime\b|\bwallClockDigits\s*\(")
_FORMAT_TIME_IMPORT = re.compile(
    r"""from\s*["'][^"']*formatTime[^"']*["']"""
)
_DAY_BACK_6 = re.compile(
    r"("
    r"getDate\s*\(\s*\)\s*-\s*6\b"
    r"|setDate\s*\([^)]{0,60}-\s*6\b"
    r"|-\s*6\b"
    r"|\b6\s*:"
    r"|:\s*6\b"
    r"|\?\s*6\b"
    r"|days?\s*[:=]\s*6\b"
    r"|back\s*=\s*6\b"
    r")"
)
_DAY_BACK_29 = re.compile(
    r"("
    r"getDate\s*\(\s*\)\s*-\s*29\b"
    r"|setDate\s*\([^)]{0,60}-\s*29\b"
    r"|-\s*29\b"
    r"|\b29\s*:"
    r"|:\s*29\b"
    r"|\?\s*29\b"
    r"|days?\s*[:=]\s*29\b"
    r"|back\s*=\s*29\b"
    r")"
)
_DAY_BACK_7 = re.compile(
    r"getDate\s*\(\s*\)\s*-\s*7\b|setDate\s*\([^)]{0,60}-\s*7\b"
)
_DAY_BACK_30 = re.compile(
    r"getDate\s*\(\s*\)\s*-\s*30\b|setDate\s*\([^)]{0,60}-\s*30\b"
)
_ROLLING_7 = re.compile(r"\b168\b|7\s*\*\s*24|24\s*\*\s*7")
_ROLLING_30 = re.compile(r"\b720\b|30\s*\*\s*24|24\s*\*\s*30")
_YEAR_START = re.compile(
    r"("
    r"-01-01"
    r"|getFullYear\s*\(\s*\)\s*\}?\s*-\s*01-01"
    r"|setMonth\s*\(\s*0\s*\)"
    r"|getMonth\s*\(\s*\)\s*[,+].{0,20}0"
    r"|[\"']-01-01[\"']"
    r")"
)
_DAYS_365 = re.compile(r"\b365\b")
_INCLUSIVE_TO = re.compile(r"T23:59:59(?:\.\d+)?Z?")
_BARE_TO_SEND = re.compile(
    r"\bto\s*:\s*to(?:\s*\.\s*trim\s*\(\s*\))?\s*\|\|\s*(?:null|undefined)"
)
_FROM_DATE_ONLY = re.compile(
    r"\bfrom\s*:\s*from(?:\s*\.\s*trim\s*\(\s*\))?\s*\|\|\s*(?:null|undefined)"
)
_TO_EMPTY_NULL = re.compile(
    r"("
    r"\bto\s*:\s*[^,}]{0,80}\|\|\s*(?:null|undefined)"
    r"|\bto\s*:\s*[^,}]{0,80}\?\?\s*(?:null|undefined)"
    r"|\bto\s*:\s*[^,}]{0,80}\?\s*[^,}]{0,80}:\s*(?:null|undefined)"
    r"|!\s*to(?:\s*\.\s*trim\s*\(\s*\))?\s*\?\s*(?:null|undefined)"
    r")"
)
_T23_ON_ASSIGN = re.compile(
    r"\b(?:from|to)\s*=\s*[^;\n]{0,80}T23:59:59"
)
_CANCEL_DEBOUNCE = re.compile(r"\bcancelDebounce\s*\(")
_RUN_CALL = re.compile(r"\brun\s*\(")
_CLEAR_IDLE = re.compile(r"\bclearHitsIdle\s*\(")
_Q_TRIM = re.compile(r"(?:query|q)\s*(?:\?|\.)\s*trim\s*\(\s*\)")
_PRESSED_ATTR = re.compile(
    r"("
    r"aria-pressed\s*="
    r"|data-pressed\s*="
    r"|data-state\s*="
    r"|data-active\s*="
    r"|aria-current\s*="
    r")",
    re.I,
)
_STICKY_PRESET = re.compile(
    r"\blet\s+(?:datePreset|selectedPreset|activePreset|searchDatePreset|"
    r"pressedPreset|pickedPreset)\s*=\s*\$state"
)
_DERIVED = re.compile(r"\$derived(?:\.by)?\s*\(")
_MATCH_HELPER = re.compile(
    r"\b(?:presetPressed|isPreset(?:Active|Pressed|Selected)|matchesPreset|"
    r"datePresetMatch|presetMatch|windowMatches|isDatePreset)\b"
)
_DATE_PERSIST = re.compile(
    r"("
    r"interlace\.(?:lastSearchFrom|lastSearchTo|searchFrom|searchTo|"
    r"searchDatePreset|lastDateFrom|lastDateTo|searchDates)"
    r"|lastSearchFrom|lastSearchTo|searchDatePreset|lastDateFrom|lastDateTo"
    r")",
    re.I,
)
_DATE_LS_KEY = re.compile(
    r"("
    r"lastSearchFrom|lastSearchTo|searchFrom|searchTo|searchDate|"
    r"searchDates|lastDateFrom|lastDateTo|datePreset"
    r")",
    re.I,
)
_ALLOWED_LS = frozenset(
    {
        "interlace.peopleSidebarCollapsed",
        "interlace.density",
        "interlace.lastView",
        "interlace.lastPersonId",
        "interlace.includeGroups",
        "interlace.peopleSort",
    }
)
_SESSION_STORE = re.compile(r"\bsessionStorage\b")
_ICLOUD = re.compile(r"\biCloud\b|CloudKit|NSUbiquitous")
_TZ_PICKER = re.compile(
    r"("
    r"timezone[-_ ]?picker"
    r"|tz[-_ ]?picker"
    r"|timeZoneSelect"
    r"|IANA\s+time\s*zone"
    r")",
    re.I,
)
_TZDATA = re.compile(r"\btzdata\b|@formatjs/intl-datetimeformat")
_READONLY_DATE = re.compile(
    r"<(?:Input|input)\b[^>]{0,400}(?:id\s*=\s*[\"'](?:from|to)[\"'])"
    r"[^>]{0,200}(?:readonly|disabled)\b",
    re.I,
)
_DOCS_PRESETS = re.compile(
    r"("
    r"presets?"
    r"|7\s*days?.{0,40}30\s*days?"
    r"|7\s*g[uü]n.{0,40}30"
    r")",
    re.I | re.S,
)
_DOCS_FILL = re.compile(
    r"("
    r"fill(?:s|ed)?\s+(?:the\s+)?date"
    r"|date filters?.{0,40}fill"
    r"|presets?.{0,80}fill"
    r")",
    re.I | re.S,
)
_DOCS_MAC_TZ = re.compile(
    r"("
    r"(?:Mac|host)\s+time\s*zone"
    r"|Mac\s+TZ"
    r")",
    re.I,
)
_DOCS_EMPTY_ANY = re.compile(
    r"("
    r"(?:empty|Any|Clear)\s*(?:/|\s+or\s+)?\s*(?:Any|empty|Clear)?"
    r".{0,40}(?:any|no date)"
    r"|empty\s*=\s*any"
    r")",
    re.I | re.S,
)
_DOCS_UTC = re.compile(
    r"("
    r"(?:storage|JSON|FTS|archive).{0,60}UTC"
    r"|UTC.{0,60}(?:storage|JSON|FTS|archive)"
    r")",
    re.I | re.S,
)
_DOCS_NOT_CALENDAR = re.compile(r"not a calendar", re.I)
_DAYS_ARE_UTC = re.compile(
    r"("
    r"days?\s+are\s+UTC"
    r"|UTC\s+(?:calendar\s+)?days?"
    r"|presets?.{0,40}UTC\s+date"
    r")",
    re.I,
)
_DATES_SURVIVE = re.compile(
    r"("
    r"(?:reopen|remount|quit|new session).{0,80}(?:restore|keep|survive).{0,40}date"
    r"|dates?.{0,40}(?:survive|restored|persist).{0,40}(?:reopen|remount|quit)"
    r")",
    re.I | re.S,
)
_CALENDAR_WORD = re.compile(r"\bcalendar\b", re.I)
_SPOTLIGHT = re.compile(r"\bSpotlight\b")
_MULTI_TAB = re.compile(r"\bmulti[- ]tab\b", re.I)
_DATE_PRESET_WINDOW_KIND = re.compile(r"\bdatePresetWindow\s*\(\s*kind\s*\)")
_NEW_DATE_YMD_MINUS = re.compile(
    r"new\s+Date\s*\(\s*[A-Za-z_$][\w$]*\s*,\s*[A-Za-z_$][\w$]*\s*,"
    r"\s*[A-Za-z_$][\w$]*\s*-\s*\d+"
)
_APPLY_WINDOW_DOT = re.compile(
    r"\bfrom\s*=\s*datePresetWindow\s*\(\s*kind\s*\)\s*\.\s*from\b"
    r"[\s\S]{0,160}\bto\s*=\s*datePresetWindow\s*\(\s*kind\s*\)\s*\.\s*to\b"
    r"|\bto\s*=\s*datePresetWindow\s*\(\s*kind\s*\)\s*\.\s*to\b"
    r"[\s\S]{0,160}\bfrom\s*=\s*datePresetWindow\s*\(\s*kind\s*\)\s*\.\s*from\b"
)
_APPLY_WINDOW_DESTRUCTURE = re.compile(
    r"\(\s*\{\s*from\s*,\s*to\s*\}\s*=\s*datePresetWindow\s*\(\s*kind\s*\)"
)
_APPLY_WINDOW_BIND = re.compile(
    r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*datePresetWindow\s*\(\s*kind\s*\)"
)
_APPLY_WINDOW_RENAME = re.compile(
    r"(?:const|let|var)\s*\{\s*from\s*:\s*([A-Za-z_$][\w$]*)\s*,"
    r"\s*to\s*:\s*([A-Za-z_$][\w$]*)\s*\}\s*=\s*datePresetWindow\s*\(\s*kind\s*\)"
)


def _read(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


def _docs_blob() -> str:
    root = repo_root()
    parts: list[str] = []
    for name in ("app.md", "search.md"):
        p = root / "docs" / "user" / name
        if p.is_file():
            parts.append(p.read_text())
    return "\n".join(parts)


def _skip_ws(src: str, i: int) -> int:
    n = len(src)
    while i < n and src[i] in " \t\n\r":
        i += 1
    return i


def _brace_or_expr(src: str, i: int) -> str:
    i = _skip_ws(src, i)
    if i >= len(src):
        return ""
    if src[i] == "{":
        close = _match_closer(src, i)
        return src[i + 1 : close] if close >= 0 else src[i + 1 :]
    j = i
    n = len(src)
    depth = 0
    while j < n:
        c = src[j]
        if c in "{(":
            depth += 1
        elif c in "})":
            if depth == 0:
                break
            depth -= 1
        elif c in ";," and depth == 0:
            break
        j += 1
    return src[i:j]


def _onclick_bodies(src: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(r"on:?click(?:\|\w+)*\s*=\s*\{", src, re.I):
        body = _brace_or_expr(src, m.end() - 1)
        if body.strip():
            out.append(body)
    return out


def _named_fn_bodies(src: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for m in re.finditer(
        r"(?:async\s+)?function\s+([A-Za-z_][\w]*)\s*\("
        r"|(?:const|let|var)\s+([A-Za-z_][\w]*)\s*=\s*(?:async\s*)?(?:function\s*)?\(",
        src,
    ):
        name = m.group(1) or m.group(2)
        if not name or name in seen:
            continue
        seen.add(name)
        body = _ts_fn_body(src, name) or _function_body(src, name)
        if body:
            out.append((name, body))
    return out


def _is_state_init(src: str, pos: int) -> bool:
    window = src[max(0, pos - 12) : pos + 40]
    return bool(_STATE_INIT.search(window))


def _assigns_from_to(body: str) -> bool:
    from_ok = False
    to_ok = False
    for m in _FROM_ASSIGN.finditer(body):
        if not _is_state_init(body, m.start()):
            from_ok = True
            break
    for m in _TO_ASSIGN.finditer(body):
        if not _is_state_init(body, m.start()):
            to_ok = True
            break
    return from_ok and to_ok


def _fill_entry_bodies(src: str) -> list[str]:
    """Functions / click handlers that write both from and to."""
    out: list[str] = []
    for name, body in _named_fn_bodies(src):
        if name == "run":
            continue
        if _assigns_from_to(body):
            out.append(body)
    for body in _onclick_bodies(src):
        expanded = _expand_fn_calls(src, body)
        if _assigns_from_to(expanded) or _assigns_from_to(body):
            out.append(expanded)
    return out


def _fill_surface(src: str) -> str:
    chunks = [_expand_fn_calls(src, b) for b in _fill_entry_bodies(src)]
    return "\n".join(chunks)


def _hook_blob(markup: str) -> str:
    return "\n".join(_hook_element_blocks(markup, _SEARCH_FILTERS_HOOK))


def _date_neighborhood(hook: str) -> str:
    """Window around #from / #to inside data-search-filters."""
    from_m = re.search(r"""\bid\s*=\s*["']from["']""", hook, re.I)
    to_m = re.search(r"""\bid\s*=\s*["']to["']""", hook, re.I)
    if not from_m and not to_m:
        return hook
    start = from_m.start() if from_m else to_m.start()  # type: ignore[union-attr]
    end = to_m.end() if to_m else from_m.end()  # type: ignore[union-attr]
    if to_m and from_m and to_m.start() < from_m.start():
        start = to_m.start()
        end = from_m.end()
    return hook[max(0, start - 500) : end + 1000]


def _in_person_picker(hook: str, pos: int) -> bool:
    for m in _PERSON_PICKER.finditer(hook):
        # cheap: person-picker block is the wrapping div; treat ±800 as inside
        if abs(pos - m.start()) < 800 and pos >= m.start():
            # stop at the next top-level date label if present
            return pos < m.start() + 1200
    return False


def _classify_blob(blob: str) -> set[str]:
    found: set[str] = set()
    if _LAB_7.search(blob):
        found.add("7d")
    if _LAB_30.search(blob):
        found.add("30d")
    if _LAB_YEAR.search(blob):
        found.add("year")
    if _LAB_ANY.search(blob):
        found.add("any")
    return found


def _preset_button_blobs(near: str, hook: str) -> list[str]:
    out: list[str] = []
    for m in _BTN_BLOCK.finditer(near):
        tag = m.group(0)
        if _TYPE_SUBMIT.search(tag):
            continue
        if _PERSON_CLEAR.search(tag):
            continue
        # Map match offset back onto hook for person-picker exclusion.
        abs_pos = hook.find(tag[: min(40, len(tag))]) if tag else -1
        if abs_pos >= 0 and _in_person_picker(hook, abs_pos):
            continue
        if _OPTION_ANY.search(tag):
            continue
        out.append(tag)
    return out


def _preset_kinds(near: str, hook: str, script: str) -> set[str]:
    kinds: set[str] = set()
    for tag in _preset_button_blobs(near, hook):
        kinds |= _classify_blob(tag)
    kinds |= _classify_blob(near)
    # {#each datePresets as p} — classify the list in script.
    each = re.search(
        r"\{#each\s+([A-Za-z_][\w]*)\b",
        near,
    )
    if each:
        name = each.group(1)
        win = _windows_around(
            script,
            re.compile(rf"\b{re.escape(name)}\s*="),
            before=40,
            after=700,
        )
        kinds |= _classify_blob(win)
    return kinds


def _preset_controls_ok(near: str) -> bool:
    """At least one compact type=button control in the date neighborhood."""
    opens = list(_BTN_OPEN.finditer(near))
    if not opens:
        return False
    for m in opens:
        tag = m.group(0)
        if _TYPE_SUBMIT.search(tag):
            continue
        if _PERSON_CLEAR.search(tag):
            continue
        native = bool(_NATIVE_BUTTON.search(tag))
        owned = bool(_OWNED_BUTTON.search(tag))
        if native and not _TYPE_BUTTON.search(tag):
            continue
        if owned and _TYPE_SUBMIT.search(tag):
            continue
        if owned or _TYPE_BUTTON.search(tag):
            return True
    return False


def _preset_compact(near: str) -> bool:
    if _SIZE_SM.search(near) or _COMPACT.search(near):
        return True
    for tag in _BTN_OPEN.findall(near):
        if _TYPE_SUBMIT.search(tag) or _PERSON_CLEAR.search(tag):
            continue
        if _SIZE_SM.search(tag) or _COMPACT.search(tag):
            return True
    return False


def _select_is_date_preset(hook: str) -> bool:
    for m in _SELECT.finditer(hook):
        window = hook[m.start() : m.start() + 500]
        if _LAB_7.search(window) and _LAB_30.search(window):
            return True
    return False


def _q_region(markup: str, hook: str) -> str:
    q = _SEARCH_Q_ID.search(markup)
    if not q:
        return ""
    chunk = markup[max(0, q.start() - 80) : q.end() + 400]
    # Strip the filters hook so #q siblings are the leftover.
    if hook and hook in chunk:
        chunk = chunk.replace(hook[:200], "")
    return chunk


def _reads_from_to(blob: str) -> bool:
    return bool(re.search(r"\bfrom\b", blob) and re.search(r"\bto\b", blob))


def _effect_searches(blob: str) -> bool:
    return bool(_RUN_CALL.search(blob) or _API_SEARCH_CALL.search(blob))


def _idle_on_empty_q(blob: str) -> bool:
    """True if empty q idles (clearHitsIdle / return) instead of api.search."""
    if not _Q_TRIM.search(blob) and not re.search(r"!\s*q\b", blob):
        return False
    if _CLEAR_IDLE.search(blob) and re.search(r"\breturn\b", blob):
        return True
    # `if (!q.trim()) return` before api.search, even without clearHitsIdle.
    for m in re.finditer(
        rf"if\s*\(\s*!\s*{_Q_TRIM.pattern}\s*\)",
        blob,
    ):
        rest = blob[m.end() : m.end() + 160]
        if re.search(r"\breturn\b", rest) or _CLEAR_IDLE.search(rest):
            return True
    return False


def _pressed_surface(markup: str, script: str, near: str) -> str:
    parts = [near]
    for m in _PRESSED_ATTR.finditer(near):
        parts.append(near[m.start() : m.start() + 220])
    for m in _DERIVED.finditer(script):
        arg = _brace_or_expr(script, m.end() - 1)
        if _reads_from_to(arg) or _MATCH_HELPER.search(arg):
            parts.append(arg)
    for name, body in _named_fn_bodies(script):
        if _MATCH_HELPER.search(name) or _MATCH_HELPER.search(body):
            if _reads_from_to(body):
                parts.append(body)
    # variant / class driven by a match helper
    if _MATCH_HELPER.search(near) or _MATCH_HELPER.search(script):
        parts.append(_windows_around(script, _MATCH_HELPER, before=40, after=240))
        parts.append(_windows_around(near, _MATCH_HELPER, before=40, after=160))
    return "\n".join(parts)


def _t_keys(blob: str) -> list[str]:
    return _T_CALL.findall(blob)


def _named_body(src: str, name: str) -> str:
    return _ts_fn_body(src, name) or _function_body(src, name) or ""


def _apply_assigns_window(body: str) -> bool:
    """True when applyDatePreset assigns from/to from datePresetWindow(kind)."""
    if _APPLY_WINDOW_DOT.search(body) or _APPLY_WINDOW_DESTRUCTURE.search(body):
        return True
    bind = _APPLY_WINDOW_BIND.search(body)
    if bind:
        ident = re.escape(bind.group(1))
        if re.search(rf"\bfrom\s*=\s*{ident}\s*\.\s*from\b", body) and re.search(
            rf"\bto\s*=\s*{ident}\s*\.\s*to\b", body
        ):
            return True
    dest = _APPLY_WINDOW_RENAME.search(body)
    if dest:
        a, b = re.escape(dest.group(1)), re.escape(dest.group(2))
        if re.search(rf"\bfrom\s*=\s*{a}\b", body) and re.search(
            rf"\bto\s*=\s*{b}\b", body
        ):
            return True
    return False


def assert_search_date_presets(crate: Path) -> None:
    """#319: compact 7d / 30d / this year / Any fill `#from` / `#to` locally.

    Click fills host-local YYYY-MM-DD then run() (cancelDebounce). Date-only
    `to` is sent inclusive. Highlight is derived. Empty `#q` still idles.
    Keep #209 / #268 / #270 / #318. D24. Not a calendar. Ada only.
    applyDatePreset assigns from/to from datePresetWindow(kind) only.
    """
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail(
            f"{_ISSUE}: SearchPane.svelte required "
            "(date presets live next to #from / #to)"
        )
    search_only = search_path.read_text()
    search_clean = _without_comments(search_only)
    search_markup = _svelte_markup(search_only)
    surface = search_markup if search_markup.strip() else search_only
    hook = _hook_blob(surface)
    if not hook.strip():
        hook = _hook_blob(search_only)
    near = _date_neighborhood(hook) if hook.strip() else ""
    app_path = crate / "web" / "App.svelte"
    app_only = _read(app_path)
    app_clean = _without_comments(app_only)
    api_path = crate / "web" / "lib" / "api.ts"
    api_txt = _read(api_path)
    prefs_path = crate / "web" / "lib" / "PeoplePrefs.ts"
    prefs = _without_comments(_read(prefs_path))
    pkg = _read(crate / "package.json")
    dtxt = _docs_blob()
    en_path = crate / "web" / "lib" / "locales" / "en.ts"
    tr_path = crate / "web" / "lib" / "locales" / "tr.ts"
    en_txt = _read(en_path)
    tr_txt = _read(tr_path)
    fill = _fill_surface(search_clean)
    fill_entries = _fill_entry_bodies(search_clean)
    run_all, run_before = _search_run_surface(search_clean)
    kinds = _preset_kinds(near, hook, search_clean) if near else set()

    # 1) preset-chrome — primary red today: no 7d / 30d / year / Any chips.
    missing = [k for k in ("7d", "30d", "year", "any") if k not in kinds]
    outside = ""
    q_region = _q_region(surface, hook)
    if q_region and _classify_blob(q_region) & {"7d", "30d", "year"}:
        if not hook or not (_classify_blob(near) & {"7d", "30d", "year"}):
            outside = "q"
    if (
        not hook.strip()
        or not near.strip()
        or missing
        or not _preset_controls_ok(near)
        or _select_is_date_preset(hook)
        or _CALENDAR_WIDGET.search(near)
        or outside == "q"
    ):
        fail(
            f"{_ISSUE}: compact type=\"button\" date presets required inside "
            "data-search-filters next to #from / #to "
            "(7 days / 30 days / this year / Any) — not a <select>, "
            "not a calendar, not siblings of #q"
        )
    if not _preset_compact(near):
        fail(
            f"{_ISSUE}: date presets must be compact "
            "(Button size=\"sm\" / text-xs) next to #from / #to"
        )
    if _SEARCH_Q_ID.search(hook):
        fail(
            f"{_ISSUE}: date presets stay under data-search-filters — "
            "do not hoist them next to #q"
        )

    # 2) preset-clear — Any / Clear writes both from and to to "".
    if not _EMPTY_ASSIGN.search(fill) and not any(
        _EMPTY_ASSIGN.search(b) for b in fill_entries
    ):
        fail(
            f"{_ISSUE}: Any / Clear must set from and to to \"\" "
            "(next run() sends no date filter)"
        )

    # 3) preset-fill-local — host civil date; never UTC slice / formatTime.
    if not (_LOCAL_Y.search(fill) and _LOCAL_D.search(fill)):
        fail(
            f"{_ISSUE}: preset fill must use host-local getFullYear / "
            "getMonth / getDate (or equivalent) — not a UTC calendar day"
        )
    if not _LOCAL_M.search(fill) and not _YEAR_START.search(fill):
        fail(
            f"{_ISSUE}: preset fill must use host-local getMonth "
            "(or write {{year}}-01-01 from getFullYear) — not UTC"
        )
    if _UTC_FILL.search(fill):
        fail(
            f"{_ISSUE}: forbid toISOString / getUTC* / Date.UTC on the "
            "preset fill path (type=date is a host-local YYYY-MM-DD)"
        )
    if _LOCAL_DAY.search(fill) or _FORMAT_TIME_IMPORT.search(search_clean):
        fail(
            f"{_ISSUE}: do not call localDay / formatTime to compute "
            "today (localDay with omitted platform slices UTC)"
        )
    if _T23_ON_ASSIGN.search(fill):
        fail(
            f"{_ISSUE}: #from / #to stay YYYY-MM-DD — do not write "
            "T23:59:59 into the type=date values"
        )

    # 4) preset-7d — today−6 → today. Not 168h. Not today−7.
    if not _DAY_BACK_6.search(fill):
        fail(
            f"{_ISSUE}: 7 days is local today−6 → today (7 inclusive "
            "calendar days) — not now−168h"
        )
    if _ROLLING_7.search(fill):
        fail(
            f"{_ISSUE}: 7 days is not a rolling 168h window "
            "(type=date cannot hold hours)"
        )
    if _DAY_BACK_7.search(fill) and not _DAY_BACK_6.search(fill):
        fail(
            f"{_ISSUE}: 7 days is today−6 → today, not today−7 "
            "(that is 8 calendar days)"
        )

    # 5) preset-30d — today−29 → today. Not 720h.
    if not _DAY_BACK_29.search(fill):
        fail(
            f"{_ISSUE}: 30 days is local today−29 → today — not 720h"
        )
    if _ROLLING_30.search(fill):
        fail(
            f"{_ISSUE}: 30 days is not a rolling 720h window"
        )
    if _DAY_BACK_30.search(fill) and not _DAY_BACK_29.search(fill):
        fail(
            f"{_ISSUE}: 30 days is today−29 → today, not today−30"
        )

    # 6) preset-year — {localYear}-01-01 → today. Not 365d. Not UTC Jan 1.
    if not _YEAR_START.search(fill) or not _LOCAL_Y.search(fill):
        fail(
            f"{_ISSUE}: this year is {{localYear}}-01-01 → local today "
            "(not UTC Jan 1, not last 365 days)"
        )
    if _DAYS_365.search(fill):
        fail(
            f"{_ISSUE}: this year is Jan 1 of the host-local year → today, "
            "not last 365 days"
        )

    # 7) preset-send — date-only to is inclusive on the send string.
    if not run_all or "api.search" not in run_all:
        fail(f"{_ISSUE}: SearchPane run() must remain the api.search caller")
    send = run_all
    if _BARE_TO_SEND.search(send) and not _INCLUSIVE_TO.search(send):
        fail(
            f"{_ISSUE}: date-only to must be sent inclusive of that stored "
            "day (T23:59:59 or equivalent on the send string) — "
            "bare to.trim() || null drops today's hits"
        )
    if not _INCLUSIVE_TO.search(send):
        fail(
            f"{_ISSUE}: date-only to send must include that day "
            "(T23:59:59 or equivalent) — do not invent a UTC instant"
        )
    if _UTC_FILL.search(send):
        fail(
            f"{_ISSUE}: do not convert from/to to UTC instants on the "
            "send path (no toISOString / Date.UTC / getUTC*)"
        )
    if not _FROM_DATE_ONLY.search(send) and re.search(
        r"\bfrom\s*:\s*[^,}]{0,80}T23:59:59", send
    ):
        fail(
            f"{_ISSUE}: from stays a date-only lower bound "
            "(do not send T23:59:59 on from)"
        )
    if not _FROM_DATE_ONLY.search(send) and not _SEARCH_FROM_EMPTY_ANY.search(
        send
    ):
        fail(
            f"{_ISSUE}: empty from still means any "
            "(from.trim() || null — date-only lower bound when set)"
        )
    if not _TO_EMPTY_NULL.search(send) and not re.search(
        r"\bto\s*:\s*[^,}]{0,80}null", send
    ):
        fail(
            f"{_ISSUE}: empty to still means any (null) — "
            "do not send a blank string as a date bound"
        )
    if _INCLUSIVE_TO.search(search_markup) or _INCLUSIVE_TO.search(near):
        fail(
            f"{_ISSUE}: T23:59:59 belongs on the send string only — "
            "#from / #to inputs stay YYYY-MM-DD"
        )

    # 8) preset-invalid — unparseable / from>to still no api.search.
    has_cmp = bool(_SEARCH_DATE_CMP.search(run_before) or _SEARCH_DATE_CMP.search(run_all))
    has_parse = bool(
        _SEARCH_DATE_PARSE.search(run_before) or _SEARCH_DATE_PARSE.search(run_all)
    )
    has_early = bool(re.search(r"\breturn\b", run_before))
    has_err = bool(_SEARCH_DATE_ERROR_SET.search(run_before))
    if not has_parse or not has_cmp or not has_early or not has_err:
        fail(
            f"{_ISSUE}: run() must not call api.search when from/to is "
            "invalid (unparseable or from > to) — keep searchDateInvalid"
        )

    # 9) preset-custom — #from / #to stay type=date and editable.
    if not _date_input_bound(surface, "from") or not _date_input_bound(surface, "to"):
        fail(
            f"{_ISSUE}: keep #from / #to as type=date bound to from / to "
            "(custom dates still work after a preset)"
        )
    if _READONLY_DATE.search(surface):
        fail(
            f"{_ISSUE}: #from / #to stay editable after a preset "
            "(do not lock the date inputs)"
        )
    if re.search(r"""\bid\s*=\s*["']from["']""", app_only) or re.search(
        r"""\bid\s*=\s*["']to["']""", app_only
    ):
        fail(
            f"{_ISSUE}: do not steal id=\"from\" / id=\"to\" off SearchPane "
            "(#311 jump day is not the search date range)"
        )

    # 10) auto-run — fill + run() on click; no from/to $effect.
    click_surf = "\n".join(
        _expand_fn_calls(search_clean, b) for b in fill_entries
    )
    if not _RUN_CALL.search(click_surf) and not _RUN_CALL.search(fill):
        fail(
            f"{_ISSUE}: preset / Any click must fill then run() "
            "(cancelDebounce then run — not fill-only)"
        )
    if not _CANCEL_DEBOUNCE.search(click_surf) and not _CANCEL_DEBOUNCE.search(
        run_all
    ):
        fail(
            f"{_ISSUE}: preset click / run() must cancelDebounce so a "
            "pending #q timer does not fire a second FTS"
        )
    for arg in _svelte_effect_args(search_clean):
        if _reads_from_to(arg) and _effect_searches(arg):
            fail(
                f"{_ISSUE}: do not add a from/to $effect — filters stay "
                "submit-only for manual typing; preset click calls run()"
            )

    # 11) preset-empty-q — empty #q still idles; no second search path.
    if _API_SEARCH_CALL.search(app_clean):
        fail(
            f"{_ISSUE}: App.svelte must not call api.search — SearchPane "
            "run() stays the only search IPC"
        )
    q_effects = [
        a
        for a in _svelte_effect_args(search_clean)
        if re.search(r"\bq\b", a)
        and (
            _RUN_CALL.search(a)
            or _CLEAR_IDLE.search(a)
            or _API_SEARCH_CALL.search(a)
        )
    ]
    if not q_effects or not any(_idle_on_empty_q(a) for a in q_effects):
        fail(
            f"{_ISSUE}: empty #q must still idle (clearHitsIdle / no "
            "useless FTS) — presets do not invent date-only browse"
        )
    preset_runs_empty = False
    for body in fill_entries:
        exp = _expand_fn_calls(search_clean, body)
        if _RUN_CALL.search(exp) and not _idle_on_empty_q(exp):
            # run() itself may idle — count that.
            if not _idle_on_empty_q(run_all):
                preset_runs_empty = True
                break
    if preset_runs_empty:
        fail(
            f"{_ISSUE}: empty #q still idles — preset click must not "
            "api.search a blank query (guard run() or the click)"
        )

    # 12) preset-pressed — derived match, not a sticky toggle.
    pressed = _pressed_surface(surface, search_clean, near)
    has_pressed_attr = bool(_PRESSED_ATTR.search(near))
    has_derived = bool(
        _DERIVED.search(pressed) or _MATCH_HELPER.search(pressed)
    )
    if not has_pressed_attr and not has_derived:
        fail(
            f"{_ISSUE}: preset highlight is derived — a chip is pressed "
            "only while #from / #to equal the window that chip would "
            "write now (aria-pressed / $derived / match helper)"
        )
    if not _reads_from_to(pressed):
        fail(
            f"{_ISSUE}: pressed look must read from / to "
            "(edit a date → highlight drops; not a sticky toggle)"
        )
    if _STICKY_PRESET.search(search_clean) and not _reads_from_to(pressed):
        fail(
            f"{_ISSUE}: do not persist which chip was clicked — "
            "highlight is a derived match of the current from / to"
        )

    # 13) preset-i18n — same new ChromeKeys; tr is not an English copy.
    t_keys = _t_keys(near)
    new_keys = [k for k in t_keys if k not in _EXISTING_DATE_KEYS]
    hardcoded = False
    for tag in _preset_button_blobs(near, hook):
        if _classify_blob(tag) and not _T_CALL.search(tag):
            # each-loop body may t(p.label) — allow if the near region has t().
            if not _T_CALL.search(near):
                hardcoded = True
    if hardcoded or len(new_keys) < 4:
        fail(
            f"{_ISSUE}: 7 days / 30 days / this year / Any must go through "
            "t() (new ChromeKeys in en + tr; not hardcoded English)"
        )
    en_entries = _chrome_pack_entries(en_txt)
    tr_entries = _chrome_pack_entries(tr_txt)
    if not en_entries or not tr_entries:
        fail(f"{_ISSUE}: en + tr chrome packs required (do not drop #131 / #278)")
    missing_en = [k for k in new_keys if k not in en_entries]
    missing_tr = [k for k in new_keys if k not in tr_entries]
    if missing_en or missing_tr:
        bits = []
        if missing_en:
            bits.append("en missing " + ", ".join(missing_en))
        if missing_tr:
            bits.append("tr missing " + ", ".join(missing_tr))
        fail(
            f"{_ISSUE}: same ChromeKeys in en + tr — " + "; ".join(bits)
        )
    copied = [
        k
        for k in new_keys
        if (en_entries.get(k) or "").strip()
        and (tr_entries.get(k) or "").strip() == (en_entries.get(k) or "").strip()
    ]
    if copied:
        fail(
            f"{_ISSUE}: tr must not be an English copy of the new date-preset "
            "keys: " + ", ".join(copied)
        )
    locale_dir = crate / "web" / "lib" / "locales"
    if locale_dir.is_dir():
        third = [
            p.name
            for p in locale_dir.iterdir()
            if p.is_file()
            and p.suffix in {".ts", ".json", ".toml"}
            and p.stem.lower() not in {"en", "tr", "index"}
            and not p.name.endswith(".d.ts")
        ]
        if third:
            fail(
                f"{_ISSUE}: no third locale pack — en + tr only. Found: "
                + ", ".join(third)
            )

    # 14) preset-keep-209 — #q first; filters secondary; two type=date; no picker.
    if not _SEARCH_Q_ID.search(surface):
        fail(f"{_ISSUE}: keep id=\"q\" as the first / primary query control (#209)")
    if _SEARCH_FILTERS_HOOK not in surface and _SEARCH_FILTERS_HOOK not in search_only:
        fail(f"{_ISSUE}: keep data-search-filters (#209)")
    if not _date_input_bound(surface, "from") or not _date_input_bound(surface, "to"):
        fail(f"{_ISSUE}: keep two local type=date inputs (#209)")
    api_m = _SEARCH_API_PLATFORM_ARG.search(search_clean)
    api_args = api_m.group(1) if api_m else search_clean
    if not _SEARCH_FROM_EMPTY_ANY.search(api_args) and not _FROM_DATE_ONLY.search(
        run_all
    ):
        fail(f"{_ISSUE}: empty from still means any (#209)")
    if _SEARCH_CDN.search(search_only) or _SEARCH_DATEPICKER_PKG.search(
        search_only + "\n" + pkg
    ):
        fail(f"{_ISSUE}: no CDN / npm datepicker (#209)")
    if not re.search(
        r"<select\b[^>]{0,400}(?:\bbind:value=\{platform\}|\bid\s*=\s*[\"']plat[\"'])",
        surface,
        re.I,
    ):
        fail(f"{_ISSUE}: keep the search platform closed <select> (#209 / #121)")

    # 15) preset-keep-268 — no sent_at rewrite; no TZ picker; type=date stays.
    if re.search(r"\bsent_at\s*=", search_clean):
        fail(f"{_ISSUE}: do not rewrite stored sent_at (#268)")
    if _TZ_PICKER.search(search_clean) or _TZ_PICKER.search(surface):
        fail(f"{_ISSUE}: no TZ picker (#268)")
    if _TZDATA.search(search_clean) or _TZDATA.search(pkg):
        fail(f"{_ISSUE}: no tzdata / network TZ database (#268)")
    if api_txt and re.search(r"\b(?:sent_at|last_activity_at)\??\s*:\s*Date\b", api_txt):
        fail(f"{_ISSUE}: api.ts sent_at stays an ISO string (#268)")

    # 16) preset-keep-270 — $effect still q-only; type-to-search; submit.
    if not _has_search_as_you_type(search_clean, surface):
        fail(
            f"{_ISSUE}: keep type-to-search (#270) — #q / $effect / "
            "debounce → run() / api.search"
        )
    if not _CLEAR_IDLE.search(search_clean):
        fail(f"{_ISSUE}: keep clearHitsIdle on empty q (#270)")
    if not re.search(
        r"(?:on:submit|onsubmit)\s*=|type\s*=\s*[\"']submit[\"']",
        surface,
        re.I,
    ):
        fail(f"{_ISSUE}: keep form submit → run() (#270)")
    if not _CANCEL_DEBOUNCE.search(run_all):
        fail(f"{_ISSUE}: run() must still cancelDebounce before api.search (#270)")

    # 17) preset-keep-318 — dates stay pane-local; remount may reset.
    web = _web_logic(crate)
    web_clean = _without_comments(web)
    persist_src = "\n".join((app_clean, search_clean, prefs))
    persist_win = "\n".join(
        [
            _windows_around(persist_src, _GETITEM, before=80, after=160),
            _windows_around(persist_src, _SETITEM, before=80, after=160),
            _windows_around(persist_src, _SESSION_STORE, before=80, after=160),
            _windows_around(persist_src, _CONFIG_TOML, before=80, after=160),
        ]
    )
    if _DATE_PERSIST.search(persist_win) and (
        _SETITEM.search(persist_win)
        or _GETITEM.search(persist_win)
        or _SESSION_STORE.search(persist_win)
    ):
        fail(
            f"{_ISSUE}: no date persist (#318) — remount may reset from/to; "
            "do not write interlace.lastSearchFrom / lastSearchTo"
        )
    for key in _ls_pref_keys(web_clean):
        if key not in _ALLOWED_LS and _DATE_LS_KEY.search(key):
            fail(
                f"{_ISSUE}: no new PeoplePrefs / localStorage key for dates "
                f"(found {key!r}; #318 filters still reset on remount)"
            )
    if re.search(
        r"\blet\s+(?:from|to|searchFrom|searchTo)\s*=\s*\$state",
        app_clean,
    ):
        fail(
            f"{_ISSUE}: do not lift from / to onto App (#318 — dates stay "
            "pane-local and may reset on remount)"
        )
    if _ICLOUD.search(persist_win) and _DATE_PERSIST.search(persist_win):
        fail(f"{_ISSUE}: do not invent an iCloud key for search dates")

    # 18) preset-d24 — fill in Mac TZ; empty / Any = any; storage UTC.
    if not dtxt.strip():
        fail(
            f"{_ISSUE}: docs/user/app.md and/or search.md required — "
            "presets fill the date filters in the Mac timezone"
        )
    if not _DOCS_PRESETS.search(dtxt) or not _DOCS_FILL.search(dtxt):
        fail(
            f"{_ISSUE}: docs must say compact 7d / 30d / this year presets "
            "fill the date filters"
        )
    if not _DOCS_MAC_TZ.search(dtxt):
        fail(
            f"{_ISSUE}: docs must say presets fill the date filters in the "
            "Mac / host timezone"
        )
    if not _DOCS_EMPTY_ANY.search(dtxt):
        fail(f"{_ISSUE}: docs must say empty / Any = any (no date filter)")
    if not _DOCS_UTC.search(dtxt):
        fail(
            f"{_ISSUE}: docs must say storage / JSON / FTS stay UTC"
        )
    if not _DOCS_NOT_CALENDAR.search(dtxt):
        fail(f"{_ISSUE}: docs must say this is not a calendar")
    if _claim_without_negation(dtxt, _DAYS_ARE_UTC):
        fail(f"{_ISSUE}: do not say the preset days are UTC")
    if _claim_without_negation(dtxt, _DATES_SURVIVE):
        fail(
            f"{_ISSUE}: do not say reopen / remount restores dates "
            "(#318 — filters still reset)"
        )
    if _claim_without_negation(dtxt, _SPOTLIGHT):
        fail(f"{_ISSUE}: not in scope — not Spotlight")
    if _claim_without_negation(dtxt, _MULTI_TAB):
        fail(f"{_ISSUE}: not in scope — not multi-tab search history")
    if _claim_without_negation(dtxt, _CALENDAR_WORD) and not _DOCS_NOT_CALENDAR.search(
        dtxt
    ):
        fail(f"{_ISSUE}: not a calendar product")

    # 19) preset-share-window — fill + highlight share datePresetWindow.
    apply_body = _named_body(search_clean, "applyDatePreset")
    pressed_body = _named_body(search_clean, "isPresetPressed")
    if not _DATE_PRESET_WINDOW_KIND.search(pressed_body):
        fail(
            f"{_ISSUE}: isPresetPressed must keep using datePresetWindow(kind) "
            "(fill and highlight share one window)"
        )
    if not apply_body or not _DATE_PRESET_WINDOW_KIND.search(apply_body):
        fail(
            f"{_ISSUE}: applyDatePreset must call datePresetWindow(kind) "
            "and assign from / to from that window — do not rebuild "
            "7d / 30d / year with new Date(y, m, day - N)"
        )
    if not _apply_assigns_window(apply_body):
        fail(
            f"{_ISSUE}: applyDatePreset must assign from / to from "
            "datePresetWindow(kind) (Any already returns \"\" / \"\")"
        )
    if _NEW_DATE_YMD_MINUS.search(apply_body):
        fail(
            f"{_ISSUE}: applyDatePreset must not rebuild 7d / 30d / year "
            "with new Date(y, m, day - N) — one window helper only"
        )
