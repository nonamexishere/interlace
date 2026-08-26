"""People list / identity / human-time chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _BODY_T_CALL,
    _DATA_PEOPLE_SIDEBAR,
    _PEOPLE_AWAIT_REFRESH,
    _PERSON_PANE_SKIP,
    _call_arg,
    _function_body,
    _match_closer,
    _rust_fn_body,
    _rust_function_body,
    _strip_html_comments,
    _svelte_interpolations,
    _svelte_markup,
    _ts_fn_body,
    _web_logic,
    _web_sources,
    _without_comments,
)

from tauri_gate.a11y import (
    _people_each_block,
    _people_list_a11y_surfaces,
)

from tauri_gate.import_boot import (
    _HUMAN_TIME_HELPERS,
    _people_list_gen,
    _unguarded_post_ipc_writes,
)

from tauri_gate.media_linkify import (
    _MIN_W0,
    _OVERFLOW_X_HIDDEN,
)

from tauri_gate.people_switcher_label import (
    _people_list_hidden_on_select,
    _strip_tag_attrs,
)

from tauri_gate.status_toasts import (
    _PEOPLE_EACH,
    _assignment_gen_guarded,
    _chrome_helper_names,
    _chrome_helper_on_body,
    _people_sidebar_regions,
    _short_time_formatter_ok,
)



_OVERFLOW_Y_SCROLL = re.compile(
    r"("
    r"overflow-y-(?:auto|scroll)"
    r"|overflow-y\s*:\s*(?:auto|scroll)"
    r"|overflow\s*:\s*auto\b"
    r"|overflow\s*:\s*scroll\b"
    r")",
    re.I,
)
_OVERFLOW_X_VISIBLE = re.compile(
    r"("
    r"overflow-x-(?:auto|scroll|visible)"
    r"|overflow-x\s*:\s*(?:auto|scroll|visible)"
    r")",
    re.I,
)
_TRUNCATE_TOKENS = re.compile(
    r"("
    r"\btruncate\b"
    r"|text-ellipsis"
    r"|text-overflow\s*:\s*ellipsis"
    r"|line-clamp-\d+"
    r"|overflow-hidden"
    r")",
    re.I,
)
_PEOPLE_NAME = re.compile(r"\b(?:display_name|displayName|personName|name)\b")
_PEOPLE_PREVIEW = re.compile(
    r"\b(?:last_activity_at|lastActivityAt|preview|last_at|status)\b"
)
_PEOPLE_ID_VISIBLE = re.compile(
    r"\{[^}]{0,60}(?:\bp\.id\b|\bperson\.id\b|\bfiltered\b[^}]{0,20}\.id)[^}]{0,20}\}"
)
_PEOPLE_ID_FALLBACK = re.compile(
    r"(?:display_name|displayName|name)\s*\|\|\s*[^\n;]{0,60}"
    r"(?:\bp\.id\b|\bperson\.id\b|\.id\b)"
)
_SCROLL_AREA_TAG = re.compile(r"<ScrollArea\b([^>]*)>", re.I | re.S)


def _scroll_area_source(crate: Path) -> str:
    p = crate / "web" / "lib" / "components" / "ui" / "scroll-area" / "scroll-area.svelte"
    return p.read_text() if p.is_file() else ""


def _region_overflow_ok(region: str, scroll_defaults: str) -> bool:
    """True if this people pane (or shared ScrollArea defaults) hide x-scroll."""
    # Explicit overflow-x auto/scroll/visible on the people pane is a fail signal
    # unless a more specific hidden also applies on the same ScrollArea.
    for m in _SCROLL_AREA_TAG.finditer(region):
        attrs = m.group(1)
        if _OVERFLOW_X_VISIBLE.search(attrs) and not _OVERFLOW_X_HIDDEN.search(attrs):
            return False
        if _OVERFLOW_X_HIDDEN.search(attrs) and _OVERFLOW_Y_SCROLL.search(attrs):
            return True
        if _OVERFLOW_X_HIDDEN.search(attrs) and _OVERFLOW_Y_SCROLL.search(scroll_defaults):
            return True
        # ScrollArea with people sidebar + defaults that clip x / allow y.
        if (
            _DATA_PEOPLE_SIDEBAR.search(attrs)
            or "border-r" in attrs
            or "min-w-0" in attrs
        ) and _OVERFLOW_X_HIDDEN.search(scroll_defaults) and _OVERFLOW_Y_SCROLL.search(
            scroll_defaults
        ):
            return True
    if _OVERFLOW_X_HIDDEN.search(region) and _OVERFLOW_Y_SCROLL.search(region):
        return True
    if _OVERFLOW_X_HIDDEN.search(scroll_defaults) and _OVERFLOW_Y_SCROLL.search(
        scroll_defaults
    ):
        # Shared ScrollArea defaults apply when the people pane uses ScrollArea.
        if _SCROLL_AREA_TAG.search(region) or "ScrollArea" in region:
            return True
    return False


def _row_clips_long_text(block: str) -> bool:
    """Names / previews must truncate or otherwise not expand the column."""
    if not block:
        return False
    has_name = bool(_PEOPLE_NAME.search(block))
    has_preview = bool(_PEOPLE_PREVIEW.search(block))
    if not has_name:
        return False
    tokens = _TRUNCATE_TOKENS.findall(block)
    if not tokens:
        return False
    # Name + activity preview both shown → both must clip (two truncate sites,
    # or one shared overflow-hidden/line-clamp wrapper plus another clip).
    if has_preview and len(tokens) < 2:
        return False
    return True


# #138 — people `/` filter: identity values on the loaded list, not display_name only.
_PEOPLE_FILTER_IDENTITY_TOKENS = re.compile(
    r"\b(?:"
    r"identity_values|identityValues|"
    r"filter_haystack|filterHaystack|"
    r"value_normalized|valueNormalized"
    r")\b"
)
# `identities` alone is too broad (person detail chrome). Require a person-field
# access (p.identities / person.identities) or the tokens above.
_PEOPLE_FILTER_IDENTITIES_FIELD = re.compile(
    r"(?:\bp|person|row)\s*\??\.\s*identities\b"
    r"|\bidentities\s*\?\?|\bidentities\s*\|\|"
    r"|\b\.\.\.\s*(?:\bp|person)\s*\??\.\s*identities\b"
)
_PEOPLE_FILTER_SKIP_CALLS = frozenset(
    {
        "if",
        "for",
        "while",
        "switch",
        "catch",
        "function",
        "return",
        "typeof",
        "new",
        "await",
        "void",
        "toLowerCase",
        "toUpperCase",
        "trim",
        "includes",
        "filter",
        "map",
        "join",
        "concat",
        "some",
        "every",
        "find",
        "String",
        "Boolean",
        "Number",
        "Array",
        "Math",
        "parseInt",
        "console",
    }
)


def _people_filter_window(src: str) -> str:
    """Logic for the people sidebar filter (`filtered` derived + named helpers)."""
    m = re.search(
        r"(?:const|let)\s+filtered\s*=\s*\$derived\s*\(",
        src,
    )
    if not m:
        m = re.search(r"(?:const|let)\s+filtered\s*=", src)
    if not m:
        return ""
    window = src[m.start() : m.start() + 1600]
    # Expand small named helpers referenced from the filter expression.
    for call in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", window):
        name = call.group(1)
        if name in _PEOPLE_FILTER_SKIP_CALLS:
            continue
        body = _function_body(src, name)
        if body and len(body) < 4000:
            window += "\n" + body
    return window


def assert_people_filter_identity(crate: Path) -> None:
    """#138: people `/` filter matches linked identity values, not only display_name.

    Static: filter expression (or its helpers) must read identity material from
    the loaded person row (identity_values / filter_haystack / p.identities).
    Display-name-only matching is a fail. Still client-side on the list.
    """
    app = (crate / "web" / "App.svelte").read_text()
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


# #265 — people list must not hold the archive mutex for the whole heavy scan.
_PEOPLE_LIST_HEAVY = re.compile(
    r"\bperson_list(?:_with_groups|_on|_on_conn|_from_conn|_snapshot)?\s*\("
)
_PEOPLE_WITH_ARCH = re.compile(r"\bwith_arch(?:_mut)?\s*\(")
_PEOPLE_TAKE_ARCH = re.compile(r"\.take\s*\(")
_PEOPLE_AWAIT_API_PEOPLE = re.compile(r"await\s+api\s*\.\s*people\s*\(")
_PEOPLE_AWAIT_ONCHANGED = re.compile(r"await\s+onChanged\s*\(")
_PEOPLE_PAGE_API = re.compile(r"api\s*\.\s*people(?:Page|Roster|Chunk|More)\s*\(")
_PEOPLE_VOID_API = re.compile(r"void\s+api\s*\.\s*people\s*\(")
_PEOPLE_THEN_API = re.compile(r"api\s*\.\s*people\s*\([^)]*\)\s*\.then\s*\(")
_PEOPLE_FIRST_PAINT_ASSIGN = re.compile(
    r"\bpeople\s*=\s*await\s+api\s*\.\s*people(?:Page|Roster|Chunk|More)\s*\("
)
_PEOPLE_FIRST_PAINT_PUSH = re.compile(r"\bpeople\s*\.(?:push|unshift|splice|concat)\s*\(")
_PEOPLE_REVIEW_DISABLED_LOADING = re.compile(
    r"disabled\s*=\s*\{[^}]*peopleLoading",
    re.I,
)
_PEOPLE_ASSIGN_AWAIT = re.compile(
    r"\bpeople\s*=\s*await\s+api\s*\.\s*people\s*\("
)
_PEOPLE_LOADING_FALSE = re.compile(r"\bpeopleLoading\s*=\s*false\b")
_PEOPLE_BARE_OPEN = re.compile(r"(?:rusqlite::)?Connection::open\s*\(")
_PEOPLE_OPEN_READONLY = re.compile(r"\bSQLITE_OPEN_READ_ONLY\b")
_PEOPLE_OPEN_FLAGS = re.compile(r"\bOpenFlags\b")
_PEOPLE_READ_ONLY = re.compile(r"\bREAD_ONLY\b")
_PEOPLE_QUERY_ONLY = re.compile(r"\bquery_only\b", re.I)
_PEOPLE_SNAPSHOT_TX = re.compile(r"unchecked_transaction|\bBEGIN\b", re.I)
_PEOPLE_COMMENT_ISSUE = re.compile(r"#265")
_PEOPLE_COMMENT_FLOCK = re.compile(r"Exclusive flock stays", re.I)
_PEOPLE_COMMENT_TAKE = re.compile(
    r"Do not take\s*\(\s*\)\s*the Archive|import pattern", re.I
)


def _people_rust_cmd_body(rust: str) -> str:
    return _rust_function_body(rust, "people") or _rust_fn_body(rust, "people")


def _people_expand_rust_calls(rust: str, blob: str, depth: int = 2) -> str:
    parts = [blob]
    seen = {"people", "with_arch", "with_arch_mut"}
    skip = {
        "Ok",
        "Err",
        "Some",
        "None",
        "vec",
        "format",
        "serde_json",
        "to_value",
        "json",
        "map_err",
        "clone",
        "lock",
        "as_ref",
        "as_mut",
        "expect",
        "unwrap",
        "from",
        "join",
        "open",
        "if",
        "for",
        "while",
        "match",
        "return",
        "person_list",
        "person_list_with_groups",
        "person_list_on",
    }

    def walk(src: str, left: int) -> None:
        if left <= 0:
            return
        for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", src):
            name = m.group(1)
            if name in seen or name in skip:
                continue
            seen.add(name)
            inner = _rust_function_body(rust, name) or _rust_fn_body(rust, name)
            if not inner:
                continue
            parts.append(inner)
            walk(inner, left - 1)

    walk(blob, depth)
    return "\n".join(parts)


def _people_with_arch_wraps_heavy(rust: str, body: str) -> bool:
    """True if a with_arch / with_arch_mut closure (or its callees) runs person_list."""
    for m in _PEOPLE_WITH_ARCH.finditer(body):
        args = _call_arg(body, m.end() - 1)
        if not args:
            continue
        expanded = _people_expand_rust_calls(rust, args)
        if _PEOPLE_LIST_HEAVY.search(expanded):
            return True
    return False


def _people_cmd_takes_archive(rust: str, body: str) -> bool:
    expanded = _people_expand_rust_calls(rust, body)
    return bool(_PEOPLE_TAKE_ARCH.search(expanded))


def _refresh_first_paints_before_full_people(refresh: str) -> bool:
    """True if refreshPeople paints a page / fires-and-forgets before the full list."""
    full = _PEOPLE_AWAIT_API_PEOPLE.search(refresh)
    if not full:
        if _PEOPLE_VOID_API.search(refresh) or _PEOPLE_THEN_API.search(refresh):
            return True
        if _PEOPLE_PAGE_API.search(refresh):
            return True
        return False
    before = refresh[: full.start()]
    if _PEOPLE_FIRST_PAINT_ASSIGN.search(before):
        return True
    if _PEOPLE_FIRST_PAINT_PUSH.search(before):
        return True
    return False


def _apply_status_releases_before_people(apply_st: str) -> bool:
    if _PEOPLE_AWAIT_REFRESH.search(apply_st):
        return False
    return bool(re.search(r"(?:void\s+)?refreshPeople\s*\(", apply_st))


def _people_load_incremental(app: str, logic: str) -> bool:
    src = _without_comments(app + "\n" + logic)
    refresh = _function_body(src, "refreshPeople") or _ts_fn_body(src, "refreshPeople")
    apply_st = _function_body(src, "applyStatus") or _ts_fn_body(src, "applyStatus")
    if refresh and _refresh_first_paints_before_full_people(refresh):
        return True
    if apply_st and _apply_status_releases_before_people(apply_st):
        return True
    return False


def _review_nav_disabled_while_people_loading(app: str) -> bool:
    for m in re.finditer(r"<Button\b[^>]*>", app, re.S):
        tag = m.group(0)
        if "review" not in tag.lower():
            continue
        if _PEOPLE_REVIEW_DISABLED_LOADING.search(tag):
            return True
    return False


def _people_refresh_body(src: str) -> str:
    return _function_body(src, "refreshPeople") or _ts_fn_body(src, "refreshPeople")


def _people_cmd_comment(rust: str) -> str:
    """Comments on `fn people` (leading body + immediately above the fn)."""
    m = re.search(r"(?:pub\s+)?(?:async\s+)?fn\s+people\s*\(", rust)
    if not m:
        return ""
    kept: list[str] = []
    for line in reversed(rust[: m.start()].splitlines()):
        s = line.strip()
        if s == "":
            if kept:
                break
            continue
        if s.startswith("#["):
            continue
        if s.startswith("//") or s.startswith("///") or s.startswith("/*") or s.startswith("*"):
            kept.append(s)
            continue
        break
    header = list(reversed(kept))
    lead: list[str] = []
    for line in _people_rust_cmd_body(rust).splitlines():
        s = line.strip()
        if s == "":
            if lead:
                break
            continue
        if s.startswith("//") or s.startswith("/*") or s.startswith("*"):
            lead.append(s)
            continue
        break
    return "\n".join(header + lead)


def _people_list_on_blob(core: str) -> str:
    """person_list_on / person_list_on_with_groups (+ one hop, not attach)."""
    parts: list[str] = []
    skip = {"attach_identity_values"}
    seen: set[str] = set()
    for name in ("person_list_on", "person_list_on_with_groups"):
        body = _rust_function_body(core, name) or _rust_fn_body(core, name)
        if not body:
            continue
        parts.append(body)
        seen.add(name)
        for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", body):
            callee = m.group(1)
            if callee in seen or callee in skip:
                continue
            seen.add(callee)
            inner = _rust_function_body(core, callee) or _rust_fn_body(core, callee)
            if inner:
                parts.append(inner)
    return "\n".join(parts)


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
    app = app_path.read_text() if app_path.is_file() else ""
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
    app = (crate / "web" / "App.svelte").read_text()
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
# Selecting / opening a person (existing selectPerson or jump-specific open).
_SELECT_PERSON_CALL = re.compile(
    r"\b(?:"
    r"selectPerson|openPerson|pickPerson|showPerson|loadPerson|"
    r"openPersonAtMessage|selectPersonAtMessage|jumpToPersonMessage"
    r")\s*\(",
    re.I,
)
_HUMAN_TIME_CALL = re.compile(
    r"\b(?:" + "|".join(_HUMAN_TIME_HELPERS) + r")\s*\("
)
_DATE_PICKER = re.compile(
    r"("
    r"\bDatePicker\b"
    r"|date-picker"
    r"|datepicker"
    r"|flatpickr"
    r"|litepicker"
    r"|air-datepicker"
    r"|type\s*=\s*[\"']date[\"']"
    r"|type\s*=\s*[\"']datetime-local[\"']"
    r")",
    re.I,
)


def _interp_dumps_iso_activity(expr: str) -> bool:
    """True if last_activity_at is stringified (raw T…Z), not passed to a formatter."""
    if not re.search(r"\blast_activity_at\b", expr):
        return False
    if re.search(r"[A-Za-z_]\w*\s*\([^)]*\blast_activity_at\b", expr):
        return False
    # Truthiness for a separator (`p.last_activity_at && p.preview ? " · " : ""`).
    if re.search(r"last_activity_at\s*&&", expr) and not re.search(
        r"last_activity_at\s*(?:\?\?|\|\|)", expr
    ):
        return False
    return True


def _attr_brace_values(src: str, attr: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(rf"{re.escape(attr)}\s*=\s*\{{", src, re.I):
        start = m.end() - 1
        end = _match_closer(src, start)
        if end > start:
            out.append(src[start + 1 : end])
    return out


def _people_uses_short_time(people_each: str) -> bool:
    if _HUMAN_TIME_CALL.search(people_each):
        return True
    for expr in _svelte_interpolations(people_each):
        if re.search(r"[A-Za-z_]\w*\s*\([^)]*\blast_activity_at\b", expr):
            return True
    return False


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
    app = app_path.read_text()
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
