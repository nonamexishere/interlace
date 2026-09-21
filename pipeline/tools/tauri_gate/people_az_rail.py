"""#376 — A–Z letter headings + present-letters jump rail (confirmed mix).

Wired immediately after assert_review_keys (#375).

Confirmed mix (2026-09-22): first surviving token after name_fold İ→i,
I→ı, strip Cf, lowercase, honorific / 1-char drop; **no token sort**.
i/ı share heading I. Empty remaining tokens → `#` (heading + rail `#`
only when present). A lone letter is that letter (X → X). Leading
punctuation after strip Cf (`=?utf-8` pattern / `(` / `=` / `?`) is `#`
— do not skip punct and take the letter after. TS helper (azLetter.ts
or equivalent) used by the sidebar only — no extra IPC, no Person JSON
field, not inside the PeopleShell `filtered` window (#312). Headings +
rail on the A–Z **unpinned rest** only (Pinned stays #368). Sticky
**new** `.letter-heading` class (copy `.day-heading` tokens; do not
reuse that class). Rail = letters that exist in the filtered rest
(digits, Turkish A–Z, `#` last). Hide on Recent and collapsed (`⌘\\`).
Click scrolls the sidebar scroller; does **not** `selectPerson`. `/`
filter reduces headings/rail. localeCompare A–Z unchanged. No new sort
keys. No section collapse. No A–Z keydown.

Not name_fold_join first char. Not full A–Z rail. Not first-visible-char
(Dr Ada → D). Not selectPerson on click.

Hooks: `data-letter-heading` / `data-letter-rail` — not `data-az-rail` /
`az-jump-rail` / `#376` in sidebar or shell (#368 `_AZ_RAIL`).

Placeholders Ada / Berk / Self. Same ChromeKey on en.ts + tr.ts if a
new string appears.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.last_read import _text, _web_file
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.people_filter import _people_filter_window
from tauri_gate.people_sort_fold import (
    _DISPLAY_CMP,
    _LOCALE_COMPARE,
    _NAME_FOLD,
    _SENSITIVITY_BASE,
    _UNDEFINED_LOCALE,
)
from tauri_gate.scan import (
    _expand_fn_calls,
    _function_body,
    _match_closer,
    _svelte_markup,
    _tauri_rust_blob,
    _ts_fn_body,
    _without_comments,
)
from tauri_gate.status_toasts_chrome import _PEOPLE_EACH, _windows_around

_ISSUE = "#376"
_PRIMARY = (
    f"{_ISSUE}: PeopleSidebar must paint sticky letter headings "
    "(data-letter-heading) on the A–Z unpinned rest"
)

_HEADING_HOOK = re.compile(r"\bdata-letter-heading\b")
_RAIL_HOOK = re.compile(r"\bdata-letter-rail\b")
_LETTER_ATTR = re.compile(r"\bdata-letter\b")
_FORBIDDEN_HOOK = re.compile(r"data-az-rail|az-jump-rail|#376")
_LETTER_CLASS = re.compile(r"\bletter-heading\b")
_DAY_HEADING = re.compile(r"\bday-heading\b")
_AZ_ON = re.compile(
    r"""peopleSort\s*===?\s*["']az["']|["']az["']\s*===?\s*peopleSort"""
)
_RECENT_ON = re.compile(
    r"""peopleSort\s*===?\s*["']recent["']|["']recent["']\s*===?\s*peopleSort"""
)
_NOT_COLLAPSED = re.compile(r"!\s*sidebarCollapsed")
_COLLAPSED_TRUE = re.compile(r"\bsidebarCollapsed\b")
_PIN_SET = re.compile(r"\b(?:pinSet|pinnedMatching|pinIds)\b")
_REST_SLICE = re.compile(
    r"""
    !\s*(?:pinSet|pinnedSet)\s*\.\s*has
    |\.filter\s*\([^)]*(?:pinSet|pinned|isPinned)
    |\b(?:unpinned|azRest|restRows|letterRest)\b
    """,
    re.X,
)
_PRESENT_LETTERS = re.compile(
    r"\b(?:presentLetters|railLetters|letterKeys|azLetters|restLetters)\b"
)
_FULL_AZ = re.compile(r"""["']ABCDEFGHIJKLMNOPQRSTUVWXYZ["']""")
_SCROLL = re.compile(r"\bscrollIntoView\b|\.scrollTop\s*=")
_SMOOTH = re.compile(r"""behavior\s*:\s*["']smooth["']""")
_BOUNCE = re.compile(r"\b(?:bounce|spring|elastic)\b", re.I)
_SELECT = re.compile(r"\b(?:onSelectPerson|selectPerson|loadPerson)\b")
_THROW = re.compile(r"\bthrow\s+|showErr\s*\(")
_TABINDEX_NEG = re.compile(r"""tabindex\s*=\s*["']-1["']""")
_ROLE_OPTION = re.compile(r"""role\s*=\s*["']option["']""")
_ROLE_PRESENTATION = re.compile(r"""role\s*=\s*["']presentation["']""")
_H3 = re.compile(r"<h3\b")
_FILTERED_EACH_KEYED = re.compile(
    r"\{#each\s+filtered\s+as\s+(\w+)(?:\s*,\s*\w+)?\s*\(\s*"
    r"(?:String\s*\(\s*)?\1\s*\.\s*id\b"
)
_PINNED_T = re.compile(r"""t\(\s*["']pinned["']\s*\)""")
_PERSON_FILTER = re.compile(r"""id\s*=\s*["']person-filter["']""")
_W72 = re.compile(r"\bw-72\b")
_W12 = re.compile(r"\bw-12\b")
_SIDEBAR_TOGGLE = re.compile(r"\bdata-sidebar-toggle\b")
_MOD_BACKSLASH = re.compile(
    r"""(?:metaKey|ctrlKey)[\s\S]{0,200}(?:Backslash|IntlBackslash|\\\\)"""
)
_IDENTITY_HAY = re.compile(r"\bidentity_values\b")
_DISPLAY_NAME = re.compile(r"\bdisplay_name\b")
_FILTERED_IDS = re.compile(r"filteredIds[\s\S]{0,200}filtered\s*\.\s*map")
_I_DOTTED = re.compile(r"""\.replace\s*\(\s*["']İ["']\s*,\s*["']i["']\s*\)""")
_I_DOTLESS = re.compile(r"""\.replace\s*\(\s*["']I["']\s*,\s*["']ı["']\s*\)""")
_TR_LOCALE_LOWER = re.compile(
    r"""toLocaleLowerCase\s*\(\s*["']tr["']\s*\)"""
)
_TOKEN_SORT = re.compile(
    r"""
    (?:tokens|parts|words)\s*\.\s*sort\s*\(
    |\.sort\s*\(\s*\)\s*;?\s*(?:return|join)
    """,
    re.X,
)
_NAME_FOLD_JOIN_FIRST = re.compile(
    r"name_fold_join|foldJoin|fold_join"
)
_EMPTY_HASH = re.compile(r"""["']#["']""")
_I_BUCKET = re.compile(
    r"""
    (?:===?\s*["'](?:i|ı)["']|["'](?:i|ı)["']\s*===?)
    |["']ı["']\s*,\s*["']i["']
    |toUpperCase\s*\(
    """,
    re.X,
)
_HONORIFIC_DR = re.compile(r"""["']dr["']""")
_ONE_CHAR_DROP = re.compile(
    r"""
    (?:length|chars)\s*(?:<=|<)\s*1
    |\.length\s*<\s*2
    """,
    re.X,
)
_SPLIT_WS = re.compile(
    r"""\bsplit\s*\(\s*(?:/\\s\+|['"]\s+['"])"""
)
_STRIP_CF = re.compile(
    r"stripCf|strip_cf|200b|200e|200f|feff|2060|\\u200b|\\u200e|\\ufeff",
    re.I,
)
_HELPER_NAME_FOLD = re.compile(r"\bname_fold(?:_join)?\b")
_FIRST_CHAR_ONLY = re.compile(
    r"""display_name\s*(?:\[[^\]]+\]|\.charAt\s*\(\s*0\s*\)|\.\[0\])"""
)
_PERSON_FOLD_FIELD = re.compile(
    r"\b(?:name_fold|az_letter|letter_fold)\s*\??\s*:"
)
_INVOKE_FOLD = re.compile(
    r"""invoke\s*\(\s*["']name_fold(?:_join)?["']"""
    r"""|fn\s+name_fold(?:_join)?\s*\("""
)
_PEOPLE_SORT_ARG = re.compile(
    r"fn\s+people\s*\([^)]*\b(?:sort|people_sort|az|fold)\b"
)
_NEXT_PRESENT = re.compile(
    r"""
    >=\s*(?:letter|L|ch|key)
    |\bnext(?:Present|Letter)
    |findIndex
    |\.find\s*\(
    """,
    re.X,
)
_T_CALL = re.compile(r"""\bt\s*\(\s*["']([A-Za-z_][A-Za-z0-9_]*)["']\s*\)""")
_PLACEHOLDER_CHROME = re.compile(r"\bAda\b|\bBerk\b|\bSelf\b")
_HTTP = re.compile(r"https?://", re.I)
_SECTION_COLLAPSE = re.compile(
    r"collapsedLetters|letterCollapsed|toggleLetterSection|hideRows"
)
_LETTER_KEYDOWN = re.compile(
    r"""
    e\.key\s*===?\s*["'][A-Za-z]["']
    |key\.length\s*===?\s*1
    |jumpLetter\s*\(\s*e\.key
    """,
    re.X,
)
_VIEW_PEOPLE_RETURN = re.compile(
    r"""ctx\.view\s*!==?\s*["']people["']\s*\)\s*return"""
)
_SLASH_FILTER = re.compile(
    r"""e\.key\s*===?\s*["']/["'][\s\S]{0,200}person-filter"""
)
_VISIBLE_TL = re.compile(r"\bvisibleTlIndices\b")
_INSPECTOR = re.compile(r"\bdata-person-inspector\b")
_REVIEW_KEYDOWN = re.compile(
    r"addEventListener\s*\(\s*[\"']keydown[\"']"
)
_LISTBOX = re.compile(r"""role\s*=\s*["']listbox["']""")
_DOCS_HEADINGS = re.compile(
    r"("
    r"letter heading"
    r"|A\s*[–-]\s*Z.{0,120}heading"
    r"|heading.{0,80}letter"
    r")",
    re.I | re.S,
)
_DOCS_RAIL = re.compile(
    r"("
    r"(?:letter|jump)\s+rail"
    r"|rail.{0,80}(?:letter|A\s*[–-]\s*Z)"
    r")",
    re.I | re.S,
)
_DOCS_RECENT_NONE = re.compile(
    r"("
    r"Recent.{0,120}(?:no|neither|without).{0,80}(?:rail|heading)"
    r"|(?:rail|heading).{0,80}Recent.{0,80}(?:no|none|hidden)"
    r")",
    re.I | re.S,
)
_DOCS_FILTER = re.compile(
    r"("
    r"(?:/|filter).{0,160}(?:rail|heading).{0,80}(?:filter|reduced|follow)"
    r"|(?:rail|heading).{0,160}(?:filter|reduced)"
    r")",
    re.I | re.S,
)
_HELPER_CANDIDATES = (
    "azLetter.ts",
    "AzLetter.ts",
    "letterFold.ts",
    "PeopleLetter.ts",
    "peopleLetter.ts",
    "az_letter.ts",
    "displayLetter.ts",
)
_HELPER_IMPORT = re.compile(
    r"""from\s+["']\./(azLetter|AzLetter|letterFold|PeopleLetter|"""
    r"""peopleLetter|az_letter|displayLetter)["']"""
)
_JUMP_FN = re.compile(
    r"\b(?:jumpLetter|jumpToLetter|scrollToLetter|onLetterClick|"
    r"azJump|letterJump)\b"
)


def _css_class_body(css: str, name: str) -> str:
    m = re.search(rf"\.{re.escape(name)}\s*\{{", css)
    if not m:
        return ""
    start = css.find("{", m.start())
    if start < 0:
        return ""
    end = _match_closer(css, start)
    return css[start + 1 : end] if end > start else ""


def _letter_helper_path(crate: Path, sidebar_raw: str) -> Path | None:
    lib = crate / "web" / "lib"
    seen: list[Path] = []
    for m in _HELPER_IMPORT.finditer(sidebar_raw):
        p = lib / f"{m.group(1)}.ts"
        if p.is_file():
            seen.append(p)
    for name in _HELPER_CANDIDATES:
        p = lib / name
        if p.is_file():
            seen.append(p)
    if lib.is_dir():
        for p in sorted(lib.glob("*.ts")):
            if p.name in {
                "api.ts",
                "i18n.ts",
                "PeoplePrefs.ts",
                "PeopleKeys.ts",
                "PeopleBoot.ts",
                "PeopleUndo.ts",
                "PeopleSearch.ts",
                "PeopleFriendly.ts",
            }:
                continue
            txt = _text(p)
            if _I_DOTTED.search(txt) and _I_DOTLESS.search(txt):
                seen.append(p)
    uniq: list[Path] = []
    for p in seen:
        if p not in uniq:
            uniq.append(p)
    return uniq[0] if uniq else None


def _fn(src: str, name: str) -> str:
    return _ts_fn_body(src, name) or _function_body(src, name) or ""


def _rail_window(sidebar: str) -> str:
    return _windows_around(sidebar, _RAIL_HOOK, 400, 900)


def _heading_window(sidebar: str) -> str:
    return _windows_around(sidebar, _HEADING_HOOK, 400, 900)


def _jump_blob(sidebar: str) -> str:
    parts = [_rail_window(sidebar), _heading_window(sidebar)]
    for m in _JUMP_FN.finditer(sidebar):
        parts.append(_fn(sidebar, m.group(0)))
    rail = _rail_window(sidebar)
    if rail:
        parts.append(_expand_fn_calls(sidebar, rail, depth=2))
    return "\n".join(parts)


def assert_az_letter_rail(crate: Path) -> None:
    """#376: A–Z rest letter headings + present-letters rail; scroll not select."""
    root = repo_root()
    side_path = _web_file(crate, "PeopleSidebar.svelte")
    shell_path = _web_file(crate, "PeopleShell.svelte")
    prefs_path = _web_file(crate, "PeoplePrefs.ts")
    keys_path = _web_file(crate, "PeopleKeys.ts")
    api_path = _web_file(crate, "api.ts")
    insp_path = _web_file(crate, "PeopleInspector.svelte")
    review_path = _web_file(crate, "ReviewPane.svelte")
    search_path = _web_file(crate, "SearchHits.svelte")
    pal_path = _web_file(crate, "CommandPalette.svelte")
    merge_path = _web_file(crate, "MergeDialog.svelte")
    css_path = crate / "web" / "app.css"
    en_path = crate / "web" / "lib" / "locales" / "en.ts"
    tr_path = crate / "web" / "lib" / "locales" / "tr.ts"
    docs_path = root / "docs" / "user" / "app.md"
    people_rs = root / "crates" / "interlace-core" / "src" / "people.rs"
    rust_main = crate / "src" / "main.rs"
    ipc_path = crate / "src" / "ipc.rs"

    if not side_path.is_file():
        fail(f"{_ISSUE}: PeopleSidebar.svelte required (A–Z letter headings + rail)")

    sidebar_raw = _text(side_path)
    sidebar = _without_comments(sidebar_raw)
    markup = _svelte_markup(sidebar_raw)
    shell_raw = _text(shell_path)
    shell = _without_comments(shell_raw)
    prefs = _without_comments(_text(prefs_path))
    keys_raw = _text(keys_path)
    keys = _without_comments(keys_raw)
    api = _without_comments(_text(api_path))
    insp = _text(insp_path)
    review = _without_comments(_text(review_path))
    search = _text(search_path)
    pal = _text(pal_path)
    merge = _text(merge_path)
    css = _text(css_path)
    docs = _text(docs_path)
    people_core = _text(people_rs)
    rust = _text(rust_main) + "\n" + _text(ipc_path) + "\n" + _tauri_rust_blob(crate)

    helper_path = _letter_helper_path(crate, sidebar_raw)
    helper_raw = _text(helper_path) if helper_path else ""
    helper = _without_comments(helper_raw)
    letter_src = helper + "\n" + sidebar
    jump = _jump_blob(sidebar)
    head_win = _heading_window(sidebar)
    rail_win = _rail_window(sidebar)
    filt = _people_filter_window(shell)

    # 1) Primary red today — sticky letter headings on the A–Z rest.
    if not _HEADING_HOOK.search(sidebar) and not _HEADING_HOOK.search(markup):
        fail(_PRIMARY)
    if not _H3.search(head_win) and not _H3.search(markup):
        fail(
            f"{_ISSUE}: letter headings are group h3s (data-letter-heading), "
            "not a fake overlay"
        )
    if not _LETTER_CLASS.search(sidebar) and not _LETTER_CLASS.search(css):
        fail(
            f"{_ISSUE}: sticky headings use a new .letter-heading class "
            "(do not reuse .day-heading)"
        )
    if _DAY_HEADING.search(markup):
        fail(
            f"{_ISSUE}: do not reuse .day-heading on the people list "
            "(timeline / #311 keeps that class)"
        )

    # 2) Quiet present-letters rail (not data-az-rail — #368 keep).
    if _FORBIDDEN_HOOK.search(sidebar) or _FORBIDDEN_HOOK.search(shell):
        fail(
            f"{_ISSUE}: do not use data-az-rail / az-jump-rail / #376 in "
            "sidebar or shell (#368 keep); use data-letter-heading / "
            "data-letter-rail"
        )
    if not _RAIL_HOOK.search(sidebar) and not _RAIL_HOOK.search(markup):
        fail(
            f"{_ISSUE}: A–Z expanded sidebar needs a quiet right-edge rail "
            "(data-letter-rail)"
        )
    if not _LETTER_ATTR.search(rail_win) and not _LETTER_ATTR.search(head_win):
        fail(
            f"{_ISSUE}: rail / headings need data-letter so click M can find "
            "the first rest M"
        )
    if not _TABINDEX_NEG.search(rail_win):
        fail(
            f"{_ISSUE}: rail controls are tabindex=\"-1\" "
            "(do not steal listbox arrows / / / j/k)"
        )
    if _FULL_AZ.search(rail_win) and not _PRESENT_LETTERS.search(sidebar):
        fail(
            f"{_ISSUE}: rail letters are only those present in the unpinned "
            "filtered rest (not a hard-coded A–Z of 26)"
        )
    if not re.search(r"\.sort\s*\(\s*compareAzLetters", sidebar) and not re.search(
        r"compareAzLetters|letterRank", helper
    ):
        fail(
            f"{_ISSUE}: rail order is digits, then A–Z (ÇÖŞÜ), then # last "
            "(not list-appearance order — U must not float to the top; "
            "# must not sit between W and X)"
        )

    # 3) A–Z + expanded only; Recent none; collapsed none.
    chrome_pred = head_win + "\n" + rail_win + "\n" + sidebar
    if not _AZ_ON.search(chrome_pred):
        fail(
            f"{_ISSUE}: letter headings + rail paint only when "
            "peopleSort === \"az\""
        )
    if not _NOT_COLLAPSED.search(chrome_pred):
        fail(
            f"{_ISSUE}: hide letter headings and the rail when the sidebar "
            "is collapsed (⌘\\\\ / w-12 avatar rail)"
        )
    if _RECENT_ON.search(head_win) and "az" not in head_win:
        fail(f"{_ISSUE}: Recent sort paints no letter headings")

    # 4) Rest-only — Pinned stays #368 t("pinned") above; Ada pinned is not under A.
    if not _PINNED_T.search(sidebar):
        fail(f"{_ISSUE}: keep t(\"pinned\") above the listbox (#368)")
    if not _PIN_SET.search(sidebar) and not _PIN_SET.search(shell):
        fail(f"{_ISSUE}: letter headings/rail must see pinSet / pinIds (rest only)")
    if not _REST_SLICE.search(sidebar) and not _REST_SLICE.search(shell):
        fail(
            f"{_ISSUE}: headings and rail walk the A–Z unpinned rest "
            "(Pinned stays a block; click S lands the first rest S)"
        )

    # 5) Click M scrolls first rest M else next present else no-op; no select.
    if not _JUMP_FN.search(sidebar) and not _SCROLL.search(jump):
        fail(
            f"{_ISSUE}: click M must scroll the first rest M (or heading) "
            "into the sidebar scroller"
        )
    if not _SCROLL.search(jump) and not _SCROLL.search(sidebar):
        fail(
            f"{_ISSUE}: rail click jump-scrolls in the sidebar scroller "
            "(scrollIntoView / scrollTop)"
        )
    if _SMOOTH.search(jump) or _SMOOTH.search(sidebar):
        fail(
            f"{_ISSUE}: scroll is not behavior: \"smooth\" "
            "(reduced motion: instant, no bounce)"
        )
    if _SELECT.search(jump):
        fail(
            f"{_ISSUE}: rail click does not call onSelectPerson / "
            "selectPerson / loadPerson (scroll only)"
        )
    if not _NEXT_PRESENT.search(jump) and not _NEXT_PRESENT.search(sidebar):
        fail(
            f"{_ISSUE}: click M lands the first M else the next present "
            "letter else no-op"
        )
    if _THROW.search(jump):
        fail(
            f"{_ISSUE}: empty letter is a no-op — do not throw / showErr"
        )
    if _BOUNCE.search(sidebar) or _BOUNCE.search(css):
        fail(f"{_ISSUE}: no bounce / spring on the letter rail")

    # 6) Presentation headings inside the listbox, not option rows.
    if _ROLE_OPTION.search(head_win):
        fail(
            f"{_ISSUE}: letter heading li is role=\"presentation\", not option "
            "(#133 ArrowUp/Down)"
        )
    if not _ROLE_PRESENTATION.search(head_win) and not _ROLE_PRESENTATION.search(
        markup
    ):
        fail(
            f"{_ISSUE}: letter headings sit in role=\"presentation\" items "
            "(listbox options stay people rows)"
        )
    if not _LISTBOX.search(markup):
        fail(f"{_ISSUE}: keep the people listbox")
    if not _FILTERED_EACH_KEYED.search(sidebar):
        fail(
            f"{_ISSUE}: keep {{#each filtered as p (p.id)}} (#368-key / #138)"
        )
    if not _PEOPLE_EACH.search(sidebar):
        fail(f"{_ISSUE}: keep {{#each filtered}}")
    if _SECTION_COLLAPSE.search(sidebar):
        fail(f"{_ISSUE}: no section collapse on letter headings")

    # 7) Sticky new class (copy .day-heading tokens; not that class).
    letter_css = _css_class_body(css, "letter-heading")
    if not letter_css.strip():
        fail(
            f"{_ISSUE}: app.css needs .letter-heading "
            "(position: sticky; top: 0; background token)"
        )
    if not re.search(r"position\s*:\s*sticky", letter_css, re.I):
        fail(f"{_ISSUE}: .letter-heading is position: sticky (timeline analog)")
    if not re.search(r"\btop\s*:\s*0\b", letter_css, re.I):
        fail(f"{_ISSUE}: .letter-heading sticks at top: 0")
    if "background" not in letter_css:
        fail(
            f"{_ISSUE}: .letter-heading needs a background token "
            "(copy .day-heading; do not reuse that class)"
        )

    # 8) TS helper — first surviving token; İ/I; i/ı → I; empty → #.
    if helper_path is None or not helper.strip():
        fail(
            f"{_ISSUE}: TS letter helper (azLetter.ts or equivalent) required "
            "— sidebar only, not IPC, not a Person field"
        )
    if helper_path and helper_path.name.lower().startswith("name_fold"):
        fail(
            f"{_ISSUE}: helper is not named name_fold "
            "(identity keying stays in fold.rs)"
        )
    if not _I_DOTTED.search(letter_src):
        fail(
            f"{_ISSUE}: letter path maps İ→i (name_fold, not ASCII toLowerCase) "
            "— placeholder İada → heading I"
        )
    if not _I_DOTLESS.search(letter_src):
        fail(
            f"{_ISSUE}: letter path maps I→ı before lowercase "
            "(Iada → heading I via ı, not a stray i bucket)"
        )
    if _TR_LOCALE_LOWER.search(letter_src) and (
        _I_DOTTED.search(letter_src) or _I_DOTLESS.search(letter_src)
    ):
        fail(
            f"{_ISSUE}: do not use toLocaleLowerCase('tr') and the İ/I replace "
            "(double map)"
        )
    i_pos = letter_src.find(".replace")
    low = re.search(r"toLowerCase\s*\(", letter_src)
    if low and i_pos >= 0 and low.start() < i_pos:
        fail(
            f"{_ISSUE}: İ→i and I→ı run before toLowerCase "
            "(ASCII I.toLowerCase is i, not ı)"
        )
    if _TOKEN_SORT.search(helper) or _TOKEN_SORT.search(letter_src):
        fail(
            f"{_ISSUE}: no token sort — Berk Ada → B (not name_fold_join A)"
        )
    if _NAME_FOLD_JOIN_FIRST.search(helper):
        fail(
            f"{_ISSUE}: letter is the first surviving token, not "
            "name_fold_join first char"
        )
    if not _EMPTY_HASH.search(helper) and not _EMPTY_HASH.search(letter_src):
        fail(
            f"{_ISSUE}: no remaining letter → # bucket "
            "(punctuation-only / empty; row still listed)"
        )
    if not re.search(r"\bshort\b", helper) and not re.search(
        r"long\[0\]\s*\?\?\s*short\[0\]", helper
    ):
        fail(
            f"{_ISSUE}: a lone letter (display name \"X\") is heading X, "
            "not # — 1-char tokens skip only as prefixes (Dr Ada → A)"
        )
    az_fn = _fn(helper, "azLetter") or helper
    split_m = re.search(r"\bsplit\s*\(", az_fn)
    before_split = az_fn[: split_m.start()] if split_m else az_fn
    if not (
        re.search(r"""["']#["']""", before_split)
        and re.search(
            r"isAsciiPunct|isPunct|punctuation|\\\\p\{P\}|startsWithPunct",
            before_split,
            re.I,
        )
    ):
        fail(
            f"{_ISSUE}: if the stripped name starts with punctuation "
            "(=?utf-8 pattern / ( / = / ?), letter is # before token trim — "
            "do not skip leading punct and take the letter after"
        )
    if not _I_BUCKET.search(letter_src):
        fail(f"{_ISSUE}: i and ı share heading I (A–Z 26, not a 29-letter rail)")
    if not _HONORIFIC_DR.search(letter_src):
        fail(
            f"{_ISSUE}: honorific drop (dr / mr / …) so Dr Ada → A "
            "(not first-visible-char D)"
        )
    if not _ONE_CHAR_DROP.search(letter_src):
        fail(
            f"{_ISSUE}: 1-char tokens skip as prefixes (Dr Ada → A); "
            "a lone letter is that letter, not #"
        )
    if not _SPLIT_WS.search(letter_src) and "split(" not in letter_src:
        fail(
            f"{_ISSUE}: letter is the first remaining token after split "
            "(Berk Ada → B)"
        )
    if not _STRIP_CF.search(letter_src):
        fail(f"{_ISSUE}: letter path strips Cf (same strip as name_fold)")
    if _HELPER_NAME_FOLD.search(helper):
        fail(
            f"{_ISSUE}: helper must not be named name_fold / name_fold_join "
            "(#312 filtered window)"
        )
    if _FIRST_CHAR_ONLY.search(helper) and not _HONORIFIC_DR.search(helper):
        fail(
            f"{_ISSUE}: not first-visible-char (Dr Ada → D); first surviving "
            "token after honorific / 1-char drop"
        )
    if helper_path and _HTTP.search(helper):
        fail(f"{_ISSUE}: letter helper is local — no http(s)")

    # 9) fold-site — not in filtered, not IPC, not Person JSON.
    if _NAME_FOLD.search(filt) or _HELPER_NAME_FOLD.search(filt):
        fail(
            f"{_ISSUE}: do not call name_fold / the letter helper inside the "
            "PeopleShell filtered window (#312)"
        )
    if not (
        _LOCALE_COMPARE.search(filt)
        and _UNDEFINED_LOCALE.search(filt)
        and _SENSITIVITY_BASE.search(filt)
        and _DISPLAY_CMP.search(filt)
    ):
        fail(
            f"{_ISSUE}: A–Z sort stays display_name.localeCompare(undefined, "
            '{{ sensitivity: "base" }}) (#312)'
        )
    if _PERSON_FOLD_FIELD.search(api) or _PERSON_FOLD_FIELD.search(people_core):
        fail(
            f"{_ISSUE}: no name_fold / az_letter field on Person / "
            "PersonSummary (TS helper only)"
        )
    if _INVOKE_FOLD.search(rust) or _INVOKE_FOLD.search(shell) or _INVOKE_FOLD.search(
        sidebar
    ):
        fail(f"{_ISSUE}: no name_fold IPC / invoke (pure TS helper)")
    if _PEOPLE_SORT_ARG.search(rust):
        fail(f"{_ISSUE}: people() still has no sort / fold argument (#312 / #265)")

    # 10) / filter reduces rail from the filtered rest.
    if not _PERSON_FILTER.search(sidebar):
        fail(f"{_ISSUE}: keep #person-filter (#138)")
    if not _IDENTITY_HAY.search(filt) and not _IDENTITY_HAY.search(shell):
        fail(f"{_ISSUE}: keep #138 identity_values haystack")
    if not _DISPLAY_NAME.search(filt):
        fail(f"{_ISSUE}: keep #138 display_name in the filter haystack")
    letter_from = sidebar + "\n" + helper
    if "filtered" not in letter_from and "filtered" not in rail_win:
        fail(
            f"{_ISSUE}: headings/rail follow the filtered rest "
            "(filter \"ada\" drops Berk / B)"
        )

    # 11) Keep collapse / pins / review / inspector / keys.
    if not _W72.search(sidebar):
        fail(f"{_ISSUE}: keep expanded w-72 (#212)")
    if not _W12.search(sidebar):
        fail(f"{_ISSUE}: keep collapsed w-12 avatar rail (#212)")
    if not _SIDEBAR_TOGGLE.search(sidebar):
        fail(f"{_ISSUE}: keep data-sidebar-toggle (#212)")
    if not _COLLAPSED_TRUE.search(sidebar):
        fail(f"{_ISSUE}: keep sidebarCollapsed (#212)")
    if keys and not _MOD_BACKSLASH.search(keys) and "Backslash" not in keys:
        fail(f"{_ISSUE}: keep ⌘\\\\ collapse (#212)")
    if not _FILTERED_IDS.search(shell) and not _FILTERED_IDS.search(keys):
        fail(
            f"{_ISSUE}: filteredIds() stays filtered.map "
            "(ArrowUp/Down is pinned-then-rest)"
        )
    if "interlace.peopleSort" not in prefs and "PEOPLE_SORT_PREF" not in prefs:
        fail(f"{_ISSUE}: keep interlace.peopleSort (#312)")
    if 'PeopleSort = "recent" | "az"' not in prefs and (
        '"recent"' not in prefs or '"az"' not in prefs
    ):
        fail(f"{_ISSUE}: peopleSort stays recent | az (no new sort keys)")
    if keys and not _VIEW_PEOPLE_RETURN.search(keys):
        fail(
            f"{_ISSUE}: keep if (ctx.view !== \"people\") return "
            "(Review #375 letters stay pane-local)"
        )
    if keys and not _SLASH_FILTER.search(keys):
        fail(f"{_ISSUE}: keep / → #person-filter")
    if keys and not _VISIBLE_TL.search(keys):
        fail(f"{_ISSUE}: keep People j/k on visibleTlIndices (not a letter map)")
    if keys and _LETTER_KEYDOWN.search(keys) and _JUMP_FN.search(keys):
        fail(
            f"{_ISSUE}: no A–Z keydown jump map (would steal / and timeline j/k)"
        )
    if review_path.is_file() and not _REVIEW_KEYDOWN.search(review):
        fail(f"{_ISSUE}: keep ReviewPane window keydown (#375)")
    if insp_path.is_file() and not _INSPECTOR.search(insp):
        fail(f"{_ISSUE}: keep data-person-inspector (#213)")
    for blob, where in (
        (search, "Search hits"),
        (pal, "⌘K palette"),
        (merge, "Merge picker"),
    ):
        if _RAIL_HOOK.search(blob) or _HEADING_HOOK.search(blob):
            fail(f"{_ISSUE}: {where} has no people letter rail")

    # 12) Locales — same ChromeKey if a new string; tr is not an English copy.
    en = _chrome_pack_entries(_text(en_path)) if en_path.is_file() else {}
    tr = _chrome_pack_entries(_text(tr_path)) if tr_path.is_file() else {}
    used = set(_T_CALL.findall(sidebar_raw)) | set(_T_CALL.findall(helper_raw))
    missing_en = sorted(k for k in used if k not in en)
    missing_tr = sorted(k for k in used if k not in tr)
    if missing_en or missing_tr:
        bits = []
        if missing_en:
            bits.append("missing en: " + ", ".join(missing_en))
        if missing_tr:
            bits.append("missing tr: " + ", ".join(missing_tr))
        fail(
            f"{_ISSUE}: same ChromeKey on en.ts + tr.ts if new strings — "
            + "; ".join(bits)
        )
    for key in used:
        ev, tv = (en.get(key) or "").strip(), (tr.get(key) or "").strip()
        if ev and tv and ev == tv and len(ev) > 12 and key not in {"pinned"}:
            fail(f"{_ISSUE}: tr {key} is not an English copy")
    for pack in (en, tr):
        for val in pack.values():
            if _PLACEHOLDER_CHROME.search(val):
                fail(
                    f"{_ISSUE}: locale packs stay chrome only — no Ada / Berk / "
                    "Self in t() values"
                )
    if "pinned" not in en or "pinned" not in tr:
        fail(f"{_ISSUE}: keep pinned on en.ts + tr.ts (#368)")

    # 13) D24 — A–Z headings + quiet rail; Recent none; / follows filter.
    if not docs.strip():
        fail(
            f"{_ISSUE}: docs/user/app.md required — A–Z letter headings + rail"
        )
    if not _DOCS_HEADINGS.search(docs):
        fail(
            f"{_ISSUE}: docs/user/app.md must say A–Z has letter headings "
            "(placeholders Ada / Berk / Self)"
        )
    if not _DOCS_RAIL.search(docs):
        fail(f"{_ISSUE}: docs/user/app.md must mention the quiet letter rail")
    if not _DOCS_RECENT_NONE.search(docs):
        fail(f"{_ISSUE}: docs/user/app.md must say Recent has no rail / headings")
    if not _DOCS_FILTER.search(docs):
        fail(
            f"{_ISSUE}: docs/user/app.md must say / filter reduces headings "
            "and the rail"
        )
