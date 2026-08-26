"""Timeline scroll / virtualize chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _HTML_BODY,
    _SCROLL_HELPER_SKIP,
    _TIMELINE_EACH_NAMES,
    _call_arg,
    _function_body,
    _match_closer,
    _matching_each_end,
    _svelte_markup,
    _timeline_block,
    _web_logic,
    _web_sources,
    _without_comments,
)

from tauri_gate.import_boot import (
    _HEIGHT_CACHE,
    _PRE_WRAP,
)


# j/k / highlight use indices from the filtered (visible) list.
_VISIBLE_KIND_JK = re.compile(
    r"("
    r"visibleTlIndices|visibleIndices|visibleTimeline|filteredTimeline"
    r"|nearestVisibleTlIndex"
    r")",
    re.I,
)
_TL_SPACER = re.compile(
    r"("
    r"\bpb-(?:8|10|12)\b"
    r"|padding-bottom\s*:"
    r"|\bh-(?:8|10|12)\b"
    r"|spacer"
    r")",
    re.I,
)
# Enough pad that the last bubble is not under the text-only chrome (not .day-heading 0.25rem).
_TL_PAD_UTIL = re.compile(r"\bpb-(?:8|10|12)\b")
_TL_LOADING_FALSE = re.compile(r"\btlLoading\s*=\s*false\b")
_SCROLL_TO_BOTTOM = re.compile(
    r"("
    r"scrollTop\s*=\s*[^;\n]*scrollHeight"
    r"|scrollTo\s*\(\s*\{[^}]*scrollHeight"
    r"|scrollIntoView\s*\("
    r")",
    re.I,
)
_SCROLL_PRESERVE = re.compile(
    r"("
    r"scrollTop\s*\+="
    r"|scrollHeight\s*-"
    r"|(?:prev(?:ious)?|old|saved|was)(?:Scroll)?(?:Height|Top)"
    r")",
    re.I,
)
_SCROLL_AFTER_LAYOUT = re.compile(r"requestAnimationFrame\s*\(|scrollIntoView\s*\(")
_RAF_CALL = re.compile(r"\b(?:window\.)?requestAnimationFrame\s*\(")
_PREPEND = re.compile(
    r"("
    r"(?:rows|older|page|reversed|chrono)\s*\.concat\s*\(\s*timeline\s*\)"
    r"|\[\s*\.\.\.[^,\]]+\s*,\s*\.\.\.timeline\s*\]"
    r"|\.unshift\s*\("
    r"|timeline\s*=\s*append\s*\?\s*[^;\n]*\.concat\s*\(\s*timeline\s*\)"
    r")",
)
# Newest-first API page flipped for chat order (older above, newest at the bottom).
_OLDEST_FIRST = re.compile(
    r"("
    r"\.toReversed\s*\("
    r"|\.reverse\s*\("
    r"|oldestFirst"
    r"|\.sort\s*\([^)]*sent_at"
    r")",
    re.I,
)

# #113 — newest page visible at the bottom; Load older at the top; prepend without jump.
# Dogfood: pad the list so the last bubble clears the text-only chrome; scroll after layout.
# Narrow pane: tlLoading = false before the open scroll; nested rAF so wrap has happened.
_LOAD_OLDER = re.compile(r"Load older")
_LAST_ROW = re.compile(
    r"("
    r"lastElementChild"
    r"|lastChild"
    r"|\.at\s*\(\s*-1\s*\)"
    r"|\[\s*length\s*-\s*1\s*\]"
    r"|length\s*-\s*1"
    r"|:last-child"
    r"|last(?:Row|Bubble|Msg|Message|Item)"
    r")",
    re.I,
)
# Whole newest-first store shown oldest-first (concat-then-reverse is ok).
_FULL_REVERSE = re.compile(
    r"("
    r"timeline\.toReversed\s*\("
    r"|timeline\.slice\s*\(\s*\)\s*\.reverse\s*\("
    r"|\[\s*\.\.\.timeline\s*\]\s*\.reverse\s*\("
    r"|\{#each\s+timeline\.toReversed"
    r")",
)
# Timeline row loop — full list names or windowed variants (#120).
_EACH_TIMELINE = re.compile(
    r"\{#each\s+(?:"
    r"timeline|dayGroups|"
    r"windowed(?:Day)?Groups|visible(?:Day)?Groups|virtual(?:Day)?Groups|"
    r"rendered(?:Day)?Groups|windowedRows|visibleRows|virtualRows|renderedRows|"
    r"windowedTimeline|visibleTimeline|virtualTimeline|renderedTimeline|"
    r"windowedItems|visibleItems|virtualItems"
    r")\b"
)
_CONCAT_BOTTOM = re.compile(r"timeline\.concat\s*\(\s*rows\s*\)")




def _person_timeline_open_tag(src: str) -> str:
    m = re.search(
        r"<[^>]*\bid=(?:[\"']person-timeline[\"']|\{[\"']person-timeline[\"']\})[^>]*>",
        src,
        re.I | re.S,
    )
    return m.group(0) if m else ""


def _has_nonzero_padding_bottom(blob: str) -> bool:
    for m in re.finditer(r"padding-bottom\s*:\s*([^;}\n]+)", blob, re.I):
        val = m.group(1).strip().lower()
        if val not in {"0", "0px", "0rem", "0em", "0%", "none"}:
            return True
    return False


def _timeline_css_pad_blocks(blob: str) -> list[str]:
    blocks: list[str] = []
    for rx in (
        r"#person-timeline(?:\s+(?:ol|ul))?\s*\{([^}]+)\}",
        r"\[id=[\"']person-timeline[\"']\](?:\s+(?:ol|ul))?\s*\{([^}]+)\}",
    ):
        blocks.extend(m.group(1) for m in re.finditer(rx, blob, re.I))
    return blocks


def _timeline_has_bottom_pad(crate: Path, app: str) -> bool:
    """True if #person-timeline / the message list pads above the text-only chrome."""
    tag = _person_timeline_open_tag(app)
    if tag and (_TL_PAD_UTIL.search(tag) or _has_nonzero_padding_bottom(tag)):
        return True
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    for block in _timeline_css_pad_blocks(blob):
        if _TL_PAD_UTIL.search(block) or _has_nonzero_padding_bottom(block):
            return True
    for p in _web_sources(crate):
        if p.suffix != ".svelte":
            continue
        text = p.read_text()
        script_end = text.rfind("</script>")
        markup = text[script_end:] if script_end >= 0 else text
        for each in _EACH_TIMELINE.finditer(markup):
            before = markup[: each.start()]
            ol = None
            for m in re.finditer(r"<ol\b[^>]*>", before, re.I | re.S):
                ol = m
            if ol and (
                _TL_PAD_UTIL.search(ol.group(0)) or _has_nonzero_padding_bottom(ol.group(0))
            ):
                return True
            end = _matching_each_end(markup, each.start())
            if end < 0:
                continue
            after = markup[end : end + 900]
            cut = after.lower().find("</scrollarea>")
            if cut < 0:
                cut = after.find("Bodies are text")
            if cut >= 0:
                after = after[:cut]
            if _TL_SPACER.search(after):
                return True
    return False


def _scrolls_after_layout(app: str, logic: str) -> bool:
    """True if open-person scroll waits for layout (rAF and/or last-row scrollIntoView)."""
    src = app + "\n" + logic
    for m in _SCROLL_AFTER_LAYOUT.finditer(src):
        window = src[max(0, m.start() - 500) : m.end() + 500]
        if m.group(0).startswith("requestAnimationFrame"):
            if re.search(r"scrollTop|scrollTo\s*\(|scrollIntoView", window):
                return True
        elif _LAST_ROW.search(window):
            return True
    return False


def _contains_open_latest_scroll(blob: str, whole: str, seen: set[str] | None = None) -> bool:
    """True if blob (or a named rAF callback it references) scrolls to latest."""
    if _SCROLL_TO_BOTTOM.search(blob):
        return True
    found = seen if seen is not None else set()
    for m in _RAF_CALL.finditer(blob):
        arg = _call_arg(blob, m.end() - 1)
        if _SCROLL_TO_BOTTOM.search(arg):
            return True
        ident = re.fullmatch(r"\s*([A-Za-z_]\w*)\s*", arg)
        if ident and ident.group(1) not in found:
            found.add(ident.group(1))
            body = _function_body(whole, ident.group(1))
            if body and _contains_open_latest_scroll(body, whole, found):
                return True
    return False


def _open_person_scroll_anchor(src: str, whole: str) -> int | None:
    """Index of the outer open-person rAF / scrollTop / scrollIntoView (not append +=)."""
    for m in _RAF_CALL.finditer(src):
        arg = _call_arg(src, m.end() - 1)
        if arg and _contains_open_latest_scroll(arg, whole):
            return m.start()
    m = _SCROLL_TO_BOTTOM.search(src)
    return m.start() if m else None


def _clears_loading_before_open_scroll(app: str, logic: str) -> bool:
    """tlLoading = false must appear before the open-person rAF/scroll, not only in finally after."""
    whole = app + "\n" + logic
    fn = _function_body(whole, "selectPerson") or whole
    cleaned = _without_comments(fn)
    whole_c = _without_comments(whole)
    anchor = _open_person_scroll_anchor(cleaned, whole_c)
    if anchor is not None:
        return bool(_TL_LOADING_FALSE.search(cleaned[:anchor]))
    m = _TL_LOADING_FALSE.search(cleaned)
    if not m:
        return False
    after = cleaned[m.end() :]
    for call in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", after):
        name = call.group(1)
        if name in _SCROLL_HELPER_SKIP:
            continue
        body = _function_body(whole_c, name)
        if body and _open_person_scroll_anchor(_without_comments(body), whole_c) is not None:
            return True
    return False


def _nested_raf_around_open_scroll(app: str, logic: str) -> bool:
    """True if a requestAnimationFrame callback itself schedules another rAF that scrolls to latest."""
    whole = _without_comments(app + "\n" + logic)
    for m in _RAF_CALL.finditer(whole):
        arg = _call_arg(whole, m.end() - 1)
        if not arg or not _RAF_CALL.search(arg):
            continue
        if _contains_open_latest_scroll(arg, whole):
            return True
    return False


def assert_timeline_latest(crate: Path) -> None:
    """#113: newest at bottom; Load older at top; prepend without jump; pad / scroll after layout.

    Narrow-pane dogfood: clear tlLoading before the open-person scroll; nested rAF for wrap.
    """
    app = (crate / "web" / "App.svelte").read_text()
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


# #120 — virtualize person timeline (visible + overscan only in the DOM).
# Static analysis: fail naive full {#each dayGroups}→{#each group.rows} without a window.
# No FPS/perf assertions in CI; dogfood measures 10k scroll.
_VIRT_SIGNAL = re.compile(
    r"("
    r"\boverscan\b"
    r"|\bvirtual(?:ize|ized|izing|isation|ization)?\b"
    r"|\bVirtualList\b"
    r"|\bvirtual(?:List|Rows?|Window|Scroll|Range|Items?)\b"
    r"|\bwindow(?:ed|ing)(?:Rows?|Items?|Groups?|Range|Start|End|Slice|Timeline|DayGroups?)?\b"
    r"|\bvisible(?:Range|Start|End|Count|Window|Slice|Rows?|Items?|Groups?|DayGroups?|"
    r"Indices|Index)\b"
    r"|\b(?:start|end)(?:Index|Row|Offset)\b"
    r"|\b(?:first|last)Visible(?:Index|Row|Item)?\b"
    r"|\brender(?:ed)?(?:Rows?|Items?|Range|Window|Slice|Groups?)\b"
    r"|\bviewport(?:Rows?|Range|Height|Top)\b"
    r"|\b(?:row|item)(?:Height|Size)\b"
    r"|\bestimated(?:Row|Item)?(?:Height|Size)\b"
    r"|\btotalHeight\b"
    r"|\bspacer(?:Height|Top|Bottom)?\b"
    r"|\bscrollMargin\b"
    r"|\bsvelte-virtual(?:-list)?\b"
    r"|@tanstack/(?:svelte-)?virtual\b"
    r"|\bcreateVirtualizer\b"
    r"|\buseVirtualizer\b"
    r"|\bVirtualizer\b"
    r")",
    re.I,
)
# Classic anti-pattern: full dayGroups then every group.rows (no window).
_NAIVE_DAYGROUPS_ROWS = re.compile(
    r"\{#each\s+dayGroups\b[^}]*\}[\s\S]{0,1200}?\{#each\s+group\.rows\b",
    re.I,
)
# Full unwindowed list each (flat timeline / filtered list of every row).
_NAIVE_FULL_ROW_EACH = re.compile(
    r"\{#each\s+(?:timeline|filteredTimeline)\b",
    re.I,
)
_BODY_INNER_HTML = re.compile(
    r"("
    r"\{@html\b"
    r"|\.innerHTML\s*="
    r"|insertAdjacentHTML\s*\("
    r")",
)
_SCOPE_10M = re.compile(
    r"("
    r"10\s*[Mm](?:illion)?\b[^.\n]{0,80}"
    r"(?:one view|single view|in (?:the )?DOM|all (?:at )?once|in one (?:list|view))"
    r"|(?:render|mount|load)\s+(?:all\s+)?10\s*[Mm]"
    r")",
    re.I,
)
_SCOPE_LAZY_EVERY_PHOTO = re.compile(
    r"("
    r"lazy[- ]decode\s+every\s+(?:photo|image|cas|attachment)"
    r"|decode\s+every\s+(?:photo|image)\s+laz"
    r"|lazyDecodeEvery"
    r")",
    re.I,
)
_JK_KEY = re.compile(
    r"("
    r"key\s*===?\s*[\"']j[\"']"
    r"|[\"']j[\"']\s*===?\s*key"
    r"|key\s*===?\s*[\"']k[\"']"
    r"|[\"']k[\"']\s*===?\s*key"
    r"|visibleTlIndices"
    r"|nearestVisibleTlIndex"
    r")",
    re.I,
)


def _derived_body(cleaned: str, name: str) -> str | None:
    """Return the body of `const name = $derived...` / `$derived.by` if present."""
    m = re.search(
        rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*\$derived(?:\.by)?\s*\(",
        cleaned,
    )
    if not m:
        return None
    open_idx = m.end() - 1
    close = _match_closer(cleaned, open_idx)
    if close < 0:
        return cleaned[m.end() : m.end() + 2500]
    return cleaned[open_idx + 1 : close]


def _body_has_row_window(body: str) -> bool:
    """True if a derived-list body actually bounds rows (not only ISO day slice)."""
    if re.search(
        r"\boverscan\b|\bvirtual|\bwindow(?:ed|ing|Start|End|Range)|"
        r"\bvisible(?:Range|Start|End|Window|Slice|Rows?|Groups?)|"
        r"\b(?:start|end)(?:Index|Row)\b|"
        r"\b(?:first|last)Visible\b|"
        r"createVirtualizer|useVirtualizer",
        body,
        re.I,
    ):
        return True
    # .slice(a, b) row window — exclude the common day-prefix .slice(0, 10).
    for sm in re.finditer(r"\.slice\s*\(\s*([^)]*)\)", body):
        args = sm.group(1)
        if re.match(r"\s*0\s*,\s*10\s*$", args):
            continue
        if "," in args:
            return True
    return False


def _list_source_is_windowed(cleaned: str, name: str) -> bool:
    """True if `name` is derived/assigned with a real row window (not a rename alone)."""
    body = _derived_body(cleaned, name)
    if body and _body_has_row_window(body):
        return True
    # Non-$derived assignment / helper: name = windowRows(...) / slice(...)
    m = re.search(
        rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*(?!\$derived)([^;]{{0,400}})",
        cleaned,
    )
    if m and _body_has_row_window(m.group(1)):
        return True
    if re.search(
        rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*"
        r"(?:\$derived(?:\.by)?\s*\()?"
        r"[\s\S]{0,240}"
        r"(?:window(?:ed|ing)\w*|virtual(?:ize|Rows|List|Items?)?|"
        r"visible(?:Range|Rows|Groups?|Window)|"
        r"overscan|createVirtualizer|useVirtualizer)",
        cleaned,
        re.I,
    ):
        return True
    return False


def _timeline_each_names_in_markup(markup: str) -> list[str]:
    """Names used in {#each ...} that look like timeline row sources."""
    names: list[str] = []
    for m in re.finditer(r"\{#each\s+([A-Za-z_]\w*)\b", markup):
        name = m.group(1)
        if name in _TIMELINE_EACH_NAMES or re.match(
            r"^(?:windowed|visible|virtual|rendered)",
            name,
            re.I,
        ):
            names.append(name)
        elif name in {"timeline", "filteredTimeline", "dayGroups"}:
            names.append(name)
    return names


def _naive_full_timeline_mount(markup: str, cleaned: str) -> bool:
    """True if the person timeline always mounts every filtered row (no window)."""
    # 1) {#each dayGroups} → {#each group.rows} with unwindowed dayGroups.
    if _NAIVE_DAYGROUPS_ROWS.search(markup):
        if not _list_source_is_windowed(cleaned, "dayGroups"):
            return True
    # 2) Flat {#each timeline|filteredTimeline} without windowing that source.
    for m in _NAIVE_FULL_ROW_EACH.finditer(markup):
        mm = re.search(r"\{#each\s+(\w+)", m.group(0))
        name = mm.group(1) if mm else "timeline"
        if not _list_source_is_windowed(cleaned, name):
            return True
    # 3) Any timeline-ish each whose source is not windowed (rename without window).
    for name in _timeline_each_names_in_markup(markup):
        if name in {"dayGroups", "timeline", "filteredTimeline"}:
            continue  # already covered; dayGroups alone without rows is headings-only
        # Nested group.rows is not a top-level list name.
        if not _list_source_is_windowed(cleaned, name):
            # Only treat as naive if the each body looks like message rows.
            for em in re.finditer(rf"\{{#each\s+{re.escape(name)}\b[^}}]*\}}", markup):
                end = _matching_each_end(markup, em.start())
                chunk = markup[em.start() : end if end > 0 else em.start() + 800]
                if re.search(
                    r"from_me|body_text|data-from-me|bubble-me|group\.rows",
                    chunk,
                    re.I,
                ):
                    return True
    return False


def _has_windowed_render_path(markup: str, cleaned: str) -> bool:
    """True if some timeline {#each} iterates a really windowed list (or VirtualList)."""
    for name in _timeline_each_names_in_markup(markup):
        if _list_source_is_windowed(cleaned, name):
            return True
    # Virtual list component / helper owns the window even without a named slice.
    if re.search(
        r"<Virtual(?:List|Scroll|izer)?\b|createVirtualizer\s*\(|useVirtualizer\s*\(",
        markup + "\n" + cleaned,
        re.I,
    ):
        return True
    # dayGroups itself windowed (still named dayGroups) + nested group.rows.
    if re.search(r"\{#each\s+dayGroups\b", markup) and _list_source_is_windowed(
        cleaned, "dayGroups"
    ):
        return True
    return False


def assert_virtualized_timeline(crate: Path) -> None:
    """#120: window person timeline (visible + overscan); keep j/k + Load older.

    Acceptance: synthetic 10k DM does not lock the window — only visible + overscan
    rows (and needed day headings) mount. Bodies still text nodes.
    Static gate: fail naive full {#each dayGroups}→{#each group.rows} without a
    window. No FPS assertions in CI (dogfood measures scroll).
    Not: 10M in one view, lazy-decode every photo.
    """
    app = (crate / "web" / "App.svelte").read_text()
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
_TL_INDEX_READ = re.compile(
    r"("
    r"\[data-tl-index\]"
    r"|getAttribute\s*\(\s*[\"']data-tl-index[\"']"
    r"|dataset\.tlIndex"
    r")"
)
_HEIGHT_OF = re.compile(
    r"\b("
    r"heightOf"
    r"|rowHeightOf"
    r"|heightAt"
    r"|tlHeightOf"
    r"|rowHeightAt"
    r")\b"
)
_OFFSET_OF = re.compile(
    r"\b("
    r"offsetOf"
    r"|rowOffsetOf"
    r"|offsetAt"
    r"|tlOffsetOf"
    r"|rowOffsetAt"
    r"|prefixSum(?:s|Of)?"
    r"|prefixOffset"
    r"|rowOffsets"
    r")\b"
)
_LIVE_AVG = re.compile(
    r"\b("
    r"measuredSum"
    r"|measuredCount"
    r"|measuredAvg"
    r"|averageHeight"
    r"|avgHeight"
    r"|medianHeight"
    r"|runningAverage"
    r"|meanHeight"
    r")\b"
)
_FIXED_INDEX_TIMES_EST = re.compile(
    r"("
    r"(?:startIndex|endIndex|\bpos\b|\bindex\b|tlIndex)"
    r"\s*\*\s*(?:ESTIMATED_ROW_HEIGHT|88)\b"
    r"|(?:ESTIMATED_ROW_HEIGHT|88)\s*\*\s*"
    r"(?:startIndex|endIndex|\bpos\b|\bindex\b|tlIndex)"
    r"|(?:\.length\s*-\s*(?:visibleRange\.)?endIndex)"
    r"\s*\*\s*(?:ESTIMATED_ROW_HEIGHT|88)\b"
    r")"
)
_SCROLL_DIV_EST = re.compile(
    r"(?:tlScrollTop|scrollTop)\s*/\s*(?:ESTIMATED_ROW_HEIGHT|88)\b"
)
_CONST_FALLBACK = re.compile(
    r"(?:\?\?|\|\||:\s*|=\s*)ESTIMATED_ROW_HEIGHT\b"
    r"|\bESTIMATED_ROW_HEIGHT\b[^;\n]{0,40}\?\?"
)
_HEIGHT_OF_NAMES = (
    "heightOf",
    "rowHeightOf",
    "heightAt",
    "tlHeightOf",
    "rowHeightAt",
)
_OFFSET_OF_NAMES = (
    "offsetOf",
    "rowOffsetOf",
    "offsetAt",
    "tlOffsetOf",
    "rowOffsetAt",
    "prefixSum",
    "prefixSumOf",
    "prefixOffset",
)


def _row_measure_path(cleaned: str) -> bool:
    """True if JS measures [data-tl-index] into a height cache (not pin-latest)."""
    if not _HEIGHT_CACHE.search(cleaned):
        return False
    if not _TL_INDEX_READ.search(cleaned):
        return False
    if re.search(r"\bgetBoundingClientRect\s*\(", cleaned):
        return True
    for m in re.finditer(r"new\s+ResizeObserver\s*\(", cleaned):
        arg = _call_arg(cleaned, cleaned.find("(", m.start()))
        if not arg:
            continue
        # #113 pin-latest only slams scrollTop = scrollHeight.
        if re.search(r"scrollHeight", arg) and not (
            _HEIGHT_CACHE.search(arg) or _TL_INDEX_READ.search(arg)
        ):
            continue
        if (
            _HEIGHT_CACHE.search(arg)
            or _TL_INDEX_READ.search(arg)
            or re.search(r"contentRect|\.height\b", arg)
        ):
            return True
    # Svelte action / $effect: observer + cache + [data-tl-index] in one file.
    return bool(re.search(r"\bResizeObserver\b", cleaned))


def _uses_prefix_sum(body: str) -> bool:
    if not body:
        return False
    if _OFFSET_OF.search(body) or _HEIGHT_OF.search(body):
        return True
    if re.search(r"\b(?:rowOffsets|prefixSums|offsets)\s*\[", body):
        return True
    return False


def _height_lookup_uses_constant(cleaned: str) -> bool:
    """Unmeasured slots must be ESTIMATED_ROW_HEIGHT, not a live average."""
    for name in _HEIGHT_OF_NAMES:
        body = _function_body(cleaned, name)
        if body:
            return bool(re.search(r"\bESTIMATED_ROW_HEIGHT\b", body))
        m = re.search(
            rf"(?:const|let|var|function)\s+{name}\b[\s\S]{{0,240}}"
            r"ESTIMATED_ROW_HEIGHT",
            cleaned,
        )
        if m:
            return True
    # Inline cache miss: rowHeights.get(i) ?? ESTIMATED_ROW_HEIGHT
    return bool(
        _HEIGHT_CACHE.search(cleaned)
        and _CONST_FALLBACK.search(cleaned)
        and re.search(
            rf"(?:{_HEIGHT_CACHE.pattern})\s*(?:\?\.|\.)?(?:get|\[\s*)",
            cleaned,
        )
    )


def assert_variable_height_timeline(crate: Path) -> None:
    """#224: measure-and-cache row heights; prefix-sum spacers; constant 88.

    Keep the #120 window. Unmeasured slots stay ESTIMATED_ROW_HEIGHT (not a
    live average). CI proves source shapes, not FPS.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#224: App.svelte required (variable-height person timeline)")
    app = app_path.read_text()
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
