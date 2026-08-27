"""Search person picker / secondary filters asserts. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.search_picker_lib import *


def assert_search_person_picker(crate: Path) -> None:
    """#123: search person is a name-facing combobox/list, not free-text Person id.

    Same people source as the sidebar (people prop). Selecting stores person_id
    for api.search({ personId }). Keyboard required: type-to-filter display names
    AND Enter to pick (first match or highlighted). Clear = no person filter.
    Fail free-text “Person id” + datalist of numeric ids as primary UX.
    Not: multi-person OR, fuzzy name search beyond plain list filter.
    """
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#123: SearchPane.svelte required (search person picker lives there)")
    src = _search_pane_blob(crate)
    cleaned = _without_comments(src)
    markup = _svelte_markup(src)
    surface = markup if markup.strip() else src
    whole = cleaned

    # 1) Reject free-text id-only UX (current pre-impl SearchPane). Prefer this
    # as the red gate so the fix target is obvious before positive checks.
    if _SEARCH_PERSON_ID_LABEL.search(surface) or _SEARCH_PERSON_ID_LABEL.search(src):
        fail(
            "#123: search person must not be labeled “Person id” — "
            "use a name-facing picker (combobox / filtered list of display names); "
            "store person_id underneath for api.search"
        )
    if _SEARCH_PERSON_DATALIST_ID_VALUE.search(surface) or _SEARCH_PERSON_DATALIST_ID_VALUE.search(
        src
    ) or _SEARCH_PERSON_DATALIST_ID_VALUE_LOOSE.search(surface) or _SEARCH_PERSON_DATALIST_ID_VALUE_LOOSE.search(
        src
    ):
        fail(
            "#123: datalist of numeric person ids is not a name picker "
            "(option value = p.id / String(p.id) forces users to know the id). "
            "Show display names; keep person_id only as the stored value"
        )
    if _SEARCH_PERSON_ID_FREE_TEXT.search(surface) or _SEARCH_PERSON_ID_FREE_TEXT.search(src):
        # Allow type=hidden storage of the id next to a name-facing control.
        hidden_only = True
        for m in _SEARCH_PERSON_ID_FREE_TEXT.finditer(surface + "\n" + src):
            tag = m.group(0)
            if not re.search(r"type\s*=\s*[\"']hidden[\"']", tag, re.I):
                hidden_only = False
                break
        if not hidden_only:
            fail(
                "#123: search person must not be a free-text Input bound to personId "
                "(users must not type a numeric id). Use a name-facing combobox / "
                "filtered list; personId stays under the hood"
            )

    # 2) api.search must still receive personId from picker state when chosen.
    api_m = _SEARCH_API_PLATFORM_ARG.search(whole)
    if not api_m:
        if not re.search(r"api\.search\s*\(", whole):
            fail("#123: SearchPane must call api.search")
        if not re.search(r"\b(?:personId|person_id)\s*:", whole):
            fail(
                "#123: api.search must receive personId when a person is chosen "
                "(personId: … in the search args; null/empty when cleared)"
            )
        api_args = whole
    else:
        api_args = api_m.group(1)
        if not re.search(r"\b(?:personId|person_id)\s*:", api_args):
            fail(
                "#123: api.search must receive personId when a person is chosen "
                "(personId: … in the search args; null/empty when cleared)"
            )

    person_arg_m = _SEARCH_API_PERSON_ARG.search(api_args)
    person_arg = (person_arg_m.group(1).strip() if person_arg_m else "") or ""
    if person_arg and re.fullmatch(r"\d+", person_arg):
        fail(
            "#123: api.search personId must come from the picker state, "
            "not a hard-coded numeric id"
        )
    if person_arg and re.fullmatch(r"null|undefined", person_arg, re.I):
        # Bare null with no state read means the picker is ignored.
        if not _SEARCH_PERSON_STATE_FLOW.search(api_args) and not _SEARCH_PERSON_STATE_FLOW.search(
            whole
        ):
            fail(
                "#123: api.search personId must read picker state "
                "(e.g. personId: personId ? Number(personId) : null) — "
                "not a bare null / ignored control"
            )
    if not _SEARCH_PERSON_STATE_FLOW.search(api_args) and not _SEARCH_PERSON_STATE_FLOW.search(
        whole
    ):
        fail(
            "#123: api.search personId must read picker state "
            "(e.g. personId: personId ? Number(personId) : null) — "
            "not a decorative control"
        )

    # 3) Name-facing picker: list/combobox of display names from people prop.
    has_people_prop = bool(
        re.search(r"\bpeople\b", whole)
        and re.search(r"people\s*:\s*Person\[\]|\{[^}]*\bpeople\b[^}]*\}", whole)
    ) or bool(re.search(r"\bpeople\b", src))
    if not has_people_prop:
        fail(
            "#123: SearchPane must take the same people list as the sidebar "
            "(people prop) for the name picker"
        )

    has_each = bool(_SEARCH_PERSON_EACH.search(surface) or _SEARCH_PERSON_EACH.search(src))
    # {#each people as p} is the minimum source loop.
    if not has_each and not re.search(r"\{#each\s+people\b", surface):
        fail(
            "#123: person picker must iterate people (or a filtered people list) "
            "so display names can be chosen — same source as the sidebar"
        )

    # display_name must appear as the visible label (not only as datalist text
    # beside value=id — already rejected above).
    picker_region = surface
    each_m = _SEARCH_PERSON_EACH.search(surface) or re.search(r"\{#each\s+people\b", surface)
    if each_m:
        end = _matching_each_end(surface, each_m.start())
        picker_region = surface[each_m.start() : end if end > 0 else each_m.start() + 800]
    if not re.search(r"\bdisplay_name\b", picker_region) and not re.search(
        r"\bdisplay_name\b", surface
    ):
        fail(
            "#123: person picker must show display_name (name-facing), "
            "not raw person ids as the primary label"
        )
    # Visible text node / binding of the name in the each body.
    if each_m and not re.search(
        r"\{[^}]{0,80}display_name[^}]{0,40}\}|display_name\s*\}",
        picker_region,
    ):
        # Allow personLabel(p) / format helpers that read display_name in script.
        if not re.search(
            r"(?:personLabel|displayName|formatPerson|personName)\s*\(",
            surface + "\n" + whole,
        ):
            fail(
                "#123: person picker list/options must present display_name to the user "
                "(search “messages with Ada” without knowing her id)"
            )

    has_name_control = bool(
        _SEARCH_PERSON_NAME_CONTROL.search(surface)
        or _SEARCH_PERSON_NAME_CONTROL.search(src)
        or re.search(
            rf"bind:value=\{{{_SEARCH_PERSON_FILTER_STATE}\}}",
            surface,
        )
        or re.search(
            r"<(?:ul|ol|div|menu)\b[^>]{0,200}(?:person-picker|person-options|people-picker)",
            surface,
            re.I,
        )
    )
    # Filtered list with clickable name rows counts even without combobox role.
    has_pick_action = bool(
        re.search(
            r"(?:onclick|on:click)(?:\|\w+)*\s*=\s*\{[^}]{0,200}"
            rf"(?:{_SEARCH_PERSON_ID_STATE}\s*="
            r"|pickPerson|selectPerson|choosePerson|onPickPerson)",
            surface,
            re.I,
        )
        or re.search(
            rf"{_SEARCH_PERSON_ID_STATE}\s*=\s*(?:p|person|match|row)\.id",
            whole,
        )
    )
    if not has_name_control and not has_pick_action:
        fail(
            "#123: require a name-facing person control "
            "(combobox / select / filtered list of display names with pick action) — "
            "not free-text id entry"
        )

    # 4) Keyboard: type-to-filter display names AND Enter to pick.
    # Required (issue): type to filter, Enter to pick first/highlighted.
    # bits-ui / role=combobox may supply both without an explicit key===Enter
    # handler in app code — accept that as the keyboard path.
    has_combobox_widget = bool(
        re.search(
            r"<(?:[A-Za-z][\w]*\.)?Combobox(?:\.Root|\.Input)?\b"
            r"|role\s*=\s*[\"']combobox[\"']"
            r"|aria-autocomplete\s*=",
            surface,
            re.I,
        )
        or re.search(
            r"<(?:[A-Za-z][\w]*\.)?Combobox(?:\.Root|\.Input)?\b",
            whole,
            re.I,
        )
    )
    has_type_filter = bool(
        _SEARCH_PERSON_TYPE_FILTER.search(whole) or _SEARCH_PERSON_TYPE_FILTER.search(surface)
    )
    if not has_type_filter and not has_combobox_widget:
        fail(
            "#123: keyboard path requires type-to-filter on display names "
            "(people.filter / includes / personFilter — plain case-insensitive "
            "substring is fine; same spirit as the sidebar filter). "
            "A Combobox widget also counts"
        )
    has_enter = bool(
        _SEARCH_PERSON_ENTER.search(whole) or _SEARCH_PERSON_ENTER.search(surface)
    )
    has_enter_pick = bool(
        _SEARCH_PERSON_ENTER_PICK.search(whole) or _SEARCH_PERSON_ENTER_PICK.search(surface)
    )
    if not has_combobox_widget:
        if not has_enter:
            fail(
                "#123: keyboard path requires Enter to pick "
                "(first match or highlighted row — key === \"Enter\" / onkeydown Enter). "
                "A Combobox widget’s built-in Enter also counts"
            )
        if not has_enter_pick:
            # Enter might only submit the Search form — require a pick path.
            fail(
                "#123: Enter on the person control must pick a person "
                "(set personId / pickPerson from the filtered list), "
                "not only submit the search form"
            )

    # 5) Forbid multi-person OR and fuzzy-beyond-list-filter scope creep.
    if _SEARCH_MULTI_PERSON_OR.search(whole) or _SEARCH_MULTI_PERSON_OR.search(surface):
        # type=checkbox for include groups is fine; only fail person multi-select.
        multi = _SEARCH_MULTI_PERSON_OR.search(whole) or _SEARCH_MULTI_PERSON_OR.search(surface)
        snippet = multi.group(0) if multi else ""
        if re.search(r"includeGroups|include groups", snippet, re.I):
            pass
        else:
            fail(
                "#123: not in scope — multi-person OR / personIds multi-select "
                f"(found {snippet!r}). Single person_id filter only"
            )
    if _SEARCH_PERSON_FUZZY_CREEP.search(whole) or _SEARCH_PERSON_FUZZY_CREEP.search(src):
        fail(
            "#123: not in scope — fuzzy name search beyond the existing list filter "
            "(plain case-insensitive includes / fold is enough)"
        )

    # 6) Keep platform (#121) and kind (#122) selects present.
    if not re.search(r"\bplatform\b", whole) or not re.search(r"<select\b", surface, re.I):
        fail("#123: keep the search platform <select> (#121) when adding the person picker")
    if not re.search(r"conversationKind|conversation_kind", whole):
        fail(
            "#123: keep the search conversation-kind <select> (#122) when adding the person picker"
        )


def assert_search_filters_secondary(crate: Path) -> None:
    """#209: filters are secondary chrome; optional local date range.

    `#q` is the first / primary control. Person / platform / kind /
    attachment / dates / include-groups live under `data-search-filters`
    (muted one-row strip or <details> disclosure) — not equal-weight grid
    siblings of `#q`. Platform / kind / attachment stay closed <select>s.
    Date range is two local type="date" inputs (empty = any). run() must
    not call api.search when from/to is unparseable or from > to; calm
    error via data-partial or existing searchError chrome. No CDN/npm
    datepicker, no Gmail labels, no invented platforms. Docs: filters
    secondary + optional date range; invalid dates do not search.
    Keep #121–#126 / #205 / #208.
    """
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#209: SearchPane.svelte required (filters + date range live there)")
    src = _search_pane_blob(crate)
    cleaned = _without_comments(src)
    markup = _svelte_markup(src)
    surface = markup if markup.strip() else src
    app_path = crate / "web" / "App.svelte"
    app = _web_logic(crate) if app_path.is_file() else ""
    pkg_path = crate / "package.json"
    pkg = pkg_path.read_text() if pkg_path.is_file() else ""
    docs_search = repo_root() / "docs" / "user" / "search.md"
    docs_app = repo_root() / "docs" / "user" / "app.md"
    dtxt = ""
    if docs_search.is_file():
        dtxt += docs_search.read_text() + "\n"
    if docs_app.is_file():
        dtxt += docs_app.read_text()

    # 1) #q is the first / primary search control.
    q_m = _SEARCH_Q_ID.search(surface)
    if not q_m:
        fail("#209: SearchPane must keep id=\"q\" as the first / primary query control")

    # 2) Filters must be demoted — not equal-weight grid siblings of #q.
    #    Documented hook: data-search-filters (muted strip or <details>).
    hook_blocks = _hook_element_blocks(surface, _SEARCH_FILTERS_HOOK)
    hook_blob = "\n".join(hook_blocks)
    q_in_hook = bool(hook_blocks) and any(_SEARCH_Q_ID.search(b) for b in hook_blocks)
    missing: list[str] = []
    for name, rx in _SEARCH_FILTER_TOKENS:
        if hook_blob and rx.search(hook_blob):
            continue
        if not hook_blob:
            missing.append(name)
        elif not rx.search(hook_blob):
            missing.append(name)
    hook_pos = surface.find(_SEARCH_FILTERS_HOOK)
    q_before_hook = hook_pos < 0 or q_m.start() < hook_pos

    form_shares_grid = False
    for form in _tag_inner(surface, "form"):
        open_end = form.find(">")
        form_tag = form[: open_end + 1] if open_end >= 0 else form[:200]
        if not _SEARCH_Q_ID.search(form):
            continue
        if _SEARCH_GRID_EQUAL.search(form_tag) and (
            not hook_blocks or q_in_hook or missing
        ):
            form_shares_grid = True
            break

    if (
        not hook_blocks
        or q_in_hook
        or not q_before_hook
        or missing
        or form_shares_grid
    ):
        fail(
            "#209: SearchPane filters still share the same equal-weight grid as #q "
            "(form is grid / sm:grid-cols-2). Query #q must be the first / primary "
            "control (full width, above filters). Person / platform / kind / "
            "attachment / dates / include-groups live under data-search-filters "
            "(muted one-row strip or <details> disclosure) — not equal-weight "
            "siblings of #q"
        )

    # 3) Hook is visually secondary (disclosure or muted / one-row strip).
    is_disclosure = bool(re.search(r"<details\b|<summary\b|disclosure", hook_blob, re.I))
    is_muted = bool(
        re.search(r"muted-foreground|text-muted|\bopacity-|text-xs", hook_blob, re.I)
    )
    is_row = bool(re.search(r"\bflex\b", hook_blob, re.I))
    if not (is_disclosure or is_muted or is_row):
        fail(
            "#209: data-search-filters must be a muted one-row strip or a "
            "<details> disclosure — not another equal-weight grid next to #q"
        )

    # 4) Platform / kind / attachment stay closed <select>s (Any + existing tokens).
    if not re.search(
        r"<select\b[^>]{0,400}(?:\bbind:value=\{platform\}|\bid\s*=\s*[\"']plat[\"'])",
        surface,
        re.I,
    ):
        fail(
            "#209: keep the search platform closed <select> (#121) — "
            "Any + existing tokens only; do not invent platforms"
        )
    if not re.search(
        r"<select\b[^>]{0,400}(?:\bbind:value=\{conversationKind\}|\bid\s*=\s*[\"']skind[\"'])",
        surface,
        re.I,
    ):
        fail(
            "#209: keep the search kind closed <select> (#122) — "
            "Any + dm / group / email_thread"
        )
    if not re.search(
        r"<select\b[^>]{0,400}(?:\bbind:value=\{attachmentFilter\}|\bid\s*=\s*[\"']satt[\"'])",
        surface,
        re.I,
    ):
        fail(
            "#209: keep the search attachment closed <select> (#125) — "
            "Any + has_file / omitted / missing"
        )
    opt_values = _search_platform_option_values(hook_blob or surface)
    for v in opt_values:
        low = (v or "").strip().lower()
        if low in _INVENTED_SEARCH_PLATFORM_TOKENS:
            fail(
                f"#209: do not invent search platform option {v!r} "
                "(no twitter/slack/…; keep core tokens only)"
            )

    # 5) Date range: two local type="date" inputs. Empty = any.
    if not _date_input_bound(surface, "from") or not _date_input_bound(surface, "to"):
        fail(
            "#209: date range must be two local <input type=\"date\"> "
            "(or Input type=\"date\") bound to from / to. Empty = any. "
            "No ISO text boxes"
        )

    api_m = _SEARCH_API_PLATFORM_ARG.search(cleaned)
    api_args = api_m.group(1) if api_m else cleaned
    if not re.search(r"\bfrom\s*:", api_args) or not re.search(r"\bto\s*:", api_args):
        fail(
            "#209: SearchPane run() must still wire from / to into api.search "
            "(empty = any / null)"
        )
    if not _SEARCH_FROM_EMPTY_ANY.search(api_args) or not _SEARCH_TO_EMPTY_ANY.search(
        api_args
    ):
        fail(
            "#209: empty from / to must mean any (null/empty to api.search) — "
            "do not send a blank string as a date bound"
        )

    # 6) Invalid dates (unparseable or from > to) must not call api.search.
    run_all, run_before = _search_run_surface(cleaned)
    if not run_all:
        fail("#209: SearchPane run() required (submit / Retry path)")
    if "api.search" not in run_all:
        fail("#209: SearchPane run() must remain the api.search caller")
    has_cmp = bool(_SEARCH_DATE_CMP.search(run_before) or _SEARCH_DATE_CMP.search(run_all))
    has_parse = bool(
        _SEARCH_DATE_PARSE.search(run_before) or _SEARCH_DATE_PARSE.search(run_all)
    )
    has_early = bool(re.search(r"\breturn\b", run_before))
    has_guarded = bool(
        re.search(
            r"(?:if\s*\([^)]{0,160}(?:valid|ok|invalid|date|from|to)[^)]{0,160}\)"
            r"[\s\S]{0,240}api\.search"
            r"|else\s*\{[\s\S]{0,240}api\.search)",
            run_all,
            re.I,
        )
    )
    has_err = bool(_SEARCH_DATE_ERROR_SET.search(run_before))
    if not has_parse or not has_cmp or not (has_early or has_guarded) or not has_err:
        fail(
            "#209: run() must not call api.search when from/to is invalid "
            "(unparseable or from > to). Show a calm in-pane error "
            "(data-partial or existing searchError chrome) and return / skip "
            "the fetch"
        )
    if not re.search(r"\bdata-partial\b|\bsearchError\b", surface):
        fail(
            "#209: invalid dates need a calm in-pane error "
            "(data-partial or existing searchError chrome) — not only showErr"
        )

    # 7) No CDN / npm / remote datepicker.
    pane_deps = src + "\n" + pkg
    if _SEARCH_CDN.search(src) or _SEARCH_DATEPICKER_PKG.search(pane_deps):
        fail(
            "#209: no CDN / npm / remote datepicker in SearchPane "
            "(use native type=\"date\" only)"
        )

    # 8) No Gmail label filter / invented platforms (already scanned options).
    if _SEARCH_GMAIL_LABEL.search(cleaned) or _SEARCH_GMAIL_LABEL.search(surface):
        fail("#209: not in scope — no Gmail label filter")

    # 9) Docs: filters secondary + optional date range; invalid dates do not search.
    if not _DOCS_FILTERS_SECONDARY.search(dtxt):
        fail(
            "#209: docs/user/search.md and/or docs/user/app.md must say "
            "search filters are secondary"
        )
    if not _DOCS_DATE_RANGE_OPTIONAL.search(dtxt):
        fail(
            "#209: docs/user/search.md and/or docs/user/app.md must say "
            "the date range is optional (empty = any)"
        )
    if not _DOCS_INVALID_DATES.search(dtxt):
        fail(
            "#209: docs/user/search.md and/or docs/user/app.md must say "
            "invalid dates do not search"
        )

    # 10) Do not soften #121–#126 / #205 / #208.
    if not re.search(r"\{#each\s+hits\b", surface) and not re.search(
        r"\{#each\s+hits\b", src
    ):
        fail("#209: keep search hits list (#124 jump chrome)")
    if not re.search(r"<mark\b", surface, re.I):
        fail("#209: keep search snippet <mark> highlight (#126)")
    if not re.search(r"data-person-picker|personFilter|personId", cleaned):
        fail("#209: keep the search person picker (#123)")
    if not re.search(r"\bdata-partial\b", surface):
        fail("#209: keep search data-partial Error+Retry (#205)")
    if not re.search(r"\bdata-chrome-search\b", app):
        fail("#209: keep chrome search field data-chrome-search (#208)")
    if re.search(r"\bapi\.search\s*\(", app_path.read_text() if app_path.is_file() else ""):
        fail(
            "#209: App.svelte must not call api.search — SearchPane run() stays "
            "the only caller (#208)"
        )
