"""Conversation-switcher chrome assert. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _INCLUDE_GROUPS_LABEL,
    _call_arg,
    _cond_uses_flag,
    _function_body,
    _template_stack,
    _timeline_block,
    _web_logic,
    _web_sources,
)

from tauri_gate.people_switcher_pretty import (
    _CONV_ALL_LABEL,
    _CONV_CREATE,
    _CONV_EACH,
    _CONV_ID_FALLBACK,
    _CONV_ID_TEXT,
    _CONV_LAST_AT,
    _CONV_MUTE,
    _CONV_PICK,
    _CONV_PIN,
    _CONV_PLATFORM,
    _CONV_RESET_ALL,
    _CONV_SELECT,
    _CONV_STATE_DEFAULT_ALL,
    _CONV_SWITCHER_HOOK,
    _CONV_TITLE,
    _MERGE_CTRL,
    _PERSON_TIMELINE_CALL,
    _UNLINK_CTRL,
    _always_expanded_conversation_list,
    _chrome_hidden_by_default,
    _chrome_toggled_by_title,
    _conversation_switcher_blocks,
    _flag_default_open,
    _groups_ctrl_pos,
    _identity_title_toggle,
    _person_pane_markups,
    _visible_switcher_text,
    _without_calls,
)
from tauri_gate.people_switcher_markup import (
    _conversation_chooser_helpers,
    _heading_exprs,
    _headings_use_label_helper,
    _people_list_hidden_on_select,
    _pretty_platform_helpers,
    _switcher_above_day_heading,
    _switcher_row_markup,
    _switcher_summary_markup,
)
from tauri_gate.people_switcher_label_extra2 import _label_helper_falls_back_to_id

from tauri_gate.status_toasts_toast import _person_detail_markup




def assert_conversation_switcher(crate: Path) -> None:
    """#114: after a person is selected, switch conversations; default All; no raw ids.

    Groups still need include-groups to appear in the list and in All.
    Identity chrome (Merge, include groups, unlink) stays hidden until the
    person name is clicked. Conversation switcher is a compact header control,
    not a second always-expanded list above the bubbles. People sidebar stays.
    All / the open panel must stack above sticky .day-heading (higher z-index
    + background). Switcher label: empty title or title === personTitle shows
    the pretty platform (WhatsApp, Gmail), not the repeated person name;
    distinct titles stay. Not in scope: create / mute / pin. Keep #111–#113.
    """
    app = _web_logic(crate)
    logic = _web_logic(crate)
    api_src = (crate / "web" / "lib" / "api.ts").read_text()
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    whole = app + "\n" + logic

    blocks = _conversation_switcher_blocks(crate)
    if not blocks:
        fail(
            "#114: after selecting a person, list their conversations "
            "({#each conversations / convos / personConversations / conversationList, "
            "a conversation <select>, or data-conversation-switcher) "
            "with title + platform + last_at"
        )
    switcher = "\n".join(blocks)

    # People sidebar and chat bubbles are not the switcher.
    if _CONV_EACH.search(switcher) is None and not _CONV_SWITCHER_HOOK.search(switcher):
        if not _CONV_SELECT.search(switcher):
            fail(
                "#114: conversation switcher must be a list or select of conversations, "
                "not the people sidebar and not a caption inside a chat bubble"
            )
    tl = _timeline_block(crate)
    if switcher.strip() and switcher.strip() in tl:
        fail(
            "#114: conversation switcher must sit outside the message bubbles "
            "(list conversations, then filter the timeline)"
        )

    detail = _person_detail_markup(app)
    if not _CONV_ALL_LABEL.search(switcher) and not _CONV_ALL_LABEL.search(detail):
        fail("#114: conversation switcher must offer All (default = current D18 merged stream)")
    if not _CONV_STATE_DEFAULT_ALL.search(logic) and not _CONV_STATE_DEFAULT_ALL.search(app):
        fail(
            "#114: default conversation must be All "
            "(selected conversation state starts null / undefined / \"all\")"
        )

    sel = _function_body(whole, "selectPerson")
    if not sel:
        fail("#114: selectPerson must still open a person (default conversation = All)")
    opened_all = bool(_CONV_RESET_ALL.search(sel)) or bool(
        re.search(
            r"conversation(?:Id|_id)\s*:\s*(?:null|undefined|(?:append\s*\?))",
            sel,
        )
    )
    if not opened_all:
        fail(
            "#114: opening a person must default to All (merged D18 stream), "
            "not leave a previously picked conversation_id selected"
        )

    choosers = _conversation_chooser_helpers(logic)
    pretty_helpers = _pretty_platform_helpers(logic)
    # Distinct titles still show; do not require interpolating conv.title when
    # that title is the open person's name (helper may show WhatsApp / Gmail).
    if not _CONV_TITLE.search(switcher):
        title_in_helper = any(
            re.search(r"(?:conversation_title|\.title\b|\btitle\b)", blob)
            for blob in choosers.values()
        )
        if not title_in_helper:
            fail("#114: each conversation in the list must show its title")

    summary_exprs = _heading_exprs(_switcher_summary_markup(crate))
    row_exprs = _heading_exprs(_switcher_row_markup(crate))
    summary_ok = _headings_use_label_helper(summary_exprs, logic, choosers, pretty_helpers)
    rows_ok = _headings_use_label_helper(row_exprs, logic, choosers, pretty_helpers)
    if not choosers and not (summary_ok and rows_ok):
        fail(
            "#114: conversation switcher label must use a helper "
            "(conversationLabel / switcherLabel / platformLabel) that shows "
            "the pretty platform (WhatsApp, Gmail — not raw whatsapp) when "
            "the title is empty or equals personTitle; distinct titles "
            "(groups, mail subjects) still use title"
        )
    if not summary_ok:
        fail(
            "#114: compact switcher summary must call that label helper "
            "(not raw selectedConversationTitle / conv.title as the only heading)"
        )
    if not rows_ok:
        fail(
            "#114: each switcher row heading must call that label helper "
            "(not raw conv.title; subtitle may still show platform + last_at)"
        )
    for blob in choosers.values():
        if _label_helper_falls_back_to_id(blob):
            fail("#114: do not fall back a missing conversation title to a raw id")

    if not _CONV_PLATFORM.search(switcher):
        fail("#114: each conversation in the list must show its platform")
    if not _CONV_LAST_AT.search(switcher):
        fail(
            "#114: each conversation in the list must show last_at "
            "(last activity time of that conversation for this person)"
        )

    if not _CONV_PICK.search(switcher) and not _CONV_PICK.search(detail):
        fail("#114: picking a conversation must select it (click / change / bind)")

    tl_filtered = False
    for m in _PERSON_TIMELINE_CALL.finditer(whole):
        arg = _call_arg(whole, m.end() - 1)
        if re.search(r"conversation(?:Id|_id)\s*:", arg):
            tl_filtered = True
            if not re.search(r"includeGroups", arg):
                fail(
                    "#114: personTimeline must still pass includeGroups "
                    "(All is the current D18 merged stream; groups stay gated)"
                )
            break
    if not tl_filtered:
        fail(
            "#114: picking one conversation must filter the timeline "
            "(personTimeline must pass conversationId / conversation_id; "
            "All passes null so the stream stays D18 merged)"
        )

    api_args = re.search(r"personTimeline\s*:\s*\(\s*args\s*:\s*\{([^}]*)\}", api_src, re.S)
    if not api_args or not re.search(r"conversation(?:Id|_id)\b", api_args.group(1)):
        fail(
            "#114: personTimeline args must include optional conversationId / conversation_id "
            "(All = omitted/null; pick one = that conversation)"
        )

    if not _INCLUDE_GROUPS_LABEL.search(app):
        fail("#114: include groups toggle must remain (groups still require it)")

    list_src = _without_calls(whole, _PERSON_TIMELINE_CALL) + "\n" + switcher
    group_in_list = re.search(
        r"includeGroups[\s\S]{0,400}[\"']group[\"']|[\"']group[\"'][\s\S]{0,400}includeGroups",
        list_src,
    )
    fetched_with_toggle = re.search(
        r"(?:conversations|convos|personConversations|conversationList|convList"
        r"|visibleConversations|filteredConversations)"
        r"\s*=\s*(?:await\s+)?[^=;\n]{0,200}includeGroups",
        list_src,
        re.I,
    )
    if not group_in_list and not fetched_with_toggle:
        fail(
            "#114: groups must require the include-groups toggle to appear in the "
            "conversation list (and in All) — filter kind === \"group\" with includeGroups, "
            "or load the list with includeGroups"
        )
    if re.search(r"kind\s*===?\s*[\"']dm[\"']", list_src) and not re.search(
        r"[\"']group[\"']|email_thread", list_src
    ):
        fail("#114: list dm / group / email_thread, not only DMs")

    visible = _visible_switcher_text(switcher)
    if _CONV_ID_TEXT.search(visible):
        fail(
            "#114: no raw conversation ids or person ids in the conversation switcher "
            "(show title + platform + last_at; data-conversation-id attributes are fine)"
        )
    if (
        _CONV_ID_FALLBACK.search(switcher)
        or _CONV_ID_FALLBACK.search(sel)
        or _CONV_ID_FALLBACK.search(detail)
    ):
        fail("#114: do not fall back a missing conversation title to a raw id")

    markup = app
    script_end = app.rfind("</script>")
    if script_end >= 0:
        markup = app[script_end:]
    if _CONV_CREATE.search(markup) or _CONV_CREATE.search(switcher):
        fail("#114: not in scope — do not add create-conversation chrome")
    if _CONV_MUTE.search(markup) or _CONV_MUTE.search(switcher):
        fail("#114: not in scope — do not add mute-conversation chrome")
    if _CONV_PIN.search(markup) or _CONV_PIN.search(switcher):
        fail("#114: not in scope — do not add pin-conversation chrome")

    if not re.search(
        r"("
        r"conversation switcher"
        r"|list(?:s|ing)? (?:their |the )?conversations"
        r"|conversations? (?:list|switcher|filter)"
        r")",
        dtxt,
        re.I,
    ):
        fail("#114: docs/user/app.md must describe the conversation switcher")
    if not re.search(
        r"("
        r"\bAll\b.{0,100}(default|merged|D18)"
        r"|(default|merged|D18).{0,100}\bAll\b"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail("#114: docs/user/app.md must say All is the default (merged D18 stream)")
    if not re.search(
        r"("
        r"filter(?:s|ed|ing)? (?:the )?timeline"
        r"|timeline.{0,60}filter"
        r"|picking (?:a |one )?conversation"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail("#114: docs/user/app.md must say picking a conversation filters the timeline")
    if not re.search(
        r"("
        r"include groups?.{0,160}conversation"
        r"|conversation.{0,160}include groups?"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#114: docs/user/app.md must say groups still need include-groups "
            "to appear in the conversation list (and in All)"
        )

    # Dogfood: reading a chat must not be buried under identity admin + a second list.
    panes = _person_pane_markups(crate)
    pane = "\n".join(panes) if panes else detail
    merge_at = _MERGE_CTRL.search(pane)
    unlink_at = _UNLINK_CTRL.search(pane)
    groups_at = _groups_ctrl_pos(pane)
    if not merge_at:
        fail(
            "#114: Merge must remain in the person chrome "
            "(hidden until the person name is clicked; do not remove it)"
        )
    if groups_at < 0:
        fail(
            "#114: include groups toggle must remain in the person chrome "
            "(hidden until the person name is clicked; groups still need it)"
        )
    if not unlink_at:
        fail(
            "#114: unlink must remain in the person chrome "
            "(hidden until the person name is clicked; do not remove it)"
        )

    chrome_sites = (
        ("Merge", merge_at.start()),
        ("include groups", groups_at),
        ("unlink", unlink_at.start()),
    )
    for label, pos in chrome_sites:
        if not _chrome_hidden_by_default(pane, pos):
            fail(
                f"#114: {label} must not show until the user opens identity chrome "
                "(default: behind {{#if …}} / hidden / <details> closed — "
                "not sitting above the timeline after selecting a person; "
                "{{#if selectedId}} alone is not a click-to-open gate)"
            )

    flags, title_in_summary = _identity_title_toggle(pane, whole)
    if not flags and not title_in_summary:
        fail(
            "#114: clicking the person title (h1 / personTitle / a button wrapping "
            "the name) must toggle identity chrome (Merge, include groups, unlink)"
        )
    if flags and any(_flag_default_open(logic, name) for name in flags):
        fail(
            "#114: identity chrome must start closed "
            "(toggle state must default false / closed, not true)"
        )
    for label, pos in chrome_sites:
        if not _chrome_toggled_by_title(pane, pos, flags, title_in_summary):
            fail(
                f"#114: clicking the person title must toggle {label} "
                "(same {{#if}} flag, <details> summary, or hidden binding — "
                "not a separate always-visible control)"
            )

    if flags:
        buried = False
        for rx in (_CONV_SWITCHER_HOOK, _CONV_SELECT, _CONV_EACH):
            hit = rx.search(pane)
            if not hit:
                continue
            stack = _template_stack(pane, hit.start())
            if any(kind == "if" and _cond_uses_flag(a, flags) for kind, a, _b in stack):
                buried = True
                break
        if buried:
            fail(
                "#114: conversation switcher must stay in the header next to the "
                "person name (not inside the identity chrome that opens on click)"
            )

    if _always_expanded_conversation_list(crate, logic):
        fail(
            "#114: conversation switcher must be compact in the header "
            "(a <select>, <details>, or a single closed control) — "
            "not a second always-expanded full-width {#each conversations} "
            "list sitting above the bubbles (data-conversation-switcher can stay; "
            "title + platform + last_at still belong inside the compact control)"
        )

    people_src = "\n".join(
        p.read_text() for p in _web_sources(crate) if p.suffix == ".svelte"
    )
    if not re.search(r"\{#each\s+filtered\b", people_src) and not re.search(
        r"id=[\"']person-filter[\"']", people_src
    ):
        fail("#114: people sidebar must stay (do not hide the people list)")
    if _people_list_hidden_on_select(crate):
        fail(
            "#114: people sidebar must stay — do not hide the people list when a "
            "person is selected (no Back-that-hides-the-list in this issue)"
        )

    if not re.search(
        r"("
        r"compact (conversation )?(switcher|control)"
        r"|(conversation )?(switcher|control).{0,80}compact"
        r"|not a second .{0,60}(list|switcher)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#114: docs/user/app.md must say the conversation switcher is a "
            "compact header control (not a second list above the bubbles)"
        )
    if not re.search(
        r"("
        r"(click(?:s|ing)?|tap(?:s|ping)?) (the )?(person )?(name|title)"
        r".{0,160}(Merge|include groups|unlink|identity)"
        r"|(Merge|include groups|unlink|identity chrome)"
        r".{0,160}(click(?:s|ing)?|hidden until|until you click)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#114: docs/user/app.md must say identity chrome "
            "(Merge, include groups, unlink) is hidden until the person name is clicked"
        )

    # Dogfood: sticky .day-heading must not cover All or the open panel.
    stacked, day_z, chrome_z, chrome_bg = _switcher_above_day_heading(crate)
    if not stacked:
        if chrome_z is None or chrome_z <= day_z:
            fail(
                "#114: conversation switcher (data-conversation-switcher / its "
                "summary or panel) or the person-pane header that contains it "
                f"must stack above .day-heading (higher z-index than {day_z}, "
                "and a background so the date cannot show through) — "
                "fail if the switcher/header z-index is missing or "
                f"≤ the day-heading z-index ({day_z})"
            )
        if not chrome_bg:
            fail(
                "#114: conversation switcher / person-pane header must have a "
                "background so the sticky .day-heading date cannot show through "
                "All or the open panel"
            )
        fail(
            "#114: conversation switcher / person-pane header must stack above "
            f".day-heading (z-index > {day_z} and a background; the date must "
            "not cover All or the dropdown)"
        )
