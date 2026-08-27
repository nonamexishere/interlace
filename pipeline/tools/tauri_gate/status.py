"""Partial-pane / retry-generation chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.status_lib import *


def assert_partial_pane_errors(crate: Path) -> None:
    """#205: one pane can fail without blanking the shell.

    Person timeline, search results, and doctor scan each expose Error +
    Retry on a `data-partial` surface. Timeline IPC fail (selectPerson /
    personShow / personConversations / personTimeline) must not paint
    EmptyState “No messages in this view” / “No people yet” / “Select a
    person”, and must not only dump to showErr / the full-width err
    banner. Search api.search fail must not paint “No hits” / “Type a
    query” and must keep q / platform / kind / dates. Doctor doctorIssues
    fail must not paint “No doctor issues” and must stay in-pane (not
    only onError → App banner). Retry is user-clicked, once per click —
    no setInterval / auto-retry / recursive retry; doctor Retry is not
    GC CAS / integrity / rebuild (doctorRun / gcCas). Owned Button for
    Retry is fine. No CDN / HTTP client / updater / network.server /
    sonner (#201/#202 bans stay). Blocking setup errors still use
    showErr / {#if err}. Docs (D24): failed timeline / search / doctor
    scan shows Error + Retry on that pane; the rest of the shell stays.
    Keep #202 EmptyState titles, #203 skeletons, #204 toasts, #137
    sentence, #156 boot spinner, #113 tlLoading-before-pin, #120
    windowing. Search-jump miss (#124) stays showErr — not this issue.
    """
    app_path = crate / "web" / "App.svelte"
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    doctor_path = crate / "web" / "lib" / "DoctorPane.svelte"
    if not app_path.is_file():
        fail("#205: App.svelte required (person timeline partial Error+Retry)")
    if not search_path.is_file():
        fail("#205: SearchPane.svelte required (search results partial Error+Retry)")
    if not doctor_path.is_file():
        fail("#205: DoctorPane.svelte required (doctor scan partial Error+Retry)")

    app = _web_logic(crate)
    search = _search_pane_blob(crate)
    doctor = doctor_path.read_text()
    en = _chrome_en_text(crate)
    pkg_path = crate / "package.json"
    pkg = pkg_path.read_text() if pkg_path.is_file() else ""
    svelte_blob = "\n".join(p.read_text() for p in _product_svelte(crate))

    # 1) Three surfaces expose Error + Retry. Grep hook: data-partial.
    app_partials = _hook_element_blocks(app, "data-partial")
    search_partials = _hook_element_blocks(search, "data-partial")
    doctor_partials = _hook_element_blocks(doctor, "data-partial")
    missing: list[str] = []
    if not app_partials:
        missing.append("person timeline")
    if not search_partials:
        missing.append("search results")
    if not doctor_partials:
        missing.append("doctor scan")
    if missing:
        fail(
            "#205: missing data-partial Error+Retry on "
            + ", ".join(missing)
            + " (person timeline / search results / doctor scan each need "
            "data-partial on the Error+Retry surface)"
        )

    surfaces = (
        ("person timeline", app, app_partials, ("selectPerson", "personTimeline")),
        ("search results", search, search_partials, ("run", "search")),
        ("doctor scan", doctor, doctor_partials, ("load", "doctorIssues")),
    )
    for label, src, blocks, _loads in surfaces:
        joined = "\n".join(blocks)
        has_retry = _block_has_retry_copy(joined, en)
        has_error = _block_has_error_copy(joined, en)
        if not has_error or not has_retry:
            fail(
                f"#205: {label} data-partial must show Error + Retry "
                "(user-clicked Retry on that pane)"
            )
        if not any(_retry_click_expr(b) or re.search(r"<(?:Button|button)\b", b) for b in blocks):
            fail(
                f"#205: {label} Retry must be a user-clicked Button / button "
                "(owned Button is fine), not an auto-retry"
            )
        if _PARTIAL_MASCOT.search(joined):
            fail(
                f"#205: {label} data-partial must not use a mascot / "
                "illustration / <img>"
            )

    # 2) Timeline IPC fail — in-pane, not EmptyState, not only showErr.
    tl_catches = _ipc_catch_bodies(
        app,
        "selectPerson",
        ("personShow", "personConversations", "personTimeline"),
    )
    if not tl_catches:
        fail(
            "#205: selectPerson must catch personShow / personConversations / "
            "personTimeline so a fail can show in-pane Error+Retry"
        )
    tl_catch = "\n".join(tl_catches)
    tl_flags = _catch_error_flags(app, tl_catch)
    if _pane_catch_dumps_banner(tl_catch) and not (
        tl_flags and any(_partial_bound_to_flags(app, b, tl_flags) for b in app_partials)
    ):
        fail(
            "#205: selectPerson / personShow / personConversations / "
            "personTimeline fail must not only dump to showErr / the "
            "full-width {#if err} banner"
        )
    if _pane_catch_dumps_banner(tl_catch):
        fail(
            "#205: selectPerson / personShow / personConversations / "
            "personTimeline fail must not write showErr / the full-width "
            "err banner (in-pane Error+Retry only; sandbox / lock stay "
            "on the banner)"
        )
    if not tl_flags:
        fail(
            "#205: selectPerson catch must set an in-pane fail flag for "
            "data-partial Error+Retry (not only showErr)"
        )
    if not any(_partial_bound_to_flags(app, b, tl_flags) for b in app_partials):
        fail(
            "#205: person timeline data-partial must show on selectPerson / "
            "personTimeline fail (bind it to the catch flag)"
        )
    for title in (
        "No messages in this view",
        "No people yet",
        "Select a person",
    ):
        # Sidebar “No people yet” may stay for true empty; the timeline
        # fail surface / exclusive chain must not paint it on this fail.
        if title == "No people yet":
            if any(title in b for b in app_partials):
                fail(
                    "#205: timeline IPC fail must not paint EmptyState "
                    "“No people yet” on the broken pane"
                )
            continue
        if not _empty_exclusive_of_partial(app, title, tl_flags):
            fail(
                "#205: timeline IPC fail must not paint EmptyState "
                f"“{title}” (show data-partial Error+Retry on that fail, "
                "not the true-empty EmptyState)"
            )
    if re.search(r"\bsetup\s*=\s*true\b", tl_catch) or re.search(
        r"\bpeople\s*=\s*\[\s*\]", tl_catch
    ):
        fail(
            "#205: timeline IPC fail must keep nav + people sidebar "
            "(do not set setup = true or clear people)"
        )

    # 3) Search api.search fail — in-pane, keep filters, not EmptyState.
    search_catches = _ipc_catch_bodies(search, "run", ("api.search", ".search("))
    if not search_catches:
        fail(
            "#205: SearchPane run() must catch api.search so a fail can "
            "show in-pane Error+Retry"
        )
    search_catch = "\n".join(search_catches)
    search_flags = _catch_error_flags(search, search_catch)
    if _pane_catch_dumps_banner(search_catch):
        fail(
            "#205: SearchPane api.search fail must not only dump to "
            "onError / showErr / the full-width err banner"
        )
    if not search_flags:
        fail(
            "#205: SearchPane run() catch must set an in-pane fail flag "
            "for data-partial Error+Retry (not only onError)"
        )
    if not any(_partial_bound_to_flags(search, b, search_flags) for b in search_partials):
        fail(
            "#205: search results data-partial must show on api.search fail "
            "(bind it to the catch flag)"
        )
    for title in ("No hits", "Type a query"):
        if not _empty_exclusive_of_partial(search, title, search_flags):
            fail(
                "#205: search api.search fail must not paint EmptyState "
                f"“{title}”"
            )
    if re.search(r"\bempty\s*=\s*true\b", search_catch):
        fail("#205: search api.search fail must not paint EmptyState “No hits”")
    if re.search(r"\bsearched\s*=\s*false\b", search_catch):
        fail("#205: search api.search fail must not paint EmptyState “Type a query”")
    for ident in _SEARCH_FILTER_IDENTS:
        if re.search(
            rf"\b{re.escape(ident)}\s*=\s*(?:[\"']{{2}}|null|undefined)",
            search_catch,
        ):
            fail(
                "#205: search api.search fail must keep q / platform / kind / "
                "dates (do not clear filters on that fail path)"
            )
    if not re.search(r"\bbind:value=\{q\}", search):
        fail("#205: search form must keep q (query) after an api.search fail")
    if not re.search(r"\bbind:value=\{platform\}", search):
        fail("#205: search form must keep platform after an api.search fail")
    if not re.search(r"\bbind:value=\{conversationKind\}", search):
        fail("#205: search form must keep kind after an api.search fail")
    if not re.search(r"\bbind:value=\{from\}", search) or not re.search(
        r"\bbind:value=\{to\}", search
    ):
        fail("#205: search form must keep dates after an api.search fail")

    # 4) Doctor doctorIssues fail — in-pane, not healthy empty, not banner-only.
    doctor_catches = _ipc_catch_bodies(doctor, "load", ("doctorIssues",))
    if not doctor_catches:
        fail(
            "#205: DoctorPane load() must catch doctorIssues so a scan fail "
            "can show in-pane Error+Retry"
        )
    doctor_catch = "\n".join(doctor_catches)
    doctor_flags = _catch_error_flags(doctor, doctor_catch)
    if _pane_catch_dumps_banner(doctor_catch):
        fail(
            "#205: doctorIssues scan fail must not only dump to onError / "
            "App showErr / the full-width err banner"
        )
    if not doctor_flags:
        fail(
            "#205: DoctorPane load() catch must set an in-pane fail flag "
            "for data-partial Error+Retry (not only onError)"
        )
    if not any(_partial_bound_to_flags(doctor, b, doctor_flags) for b in doctor_partials):
        fail(
            "#205: doctor scan data-partial must show on doctorIssues fail "
            "(bind it to the catch flag; failure stays on the Doctor pane)"
        )
    if not _empty_exclusive_of_partial(doctor, "No doctor issues", doctor_flags):
        fail(
            "#205: doctorIssues scan fail must not paint EmptyState "
            "“No doctor issues”"
        )

    # 5) Retry is user-clicked, once per click. Doctor Retry is not GC.
    tl_retry = "\n".join(
        _resolve_handler_blob(app, _retry_click_expr(b)) for b in app_partials
    )
    search_retry = "\n".join(
        _resolve_handler_blob(search, _retry_click_expr(b)) for b in search_partials
    )
    doctor_retry = "\n".join(
        _resolve_handler_blob(doctor, _retry_click_expr(b)) for b in doctor_partials
    )
    if _DOCTOR_HEAVY.search(doctor_retry) or (
        _DOCTOR_HEAVY.search("\n".join(doctor_partials))
        and re.search(r"Retry", "\n".join(doctor_partials), re.I)
    ):
        fail(
            "#205: Doctor Retry must re-call load / doctorIssues once — "
            "not doctorRun / gcCas / integrity / rebuild"
        )
    if not re.search(r"\b(?:load|doctorIssues)\b", doctor_retry + "\n" + "\n".join(doctor_partials)):
        fail(
            "#205: Doctor Retry must re-call load / doctorIssues once "
            "(not GC CAS / integrity / rebuild)"
        )
    if _catch_auto_retries(tl_catch, ("selectPerson", "personShow", "personTimeline")):
        fail(
            "#205: Retry must be user-clicked, once per click "
            "(no setInterval / auto-retry / recursive retry that hammers "
            "a locked archive)"
        )
    if _catch_auto_retries(search_catch, ("run", "search")):
        fail(
            "#205: Retry must be user-clicked, once per click "
            "(no setInterval / auto-retry / recursive retry that hammers "
            "a locked archive)"
        )
    if _catch_auto_retries(doctor_catch, ("load", "doctorIssues", "doctorRun")):
        fail(
            "#205: Retry must be user-clicked, once per click "
            "(no setInterval / auto-retry / recursive retry that hammers "
            "a locked archive)"
        )
    if (
        _interval_retries(app, ("selectPerson", "personTimeline", "personShow"))
        or _interval_retries(search, ("run", "search"))
        or _interval_retries(doctor, ("load", "doctorIssues", "doctorRun"))
    ):
        fail(
            "#205: Retry must be user-clicked, once per click "
            "(no setInterval / auto-retry loop that hammers a locked archive)"
        )
    if (
        _effect_auto_retries(app, tl_flags, ("selectPerson", "personTimeline"))
        or _effect_auto_retries(search, search_flags, ("run",))
        or _effect_auto_retries(doctor, doctor_flags, ("load", "doctorIssues"))
    ):
        fail(
            "#205: Retry must be user-clicked, once per click "
            "(no $effect auto-retry that hammers a locked archive)"
        )
    for label, blob in (
        ("person timeline", tl_retry),
        ("search results", search_retry),
        ("doctor scan", doctor_retry),
    ):
        if _AUTO_RETRY_TIMER.search(blob):
            fail(
                f"#205: {label} Retry must be once per click "
                "(no setInterval in the Retry handler)"
            )

    # 6) Shell stays. Blocking setup errors still use the banner.
    if not re.search(r"<nav\b", app):
        fail("#205: nav must stay (timeline / search / doctor pane fail is in-pane)")
    if "data-people-sidebar" not in app:
        fail(
            "#205: people sidebar must stay on a timeline IPC fail "
            "(do not require the people list to unmount)"
        )
    if not re.search(r"\bfunction\s+showErr\b|\bshowErr\s*=", app):
        fail(
            "#205: keep showErr / {#if err} for sandbox #137, lock, and "
            "not-an-archive (do not ban showErr globally)"
        )
    err_branch = _svelte_if_true_branch(app, "err")
    if not err_branch or not re.search(r"\{err\}", err_branch):
        fail(
            "#205: keep the in-page {#if err} banner for sandbox #137 / lock / "
            "not-an-archive (pane fails are in-pane; blocking setup stays here)"
        )
    # Search-jump miss (#124) stays showErr — not this issue (IN.md).
    jump = _ident_body(app, "openPersonAtMessage")
    if jump and "showErr" not in jump:
        fail(
            "#205: openPersonAtMessage must still contain showErr "
            "(#124 miss path)"
        )

    # 7) No CDN / HTTP client / updater / network.server / sonner.
    #    Do not weaken #201/#202 package bans.
    if _TOAST_SONNER_PKG.search(pkg):
        fail("#205: do not add sonner — #201/#202 package bans stay")
    if _HTTP_CLIENT_PKG.search(pkg):
        fail("#205: not in scope — no HTTP client")
    chrome = _web_chrome_blob(crate)
    if _PARTIAL_CDN.search("\n".join(app_partials + search_partials + doctor_partials)):
        fail("#205: data-partial Error+Retry must not load a CDN / network client")
    if _TOAST_CDN.search(chrome) or _TOAST_CDN.search(svelte_blob):
        fail("#205: no CDN toast / HTTP client kit on the partial surfaces")
    toml = (crate / "Cargo.toml").read_text() if (crate / "Cargo.toml").is_file() else ""
    if "tauri-plugin-http" in toml or "tauri-plugin-updater" in toml:
        fail("#205: not in scope — no HTTP client / updater")
    ent_path = crate / "Interlace.entitlements"
    if ent_path.is_file() and "network.server" in ent_path.read_text():
        fail("#205: entitlements must omit network.server")

    # 8) D24: failed timeline / search / doctor scan → Error + Retry; shell stays.
    #    Do not require dropping the #137 sentence or #204 toast lines.
    dtxt = _typo_docs_blob()
    if not dtxt.strip():
        fail(
            "#205: docs/user/app.md (and/or docs/hacking/tauri.md) required "
            "(failed timeline / search / doctor scan shows Error + Retry "
            "on that pane; the rest of the shell stays)"
        )
    if not _docs_205_ok(dtxt):
        fail(
            "#205: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "a failed timeline / search / doctor scan shows Error + Retry "
            "on that pane and the rest of the shell stays"
        )


def assert_partial_retry_generation(crate: Path) -> None:
    """#205 follow-up: Search run() / Doctor load() must drop stale responses.

    Timeline already sequences personShow / personTimeline with tlGen so a
    stale catch cannot write tlError after a newer success. run() and
    load() must do the same (searchGen / scanGen or equivalent): increment
    at start; catch / success / finally writes to searchError / hits /
    searching / empty and scanError / scanning / issues only apply when
    that gen is current. An early `if (searching) return` /
    `if (scanning) return` is enough only when it actually prevents a
    second IPC (busy set true after the return and before the IPC, no
    await in between). Do not change selectPerson / tlGen. Doctor Retry
    stays load / doctorIssues (existing #205). #124 showErr on
    openPersonAtMessage stays in assert_partial_pane_errors.
    """
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    doctor_path = crate / "web" / "lib" / "DoctorPane.svelte"
    if not search_path.is_file():
        fail(
            "#205: SearchPane.svelte required "
            "(run() must ignore stale search responses)"
        )
    if not doctor_path.is_file():
        fail(
            "#205: DoctorPane.svelte required "
            "(load() must ignore stale doctorIssues responses)"
        )

    search = _search_pane_blob(crate)
    doctor = doctor_path.read_text()
    run_body = _without_comments(_ident_body(search, "run"))
    load_body = _without_comments(_ident_body(doctor, "load"))
    if not run_body:
        fail("#205: SearchPane run() required (must ignore stale api.search)")
    if not load_body:
        fail("#205: DoctorPane load() required (must ignore stale doctorIssues)")

    search_ipc = ("api.search",)
    doctor_ipc = ("doctorIssues",)
    search_writes = ("searchError", "hits", "searching", "empty")
    doctor_writes = ("scanError", "scanning", "issues")

    search_early = _early_busy_ipc_status(run_body, "searching", search_ipc)
    if search_early != "ok":
        search_tok = _gen_increment_before_ipc(
            run_body, _first_substr_pos(run_body, search_ipc)
        )
        if search_tok:
            bad = _unguarded_post_ipc_writes(
                run_body, search_tok[0], search_tok[1], search_writes, search_ipc
            )
            if bad:
                fail(
                    "#205: SearchPane run() must not apply a stale catch — "
                    "write searchError / hits / searching only when the "
                    "run() generation is still current"
                )
        elif search_early == "incomplete":
            fail(
                "#205: SearchPane run() if (searching) return does not "
                "prevent a second api.search (set searching = true after "
                "the return and before the IPC, with no await in between "
                "— or use a gen token like tlGen)"
            )
        else:
            fail(
                "#205: SearchPane run() must increment a generation token "
                "(like App tlGen) and only write searchError / hits / "
                "searching when that gen is current (a second overlapping "
                "run() must not let a stale catch win)"
            )

    doctor_early = _early_busy_ipc_status(load_body, "scanning", doctor_ipc)
    if doctor_early != "ok":
        doctor_tok = _gen_increment_before_ipc(
            load_body, _first_substr_pos(load_body, doctor_ipc)
        )
        if doctor_tok:
            bad = _unguarded_post_ipc_writes(
                load_body, doctor_tok[0], doctor_tok[1], doctor_writes, doctor_ipc
            )
            if bad:
                fail(
                    "#205: DoctorPane load() must not apply a stale catch — "
                    "write scanError / scanning / issues only when the "
                    "load() generation is still current"
                )
        elif doctor_early == "incomplete":
            fail(
                "#205: DoctorPane load() if (scanning) return does not "
                "prevent a second doctorIssues (set scanning = true after "
                "the return and before the IPC, with no await in between "
                "— or use a gen token like tlGen)"
            )
        else:
            fail(
                "#205: DoctorPane load() must increment a generation token "
                "(like App tlGen / scanGen) and only write scanError / "
                "scanning / issues when that gen is current (overlapping "
                "Retry / Refresh must not apply a stale catch)"
            )
