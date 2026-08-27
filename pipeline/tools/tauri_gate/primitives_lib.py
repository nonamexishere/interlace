"""Helpers extracted from primitives.py (primitives_lib)."""
from __future__ import annotations

from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import fail

from tauri_gate.scan import (
    _BODY_T_CALL,
    _chrome_en_text,
    _CMD_PALETTE_PKG,
    _function_body,
    _HUE_YELLOW,
    _product_svelte,
    _search_pane_blob,
    _SPLASH_VIDEO,
    _svelte_markup,
    _template_stack,
    _timeline_block,
    _TOAST_SONNER_PKG,
    _web_logic,
    _web_sources,
)

from tauri_gate.a11y_lib import (
    _SPIN_ANIM,
    _css_prefers_reduced_blocks,
)

from tauri_gate.design_lib import (
    _EMPTY_MASCOT,
    _lucide_attr_block,
    _lucide_surface,
)

from tauri_gate.import_boot_setup import _boot_opening_block
from tauri_gate.import_boot_guards import (
    _empty_state_blocks,
    _has_css_spinner,
    _ident_negated,
    _owned_imported_names,
    _svelte_if_true_branch,
)

from tauri_gate.status_toasts_chrome import (
    _CDN_HINT,
    _HUE_AMBER,
    _NET_IMG,
    _SECOND_UI_KIT,
    _SERVER_PROGRESS,
    _SKELETON_HOOK,
    _SPINNER_NAME,
    _cond_code,
    _owned_skeleton_names,
    _people_inflight_branch,
    _skeleton_hook_positions,
    _typo_docs_blob,
)
from tauri_gate.status_toasts_toast import (
    _people_sidebar_regions,
    _web_chrome_blob,
)




# #201 — owned Tooltip, Separator, Badge, Card (no one-off chrome).
_OWNED_PRIMITIVES_201 = ("tooltip", "separator", "badge", "card")
_BITS_KIT_CDN = re.compile(
    r"("
    r"(?:unpkg(?:\.com)?|jsdelivr(?:\.net)?|esm\.sh|cdn\.)[^\"'\s)]*bits-ui"
    r"|bits-ui[^\"'\s)]*(?:unpkg|jsdelivr|esm\.sh)"
    r"|https?://[^\"'\s)]*(?:unpkg|jsdelivr|esm\.sh|cdn\.)[^\"'\s)]*"
    r"(?:bits-ui|@radix-ui|shadcn|daisyui|flowbite|melt-ui|skeletonlabs|ark-ui)"
    r")",
    re.I,
)
_NETWORK_AVATAR_IMG = re.compile(
    r"<img\b[^>]{0,400}\bsrc\s*=\s*[\"']https?://",
    re.I | re.S,
)
_DOCS_OWNED_CHIPS_BANNERS = re.compile(
    r"("
    r"(?:platform[- ]?chips?|banners?).{0,200}"
    r"(?:owned.{0,60})?(?:badge|card|shadcn[- ]?(?:svelte )?primitives?)"
    r"|(?:owned.{0,60})?(?:badge|card|shadcn[- ]?(?:svelte )?primitives?).{0,200}"
    r"(?:platform[- ]?chips?|banners?)"
    r")",
    re.I | re.S,
)
_DOCS_NOT_ONE_OFF_CHROME = re.compile(
    r"("
    r"not one-off(?: chrome)?"
    r"|not.{0,48}one-off chrome"
    r"|rather than one-off"
    r"|instead of one-off"
    r"|not hand-?rolled chrome"
    r")",
    re.I,
)
_DIALOG_FOOTER_BLOCK = re.compile(
    r"<Dialog\.Footer\b[^>]*>[\s\S]*?</Dialog\.Footer>",
    re.I,
)


def _owned_tag_match(tag: str, names: list[str]) -> bool:
    tag_l = tag.lower()
    for n in names:
        nl = n.lower()
        if tag_l == nl or tag_l.startswith(nl + "."):
            return True
    return False


def _owned_used_in(block: str, names: list[str]) -> bool:
    for n in names:
        if re.search(rf"<{re.escape(n)}(?:\.\w+)?\b", block):
            return True
    return False


def _hook_tag_name(src: str, hook: str) -> str:
    m = re.search(
        rf"<([A-Za-z][\w:.-]*)\b[^>]*\b{re.escape(hook)}\b",
        src,
        re.S,
    )
    return m.group(1) if m else ""


def _chip_hook_files(crate: Path) -> list[tuple[Path, str]]:
    found: list[tuple[Path, str]] = []
    for p in _product_svelte(crate):
        text = p.read_text()
        if re.search(r"\bdata-platform-chip\b|\bplatform-chip\b", text):
            found.append((p, text))
    return found


# #202 — EmptyState next action on every major empty view (no mascot).
# Titles stay English-grepable (#131). Action may be a label + handler,
# onclick, snippet, or Button/button child. Import idle may use data-empty
# instead of <EmptyState> if that hook still carries a next action.
_EMPTY_TITLES_202 = (
    ("App.svelte", "No people yet", "People: no people yet"),
    ("App.svelte", "No match", "People: no filter match"),
    ("SearchPane.svelte", "Type a query", "Search: no query"),
    ("SearchPane.svelte", "No hits", "Search: no hits"),
    ("ReviewPane.svelte", "Nothing to review", "Review: nothing to review"),
    ("App.svelte", "No messages in this view", "Timeline: no messages"),
    ("DoctorPane.svelte", "No doctor issues", "Doctor healthy"),
)
# IN.md: Select a person still needs a next action if that EmptyState stays.
_EMPTY_TITLES_202_OPTIONAL_IF_ABSENT = (
    ("App.svelte", "Select a person", "Timeline: select a person"),
)
_EMPTY_NEXT_ACTION = re.compile(
    r"("
    r"\baction(?:Label|Text|Click|Handler)?\s*="
    r"|\bprimaryAction\s*="
    r"|\bnextAction\s*="
    r"|\bcta(?:Label)?\s*="
    r"|\bonAction\s*="
    r"|\bonaction\s*="
    r"|\bonclick\s*="
    r"|\bon:click\s*="
    r"|\{#snippet\s+(?:action|children|cta)\b"
    r"|\{@render\s+(?:action|children|cta)\b"
    r"|<(?:Button|button)\b"
    r"|Pick file"
    r"|Clear filter"
    r")",
    re.I,
)
_EMPTY_OPTIONAL_ACTION = re.compile(
    r"("
    r"\baction(?:Label|Text|Click|Handler)?\s*\??\s*:"
    r"|\bprimaryAction\s*\??\s*:"
    r"|\bnextAction\s*\??\s*:"
    r"|\bcta(?:Label)?\s*\??\s*:"
    r"|\bonAction\s*\??\s*:"
    r"|\bonclick\s*\??\s*:"
    r"|children\s*\??\s*:"
    r"|\{#if\s+[^}]{0,120}(?:action|onclick|onAction|cta|children)\b"
    r"|\{@render\s+(?:action|children|cta)\b"
    r"|\{#snippet\s+(?:action|children|cta)\b"
    r")",
    re.I,
)
_EMPTY_GRADIENT = re.compile(r"\bbg-gradient(?:-|to-|\b)", re.I)
_SKELETON_PKG_202 = re.compile(
    r"[\"'](?:svelte-skeleton|skeleton-svelte|@skeletonlabs(?:/[^\"']*)?)[\"']",
    re.I,
)
_DOCS_EMPTY_NEXT_ACTION = re.compile(
    r"("
    r"empty(?:[- ]states?| views?)?.{0,120}(?:next action|helpful action)"
    r"|(?:next action|helpful action).{0,120}empty(?:[- ]states?| views?)?"
    r"|empty(?:[- ]states?| views?)?.{0,80}(?:import|clear filter|pick file)"
    r")",
    re.I | re.S,
)
_DOCS_EMPTY_NO_MASCOT = re.compile(
    r"("
    r"(?:empty(?:[- ]states?| views?)?).{0,80}(?:no |not |without ).{0,40}mascot"
    r"|no mascot.{0,80}empty"
    r"|not.{0,40}(?:a )?mascot"
    r")",
    re.I | re.S,
)


def _empty_block_title(block: str) -> str:
    m = re.search(r"\btitle\s*=\s*[\"']([^\"']+)[\"']", block)
    if m:
        return m.group(1)
    m = re.search(r"\btitle\s*=\s*\{[\"']([^\"']+)[\"']\}", block)
    if m:
        return m.group(1)
    return ""


def _empty_usage_has_action(block: str) -> bool:
    return bool(_EMPTY_NEXT_ACTION.search(block))


def _empty_file(crate: Path, name: str) -> Path:
    if name == "App.svelte":
        return crate / "web" / "App.svelte"
    return crate / "web" / "lib" / name
_SKELETON_MUTED_BAR = re.compile(
    r"("
    r"\bbg-muted\b"
    r"|var\(--(?:color-)?muted\)"
    r")"
)
_SKELETON_ANIM = re.compile(
    r"("
    r"\banimate-(?:pulse|shimmer|skeleton)\b"
    r"|@keyframes\s+[\w-]*(?:shimmer|pulse|skeleton)[\w-]*"
    r"|animation\s*:\s*[^;\n}]*(?:shimmer|pulse|skeleton)"
    r")",
    re.I,
)
_SKELETON_JS_SHIMMER = re.compile(
    r"("
    r"requestAnimationFrame\s*\([^)]{0,80}(?:shimmer|skeleton|pulse)"
    r"|setInterval\s*\([^)]{0,80}(?:shimmer|skeleton|pulse)"
    r")",
    re.I,
)
_SKELETON_PKG_203 = re.compile(
    r"[\"'](?:svelte-skeleton|skeleton-svelte|@skeletonlabs(?:/[^\"']*)?"
    r"|react-loading-skeleton|react-content-loader)[\"']",
    re.I,
)
_SKELETON_SVG_ANIM = re.compile(r"<animate(?:Transform|Motion)?\b", re.I)
_DOCS_203_SKELETON = re.compile(
    r"("
    r"(?:quiet\s+)?(?:muted\s+)?skeleton.{0,240}(?:people|timeline|search)"
    r"|(?:people|timeline|search).{0,240}(?:quiet\s+)?(?:muted\s+)?skeleton"
    r")",
    re.I | re.S,
)
_DOCS_203_BOOT_STAYS = re.compile(
    r"("
    r"boot(?:\s*/\s*opening)?\s+spinner.{0,48}stay"
    r"|spinner stay"
    r"|boot spinner stays"
    r"|keep.{0,48}(?:boot|opening).{0,24}spinner"
    r")",
    re.I | re.S,
)
_DOCS_203_REDUCE_STATIC = re.compile(
    r"("
    r"reduced[- ]motion.{0,80}static"
    r"|static.{0,48}(?:bars|skeleton)"
    r")",
    re.I | re.S,
)
_SKELETON_REDUCE_STATIC = re.compile(
    r"("
    r"animation\s*:\s*none\b"
    r"|animation-duration\s*:\s*0(?:\.\d+)?(?:s|ms)?\b"
    r"|animation-iteration-count\s*:\s*1\b"
    r"|animate-none\b"
    r"|motion-reduce:animate-none\b"
    r")",
    re.I,
)


def _has_skeleton_hook(block: str, owned_names: list[str]) -> bool:
    if not block:
        return False
    if _SKELETON_HOOK.search(block):
        return True
    return bool(owned_names) and _owned_used_in(block, owned_names)


def _skeleton_owned_files(crate: Path) -> list[Path]:
    ui = crate / "web" / "lib" / "components" / "ui" / "skeleton"
    if not ui.is_dir():
        return []
    return [p for p in ui.rglob("*") if p.suffix in {".svelte", ".ts", ".css"}]

from tauri_gate.primitives_lib_rest import (
    _docs_203_surfaces,
    _APPEND_IDENT,
    _REPLACE_IDENT,
    _LOAD_OLDER_SELECT_APPEND,
    _cond_hides_skeleton_on_append,
    _cond_shows_skeleton_on_append,
    _stack_hides_on_append,
    _guard_flags,
    _svelte_if_true_branches,
    _select_person_append_param,
    _flag_assigned_from_append,
    _flag_cleared_on_append,
    _flag_set_true_in,
    _open_person_clears_append_flag,
    __all__,
)

__all__ = [
    "_OWNED_PRIMITIVES_201",
    "_BITS_KIT_CDN",
    "_NETWORK_AVATAR_IMG",
    "_DOCS_OWNED_CHIPS_BANNERS",
    "_DOCS_NOT_ONE_OFF_CHROME",
    "_DIALOG_FOOTER_BLOCK",
    "_owned_tag_match",
    "_owned_used_in",
    "_hook_tag_name",
    "_chip_hook_files",
    "_EMPTY_TITLES_202",
    "_EMPTY_TITLES_202_OPTIONAL_IF_ABSENT",
    "_EMPTY_NEXT_ACTION",
    "_EMPTY_OPTIONAL_ACTION",
    "_EMPTY_GRADIENT",
    "_SKELETON_PKG_202",
    "_DOCS_EMPTY_NEXT_ACTION",
    "_DOCS_EMPTY_NO_MASCOT",
    "_empty_block_title",
    "_empty_usage_has_action",
    "_empty_file",
    "_SKELETON_MUTED_BAR",
    "_SKELETON_ANIM",
    "_SKELETON_JS_SHIMMER",
    "_SKELETON_PKG_203",
    "_SKELETON_SVG_ANIM",
    "_DOCS_203_SKELETON",
    "_DOCS_203_BOOT_STAYS",
    "_DOCS_203_REDUCE_STATIC",
    "_SKELETON_REDUCE_STATIC",
    "_has_skeleton_hook",
    "_skeleton_owned_files",
    "_docs_203_surfaces",
    "_APPEND_IDENT",
    "_REPLACE_IDENT",
    "_LOAD_OLDER_SELECT_APPEND",
    "_cond_hides_skeleton_on_append",
    "_cond_shows_skeleton_on_append",
    "_stack_hides_on_append",
    "_guard_flags",
    "_svelte_if_true_branches",
    "_select_person_append_param",
    "_flag_assigned_from_append",
    "_flag_cleared_on_append",
    "_flag_set_true_in",
    "_open_person_clears_append_flag",
    "annotations",
    "re",
    "Path",
    "fail",
    "_BODY_T_CALL",
    "_chrome_en_text",
    "_CMD_PALETTE_PKG",
    "_function_body",
    "_HUE_YELLOW",
    "_product_svelte",
    "_search_pane_blob",
    "_SPLASH_VIDEO",
    "_svelte_markup",
    "_template_stack",
    "_timeline_block",
    "_TOAST_SONNER_PKG",
    "_web_logic",
    "_web_sources",
    "_SPIN_ANIM",
    "_css_prefers_reduced_blocks",
    "_EMPTY_MASCOT",
    "_lucide_attr_block",
    "_lucide_surface",
    "_boot_opening_block",
    "_empty_state_blocks",
    "_has_css_spinner",
    "_ident_negated",
    "_owned_imported_names",
    "_svelte_if_true_branch",
    "_CDN_HINT",
    "_HUE_AMBER",
    "_NET_IMG",
    "_SECOND_UI_KIT",
    "_SERVER_PROGRESS",
    "_SKELETON_HOOK",
    "_SPINNER_NAME",
    "_cond_code",
    "_owned_skeleton_names",
    "_people_inflight_branch",
    "_skeleton_hook_positions",
    "_typo_docs_blob",
    "_people_sidebar_regions",
    "_web_chrome_blob",
]
