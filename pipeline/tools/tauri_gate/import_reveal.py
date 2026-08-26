"""Reveal-archive / defer-doctor chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _ARBITRARY_SHELL,
    _FETCH_CALL,
    _LINKIFY_FETCH,
    _SCROLL_HELPER_SKIP,
    _expand_fn_calls,
    _function_body,
    _js_next,
    _rust_body_with_callees,
    _rust_call_arg,
    _rust_fn_signature,
    _rust_function_body,
    _svelte_markup,
    _tauri_rust_blob,
    _ts_fn_body,
    _ts_function_body,
    _web_logic,
    _without_comments,
)

from tauri_gate.import_boot import (
    _boot_opening_block,
    _element_block_at,
)

from tauri_gate.media_linkify import (
    _PLUGIN_SHELL,
    _SHELL_CAP,
    _hook_element_blocks,
)

from tauri_gate.status_toasts import (
    _claim_without_negation,
    _invoke_payloads,
    _payload_has_path_or_url,
    _windows_around,
)




# #274 — Reveal archive folder in Finder from Doctor / People.
_REVEAL_ARCHIVE_HOOK = re.compile(
    r"data-(?:reveal-archive|reveal-root|reveal-folder|"
    r"reveal-archive-root|archive-reveal)"
)
_REVEAL_ARCHIVE_HOOK_NAMES = (
    "data-reveal-archive",
    "data-reveal-root",
    "data-reveal-folder",
    "data-reveal-archive-root",
    "data-archive-reveal",
)
_REVEAL_ARCHIVE_LABEL = re.compile(
    r"("
    r">\s*Reveal(?:\s+in\s+Finder|\s+archive(?:\s+folder)?)?\s*<"
    r"|t\(\s*[\"']reveal(?:InFinder|Archive|Folder|Root|ArchiveFolder)[\"']\s*\)"
    r"|aria-label\s*=\s*[\"']Reveal(?: in Finder| archive(?: folder)?)?[\"']"
    r")"
)
_REVEAL_ARCHIVE_FN = re.compile(
    r"\b(?:"
    r"revealArchive|revealArchiveRoot|revealRoot|revealFolder|"
    r"revealOpenArchive|onRevealArchive|handleRevealArchive|"
    r"openArchiveInFinder|revealArchiveFolder"
    r")\b"
)
_REVEAL_ARCHIVE_COMPONENT = re.compile(
    r"<Reveal(?:Archive|Folder|Root|ArchiveRoot|ArchiveFolder)\b"
)
_REVEAL_ARCHIVE_CMD_SNAKE = (
    "reveal_archive",
    "reveal_archive_root",
    "reveal_root",
    "reveal_folder",
    "reveal_open_archive",
    "reveal_archive_folder",
)
_REVEAL_ARCHIVE_CAMEL = (
    "revealArchive",
    "revealArchiveRoot",
    "revealRoot",
    "revealFolder",
    "revealOpenArchive",
    "revealArchiveFolder",
)
_REVEAL_ARCHIVE_SKIP_EXTRA = frozenset(
    {
        "App.svelte",
        "DoctorPane.svelte",
        "CasAttach.svelte",
        "SearchPane.svelte",
        "CommandPalette.svelte",
        "ConfirmDialog.svelte",
        "ReviewPane.svelte",
        "ImportPane.svelte",
        "EmptyState.svelte",
        "api.ts",
    }
)
_REVEAL_ARCHIVE_HANDLER_SKIP = frozenset(
    {
        "t",
        "e",
        "event",
        "true",
        "false",
        "void",
        "undefined",
        "null",
        "console",
        "preventDefault",
        "stopPropagation",
        "Button",
        "ask",
    }
)
_REVEAL_ARCHIVE_DOC = re.compile(
    r"("
    r"Reveal(?: in Finder)?(?: the)? archive folder"
    r"|Reveal archive"
    r"|reveal the (?:open )?archive"
    r"|archive folder.{0,80}Finder"
    r"|Finder.{0,80}archive folder"
    r")",
    re.I | re.S,
)
_REVEAL_ARCHIVE_DOC_COPY = re.compile(
    r"("
    r"copy (?:that |the )folder"
    r"|folder is the backup unit"
    r"|copy.{0,80}after (?:you )?clos"
    r"|after (?:you )?clos(?:e|ing).{0,80}(?:app|window)"
    r")",
    re.I | re.S,
)
_REVEAL_ARCHIVE_ENCRYPT = re.compile(
    r"("
    r"database is encrypted"
    r"|your data is encrypted"
    r"|is encrypted at rest"
    r"|SQLCipher"
    r")",
    re.I,
)
_REVEAL_ARCHIVE_UPLOAD = re.compile(r"\bupload\b", re.I)
_REVEAL_ARCHIVE_ZIP_ICLOUD = re.compile(
    r"("
    r"zip[- ]to[- ]icloud"
    r"|icloud[- ](?:drive[- ])?backup"
    r"|backup[- _]zip"
    r"|zip[- _]backup"
    r")",
    re.I,
)
_REVEAL_ARCHIVE_SECOND_CAS = re.compile(
    r"("
    r"second (?:copy of )?CAS"
    r"|duplicate(?:d)? (?:the )?CAS"
    r"|backup_cas|copy_cas|cas_copy"
    r")",
    re.I,
)
_REVEAL_ARCHIVE_BACKUP_FN = re.compile(
    r"\bfn\s+(?:backup|backup_zip|zip_backup|icloud_backup|copy_cas|backup_cas)\b"
)


def _looks_like_reveal_archive(block: str) -> bool:
    if _REVEAL_ARCHIVE_HOOK.search(block):
        return True
    if _REVEAL_ARCHIVE_FN.search(block):
        return True
    if _REVEAL_ARCHIVE_COMPONENT.search(block):
        return True
    return bool(_REVEAL_ARCHIVE_LABEL.search(block))


def _doctor_backup_section(src: str) -> str:
    """Doctor Backup <section> (heading + copy + controls)."""
    markup = _svelte_markup(src)
    i = 0
    while True:
        m = re.search(r"<section\b", markup[i:], re.I)
        if not m:
            break
        start = i + m.start()
        block = _element_block_at(markup, start)
        if re.search(r">\s*Backup\s*<", block) or re.search(
            r"<h[1-6][^>]*>\s*Backup\s*</h[1-6]>", block, re.I
        ):
            return block
        i = start + max(len(block), 1)
    m = re.search(r"<h[1-6][^>]*>\s*Backup\s*</h[1-6]>", markup, re.I)
    if m:
        rest = markup[m.start() :]
        nxt = re.search(r"<h[1-6]\b|<section\b", rest[m.end() - m.start() :])
        if nxt:
            return rest[: m.end() - m.start() + nxt.start()]
        return rest[:2000]
    return _windows_around(markup, re.compile(r"\bBackup\b"), before=40, after=1600)


def _reveal_archive_extra(crate: Path, host: str) -> str:
    """Helpers Doctor / People actually mount. CasAttach Reveal-CAS does not count."""
    web = crate / "web"
    if not web.is_dir():
        return ""
    extra: list[str] = []
    for p in sorted(web.rglob("*")):
        if "node_modules" in p.parts:
            continue
        if p.suffix not in {".svelte", ".ts"}:
            continue
        if p.name in _REVEAL_ARCHIVE_SKIP_EXTRA:
            continue
        text = p.read_text()
        name_hit = bool(re.search(r"revealArchive|RevealArchive|reveal.?root", p.name, re.I))
        hook = bool(
            _REVEAL_ARCHIVE_HOOK.search(text)
            or _REVEAL_ARCHIVE_FN.search(text)
            or _REVEAL_ARCHIVE_COMPONENT.search(text)
        )
        if not name_hit and not hook:
            continue
        stem = p.stem
        if stem in host or re.search(rf"\b{re.escape(stem)}\b|{re.escape(p.name)}", host):
            extra.append(text)
    return "\n".join(extra)


def _reveal_archive_mounted_extra(surface: str, extra: str) -> str:
    """Extra sources the surface actually references (unwired drafts do not count)."""
    if not extra.strip():
        return ""
    # Split on typical Svelte file starts is unreliable; treat as one blob
    # only when the surface names a reveal-archive helper.
    if _REVEAL_ARCHIVE_COMPONENT.search(surface) or _REVEAL_ARCHIVE_FN.search(surface):
        return extra
    for hook in _REVEAL_ARCHIVE_HOOK_NAMES:
        if hook in surface:
            return extra
    return ""


def _people_path_window(app: str) -> str:
    """People sidebar around the shown archive path (st.path)."""
    markup = _svelte_markup(app)
    blocks = _hook_element_blocks(markup, "data-people-sidebar")
    sidebar = "\n".join(blocks) if blocks else markup
    return _windows_around(sidebar, re.compile(r"\{st\.path\}"), before=280, after=560)


def _people_reveal_control_src(app: str, extra: str) -> str:
    markup = _svelte_markup(app)
    extra_m = _svelte_markup(extra) if extra else extra
    blocks = _hook_element_blocks(markup, "data-people-sidebar")
    sidebar = "\n".join(blocks) if blocks else markup
    parts: list[str] = []
    path_win = _people_path_window(app)
    mounted = _reveal_archive_mounted_extra(path_win + "\n" + sidebar, extra_m)
    if _looks_like_reveal_archive(path_win) or _looks_like_reveal_archive(mounted):
        parts.append(path_win)
        if mounted.strip():
            parts.append(mounted)
    for hook in _REVEAL_ARCHIVE_HOOK_NAMES:
        parts.extend(_hook_element_blocks(sidebar, hook))
        if extra:
            parts.extend(_hook_element_blocks(extra, hook))
    if not parts and _looks_like_reveal_archive(sidebar):
        parts.append(sidebar)
    seen: set[str] = set()
    uniq: list[str] = []
    for p in parts:
        if p and p not in seen:
            seen.add(p)
            uniq.append(p)
    return "\n".join(uniq)


def _doctor_reveal_control_src(doctor: str, extra: str) -> str:
    section = _doctor_backup_section(doctor)
    extra_m = _svelte_markup(extra) if extra else extra
    mounted = _reveal_archive_mounted_extra(section, extra_m)
    parts: list[str] = []
    if _looks_like_reveal_archive(section) or _looks_like_reveal_archive(mounted):
        parts.append(section)
        if mounted.strip():
            parts.append(mounted)
    for hook in _REVEAL_ARCHIVE_HOOK_NAMES:
        parts.extend(_hook_element_blocks(section, hook))
        if mounted:
            parts.extend(_hook_element_blocks(mounted, hook))
    seen: set[str] = set()
    uniq: list[str] = []
    for p in parts:
        if p and p not in seen:
            seen.add(p)
            uniq.append(p)
    return "\n".join(uniq)


def _reveal_archive_handler_src(host: str, control: str) -> str:
    names: set[str] = set(_REVEAL_ARCHIVE_FN.findall(host))
    names.update(_REVEAL_ARCHIVE_FN.findall(control))
    for m in re.finditer(r"(?:onclick|on:click)\s*=\s*\{([^}]{0,400})\}", control):
        names.update(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", m.group(1)))
    chunks = [control]
    for name in sorted(names):
        if name in _REVEAL_ARCHIVE_HANDLER_SKIP:
            continue
        fn = (
            _ts_function_body(host, name)
            or _ts_fn_body(host, name)
            or _function_body(host, name)
        )
        if fn:
            chunks.append(fn)
            chunks.append(_expand_fn_calls(host, fn))
    return "\n".join(chunks)


def _find_reveal_archive_cmd(rust: str, web: str) -> str:
    """Rust command that reveals the open archive root (not reveal_cas / open_url)."""
    for name in _REVEAL_ARCHIVE_CMD_SNAKE:
        if re.search(rf"\bfn\s+{re.escape(name)}\b", rust):
            return name
    for camel, snake in zip(_REVEAL_ARCHIVE_CAMEL, _REVEAL_ARCHIVE_CMD_SNAKE, strict=True):
        if re.search(rf"\b{re.escape(camel)}\b", web) and re.search(
            rf"\bfn\s+{re.escape(snake)}\b", rust
        ):
            return snake
    for name in _REVEAL_ARCHIVE_CMD_SNAKE:
        if re.search(
            rf"invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']{re.escape(name)}[\"']",
            web,
        ) and re.search(rf"\bfn\s+{re.escape(name)}\b", rust):
            return name
    gh = re.search(r"generate_handler!\s*\[([^\]]*)\]", rust, re.S)
    if not gh:
        return ""
    for name in re.findall(r"\b([a-z][a-z0-9_]*)\b", gh.group(1)):
        if name in {"reveal_cas", "open_url", "cas_data_url"}:
            continue
        body = _rust_function_body(rust, name)
        if not body:
            continue
        if "cas_blob_path" in body:
            continue
        if (
            "/usr/bin/open" in body
            and re.search(r"[\"']-R[\"']", body)
            and re.search(r"\barchive_root\b", body)
        ):
            return name
    return ""


def _reveal_archive_cmd_invoke(cmd: str) -> re.Pattern[str]:
    names = {cmd, _REVEAL_ARCHIVE_CAMEL[_REVEAL_ARCHIVE_CMD_SNAKE.index(cmd)]} if cmd in _REVEAL_ARCHIVE_CMD_SNAKE else {cmd}
    # camelCase of an unknown snake name
    if cmd not in _REVEAL_ARCHIVE_CMD_SNAKE:
        parts = cmd.split("_")
        names.add(parts[0] + "".join(p.title() for p in parts[1:]))
    alt = "|".join(re.escape(n) for n in sorted(names))
    return re.compile(
        r"(?:"
        r"invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']" + re.escape(cmd) + r"[\"']"
        r"|api\.(?:" + alt + r")\s*\("
        r")"
    )


_REVEAL_ARCHIVE_CANON_CMP = re.compile(
    r"("
    r"\bcanon\b.{0,40}(?:!=|==).{0,40}\bexpected\b"
    r"|\bexpected\b.{0,40}(?:!=|==).{0,40}\bcanon\b"
    r")"
)
_REVEAL_ARCHIVE_CANON_BIND = re.compile(
    r"\blet\s+(?:mut\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=;]+)?="
    r"\s*[^;]*\bcanonicalize\s*\("
)


def _reveal_archive_canon_self_cmp(body: str) -> bool:
    """True if two canonicalize() results are compared with != / ==."""
    if _REVEAL_ARCHIVE_CANON_CMP.search(body):
        return True
    names: list[str] = []
    seen: set[str] = set()
    for name in _REVEAL_ARCHIVE_CANON_BIND.findall(body):
        if name not in seen:
            seen.add(name)
            names.append(name)
    if len(names) < 2:
        return False
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            if re.search(
                rf"\b{re.escape(a)}\b.{{0,40}}(?:!=|==).{{0,40}}\b{re.escape(b)}\b"
                rf"|\b{re.escape(b)}\b.{{0,40}}(?:!=|==).{{0,40}}\b{re.escape(a)}\b",
                body,
            ):
                return True
    return False


def assert_reveal_archive(crate: Path) -> None:
    """#274: Reveal archive folder in Finder from Doctor / People.

    Doctor Backup and People (near st.path) have a Reveal control.
    A Rust command (not reveal_cas, not open_url) reads archive_root
    from app state and runs /usr/bin/open -R. No path from the webview
    (or a client path is ignored). Canonicalize; refuse if not the
    open root. reveal_cas stays hash-only. No plugin-shell / opener /
    fetch("http / upload / zip-to-iCloud / encryption claim / second
    CAS copy. Docs: Reveal archive folder; copy after close.
    Do not rewrite #135 / #204 / #272 / #273.
    Follow-up: exactly one canonicalize on the archive root; fail
    if two canonicalize() results are compared (!= / ==). Keep
    /usr/bin/open -R, archive_root from app state, no webview path.
    """
    doctor_path = crate / "web" / "lib" / "DoctorPane.svelte"
    if not doctor_path.is_file():
        fail("#274: DoctorPane.svelte required (Backup Reveal archive)")
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#274: App.svelte required (People Reveal near archive path)")
    doctor = doctor_path.read_text()
    app = app_path.read_text()
    extra_doc = _reveal_archive_extra(crate, doctor)
    extra_people = _reveal_archive_extra(crate, app)
    doctor_control = _doctor_reveal_control_src(doctor, extra_doc)

    # 1) Primary red: Doctor Backup has no Reveal archive control.
    if not doctor_control.strip():
        fail(
            "#274: Doctor Backup section must have a Reveal control "
            "(Reveal in Finder / Reveal archive / data-reveal-archive)"
        )

    people_control = _people_reveal_control_src(app, extra_people)
    if not people_control.strip():
        fail(
            "#274: People sidebar must have a Reveal control near the "
            "shown archive path (st.path)"
        )

    web = _web_logic(crate)
    rust = _tauri_rust_blob(crate)
    api_path = crate / "web" / "lib" / "api.ts"
    api = api_path.read_text() if api_path.is_file() else ""
    toml = (crate / "Cargo.toml").read_text() if (crate / "Cargo.toml").is_file() else ""
    pkg = (crate / "package.json").read_text() if (crate / "package.json").is_file() else ""
    caps_path = crate / "capabilities" / "default.json"
    caps = caps_path.read_text() if caps_path.is_file() else ""
    app_docs = repo_root() / "docs" / "user" / "app.md"
    backup_docs = repo_root() / "docs" / "user" / "backup.md"
    dtxt = ""
    if app_docs.is_file():
        dtxt += app_docs.read_text() + "\n"
    if backup_docs.is_file():
        dtxt += backup_docs.read_text()

    host = doctor + "\n" + extra_doc + "\n" + app + "\n" + extra_people + "\n" + api
    handler = _reveal_archive_handler_src(host, doctor_control + "\n" + people_control)

    # 3) Rust command reveals the open archive root (not reveal_cas / open_url).
    cmd = _find_reveal_archive_cmd(rust, web + "\n" + handler)
    if not cmd or cmd in {"reveal_cas", "open_url"}:
        fail(
            "#274: a Rust command (not reveal_cas, not open_url) must "
            "reveal the open archive root via /usr/bin/open -R"
        )
    sig = _rust_fn_signature(rust, cmd)
    body = _rust_body_with_callees(rust, cmd)
    if not body.strip():
        fail(
            f"#274: Rust command {cmd} must read archive_root and "
            "reveal that folder (fn taking no webview path)"
        )
    if not re.search(r"\barchive_root\b", body):
        fail(
            f"#274: {cmd} must read archive_root from app state "
            "(do not take st.path from the webview)"
        )
    has_path_arg = bool(re.search(r"\b(?:path|url|file|href|uri)\s*:", sig, re.I))
    if has_path_arg and not re.search(r"\barchive_root\b", body):
        fail(
            f"#274: {cmd} must not take a path from the webview — "
            "read archive_root (or ignore a client path)"
        )
    if not re.search(r"std::process|\buse\s+std::process", rust):
        fail(
            "#274: open Finder with std::process "
            "(not tauri-plugin-shell / plugin-opener)"
        )
    if not re.search(r"Command::new|std::process::Command", body):
        fail(
            f"#274: {cmd} must reveal the folder with std::process::Command "
            "(/usr/bin/open -R)"
        )
    if "/usr/bin/open" not in body:
        fail(f"#274: {cmd} must use /usr/bin/open -R on the archive root")
    if not re.search(r"[\"']-R[\"']", body):
        fail(
            f"#274: {cmd} must pass -R so Finder selects the archive folder "
            "(not a file inside cas/)"
        )
    if "cas_blob_path" in body:
        fail(
            f"#274: {cmd} must reveal the archive root, not a CAS blob "
            "(do not reuse reveal_cas / cas_blob_path)"
        )
    if not re.search(r"\bcanonicalize\s*\(", body):
        fail(f"#274: {cmd} must canonicalize the open archive root")
    if has_path_arg and not re.search(
        r"("
        r"starts_with"
        r"|not the open root"
        r"|outside (?:the )?(?:open )?archive"
        r"|is not the open"
        r")",
        body,
    ):
        fail(
            f"#274: {cmd} must refuse a client path that is not the "
            "open archive root"
        )
    if re.search(r"[\"']https?://", body):
        fail(f"#274: {cmd} must not open http(s) — folder only")
    if _ARBITRARY_SHELL.search(body) or _ARBITRARY_SHELL.search(rust):
        fail("#274: no shell of arbitrary commands — only /usr/bin/open on the archive root")
    for m in re.finditer(r"Command::new\s*\(", body):
        arg = _rust_call_arg(body, m.end() - 1)
        if "/usr/bin/open" not in arg:
            fail(
                "#274: no shell of arbitrary commands — "
                "Command::new must be /usr/bin/open on the archive root"
            )
    if not re.search(
        r"generate_handler!\s*\[[^\]]*\b" + re.escape(cmd) + r"\b", rust, re.S
    ):
        fail(f"#274: register {cmd} in generate_handler")

    # Frontend invokes that command — not reveal_cas (hash) / open_url.
    invoke_rx = _reveal_archive_cmd_invoke(cmd)
    if not invoke_rx.search(handler) and not invoke_rx.search(web):
        fail(
            f"#274: Doctor / People Reveal must invoke {cmd} "
            "(not reveal_cas, not open_url)"
        )
    if re.search(r"\brevealCas\s*\(|invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']reveal_cas[\"']", handler):
        fail(
            "#274: do not reuse reveal_cas (CAS hash) to reveal the "
            "archive folder"
        )
    if re.search(r"\bopenUrl\s*\(|invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']open_url[\"']", handler):
        fail("#274: do not reuse open_url for a folder (#272 is http(s) only)")
    payloads = _invoke_payloads(web + "\n" + handler, invoke_rx)
    for payload in payloads:
        if _payload_has_path_or_url(payload) and has_path_arg:
            if not re.search(r"\barchive_root\b", body):
                fail(
                    f"#274: do not pass st.path from the webview to {cmd} "
                    "(read archive_root)"
                )

    # 4) reveal_cas still takes hash only (do not soften #135).
    cas_sig = _rust_fn_signature(rust, "reveal_cas")
    cas_body = _rust_function_body(rust, "reveal_cas")
    if not cas_sig.strip() or not cas_body.strip():
        fail("#274: keep reveal_cas (hash only) — do not soften #135")
    if not re.search(r"\bhash\b", cas_sig, re.I):
        fail("#274: reveal_cas must still take a hash (do not soften #135)")
    if re.search(r"\b(?:path|url|file|href|uri)\s*:", cas_sig, re.I):
        fail(
            "#274: reveal_cas must still take the hash only — "
            "no path from the webview"
        )
    if "cas_blob_path" not in cas_body:
        fail("#274: reveal_cas must still resolve cas/ab/cd/<hash> via cas_blob_path")
    if not re.search(
        r"generate_handler!\s*\[[^\]]*\breveal_cas\b", rust, re.S
    ):
        fail("#274: keep reveal_cas in generate_handler (do not soften #135)")
    if not re.search(
        r"revealCas\s*:\s*\(\s*hash\b|invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']reveal_cas[\"']\s*,\s*\{\s*hash",
        api,
    ):
        fail("#274: api.revealCas must still take hash only (do not soften #135)")

    # 5) Bans: plugin-shell / opener / fetch / upload / zip-iCloud / encrypt / second CAS.
    if _PLUGIN_SHELL.search(toml) or _PLUGIN_SHELL.search(pkg):
        fail(
            "#274: do not add tauri-plugin-shell / tauri-plugin-opener "
            "(std::process file-only open)"
        )
    if _PLUGIN_SHELL.search(rust) or _PLUGIN_SHELL.search(web):
        fail(
            "#274: do not add tauri-plugin-shell / tauri-plugin-opener "
            "(std::process file-only open)"
        )
    if _SHELL_CAP.search(caps):
        fail(
            "#274: capabilities must not add shell:allow-execute / "
            "shell:allow-open / opener (no arbitrary Command)"
        )
    reveal_surf = _without_comments(handler + "\n" + doctor_control + "\n" + people_control + "\n" + body)
    if _FETCH_CALL.search(reveal_surf) or _LINKIFY_FETCH.search(reveal_surf):
        fail('#274: no fetch("http — reveal is local /usr/bin/open -R')
    if _REVEAL_ARCHIVE_UPLOAD.search(reveal_surf):
        fail("#274: no upload")
    if _REVEAL_ARCHIVE_ZIP_ICLOUD.search(doctor + "\n" + app + "\n" + rust + "\n" + handler):
        fail("#274: no zip-to-iCloud backup command")
    if _REVEAL_ARCHIVE_BACKUP_FN.search(rust):
        fail("#274: no zip-to-iCloud / interlace backup command")
    product_claim = "\n".join((doctor, app, rust, dtxt, handler))
    if _claim_without_negation(product_claim, _REVEAL_ARCHIVE_ENCRYPT):
        fail(
            "#274: no “database is encrypted” / SQLCipher claim "
            "(folder is the backup unit; FileVault)"
        )
    if _REVEAL_ARCHIVE_SECOND_CAS.search(handler + "\n" + body) or re.search(
        r"\bfn\s+(?:copy_cas|backup_cas|duplicate_cas)\b", rust
    ):
        fail("#274: no second CAS copy — backup is copy the archive folder")

    # 6) Docs: Reveal archive folder from Doctor / People; copy after close.
    if not dtxt.strip():
        fail(
            "#274: docs/user/app.md and/or docs/user/backup.md required — "
            "Reveal archive folder in Finder from Doctor / People; "
            "backup is still copy that folder after closing the app"
        )
    doc_win = ""
    for m in _REVEAL_ARCHIVE_DOC.finditer(dtxt):
        i = m.start()
        doc_win += dtxt[max(0, i - 80) : m.end() + 200] + "\n"
    if not doc_win.strip():
        fail(
            "#274: docs/user/app.md and/or docs/user/backup.md must say "
            "Reveal archive folder in Finder from Doctor / People"
        )
    if not re.search(r"\bDoctor\b", doc_win):
        fail(
            "#274: docs must say Reveal archive folder from Doctor "
            "(and People)"
        )
    if not re.search(r"\bPeople\b", doc_win):
        fail(
            "#274: docs must say Reveal archive folder from People "
            "(and Doctor)"
        )
    copy_win = ""
    for m in _REVEAL_ARCHIVE_DOC_COPY.finditer(dtxt):
        i = m.start()
        copy_win += dtxt[max(0, i - 80) : m.end() + 160] + "\n"
    if not copy_win.strip() or not re.search(
        r"("
        r"copy (?:that |the )folder"
        r"|folder is the backup unit"
        r")",
        copy_win,
        re.I,
    ):
        fail(
            "#274: docs must say backup is still copy that folder "
            "after closing the app"
        )
    if not re.search(
        r"("
        r"after (?:you )?clos"
        r"|clos(?:e|ing) (?:the )?(?:app|window)"
        r")",
        copy_win,
        re.I,
    ):
        fail(
            "#274: docs must say copy that folder after closing the app"
        )

    # 7) Follow-up: exactly one canonicalize; no dead self-comparison.
    own = _rust_function_body(rust, cmd)
    surf = own if own.strip() else body
    n_canon = len(re.findall(r"\bcanonicalize\s*\(", surf))
    if n_canon != 1 or _reveal_archive_canon_self_cmp(surf):
        fail(
            f"#274: {cmd} must canonicalize the archive root once — "
            "do not compare two canonicalize() results (!= / ==); "
            "drop the dead canon != expected self-check"
        )


# #136 — defer doctor CAS scan so large archives open fast.
_DOCTOR_ISSUE_API = re.compile(
    r"("
    r"(?:api\.)?doctorIssues\b"
    r"|(?:api\.)?doctor_issues\b"
    r"|invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']doctor_issues"
    r")",
)
_DOCTOR_RUN_API = re.compile(r"(?:api\.)?doctorRun\b|doctor_run_cmd|\bdoctor_run\b")
_QUICK_DOCTOR = re.compile(
    r"("
    r"doctorIssuesQuick"
    r"|doctor_issues_quick"
    r"|quick\s*:\s*true"
    r"|mode\s*:\s*[\"']quick[\"']"
    r"|doctorIssues\s*\(\s*true\s*\)"
    r")",
    re.I,
)
_GC_ON_OPEN = re.compile(r"\bgc_cas\b|\bgcCas\s*:\s*true")
_GC_THREAD = re.compile(
    r"("
    r"thread::spawn"
    r"|std::thread"
    r"|Builder::new\s*\(\s*\)\s*\.name\s*\(\s*[\"'][^\"']*gc"
    r")",
    re.I,
)
_OPEN_AWAIT_SKIP = _SCROLL_HELPER_SKIP | {
    "api",
    "invoke",
    "doctorIssues",
    "doctorIssuesQuick",
    "doctorRun",
    "people",
    "linkEvents",
    "status",
    "open",
    "init",
    "pickFolder",
    "rememberedPath",
    "showErr",
    "csv",
    "trim",
}


def _await_expression(src: str, start: int) -> str:
    """Expression after `await` at `start`, up to `;` / newline at depth 0."""
    n = len(src)
    i = start
    while i < n and src[i] in " \t":
        i += 1
    depth = 0
    j = i
    while j < n:
        nxt = _js_next(src, j)
        if nxt != j:
            j = nxt
            continue
        c = src[j]
        if c in "({[":
            depth += 1
        elif c in ")}]":
            if depth == 0:
                break
            depth -= 1
        elif c in ";,\n" and depth == 0:
            break
        j += 1
    return src[i:j].strip()


def _doctor_expr_is_quick(expr: str) -> bool:
    return bool(_QUICK_DOCTOR.search(expr))


def _doctor_expr_is_full_scan(expr: str) -> bool:
    if not _DOCTOR_ISSUE_API.search(expr):
        return False
    return not _doctor_expr_is_quick(expr)


def _open_awaited_surface(web: str, roots: tuple[str, ...]) -> str:
    """Bodies of `roots` plus only functions they `await` (not fire-and-forget)."""
    parts: list[str] = []
    seen: set[str] = set()

    def walk(name: str) -> None:
        if name in seen or name in _OPEN_AWAIT_SKIP:
            return
        seen.add(name)
        body = _ts_function_body(web, name) or _function_body(web, name)
        if not body:
            return
        parts.append(body)
        for m in re.finditer(r"\bawait\s+", body):
            expr = _await_expression(body, m.end())
            ident = re.match(r"(?:api\.)?([A-Za-z_]\w*)", expr)
            if ident:
                walk(ident.group(1))

    for root_name in roots:
        walk(root_name)
    return "\n".join(parts)


def _awaited_exprs(src: str) -> list[str]:
    return [_await_expression(src, m.end()) for m in re.finditer(r"\bawait\s+", src)]


def _core_rust_blob(root: Path) -> str:
    src = root / "crates" / "interlace-core" / "src"
    if not src.is_dir():
        return ""
    return "\n".join(p.read_text() for p in sorted(src.rglob("*.rs")) if p.is_file())


def _full_doctor_scan_body(core_src: str, rust: str) -> str:
    """Archive::doctor_issues (full) plus callees — not the quick path."""
    blob = core_src + "\n" + rust
    body = _rust_body_with_callees(blob, "doctor_issues")
    if body.strip():
        return body
    return _rust_function_body(blob, "doctor_issues")


def assert_defer_doctor_cas(crate: Path) -> None:
    """#136: open shows People without awaiting a full CAS walk.

    Doctor badge may load async or stay empty until the Doctor tab.
    Doctor tab (load / Refresh) still runs the full scan that walks
    referenced CAS hashes. A missing blob still surfaces. No background
    GC on open.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#136: App.svelte required (open / applyStatus must show People first)")
    doctor_path = crate / "web" / "lib" / "DoctorPane.svelte"
    if not doctor_path.is_file():
        fail("#136: DoctorPane.svelte required (full CAS scan on the Doctor tab)")
    app = app_path.read_text()
    doctor_txt = doctor_path.read_text()
    web = _web_logic(crate)
    rust = _tauri_rust_blob(crate)
    root = repo_root()
    core_src = _core_rust_blob(root)
    docs_app = root / "docs" / "user" / "app.md"
    dtxt = docs_app.read_text() if docs_app.is_file() else ""
    docs_doc = root / "docs" / "user" / "doctor.md"
    ddoc = docs_doc.read_text() if docs_doc.is_file() else ""

    apply_body = _ts_function_body(web, "applyStatus") or _function_body(web, "applyStatus")
    if not apply_body.strip():
        fail("#136: applyStatus required (open / create / reopen last archive)")
    if not re.search(r"\b(?:api\.)?people\s*\(|\brefreshPeople\s*\(", apply_body):
        fail(
            "#136: applyStatus must still load People "
            "(people list + status) when opening clears"
        )

    open_path = _ts_function_body(web, "openPath") or _function_body(web, "openPath")
    if not open_path.strip():
        fail("#136: openPath required (opening must clear before a full CAS walk)")
    if not re.search(r"\bopening\s*=\s*true\b", open_path):
        fail("#136: openPath must set opening = true while the archive opens")
    if not re.search(r"\bopening\s*=\s*false\b", open_path):
        fail("#136: opening must clear so People can render (do not wait on CAS)")
    if not re.search(r"\bapplyStatus\s*\(", open_path):
        fail("#136: openPath must apply status / people (applyStatus) when opening")

    create_body = _ts_function_body(web, "createArchive") or _function_body(
        web, "createArchive"
    )
    if not create_body.strip():
        fail("#136: createArchive required (create must show People without a CAS walk)")
    if not re.search(r"\bapplyStatus\s*\(", create_body):
        fail("#136: createArchive must apply status / people without waiting on CAS")

    if not re.search(r"rememberedPath|openPath\s*\(", app):
        fail("#136: reopen last archive must go through openPath / applyStatus")

    # 1) Open / applyStatus does not await a full CAS walk before People / opening.
    open_surface = _open_awaited_surface(
        web, ("applyStatus", "openPath", "createArchive", "openPicker")
    )
    if not open_surface.strip():
        open_surface = apply_body + "\n" + open_path + "\n" + create_body
    open_clean = _without_comments(open_surface)
    for expr in _awaited_exprs(open_clean):
        if _DOCTOR_RUN_API.search(expr):
            fail(
                "#136: open / applyStatus must not await doctorRun "
                "(People must not wait on a doctor action / GC)"
            )
        if _doctor_expr_is_full_scan(expr):
            fail(
                "#136: open / applyStatus must show People without awaiting a full "
                "CAS walk (cas_get / every attachments.cas_hash) before opening "
                "clears — Doctor badge may be async or empty until the Doctor tab"
            )
    if re.search(r"\bcas_get\b", open_clean) and re.search(r"cas_hash", open_clean):
        fail(
            "#136: applyStatus / open must not walk every attachments.cas_hash / "
            "cas_get before People render"
        )

    # Rust open / create / status must not themselves walk CAS or start GC.
    for name in ("open", "init", "hold", "status"):
        body = _rust_body_with_callees(rust, name)
        if not body.strip():
            continue
        if _GC_ON_OPEN.search(body):
            fail(
                f"#136: no background GC on open "
                f"(gc_cas must not run from Rust {name}())"
            )
        if re.search(r"\bcas_get\b", body) and re.search(
            r"cas_hash|attachments", body
        ):
            fail(
                f"#136: Rust {name}() must not walk attachments.cas_hash / cas_get "
                "(opening must not wait on a full CAS scan)"
            )
        if re.search(r"\bdoctor_issues\s*\(", body) and not _doctor_expr_is_quick(body):
            fail(
                f"#136: Rust {name}() must not run the full doctor_issues CAS walk "
                "(People stay behind opening if open/status awaits it)"
            )

    # People render when opening clears — not inside the spinner, not gated on doctor.
    if not re.search(r"booting\s*\|\|\s*opening|opening\s*\|\|\s*booting", app):
        fail(
            "#136: opening must gate the spinner so People render when opening clears"
        )
    boot = _boot_opening_block(app)
    if re.search(r"data-people-sidebar|{#each\s+people\b", boot):
        fail(
            "#136: People list must render after opening clears, "
            "not inside the opening spinner"
        )
    if not re.search(r"data-people-sidebar|{#each\s+people\b", app):
        fail("#136: People list must still render after open (sidebar / people rows)")

    # 2) Doctor tab still runs the full scan (load / Refresh / doctorIssues).
    load_body = _ts_function_body(doctor_txt, "load") or _function_body(doctor_txt, "load")
    if not load_body.strip():
        fail("#136: DoctorPane load must run the full doctor scan")
    load_clean = _without_comments(load_body)
    if not any(_doctor_expr_is_full_scan(expr) for expr in _awaited_exprs(load_clean)):
        # Fire-and-forget still counts if load calls the full API (Refresh / tab).
        if not _DOCTOR_ISSUE_API.search(load_clean) or _doctor_expr_is_quick(load_clean):
            fail(
                "#136: Doctor tab (DoctorPane load) must run a full scan "
                "(doctorIssues / doctor_issues) that walks referenced CAS hashes "
                "— not only a quick SQLite+FTS check"
            )
        if _doctor_expr_is_quick(load_clean) and not any(
            _doctor_expr_is_full_scan(expr) for expr in _awaited_exprs(load_clean)
        ):
            fail(
                "#136: Doctor tab must invoke the full doctorIssues scan "
                "(not doctorIssuesQuick / quick: true only)"
            )
    if not re.search(r"\bRefresh\b", doctor_txt):
        fail("#136: Doctor tab must keep Refresh (full scan)")
    if not re.search(r"onclick=\{[^}]*\bload\b", doctor_txt):
        fail("#136: Refresh must call load (full doctorIssues scan)")
    if not re.search(r"onMount\s*\(\s*\(\s*\)\s*=>\s*\{[^}]*\bload\s*\(", doctor_txt, re.S):
        if "load()" not in doctor_txt:
            fail("#136: DoctorPane must load the full scan when the Doctor tab opens")

    # IPC used by the Doctor tab still calls the full Archive::doctor_issues.
    cmd_body = _rust_body_with_callees(rust, "doctor_issues_cmd")
    if not cmd_body.strip():
        fail(
            "#136: doctor_issues_cmd must still run the full doctor_issues scan "
            "(Doctor tab / Refresh)"
        )
    if not re.search(r"\bdoctor_issues\s*\(", cmd_body):
        fail(
            "#136: doctor_issues_cmd must call doctor_issues() "
            "(full scan, not only a quick flag)"
        )
    if re.search(r"doctor_issues_quick", cmd_body) and not re.search(
        r"\bdoctor_issues\s*\(", cmd_body
    ):
        fail("#136: Doctor-tab IPC must run the full doctor_issues path")

    full_body = _full_doctor_scan_body(core_src, rust)
    if not full_body.strip():
        fail("#136: Archive::doctor_issues (full) must still exist for the Doctor tab")
    if not re.search(r"\bcas_get\b", full_body):
        fail(
            "#136: full doctor scan must cas_get referenced hashes "
            "(Doctor tab still walks CAS)"
        )
    if not re.search(r"cas_hash", full_body):
        fail(
            "#136: full doctor scan must walk attachments.cas_hash "
            "(referenced CAS hashes)"
        )
    if not re.search(r"CAS blob missing", full_body):
        fail(
            "#136: a missing blob must still surface as a doctor issue "
            "on the full path (Doctor tab / doctor_issues)"
        )

    # CLI with no flag stays a full scan.
    cli = root / "crates" / "interlace-core" / "src" / "cli.rs"
    if cli.is_file():
        cli_txt = cli.read_text()
        if not re.search(r"\bdoctor_issues\s*\(\s*\)", cli_txt):
            fail(
                "#136: CLI `interlace doctor` (no flag) must keep a full "
                "doctor_issues() scan"
            )

    # 3) No background GC on open (applyStatus / open / create / boot).
    if _GC_ON_OPEN.search(open_clean):
        fail(
            "#136: no background GC on open "
            "(gc_cas / GC thread not started from applyStatus/open)"
        )
    if _GC_THREAD.search(open_clean) and _GC_ON_OPEN.search(open_clean + "\n" + rust):
        fail("#136: no background GC thread on open")
    boot_src = _without_comments(app)
    if _GC_ON_OPEN.search(boot_src) and re.search(
        r"rememberedPath|opening\s*=\s*true", boot_src
    ):
        # gcCas: true on the Doctor tab is fine; fail only if it sits on the open path.
        for name in ("applyStatus", "openPath", "createArchive", "openPicker"):
            body = _ts_function_body(web, name) or _function_body(web, name)
            if body and _GC_ON_OPEN.search(_without_comments(body)):
                fail(
                    "#136: no background GC on open "
                    f"(gc_cas must not start from {name})"
                )
    if re.search(r"thread::spawn", rust) and re.search(
        r"gc_cas", _rust_body_with_callees(rust, "open") + _rust_body_with_callees(rust, "init")
    ):
        fail("#136: no background GC thread started from open/init")

    # 4) Docs (D24): open is not blocked on hashing cas/; Doctor tab finds missing blobs.
    if not dtxt.strip():
        fail(
            "#136: docs/user/app.md required "
            "(open is not blocked on hashing cas/; Doctor tab still finds missing blobs)"
        )
    if not re.search(
        r"("
        r"not blocked on hashing"
        r"|without (?:waiting|blocking).{0,60}(?:hash|cas/|CAS)"
        r"|open(?:ing)?(?:ing an archive| of (?:an? )?archive)?.{0,80}"
        r"not.{0,40}(?:hash|walk|scan|blocked).{0,40}cas"
        r"|People.{0,60}(?:immediately|without waiting).{0,60}(?:cas|doctor|hash)"
        r"|does not wait.{0,40}(?:hash|cas/|CAS)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail("#136: docs/user/app.md must say open is not blocked on hashing cas/")
    if not re.search(
        r"("
        r"Doctor tab.{0,100}(?:missing blob|referenced.{0,20}blob|walk.{0,40}cas)"
        r"|missing blob.{0,80}Doctor"
        r"|Doctor.{0,80}(?:still )?(?:walk|find).{0,40}(?:missing|referenced|cas|blob)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#136: docs/user/app.md must say the Doctor tab still finds a missing blob "
            "(full scan of referenced CAS hashes)"
        )
    if not ddoc.strip():
        fail(
            "#136: docs/user/doctor.md required "
            "(Doctor tab still walks referenced CAS / finds missing blobs)"
        )
    if not re.search(
        r"("
        r"Doctor tab.{0,120}(?:missing|referenced|cas_hash|CAS)"
        r"|CAS file missing"
        r"|missing blob"
        r"|cas_hash"
        r"|referenced.{0,40}(?:CAS|blob|hash|attachments)"
        r")",
        ddoc,
        re.I | re.S,
    ):
        fail(
            "#136: docs/user/doctor.md must say the Doctor tab still walks "
            "referenced CAS hashes / finds a missing blob"
        )
