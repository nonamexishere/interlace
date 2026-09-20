"""#402 — Search Enter on a sent DM must open the other person, not Self.

Confirmed mix (2026-09-20): remap person_id and person_name in search_cmd
hit JSON. activateHit stays h.person_id. For dm and email_thread, when the
sender person is Self, set both fields to the unique live non-self
participant. Tombstoned persons do not count. Self-only stays Self.
Many-peers / unlinked-other keep sender. Group unchanged. Keep #371
click/j/k preview, no-person no jump, #124 message_id.

Must-IDs: union of 402-a/b/c research as they match this mix.
Placeholders Ada / Berk / Self. Additive chrome + search_cmd SQL.
Do not require #400 pinJump.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.last_read import _text, _web_file
from tauri_gate.scan import (
    _RUST_CALL_SKIP,
    _rust_function_body,
    _svelte_markup,
    _without_comments,
)
from tauri_gate.search_hit_preview import (
    _ACTIVATE,
    _JUMP_OR_VIEW,
    _KEY_ENTER,
    _KEY_J,
    _KEY_K,
    _NEW_INVOKE,
    _PERSON_GUARD,
    _SENT_AT_PAYLOAD,
    _click_path,
    _enter_branch,
    _fn,
)
from tauri_gate.search_hits_jump import (
    _HIT_MESSAGE_ID_READ,
    _HIT_PERSON_ID_READ,
    _VIEW_PEOPLE,
    _hits_each_block,
)

_ISSUE = "#402"

_SKIP_CALLEES = _RUST_CALL_SKIP | {
    "search",
    "attachments_for",
    "complete_attachments",
    "extract_attached_filenames",
    "parse_platform",
    "parse_conversation_kind",
    "parse_attachment_filter",
    "err",
    "with_arch",
    "query_row",
    "json",
    "collect",
    "iter",
    "map_err",
    "unwrap_or_else",
    "unwrap_or_default",
    "cloned",
    "get",
    "push",
    "into",
    "format",
    "vec",
    "serde_json",
    "Value",
    "Array",
    "SearchQuery",
    "labels_list",
}

_PARTICIPANTS = re.compile(r"\bconversation_participants\b")
_SELF_IDENTITIES = re.compile(r"\bself_identities\b")
_IS_SELF_ONE = re.compile(r"\bis_self\s*=\s*1\b|\bis_self\s*==\s*(?:true|1)\b")
_IS_SELF_ZERO = re.compile(
    r"\bis_self\s*=\s*0\b"
    r"|\bis_self\s*==\s*(?:false|0)\b"
    r"|!\s*(?:[A-Za-z_][A-Za-z0-9_]*\.)?is_self\b"
)
_DM = re.compile(r"""['\"]dm['\"]""")
_EMAIL = re.compile(r"""['\"]email_thread['\"]""")
_GROUP_KIND = re.compile(r"""['\"]group['\"]""")
_TOMBSTONE = re.compile(r"\btombstoned_at\s+IS\s+NULL\b", re.I)
_RECIPIENTS = re.compile(r"\bmessage_recipients\b")
_INSERT_PERSON = re.compile(r"INSERT\s+INTO\s+persons\b", re.I)
_PROMOTE = re.compile(r"\bpromote_unlinked_names\b")
_TITLE_AS_PERSON = re.compile(
    r"person_id[^\n]{0,80}c\.title|person_name[^\n]{0,80}c\.title",
    re.I,
)
_JUMP_PERSON_FIELD = re.compile(r"\bjump_person_id\b|\bjumpPersonId\b")
_PERSON_ID_JSON = re.compile(r"""["']person_id["']\s*:""")
_PERSON_NAME_JSON = re.compile(r"""["']person_name["']\s*:""")
_SEARCH_CALL = re.compile(r"\bsearch\s*\(")
_INCLUDE_GROUPS_ON = re.compile(r"\bincludeGroups\s*=\s*true\b")
_KIND_GROUP = re.compile(r"conversationKind[^\n]{0,80}group", re.I)
_LIST_NAME = re.compile(
    r"(?:h|hit)\s*\.\s*person_name\s*\|\|"
    r"\s*(?:h|hit)\s*\.\s*conversation_title"
)
_FIRST_LIVE = re.compile(
    r"ORDER\s+BY\s+(?:p|persons)\.id\s+LIMIT\s+1"
    r"|MIN\s*\(\s*(?:p|persons)\.id\s*\)",
    re.I,
)
_UNIQUE = re.compile(
    r"COUNT\s*\("
    r"|HAVING\s+COUNT"
    r"|\.len\s*\(\s*\)\s*==\s*1"
    r"|==\s*1(?:usize|u32|u64|i32|i64)?"
    r"|==\s*1\s*\)",
    re.I,
)
_DOCS_ENTER_ADA = re.compile(
    r"Enter.{0,160}(?:Ada|People|timeline).{0,80}(?:timeline|message|opens?)",
    re.I | re.S,
)
_DOCS_SENDER_JUMP = re.compile(
    r"(?:from.me|sent|you sent).{0,80}(?:opens?|jumps?).{0,40}Self"
    r"|Enter.{0,80}(?:sender|Self).{0,40}(?:timeline|person)",
    re.I | re.S,
)
_STRUCT_HIT = re.compile(r"pub\s+struct\s+SearchHit\s*\{")


def _people_src(root: Path) -> str:
    parts: list[str] = []
    src = root / "crates" / "interlace-core" / "src" / "people.rs"
    if src.is_file():
        parts.append(src.read_text())
    d = root / "crates" / "interlace-core" / "src" / "people"
    if d.is_dir():
        for p in sorted(d.glob("*.rs")):
            parts.append(p.read_text())
    return "\n".join(parts)


def _callee_bodies(blob: str, from_body: str, depth: int = 2) -> str:
    parts = [from_body]
    seen = set(_SKIP_CALLEES)

    def walk(src: str, left: int) -> None:
        if left <= 0:
            return
        for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", src):
            name = m.group(1)
            if name in seen or name.startswith("parse_"):
                continue
            seen.add(name)
            inner = _rust_function_body(blob, name)
            if not inner:
                continue
            parts.append(inner)
            walk(inner, left - 1)

    walk(from_body, depth)
    return "\n".join(parts)


def _enrichment(ipc_src: str, people_src: str) -> str:
    cmd = _rust_function_body(ipc_src, "search_cmd")
    if not cmd:
        return ""
    blob = ipc_src + "\n" + people_src
    return _callee_bodies(blob, cmd)


def _search_hit_struct(model: str) -> str:
    m = _STRUCT_HIT.search(model)
    if not m:
        return ""
    brace = model.find("{", m.start())
    if brace < 0:
        return ""
    depth = 0
    i = brace
    while i < len(model):
        if model[i] == "{":
            depth += 1
        elif model[i] == "}":
            depth -= 1
            if depth == 0:
                return model[brace + 1 : i]
        i += 1
    return model[brace + 1 : brace + 400]


def _has_sender_self(blob: str) -> bool:
    return bool(_SELF_IDENTITIES.search(blob) or _IS_SELF_ONE.search(blob))


def _has_peer_remap(blob: str) -> bool:
    return bool(
        _PARTICIPANTS.search(blob)
        and _has_sender_self(blob)
        and _IS_SELF_ZERO.search(blob)
        and _DM.search(blob)
        and _EMAIL.search(blob)
        and _UNIQUE.search(blob)
        and _TOMBSTONE.search(blob)
    )


def _jk_branches(hits_key: str) -> str:
    parts: list[str] = []
    for rx in (_KEY_J, _KEY_K):
        for m in rx.finditer(hits_key):
            start = hits_key.rfind("if", 0, m.start())
            if start < 0:
                start = max(0, m.start() - 80)
            brace = hits_key.find("{", m.start())
            if brace < 0:
                parts.append(hits_key[start : m.end() + 240])
                continue
            depth = 0
            i = brace
            while i < len(hits_key):
                if hits_key[i] == "{":
                    depth += 1
                elif hits_key[i] == "}":
                    depth -= 1
                    if depth == 0:
                        parts.append(hits_key[start : i + 1])
                        break
                i += 1
    return "\n".join(parts)


def assert_search_jump_peer(crate: Path) -> None:
    """#402: search_cmd remaps from-me dm/email_thread hits to the unique peer."""
    root = repo_root()
    search_path = _web_file(crate, "SearchPane.svelte")
    hits_path = _web_file(crate, "SearchHits.svelte")
    app_path = crate / "web" / "App.svelte"
    api_path = _web_file(crate, "api.ts")
    ipc_path = crate / "src" / "ipc.rs"
    model_path = root / "crates" / "interlace-core" / "src" / "model.rs"
    docs_path = root / "docs" / "user" / "app.md"
    if not search_path.is_file():
        fail(f"{_ISSUE}: SearchPane.svelte required (activateHit still h.person_id)")
    if not hits_path.is_file():
        fail(f"{_ISSUE}: SearchHits.svelte required (list person_name is the peer)")
    if not app_path.is_file():
        fail(f"{_ISSUE}: App.svelte required (jumpToMessage still #124)")
    if not ipc_path.is_file():
        fail(f"{_ISSUE}: ipc.rs search_cmd required (remap person_id / person_name)")

    search_raw = search_path.read_text()
    hits_raw = _text(hits_path)
    app_raw = app_path.read_text()
    api_raw = _text(api_path)
    ipc_raw = ipc_path.read_text()
    model_raw = _text(model_path)
    docs_raw = _text(docs_path)
    people_raw = _people_src(root)

    search = _without_comments(search_raw)
    hits = _without_comments(hits_raw)
    app = _without_comments(app_raw)
    api = _without_comments(api_raw)
    hits_m = _svelte_markup(hits_raw) if hits_raw else ""
    pane_m = _svelte_markup(search_raw)

    activate = _fn(search, "activateHit") or _fn(search_raw, "activateHit")
    hits_key = _fn(search, "onHitsKey") or _fn(search_raw, "onHitsKey")
    jump = _fn(app, "jumpToMessage") or _fn(app_raw, "jumpToMessage")
    enter = _enter_branch(hits_key)
    click = _click_path(search, _hits_each_block(hits_m or hits))
    jk = _jk_branches(hits_key)
    cmd = _rust_function_body(ipc_raw, "search_cmd")
    enrich = _enrichment(ipc_raw, people_raw)
    hit_struct = _search_hit_struct(model_raw)

    # 1) keep-124-activate — Enter still activateHit → h.person_id + message_id.
    if not activate:
        fail(f"{_ISSUE}: keep activateHit — Enter still jumps h.person_id (#124)")
    if not _PERSON_GUARD.search(activate):
        fail(
            f"{_ISSUE}: keep activateHit guard — jump only when h.person_id is set "
            "(no person still does not jump)"
        )
    if not _HIT_PERSON_ID_READ.search(activate):
        fail(
            f"{_ISSUE}: activateHit still passes personId: h.person_id "
            "(remap in search_cmd JSON, not a new jump field)"
        )
    if not _HIT_MESSAGE_ID_READ.search(activate):
        fail(f"{_ISSUE}: keep #124 message_id — activateHit still carries h.message_id")
    if not _SENT_AT_PAYLOAD.search(activate):
        fail(f"{_ISSUE}: keep #124 sentAt: h.sent_at on the jump payload")
    if _JUMP_PERSON_FIELD.search(activate) or _JUMP_PERSON_FIELD.search(api):
        fail(
            f"{_ISSUE}: no jump_person_id — Enter still uses h.person_id "
            "(peer is that field after search_cmd remap)"
        )
    if re.search(r"\bis_self\b|\bself_identities\b|\bconversation_participants\b", activate):
        fail(
            f"{_ISSUE}: remap person_id in search_cmd, not in activateHit "
            "(keep the #124 pass-through)"
        )

    # 2) keep-124 Enter path.
    if not enter or not _ACTIVATE.search(enter):
        fail(f"{_ISSUE}: keep Enter → activateHit (#124 / #371)")
    if not jump:
        fail(f"{_ISSUE}: keep jumpToMessage (#124)")
    if not _VIEW_PEOPLE.search(jump):
        fail(f"{_ISSUE}: keep jumpToMessage view = \"people\" (#124)")
    if not re.search(r"\bopenPersonAtMessage\s*\(", jump):
        fail(f"{_ISSUE}: keep jumpToMessage → openPersonAtMessage (#124)")

    # 3) keep-371 click / j/k preview only.
    if _JUMP_OR_VIEW.search(click):
        fail(
            f"{_ISSUE}: keep #371 — click selects for preview, it must not jump "
            "(no activateHit / onJumpToMessage / view = \"people\")"
        )
    if _ACTIVATE.search(jk) or _JUMP_OR_VIEW.search(jk):
        fail(
            f"{_ISSUE}: keep #371 — j/k still preview only "
            "(no activateHit / onJumpToMessage)"
        )
    if _NEW_INVOKE.search(search) or _NEW_INVOKE.search(hits):
        fail(
            f"{_ISSUE}: keep #371 — no new invoke name on SearchPane / SearchHits "
            "(search_cmd / search_body / labels_list only)"
        )

    # 4) keep-371 no-person never jumps.
    if re.search(
        r"(?:person_id|personId)[^\n]{0,80}(?:==\s*null|===\s*null)"
        r"[\s\S]{0,240}(?:onJumpToMessage|jumpToMessage|openPersonAtMessage|"
        r"view\s*=\s*[\"']people[\"'])",
        activate,
    ):
        fail(
            f"{_ISSUE}: a hit with no person_id never jumps "
            "(unlinked sender — do not invent a person)"
        )

    # 5) keep group include-groups; do not remap group in chrome.
    if not (_KIND_GROUP.search(jump) and _INCLUDE_GROUPS_ON.search(jump)):
        fail(
            f"{_ISSUE}: keep group Enter — jumpToMessage still sets includeGroups "
            "when conversationKind is group (#124)"
        )

    # 6) list still shows person_name (peer after remap).
    if not _LIST_NAME.search(hits_m) and not _LIST_NAME.search(hits):
        fail(
            f"{_ISSUE}: keep SearchHits list meta — person_name || conversation_title "
            "(person_name is the peer after remap)"
        )

    # 7) keep-fts — core SearchHit shape + search() still used. Do not open search.rs.
    if not cmd:
        fail(f"{_ISSUE}: search_cmd required")
    if not _SEARCH_CALL.search(cmd):
        fail(
            f"{_ISSUE}: keep FTS search() — person remap is post-hit enrichment "
            "in search_cmd / a people helper, not a search.rs rewrite"
        )
    if re.search(r"\bperson_id\b", hit_struct):
        fail(
            f"{_ISSUE}: keep core SearchHit shape — person_id stays search_cmd JSON "
            "(do not put jump person on FTS SearchHit)"
        )
    if not _PERSON_ID_JSON.search(cmd) or not _PERSON_NAME_JSON.search(cmd):
        fail(
            f"{_ISSUE}: search_cmd JSON still has person_id and person_name "
            "(activateHit reads those fields)"
        )

    # 8) docs — Enter still opens Ada; do not document sender-as-jump.
    if docs_raw and not _DOCS_ENTER_ADA.search(docs_raw):
        fail(
            f"{_ISSUE}: keep docs/user/app.md — Enter opens Ada’s timeline on that message"
        )
    if docs_raw and _DOCS_SENDER_JUMP.search(docs_raw):
        fail(
            f"{_ISSUE}: do not document sender-as-jump for DMs — Enter opens the peer"
        )

    # 9) Primary red today: search_cmd is still sender-only.
    if not _has_peer_remap(enrich):
        fail(
            f"{_ISSUE}: search_cmd still sender-only — remap person_id and "
            "person_name to the unique live non-self participant on a from-me "
            "dm / email_thread"
        )

    # 10) many-peers: not first-live MIN(id) / ORDER BY id LIMIT 1.
    if _FIRST_LIVE.search(enrich) and not _UNIQUE.search(enrich):
        fail(
            f"{_ISSUE}: many-peers keep sender — do not pick MIN(p.id) / "
            "ORDER BY p.id LIMIT 1 (exactly one live non-self person, else sender)"
        )

    # 11) group: remap filter is dm + email_thread, not group.
    remap_kinds = ""
    kind_in = re.search(
        r"kind\s+IN\s*\(([^)]{0,200})\)",
        enrich,
        re.I,
    )
    if kind_in:
        remap_kinds = kind_in.group(1)
    if remap_kinds and _GROUP_KIND.search(remap_kinds) and _PARTICIPANTS.search(enrich):
        fail(
            f"{_ISSUE}: group hits stay sender — do not remap kind=group "
            "person_id to a participant"
        )

    # 12) do not invent a person / steal To-Cc / title-match.
    if _RECIPIENTS.search(enrich):
        fail(
            f"{_ISSUE}: do not join message_recipients — peers are "
            "conversation_participants only"
        )
    if _INSERT_PERSON.search(enrich) or _PROMOTE.search(enrich):
        fail(
            f"{_ISSUE}: do not invent a person (no INSERT persons / "
            "promote_unlinked_names on the jump path)"
        )
    if _TITLE_AS_PERSON.search(enrich):
        fail(f"{_ISSUE}: do not take person_id / person_name from c.title")

    # 13) person_name remaps with person_id (list-name-peer).
    if _PARTICIPANTS.search(enrich) and not re.search(
        r"\bdisplay_name\b",
        enrich,
    ):
        fail(
            f"{_ISSUE}: person_name is the same peer display_name as person_id "
            "(list shows Ada, not Self, on a sent DM)"
        )
