"""#310 — find in this conversation (People + open person).

⌘F on People with a person selected stays on People and focuses a pane
find field (not #q, not chrome). Step through filteredTimeline hits
(tlIndex + ensureTlIndexVisible). <mark class="search-mark"> text
siblings via a new substring splitter (not splitSnippet on bodies).
Neighbors stay. Search-tab / no person / Review / Import / Doctor still
#q. Keep #208 / #126 / #273 / j/k / / / AltGr-safe mod.

Must-IDs: find-people-stays, find-miss-quiet, find-highlight-visible,
find-search-tab-q, find-keep-208, find-keep-126, find-bodies-text,
find-no-second-fts, find-keep-jk-slash-mod, find-keep-273, find-d24.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.keyboard_lib import (
    _FOCUS_PERSON_FILTER,
    _KEY_J,
    _KEY_K,
    _KEY_SLASH,
    _PREVENT_DEFAULT,
    _VIEW_SEARCH_ASSIGN,
    _app_keydown_body,
    _expand_fn_calls,
    _windows_around,
    _without_comments,
)
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.scan import (
    _HTML_BODY,
    _function_body,
    _search_pane_blob,
    _svelte_markup,
    _ts_fn_body,
    _web_logic,
)
from tauri_gate.search_field_keys import _API_SEARCH_CALL, _CHROME_SEARCH_HOOK
from tauri_gate.search_hits_jump_rest import _SEARCH_UNSAFE_HTML
from tauri_gate.status_toasts_chrome import _FOCUS_SEARCH_Q
from tauri_gate.status_toasts_toast import _KEY_F

_ISSUE = "#310"
_PANE = (
    "TimelinePane.svelte",
    "TimelineList.svelte",
    "TimelineRows.svelte",
    "PeopleShell.svelte",
    "LinkifyBody.svelte",
)
_FIND_Q = re.compile(
    r"\b(?:findQ|findQuery|tlFindQ|tlFindQuery|paneFindQ|threadFind|"
    r"conversationFind|inThreadFind|findInConversation|timelineFind|"
    r"peopleFind|tlFind)\b"
)
_FIND_HOOK = re.compile(
    r"data-(?:tl-)?find(?:-in-(?:conversation|thread|timeline))?"
    r"|id=[\"'](?:tl-find|person-find|timeline-find|find-in-conversation|"
    r"conversation-find|pane-find)[\"']",
    re.I,
)
_PERSON_OPEN = re.compile(
    r"if\s*\([^)]{0,240}\bselectedId\b"
    r"|view\s*===?\s*[\"']people[\"'][\s\S]{0,160}\bselectedId\b"
    r"|\bselectedId\b[\s\S]{0,160}view\s*===?\s*[\"']people[\"']"
    r"|(?:ctx\.)?selectedId\s*(?:&&|!=|!==)"
    r"|&&\s*(?:ctx\.)?selectedId\b"
)
_SPLITTER = re.compile(
    r"\b(?:splitFind|splitFindMarks|splitSubstring|splitQueryMarks|"
    r"markSubstring|findSegments|findMarkSegments|splitBodyMarks|"
    r"substringSegments|splitFindQuery)\b"
)
_MARK = re.compile(r"<mark\b[^>]*search-mark", re.I)
_SHIFT_ENTER = re.compile(
    r"shiftKey[\s\S]{0,120}(?:key\s*===?\s*[\"']Enter[\"'])"
    r"|(?:key\s*===?\s*[\"']Enter[\"'])[\s\S]{0,120}shiftKey"
)
_ENTER = re.compile(r"(?:e\.)?key\s*===?\s*[\"']Enter[\"']")
_OLDER = re.compile(r"\b(?:loadOlder|onLoadOlder|selectPerson\s*\([^)]*true)")
_FTS = re.compile(
    r"CREATE\s+VIRTUAL\s+TABLE|\bfts5\b|api\.search\s*\("
    r"|invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']search",
    re.I,
)
_BODY_RE = re.compile(
    r"new\s+RegExp\s*\(\s*(?:findQ|findQuery|tlFind|query)\b"
    r"|(?:body_text|displayBody|subject)\s*\.match\s*\(\s*(?:findQ|findQuery|tlFind)"
)
_ATTACH = re.compile(
    r"(?:findQ|findQuery|tlFind).{0,160}(?:attachments?\.|file_name|filename)"
    r"|(?:attachments?\.|file_name|filename).{0,160}(?:findQ|findQuery|tlFind)",
    re.I | re.S,
)
_MOD = re.compile(
    r"metaKey\s*\|\|\s*\(\s*(?:e\.)?ctrlKey\s*&&\s*!(?:e\.)?altKey\s*\)"
)
_DOCS_STAY = re.compile(
    r"(?:⌘\s*F|Ctrl\+F|Ctrl-F|find).{0,180}"
    r"(?:People|timeline|thread|conversation).{0,140}"
    r"(?:stay|stays|staying|does not leave|without leaving|on the thread|on People)"
    r"|(?:People|timeline|thread|conversation).{0,100}"
    r"(?:find|⌘\s*F|Ctrl\+F).{0,140}"
    r"(?:stay|stays|on the thread|on People|does not (?:switch|leave))",
    re.I | re.S,
)
_DOCS_Q = re.compile(
    r"(?:Search tab|Search view|from Search|on Search).{0,100}"
    r"(?:⌘\s*F|Ctrl\+F|Ctrl-F).{0,80}(?:#q|query)"
    r"|(?:⌘\s*F|Ctrl\+F|Ctrl-F).{0,100}"
    r"(?:Search tab|Search view|from Search).{0,80}(?:#q|query)",
    re.I | re.S,
)
_DOCS_SLASH = re.compile(
    r"(?:`/`|slash).{0,120}(?:people filter|#person-filter|person-filter)",
    re.I | re.S,
)
_DOCS_CHROME = re.compile(
    r"chrome.{0,48}search.{0,48}(?:Search|#q|archive)"
    r"|compact search field.{0,80}(?:Search|#q|archive)",
    re.I | re.S,
)
_T_CALL = re.compile(r"""\bt\s*\(\s*["']([A-Za-z_][\w]*)["']""")
_ESC_FIND = re.compile(
    r"(?:key\s*===?\s*[\"']Escape[\"'])[\s\S]{0,200}(?:findQ|findQuery|tlFind)"
    r"|(?:findQ|findQuery|tlFind)[\s\S]{0,200}(?:key\s*===?\s*[\"']Escape[\"'])"
)
_ESC_BLUR = re.compile(
    r"(?:findQ|findQuery|tlFind)[\s\S]{0,240}\.blur\s*\("
    r"|\.blur\s*\([\s\S]{0,240}(?:findQ|findQuery|tlFind)"
)


def _read(crate: Path, rel: str) -> str:
    p = crate / "web" / "lib" / rel
    return p.read_text() if p.is_file() else ""


def _find_key_surface(crate: Path) -> str:
    app = _web_logic(crate)
    cleaned = _without_comments(app)
    raw = _app_keydown_body(cleaned) or _app_keydown_body(app)
    body = _expand_fn_calls(cleaned, raw) if raw else ""
    if body == raw:
        body = _expand_fn_calls(app, raw) if raw else ""
    return _windows_around(body, _KEY_F) if body else ""


def _pane_blob(crate: Path) -> str:
    return "\n".join(_read(crate, n) for n in _PANE)


def _find_logic(crate: Path) -> str:
    extra = "\n".join(
        _read(crate, n)
        for n in (
            "PeopleKeys.ts",
            "snippetHighlight.ts",
            "TimelineMail.ts",
            "findHighlight.ts",
            "findInConversation.ts",
            "timelineFind.ts",
        )
    )
    return _without_comments(_pane_blob(crate) + "\n" + extra + "\n" + _read(crate, "../App.svelte"))


def _field_tag(markup: str) -> str:
    m = _FIND_HOOK.search(markup)
    if not m:
        return ""
    lt = markup.rfind("<", 0, m.start() + 1)
    gt = markup.find(">", m.end())
    return markup[lt : gt + 1] if lt >= 0 and gt > lt else ""


def _filter_pred(src: str) -> str:
    m = re.search(r"filteredTimeline\s*=\s*\$derived\s*\(", src)
    if not m:
        return ""
    open_p = src.find("(", m.end() - 1)
    if open_p < 0:
        return ""
    depth = 0
    for i, ch in enumerate(src[open_p:], open_p):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return src[open_p : i + 1]
    return src[open_p : open_p + 800]


def _fn(src: str, name: str) -> str:
    return _ts_fn_body(src, name) or _function_body(src, name) or ""


def _near(src: str, other: str, span: int = 360) -> bool:
    q = r"(?:findQ|findQuery|tlFindQ|tlFind)"
    return bool(
        re.search(rf"{q}[\s\S]{{0,{span}}}{other}|{other}[\s\S]{{0,{span}}}{q}", src)
    )


def assert_find_in_conversation(crate: Path) -> None:
    """#310: in-timeline find on People + open person; Search-tab still #q."""
    app_path = crate / "web" / "App.svelte"
    keys_path = crate / "web" / "lib" / "PeopleKeys.ts"
    rows_path = crate / "web" / "lib" / "TimelineRows.svelte"
    if not app_path.is_file():
        fail(f"{_ISSUE}: App.svelte required (Find map / whenSearchPaneReady)")
    if not keys_path.is_file():
        fail(f"{_ISSUE}: PeopleKeys.ts required (⌘F / Ctrl+F find map)")
    if not rows_path.is_file():
        fail(f"{_ISSUE}: TimelineRows.svelte required (bubble marks)")
    app_raw = app_path.read_text()
    app = _without_comments(app_raw)
    keys = _without_comments(keys_path.read_text())
    pane = _without_comments(_pane_blob(crate))
    logic = _find_logic(crate)
    search = _search_pane_blob(crate)
    hits = _read(crate, "SearchHits.svelte")
    empty = _read(crate, "TimelineEmpty.svelte")
    nav = _read(crate, "PeopleNav.svelte")
    rows = _read(crate, "TimelineRows.svelte")
    linkify = _read(crate, "LinkifyBody.svelte")
    markup = _svelte_markup(pane)
    f_surface = _find_key_surface(crate)
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) find-people-stays
    if not _PERSON_OPEN.search(f_surface) and not _PERSON_OPEN.search(keys):
        fail(
            f"{_ISSUE}: ⌘F / Ctrl+F on People with a person selected must stay "
            "on People (branch view === \"people\" && selectedId; do not always "
            "whenSearchPaneReady → Search #q)"
        )
    m = _PERSON_OPEN.search(f_surface) or _PERSON_OPEN.search(keys)
    src = f_surface if _PERSON_OPEN.search(f_surface) else keys
    stay = src[m.start() : m.start() + 520] if m else ""
    if re.search(r"\bwhenSearchPaneReady\b", stay) and not re.search(
        r"\breturn\b", stay.split("whenSearchPaneReady")[0]
    ):
        fail(
            f"{_ISSUE}: People + open person ⌘F must not call whenSearchPaneReady "
            "(stay on People; focus the pane find field)"
        )
    if _VIEW_SEARCH_ASSIGN.search(stay) and "return" not in stay.split("search", 1)[0]:
        fail(f"{_ISSUE}: People + open person ⌘F must not assign view = \"search\"")
    tag = _field_tag(markup)
    if not tag:
        fail(
            f"{_ISSUE}: timeline pane must have a find field "
            "(data-tl-find / data-find-in-conversation / id tl-find — "
            "not id=\"q\", not data-chrome-search)"
        )
    if re.search(r"id\s*=\s*[\"']q[\"']", tag):
        fail(f"{_ISSUE}: pane find field must not steal id=\"q\" (SearchPane keeps #q)")
    if _CHROME_SEARCH_HOOK.search(tag):
        fail(f"{_ISSUE}: pane find field must not be data-chrome-search (keep #208)")
    if not re.search(r"<Input\b|<input\b", tag, re.I):
        fail(f"{_ISSUE}: pane find field must be an Input / input on the timeline pane")

    # 2) find-search-tab-q + other-views
    if not re.search(r"id=[\"']q[\"']", search):
        fail(f"{_ISSUE}: SearchPane must keep id=\"q\" so Search-tab ⌘F can focus it")
    if not (
        re.search(r"\bwhenSearchPaneReady\b", f_surface) or _FOCUS_SEARCH_Q.search(f_surface)
    ):
        fail(
            f"{_ISSUE}: Search-tab / no person / Review / Import / Doctor ⌘F "
            "must still focus #q (whenSearchPaneReady)"
        )
    other = keys + "\n" + app
    for view in ("review", "import", "doctor"):
        if not re.search(rf"[\"']{view}[\"']", other):
            fail(f"{_ISSUE}: keep view \"{view}\" on the archive Search ⌘F path")

    # 3) find-highlight-visible
    mark_src = rows + "\n" + linkify + "\n" + pane
    if not _MARK.search(mark_src):
        fail(
            f"{_ISSUE}: a loaded Ada bubble match must highlight with "
            "<mark class=\"search-mark\"> text children "
            "(TimelineRows / LinkifyBody — not SearchHits only)"
        )
    if not _SPLITTER.search(logic):
        fail(
            f"{_ISSUE}: find marks need a new substring splitter "
            "(splitFind / findSegments / markSubstring — do not run "
            "splitSnippet «» on timeline bodies)"
        )
    if re.search(r"\bsplitSnippet\s*\(", rows + "\n" + linkify):
        fail(
            f"{_ISSUE}: do not run splitSnippet on timeline bodies "
            "(«» FTS markers are not there — new substring splitter)"
        )
    if not _FIND_Q.search(logic):
        fail(
            f"{_ISSUE}: client find query (findQ / findQuery / tlFind) over "
            "loaded bubbles"
        )
    if not _near(logic, r"ensureTlIndexVisible") or not _near(logic, r"\btlIndex\b"):
        fail(
            f"{_ISSUE}: a loaded hit must be shown via tlIndex + "
            "ensureTlIndexVisible (jump off-window loaded rows; data-tl-index)"
        )
    if not re.search(r"data-tl-index", rows):
        fail(f"{_ISSUE}: keep data-tl-index so ensureTlIndexVisible can show a hit")

    # 4) step through — do not filter-hide neighbors
    pred = _filter_pred(pane)
    if _FIND_Q.search(pred):
        fail(
            f"{_ISSUE}: step through hits — do not AND the find query into "
            "filteredTimeline (neighbors stay; j/k still visibleTlIndices)"
        )
    if not re.search(r"platformFilter", pred) or not re.search(r"kindFilter", pred):
        fail(
            f"{_ISSUE}: filteredTimeline stays platform + kind chips "
            "(find walks that list; do not replace the chip filter)"
        )

    # 5) haystack / quoted / case / compose / corpus
    hay = logic
    if not _near(hay, r"displayBody\s*\(") or not _near(hay, r"\bsubject\b"):
        fail(
            f"{_ISSUE}: find haystack is displayBody(body_text) and subject "
            "(not attachment names)"
        )
    if _ATTACH.search(hay):
        fail(f"{_ISSUE}: do not match attachment names (haystack is body + subject)")
    if not _near(hay, r"(?:splitQuotedBody|parts\.main|quotedOpen)"):
        fail(
            f"{_ISSUE}: match only visible text — do not search folded quoted tails "
            "(splitQuotedBody / parts.main / quotedOpen)"
        )
    if not _near(hay, r"toLowerCase") or not _near(hay, r"\.includes"):
        fail(
            f"{_ISSUE}: find is case-insensitive (toLowerCase() + includes), "
            "same idea as people /"
        )
    if not _near(hay, r"filteredTimeline"):
        fail(
            f"{_ISSUE}: find among the current platform/kind filteredTimeline "
            "(compose-filters — not the unfiltered timeline)"
        )
    if _OLDER.search(hay) and _FIND_Q.search(hay):
        fail(
            f"{_ISSUE}: do not auto Load older on find "
            "(loaded timeline only; jump loaded off-window hits)"
        )

    # 6) find-next
    if not _ENTER.search(hay) and not _ENTER.search(pane):
        fail(f"{_ISSUE}: Enter steps to the next in-conversation hit (first hit as you type)")
    if not _SHIFT_ENTER.search(hay) and not _SHIFT_ENTER.search(pane):
        fail(f"{_ISSUE}: Shift+Enter steps to the previous in-conversation hit")

    # 7) find-miss-quiet
    if re.search(r"No hits", pane) or (re.search(r"No hits", empty) and _FIND_Q.search(empty)):
        fail(
            f"{_ISSUE}: a miss must not mount Search EmptyState \"No hits\" "
            "(stay on the thread; no marks)"
        )
    if _FIND_Q.search(empty) and re.search(r"No messages in this view", empty):
        fail(
            f"{_ISSUE}: a miss must not show timeline \"No messages in this view\" "
            "(that CTA is chip-empty, not find-miss)"
        )

    # 8) find-esc
    esc_src = keys + "\n" + pane + "\n" + hay
    if not _ESC_FIND.search(esc_src):
        fail(
            f"{_ISSUE}: Esc in the find field must clear the query / marks "
            "(empty field then blurs)"
        )
    if not _ESC_BLUR.search(esc_src):
        fail(f"{_ISSUE}: empty find field Esc must blur (after clear)")

    # 9) find-keep-208
    if not _CHROME_SEARCH_HOOK.search(nav + "\n" + app):
        fail(f"{_ISSUE}: keep data-chrome-search (#208) — do not hijack chrome as pane find")
    submit = _fn(app_raw, "submitChromeSearch")
    if not submit or not re.search(r"\bwhenSearchPaneReady\b", submit):
        fail(
            f"{_ISSUE}: chrome search must still whenSearchPaneReady → #q "
            "(keep #208; do not bind chrome to timeline find)"
        )

    # 10) find-keep-126 + find-bodies-text
    if not re.search(r"\bsplitSnippet\b", hits) or not _MARK.search(hits):
        fail(f"{_ISSUE}: SearchHits must keep splitSnippet + <mark class=\"search-mark\"> (#126)")
    if _SEARCH_UNSAFE_HTML.search(hits) or _HTML_BODY.search(hits):
        fail(f"{_ISSUE}: SearchHits snippet / expanded body stay text (#126)")
    body_src = rows + "\n" + linkify + "\n" + pane
    if _HTML_BODY.search(body_src) or re.search(r"\.innerHTML\s*=|insertAdjacentHTML\s*\(", body_src):
        fail(
            f"{_ISSUE}: find marks are Svelte text siblings — no {{@html}} / "
            "innerHTML / insertAdjacentHTML of body_text / displayBody"
        )

    # 11) find-no-second-fts
    if _API_SEARCH_CALL.search(hay) or _FTS.search(hay):
        fail(
            f"{_ISSUE}: in-timeline find is client substring on loaded rows — "
            "no api.search / second FTS"
        )
    if _BODY_RE.search(hay):
        fail(f"{_ISSUE}: do not regex-parse bodies (toLowerCase + includes / indexOf only)")

    # 12) find-keep-jk-slash-mod
    if not _KEY_SLASH.search(keys) or not _FOCUS_PERSON_FILTER.search(keys):
        fail(f"{_ISSUE}: `/` must still focus #person-filter")
    if not _KEY_J.search(keys) or not _KEY_K.search(keys):
        fail(f"{_ISSUE}: keep timeline j/k on People")
    if not re.search(r"visibleTlIndices", keys):
        fail(f"{_ISSUE}: j/k still walk visibleTlIndices (not the hit list)")
    if not _MOD.search(keys) and not _MOD.search(app):
        fail(f"{_ISSUE}: keep AltGr-safe mod (metaKey || (ctrlKey && !altKey)) on Find")
    if not _PREVENT_DEFAULT.search(f_surface):
        fail(f"{_ISSUE}: ⌘F / Ctrl+F must preventDefault (webview must not take Find)")

    # 13) find-keep-273
    bubble = _fn(app_raw, "searchFromBubble")
    if not bubble or not re.search(r"\bwhenSearchPaneReady\b", bubble):
        fail(
            f"{_ISSUE}: bubble context Search still opens FTS Search and focuses #q "
            "(#273 — that is not in-timeline find)"
        )
    if not re.search(r"display_name", bubble):
        fail(f"{_ISSUE}: bubble Search still seeds the person name (Ada), not a raw id")

    # 14) find-d24
    if not dtxt.strip():
        fail(f"{_ISSUE}: docs/user/app.md required (People-timeline find)")
    if not _DOCS_STAY.search(dtxt):
        fail(f"{_ISSUE}: docs/user/app.md must say People timeline find stays on the thread")
    if not _DOCS_Q.search(dtxt):
        fail(f"{_ISSUE}: docs/user/app.md must say Search-tab ⌘F still focuses #q")
    if not _DOCS_SLASH.search(dtxt):
        fail(f"{_ISSUE}: docs/user/app.md must keep `/` focusing the people filter")
    if not _DOCS_CHROME.search(dtxt):
        fail(f"{_ISSUE}: docs/user/app.md must keep chrome search as archive Search")

    # 15) copy en+tr if the field has visible chrome (#131). Ada only.
    vis = re.search(r"(?:placeholder|aria-label|title)\s*=\s*\{?([^}>\n]+)", tag, re.I)
    if vis:
        raw = vis.group(1)
        if re.search(r"[\"'][A-Za-z]", raw) and not _T_CALL.search(raw):
            fail(
                f"{_ISSUE}: find field visible chrome copy must use t() "
                "(en+tr, #131; placeholders Ada only)"
            )
        km = _T_CALL.search(raw)
        if km:
            key = km.group(1)
            en_p = crate / "web" / "lib" / "locales" / "en.ts"
            tr_p = crate / "web" / "lib" / "locales" / "tr.ts"
            en = _chrome_pack_entries(en_p.read_text()) if en_p.is_file() else {}
            tr = _chrome_pack_entries(tr_p.read_text()) if tr_p.is_file() else {}
            if key not in en or key not in tr:
                fail(f"{_ISSUE}: find field copy key {key!r} must exist in en.ts and tr.ts (#131)")
    if re.search(r"/Users/|/home/", pane + "\n" + keys):
        fail(f"{_ISSUE}: tests stay placeholders (Ada) — no real home paths")
