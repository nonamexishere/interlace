"""#307 — File → Recent archives (native sibling bookmark list).

Approach A: native File Recent + sibling App Support list. Keep
last-archive.bookmark as the boot singleton. Rebuild after a successful
app open / init. Click one recent → resolve that bookmark only →
existing open (flock + People). Missing folder: drop on pick, no panic.
CLI does not write recents. Placeholders ArchiveA / ArchiveB / Ada.

Must-IDs (gate grep): recent-file-menu, recent-shows-a-and-b,
recent-pick-opens, recent-flock-people, recent-missing-no-panic,
recent-bookmarks-not-urls, recent-keep-last-archive, recent-keep-130,
recent-d24, recent-placeholders.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.locale_menu import (
    _CHECK_UPDATES_ITEM,
    _FILE_SUBMENU,
    _ICLOUD_MENU_ITEM,
    _IMPORT_ITEM,
    _OPEN_ITEM,
    _PREFERENCES_ITEM,
    _VIEW_SUBMENU,
    _menu_handler_surface,
    _on_menu_event_bodies,
)
from tauri_gate.scan import (
    _CONFIG_TOML,
    _LAST_PATH_API,
    _function_body,
    _rust_fn_body,
    _tauri_rust_blob,
    _web_logic,
    _without_comments,
)
from tauri_gate.status_toasts_chrome import _toml_keys_in_fn, _windows_around

_CONFIG_DIR = re.compile(
    r"\bconfig_dir\s*\(|\bINTERLACE_CONFIG_DIR\b|Application Support/Interlace"
)
_RECENT_SURFACE = re.compile(
    r"SubmenuBuilder\s*::\s*new\s*\(\s*[^,]+,\s*[\"']Recent(?: archives)?[\"']"
    r"|[\"']Recent archives[\"']|[\"']Open Recent[\"']"
    r"|MenuItem\s*::\s*with_id\s*\(\s*[^,]+,\s*[\"']recent[-_]"
    r"|\.text\s*\(\s*[\"']recent[-_]",
    re.I,
)
_RECENTS_WRITE = re.compile(
    r"\b(?:write|record|persist|save|add|push|insert|remember|touch)_recents?\w*\s*\(",
    re.I,
)
_RECENTS_READ = re.compile(r"\b(?:read|load|list|get)_recents?\w*\s*\(", re.I)
_RECENTS_WORD = re.compile(r"\brecents?\b", re.I)
_SET_MENU = re.compile(r"\bset_menu\s*\(|\brebuild_\w*menu\s*\(")
_RESOLVE = re.compile(r"\bresolve_security_scoped_bookmark\s*\(")
_CREATE_BM = re.compile(r"\bcreate_security_scoped_bookmark\s*\(")
_UNWRAP = re.compile(r"\.unwrap\s*\(|\.expect\s*\(|\bpanic!\s*\(")
_DROP = re.compile(
    r"\b(?:retain|swap_remove|remove_recent|drop_recent|delete_recent)\s*\("
    r"|\.remove\s*\(",
    re.I,
)
_CAP = re.compile(
    r"\b(?:MAX_RECENTS|RECENTS_CAP|RECENT_CAP|RECENT_LIMIT|MAX_RECENT)\b"
    r"|\.truncate\s*\(|while\s+[\w.]+\.len\s*\(\s*\)\s*>"
    r"|if\s+[\w.]+\.len\s*\(\s*\)\s*>",
    re.I,
)
_BASENAME = re.compile(
    r"\bfile_name\s*\(|\.file_name\b|\bfile_stem\s*\(|\bbasename\b|\bfileName\b",
    re.I,
)
_MRU = re.compile(
    r"\binsert\s*\(\s*0\s*,|\.push_front\s*\(|insert_front|most[-_ ]recent|rotate_right",
    re.I,
)
_DEDUP = re.compile(r"\bretain\s*\(|\.position\s*\(|dedup|same.{0,24}folder", re.I)
_CHECKMARK = re.compile(r"CheckMenuItem|set_checked\s*\(|\.checked\s*\(|checkmark", re.I)
_URL_STORE = re.compile(
    r"https?://|file://|NSRecentDocuments|noteNewRecentDocumentURL|NSDocumentController",
    re.I,
)
_ICLOUD = re.compile(r"\biCloud\b|NSUbiquitous|ubiquity", re.I)
_LAST_BM_FILE = re.compile(r"last-archive\.bookmark|\bLAST_BOOKMARK_FILE\b")
_OPEN_REACH = re.compile(
    r"\b(?:crate::)?(?:ipc::)?open\s*\(|\bopenPath\s*\(|\bapi\.open\s*\("
    r"|emit\s*\(\s*[\"'](?:menu-)?open-recent|emit\s*\(\s*[\"']menu-recent"
)
_PEOPLE_LOAD = re.compile(r"\b(?:openPath|applyStatus|refreshPeople|api\.open)\b")
_EXCLUSIVE = re.compile(r"\bLockMode\s*::\s*Exclusive\b")
_SHARED_OPEN = re.compile(r"\bLockMode\s*::\s*Shared\b")
_EMPTY_OMIT = re.compile(r"is_empty\s*\(\s*\)|!\s*[\w.]+\.is_empty\s*\(\s*\)")
_RECENT_ID = re.compile(r"[\"']recent[-_]|starts_with\s*\(\s*[\"']recent", re.I)
_BYTES = re.compile(r"Vec\s*<\s*u8\s*>|\bbookmark\b|\bbytes\b")
_REAL_HOME = re.compile(
    r"/Users/[A-Za-z]|/home/[A-Za-z]|Documents/Interlace|Desktop/Interlace"
)
_DOCS_RECENT = re.compile(
    r"File\s*(?:→|->)\s*Recent|Recent archives|File menu.{0,48}[Rr]ecent",
    re.I | re.S,
)
_DOCS_MISSING = re.compile(
    r"missing.{0,48}(?:folder|archive).{0,48}(?:crash|panic|drop)"
    r"|deleted.{0,24}folder.{0,48}(?:crash|panic|drop)|does not (?:crash|panic)",
    re.I | re.S,
)
_VIEW_LABELS = ("People", "Search", "Review", "Doctor")
_MENU_FNS = (
    "native_menu", "rebuild_menu", "rebuild_file_menu", "file_menu",
    "recent_submenu", "recent_menu", "build_recent",
)
_PICK_FNS = (
    "handle_recent", "open_recent", "on_recent", "pick_recent",
    "recent_clicked", "activate_recent", "open_recent_archive",
)
_WRITE_FNS = (
    "write_recents", "write_recent_archives", "save_recents", "record_recent",
    "persist_recent", "add_recent", "push_recent", "insert_recent",
    "remember_recent", "touch_recent",
)


def _read(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


def _named_bodies(src: str, names: tuple[str, ...]) -> str:
    return "\n".join(_rust_fn_body(src, n) for n in names)


def _file_submenu(src: str) -> str:
    m = re.search(r"SubmenuBuilder\s*::\s*new\s*\(\s*[^,]+,\s*[\"']File[\"']", src)
    return src[m.start() : m.start() + 4500] if m else ""


def _write_blob(session: str, rust: str) -> str:
    return "\n".join(
        [
            _named_bodies(session, _WRITE_FNS),
            _named_bodies(rust, _WRITE_FNS),
            _windows_around(session, _RECENTS_WRITE, before=80, after=500),
            _windows_around(rust, _RECENTS_WRITE, before=80, after=500),
        ]
    )


def _pick_blob(rust: str, web: str) -> str:
    chunks = [
        b
        for b in _on_menu_event_bodies(rust)
        if _RECENTS_WORD.search(b) or _RECENT_ID.search(b)
    ]
    chunks.append(_named_bodies(rust, _PICK_FNS))
    chunks.extend(filter(None, (_function_body(web, n) for n in _PICK_FNS)))
    handlers = _menu_handler_surface(rust, web)
    chunks.append(_windows_around(handlers, _RECENTS_WORD, before=80, after=400))
    chunks.append(_windows_around(handlers, _RECENT_ID, before=80, after=400))
    return "\n".join(chunks)


def _records_list(persist: str, open_b: str, init_b: str, session: str) -> bool:
    writers = persist + "\n" + open_b + "\n" + init_b
    if not _RECENTS_WRITE.search(writers) and not _RECENTS_WRITE.search(session):
        return False
    return bool(_RECENTS_WRITE.search(writers) or _RECENTS_WORD.search(persist))


def _menu_names_two(menu: str, session: str) -> bool:
    if not _RECENTS_READ.search(menu) and not _RECENTS_READ.search(session):
        return False
    return bool(
        re.search(r"\bfor\b.{0,120}recent", menu, re.I | re.S)
        or re.search(r"recents?\w*\.iter\s*\(", menu, re.I)
        or re.search(r"\bfor\b.{0,80}in\s+[\w.]*recents?", menu, re.I | re.S)
    )


def _placeholder_files(root: Path) -> list[Path]:
    # Not this module: scanning it matches _REAL_HOME's own needle.
    out = [
        root / "pipeline" / "state" / "307-test-author.md",
        root / "docs" / "user" / "app.md",
    ]
    tests = root / "crates" / "interlace-core" / "tests"
    if tests.is_dir():
        for p in tests.glob("*.rs"):
            text = p.read_text()
            if _RECENTS_WRITE.search(text) or re.search(r"recent.archive", text, re.I):
                out.append(p)
    return out


def assert_recent_archives(crate: Path) -> None:
    """#307: File → Recent archives (approach A + IN SPEC_GAP fills).

    Native File Recent. After two app opens the path can name ArchiveA and
    ArchiveB. Pick → existing open (flock + People). Missing: drop on pick,
    no unwrap; do not resolve every recent at rebuild. Opaque bytes in a
    sibling under config_dir() — not last-archive.bookmark / config.toml /
    URLs / iCloud. Keep last-archive + write_last_path + #130. Cap exists
    (not a 5-row fixture). CLI does not write recents. D24. Placeholders.
    """
    root = repo_root()
    rust = _without_comments(_tauri_rust_blob(crate))
    web = _without_comments(_web_logic(crate))
    menu_rs = _without_comments(_read(crate / "src" / "menu.rs"))
    session_path = root / "crates" / "interlace-core" / "src" / "session.rs"
    session = _without_comments(_read(session_path))
    cli = _without_comments(_read(root / "crates" / "interlace-core" / "src" / "cli.rs"))
    dtxt = _read(root / "docs" / "user" / "app.md")
    persist = _rust_fn_body(rust, "persist_bookmark")
    open_b = _rust_fn_body(rust, "open")
    init_b = _rust_fn_body(rust, "init")
    menu = _named_bodies(rust, _MENU_FNS) or menu_rs
    file_menu = _file_submenu(menu_rs) or _file_submenu(rust)
    pick = _pick_blob(rust, web)
    store = _write_blob(session, rust)
    handlers = _menu_handler_surface(rust, web)
    menu_all = menu_rs + rust

    # 1) recent-file-menu — File has a Recent surface besides Open + Import.
    if not menu_rs.strip() and not _rust_fn_body(rust, "native_menu").strip():
        fail(
            "#307: crates/interlace-tauri/src/menu.rs required "
            "(File → Recent archives lives on the native File menu)"
        )
    if not (_RECENT_SURFACE.search(file_menu) or _RECENT_SURFACE.search(menu)):
        fail(
            "#307: File menu must list Recent archives "
            "(submenu or items besides Open archive + Import)"
        )

    # 2) recent-shows-a-and-b — two successful opens can name both.
    if not _records_list(persist, open_b, init_b, session) or not _menu_names_two(
        menu, session
    ):
        fail(
            "#307: after two successful opens File → Recent must be able to "
            "name both ArchiveA and ArchiveB (persist a list of display "
            "tokens + bookmarks on app open / init; rebuild the File menu; "
            "not only last-archive.bookmark)"
        )

    # 3) recent-pick-opens — picking a recent reaches existing open.
    if not _RECENT_ID.search(pick) and not _RECENT_ID.search(handlers):
        fail(
            "#307: picking a Recent item must be wired "
            "(on_menu_event recent id → existing open)"
        )
    if not _OPEN_REACH.search(pick) and not _OPEN_REACH.search(handlers):
        fail(
            "#307: picking a Recent item must reach existing open "
            "(ipc open / openPath / api.open — flock + People)"
        )

    # 4) recent-flock-people — Exclusive flock + People load.
    if not open_b.strip() or not _EXCLUSIVE.search(open_b):
        fail(
            "#307: picking a recent must use existing open "
            "(Exclusive flock); do not invent a Shared opener"
        )
    if _SHARED_OPEN.search(pick):
        fail(
            "#307: picking a recent must use existing open "
            "(Exclusive flock), not LockMode::Shared"
        )
    if not _PEOPLE_LOAD.search(pick) and not _PEOPLE_LOAD.search(handlers):
        fail(
            "#307: picking a recent must load People "
            "(openPath / applyStatus / refreshPeople / api.open)"
        )

    # 5) recent-missing-no-panic — drop on failed pick; no unwrap; no probe.
    if not _RESOLVE.search(pick):
        fail(
            "#307: picking a recent must resolve that one bookmark "
            "(drop the entry if resolve fails or the folder is gone)"
        )
    if not _DROP.search(pick):
        fail(
            "#307: if resolve fails or the folder is gone, drop that "
            "Recent entry and rebuild — do not panic "
            "(placeholders ArchiveA / ArchiveB / Ada)"
        )
    if not _SET_MENU.search(pick) and not re.search(r"\bnative_menu\s*\(", pick):
        fail(
            "#307: after dropping a missing Recent entry, rebuild the "
            "File menu (omit Recent when the list is empty)"
        )
    if _UNWRAP.search(pick):
        fail(
            "#307: a missing folder must not unwrap / expect / panic "
            "(drop the entry on the failed pick)"
        )
    if _RESOLVE.search(menu):
        fail(
            "#307: do not resolve every recent at rebuild "
            "(bookmark ACTIVE is one slot; use stored display tokens; "
            "drop on pick only — no disable-at-rebuild)"
        )

    # 6) recent-bookmarks-not-urls — opaque bytes, sibling, not URLs.
    if not session_path.is_file():
        fail(
            "#307: crates/interlace-core/src/session.rs required "
            "(recents sibling under config_dir(); not config.toml)"
        )
    if not store.strip() or not _RECENTS_WRITE.search(store + session):
        fail(
            "#307: store recents as opaque bookmark bytes under "
            "session::config_dir() (sibling file; not last-archive.bookmark)"
        )
    if not _CONFIG_DIR.search(store) and "config_dir" not in store:
        fail(
            "#307: store recents in a sibling file under "
            "session::config_dir() (not config.toml / last-archive.bookmark)"
        )
    if _LAST_BM_FILE.search(store):
        fail(
            "#307: recents must not overwrite last-archive.bookmark "
            "(sibling file under session::config_dir())"
        )
    if _LAST_PATH_API.search(store) or _CONFIG_TOML.search(store):
        fail(
            "#307: do not persist recents via write_last_path / "
            "config.toml keys (sibling bookmark list)"
        )
    if _URL_STORE.search(store) or _URL_STORE.search(persist + pick):
        fail(
            "#307: recents are local security-scoped bookmark bytes "
            "(not http(s) / file:// / NSRecentDocuments)"
        )
    if _ICLOUD.search(store) or _ICLOUD.search(menu + persist):
        fail("#307: no iCloud recents")
    if not _CREATE_BM.search(persist) and not _BYTES.search(store):
        fail(
            "#307: recents store opaque bookmark bytes "
            "(same create/resolve path as last-archive; not URLs)"
        )

    # 7) recent-keep-last-archive — singleton + write_last_path stay.
    if 'LAST_BOOKMARK_FILE: &str = "last-archive.bookmark"' not in session:
        fail(
            "#307: keep last-archive.bookmark as the boot singleton "
            "(do not multiplex recents into that file)"
        )
    wl = _rust_fn_body(session, "write_last_path")
    if not wl.strip() or "last_archive_path" not in wl:
        fail("#307: keep session.rs write_last_path as the last_archive_path writer")
    extra = [k for k in _toml_keys_in_fn(wl) if k != "last_archive_path"]
    if extra:
        fail(
            "#307: do not rewrite session.rs write_last_path to dump "
            "extra keys (recents are not last_archive_path / config.toml)"
        )
    if not _rust_fn_body(session, "write_last_bookmark").strip() or not _rust_fn_body(
        session, "read_last_bookmark"
    ).strip():
        fail(
            "#307: keep write_last_bookmark / read_last_bookmark "
            "(last-archive singleton stays)"
        )
    if "read_last_bookmark" not in _rust_fn_body(rust, "remembered_path"):
        fail("#307: keep remembered_path on the last-archive.bookmark singleton")
    if "write_last_path" not in open_b:
        fail("#307: keep write_last_path on existing open")

    # 8) recent-keep-130 — Open archive, Import, View; no updater / prefs / iCloud.
    if not _FILE_SUBMENU.search(menu_all):
        fail("#307: keep #130 File submenu (Open archive + Import)")
    if not _OPEN_ITEM.search(menu_all):
        fail("#307: keep #130 File → Open archive")
    if not _IMPORT_ITEM.search(menu_all):
        fail("#307: keep #130 File → Import")
    if not _VIEW_SUBMENU.search(menu_all):
        fail("#307: keep #130 View submenu")
    for label in _VIEW_LABELS:
        if not re.search(rf"[\"']{label}[\"']", menu_all):
            fail(f"#307: keep #130 View → {label}")
    if _CHECK_UPDATES_ITEM.search(menu_all + handlers):
        fail("#307: keep #130 — no Check for Updates")
    if _PREFERENCES_ITEM.search(menu_all):
        fail("#307: keep #130 — no Preferences / Settings menu item")
    if _ICLOUD_MENU_ITEM.search(menu_all):
        fail("#307: keep #130 — no iCloud menu item")

    # 9) cap exists — not frozen as the integer 5 in a 5-row fixture.
    if not _CAP.search(store + persist + session):
        fail("#307: recents list must have a cap (truncate / MAX; not a 5-row fixture table)")

    # 10) CLI does not write recents.
    if _RECENTS_WRITE.search(cli) or _RECENTS_WRITE.search(
        _rust_fn_body(session, "init_owner_archive")
    ):
        fail(
            "#307: CLI open / init must not write recents "
            "(app open / init only; CLI still write_last_path)"
        )

    # 11) menu-rebuild after successful open/init; empty list omits Recent.
    opened = persist + "\n" + open_b + "\n" + init_b
    if not _SET_MENU.search(opened) and not re.search(
        r"\b(?:rebuild_\w*menu|native_menu)\s*\(", opened
    ):
        fail(
            "#307: rebuild File → Recent after a successful app open / init "
            "(in-session: Open ArchiveA then ArchiveB then Recent shows both)"
        )
    if not _EMPTY_OMIT.search(menu) or not _RECENT_SURFACE.search(menu):
        fail("#307: omit the Recent submenu when the list is empty (rebuild after a drop)")

    # 12) label-order — basename, MRU, dedup. Current may appear; no checkmark.
    if not _BASENAME.search(store + persist + menu):
        fail(
            "#307: Recent labels are the folder basename "
            "(placeholders ArchiveA / ArchiveB / Ada)"
        )
    if not _MRU.search(store + persist):
        fail("#307: recents are most-recent first (Open ArchiveA then ArchiveB → B then A)")
    if not _DEDUP.search(store + persist):
        fail("#307: dedup the same folder in recents (newer wins)")
    if _CHECKMARK.search(menu):
        fail("#307: the current archive may appear in Recent; do not add a checkmark")

    # 13) recent-d24 — user-facing Recent sentence.
    if not dtxt.strip():
        fail(
            "#307: docs/user/app.md required — File lists recent archives; "
            "a missing folder does not crash"
        )
    if not _DOCS_RECENT.search(dtxt):
        fail("#307: docs/user/app.md must say File lists recent archives")
    if not _DOCS_MISSING.search(dtxt):
        fail("#307: docs/user/app.md must say a missing folder does not crash")

    # 14) recent-placeholders — no real archive folder names in tests.
    for path in _placeholder_files(root):
        if path.is_file() and _REAL_HOME.search(path.read_text()):
            fail(
                "#307: do not dump real archive folder names into tests "
                "(placeholders ArchiveA / ArchiveB / Ada only)"
            )
