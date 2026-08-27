"""Helpers extracted from timeline_rows.py (timeline_rows_lib)."""
from __future__ import annotations

from __future__ import annotations
import re
from pathlib import Path
from common import fail, repo_root
from tauri_gate.scan import (
    _BUBBLE_ME_VARS,
    _BUBBLE_THEM_VARS,
    _call_arg,
    _css_var,
    _function_body,
    _helper_with_callees,
    _HTML_BODY,
    _search_pane_blob,
    _svelte_markup,
    _timeline_block,
    _ts_function_body,
    _web_logic,
    _web_sources,
    _without_comments,
)
from tauri_gate.import_boot_guards import (
    _HUMAN_TIME_HELPERS,
    _PRE_WRAP,
)
from tauri_gate.media_linkify_lib import _SHOW_QUOTED
from tauri_gate.status_toasts_chrome import _MONTH_SHORT
from tauri_gate.status_toasts_toast import _person_detail_markup
from tauri_gate.timeline_grouping import (
    _CID_IMG,
    _DAY_HEADING,
    _FROM_ME_LAYOUT,
    _MAIL_ROW_GATE,
    _SUBJECT_TITLE_HELPER,
    _grouping_logic_src,
    _standalone_subject_bindings,
)
from tauri_gate.timeline_latest import _derived_body
_ALIGN_RIGHT = (
    "ml-auto",
    "justify-end",
    "self-end",
    "items-end",
    "margin-left: auto",
    "margin-inline-start: auto",
    "justify-content: flex-end",
    "justify-content: end",
    "align-self: flex-end",
    "align-self: end",
)
_ALIGN_LEFT = (
    "mr-auto",
    "justify-start",
    "self-start",
    "items-start",
    "margin-right: auto",
    "margin-inline-end: auto",
    "justify-content: flex-start",
    "justify-content: start",
    "align-self: flex-start",
    "align-self: start",
)
_BUBBLE_ME_USE = ("var(--bubble-me)", "var(--color-bubble-me)", "bg-bubble-me", "bubble-me")
_BUBBLE_THEM_USE = (
    "var(--bubble-them)",
    "var(--color-bubble-them)",
    "bg-bubble-them",
    "bubble-them",
)
_PREV_DAY = re.compile(
    r"("
    r"timeline\s*\[\s*i\s*-\s*1\s*\]"
    r"|prev(?:ious)?Day"
    r"|lastDay"
    r"|dayChanged"
    r"|isNewDay"
    r")",
    re.I,
)
# Calendar day of sent_at: UTC ISO prefix, UTC getters, or host-local getters / Intl.
# #268: slice(0, 10) is not the only legal day key.
_ISO_DAY = re.compile(
    r"("
    r"\.slice\s*\(\s*0\s*,\s*10\s*\)"
    r"|\.substring\s*\(\s*0\s*,\s*10\s*\)"
    r"|toISOString\s*\(\s*\)\s*\.\s*slice\s*\(\s*0\s*,\s*10\s*\)"
    r"|getUTCFullYear"
    r"|getFullYear"
    r"|getMonth"
    r"|getDate"
    r"|toLocaleDateString"
    r"|Intl\.DateTimeFormat"
    r")",
)
_LOCAL_DAY = re.compile(
    r"("
    r"toLocaleDateString"
    r"|\.getFullYear\s*\("
    r"|\.getMonth\s*\("
    r"|\.getDate\s*\("
    r")",
)
_YESTERDAY = re.compile(r"\byesterday\b", re.I)
_TZ_PICKER = re.compile(
    r"(<select\b[^>]{0,120}(timezone|timeZone|tz)\b"
    r"|bind:value=\{[^}]*timeZone"
    r"|name=[\"']timezone[\"'])",
    re.I,
)
_HEADING_IF = re.compile(r"\{#if\s+([^}]+)\}")
_SENT_AT_GUARD = re.compile(
    r"("
    r"sent_at\s*\?\.|"
    r"sent_at\s*&&|"
    r"!\s*(?:row\.)?sent_at|"
    r"if\s*\(\s*!\s*(?:iso|day)\b"
    r")",
)


# #268 — host-TZ day headings + short times; storage stays UTC ISO.
_DAY_KEY_HELPERS = (
    "utcDay",
    "utc_day",
    "localDay",
    "local_day",
    "hostDay",
    "calendarDay",
    "dayKey",
    "isoDay",
)
_TIME_HELPERS = (
    "utcTime",
    "localTime",
    "hostTime",
    "bubbleTime",
)
_UTC_ISO_DAY_SLICE = re.compile(
    r"\.slice\s*\(\s*0\s*,\s*10\s*\)|\.substring\s*\(\s*0\s*,\s*10\s*\)"
)
_LOCAL_CAL_GETTERS = re.compile(
    r"("
    r"\bgetFullYear\s*\("
    r"|\bgetMonth\s*\("
    r"|\bgetDate\s*\("
    r"|toLocaleDateString"
    r"|Intl\.DateTimeFormat"
    r")"
)
_LOCAL_HM_GETTERS = re.compile(
    r"("
    r"\bgetHours\s*\("
    r"|\bgetMinutes\s*\("
    r"|\bgetDate\s*\("
    r"|toLocaleString"
    r"|toLocaleTimeString"
    r"|Intl\.DateTimeFormat"
    r"|hour\s*:\s*[\"']2-digit[\"']"
    r")"
)
_FORCED_UTC_TZ = re.compile(r"timeZone\s*:\s*[\"']UTC[\"']")
_PARSE_ISO_UTC = re.compile(r"new\s+Date\s*\(|Date\.parse\s*\(")
_TZDATA_DEP = re.compile(
    r"("
    r"\btzdata\b"
    r"|\bchrono-tz\b"
    r"|\biana-time-zone\b"
    r"|\bmoment-timezone\b"
    r"|\bluxon\b"
    r"|timezonedb"
    r"|worldtimeapi"
    r")",
    re.I,
)
_SEARCH_TYPE_DATE = re.compile(r"type\s*=\s*\{?\s*[\"']date[\"']")
_WA_OR_WALLCLOCK = re.compile(
    r"("
    r"\bwhatsapp\b"
    r"|wall[-_ ]?clock"
    r"|\bexport\b"
    r")",
    re.I,
)
_ISO_DIGIT_ESCAPE = re.compile(
    r"("
    r"\.slice\s*\("
    r"|\.substring\s*\("
    r"|\.substr\s*\("
    r"|split\s*\(\s*[\"']T[\"']"
    r"|\.match\s*\("
    r")"
)
_DOCS_WA_WALL = re.compile(
    r"("
    r"whatsapp.{0,140}(?:wall[- ]?clock|export(?:ed)?\s+time|export\s+wall)"
    r"|(?:wall[- ]?clock|export(?:ed)?\s+time).{0,140}whatsapp"
    r")",
    re.I | re.S,
)
_DOCS_GMAIL_ZONE = re.compile(
    r"("
    r"gmail.{0,140}(?:host|Mac)(?:'s)?\s+time\s*zone"
    r"|(?:host|Mac)(?:'s)?\s+time\s*zone.{0,140}gmail"
    r"|zoned.{0,100}(?:gmail|time\s*zone|host|Mac)"
    r"|gmail.{0,100}zoned"
    r")",
    re.I | re.S,
)


def _fn_body(src: str, name: str) -> str:
    return _ts_function_body(src, name) or _function_body(src, name) or ""


def _host_local_day_ok(body: str) -> bool:
    """Parse ISO as UTC, then host-local calendar getters.

    Dual-path bodies may also slice WhatsApp wall-clock digits. Slice-only
    (no Date + local getters) still fails.
    """
    if not body or _FORCED_UTC_TZ.search(body):
        return False
    if not _PARSE_ISO_UTC.search(body):
        return False
    return bool(_LOCAL_CAL_GETTERS.search(body))


def _human_time_host_local(body: str) -> bool:
    """Month + hour:minute from host-local getters / Intl, not the UTC ISO slice."""
    if not body or _FORCED_UTC_TZ.search(body):
        return False
    if not _PARSE_ISO_UTC.search(body):
        return False
    has_month = bool(_MONTH_SHORT.search(body) or re.search(r"\bgetMonth\s*\(", body))
    has_local_hm = bool(_LOCAL_HM_GETTERS.search(body))
    return has_month and has_local_hm


def _called_day_keys(region: str) -> list[str]:
    found: list[str] = []
    for name in _DAY_KEY_HELPERS:
        if re.search(rf"\b{re.escape(name)}\s*\(", region):
            found.append(name)
    return found


def _split_tz_helper_names() -> tuple[str, ...]:
    names: list[str] = []
    for name in (
        *_DAY_KEY_HELPERS,
        "localDayLabel",
        "utcDayLabel",
        *_TIME_HELPERS,
        *_HUMAN_TIME_HELPERS,
    ):
        if name not in names:
            names.append(name)
    return tuple(names)


def _whatsapp_escape_ok(body: str) -> bool:
    """WhatsApp / omitted-platform path uses stored wall-clock digits."""
    if not body:
        return False
    if not _WA_OR_WALLCLOCK.search(body):
        return False
    return bool(_ISO_DIGIT_ESCAPE.search(body))


def _zoned_gmail_ok(body: str) -> bool:
    """Gmail / zoned path: new Date + host-local getters, not forced UTC."""
    if not body or _FORCED_UTC_TZ.search(body):
        return False
    if not _PARSE_ISO_UTC.search(body):
        return False
    return bool(_LOCAL_CAL_GETTERS.search(body) or _LOCAL_HM_GETTERS.search(body))


def _helper_call_args(src: str, name: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(rf"\b{re.escape(name)}\s*\(", src):
        out.append(_call_arg(src, m.end() - 1))
    return out


def _assert_typed_fn_body_visible() -> None:
    """Depth-0 `{` after `: string` is the function body, not a type object."""
    typed_day = (
        "export function localDay(iso: string | null | undefined): string {\n"
        "  return 'ok';\n"
        "}\n"
    )
    if not _ts_function_body(typed_day, "localDay").strip():
        fail(
            "#268: _ts_function_body must find the body of "
            "export function localDay(...): string {"
        )
    foo_src = "function foo(): string { return 1 }"
    if "return 1" not in _ts_function_body(foo_src, "foo"):
        fail(
            "#268: _ts_function_body must extract a typed "
            "function foo(): string { return 1 } body"
        )
# Sole body fallback that treats subject as body when body is empty — not a title.
_SUBJECT_BODY_FALLBACK_ONLY = re.compile(
    r"(?:body_text\s*\|\|\s*(?:(?:item\.)?row\.)?subject"
    r"|(?:displayBody|bodyText)\s*\(\s*(?:(?:item\.)?row\.)?body_text\s*\|\|"
    r"\s*(?:(?:item\.)?row\.)?subject)",
    re.I,
)
_QUOTE_SPLIT = re.compile(
    r"("
    # “On … wrote:” marker (literal, regex, or template).
    r"On\s+.{0,60}wrote\s*:"
    r"|On\s+\\?\$\{[^}]{0,40}\}\s+wrote"
    r"|/On\s+.+?wrote\s*:/"
    r"|[\"']On [\"'][^;]{0,80}wrote"
    r"|[\"']wrote:[\"']"
    r"|wrote:"
    # Named pure split / fold helpers (synthetic placeholders only in tests).
    r"|splitQuoted(?:Body|Tail|Text)?"
    r"|splitQuote(?:d)?(?:Body|Tail)?"
    r"|quoteTail"
    r"|quotedTail"
    r"|quotedBody"
    r"|foldQuoted"
    r"|quoteSplit"
    r"|mailQuote"
    r"|extractQuoted"
    r"|stripQuoted"
    r"|unquotedBody"
    r"|bodyWithoutQuote"
    r"|mainBody(?:Text)?"
    # Leading “>” quote lines.
    r"|startsWith\s*\(\s*[\"']>[\"']"
    r"|lines?\s*\.?\s*(?:filter|map|find|some|every|startsWith)"
    r"[^;]{0,80}[\"']>[\"']"
    r"|[\"']>[\"']\s*===?\s*.{0,20}(?:trim|charAt|\[0\])"
    r")",
    re.I | re.S,
)
_SEND_MAIL_UI = re.compile(
    r"("
    r">\s*Send\s+(?:mail|email|message)\s*<"
    r"|[\"']Send (?:mail|email|message)[\"']"
    r"|compose(?:Mail|Email|Message)"
    r"|data-compose-mail"
    r"|reply-all"
    r"|Reply all"
    r"|mailto:"
    r"|type=[\"']email[\"'][^>]{0,80}compose"
    r"|placeholder=[\"'][^\"']*(?:Write a (?:mail|reply)|Compose)"
    r")",
    re.I,
)
_WA_PLAIN_BODY = re.compile(
    r"("
    r"(?:platform|row\.platform)\s*===?\s*[\"']whatsapp[\"']"
    r"|[\"']whatsapp[\"']\s*===?\s*(?:platform|row\.platform)"
    r"|\bisWhats?App\b"
    r"|!\s*(?:isMail|isEmail|isGmail|mailRow|emailRow)\b"
    r"|\{:else\b"
    r")",
    re.I,
)

__all__ = [
    "_ALIGN_RIGHT",
    "_ALIGN_LEFT",
    "_BUBBLE_ME_USE",
    "_BUBBLE_THEM_USE",
    "_PREV_DAY",
    "_ISO_DAY",
    "_LOCAL_DAY",
    "_YESTERDAY",
    "_TZ_PICKER",
    "_HEADING_IF",
    "_SENT_AT_GUARD",
    "_DAY_KEY_HELPERS",
    "_TIME_HELPERS",
    "_UTC_ISO_DAY_SLICE",
    "_LOCAL_CAL_GETTERS",
    "_LOCAL_HM_GETTERS",
    "_FORCED_UTC_TZ",
    "_PARSE_ISO_UTC",
    "_TZDATA_DEP",
    "_SEARCH_TYPE_DATE",
    "_WA_OR_WALLCLOCK",
    "_ISO_DIGIT_ESCAPE",
    "_DOCS_WA_WALL",
    "_DOCS_GMAIL_ZONE",
    "_fn_body",
    "_host_local_day_ok",
    "_human_time_host_local",
    "_called_day_keys",
    "_split_tz_helper_names",
    "_whatsapp_escape_ok",
    "_zoned_gmail_ok",
    "_helper_call_args",
    "_assert_typed_fn_body_visible",
    "_SUBJECT_BODY_FALLBACK_ONLY",
    "_QUOTE_SPLIT",
    "_SEND_MAIL_UI",
    "_WA_PLAIN_BODY",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_BUBBLE_ME_VARS",
    "_BUBBLE_THEM_VARS",
    "_css_var",
    "_helper_with_callees",
    "_HTML_BODY",
    "_search_pane_blob",
    "_svelte_markup",
    "_timeline_block",
    "_web_logic",
    "_web_sources",
    "_without_comments",
    "_HUMAN_TIME_HELPERS",
    "_PRE_WRAP",
    "_SHOW_QUOTED",
    "_person_detail_markup",
    "_CID_IMG",
    "_DAY_HEADING",
    "_FROM_ME_LAYOUT",
    "_MAIL_ROW_GATE",
    "_SUBJECT_TITLE_HELPER",
    "_grouping_logic_src",
    "_standalone_subject_bindings",
    "_derived_body",
    "annotations",
    "_call_arg",
    "_function_body",
    "_ts_function_body",
    "_MONTH_SHORT",
]
