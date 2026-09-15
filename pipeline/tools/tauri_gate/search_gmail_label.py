"""#365 — Search filter by Gmail label (mix A).

Wired immediately after assert_search_filters_secondary (#209 family).

Confirmed mix: new labels_list IPC (not status/open). SearchQuery.label_id:
Option<i64>; chrome shows the stored name (option text), id is the private
option value. search() ANDs EXISTS on message_labels (do not JOIN labels
into the FTS SELECT). Empty / Any = None / omit. CLI --label absent.

Chrome: closed <select data-gmail-label> inside data-search-filters, next
to Platform / Kind / Attachment. #q stays first. Any is t() en+tr, default.
Option text is stored names (Inbox / Sent / Family), not t("Inbox"), not a
raw id. WhatsApp-only (no labels rows): Any-only, not hidden, not a spinner.
Invalid pick: searchError, no api.search. Core unknown id: 0 hits.
Catalog ORDER BY name. No hide-list. Empty q still []. Timeline chips stay
unclickable. No Search-hit chips.

#209 check 8 is a shape keep (hooked closed select allowed). #364 check 9
still bans chips on SearchHits / inspector; it does not fail this select.

Placeholders only (Ada / Berk). Plant strings Inbox / Sent / Family.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.scan import (
    _match_closer,
    _rust_function_body,
    _search_pane_blob,
    _svelte_markup,
    _tauri_rust_blob,
    _web_logic,
    _without_comments,
)
from tauri_gate.search_filters_lib import _SEARCH_API_PLATFORM_ARG
from tauri_gate.search_picker_lib import (
    _SEARCH_DATE_ERROR_SET,
    _SEARCH_FILTERS_HOOK,
    _SEARCH_GMAIL_LABEL,
    _SEARCH_Q_ID,
    _hook_element_blocks,
    _search_run_surface,
)

_ISSUE = "#365"

_SELECT_HOOK = re.compile(r"\bdata-gmail-label\b")
_SLABEL = re.compile(r"""\bid\s*=\s*["']slabel["']""")
_CLOSED_SELECT = re.compile(
    r"<select\b[^>]{0,400}\bdata-gmail-label\b"
    r"|<select\b[^>]{0,400}\bid\s*=\s*[\"']slabel[\"']",
    re.I,
)
_LABEL_SELECT_BLOCK = re.compile(
    r"<select\b[^>]{0,400}(?:\bdata-gmail-label\b|\bid\s*=\s*[\"']slabel[\"'])"
    r"[^>]*>[\s\S]{0,4000}?</select>",
    re.I,
)
_FREE_TEXT = re.compile(
    r"<Input\b[^>]{0,400}(?:data-gmail-label|labelFilter|labelId|"
    r"id\s*=\s*[\"']slabel[\"'])"
    r"|<input\b(?![^>]*\btype\s*=\s*[\"'](?:hidden|checkbox|radio)[\"'])"
    r"[^>]{0,400}(?:data-gmail-label|labelFilter|id\s*=\s*[\"']slabel[\"'])",
    re.I,
)
_T_INBOX = re.compile(
    r"""\bt\s*\(\s*["'](?:Inbox|Sent|Family)["']"""
    r"""|\bt\s*\(\s*(?:name|lab(?:el)?\.name|n)\b"""
)
_T_CALL = re.compile(r"""\bt\s*\(\s*["']([A-Za-z_][\w]*)["']\s*\)""")
_OPTION_NAME = re.compile(
    r"\{(?:lab(?:el)?\.)?name\}|\{n(?:ame)?\}",
)
_OPTION_ID_TEXT = re.compile(
    r"<option\b[^>]*>\s*\{(?:lab(?:el)?\.)?id\}",
    re.I,
)
_ANY_OPTION = re.compile(
    r"<option\b[^>]*\bvalue\s*=\s*[\"'][\"'][^>]*>",
    re.I,
)
_LABEL_STATE = (
    r"(?:labelId|label_id|selectedLabelId|pickedLabelId|searchLabelId|gmailLabelId)"
)
_LABEL_LIST = (
    r"(?:labels|labelOptions|gmailLabels|archiveLabels|labelList|loadedLabels)"
)
_LABELS_LIST_API = re.compile(
    r"\b(?:labelsList|labels_list|labelsListCmd)\b"
    r"""|\binvoke\s*[<(][^)]*["']labels_list"""
)
_LABELS_LIST_CMD = re.compile(r"\blabels_list(?:_cmd)?\b")
_STATUS_LABELS = re.compile(
    r"(?:status\s*\(\s*\)|\bst\b|\bstatus\b)\s*\.\s*labels\b"
    r"|\bapplyStatus\b[\s\S]{0,200}\blabels\b",
    re.I,
)
_ORDER_BY_NAME = re.compile(r"ORDER\s+BY\s+name\b", re.I)
_HIDE_LIST = re.compile(
    r"""["'](?:Unread|Opened|Important|Trash|Category)["']"""
    r"|hide(?:n)?Labels|LABEL_HIDE|systemLabels",
    re.I,
)
_SPIN = re.compile(r"spinner|skeleton|animate-spin|loadingLabels", re.I)
_CLI_LABEL = re.compile(r"""--label\b|#\[arg[^\]]*long\s*=\s*["']label["']""")
_LABEL_ID_FIELD = re.compile(r"\blabel_id\s*:")
_LABEL_ID_TS = re.compile(r"\b(?:labelId|label_id)\s*:")
_EMPTY_AS_ANY = re.compile(
    rf"(?:labelId|label_id)\s*:\s*(?:"
    rf"{_LABEL_STATE}\s*\|\|\s*(?:null|undefined)"
    rf"|{_LABEL_STATE}\s*\?\?\s*(?:null|undefined)"
    rf"|{_LABEL_STATE}\s*\?\s*{_LABEL_STATE}[^,}}]{{0,40}}:\s*(?:null|undefined)"
    rf"|!{_LABEL_STATE}\s*\?\s*(?:null|undefined)"
    rf"|{_LABEL_STATE}\s*\?\s*Number"
    r")",
    re.I,
)
_INVALID_MEMBER = re.compile(
    rf"(?:"
    rf"{_LABEL_LIST}\s*\.\s*(?:some|find|includes|findIndex|someId)"
    rf"|includes\s*\([^)]{{0,40}}{_LABEL_STATE}"
    rf"|invalid(?:Label|Pick|_label|_pick)"
    rf"|label(?:Missing|Gone|Invalid|Unknown)"
    rf"|loaded(?:Labels|Ids)"
    r")",
    re.I,
)
_CHIP_HOOK = re.compile(
    r"\bdata-(?:mail-label|label-chip|gmail-labels|mail-labels)\b"
)
_CHIP_CLICK = re.compile(r"\bonclick\b|\bhref\s*=|\bapi\.search")
_HANDLER = re.compile(r"generate_handler!\s*\[(.*?)\]", re.S)
_DOCS_LABEL = re.compile(
    r"("
    r"(?:label|Label).{0,80}(?:filter|select|closed)"
    r"|(?:filter|select).{0,80}(?:label|Label)"
    r"|secondary[^\n]{0,120}label"
    r")",
    re.I | re.S,
)
_DOCS_ANY = re.compile(
    r"("
    r"(?:empty|Any).{0,60}(?:no predicate|omit|any)"
    r"|label.{0,40}(?:empty|Any).{0,40}(?:any|omit|predicate)"
    r")",
    re.I | re.S,
)
_DOCS_INVALID = re.compile(
    r"("
    r"invalid\s+(?:pick|label).{0,60}(?:do\s+not|don't|does\s+not)\s+search"
    r"|invalid\s+(?:pick|label).{0,80}(?:do\s+not|don't|no)\s+"
    r"(?:search|fetch|invoke|api\.search)"
    r")",
    re.I | re.S,
)
_NEW_LOCALE_ARCHIVE = re.compile(r"^(?:inbox|sent|family)$", re.I)
_BLIND = frozenset({"search.rs", "identity.rs"})
_BLIND_DIRS = frozenset({"import"})


def _text(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


def _rust_struct_body(src: str, name: str) -> str:
    m = re.search(rf"(?:pub\s+)?struct\s+{re.escape(name)}\s*\{{", src)
    if not m:
        return ""
    start = src.find("{", m.start())
    if start < 0:
        return ""
    end = _match_closer(src, start)
    if end < 0:
        return src[start:]
    return src[start : end + 1]


def _core_catalog_blob(root: Path) -> str:
    """Core + Tauri sources except blinded search / import / identity bodies."""
    parts: list[str] = []
    for base in (
        root / "crates" / "interlace-core" / "src",
        root / "crates" / "interlace-tauri" / "src",
    ):
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.rs")):
            if p.name in _BLIND:
                continue
            if any(part in _BLIND_DIRS for part in p.parts):
                continue
            parts.append(p.read_text())
    return "\n".join(parts)


def _label_select_region(surface: str, hook_blob: str) -> str:
    for blob in (hook_blob, surface):
        m = _LABEL_SELECT_BLOCK.search(blob)
        if m:
            return m.group(0)
    return ""


def assert_search_gmail_label(crate: Path) -> None:
    """#365: closed label select under Search Filters (mix A)."""
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail(f"{_ISSUE}: select missing")

    src = _search_pane_blob(crate)
    cleaned = _without_comments(src)
    markup = _svelte_markup(src)
    surface = markup if markup.strip() else src
    hook_blocks = _hook_element_blocks(surface, _SEARCH_FILTERS_HOOK)
    hook_blob = "\n".join(hook_blocks)

    # 1) closed select under data-search-filters — primary red today.
    if not hook_blocks or not (
        _CLOSED_SELECT.search(hook_blob) or _SELECT_HOOK.search(hook_blob)
    ):
        fail(f"{_ISSUE}: select missing")
    if not _CLOSED_SELECT.search(hook_blob):
        fail(
            f"{_ISSUE}: closed <select data-gmail-label> under "
            "data-search-filters (not free-text, not outside the hook)"
        )
    if _FREE_TEXT.search(surface) or _FREE_TEXT.search(src):
        fail(f"{_ISSUE}: label filter is a closed <select>, not free-text")
    if _SELECT_HOOK.search(surface) and not _SELECT_HOOK.search(hook_blob):
        fail(
            f"{_ISSUE}: data-gmail-label must live under data-search-filters "
            "(not a #q sibling)"
        )

    q_m = _SEARCH_Q_ID.search(surface)
    if not q_m:
        fail(f"{_ISSUE}: keep id=\"q\" as the first / primary query control")
    sel_m = _CLOSED_SELECT.search(surface) or _SELECT_HOOK.search(surface)
    if sel_m and q_m.start() > sel_m.start():
        fail(f"{_ISSUE}: #q stays first; the label select is not a sibling of #q")

    region = _label_select_region(surface, hook_blob)
    if not region:
        fail(f"{_ISSUE}: select missing")

    # 2) Any default via t(); empty / Any omits the arg.
    if not _ANY_OPTION.search(region):
        fail(
            f"{_ISSUE}: label <select> must include an empty-value Any option "
            '(value="" — empty means any)'
        )
    first_opt = re.search(r"<option\b[^>]*>[\s\S]{0,200}?</option>", region, re.I)
    first = first_opt.group(0) if first_opt else region
    if not re.search(r"\bvalue\s*=\s*[\"'][\"']", first, re.I):
        fail(f"{_ISSUE}: Any is the default empty-value option")
    if re.search(r">\s*Any\s*<", first) and not _T_CALL.search(first):
        fail(f"{_ISSUE}: Any is t() chrome (en+tr), not hardcoded English")
    t_any = _T_CALL.search(first)
    if not t_any:
        fail(f"{_ISSUE}: Any option text is t() (en+tr)")

    api_m = _SEARCH_API_PLATFORM_ARG.search(cleaned)
    api_args = api_m.group(1) if api_m else cleaned
    if not _LABEL_ID_TS.search(api_args) and not _LABEL_ID_TS.search(cleaned):
        fail(
            f"{_ISSUE}: api.search must receive labelId from the select "
            "(empty / Any omits — null / absent)"
        )
    if not _EMPTY_AS_ANY.search(api_args) and not _EMPTY_AS_ANY.search(cleaned):
        fail(
            f"{_ISSUE}: empty / Any must omit the label predicate "
            "(labelId: labelId || null — same as empty platform)"
        )
    if re.search(
        rf"\b(?:let|const|var)\s+{_LABEL_STATE}\s*=\s*\$state\s*(?:<[^>]*>)?\s*\(\s*"
        r"(?:[1-9]\d*|[\"'][^\"']+[\"'])\s*\)",
        cleaned,
    ):
        fail(f"{_ISSUE}: label state must default to empty / Any, not a planted id")

    # 3) option text is the stored name, not t("Inbox"), not a raw id.
    if _T_INBOX.search(region) or _T_INBOX.search(cleaned):
        fail(
            f"{_ISSUE}: option text is the stored name (Inbox / Sent / Family), "
            "not t(\"Inbox\") / t(name)"
        )
    if not _OPTION_NAME.search(region) and not _OPTION_NAME.search(surface):
        fail(
            f"{_ISSUE}: option text is the stored name ({{lab.name}}), "
            "not a chrome key"
        )
    if _OPTION_ID_TEXT.search(region):
        fail(
            f"{_ISSUE}: chrome shows the name, not a raw numeric id "
            "(id may be the private option value)"
        )

    # 4) invalid pick: searchError, no api.search.
    run_all, run_before = _search_run_surface(cleaned)
    if not run_all:
        fail(f"{_ISSUE}: SearchPane run() required (submit / Retry path)")
    if "api.search" not in run_all:
        fail(f"{_ISSUE}: SearchPane run() must remain the api.search caller")
    has_member = bool(
        _INVALID_MEMBER.search(run_before) or _INVALID_MEMBER.search(run_all)
    )
    has_early = bool(re.search(r"\breturn\b", run_before))
    has_err = bool(_SEARCH_DATE_ERROR_SET.search(run_before))
    if not has_member or not has_early or not has_err:
        fail(
            f"{_ISSUE}: invalid pick (stale id / not in the loaded list) must "
            "set searchError and skip api.search (same family as invalid dates)"
        )

    # 5) WA-only: Any-only, not hidden, not a spinner.
    if re.search(
        rf"\{{#if\s+[^}}]*\b{_LABEL_LIST}\b[^}}]*\.length[^}}]*\}}"
        r"[\s\S]{0,800}data-gmail-label",
        surface,
    ):
        fail(
            f"{_ISSUE}: WhatsApp-only (empty catalog) keeps the select "
            "Any-only — do not hide it behind labels.length"
        )
    if _SPIN.search(region) or (
        _SPIN.search(hook_blob) and _SELECT_HOOK.search(hook_blob)
    ):
        fail(f"{_ISSUE}: WA-only / empty catalog is Any-only, not a spinner")
    if re.search(r"<select\b[^>]{0,400}data-gmail-label[^>]*>\s*</select>", surface, re.I):
        fail(f"{_ISSUE}: empty catalog still has the Any option (not zero options)")

    # 6) labels_list IPC + SearchQuery.label_id (not status / not CLI --label).
    api = _text(crate / "web" / "lib" / "api.ts")
    rust = _tauri_rust_blob(crate)
    if not _LABELS_LIST_API.search(api) and not _LABELS_LIST_API.search(cleaned):
        fail(f"{_ISSUE}: api.labelsList() (new labels_list IPC, not status / open)")
    if not _LABELS_LIST_CMD.search(rust):
        fail(f"{_ISSUE}: generate_handler / ipc must expose labels_list")
    h = _HANDLER.search(rust)
    if h and not _LABELS_LIST_CMD.search(h.group(1)):
        fail(f"{_ISSUE}: labels_list must be in generate_handler")
    if not _LABELS_LIST_API.search(cleaned) and not re.search(
        r"labelsList\s*\(|labels_list", cleaned
    ):
        fail(f"{_ISSUE}: SearchPane loads the catalog via labels_list")
    if not re.search(r"\barchivePath\b", cleaned):
        fail(
            f"{_ISSUE}: catalog reload keys off archivePath (flips with api.open), "
            "not the later people assignment"
        )
    if _STATUS_LABELS.search(cleaned) or _STATUS_LABELS.search(api):
        fail(f"{_ISSUE}: catalog is labels_list IPC, not status / open")
    if not _LABEL_ID_TS.search(api):
        fail(f"{_ISSUE}: api.search args include labelId")

    root = repo_root()
    model = _text(root / "crates" / "interlace-core" / "src" / "model.rs")
    sq = _rust_struct_body(model, "SearchQuery")
    if not re.search(r"\blabel_id\s*:\s*Option\s*<\s*i64\s*>", sq):
        fail(f"{_ISSUE}: SearchQuery.label_id: Option<i64>")
    ipc = _text(crate / "src" / "ipc.rs")
    args = _rust_struct_body(ipc, "SearchArgs")
    if not _LABEL_ID_FIELD.search(args):
        fail(f"{_ISSUE}: SearchArgs carries label_id (IPC labelId)")

    catalog = _core_catalog_blob(root)
    list_fn = _rust_function_body(catalog, "labels_list")
    if list_fn and not _ORDER_BY_NAME.search(list_fn):
        fail(f"{_ISSUE}: labels_list is ORDER BY name (no hide-list)")
    if not list_fn and not _ORDER_BY_NAME.search(catalog):
        fail(f"{_ISSUE}: labels_list is ORDER BY name (no hide-list)")
    if _HIDE_LIST.search(region) or _HIDE_LIST.search(list_fn or ""):
        fail(f"{_ISSUE}: no hide-list — every labels row (Inbox / Sent / Family)")

    cli = _text(root / "crates" / "interlace-core" / "src" / "cli.rs") + "\n" + _text(
        root / "crates" / "interlace-core" / "src" / "cli" / "search.rs"
    )
    if _CLI_LABEL.search(cli):
        fail(f"{_ISSUE}: CLI --label is absent (CLI compiles the field as None)")

    # 7) no SearchHits chips / no data-gmail-label on hits.
    hits = _text(crate / "web" / "lib" / "SearchHits.svelte")
    if _SELECT_HOOK.search(hits) or _SEARCH_GMAIL_LABEL.search(hits) or _CHIP_HOOK.search(
        hits
    ):
        fail(f"{_ISSUE}: do not put a label select or chips on SearchHits")

    # 8) timeline chips stay unclickable; no Search select on the timeline.
    rows = _text(crate / "web" / "lib" / "TimelineRows.svelte")
    if _SELECT_HOOK.search(rows):
        fail(f"{_ISSUE}: do not put a Search label select on the timeline")
    for m in re.finditer(
        r"<div\b[^>]*\bdata-mail-labels\b[^>]*>[\s\S]*?</div>",
        rows,
    ):
        if _CHIP_CLICK.search(m.group(0)):
            fail(
                f"{_ISSUE}: timeline chips stay unclickable "
                "(not a Search control / no chip→Search)"
            )

    # 9) D24 — filters list includes label; empty / Any = no predicate; invalid skip.
    dtxt = _text(root / "docs" / "user" / "search.md") + "\n" + _text(
        root / "docs" / "user" / "app.md"
    )
    if not _DOCS_LABEL.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/search.md and/or docs/user/app.md must say "
            "Filters include a label closed select"
        )
    if not _DOCS_ANY.search(dtxt):
        fail(
            f"{_ISSUE}: docs must say empty / Any = no label predicate"
        )
    if not _DOCS_INVALID.search(dtxt):
        fail(f"{_ISSUE}: docs must say an invalid pick does not search")

    # 10) en+tr Any key; archive names stay out of the pack.
    en = _chrome_pack_entries(_text(crate / "web" / "lib" / "locales" / "en.ts"))
    tr = _chrome_pack_entries(_text(crate / "web" / "lib" / "locales" / "tr.ts"))
    extra_en = set(en) - set(tr)
    extra_tr = set(tr) - set(en)
    if extra_en or extra_tr:
        bits: list[str] = []
        if extra_en:
            bits.append("in en only: " + ", ".join(sorted(extra_en)))
        if extra_tr:
            bits.append("in tr only: " + ", ".join(sorted(extra_tr)))
        fail(f"{_ISSUE}: en+tr packs must stay aligned — " + "; ".join(bits))
    any_key = t_any.group(1)
    if any_key not in en or any_key not in tr:
        fail(f"{_ISSUE}: Any key {any_key!r} must exist on both en and tr")
    if en.get(any_key) == tr.get(any_key) and any_key not in {"searchAnyDate"}:
        # New key must not be an English copy on tr.
        if (tr.get(any_key) or "").strip().lower() in {"any", "inbox", "sent", "family"}:
            fail(f"{_ISSUE}: tr Any is not an English copy (found {tr.get(any_key)!r})")
    for key in list(en) + list(tr):
        if _NEW_LOCALE_ARCHIVE.search(key):
            fail(
                f"{_ISSUE}: do not add Inbox/Sent/Family as t() chrome keys "
                f"(found {key}; names are archive data)"
            )

    # 11) keep #121–#126 / #205 / #208 / #209 rest / #318.
    if not re.search(
        r"<select\b[^>]{0,400}(?:\bbind:value=\{platform\}|\bid\s*=\s*[\"']plat[\"'])",
        surface,
        re.I,
    ):
        fail(f"{_ISSUE}: keep the search platform closed <select> (#121)")
    if not re.search(
        r"<select\b[^>]{0,400}(?:\bbind:value=\{conversationKind\}|\bid\s*=\s*[\"']skind[\"'])",
        surface,
        re.I,
    ):
        fail(f"{_ISSUE}: keep the search kind closed <select> (#122)")
    if not re.search(
        r"<select\b[^>]{0,400}(?:\bbind:value=\{attachmentFilter\}|\bid\s*=\s*[\"']satt[\"'])",
        surface,
        re.I,
    ):
        fail(f"{_ISSUE}: keep the search attachment closed <select> (#125)")
    if not re.search(r"data-person-picker|personFilter|personId", cleaned):
        fail(f"{_ISSUE}: keep the search person picker (#123)")
    if not re.search(r"\{#each\s+hits\b", surface) and not re.search(
        r"\{#each\s+hits\b", src
    ):
        fail(f"{_ISSUE}: keep search hits list (#124)")
    if not re.search(r"<mark\b", surface, re.I) and not re.search(
        r"<mark\b", hits, re.I
    ):
        fail(f"{_ISSUE}: keep search snippet <mark> highlight (#126)")
    if not re.search(r"\bdata-partial\b", surface) and not re.search(
        r"\bdata-partial\b", hits
    ):
        fail(f"{_ISSUE}: keep search data-partial Error+Retry (#205)")
    app_path = crate / "web" / "App.svelte"
    app = _text(app_path)
    if not re.search(r"\bdata-chrome-search\b", _web_logic(crate)):
        fail(f"{_ISSUE}: keep chrome search field data-chrome-search (#208)")
    if re.search(r"\bapi\.search\s*\(", app):
        fail(
            f"{_ISSUE}: App.svelte must not call api.search — SearchPane run() "
            "stays the only caller (#208)"
        )
    if re.search(r"\b(?:searchLabelId|labelId)\s*=\s*\$state", app) or re.search(
        r"bind:labelId|bind:label_id", app
    ):
        fail(f"{_ISSUE}: keep #318 — do not lift the label filter onto App")
