"""Helpers extracted from timeline_filters.py (timeline_filters_lib)."""
from __future__ import annotations

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

from tauri_gate.people_switcher_label_extra2 import _PRETTY_WHATSAPP

from tauri_gate.status_toasts_toast import _person_detail_markup

from tauri_gate.timeline_latest import (
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

__all__ = [
    "_svelte_snippet_body",
    "_person_detail_with_renders",
    "_PLATFORM_CHIP",
    "_PLATFORM_CHIP_NEAR",
    "_REMOTE_PLATFORM_IMG",
    "_REMOTE_PLATFORM_URL",
    "_PLATFORM_FILTER_STATE",
    "_PLATFORM_FILTER_HOOK",
    "_PLATFORM_TOOLBAR_ALL",
    "_PRETTY_PLATFORM_MAP",
    "_CLIENT_PLATFORM_FILTER",
    "_API_PLATFORM_FILTER",
    "_PLATFORM_OPTIONS_FROM_DATA",
    "_INVENTED_PLATFORM_LIST",
    "_KIND_FILTER_STATE",
    "_KIND_FILTER_HOOK",
    "_KIND_TOOLBAR_ALL",
    "_KIND_OPT_DM",
    "_KIND_OPT_EMAIL",
    "_KIND_OPT_GROUP",
    "_KIND_OPTIONS_FROM_DATA",
    "_STATIC_KIND_MATRIX",
    "_CLIENT_KIND_FILTER",
    "_DERIVED_KIND_FILTER",
    "_API_KIND_FILTER",
    "_COMBINED_FILTER_PATH",
    "_FILTERED_EMPTY",
    "_KIND_BYPASS_GROUPS",
    "re",
    "Path",
    "fail",
    "_INCLUDE_GROUPS_LABEL",
    "_PRETTY_GMAIL",
    "_RAW_WHATSAPP",
    "_matching_each_end",
    "_timeline_block",
    "_web_logic",
    "_web_sources",
    "_without_comments",
    "_PRETTY_WHATSAPP",
    "_person_detail_markup",
    "_EACH_TIMELINE",
    "_VISIBLE_KIND_JK",
    "annotations",
]
