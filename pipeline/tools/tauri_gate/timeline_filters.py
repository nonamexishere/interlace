"""Timeline platform / kind filter chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.timeline_filters_lib import *


def assert_timeline_platform_chips(crate: Path) -> None:
    """#115: platform chip on each bubble + All + data-derived platform toolbar.

    Acceptance: “WhatsApp only” hides Gmail for that person. Chip is text/badge,
    not a remote CDN brand image. Toolbar offers All plus only platforms present
    for this person (from conversations / timeline) — dynamic {#each} is OK;
    a forever-visible WhatsApp+Gmail button matrix is not required. Client filter
    on row.platform is OK; API/core platform arg also OK when paging.
    """
    app = _web_logic(crate)
    logic = _web_logic(crate)
    api_src = (crate / "web" / "lib" / "api.ts").read_text()
    whole = app + "\n" + logic
    cleaned = _without_comments(whole)
    block = _timeline_block(crate)
    blob = "\n".join(p.read_text() for p in _web_sources(crate))
    detail = _person_detail_markup(app)

    # 1) Bubble/row shows platform as a chip/badge — not only bare caption text.
    chip_in_row = bool(_PLATFORM_CHIP.search(block)) and (
        "platform" in block or "platformLabel" in block or "PlatformChip" in block
    )
    if not chip_in_row:
        chip_in_row = bool(_PLATFORM_CHIP_NEAR.search(block))
    if not chip_in_row:
        # Dedicated chip component used from the row (markup may live next door).
        chip_component = bool(
            re.search(
                r"<(?:PlatformChip|platform-chip)\b|data-platform-chip",
                block,
                re.I,
            )
        ) or (
            bool(re.search(r"data-platform-chip|PlatformChip|platform-chip", blob, re.I))
            and bool(
                re.search(
                    r"<(?:PlatformChip|platform-chip)\b|data-platform-chip",
                    block + "\n" + cleaned,
                    re.I,
                )
            )
        )
        if not chip_component:
            fail(
                "#115: each timeline bubble/row must show platform as a chip "
                "(text chip / badge / data-platform-chip), not only bare caption "
                "text like {row.platform}"
            )
    if not re.search(r"\.platform\b|platformLabel|row\.platform", block + "\n" + cleaned):
        fail("#115: chip must still come from the row/conversation platform field")

    # 2) Chip is not a remote image / CDN brand logo.
    timeline_chrome = block + "\n" + detail
    if _REMOTE_PLATFORM_IMG.search(timeline_chrome) or _REMOTE_PLATFORM_IMG.search(blob):
        fail("#115: platform chip must not be a remote <img> / CDN brand logo")
    if _REMOTE_PLATFORM_URL.search(blob):
        fail("#115: platform chip must not load brand logos via url(https://…)")
    if re.search(
        r"<img\b[^>]{0,200}(?:platform|whatsapp|gmail)[^>]{0,200}"
        r"src\s*=\s*[\"']https?://",
        blob,
        re.I | re.S,
    ):
        fail("#115: platform chip must not be an http(s) image (text chip only)")

    # Pretty labels (WhatsApp / Gmail) are OK; raw whatsapp/gmail also OK on chip.
    has_pretty = bool(_PRETTY_WHATSAPP.search(cleaned) and _PRETTY_GMAIL.search(cleaned))
    has_map = bool(_PRETTY_PLATFORM_MAP.search(cleaned))
    if not (has_pretty or has_map or _RAW_WHATSAPP.search(block)):
        # Still require some platform surface on the row.
        if "row.platform" not in block and ".platform" not in block:
            fail(
                "#115: chip may use pretty labels (WhatsApp / Gmail) or raw "
                "platform; must still bind the row platform"
            )

    # 3) Platform filter toolbar: All + data-derived options (not conversation switcher alone).
    # Dynamic {#each availablePlatforms} is OK — do not require WhatsApp and Gmail
    # as always-rendered static buttons for every person.
    has_filter_state = bool(_PLATFORM_FILTER_STATE.search(cleaned))
    has_filter_hook = bool(_PLATFORM_FILTER_HOOK.search(blob))
    toolbar_blob = detail if detail.strip() else app
    # Exclude the message {#each} body so conversation switcher / caption is not enough.
    toolbar_only = toolbar_blob
    for m in _EACH_TIMELINE.finditer(toolbar_blob):
        end = _matching_each_end(toolbar_blob, m.start())
        if end > m.start():
            toolbar_only = toolbar_only.replace(toolbar_blob[m.start() : end], "", 1)
    has_toolbar_all = bool(_PLATFORM_TOOLBAR_ALL.search(toolbar_only)) or bool(
        _PLATFORM_TOOLBAR_ALL.search(cleaned)
    )
    has_dynamic_each = bool(
        re.search(
            r"\{#each\s+(?:availablePlatforms|platformOptions|presentPlatforms|"
            r"personPlatforms|timelinePlatforms|platformsFor)\b",
            toolbar_only + "\n" + app,
            re.I,
        )
    )
    options_from_data = bool(_PLATFORM_OPTIONS_FROM_DATA.search(cleaned))
    if not (has_filter_state or has_filter_hook):
        fail(
            "#115: person timeline must have a platform filter toolbar state "
            "(selectedPlatform / platformFilter / data-platform-filter) — "
            "All + platforms present for this person"
        )
    if not has_toolbar_all:
        fail(
            "#115: platform filter toolbar must offer All when the platform "
            "dimension is active (default = every platform)"
        )
    if not options_from_data:
        fail(
            "#115: platform toolbar options must come from platforms present for "
            "this person (unique platform values from conversations / timeline "
            "via map/Set/for…of), not a hard-coded forever list"
        )
    # Labels / raw values may live only in a helper; dynamic each is enough chrome.
    if not (
        has_dynamic_each
        or has_pretty
        or has_map
        or re.search(
            r"(?:platformFilter|selectedPlatform|timelinePlatform|tlPlatform|"
            r"activePlatform|filterPlatform|platformOnly)[^;]{0,200}"
            r"[\"'](?:whatsapp|gmail)[\"']",
            cleaned,
            re.I | re.S,
        )
        or re.search(r">\s*(?:WhatsApp|Gmail)\s*<|[\"'](?:WhatsApp|Gmail)[\"']", cleaned)
    ):
        fail(
            "#115: platform filter must surface platform options "
            "(data-derived {#each}, pretty labels, or raw platform values)"
        )

    # Default selection is All (null / undefined / "all").
    if not re.search(
        r"(?:selectedPlatform|platformFilter|timelinePlatform|tlPlatform|"
        r"activePlatform|pickedPlatform|filterPlatform|platformOnly|"
        r"timelinePlatformFilter)"
        r"\s*=\s*\$state\s*(?:<[^>]*>)?\s*\(\s*(?:null|undefined|[\"']all[\"'])",
        cleaned,
        re.I,
    ) and not re.search(
        r"(?:selectedPlatform|platformFilter|timelinePlatform|tlPlatform|"
        r"activePlatform|filterPlatform|platformOnly)"
        r"\s*=\s*(?:null|undefined|[\"']all[\"'])",
        cleaned,
        re.I,
    ):
        fail(
            "#115: platform filter must default to All "
            "(selected platform state starts null / undefined / \"all\")"
        )

    # 4) Filtering WhatsApp excludes other platforms (client row.platform or API arg).
    client_ok = bool(_CLIENT_PLATFORM_FILTER.search(cleaned))
    api_ok = bool(_API_PLATFORM_FILTER.search(cleaned))
    # Also accept derived list filtered by platform before {#each}.
    derived_ok = bool(
        re.search(
            r"(?:filteredTimeline|visibleTimeline|timelineRows|platformRows|"
            r"shownTimeline|displayTimeline|tlRows)"
            r"[^;]{0,300}\.platform\b"
            r"|\.platform\b[^;]{0,200}"
            r"(?:filteredTimeline|visibleTimeline|platformRows|displayTimeline)",
            cleaned,
            re.I | re.S,
        )
    )
    if not (client_ok or api_ok or derived_ok):
        fail(
            "#115: “WhatsApp only” must hide other platforms for that person "
            "(filter timeline rows by row.platform client-side, or pass platform "
            "into personTimeline / the core query so Load older stays consistent)"
        )

    # If filter is pushed into the API, personTimeline args must accept platform.
    if api_ok:
        api_args = re.search(
            r"personTimeline\s*:\s*\(\s*args\s*:\s*\{([^}]*)\}",
            api_src,
            re.S,
        )
        if not api_args or not re.search(r"\bplatform\b", api_args.group(1)):
            fail(
                "#115: personTimeline args must include optional platform when "
                "the UI passes a platform filter into the timeline query"
            )

    # 5) Only platforms present for this person — not a hard-coded invented forever-list.
    # (options_from_data already required in §3; still reject invented-only lists.)
    for m in _INVENTED_PLATFORM_LIST.finditer(cleaned):
        window = cleaned[max(0, m.start() - 80) : m.end() + 80]
        if re.search(
            r"platformFilter|selectedPlatform|platformOptions|toolbar|platforms\s*=",
            window,
            re.I,
        ) and not _PLATFORM_OPTIONS_FROM_DATA.search(
            cleaned[max(0, m.start() - 400) : m.end() + 400]
        ):
            fail(
                "#115: do not invent toolbar platforms (slack/discord/…) — "
                "only offer platforms that exist for this person"
            )

from tauri_gate.timeline_filters_more import assert_timeline_kind_filter
