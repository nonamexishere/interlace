"""Additional import_doctor asserts."""
from __future__ import annotations

from tauri_gate.import_doctor_drop import *
from tauri_gate.import_doctor_cancel import *


def assert_import_cancel(crate: Path) -> None:
    """#266: cooperative Cancel — enabled while running; in-file abort; sources reuse."""
    root = repo_root()
    import_path = crate / "web" / "lib" / "ImportPane.svelte"
    import_src = import_path.read_text() if import_path.is_file() else ""
    rust_path = crate / "src" / "main.rs"
    rust = _tauri_rust_blob(crate) if rust_path.is_file() else ""
    api_path = crate / "web" / "lib" / "api.ts"
    api = api_path.read_text() if api_path.is_file() else ""
    rust_surf = _without_comments(rust)
    api_surf = _without_comments(api)

    # 1) import_cancel / importCancel in main.rs AND api.ts (first fail today).
    if not _IMPORT_CANCEL_CMD.search(rust_surf):
        fail(
            "#266: import_cancel (or importCancel) required in "
            "crates/interlace-tauri/src/main.rs"
        )
    if not _IMPORT_CANCEL_CMD.search(api_surf):
        fail(
            "#266: import_cancel (or importCancel) required in "
            "crates/interlace-tauri/web/lib/api.ts"
        )

    # 2) ImportPane click / handler calls that API.
    if "data-import-cancel" not in import_src:
        fail("#266: keep #220 data-import-cancel")
    cancel_tag = _contrast_surface_tag(import_src, "data-import-cancel")
    if not cancel_tag or not _IMPORT_CANCEL_CLICK.search(cancel_tag):
        fail(
            "#266: data-import-cancel must have a click / handler "
            "(onclick / on:click)"
        )
    if not _IMPORT_CANCEL_API_CALL.search(import_src):
        fail(
            "#266: ImportPane must call api.importCancel "
            "(or invoke import_cancel) from the Cancel handler"
        )

    # 3) Cancel is enabled while running (not a bare disabled / {true}).
    if _IMPORT_CANCEL_UNCOND_DISABLED.search(cancel_tag):
        fail(
            "#266: data-import-cancel must be enabled while running "
            "(not a bare disabled / disabled={true}; "
            "disabled={…} only when not running / already cancelling)"
        )

    # 4) Core or Tauri mentions a cancel flag.
    model = (root / "crates" / "interlace-core" / "src" / "model.rs").read_text()
    import_mod = (root / "crates" / "interlace-core" / "src" / "import" / "mod.rs")
    import_txt = import_mod.read_text() if import_mod.is_file() else ""
    ctx_path = root / "crates" / "interlace-core" / "src" / "import" / "context.rs"
    ctx_txt = ctx_path.read_text() if ctx_path.is_file() else ""
    flag_blob = _without_comments(model + "\n" + import_txt + "\n" + ctx_txt + "\n" + rust)
    if not _IMPORT_CANCEL_FLAG.search(flag_blob) and not re.search(
        r"\binterrupted\b", rust_surf
    ):
        fail(
            "#266: core or Tauri must mention a cancel flag "
            "(AtomicBool / ImportCancel / cancel / interrupted)"
        )

    # 5) tick / progress treats interrupted as terminal (not only done/failed).
    tick = _ts_fn_body(import_src, "tick") or _function_body(import_src, "tick")
    if not tick or not _IMPORT_TICK_INTERRUPTED.search(tick):
        fail(
            "#266: tick / progress must treat interrupted "
            "(or failed-on-cancel) as terminal (not only done/failed)"
        )

    # 6) No JoinHandle abort / thread::kill.
    if _IMPORT_THREAD_KILL.search(rust_surf):
        fail(
            "#266: no JoinHandle abort / thread::kill "
            "(cooperative flag only)"
        )

    # 7) docs: Cancel stops the import (not “cannot be stopped”).
    docs = root / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    if not dtxt.strip():
        fail("#266: docs/user/app.md required — Cancel stops the import")
    if _IMPORT_DOCS_NO_STOP.search(dtxt):
        fail(
            "#266: docs/user/app.md must not say Cancel is disabled / "
            "the import cannot be stopped"
        )
    if not _IMPORT_DOCS_STOPS.search(dtxt):
        fail("#266: docs/user/app.md must say Cancel stops the import")

    # 8) WhatsApp import() must not call self.probe( (second full ZIP hash/open).
    wa_path = root / "crates" / "interlace-core" / "src" / "import" / "whatsapp.rs"
    wa = _whatsapp_blob(root) if wa_path.is_file() else ""
    import_body = _rust_fn_body(wa, "import")
    if not import_body.strip():
        fail("#266: crates/interlace-core/src/import/whatsapp.rs fn import required")
    if _IMPORT_SELF_PROBE.search(import_body):
        fail(
            "#266: WhatsApp import() must not call self.probe( "
            "(second full ZIP hash/open)"
        )

    # 9) Cancel on ZIP open / list / hash — not only maybe_commit.
    if not _import_fn_checks_cancel(import_txt, "hash_file"):
        fail(
            "#266: hash_file must check cancel "
            "(Cancelled / is_cancelled), not only maybe_commit"
        )
    if not _import_fn_checks_cancel(wa, "open_zip_cancellable"):
        fail(
            "#266: ZIP open must be cancellable "
            "(open_zip_cancellable + Cancelled / is_cancelled)"
        )
    if not _import_fn_checks_cancel(wa, "list_zip"):
        fail(
            "#266: list_zip must check cancel "
            "(Cancelled / is_cancelled), not only maybe_commit"
        )

    # 10) ImportPane must not promise only “Stops after this file”.
    help_blob = _import_describedby_blob(import_src, cancel_tag)
    pane_cancel = help_blob + "\n" + import_src
    if _IMPORT_STOPS_AFTER_FILE.search(pane_cancel):
        fail(
            "#266: ImportPane must not promise only “Stops after this file”"
        )
    if _IMPORT_AFTER_THIS_FILE.search(help_blob) and not re.search(
        r"\b(?:hash|open|checkpoint)\b", help_blob, re.I
    ):
        fail(
            "#266: ImportPane must not promise only “after this file”"
        )
    if not help_blob.strip() or not _IMPORT_CANCEL_OPEN.search(help_blob):
        fail(
            "#266: ImportPane cancel help must mention ZIP open "
            "(hash / open / checkpoint), not “Stops after this file”"
        )

    # 11) Still no JoinHandle abort / thread::kill (keep #220 / earlier #266).
    if _IMPORT_THREAD_KILL.search(rust_surf):
        fail(
            "#266: no JoinHandle abort / thread::kill "
            "(cooperative flag only)"
        )

    # 12) upsert_source / abort_cancelled: origin_path fallback or UPDATE file_blake3.
    upsert_body = _rust_fn_body(import_txt, "upsert_source")
    abort_body = _rust_fn_body(import_txt, "abort_cancelled")
    if not upsert_body.strip():
        fail("#266: upsert_source required in crates/interlace-core/src/import/mod.rs")
    if not _upsert_origin_fallback_or_hash_update(upsert_body, abort_body):
        fail(
            "#266: upsert_source / abort_cancelled must fall back to "
            "origin_path when blake3 misses, or UPDATE file_blake3 "
            "on the existing row (not a hashless-only insert)"
        )

    # 13) WhatsApp media Err arm near read_zip_entry_capped returns Cancelled.
    media_match = _without_comments(_wa_media_zip_match_body(wa))
    if (
        not media_match.strip()
        or not re.search(r"\bCancelled\b", media_match)
        or not re.search(r"\breturn\b", media_match)
    ):
        fail(
            "#266: WhatsApp media Err arm near read_zip_entry_capped "
            "must return Cancelled (not only ctx.warn / media_read)"
        )

    # 14) ImportCancel docs must not embed #266.
    cancel_docs = _import_cancel_struct_docs(model)
    if "#266" in cancel_docs:
        fail("#266: ImportCancel docs in model.rs must not contain #266")
