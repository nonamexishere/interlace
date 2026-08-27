"""Helpers extracted from search_filters.py (search_filters_lib)."""
from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import fail

from tauri_gate.scan import (
    _search_pane_blob,
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

__all__ = [
    "_CORE_SEARCH_PLATFORM_TOKENS",
    "_INVENTED_SEARCH_PLATFORM_TOKENS",
    "_SEARCH_PLATFORM_FREE_TEXT",
    "_SEARCH_PLATFORM_SELECT",
    "_SEARCH_OPTION_VALUE",
    "_SEARCH_OPTION_VALUE_ATTR",
    "_SEARCH_SELECT_ITEM_VALUE",
    "_SEARCH_API_PLATFORM_ARG",
    "_SEARCH_PLATFORM_ARG",
    "_SEARCH_PLATFORM_EMPTY_AS_ANY",
    "_SEARCH_PLATFORM_STATE_FLOW",
    "_search_platform_option_values",
    "_CORE_SEARCH_KIND_TOKENS",
    "_INVENTED_SEARCH_KIND_TOKENS",
    "_SEARCH_KIND_STATE",
    "_SEARCH_KIND_FREE_TEXT",
    "_SEARCH_KIND_SELECT",
    "_SEARCH_API_KIND_ARG",
    "_SEARCH_KIND_EMPTY_AS_ANY",
    "_SEARCH_KIND_STATE_FLOW",
    "_CORE_SEARCH_ATTACHMENT_TOKENS",
    "_INVENTED_SEARCH_ATTACHMENT_TOKENS",
    "_SEARCH_ATTACHMENT_STATE",
    "_SEARCH_ATTACHMENT_FREE_TEXT",
    "_SEARCH_ATTACHMENT_SELECT",
    "_SEARCH_API_ATTACHMENT_ARG",
    "_SEARCH_ATTACHMENT_EMPTY_AS_ANY",
    "_SEARCH_ATTACHMENT_STATE_FLOW",
    "re",
    "Path",
    "fail",
    "_search_pane_blob",
    "_svelte_markup",
    "_without_comments",
    "annotations",
]
