"""Helpers extracted from search_picker.py (search_picker_lib)."""
from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _expand_fn_calls,
    _function_body,
    _matching_each_end,
    _search_pane_blob,
    _svelte_markup,
    _ts_fn_body,
    _web_logic,
    _without_comments,
)

from tauri_gate.media_linkify_lib import _hook_element_blocks

from tauri_gate.search_filters_lib import (
    _INVENTED_SEARCH_PLATFORM_TOKENS,
    _SEARCH_API_PLATFORM_ARG,
    _search_platform_option_values,
)

from tauri_gate.status_toasts_toast import _tag_inner




# #123 — SearchPane person picker by display name (not free-text numeric id).
# State names accepted for the chosen person id (numeric under the hood).
_SEARCH_PERSON_ID_STATE = (
    r"(?:personId|person_id|selectedPersonId|pickedPersonId|searchPersonId)"
)
# Free-text filter / query over display names (not the stored id).
_SEARCH_PERSON_FILTER_STATE = (
    r"(?:personFilter|personQuery|personSearch|searchPersonFilter|personNameFilter|"
    r"personPickQuery|personPickerQuery|personText|nameFilter)"
)
# Label that treats the control as a raw id field (pre-impl UX).
_SEARCH_PERSON_ID_LABEL = re.compile(
    r">\s*Person\s*id\s*<"
    r"|for\s*=\s*[\"']sp[\"'][^>]*>\s*Person\s*id\s*<"
    r"|placeholder\s*=\s*[\"'][^\"']*\bperson\s*id\b[^\"']*[\"']",
    re.I,
)
# Free-text Input bound to the stored person id (user types a number).
# id="sp" alone is fine for a name-filter field; fail only when bound to id state
# or when the id field uses list= datalist of people ids.
_SEARCH_PERSON_ID_FREE_TEXT = re.compile(
    rf"<Input\b[^>]{{0,400}}\bbind:value=\{{{_SEARCH_PERSON_ID_STATE}\}}"
    rf"|<input\b(?![^>]*\btype\s*=\s*[\"'](?:hidden|checkbox|radio|submit|button)[\"'])"
    rf"[^>]{{0,400}}\bbind:value=\{{{_SEARCH_PERSON_ID_STATE}\}}"
    rf"|<Input\b[^>]{{0,200}}(?:\bid\s*=\s*[\"']sp[\"'][^>]{{0,200}}\blist\s*="
    rf"|\blist\s*=\s*[\"']people-ids[\"'][^>]{{0,200}}\bbind:value=\{{{_SEARCH_PERSON_ID_STATE}\}})"
    rf"|<input\b(?![^>]*\btype\s*=\s*[\"'](?:hidden|checkbox|radio|submit|button)[\"'])"
    rf"[^>]{{0,200}}(?:\bid\s*=\s*[\"']sp[\"'][^>]{{0,200}}\blist\s*="
    rf"|\blist\s*=\s*[\"']people-ids[\"'])",
    re.I,
)
# datalist whose option values are numeric person ids (primary pre-impl UX).
_SEARCH_PERSON_DATALIST_ID_VALUE = re.compile(
    r"<datalist\b[^>]{0,200}(?:people-ids|person-ids|people_ids)[^>]*>[\s\S]{0,1200}?"
    r"<option\b[^>]*\bvalue\s*=\s*\{[^}]{0,40}\b(?:p\.id|person\.id|String\s*\(\s*p\.id)",
    re.I,
)
_SEARCH_PERSON_DATALIST_ID_VALUE_LOOSE = re.compile(
    r"<datalist\b[^>]*>[\s\S]{0,1200}?"
    r"<option\b[^>]*\bvalue\s*=\s*\{\s*(?:String\s*\(\s*)?(?:p|person)\.id",
    re.I,
)
# Visible each of people (or a filtered people list) for the name picker.
_SEARCH_PERSON_EACH = re.compile(
    r"\{#each\s+(?:"
    r"people|filteredPeople|personOptions|searchPeople|filteredSearchPeople|"
    r"personMatches|personList|pickerPeople|visiblePeople|nameMatches|"
    r"filteredPerson(?:s|Options)?|personPicker(?:People|List|Options)?"
    r")\b",
    re.I,
)
# Name-facing control chrome (combobox / listbox / select / filtered list).
_SEARCH_PERSON_NAME_CONTROL = re.compile(
    r"("
    r"<(?:[A-Za-z][\w]*\.)?Combobox(?:\.Root)?\b"
    r"|role\s*=\s*[\"'](?:combobox|listbox)[\"']"
    r"|aria-autocomplete\s*="
    r"|data-person-picker"
    r"|id\s*=\s*[\"'](?:person-picker|sp-person|search-person)[\"']"
    r"|<select\b[^>]{0,400}(?:"
    rf"\bbind:value=\{{{_SEARCH_PERSON_ID_STATE}\}}"
    r"|\bid\s*=\s*[\"'](?:sp|person|search-person|person-picker)[\"']"
    r")"
    r")",
    re.I,
)
# Type-to-filter path over people display names (plain includes / fold OK).
_SEARCH_PERSON_TYPE_FILTER = re.compile(
    r"("
    r"people\.filter\s*\("
    r"|(?:filteredPeople|personOptions|searchPeople|personMatches|pickerPeople|"
    r"visiblePeople|nameMatches|filteredPerson(?:s|Options)?|"
    r"personPicker(?:People|List|Options)?)\s*="
    r"|display_name[^;\n]{0,100}\.toLowerCase"
    r"|display_name[^;\n]{0,100}\.includes"
    r"|(?:toLowerCase\s*\(\s*\)[^;\n]{0,60}includes|"
    r"includes\s*\([^)]{0,60}toLowerCase)"
    rf"|{_SEARCH_PERSON_FILTER_STATE}"
    r"|Combobox\.(?:Input|Root)|cmdk|command-input"
    r")",
    re.I,
)
# Enter to pick (first match or highlighted row).
_SEARCH_PERSON_ENTER = re.compile(
    r"("
    r"(?:key|code)\s*===?\s*[\"']Enter[\"']"
    r"|(?:on:keydown|onkeydown)(?:\|\w+)*\s*=\s*\{[^}]{0,300}Enter"
    r"|keydown[^;\n]{0,160}Enter"
    r"|case\s*[\"']Enter[\"']"
    r")",
    re.I,
)
# Enter handler must actually choose a person (not only submit Search).
_SEARCH_PERSON_ENTER_PICK = re.compile(
    rf"("
    rf"(?:key|code)\s*===?\s*[\"']Enter[\"'][\s\S]{{0,400}}"
    rf"(?:{_SEARCH_PERSON_ID_STATE}\s*="
    r"|pickPerson|selectPerson|choosePerson|setPerson|onPickPerson"
    r"|\.id\b)"
    rf"|(?:pickPerson|selectPerson|choosePerson)\s*\("
    rf"|{_SEARCH_PERSON_ID_STATE}\s*=\s*(?:p|person|match|first|hit|row|selected)\.id"
    r")",
    re.I,
)
# api.search personId flows from picker state (empty → null).
_SEARCH_API_PERSON_ARG = re.compile(
    rf"\b(?:personId|person_id)\s*:\s*([^,\n}}]+)",
    re.I,
)
_SEARCH_PERSON_STATE_FLOW = re.compile(
    rf"(?:personId|person_id)\s*:\s*(?:"
    rf"{_SEARCH_PERSON_ID_STATE}\s*\?\s*Number\s*\(\s*{_SEARCH_PERSON_ID_STATE}\s*\)"
    rf"|{_SEARCH_PERSON_ID_STATE}\s*\?\s*{_SEARCH_PERSON_ID_STATE}"
    rf"|Number\s*\(\s*{_SEARCH_PERSON_ID_STATE}\s*\)"
    rf"|{_SEARCH_PERSON_ID_STATE}\s*\|\|"
    rf"|{_SEARCH_PERSON_ID_STATE}\s*\?\?"
    rf"|{_SEARCH_PERSON_ID_STATE}\b"
    r")",
    re.I,
)
# Multi-person OR scope creep (single personId only).
_SEARCH_MULTI_PERSON_OR = re.compile(
    r"("
    r"\bpersonIds\s*:"
    r"|\bperson_ids\s*:"
    r"|\bselectedPersonIds\b"
    r"|\bpickedPersonIds\b"
    r"|\bsearchPersonIds\b"
    r"|multi(?:ple)?[-\s]?person"
    r"|person\s*OR\s*person"
    r"|any\s+of\s+(?:these\s+)?people"
    r"|multiple\s+people"
    r"|bind:value=\{[^}]{0,40}personIds"
    r"|type\s*=\s*[\"']checkbox[\"'][^>]{0,200}person"
    r")",
    re.I,
)
# Fuzzy-beyond-filter product claims (plain includes is fine; fuse.js etc. not).
_SEARCH_PERSON_FUZZY_CREEP = re.compile(
    r"("
    r"\bfuse\.js\b"
    r"|\bfuzzysort\b"
    r"|\bfuseSearch\b"
    r"|\bfuzzy(?:Match|Search|Filter)?\b"
    r"|levenshtein"
    r"|string-similarity"
    r")",
    re.I,
)


# #209 — search filters are secondary chrome; optional local date range.
_SEARCH_FILTERS_HOOK = "data-search-filters"
_SEARCH_Q_ID = re.compile(
    r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""",
    re.I,
)
_SEARCH_GRID_EQUAL = re.compile(
    r"\b(?:sm:)?grid-cols-(?:2|3|4)\b",
    re.I,
)
_SEARCH_DATE_TYPE = re.compile(
    r"""type\s*=\s*(?:["']date["']|\{\s*["']date["']\s*\})""",
    re.I,
)
_SEARCH_DATE_INPUT = re.compile(
    r"<(?:Input|input)\b[^>]*>",
    re.I | re.S,
)
_SEARCH_FROM_EMPTY_ANY = re.compile(
    r"\bfrom\s*:\s*(?:"
    r"from(?:\.trim\(\s*\))?\s*\|\|\s*(?:null|undefined)"
    r"|from(?:\.trim\(\s*\))?\s*\?\?\s*(?:null|undefined)"
    r"|from(?:\.trim\(\s*\))?\s*\?\s*from[^,}]{0,60}:\s*(?:null|undefined)"
    r"|!\s*from(?:\.trim\(\s*\))?\s*\?\s*(?:null|undefined)"
    r")",
    re.I,
)
_SEARCH_TO_EMPTY_ANY = re.compile(
    r"\bto\s*:\s*(?:"
    r"to(?:\.trim\(\s*\))?\s*\|\|\s*(?:null|undefined)"
    r"|to(?:\.trim\(\s*\))?\s*\?\?\s*(?:null|undefined)"
    r"|to(?:\.trim\(\s*\))?\s*\?\s*to[^,}]{0,60}:\s*(?:null|undefined)"
    r"|!\s*to(?:\.trim\(\s*\))?\s*\?\s*(?:null|undefined)"
    r")",
    re.I,
)
_SEARCH_DATE_CMP = re.compile(
    r"("
    r"\bfrom(?:Date|Day|Ms|Val|Iso)?\b[^;\n]{0,80}>\s*(?:to(?:Date|Day|Ms|Val|Iso)?)\b"
    r"|\bto(?:Date|Day|Ms|Val|Iso)?\b[^;\n]{0,80}<\s*(?:from(?:Date|Day|Ms|Val|Iso)?)\b"
    r")",
    re.I,
)
_SEARCH_DATE_PARSE = re.compile(
    r"("
    r"Date\.parse"
    r"|new\s+Date\s*\("
    r"|Number\.isNaN"
    r"|\bisNaN\s*\("
    r"|Invalid Date"
    r"|\\d\{4\}-\\d\{2\}-\\d\{2\}"
    r"|YYYY-MM-DD"
    r"|invalid(?:Date|Range|_date|_range)"
    r"|parse(?:Date|Day|Iso)"
    r"|unparseable"
    r")",
    re.I,
)
_SEARCH_DATE_ERROR_SET = re.compile(
    r"\bsearchError\s*=\s*(?![\s]*[\"']{2})",
)
_SEARCH_GMAIL_LABEL = re.compile(
    r"("
    r"gmail[-_ ]?label"
    r"|labelIds"
    r"|label[-_ ]?filter"
    r"|data-gmail-label"
    r")",
    re.I,
)
_SEARCH_DATEPICKER_PKG = re.compile(
    r"("
    r"\bdatepicker\b"
    r"|flatpickr"
    r"|litepicker"
    r"|pikaday"
    r"|air-datepicker"
    r"|react-datepicker"
    r"|svelte-datepicker"
    r"|vanillajs-datepicker"
    r"|daterangepicker"
    r"|@duetds/date-picker"
    r"|js-datepicker"
    r")",
    re.I,
)
_SEARCH_CDN = re.compile(
    r"("
    r"cdn\.jsdelivr"
    r"|unpkg\.com"
    r"|cdnjs"
    r"|cdn\."
    r"|https?://[^\"'\s]+datepicker"
    r")",
    re.I,
)
_DOCS_FILTERS_SECONDARY = re.compile(
    r"("
    r"filters?\s+are\s+secondary"
    r"|secondary\s+(?:chrome\s+)?filters?"
    r"|filters?\s+\([^)]{0,60}\)\s+as\s+secondary"
    r"|secondary\s+controls?"
    r")",
    re.I,
)
_DOCS_DATE_RANGE_OPTIONAL = re.compile(
    r"("
    r"optional\s+date\s+range"
    r"|date\s+range\s+is\s+optional"
    r"|optional\s+(?:local\s+)?(?:from\s*/\s*to|from/to)"
    r"|empty\s*=\s*any"
    r")",
    re.I,
)
_DOCS_INVALID_DATES = re.compile(
    r"("
    r"invalid\s+dates?\s+(?:do\s+not|don't|does\s+not|doesn't)\s+search"
    r"|invalid\s+dates?\s+(?:do\s+not|don't|does\s+not|doesn't)\s+(?:fetch|call)"
    r"|invalid\s+(?:date|from/to|from\s*/\s*to)[^\n.]{0,80}"
    r"(?:do\s+not|don't|does\s+not|doesn't|no)\s+"
    r"(?:search|fetch|invoke|api\.search)"
    r")",
    re.I,
)
_SEARCH_FILTER_TOKENS = (
    ("person", re.compile(r"data-person-picker|\bid\s*=\s*[\"']sp[\"']|personFilter", re.I)),
    ("platform", re.compile(r"\bid\s*=\s*[\"']plat[\"']|bind:value=\{platform\}", re.I)),
    ("kind", re.compile(r"\bid\s*=\s*[\"']skind[\"']|bind:value=\{conversationKind\}", re.I)),
    (
        "attachment",
        re.compile(r"\bid\s*=\s*[\"']satt[\"']|bind:value=\{attachmentFilter\}", re.I),
    ),
    ("from", re.compile(r"\bid\s*=\s*[\"']from[\"']|bind:value=\{from\}", re.I)),
    ("to", re.compile(r"\bid\s*=\s*[\"']to[\"']|bind:value=\{to\}", re.I)),
    (
        "include-groups",
        re.compile(r"includeGroups|include groups|include-groups", re.I),
    ),
)


def _search_run_surface(src: str) -> tuple[str, str]:
    """run() body and the prefix before the first api.search call."""
    body = _ts_fn_body(src, "run") or _function_body(src, "run")
    if not body:
        return "", ""
    expanded = _expand_fn_calls(src, body)
    idx = body.find("api.search")
    if idx < 0:
        return expanded, _expand_fn_calls(src, body)
    return expanded, _expand_fn_calls(src, body[:idx])


def _date_input_bound(markup: str, ident: str) -> bool:
    """True if a type=date Input/input is bound to ident (from / to)."""
    for tag in _SEARCH_DATE_INPUT.findall(markup):
        if not _SEARCH_DATE_TYPE.search(tag):
            continue
        if re.search(
            rf"bind:value={{\s*{re.escape(ident)}\s*}}|\bid\s*=\s*[\"']{re.escape(ident)}[\"']",
            tag,
            re.I,
        ):
            return True
    # type and bind may be split across multiline attributes already in the tag.
    return bool(
        re.search(
            rf"<(?:Input|input)\b[^>]{{0,500}}type\s*=\s*(?:[\"']date[\"']|{{\s*[\"']date[\"']\s*}})[^>]{{0,300}}"
            rf"(?:bind:value={{\s*{re.escape(ident)}\s*}}|\bid\s*=\s*[\"']{re.escape(ident)}[\"'])"
            rf"|<(?:Input|input)\b[^>]{{0,500}}(?:bind:value={{\s*{re.escape(ident)}\s*}}|\bid\s*=\s*[\"']{re.escape(ident)}[\"'])"
            rf"[^>]{{0,300}}type\s*=\s*(?:[\"']date[\"']|{{\s*[\"']date[\"']\s*}})",
            markup,
            re.I | re.S,
        )
    )

__all__ = [
    "_SEARCH_PERSON_ID_STATE",
    "_SEARCH_PERSON_FILTER_STATE",
    "_SEARCH_PERSON_ID_LABEL",
    "_SEARCH_PERSON_ID_FREE_TEXT",
    "_SEARCH_PERSON_DATALIST_ID_VALUE",
    "_SEARCH_PERSON_DATALIST_ID_VALUE_LOOSE",
    "_SEARCH_PERSON_EACH",
    "_SEARCH_PERSON_NAME_CONTROL",
    "_SEARCH_PERSON_TYPE_FILTER",
    "_SEARCH_PERSON_ENTER",
    "_SEARCH_PERSON_ENTER_PICK",
    "_SEARCH_API_PERSON_ARG",
    "_SEARCH_PERSON_STATE_FLOW",
    "_SEARCH_MULTI_PERSON_OR",
    "_SEARCH_PERSON_FUZZY_CREEP",
    "_SEARCH_FILTERS_HOOK",
    "_SEARCH_Q_ID",
    "_SEARCH_GRID_EQUAL",
    "_SEARCH_DATE_TYPE",
    "_SEARCH_DATE_INPUT",
    "_SEARCH_FROM_EMPTY_ANY",
    "_SEARCH_TO_EMPTY_ANY",
    "_SEARCH_DATE_CMP",
    "_SEARCH_DATE_PARSE",
    "_SEARCH_DATE_ERROR_SET",
    "_SEARCH_GMAIL_LABEL",
    "_SEARCH_DATEPICKER_PKG",
    "_SEARCH_CDN",
    "_DOCS_FILTERS_SECONDARY",
    "_DOCS_DATE_RANGE_OPTIONAL",
    "_DOCS_INVALID_DATES",
    "_SEARCH_FILTER_TOKENS",
    "_search_run_surface",
    "_date_input_bound",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_matching_each_end",
    "_search_pane_blob",
    "_svelte_markup",
    "_web_logic",
    "_without_comments",
    "_hook_element_blocks",
    "_INVENTED_SEARCH_PLATFORM_TOKENS",
    "_SEARCH_API_PLATFORM_ARG",
    "_search_platform_option_values",
    "_tag_inner",
    "annotations",
    "_expand_fn_calls",
    "_function_body",
    "_ts_fn_body",
]
