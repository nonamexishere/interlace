"""#423 — inspector group roster is as-of the focused message.

Wired immediately after assert_group_inspector_names (#322).

Pass the focused message id into the participants read so the roster
can reflect who was in the group at that message's sent_at. Reuse the
existing inThisGroup heading. Do not show joined/left dates in the
inspector. No new locale key for membership dates.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.last_read import _text, _web_file
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.scan import _function_body, _ts_fn_body, _without_comments

_ISSUE = "#423"

_API_CALL = re.compile(r"\bapi\.conversationParticipants\s*\(")
_CID_ONLY = re.compile(
    r"\bapi\.conversationParticipants\s*\(\s*"
    r"(?:cid|conversationId|conversation_id)\s*\)"
)
_MSG_ID_IN_CALL = re.compile(
    r"\bapi\.conversationParticipants\s*\([^;]{0,200}?"
    r"(?:message_id|messageId)"
)
_FOCUS_MSG = re.compile(
    r"timeline\s*\[\s*tlIndex\s*\]\s*\??\.?\s*message_id"
)
_IN_THIS_GROUP = re.compile(r"""t\s*\(\s*["']inThisGroup["']\s*\)""")
_JOINED_LEFT_T = re.compile(
    r"""t\s*\(\s*["'](?:joined|left|joinedAt|leftAt|"""
    r"""membershipJoined|membershipLeft|memberSince|inGroupAt)["']\s*\)"""
)
_JOINED_LEFT_UI = re.compile(r"\b(?:joined_at|left_at|joinedAt|leftAt)\b")
_GROUP_SECTION = re.compile(
    r"\{#if\s+includeGroups\s*&&\s*conversation_kind\s*===\s*[\"']group[\"']\s*\}"
    r"[\s\S]*?\{/if\}"
)
_API_SIG_MSG = re.compile(
    r"conversationParticipants\s*:\s*\([^)]*\b(?:messageId|message_id)\b"
)
_CMD_SIG_MSG = re.compile(
    r"fn\s+conversation_participants_cmd\s*\([\s\S]{0,300}?\bmessage_id\s*:"
)
_NEW_MEMBERSHIP_LOCALE = re.compile(
    r"^(?:joined|left|joinedAt|leftAt|membershipJoined|membershipLeft|"
    r"memberSince|inGroupAt|asOfMembership)$",
    re.I,
)


def _fn(src: str, name: str) -> str:
    return _ts_fn_body(src, name) or _function_body(src, name) or ""


def assert_group_membership_asof(crate: Path) -> None:
    """#423: group roster read passes focused message id; heading stays inThisGroup."""
    insp_path = _web_file(crate, "PeopleInspector.svelte")
    if not insp_path.is_file():
        fail(
            f"{_ISSUE}: PeopleInspector.svelte required "
            "(as-of roster lives on the existing in-this-group list)"
        )
    insp = _without_comments(_text(insp_path))
    load = _fn(insp, "loadGroupParticipants")
    body = load if load.strip() else insp

    # Primary red today: call is conversation-id only; focused message_id is not.
    if not _MSG_ID_IN_CALL.search(body) and not (
        _API_CALL.search(body) and _FOCUS_MSG.search(body)
    ):
        fail(
            f"{_ISSUE}: loadGroupParticipants must pass the focused "
            "timeline[tlIndex].message_id into api.conversationParticipants "
            "(not conversation id alone)"
        )
    if _CID_ONLY.search(body) and not _FOCUS_MSG.search(body):
        fail(
            f"{_ISSUE}: loadGroupParticipants must pass the focused "
            "timeline[tlIndex].message_id into api.conversationParticipants "
            "(not conversation id alone)"
        )

    api = _text(_web_file(crate, "api.ts"))
    if not _API_SIG_MSG.search(api):
        fail(
            f"{_ISSUE}: api.conversationParticipants must accept messageId "
            "(focused bubble) so the roster can be as-of that message"
        )

    cmd = _text(crate / "src" / "people_cmd.rs")
    if not _CMD_SIG_MSG.search(cmd):
        fail(
            f"{_ISSUE}: conversation_participants_cmd must take message_id "
            "and read who was in the group at that message"
        )

    # Heading stays inThisGroup; no new locale key; no joined/left chrome.
    if not _IN_THIS_GROUP.search(insp):
        fail(
            f"{_ISSUE}: reuse t(\"inThisGroup\") for the member list "
            "(no new heading ChromeKey)"
        )
    if _JOINED_LEFT_T.search(insp):
        fail(
            f"{_ISSUE}: do not show joined/left text in the inspector "
            "(no new locale string for membership dates)"
        )
    section_m = _GROUP_SECTION.search(insp)
    if section_m and _JOINED_LEFT_UI.search(section_m.group(0)):
        fail(
            f"{_ISSUE}: do not show joined or left text beside member names "
            "(filter-only list; reuse inThisGroup)"
        )

    en_path = crate / "web" / "lib" / "locales" / "en.ts"
    tr_path = crate / "web" / "lib" / "locales" / "tr.ts"
    en = _chrome_pack_entries(_text(en_path)) if en_path.is_file() else {}
    tr = _chrome_pack_entries(_text(tr_path)) if tr_path.is_file() else {}
    if "inThisGroup" not in en or "inThisGroup" not in tr:
        fail(f"{_ISSUE}: keep existing inThisGroup on both en.ts and tr.ts")
    for k in set(en) | set(tr):
        if _NEW_MEMBERSHIP_LOCALE.match(k):
            fail(
                f"{_ISSUE}: no new locale string for membership dates "
                f"(found {k!r}); reuse inThisGroup only"
            )
