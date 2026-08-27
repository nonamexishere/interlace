"""Reveal-archive / defer-doctor chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.import_reveal_cmd import *
from tauri_gate.import_reveal_doctor import *


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
    app = _web_logic(crate)
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

from tauri_gate.import_reveal_more import assert_defer_doctor_cas
