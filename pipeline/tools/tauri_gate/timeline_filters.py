"""Timeline platform / kind filter chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import fail

from tauri_gate.scan import (
    _INCLUDE_GROUPS_LABEL,
    _PRETTY_GMAIL,
    _RAW_WHATSAPP,
    _matching_each_end,
    _timeline_block,
    _web_logic,
    _web_sources,
    _without_comments,
)

from tauri_gate.people_switcher_label import _PRETTY_WHATSAPP

from tauri_gate.status_toasts import _person_detail_markup

from tauri_gate.timeline_scroll import (
    _EACH_TIMELINE,
    _VISIBLE_KIND_JK,
)




def _svelte_snippet_body(src: str, name: str) -> str:
    """Body of `{#snippet name …}…{/snippet}` (no nested snippet support)."""
    head = re.search(rf"\{{#snippet\s+{re.escape(name)}\b[^}}]*\}}", src)
    if not head:
        return ""
    end = src.find("{/snippet}", head.end())
    if end < 0:
        return src[head.end() :]
    return src[head.end() : end]


def _person_detail_with_renders(app: str) -> str:
    """Person-column markup plus any `{@render snippet()}` bodies it invokes."""
    detail = _person_detail_markup(app)
    extra: list[str] = []
    for m in re.finditer(r"\{@render\s+([A-Za-z_]\w*)\s*\(", detail):
        extra.append(_svelte_snippet_body(app, m.group(1)))
    return detail + ("\n" + "\n".join(extra) if extra else "")


# #115 — platform chip on timeline bubbles + All | platform toolbar filter.
_PLATFORM_CHIP = re.compile(
    r"("
    r"data-platform-chip"
    r"|platform-chip"
    r"|platformChip"
    r"|class:[A-Za-z0-9_-]*chip\b"
    r"|class=[\"'][^\"']*\b(?:platform-)?chip\b"
    r"|class=[\"'][^\"']*\bbadge\b"
    r"|class:badge\b"
    r"|class=\{[^}]*(?:chip|badge)[^}]*\}"
    r")",
    re.I,
)
_PLATFORM_CHIP_NEAR = re.compile(
    r"("
    r"data-platform-chip"
    r"|platform-chip"
    r"|platformChip"
    r"|\bchip\b[^;{]{0,160}(?:\.platform\b|platformLabel|platform)"
    r"|(?:\.platform\b|platformLabel|platform)[^;{]{0,160}\bchip\b"
    r"|\bbadge\b[^;{]{0,160}(?:\.platform\b|platformLabel|platform)"
    r"|(?:\.platform\b|platformLabel|platform)[^;{]{0,160}\bbadge\b"
    r")",
    re.I | re.S,
)
_REMOTE_PLATFORM_IMG = re.compile(
    r"<img\b[^>]{0,400}https?://[^>]{0,200}"
    r"(?:logo|brand|whatsapp|gmail|favicon|cdn)",
    re.I | re.S,
)
_REMOTE_PLATFORM_URL = re.compile(
    r"url\(\s*['\"]?https?://[^)]*(?:logo|brand|whatsapp|gmail|cdn)",
    re.I,
)
_PLATFORM_FILTER_STATE = re.compile(
    r"\b(?:"
    r"selectedPlatform|platformFilter|timelinePlatform|tlPlatform|"
    r"platformTab|activePlatform|pickedPlatform|filterPlatform|"
    r"platformOnly|timelinePlatformFilter"
    r")\b"
)
_PLATFORM_FILTER_HOOK = re.compile(
    r"(data-platform-filter|id=[\"']platform-filter[\"']|"
    r"data-timeline-platform|class=[\"'][^\"']*platform-filter)",
    re.I,
)
_PLATFORM_TOOLBAR_ALL = re.compile(
    r"("
    r">\s*All\s*<"
    r"|[\"']All[\"']"
    r"|platformFilter\s*===\s*[\"']all[\"']"
    r"|selectedPlatform\s*(?:===?|==)\s*(?:null|undefined|[\"']all[\"'])"
    r")",
    re.I,
)
_PRETTY_PLATFORM_MAP = re.compile(
    r"("
    r"[\"']whatsapp[\"']\s*[:=]\s*[\"']WhatsApp[\"']"
    r"|[\"']gmail[\"']\s*[:=]\s*[\"']Gmail[\"']"
    r"|case\s+[\"']whatsapp[\"']\s*:[^;]{0,40}WhatsApp"
    r"|case\s+[\"']gmail[\"']\s*:[^;]{0,40}Gmail"
    r"|platform\s*===\s*[\"']whatsapp[\"'][^?]{0,40}\?\s*[\"']WhatsApp[\"']"
    r"|platform\s*===\s*[\"']gmail[\"'][^?]{0,40}\?\s*[\"']Gmail[\"']"
    r")",
    re.I,
)
# Client-side: keep row when All or row.platform matches the selection.
_CLIENT_PLATFORM_FILTER = re.compile(
    r"("
    r"\.filter\s*\(\s*(?:\(?)(?:row|r|item|m|msg|t|tl)[^)]{0,80}"
    r"\.platform\b"
    r"|(?:row|r|item|m)\.platform\s*===?\s*(?:selectedPlatform|platformFilter|"
    r"timelinePlatform|tlPlatform|activePlatform|pickedPlatform|filterPlatform|"
    r"platformOnly|p|plat)\b"
    r"|(?:selectedPlatform|platformFilter|timelinePlatform|tlPlatform|"
    r"activePlatform|pickedPlatform|filterPlatform|platformOnly)"
    r"\s*===?\s*(?:row|r|item|m)\.platform\b"
    r"|(?:selectedPlatform|platformFilter|timelinePlatform|tlPlatform|"
    r"activePlatform|filterPlatform)\s*(?:===?|==)\s*[\"']all[\"']"
    r"[^|]{0,80}\|\|"
    r")",
    re.I | re.S,
)
# API / core: personTimeline({ … platform: … }) or person_timeline platform arg.
_API_PLATFORM_FILTER = re.compile(
    r"("
    r"personTimeline\s*\(\s*\{[^}]{0,400}\bplatform\s*:"
    r"|\bplatform\s*:\s*(?:selectedPlatform|platformFilter|timelinePlatform|"
    r"tlPlatform|activePlatform|filterPlatform|null)"
    r")",
    re.I | re.S,
)
# Toolbar options come from this person's conversations / timeline platforms.
_PLATFORM_OPTIONS_FROM_DATA = re.compile(
    r"("
    r"(?:conversations|convos|timeline|personConversations|conversationList)"
    r"\s*(?:\?\.|\.)\s*(?:map|flatMap|reduce|forEach|filter)\s*\([^)]{0,120}"
    r"\.platform\b"
    r"|\.platform\b[\s\S]{0,100}(?:Set|unique|uniq|platformsFor|personPlatforms|"
    r"availablePlatforms|timelinePlatforms|presentPlatforms)"
    r"|(?:Set|unique|uniq|platformsFor|personPlatforms|availablePlatforms|"
    r"timelinePlatforms|presentPlatforms|platformOptions)"
    r"[\s\S]{0,180}\.platform\b"
    r"|new\s+Set\s*\([^)]{0,200}\.platform\b"
    r"|for\s*\(\s*(?:const|let)\s+\w+\s+of\s+"
    r"(?:conversations|convos|timeline|personConversations)\b[^)]{0,80}\)"
    r"[\s\S]{0,220}\.platform\b"
    r"|(?:conversations|convos|timeline|personConversations)"
    r"[\s\S]{0,220}\.platform\b[\s\S]{0,80}(?:add|push|Set)"
    r"|\{#each\s+(?:availablePlatforms|platformOptions|presentPlatforms|"
    r"personPlatforms|timelinePlatforms)\b"
    r")",
    re.I | re.S,
)
# Hard-coded forever list of invented platforms (slack/discord/telegram/signal…)
# used as the toolbar source without deriving from the person.
_INVENTED_PLATFORM_LIST = re.compile(
    r"\[\s*[\"'](?:whatsapp|gmail|contacts)[\"']\s*,\s*"
    r"[\"'](?:whatsapp|gmail|contacts|telegram|signal|slack|discord|imessage|"
    r"sms|messenger|instagram|twitter)[\"']"
    r"[^\]]{0,200}\]",
    re.I,
)

# #116 — conversation kind filter (All | dm | email_thread | group).
_KIND_FILTER_STATE = re.compile(
    r"\b(?:"
    r"kindFilter|conversationKindFilter|timelineKind|tlKind|"
    r"selectedKind|activeKind|pickedKind|filterKind|"
    r"kindOnly|timelineKindFilter|conversationKind|"
    r"kindTab|selectedConversationKind"
    r")\b"
)
_KIND_FILTER_HOOK = re.compile(
    r"(data-kind-filter|id=[\"']kind-filter[\"']|"
    r"data-timeline-kind|class=[\"'][^\"']*kind-filter|"
    r"aria-label=[\"'][^\"']*[Kk]ind)",
    re.I,
)
_KIND_TOOLBAR_ALL = re.compile(
    r"("
    r">\s*All\s*<"
    r"|[\"']All[\"']"
    r"|kindFilter\s*===\s*[\"']all[\"']"
    r"|conversationKindFilter\s*===\s*[\"']all[\"']"
    r"|selectedKind\s*(?:===?|==)\s*(?:null|undefined|[\"']all[\"'])"
    r"|timelineKind\s*(?:===?|==)\s*(?:null|undefined|[\"']all[\"'])"
    r")",
    re.I,
)
# Pretty labels or raw archive kinds in helpers / options (not required all-at-once).
_KIND_OPT_DM = re.compile(
    r"("
    r">\s*DMs?\s*<"
    r"|[\"']DMs?[\"']"
    r"|[\"']dm[\"']"
    r")",
    re.I,
)
_KIND_OPT_EMAIL = re.compile(
    r"("
    r">\s*Email(?:\s+threads?)?\s*<"
    r"|[\"']Email(?:\s+threads?)?[\"']"
    r"|[\"']email_thread[\"']"
    r"|[\"']email[\"']"
    r")",
    re.I,
)
_KIND_OPT_GROUP = re.compile(
    r"("
    r">\s*Groups?\s*<"
    r"|[\"']Groups?[\"']"
    r"|[\"']group[\"']"
    r")",
    re.I,
)
# Kind toolbar options come from this person's conversations / timeline kinds.
# Dynamic {#each availableKinds} is OK for chrome, but the list itself must be
# harvested from data (not a hard-coded forever All|DMs|Email|Groups matrix).
# PersonConversation uses `.kind`; TimelineRow uses `.conversation_kind`.
# Require collecting into a Set/array (add/push) so the filteredTimeline row
# filter alone is not mistaken for option derivation.
_KIND_OPTIONS_FROM_DATA = re.compile(
    r"("
    r"for\s*\(\s*(?:const|let)\s+\w+\s+of\s+"
    r"(?:conversations|convos|timeline|personConversations)\b[^)]{0,80}\)"
    r"[\s\S]{0,220}\.(?:conversation_kind|kind)\b[\s\S]{0,80}(?:\.add\b|push\s*\()"
    r"|(?:availableKinds|kindOptions|presentKinds|personKinds|timelineKinds|"
    r"kindsPresent)\b[\s\S]{0,500}"
    r"(?:for\s*\(\s*(?:const|let)\s+\w+\s+of\s+"
    r"(?:conversations|convos|timeline|personConversations)\b"
    r"|(?:conversations|convos|timeline|personConversations)\s*"
    r"(?:\?\.|\.)\s*(?:map|flatMap|reduce|forEach)\b)"
    r"[\s\S]{0,240}\.(?:conversation_kind|kind)\b"
    r"|(?:conversations|convos|timeline|personConversations)\s*"
    r"(?:\?\.|\.)\s*(?:map|flatMap)\s*\(\s*\w+\s*=>\s*\w+\.(?:conversation_kind|kind)\b"
    r"|new\s+Set\s*\(\s*(?:conversations|convos|timeline|personConversations)"
    r"\s*(?:\?\.|\.)\s*map\s*\([^)]{0,80}\.(?:conversation_kind|kind)\b"
    r")",
    re.I | re.S,
)
# Forever-hard-coded kind toolbar: static onclick targets for dm + email_thread +
# group without a data-derived options list (WhatsApp path must not force Email).
_STATIC_KIND_MATRIX = re.compile(
    r"(?:kindFilter|conversationKindFilter|timelineKind|selectedKind|filterKind)"
    r"\s*=\s*[\"']dm[\"']"
    r"[\s\S]{0,500}"
    r"(?:kindFilter|conversationKindFilter|timelineKind|selectedKind|filterKind)"
    r"\s*=\s*[\"']email_thread[\"']"
    r"[\s\S]{0,500}"
    r"(?:kindFilter|conversationKindFilter|timelineKind|selectedKind|filterKind)"
    r"\s*=\s*[\"']group[\"']",
    re.I,
)
# Client-side: keep row when All or row.conversation_kind matches.
_CLIENT_KIND_FILTER = re.compile(
    r"("
    r"\.filter\s*\(\s*(?:\(?)(?:row|r|item|m|msg|t|tl|x)[^)]{0,100}"
    r"\.conversation_kind\b"
    r"|(?:row|r|item|m|x)\.conversation_kind\s*===?\s*"
    r"(?:kindFilter|conversationKindFilter|timelineKind|tlKind|"
    r"selectedKind|activeKind|pickedKind|filterKind|kindOnly|k|kind)\b"
    r"|(?:kindFilter|conversationKindFilter|timelineKind|tlKind|"
    r"selectedKind|activeKind|pickedKind|filterKind|kindOnly)"
    r"\s*===?\s*(?:row|r|item|m|x)\.conversation_kind\b"
    r"|(?:kindFilter|conversationKindFilter|timelineKind|tlKind|"
    r"selectedKind|filterKind|kindOnly)"
    r"\s*(?:===?|==)\s*[\"']all[\"']"
    r"[^|]{0,100}\|\|"
    r"|conversation_kind\s*===?\s*[\"'](?:dm|email_thread|group)[\"']"
    r")",
    re.I | re.S,
)
# Derived list that reads conversation_kind (filteredTimeline / visibleTimeline…).
_DERIVED_KIND_FILTER = re.compile(
    r"("
    r"(?:filteredTimeline|visibleTimeline|timelineRows|kindRows|"
    r"shownTimeline|displayTimeline|tlRows|visibleRows)"
    r"[^;]{0,400}\.conversation_kind\b"
    r"|\.conversation_kind\b[^;]{0,300}"
    r"(?:filteredTimeline|visibleTimeline|kindRows|displayTimeline|"
    r"shownTimeline|tlRows)"
    r")",
    re.I | re.S,
)
# API / core: personTimeline({ … kind: … }) — optional; client-side is enough.
_API_KIND_FILTER = re.compile(
    r"("
    r"personTimeline\s*\(\s*\{[^}]{0,400}\b(?:kind|conversation_kind)\s*:"
    r"|\b(?:kind|conversationKind)\s*:\s*(?:kindFilter|conversationKindFilter|"
    r"timelineKind|tlKind|selectedKind|activeKind|filterKind|null)"
    r")",
    re.I | re.S,
)
# Platform and kind both participate in the same filter path (AND).
_COMBINED_FILTER_PATH = re.compile(
    r"("
    # Single filter callback / expression that mentions both fields.
    r"\.filter\s*\([^)]{0,200}\.platform\b[^)]{0,200}\.conversation_kind\b"
    r"|\.filter\s*\([^)]{0,200}\.conversation_kind\b[^)]{0,200}\.platform\b"
    # Derived list that chains / includes both predicates nearby.
    r"|(?:filteredTimeline|visibleTimeline|timelineRows|shownTimeline|"
    r"displayTimeline|tlRows)"
    r"[^;]{0,500}\.platform\b[^;]{0,500}\.conversation_kind\b"
    r"|(?:filteredTimeline|visibleTimeline|timelineRows|shownTimeline|"
    r"displayTimeline|tlRows)"
    r"[^;]{0,500}\.conversation_kind\b[^;]{0,500}\.platform\b"
    # Both filter states referenced near the same derived / filter site.
    r"|(?:platformFilter|selectedPlatform|timelinePlatform|tlPlatform|"
    r"activePlatform|filterPlatform)"
    r"[^;]{0,400}"
    r"(?:kindFilter|conversationKindFilter|timelineKind|tlKind|"
    r"selectedKind|filterKind|kindOnly)"
    r"|(?:kindFilter|conversationKindFilter|timelineKind|tlKind|"
    r"selectedKind|filterKind|kindOnly)"
    r"[^;]{0,400}"
    r"(?:platformFilter|selectedPlatform|timelinePlatform|tlPlatform|"
    r"activePlatform|filterPlatform)"
    r")",
    re.I | re.S,
)
# Empty when the *filtered* timeline is empty (not only the raw unfiltered list).
_FILTERED_EMPTY = re.compile(
    r"("
    r"(?:filteredTimeline|visibleTimeline|timelineRows|kindRows|"
    r"shownTimeline|displayTimeline|tlRows|visibleRows)"
    r"\s*(?:\?\.|\.)?\s*length\s*===?\s*0"
    r"|!\s*(?:filteredTimeline|visibleTimeline|timelineRows|kindRows|"
    r"shownTimeline|displayTimeline|tlRows|visibleRows)"
    r"\s*(?:\?\.|\.)?\s*length"
    r"|(?:filteredTimeline|visibleTimeline|timelineRows|kindRows|"
    r"shownTimeline|displayTimeline|tlRows|visibleRows)"
    r"\s*\.length\s*(?:===?|==)\s*0"
    r"|(?:filteredTimeline|visibleTimeline)\s*\.length\s*===\s*0"
    r")",
    re.I,
)
# Kind=group must not force includeGroups on / bypass the D18 groups gate.
_KIND_BYPASS_GROUPS = re.compile(
    r"("
    r"(?:kindFilter|conversationKindFilter|timelineKind|selectedKind|filterKind)"
    r"[^;]{0,120}===?\s*[\"']group[\"'][^;]{0,160}"
    r"includeGroups\s*=\s*true"
    r"|includeGroups\s*=\s*true[^;]{0,160}"
    r"(?:kindFilter|conversationKindFilter|timelineKind|selectedKind|filterKind)"
    r"[^;]{0,80}===?\s*[\"']group[\"']"
    r"|(?:kindFilter|conversationKindFilter|selectedKind)\s*===?\s*[\"']group[\"']"
    r"[^;]{0,200}personTimeline\s*\([^)]{0,200}includeGroups\s*:\s*true"
    r")",
    re.I | re.S,
)


def assert_timeline_platform_chips(crate: Path) -> None:
    """#115: platform chip on each bubble + All + data-derived platform toolbar.

    Acceptance: “WhatsApp only” hides Gmail for that person. Chip is text/badge,
    not a remote CDN brand image. Toolbar offers All plus only platforms present
    for this person (from conversations / timeline) — dynamic {#each} is OK;
    a forever-visible WhatsApp+Gmail button matrix is not required. Client filter
    on row.platform is OK; API/core platform arg also OK when paging.
    """
    app = (crate / "web" / "App.svelte").read_text()
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
    app = (crate / "web" / "App.svelte").read_text()
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
