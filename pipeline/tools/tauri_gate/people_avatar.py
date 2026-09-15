"""#366 — person avatar from Contacts PHOTO (mix A).

Wired immediately after assert_person_inspector (#213 family).

Confirmed mix: PersonSummary.photo_cas_hash: Option<String> batch-attached
in the same person_list tx. which-photo = MIN(contacts_raw.id) among
non-null hashes. Bytes via cas_data_url cache (not cas://, not per-row
person_photo IPC, not bytes in the people JSON).

Chrome: one PersonAvatar.svelte on expanded people row, collapsed rail,
inspector header, merge picker. Reserved size-8. Initials: two-word first
letters / Ada→AD / empty User / CJK one grapheme. self same PHOTO/initials
rule. src / {#key} = person id + hash. Name-only / missing blob / onerror
→ initials. No Search/timeline faces. No image crate / dHash. D24 app.md.
Muted initials.

#138 / #212 / #213 / #265 stay as their own asserts. Do not delete them.
Placeholders only (Ada / Berk).
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.scan import (
    _match_closer,
    _svelte_markup,
    _without_comments,
)

_ISSUE = "#366"

_AVATAR_FILE = "PersonAvatar.svelte"
_SURFACES = (
    "PeopleSidebar.svelte",
    "PeopleInspector.svelte",
    "MergeDialog.svelte",
)
_NO_FACE = (
    "SearchHits.svelte",
    "SearchPane.svelte",
    "TimelineRows.svelte",
    "TimelineList.svelte",
    "TimelinePane.svelte",
)

_IMPORT_AVATAR = re.compile(
    r"""import\s+PersonAvatar\s+from\s+["'][^"']*PersonAvatar\.svelte["']"""
)
_PERSON_PHOTO_IPC = re.compile(
    r"""
    \binvoke\s*\(\s*["']person_photo["']
    |\bapi\s*\.\s*personPhoto\s*\(
    |\bpersonPhoto\s*\(\s*p\s*\.\s*id
    |\bpeoplePhoto\s*\(
    |\bfunction\s+person_photo\b
    |\basync\s+fn\s+person_photo\b
    """,
    re.I | re.X,
)
_HTTP_SRC = re.compile(
    r"""
    <img\b[^>]{0,400}https?://
    |src\s*=\s*["']https?://
    |\bgravatar\b
    """,
    re.I | re.S | re.X,
)
_CAS_SCHEME_SRC = re.compile(
    r"""src\s*=\s*["'{`][^"'`]{0,80}cas://""",
    re.I,
)
_CAS_DATA_URL = re.compile(r"\bcasDataUrl\s*\(")
_ONERROR = re.compile(r"\bonerror\b")
_SIZE_8 = re.compile(r"\bsize-8\b")
_MUTED = re.compile(
    r"\btext-muted-foreground\b|\bbg-muted\b|--chrome-chip-fg|--chrome-chip-bg"
)
_RAW_HUE = re.compile(
    r"""(?:color|background(?:-color)?)\s*:\s*#|text-(?:red|blue|green|yellow|orange|purple|pink)-\d{2,3}|--avatar-"""
)
_KEY_ID_HASH = re.compile(
    r"""
    \{#key\s+[^}]{0,200}(?:personId|person_id|\.id|p\.id)[^}]{0,200}(?:hash|photoCasHash|photo_cas_hash)
    |\{#key\s+[^}]{0,200}(?:hash|photoCasHash|photo_cas_hash)[^}]{0,200}(?:personId|person_id|\.id|p\.id)
    |key\s*=\s*\{[^}]{0,200}(?:personId|person_id|\.id)[^}]{0,200}(?:hash|photoCasHash|photo_cas_hash)
    """,
    re.I | re.X,
)
_INITIALS_SPLIT = re.compile(
    r"""\.split\s*\(\s*(?:/\\s\+/|["']\s+["']|/\s+/)"""
    r"""|\.split\s*\(\s*/\\s\+/"""
)
_INITIALS_TWO = re.compile(
    r"""
    \.slice\s*\(\s*0\s*,\s*2\s*\)
    |\.substring\s*\(\s*0\s*,\s*2\s*\)
    |\.substr\s*\(\s*0\s*,\s*2\s*\)
    """,
    re.X,
)
_EMPTY_USER = re.compile(
    r"""
    @lucide/svelte/icons/user
    |<User\b
    """,
    re.I | re.X,
)
_CJK_ONE = re.compile(
    r"""
    Intl\.Segmenter
    |Array\.from\s*\(
    |\[\s*\.\.\.\s*(?:name|displayName|display_name|n)\s*\]
    |\\p\{(?:Script=Han|L)
    |\bgrapheme
    """,
    re.I | re.X,
)
_PHOTO_FIELD_RS = re.compile(r"\bphoto_cas_hash\s*:\s*Option\s*<\s*String\s*>")
_PHOTO_FIELD_TS = re.compile(r"\bphoto_cas_hash\s*\??\s*:\s*string")
_PHOTO_BYTES = re.compile(
    r"\bphoto_bytes\b|\bphoto_data\b|\bphotoCasBytes\b|photo_cas_hash\s*:\s*Vec\s*<"
)
_IMAGE_CRATE = re.compile(
    r"""(?m)^\s*(?:image\s*=|image\s*\{)\s*"""
    r"""|^\s*image\s*=\s*["']"""
)
_DHASH_COMPUTE = re.compile(
    r"""
    \bphoto_dhash\s*=
    |\bphoto_dhash\b.{0,40}(?:UPDATE|SET)
    |\bdhash\s*\(
    """,
    re.I | re.X,
)
_ATTACH_PHOTO = re.compile(
    r"\battach_photo_hashes\b|\battach_photo\b"
)
_UNCHECKED_TX = re.compile(r"\bunchecked_transaction\b")
_CAS_GET = re.compile(r"\bcas_get\b|\bfs::read\b")
_DOCS_AVATAR = re.compile(
    r"""
    (?:
        (?:contact\s+)?photo.{0,80}initials
        |initials.{0,80}(?:contact\s+)?photo
        |local(?:-|\s+)CAS.{0,80}(?:avatar|photo|initials)
        |(?:avatar|face).{0,80}(?:initials|contact\s+photo|local)
    )
    """,
    re.I | re.S | re.X,
)
_GROUP_PARTICIPANTS = re.compile(
    r"<ul\b[^>]{0,200}data-group-participants\b[^>]*>[\s\S]{0,4000}?</ul>",
    re.I,
)
_BLIND = frozenset({"identity.rs", "search.rs"})
_BLIND_DIRS = frozenset({"import"})


def _text(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


def _rust_struct_body(src: str, name: str) -> str:
    m = re.search(rf"(?:pub\s+)?struct\s+{re.escape(name)}\s*\{{", src)
    if not m:
        return ""
    start = src.find("{", m.start())
    if start < 0:
        return ""
    end = _match_closer(src, start)
    if end < 0:
        return src[start:]
    return src[start : end + 1]


def _core_people_blob(root: Path) -> str:
    parts: list[str] = []
    base = root / "crates" / "interlace-core" / "src"
    for rel in ("people.rs", "people/list.rs", "people/attach.rs"):
        p = base / rel
        if p.is_file():
            parts.append(p.read_text())
    return "\n".join(parts)


def _core_toml_blob(root: Path) -> str:
    parts: list[str] = []
    for rel in (
        "Cargo.toml",
        "crates/interlace-core/Cargo.toml",
        "crates/interlace-tauri/Cargo.toml",
    ):
        p = root / rel
        if p.is_file():
            parts.append(p.read_text())
    return "\n".join(parts)


def _web_file(crate: Path, name: str) -> Path:
    return crate / "web" / "lib" / name


def _if_else_blocks(src: str, cond: str) -> tuple[str, str]:
    m = re.search(rf"\{{#if\s+{cond}\}}", src)
    if not m:
        return "", ""
    start = m.end()
    depth = 1
    i = start
    else_at = -1
    while i < len(src) and depth:
        nxt_if = src.find("{#if", i)
        nxt_else = src.find("{:else", i)
        nxt_end = src.find("{/if}", i)
        cands = [(p, k) for p, k in ((nxt_if, "if"), (nxt_else, "else"), (nxt_end, "end")) if p >= 0]
        if not cands:
            break
        pos, kind = min(cands)
        if kind == "if":
            depth += 1
            i = pos + 4
        elif kind == "else" and depth == 1 and else_at < 0:
            else_at = pos
            i = pos + 6
        elif kind == "end":
            depth -= 1
            if depth == 0:
                mid = else_at if else_at >= 0 else pos
                then = src[start:mid]
                els = src[else_at + 6 : pos] if else_at >= 0 else ""
                return then, els
            i = pos + 5
        else:
            i = pos + 6
    return "", ""


def assert_people_avatar(crate: Path) -> None:
    """#366: shared PersonAvatar from list photo_cas_hash (mix A)."""
    root = repo_root()
    avatar_path = _web_file(crate, _AVATAR_FILE)
    if not avatar_path.is_file():
        fail(f"{_ISSUE}: PersonAvatar.svelte missing")

    avatar = _text(avatar_path)
    avatar_clean = _without_comments(avatar)
    avatar_mark = _svelte_markup(avatar)

    # 2) Four surfaces share the same module.
    for name in _SURFACES:
        src = _text(_web_file(crate, name))
        if not _IMPORT_AVATAR.search(src):
            fail(
                f"{_ISSUE}: {name} must import PersonAvatar.svelte "
                "(shared component on expanded / collapsed / inspector / merge)"
            )

    sidebar = _text(_web_file(crate, "PeopleSidebar.svelte"))
    sidebar_mark = _svelte_markup(sidebar)
    collapsed, expanded = _if_else_blocks(sidebar_mark, r"sidebarCollapsed")
    if "PersonAvatar" not in collapsed:
        fail(
            f"{_ISSUE}: collapsed rail must mount PersonAvatar "
            "(upgrade the size-8 glyph, same rule)"
        )
    if "PersonAvatar" not in expanded:
        fail(
            f"{_ISSUE}: expanded people row must mount PersonAvatar "
            "(reserved face next to the name)"
        )

    inspector = _text(_web_file(crate, "PeopleInspector.svelte"))
    inspector_mark = _svelte_markup(inspector)
    header = inspector_mark
    title = re.search(r"\{personTitle\}", inspector_mark)
    if title:
        header = inspector_mark[max(0, title.start() - 400) : title.end() + 200]
    if "PersonAvatar" not in header and "PersonAvatar" not in inspector_mark:
        fail(f"{_ISSUE}: inspector header must mount PersonAvatar beside personTitle")

    merge = _text(_web_file(crate, "MergeDialog.svelte"))
    merge_mark = _svelte_markup(merge)
    merge_each = re.search(
        r"\{#each\s+mergeList\b[\s\S]{0,2500}?\{/each\}", merge_mark
    )
    merge_body = merge_each.group(0) if merge_each else merge_mark
    if "PersonAvatar" not in merge_body:
        fail(f"{_ISSUE}: merge picker must mount PersonAvatar (same list field / component)")

    # 3) List field — hash only, not bytes.
    people_rs = _text(root / "crates" / "interlace-core" / "src" / "people.rs")
    summary = _rust_struct_body(people_rs, "PersonSummary")
    if not _PHOTO_FIELD_RS.search(summary):
        fail(
            f"{_ISSUE}: PersonSummary.photo_cas_hash: Option<String> "
            "(batch attach on person_list, not a sidecar)"
        )
    api_ts = _text(_web_file(crate, "api.ts"))
    if not _PHOTO_FIELD_TS.search(api_ts):
        fail(f"{_ISSUE}: api.ts Person must carry photo_cas_hash (64-hex or null)")
    if _PHOTO_BYTES.search(summary) or _PHOTO_BYTES.search(api_ts):
        fail(f"{_ISSUE}: people JSON is the 64-hex only — not photo bytes / data:")

    people_blob = _core_people_blob(root)
    people_clean = _without_comments(people_blob)
    if not _ATTACH_PHOTO.search(people_clean):
        fail(
            f"{_ISSUE}: photo attach must be a batch sibling of "
            "attach_identity_values (attach_photo_hashes in the list tx)"
        )
    if _ATTACH_PHOTO.search(people_clean) and not _UNCHECKED_TX.search(people_clean):
        fail(
            f"{_ISSUE}: photo attach stays in the same unchecked_transaction "
            "as attach_identity_values (#265)"
        )
    if _CAS_GET.search(people_clean) and re.search(
        r"attach_photo|photo_cas_hash", people_clean
    ):
        # person_list must not read CAS bytes while attaching hashes.
        attach_hit = _ATTACH_PHOTO.search(people_clean)
        if attach_hit:
            window = people_clean[max(0, attach_hit.start() - 200) : attach_hit.end() + 800]
            if _CAS_GET.search(window):
                fail(
                    f"{_ISSUE}: person_list must not cas_get / fs::read photo bytes "
                    "(hash only; missing blob still Ok)"
                )

    # 4) No per-row person_photo IPC.
    chrome = "\n".join(_text(_web_file(crate, n)) for n in (*_SURFACES, "api.ts", _AVATAR_FILE))
    tauri_main = _text(crate / "src" / "main.rs")
    if _PERSON_PHOTO_IPC.search(chrome) or _PERSON_PHOTO_IPC.search(tauri_main):
        fail(
            f"{_ISSUE}: no per-row person_photo IPC "
            "(hash rides person_list; bytes are casDataUrl(hash))"
        )

    # 5) Reserved size-8 slot (present with and without a hash).
    if not _SIZE_8.search(avatar_mark) and not _SIZE_8.search(avatar_clean):
        fail(f"{_ISSUE}: PersonAvatar must reserve a size-8 slot on all four surfaces")
    img_only = re.search(
        r"\{#if\s+[^}]{0,160}(?:src|hash|photoCasHash)[^}]*\}[\s\S]{0,400}size-8",
        avatar_mark,
    )
    size_in_root = bool(_SIZE_8.search(avatar_mark) or _SIZE_8.search(avatar_clean))
    if img_only and not size_in_root:
        fail(
            f"{_ISSUE}: size-8 must sit in the layout before casDataUrl resolves "
            "(do not mount the slot only on <img>)"
        )

    # 6) Wrong-face key = person id + hash.
    key_src = avatar_mark + "\n" + avatar_clean + "\n" + sidebar_mark + "\n" + merge_mark
    if not _KEY_ID_HASH.search(key_src):
        fail(
            f"{_ISSUE}: src / {{#key}} must include person id and hash "
            "(Ada → Berk must not keep Ada's face)"
        )

    # 7) Missing blob / onerror → initials, never a broken <img>.
    if not _ONERROR.search(avatar):
        fail(f"{_ISSUE}: <img onerror> must fall back to initials (never a broken image)")
    if not _EMPTY_USER.search(avatar):
        fail(f"{_ISSUE}: empty display_name uses Lucide User (not a blank or ?)")
    if not _INITIALS_SPLIT.search(avatar_clean) and not _INITIALS_TWO.search(avatar_clean):
        fail(
            f"{_ISSUE}: initials are two-word first letters, or first two letters "
            "of one word (Ada → AD)"
        )
    if not _INITIALS_TWO.search(avatar_clean):
        fail(f"{_ISSUE}: one-word initials are the first two letters (Ada → AD)")
    if not _CJK_ONE.search(avatar_clean) and not re.search(
        r"(?:length|grapheme|segment).{0,40}===?\s*1", avatar_clean
    ):
        # slice(0, 2) on a single BMP CJK char already stays one; still require
        # a one-grapheme path so a lone ideograph is not padded.
        if not re.search(r"\blength\b", avatar_clean):
            fail(f"{_ISSUE}: CJK / single grapheme initials stay one (do not pad)")

    # 8) casDataUrl, not http / gravatar / cas://.
    if not _CAS_DATA_URL.search(avatar_clean):
        fail(
            f"{_ISSUE}: PersonAvatar loads bytes via casDataUrl "
            "(Vite cannot fetch cas://)"
        )
    if _HTTP_SRC.search(avatar) or _HTTP_SRC.search(inspector_mark):
        fail(f"{_ISSUE}: no http(s) / gravatar avatar src (local CAS / data: only)")
    if _CAS_SCHEME_SRC.search(avatar):
        fail(f"{_ISSUE}: do not set <img src> to cas:// (use casDataUrl / data:)")

    # 9) No Search / timeline / in-this-group faces.
    for name in _NO_FACE:
        src = _text(_web_file(crate, name))
        if _IMPORT_AVATAR.search(src) or re.search(r"<PersonAvatar\b", src):
            fail(f"{_ISSUE}: do not mount PersonAvatar on {name}")
    group_ul = _GROUP_PARTICIPANTS.search(inspector_mark) or _GROUP_PARTICIPANTS.search(
        inspector
    )
    if group_ul and re.search(r"<PersonAvatar\b", group_ul.group(0)):
        fail(
            f"{_ISSUE}: do not put faces on data-group-participants "
            "(keep #322 img-free names)"
        )

    # 10) No image crate / dHash on this ticket.
    toml = _core_toml_blob(root)
    if _IMAGE_CRATE.search(toml) or re.search(
        r"""(?m)^\s*image\s*=\s*\{""", toml
    ):
        fail(f"{_ISSUE}: do not add the image crate (#80 / D14)")
    if _DHASH_COMPUTE.search(people_clean):
        fail(f"{_ISSUE}: do not compute photo_dhash (#80 / D14)")

    # 11) D24 — people / inspector / merge mention local photo or initials.
    docs = _text(root / "docs" / "user" / "app.md")
    if not _DOCS_AVATAR.search(docs):
        fail(
            f"{_ISSUE}: docs/user/app.md must say the people row / inspector / "
            "merge picker show a local contact photo or initials"
        )

    # 12) Muted initials (light + dark stay readable).
    if not _MUTED.search(avatar):
        fail(
            f"{_ISSUE}: initials use a muted token "
            "(text-muted-foreground / bg-muted — no new --avatar-* hue)"
        )
    if _RAW_HUE.search(avatar_mark):
        fail(f"{_ISSUE}: initials must not invent a raw hue or --avatar-* token")
