"""Additional primitives asserts."""
from __future__ import annotations

from tauri_gate.primitives_lib import *


def assert_loading_skeletons(crate: Path) -> None:
    """#203: quiet muted skeleton on people / timeline / search in-flight.

    Token bars (bg-muted / muted), data-skeleton and/or owned Skeleton.
    Keep #156 boot CSS spinner + “Opening last archive”. Search in-flight
    is not EmptyState “No hits” / “Type a query”. Reduced-motion: static
    bars (existing app.css reduce may count). Not: server %, every
    virtualized row, video splash, skeleton npm/CDN. Docs: quiet muted
    skeleton; boot spinner stays; reduced-motion is static.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#203: App.svelte required (people list + person timeline in-flight)")
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#203: SearchPane.svelte required (search hits in-flight)")
    app = _web_logic(crate)
    search = _search_pane_blob(crate)
    css_path = crate / "web" / "app.css"
    css = css_path.read_text() if css_path.is_file() else ""
    pkg_path = crate / "package.json"
    pkg = pkg_path.read_text() if pkg_path.is_file() else ""

    people_flag, people_branch = _people_inflight_branch(app)
    if not people_branch:
        for region in _people_sidebar_regions(crate):
            flag, block = _people_inflight_branch(region)
            if block:
                people_flag, people_branch = flag, block
                break
    tl_branch = _svelte_if_true_branch(app, "tlLoading")
    search_branch = _svelte_if_true_branch(search, "searching")

    people_names = _owned_skeleton_names(app)
    search_names = _owned_skeleton_names(search)
    # 1) Three surfaces show a muted skeleton while in-flight.
    missing: list[str] = []
    if not _has_skeleton_hook(people_branch, people_names):
        missing.append("people list")
    if not _has_skeleton_hook(tl_branch, people_names):
        missing.append("person timeline")
    if not _has_skeleton_hook(search_branch, search_names):
        missing.append("search hits")
    if missing:
        fail(
            "#203: "
            + ", ".join(missing)
            + " must show a quiet muted skeleton while in-flight "
            "(data-skeleton and/or owned $lib/components/ui/skeleton)"
        )

    owned_files = _skeleton_owned_files(crate)
    skel_chrome = people_branch + "\n" + tl_branch + "\n" + search_branch
    for p in owned_files:
        skel_chrome += "\n" + p.read_text()

    # 2) Token bars — muted, not a raw amber/yellow shimmer.
    if not _SKELETON_MUTED_BAR.search(skel_chrome):
        fail(
            "#203: skeleton bars must use the muted token "
            "(bg-muted / var(--muted)), not a raw hue"
        )
    if _HUE_AMBER.search(skel_chrome) or _HUE_YELLOW.search(skel_chrome):
        fail("#203: skeleton must not use a raw amber/yellow shimmer")
    if _NET_IMG.search(skel_chrome) or _CDN_HINT.search(skel_chrome):
        fail("#203: skeleton must not load a CDN / network shimmer")

    # 3) Keep #156 boot / opening CSS spinner + exact copy. Do not require a skeleton.
    boot = _boot_opening_block(app)
    en_pack = _chrome_en_text(crate)
    if "Opening last archive" not in boot and "Opening last archive" not in app:
        if "Opening last archive" not in en_pack:
            fail(
                "#203: keep the #156 copy substring “Opening last archive” "
                "(do not replace the boot spinner with a skeleton)"
            )
    css_blob = "\n".join(p.read_text() for p in _web_sources(crate) if p.suffix == ".css")
    boot_with_css = boot + "\n" + css_blob
    if boot and not _has_css_spinner(boot) and not (
        (_SPINNER_NAME.search(boot) or re.search(r"animate-spin", boot))
        and _SPIN_ANIM.search(boot_with_css)
    ):
        fail(
            "#203: keep the #156 boot / opening CSS spinner — "
            "do not replace it with a skeleton"
        )

    # 4) Search in-flight is not EmptyState “No hits” / “Type a query”.
    if re.search(r"\bNo hits\b", search_branch):
        fail("#203: search in-flight must not be the EmptyState “No hits”")
    if re.search(r"\bType a query\b", search_branch):
        fail("#203: search in-flight must not be “Type a query” while searching")
    if "No hits" not in search and "No hits" not in en_pack:
        fail("#203: keep EmptyState “No hits” for the empty (not searching) branch")

    # People in-flight is not the #202 empty copy.
    if re.search(r"\bNo people yet\b", people_branch) or re.search(
        r"\bNo match\b", people_branch
    ):
        fail(
            "#203: people list must not show “No people yet” / “No match” while in-flight"
        )
    refresh = _function_body(app, "refreshPeople")
    if people_flag and refresh and not re.search(
        rf"\b{re.escape(people_flag)}\s*=\s*true\b", refresh
    ):
        fail(
            f"#203: refreshPeople must set {people_flag} = true while "
            "api.people() is in flight so the people skeleton can show"
        )

    # 5) prefers-reduced-motion → static bars. Existing app.css reduce may count.
    reduce_css = "\n".join(_css_prefers_reduced_blocks(css + "\n" + css_blob))
    has_skel_anim = bool(
        _SKELETON_ANIM.search(skel_chrome) or re.search(r"animate-pulse", skel_chrome)
    )
    if _SKELETON_JS_SHIMMER.search(skel_chrome) or _SKELETON_SVG_ANIM.search(skel_chrome):
        fail(
            "#203: prefers-reduced-motion: reduce → no animated shimmer on the "
            "skeletons (static bars; no JS / SVG shimmer that bypasses CSS)"
        )
    if has_skel_anim and not _SKELETON_REDUCE_STATIC.search(reduce_css):
        fail(
            "#203: prefers-reduced-motion: reduce → no animated shimmer on the "
            "skeletons (static bars; existing app.css reduce may count if it "
            "kills the CSS animation)"
        )

    # 6) Not in scope: server %, every virtualized row, video splash, npm/CDN kit.
    if _SERVER_PROGRESS.search(skel_chrome):
        fail("#203: not in scope — no percent progress from a server")
    if _SPLASH_VIDEO.search(skel_chrome) or _SPLASH_VIDEO.search(boot):
        fail("#203: not in scope — no video splash")
    if _SKELETON_PKG_203.search(pkg) or _SKELETON_PKG_202.search(pkg):
        fail("#203: not in scope — do not add a skeleton npm package / CDN shimmer kit")
    tl_rows = _timeline_block(crate)
    tl_owned = people_names
    if _SKELETON_HOOK.search(tl_rows) or _owned_used_in(tl_rows, tl_owned):
        fail(
            "#203: not in scope — do not skeleton every virtualized timeline row at once"
        )

    # 7) D24: quiet muted skeleton on people / timeline / search; boot spinner
    # stays; reduced-motion is static.
    dtxt = _typo_docs_blob()
    if not dtxt.strip():
        fail(
            "#203: docs/user/app.md (and/or docs/hacking/tauri.md) required "
            "(quiet muted skeleton on people / timeline / search)"
        )
    if not _docs_203_surfaces(dtxt) or not _DOCS_203_SKELETON.search(dtxt):
        fail(
            "#203: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "people / timeline / search show a quiet muted skeleton while loading "
            "(boot spinner stays; reduced-motion is static)"
        )
    if not _DOCS_203_BOOT_STAYS.search(dtxt):
        fail(
            "#203: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "the boot spinner stays"
        )
    if not _DOCS_203_REDUCE_STATIC.search(dtxt):
        fail(
            "#203: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "reduced-motion is static"
        )


def assert_timeline_append_skeleton_guard(crate: Path) -> None:
    """#203 follow-up: timeline skeleton only on replace, never Load older.

    {#if tlLoading} may stay true so Load older stays disabled. Bars
    (data-skeleton / owned Skeleton) must sit behind an append /
    tlAppending (or equivalent) guard. selectPerson(..., true) must
    actually set that flag. openPersonAtMessage is a full replace.
    Do not require bars on Load older. Existing people / search hooks
    stay in assert_loading_skeletons.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#203: App.svelte required (timeline append must not mount the skeleton)")
    app = _web_logic(crate)
    markup = _svelte_markup(app)
    names = _owned_skeleton_names(app)
    branches = _svelte_if_true_branches(markup, "tlLoading")
    if not branches:
        branches = _svelte_if_true_branches(app, "tlLoading")

    hooked = [(b, _skeleton_hook_positions(b, names)) for b in branches]
    hooked = [(b, pos) for b, pos in hooked if pos]
    if not hooked:
        # Replace path still needs a skeleton hook — existing #203 assert.
        return

    append_flags: list[str] = []
    replace_flags: list[str] = []
    unguarded = False
    for block, positions in hooked:
        for pos in positions:
            stack = _template_stack(block, pos)
            if _stack_hides_on_append(stack):
                af, rf = _guard_flags(stack)
                append_flags.extend(af)
                replace_flags.extend(rf)
                continue
            unguarded = True

    if unguarded:
        fail(
            "#203: {#if tlLoading} must not mount data-skeleton / <Skeleton> "
            "on Load older — guard with !append / !tlAppending (or equivalent)"
        )

    select_fn = _function_body(app, "selectPerson")
    append_param = _select_person_append_param(app)
    load_win = ""
    i = app.find("Load older")
    if i >= 0:
        load_win = app[max(0, i - 500) : i + 80]
    load_calls_append = bool(_LOAD_OLDER_SELECT_APPEND.search(load_win) or _LOAD_OLDER_SELECT_APPEND.search(app))

    wired = False
    for flag in dict.fromkeys(append_flags):
        if _flag_assigned_from_append(select_fn, flag, append_param):
            wired = True
        elif _flag_set_true_in(select_fn, flag) or _flag_set_true_in(load_win, flag):
            wired = True
        if not _open_person_clears_append_flag(app, flag):
            fail(
                "#203: openPersonAtMessage is a full replace — do not inherit "
                "a stale append / hide-bars flag (clear tlAppending or equivalent)"
            )
    for flag in dict.fromkeys(replace_flags):
        if _flag_cleared_on_append(select_fn, flag, append_param):
            wired = True
        if re.search(
            rf"\b{re.escape(flag)}\s*=\s*(?:true|!\s*{re.escape(append_param)})",
            select_fn,
        ):
            wired = True

    if load_calls_append and not wired:
        fail(
            "#203: Load older / selectPerson(..., true) must not show the "
            "timeline skeleton bars (set the append / tlAppending guard)"
        )
