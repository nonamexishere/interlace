"""#307 fold — PR #327 review (empty-bookmark clobber, & labels,
ACTIVE restore, stable ids, move-dedup).

Additive checks for IN Do 1–5 only. Existing assert_recent_archives
keep-checks 1–14 stay. Do not grep comments (Do 6–7 are impl-only).
Placeholders ArchiveA / ArchiveB / Ada.

Must-IDs: recent-keep-old-bookmark, recent-ampersand-label,
recent-restore-active, recent-stable-id, recent-move-dedup.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.recent_archives import (
    _MENU_FNS,
    _RESOLVE,
    _named_bodies,
    _read,
)
from tauri_gate.scan import (
    _match_closer,
    _rust_fn_body,
    _tauri_rust_blob,
    _without_comments,
)

_EMPTY_BM = re.compile(r"\bbookmark\s*\.\s*is_empty\s*\(")
_EXISTING_BM = re.compile(r"\.bookmark\b")
_MOVE_EXISTING = re.compile(r"\b(?:remove|swap_remove)\s*\(")
_AMP_ESC = re.compile(
    r"""\.replace\s*\(\s*(?:'&'|"&")\s*,\s*(?:"&&"|'&&')"""
)
_INDEX_ID = re.compile(
    r"""format!\s*\(\s*["']recent-\{(?:i|idx|index)\}["']"""
    r"""|format!\s*\(\s*["']recent-\{\}["']\s*,\s*(?:i|idx|index)\b"""
)
_PARSE_USIZE = re.compile(r"parse\s*::\s*<\s*usize\s*>")
_INDEX_GET = re.compile(r"recents\w*\.get\s*\(\s*(?:idx|index|i)\s*\)")
_DROP_USIZE_SIG = re.compile(r"fn\s+drop_recent\s*\(\s*\w+\s*:\s*usize\b")
_DROP_USIZE_CALL = re.compile(r"\bdrop_recent\s*\(\s*(?:idx|index|i)\s*\)")
_HASH_ID = re.compile(r"DefaultHasher|\bHasher\b|\.hash\s*\(")
_KEY_AS_ID = re.compile(
    r"""format!\s*\(\s*["']recent-[^"']*["']\s*,\s*&?(?:entry\.)?path"""
    r"""|\.text\s*\(\s*&?(?:entry\.)?path\b"""
    r"""|with_id\s*\([^;]{0,80}(?:entry\.)?path"""
)
_KEY_LOOKUP = re.compile(
    r"\.path\s*==|recent_menu_id|recent_item_id|recent_id\s*\("
)
_KEY_ARG = re.compile(r"path|key|stored|picked|old_key|\.path\b|id\b")
_IS_DIR_ELSE = re.compile(
    r"filter\s*\(\s*\|[^|]*\|\s*[^)]*is_dir\s*\(\s*\)\s*\)\s*else\s*\{"
)
_IF_NOT_DIR = re.compile(r"if\s+!\s*[\w.]+\s*\.\s*is_dir\s*\(\s*\)\s*\{")
_IF_DIR = re.compile(r"if\s+[\w.]+\s*\.\s*is_dir\s*\(\s*\)\s*\{")


def _fn(src: str, name: str) -> str:
    return _rust_fn_body(src, name)


def _keeps_old_bookmark_when_empty(rec: str) -> bool:
    if not rec.strip() or not _EMPTY_BM.search(rec):
        return False
    if _EXISTING_BM.search(rec):
        return True
    return bool(_MOVE_EXISTING.search(rec))


def _escapes_ampersand_in_menu(menu: str, rust: str) -> bool:
    if _AMP_ESC.search(menu):
        return True
    if not _AMP_ESC.search(rust):
        return False
    for name in re.findall(r"\b([A-Za-z_][\w]*)\s*\(", menu):
        body = _fn(rust, name)
        if body and _AMP_ESC.search(body):
            return True
    return False


def _brace_body(src: str, open_at: int) -> tuple[str, int]:
    if open_at < 0 or open_at >= len(src) or src[open_at] != "{":
        return "", -1
    close = _match_closer(src, open_at)
    if close < 0:
        return src[open_at + 1 :], -1
    return src[open_at + 1 : close], close


def _not_dir_blobs(src: str) -> tuple[str, str, str]:
    """fail blob (not a dir), success blob, prefix before the is_dir branch."""
    m = _IS_DIR_ELSE.search(src)
    if m:
        body, close = _brace_body(src, src.find("{", m.end() - 1))
        after = src[close + 1 :] if close >= 0 else ""
        return body, after, src[: m.start()]
    m = _IF_NOT_DIR.search(src)
    if m:
        body, close = _brace_body(src, src.find("{", m.end() - 1))
        after = src[close + 1 :] if close >= 0 else ""
        return body, after, src[: m.start()]
    m = _IF_DIR.search(src)
    if m:
        success, close = _brace_body(src, src.find("{", m.end() - 1))
        rest = src[close + 1 :] if close >= 0 else ""
        fail_b = ""
        em = re.match(r"\s*else\s*\{", rest)
        if em:
            fail_b, _ = _brace_body(rest, rest.find("{"))
        return fail_b, success, src[: m.start()]
    return "", src, ""


def _restores_active_on_drop(fail_blob: str, pick: str) -> bool:
    blob = fail_blob or pick
    if "read_last_bookmark" not in blob:
        return False
    at = blob.find("read_last_bookmark")
    return bool(_RESOLVE.search(blob[at:]))


def _uses_index_recent_id(menu: str, pick: str, session: str) -> bool:
    if _INDEX_ID.search(menu) or _INDEX_ID.search(pick):
        return True
    if _PARSE_USIZE.search(pick) or _INDEX_GET.search(pick):
        return True
    if _DROP_USIZE_SIG.search(session) or _DROP_USIZE_CALL.search(pick):
        return True
    return False


def _helper_makes_id(menu: str, rust: str) -> bool:
    for name in re.findall(r"\b([A-Za-z_][\w]*)\s*\(", menu):
        body = _fn(rust, name)
        if not body:
            continue
        if _HASH_ID.search(body) or re.search(r"format!\s*\(\s*[\"']recent-", body):
            return True
    return False


def _stable_recent_id(menu: str, pick: str, rust: str, session: str) -> bool:
    if _uses_index_recent_id(menu, pick, session):
        return False
    hashed = bool(_HASH_ID.search(menu) or _HASH_ID.search(rust))
    keyed = bool(_KEY_AS_ID.search(menu) or _helper_makes_id(menu, rust))
    lookup = bool(_KEY_LOOKUP.search(pick) or re.search(r"\.find\s*\(", pick))
    drop_sig = _fn(session, "drop_recent")
    drop_ok = bool(drop_sig) and not _DROP_USIZE_SIG.search(session)
    if not drop_sig:
        drop_ok = bool(re.search(r"\.retain\s*\(", pick))
    return (hashed or keyed) and lookup and drop_ok


def _drop_by_stored_key(src: str) -> bool:
    if not src.strip():
        return False
    for m in re.finditer(r"\bdrop_recent\s*\(\s*([^)]+)\)", src):
        arg = m.group(1).strip()
        if arg in {"idx", "index", "i"} or re.fullmatch(r"\d+", arg):
            continue
        if _KEY_ARG.search(arg):
            return True
    if re.search(r"\.retain\s*\(\s*\|[^|]+\|\s*[^)]*\.path\s*!=", src) and re.search(
        r"entry\s*\.\s*path|stored|old_key|picked|key\b", src
    ):
        return True
    return False


def _drops_picked_key_on_move(
    pick: str, persist: str, record: str
) -> bool:
    fail_b, success_b, prefix = _not_dir_blobs(pick)
    if _drop_by_stored_key(prefix + "\n" + success_b):
        return True
    extra = persist + "\n" + record
    if _drop_by_stored_key(extra) and re.search(
        r"old_key|previous|from_key|replace_key|picked", extra
    ):
        return True
    return False


def assert_recent_archives_fold(crate: Path) -> None:
    """#307 fold: keep old bookmark, && labels, ACTIVE restore, stable id, move-dedup."""
    root = repo_root()
    rust = _without_comments(_tauri_rust_blob(crate))
    menu_rs = _without_comments(_read(crate / "src" / "menu.rs"))
    session = _without_comments(
        _read(root / "crates" / "interlace-core" / "src" / "session.rs")
    )
    menu = _named_bodies(rust, _MENU_FNS) or menu_rs
    file_menu = _fn(rust, "file_menu") or _fn(menu_rs, "file_menu")
    pick = _fn(rust, "open_recent") or _fn(menu_rs, "open_recent")
    record = _fn(session, "record_recent")
    persist = _fn(rust, "persist_bookmark")

    # 1) recent-keep-old-bookmark
    if not _keeps_old_bookmark_when_empty(record):
        fail(
            "#307: record_recent must keep existing bookmark bytes when the "
            "incoming bookmark is empty (do not clobber a stored bookmark "
            "for ArchiveA; only store empty bytes on a first-time record)"
        )

    # 2) recent-ampersand-label
    label_src = file_menu or menu
    if not _escapes_ampersand_in_menu(label_src, rust):
        fail(
            "#307: Recent menu item text must escape & as && "
            "(folder basename ArchiveA & ArchiveB must show the ampersand; "
            "stored display token stays unescaped)"
        )
    if _AMP_ESC.search(record):
        fail(
            "#307: stored display token must stay unescaped "
            "(escape & as && only in menu item text; placeholders "
            "ArchiveA / ArchiveB / Ada)"
        )

    # 3) recent-restore-active
    fail_blob, _, _ = _not_dir_blobs(pick)
    if not _restores_active_on_drop(fail_blob, pick):
        fail(
            "#307: after a successful resolve that is not a directory, "
            "re-resolve read_last_bookmark() so ACTIVE returns to the open "
            "archive (do not leave the session scoped to a URL you just "
            "decided was unusable; do not resolve every recent at rebuild)"
        )
    if _RESOLVE.search(menu):
        fail(
            "#307: do not resolve every recent at rebuild "
            "(restore ACTIVE only on the drop path after a successful "
            "resolve that is not a directory)"
        )

    # 4) recent-stable-id
    if _uses_index_recent_id(file_menu or menu, pick, session) or not _stable_recent_id(
        file_menu or menu, pick, rust, session
    ):
        fail(
            "#307: menu id + pick lookup must be stable "
            "(hash of the dedup key, or the key itself) — not "
            "recent-{index} / parse::<usize> on the suffix; drop by that "
            "id/key, not by list index"
        )

    # 5) recent-move-dedup
    if not _drops_picked_key_on_move(pick, persist, record):
        fail(
            "#307: after a successful resolve+open of a picked recent, drop "
            "the picked entry by its stored key so a moved ArchiveA does "
            "not leave two basename rows (do not resolve every recent at "
            "rebuild)"
        )
    if _RESOLVE.search(menu):
        fail(
            "#307: do not resolve every recent at menu rebuild "
            "(drop the picked stored key on a successful pick; "
            "ACTIVE is one slot)"
        )
