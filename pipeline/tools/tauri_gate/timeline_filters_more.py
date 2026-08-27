"""Additional timeline_filters asserts."""
from __future__ import annotations

from tauri_gate.timeline_filters_lib import *


def assert_timeline_kind_filter(crate: Path) -> None:
    """#116: All + data-derived kind filter, AND with platform filter.

    Acceptance: Email-only shows conversation_kind === email_thread only.
    Kind toolbar options come from kinds present for this person (conversations /
    timeline) — dynamic {#each} is OK; a forever-visible All|DMs|Email|Groups
    button matrix is not required (WhatsApp path must not force Email threads
    buttons into the markup). Empty state when the combined filter yields no rows.
    Load older must not be required / shown under that empty filtered view.
    Groups still need include-groups (kind=Groups must not invent group rows).
    j/k walks visible (combined-filtered) indices. Client-side like #115 is OK.
    """
    app = _web_logic(crate)
    logic = _web_logic(crate)
    api_src = (crate / "web" / "lib" / "api.ts").read_text()
    whole = app + "\n" + logic
    cleaned = _without_comments(whole)
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    detail = _person_detail_markup(app)

    # 1) Kind filter toolbar state / hook (distinct from the #114 conversation switcher).
    has_filter_state = bool(_KIND_FILTER_STATE.search(cleaned))
    has_filter_hook = bool(_KIND_FILTER_HOOK.search(blob))
    if not (has_filter_state or has_filter_hook):
        fail(
            "#116: person timeline must have a conversation-kind filter "
            "(kindFilter / conversationKindFilter / data-kind-filter) — "
            "All + kinds present for this person"
        )

    # Toolbar chrome: All for the active kind dimension. Kind chips themselves
    # must be data-derived (not a forever-hard-coded full matrix always in DOM).
    toolbar_blob = detail if detail.strip() else app
    toolbar_only = toolbar_blob
    for m in _EACH_TIMELINE.finditer(toolbar_blob):
        end = _matching_each_end(toolbar_blob, m.start())
        if end > m.start():
            toolbar_only = toolbar_only.replace(toolbar_blob[m.start() : end], "", 1)
    has_toolbar_all = bool(_KIND_TOOLBAR_ALL.search(toolbar_only)) or bool(
        _KIND_TOOLBAR_ALL.search(cleaned)
    )
    options_from_data = bool(_KIND_OPTIONS_FROM_DATA.search(cleaned))
    has_dynamic_each = bool(
        re.search(
            r"\{#each\s+(?:availableKinds|kindOptions|presentKinds|personKinds|"
            r"timelineKinds|kindsPresent)\b",
            toolbar_only + "\n" + app,
            re.I,
        )
    )
    if not has_toolbar_all:
        fail(
            "#116: kind filter must offer All when the kind dimension is active "
            "(default = every kind / D18 merged)"
        )
    if not options_from_data:
        fail(
            "#116: kind toolbar options must come from kind / conversation_kind "
            "values present for this person (conversations / timeline via "
            "map/Set/for…of into availableKinds), not a hard-coded forever "
            "All|DMs|Email|Groups matrix always rendered for every person"
        )
    # Static onclick matrix for dm + email_thread + group always in the toolbar
    # forces Email threads under a WhatsApp-only person — reject that.
    if _STATIC_KIND_MATRIX.search(toolbar_only):
        fail(
            "#116: do not hard-code always-rendered DMs + Email threads + Groups "
            "buttons — derive kind chips from this person's conversation_kind "
            "values (dynamic {#each} is OK; WhatsApp must not force Email threads)"
        )
    # Pretty labels / raw archive kinds may live in a helper map; not all required
    # to be visible at once. At least one known kind token should exist for UX.
    has_kind_token = bool(
        _KIND_OPT_DM.search(cleaned)
        or _KIND_OPT_EMAIL.search(cleaned)
        or _KIND_OPT_GROUP.search(cleaned)
        or re.search(r"[\"'](?:dm|email_thread|group)[\"']", cleaned)
    )
    if not (has_kind_token or has_dynamic_each):
        fail(
            "#116: kind filter must be able to select archive kinds "
            "(dm / email_thread / group labels or values, or {#each} over them)"
        )

    # Default selection is All (null / undefined / "all").
    if not re.search(
        r"(?:kindFilter|conversationKindFilter|timelineKind|tlKind|"
        r"selectedKind|activeKind|pickedKind|filterKind|kindOnly|"
        r"timelineKindFilter|selectedConversationKind)"
        r"\s*=\s*\$state\s*(?:<[^>]*>)?\s*\(\s*(?:null|undefined|[\"']all[\"'])",
        cleaned,
        re.I,
    ) and not re.search(
        r"(?:kindFilter|conversationKindFilter|timelineKind|tlKind|"
        r"selectedKind|activeKind|filterKind|kindOnly)"
        r"\s*=\s*(?:null|undefined|[\"']all[\"'])",
        cleaned,
        re.I,
    ):
        fail(
            "#116: kind filter must default to All "
            "(kind state starts null / undefined / \"all\")"
        )

    # 2) Filtering by kind keeps only matching conversation_kind rows.
    client_ok = bool(_CLIENT_KIND_FILTER.search(cleaned))
    derived_ok = bool(_DERIVED_KIND_FILTER.search(cleaned))
    api_ok = bool(_API_KIND_FILTER.search(cleaned))
    if not (client_ok or derived_ok or api_ok):
        fail(
            "#116: Email-only must show email_thread rows only "
            "(filter timeline rows by row.conversation_kind client-side, "
            "or pass kind into personTimeline / the core query)"
        )
    # Prefer conversation_kind field (archive / TimelineRow), not invented labels alone.
    if not re.search(r"\bconversation_kind\b", cleaned):
        fail(
            "#116: kind filter must key off conversation_kind on timeline rows "
            "(dm / group / email_thread)"
        )

    if api_ok:
        api_args = re.search(
            r"personTimeline\s*:\s*\(\s*args\s*:\s*\{([^}]*)\}",
            api_src,
            re.S,
        )
        if not api_args or not re.search(
            r"\b(?:kind|conversation_kind)\b", api_args.group(1)
        ):
            fail(
                "#116: personTimeline args must include optional kind / "
                "conversation_kind when the UI passes a kind filter into the query"
            )

    # 3) AND with the platform filter — both present on the filter path.
    has_platform = bool(_PLATFORM_FILTER_STATE.search(cleaned)) or bool(
        _PLATFORM_FILTER_HOOK.search(blob)
    )
    if not has_platform:
        fail(
            "#116: platform filter (#115) must remain; kind filter ANDs with it "
            "(Email + WhatsApp keeps only matching rows)"
        )
    if not _COMBINED_FILTER_PATH.search(cleaned):
        fail(
            "#116: kind filter must AND with the platform filter "
            "(same filter path / derived list must consider both "
            "conversation_kind and platform — not replace the platform toolbar)"
        )

    # 4) Groups still require include-groups; kind=Groups must not invent group rows.
    if not _INCLUDE_GROUPS_LABEL.search(app) and not _INCLUDE_GROUPS_LABEL.search(blob):
        fail("#116: include groups toggle must remain (groups still require it)")
    if _KIND_BYPASS_GROUPS.search(cleaned):
        fail(
            "#116: kind=Groups must not force includeGroups=true or bypass the "
            "include-groups gate — groups stay out of the stream when groups are off"
        )
    # Selecting Groups must not be the only way groups appear; includeGroups still gates load.
    if re.search(
        r"(?:kindFilter|conversationKindFilter|selectedKind)\s*===?\s*[\"']group[\"']"
        r"[^;{]{0,200}includeGroups\s*=\s*(?:true|!0|1)\b",
        cleaned,
        re.I | re.S,
    ):
        fail(
            "#116: do not auto-enable include groups when the kind filter is Groups"
        )

    # 5) Empty state when the combined filtered list is empty (email-only, no mail).
    # Raw timeline.length === 0 alone is not enough once filters hide every row.
    # Require EmptyState (or data-empty) in a branch that keys off the *filtered* list,
    # not merely filteredTimeline.length used for day-grouping loops.
    empty_src = app + "\n" + blob
    markup = app
    script_end = app.rfind("</script>")
    if script_end >= 0:
        markup = app[script_end:]
    filtered_empty_cond = re.compile(
        r"("
        r"\{#if\s+[^}]{0,200}"
        r"(?:filteredTimeline|visibleTimeline|timelineRows|displayTimeline|"
        r"shownTimeline|tlRows|visibleRows)"
        r"[^}]{0,80}(?:length|===?\s*0)"
        r"|\{:else\s+if\s+[^}]{0,200}"
        r"(?:filteredTimeline|visibleTimeline|timelineRows|displayTimeline|"
        r"shownTimeline|tlRows|visibleRows)"
        r"[^}]{0,80}(?:length|===?\s*0)"
        r"|(?:filteredTimeline|visibleTimeline|timelineRows|displayTimeline|"
        r"shownTimeline|tlRows|visibleRows)"
        r"\s*(?:\?\.|\.)?\s*length\s*===?\s*0"
        r"|!\s*(?:filteredTimeline|visibleTimeline|timelineRows|displayTimeline|"
        r"shownTimeline|tlRows|visibleRows)"
        r"\s*(?:\?\.|\.)?\s*length"
        r")",
        re.I,
    )
    # Walk markup: filtered-empty condition must sit near EmptyState / data-empty.
    empty_ok = False
    for m in filtered_empty_cond.finditer(markup + "\n" + cleaned):
        window = (markup + "\n" + cleaned)[m.start() : m.end() + 280]
        if re.search(r"EmptyState|data-empty", window, re.I):
            empty_ok = True
            break
    # Script-side flag that drives EmptyState is also OK.
    if not empty_ok and re.search(
        r"(?:filteredEmpty|isFilterEmpty|noVisibleRows|filterEmpty|tlEmpty)\s*=",
        cleaned,
        re.I,
    ):
        if re.search(
            r"(?:filteredEmpty|isFilterEmpty|noVisibleRows|filterEmpty|tlEmpty)"
            r"[\s\S]{0,400}(?:EmptyState|data-empty)"
            r"|(?:EmptyState|data-empty)[\s\S]{0,400}"
            r"(?:filteredEmpty|isFilterEmpty|noVisibleRows|filterEmpty|tlEmpty)",
            empty_src,
            re.I,
        ):
            empty_ok = True
    if not empty_ok:
        fail(
            "#116: when the kind/platform filter yields no rows "
            "(e.g. Email-only and the person has no mail), show an empty state "
            "on the filtered list — not only when the unfiltered timeline is empty"
        )
    # Empty copy should be reachable in the person timeline pane (static presence).
    # `{@render timelinePaneState()}` hosts EmptyState in a snippet above this
    # window; expand renders so we do not require a fake data-empty on the list.
    pane_empty = _person_detail_with_renders(app)
    if not re.search(
        r"EmptyState|data-empty", pane_empty if pane_empty.strip() else app, re.I
    ):
        fail("#116: person timeline must keep an EmptyState path for the empty filter case")

    # 5b) Load older must not show under the empty filtered view.
    # #113 still requires the control to exist in markup; it must not be required
    # (or left visible) when filteredTimeline is empty next to "No messages…".
    if re.search(r"Load older", markup, re.I):
        load_guarded = False
        for m in re.finditer(r"\{#if\s+([^}]+)\}", markup):
            cond = m.group(1)
            block_start = m.end()
            # End at matching {/if} at depth 1 from this {#if}, approx via next Load older.
            next_load = markup.find("Load older", block_start)
            if next_load < 0:
                continue
            between = markup[block_start:next_load]
            # Skip if another {#if} opens first without this cond applying directly —
            # require Load older appears before any nested {#if} or only simple content.
            if re.search(r"\{#if\b", between):
                continue
            if re.search(
                r"(?:filteredTimeline|visibleTimeline|timelineRows|displayTimeline|"
                r"shownTimeline|tlRows|visibleRows)",
                cond,
                re.I,
            ):
                load_guarded = True
                break
        # Also accept: Load older only after an {:else} of a filtered-empty branch
        # (empty filtered → EmptyState; else → Load older path).
        if not load_guarded and re.search(
            r"(?:filteredTimeline|visibleTimeline|timelineRows|displayTimeline|"
            r"shownTimeline|tlRows|visibleRows)"
            r"[^}]{0,80}(?:length\s*===?\s*0|!\s*\w+\.length)"
            r"[\s\S]{0,400}\{:else\b[\s\S]{0,400}Load older",
            markup,
            re.I,
        ):
            load_guarded = True
        if not load_guarded:
            fail(
                "#116: Load older must not show under the empty filtered view "
                "(gate it on filteredTimeline.length / visible rows — do not "
                "require Load older when the kind/platform filter hides every row)"
            )

    # 6) j/k / highlight walk visible indices from the combined-filtered list.
    if not _VISIBLE_KIND_JK.search(cleaned):
        fail(
            "#116: j/k must walk only visible (combined-filtered) timeline rows "
            "(visibleTlIndices / filteredTimeline), not the full unfiltered list"
        )
    # visible indices derivation should hang off the same filtered list that applies kind.
    if not re.search(
        r"(?:visibleTlIndices|visibleIndices)\s*=\s*\$derived\s*\("
        r"[^)]{0,200}(?:filteredTimeline|visibleTimeline|timelineRows)",
        cleaned,
        re.I | re.S,
    ) and not re.search(
        r"(?:filteredTimeline|visibleTimeline)[^;]{0,200}"
        r"(?:visibleTlIndices|visibleIndices|\.map\s*\([^)]*index)",
        cleaned,
        re.I | re.S,
    ):
        # Softer: onKey / j/k references filtered or visible indices at all.
        if not re.search(
            r"(?:key\s*===?\s*[\"']j[\"']|[\"']j[\"']\s*\|\||ArrowDown)"
            r"[\s\S]{0,400}"
            r"(?:visibleTlIndices|visibleIndices|filteredTimeline|visibleTimeline)",
            cleaned,
            re.I,
        ) and not re.search(
            r"(?:visibleTlIndices|visibleIndices|filteredTimeline)"
            r"[\s\S]{0,400}"
            r"(?:key\s*===?\s*[\"']j[\"']|[\"']j[\"']|ArrowDown)",
            cleaned,
            re.I,
        ):
            fail(
                "#116: j/k (and the selection ring) must use the combined-filtered "
                "visible indices so hidden kind/platform rows are skipped"
            )
