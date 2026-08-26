"""Search platform / kind / attachment filter asserts. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import fail

from tauri_gate.scan import (
    _svelte_markup,
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
