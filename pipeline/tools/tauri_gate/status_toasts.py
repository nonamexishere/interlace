"""In-flight / recoverable-toast chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.status_toasts_chrome import *
from tauri_gate.status_toasts_toast import *
from tauri_gate.status_toasts_extra2 import *


def assert_inflight_audible_status(crate: Path) -> None:
    """#203 follow-up: people / timeline in-flight must stay audible.

    aria-busy on the region and/or role=status / sr-only text that is
    not aria-hidden. Decorative bars may stay aria-hidden. Search may
    keep the submit label “Searching…”.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#203: App.svelte required (people / timeline in-flight a11y)")
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#203: SearchPane.svelte required (search in-flight a11y)")
    app = _web_logic(crate)
    search = _search_pane_blob(crate)

    people_flag, people_branch = _people_inflight_branch(app)
    if not people_branch:
        for region in _people_sidebar_regions(crate):
            flag, block = _people_inflight_branch(region)
            if block:
                people_flag, people_branch = flag, block
                break
    people_surface = (
        _region_window(app, r"data-people-sidebar")
        + "\n"
        + _open_tag_around(app, r"""role=["']listbox["']""")
        + "\n"
        + people_branch
    )
    if not _inflight_is_audible(people_surface, people_branch, people_flag):
        fail(
            "#203: people list in-flight must expose aria-busy on the region "
            "or a role=\"status\" / sr-only line that is not aria-hidden"
        )

    tl_branch = _svelte_if_true_branch(app, "tlLoading")
    tl_surface = (
        _region_window(app, r"""id=["']person-timeline["']""")
        + "\n"
        + _open_tag_around(app, r"""id=["']person-timeline["']""")
        + "\n"
        + tl_branch
    )
    if not _inflight_is_audible(tl_surface, tl_branch, "tlLoading"):
        fail(
            "#203: person timeline in-flight must expose aria-busy on the region "
            "or a role=\"status\" / sr-only line that is not aria-hidden"
        )

    search_branch = _svelte_if_true_branch(search, "searching")
    if _SEARCHING_SUBMIT.search(search):
        return
    search_surface = search_branch + "\n" + search
    if not _inflight_is_audible(search_surface, search_branch, "searching"):
        fail(
            "#203: search in-flight must keep “Searching…” or expose aria-busy "
            "/ a role=\"status\" / sr-only line that is not aria-hidden"
        )


def assert_recoverable_toasts(crate: Path) -> None:
    """#204: owned toast for copy / Reveal failures; blocking errors stay in-page.

    data-toast and/or $lib/components/ui/toast (or Toaster). Reveal-fail and
    copy-fail go through the toast, not only err = / the full-width banner.
    Sandbox #137 sentence, lock, and not-an-archive stay in-page via
    friendly / banner. Toasts never interpolate body_text. ConfirmDialog
    stays. No analytics / Sentry / HTTP client / CDN toast kit. Do not
    add sonner here — #201/#202 package bans stay.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#204: App.svelte required (err banner + copy / sandbox copy)")
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    if not cas_path.is_file():
        fail("#204: CasAttach.svelte required (Reveal in Finder failure path)")
    app = _web_logic(crate)
    svelte_blob = "\n".join(p.read_text() for p in _product_svelte(crate))
    pkg_path = crate / "package.json"
    pkg = pkg_path.read_text() if pkg_path.is_file() else ""

    # 1) Toast chrome exists (owned primitive and/or data-toast). No CDN kit.
    if not _toast_chrome_ok(crate, svelte_blob):
        fail(
            "#204: toast chrome required (data-toast and/or owned "
            "$lib/components/ui/toast) — copy / Reveal failures must not "
            "be only the full-width err banner"
        )
    if _TOAST_CDN.search(_web_chrome_blob(crate)):
        fail("#204: toast chrome must be owned — no CDN / network toast kit")

    # 2) Reveal-fail and copy-fail use the toast, not only showErr / err =.
    reveal_blob = _reveal_fail_blob(crate)
    if not _uses_toast_sink(reveal_blob) or _assigns_err_banner(reveal_blob):
        fail(
            "#204: Reveal in Finder failure must show a toast, not only "
            "the full-width err banner (do not showErr / err = on that path)"
        )
    copy_blob = _copy_fail_blob(crate)
    if not _uses_toast_sink(copy_blob) or _assigns_err_banner(copy_blob):
        fail(
            "#204: Copy text / clipboard failure must show a toast, not only "
            "the full-width err banner (do not showErr / err = on that path)"
        )

    # 3) Toast markup / helper must not interpolate body_text.
    toast_src = _toast_source_blob(crate)
    if _TOAST_BODY_INTERP.search(toast_src) or _toast_args_include_body(
        toast_src + "\n" + reveal_blob + "\n" + copy_blob
    ):
        fail(
            "#204: toast markup / helper must not interpolate body_text "
            "(no {body_text} / copyMenu.body_text / copyMenu.text — chrome copy only)"
        )

    # 4) Sandbox #137 sentence, lock, and not-an-archive stay in-page.
    friendly = _ident_body(app, "friendly")
    toast_only = _owned_toast_paths(crate)
    toast_files = "\n".join(p.read_text() for p in toast_only)
    in_page_sandbox = bool(
        _SANDBOX_137.search(app)
        or "SANDBOX_DENIED" in app
        or _SANDBOX_137.search(friendly)
        or "SANDBOX_DENIED" in friendly
    )
    if not in_page_sandbox:
        fail(
            "#204: sandbox-denied must keep the exact #137 sentence in-page "
            "(setup / err banner / friendly / SANDBOX_DENIED), not toast-only: "
            "macOS blocked that folder. Use Open existing… once so Interlace "
            "can remember it."
        )
    if _SANDBOX_137.search(toast_files) and not (
        _SANDBOX_137.search(app) or "SANDBOX_DENIED" in friendly
    ):
        fail(
            "#204: sandbox-denied #137 sentence must stay in-page "
            "(friendly / SANDBOX_DENIED / err banner), not toast-only"
        )
    if "SANDBOX_DENIED" not in friendly and not _SANDBOX_137.search(friendly):
        fail(
            "#204: friendly() must still surface the #137 sandbox sentence "
            "in-page (not toast-only)"
        )
    if "archive in use" not in friendly:
        fail(
            "#204: lock (archive in use) must stay in-page via friendly / "
            "err banner, not toast-only"
        )
    if "not an Interlace archive" not in friendly:
        fail(
            "#204: not-an-archive must stay in-page via friendly / err banner, "
            "not toast-only"
        )
    err_branch = _svelte_if_true_branch(app, "err")
    if not err_branch or not re.search(r"\{err\}", err_branch):
        fail(
            "#204: keep the in-page {#if err} banner for sandbox / lock / "
            "not-an-archive (do not move those to toast-only)"
        )

    # 5) ConfirmDialog stays. No analytics / remote reporter / HTTP client.
    confirm = crate / "web" / "lib" / "ConfirmDialog.svelte"
    if not confirm.is_file():
        fail(
            "#204: ConfirmDialog must stay "
            "(do not replace merge/unlink/undo/doctor confirm with a toast)"
        )
    if not any(
        p.name != "ConfirmDialog.svelte" and "ConfirmDialog" in p.read_text()
        for p in _product_svelte(crate)
    ):
        fail(
            "#204: ConfirmDialog must stay mounted "
            "(App / Review / Doctor — not replaced by a toast)"
        )
    logic = _web_logic(crate)
    if _ANALYTICS_REMOTE_PKG.search(pkg) or _ANALYTICS_REMOTE_PKG.search(logic):
        fail("#204: not in scope — no analytics / Sentry / remote reporter")
    if _HTTP_CLIENT_PKG.search(pkg):
        fail("#204: not in scope — no HTTP client")

    # 6) D24: copy / Reveal failures toast; sandbox / lock stay in-page.
    docs_path = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs_path.read_text() if docs_path.is_file() else ""
    if not dtxt.strip():
        fail(
            "#204: docs/user/app.md required (copy / Reveal failures toast; "
            "sandbox / lock / not-an-archive stay in-page)"
        )
    if not _SANDBOX_137.search(dtxt):
        fail(
            "#204: docs/user/app.md must keep the #137 sandbox sentence "
            "(macOS blocked that folder. Use Open existing… once so "
            "Interlace can remember it.)"
        )
    docs_blob = _typo_docs_blob()
    if not _DOCS_204_TOAST.search(docs_blob):
        fail(
            "#204: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "copy / Reveal failures toast"
        )
    if not _DOCS_204_INPAGE.search(docs_blob):
        fail(
            "#204: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "sandbox / lock / not-an-archive stay in-page"
        )
