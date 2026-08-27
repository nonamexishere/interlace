"""Timeline scroll / virtualize chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.timeline_latest import *
from tauri_gate.timeline_virtual import *


def assert_timeline_latest(crate: Path) -> None:
    """#113: newest at bottom; Load older at top; prepend without jump; pad / scroll after layout.

    Narrow-pane dogfood: clear tlLoading before the open-person scroll; nested rAF for wrap.
    """
    app = _web_logic(crate)
    logic = _web_logic(crate)
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    found_each = False
    found_load = False
    for p in _web_sources(crate):
        if p.suffix != ".svelte":
            continue
        text = p.read_text()
        script_end = text.rfind("</script>")
        markup = text[script_end:] if script_end >= 0 else text
        if _LOAD_OLDER.search(markup):
            found_load = True
        each = _EACH_TIMELINE.search(markup)
        if not each:
            continue
        found_each = True
        if not _LOAD_OLDER.search(markup):
            fail("#113: Load older button is required (intersection observer is optional)")
        if markup.find("Load older") > each.start():
            fail("#113: Load older must sit at the top of the message list, not under it")
        # A leftover control under the list is the current bug even if one also sits above.
        after_each = markup.find("{/each}", each.start())
        if after_each >= 0 and "Load older" in markup[after_each:]:
            fail("#113: Load older must sit at the top of the message list, not under it")
    if not found_each:
        fail("#113: person timeline must still {#each timeline} or {#each dayGroups}")
    if not found_load:
        fail("#113: Load older button is required (intersection observer is optional)")

    concat_bottom = bool(_CONCAT_BOTTOM.search(logic))
    prepended = bool(_PREPEND.search(logic))
    full_reverse = bool(_FULL_REVERSE.search(logic))
    oldest_first = bool(_OLDEST_FIRST.search(logic))
    if concat_bottom and not full_reverse:
        fail("#113: older pages must be prepended, not concatenated at the bottom")
    if not (prepended or full_reverse or oldest_first):
        fail(
            "#113: visual order is a chat — older above, newest at the bottom "
            "(reverse or sort the newest-first page; prepend older rows)"
        )

    # Initial fetch is already the newest page (`before` unset). Latest must be visible.
    if not _SCROLL_TO_BOTTOM.search(logic) and not _SCROLL_TO_BOTTOM.search(app):
        fail(
            "#113: opening a person must scroll to the bottom "
            "so the latest messages are visible"
        )

    if not _SCROLL_PRESERVE.search(logic) and not _SCROLL_PRESERVE.search(app):
        fail(
            "#113: preserve scroll position when prepending older rows "
            "(do not jump the viewport to 0)"
        )

    # Last bubble must sit above the “Bodies are text only” chrome, not under it.
    if not _timeline_has_bottom_pad(crate, app):
        fail(
            "#113: last bubble must sit above the “Bodies are text only” chrome — "
            "pad the bottom of the message list / #person-timeline "
            "(pb-8, pb-10, pb-12, padding-bottom, or a spacer after {/each})"
        )

    # tick then scrollTop = scrollHeight runs before day groups / images settle.
    if not _scrolls_after_layout(app, logic):
        fail(
            "#113: opening a person must scroll to the newest message after layout "
            "(requestAnimationFrame and/or scrollIntoView on the last row), "
            "not only await tick() then scrollTop = scrollHeight"
        )

    # Loading line still in the pane (tlLoading true) makes one rAF land short on a wrap.
    if not _clears_loading_before_open_scroll(app, logic):
        fail(
            "#113: clear tlLoading before the open-person scroll to latest "
            "(tlLoading = false must run before that scrollTop / scrollIntoView / "
            "requestAnimationFrame, not only in finally after it — "
            "the loading line must leave the pane first)"
        )
    if not _nested_raf_around_open_scroll(app, logic):
        fail(
            "#113: opening a person must wait for wrap on a short pane "
            "(nested requestAnimationFrame around the open-person scroll to latest; "
            "a single rAF while tlLoading is still true is not enough)"
        )

    if not re.search(
        r"("
        r"opens? at (the )?(latest|newest)"
        r"|(latest|newest) messages"
        r"|scroll(?:s|ed)? to the bottom"
        r")",
        dtxt,
        re.I,
    ):
        fail("#113: docs/user/app.md must say the person timeline opens at the latest messages")
    if not re.search(
        r"Load older.{0,80}(top|above)|(top|above).{0,80}Load older",
        dtxt,
        re.I | re.S,
    ):
        fail("#113: docs/user/app.md must say Load older is at the top")
    if not re.search(
        r"("
        r"does not jump"
        r"|don.?t jump"
        r"|without jump"
        r"|keep(?:s|ing)? (the )?(scroll|viewport|place)"
        r"|preserve(?:s|d)? scroll"
        r"|scroll position"
        r")",
        dtxt,
        re.I,
    ):
        fail("#113: docs/user/app.md must say loading older does not jump the viewport")


def assert_virtualized_timeline(crate: Path) -> None:
    """#120: window person timeline (visible + overscan); keep j/k + Load older.

    Acceptance: synthetic 10k DM does not lock the window — only visible + overscan
    rows (and needed day headings) mount. Bodies still text nodes.
    Static gate: fail naive full {#each dayGroups}→{#each group.rows} without a
    window. No FPS assertions in CI (dogfood measures scroll).
    Not: 10M in one view, lazy-decode every photo.
    """
    app = _web_logic(crate)
    logic = _web_logic(crate)
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    whole = app + "\n" + logic
    cleaned = _without_comments(whole)
    markup = _svelte_markup(app)
    # Prefer person-timeline pane if present.
    pt = markup.find("person-timeline")
    if pt >= 0:
        timeline_markup = markup[pt:]
    else:
        timeline_markup = markup
    block = _timeline_block(crate)

    # 1) Reject naive full double-each over dayGroups/rows (current App.svelte).
    # Prefer this message as the pre-impl red gate so the fix target is obvious.
    if _naive_full_timeline_mount(timeline_markup, cleaned):
        fail(
            "#120: do not always mount every filtered row "
            "({#each dayGroups} → {#each group.rows} over the full list, or "
            "{#each timeline|filteredTimeline} without a window). "
            "Window to visible + overscan only so a synthetic 10k DM stays scrollable"
        )

    # 2) Virtualization / windowing signal must exist (overscan, virtual list, …).
    if not _VIRT_SIGNAL.search(cleaned) and not _VIRT_SIGNAL.search(blob):
        fail(
            "#120: person timeline must window the list "
            "(only visible + overscan rows in the DOM — overscan / virtual list / "
            "visibleRange / startIndex+endIndex / windowed rows; "
            "do not always mount every filtered bubble)"
        )

    # 3) Positive: render path must each a windowed list (or VirtualList).
    if not _has_windowed_render_path(timeline_markup, cleaned):
        fail(
            "#120: person timeline render path must iterate a windowed list "
            "(windowed/visible/virtual/rendered rows or groups, or a list derived "
            "with overscan/slice/startIndex — not the full filtered set)"
        )

    # 4) Keep Load older (#113) — still at the list, not dropped by virtualization.
    if not _LOAD_OLDER.search(markup) and not _LOAD_OLDER.search(app):
        fail("#120: keep Load older when virtualizing (do not regress #113)")

    # 5) Keep j/k on visible (filtered) indices (#113 / #116).
    if not _JK_KEY.search(cleaned) and not _VISIBLE_KIND_JK.search(cleaned):
        fail(
            "#120: keep j/k walking visible timeline rows "
            "(visibleTlIndices / j|k handlers — do not regress #113/#116)"
        )

    # 6) Bodies still text nodes — no {@html} / innerHTML of message body.
    body_surface = block + "\n" + timeline_markup
    if _HTML_BODY.search(body_surface) or _BODY_INNER_HTML.search(body_surface):
        # Allow innerHTML only outside body bindings (e.g. unrelated); still forbid {@html}.
        if _HTML_BODY.search(body_surface):
            fail(
                "#120: bodies still text nodes — no {@html} of the message body "
                "(keep whitespace-pre-wrap / plain text bindings)"
            )
        # innerHTML near body_text / displayBody is the product footgun.
        if re.search(
            r"(?:body_text|displayBody|message\.body|row\.body)[\s\S]{0,120}\.innerHTML\s*="
            r"|\.innerHTML\s*=[\s\S]{0,120}(?:body_text|displayBody)",
            body_surface,
            re.I,
        ):
            fail(
                "#120: bodies still text nodes — no innerHTML of the message body"
            )

    # 7) Not in scope: 10M-in-one-view / lazy-decode-every-photo (product claims).
    scope_src = _without_comments(blob)
    # Ignore this gate file and issue notes if they ever land under web/ (they should not).
    if _SCOPE_10M.search(scope_src):
        fail(
            "#120: not in scope — do not claim or build 10M messages in one view "
            "(window the list for 10k-class DMs only)"
        )
    if _SCOPE_LAZY_EVERY_PHOTO.search(scope_src):
        fail(
            "#120: not in scope — lazy-decode every photo / CAS is a separate concern, "
            "not part of timeline windowing"
        )


def assert_variable_height_timeline(crate: Path) -> None:
    """#224: measure-and-cache row heights; prefix-sum spacers; constant 88.

    Keep the #120 window. Unmeasured slots stay ESTIMATED_ROW_HEIGHT (not a
    live average). CI proves source shapes, not FPS.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#224: App.svelte required (variable-height person timeline)")
    app = _web_logic(crate)
    logic = _web_logic(crate)
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    cleaned = _without_comments(app + "\n" + logic)
    markup = _svelte_markup(app)
    pt = markup.find("person-timeline")
    timeline_markup = markup[pt:] if pt >= 0 else markup
    block = _timeline_block(crate)
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) Still windowed — #120 stays; re-check the window hooks.
    if not re.search(r"\bvisibleRange\b", cleaned) and not re.search(
        r"\bwindowedDayGroups\b", cleaned
    ):
        fail(
            "#224: keep the #120 window "
            "(visibleRange / windowedDayGroups — do not remount every filtered row)"
        )

    # 2) Height cache + measure path on [data-tl-index].
    if not _row_measure_path(cleaned):
        fail(
            "#224: person timeline must measure-and-cache variable row heights "
            "(rowHeights plus ResizeObserver / getBoundingClientRect on "
            "[data-tl-index]); unmeasured slots keep constant "
            "ESTIMATED_ROW_HEIGHT = 88 — not startIndex * 88 spacers"
        )

    # 3) heightOf / offsetOf (or equivalent prefix-sum helpers) + constant 88.
    if not _HEIGHT_OF.search(cleaned) and not (
        _HEIGHT_CACHE.search(cleaned) and _CONST_FALLBACK.search(cleaned)
    ):
        fail(
            "#224: heightOf (or equivalent) must look up the rowHeights cache "
            "and fall back to constant ESTIMATED_ROW_HEIGHT"
        )
    if not _OFFSET_OF.search(cleaned):
        fail(
            "#224: offsetOf (or equivalent prefix-sum helper) must exist so "
            "spacers / visibleRange / j/k use measured (or constant-fallback) heights"
        )
    if not re.search(r"ESTIMATED_ROW_HEIGHT\s*=\s*88", cleaned):
        fail(
            "#224: unmeasured slots must use constant ESTIMATED_ROW_HEIGHT = 88 "
            "(do not drop the #120 estimate; do not replace it with a live average)"
        )
    if _LIVE_AVG.search(cleaned):
        fail(
            "#224: unmeasured slots must use constant ESTIMATED_ROW_HEIGHT — "
            "not a live average (measuredSum / measuredCount / fallbackHeight "
            "that divides measured stats)"
        )
    fb = _function_body(cleaned, "fallbackHeight")
    if fb and re.search(r"measuredSum|measuredCount|/\s*\w+", fb):
        fail(
            "#224: unmeasured slots must use constant ESTIMATED_ROW_HEIGHT — "
            "not fallbackHeight() that divides measured stats"
        )
    if not _height_lookup_uses_constant(cleaned):
        fail(
            "#224: heightOf / cache miss must use constant ESTIMATED_ROW_HEIGHT "
            "(not a running average of measured heights)"
        )
    for name in _OFFSET_OF_NAMES:
        body = _function_body(cleaned, name)
        if not body:
            continue
        if _FIXED_INDEX_TIMES_EST.search(body) and not (
            _HEIGHT_OF.search(body) or _HEIGHT_CACHE.search(body)
        ):
            fail(
                "#224: offsetOf must sum measured (or constant-fallback) heights, "
                "not return index * ESTIMATED_ROW_HEIGHT"
            )

    # 4) Spacers are prefix sums, not startIndex * 88 / (total - endIndex) * 88.
    spacer_top = _derived_body(cleaned, "spacerTop") or ""
    spacer_bottom = _derived_body(cleaned, "spacerBottom") or ""
    if not spacer_top or not spacer_bottom:
        fail(
            "#224: spacerTop / spacerBottom must exist and use prefix sums "
            "(offsetOf), not startIndex * ESTIMATED_ROW_HEIGHT"
        )
    if _FIXED_INDEX_TIMES_EST.search(spacer_top) or _FIXED_INDEX_TIMES_EST.search(
        spacer_bottom
    ):
        fail(
            "#224: spacerTop / spacerBottom must not be "
            "startIndex * ESTIMATED_ROW_HEIGHT / "
            "(total - endIndex) * ESTIMATED_ROW_HEIGHT — use offsetOf "
            "(prefix sums of measured or constant-fallback heights)"
        )
    if not _uses_prefix_sum(spacer_top) or not _uses_prefix_sum(spacer_bottom):
        fail(
            "#224: spacerTop / spacerBottom must use prefix sums "
            "(offsetOf or equivalent), not a fixed row estimate"
        )

    # 5) visibleRange walks prefix sums, not scrollTop / 88.
    vr = _derived_body(cleaned, "visibleRange") or ""
    if not vr:
        fail(
            "#224: visibleRange must walk prefix sums of measured "
            "(or constant-fallback) heights, not tlScrollTop / ESTIMATED_ROW_HEIGHT"
        )
    if _SCROLL_DIV_EST.search(vr):
        fail(
            "#224: visibleRange must not be only tlScrollTop / ESTIMATED_ROW_HEIGHT "
            "— walk prefix sums / measured heights"
        )
    if not _uses_prefix_sum(vr):
        fail(
            "#224: visibleRange must walk prefix sums / measured heights "
            "(offsetOf / heightOf), not divide scrollTop by 88"
        )

    # 6) ensureTlIndexVisible uses prefix sums, not pos * 88.
    ensure = _function_body(cleaned, "ensureTlIndexVisible")
    if not ensure:
        fail(
            "#224: keep ensureTlIndexVisible and point it at prefix sums "
            "(not pos * ESTIMATED_ROW_HEIGHT)"
        )
    if _FIXED_INDEX_TIMES_EST.search(ensure):
        fail(
            "#224: ensureTlIndexVisible must use prefix sums "
            "(offsetOf), not pos * ESTIMATED_ROW_HEIGHT"
        )
    if not _uses_prefix_sum(ensure):
        fail(
            "#224: ensureTlIndexVisible must use prefix sums of measured "
            "(or constant-fallback) heights so j/k lands on the selected bubble"
        )

    # 7) j/k + Load older + text bodies stay (#120 / #113 / #116).
    if not _LOAD_OLDER.search(markup) and not _LOAD_OLDER.search(app):
        fail("#224: keep Load older when measuring row heights (do not regress #113)")
    if not _JK_KEY.search(cleaned) and not _VISIBLE_KIND_JK.search(cleaned):
        fail(
            "#224: keep j/k walking visible timeline rows "
            "(do not regress #113/#116/#120)"
        )
    body_surface = block + "\n" + timeline_markup
    if _HTML_BODY.search(body_surface):
        fail(
            "#224: bodies still text nodes — no {@html} of the message body "
            "(keep whitespace-pre-wrap / displayBody)"
        )
    if not _PRE_WRAP.search(block):
        fail("#224: bodies still whitespace-pre-wrap text nodes")

    # 8) D24: measured row heights so two-sided DMs scroll without jumping.
    if not dtxt.strip():
        fail(
            "#224: docs/user/app.md required — person timeline virtualizes with "
            "measured row heights so two-sided DMs scroll without jumping"
        )
    if not re.search(r"only the rows in \(and near\) the viewport", dtxt, re.I):
        fail(
            "#224: keep the existing “only the rows in (and near) the viewport” "
            "sentence in docs/user/app.md"
        )
    if not re.search(r"measured\s+row\s+heights?", dtxt, re.I):
        fail(
            "#224: docs/user/app.md must say the person timeline virtualizes "
            "with measured row heights so two-sided DMs scroll without jumping"
        )

    # 9) Not in scope (same spirit as #120).
    scope_src = _without_comments(blob)
    if _SCOPE_10M.search(scope_src):
        fail(
            "#224: not in scope — do not claim or build 10M messages in one view"
        )
    if _SCOPE_LAZY_EVERY_PHOTO.search(scope_src):
        fail(
            "#224: not in scope — lazy-decode every photo / CAS is a separate "
            "concern, not part of variable-height windowing"
        )
