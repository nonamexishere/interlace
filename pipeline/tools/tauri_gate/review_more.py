"""Additional review asserts."""
from __future__ import annotations

from tauri_gate.review_queue import *
from tauri_gate.review_undo import *


def assert_review_chrome(crate: Path) -> None:
    """#221: ReviewPane Card chrome — safe, reversible, still no raw ids.

    Follow-up (undo freeze): skip split_person / undo_of; ConfirmDialog
    sets open = false before await onconfirm(); undo does not await
    onChanged().
    Follow-up (in-flight Accept/Reject): disable Accept/Reject while
    resolving/undoing; accept/reject/ask return early on that flag;
    callbacks call onError.
    Follow-up (onerror + undo-while-resolving): ConfirmDialog go()
    catches onconfirm and has onerror/onError; App ConfirmDialog
    passes onerror/onError/showErr; Undo disabled + requestUndo
    honor resolving.
    """
    review_path = crate / "web" / "lib" / "ReviewPane.svelte"
    if not review_path.is_file():
        fail("#221: ReviewPane.svelte required (review queue chrome lives there)")
    src = review_path.read_text()
    cleaned = _without_comments(src)
    markup = _svelte_markup(src)
    surface = markup if markup.strip() else src
    visible = _hue_surface(src)

    # 1) Owned Card + Separator imports.
    if not _REVIEW_CARD_IMPORT.search(src) or not _REVIEW_SEP_IMPORT.search(src):
        fail(
            "#221: ReviewPane.svelte must import Card from "
            "$lib/components/ui/card and Separator from "
            "$lib/components/ui/separator"
        )

    # 2) data-review-card on the open-card root.
    if "data-review-card" not in src:
        fail("#221: data-review-card required on the open review card")

    # 3) Explicit Accept / Reject; neither button tag is destructive.
    if not _REVIEW_ACCEPT.search(surface):
        fail("#221: keep Accept on the review card (explicit >Accept<)")
    if not _REVIEW_REJECT.search(surface):
        fail("#221: keep Reject on the review card (explicit >Reject<)")
    for label in ("Accept", "Reject"):
        tag = _review_action_tag(surface, label)
        if tag and re.search(r"\bdestructive\b", tag, re.I):
            fail(
                f"#221: {label} button must not use destructive "
                "(Reject is suppress; Accept is a link you can undo)"
            )

    # 4) No raw review / person id visible-string patterns.
    raw = _REVIEW_RAW_VISIBLE.search(visible)
    if raw:
        fail(
            "#221: queue/detail markup must not show #{r.id} / "
            "person ${ / person ${r.right_person_id / Accept review ${id} "
            f"(found {raw.group(0)!r})"
        )

    # 5) Identifiers + sample text nodes stay (#128).
    if not (
        re.search(r"\bidentifierLabel\b", cleaned + "\n" + surface)
        or re.search(r"\bvalue_normalized\b", surface + "\n" + cleaned)
    ):
        fail(
            "#221: keep identifierLabel or value_normalized on the review card"
        )
    if re.search(r"\{@html\b", surface):
        fail("#221: ReviewPane samples must stay text nodes — no {@html")
    if not re.search(
        r"("
        r"\{[^}]{0,40}body_text[^}]{0,40}\}"
        r"|whitespace-pre-wrap[^>]{0,80}body_text"
        r"|body_text[^;\n]{0,40}\}"
        r")",
        surface,
        re.I,
    ):
        fail("#221: sample bodies must remain text bindings of body_text")

    # 6) Undo on the Review pane (link events), not only the People sidebar.
    if not _REVIEW_LINK_EVENTS.search(cleaned):
        fail("#221: ReviewPane must call linkEvents (undo lives on the pane)")
    if not _REVIEW_UNDO_USE.search(cleaned):
        fail("#221: ReviewPane must call undo (api.undo after Accept)")
    if "data-review-undo" not in src:
        fail("#221: data-review-undo required on the Review pane Undo control")
    if re.search(r"events\s*\[\s*0\s*\]", cleaned) and not re.search(
        r"split_person|undo_of|lastUndoable", cleaned
    ):
        fail(
            "#221: do not undo events[0] blindly — skip split_person / "
            "already-undone / system import links"
        )
    if "split_person" not in cleaned or "undo_of" not in cleaned:
        fail(
            "#221: Review undo must skip split_person and already-undone "
            "events (undo_of)"
        )

    # 6b) Follow-up (undo freeze): ConfirmDialog closes before onconfirm;
    #     Review undo must not await onChanged() (People person_list).
    confirm_path = crate / "web" / "lib" / "ConfirmDialog.svelte"
    if not confirm_path.is_file():
        fail(
            "#221: ConfirmDialog.svelte required "
            "(go() must close before await onconfirm())"
        )
    confirm_src = _without_comments(confirm_path.read_text())
    go_body = _ts_fn_body(confirm_src, "go") or _function_body(confirm_src, "go")
    if not go_body:
        fail(
            "#221: ConfirmDialog.svelte go() required "
            "(set open = false before await onconfirm())"
        )
    await_onconfirm = _REVIEW_AWAIT_ONCONFIRM.search(go_body)
    if await_onconfirm:
        close_open = _REVIEW_OPEN_FALSE.search(go_body)
        if not close_open or close_open.start() > await_onconfirm.start():
            fail(
                "#221: ConfirmDialog go() must set open = false before "
                "await onconfirm() (or not await onconfirm)"
            )
    undo_blob = _review_undo_action_blob(cleaned)
    if _REVIEW_AWAIT_CHANGED.search(undo_blob):
        fail(
            "#221: ReviewPane must not await onChanged() after undo "
            "(People refresh must not block the confirm callback)"
        )

    # 6c) Follow-up (in-flight Accept/Reject): disable + no-op + onError.
    tokens = _review_inflight_tokens(cleaned)
    for label in ("Accept", "Reject"):
        tag = _review_action_tag(surface, label)
        expr = _review_attr_expr(tag, "disabled") if tag else ""
        if not _review_mentions_inflight(cleaned, expr, tokens):
            fail(
                f"#221: {label} button must be disabled while "
                "resolving/undoing (not only !canAccept())"
            )
    for name in ("accept", "reject", "ask"):
        body = _review_fn_body(cleaned, name)
        if not body:
            fail(f"#221: ReviewPane {name}() required")
        conds = _review_if_return_conds(body)
        cond_blob = "\n".join(
            _expand_fn_calls(cleaned, c, depth=2) for c in conds
        )
        if not _review_mentions_inflight(cleaned, cond_blob, tokens):
            fail(
                f"#221: {name}() must return early when resolving/undoing "
                "(or a similar in-flight flag) is set"
            )
    onconfirm = _review_onconfirm_blob(cleaned)
    wrapped = _review_has_try_onerror(cleaned, onconfirm) if onconfirm else False
    if not wrapped:
        for name in ("accept", "reject"):
            body = _review_fn_body(cleaned, name)
            cbs = _review_ask_callback_bodies(cleaned, body) if body else []
            if not cbs or not any(
                _review_has_try_onerror(cleaned, cb) for cb in cbs
            ):
                fail(
                    "#221: Accept/Reject callbacks must try/catch and "
                    "call onError (same as runUndo)"
                )
    cancel_tag = _review_action_tag(
        _svelte_markup(confirm_path.read_text()) or confirm_src, "Cancel"
    )
    cancel_disabled = _review_attr_expr(cancel_tag, "disabled") if cancel_tag else ""
    if re.search(r"\bbusy\b", cancel_disabled) and not (
        _confirm_refuses_open_while_busy(confirm_src)
    ):
        fail(
            "#221: ConfirmDialog must refuse open = true while busy "
            "(or leave Cancel enabled so a resurrected overlay is dismissable)"
        )

    # 6d) Follow-up (onerror + undo-while-resolving): catch + banner;
    #     Undo disabled / requestUndo honor resolving.
    has_onerror = bool(_REVIEW_ONERROR_PROP.search(confirm_src))
    if not has_onerror or not _confirm_go_catches_onconfirm(go_body):
        fail(
            "#221: ConfirmDialog go() must catch onconfirm "
            "and have an onerror / onError prop"
        )
    app_confirm_path = crate / "web" / "App.svelte"
    app_confirm_src = (
        app_confirm_path.read_text() if app_confirm_path.is_file() else ""
    )
    app_confirm_tag = _review_component_tag(app_confirm_src, "ConfirmDialog")
    if not app_confirm_tag:
        fail("#221: App.svelte ConfirmDialog required")
    if not _REVIEW_APP_CONFIRM_ERR.search(app_confirm_tag):
        fail(
            "#221: App.svelte ConfirmDialog must pass "
            "onerror / onError / showErr"
        )
    undo_tag = _review_undo_control_tag(surface)
    undo_disabled = _review_attr_expr(undo_tag, "disabled") if undo_tag else ""
    if not _review_mentions_inflight(cleaned, undo_disabled, {"resolving"}):
        fail(
            "#221: Review Undo disabled must mention resolving "
            "(not only undoing)"
        )
    undo_req = _review_fn_body(cleaned, "requestUndo")
    if not undo_req:
        fail("#221: ReviewPane requestUndo() required")
    undo_conds = _review_if_return_conds(undo_req)
    undo_cond_blob = "\n".join(
        _expand_fn_calls(cleaned, c, depth=2) for c in undo_conds
    )
    if not _review_mentions_inflight(cleaned, undo_cond_blob, {"resolving"}):
        fail(
            "#221: requestUndo() must return early when resolving"
        )

    # 7) No name_score threshold UI; sample loop stays panel.samples.
    if _REVIEW_NAME_SCORE_UI.search(cleaned):
        fail(
            "#221: do not invent name_score raise/lower UI "
            "(threshold policy is not this issue)"
        )
    if not _REVIEW_SAMPLE_EACH.search(surface):
        fail(
            "#221: sample loop must stay {#each panel.samples "
            "(do not add a second body dump)"
        )
    if _REVIEW_SECOND_BODY.search(surface):
        fail(
            "#221: do not add a second body dump — keep the existing "
            "panel.samples loop"
        )

    # 8) docs/user/app.md: Review + undo / reversible / no raw person id
    #    (or identifiers + undo).
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    review_docs = _review_docs_blob(dtxt)
    if not dtxt.strip() or not review_docs:
        fail(
            "#221: docs/user/app.md required — Review + undo / reversible / "
            "no raw person id (or identifiers + undo)"
        )
    has_undo = bool(_REVIEW_DOCS_UNDO.search(review_docs))
    has_no_raw = bool(_REVIEW_DOCS_NO_RAW.search(review_docs))
    has_idents = bool(_REVIEW_DOCS_IDENTS.search(review_docs))
    if not (has_undo and (has_no_raw or has_idents)):
        fail(
            "#221: docs/user/app.md must say Review + undo / reversible / "
            "no raw person id (or identifiers + undo)"
        )

    # 9) Do not soften #q, sidebar, overlay, inspector, CSP,
    #    #219 tokens, #220 data-import-cancel, #218 no Theme.
    svelte_files = _product_svelte(crate)
    svelte_blob = "\n".join(p.read_text() for p in svelte_files)
    app_path = crate / "web" / "App.svelte"
    app = _web_logic(crate) if app_path.is_file() else ""
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = _search_pane_blob(crate) if search_path.is_file() else ""
    conf = (crate / "tauri.conf.json").read_text()
    css_path = crate / "web" / "app.css"
    css = css_path.read_text() if css_path.is_file() else ""
    light_blob = _contrast_light_blob(css)
    dark_blob = _contrast_dark_blob(css)
    if not re.search(r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""", search):
        fail('#221: keep id="q" as the canonical query field (#208)')
    if not re.search(r"\bdata-people-sidebar\b", app):
        fail("#221: keep data-people-sidebar (#159 / #212)")
    if not re.search(r"titleBarStyle", conf) and not re.search(
        r"\bdata-tauri-drag-region\b", app
    ):
        fail("#221: keep the overlay titlebar (#211)")
    if not re.search(r"\bdata-person-inspector\b", app):
        fail("#221: keep data-person-inspector (#213)")
    if CSP not in conf:
        fail("#221: do not soften tauri CSP")
    if not _css_var(light_blob, _STATUS_WARNING_NAMES) or not _css_var(
        dark_blob, _STATUS_WARNING_NAMES
    ):
        fail("#221: keep #219 --warning / --color-warning in light and dark")
    if "data-import-cancel" not in svelte_blob:
        fail("#221: keep #220 data-import-cancel")
    if not _css_var(css, _APPEARANCE_SCRIM_NAMES):
        fail("#221: keep #218 --overlay / --scrim / --lightbox-scrim")
    if _APPEARANCE_THEME_UI.search(svelte_blob) or _APPEARANCE_MENU_LABEL.search(
        svelte_blob
    ):
        fail("#221: keep #218 — no Theme / Appearance menu / data-theme")


def assert_sidebar_undo_chrome(crate: Path) -> None:
    """#269: people sidebar undo — human label, skip split_person.

    Same undoable set as Review lastUndoable. No raw event id as the title.
    Confirm has no Undo event ${id}. ConfirmDialog close-first + App
    onerror stay (#221). Do not rewrite #221 / #265.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#269: App.svelte required (people sidebar undo chrome lives there)")
    app_src = _web_logic(crate)
    cleaned = _without_comments(app_src)
    markup = _svelte_markup(app_src)
    sidebar = _people_sidebar_region(markup) or markup

    # 1) Visible title is not #{e.id} / raw event id.
    title_blobs: list[str] = [_markup_text_nodes(sidebar)]
    for src, inner in _svelte_each_blocks(markup):
        if _SIDEBAR_UNDO_EACH_SRC.search(src):
            title_blobs.append(_markup_text_nodes(inner))
    title_blob = "\n".join(title_blobs)
    raw_title = _SIDEBAR_RAW_ID_TITLE.search(title_blob) or _SIDEBAR_BARE_ID_TEXT.search(
        title_blob
    )
    if raw_title:
        fail(
            "#269: people sidebar undo list must not show #{e.id} / raw "
            "event id as the title (use a short human op + name label; "
            f"found {raw_title.group(0)!r})"
        )

    # 2) Undo path mentions split_person + undo_of (or lastUndoable).
    has_split = "split_person" in cleaned
    has_undo_of = "undo_of" in cleaned
    has_last = "lastUndoable" in cleaned
    if not (has_split and (has_undo_of or has_last)):
        fail(
            "#269: App.svelte undo path must mention split_person and "
            "undo_of (or lastUndoable) — skip the leftover undo-log"
        )

    # 3) Do not call doUndo / api.undo on every events row / split_person.
    for src, inner in _svelte_each_blocks(markup):
        head = src.split(" as ", 1)[0].strip()
        if not re.fullmatch(r"events", head):
            continue
        if not re.search(r"\b(?:doUndo|api\s*\.\s*undo)\s*\(", inner):
            continue
        guard = _sidebar_each_guard_blob(cleaned, inner)
        if not re.search(r"split_person|undo_of|lastUndoable", guard):
            fail(
                "#269: do not call doUndo / api.undo on every events row "
                "including split_person — filter to the Review lastUndoable "
                "set (user merge/link/unlink, not already undone)"
            )

    # 4) Confirm title/body for sidebar undo has no Undo event ${id}.
    undo_fn_blob = _sidebar_undo_fn_blob(cleaned)
    confirm_blob = undo_fn_blob if undo_fn_blob.strip() else cleaned
    raw_confirm = _SIDEBAR_CONFIRM_RAW.search(confirm_blob)
    if raw_confirm:
        fail(
            "#269: sidebar undo confirm must not say Undo event ${id} / "
            "event ${id} (Undo last link? / Undo this merge? is fine; "
            f"found {raw_confirm.group(0)!r})"
        )

    # 5) Keep #221: ConfirmDialog close-first + App onerror; Review
    #    lastUndoable / data-review-undo / skip split_person.
    confirm_path = crate / "web" / "lib" / "ConfirmDialog.svelte"
    if not confirm_path.is_file():
        fail(
            "#269: keep #221 — ConfirmDialog.svelte required "
            "(go() must close before await onconfirm())"
        )
    confirm_src = _without_comments(confirm_path.read_text())
    go_body = _ts_fn_body(confirm_src, "go") or _function_body(confirm_src, "go")
    if not go_body:
        fail(
            "#269: keep #221 — ConfirmDialog.svelte go() required "
            "(set open = false before await onconfirm())"
        )
    await_onconfirm = _REVIEW_AWAIT_ONCONFIRM.search(go_body)
    if await_onconfirm:
        close_open = _REVIEW_OPEN_FALSE.search(go_body)
        if not close_open or close_open.start() > await_onconfirm.start():
            fail(
                "#269: keep #221 — ConfirmDialog go() must set open = false "
                "before await onconfirm() (or not await onconfirm)"
            )
    has_onerror = bool(_REVIEW_ONERROR_PROP.search(confirm_src))
    if not has_onerror or not _confirm_go_catches_onconfirm(go_body):
        fail(
            "#269: keep #221 — ConfirmDialog go() must catch onconfirm "
            "and have an onerror / onError prop"
        )
    app_confirm_tag = _review_component_tag(app_src, "ConfirmDialog")
    if not app_confirm_tag:
        fail("#269: keep #221 — App.svelte ConfirmDialog required")
    if not _REVIEW_APP_CONFIRM_ERR.search(app_confirm_tag):
        fail(
            "#269: keep #221 — App.svelte ConfirmDialog must pass "
            "onerror / onError / showErr"
        )
    review_path = crate / "web" / "lib" / "ReviewPane.svelte"
    review_src = review_path.read_text() if review_path.is_file() else ""
    if "data-review-undo" not in review_src or "lastUndoable" not in review_src:
        fail("#269: keep #221 — Review data-review-undo / lastUndoable")
    if "split_person" not in review_src or "undo_of" not in review_src:
        fail("#269: keep #221 — Review undo must still skip split_person / undo_of")

    # 6) Docs: sidebar undo + skip split / no raw event id.
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    if not dtxt.strip():
        fail(
            "#269: docs/user/app.md required — people sidebar undo uses a "
            "name/op label, skips split_person / undo-log, no raw event id"
        )
    if not _SIDEBAR_DOCS_UNDO.search(dtxt):
        fail(
            "#269: docs/user/app.md must say people sidebar undo "
            "(name/op label, matches Review)"
        )
    if not _SIDEBAR_DOCS_SKIP.search(dtxt):
        fail(
            "#269: docs/user/app.md must say sidebar undo skips "
            "split_person / undo-log / already-undone"
        )
    if not _SIDEBAR_DOCS_NO_RAW.search(dtxt):
        fail(
            "#269: docs/user/app.md must say sidebar undo does not use a "
            "raw event id as the title (name/op label)"
        )
