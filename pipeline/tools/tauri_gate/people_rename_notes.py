"""#367 — inspector rename + notes (confirmed mix).

Wired immediately after assert_people_avatar (#213 / #366 family).

Confirmed mix: person_rename + person_set_notes as live UPDATE persons via
existing exclusive flock (with_arch_mut). Not merge. Not identity rewrite.
Notes ride person_show only (not PersonSummary.notes). Empty / whitespace
name refused, no write. Same name no-op. Empty notes allowed (clear). Self
same rule. I2: colliding name does not enqueue review.

Chrome: keep collapse {personTitle} + #366 avatar. Under last-activity:
owned Input + Confirm (inline, not a modal). Notes + explicit Save (not
blur-only). After write: refreshPeople + personShow so six surfaces follow
the new display_name. Window title stays personTitle — Interlace.

#213 / #366 / #129 / #138 stay as their own asserts. Do not delete them.
Placeholders only (Ada / Berk). Plant Ada K. and notes work.
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

_ISSUE = "#367"

_OWNED_INPUT = re.compile(
    r"""import\s+\{[^}]*\bInput\b[^}]*\}\s+from\s+["']\$lib/components/ui/input"""
)
_HEADER_TITLE = re.compile(r"\{personTitle\}")
_AVATAR = re.compile(r"<PersonAvatar\b")
_COLLAPSE_ASSIGN = re.compile(
    r"showPersonChrome\s*=\s*!?\s*showPersonChrome|showPersonChrome\s*=\s*false"
)
_RENAME_CONFIRM = re.compile(
    r""">Confirm<
    |>\{t\(\s*["'](?:confirm|renameConfirm|renameSave)["']\s*\)\}
    |t\(\s*["'](?:confirm|renameConfirm|renameSave)["']\s*\)
    |data-person-rename-confirm
    """,
    re.I | re.X,
)
_NOTES_SAVE = re.compile(
    r""">Save<
    |>\{t\(\s*["'](?:save|saveNotes|notesSave)["']\s*\)\}
    |t\(\s*["'](?:save|saveNotes|notesSave)["']\s*\)
    |data-person-notes-save
    """,
    re.I | re.X,
)
_NOTES_FIELD = re.compile(
    r"""
    \bnotes\b
    |\bpersonNotes\b
    |\bnotesDraft\b
    |\bsetNotes\b
    """,
    re.I | re.X,
)
_INPUT_TAG = re.compile(r"<Input\b")
_PERSON_RENAME = re.compile(r"\bperson_rename(?:_cmd)?\b|\bpersonRename\s*\(")
_PERSON_SET_NOTES = re.compile(r"\bperson_set_notes(?:_cmd)?\b|\bpersonSetNotes\s*\(")
_PERSON_SHOW_NOTES_TS = re.compile(
    r"""personShow[\s\S]{0,400}\bnotes\s*\??\s*:
    |\bnotes\s*\??\s*:\s*(?:string|Option)
    """,
    re.I,
)
_PERSON_SHOW_NOTES_RS = re.compile(
    r"""
    \bnotes\s*:
    |["']notes["']\s*:
    """,
    re.I | re.X,
)
_SUMMARY_NOTES = re.compile(r"\bnotes\s*:")
_MERGE_CALL = re.compile(r"\bapi\s*\.\s*merge\s*\(|\bperson_merge\s*\(")
_RESOLVE_ENQUEUE = re.compile(
    r"""
    \bresolve_run\s*\(
    |\benqueue_name
    |\benqueue_exact_name
    |\benqueue_
    """,
    re.I | re.X,
)
_OPEN_ARCHIVE = re.compile(r"\bopen_archive\s*\(")
_WITH_ARCH_MUT = re.compile(r"\bwith_arch_mut\s*\(")
_REFRESH = re.compile(r"\brefreshPeople\s*\(|\bonPeopleChanged\s*\(")
_PERSON_SHOW_REFRESH = re.compile(
    r"""
    \bpersonShow\s*\(
    |\bloadPerson\s*\(
    |\bpersonTitle\s*=
    """,
    re.X,
)
_WINDOW_TITLE = re.compile(
    r"""personTitle\s*\+\s*["']\s*—\s*Interlace["']"""
)
_EMPTY_NAME = re.compile(
    r"""
    \.trim\s*\(\s*\)
    .{0,240}
    (?:
        return
        |length\s*===?\s*0
        |!\s*\w+
    )
    """,
    re.S | re.X,
)
_BLUR_NOTES_WRITE = re.compile(
    r"""
    on:?blur\b
    .{0,240}
    (?:personSetNotes|person_set_notes|setNotes)
    |
    (?:personSetNotes|person_set_notes)
    .{0,120}
    on:?blur\b
    """,
    re.I | re.S | re.X,
)
_DOCS_RENAME = re.compile(
    r"""
    rename.{0,120}(?:not.{0,40}merge|notes)
    |(?:inspector|person).{0,80}rename
    """,
    re.I | re.S | re.X,
)
_DOCS_NOTES = re.compile(
    r"""
    notes.{0,80}(?:SQLite|archive|persist|save)
    |(?:SQLite|archive).{0,80}notes
    """,
    re.I | re.S | re.X,
)
_DOCS_NOT_MERGE = re.compile(
    r"""
    rename.{0,60}not.{0,20}merge
    |not.{0,20}(?:a\s+)?merge.{0,40}rename
    """,
    re.I | re.S | re.X,
)
_HAYSTACK_NOTES = re.compile(
    r"""
    (?:hay|filter|keywords).{0,80}\.notes
    |\.notes.{0,80}(?:hay|filter|keywords|toLowerCase)
    |p\.notes
    """,
    re.I | re.X,
)
_SEARCH_RELABEL = re.compile(
    r"""
    \$effect\s*\([\s\S]{0,500}personId[\s\S]{0,400}personFilter
    |\$derived[\s\S]{0,400}personId[\s\S]{0,200}display_name
    |people\s*\.\s*find\s*\([\s\S]{0,120}personId
    """,
    re.X,
)
_T_KEY = re.compile(r"""\bt\(\s*["']([A-Za-z][A-Za-z0-9_]*)["']""")
_CHROME_KEY_HINT = re.compile(r"rename|notes|save|confirm", re.I)
_BLIND = frozenset({"identity.rs", "search.rs"})
_BLIND_DIRS = frozenset({"import"})


def _text(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


def _web_file(crate: Path, name: str) -> Path:
    return crate / "web" / "lib" / name


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


def _fn_bodies(src: str, names: tuple[str, ...]) -> str:
    parts: list[str] = []
    for name in names:
        for m in re.finditer(rf"(?:async\s+)?fn\s+{re.escape(name)}\b", src):
            start = src.find("{", m.start())
            if start < 0:
                continue
            end = _match_closer(src, start)
            parts.append(src[m.start() : end + 1] if end >= 0 else src[m.start() : m.start() + 800])
    return "\n".join(parts)


def _ts_fn_windows(src: str, names: tuple[str, ...]) -> str:
    parts: list[str] = []
    for name in names:
        for m in re.finditer(
            rf"(?:async\s+)?function\s+{re.escape(name)}\b|const\s+{re.escape(name)}\s*=",
            src,
        ):
            parts.append(src[m.start() : m.start() + 900])
    return "\n".join(parts)


def _last_activity_region(mark: str) -> str:
    m = re.search(r"lastActivity|last_activity_at", mark)
    if not m:
        return ""
    rest = mark[m.start() :]
    end = re.search(r"Merge…|Merge\.\.\.|>Merge<|>\{t\(\s*[\"']identities[\"']", rest)
    return rest[: end.start()] if end else rest[:2500]


def _collapse_header(mark: str) -> str:
    title = _HEADER_TITLE.search(mark)
    if not title:
        return ""
    return mark[max(0, title.start() - 500) : title.end() + 280]


def _core_people_blob(root: Path) -> str:
    parts: list[str] = []
    base = root / "crates" / "interlace-core" / "src"
    people = base / "people.rs"
    if people.is_file():
        parts.append(people.read_text())
    people_dir = base / "people"
    if people_dir.is_dir():
        for p in sorted(people_dir.glob("*.rs")):
            if p.name in _BLIND:
                continue
            parts.append(p.read_text())
    return "\n".join(parts)


def _lib_people_use(lib: str) -> str:
    m = re.search(r"pub use people::\{", lib)
    if not m:
        return ""
    start = lib.find("{", m.start())
    if start < 0:
        return ""
    end = _match_closer(lib, start)
    return lib[m.start() : end + 1] if end >= 0 else lib[m.start() : m.start() + 400]


def _locale_keys(src: str) -> set[str]:
    return set(re.findall(r"(?m)^\s+([A-Za-z][A-Za-z0-9_]*)\s*:", src))


def _locale_value(src: str, key: str) -> str:
    m = re.search(rf'(?m)^\s+{re.escape(key)}\s*:\s*("(?:\\.|[^"\\])*")', src)
    return m.group(1) if m else ""


def assert_people_rename_notes(crate: Path) -> None:
    """#367: inspector rename + notes (mix: two writers, person_show, Save)."""
    root = repo_root()
    inspector_path = _web_file(crate, "PeopleInspector.svelte")
    if not inspector_path.is_file():
        fail(f"{_ISSUE}: PeopleInspector.svelte required (rename + notes live in the inspector)")

    inspector = _text(inspector_path)
    inspector_clean = _without_comments(inspector)
    inspector_mark = _svelte_markup(inspector)
    header = _collapse_header(inspector_mark)
    region = _last_activity_region(inspector_mark)

    # 1) Keep collapse {personTitle} + #366 avatar (header is not the editor).
    if not _HEADER_TITLE.search(inspector_mark):
        fail(f"{_ISSUE}: inspector header must still interpolate {{personTitle}}")
    if not _COLLAPSE_ASSIGN.search(inspector_clean) and not _COLLAPSE_ASSIGN.search(inspector):
        fail(
            f"{_ISSUE}: inspector header must stay a collapse control "
            "(toggle showPersonChrome — do not replace it with the rename Input)"
        )
    if _INPUT_TAG.search(header):
        fail(
            f"{_ISSUE}: collapse header must stay a button — "
            "rename Input sits under last-activity, not on the title"
        )
    if not _AVATAR.search(header) and not _AVATAR.search(inspector_mark):
        fail(f"{_ISSUE}: keep PersonAvatar beside {{personTitle}} (#366)")

    # 2) Primary red today: inline Input + Confirm under last-activity.
    if not _OWNED_INPUT.search(inspector) and not _OWNED_INPUT.search(inspector_clean):
        fail(
            f"{_ISSUE}: inspector must have an owned rename Input + Confirm "
            "under last-activity (not on the collapse header)"
        )
    if not region.strip():
        fail(
            f"{_ISSUE}: inspector must have an owned rename Input + Confirm "
            "under last-activity (not on the collapse header)"
        )
    if not _INPUT_TAG.search(region):
        fail(
            f"{_ISSUE}: inspector must have an owned rename Input + Confirm "
            "under last-activity (not on the collapse header)"
        )
    if not _RENAME_CONFIRM.search(region) and not _RENAME_CONFIRM.search(inspector_mark):
        fail(
            f"{_ISSUE}: rename confirm is an inline Confirm next to the Input "
            "(not a modal-only path, not blur)"
        )

    # 3) Notes field + explicit Save (not blur-only).
    if not _NOTES_FIELD.search(inspector_clean) and not _NOTES_FIELD.search(inspector_mark):
        fail(f"{_ISSUE}: inspector must have a notes field (one TEXT, person_show)")
    if not _NOTES_SAVE.search(inspector_mark) and not _NOTES_SAVE.search(inspector_clean):
        fail(f"{_ISSUE}: notes need an explicit Save (not blur-only)")
    if _BLUR_NOTES_WRITE.search(inspector_clean) and not _NOTES_SAVE.search(inspector_mark):
        fail(f"{_ISSUE}: notes persist via Save — blur-only is not the only path")

    # 4) Empty / whitespace name stays on the confirm and does not write.
    rename_src = (
        inspector_clean
        + "\n"
        + _ts_fn_windows(
            inspector_clean,
            ("rename", "confirmRename", "onRename", "saveRename", "commitRename"),
        )
    )
    if not _EMPTY_NAME.search(rename_src) and not _EMPTY_NAME.search(inspector_clean):
        fail(
            f"{_ISSUE}: empty / whitespace name must stay on the confirm and not write"
        )
    if re.search(r"personRename\s*\(|person_rename", inspector_clean):
        window = inspector_clean
        if not re.search(
            r"""\.trim\s*\(\s*\).{0,400}(?:personRename|person_rename)|"""
            r"""(?:if\s*\([^)]*trim[^)]*\)[\s\S]{0,200}return)[\s\S]{0,400}(?:personRename|person_rename)""",
            window,
            re.S,
        ):
            fail(
                f"{_ISSUE}: empty / whitespace name must not invoke person_rename"
            )

    # 5) Published core writers + person_show (notes).
    lib = _text(root / "crates" / "interlace-core" / "src" / "lib.rs")
    people_use = _lib_people_use(lib)
    if not re.search(r"\bperson_rename\b", people_use) and not re.search(
        r"\bperson_rename\b", lib
    ):
        fail(f"{_ISSUE}: person_rename must be published from lib.rs")
    if not re.search(r"\bperson_set_notes\b", people_use) and not re.search(
        r"\bperson_set_notes\b", lib
    ):
        fail(f"{_ISSUE}: person_set_notes must be published from lib.rs")
    if not re.search(r"\bperson_show\b", people_use) and not re.search(
        r"pub use people::\{[^}]*\bperson_show\b", lib
    ):
        fail(
            f"{_ISSUE}: person_show must be a published core helper "
            "(notes ride person_show, not PersonSummary)"
        )

    people_rs = _text(root / "crates" / "interlace-core" / "src" / "people.rs")
    summary = _rust_struct_body(people_rs, "PersonSummary")
    if _SUMMARY_NOTES.search(summary):
        fail(
            f"{_ISSUE}: do not add PersonSummary.notes "
            "(notes ride person_show only; list stays thin)"
        )

    api_ts = _text(_web_file(crate, "api.ts"))
    person_type = _rust_struct_body(api_ts.replace("export type", "struct"), "Person")
    if not person_type:
        pm = re.search(r"export type Person\s*=\s*\{", api_ts)
        if pm:
            start = api_ts.find("{", pm.start())
            end = _match_closer(api_ts, start)
            person_type = api_ts[start : end + 1] if end >= 0 else ""
    if _SUMMARY_NOTES.search(person_type):
        fail(
            f"{_ISSUE}: api.ts Person must not grow notes "
            "(list payload stays thin; notes are person_show)"
        )
    if not re.search(r"\bnotes\s*\??\s*:", api_ts) or not re.search(
        r"personShow[\s\S]{0,500}\bnotes\b", api_ts
    ):
        fail(f"{_ISSUE}: person_show / personShow must carry notes")

    # 6) Tauri IPC uses with_arch_mut on the flock this app already holds.
    people_cmd = _text(crate / "src" / "people_cmd.rs")
    main_rs = _text(crate / "src" / "main.rs")
    ipc_rs = _text(crate / "src" / "ipc.rs")
    tauri_blob = "\n".join((people_cmd, main_rs, ipc_rs, api_ts))
    if not _PERSON_RENAME.search(tauri_blob):
        fail(f"{_ISSUE}: person_rename IPC missing (people_cmd + generate_handler + api.ts)")
    if not _PERSON_SET_NOTES.search(tauri_blob):
        fail(
            f"{_ISSUE}: person_set_notes IPC missing (people_cmd + generate_handler + api.ts)"
        )
    if not re.search(r"\bperson_rename(?:_cmd)?\b", main_rs):
        fail(f"{_ISSUE}: generate_handler must register person_rename / person_rename_cmd")
    if not re.search(r"\bperson_set_notes(?:_cmd)?\b", main_rs):
        fail(
            f"{_ISSUE}: generate_handler must register person_set_notes / person_set_notes_cmd"
        )
    writer_fns = _fn_bodies(
        people_cmd + "\n" + ipc_rs + "\n" + main_rs,
        (
            "person_rename",
            "person_rename_cmd",
            "person_set_notes",
            "person_set_notes_cmd",
        ),
    )
    if not writer_fns.strip():
        fail(f"{_ISSUE}: person_rename / person_set_notes commands must exist")
    if not _WITH_ARCH_MUT.search(writer_fns):
        fail(
            f"{_ISSUE}: writers must use with_arch_mut "
            "(existing exclusive flock — no second open_archive)"
        )
    if _OPEN_ARCHIVE.search(writer_fns):
        fail(f"{_ISSUE}: writers must not open_archive / take a second flock")

    people_cmd_show = _fn_bodies(people_cmd + "\n" + ipc_rs, ("person_show",))
    if people_cmd_show and not _PERSON_SHOW_NOTES_RS.search(people_cmd_show):
        fail(f"{_ISSUE}: person_show IPC JSON must include notes")

    # 7) After write: refreshPeople + personShow so six surfaces + title update.
    shell = _text(_web_file(crate, "PeopleShell.svelte"))
    app = _text(crate / "web" / "App.svelte")
    timeline = _text(_web_file(crate, "TimelinePane.svelte"))
    write_chrome = "\n".join((inspector_clean, shell, app, timeline, api_ts))
    if not _REFRESH.search(write_chrome):
        fail(
            f"{_ISSUE}: after rename / notes write, refreshPeople "
            "so sidebar / palette / merge / Search see the new name"
        )
    rename_windows = (
        _ts_fn_windows(
            write_chrome,
            (
                "rename",
                "confirmRename",
                "onRename",
                "saveRename",
                "commitRename",
                "saveNotes",
                "onSaveNotes",
            ),
        )
        + write_chrome
    )
    if not _PERSON_SHOW_REFRESH.search(rename_windows):
        fail(
            f"{_ISSUE}: after rename, personShow / personTitle "
            "so the window title is Ada K. — Interlace"
        )
    if not _WINDOW_TITLE.search(app):
        fail(
            f"{_ISSUE}: window title must stay personTitle — Interlace "
            "(Ada K. after rename; not a raw id)"
        )

    # 8) Rename is not a merge. I2 does not enqueue.
    rename_call_src = inspector_clean + "\n" + shell + "\n" + api_ts
    if _PERSON_RENAME.search(rename_call_src) and _MERGE_CALL.search(
        _ts_fn_windows(
            rename_call_src,
            ("rename", "confirmRename", "onRename", "saveRename", "commitRename"),
        )
    ):
        fail(f"{_ISSUE}: rename path must not call person_merge / api.merge")
    core_blob = _core_people_blob(root)
    core_clean = _without_comments(core_blob)
    writer_core = _fn_bodies(
        core_clean,
        ("person_rename", "person_set_notes"),
    )
    if writer_core and _MERGE_CALL.search(writer_core):
        fail(f"{_ISSUE}: person_rename must not call person_merge")
    if writer_core and _RESOLVE_ENQUEUE.search(writer_core):
        fail(
            f"{_ISSUE}: I2 — colliding rename must not resolve_run / enqueue review"
        )

    # 9) Six surfaces still read list display_name / personTitle. Notes stay out.
    sidebar = _text(_web_file(crate, "PeopleSidebar.svelte"))
    palette = _text(_web_file(crate, "CommandPalette.svelte"))
    merge = _text(_web_file(crate, "MergeDialog.svelte"))
    search = _text(_web_file(crate, "SearchPane.svelte"))
    for name, src, needle in (
        ("PeopleSidebar.svelte", sidebar, r"\bdisplay_name\b"),
        ("CommandPalette.svelte", palette, r"\bdisplay_name\b"),
        ("MergeDialog.svelte", merge, r"\bdisplay_name\b"),
        ("SearchPane.svelte", search, r"\bdisplay_name\b"),
    ):
        if not re.search(needle, src):
            fail(
                f"{_ISSUE}: {name} must keep reading people[].display_name "
                "(refreshPeople is enough after rename)"
            )
    hay = "\n".join((sidebar, palette, search))
    if _HAYSTACK_NOTES.search(hay):
        fail(f"{_ISSUE}: notes must not enter the / or palette haystack (#138)")
    if not _SEARCH_RELABEL.search(search):
        fail(
            f"{_ISSUE}: Search picked caption must follow people[] after rename "
            "(re-derive personFilter from personId)"
        )

    # 10) i18n: new chrome keys in both packs; tr is not an English copy.
    en = _text(_web_file(crate, "locales/en.ts"))
    tr = _text(_web_file(crate, "locales/tr.ts"))
    t_keys = set(_T_KEY.findall(inspector))
    chrome_keys = {k for k in t_keys if _CHROME_KEY_HINT.search(k)}
    if not chrome_keys:
        fail(
            f"{_ISSUE}: rename / notes / save chrome must use t() keys "
            "present in both en.ts and tr.ts"
        )
    en_keys = _locale_keys(en)
    tr_keys = _locale_keys(tr)
    for key in sorted(chrome_keys):
        if key not in en_keys or key not in tr_keys:
            fail(
                f"{_ISSUE}: chrome key {key} must exist in both locales/en.ts and locales/tr.ts"
            )
        ev, tv = _locale_value(en, key), _locale_value(tr, key)
        if ev and tv and ev == tv and key not in {"media"}:
            fail(f"{_ISSUE}: tr.ts {key} must not be an English copy (#278)")

    # 11) D24 — inspector rename (not a merge) + notes persist in SQLite.
    docs = _text(root / "docs" / "user" / "app.md")
    if not _DOCS_RENAME.search(docs):
        fail(
            f"{_ISSUE}: docs/user/app.md must say the inspector can rename a person"
        )
    if not _DOCS_NOTES.search(docs):
        fail(
            f"{_ISSUE}: docs/user/app.md must say notes persist in the archive / SQLite"
        )
    if not _DOCS_NOT_MERGE.search(docs):
        fail(f"{_ISSUE}: docs/user/app.md must say rename is not a merge")

    # 12) Keep #213 / #366 / #129 / #138 (do not delete those asserts).
    if not re.search(r"\bdata-person-inspector\b", inspector_mark):
        fail(f"{_ISSUE}: keep data-person-inspector (#213)")
    if not _AVATAR.search(inspector_mark):
        fail(f"{_ISSUE}: keep PersonAvatar on the inspector (#366)")
    if not _WINDOW_TITLE.search(app):
        fail(f"{_ISSUE}: keep personTitle — Interlace (#129)")
    if not re.search(r"\bidentity_values\b", sidebar) and not re.search(
        r"\bidentity_values\b", _text(crate / "web" / "lib" / "PeopleShell.svelte")
    ):
        fail(f"{_ISSUE}: keep / filter on display_name + identity_values (#138)")
