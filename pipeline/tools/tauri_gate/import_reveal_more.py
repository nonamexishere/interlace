"""Additional import_reveal asserts."""
from __future__ import annotations

from tauri_gate.import_reveal_cmd import *
from tauri_gate.import_reveal_doctor import *


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
    app = _web_logic(crate)
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
