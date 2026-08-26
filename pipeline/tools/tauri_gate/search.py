"""Search chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _CHROME_SEARCH_HOOK,
    _FETCH_CALL,
    _FOCUS_SEARCH_Q,
    _HTML_BODY,
    _HUMAN_TIME_HELPERS,
    _PEOPLE_AWAIT_REFRESH,
    _VIEW_SEARCH_ASSIGN,
    _claim_without_negation,
    _cond_code,
    _expand_fn_calls,
    _first_substr_pos,
    _function_body,
    _hook_element_blocks,
    _ident_negated,
    _if_gen_eq_contains,
    _js_next,
    _match_closer,
    _matching_each_end,
    _owned_skeleton_names,
    _people_list_gen,
    _product_svelte,
    _review_if_return_conds,
    _same_block_gen_ne_return,
    _short_time_formatter_ok,
    _skeleton_hook_positions,
    _svelte_effect_args,
    _svelte_interpolations,
    _svelte_markup,
    _svelte_open_tag_at,
    _tag_inner,
    _template_stack,
    _try_catch_blocks,
    _ts_fn_body,
    _ts_function_body,
    _web_logic,
    _web_sources,
    _without_comments,
)



# #121 — SearchPane platform select (closed control; core tokens only).
# Tokens Tauri parse_platform accepts for search (not CLI Platform::Owner).
_CORE_SEARCH_PLATFORM_TOKENS = frozenset({"whatsapp", "gmail", "contacts"})
_INVENTED_SEARCH_PLATFORM_TOKENS = frozenset(
    {
        "twitter",
        "x",
        "slack",
        "discord",
        "telegram",
        "signal",
        "imessage",
        "sms",
        "messenger",
        "instagram",
        "facebook",
        "linkedin",
        "reddit",
        "mastodon",
        "matrix",
        "irc",
    }
)
# Free-text textbox bound to search platform state (invalid tokens typable).
_SEARCH_PLATFORM_FREE_TEXT = re.compile(
    r"<Input\b[^>]{0,400}\bbind:value=\{platform\}"
    r"|<input\b(?![^>]*\btype\s*=\s*[\"'](?:hidden|checkbox|radio|submit|button)[\"'])"
    r"[^>]{0,400}\bbind:value=\{platform\}"
    r"|<Input\b[^>]{0,200}\bid\s*=\s*[\"']plat[\"'][^>]{0,200}>"
    r"|<input\b(?![^>]*\btype\s*=\s*[\"'](?:hidden|checkbox|radio|submit|button)[\"'])"
    r"[^>]{0,200}\bid\s*=\s*[\"']plat[\"'][^>]{0,200}>",
    re.I,
)
# Closed platform control: native <select> or bits-ui / Select root.
_SEARCH_PLATFORM_SELECT = re.compile(
    r"<select\b[^>]{0,400}(?:\bbind:value=\{platform\}|\bid\s*=\s*[\"']plat[\"'])"
    r"|(?:\bbind:value=\{platform\}|\bid\s*=\s*[\"']plat[\"'])[^>]{0,400}>"
    r"|<(?:[A-Za-z][\w]*\.)?Select(?:\.Root)?\b[^>]{0,400}\bplatform\b",
    re.I,
)
_SEARCH_OPTION_VALUE = re.compile(
    r"<option\b([^>]*)>",
    re.I,
)
_SEARCH_OPTION_VALUE_ATTR = re.compile(
    r"\bvalue\s*=\s*(?:\{\s*([\"'])(.*?)\1\s*\}|([\"'])(.*?)\3|\{([^}]*)\})",
    re.I | re.S,
)
# bits-ui / custom Select.Item value="…"
_SEARCH_SELECT_ITEM_VALUE = re.compile(
    r"<(?:[A-Za-z][\w]*\.)?(?:Select\.Item|SelectItem|Option)\b([^>]*)>",
    re.I,
)
_SEARCH_API_PLATFORM_ARG = re.compile(
    r"api\.search\s*\(\s*\{([\s\S]{0,800}?)\}",
    re.I,
)
_SEARCH_PLATFORM_ARG = re.compile(
    r"\bplatform\s*:\s*([^,\n}]+)",
    re.I,
)
# Empty select value must mean any → null/empty from select *state* (not bare null).
_SEARCH_PLATFORM_EMPTY_AS_ANY = re.compile(
    r"platform\s*:\s*(?:"
    r"platform\s*\|\|\s*(?:null|undefined)"
    r"|platform\s*\?\?\s*(?:null|undefined)"
    r"|platform\s*\?\s*platform\s*:\s*(?:null|undefined)"
    r"|platform\s*===\s*[\"'][\"']\s*\?\s*(?:null|undefined)"
    r"|!platform\s*\?\s*(?:null|undefined)\s*:\s*platform"
    r"|platform\b"
    r")",
    re.I,
)
# api.search platform arg must read the select binding (not a decorative control).
_SEARCH_PLATFORM_STATE_FLOW = re.compile(
    r"platform\s*:\s*platform\b",
    re.I,
)


def _search_platform_option_values(markup: str) -> list[str]:
    """Collect value= attributes from <option> / Select.Item near platform control."""
    values: list[str] = []
    for tag_re in (_SEARCH_OPTION_VALUE, _SEARCH_SELECT_ITEM_VALUE):
        for m in tag_re.finditer(markup):
            attrs = m.group(1) or ""
            am = _SEARCH_OPTION_VALUE_ATTR.search(attrs)
            if not am:
                # <option>any</option> with no value attr → empty string in HTML
                if tag_re is _SEARCH_OPTION_VALUE and "value" not in attrs.lower():
                    values.append("")
                continue
            if am.group(2) is not None:
                values.append(am.group(2))
            elif am.group(4) is not None:
                values.append(am.group(4))
            else:
                # value={expr} — only accept string literals inside
                expr = (am.group(5) or "").strip()
                lit = re.fullmatch(r"([\"'])(.*)\1", expr)
                if lit:
                    values.append(lit.group(2))
                elif expr in {"\"\"", "''"}:
                    values.append("")
    return values


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
    src = search_path.read_text()
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


# #122 — SearchPane conversation-kind select (closed control; dm|group|email_thread).
_CORE_SEARCH_KIND_TOKENS = frozenset({"dm", "group", "email_thread"})
_INVENTED_SEARCH_KIND_TOKENS = frozenset(
    {
        "channel",
        "room",
        "broadcast",
        "community",
        "thread",
        "space",
        "channel_thread",
        "mailing_list",
        "list",
        "forum",
        "chat",
        "private",
        "public",
        "supergroup",
    }
)
# State bindings accepted for the kind select (camel/snake + short names).
_SEARCH_KIND_STATE = (
    r"(?:conversationKind|conversation_kind|searchKind|kindFilter|kind)"
)
# Free-text textbox bound to search kind state (invalid tokens typable).
_SEARCH_KIND_FREE_TEXT = re.compile(
    rf"<Input\b[^>]{{0,400}}\bbind:value=\{{{_SEARCH_KIND_STATE}\}}"
    rf"|<input\b(?![^>]*\btype\s*=\s*[\"'](?:hidden|checkbox|radio|submit|button)[\"'])"
    rf"[^>]{{0,400}}\bbind:value=\{{{_SEARCH_KIND_STATE}\}}"
    rf"|<Input\b[^>]{{0,200}}\bid\s*=\s*[\"'](?:skind|kind|conv-kind|conversation-kind)[\"']"
    rf"[^>]{{0,200}}>"
    rf"|<input\b(?![^>]*\btype\s*=\s*[\"'](?:hidden|checkbox|radio|submit|button)[\"'])"
    rf"[^>]{{0,200}}\bid\s*=\s*[\"'](?:skind|kind|conv-kind|conversation-kind)[\"']"
    rf"[^>]{{0,200}}>",
    re.I,
)
# Closed kind control: native <select> or bits-ui Select.
_SEARCH_KIND_SELECT = re.compile(
    rf"<select\b[^>]{{0,400}}(?:\bbind:value=\{{{_SEARCH_KIND_STATE}\}}"
    rf"|\bid\s*=\s*[\"'](?:skind|kind|conv-kind|conversation-kind)[\"'])"
    rf"|(?:\bbind:value=\{{{_SEARCH_KIND_STATE}\}}"
    rf"|\bid\s*=\s*[\"'](?:skind|kind|conv-kind|conversation-kind)[\"'])[^>]{{0,400}}>"
    rf"|<(?:[A-Za-z][\w]*\.)?Select(?:\.Root)?\b[^>]{{0,400}}"
    rf"\b(?:conversationKind|conversation_kind|searchKind|kindFilter)\b",
    re.I,
)
_SEARCH_API_KIND_ARG = re.compile(
    r"\b(?:conversationKind|conversation_kind)\s*:\s*([^,\n}]+)",
    re.I,
)
# Empty select value must mean any → null/empty from select *state*.
_SEARCH_KIND_EMPTY_AS_ANY = re.compile(
    r"(?:conversationKind|conversation_kind)\s*:\s*(?:"
    rf"{_SEARCH_KIND_STATE}\s*\|\|\s*(?:null|undefined)"
    rf"|{_SEARCH_KIND_STATE}\s*\?\?\s*(?:null|undefined)"
    rf"|{_SEARCH_KIND_STATE}\s*\?\s*{_SEARCH_KIND_STATE}\s*:\s*(?:null|undefined)"
    rf"|{_SEARCH_KIND_STATE}\s*===\s*[\"'][\"']\s*\?\s*(?:null|undefined)"
    rf"|!{_SEARCH_KIND_STATE}\s*\?\s*(?:null|undefined)\s*:\s*{_SEARCH_KIND_STATE}"
    rf"|{_SEARCH_KIND_STATE}\b"
    r")",
    re.I,
)
# api.search kind arg must read the select binding (not a decorative control).
_SEARCH_KIND_STATE_FLOW = re.compile(
    rf"(?:conversationKind|conversation_kind)\s*:\s*{_SEARCH_KIND_STATE}\b",
    re.I,
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
    src = search_path.read_text()
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
    src = search_path.read_text()
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


# #124 — search hit jumps to that message on the person timeline (not a dead end).
# Jump / open-at-message handlers (App callback or local + parent wire).
_SEARCH_JUMP_FN = re.compile(
    r"\b(?:"
    r"jumpToMessage|jumpToHit|jumpToSearchHit|openSearchHit|openHit|goToMessage|"
    r"openPersonAtMessage|selectPersonAtMessage|openAtMessage|jumpToPersonMessage|"
    r"onJumpToMessage|onOpenHit|onOpenSearchHit|onJumpHit|onSearchHit|"
    r"handleSearchHit|activateSearchHit|openHitOnTimeline"
    r")\b",
    re.I,
)
# Props / callbacks SearchPane may receive from App for the jump path.
_SEARCH_JUMP_PROP = re.compile(
    r"\b(?:"
    r"onJumpToMessage|onOpenHit|onOpenSearchHit|onJumpHit|onSearchHit|"
    r"jumpToMessage|openSearchHit|openHit|onJump"
    r")\b",
    re.I,
)
# Switching to the People view (leave Search).
_VIEW_PEOPLE = re.compile(
    r"view\s*=\s*[\"']people[\"']"
    r"|view\s*=\s*\{?\s*[\"']people[\"']"
    r"|\bsetView\s*\(\s*[\"']people[\"']\s*\)"
    r"|\bnavigate\s*\(\s*[\"']people[\"']\s*\)",
    re.I,
)
# Hit activation must read person_id from the hit (not the search filter state).
_HIT_PERSON_ID_READ = re.compile(
    r"(?:h|hit|row|item|searchHit)\s*\.\s*(?:person_id|personId)\b"
    r"|\b(?:h|hit|row|item|searchHit)\s*\?\s*\.\s*(?:person_id|personId)\b"
    r"|(?:person_id|personId)\s*:\s*(?:h|hit|row|item|searchHit)\s*\.\s*(?:person_id|personId)",
    re.I,
)
# Message id from the hit carried into the jump / scroll path (not only toggle expand).
_HIT_MESSAGE_ID_READ = re.compile(
    r"(?:h|hit|row|item|searchHit)\s*\.\s*(?:message_id|messageId)\b"
    r"|(?:message_id|messageId)\s*:\s*(?:h|hit|row|item|searchHit)\s*\.\s*(?:message_id|messageId)",
    re.I,
)
# Expand-body path (no person_id / stay on Search) — current toggle + searchBody.
_SEARCH_EXPAND_BODY = re.compile(
    r"\b(?:api\.)?searchBody\s*\("
    r"|\bexpanded\s*="
    r"|\btoggle\s*\(\s*(?:h|hit|id|message_id|messageId)",
    re.I,
)
# Scroll / highlight once the target row is known.
_SEARCH_JUMP_SCROLL_HL = re.compile(
    r"("
    r"\bensureTlIndexVisible\s*\("
    r"|\bscrollIntoView\s*\("
    r"|\btlIndex\s*="
    r"|data-message-id"
    r"|data-tl-index"
    r"|data-message="
    r"|\bfindIndex\s*\([^)]{0,80}(?:message_id|messageId)"
    r"|\.findIndex\s*\("
    r"|\bscrollToMessage\s*\("
    r"|\bscrollMessageIntoView\s*\("
    r"|\bhighlightMessage\s*\("
    r"|ring-2\s+ring-ring"
    r")",
    re.I,
)
# Loading a timeline window that can include the target message (around / after /
# before cursor, or messageId arg). Repeated Load older is OK if bounded — we
# only require some load path that can place message_id in the loaded set.
_SEARCH_JUMP_LOAD_WINDOW = re.compile(
    r"("
    r"\bpersonTimeline\s*\("
    r"|\bapi\.personTimeline\s*\("
    r"|\baround\s*:"
    r"|\bafter\s*:"
    r"|\bbefore\s*:"
    r"|\bmessageId\s*:"
    r"|\bmessage_id\s*:"
    r"|\baroundMessage\b"
    r"|\bloadAround\b"
    r"|\bopenAround\b"
    r"|\bjumpLoad\b"
    r"|\bselectPerson\s*\("
    r")",
    re.I,
)
# Names accepted for the open-hit / jump entry point (click + Enter call this).
# Plain string (adjacent literals) so it embeds cleanly in larger patterns.
_SEARCH_JUMP_CALL_RE = (
    r"jumpToMessage|jumpToHit|jumpToSearchHit|openSearchHit|openHit|goToMessage|"
    r"openPersonAtMessage|selectPersonAtMessage|openAtMessage|jumpToPersonMessage|"
    r"onJumpToMessage|onOpenHit|onOpenSearchHit|onJumpHit|onSearchHit|"
    r"handleSearchHit|activateSearchHit|openHitOnTimeline|activateHit|openHitRow"
)
# Hit click / Enter invokes a jump or activate entry (not only toggle).
_HIT_ACTIVATES_JUMP = re.compile(
    rf"("
    rf"(?:onclick|on:click)(?:\|\w+)*\s*=\s*\{{[\s\S]{{0,400}}\b(?:"
    rf"{_SEARCH_JUMP_CALL_RE}"
    rf")\s*\("
    rf"|(?:onclick|on:click)(?:\|\w+)*\s*=\s*\{{[\s\S]{{0,400}}"
    rf"(?:h|hit)\s*\.\s*(?:person_id|personId)"
    rf"|(?:key|code)\s*===?\s*[\"']Enter[\"'][\s\S]{{0,400}}\b(?:"
    rf"{_SEARCH_JUMP_CALL_RE}"
    rf")\s*\("
    rf"|(?:key|code)\s*===?\s*[\"']Enter[\"'][\s\S]{{0,400}}"
    rf"(?:h|hit)\s*\.\s*(?:person_id|personId)"
    rf")",
    re.I,
)
# Jump handler body must select person + carry message id (not a no-op name).
_JUMP_BODY_SELECTS_PERSON = re.compile(
    r"("
    r"\bselectPerson\s*\("
    r"|\bopenPerson\s*\("
    r"|\bopenPersonAtMessage\s*\("
    r"|\bselectPersonAtMessage\s*\("
    r"|view\s*=\s*[\"']people[\"']"
    r")",
    re.I,
)
_JUMP_BODY_USES_MESSAGE = re.compile(
    r"("
    r"\b(?:message_id|messageId)\b"
    r"|\bensureTlIndexVisible\s*\("
    r"|\btlIndex\s*="
    r"|data-message-id"
    r"|\bfindIndex\s*\("
    r"|\bscrollIntoView\s*\("
    r")",
    re.I,
)
# person_id presence guard on the hit (not the Search filter personId state alone).
_HIT_PERSON_GUARD = re.compile(
    r"("
    r"(?:h|hit|row|item|searchHit)\s*\.\s*(?:person_id|personId)\s*"
    r"(?:\?\?|\|\||&&|!=|!==|==|===|\?)"
    r"|(?:h|hit|row|item|searchHit)\s*\?\s*\.\s*(?:person_id|personId)"
    r"|\bif\s*\([^)]{0,100}(?:h|hit|row|item|searchHit)\s*\.\s*(?:person_id|personId)"
    r"|\b(?:person_id|personId)\s*(?:!=|!==|==|===)\s*(?:null|undefined)[\s\S]{0,120}"
    r"(?:jumpTo|openHit|openSearch|onJump|goToMessage|selectPerson|view\s*=)"
    r")",
    re.I,
)
# #124 miss path — do not treat last loaded row as the hit when findIndex misses.
_IDX_NAME = r"(?:idx|index|foundIdx|foundIndex|tlIdx|pos|foundAt|messageIdx|messageIndex)"
_LOADED_NAME = r"(?:loaded|timeline|rows|chrono|batch|msgs|messages|page|window)"
# tlIndex = idx >= 0 ? idx : Math.max(0, loaded.length - 1)  (and close variants)
_SEARCH_JUMP_LAST_ROW_FALLBACK = re.compile(
    rf"("
    rf"tlIndex\s*=\s*{_IDX_NAME}\s*>=?\s*0\s*\?\s*{_IDX_NAME}\s*:\s*"
    rf"(?:Math\.max\s*\(\s*0\s*,\s*)?{_LOADED_NAME}\s*\.length\s*-\s*1"
    rf"|{_IDX_NAME}\s*>=?\s*0\s*\?\s*{_IDX_NAME}\s*:\s*"
    rf"(?:Math\.max\s*\(\s*0\s*,\s*)?{_LOADED_NAME}\s*\.length\s*-\s*1"
    rf"|{_IDX_NAME}\s*(?:<\s*0|===?\s*-1)\s*\?\s*"
    rf"(?:Math\.max\s*\(\s*0\s*,\s*)?{_LOADED_NAME}\s*\.length\s*-\s*1"
    rf"|findIndex\s*\([\s\S]{{0,160}}(?:message_id|messageId)[\s\S]{{0,280}}"
    rf"tlIndex\s*=\s*[^;\n]{{0,120}}{_LOADED_NAME}\s*\.length\s*-\s*1"
    rf"|tlIndex\s*=\s*{_IDX_NAME}\s*>=?\s*0\s*\?\s*{_IDX_NAME}\s*:"
    rf")",
    re.I,
)
# Any ternary that sets tlIndex from findIndex-style idx with a non-idx false branch
# (wrong-row success) — pairs with the last-row ban above.
_SEARCH_JUMP_TLINDEX_MISS_TERNARY = re.compile(
    rf"tlIndex\s*=\s*{_IDX_NAME}\s*(?:>=?\s*0|<\s*0|===?\s*-1)\s*\?",
    re.I,
)
# Miss branch must surface showErr / onError / throw (not only catch).
_SEARCH_JUMP_MISS_ERROR = re.compile(
    rf"("
    rf"if\s*\(\s*{_IDX_NAME}\s*(?:<\s*0|===?\s*-1)\s*\)\s*\{{[\s\S]{{0,280}}"
    rf"(?:showErr|onError)\s*\("
    rf"|if\s*\(\s*{_IDX_NAME}\s*(?:<\s*0|===?\s*-1)\s*\)[\s\S]{{0,120}}"
    rf"(?:showErr|onError)\s*\("
    rf"|if\s*\(\s*{_IDX_NAME}\s*(?:<\s*0|===?\s*-1)\s*\)\s*\{{[\s\S]{{0,200}}\bthrow\b"
    rf"|if\s*\(\s*{_IDX_NAME}\s*>=?\s*0\s*\)[\s\S]{{0,400}}"
    rf"else\s*\{{[\s\S]{{0,200}}(?:showErr|onError)\s*\("
    rf"|if\s*\(\s*!(?:found|row|hit|target|match|located)\b[\s\S]{{0,160}}"
    rf"(?:showErr|onError)\s*\("
    rf"|if\s*\(\s*!{_LOADED_NAME}\.some\s*\([\s\S]{{0,200}}"
    rf"(?:message_id|messageId)[\s\S]{{0,100}}\)\s*\)\s*\{{[\s\S]{{0,240}}"
    rf"(?:showErr|onError)\s*\("
    rf"|if\s*\(\s*{_LOADED_NAME}\.findIndex\s*\([\s\S]{{0,200}}"
    rf"(?:message_id|messageId)[\s\S]{{0,80}}\)\s*(?:<\s*0|===?\s*-1)"
    rf"[\s\S]{{0,200}}(?:showErr|onError)\s*\("
    rf")",
    re.I,
)


def _search_jump_handler_bodies(blob: str) -> list[str]:
    """Bodies of jump/open-hit functions (placeholder names from the gate list)."""
    names = (
        "jumpToMessage",
        "jumpToHit",
        "jumpToSearchHit",
        "openSearchHit",
        "openHit",
        "goToMessage",
        "openPersonAtMessage",
        "selectPersonAtMessage",
        "openAtMessage",
        "jumpToPersonMessage",
        "handleSearchHit",
        "activateSearchHit",
        "openHitOnTimeline",
        "activateHit",
        "openHitRow",
        "onJumpToMessage",
        "onOpenHit",
        "onOpenSearchHit",
    )
    bodies: list[str] = []
    for name in names:
        body = _function_body(blob, name)
        if body.strip():
            bodies.append(body)
    return bodies


def _assert_search_jump_miss_path(web_blob: str, jump_bodies: list[str]) -> None:
    """#124 miss: error on unfound message_id; never ring last loaded as the hit."""
    path = "\n".join(jump_bodies) if jump_bodies else web_blob
    path_clean = _without_comments(path)
    blob_clean = _without_comments(web_blob)

    # 1) Forbid last-row (or any idx-ternary) fallback as a successful hit ring.
    if _SEARCH_JUMP_LAST_ROW_FALLBACK.search(path_clean) or (
        _SEARCH_JUMP_LAST_ROW_FALLBACK.search(blob_clean)
        and re.search(
            r"findIndex\s*\([\s\S]{0,120}(?:message_id|messageId)",
            blob_clean,
            re.I,
        )
    ):
        fail(
            "#124: when message_id is not in the loaded timeline after the jump walk, "
            "do not set tlIndex to the last loaded row "
            "(tlIndex = idx >= 0 ? idx : Math.max(0, loaded.length - 1)). "
            "That rings an unrelated message with no error. Surface showErr instead"
        )
    if _SEARCH_JUMP_TLINDEX_MISS_TERNARY.search(path_clean):
        fail(
            "#124: do not assign tlIndex via idx-miss ternary "
            "(tlIndex = idx >= 0 ? idx : <fallback>). "
            "On miss: showErr (or equivalent) and return — only set tlIndex when "
            "the hit row is actually found"
        )

    # 2) Require an explicit miss → error path (catch-only showErr is not enough).
    has_miss_err = bool(
        _SEARCH_JUMP_MISS_ERROR.search(path_clean)
        or _SEARCH_JUMP_MISS_ERROR.search(blob_clean)
    )
    if not has_miss_err:
        fail(
            "#124: when the jump path cannot place message_id in the loaded set "
            "(miss after bounded walk / cap), surface an error "
            "(if (idx < 0) { showErr(...); return } / else showErr / "
            "!loaded.some(...message_id) showErr). "
            "Do not treat a wrong row as a successful hit highlight"
        )

    # Prefer (not hard-gated): pass hit.sent_at into onJumpToMessage /
    # openPersonAtMessage when present so the walk can seek near the hit.


def assert_search_jump_to_message(crate: Path) -> None:
    """#124: search hit with person_id jumps to that message on the person timeline.

    With person_id: switch to People, select that person, load a window around
    message_id, scroll the row into view, highlight once (tlIndex / ring as j/k).
    Without person_id: stay on Search and expand body (toggle / searchBody).
    Miss after bounded load: showErr (or equivalent); never ring last-loaded as hit.
    Virtualized timeline (#120): ensure target index enters the window
    (ensureTlIndexVisible / scroll estimate) when that path exists.
    Not: FTS rewrite, inventing a person when person_id is missing.
    """
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    app_path = crate / "web" / "App.svelte"
    if not search_path.is_file():
        fail("#124: SearchPane.svelte required (search hit jump lives there)")
    if not app_path.is_file():
        fail("#124: App.svelte required (People view / selectPerson / timeline scroll)")

    search_src = search_path.read_text()
    app_src = app_path.read_text()
    logic = _web_logic(crate)
    search_clean = _without_comments(search_src)
    app_clean = _without_comments(app_src)
    logic_clean = _without_comments(logic)
    search_markup = _svelte_markup(search_src)
    surface = search_markup if search_markup.strip() else search_src
    # Jump path may live in SearchPane, App, or a small helper under web/.
    web_blob = search_clean + "\n" + app_clean + "\n" + logic_clean

    # 1) Hits must still be listed and activatable (click and/or keyboard Enter).
    if not re.search(r"\{#each\s+hits\b", surface) and not re.search(
        r"\{#each\s+hits\b", search_src
    ):
        fail("#124: SearchPane must list hits ({#each hits}) so a hit can be opened")
    has_hit_click = bool(
        re.search(r"(?:onclick|on:click)(?:\|\w+)*\s*=\s*\{", surface)
        and re.search(
            r"message_id|messageId|toggle|jump|openHit|openSearch|activate",
            surface + "\n" + search_clean,
            re.I,
        )
    )
    has_hit_enter = bool(
        re.search(r"(?:key|code)\s*===?\s*[\"']Enter[\"']", search_clean)
    )
    if not has_hit_click and not has_hit_enter:
        fail(
            "#124: search hits must be activatable (click and/or Enter) — "
            "a hit is not a dead end"
        )

    # 2) Without person_id: keep expand-body on Search (toggle / searchBody).
    if not _SEARCH_EXPAND_BODY.search(search_clean) and not _SEARCH_EXPAND_BODY.search(
        search_src
    ):
        fail(
            "#124: without person_id, stay on Search and expand body as today "
            "(toggle / api.searchBody / expanded = message_id) — do not invent a person"
        )

    # 3) Hit activation must invoke a jump/activate path (primary pre-impl red).
    #    Current SearchPane only toggle(h.message_id) / Enter → toggle — fail that.
    hit_activates_jump = bool(
        _HIT_ACTIVATES_JUMP.search(search_src)
        or _HIT_ACTIVATES_JUMP.search(search_clean)
        or _HIT_ACTIVATES_JUMP.search(surface)
    )
    if not hit_activates_jump:
        fail(
            "#124: search hit with person_id must not only expand the body on Search — "
            "click/Enter must call a jump handler (jumpToMessage / openSearchHit / "
            "activateHit / onJumpToMessage…) or branch on hit.person_id. "
            "Without person_id, expand body stays"
        )

    # 4) Jump handler must exist and do real work: People + person + message.
    jump_bodies = _search_jump_handler_bodies(web_blob)
    # Inline arrow assigned to prop: onJumpToMessage={async (pid, mid) => { ... }}
    inline_jump = re.findall(
        r"(?:onJumpToMessage|onOpenHit|onOpenSearchHit|onJumpHit|onSearchHit|onJump)\s*="
        r"\s*\{([\s\S]{0,1500}?)\}(?=\s|/?>)",
        app_src + "\n" + search_src,
        re.I,
    )
    jump_bodies.extend(inline_jump)

    has_jump_symbol = bool(
        _SEARCH_JUMP_FN.search(web_blob) or _SEARCH_JUMP_PROP.search(web_blob)
    )
    if not has_jump_symbol and not jump_bodies:
        fail(
            "#124: require a jump handler (jumpToMessage / openSearchHit / "
            "onJumpToMessage / activateHit / …) that opens the hit on the person timeline"
        )

    # App wires SearchPane callback, or SearchPane jumps itself (view/selectPerson).
    app_wires_jump = bool(
        re.search(
            r"<SearchPane\b[^>]{0,500}(?:"
            r"onJumpToMessage|onOpenHit|onOpenSearchHit|onJumpHit|onSearchHit|"
            r"jumpToMessage|openSearchHit|onJump|activateHit"
            r")",
            app_src,
            re.I,
        )
        or re.search(
            r"SearchPane[\s\S]{0,500}(?:"
            r"onJumpToMessage|onOpenHit|onOpenSearchHit|onJumpHit|onSearchHit|"
            r"jumpToMessage|openSearchHit|onJump|activateHit"
            r")",
            app_clean,
            re.I,
        )
    )
    search_jumps_inline = bool(
        _HIT_PERSON_ID_READ.search(search_clean)
        and (
            _VIEW_PEOPLE.search(search_clean)
            or re.search(r"\bselectPerson\s*\(|\bopenPerson\s*\(", search_clean)
        )
    )
    if not app_wires_jump and not search_jumps_inline and not jump_bodies:
        fail(
            "#124: wire SearchPane → App jump (onJumpToMessage={…} / jumpToMessage) "
            "or jump from SearchPane into People + selectPerson"
        )

    # Real work inside a jump handler (reject no-op name-only stubs).
    body_selects = any(_JUMP_BODY_SELECTS_PERSON.search(b) for b in jump_bodies)
    body_message = any(_JUMP_BODY_USES_MESSAGE.search(b) for b in jump_bodies)
    # selectPerson / view=people near a jump call site also counts (thin wrapper).
    jump_call_near_select = bool(
        re.search(
            rf"(?:{_SEARCH_JUMP_CALL_RE})\s*\([\s\S]{{0,600}}"
            r"(?:selectPerson\s*\(|openPerson\s*\(|view\s*=\s*[\"']people[\"'])"
            rf"|(?:selectPerson\s*\(|view\s*=\s*[\"']people[\"'])[\s\S]{{0,600}}"
            rf"(?:{_SEARCH_JUMP_CALL_RE})\s*\(",
            web_blob,
            re.I,
        )
    )
    # Combined handler in SearchPane: if (h.person_id) { onJump… } else toggle
    search_branches_to_jump = bool(
        re.search(
            r"(?:h|hit)\s*\.\s*(?:person_id|personId)[\s\S]{0,200}"
            rf"(?:{_SEARCH_JUMP_CALL_RE})\s*\(",
            search_clean,
            re.I,
        )
    )

    if not (body_selects or jump_call_near_select or search_jumps_inline):
        fail(
            "#124: jump path must switch to People and select the hit's person "
            "(view = \"people\" + selectPerson / openPerson / openPersonAtMessage — "
            "not a no-op jump name)"
        )
    if not (body_message or search_branches_to_jump or _HIT_MESSAGE_ID_READ.search(
        "\n".join(jump_bodies) if jump_bodies else ""
    )):
        # Message id must reach the open/scroll path.
        if not re.search(
            rf"(?:{_SEARCH_JUMP_CALL_RE})\s*\([^)]{{0,120}}"
            r"(?:message_id|messageId|h\.message|hit\.message)",
            web_blob,
            re.I,
        ) and not re.search(
            r"(?:h|hit)\s*\.\s*(?:message_id|messageId)[\s\S]{0,200}"
            rf"(?:{_SEARCH_JUMP_CALL_RE}|selectPerson|tlIndex|ensureTlIndexVisible)",
            web_blob,
            re.I,
        ):
            fail(
                "#124: jump path must carry hit.message_id "
                "(open around that message, set tlIndex / scroll to that row)"
            )

    # 5) Only jump when person_id is present (no inventing a person).
    if not _HIT_PERSON_GUARD.search(web_blob) and not _HIT_PERSON_ID_READ.search(
        search_clean
    ):
        fail(
            "#124: only jump when hit.person_id is present — without it stay on Search "
            "and expand body (do not invent a person from the hit)"
        )
    # Prefer an explicit guard near jump (hit.person_id ? jump : toggle).
    if not _HIT_PERSON_GUARD.search(web_blob):
        fail(
            "#124: branch on hit.person_id before jumping "
            "(if present → People timeline; else → expand body on Search)"
        )

    # 6) Load a window that can contain message_id.
    # Require load signal inside jump bodies or within a jump-related window —
    # not only the ordinary selectPerson used for sidebar clicks.
    load_in_jump = any(_SEARCH_JUMP_LOAD_WINDOW.search(b) for b in jump_bodies)
    load_near_jump = bool(
        re.search(
            rf"(?:{_SEARCH_JUMP_CALL_RE})[\s\S]{{0,800}}"
            r"(?:personTimeline|around\s*:|after\s*:|before\s*:|aroundMessage|"
            r"loadAround|openAround|selectPerson\s*\()"
            rf"|(?:personTimeline|aroundMessage|loadAround)[\s\S]{{0,400}}"
            rf"(?:{_SEARCH_JUMP_CALL_RE}|message_id|messageId)",
            web_blob,
            re.I,
        )
    )
    if not load_in_jump and not load_near_jump and not body_selects:
        fail(
            "#124: jump path must load a timeline window around message_id "
            "(personTimeline before/after/around, or selectPerson load that can "
            "place the hit in the loaded set — bounded Load older OK for dogfood)"
        )

    # 7) Scroll into view + highlight once — must appear in jump path, not only j/k.
    # Require coupling to a jump handler name (bare tlIndex/message_id elsewhere is j/k / mail fold).
    scroll_in_jump = any(_SEARCH_JUMP_SCROLL_HL.search(b) for b in jump_bodies)
    scroll_near_jump = bool(
        re.search(
            rf"(?:{_SEARCH_JUMP_CALL_RE})[\s\S]{{0,900}}"
            r"(?:ensureTlIndexVisible\s*\(|tlIndex\s*=|scrollIntoView\s*\(|"
            r"data-message-id|scrollToMessage|scrollMessageIntoView|findIndex\s*\()"
            rf"|(?:ensureTlIndexVisible\s*\(|scrollToMessage\s*\(|scrollMessageIntoView\s*\()"
            rf"[\s\S]{{0,400}}(?:{_SEARCH_JUMP_CALL_RE}|message_id|messageId)",
            web_blob,
            re.I,
        )
    )
    if not scroll_in_jump and not scroll_near_jump:
        fail(
            "#124: after jump, scroll the target message into view and highlight once "
            "(tlIndex = … / ensureTlIndexVisible / scrollIntoView / data-message-id — "
            "same ring as j/k selection; must be on the jump path, not only j/k)"
        )
    # Virtualized timeline: ensureTlIndexVisible (or scroll) must exist in App.
    if not re.search(r"\bensureTlIndexVisible\s*\(", app_clean) and not re.search(
        r"scrollIntoView|data-message-id", app_clean
    ):
        fail(
            "#124: timeline must be able to bring the jumped-to index into view "
            "(ensureTlIndexVisible or scrollIntoView / data-message-id; "
            "virtualized lists must open the virtual window on that index)"
        )

    # 8) Keep #121–#123 search chrome.
    if not re.search(r"\bplatform\b", search_clean) or not re.search(
        r"<select\b", surface, re.I
    ):
        fail("#124: keep the search platform <select> (#121) when adding jump-to-hit")
    if not re.search(r"conversationKind|conversation_kind", search_clean):
        fail(
            "#124: keep the search conversation-kind <select> (#122) when adding jump-to-hit"
        )
    if not re.search(
        r"personId|person_id|personFilter|data-person-picker", search_clean
    ):
        fail("#124: keep the search person picker (#123) when adding jump-to-hit")

    # 9) Keep api.search (do not rewrite FTS as part of jump-to-hit).
    if not re.search(r"api\.search\s*\(", search_clean):
        fail("#124: keep api.search (do not rewrite FTS as part of jump-to-hit)")

    # 10) Miss path: error when message_id not in loaded set; never ring last row.
    _assert_search_jump_miss_path(web_blob, jump_bodies)


# #125 — SearchPane attachment presence select (closed; has_file|omitted|missing).
_CORE_SEARCH_ATTACHMENT_TOKENS = frozenset({"has_file", "omitted", "missing"})
_INVENTED_SEARCH_ATTACHMENT_TOKENS = frozenset(
    {
        "video",
        "video_only",
        "image",
        "image_only",
        "audio",
        "audio_only",
        "mime",
        "media",
        "has_media",
        "has:media",
        "hasmedia",
        "sticker",
        "voice",
        "pdf",
        "document",
        "photo",
        "file_type",
        "filetype",
        "mimetype",
        "mime_type",
    }
)
# State bindings accepted for the attachment select (camel/snake + short names).
_SEARCH_ATTACHMENT_STATE = (
    r"(?:attachmentFilter|attachment_filter|attFilter|attachFilter|searchAttachment)"
)
# Free-text textbox bound to attachment filter state (invalid tokens typable).
_SEARCH_ATTACHMENT_FREE_TEXT = re.compile(
    rf"<Input\b[^>]{{0,400}}\bbind:value=\{{{_SEARCH_ATTACHMENT_STATE}\}}"
    rf"|<input\b(?![^>]*\btype\s*=\s*[\"'](?:hidden|checkbox|radio|submit|button)[\"'])"
    rf"[^>]{{0,400}}\bbind:value=\{{{_SEARCH_ATTACHMENT_STATE}\}}"
    rf"|<Input\b[^>]{{0,200}}\bid\s*=\s*[\"'](?:satt|att|attachment|attachment-filter)[\"']"
    rf"[^>]{{0,200}}>"
    rf"|<input\b(?![^>]*\btype\s*=\s*[\"'](?:hidden|checkbox|radio|submit|button)[\"'])"
    rf"[^>]{{0,200}}\bid\s*=\s*[\"'](?:satt|att|attachment|attachment-filter)[\"']"
    rf"[^>]{{0,200}}>",
    re.I,
)
# Closed attachment control: native <select> or bits-ui Select.
_SEARCH_ATTACHMENT_SELECT = re.compile(
    rf"<select\b[^>]{{0,400}}(?:\bbind:value=\{{{_SEARCH_ATTACHMENT_STATE}\}}"
    rf"|\bid\s*=\s*[\"'](?:satt|att|attachment|attachment-filter)[\"'])"
    rf"|(?:\bbind:value=\{{{_SEARCH_ATTACHMENT_STATE}\}}"
    rf"|\bid\s*=\s*[\"'](?:satt|att|attachment|attachment-filter)[\"'])[^>]{{0,400}}>"
    rf"|<(?:[A-Za-z][\w]*\.)?Select(?:\.Root)?\b[^>]{{0,400}}"
    rf"\b(?:attachmentFilter|attachment_filter|attFilter|attachFilter)\b",
    re.I,
)
_SEARCH_API_ATTACHMENT_ARG = re.compile(
    r"\b(?:attachmentFilter|attachment_filter)\s*:\s*([^,\n}]+)",
    re.I,
)
# Empty select value must mean any → null/empty from select *state*.
_SEARCH_ATTACHMENT_EMPTY_AS_ANY = re.compile(
    r"(?:attachmentFilter|attachment_filter)\s*:\s*(?:"
    rf"{_SEARCH_ATTACHMENT_STATE}\s*\|\|\s*(?:null|undefined)"
    rf"|{_SEARCH_ATTACHMENT_STATE}\s*\?\?\s*(?:null|undefined)"
    rf"|{_SEARCH_ATTACHMENT_STATE}\s*\?\s*{_SEARCH_ATTACHMENT_STATE}\s*:\s*(?:null|undefined)"
    rf"|{_SEARCH_ATTACHMENT_STATE}\s*===\s*[\"'][\"']\s*\?\s*(?:null|undefined)"
    rf"|!{_SEARCH_ATTACHMENT_STATE}\s*\?\s*(?:null|undefined)\s*:\s*{_SEARCH_ATTACHMENT_STATE}"
    rf"|{_SEARCH_ATTACHMENT_STATE}\b"
    r")",
    re.I,
)
# api.search attachment arg must read the select binding (not a decorative control).
_SEARCH_ATTACHMENT_STATE_FLOW = re.compile(
    rf"(?:attachmentFilter|attachment_filter)\s*:\s*{_SEARCH_ATTACHMENT_STATE}\b",
    re.I,
)


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
    src = search_path.read_text()
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


# #126 — safe search snippet highlight: <mark> siblings, never innerHTML of body.
# Core FTS snippets already wrap hits with «…» (see docs/user/search.md).
_SEARCH_HIGHLIGHT_HELPER = re.compile(
    r"\b(?:"
    r"splitSnippet|snippetSegments|snippetParts|highlightSnippet|highlightSegments|"
    r"markSegments|markSnippet|segmentSnippet|parseSnippet|snippetMarks|"
    r"highlightSearch|searchHighlight|ftsSnippet|splitFtsSnippet|"
    r"splitMarkers|markerSegments|wrapMarks"
    r")\b",
    re.I,
)
# Split evidence: FTS guillemet markers or a snippet-aware split / segment helper.
_SEARCH_SNIPPET_SPLIT = re.compile(
    r"("
    r"[«»]"  # core FTS snippet markers
    r"|\\u00ab|\\u00bb"  # unicode escapes
    r"|\bsplit\s*\([^)]*(?:snippet|«|»|marker)"
    r"|\.split\s*\(\s*(?:/[«»]|[\"']«|new\s+RegExp\s*\(\s*[\"']«)"
    r"|\b(?:snippetSegments|snippetParts|markSegments|highlightSegments|"
    r"segmentSnippet|splitSnippet|splitMarkers|markerSegments)\b"
    r"|\b(?:segments?|parts)\s*(?:=|:)\s*(?:splitSnippet|highlightSnippet|"
    r"snippetSegments|markSegments|segmentSnippet)\b"
    r")",
    re.I,
)
# <mark> with yellow / highlight / mark class, or bare <mark> used as the hit wrap.
_SEARCH_MARK_TAG = re.compile(r"<mark\b", re.I)
_SEARCH_MARK_STYLE = re.compile(
    r"("
    r"<mark\b[^>]{0,200}\bclass\s*=\s*[\"'][^\"']*"
    r"(?:yellow|highlight|mark|bg-yellow|bg-amber|bg-\[|search-hit|hit-mark)"
    r"|<mark\b"  # intentional <mark> (UA default is yellow-ish; class optional)
    r"|\b(?:bg-yellow-\d+|bg-amber-\d+|text-yellow|highlight|hit-mark|search-mark)\b"
    r")",
    re.I,
)
# Dangerous HTML injection on search snippet/body path.
_SEARCH_UNSAFE_HTML = re.compile(
    r"("
    r"\{@html\b"
    r"|\.innerHTML\s*="
    r"|insertAdjacentHTML\s*\("
    r"|dangerouslySetInnerHTML"
    r")",
    re.I,
)
# Building an HTML string of <mark> via replace (regex highlight → inject path).
_SEARCH_REGEX_HTML_MARK = re.compile(
    r"("
    r"\.replace\s*\([^)]{0,200},\s*[`'\"][^`'\"]*<mark\b"
    r"|replace\s*\(\s*(?:new\s+)?RegExp\b[\s\S]{0,200}<mark\b"
    r"|return\s+[`'\"][^`'\"]*<mark\b[^`'\"]*[`'\"]"  # helper returns HTML string
    r")",
    re.I,
)
# HTML mail renderer (out of scope for #126).
_SEARCH_HTML_MAIL = re.compile(
    r"("
    r"\bDOMParser\b"
    r"|\bsrcdoc\s*="
    r"|\brenderHtmlMail\b|\bhtmlMail\b|\bMimeHtml\b|\brenderMime\b"
    r"|iframe[^>]{0,80}(?:body|snippet|mail|message)"
    r")",
    re.I,
)


def _search_highlight_surface(crate: Path) -> tuple[str, str, list[Path]]:
    """SearchPane + relative snippet/highlight helpers (not CasAttach / general UI)."""
    web = crate / "web"
    lib = web / "lib"
    search_path = lib / "SearchPane.svelte"
    paths: list[Path] = []
    seen: set[Path] = set()
    if search_path.is_file():
        paths.append(search_path)
        seen.add(search_path.resolve())
        text = search_path.read_text()
        for m in re.finditer(r"""from\s+["'](\.[^"']+)["']""", text):
            rel = m.group(1)
            base = (search_path.parent / rel).resolve()
            candidates = [base]
            if not base.suffix:
                candidates.extend(
                    [
                        Path(str(base) + ".ts"),
                        Path(str(base) + ".js"),
                        Path(str(base) + ".svelte"),
                        base / "index.ts",
                        base / "index.js",
                    ]
                )
            for c in candidates:
                if not c.is_file() or c.resolve() in seen:
                    continue
                try:
                    c.relative_to(web.resolve())
                except ValueError:
                    continue
                name = c.name.lower()
                body = c.read_text()
                # Only pull helpers involved in snippet split / mark render.
                if re.search(
                    r"snippet|highlight|mark.?segment|fts.?marker|split.?marker",
                    name + "\n" + body[:4000],
                    re.I,
                ) and not re.search(
                    r"CasAttach|EmptyState|DoctorPane|ImportPane|ReviewPane",
                    c.name,
                ):
                    # Skip pure API types modules unless they define a split helper.
                    if c.name in {"api.ts", "api.js"} and not _SEARCH_HIGHLIGHT_HELPER.search(
                        body
                    ):
                        continue
                    paths.append(c)
                    seen.add(c.resolve())
    blob = "\n".join(p.read_text() for p in paths)
    cleaned = _without_comments(blob)
    return blob, cleaned, paths


def assert_search_safe_highlight(crate: Path) -> None:
    """#126: highlight search tokens with <mark> siblings; never innerHTML the body.

    Split the snippet on core FTS markers («…») or matched query terms; render
    plain text + <mark> Svelte elements (text children only). Yellow / mark
    styling so query e.g. fatura shows a visible mark. Expanded search body
    (api.searchBody → body_text) stays text — a body containing <script> must
    not execute. Not: regex HTML inject, HTML mail. Keep #121–#125 chrome.
    """
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#126: SearchPane.svelte required (search snippet highlight lives there)")
    src = search_path.read_text()
    cleaned = _without_comments(src)
    markup = _svelte_markup(src)
    surface = markup if markup.strip() else src
    _blob, blob_clean, helper_paths = _search_highlight_surface(crate)
    # Hits list region is the snippet path; expanded body is the other surface.
    hits_m = re.search(
        r"\{#each\s+hits\b[\s\S]{0,8000}?\{/each\}",
        surface,
        re.I,
    )
    hits_region = hits_m.group(0) if hits_m else surface

    # 1) Primary red: snippet path must render <mark> for hit highlights.
    #    Not a single raw string of h.snippet alone.
    has_mark = bool(_SEARCH_MARK_TAG.search(hits_region)) or bool(
        _SEARCH_MARK_TAG.search(surface)
    )
    # Allow a small child component used only for the snippet line (e.g. SnippetHighlight).
    if not has_mark:
        for p in helper_paths:
            if p.suffix == ".svelte" and p.name != "SearchPane.svelte":
                htxt = p.read_text()
                if _SEARCH_MARK_TAG.search(htxt) and re.search(
                    r"snippet|highlight|mark|segment",
                    htxt,
                    re.I,
                ):
                    has_mark = True
                    break
    if not has_mark:
        fail(
            "#126: search snippet path must render <mark> for hit highlights "
            "(text + <mark> Svelte element siblings — not a single raw snippet string). "
            "Split on core FTS markers «…» or matched query terms"
        )

    # 2) Must actually split into segments (siblings), not wrap the whole snippet
    #    once without a split path. Evidence: FTS markers, segment helper, or
    #    {#each} over parts next to <mark>.
    has_split = bool(_SEARCH_SNIPPET_SPLIT.search(blob_clean)) or bool(
        _SEARCH_HIGHLIGHT_HELPER.search(blob_clean)
    )
    has_each_segments = bool(
        re.search(
            r"\{#each\s+(?:[^}]*\b(?:seg(?:ment)?s?|parts|tokens|chunks|marks|"
            r"highlighted|snippetParts|snippetSegments)\b|"
            r"[^}]{0,80}(?:splitSnippet|highlightSnippet|snippetSegments|"
            r"markSegments|segmentSnippet)\s*\()",
            hits_region + "\n" + surface,
            re.I,
        )
    )
    # <mark> text content must be a segment field, not the full raw snippet alone.
    mark_wraps_full_snippet = bool(
        re.search(
            r"<mark\b[^>]*>\s*\{(?:\(?\s*)?(?:h\.)?snippet\b[^}]{0,120}\}\s*</mark>",
            hits_region,
            re.I,
        )
    )
    if not has_split and not has_each_segments:
        fail(
            "#126: split the snippet into plain-text + <mark> siblings "
            "(core FTS markers «…», or a pure segment helper / {#each} over parts) — "
            "do not leave the hit as one unsplit string"
        )
    if mark_wraps_full_snippet and not has_each_segments and not has_split:
        fail(
            "#126: do not wrap the entire raw snippet in one <mark> — "
            "split on matched terms / FTS «…» markers into text + <mark> siblings"
        )

    # 3) Yellow / highlight styling on the mark (class or intentional <mark>).
    style_blob = hits_region + "\n" + surface
    for p in helper_paths:
        if p.suffix in {".svelte", ".css"}:
            style_blob += "\n" + p.read_text()
    if not _SEARCH_MARK_STYLE.search(style_blob):
        fail(
            "#126: <mark> must be visibly highlighted "
            "(yellow/amber/highlight class e.g. bg-yellow-200, or intentional <mark> styling) "
            "so a query match is obvious"
        )

    # 4) Ban innerHTML / {@html on search snippet and expanded body path.
    if _SEARCH_UNSAFE_HTML.search(blob_clean) or _SEARCH_UNSAFE_HTML.search(cleaned):
        # Narrow: only fail if it touches snippet/body/search surfaces (not unrelated).
        unsafe = re.search(
            r"(?:snippet|body_text|searchBody|\bbody\b|highlight|mark)[\s\S]{0,160}"
            r"(?:\{@html\b|\.innerHTML\s*=|insertAdjacentHTML\s*\()"
            r"|(?:\{@html\b|\.innerHTML\s*=|insertAdjacentHTML\s*\()[\s\S]{0,160}"
            r"(?:snippet|body_text|searchBody|\bbody\b|highlight)",
            blob_clean,
            re.I,
        )
        bare_html = _HTML_BODY.search(blob_clean) or re.search(
            r"\.innerHTML\s*=", blob_clean
        )
        if unsafe or bare_html:
            fail(
                "#126: never assign innerHTML / {@html on the search snippet or body path "
                "(render text + <mark> Svelte elements with text children only — "
                "a body containing <script> must stay text)"
            )

    # Expanded body path specifically: {body} / body_text must stay text bindings.
    expanded_region = ""
    exp = re.search(
        r"\{#if\s+expanded\b[\s\S]{0,800}?\{/if\}",
        surface,
        re.I,
    )
    if exp:
        expanded_region = exp.group(0)
    if expanded_region and (
        _HTML_BODY.search(expanded_region)
        or re.search(r"\.innerHTML\s*=", expanded_region)
        or re.search(r"\{@html\s+body\b", expanded_region)
    ):
        fail(
            "#126: expanded search body must stay text-safe "
            "(no {@html body} / innerHTML of full body — <script> in body stays text)"
        )
    # Global SearchPane ban on {@html body} even outside the if-region.
    if re.search(r"\{@html\s+(?:body|body_text|snippet)\b", blob_clean):
        fail(
            "#126: expanded search body / snippet must stay text-safe — "
            "no {@html body} / {@html snippet}"
        )

    # 5) Not: regex highlight that builds HTML strings to inject.
    if _SEARCH_REGEX_HTML_MARK.search(blob_clean):
        fail(
            "#126: not in scope — regex highlight that builds HTML mark strings "
            "(no .replace(…, '<mark>…') inject path; use text + <mark> element siblings)"
        )

    # 6) Not: HTML mail renderer.
    if _SEARCH_HTML_MAIL.search(blob_clean):
        # Ignore false positives in comments already stripped; still scope to search.
        fail(
            "#126: not in scope — HTML mail renderer "
            "(DOMParser / srcdoc / htmlMail on search path); snippets and body stay text"
        )

    # 7) Keep #121–#125 search chrome.
    if not re.search(r"\bplatform\b", cleaned) or not re.search(
        r"<select\b", surface, re.I
    ):
        fail("#126: keep the search platform <select> (#121) when adding safe highlight")
    if not re.search(r"conversationKind|conversation_kind", cleaned):
        fail(
            "#126: keep the search conversation-kind <select> (#122) when adding safe highlight"
        )
    if not re.search(r"personId|person_id|personFilter|data-person-picker", cleaned):
        fail("#126: keep the search person picker (#123) when adding safe highlight")
    if not re.search(r"\{#each\s+hits\b", surface) and not re.search(
        r"\{#each\s+hits\b", src
    ):
        fail("#126: keep search hits list (#124 jump chrome) when adding safe highlight")
    if not re.search(r"attachmentFilter|attachment_filter", cleaned):
        fail(
            "#126: keep the search attachment filter (#125) when adding safe highlight"
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
    src = search_path.read_text()
    cleaned = _without_comments(src)
    markup = _svelte_markup(src)
    surface = markup if markup.strip() else src
    app_path = crate / "web" / "App.svelte"
    app = app_path.read_text() if app_path.is_file() else ""
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
    if re.search(r"\bapi\.search\s*\(", app):
        fail(
            "#209: App.svelte must not call api.search — SearchPane run() stays "
            "the only caller (#208)"
        )


# #210 — search hit rows: short time + person/title, then highlighted snippet.
_HIT_TIME_EXTRA = ("utcTime",)
_HIT_SENT_AT_NO_DATE = re.compile(
    r"""(?:h\.)?sent_at\s*\|\|\s*["']no date["']""",
    re.I,
)
_HIT_LOG_JOIN = re.compile(
    r"""\.join\s*\(\s*["']\s*·\s*["']\s*\)""",
)
_HIT_PERSON_OR_TITLE = re.compile(
    r"\b(?:person_name|personName|conversation_title|conversationTitle)\b"
)
_HIT_DENSITY_META = re.compile(
    r"\btext-xs\b|text-\[(?:12|13)px\]",
    re.I,
)
_HIT_DENSITY_SNIP = re.compile(
    r"\btext-sm\b|text-\[(?:14|15)px\]",
    re.I,
)
_HIT_DENSITY_PAD = re.compile(
    r"\b(?:py-1\.5|py-2|gap-1\.5|gap-2)\b",
    re.I,
)
_DOCS_HIT_DENSITY = re.compile(
    r"("
    r"(?:search )?hits?"
    r".{0,200}short(?:er)?(?: UTC| human)? time"
    r".{0,120}person(?:/|\s+or\s+|\s+and/?or\s+)(?:conversation )?title"
    r".{0,100}(?:highlighted )?snippet"
    r")",
    re.I | re.S,
)
_DOCS_HIT_NOT_ISO = re.compile(
    r"("
    r"(?:search )?hits?.{0,220}not (?:a |the )?raw ISO"
    r"|not (?:a |the )?raw ISO dump"
    r")",
    re.I | re.S,
)


def _hit_time_helpers() -> tuple[str, ...]:
    return _HUMAN_TIME_HELPERS + _HIT_TIME_EXTRA


def _hit_time_call_rx() -> re.Pattern[str]:
    return re.compile(r"\b(?:" + "|".join(_hit_time_helpers()) + r")\s*\(")


def _hits_each_block(markup: str) -> str:
    m = re.search(r"\{#each\s+hits\b", markup)
    if not m:
        return ""
    end = _matching_each_end(markup, m.start())
    if end < 0:
        return markup[m.start() :]
    return markup[m.start() : end]


def _interp_dumps_iso_sent_at(expr: str) -> bool:
    """True if sent_at is stringified (raw ISO), not passed to a formatter.

    Jump payload `sentAt: h.sent_at` is API, not display — ignore those.
    """
    stripped = re.sub(r"\bsentAt\s*:\s*(?:[\w.$]+\.)?sent_at\b", "", expr)
    if not re.search(r"\bsent_at\b", stripped):
        return False
    names = "|".join(_hit_time_helpers())
    if re.search(rf"\b(?:{names})\s*\([^)]*\bsent_at\b", stripped):
        return False
    return True


def _hits_uses_short_time(hits_each: str) -> bool:
    if _hit_time_call_rx().search(hits_each):
        return True
    names = "|".join(_hit_time_helpers())
    for expr in _svelte_interpolations(hits_each):
        if re.search(rf"\b(?:{names})\s*\([^)]*\bsent_at\b", expr):
            return True
    return False


def _hits_meta_is_five_field_log(hits_each: str) -> bool:
    """True if one interpolation still joins sent_at + platform + kind."""
    for expr in _svelte_interpolations(hits_each):
        has_sent = bool(re.search(r"\bsent_at\b", expr))
        has_plat = bool(re.search(r"\bplatform\b", expr))
        has_kind = bool(re.search(r"\bconversation_kind\b", expr))
        if has_sent and has_plat and has_kind:
            return True
        if _HIT_LOG_JOIN.search(expr) and has_plat and has_kind:
            return True
    if re.search(
        r"sent_at[\s\S]{0,240}platform[\s\S]{0,240}conversation_kind"
        r"[\s\S]{0,120}\.join\s*\(\s*[\"']\s*·",
        hits_each,
    ):
        return True
    return False


def assert_search_hit_density(crate: Path) -> None:
    """#210: hit rows show short time + person/title, then a highlighted snippet.

    Format `h.sent_at` with existing `humanTime` / `utcTime` (or another name
    in `_HUMAN_TIME_HELPERS`). Quiet meta is short time + person name and/or
    conversation title — not a five-field `sent_at · platform · kind · name ·
    title` dump. Snippet stays splitSnippet + <mark> text children. Keep
    #124 j/k+Enter, #126 mark path, #208 chrome search, #209 filters. Not:
    regex HTML inject, HTML mail renderer, FTS «» rewrite.
    """
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#210: SearchPane.svelte required (search hit rows live there)")
    src = search_path.read_text()
    cleaned = _without_comments(src)
    markup = _svelte_markup(src)
    surface = markup if markup.strip() else src
    hits_each = _hits_each_block(surface)
    if not hits_each.strip():
        hits_each = _hits_each_block(src)
    app_path = crate / "web" / "App.svelte"
    app = app_path.read_text() if app_path.is_file() else ""
    logic = _web_logic(crate)
    docs_search = repo_root() / "docs" / "user" / "search.md"
    docs_app = repo_root() / "docs" / "user" / "app.md"
    dtxt = ""
    if docs_search.is_file():
        dtxt += docs_search.read_text() + "\n"
    if docs_app.is_file():
        dtxt += docs_app.read_text()

    # 1) Hits list hooks stay.
    if not re.search(r"\{#each\s+hits\b", surface) and not re.search(
        r"\{#each\s+hits\b", src
    ):
        fail("#210: SearchPane must still list hits ({#each hits})")
    if not hits_each.strip():
        fail("#210: search hits {#each hits} body missing")
    if not re.search(r"\bdata-search-hits\b", surface):
        fail("#210: keep data-search-hits on the hits list")
    if not re.search(r"\bdata-search-hit\b", hits_each):
        fail("#210: keep data-search-hit on each hit row")

    # 2) Still show sent_at — as a short time, not dropped (jump payload alone
    #    does not count; that stays API).
    if not re.search(r"\bsent_at\b", hits_each):
        fail(
            "#210: hit rows must still show sent_at "
            "(as a short time, not drop the timestamp)"
        )

    # 3) Visible hit meta is not the raw ISO T…Z string.
    raw_dump = any(
        _interp_dumps_iso_sent_at(expr) for expr in _svelte_interpolations(hits_each)
    )
    if raw_dump or _HIT_SENT_AT_NO_DATE.search(hits_each):
        fail(
            "#210: hit rows must not display raw ISO sent_at "
            "(T…Z / h.sent_at || \"no date\" in a join); "
            "use humanTime / utcTime (e.g. 11 Aug 14:32)"
        )

    # 4) Five-field log dump is gone (sent_at · platform · kind · name · title).
    if _hits_meta_is_five_field_log(hits_each):
        fail(
            "#210: hit meta must not join sent_at with platform and "
            "conversation_kind as one ` · ` log line; quiet meta is "
            "short time + person/title, then the snippet"
        )

    # 5) A formatter exists and the hit row actually calls it.
    if not _short_time_formatter_ok(logic):
        fail(
            "#210: format sent_at as a short UTC time "
            "(e.g. 11 Aug 14:32) — month + hour:minute, not YYYY-MM-DDTHH:MM:SSZ"
        )
    if not _hits_uses_short_time(hits_each):
        fail(
            "#210: hit meta must pass sent_at through a short-time helper "
            "(humanTime / utcTime / another name in _HUMAN_TIME_HELPERS), "
            "not interpolate the ISO"
        )

    # 6) Person name and/or conversation title stay on the row.
    if not _HIT_PERSON_OR_TITLE.search(hits_each):
        fail(
            "#210: hit rows must show a person name and/or conversation title "
            "(quiet meta is short time + person/title)"
        )

    # 7) Snippet stays splitSnippet + <mark> text children (#126).
    if not re.search(r"\bsplitSnippet\b", hits_each + "\n" + cleaned):
        fail(
            "#210: keep splitSnippet (or the existing #126 helper) so the "
            "snippet is text + <mark> siblings"
        )
    if not _SEARCH_MARK_TAG.search(hits_each):
        fail(
            "#210: keep <mark> text children on the snippet path "
            "(no {@html} / innerHTML of snippet or body)"
        )
    if re.search(
        r"<mark\b[^>]*>\s*\{(?:\(?\s*)?(?:h\.)?snippet\b[^}]{0,120}\}\s*</mark>",
        hits_each,
        re.I,
    ) and not re.search(r"\{#each\s+", hits_each):
        fail(
            "#210: do not wrap the entire raw snippet in one <mark> — "
            "keep splitSnippet + text / <mark> siblings"
        )

    # 8) No {@html} / innerHTML / regex HTML inject / HTML mail on search path.
    blob = hits_each + "\n" + cleaned
    if _SEARCH_UNSAFE_HTML.search(blob) or _SEARCH_UNSAFE_HTML.search(surface):
        unsafe = re.search(
            r"(?:snippet|body_text|searchBody|\bbody\b|highlight|mark)[\s\S]{0,160}"
            r"(?:\{@html\b|\.innerHTML\s*=|insertAdjacentHTML\s*\()"
            r"|(?:\{@html\b|\.innerHTML\s*=|insertAdjacentHTML\s*\()[\s\S]{0,160}"
            r"(?:snippet|body_text|searchBody|\bbody\b|highlight)",
            blob,
            re.I,
        )
        bare_html = _HTML_BODY.search(blob) or re.search(r"\.innerHTML\s*=", blob)
        if unsafe or bare_html:
            fail(
                "#210: never assign innerHTML / {@html on the search snippet or "
                "body path (a body containing <script> must stay text)"
            )
    if re.search(r"\{@html\s+(?:body|body_text|snippet)\b", blob):
        fail(
            "#210: expanded search body / snippet must stay text-safe — "
            "no {@html body} / {@html snippet}"
        )
    if _SEARCH_REGEX_HTML_MARK.search(blob):
        fail(
            "#210: not in scope — regex highlight that builds HTML mark strings "
            "(no FTS marker rewrite; use text + <mark> siblings)"
        )
    if _SEARCH_HTML_MAIL.search(blob):
        fail(
            "#210: not in scope — HTML mail renderer "
            "(DOMParser / srcdoc / htmlMail on search path)"
        )

    # 9) j/k (or arrows) + Enter/Space still activateHit (#124).
    hits_key = _ts_function_body(src, "onHitsKey") or _function_body(src, "onHitsKey")
    if not hits_key:
        fail("#210: keep onHitsKey (#124) — j/k + Enter jump")
    if not re.search(r"""["']j["']""", hits_key) and not re.search(
        r"ArrowDown", hits_key
    ):
        fail("#210: onHitsKey must still handle j / ArrowDown")
    if not re.search(r"""["']k["']""", hits_key) and not re.search(
        r"ArrowUp", hits_key
    ):
        fail("#210: onHitsKey must still handle k / ArrowUp")
    if not re.search(r"""["']Enter["']""", hits_key) and not re.search(
        r"""["'] ["']""", hits_key
    ):
        fail("#210: onHitsKey must still handle Enter / Space → activateHit")
    if not re.search(r"\bactivateHit\b", hits_key):
        fail("#210: onHitsKey Enter / Space must still call activateHit (#124)")

    # 10) Jump payload still carries ISO sent_at (API, not display).
    act = _ts_function_body(src, "activateHit") or _function_body(src, "activateHit")
    if act and not re.search(r"sentAt\s*:\s*(?:h\.)?sent_at\b", act):
        fail(
            "#210: keep sentAt: h.sent_at on the jump payload — "
            "that is API, not display (do not drop the ISO field)"
        )

    # 11) Light people-list density (do not over-constrain Tailwind).
    if not _HIT_DENSITY_META.search(hits_each):
        fail(
            "#210: hit meta should stay people-list scale "
            "(text-xs / 12–13px), not giant cards"
        )
    if not _HIT_DENSITY_SNIP.search(hits_each):
        fail(
            "#210: hit snippet should stay people-list scale "
            "(text-sm / 14–15px)"
        )
    if not _HIT_DENSITY_PAD.search(hits_each):
        fail(
            "#210: hit rows should stay tight (py-2 / gap-2), not giant cards"
        )

    # 12) Do not soften #121–#126 / #205 / #208 / #209.
    if not re.search(r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""", surface):
        fail("#210: keep id=\"q\" as the canonical query field (#208 / #209)")
    if not re.search(r"\bdata-search-filters\b", surface):
        fail("#210: keep data-search-filters (#209)")
    if not re.search(r"\bdata-chrome-search\b", app):
        fail("#210: keep chrome search field data-chrome-search (#208)")
    if re.search(r"\bapi\.search\s*\(", app):
        fail(
            "#210: App.svelte must not call api.search — SearchPane run() stays "
            "the only caller (#208)"
        )
    if not re.search(r"data-person-picker|personFilter|personId", cleaned):
        fail("#210: keep the search person picker (#123)")
    if not re.search(r"\bdata-partial\b", surface):
        fail("#210: keep search data-partial Error+Retry (#205)")

    # 13) Docs (D24): short time + person/title, then highlighted snippet.
    if not _DOCS_HIT_DENSITY.search(dtxt):
        fail(
            "#210: docs/user/search.md and/or docs/user/app.md must say "
            "search hits show a short time + person/title, then a "
            "highlighted snippet"
        )
    if not _DOCS_HIT_NOT_ISO.search(dtxt):
        fail(
            "#210: docs/user/search.md and/or docs/user/app.md must say "
            "search hits are not a raw ISO dump"
        )
_API_SEARCH_CALL = re.compile(r"\bapi\.search\s*\(")
_INVOKE_SEARCH_CMD = re.compile(
    r"invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']search(?:_cmd)?[\"']",
    re.I,
)
_CHROME_TO_Q = re.compile(
    r"("
    r"getElementById\s*\(\s*[\"']q[\"']"
    r"|querySelector\s*\(\s*[\"']#q[\"']"
    r"|bind:value=\{[^}]*\bq\b[^}]*\}"
    r"|\bq\s*=\s*"
    r")"
)
_CHROME_FIELD_EL = re.compile(r"<Input\b|<input\b|<form\b", re.I)
_SPOTLIGHT_WORD = re.compile(r"\bspotlight\b", re.I)
_MULTI_ARCHIVE_WORD = re.compile(r"\bmulti[- ]archive\b", re.I)
_REMOTE_SEARCH_WORD = re.compile(
    r"("
    r"\bremote\s+search\b"
    r"|search\s+(?:the\s+)?(?:web|cloud|network)\b"
    r"|https?://[^\s\"']+/search"
    r")",
    re.I,
)


def _chrome_search_handler_surface(app: str, chrome_chunk: str) -> str:
    """Markup around the hook plus named submit/focus/key handlers."""
    parts = [chrome_chunk]
    names = re.findall(
        r"(?:on:submit|onsubmit|on:focus|onfocus|on:keydown|onkeydown|"
        r"on:input|oninput|on:change|onchange|on:click|onclick|on:blur|onblur)"
        r"\s*=\s*\{[^}]{0,160}?\b([A-Za-z_][\w]*)\s*\(",
        chrome_chunk,
    )
    names += re.findall(
        r"(?:on:submit|onsubmit|on:focus|onfocus|on:keydown|onkeydown|"
        r"on:input|oninput|on:change|onchange|on:click|onclick)"
        r"\s*=\s*\{([A-Za-z_][\w]*)\}",
        chrome_chunk,
    )
    for extra in (
        "onChromeSearch",
        "chromeSearch",
        "submitChromeSearch",
        "focusChromeSearch",
        "openChromeSearch",
        "goSearch",
        "routeChromeSearch",
    ):
        names.append(extra)
    seen: set[str] = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        inner = _ts_fn_body(app, name) or _function_body(app, name)
        if inner:
            parts.append(_expand_fn_calls(app, inner))
    return "\n".join(parts)


def assert_chrome_search_field(crate: Path) -> None:
    """#208: always-available chrome search field; #q stays canonical.

    data-chrome-search lives in App.svelte chrome (nav/header), not only
    SearchPane. Using it routes to Search and focuses / copies into #q.
    SearchPane run() remains the only api.search caller. No Spotlight,
    no multi-archive, no remote search, no second FTS.
    Not #209 filters, #210 hit density, #211 titlebar, #215 palette,
    #224 virtualizer.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#208: App.svelte required (chrome search field lives in nav/header)")
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#208: SearchPane.svelte required (#q stays the canonical query)")
    app = app_path.read_text()
    search = search_path.read_text()
    markup = _svelte_markup(app)
    app_clean = _without_comments(app)
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) Chrome hook in App.svelte nav/header — not only SearchPane.
    if not _CHROME_SEARCH_HOOK.search(app):
        if _CHROME_SEARCH_HOOK.search(search):
            fail(
                "#208: data-chrome-search must be in App.svelte chrome "
                "(nav/header), not only inside SearchPane"
            )
        fail(
            "#208: App.svelte chrome (nav/header) must include a search field "
            "/ wrapper with data-chrome-search (visible when the archive is "
            "open, not only on the Search tab)"
        )
    if not _CHROME_SEARCH_HOOK.search(markup):
        fail(
            "#208: data-chrome-search must be in App.svelte chrome markup "
            "(nav/header), not only a script string"
        )

    chrome_chunks = [
        chunk
        for tag in ("nav", "header")
        for chunk in _tag_inner(markup, tag)
        if _CHROME_SEARCH_HOOK.search(chunk)
    ]
    if not chrome_chunks:
        fail(
            "#208: data-chrome-search must sit in App.svelte <nav> or <header> "
            "chrome, not only inside a pane"
        )
    chrome_chunk = chrome_chunks[0]
    hook = _CHROME_SEARCH_HOOK.search(markup)
    if hook:
        for kind, cond, _extra in _template_stack(markup, hook.start()):
            if kind in {"if", "if-else"} and re.search(
                r"view\s*===?\s*[\"']search[\"']", cond
            ):
                fail(
                    "#208: chrome search (data-chrome-search) must be available "
                    "whenever the archive is open, not only when view === \"search\""
                )
            if (
                kind == "if"
                and re.search(r"\bsetup\b", cond)
                and not re.search(r"!\s*setup", cond)
            ):
                fail(
                    "#208: chrome search must be visible when the archive is "
                    "open (st && !setup), not only on the setup screen"
                )

    # 2) #q stays the canonical field in SearchPane (do not steal the id).
    if not re.search(r"id=[\"']q[\"']", search):
        fail("#208: SearchPane must keep id=\"q\" as the canonical query field")
    if re.search(r"id=[\"']q[\"']", markup):
        fail(
            "#208: #q stays the canonical field in SearchPane — do not give "
            "the chrome field id=\"q\""
        )

    # 3) Chrome field is an input / form (or wraps one).
    around = markup[
        max(0, (hook.start() if hook else 0) - 220) : (hook.end() if hook else 0) + 700
    ]
    if not _CHROME_FIELD_EL.search(chrome_chunk) and not _CHROME_FIELD_EL.search(around):
        fail(
            "#208: data-chrome-search must be a search field or wrap one "
            "(Input / input / form) in App chrome"
        )

    # 4) Chrome path routes to Search and focuses / copies into #q.
    chrome_surface = _chrome_search_handler_surface(app, chrome_chunk + "\n" + around)
    if not _VIEW_SEARCH_ASSIGN.search(chrome_surface):
        fail(
            "#208: chrome search field must route to Search "
            "(view = \"search\") and then focus #q (or copy into #q)"
        )
    if not _CHROME_TO_Q.search(chrome_surface) and not _FOCUS_SEARCH_Q.search(
        chrome_surface
    ):
        fail(
            "#208: chrome search field must focus #q or copy the typed text "
            "into #q (SearchPane query stays canonical)"
        )

    # 5) SearchPane run() remains the only api.search caller.
    run_body = _ts_fn_body(search, "run") or _function_body(search, "run")
    if not run_body or not _API_SEARCH_CALL.search(run_body):
        fail(
            "#208: SearchPane run() must remain the only api.search caller "
            "(do not add a second FTS path)"
        )
    if _API_SEARCH_CALL.search(app_clean):
        fail(
            "#208: App.svelte must not call api.search — SearchPane run() is "
            "the only search IPC"
        )
    if _INVOKE_SEARCH_CMD.search(app_clean):
        fail(
            "#208: App.svelte must not invoke search / search_cmd — SearchPane "
            "run() remains the only api.search caller"
        )
    for p in _product_svelte(crate):
        if p.name == "SearchPane.svelte":
            continue
        other = _without_comments(p.read_text())
        if _API_SEARCH_CALL.search(other):
            fail(
                f"#208: {p.relative_to(crate)} must not call api.search — "
                "SearchPane run() is the only caller"
            )
        if _INVOKE_SEARCH_CMD.search(other):
            fail(
                f"#208: {p.relative_to(crate)} must not invoke search — "
                "SearchPane run() remains the only api.search caller"
            )

    # 6) D24: chrome always available; ⌘F from every view including People → #q;
    #    `/` still people filter.
    if not dtxt.strip():
        fail(
            "#208: docs/user/app.md required — chrome search is always available"
        )
    if not re.search(
        r"("
        r"chrome.{0,48}search.{0,48}(?:always|every|nav|header)"
        r"|search.{0,48}(?:always available|in (?:the )?chrome|in (?:the )?nav)"
        r"|always[- ]available.{0,24}search"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail("#208: docs/user/app.md must say chrome search is always available")
    if not re.search(
        r"("
        r"(?:⌘\s*F|Ctrl\+F|Ctrl-F).{0,160}"
        r"(?:every view|including People|from People).{0,80}(?:#q|Search)"
        r"|(?:every view|including People).{0,80}(?:⌘\s*F|Ctrl\+F|Ctrl-F)"
        r".{0,80}(?:#q|Search)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#208: docs/user/app.md must say ⌘F from every view including "
            "People focuses #q"
        )
    if not re.search(
        r"("
        r"`/`"
        r"|slash"
        r")"
        r".{0,120}"
        r"("
        r"people filter"
        r"|#person-filter"
        r"|person-filter"
        r"|filters? (?:the )?(?:loaded )?people"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#208: docs/user/app.md must keep `/` focusing the people filter"
        )

    # 7) Not: Spotlight, multi-archive, remote search / rewritten FTS.
    #    Do not require #209 filters, #210 hit density, #211 titlebar,
    #    #215 palette, or #224 virtualizer.
    web_claim = "\n".join(p.read_text() for p in _web_sources(crate)) + "\n" + dtxt
    if _claim_without_negation(web_claim, _SPOTLIGHT_WORD):
        fail("#208: not in scope — no Spotlight / OS-wide search")
    if _claim_without_negation(web_claim, _MULTI_ARCHIVE_WORD):
        fail("#208: not in scope — no multi-archive search")
    if _claim_without_negation(web_claim, _REMOTE_SEARCH_WORD):
        fail("#208: not in scope — no remote search")
_SEARCH_Q_TOKEN = re.compile(r"(?<![\w$])q(?![\w$])")
_SEARCH_TYPE_INPUT_ATTR = re.compile(
    r"(?:on:input|oninput|on:keyup|onkeyup)\s*=",
    re.I,
)
_SEARCH_TYPE_HANDLER = re.compile(
    r"(?:on:input|oninput|on:keyup|onkeyup)\s*=\s*\{"
    r"(?:"
    r"\s*([A-Za-z_][\w]*)\s*\}"
    r"|[^}]{0,240}?\b([A-Za-z_][\w]*)\s*\("
    r")",
    re.I,
)
_SEARCH_AS_YOU_TYPE_TRIGGER = re.compile(
    r"("
    r"\brun\s*\("
    r"|\bapi\.search\s*\("
    r"|setTimeout\s*\(\s*(?:async\s*)?(?:\(\s*\)\s*=>\s*)?(?:void\s+)?run\b"
    r"|debounce(?:d)?\s*\(\s*(?:async\s*)?(?:\(\s*\)\s*=>\s*)?(?:void\s+)?run\b"
    r")",
)
_SEARCH_PEOPLE_FROM_RUN = re.compile(
    r"("
    r"\brefreshPeople\s*\("
    r"|\bapplyStatus\s*\("
    r"|\bapi\.people\s*\("
    r"|invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']people[\"']"
    r")",
)
_SEARCH_DISABLED_PEOPLE = re.compile(
    r"disabled\s*=\s*\{[^}]*\bpeopleLoading\b",
    re.I,
)
_TANTIVY_WORD = re.compile(r"\btantivy\b", re.I)
_SEARCH_TYPE_HANDLER_SKIP = frozenset(
    {
        "preventDefault",
        "stopPropagation",
        "stopImmediatePropagation",
        "trim",
        "String",
        "Number",
        "Boolean",
        "clearTimeout",
        "setTimeout",
        "requestAnimationFrame",
        "queueMicrotask",
    }
)
_DOCS_TYPE_TO_SEARCH = re.compile(
    r"("
    r"search[- ]as[- ]you[- ]type"
    r"|as[- ]you[- ]type"
    r"|type[- ]to[- ]search"
    r"|typ(?:e|ing|es)\s+(?:a\s+token|in\s+(?:search\s+)?#q|in\s+the\s+query)"
    r".{0,80}(?:search(?:es)?|runs?\s+(?:a\s+)?search|starts?\s+search)"
    r"|typ(?:e|ing)\s+in\s+(?:search\s+)?#q\s+search"
    r")",
    re.I | re.S,
)
_DOCS_SEARCH_NOT_WAIT_PEOPLE = re.compile(
    r"("
    r"(?:search|#q|typ(?:e|ing)).{0,100}"
    r"(?:does not wait|doesn't wait|do not wait|without waiting|"
    r"not blocked|is not blocked|not wait)"
    r".{0,80}people"
    r"|"
    r"(?:does not wait|doesn't wait|without waiting|not blocked)"
    r".{0,80}people.{0,40}(?:list|refresh|rebuild)"
    r"|"
    r"people.{0,40}(?:list|refresh|rebuild).{0,60}"
    r"(?:does not block|doesn't block|do not block|not block)"
    r".{0,40}(?:search|#q)"
    r")",
    re.I | re.S,
)
_SEARCH_HITS_EMPTY = re.compile(
    r"("
    r"!\s*hits(?:\s*\.length)?\b"
    r"|hits\.length\s*(?:===?|<=|<)\s*0\b"
    r"|0\s*(?:===?|>=|>)\s*hits\.length"
    r"|hits\.length\s*<\s*1\b"
    r")",
)
_SEARCH_HITS_NONEMPTY = re.compile(
    r"("
    r"hits\.length\s*(?:>|>=|!==?)\s*0\b"
    r"|hits\.length\s*(?:>|>=)\s*[1-9]"
    r"|(?<!!)\bhits\.length\b"
    r")",
)
_SEARCH_PRE_IPC_EXPANDED = re.compile(
    r"\bexpanded\s*=\s*(?:null|undefined|void\s+0)\b"
)
_SEARCH_PRE_IPC_BODY = re.compile(r"\bbody\s*=\s*(?:\"\"|''|``)")
_SEARCH_PRE_IPC_HITINDEX = re.compile(r"\bhitIndex\s*=(?!=)")
_SEARCH_PRE_IPC_HITS_CLEAR = re.compile(r"\bhits\s*=\s*\[\s*\]")
_SEARCH_CLEAR_TIMEOUT = re.compile(r"\bclear(?:Timeout|Interval)\s*\(")
_SEARCH_TIMER_PERSON_BLUR = re.compile(r"personBlur", re.I)
_SEARCH_ERR_HANDLER = re.compile(r"\b(?:showErr|onError)\b")
_SEARCH_VOID_CALL = re.compile(r"\bvoid\s+([A-Za-z_$][\w$]*)\s*\(")
_SEARCH_RESTATE_DEBOUNCE_COMMENT = re.compile(
    r"Typing in #q searches\s*\(\s*debounce\s*\)",
    re.I,
)


def _search_q_open_tag(markup: str) -> str:
    """Open <Input>/<input> tag that carries id=q."""
    for m in re.finditer(r"<(?:Input|input)\b", markup, re.I):
        tag = _svelte_open_tag_at(markup, m.start())
        if _SEARCH_Q_ID.search(tag):
            return tag
    return ""


def _search_type_input_surface(src: str, q_tag: str) -> str:
    """Named / inline input handlers on the #q field (not the person filter)."""
    if not q_tag or not _SEARCH_TYPE_INPUT_ATTR.search(q_tag):
        return ""
    parts = [q_tag]
    names: list[str] = []
    for m in _SEARCH_TYPE_HANDLER.finditer(q_tag):
        names.extend(n for n in m.groups() if n)
    seen: set[str] = set()
    for name in names:
        if name in seen or name in _SEARCH_TYPE_HANDLER_SKIP:
            continue
        seen.add(name)
        inner = _ts_fn_body(src, name) or _function_body(src, name)
        if inner:
            parts.append(_expand_fn_calls(src, inner))
    return "\n".join(parts)


def _search_as_you_type_surface(src: str, markup: str) -> str:
    """Effect / #q-input blobs that can fire search when the query changes.

    Form onsubmit / chrome requestSubmit do not count (that is submit-only).
    Person-filter oninput does not count (different field).
    """
    parts: list[str] = []
    for arg in _svelte_effect_args(src):
        if not _SEARCH_Q_TOKEN.search(arg):
            continue
        parts.append(_expand_fn_calls(src, arg))
    q_tag = _search_q_open_tag(markup)
    input_surf = _search_type_input_surface(src, q_tag)
    if input_surf.strip():
        parts.append(input_surf)
    return "\n".join(parts)


def _has_search_as_you_type(src: str, markup: str) -> bool:
    surface = _search_as_you_type_surface(src, markup)
    return bool(surface.strip()) and bool(_SEARCH_AS_YOU_TYPE_TRIGGER.search(surface))


def _search_gated_on_people_loading(
    stack: list[tuple[str, str, str]],
) -> bool:
    """True if Search is only mounted when peopleLoading is false."""
    for kind, cond, _extra in stack:
        if not re.search(r"\bpeopleLoading\b", cond):
            continue
        if kind == "if" and re.search(r"!\s*peopleLoading", cond):
            return True
        if kind == "if-else" and not re.search(r"!\s*peopleLoading", cond):
            return True
    return False


def _cond_requires_empty_hits(cond: str) -> bool:
    """True if this {#if} only runs when the hits list is empty."""
    return bool(_SEARCH_HITS_EMPTY.search(_cond_code(cond)))


def _cond_requires_existing_hits(cond: str) -> bool:
    """True if this {#if} only runs when previous hits are on screen."""
    code = _cond_code(cond)
    if _SEARCH_HITS_EMPTY.search(code):
        return False
    return bool(_SEARCH_HITS_NONEMPTY.search(code))


def _stack_searching_true(stack: list[tuple[str, str, str]]) -> bool:
    """True if this markup sits in a branch shown while `searching` is true."""
    for kind, cond, _extra in stack:
        if not re.search(r"\bsearching\b", cond):
            continue
        code = _cond_code(cond)
        if kind == "if":
            return not _ident_negated(code, "searching")
        if kind == "if-else":
            return _ident_negated(code, "searching")
    return False


def _stack_requires_empty_hits(stack: list[tuple[str, str, str]]) -> bool:
    for kind, cond, _extra in stack:
        if kind == "if" and _cond_requires_empty_hits(cond):
            return True
        if kind == "if-else" and _cond_requires_existing_hits(cond):
            return True
    return False


def _stack_requires_existing_hits(stack: list[tuple[str, str, str]]) -> bool:
    for kind, cond, _extra in stack:
        if kind == "if" and _cond_requires_existing_hits(cond):
            return True
        if kind == "if-else" and _cond_requires_empty_hits(cond):
            return True
    return False


def _search_skeleton_stacks(
    markup: str, src: str
) -> list[list[tuple[str, str, str]]]:
    """Template stacks at each #203 skeleton hook in Search markup."""
    names = _owned_skeleton_names(src)
    return [
        _template_stack(markup, pos)
        for pos in _skeleton_hook_positions(markup, names)
    ]


def _blank_returning_blocks(src: str) -> str:
    """Blank `{ … return … }` so error-path assigns are not the start of run()."""
    chars = list(src)
    i = 0
    n = len(src)
    while i < n:
        nxt = _js_next(src, i)
        if nxt != i:
            i = nxt
            continue
        if src[i] == "{":
            close = _match_closer(src, i)
            if close > i and re.search(r"\breturn\b", src[i + 1 : close]):
                for k in range(i, close + 1):
                    if chars[k] not in "\n\r":
                        chars[k] = " "
                i = close + 1
                continue
        i += 1
    return "".join(chars)


def _run_before_ipc(body: str) -> str:
    """run() text before the first `api.search` (error-return blocks blanked)."""
    ipc_at = _first_substr_pos(body, ("api.search",))
    prefix = body if ipc_at < 0 else body[:ipc_at]
    return _blank_returning_blocks(prefix)


def _run_clears_debounce_timer(pre_ipc: str) -> bool:
    """True if the pre-IPC prefix clears a timer other than the person-blur one."""
    for m in _SEARCH_CLEAR_TIMEOUT.finditer(pre_ipc):
        open_p = pre_ipc.find("(", m.start())
        if open_p < 0:
            continue
        close = _match_closer(pre_ipc, open_p)
        arg = pre_ipc[open_p + 1 : close] if close > open_p else ""
        if _SEARCH_TIMER_PERSON_BLUR.search(arg):
            continue
        return True
    return False


def _js_unawaited_calls(blob: str, name: str) -> list[int]:
    """Close-paren index of each `name(` that is not `await` / a definition."""
    out: list[int] = []
    for m in re.finditer(rf"\b{re.escape(name)}\s*\(", blob):
        before = blob[: m.start()]
        if re.search(r"\bawait\s+$", before):
            continue
        if re.search(r"\b(?:async\s+)?function\s+$", before):
            continue
        if re.search(
            rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*"
            rf"(?:async\s*)?(?:function\s*)?$",
            before,
        ):
            continue
        open_p = m.end() - 1
        close = _match_closer(blob, open_p)
        if close > open_p:
            out.append(close)
    return out


def _trailing_catch_has_err(blob: str, close: int) -> bool:
    """True if `name(…)` is followed by `.catch(…showErr|onError…)`."""
    rest = blob[close + 1 :].lstrip()
    if not rest.startswith(".catch"):
        return False
    open_p = blob.find("(", close + 1)
    if open_p < 0:
        return False
    end = _match_closer(blob, open_p)
    if end < 0:
        return False
    return bool(_SEARCH_ERR_HANDLER.search(blob[open_p + 1 : end]))


def _fire_forget_people_caught(app: str, apply_body: str) -> bool:
    """applyStatus's unawaited refreshPeople (or a void wrapper) has .catch."""
    sites = _js_unawaited_calls(apply_body, "refreshPeople")
    if sites:
        return all(_trailing_catch_has_err(apply_body, close) for close in sites)
    for m in _SEARCH_VOID_CALL.finditer(apply_body):
        name = m.group(1)
        if name == "refreshPeople":
            continue
        inner = _ts_fn_body(app, name) or _function_body(app, name)
        if not inner or not re.search(r"\brefreshPeople\s*\(", inner):
            continue
        inner_sites = _js_unawaited_calls(inner, "refreshPeople")
        if inner_sites and all(
            _trailing_catch_has_err(inner, close) for close in inner_sites
        ):
            return True
        return False
    return False


def _hits_key_bails_on_searching(body: str) -> bool:
    """True if a hit-key if-return fires on `searching` while hits exist."""
    for cond in _review_if_return_conds(body):
        if not re.search(r"(?<![\w.])searching\b", cond):
            continue
        if _ident_negated(cond, "searching") and not re.search(
            r"(?<![!\w.])searching\b", cond
        ):
            continue
        # `searching && !hits.length` only — not a bail on a visible list.
        if (
            _SEARCH_HITS_EMPTY.search(cond)
            and "&&" in cond
            and "||" not in cond
        ):
            continue
        return True
    return False


def _js_comment_text(src: str) -> str:
    """`//` and `/*` blobs only (markup / strings skipped via `_js_next`)."""
    bits: list[str] = []
    i = 0
    n = len(src)
    while i < n:
        if src.startswith("//", i) or src.startswith("/*", i):
            end = _js_next(src, i)
            bits.append(src[i:end])
            i = end
            continue
        nxt = _js_next(src, i)
        i = nxt if nxt != i else i + 1
    return "\n".join(bits)


def _js_dot_catch_args(blob: str) -> list[str]:
    """Argument blobs of each `.catch(` (strings / comments skipped)."""
    out: list[str] = []
    i = 0
    n = len(blob)
    while i < n:
        nxt = _js_next(blob, i)
        if nxt != i:
            i = nxt
            continue
        if blob.startswith(".catch", i) and (
            i + 6 >= n or not (blob[i + 6].isalnum() or blob[i + 6] in "_$")
        ):
            j = i + 6
            while j < n and blob[j] in " \t\n\r":
                j += 1
            if j < n and blob[j] == "(":
                close = _match_closer(blob, j)
                if close > j:
                    out.append(blob[j + 1 : close])
                    i = close + 1
                    continue
        i += 1
    return out


def _js_handler_body(arg: str) -> str:
    """Normalize a `.catch` argument to a body-like blob.

    Bare `showErr` / `onError` become `showErr()` so the call regex hits.
    """
    s = arg.strip()
    if not s:
        return ""
    fn = re.match(r"(?:async\s+)?function\b", s)
    if fn:
        brace = s.find("{", fn.end())
        if brace >= 0:
            close = _match_closer(s, brace)
            if close > brace:
                return s[brace + 1 : close]
    arrow = re.match(
        r"(?:async\s+)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>",
        s,
    )
    if arrow:
        rest = s[arrow.end() :].lstrip()
        if rest.startswith("{"):
            close = _match_closer(rest, 0)
            if close > 0:
                return rest[1:close]
        return rest
    if re.fullmatch(r"[A-Za-z_$][\w$]*", s):
        return f"{s}()"
    return s


def _refresh_people_catch_blobs(refresh: str) -> list[str]:
    """try/catch bodies and `.catch` handlers inside refreshPeople."""
    blobs = [catch for _try, catch in _try_catch_blocks(refresh)]
    blobs.extend(_js_handler_body(arg) for arg in _js_dot_catch_args(refresh))
    return [b for b in blobs if b.strip()]


def _site_gen_guarded(body: str, pos: int, local: str, counter: str) -> bool:
    return _if_gen_eq_contains(body, pos, local, counter) or _same_block_gen_ne_return(
        body, pos, local, counter
    )


def _catch_err_positions(catch: str) -> list[int]:
    """showErr / onError / non-empty err= / throw sites in a catch blob."""
    pos: list[int] = []
    for m in re.finditer(r"\b(?:showErr|onError)\s*\(", catch):
        pos.append(m.start())
    for m in re.finditer(r"\berr\s*=(?!=)", catch):
        rest = catch[m.end() :].lstrip()
        if rest.startswith('""') or rest.startswith("''"):
            continue
        if re.match(r"['\"]\s*['\"]", rest):
            continue
        pos.append(m.start())
    for m in re.finditer(r"\bthrow\b", catch):
        pos.append(m.start())
    return pos


def _refresh_people_catch_gen_guarded(
    refresh: str, local: str, counter: str
) -> bool:
    """True if refreshPeople catch only surfaces errors when gen is current.

    Caller `void refreshPeople().catch(showErr)` is not gen-aware: a
    superseded `archive changed` still paints the banner. Requires a
    catch *inside* refreshPeople whose showErr / err= / throw is
    `if (gen === peopleGen)` (or `if (gen !== peopleGen) return`).
    """
    blobs = _refresh_people_catch_blobs(refresh)
    if not blobs:
        return False
    saw_surface = False
    for blob in blobs:
        sites = _catch_err_positions(blob)
        if not sites:
            continue
        saw_surface = True
        for pos in sites:
            if not _site_gen_guarded(blob, pos, local, counter):
                return False
    return saw_surface


def assert_search_as_you_type(crate: Path) -> None:
    """#270: typing in #q searches; do not hitch on a people refresh.

    `#q` / SearchPane needs an input / `$effect` / debounce path to `run()`
    / `api.search` — form submit alone is not enough. `run()` must not call
    `people` / `refreshPeople` / `applyStatus`. `#q` must not be disabled
    (or unmounted) because `peopleLoading` is true. Keep `#q`, `<mark>` /
    `splitSnippet`, `data-search-filters`. No Tantivy, no `fetch(`, no
    remote search. Docs: type-to-search; not blocked on people refresh.
    Do not rewrite #126 / #208 / #209 / #210 / #265.

    Follow-up (type-to-search lag): first in-flight (`searching`, no hits)
    still has the #203 skeleton. Later `run()` must not clear `expanded` /
    `hitIndex` / `body` before `api.search`. Previous `hits` stay until
    the gen-guarded assign — no `hits = []` at the start of `run()`, and
    `{#if searching}` must not paint the skeleton over existing hits.
    Do not rewrite #203 / #205 / the rest of #270.

    Follow-up (PR #288 review fold): `run()` clears the debounce timer
    (or a named timer) before `api.search`. `applyStatus` /
    `refreshPeople` fire-and-forget has `.catch` / `showErr` / `onError`.
    `onHitsKey` does not `return` solely on `searching` when hits exist.
    No restating “Typing in #q searches (debounce)” comment.

    Follow-up (PR #288 peopleGen catch): `refreshPeople` increments
    `peopleGen` and, in `catch`, only `showErr` / assigns error when
    `gen === peopleGen` (or equivalent). `applyStatus` still does not
    `await refreshPeople()`. Do not rewrite #265 / #205 / earlier #270.
    """
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#270: SearchPane.svelte required (type-to-search lives on #q)")
    app_path = crate / "web" / "App.svelte"
    src = search_path.read_text()
    cleaned = _without_comments(src)
    markup = _svelte_markup(src)
    surface = markup if markup.strip() else src
    app = app_path.read_text() if app_path.is_file() else ""
    app_clean = _without_comments(app)
    app_markup = _svelte_markup(app) if app else ""
    docs_search = repo_root() / "docs" / "user" / "search.md"
    docs_app = repo_root() / "docs" / "user" / "app.md"
    dtxt = ""
    if docs_app.is_file():
        dtxt += docs_app.read_text() + "\n"
    if docs_search.is_file():
        dtxt += docs_search.read_text()

    # 1) Primary red: typing in #q must run search (debounce OK).
    #    bind:value + form onsubmit is submit-only and is not enough.
    if not _has_search_as_you_type(cleaned, surface):
        fail(
            "#270: #q / SearchPane must search as you type "
            "(input / $effect / debounce → run() / api.search) — "
            "not submit-only"
        )

    # 2) run() (or the as-you-type path) must not wait on a people rebuild.
    run_body = _ts_fn_body(cleaned, "run") or _function_body(cleaned, "run")
    run_surf = _expand_fn_calls(cleaned, run_body) if run_body else ""
    type_surf = _search_as_you_type_surface(cleaned, surface)
    if _SEARCH_PEOPLE_FROM_RUN.search(run_surf) or _SEARCH_PEOPLE_FROM_RUN.search(
        type_surf
    ):
        fail(
            "#270: run() / the as-you-type path must not call people / "
            "refreshPeople / applyStatus (hits stay usable while a people "
            "refresh is in flight)"
        )

    # 3) #q is not disabled or unmounted because people are loading.
    q_tag = _search_q_open_tag(surface) or _search_q_open_tag(src)
    if q_tag and _SEARCH_DISABLED_PEOPLE.search(q_tag):
        fail(
            "#270: #q must not be disabled={peopleLoading} "
            "(typing stays usable while the people list fills)"
        )
    for block in _hook_element_blocks(app_markup, "data-chrome-search"):
        if _SEARCH_DISABLED_PEOPLE.search(block):
            fail(
                "#270: chrome search must not be disabled={peopleLoading} "
                "(#q / the same run() stays usable while people loads)"
            )
    q_pos = _SEARCH_Q_ID.search(surface)
    if q_pos and _search_gated_on_people_loading(
        _template_stack(surface, q_pos.start())
    ):
        fail(
            "#270: #q must not sit behind {#if !peopleLoading} "
            "(Search stays mounted while the people list fills)"
        )
    sp = re.search(r"<SearchPane\b", app_markup)
    if sp and _search_gated_on_people_loading(
        _template_stack(app_markup, sp.start())
    ):
        fail(
            "#270: SearchPane must not sit behind {#if !peopleLoading} "
            "(Search stays usable while the people list fills)"
        )

    # 4) Keep #q, <mark> / splitSnippet, data-search-filters.
    if not _SEARCH_Q_ID.search(surface) and not re.search(r"id=[\"']q[\"']", src):
        fail('#270: keep id="q" as the canonical query field')
    if not _SEARCH_MARK_TAG.search(surface) and not _SEARCH_MARK_TAG.search(src):
        fail("#270: keep <mark> siblings on the search snippet path (#126)")
    if not (
        _SEARCH_HIGHLIGHT_HELPER.search(cleaned)
        or _SEARCH_SNIPPET_SPLIT.search(cleaned)
        or re.search(r"\bsplitSnippet\b", src)
    ):
        fail("#270: keep splitSnippet / snippet split on the hit path (#126)")
    if _SEARCH_FILTERS_HOOK not in surface and _SEARCH_FILTERS_HOOK not in src:
        fail("#270: keep data-search-filters (#209)")

    # 5) Submit still works (as-you-type is extra, not a submit delete).
    if not re.search(
        r"(?:on:submit|onsubmit)\s*=|type\s*=\s*[\"']submit[\"']",
        surface,
        re.I,
    ):
        fail(
            "#270: keep form submit → run() "
            "(as-you-type is in addition to submit, not a replacement)"
        )

    # 6) No Tantivy / no fetch( / remote search.
    rust_path = crate / "src" / "main.rs"
    rust = rust_path.read_text() if rust_path.is_file() else ""
    pkg = (crate / "package.json").read_text() if (crate / "package.json").is_file() else ""
    toml = (crate / "Cargo.toml").read_text() if (crate / "Cargo.toml").is_file() else ""
    product_claim = "\n".join(
        (cleaned, app_clean, rust, pkg, toml, dtxt)
    )
    if _claim_without_negation(product_claim, _TANTIVY_WORD):
        fail("#270: not in scope — no Tantivy (keep FTS5; that is #82)")
    if _FETCH_CALL.search(cleaned) or _FETCH_CALL.search(
        _search_as_you_type_surface(cleaned, surface)
    ):
        fail("#270: not in scope — no fetch( / remote search")
    if _claim_without_negation(product_claim, _REMOTE_SEARCH_WORD):
        fail("#270: not in scope — no remote search")

    # 7) D24: type-to-search; not blocked on people refresh.
    if not dtxt.strip():
        fail(
            "#270: docs/user/app.md required — typing in #q searches; "
            "does not wait for the people list"
        )
    if not _DOCS_TYPE_TO_SEARCH.search(dtxt):
        fail(
            "#270: docs/user/app.md must say typing in #q searches "
            "(search-as-you-type / type-to-search; debounce OK)"
        )
    if not _DOCS_SEARCH_NOT_WAIT_PEOPLE.search(dtxt):
        fail(
            "#270: docs/user/app.md must say search is not blocked on "
            "a people refresh / does not wait for the people list"
        )

    # 8) First in-flight (searching, no hits) still has the #203 skeleton.
    skel_stacks = _search_skeleton_stacks(surface, src)
    first_inflight = [
        st
        for st in skel_stacks
        if _stack_searching_true(st) and not _stack_requires_existing_hits(st)
    ]
    if not first_inflight:
        fail(
            "#270: first in-flight (searching, no hits) must still show "
            "the #203 skeleton — do not paint “No hits” / “Type a query” "
            "while the first api.search is in flight"
        )

    # 9) Follow-up searching must not paint that skeleton over existing hits.
    followup_flash = [
        st
        for st in skel_stacks
        if _stack_searching_true(st) and not _stack_requires_empty_hits(st)
    ]
    if followup_flash:
        fail(
            "#270: {#if searching} must not paint the #203 skeleton over "
            "existing hits — keep the previous list until the new "
            "api.search reply applies (gate the skeleton on no hits)"
        )

    # 10) Follow-up run() does not clear expanded / hitIndex / body before IPC.
    pre_ipc = _run_before_ipc(run_body) if run_body else ""
    if (
        _SEARCH_PRE_IPC_EXPANDED.search(pre_ipc)
        or _SEARCH_PRE_IPC_BODY.search(pre_ipc)
        or _SEARCH_PRE_IPC_HITINDEX.search(pre_ipc)
    ):
        fail(
            "#270: follow-up run() must not clear expanded / hitIndex / "
            "body before api.search — reset those only when applying the "
            "new hits (or on error / idle clear)"
        )

    # 11) Previous hits stay until the gen-guarded assign.
    if _SEARCH_PRE_IPC_HITS_CLEAR.search(pre_ipc):
        fail(
            "#270: previous hits must stay until the gen-guarded assign "
            "— no hits = [] at the start of run()"
        )

    # 12) run() clears the debounce timer before api.search (submit / Retry /
    #     chrome requestSubmit must not leave a second FTS armed).
    pre_timer = _expand_fn_calls(cleaned, pre_ipc) if pre_ipc else ""
    if not _run_clears_debounce_timer(pre_timer or pre_ipc):
        fail(
            "#270: run() must clear the debounce timer (or a named timer) "
            "before api.search — submit / Retry / chrome requestSubmit "
            "must not leave a second FTS armed"
        )

    # 13) applyStatus / refreshPeople fire-and-forget surfaces errors.
    apply_body = _ts_fn_body(app_clean, "applyStatus") or _function_body(
        app_clean, "applyStatus"
    )
    if not apply_body or not _fire_forget_people_caught(app_clean, apply_body):
        fail(
            "#270: applyStatus / refreshPeople fire-and-forget must "
            ".catch(showErr) / onError — do not leave void refreshPeople() "
            "unhandled"
        )

    # 14) Hit-list keys still work while a follow-up search is in flight.
    hits_key = (
        _ts_fn_body(cleaned, "onHitsKey")
        or _function_body(cleaned, "onHitsKey")
        or _ts_fn_body(cleaned, "onHitKey")
        or _function_body(cleaned, "onHitKey")
    )
    if hits_key and _hits_key_bails_on_searching(hits_key):
        fail(
            "#270: onHitsKey must not return solely on searching when "
            "hits exist — gate keyboard nav on !hits.length only"
        )

    # 15) Do not restate the $effect body in a comment.
    if _SEARCH_RESTATE_DEBOUNCE_COMMENT.search(_js_comment_text(src)):
        fail(
            '#270: drop the restating “Typing in #q searches (debounce)” '
            "comment — a one-liner on why the effect must not track "
            "run()’s other inputs is OK"
        )

    # 16) refreshPeople increments peopleGen (keep the success-path guard).
    refresh = _ts_fn_body(app_clean, "refreshPeople") or _function_body(
        app_clean, "refreshPeople"
    )
    people_tok = _people_list_gen(refresh) if refresh else None
    if not refresh or not people_tok:
        fail(
            "#270: refreshPeople must increment peopleGen "
            "(and keep people = next only when that gen is current)"
        )

    # 17) catch only showErr / assigns error when gen === peopleGen.
    #     Today's void refreshPeople().catch(showErr) is not enough —
    #     a superseded archive-changed still paints the banner.
    if not _refresh_people_catch_gen_guarded(
        refresh, people_tok[0], people_tok[1]
    ):
        fail(
            "#270: refreshPeople catch must only showErr / assign error "
            "when gen === peopleGen — a superseded people() "
            "(archive changed) must not paint the banner on the new archive"
        )

    # 18) applyStatus still does not await the people rebuild.
    if apply_body and _PEOPLE_AWAIT_REFRESH.search(apply_body):
        fail(
            "#270: applyStatus must not await refreshPeople() "
            "(search still must not wait on a people rebuild)"
        )
