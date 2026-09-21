"""#377 — click a group participant to open that person (confirmed mix).

Wired immediately after assert_az_letter_rail (#376).

Confirmed mix (2026-09-22): nullable person_id on ConversationParticipantName
from conversation_participants ⨝ identities LEFT JOIN live person_identities
⨝ persons (tombstoned_at IS NULL). Click uses that id. No extra IPC. No
name-match. No invent-person. New leftover ChromeKey toast, stay put.
t("self") only when personById(person_id)?.is_self; leftover never (self).
Click already-open Berk is a no-op (do not selectPerson / reload). Tombstone
= leftover. includeGroups stays true. Names stay display_name || value.
Button type="button" inside data-group-participants <li>. DMs no member list.

Not extra IPC. Not name-match. Not invent person. Not reload when already
selected. Keep #322 / #374 / #376 / #213 / #366.

Placeholders Ada / Berk / Self. Same ChromeKey on en.ts + tr.ts.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.group_inspector_names import (
    _CONV_ID_BIND,
    _DISPLAY_THEN_VALUE,
    _FROM_CP,
    _GROUP_KIND,
    _INCLUDE_GROUPS,
    _JOIN_IDENT,
    _KIND_DM,
    _KIND_EMAIL,
    _ORDER_ID,
    _PERSON_COLLAPSE,
    _RAW_ID_LABEL,
    _people_core_blob,
)
from tauri_gate.include_groups import _WRITE_GROUPS
from tauri_gate.last_read import _text, _web_file
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.people_inspector_lib import _strip_tag_attrs
from tauri_gate.scan import (
    CSP,
    _expand_fn_calls,
    _function_body,
    _match_closer,
    _rust_function_body,
    _svelte_markup,
    _tauri_rust_blob,
    _template_stack,
    _ts_fn_body,
    _without_comments,
)
from tauri_gate.status_toasts_chrome import _windows_around
from tauri_gate.timeline_gmail_labels import _rust_struct_body, _ts_type_body

_ISSUE = "#377"
_PRIMARY = (
    f"{_ISSUE}: data-group-participants member names must be "
    'type="button" controls (not dead <li> text)'
)

_GROUP_UL = re.compile(
    r"<ul\b[^>]*\bdata-group-participants\b[^>]*>[\s\S]*?</ul>",
    re.I,
)
_MEMBER_EACH = re.compile(
    r"\{#each\s+[^}]*\bparticipants\b[^}]*\}[\s\S]*?\{/each\}",
    re.I,
)
_TYPE_BUTTON = re.compile(r"""type\s*=\s*["']button["']""")
_NATIVE_BUTTON = re.compile(r"<button\b", re.I)
_OWNED_BUTTON = re.compile(r"<Button\b")
_ANCHOR = re.compile(r"<a\b", re.I)
_FOCUS_RING = re.compile(r"focus-visible:ring-2")
_FOCUS_RING_COLOR = re.compile(r"focus-visible:ring-ring")
_LUCIDE = re.compile(r"\blucide-svelte\b|<User\b|<Users\b|<CircleUser\b")
_BOUNCE = re.compile(r"\b(?:bounce|spring|elastic)\b", re.I)
_PERSON_AVATAR = re.compile(r"<PersonAvatar\b")
_IMG = re.compile(r"<img\b", re.I)
_ONCLICK = re.compile(r"\bon:?click\s*=\s*\{")
_PERSON_ID_FIELD = re.compile(r"\bperson_id\b")
_TS_PERSON_ID = re.compile(
    r"\bperson_id\s*\??\s*:\s*(?:number\s*\|\s*null|null\s*\|\s*number|number)\b"
)
_RS_PERSON_ID = re.compile(r"\bperson_id\s*:\s*Option\s*<\s*i64\s*>")
_DTO_IS_SELF = re.compile(r"\bis_self\s*\??\s*:")
_SELECT = re.compile(r"\b(?:onSelectPerson|selectPerson|loadPerson)\b")
_SELECT_IDENTITY = re.compile(
    r"\b(?:onSelectPerson|selectPerson|loadPerson)\s*\(\s*"
    r"(?:[\w$.]*\bidentity_id\b)"
)
_SELECT_PERSON_ID = re.compile(
    r"\b(?:onSelectPerson|selectPerson|loadPerson)\s*\(\s*"
    r"(?:[\w$.]*\bperson_id\b|\w+)"
)
_SELECTED_EQ = re.compile(
    r"(?:"
    r"(?:person_id|pid|id)\s*===?\s*selectedId"
    r"|selectedId\s*===?\s*(?:person_id|pid|id)"
    r"|(?:person_id|pid|id)\s*!==?\s*selectedId"
    r"|selectedId\s*!==?\s*(?:person_id|pid|id)"
    r")"
)
_PERSON_ID_NULL = re.compile(
    r"(?:"
    r"(?:person_id|pid)\s*==\s*null"
    r"|(?:person_id|pid)\s*===\s*undefined"
    r"|(?:person_id|pid)\s*==\s*undefined"
    r"|!\s*(?:[\w$.]*\bperson_id\b|pid)"
    r"|(?:person_id|pid)\s*\?\?"
    r"|typeof\s+(?:[\w$.]*\bperson_id\b|pid)"
    r"|== null|===\s*null"
    r")"
)
_SHOW_TOAST = re.compile(r"\bshowToast\s*\(")
_T_CALL = re.compile(r"""\bt\s*\(\s*["']([A-Za-z_][A-Za-z0-9_]*)["']\s*\)""")
_T_SELF = re.compile(r"""\bt\s*\(\s*["']self["']\s*\)""")
_IS_SELF = re.compile(r"\bis_self\b")
_PERSON_BY_ID = re.compile(r"\bpersonById\s*\(")
_SELF_BY_NAME = re.compile(
    r"""(?:display_name|value)\s*===?\s*["']Self["']"""
    r"""|["']Self["']\s*===?\s*(?:[\w$.]*\bdisplay_name\b|[\w$.]*\bvalue\b)"""
)
_REUSE_TOAST = re.compile(
    r"""showToast\s*\(\s*["']Could not (?:open|copy|reveal)["']"""
    r"""|showToast\s*\(\s*t\s*\(\s*["'](?:openOriginalMissing|archiveCopied|importRunning)["']"""
)
_SHOW_ERR = re.compile(r"\bshowErr\s*\(")
_INVENT = re.compile(
    r"("
    r"INSERT\s+INTO\s+persons"
    r"|createPerson|personCreate|create_person|person_create"
    r"|\bapi\.merge\s*\("
    r"|\bonMerge\s*\("
    r"|\bunlink\s*\("
    r"|linkIdentity|link_identity"
    r")",
    re.I,
)
_NAME_MATCH = re.compile(
    r"("
    r"people\s*\.find\s*\("
    r"|display_name\s*===?"
    r"|identity_values[^\n]{0,80}participant"
    r"|participant[^\n]{0,80}identity_values"
    r")",
    re.I,
)
_EXTRA_CMD = re.compile(
    r"("
    r"person_for_identity|live_person_for_identity"
    r"|identity_person|person_of_identity"
    r"|personForIdentity|livePersonForIdentity"
    r"|identityPerson|personOfIdentity"
    r")",
    re.I,
)
_INVOKE = re.compile(r"""\binvoke\s*(?:<[^>]*>)?\s*\(\s*["']""")
_PERSON_IDENTITIES = re.compile(r"\bperson_identities\b", re.I)
_PERSONS_JOIN = re.compile(r"\bpersons\b", re.I)
_TOMBSTONE_LIVE = re.compile(r"tombstoned_at\s+IS\s+NULL", re.I)
_MERGED_INTO = re.compile(r"\bmerged_into\b", re.I)
_WRITE_GROUPS_FALSE = re.compile(
    r"writeIncludeGroupsPref\s*\(\s*false\s*\)"
)
_EACH_KEY_IDENTITY = re.compile(
    r"\{#each\s+[^}]*\bparticipants\b[^}]*\(\s*[\w$.]*\bidentity_id\b"
)
_EACH_KEY_PERSON = re.compile(
    r"\{#each\s+[^}]*\bparticipants\b[^}]*\(\s*[\w$.]*\bperson_id\b"
)
_COLLAPSE_ROWS = re.compile(
    r"("
    r"uniquePerson|uniqPerson|byPersonId"
    r"|\.reduce\s*\([^)]*person_id"
    r"|groupBy\s*\([^)]*person_id"
    r")",
    re.I,
)
_EDITOR = re.compile(
    r"("
    r"add member|remove member|invite to group|leave group|"
    r"edit membership|onAddMember|onRemoveMember|addParticipant|"
    r"removeParticipant"
    r")",
    re.I,
)
_JID = re.compile(r"\bwhatsapp_jid\b|\bwa_jid\b|\bjid\b", re.I)
_FETCH = re.compile(r"\bfetch\s*\(|\baxios\b|tauri-plugin-http")
_HTML = re.compile(r"\{@html\b|\binnerHTML\b")
_CHROME_TRUE = re.compile(r"\bshowPersonChrome\s*=\s*true\b")
_MAIL_HOOK = re.compile(r"\bdata-mail-recipients\b")
_LETTER_RAIL = re.compile(r"\bdata-letter-rail\b")
_LETTER_HEADING = re.compile(r"\bdata-letter-heading\b")
_IN_THIS_GROUP = re.compile(r"""t\s*\(\s*["']inThisGroup["']\s*\)""")
_INSPECTOR_HOOK = re.compile(r"\bdata-person-inspector\b")
_LOAD_PERSON_DEF = re.compile(
    r"function\s+loadPerson\s*\([^)]*groups\s*=\s*includeGroups"
    r"|loadPerson\s*=\s*(?:async\s*)?\([^)]*groups\s*=\s*includeGroups"
)
_SELECT_PERSON_DEF = re.compile(
    r"function\s+selectPerson\s*\([^)]*groups\s*=\s*includeGroups"
    r"|selectPerson\s*\([^)]*groups\s*=\s*includeGroups"
)
_PLACEHOLDER_CHROME = re.compile(r"\bAda\b|\bBerk\b|\bSelf\b")
_KEEP_HEADING_KEYS = frozenset(
    {
        "inspector",
        "identities",
        "lastActivity",
        "inThisGroup",
        "includeGroups",
        "media",
        "personNotes",
        "saveNotes",
        "personName",
        "renameConfirm",
    }
)
_DOCS_CLICK = re.compile(
    r"("
    r"click.{0,160}(?:open|select).{0,80}person"
    r"|opens? that person"
    r"|click.{0,40}Berk"
    r"|participant.{0,80}(?:control|button|click).{0,80}person"
    r")",
    re.I | re.S,
)
_DOCS_LEFTOVER = re.compile(
    r"("
    r"leftover.{0,120}toast"
    r"|no (?:live )?person.{0,80}toast"
    r"|toast.{0,80}(?:stay|leftover|no navigation)"
    r"|stay put.{0,80}toast"
    r")",
    re.I | re.S,
)
_DOCS_DM = re.compile(
    r"("
    r"DMs?(?: do not| don't| does not| never).{0,80}"
    r"(?:member|participant|roster)"
    r")",
    re.I | re.S,
)
_DOCS_TEXT = re.compile(
    r"("
    r"names? (?:are|is) text.{0,40}not.{0,20}ids?"
    r"|text, not.{0,20}ids?"
    r")",
    re.I | re.S,
)
_HANDLER = re.compile(r"generate_handler!\s*\[(.*?)\]", re.S)
_OPEN_FN = re.compile(
    r"(?:async\s+)?function\s+(\w*(?:participant|openPerson|openMember|"
    r"openLive|openGroup)[A-Za-z_]*)"
    r"|(?:const|let)\s+(\w*(?:participant|openPerson|openMember|"
    r"openLive|openGroup)[A-Za-z_]*)\s*=",
    re.I,
)


def _fn(src: str, name: str) -> str:
    return _ts_fn_body(src, name) or _function_body(src, name) or ""


def _group_ul(markup: str) -> str:
    m = _GROUP_UL.search(markup)
    return m.group(0) if m else ""


def _member_each(ul: str) -> str:
    m = _MEMBER_EACH.search(ul)
    return m.group(0) if m else ul


def _if_conds_at(markup: str, pos: int) -> list[str]:
    return [a for kind, a, _b in _template_stack(markup, pos) if kind == "if"]


def _onclick_spans(markup: str) -> list[str]:
    out: list[str] = []
    for m in _ONCLICK.finditer(markup):
        start = markup.find("{", m.start())
        if start < 0:
            continue
        end = _match_closer(markup, start)
        if end > start:
            out.append(markup[start : end + 1])
    return out


def _click_blob(insp: str, member: str) -> str:
    parts = [member, *_onclick_spans(member)]
    for m in _OPEN_FN.finditer(insp):
        name = m.group(1) or m.group(2)
        if name:
            parts.append(_fn(insp, name))
    blob = "\n".join(parts)
    return blob + "\n" + _expand_fn_calls(insp, blob, depth=2)


def _inspector_mount(shell: str) -> str:
    m = re.search(r"<PeopleInspector\b", shell)
    if not m:
        return ""
    start = m.start()
    end = shell.find("</PeopleInspector>", start)
    if end < 0:
        end = start + 900
    else:
        end += len("</PeopleInspector>")
    return shell[start:end]


def _select_clause(sql: str) -> str:
    m = re.search(r"\bSELECT\b", sql, re.I)
    if not m:
        return sql
    rest = sql[m.end() :]
    frm = re.search(r"\bFROM\b", rest, re.I)
    return rest[: frm.start()] if frm else rest[:800]


def assert_group_participant_open(crate: Path) -> None:
    """#377: group participant name is a control; live person_id opens that person."""
    root = repo_root()
    insp_path = _web_file(crate, "PeopleInspector.svelte")
    if not insp_path.is_file():
        fail(
            f"{_ISSUE}: PeopleInspector.svelte required "
            "(group participant open lives on data-group-participants)"
        )

    insp_raw = _text(insp_path)
    insp = _without_comments(insp_raw)
    markup = _svelte_markup(insp_raw)
    ul = _group_ul(markup) or _group_ul(insp)
    each = _member_each(ul) if ul else ""
    member = each or ul

    # 1) Primary red today — name is a type="button" control in the #322 list.
    if not ul:
        fail(
            f"{_ISSUE}: keep data-group-participants "
            "(#322 in-this-group list; names become controls there)"
        )
    if not _TYPE_BUTTON.search(member) or not _NATIVE_BUTTON.search(member):
        fail(_PRIMARY)

    # 2) Chrome — native button, focus-visible ring, no Lucide / bounce / faces.
    if not _FOCUS_RING.search(member) or not _FOCUS_RING_COLOR.search(member):
        fail(
            f"{_ISSUE}: participant button needs focus-visible:ring-2 "
            "focus-visible:ring-ring"
        )
    if _OWNED_BUTTON.search(member):
        fail(
            f"{_ISSUE}: participant name is a native type=\"button\", "
            "not the outline Button primitive"
        )
    if _ANCHOR.search(member):
        fail(f"{_ISSUE}: participant name is a button, not an <a>")
    if _LUCIDE.search(member) or _LUCIDE.search(ul):
        fail(f"{_ISSUE}: no Lucide icon on the member list")
    if _BOUNCE.search(member):
        fail(f"{_ISSUE}: reduced motion — no bounce on participant click")
    if _PERSON_AVATAR.search(ul) or _IMG.search(ul):
        fail(
            f"{_ISSUE}: no PersonAvatar / <img> inside data-group-participants "
            "(#366 / PHOTO is a later ticket)"
        )

    shell_path = _web_file(crate, "PeopleShell.svelte")
    tl_path = _web_file(crate, "TimelinePane.svelte")
    api_path = _web_file(crate, "api.ts")
    side_path = _web_file(crate, "PeopleSidebar.svelte")
    az_path = _web_file(crate, "azLetter.ts")
    prefs_path = _web_file(crate, "PeoplePrefs.ts")
    en_path = crate / "web" / "lib" / "locales" / "en.ts"
    tr_path = crate / "web" / "lib" / "locales" / "tr.ts"
    docs_path = root / "docs" / "user" / "app.md"
    people_rs_path = root / "crates" / "interlace-core" / "src" / "people.rs"
    i18n_path = crate / "web" / "lib" / "i18n.ts"
    ent = _text(crate / "Interlace.entitlements")
    conf = _text(crate / "tauri.conf.json")

    shell_raw = _text(shell_path)
    shell = _without_comments(shell_raw)
    tl = _without_comments(_text(tl_path))
    api = _text(api_path)
    side = _text(side_path)
    docs = _text(docs_path)
    people_rs = _text(people_rs_path)
    i18n = _text(i18n_path)
    rust = _tauri_rust_blob(crate)
    core = _people_core_blob(root)
    click = _click_blob(insp, member)
    mount = _inspector_mount(shell_raw) or _inspector_mount(shell)
    qbody = _rust_function_body(core, "conversation_participant_names")
    api_dto = _ts_type_body(api, "ConversationParticipantName")
    rs_dto = _rust_struct_body(people_rs, "ConversationParticipantName")
    en = _chrome_pack_entries(_text(en_path)) if en_path.is_file() else {}
    tr = _chrome_pack_entries(_text(tr_path)) if tr_path.is_file() else {}

    # 3) payload-person-id — nullable on the existing #322 DTO; no extra IPC.
    if not api_dto:
        fail(
            f"{_ISSUE}: api.ts ConversationParticipantName required "
            "(nullable person_id on the existing names payload)"
        )
    if not _TS_PERSON_ID.search(api_dto):
        fail(
            f"{_ISSUE}: ConversationParticipantName must grow nullable "
            "person_id (number | null) — click uses that id, not a second command"
        )
    if not rs_dto or not _RS_PERSON_ID.search(rs_dto):
        fail(
            f"{_ISSUE}: people.rs ConversationParticipantName must add "
            "person_id: Option<i64> (same JSON as api.ts)"
        )
    if _DTO_IS_SELF.search(api_dto) or _DTO_IS_SELF.search(rs_dto):
        fail(
            f"{_ISSUE}: do not add is_self on the names payload "
            "(suffix uses personById(person_id)?.is_self)"
        )
    if _EXTRA_CMD.search(rust) or _EXTRA_CMD.search(api) or _EXTRA_CMD.search(click):
        fail(
            f"{_ISSUE}: do not add a second identity→person command "
            "(click uses list person_id; no extra IPC)"
        )
    if _INVOKE.search(click):
        fail(
            f"{_ISSUE}: click must not invoke a new command "
            "(person_id is already on the #322 list JSON)"
        )
    handlers = _HANDLER.search(rust)
    if handlers and _EXTRA_CMD.search(handlers.group(1)):
        fail(f"{_ISSUE}: do not register a second identity→person command")

    # 4) tombstone = leftover — live join only; no merged_into; no name collapse.
    if not qbody:
        fail(
            f"{_ISSUE}: conversation_participant_names required "
            "(add nullable person_id via live person_identities ⨝ persons)"
        )
    if not _FROM_CP.search(qbody) or not _JOIN_IDENT.search(qbody):
        fail(
            f"{_ISSUE}: keep conversation_participants ⨝ identities "
            "for that conversation_id (#322 grain)"
        )
    if not _CONV_ID_BIND.search(qbody):
        fail(f"{_ISSUE}: names query still binds conversation_id (#322)")
    if not _PERSON_IDENTITIES.search(qbody) or not _PERSONS_JOIN.search(qbody):
        fail(
            f"{_ISSUE}: nullable person_id comes from person_identities ⨝ "
            "persons (live rows only)"
        )
    if not _TOMBSTONE_LIVE.search(qbody):
        fail(
            f"{_ISSUE}: tombstone is not live — JOIN / subquery must use "
            "tombstoned_at IS NULL so a tombstone-only link serializes person_id null"
        )
    if _MERGED_INTO.search(qbody):
        fail(f"{_ISSUE}: do not chase merged_into (tombstone-only → leftover toast)")
    select_sql = _select_clause(qbody)
    if _PERSON_COLLAPSE.search(member) or re.search(
        r"\bp\.display_name\b|\bpersons\.\w*display_name\b", select_sql, re.I
    ):
        fail(
            f"{_ISSUE}: do not SELECT persons.display_name "
            "(two identities of Berk stay two controls; labels stay identity text)"
        )
    if not _ORDER_ID.search(qbody):
        fail(f"{_ISSUE}: keep ORDER BY identity_id (#322)")
    if _INVENT.search(qbody):
        fail(f"{_ISSUE}: names query must not INSERT / create a person")

    # 5) click live id → selectPerson / loadPerson; already-selected is a no-op.
    if not _ONCLICK.search(member) and not _SELECT.search(click):
        fail(
            f"{_ISSUE}: click Berk with a live person_id must call "
            "selectPerson / loadPerson (wire onSelectPerson from PeopleShell)"
        )
    if not _SELECT.search(click):
        fail(
            f"{_ISSUE}: live person_id click calls onSelectPerson / loadPerson / "
            "selectPerson with that id"
        )
    if _SELECT_IDENTITY.search(click):
        fail(
            f"{_ISSUE}: click uses person_id, not identity_id "
            "(do not match by display name either)"
        )
    if not _PERSON_ID_FIELD.search(click):
        fail(f"{_ISSUE}: click path reads participant.person_id (not a name match)")
    if "onSelectPerson" not in mount and "loadPerson" not in mount:
        fail(
            f"{_ISSUE}: PeopleShell must pass onSelectPerson / loadPerson "
            "into PeopleInspector (sidebar path)"
        )
    if not _LOAD_PERSON_DEF.search(shell) and not _SELECT_PERSON_DEF.search(tl):
        fail(
            f"{_ISSUE}: loadPerson / selectPerson still default groups = "
            "includeGroups (keep include-groups on)"
        )
    if not _SELECT.search(shell) or "selectPerson" not in shell:
        fail(
            f"{_ISSUE}: PeopleShell loadPerson must still call "
            "timelinePane.selectPerson"
        )
    if not _SELECTED_EQ.search(click):
        fail(
            f"{_ISSUE}: click Berk while Berk is open is a no-op "
            "(do not selectPerson / reload / clear conversation)"
        )

    # 6) leftover toast stay put — new ChromeKey; no invent; no name-match.
    if "showToast" not in insp and not _SHOW_TOAST.search(click):
        fail(
            f"{_ISSUE}: leftover / no live person → showToast (stay put); "
            "PeopleInspector needs the App.svelte showToast helper"
        )
    if "showToast" not in mount:
        fail(f"{_ISSUE}: PeopleShell must pass showToast into PeopleInspector")
    if not _SHOW_TOAST.search(click):
        fail(
            f"{_ISSUE}: null / missing live person_id → showToast(t(key)), "
            "no navigation"
        )
    if not _PERSON_ID_NULL.search(click):
        fail(
            f"{_ISSUE}: leftover branch is null / missing person_id "
            "(tombstone-only and unlinked share that toast)"
        )
    if _REUSE_TOAST.search(click):
        fail(
            f"{_ISSUE}: leftover uses a new calm ChromeKey — do not reuse "
            '"Could not open" / "Could not copy"'
        )
    if _SHOW_ERR.search(click) and not _SHOW_TOAST.search(click):
        fail(f"{_ISSUE}: leftover is a calm toast, not showErr")
    leftover_keys = [
        k
        for k in _T_CALL.findall(click)
        if k not in _KEEP_HEADING_KEYS and k != "self"
    ]
    if not leftover_keys:
        fail(
            f"{_ISSUE}: leftover toast must t() a new ChromeKey "
            "(same key on en.ts + tr.ts)"
        )
    if _INVENT.search(click):
        fail(
            f"{_ISSUE}: do not invent / INSERT / merge / link a person "
            "on leftover click (stay put)"
        )
    if _NAME_MATCH.search(click):
        fail(
            f"{_ISSUE}: do not resolve identity → person by display_name / "
            "identity_values (names never auto-merge)"
        )
    if _HTML.search(click) or _HTML.search(member):
        fail(f"{_ISSUE}: leftover toast is a string, not {{@html}} / innerHTML")

    # 7) (self) only when is_self — leftover never gets it; not the name "Self".
    if not _T_SELF.search(member) and not _T_SELF.search(insp):
        fail(
            f"{_ISSUE}: self row appends t(\"self\") "
            "(en visible copy is (self))"
        )
    self_win = _windows_around(member + "\n" + insp, _T_SELF, 160, 160)
    if not _IS_SELF.search(self_win) or not _PERSON_BY_ID.search(self_win + "\n" + member):
        fail(
            f"{_ISSUE}: t(\"self\") only when personById(person_id)?.is_self "
            "(leftover never gets (self))"
        )
    if _SELF_BY_NAME.search(insp) or _SELF_BY_NAME.search(member):
        fail(f"{_ISSUE}: do not label (self) by the name \"Self\"")
    if "self" not in en or "self" not in tr:
        fail(f"{_ISSUE}: self ChromeKey must exist on both en.ts and tr.ts")
    if (en.get("self") or "").strip() != "(self)":
        fail(f"{_ISSUE}: en self copy is (self) (issue text)")
    if (tr.get("self") or "").strip() in {"", "(self)", (en.get("self") or "").strip()}:
        fail(f"{_ISSUE}: tr self must not be an English copy")

    # 8) keep-groups — includeGroups stays true; do not write the pref false.
    if _WRITE_GROUPS.search(click) or _WRITE_GROUPS_FALSE.search(click):
        fail(
            f"{_ISSUE}: participant click must not writeIncludeGroupsPref(false) "
            "(includeGroups stays true)"
        )
    if _CHROME_TRUE.search(click):
        fail(
            f"{_ISSUE}: participant click does not auto-open the inspector "
            "(#213 default-off; selectPerson may close it)"
        )

    # 9) names text not ids; two Berk identities stay two controls.
    visible = re.sub(r"\{[#/:@].*?\}", "", _strip_tag_attrs(member), flags=re.S)
    if _RAW_ID_LABEL.search(visible):
        fail(
            f"{_ISSUE}: visible labels stay display_name || value — "
            "not identity_id / person_id / conversation_id"
        )
    if not _DISPLAY_THEN_VALUE.search(member):
        fail(
            f"{_ISSUE}: button label is still identity display_name || value "
            "(#322; never raw ids)"
        )
    if _EACH_KEY_PERSON.search(ul) or _EACH_KEY_PERSON.search(member):
        fail(f"{_ISSUE}: {{#each}} key is identity_id, not person_id")
    if not _EACH_KEY_IDENTITY.search(ul) and not _EACH_KEY_IDENTITY.search(member):
        fail(
            f"{_ISSUE}: {{#each}} key = identity_id "
            "(two identities of Berk stay two controls; both open Berk)"
        )
    if _COLLAPSE_ROWS.search(insp):
        fail(
            f"{_ISSUE}: do not collapse two identities onto one row "
            "(both Berk controls stay)"
        )
    if _JID.search(member) or _JID.search(click) or _JID.search(qbody):
        fail(f"{_ISSUE}: never paint a JID / whatsapp_jid (placeholders Ada / Berk / Self)")

    # 10) DMs still have no member list (#322 gate).
    hook = _GROUP_UL.search(markup) or _GROUP_UL.search(insp)
    gate_conds = _if_conds_at(markup or insp, hook.start()) if hook else []
    gate_blob = " && ".join(gate_conds)
    if not _INCLUDE_GROUPS.search(gate_blob) or not _GROUP_KIND.search(gate_blob):
        fail(
            f"{_ISSUE}: member list still only when includeGroups && "
            'conversation_kind === "group" (DMs / email_thread have no roster)'
        )
    if _KIND_DM.search(ul) and not re.search(r"!", ul):
        fail(f"{_ISSUE}: open kind=dm must not grow a member list")
    if _KIND_EMAIL.search(ul) and not re.search(
        r"!==?\s*[\"']email_thread[\"']|===?\s*[\"']group[\"']", gate_blob
    ):
        fail(f"{_ISSUE}: email_thread is not a group roster")
    if not _IN_THIS_GROUP.search(insp):
        fail(f"{_ISSUE}: keep t(\"inThisGroup\") (#322 heading)")

    # 11) keep #374 / #376 / #213 / no membership editor / no HTTP.
    if not _MAIL_HOOK.search(insp):
        fail(f"{_ISSUE}: keep data-mail-recipients as a sibling (#374)")
    if _MAIL_HOOK.search(ul):
        fail(
            f"{_ISSUE}: do not mix To/Cc/Bcc into data-group-participants (#374)"
        )
    if not _LETTER_RAIL.search(side) or not _LETTER_HEADING.search(side):
        fail(f"{_ISSUE}: keep #376 data-letter-rail / data-letter-heading")
    if not az_path.is_file():
        fail(f"{_ISSUE}: keep #376 azLetter.ts (do not start rail work here)")
    if _LETTER_RAIL.search(insp) or _LETTER_HEADING.search(insp):
        fail(f"{_ISSUE}: A–Z rail stays on the People sidebar, not the inspector")
    if not _INSPECTOR_HOOK.search(insp):
        fail(f"{_ISSUE}: keep data-person-inspector (#213)")
    if "overflow-y-auto" not in insp:
        fail(f"{_ISSUE}: keep inspector overflow-y-auto (#322 / #213)")
    if _EDITOR.search(member) or _EDITOR.search(ul):
        fail(f"{_ISSUE}: no membership editor (read-only name controls)")
    if _FETCH.search(click) or _FETCH.search(member) or _FETCH.search(qbody):
        fail(f"{_ISSUE}: no fetch / HTTP on the participant-open path")
    if "network.server" in ent:
        fail(f"{_ISSUE}: entitlements must omit network.server")
    if CSP not in conf:
        fail(f"{_ISSUE}: do not soften tauri CSP")
    if "writeIncludeGroupsPref" not in insp and not _WRITE_GROUPS.search(insp):
        fail(f"{_ISSUE}: keep #309 writeIncludeGroupsPref on the inspector tick")
    if "interlace.includeGroups" not in _text(prefs_path):
        fail(f"{_ISSUE}: keep #309 interlace.includeGroups pref")

    # 12) locales — leftover + self; same ChromeKey; tr is not an English copy.
    used = set(_T_CALL.findall(member)) | set(_T_CALL.findall(click)) | {"self"}
    used |= set(leftover_keys)
    missing_en = sorted(k for k in used if k not in en)
    missing_tr = sorted(k for k in used if k not in tr)
    if missing_en or missing_tr:
        bits = []
        if missing_en:
            bits.append("missing en: " + ", ".join(missing_en))
        if missing_tr:
            bits.append("missing tr: " + ", ".join(missing_tr))
        fail(
            f"{_ISSUE}: same ChromeKey on en.ts + tr.ts — " + "; ".join(bits)
        )
    extra_en = set(en) - set(tr)
    extra_tr = set(tr) - set(en)
    if extra_en or extra_tr:
        bits = []
        if extra_en:
            bits.append("in en only: " + ", ".join(sorted(extra_en)))
        if extra_tr:
            bits.append("in tr only: " + ", ".join(sorted(extra_tr)))
        fail(f"{_ISSUE}: same ChromeKey on both packs — " + "; ".join(bits))
    for key in leftover_keys:
        ev, tv = (en.get(key) or "").strip(), (tr.get(key) or "").strip()
        if not ev or not tv:
            fail(f"{_ISSUE}: leftover key {key} must have copy on both packs")
        if ev == tv:
            fail(f"{_ISSUE}: tr {key} must not be an English copy")
        if re.search(r"Could not open|Could not copy", ev, re.I):
            fail(f"{_ISSUE}: leftover copy is not \"Could not open\" / \"Could not copy\"")
    if "export function t" in i18n and "ChromeKey" not in i18n:
        fail(f"{_ISSUE}: t() stays key-only (ChromeKey → string)")
    for pack in (en, tr):
        for val in pack.values():
            if _PLACEHOLDER_CHROME.search(val):
                fail(
                    f"{_ISSUE}: locale packs stay chrome only — no Ada / Berk / "
                    "Self in t() values"
                )

    # 13) D24 — click opens that person; leftover stay + toast; DMs no list.
    if not docs.strip():
        fail(
            f"{_ISSUE}: docs/user/app.md required — click a group name opens "
            "that person; leftover stays with a toast"
        )
    if not _DOCS_CLICK.search(docs):
        fail(
            f"{_ISSUE}: docs/user/app.md must say clicking a group participant "
            "opens that person (placeholders Ada / Berk / Self)"
        )
    if not _DOCS_LEFTOVER.search(docs):
        fail(
            f"{_ISSUE}: docs/user/app.md must say a leftover name stays put "
            "with a calm toast"
        )
    if not _DOCS_DM.search(docs):
        fail(f"{_ISSUE}: keep “DMs do not grow a member list” in docs/user/app.md")
    if not _DOCS_TEXT.search(docs):
        fail(f"{_ISSUE}: keep “names are text, not ids” in docs/user/app.md")
