"""Additional search_filters asserts."""
from __future__ import annotations

from tauri_gate.search_filters_lib import *


def assert_search_attachment_filter(crate: Path) -> None:
    """#125: Search attachment presence is a closed <select>, not free-text.

    Options: empty/any + has_file + omitted + missing. Empty value means any and
    is sent as null/empty to api.search (attachmentFilter / attachment_filter).
    Labels: Any | Has file | Omitted | Missing. Not: MIME taxonomy, video-only.
    Keep #121–#124 search chrome.
    """
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#125: SearchPane.svelte required (search attachment control lives there)")
    src = _search_pane_blob(crate)
    cleaned = _without_comments(src)
    markup = _svelte_markup(src)
    surface = markup if markup.strip() else src
    whole = cleaned

    # 1) api.search must receive attachmentFilter / attachment_filter from select state.
    api_m = _SEARCH_API_PLATFORM_ARG.search(whole)
    if not api_m:
        if not re.search(r"api\.search\s*\(", whole):
            fail("#125: SearchPane must call api.search")
        if not re.search(r"\b(?:attachmentFilter|attachment_filter)\s*:", whole):
            fail(
                "#125: api.search must receive attachmentFilter / attachment_filter "
                "from the select (attachmentFilter: … in the search args)"
            )
        api_args = whole
    else:
        api_args = api_m.group(1)
        if not re.search(r"\b(?:attachmentFilter|attachment_filter)\s*:", api_args):
            fail(
                "#125: api.search must receive attachmentFilter / attachment_filter "
                "from the select (attachmentFilter: … in the search args)"
            )

    att_arg_m = _SEARCH_API_ATTACHMENT_ARG.search(api_args)
    att_arg = (att_arg_m.group(1).strip() if att_arg_m else "") or ""
    if att_arg and re.fullmatch(
        r"[\"'](?:" + "|".join(sorted(_INVENTED_SEARCH_ATTACHMENT_TOKENS)) + r")[\"']",
        att_arg,
        re.I,
    ):
        fail(
            "#125: api.search attachment filter must come from the select state, "
            "not a hard-coded invented token"
        )
    if att_arg and re.fullmatch(r"[\"'](?:has_file|omitted|missing)[\"']", att_arg, re.I):
        fail(
            "#125: api.search attachment filter must be user-selected from the control, "
            "not hard-coded to a single value"
        )
    if not _SEARCH_ATTACHMENT_STATE_FLOW.search(api_args) and not _SEARCH_ATTACHMENT_STATE_FLOW.search(
        whole
    ):
        fail(
            "#125: api.search attachment filter must read the select state "
            "(e.g. attachmentFilter: attachmentFilter || null) — not a bare null / ignored control"
        )

    # 2) Fail free-text Input/textbox for attachment (invalid tokens typable).
    if _SEARCH_ATTACHMENT_FREE_TEXT.search(surface) or _SEARCH_ATTACHMENT_FREE_TEXT.search(src):
        fail(
            "#125: search attachment filter must not be a free-text Input/textbox "
            "(invalid tokens cannot be typed — use a closed <select>)"
        )
    if re.search(
        r"(?:Attachment|>\s*Has\s*file\s*<|for\s*=\s*[\"'](?:satt|att|attachment)[\"'])",
        surface,
        re.I,
    ) and re.search(
        r"<Input\b|<input\b(?![^>]*\btype\s*=\s*[\"'](?:hidden|checkbox|radio)[\"'])",
        surface,
        re.I,
    ):
        for m in re.finditer(
            r"(?:Attachment|>\s*Has\s*file\s*<|for\s*=\s*[\"'](?:satt|att|attachment)[\"'])",
            surface,
            re.I,
        ):
            window = surface[m.start() : m.start() + 400]
            if re.search(
                rf"<Input\b[^>]{{0,200}}(?:att|attachment)|"
                rf"<input\b[^>]{{0,200}}(?:att|attachment)|"
                rf"bind:value=\{{{_SEARCH_ATTACHMENT_STATE}\}}",
                window,
                re.I,
            ) and not re.search(r"<select\b|Select\.Root|SelectItem", window, re.I):
                fail(
                    "#125: search attachment filter must not be a free-text Input/textbox "
                    "(invalid tokens cannot be typed — use a closed <select>)"
                )

    # 3) Closed control: <select> (or equivalent) bound to attachment state.
    has_select = bool(_SEARCH_ATTACHMENT_SELECT.search(surface)) or bool(
        _SEARCH_ATTACHMENT_SELECT.search(src)
    )
    if not has_select:
        att_label = re.search(
            r"(?:for\s*=\s*[\"'](?:satt|att|attachment|attachment-filter)[\"']"
            r"|>\s*Attachment\s*<"
            r"|id\s*=\s*[\"'](?:satt|att|attachment|attachment-filter)[\"'])",
            surface,
            re.I,
        )
        if att_label:
            window = surface[att_label.start() : att_label.start() + 800]
            has_select = bool(re.search(r"<select\b", window, re.I)) or bool(
                re.search(r"<(?:[A-Za-z][\w]*\.)?Select(?:\.Root)?\b", window, re.I)
            )
    if not has_select:
        fail(
            "#125: search attachment filter must be a closed <select> "
            "(or equivalent Select control) with fixed options — not free text"
        )

    # 4) Options: empty/any + has_file + omitted + missing; only those tokens.
    option_region = surface
    sel = re.search(
        rf"<select\b[^>]{{0,400}}(?:\bbind:value=\{{{_SEARCH_ATTACHMENT_STATE}\}}"
        rf"|\bid\s*=\s*[\"'](?:satt|att|attachment|attachment-filter)[\"'])"
        rf"[^>]*>[\s\S]{{0,2000}}?</select>",
        surface,
        re.I,
    )
    if not sel:
        sel = re.search(
            r"(?:for\s*=\s*[\"'](?:satt|att|attachment|attachment-filter)[\"']"
            r"|>\s*Attachment\s*<)[\s\S]{0,200}"
            r"<select\b[^>]*>[\s\S]{0,2000}?</select>",
            surface,
            re.I,
        )
    if sel:
        option_region = sel.group(0)

    values = _search_platform_option_values(option_region)
    if not values:
        if sel:
            values = _search_platform_option_values(surface)

    norm = [v.strip() for v in values]
    lower = [v.lower() for v in norm]

    if "" not in norm:
        fail(
            "#125: attachment <select> must include an empty-value option for Any "
            '(value="" — empty means any; do not send a literal "any" token)'
        )
    if "has_file" not in lower:
        fail("#125: attachment <select> must offer has_file (label: Has file)")
    if "omitted" not in lower:
        fail("#125: attachment <select> must offer omitted")
    if "missing" not in lower:
        fail("#125: attachment <select> must offer missing")

    for v in lower:
        if v == "":
            continue
        if v in _INVENTED_SEARCH_ATTACHMENT_TOKENS:
            fail(
                f"#125: do not invent search attachment option {v!r} "
                "(only: has_file, omitted, missing — no MIME/video-only taxonomy)"
            )
        if v not in _CORE_SEARCH_ATTACHMENT_TOKENS:
            if v in {"any", "all"}:
                fail(
                    "#125: Any/all must use empty value=\"\" "
                    "(core has no \"any\" attachment_filter token — empty means any)"
                )
            fail(
                f"#125: attachment option value {v!r} is not accepted "
                "(allowed: has_file, omitted, missing; empty = any; no MIME/video-only)"
            )

    # 5) Empty value means any → null/empty from select state to api.search.
    if not _SEARCH_ATTACHMENT_EMPTY_AS_ANY.search(whole):
        fail(
            "#125: empty attachment filter must mean any "
            "(send null/empty from select state — e.g. attachmentFilter: attachmentFilter || null)"
        )

    # Default state should be empty/any, not a forced filter.
    if re.search(
        rf"\b(?:let|const|var)\s+{_SEARCH_ATTACHMENT_STATE}\s*=\s*\$state\s*\(\s*[\"']"
        r"(?:has_file|omitted|missing|"
        + "|".join(re.escape(t) for t in sorted(_INVENTED_SEARCH_ATTACHMENT_TOKENS))
        + r")[\"']\s*\)",
        whole,
        re.I,
    ) or re.search(
        rf"\b{_SEARCH_ATTACHMENT_STATE}\s*=\s*\$state\s*\(\s*[\"']"
        r"(?:has_file|omitted|missing)[\"']\s*\)",
        whole,
        re.I,
    ):
        fail(
            "#125: attachment filter state must default to empty/any "
            "(not pre-selected to a single value)"
        )

    # 6) No MIME / video-only option tokens anywhere in SearchPane surface for this control.
    banned_opt = re.search(
        r"<option\b[^>]*\bvalue\s*=\s*[\"'](?:video(?:_only)?|image(?:_only)?|mime|media|"
        r"has[_:]?media|audio(?:_only)?|sticker|voice|pdf)[\"']",
        surface,
        re.I,
    )
    if banned_opt:
        fail(
            f"#125: not in scope — MIME/video-only attachment options "
            f"(found {banned_opt.group(0)!r}); only has_file / omitted / missing"
        )

    # 7) Keep #121–#124 search chrome.
    if not re.search(r"\bplatform\b", whole) or not re.search(r"<select\b", surface, re.I):
        fail("#125: keep the search platform <select> (#121) when adding attachment filter")
    if not re.search(r"conversationKind|conversation_kind", whole):
        fail(
            "#125: keep the search conversation-kind <select> (#122) when adding attachment filter"
        )
    if not re.search(r"personId|person_id|personFilter|data-person-picker", whole):
        fail("#125: keep the search person picker (#123) when adding attachment filter")
    # Jump path may live in App; SearchPane must still list activatable hits.
    if not re.search(r"\{#each\s+hits\b", surface) and not re.search(
        r"\{#each\s+hits\b", src
    ):
        fail("#125: keep search hits list (#124 jump chrome) when adding attachment filter")
