"""Listbox / focus / ARIA chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.a11y_lib import *


def assert_a11y_listbox_focus_motion(crate: Path) -> None:
    """#133: people listbox, timeline article/label, focus rings, reduced motion.

    VoiceOver can move through people and hear the selected name. Tab order is
    not a trap. Not a full WCAG audit / certificate.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#133: App.svelte required (people list + timeline a11y)")
    app = _web_logic(crate)
    markup = _strip_html_comments(_svelte_markup(app))
    chrome, people_each = _people_list_a11y_surfaces(crate)
    if not chrome.strip():
        chrome = markup
    if not people_each.strip():
        people_each = _people_each_block(markup)
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = _search_pane_blob(crate) if search_path.is_file() else ""
    css_blob = _css_without_comments(
        "\n".join(p.read_text() for p in _web_sources(crate) if p.suffix == ".css")
    )
    index_html = ""
    index_path = crate / "index.html"
    if index_path.is_file():
        index_html = _css_without_comments(index_path.read_text())
    button_src = ""
    button_path = (
        crate / "web" / "lib" / "components" / "ui" / "button" / "button.svelte"
    )
    if button_path.is_file():
        button_src = button_path.read_text()
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    docs_blob = ""
    docs_root = repo_root() / "docs"
    if docs_root.is_dir():
        docs_blob = "\n".join(
            p.read_text()
            for p in sorted(docs_root.rglob("*.md"))
            if p.is_file()
        )
    readme = repo_root() / "README.md"
    if readme.is_file():
        docs_blob += "\n" + readme.read_text()
    tl_block = _timeline_block(crate)
    boot = _boot_opening_block(app)

    # 1) People list: listbox + option, or list + aria-activedescendant.
    #    Prefer this as the pre-impl red — today is <ul><li><button> with neither.
    if not _PEOPLE_EACH.search(markup) and not _PEOPLE_EACH.search(chrome):
        fail(
            "#133: people sidebar must still {#each filtered …} "
            "(listbox/option wraps that list, not SearchPane)"
        )
    has_listbox = bool(_A11Y_ROLE_LISTBOX.search(chrome))
    has_option = bool(_A11Y_ROLE_OPTION.search(people_each) or _A11Y_ROLE_OPTION.search(chrome))
    has_activedesc = bool(_A11Y_ACTIVEDESC.search(chrome))
    has_list = bool(
        _A11Y_ROLE_LIST.search(chrome)
        or re.search(r"<ul\b|<ol\b", chrome, re.I)
    )
    listbox_pattern = has_listbox and has_option
    activedesc_pattern = has_list and has_activedesc
    if not listbox_pattern and not activedesc_pattern:
        fail(
            "#133: people list must be role=\"listbox\" + role=\"option\" "
            "(or a list + aria-activedescendant). "
            "Today's <ul><li><button> is not a listbox — VoiceOver cannot "
            "move through people as options and hear the selected name"
        )
    if has_listbox and not has_option and not has_activedesc:
        fail(
            "#133: people listbox must have role=\"option\" on each person "
            "(or aria-activedescendant pointing at the active option)"
        )

    # 2) aria-selected on the selected person (VoiceOver hears selected name).
    if not _A11Y_SELECTED.search(people_each) and not _A11Y_SELECTED.search(chrome):
        fail(
            "#133: selected person must set aria-selected "
            "(VoiceOver hears the selected name — bind to selectedId === p.id)"
        )
    if not _A11Y_SELECTED_STATE.search(people_each) and not _A11Y_SELECTED_STATE.search(
        chrome
    ):
        fail(
            "#133: aria-selected must follow the selected person "
            "(selectedId === p.id / equivalent), not a constant true"
        )
    if not re.search(r"\bdisplay_name\b", people_each):
        fail(
            "#133: people options must expose display_name "
            "(VoiceOver hears the selected name; not a raw person id)"
        )
    if _A11Y_PERSON_ID_LABEL.search(people_each) and not _A11Y_NAME_IN_LABEL.search(
        people_each
    ):
        fail(
            "#133: people option accessible name must be the display name, "
            "not a raw person id"
        )

    # 3) Timeline message rows: <article> and/or aria-label — not a bare clickable div.
    #    Accessible name is time + preview/snippet, never a raw person id.
    has_article = bool(_A11Y_ARTICLE.search(tl_block))
    has_row_label = bool(_A11Y_ARIA_LABEL.search(tl_block))
    if not has_article and not has_row_label:
        fail(
            "#133: timeline message rows must be <article> (or role=\"article\") "
            "and/or have an accessible name (aria-label) — not a raw clickable <div>"
        )
    # Article must sit on the message (time / body / data-tl-index), not only .day-heading.
    if has_article:
        article_on_row = bool(
            re.search(
                r"<article\b[^>]{0,500}(?:data-tl-index|data-from-me|body_text|displayBody)",
                tl_block,
                re.I | re.S,
            )
            or re.search(
                r"(?:data-tl-index|data-from-me).{0,240}<article\b",
                tl_block,
                re.I | re.S,
            )
            or re.search(
                r"<article\b.{0,900}(?:<time\b|body_text|displayBody|whitespace-pre-wrap)",
                tl_block,
                re.I | re.S,
            )
        )
        if not article_on_row:
            fail(
                "#133: <article> must be the message row (time + body / snippet), "
                "not only a day heading"
            )
    if _A11Y_PERSON_ID_LABEL.search(tl_block) and not _A11Y_NAME_IN_LABEL.search(tl_block):
        fail(
            "#133: timeline accessible name must be time + preview/snippet, "
            "not a raw person id"
        )

    # 4) Visible focus rings on people options and timeline rows (not only j/k ring-2).
    people_surface = chrome + "\n" + people_each
    people_focus = bool(_A11Y_FOCUS_VISIBLE.search(people_surface))
    if not people_focus and re.search(r"<Button\b", people_each) and _A11Y_FOCUS_VISIBLE.search(
        button_src
    ):
        people_focus = True
    if not people_focus:
        people_focus = _css_focus_visible_for(
            css_blob,
            (
                "[role='option']",
                '[role="option"]',
                "[role=option]",
                "listbox",
                "people-option",
                "person-option",
                "data-people-sidebar",
            ),
        )
    if not people_focus:
        fail(
            "#133: people options need a visible focus-visible ring "
            "(focus-visible:ring / :focus-visible) — browser default outline "
            "on a raw <button> is not enough; j/k selection ring is not focus"
        )
    tl_focus = bool(_A11Y_FOCUS_VISIBLE.search(tl_block))
    if not tl_focus:
        tl_focus = _css_focus_visible_for(
            css_blob,
            (
                "article",
                "[role='article']",
                '[role="article"]',
                "timeline",
                "data-tl-index",
                "bubble-me",
                "bubble-them",
            ),
        )
    if not tl_focus:
        fail(
            "#133: timeline message rows need a visible focus-visible ring "
            "(focus-visible:ring on the article) — the j/k ring-2 highlight "
            "is selection, not keyboard focus"
        )
    if button_src and not _A11Y_FOCUS_VISIBLE.search(button_src):
        fail(
            "#133: nav Button primitive must keep focus-visible:ring "
            "(do not drop visible focus on chrome)"
        )

    # 5) prefers-reduced-motion: disable spin / animation / transitions; scroll auto.
    #    Sticky .day-heading has no animation today — still wrap transitions.
    reduce_css = "\n".join(_css_prefers_reduced_blocks(css_blob))
    reduce_html = "\n".join(_css_prefers_reduced_blocks(index_html))
    reduce_all = reduce_css + "\n" + reduce_html
    has_reduce_media = bool(reduce_css.strip() or reduce_html.strip())
    has_motion_tw = bool(
        _A11Y_MOTION_REDUCE_TW.search(app)
        or _A11Y_MOTION_REDUCE_TW.search(boot)
        or _A11Y_MOTION_REDUCE_TW.search(css_blob)
    )
    if not has_reduce_media and not has_motion_tw:
        fail(
            "#133: must honor prefers-reduced-motion "
            "(@media (prefers-reduced-motion: reduce) in CSS, or Tailwind "
            "motion-reduce) — disable spin / animation / sticky-date animation"
        )
    if not _A11Y_ANIM_NONE.search(reduce_all) and not _A11Y_ANIM_NONE.search(app) and not (
        has_motion_tw and re.search(r"motion-reduce:animate-none", app + "\n" + boot + "\n" + css_blob)
    ):
        fail(
            "#133: prefers-reduced-motion must disable animation "
            "(animation: none / animate-none / motion-reduce:animate-none) "
            "so the boot spinner does not spin"
        )
    if not _A11Y_TRANS_NONE.search(reduce_all) and not re.search(
        r"motion-reduce:transition-none", app + "\n" + css_blob
    ):
        fail(
            "#133: prefers-reduced-motion must disable or zero transitions "
            "(transition: none / motion-reduce:transition-none) — including "
            "any sticky-date animation"
        )
    if not _A11Y_SCROLL_AUTO.search(reduce_all) and not re.search(
        r"motion-reduce:scroll-auto", app + "\n" + css_blob
    ):
        fail(
            "#133: prefers-reduced-motion must set scroll-behavior: auto "
            "(or motion-reduce:scroll-auto)"
        )
    # Pre-JS splash spinner is inline in index.html — app.css cannot stop it.
    if _SPIN_ANIM.search(index_html) and not _A11Y_ANIM_NONE.search(reduce_html):
        fail(
            "#133: index.html boot spinner must honor prefers-reduced-motion "
            "(disable boot-spin / animation under reduce — app.css does not apply pre-JS)"
        )
    if re.search(r"animate-spin", boot) or re.search(r"animate-spin", app):
        covered = bool(
            re.search(r"motion-reduce:animate-none", boot)
            or re.search(r"motion-reduce:animate-none", app)
            or _A11Y_ANIM_NONE.search(reduce_css)
        )
        if not covered:
            fail(
                "#133: Opening-last-archive animate-spin must stop under "
                "prefers-reduced-motion (motion-reduce:animate-none or "
                "animation: none in the reduce media query)"
            )

    # 6) Keep the existing SearchPane person-picker listbox (do not steal it).
    if not search_path.is_file():
        fail("#133: SearchPane.svelte required (keep its listbox/option picker)")
    search_markup = _strip_html_comments(_svelte_markup(search))
    if not _A11Y_ROLE_LISTBOX.search(search) and not _A11Y_ROLE_LISTBOX.search(search_markup):
        fail(
            "#133: keep SearchPane's existing role=\"listbox\" "
            "(people sidebar is a second listbox; do not remove the picker)"
        )
    if not _A11Y_ROLE_OPTION.search(search) and not _A11Y_ROLE_OPTION.search(search_markup):
        fail(
            "#133: keep SearchPane's existing role=\"option\" on person picker rows"
        )

    # 7) Ban claiming a WCAG audit certificate (out of scope).
    if _A11Y_WCAG_CERT.search(docs_blob) or _A11Y_WCAG_CERT.search(dtxt):
        fail(
            "#133: do not claim a WCAG certificate / certified audit in docs "
            "(this issue is listbox + focus + reduced motion, not a full audit)"
        )

    # 8) Tab order is not a trap: filter → people options → timeline/chrome.
    #    Lightbox/dialogs may trap (already). Do not inert the people+timeline grid.
    grid_tag = _open_tag_around(
        markup,
        r"grid-cols-\[minmax\(0,18rem\)_minmax\(0,1fr\)\]",
    )
    if not grid_tag:
        grid_tag = _open_tag_around(markup, r"data-people-sidebar")
    sidebar_tag = _open_tag_around(markup, r"data-people-sidebar")
    timeline_tag = _open_tag_around(markup, r"id=[\"']person-timeline[\"']")
    for tag, where in (
        (grid_tag, "people+timeline grid"),
        (sidebar_tag, "people sidebar"),
        (timeline_tag, "person timeline"),
    ):
        if tag and _A11Y_INERT.search(tag):
            fail(
                f"#133: do not put inert on the {where} "
                "(tab order must reach people filter → people options → timeline; "
                "dialogs/lightbox may still trap)"
            )
    filter_win = ""
    fm = re.search(r"id=[\"']person-filter[\"']", markup)
    if fm:
        filter_win = markup[max(0, fm.start() - 160) : fm.end() + 160]
    if filter_win and _A11Y_TABINDEX_NEG.search(filter_win):
        fail(
            "#133: #person-filter must stay in tab order "
            "(do not tabindex=\"-1\" the people filter)"
        )
    # tabindex="-1" on every person skips the list unless the listbox uses
    # aria-activedescendant (roving focus stays on the listbox).
    if _A11Y_TABINDEX_NEG.search(people_each) and not has_activedesc:
        dynamic_tab = bool(re.search(r"tabindex\s*=\s*\{", people_each))
        if not dynamic_tab:
            fail(
                "#133: do not tabindex=\"-1\" every person "
                "(that skips the list). Use listbox + options in tab order, "
                "or roving tabindex with aria-activedescendant"
            )

    # 9) User-visible: one line in docs (keyboard + VoiceOver). Not a certificate.
    if not dtxt.strip():
        fail("#133: docs/user/app.md required (VoiceOver / people list; not a WCAG certificate)")
    if not re.search(r"VoiceOver", dtxt):
        fail(
            "#133: docs/user/app.md must mention VoiceOver on the people list "
            "(hear the selected name; keyboard tab order) — not a WCAG certificate"
        )

from tauri_gate.a11y_more import assert_focus_aria_audit
