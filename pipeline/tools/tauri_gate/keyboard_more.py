"""Additional keyboard asserts."""
from __future__ import annotations

from tauri_gate.keyboard_lib import *


def assert_keyboard_list_arrows(crate: Path) -> None:
    """#214: list arrows selectPerson, roving tabindex, tab path, no trap.

    ArrowDown/Up on a focused people listbox/option change the selected
    person (selectPerson next/prev on filtered), not only timeline tlIndex.
    Selected option tabindex 0, others -1. Tab: #person-filter → people →
    #person-timeline; undo / Open other archive are not a stop. INPUT
    guard still returns before bare j/k. Docs. Do not rewrite #132.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#214: App.svelte required (people listbox arrows + tab path)")
    app = _web_logic(crate)
    app_clean = _without_comments(app)
    markup = _strip_html_comments(_svelte_markup(app))
    chrome, people_each = _people_list_a11y_surfaces(crate)
    if not people_each.strip():
        people_each = _people_each_block(markup)
    if not chrome.strip():
        chrome = markup
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = _search_pane_blob(crate) if search_path.is_file() else ""
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    conf_path = crate / "tauri.conf.json"
    conf = conf_path.read_text() if conf_path.is_file() else ""

    raw_body = _app_keydown_body(app_clean) or _app_keydown_body(app)
    if not raw_body.strip():
        fail(
            "#214: App.svelte must handle window keydown "
            "(onKey) so listbox arrows can selectPerson"
        )
    body = _expand_list_arrow_calls(app_clean, raw_body)
    if body == raw_body:
        body = _expand_list_arrow_calls(app, raw_body)

    # 1) When a people listbox/option is focused, ArrowDown/Up selectPerson
    #    next/prev on filtered — not only timeline tlIndex.
    if not _KEY_ARROW_DOWN.search(raw_body) and not _KEY_ARROW_DOWN.search(body):
        fail(
            "#214: onKey must handle ArrowDown "
            "(people listbox when focused; timeline otherwise)"
        )
    if not _KEY_ARROW_UP.search(raw_body) and not _KEY_ARROW_UP.search(body):
        fail(
            "#214: onKey must handle ArrowUp "
            "(people listbox when focused; timeline otherwise)"
        )
    if not _list_arrow_selects_person(
        raw_body, app_clean, _KEY_ARROW_DOWN
    ) and not _list_arrow_selects_person(raw_body, app, _KEY_ARROW_DOWN):
        fail(
            "#214: ArrowDown/Up when a people listbox/option is focused "
            "must selectPerson next/prev on filtered (not only timeline tlIndex)"
        )
    if not _list_arrow_selects_person(
        raw_body, app_clean, _KEY_ARROW_UP
    ) and not _list_arrow_selects_person(raw_body, app, _KEY_ARROW_UP):
        fail(
            "#214: ArrowUp when a people listbox/option is focused "
            "must selectPerson prev on filtered (not only timeline tlIndex)"
        )
    # Timeline arrows stay when the listbox is not focused (do not drop j/k).
    if not re.search(r"\btlIndex\b", raw_body) and not re.search(r"\btlIndex\b", body):
        fail(
            "#214: timeline j/k + arrows must stay when focus is not "
            "in the people listbox (keep tlIndex walk)"
        )

    # 2) Selected option tabindex="0" / {0}; other options tabindex="-1" / {-1}.
    if not people_each.strip():
        fail("#214: people list {{#each filtered}} required (roving tabindex on options)")
    if not _A11Y_ROLE_OPTION.search(people_each) and not _A11Y_ROLE_OPTION.search(chrome):
        fail('#214: people rows must stay role="option" (listbox arrows + roving tabindex)')
    option_blob = "\n".join(_people_option_tags(people_each)) or people_each
    if not _TABINDEX_ATTR.search(option_blob):
        fail(
            "#214: people listbox options must use roving tabindex "
            '(selected tabindex="0" / {0}, others tabindex="-1" / {-1}) — '
            "do not leave every person button default-tabbable"
        )
    if not _option_roving_tabindex_ok(people_each):
        fail(
            "#214: selected people option must be tabindex=\"0\" (or {0}); "
            "other options tabindex=\"-1\" (or {-1})"
        )

    # 3) Tab path: #person-filter → people list → #person-timeline.
    #    Undo / Open other archive must not remain default-tabbable between them.
    #    People / Timeline children only — palette / Search listboxes sort first.
    shell_markup = "\n".join(
        _svelte_markup(p.read_text())
        for p in _web_sources(crate)
        if p.suffix == ".svelte"
        and (p.name == "App.svelte" or p.name.startswith(("People", "Timeline")))
    )
    filter_m = re.search(r"id\s*=\s*[\"']person-filter[\"']", shell_markup)
    list_m = _A11Y_ROLE_LISTBOX.search(shell_markup) or _A11Y_ROLE_OPTION.search(
        shell_markup
    )
    tl_m = re.search(r"id\s*=\s*[\"']person-timeline[\"']", shell_markup)
    if not filter_m:
        fail("#214: keep #person-filter in the People shell (Tab starts there)")
    if not list_m:
        fail('#214: keep the people role="listbox" / option list in the People shell')
    if not tl_m:
        fail("#214: keep #person-timeline (Tab ends at the timeline after the selected person)")
    if not (filter_m.start() < list_m.start() < tl_m.start()):
        fail(
            "#214: Tab path must be #person-filter then people list then "
            "#person-timeline (filter → selected person → timeline)"
        )
    filter_win = shell_markup[max(0, filter_m.start() - 160) : filter_m.end() + 160]
    if _A11Y_TABINDEX_NEG.search(filter_win):
        fail(
            "#214: #person-filter must stay in tab order "
            "(do not tabindex=\"-1\" the people filter)"
        )
    if not _sidebar_chrome_untabbable(shell_markup):
        fail(
            "#214: undo / \"Open other archive\" must not stay default-tabbable "
            "between #person-filter and #person-timeline "
            '(tabindex="-1"; they stay clickable)'
        )

    # 4) INPUT/TEXTAREA/SELECT guard still returns before bare j/k (#q).
    if not _INPUT_TAG_GUARD.search(raw_body) and not _INPUT_TAG_GUARD.search(body):
        fail(
            "#214: keep the INPUT/TEXTAREA/SELECT guard "
            "(Search #q must never see bare j/k)"
        )
    guard_span = _input_guard_span(raw_body)
    if not guard_span:
        fail(
            "#214: INPUT/TEXTAREA/SELECT guard must still wrap the early return "
            "(Search #q never intercepted)"
        )
    guard = raw_body[guard_span[0] : guard_span[1] + 1]
    if not re.search(r"\breturn\b", guard):
        fail(
            "#214: INPUT/TEXTAREA/SELECT guard must return before bare j/k "
            "(Search #q never intercepted)"
        )
    pre = raw_body[: guard_span[0]]
    if _bare_letter_before_guard(pre, _KEY_J) or _bare_letter_before_guard(pre, _KEY_K):
        fail(
            "#214: do not handle bare j/k before the INPUT/TEXTAREA/SELECT guard "
            "— Search #q must not be intercepted"
        )
    if _bare_letter_before_guard(pre, _KEY_ARROW_EITHER):
        fail(
            "#214: do not handle bare ArrowDown/Up before the INPUT guard "
            "(#q / #person-filter must keep their caret)"
        )
    if not _KEY_J.search(raw_body) or not _KEY_K.search(raw_body):
        fail("#214: keep timeline j/k (letters still move messages; arrows may move the list)")

    # 5) Docs: arrows in people list; Tab filter → person → timeline;
    #    j/k still messages; Search #q not intercepted.
    if not dtxt.strip():
        fail(
            "#214: docs/user/app.md required — people-list arrows, Tab order, "
            "j/k on messages, Search #q not intercepted"
        )
    if not _DOCS_LIST_ARROWS.search(dtxt):
        fail(
            "#214: docs/user/app.md must say arrow keys in the people list "
            "change the selected person"
        )
    if not _DOCS_TAB_PATH.search(dtxt):
        fail(
            "#214: docs/user/app.md must document Tab order "
            "(filter → selected person → timeline)"
        )
    if not _DOCS_JK_MESSAGES.search(dtxt):
        fail("#214: docs/user/app.md must keep j/k on messages / the timeline")
    if not _DOCS_Q_SAFE.search(dtxt):
        fail(
            "#214: docs/user/app.md must say typing in Search #q is never intercepted"
        )

    # 6) Do not soften ⌘F, ⌘1–5, #q, sidebar, overlay, inspector, CSP.
    prefix, _tail = _split_people_only(raw_body)
    prefix_x = _expand_fn_calls(app_clean, prefix) if prefix.strip() else body
    if prefix_x == prefix:
        prefix_x = _expand_fn_calls(app, prefix) if prefix.strip() else body
    if not _KEY_F.search(prefix_x) and not _KEY_F.search(raw_body):
        fail("#214: keep ⌘F / ctrl+F Find (do not rewrite #132)")
    if not _has_mod_combo(prefix_x) and not _has_mod_combo(raw_body):
        fail(
            "#214: keep metaKey or ctrlKey on Find / tab digits "
            "(do not rewrite #132 ⌘F / ⌘1–5)"
        )
    for tok in _VIEW_TAB_ORDER:
        if not re.search(rf"[\"']{tok}[\"']", prefix_x) and not re.search(
            rf"[\"']{tok}[\"']", raw_body
        ):
            fail(
                f'#214: keep ⌘1–5 view "{tok}" '
                "(1 People … 5 Doctor — do not rewrite #132)"
            )
    if not re.search(r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""", search):
        fail('#214: keep id="q" as the canonical query field (#208)')
    if not re.search(r"\bdata-people-sidebar\b", app):
        fail("#214: keep data-people-sidebar (#159 / #212)")
    if not re.search(r"\bdata-person-inspector\b", app):
        fail("#214: keep data-person-inspector (#213)")
    if not re.search(r"titleBarStyle", conf) and not re.search(
        r"\bdata-tauri-drag-region\b", app
    ):
        fail("#214: keep the overlay titlebar (#211)")
    if CSP not in conf:
        fail("#214: do not soften tauri CSP")
