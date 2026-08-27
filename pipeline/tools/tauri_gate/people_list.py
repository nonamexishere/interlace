"""People list / identity / human-time chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.people_filter import *
from tauri_gate.people_time import *


def assert_people_filter_identity(crate: Path) -> None:
    """#138: people `/` filter matches linked identity values, not only display_name.

    Static: filter expression (or its helpers) must read identity material from
    the loaded person row (identity_values / filter_haystack / p.identities).
    Display-name-only matching is a fail. Still client-side on the list.
    """
    app = _web_logic(crate)
    logic = _web_logic(crate)
    src = _without_comments(app + "\n" + logic)

    if "person-filter" not in src:
        fail("#138: people sidebar must keep id=person-filter")
    if not _PEOPLE_EACH.search(app):
        fail("#138: people list must still {#each filtered …} as person rows")

    window = _people_filter_window(src)
    if not window.strip():
        fail("#138: people sidebar `filtered` list derivation missing")

    has_identity = bool(_PEOPLE_FILTER_IDENTITY_TOKENS.search(window)) or bool(
        _PEOPLE_FILTER_IDENTITIES_FIELD.search(window)
    )
    if not has_identity:
        fail(
            "#138: people `/` filter must match linked identity values "
            "(identity_values / filter_haystack / p.identities on the loaded list), "
            "not only display_name"
        )
    if "display_name" not in window and "displayName" not in window:
        fail("#138: people filter must still match display_name")


def assert_people_list_lock(crate: Path) -> None:
    """#265: Review / Confirm / Undo stay callable while people is filling.

    Static: `people` must not hold `with_arch` around the entire heavy
    `person_list`, or the UI first-paints without awaiting the full list
    before Review / undo. Do not `take()` the Archive (import pattern).
    Keep #138 identity haystack and #221 void onChanged / close-first.
    Not a wall-clock “minutes” bound. Do not rewrite #203 / #110 / #221.

    #265 follow-up: refreshPeople increments peopleGen and discards stale
    api.people() replies; snapshot is read-only + query_only; list +
    attach_identity_values share one BEGIN / unchecked_transaction;
    people() comment is not the three-line history.
    """
    rust_path = crate / "src" / "main.rs"
    app_path = crate / "web" / "App.svelte"
    review_path = crate / "web" / "lib" / "ReviewPane.svelte"
    confirm_path = crate / "web" / "lib" / "ConfirmDialog.svelte"
    rust = rust_path.read_text() if rust_path.is_file() else ""
    app = _web_logic(crate) if app_path.is_file() else ""
    logic = _web_logic(crate)
    review_src = review_path.read_text() if review_path.is_file() else ""
    confirm_src = confirm_path.read_text() if confirm_path.is_file() else ""

    people_body = _people_rust_cmd_body(rust)
    if not people_body.strip():
        fail("#265: people command required (Tauri IPC)")

    if _people_cmd_takes_archive(rust, people_body):
        fail(
            "#265: people must not take() the Archive out of the mutex "
            "(Review / Confirm / Undo would see no archive — that is the import pattern)"
        )

    holds_heavy = _people_with_arch_wraps_heavy(rust, people_body)
    incremental = _people_load_incremental(app, logic)
    if holds_heavy and not incremental:
        fail(
            "#265: people must not hold with_arch around the entire person_list, "
            "or people load must first-paint without awaiting the full list "
            "before Review / undo"
        )

    if _review_nav_disabled_while_people_loading(app):
        fail(
            "#265: Review tab must stay clickable while people is filling "
            "(do not disable Review on peopleLoading)"
        )

    review_clean = _without_comments(review_src)
    if _PEOPLE_AWAIT_ONCHANGED.search(review_clean):
        fail(
            "#265: ReviewPane must not await onChanged() "
            "(keep #221 — People refresh must not block Accept / Reject / Undo)"
        )
    if _PEOPLE_AWAIT_API_PEOPLE.search(review_clean):
        fail(
            "#265: Review / undo must not await api.people() "
            "(keep #221 — Review stays callable while people is filling)"
        )

    if confirm_src:
        confirm_clean = _without_comments(confirm_src)
        go_body = _ts_fn_body(confirm_clean, "go") or _function_body(confirm_clean, "go")
        if go_body:
            await_onconfirm = re.search(r"await\s+onconfirm\s*\(", go_body)
            if await_onconfirm:
                close_open = re.search(r"\bopen\s*=\s*false\b", go_body)
                if not close_open or close_open.start() > await_onconfirm.start():
                    fail(
                        "#265: ConfirmDialog go() must set open = false before "
                        "await onconfirm() (keep #221 close-first)"
                    )

    src = _without_comments(app + "\n" + logic)
    window = _people_filter_window(src)
    has_identity = bool(_PEOPLE_FILTER_IDENTITY_TOKENS.search(window)) or bool(
        _PEOPLE_FILTER_IDENTITIES_FIELD.search(window)
    )
    if not has_identity:
        fail(
            "#265: people `/` filter must still match linked identity values "
            "(identity_values / filter_haystack / p.identities on the loaded list)"
        )

    # Follow-up: stale people reply + read-only snapshot + one-transaction list.
    refresh = _people_refresh_body(src)
    if not refresh.strip():
        fail("#265: refreshPeople required (must discard stale api.people() replies)")
    tok = _people_list_gen(refresh)
    for m in _PEOPLE_ASSIGN_AWAIT.finditer(refresh):
        if not tok or not _assignment_gen_guarded(
            refresh, m.start(), tok[0], tok[1]
        ):
            fail(
                "#265: refreshPeople must not assign unguarded "
                "people = await api.people() "
                "(increment peopleGen and keep the assignment only when gen is current)"
            )
    if not tok:
        fail(
            "#265: refreshPeople must increment a generation "
            "(peopleGen; tlGen only if it is also the people-list gen)"
        )
    if not _PEOPLE_LOADING_FALSE.search(refresh):
        fail(
            "#265: refreshPeople must clear peopleLoading only when the "
            "generation is current"
        )
    bad = _unguarded_post_ipc_writes(
        refresh, tok[0], tok[1], ("people", "peopleLoading"), ("api.people",)
    )
    if bad:
        fail(
            "#265: refreshPeople must not assign people / clear peopleLoading "
            "when the generation is stale"
        )

    snap = _people_expand_rust_calls(rust, people_body)
    if _PEOPLE_BARE_OPEN.search(snap):
        fail(
            "#265: people snapshot must not use bare Connection::open "
            "(open read-only with SQLITE_OPEN_READ_ONLY / OpenFlags + READ_ONLY)"
        )
    readonly = bool(_PEOPLE_OPEN_READONLY.search(snap)) or (
        bool(_PEOPLE_OPEN_FLAGS.search(snap)) and bool(_PEOPLE_READ_ONLY.search(snap))
    )
    if not readonly or not _PEOPLE_QUERY_ONLY.search(snap):
        fail(
            "#265: people snapshot must open read-only "
            "(SQLITE_OPEN_READ_ONLY / OpenFlags + READ_ONLY) and set query_only"
        )

    people_rs = (
        repo_root() / "crates" / "interlace-core" / "src" / "people.rs"
    )
    core_people = people_rs.read_text() if people_rs.is_file() else ""
    list_blob = _people_list_on_blob(core_people)
    if not list_blob.strip():
        fail(
            "#265: person_list_on / person_list_on_with_groups required "
            "(list + attach_identity_values must share one snapshot)"
        )
    if not _PEOPLE_SNAPSHOT_TX.search(list_blob):
        fail(
            "#265: person_list_on / person_list_on_with_groups must use "
            "unchecked_transaction or BEGIN so list + attach_identity_values "
            "are one snapshot"
        )

    comment = _people_cmd_comment(rust)
    if (
        _PEOPLE_COMMENT_ISSUE.search(comment)
        and _PEOPLE_COMMENT_FLOCK.search(comment)
        and _PEOPLE_COMMENT_TAKE.search(comment)
    ):
        fail(
            "#265: people() comment must not be the three-line #265 / "
            "Exclusive flock / take() history (one-line why is OK)"
        )


def assert_people_sidebar_no_x_scroll(crate: Path) -> None:
    """#159: people sidebar must not pan sideways; vertical scroll only.

    Long names and activity previews stay readable via truncate / min-w-0 /
    minmax(0, …) — they must not push the left column wider. People list stays
    when a chat is open. No raw person ids in list labels. Not #114 switcher.
    """
    app = _web_logic(crate)
    people_src = "\n".join(
        p.read_text() for p in _web_sources(crate) if p.suffix == ".svelte"
    )
    regions = _people_sidebar_regions(crate)
    region_blob = "\n".join(regions) if regions else ""
    scroll_defaults = _scroll_area_source(crate)

    # 1) People list still exists and is not hidden when a person is selected.
    if not _PEOPLE_EACH.search(people_src) and not re.search(
        r"id=[\"']person-filter[\"']", people_src
    ):
        fail(
            "#159: people sidebar must still list people "
            "({#each filtered …} and/or person-filter) — do not remove the left column"
        )
    if _people_list_hidden_on_select(crate):
        fail(
            "#159: people sidebar must stay visible when a person is selected "
            "(do not hide the people list when a chat is open — that is not this issue)"
        )

    # 2) Scroll container: overflow-x hidden; overflow-y auto/scroll.
    if not regions and not (
        _OVERFLOW_X_HIDDEN.search(scroll_defaults)
        and _OVERFLOW_Y_SCROLL.search(scroll_defaults)
        and _SCROLL_AREA_TAG.search(app)
    ):
        fail(
            "#159: people sidebar scroll region not found "
            "({#each filtered}, person-filter, or data-people-sidebar)"
        )

    overflow_ok = False
    if regions:
        overflow_ok = any(_region_overflow_ok(r, scroll_defaults) for r in regions)
    if not overflow_ok:
        # Shared ScrollArea defaults alone are enough when people pane uses it.
        if (
            _SCROLL_AREA_TAG.search(app)
            and _OVERFLOW_X_HIDDEN.search(scroll_defaults)
            and _OVERFLOW_Y_SCROLL.search(scroll_defaults)
            and not _OVERFLOW_X_VISIBLE.search(region_blob)
        ):
            overflow_ok = True
    if not overflow_ok:
        fail(
            "#159: people pane must hide horizontal overflow "
            "(overflow-x: hidden / overflow-x-hidden on the people ScrollArea "
            "or shared ScrollArea defaults) while still allowing vertical scroll "
            "(overflow-y: auto|scroll)"
        )
    if _OVERFLOW_X_VISIBLE.search(region_blob) and not _OVERFLOW_X_HIDDEN.search(
        region_blob + "\n" + scroll_defaults
    ):
        fail(
            "#159: people pane must not enable horizontal pan "
            "(overflow-x auto/scroll/visible without overflow-x hidden)"
        )

    # 3) Long names / previews do not expand the column indefinitely.
    each_blocks = []
    for p in _web_sources(crate):
        if p.suffix != ".svelte" or p.name in _PERSON_PANE_SKIP:
            continue
        text = p.read_text()
        markup = _svelte_markup(text)
        block = _people_each_block(markup)
        if block:
            each_blocks.append(block)
    if not each_blocks:
        fail("#159: people list must still {#each filtered …} as person rows")
    people_rows = "\n".join(each_blocks)
    if not _row_clips_long_text(people_rows):
        fail(
            "#159: long person names and activity previews must truncate "
            "(or ellipsis / line-clamp / overflow-hidden) so they stay readable "
            "without pushing the people column wider"
        )
    # Column track or row ancestors must be able to shrink (min-w-0 / minmax(0, …)).
    column_blob = region_blob + "\n" + app
    if not _MIN_W0.search(column_blob) and not _MIN_W0.search(people_rows):
        fail(
            "#159: people column / row content must allow shrink "
            "(min-w-0 or grid minmax(0, …)) so truncate can take effect"
        )

    # 4) No raw person-id copy in people list labels (undo event ids elsewhere ok).
    visible_rows = _strip_tag_attrs(people_rows)
    visible_rows = re.sub(r"\{[#/:@].*?\}", "", visible_rows, flags=re.S)
    if _PEOPLE_ID_VISIBLE.search(visible_rows):
        fail(
            "#159: no raw person ids in the people list labels "
            "(show display name / preview; data-id attributes are fine)"
        )
    if _PEOPLE_ID_FALLBACK.search(people_rows):
        fail("#159: do not fall back a missing person name to a raw id")


def assert_human_time_people(crate: Path) -> None:
    """#184: people list / VoiceOver show a short time, not raw ISO last_activity_at.

    Visible sidebar options and the name VoiceOver reads are name + a short
    time (e.g. 11 Aug 14:32), not 2024-08-11T14:32:00Z. Archive / api.ts JSON
    still carries ISO last_activity_at. Do not t() bodies. Not a date-picker
    locale pack. Do not require “yesterday” in App.svelte (#112).
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#184: App.svelte required (people list last_activity_at display)")
    app = _web_logic(crate)
    logic = _web_logic(crate)
    chrome, people_each = _people_list_a11y_surfaces(crate)
    if not people_each.strip():
        markup = _strip_html_comments(_svelte_markup(app))
        people_each = _people_each_block(markup)
        chrome = markup
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    if not _PEOPLE_EACH.search(app) and not _PEOPLE_EACH.search(chrome):
        fail("#184: people sidebar must still {#each filtered …} as person options")
    if not people_each.strip():
        fail("#184: people list {#each filtered} body missing")

    # 1) Still show last_activity_at — as a short time, not dropped.
    if not re.search(r"\blast_activity_at\b", people_each):
        fail(
            "#184: people list must still show last_activity_at "
            "(as a short time, not drop the activity timestamp)"
        )

    # 2) Visible option text is not the raw ISO T…Z string.
    raw_dump = any(_interp_dumps_iso_activity(expr) for expr in _svelte_interpolations(people_each))
    if raw_dump:
        fail(
            "#184: people list must not display raw ISO last_activity_at "
            "(T…Z / 2024-08-11T14:32:00Z); use a short time (e.g. 11 Aug 14:32)"
        )

    # 3) A formatter exists (month + hour:minute; UTC / ISO prefix). Helper
    #    may live in another web/ file. Do not require “yesterday” in App.svelte.
    if not _short_time_formatter_ok(logic):
        fail(
            "#184: format last_activity_at as a short time "
            "(e.g. 11 Aug 14:32) — month + hour:minute, not YYYY-MM-DDTHH:MM:SSZ"
        )
    if not _people_uses_short_time(people_each):
        fail(
            "#184: people options must pass last_activity_at through a short-time "
            "helper (e.g. humanTime(p.last_activity_at)), not interpolate the ISO"
        )

    # 4) VoiceOver: name + short time, not 2024-08-11T14:32:00Z.
    if not re.search(r"\b(?:display_name|displayName|personLabel|personName)\b", people_each):
        fail(
            "#184: VoiceOver on a person must hear the name plus a short time "
            "(keep display_name / personLabel on the option)"
        )
    labels = _attr_brace_values(people_each, "aria-label")
    if labels:
        for lab in labels:
            has_name = bool(
                re.search(r"display_name|displayName|personLabel|personName", lab)
            )
            wrapped = bool(
                re.search(r"[A-Za-z_]\w*\s*\([^)]*\blast_activity_at\b", lab)
                or _HUMAN_TIME_CALL.search(lab)
            )
            raw_in_label = bool(re.search(r"\blast_activity_at\b", lab)) and not wrapped
            if not has_name:
                fail(
                    "#184: VoiceOver aria-label must include the person name "
                    "plus a short time"
                )
            if raw_in_label:
                fail(
                    "#184: VoiceOver must not read raw ISO last_activity_at "
                    "(2024-08-11T14:32:00Z) — aria-label is name + short time"
                )
            if not wrapped:
                fail(
                    "#184: VoiceOver aria-label must be the name plus a short time "
                    "(not 2024-08-11T14:32:00Z)"
                )

    # 5) Archive / API JSON types still carry ISO last_activity_at.
    api_path = crate / "web" / "lib" / "api.ts"
    if not api_path.is_file():
        fail("#184: web/lib/api.ts required (Person.last_activity_at stays ISO)")
    api = api_path.read_text()
    if not re.search(
        r"export type Person\s*=\s*\{[^}]*\blast_activity_at\??\s*:\s*string",
        api,
        re.S,
    ):
        fail(
            "#184: API Person JSON must still carry ISO last_activity_at "
            "(do not strip the field from api.ts)"
        )

    # 6) Do not t() message bodies or previews.
    helpers = _chrome_helper_names(logic)
    body_blob = logic + "\n" + app
    if _chrome_helper_on_body(body_blob, helpers) or _BODY_T_CALL.search(body_blob):
        fail("#184: do not t() message bodies or previews (t(body_text) / t(preview))")

    # 7) Not a date-picker locale pack.
    if _DATE_PICKER.search(logic) or _DATE_PICKER.search(app):
        fail("#184: not a date-picker locale pack")

    # 8) Docs: people list / VoiceOver use a short time, not the raw ISO.
    if not dtxt.strip():
        fail("#184: docs/user/app.md required (people list / VoiceOver short time)")
    if not re.search(
        r"("
        r"(?:people list|VoiceOver).{0,220}short(?:er)?(?: human)? time"
        r"|short(?:er)?(?: human)? time.{0,220}(?:people list|VoiceOver)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#184: docs/user/app.md must say people list / VoiceOver use a "
            "short time, not the raw ISO"
        )
    if not re.search(
        r"("
        r"not (?:the |a )?raw ISO"
        r"|not (?:the |a )?raw.{0,24}ISO"
        r"|not .{0,40}2024-08-11T"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#184: docs/user/app.md must say people list / VoiceOver time is "
            "not the raw ISO"
        )
