"""#308 — File → Switch archive (close-to-setup).

Approach A: File → Switch archive drops the exclusive flock, clears
People / timeline / Review, returns to SetupScreen. Then Open / Create
as today. File → Open archive stays picker-first (#130). Refuse while
importing. Leave last-archive until B succeeds. Clear lastView /
lastPersonId. Hide or disable Switch on setup. Placeholders ArchiveA /
ArchiveB / Ada.

Must-IDs: switch-file-menu, switch-returns-setup, switch-clears-session,
switch-flock-released, switch-then-open-b, switch-keep-130,
switch-keep-307, switch-no-two, switch-no-import-old, switch-d24,
switch-placeholders, switch-enabled-after-open.
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
from tauri_gate.recent_archives import (
    _RECENT_SURFACE,
    _VIEW_LABELS,
    _file_submenu,
    _named_bodies,
    _read,
)
from tauri_gate.scan import (
    _function_body,
    _rust_fn_body,
    _tauri_rust_blob,
    _ts_fn_body,
    _web_logic,
    _without_comments,
)

_SWITCH_LABEL = re.compile(r"[\"']Switch archive[\"']")
_SWITCH_ID = re.compile(
    r"[\"'](?:switch-archive|close-archive|menu-switch-archive|menu-close-archive)[\"']"
)
_SWITCH_EVENT = re.compile(
    r"[\"'](?:menu-switch-archive|menu-close-archive|menu-switch|switch-archive)[\"']"
)
_OPEN_ARCHIVE_EVT = re.compile(r"[\"']menu-open-archive[\"']")
_SETUP_TRUE = re.compile(r"\bsetSetup\s*\(\s*true\s*\)|\bsetup\s*=\s*true\b")
_ARCHIVE_NONE = re.compile(r"archive\s*=\s*None|\.archive[^=]{0,80}=\s*None")
_ROOT_NONE = re.compile(r"archive_root[^=]{0,80}=\s*None")
_EXCLUSIVE = re.compile(r"\bLockMode\s*::\s*Exclusive\b|\bopen_archive\s*\(")
_WRITE_LAST = re.compile(r"\bwrite_last_path\s*\(|\bwrite_last_bookmark\s*\(")
_PERSIST = re.compile(r"\bpersist_bookmark\s*\(|\brecord_recent\s*\(")
_LAST_BM = re.compile(r"last-archive\.bookmark|\blast_archive_path\b")
_IMPORT_RUN = re.compile(r"\bimport\b.{0,120}running|running.{0,80}\bimport\b", re.S)
_IMPORT_CANCEL = re.compile(r"\bimport_cancel\s*\(|\bimportCancel\b|\.cancel\s*\(")
_IMPORT_START = re.compile(r"\bimport_start\s*\(|\bimportStart\b")
_LAST_VIEW = re.compile(r"interlace\.lastView|\bLAST_VIEW_PREF\b")
_LAST_PERSON = re.compile(r"interlace\.lastPersonId|\bLAST_PERSON_PREF\b")
_REMOVE_PREF = re.compile(r"\bremoveItem\s*\(|\bclearLast\w*\s*\(")
_PICK = re.compile(r"\bopenPicker\s*\(|\bpick_folder\s*\(|\bpickFolder\s*\(")
_PEOPLE_CLEAR = re.compile(r"\bpeople\s*=\s*\[\s*\]")
_SEL_CLEAR = re.compile(r"\bselectedId\s*=\s*null\b")
_TL_CLEAR = re.compile(r"\bevents\s*=\s*\[\s*\]|\btimeline\s*=\s*\[\s*\]")
_ST_CLEAR = re.compile(r"\bst\s*=\s*null\b")
_DOCTOR_CLEAR = re.compile(r"\bdoctor\s*=\s*\[\s*\]")
_TWO_ARCH = re.compile(
    r"\bsecond_archive\b|\barchive_alt\b|\barchives\s*:\s*(?:Vec|HashMap|BTreeMap)"
)
_OPTION_ARCH = re.compile(r"archive\s*:\s*Arc\s*<\s*Mutex\s*<\s*Option\s*<\s*Archive")
_REBUILD = re.compile(r"\brebuild_menu\s*\(|\bset_menu\s*\(|\bnative_menu\s*\(")
_CREATE = re.compile(r"\bcreateArchive\b|[\"']createArchive[\"']")
_OPEN_EXISTING = re.compile(r"\bopenExisting\b|onOpenExisting")
_PEOPLE_LOAD = re.compile(r"\b(?:applyStatus|refreshPeople|api\.open)\b")
_API_CLOSE = re.compile(
    r"""invoke\s*(?:<[^>]*>)?\s*\(\s*[\"'](?:close|close_archive|switch_archive)[\"']"""
)
_HANDLER_CLOSE = re.compile(
    r"\b(?:close_archive|switch_archive|close_session)\b|\n\s*close\s*[,\]\n]"
)
_REAL_HOME = re.compile(
    r"/Users/[A-Za-z]|/home/[A-Za-z]|Documents/Interlace|Desktop/Interlace"
)
_DOCS_SWITCH = re.compile(r"File\s*(?:→|->)\s*Switch archive|Switch archive", re.I)
_DOCS_NO_QUIT = re.compile(r"without quitting|without quit", re.I)
_DOCS_FLOCK = re.compile(
    r"(?:flock.{0,100}(?:drop|release)|(?:drop|release).{0,100}flock)"
    r".{0,160}CLI"
    r"|CLI.{0,100}write.{0,80}(?:after|switch|flock)"
    r"|switch.{0,80}(?:flock|CLI)",
    re.I | re.S,
)
_CLOSE_RS = (
    "close",
    "close_archive",
    "switch_archive",
    "drop_archive",
    "release_archive",
    "close_session",
)
_CLOSE_JS = (
    "closeArchive",
    "switchArchive",
    "onSwitchArchive",
    "closeSession",
    "resetSession",
    "returnToSetup",
    "switchToSetup",
)
_MENU_FNS = ("native_menu", "rebuild_menu", "rebuild_file_menu", "file_menu")
_OPEN_OTHER = re.compile(r"Open other archive")
_HOLD_CALL = re.compile(r"\bhold\s*\(")
_PERSIST_OR_REBUILD = re.compile(r"\b(?:persist_bookmark|rebuild_menu)\s*\(")


def _around(src: str, rx: re.Pattern[str], before: int = 220, after: int = 280) -> str:
    return "\n".join(
        src[max(0, m.start() - before) : m.end() + after] for m in rx.finditer(src)
    )


def _js_body(src: str, name: str) -> str:
    return _ts_fn_body(src, name) or _function_body(src, name)


def _switch_rust(rust: str) -> str:
    return "\n".join(
        [
            _named_bodies(rust, _CLOSE_RS),
            _around(rust, _SWITCH_ID),
            _around(rust, _SWITCH_LABEL),
        ]
    )


def _switch_web(web: str, handlers: str) -> str:
    chunks = [handlers, _around(web, _SWITCH_EVENT), _around(web, _SWITCH_ID)]
    chunks.extend(_js_body(web, n) for n in _CLOSE_JS)
    return "\n".join(chunks)


def _switch_gated(file_menu: str, rust: str) -> bool:
    blob = _around(file_menu or rust, _SWITCH_LABEL)
    if re.search(
        r"\bif\b.{0,160}(?:archive|is_some|is_none|setup|open)", blob, re.I | re.S
    ):
        return True
    if re.search(r"[\"']Switch archive[\"']\s*,\s*(?!true\b)\w+", blob):
        return True
    if re.search(r"\.enabled\s*\(\s*(?!true\b)", blob) or re.search(
        r"\bset_enabled\s*\(", blob
    ):
        return True
    return False


def _refuses_import(close: str, file_menu: str) -> bool:
    if _IMPORT_RUN.search(close):
        return True
    if _SWITCH_LABEL.search(file_menu) and re.search(r"\brunning\b", file_menu):
        return True
    return False


def _hold_before_rebuild(body: str) -> bool:
    """True when hold( precedes persist_bookmark( / rebuild_menu(."""
    hold = _HOLD_CALL.search(body)
    rebuild = _PERSIST_OR_REBUILD.search(body)
    if hold is None or rebuild is None:
        return False
    return hold.start() < rebuild.start()


def _placeholder_files(root: Path) -> list[Path]:
    out = [
        root / "pipeline" / "state" / "308-test-author.md",
        root / "docs" / "user" / "app.md",
    ]
    tests = root / "crates" / "interlace-core" / "tests"
    if tests.is_dir():
        for p in tests.glob("*.rs"):
            text = p.read_text()
            if re.search(r"switch.archive|Switch archive", text, re.I):
                out.append(p)
    return out


def assert_switch_archive(crate: Path) -> None:
    """#308: File → Switch archive closes to setup (approach A + fills).

    Fold: open / init hold the Archive before persist_bookmark / rebuild_menu.
    """
    root = repo_root()
    rust = _without_comments(_tauri_rust_blob(crate))
    web = _without_comments(_web_logic(crate))
    menu_rs = _without_comments(_read(crate / "src" / "menu.rs"))
    main_rs = _without_comments(_read(crate / "src" / "main.rs"))
    ipc_rs = _without_comments(_read(crate / "src" / "ipc.rs"))
    api_ts = _without_comments(_read(crate / "web" / "lib" / "api.ts"))
    setup = _without_comments(_read(crate / "web" / "lib" / "SetupScreen.svelte"))
    dtxt = _read(root / "docs" / "user" / "app.md")
    menu = _named_bodies(rust, _MENU_FNS) or menu_rs
    file_menu = _file_submenu(menu_rs) or _file_submenu(rust)
    handlers = _menu_handler_surface(rust, web)
    close = _switch_rust(rust)
    sw_web = _switch_web(web, handlers)
    menu_all = menu_rs + rust
    open_fn = _rust_fn_body(rust, "open")
    init_fn = _rust_fn_body(rust, "init")
    apply = _js_body(web, "applyStatus")
    picker = _js_body(web, "openPicker")

    # 1) switch-file-menu — File lists Switch archive (not Open other…).
    if not (
        _SWITCH_LABEL.search(file_menu)
        or _SWITCH_LABEL.search(menu)
        or _SWITCH_LABEL.search(menu_rs)
    ):
        fail(
            "#308: File menu must list Switch archive "
            "(close-to-setup; distinct from Open archive)"
        )
    if _OPEN_OTHER.search(file_menu) and not _SWITCH_LABEL.search(file_menu):
        fail(
            "#308: File label must be Switch archive "
            "(sidebar Open other archive… stays picker-first)"
        )
    if not _SWITCH_ID.search(menu + menu_rs + rust):
        fail(
            "#308: File → Switch archive must have a menu id "
            "(switch-archive / close-archive; not open-archive)"
        )
    if not _switch_gated(file_menu, rust):
        fail(
            "#308: hide or disable Switch archive when no archive is open "
            "(already on setup)"
        )

    # 2) switch-returns-setup — listen → setSetup(true); SetupScreen stays.
    if not _SWITCH_EVENT.search(web) and not _SWITCH_ID.search(handlers):
        fail(
            "#308: Switch archive must be wired "
            "(on_menu_event emit + listen; not File → Open archive)"
        )
    if _OPEN_ARCHIVE_EVT.search(close) or (
        _OPEN_ARCHIVE_EVT.search(sw_web) and not _SETUP_TRUE.search(sw_web)
    ):
        fail(
            "#308: Switch archive must close to setup "
            "(do not emit menu-open-archive / open the picker)"
        )
    if not _SETUP_TRUE.search(sw_web):
        fail(
            "#308: Switch archive must return to SetupScreen "
            "(setSetup(true) / setup = true after close; Create + Open existing)"
        )
    if not _CREATE.search(setup) or not _OPEN_EXISTING.search(setup):
        fail(
            "#308: after Switch, SetupScreen must still offer Create + Open existing "
            "(placeholders ArchiveA / ArchiveB / Ada)"
        )

    # 3) switch-clears-session — People / timeline / Review / last prefs.
    if not _PEOPLE_CLEAR.search(sw_web):
        fail(
            "#308: Switch must clear People "
            "(people = []; do not leave ArchiveA’s list on setup)"
        )
    if not _SEL_CLEAR.search(sw_web):
        fail("#308: Switch must clear the selected person (selectedId = null)")
    if not _TL_CLEAR.search(sw_web):
        fail("#308: Switch must clear the timeline (events / timeline = [])")
    if not _ST_CLEAR.search(sw_web) and not _DOCTOR_CLEAR.search(sw_web):
        fail(
            "#308: Switch must unmount Review / timeline chrome "
            "(st = null and/or doctor = []; SetupScreen is the only pane)"
        )
    if not (_LAST_VIEW.search(sw_web) and _LAST_PERSON.search(sw_web)):
        fail(
            "#308: Switch must clear interlace.lastView / interlace.lastPersonId "
            "(Open ArchiveB must not inherit Review or ArchiveA’s person id)"
        )
    if not _REMOVE_PREF.search(sw_web):
        fail(
            "#308: Switch must removeItem interlace.lastView / "
            "interlace.lastPersonId (or clearLast*)"
        )

    # 4) switch-flock-released — drop A without opening B; leave last-archive.
    if not _ARCHIVE_NONE.search(close) and not _ARCHIVE_NONE.search(ipc_rs):
        fail(
            "#308: Switch must drop the exclusive flock "
            "(state.archive = None without opening ArchiveB; CLI can write ArchiveA)"
        )
    if _EXCLUSIVE.search(close):
        fail(
            "#308: Switch must not Exclusive-open another path "
            "(drop ArchiveA, then Open / Create as today)"
        )
    if not _ROOT_NONE.search(close) and not _ROOT_NONE.search(
        _named_bodies(rust, _CLOSE_RS)
    ):
        fail("#308: Switch must clear archive_root (do not leave cas:// on ArchiveA)")
    if _WRITE_LAST.search(close) or _PERSIST.search(close) or _LAST_BM.search(close):
        fail(
            "#308: leave last-archive.bookmark / last_archive_path / recents on "
            "ArchiveA until ArchiveB succeeds (Switch does not rewrite them)"
        )
    if not _REBUILD.search(close) and not _REBUILD.search(_around(rust, _SWITCH_ID)):
        fail(
            "#308: rebuild the File menu after Switch "
            "(hide or disable Switch on setup)"
        )
    if not _API_CLOSE.search(api_ts) and not _HANDLER_CLOSE.search(main_rs):
        fail(
            "#308: expose a close / close_archive IPC "
            "(or drop archive on the Switch menu arm) so flock is gone before B"
        )

    # 5) switch-then-open-b — then today’s Open; Ada on B; no flock on A.
    if _PICK.search(close) or _PICK.search(_around(sw_web, _SWITCH_EVENT)):
        fail(
            "#308: Switch is setup-first "
            "(do not open the folder picker; Cancel-leaves-A is File → Open archive)"
        )
    if not _PEOPLE_LOAD.search(apply) and "refreshPeople" not in apply:
        fail(
            "#308: after Switch, Open ArchiveB must load B’s people "
            "(applyStatus / refreshPeople; Ada on ArchiveB only)"
        )
    if not open_fn.strip() or not re.search(r"\bLockMode\s*::\s*Exclusive\b", open_fn):
        fail(
            "#308: Open ArchiveB after Switch uses existing open "
            "(Exclusive flock on B; no flock on ArchiveA)"
        )

    # 6) switch-keep-130 — Open archive + Import + View; picker Cancel leaves A.
    if not _FILE_SUBMENU.search(menu_all):
        fail("#308: keep #130 File submenu (Open archive + Import)")
    if not _OPEN_ITEM.search(menu_all):
        fail("#308: keep #130 File → Open archive")
    if not _IMPORT_ITEM.search(menu_all):
        fail("#308: keep #130 File → Import")
    if not _VIEW_SUBMENU.search(menu_all):
        fail("#308: keep #130 View submenu")
    for label in _VIEW_LABELS:
        if not re.search(rf"[\"']{label}[\"']", menu_all):
            fail(f"#308: keep #130 View → {label}")
    if _CHECK_UPDATES_ITEM.search(menu_all + handlers):
        fail("#308: keep #130 — no Check for Updates")
    if _PREFERENCES_ITEM.search(menu_all):
        fail("#308: keep #130 — no Preferences / Settings menu item")
    if _ICLOUD_MENU_ITEM.search(menu_all):
        fail("#308: keep #130 — no iCloud menu item")
    if not picker.strip() or not re.search(
        r"if\s*\(\s*!\s*folder\s*\)\s*return", picker
    ):
        fail(
            "#308: File → Open archive picker Cancel while ArchiveA is open "
            "must still leave ArchiveA (#130)"
        )
    if _SETUP_TRUE.search(picker):
        fail(
            "#308: File → Open archive must stay picker-first "
            "(Cancel does not close to setup; that is Switch)"
        )

    # 7) switch-keep-307 — Recent surface stays.
    if not (_RECENT_SURFACE.search(file_menu) or _RECENT_SURFACE.search(menu)):
        fail(
            "#308: keep #307 File → Recent archives "
            "(sibling list; rebuild after open; no URLs)"
        )

    # 8) switch-no-two — one live Archive; import worker must not hold A.
    if not _OPTION_ARCH.search(main_rs):
        fail(
            "#308: AppState must stay one Option<Archive> "
            "(do not open ArchiveA and ArchiveB at once)"
        )
    if _TWO_ARCH.search(main_rs):
        fail("#308: do not add a second Archive slot (no two archives)")

    # 9) switch-no-import-old — refuse while importing (no-op / disabled).
    if not _refuses_import(close, file_menu):
        fail(
            "#308: refuse Switch while import is running "
            "(no-op / disabled; Finish or Cancel first)"
        )
    if _IMPORT_CANCEL.search(close) or _IMPORT_CANCEL.search(
        _around(sw_web, _SWITCH_EVENT)
    ):
        fail(
            "#308: refuse Switch while import is running "
            "(do not cancel-then-switch; Finish or Cancel first)"
        )
    if _IMPORT_START.search(close) or _IMPORT_START.search(sw_web):
        fail(
            "#308: do not start a background import on ArchiveA after Switch "
            "(no two archives; no import on the old path)"
        )

    # 10) switch-d24
    if not dtxt.strip():
        fail(
            "#308: docs/user/app.md required — File can switch without quitting; "
            "flock drops so CLI can write ArchiveA"
        )
    if not _DOCS_SWITCH.search(dtxt):
        fail("#308: docs/user/app.md must say File → Switch archive")
    if not _DOCS_NO_QUIT.search(dtxt):
        fail("#308: docs/user/app.md must say you can switch without quitting")
    if not _DOCS_FLOCK.search(dtxt):
        fail(
            "#308: docs/user/app.md must say Switch drops the exclusive flock "
            "so CLI can write ArchiveA"
        )

    # 11) switch-placeholders
    for path in _placeholder_files(root):
        if path.is_file() and _REAL_HOME.search(path.read_text()):
            fail(
                "#308: do not dump real archive folder names into tests "
                "(placeholders ArchiveA / ArchiveB / Ada only)"
            )

    # 12) switch-enabled-after-open — hold first so File rebuilds with archive Some.
    for name, body in (("open", open_fn), ("init", init_fn)):
        if not _hold_before_rebuild(body):
            fail(
                f"#308: {name} must hold( the Archive before persist_bookmark( / "
                "rebuild_menu( so File rebuilds Switch enabled when state.archive is Some"
            )
