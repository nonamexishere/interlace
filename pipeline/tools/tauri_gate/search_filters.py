"""Search platform / kind / attachment filter asserts. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.search_filters_lib import *


def assert_search_platform_select(crate: Path) -> None:
    """#121: Search platform is a closed <select>, not free-text.

    Options: empty/any + whatsapp + gmail (core tokens). Empty value means any
    and is sent as null/empty to api.search from select state. Invalid tokens
    cannot be typed. contacts may appear (existing core + Tauri parse); do not
    invent twitter/slack/… or offer owner unless parse_platform accepts it.
    Not: new platforms, regex platform matching.
    """
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#121: SearchPane.svelte required (search platform control lives there)")
    src = _search_pane_blob(crate)
    cleaned = _without_comments(src)
    markup = _svelte_markup(src)
    # Prefer markup; fall back to whole file for script-only option lists.
    surface = markup if markup.strip() else src
    whole = cleaned

    # 1) Must still call api.search with a platform arg (filter reaches core).
    api_m = _SEARCH_API_PLATFORM_ARG.search(whole)
    if not api_m:
        # Multiline / nested — looser fallback.
        if not re.search(r"api\.search\s*\(", whole):
            fail("#121: SearchPane must call api.search")
        if not re.search(r"\bplatform\s*:", whole):
            fail(
                "#121: api.search must receive platform from the select "
                "(platform: … in the search args)"
            )
        api_args = whole
    else:
        api_args = api_m.group(1)
        if not re.search(r"\bplatform\s*:", api_args):
            fail(
                "#121: api.search must receive platform from the select "
                "(platform: … in the search args)"
            )

    plat_arg_m = _SEARCH_PLATFORM_ARG.search(api_args)
    plat_arg = (plat_arg_m.group(1).strip() if plat_arg_m else "") or ""
    if plat_arg and re.fullmatch(
        r"[\"'](?:" + "|".join(sorted(_INVENTED_SEARCH_PLATFORM_TOKENS)) + r")[\"']",
        plat_arg,
        re.I,
    ):
        fail(
            "#121: api.search platform must come from the select state, "
            "not a hard-coded invented token"
        )
    if plat_arg and re.fullmatch(r"[\"'](?:whatsapp|gmail|contacts|owner)[\"']", plat_arg, re.I):
        fail(
            "#121: api.search platform must be user-selected from the control, "
            "not hard-coded to a single platform"
        )
    # Must flow from select state (platform: platform …), not bare null only.
    if not _SEARCH_PLATFORM_STATE_FLOW.search(api_args) and not _SEARCH_PLATFORM_STATE_FLOW.search(
        whole
    ):
        fail(
            "#121: api.search platform must read the select state "
            "(e.g. platform: platform || null) — not a bare null / ignored control"
        )

    # 2) Fail free-text Input/textbox for platform (invalid tokens typable).
    if _SEARCH_PLATFORM_FREE_TEXT.search(surface) or _SEARCH_PLATFORM_FREE_TEXT.search(src):
        fail(
            "#121: search platform must not be a free-text Input/textbox "
            "(invalid tokens cannot be typed — use a closed <select>)"
        )
    # Platform label + Input nearby without a select is also free-text.
    if re.search(r"Platform", surface, re.I) and re.search(
        r"<Input\b|<input\b(?![^>]*\btype\s*=\s*[\"'](?:hidden|checkbox|radio)[\"'])",
        surface,
        re.I,
    ):
        # Only fail when the free-text sits in the platform field region.
        for m in re.finditer(r"Platform", surface, re.I):
            window = surface[m.start() : m.start() + 400]
            if re.search(
                r"<Input\b[^>]{0,200}(?:platform|plat)|"
                r"<input\b[^>]{0,200}(?:platform|plat)|"
                r"bind:value=\{platform\}",
                window,
                re.I,
            ) and not re.search(r"<select\b|Select\.Root|SelectItem", window, re.I):
                fail(
                    "#121: search platform must not be a free-text Input/textbox "
                    "(invalid tokens cannot be typed — use a closed <select>)"
                )

    # 3) Closed control: <select> (or equivalent) bound to platform.
    has_select = bool(_SEARCH_PLATFORM_SELECT.search(surface)) or bool(
        _SEARCH_PLATFORM_SELECT.search(src)
    )
    # Also accept a plain <select> whose options carry core tokens next to Platform.
    if not has_select:
        plat_label = re.search(
            r"(?:for\s*=\s*[\"']plat[\"']|>\s*Platform\s*<|id\s*=\s*[\"']plat[\"'])",
            surface,
            re.I,
        )
        if plat_label:
            window = surface[plat_label.start() : plat_label.start() + 800]
            has_select = bool(re.search(r"<select\b", window, re.I)) or bool(
                re.search(r"<(?:[A-Za-z][\w]*\.)?Select(?:\.Root)?\b", window, re.I)
            )
    if not has_select:
        fail(
            "#121: search platform must be a closed <select> "
            "(or equivalent Select control) with fixed options — not free text"
        )

    # 4) Options: empty/any + whatsapp + gmail; only core tokens.
    # Narrow to the platform <select>…</select> when present.
    option_region = surface
    sel = re.search(
        r"<select\b[^>]{0,400}(?:\bbind:value=\{platform\}|\bid\s*=\s*[\"']plat[\"'])"
        r"[^>]*>[\s\S]{0,2000}?</select>",
        surface,
        re.I,
    )
    if not sel:
        sel = re.search(
            r"(?:for\s*=\s*[\"']plat[\"']|>\s*Platform\s*<)[\s\S]{0,200}"
            r"<select\b[^>]*>[\s\S]{0,2000}?</select>",
            surface,
            re.I,
        )
    if sel:
        option_region = sel.group(0)

    values = _search_platform_option_values(option_region)
    # Fallback: any option values in SearchPane markup if region parse missed.
    if not values:
        values = _search_platform_option_values(surface)

    norm = [v.strip() for v in values]
    lower = [v.lower() for v in norm]

    if "" not in norm:
        # Empty value required for “any”. value="any"/"all" alone is not enough.
        fail(
            "#121: platform <select> must include an empty-value option for Any "
            '(value="" — empty means any; do not send a literal "any" token)'
        )

    if "whatsapp" not in lower:
        fail(
            "#121: platform <select> must offer whatsapp "
            "(core token; issue: Any | whatsapp | gmail)"
        )
    if "gmail" not in lower:
        fail(
            "#121: platform <select> must offer gmail "
            "(core token; issue: Any | whatsapp | gmail)"
        )

    for v in lower:
        if v == "":
            continue
        if v in _INVENTED_SEARCH_PLATFORM_TOKENS:
            fail(
                f"#121: do not invent search platform option {v!r} "
                "(only core tokens: whatsapp, gmail, and optionally contacts)"
            )
        if v not in _CORE_SEARCH_PLATFORM_TOKENS:
            # Labels like "Any" must not appear as non-empty values.
            if v in {"any", "all"}:
                fail(
                    "#121: Any/all must use empty value=\"\" (core has no \"any\" platform "
                    "token — empty means any)"
                )
            fail(
                f"#121: platform option value {v!r} is not accepted by search "
                "(allowed: whatsapp, gmail, contacts; empty = any; no owner unless IPC accepts it)"
            )

    # 5) Empty value means any → null/empty from select state to api.search.
    if not _SEARCH_PLATFORM_EMPTY_AS_ANY.search(whole):
        fail(
            "#121: empty platform must mean any "
            "(send null/empty from select state — e.g. platform: platform || null)"
        )

    # Default state should be empty/any, not a forced platform.
    if re.search(
        r"\b(?:let|const|var)\s+platform\s*=\s*\$state\s*\(\s*[\"']"
        r"(?:whatsapp|gmail|contacts|owner|"
        + "|".join(sorted(_INVENTED_SEARCH_PLATFORM_TOKENS))
        + r")[\"']\s*\)",
        whole,
        re.I,
    ) or re.search(
        r"\bplatform\s*=\s*\$state\s*\(\s*[\"']"
        r"(?:whatsapp|gmail|contacts|owner)[\"']\s*\)",
        whole,
        re.I,
    ):
        fail(
            "#121: platform state must default to empty/any "
            "(not pre-selected to a single platform)"
        )


def assert_search_conversation_kind(crate: Path) -> None:
    """#122: Search conversation kind is a closed <select>, not free-text.

    Options: empty/any + dm + group + email_thread. Empty value means any and is
    sent as null/empty to api.search (conversationKind / conversation_kind).
    Groups still respect include-groups (checkbox must remain). Do not invent
    kinds beyond those three. Not: Gmail label filter.
    """
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#122: SearchPane.svelte required (search conversation-kind control lives there)")
    src = _search_pane_blob(crate)
    cleaned = _without_comments(src)
    markup = _svelte_markup(src)
    surface = markup if markup.strip() else src
    whole = cleaned

    # 1) api.search must receive conversationKind / conversation_kind from select state.
    api_m = _SEARCH_API_PLATFORM_ARG.search(whole)
    if not api_m:
        if not re.search(r"api\.search\s*\(", whole):
            fail("#122: SearchPane must call api.search")
        if not re.search(r"\b(?:conversationKind|conversation_kind)\s*:", whole):
            fail(
                "#122: api.search must receive conversationKind / conversation_kind "
                "from the select (conversationKind: … in the search args)"
            )
        api_args = whole
    else:
        api_args = api_m.group(1)
        if not re.search(r"\b(?:conversationKind|conversation_kind)\s*:", api_args):
            fail(
                "#122: api.search must receive conversationKind / conversation_kind "
                "from the select (conversationKind: … in the search args)"
            )

    kind_arg_m = _SEARCH_API_KIND_ARG.search(api_args)
    kind_arg = (kind_arg_m.group(1).strip() if kind_arg_m else "") or ""
    if kind_arg and re.fullmatch(
        r"[\"'](?:" + "|".join(sorted(_INVENTED_SEARCH_KIND_TOKENS)) + r")[\"']",
        kind_arg,
        re.I,
    ):
        fail(
            "#122: api.search conversation kind must come from the select state, "
            "not a hard-coded invented token"
        )
    if kind_arg and re.fullmatch(r"[\"'](?:dm|group|email_thread)[\"']", kind_arg, re.I):
        fail(
            "#122: api.search conversation kind must be user-selected from the control, "
            "not hard-coded to a single kind"
        )
    if not _SEARCH_KIND_STATE_FLOW.search(api_args) and not _SEARCH_KIND_STATE_FLOW.search(whole):
        fail(
            "#122: api.search conversation kind must read the select state "
            "(e.g. conversationKind: conversationKind || null) — not a bare null / ignored control"
        )

    # 2) Fail free-text Input/textbox for kind (invalid tokens typable).
    if _SEARCH_KIND_FREE_TEXT.search(surface) or _SEARCH_KIND_FREE_TEXT.search(src):
        fail(
            "#122: search conversation kind must not be a free-text Input/textbox "
            "(invalid tokens cannot be typed — use a closed <select>)"
        )
    # Label "Kind" only — do not match the "kind" suffix inside id="skind".
    if re.search(
        r"(?:Conversation\s+kind|>\s*Kind\s*<|for\s*=\s*[\"'](?:skind|kind)[\"'])",
        surface,
        re.I,
    ) and re.search(
        r"<Input\b|<input\b(?![^>]*\btype\s*=\s*[\"'](?:hidden|checkbox|radio)[\"'])",
        surface,
        re.I,
    ):
        for m in re.finditer(
            r"(?:Conversation\s+kind|>\s*Kind\s*<|for\s*=\s*[\"'](?:skind|kind)[\"'])",
            surface,
            re.I,
        ):
            window = surface[m.start() : m.start() + 400]
            if re.search(
                rf"<Input\b[^>]{{0,200}}(?:kind|skind)|"
                rf"<input\b[^>]{{0,200}}(?:kind|skind)|"
                rf"bind:value=\{{{_SEARCH_KIND_STATE}\}}",
                window,
                re.I,
            ) and not re.search(r"<select\b|Select\.Root|SelectItem", window, re.I):
                fail(
                    "#122: search conversation kind must not be a free-text Input/textbox "
                    "(invalid tokens cannot be typed — use a closed <select>)"
                )

    # 3) Closed control: <select> (or equivalent) bound to kind state.
    has_select = bool(_SEARCH_KIND_SELECT.search(surface)) or bool(
        _SEARCH_KIND_SELECT.search(src)
    )
    if not has_select:
        kind_label = re.search(
            r"(?:for\s*=\s*[\"'](?:skind|kind|conv-kind|conversation-kind)[\"']"
            r"|>\s*(?:Conversation\s*kind|Kind)\s*<"
            r"|id\s*=\s*[\"'](?:skind|kind|conv-kind|conversation-kind)[\"'])",
            surface,
            re.I,
        )
        if kind_label:
            window = surface[kind_label.start() : kind_label.start() + 800]
            has_select = bool(re.search(r"<select\b", window, re.I)) or bool(
                re.search(r"<(?:[A-Za-z][\w]*\.)?Select(?:\.Root)?\b", window, re.I)
            )
    if not has_select:
        fail(
            "#122: search conversation kind must be a closed <select> "
            "(or equivalent Select control) with fixed options — not free text"
        )

    # 4) Options: empty/any + dm + group + email_thread; only those tokens.
    option_region = surface
    sel = re.search(
        rf"<select\b[^>]{{0,400}}(?:\bbind:value=\{{{_SEARCH_KIND_STATE}\}}"
        rf"|\bid\s*=\s*[\"'](?:skind|kind|conv-kind|conversation-kind)[\"'])"
        rf"[^>]*>[\s\S]{{0,2000}}?</select>",
        surface,
        re.I,
    )
    if not sel:
        sel = re.search(
            r"(?:for\s*=\s*[\"'](?:skind|kind|conv-kind|conversation-kind)[\"']"
            r"|>\s*(?:Conversation\s*kind|Kind)\s*<)[\s\S]{0,200}"
            r"<select\b[^>]*>[\s\S]{0,2000}?</select>",
            surface,
            re.I,
        )
    if sel:
        option_region = sel.group(0)

    values = _search_platform_option_values(option_region)
    if not values:
        # Fallback only if a dedicated kind select region was found; do not
        # swallow platform <option> values from the rest of SearchPane.
        if sel:
            values = _search_platform_option_values(surface)

    norm = [v.strip() for v in values]
    lower = [v.lower() for v in norm]

    if "" not in norm:
        fail(
            "#122: conversation-kind <select> must include an empty-value option for Any "
            '(value="" — empty means any; do not send a literal "any" token)'
        )
    if "dm" not in lower:
        fail("#122: conversation-kind <select> must offer dm")
    if "group" not in lower:
        fail("#122: conversation-kind <select> must offer group")
    if "email_thread" not in lower:
        fail("#122: conversation-kind <select> must offer email_thread")

    for v in lower:
        if v == "":
            continue
        if v in _INVENTED_SEARCH_KIND_TOKENS:
            fail(
                f"#122: do not invent search conversation-kind option {v!r} "
                "(only: dm, group, email_thread)"
            )
        if v not in _CORE_SEARCH_KIND_TOKENS:
            if v in {"any", "all"}:
                fail(
                    "#122: Any/all must use empty value=\"\" "
                    "(core has no \"any\" conversation_kind token — empty means any)"
                )
            fail(
                f"#122: conversation-kind option value {v!r} is not accepted "
                "(allowed: dm, group, email_thread; empty = any)"
            )

    # 5) Empty value means any → null/empty from select state to api.search.
    if not _SEARCH_KIND_EMPTY_AS_ANY.search(whole):
        fail(
            "#122: empty conversation kind must mean any "
            "(send null/empty from select state — e.g. conversationKind: conversationKind || null)"
        )

    # Default state should be empty/any, not a forced kind.
    if re.search(
        rf"\b(?:let|const|var)\s+{_SEARCH_KIND_STATE}\s*=\s*\$state\s*\(\s*[\"']"
        r"(?:dm|group|email_thread|"
        + "|".join(sorted(_INVENTED_SEARCH_KIND_TOKENS))
        + r")[\"']\s*\)",
        whole,
        re.I,
    ) or re.search(
        rf"\b{_SEARCH_KIND_STATE}\s*=\s*\$state\s*\(\s*[\"']"
        r"(?:dm|group|email_thread)[\"']\s*\)",
        whole,
        re.I,
    ):
        fail(
            "#122: conversation-kind state must default to empty/any "
            "(not pre-selected to a single kind)"
        )

    # Groups still respect include-groups — checkbox must remain on SearchPane.
    if not re.search(r"include groups", src, re.I) and not re.search(
        r"includeGroups", whole
    ):
        fail(
            "#122: keep include-groups on Search (kind=group still respects include_groups)"
        )

from tauri_gate.search_filters_more import assert_search_attachment_filter
