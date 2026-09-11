"""#322 — inspector lists group participant names.

Confirmed mix: inspector gets a separate read-only “in this group”
name list. Do not mix into {#each identities}. Keep #213 identities /
Merge / include-groups / unlink.

Data: conversation_participants ⨝ identities for that conversation_id
only. Not timeline senders. Not a union of every group.

Open conversation: selectedConversationId if set; else focused bubble
conversation_id when conversation_kind === "group". Include-groups on
required. Do not unhide #116 {#if false} on data-conversation-switcher.
All / focused DM → no member list. DM / email_thread: no member section.

Names: display_name then value. Never ident.id / person_id /
conversation_id / JID. Do not collapse two identities onto one
persons.display_name. Include self. One-sender group still shows the
section. No cap (existing inspector scroll). Order: identity_id.

New en+tr heading ChromeKey. t() stays key-only.

Keep #213 / #114 (switcher may stay hidden) / #309. No new importer.
No membership editor. No avatars. No whatsapp_jid. No HTTP / SQLCipher.
D24 docs/user/app.md. Placeholders only (Ada, Cemre Yıldız).
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.copy_archive import (
    _HTTP_CLIENT,
    _PLUGIN_SHELL,
    _REAL_HOME,
    _SHELL_CAP,
)
from tauri_gate.import_reveal_cmd import _REVEAL_ARCHIVE_ENCRYPT
from tauri_gate.include_groups import (
    _GROUPS_KEY,
    _GROUPS_KEY_RX,
    _INSPECTOR_BIND,
    _WRITE_GROUPS,
)
from tauri_gate.locale_more import _chrome_pack_entries
from tauri_gate.people_inspector_lib import (
    _INSPECTOR_HOOK,
    _INSPECTOR_ID_FALLBACK,
    _INSPECTOR_ID_VISIBLE,
    _INSPECTOR_REMOTE_IMG,
    _MERGE_CTRL,
    _TIMELINE_EACH_NAMES,
    _UNLINK_CTRL,
    _groups_ctrl_pos,
    _inspector_hidden_by_default,
    _inspector_ident_each,
    _inspector_surface,
    _inspector_toggle_flags,
    _strip_html_comments,
    _strip_tag_attrs,
    _svelte_markup,
)
from tauri_gate.people_switcher_pretty import (
    _CONV_STATE_DEFAULT_ALL,
    _CONV_SWITCHER_HOOK,
    _conversation_switcher_blocks,
    _flag_default_open,
)
from tauri_gate.scan import (
    CSP,
    _ARBITRARY_SHELL,
    _FETCH_CALL,
    _LINKIFY_FETCH,
    _matching_each_end,
    _rust_fn_signature,
    _rust_function_body,
    _tauri_rust_blob,
    _template_stack,
    _ts_fn_body,
    _web_logic,
    _without_comments,
)
from tauri_gate.status_toasts_chrome import (
    _claim_without_negation,
    _invoke_payloads,
    _payload_has_path_or_url,
    _windows_around,
)

_ISSUE = "#322"
_KEEP_HEADING_KEYS = frozenset({"inspector", "identities", "lastActivity"})
_EXISTING_CORE_FNS = frozenset(
    {
        "person_conversations",
        "person_timeline",
        "person_timeline_rows",
        "person_timeline_rows_for",
        "person_list",
        "person_list_on",
        "person_list_on_with_groups",
        "person_list_with_groups",
        "person_identities",
        "person_display_name",
        "person_show",
        "merge_targets",
        "recent_link_events",
        "attachments_for",
        "complete_attachments",
        "extract_attached_filenames",
    }
)
_EXISTING_CMDS = frozenset(
    {
        "person_show",
        "person_timeline",
        "person_conversations_cmd",
        "person_merge_cmd",
        "person_unlink_cmd",
        "person_undo_cmd",
        "link_events",
        "people",
    }
)
_IMPORT_KEEP = (
    "ContactsImporter",
    "GmailMboxImporter",
    "TakeoutImporter",
    "WhatsappImporter",
)
_MEMBER_SRC = re.compile(
    r"\b(?:"
    r"participants|participantNames|participant_names|"
    r"groupParticipants|group_participants|groupMembers|group_members|"
    r"memberNames|member_names|members|"
    r"inThisGroup|in_this_group|groupNames|group_names|"
    r"conversationParticipants|conversation_participants|"
    r"peerNames|peer_names|roster"
    r")\b",
    re.I,
)
_MEMBER_HOOK = re.compile(
    r"\bdata-(?:group-)?(?:participants|members|in-this-group|group-names)\b",
    re.I,
)
_MEMBER_EACH = re.compile(
    r"\{#each\s+[^}]*"
    r"(?:participants|participantNames|participant_names|"
    r"groupParticipants|group_participants|groupMembers|group_members|"
    r"memberNames|member_names|members|"
    r"inThisGroup|in_this_group|groupNames|group_names|"
    r"conversationParticipants|conversation_participants|"
    r"peerNames|peer_names|roster)"
    r"\b",
    re.I,
)
_GROUP_KIND = re.compile(
    r"(?:"
    r"(?:conversation_kind|\.kind)\s*===?\s*[\"']group[\"']"
    r"|[\"']group[\"']\s*===?\s*(?:conversation_kind|\.kind)"
    r")",
)
_KIND_DM = re.compile(
    r"(?:conversation_kind|\.kind)\s*===?\s*[\"']dm[\"']"
)
_KIND_EMAIL = re.compile(
    r"(?:conversation_kind|\.kind)\s*===?\s*[\"']email_thread[\"']"
)
_KIND_FILTER_AS_OPEN = re.compile(
    r"\bkindFilter\s*===?\s*[\"']group[\"']",
)
_SELECTED_CONV = re.compile(r"\bselectedConversationId\b")
_FOCUSED_BUBBLE = re.compile(
    r"("
    r"timeline\s*(?:\[[^\]]{0,40}tlIndex|[^\n]{0,40}tlIndex)"
    r"|filteredTimeline\s*\[[^\]]{0,40}tlIndex"
    r"|tlIndex\b[^\n]{0,80}conversation_id"
    r"|conversation_id[^\n]{0,80}tlIndex"
    r")",
)
_INCLUDE_GROUPS = re.compile(r"\bincludeGroups\b")
_DISPLAY_THEN_VALUE = re.compile(
    r"(?:display_name|displayName)\s*(?:\?\?|\|\|)\s*"
    r"(?:[\w$.?]*\bvalue\b)",
)
_VALUE_THEN_DISPLAY = re.compile(
    r"\bvalue(?:_normalized|_raw)?\s*(?:\?\?|\|\|)\s*"
    r"(?:[\w$.?]*\bdisplay_name\b|[\w$.?]*\bdisplayName\b)",
)
_RAW_ID_LABEL = re.compile(
    r"\{[^}]{0,100}(?:"
    r"\bident(?:ity)?\.id\b"
    r"|\bperson_id\b"
    r"|\bpersonId\b"
    r"|\bconversation_id\b"
    r"|\bconversationId\b"
    r"|\.id\b"
    r")[^}]{0,40}\}"
)
_JID = re.compile(r"\bwhatsapp_jid\b|\bwa_jid\b|\bjid\b", re.I)
_PERSON_COLLAPSE = re.compile(
    r"("
    r"\bpersons\.[A-Za-z_]*display_name\b"
    r"|\bp\.display_name\b"
    r"|\bperson(?:s)?\.display_name\b"
    r")",
    re.I,
)
_ROLE_SKIP_ME = re.compile(
    r"("
    r"role\s*(?:!=|<>|NOT\s+IN)\s*[\"']me[\"']"
    r"|role\s+NOT\s+IN\s*\([^)]*[\"']me[\"']"
    r"|!=\s*[\"']me[\"']"
    r")",
    re.I,
)
_ORDER_ID = re.compile(
    r"ORDER\s+BY\s+"
    r"(?:(?:cp|i|identities)\.)?(?:identity_id|\bid\b)",
    re.I,
)
_SQL_LIMIT = re.compile(r"\bLIMIT\s+\d+", re.I)
_JS_CAP = re.compile(
    r"\.(?:slice|take|limit)\s*\(\s*0\s*,\s*\d+",
)
_LENGTH_GATE = re.compile(
    r"\.length\s*(?:>|>=|===?|!==?)\s*[12]\b"
    r"|\.length\s*(?:<|<=)\s*[12]\b",
)
_T_CALL = re.compile(r"""\bt\s*\(\s*["']([A-Za-z_][\w]*)["']\s*\)""")
_T_FN = re.compile(
    r"export\s+function\s+t\s*\(\s*key\s*:\s*ChromeKey\s*\)"
)
_T_NOT_KEY = re.compile(
    r"""\bt\s*\(\s*(?:[\w$.]*\b(?:display_name|displayName|value|name)\b)"""
)
_CLIENT_PARAM = re.compile(
    r"\b(?:path|url|file|href|uri|dest|source|root)\s*:",
    re.I,
)
_OPEN_SECOND = re.compile(r"\bopen_archive\s*\(|LockMode\s*::\s*Exclusive")
_WITH_ARCH = re.compile(r"\bwith_arch\s*\(")
_SENDER_SRC = re.compile(
    r"("
    r"sender_identity_id"
    r"|DISTINCT\s+[^\n]{0,40}sender"
    r"|filteredTimeline[^\n]{0,80}sender"
    r"|timeline\s*\.[^\n]{0,80}sender"
    r")",
    re.I,
)
_UNION_ALL_GROUPS = re.compile(
    r"("
    r"kind\s*===?\s*[\"']group[\"'][^\n]{0,80}person_id"
    r"|person_id[^\n]{0,120}kind\s*===?\s*[\"']group[\"']"
    r"|FROM\s+conversation_participants[^\n]{0,200}person_id"
    r")",
    re.I | re.S,
)
_EDITOR = re.compile(
    r"("
    r"add member|remove member|invite to group|leave group|"
    r"edit membership|onAddMember|onRemoveMember|addParticipant|"
    r"removeParticipant"
    r")",
    re.I,
)
_IF_FALSE = re.compile(r"\{#if\s+false\s*\}")
_DOCS_GROUP_NAMES = re.compile(
    r"("
    r"(?:group|include groups).{0,240}(?:participant|member) names?"
    r"|(?:participant|member) names?.{0,240}(?:inspector|group)"
    r"|inspector.{0,200}(?:participant|member) names?"
    r")",
    re.I | re.S,
)
_DOCS_DM_NO = re.compile(
    r"("
    r"DMs?(?: do not| don't| does not| never).{0,80}"
    r"(?:member|participant|roster)"
    r"|(?:member|participant).{0,80}(?:not|never).{0,40}DMs?"
    r"|DMs? do not"
    r")",
    re.I | re.S,
)
_DOCS_TEXT_NOT_IDS = re.compile(
    r"("
    r"names? (?:are|is) text.{0,40}not.{0,20}ids?"
    r"|text, not.{0,20}ids?"
    r"|not raw (?:person |identity |conversation )?ids?"
    r"|names? (?:are|is) (?:text|not ids?)"
    r")",
    re.I | re.S,
)
_DOCS_NOT_TL = re.compile(
    r"not a second timeline|not another timeline",
    re.I,
)
_PLACEHOLDERS = re.compile(r"\bAda\b|Cemre Yıldız")
_FN_DEF = re.compile(r"(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*\(")
_HANDLER = re.compile(r"generate_handler!\s*\[(.*?)\]", re.S)
_API_MEMBER = re.compile(
    r"\b([A-Za-z_]*(?:participant|groupParticipant|groupMember|"
    r"memberName|inThisGroup)[A-Za-z_]*)\s*:",
    re.I,
)
_INVOKE_MEMBER = re.compile(
    r"invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']"
    r"([A-Za-z_]*(?:participant|group_participant|group_member|"
    r"member_name|in_this_group)[A-Za-z_]*)[\"']",
    re.I,
)
_CONV_ID_BIND = re.compile(
    r"conversation_id\s*=\s*[?:?]\w+|WHERE[^\n]{0,160}conversation_id",
    re.I,
)
_JOIN_IDENT = re.compile(
    r"JOIN\s+identities\b|\bidentities\s+\w+\s+ON",
    re.I,
)
_FROM_CP = re.compile(r"FROM\s+conversation_participants\b", re.I)


def _text(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


def _people_core_blob(root: Path) -> str:
    """people.rs + people/*.rs only (do not open import / identity / search)."""
    parts: list[str] = []
    src = root / "crates" / "interlace-core" / "src" / "people.rs"
    if src.is_file():
        parts.append(src.read_text())
    d = root / "crates" / "interlace-core" / "src" / "people"
    if d.is_dir():
        for p in sorted(d.glob("*.rs")):
            parts.append(p.read_text())
    return "\n".join(parts)


def _handler_names(rust: str) -> list[str]:
    m = _HANDLER.search(rust)
    if not m:
        return []
    return re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", m.group(1))


def _member_blocks(surface: str) -> list[str]:
    """Separate in-this-group name list blocks inside the inspector."""
    out: list[str] = []
    for m in _MEMBER_EACH.finditer(surface):
        end = _matching_each_end(surface, m.start())
        out.append(surface[m.start() : end if end > 0 else m.end() + 400])
    for m in _MEMBER_HOOK.finditer(surface):
        out.append(surface[max(0, m.start() - 80) : m.end() + 500])
    return out


def _member_each_inside_identities(surface: str) -> bool:
    ident = _inspector_ident_each(surface)
    if not ident:
        return False
    return bool(_MEMBER_EACH.search(ident) or _MEMBER_HOOK.search(ident))


def _if_conds_at(markup: str, pos: int) -> list[str]:
    return [a for kind, a, _b in _template_stack(markup, pos) if kind == "if"]


def _switcher_hidden_if_false(tl: str) -> bool:
    m = _CONV_SWITCHER_HOOK.search(tl)
    if not m:
        return False
    return any(re.fullmatch(r"false", a.strip()) for a in _if_conds_at(tl, m.start()))


def _participant_query(core: str) -> tuple[str, str]:
    """New conversation_participants ⨝ identities name list (not person_identities)."""
    for m in _FN_DEF.finditer(core):
        name = m.group(1)
        if name in _EXISTING_CORE_FNS:
            continue
        body = _rust_function_body(core, name)
        if not body:
            continue
        if not _FROM_CP.search(body):
            continue
        if not _JOIN_IDENT.search(body):
            continue
        if not re.search(r"\bdisplay_name\b", body):
            continue
        if not _CONV_ID_BIND.search(body):
            continue
        return name, body
    return "", ""


def _participant_cmd(rust: str, query: str) -> tuple[str, str]:
    names = _handler_names(rust)
    for name in names:
        if name in _EXISTING_CMDS:
            continue
        body = _rust_function_body(rust, name)
        if not body:
            continue
        if query and query in body:
            return name, body
        if re.search(r"participant", name, re.I) or re.search(
            r"participant", body, re.I
        ):
            return name, body
    for m in _FN_DEF.finditer(rust):
        name = m.group(1)
        if name in _EXISTING_CMDS:
            continue
        body = _rust_function_body(rust, name)
        if query and query in body:
            return name, body
        if re.search(r"participant", name, re.I) and body:
            return name, body
    return "", ""


def _api_member_name(api: str) -> str:
    m = _API_MEMBER.search(api)
    if m:
        return m.group(1)
    m = _INVOKE_MEMBER.search(api)
    return m.group(1) if m else ""


def _heading_keys(blob: str) -> list[str]:
    keys = []
    for k in _T_CALL.findall(blob):
        if k not in _KEEP_HEADING_KEYS and k not in keys:
            keys.append(k)
    return keys


def assert_group_inspector_names(crate: Path) -> None:
    """#322: group (include groups on) lists participant names in the inspector."""
    insp_path = crate / "web" / "lib" / "PeopleInspector.svelte"
    if not insp_path.is_file():
        fail(
            f"{_ISSUE}: PeopleInspector.svelte required "
            "(separate read-only in-this-group name list lives there)"
        )
    insp_raw = insp_path.read_text()
    insp = _without_comments(insp_raw)
    markup = _strip_html_comments(_svelte_markup(insp_raw))
    surface = _inspector_surface(crate, markup)
    if not surface.strip():
        surface = markup

    # 1) group-inspector-names — primary red today.
    if not _INSPECTOR_HOOK.search(surface) and not _INSPECTOR_HOOK.search(insp):
        fail(
            f"{_ISSUE}: data-person-inspector required "
            "(names go on the existing inspector, not a new pane)"
        )
    if _member_each_inside_identities(surface):
        fail(
            f"{_ISSUE}: do not mix group participant names into "
            "{#each identities} — keep a separate read-only list"
        )
    blocks = _member_blocks(surface)
    if not blocks:
        fail(
            f"{_ISSUE}: inspector (data-person-inspector) must list group "
            "participant names in a separate read-only “in this group” "
            "section (not mixed into {#each identities})"
        )
    member = "\n".join(blocks)
    ident = _inspector_ident_each(surface) or _inspector_ident_each(insp)
    if not ident.strip():
        fail(
            f"{_ISSUE}: keep {{#each identities}} "
            "(#213 person identities stay; names are a second list)"
        )
    if _MEMBER_SRC.search(ident) and _DISPLAY_THEN_VALUE.search(ident):
        fail(
            f"{_ISSUE}: do not mix group participant names into "
            "{#each identities}"
        )

    shell_path = crate / "web" / "lib" / "PeopleShell.svelte"
    tl_path = crate / "web" / "lib" / "TimelinePane.svelte"
    api_path = crate / "web" / "lib" / "api.ts"
    shell = _without_comments(_text(shell_path))
    tl = _without_comments(_text(tl_path))
    api = _text(api_path)
    web = _without_comments(_web_logic(crate))
    people_web = "\n".join((insp, shell, tl))
    rust = _tauri_rust_blob(crate)
    rust_c = _without_comments(rust)
    root = repo_root()
    core = _people_core_blob(root)
    people_rs = _text(root / "crates" / "interlace-core" / "src" / "people.rs")
    lib_rs = _text(root / "crates" / "interlace-core" / "src" / "lib.rs")
    i18n = _text(crate / "web" / "lib" / "i18n.ts")
    en = _chrome_pack_entries(_text(crate / "web" / "lib" / "locales" / "en.ts"))
    tr = _chrome_pack_entries(_text(crate / "web" / "lib" / "locales" / "tr.ts"))
    dtxt = _text(root / "docs" / "user" / "app.md")
    toml = _text(crate / "Cargo.toml")
    pkg = _text(crate / "package.json")
    caps = _text(crate / "capabilities" / "default.json")
    ent = _text(crate / "Interlace.entitlements")
    conf = _text(crate / "tauri.conf.json")

    # 2) open-conversation — selectedConversationId else focused group bubble.
    load_surf = "\n".join(
        [
            member,
            _windows_around(people_web, _MEMBER_SRC, before=220, after=280),
            _windows_around(people_web, _MEMBER_HOOK, before=160, after=240),
            _windows_around(people_web, _API_MEMBER, before=160, after=240),
            _windows_around(people_web, _INVOKE_MEMBER, before=160, after=240),
        ]
    )
    if not _SELECTED_CONV.search(load_surf + "\n" + people_web):
        fail(
            f"{_ISSUE}: open conversation is selectedConversationId if set "
            "(do not invent a third picker)"
        )
    if not _SELECTED_CONV.search(load_surf) and not re.search(
        r"selectedConversation(?:Id)?", load_surf
    ):
        fail(
            f"{_ISSUE}: the in-this-group list must key off "
            "selectedConversationId if set (not kindFilter Groups, not All)"
        )
    if not _FOCUSED_BUBBLE.search(load_surf) and not re.search(
        r"conversation_kind\s*===?\s*[\"']group[\"']", load_surf
    ):
        fail(
            f"{_ISSUE}: when selectedConversationId is unset, use the focused "
            "bubble conversation_id if conversation_kind === \"group\""
        )
    if not _INCLUDE_GROUPS.search(load_surf) and not _INCLUDE_GROUPS.search(member):
        fail(
            f"{_ISSUE}: include-groups on is required to load the group "
            "member list (groups stay gated — #309)"
        )
    if _KIND_FILTER_AS_OPEN.search(member) and not _SELECTED_CONV.search(load_surf):
        fail(
            f"{_ISSUE}: kindFilter === \"group\" is not the open conversation "
            "(All / Groups chip can be many chats)"
        )
    member_pos = _MEMBER_EACH.search(surface) or _MEMBER_HOOK.search(surface)
    gate_conds = _if_conds_at(surface, member_pos.start()) if member_pos else []
    gate_blob = " && ".join(gate_conds) + "\n" + member + "\n" + load_surf
    if not _GROUP_KIND.search(gate_blob) and not re.search(
        r"[\"']group[\"']", gate_blob
    ):
        fail(
            f"{_ISSUE}: show the member list only when the open conversation "
            "is kind=group (All / a focused DM → no list)"
        )
    if not _switcher_hidden_if_false(_text(tl_path)):
        fail(
            f"{_ISSUE}: do not unhide #116 {{#if false}} on "
            "data-conversation-switcher (inspector only; no third picker)"
        )

    # 3) participants-from-table — that conversation_id only.
    qname, qbody = _participant_query(core)
    if not qname or not qbody:
        fail(
            f"{_ISSUE}: names come from conversation_participants ⨝ "
            "identities for that conversation_id only "
            "(not timeline senders, not a union of every group)"
        )
    if not re.search(rf"\b{re.escape(qname)}\b", people_rs):
        fail(
            f"{_ISSUE}: export {qname} from people.rs "
            "(sibling of person_identities / person_conversations)"
        )
    if not re.search(rf"\b{re.escape(qname)}\b", lib_rs):
        fail(f"{_ISSUE}: export {qname} from interlace-core lib.rs")
    if _SENDER_SRC.search(qbody) and not _FROM_CP.search(qbody):
        fail(
            f"{_ISSUE}: do not list distinct messages.sender_identity_id "
            "(DESIGN: sender ≠ membership; use conversation_participants)"
        )
    if re.search(r"sender_identity_id", load_surf) and not qname:
        fail(
            f"{_ISSUE}: do not scrape the loaded timeline page for senders "
            "(use the participants table)"
        )
    if re.search(
        r"FROM\s+conversation_participants\b(?![^\"]{0,400}conversation_id)",
        qbody,
        re.I | re.S,
    ) and not _CONV_ID_BIND.search(qbody):
        fail(
            f"{_ISSUE}: query that conversation_id only "
            "(not a union of every group this person is in)"
        )
    if re.search(r"\bperson_id\b", qbody) and not _CONV_ID_BIND.search(qbody):
        fail(
            f"{_ISSUE}: do not key the roster by person_id across groups "
            "(one conversation_id)"
        )
    if _UNION_ALL_GROUPS.search(qbody) and not _CONV_ID_BIND.search(qbody):
        fail(
            f"{_ISSUE}: not a union of every group — filter that "
            "conversation_id only"
        )

    # 4) no-client-path — integer conversation id; with_arch; no path/URL.
    cmd, cmd_body = _participant_cmd(rust_c, qname)
    if not cmd:
        fail(
            f"{_ISSUE}: thin Tauri command required "
            f"(calls {qname}; archive from app state; conversation_id integer)"
        )
    if cmd not in _handler_names(rust):
        fail(f"{_ISSUE}: register {cmd} in generate_handler")
    sig = _rust_fn_signature(rust, cmd)
    if _CLIENT_PARAM.search(sig):
        fail(
            f"{_ISSUE}: {cmd} takes no path / root / URL "
            "(conversation_id is the same integer person_timeline already takes)"
        )
    if not re.search(r"\bconversation_id\b", sig):
        fail(f"{_ISSUE}: {cmd} must take conversation_id: i64 (no client path)")
    if not _WITH_ARCH.search(cmd_body):
        fail(
            f"{_ISSUE}: {cmd} reads via with_arch on the held Exclusive "
            "(no second open_archive)"
        )
    if _OPEN_SECOND.search(cmd_body):
        fail(f"{_ISSUE}: do not open_archive a second Exclusive from {cmd}")
    api_name = _api_member_name(api)
    if not api_name:
        fail(
            f"{_ISSUE}: api.ts wrapper required for the participants command "
            "(no path / URL from the webview)"
        )
    api_fn = _ts_fn_body(api, api_name) or ""
    api_win = _windows_around(api, re.compile(rf"\b{re.escape(api_name)}\b"), 40, 220)
    for payload in _invoke_payloads(api_win + "\n" + api_fn, re.compile(re.escape(cmd))):
        if _payload_has_path_or_url(payload):
            fail(f"{_ISSUE}: api.{api_name} must not send a path / URL")
    if not re.search(rf"\b{re.escape(api_name)}\b", people_web):
        fail(
            f"{_ISSUE}: inspector / shell / timeline must invoke {api_name} "
            "when the open conversation is a group (include groups on)"
        )

    # 5) dm / email_thread silent — no fake roster.
    if _KIND_DM.search(member) and not re.search(r"!", member):
        if not re.search(r"!==?\s*[\"']dm[\"']|===?\s*[\"']group[\"']", gate_blob):
            fail(
                f"{_ISSUE}: open kind=dm must not grow a member list "
                "(do not invent members from counterpart + self)"
            )
    if not re.search(r"[\"']group[\"']", gate_blob):
        fail(
            f"{_ISSUE}: DM / email_thread omit the member section "
            "(treat email_thread like DM — no fake roster)"
        )
    if re.search(r"[\"']email_thread[\"']", member) and not re.search(
        r"!==?\s*[\"']email_thread[\"']|===?\s*[\"']group[\"']", gate_blob
    ):
        fail(
            f"{_ISSUE}: email_thread is not a group roster "
            "(same silence as DM)"
        )
    for cond in gate_conds:
        if _LENGTH_GATE.search(cond) and not _GROUP_KIND.search(cond):
            fail(
                f"{_ISSUE}: one-sender group still shows the section "
                "(gate on kind=group, not length ≥ 2)"
            )

    # 6) names-text-not-ids — display_name then value; no person collapse.
    visible = re.sub(r"\{[#/:@].*?\}", "", _strip_tag_attrs(member), flags=re.S)
    if _RAW_ID_LABEL.search(visible) or _INSPECTOR_ID_VISIBLE.search(visible):
        fail(
            f"{_ISSUE}: visible participant labels are text "
            "(display_name then value) — not ident.id / person_id / "
            "conversation_id"
        )
    if _INSPECTOR_ID_FALLBACK.search(member):
        fail(
            f"{_ISSUE}: do not fall back a missing name to a raw id "
            "(display_name then value; never ident.id)"
        )
    if not _DISPLAY_THEN_VALUE.search(member) and not re.search(
        r"display_name", member
    ):
        fail(
            f"{_ISSUE}: names are identity display_name, then value if "
            "display_name is empty"
        )
    if _VALUE_THEN_DISPLAY.search(member) and not _DISPLAY_THEN_VALUE.search(member):
        fail(
            f"{_ISSUE}: display_name then value "
            "(do not prefer value the way {#each identities} does)"
        )
    if _JID.search(member) or _JID.search(qbody):
        fail(
            f"{_ISSUE}: never use a JID / whatsapp_jid as the label "
            "(no fake WhatsApp JID)"
        )
    if _PERSON_COLLAPSE.search(member) or (
        re.search(r"JOIN\s+persons\b", qbody, re.I)
        and re.search(r"persons\.\w*display_name|\bp\.display_name\b", qbody)
    ):
        fail(
            f"{_ISSUE}: do not collapse two identities onto one "
            "persons.display_name (I2 / D16 / #342 parked)"
        )
    if re.search(r"\bkind\b", member) and re.search(
        r"\{[^}]*\bkind\b[^}]*\}", member
    ):
        fail(
            f"{_ISSUE}: in-this-group labels are display-name text, "
            "not kind+value identities"
        )

    # 7) include-self / order / no-cap / overflow.
    if _ROLE_SKIP_ME.search(qbody):
        fail(f"{_ISSUE}: include role=me / self in the name list")
    if not _ORDER_ID.search(qbody):
        fail(f"{_ISSUE}: order participant names by identity_id")
    if _SQL_LIMIT.search(qbody) or _JS_CAP.search(member + "\n" + load_surf):
        fail(
            f"{_ISSUE}: no cap on the name list "
            "(scroll the existing inspector overflow-y-auto)"
        )
    if "overflow-y-auto" not in surface and "overflow-y-auto" not in insp:
        fail(
            f"{_ISSUE}: keep the existing inspector overflow-y-auto "
            "(no new cap / no new pane)"
        )
    if _UNLINK_CTRL.search(member) or _MERGE_CTRL.search(member):
        fail(
            f"{_ISSUE}: in-this-group list is read-only names "
            "(not unlink / not Merge targets)"
        )

    # 8) locale — new en+tr heading ChromeKey; t() key-only.
    heading = _heading_keys(member)
    if not heading:
        fail(
            f"{_ISSUE}: new en+tr heading ChromeKey for the in-this-group "
            "section (do not reuse t(\"identities\"); t() stays key-only)"
        )
    hkey = heading[0]
    if hkey not in en or hkey not in tr:
        fail(
            f"{_ISSUE}: {hkey} must exist on both en.ts and tr.ts "
            "(same ChromeKey — #278)"
        )
    if not (en.get(hkey) or "").strip() or not (tr.get(hkey) or "").strip():
        fail(f"{_ISSUE}: {hkey} must have copy on both packs")
    if (en.get(hkey) or "").strip() == (tr.get(hkey) or "").strip():
        fail(f"{_ISSUE}: tr {hkey} must not be an English copy (#278)")
    extra_en = set(en) - set(tr)
    extra_tr = set(tr) - set(en)
    if extra_en or extra_tr:
        bits: list[str] = []
        if extra_en:
            bits.append("in en only: " + ", ".join(sorted(extra_en)))
        if extra_tr:
            bits.append("in tr only: " + ", ".join(sorted(extra_tr)))
        fail(
            f"{_ISSUE}: same ChromeKey on both en and tr packs — "
            + "; ".join(bits)
        )
    if not _T_FN.search(i18n):
        fail(f"{_ISSUE}: t() stays key-only (ChromeKey → string)")
    if _T_NOT_KEY.search(member):
        fail(
            f"{_ISSUE}: t() stays key-only "
            "(do not t(display_name) / t(name); names are imported text)"
        )
    for pack in (en, tr):
        for val in pack.values():
            if _PLACEHOLDERS.search(val):
                fail(
                    f"{_ISSUE}: placeholder names (Ada, Cemre Yıldız) stay "
                    "out of the chrome pack"
                )

    # 9) keep-213 — identities / Merge / include-groups / unlink / closed.
    if not re.search(r"\{#each\s+[^}]*\bidentit", ident, re.I):
        fail(f"{_ISSUE}: keep #213 {{#each identities}}")
    if not re.search(r"\bkind\b", ident) or not re.search(
        r"\b(?:value|display_name)\b", ident
    ):
        fail(
            f"{_ISSUE}: keep #213 identity labels as kind + value / "
            "display_name (not raw ids)"
        )
    if not _MERGE_CTRL.search(surface) and not _MERGE_CTRL.search(insp):
        fail(f"{_ISSUE}: keep Merge… inside data-person-inspector (#213)")
    if _groups_ctrl_pos(surface) < 0 and _groups_ctrl_pos(insp) < 0:
        fail(f"{_ISSUE}: keep include-groups inside data-person-inspector (#213 / #309)")
    if not _UNLINK_CTRL.search(surface) and not _UNLINK_CTRL.search(insp):
        fail(f"{_ISSUE}: keep unlink inside data-person-inspector (#213)")
    hook = _INSPECTOR_HOOK.search(markup) or _INSPECTOR_HOOK.search(insp)
    hook_pos = hook.start() if hook else 0
    if not _inspector_hidden_by_default(markup or insp, hook_pos):
        fail(
            f"{_ISSUE}: keep #213 inspector hidden by default "
            "(tests open it first)"
        )
    flags = _inspector_toggle_flags(markup or insp, hook_pos)
    if flags and any(_flag_default_open(insp + "\n" + web, name) for name in flags):
        fail(f"{_ISSUE}: keep #213 inspector starting closed")
    if re.search(r"""id\s*=\s*["']person-timeline["']|#person-timeline""", member):
        fail(f"{_ISSUE}: inspector must not become a second timeline (#213)")
    for name in _TIMELINE_EACH_NAMES:
        if re.search(rf"\{{#each\s+{re.escape(name)}\b", member):
            fail(f"{_ISSUE}: do not {{#each}} timeline rows in the inspector (#213)")
    if _INSPECTOR_REMOTE_IMG.search(member) or _INSPECTOR_REMOTE_IMG.search(surface):
        fail(f"{_ISSUE}: no network avatar <img> (#213)")

    # 10) keep-114 — switcher markup may stay hidden.
    if not _conversation_switcher_blocks(crate):
        fail(
            f"{_ISSUE}: keep #114 data-conversation-switcher markup "
            "(may stay under {#if false})"
        )
    if not _CONV_STATE_DEFAULT_ALL.search(tl) and not _CONV_STATE_DEFAULT_ALL.search(web):
        fail(f"{_ISSUE}: keep #114 default conversation = All")
    if _CONV_SWITCHER_HOOK.search(insp):
        fail(
            f"{_ISSUE}: do not move the conversation switcher inside the "
            "inspector (#114)"
        )

    # 11) keep-309 — include-groups pref untouched.
    if not _INSPECTOR_BIND.search(insp):
        fail(
            f"{_ISSUE}: keep the People inspector include-groups checkbox "
            "(bind:checked={{includeGroups}} — #309)"
        )
    if _GROUPS_KEY not in web and not _GROUPS_KEY_RX.search(web):
        fail(f"{_ISSUE}: keep #309 interlace.includeGroups local pref")
    if not _WRITE_GROUPS.search(insp) and "writeIncludeGroupsPref" not in insp:
        fail(f"{_ISSUE}: keep #309 writeIncludeGroupsPref on the inspector tick")

    # 12) bans — no importer / editor / avatars / JID / HTTP / SQLCipher.
    for name in _IMPORT_KEEP:
        if name not in lib_rs:
            fail(f"{_ISSUE}: do not drop {name} (no new importer; keep the set)")
    if re.search(r"pub use import::\{[^}]*Group", lib_rs):
        fail(f"{_ISSUE}: no new group-metadata importer")
    if _JID.search(people_web) or _JID.search(api) or _JID.search(qbody):
        fail(f"{_ISSUE}: no whatsapp_jid (D16 — never invent a JID)")
    if _EDITOR.search(member) or _EDITOR.search(insp):
        fail(f"{_ISSUE}: no membership editor (read-only names)")
    if re.search(r"<img\b", member, re.I):
        fail(f"{_ISSUE}: no avatars on the in-this-group list")
    if _PLUGIN_SHELL.search(toml) or _PLUGIN_SHELL.search(pkg):
        fail(f"{_ISSUE}: do not add tauri-plugin-shell / tauri-plugin-opener")
    if _SHELL_CAP.search(caps):
        fail(f"{_ISSUE}: capabilities must not add shell:allow-execute / opener")
    own = cmd_body + "\n" + qbody + "\n" + member
    if _FETCH_CALL.search(own) or _LINKIFY_FETCH.search(own):
        fail(f"{_ISSUE}: no fetch / HTTP from the participants path")
    if _HTTP_CLIENT.search(toml) or _HTTP_CLIENT.search(own):
        fail(f"{_ISSUE}: no HTTP client / tauri-plugin-http")
    if "network.server" in ent:
        fail(f"{_ISSUE}: entitlements must omit network.server")
    if CSP not in conf:
        fail(f"{_ISSUE}: do not soften tauri CSP")
    if _ARBITRARY_SHELL.search(own):
        fail(f"{_ISSUE}: no arbitrary shell — names are a local table read")
    if _claim_without_negation(dtxt + "\n" + member, _REVEAL_ARCHIVE_ENCRYPT):
        fail(f"{_ISSUE}: no SQLCipher / “encrypted DB” claim")
    if _REAL_HOME.search(member + "\n" + qbody + "\n" + cmd_body):
        fail(f"{_ISSUE}: tests stay placeholders (Ada, Cemre Yıldız)")

    # 13) D24 — group (include groups on) lists names; DMs do not; text not ids.
    if not dtxt.strip():
        fail(
            f"{_ISSUE}: docs/user/app.md required — a group (include groups on) "
            "lists participant names in the inspector"
        )
    if not _DOCS_GROUP_NAMES.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say a group (include groups on) "
            "lists participant names in the inspector"
        )
    if not _DOCS_DM_NO.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say DMs do not grow a member list"
        )
    if not _DOCS_TEXT_NOT_IDS.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say names are text, not ids"
        )
    if not _DOCS_NOT_TL.search(dtxt):
        fail(
            f"{_ISSUE}: keep “not a second timeline” in docs/user/app.md (#213)"
        )
