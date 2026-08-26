"""Owned primitives / empty / skeleton chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import fail

from tauri_gate.scan import (
    _BODY_T_CALL,
    _CMD_PALETTE_PKG,
    _HUE_YELLOW,
    _SPLASH_VIDEO,
    _TOAST_SONNER_PKG,
    _chrome_en_text,
    _function_body,
    _product_svelte,
    _svelte_markup,
    _template_stack,
    _timeline_block,
    _web_sources,
)

from tauri_gate.a11y import (
    _SPIN_ANIM,
    _css_prefers_reduced_blocks,
)

from tauri_gate.design import (
    _EMPTY_MASCOT,
    _lucide_attr_block,
    _lucide_surface,
)

from tauri_gate.import_boot import (
    _boot_opening_block,
    _empty_state_blocks,
    _has_css_spinner,
    _ident_negated,
    _owned_imported_names,
    _svelte_if_true_branch,
)

from tauri_gate.status_toasts import (
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
    _people_sidebar_regions,
    _skeleton_hook_positions,
    _typo_docs_blob,
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


def assert_owned_primitives(crate: Path) -> None:
    """#201: own Tooltip, Separator, Badge, Card — no one-off chrome.

    Four primitive dirs under web/lib/components/ui/ (svelte + index.ts).
    Platform chip is Badge. A banner or dialog footer uses Card/Separator.
    bits-ui stays the local kit (no second library, no CDN). Not: network
    avatars, Command (#215), Toast (#204). Docs: owned Badge/Card for
    chips/banners, not one-off chrome.
    """
    ui = crate / "web" / "lib" / "components" / "ui"
    if not ui.is_dir():
        fail("#201: web/lib/components/ui/ required for owned primitives")

    # 1) Owned tooltip / separator / badge / card files exist.
    missing: list[str] = []
    for name in _OWNED_PRIMITIVES_201:
        d = ui / name
        if not d.is_dir():
            missing.append(f"{name}/")
            continue
        if not any(d.glob("*.svelte")):
            missing.append(f"{name}/*.svelte")
        if not (d / "index.ts").is_file():
            missing.append(f"{name}/index.ts")
    if missing:
        fail(
            "#201: missing owned primitives under web/lib/components/ui/ "
            "(tooltip, separator, badge, card — each needs at least one "
            ".svelte and index.ts). Missing: " + ", ".join(missing)
        )

    # 2) Platform chip is the Badge primitive (keep existing hooks).
    chip_files = _chip_hook_files(crate)
    if not chip_files:
        fail(
            "#201: keep data-platform-chip / platform-chip on the platform "
            "chip (implemented with the Badge primitive)"
        )
    badge_ok = False
    for _p, text in chip_files:
        names = _owned_imported_names(text, "badge")
        if not names:
            continue
        tag = _hook_tag_name(text, "data-platform-chip") or _hook_tag_name(
            text, "platform-chip"
        )
        if tag and _owned_tag_match(tag, names):
            badge_ok = True
            break
    if not badge_ok:
        fail(
            "#201: platform chip (data-platform-chip / platform-chip) must "
            "be the Badge primitive (import from $lib/components/ui/badge "
            "or relative components/ui/badge) — not a hand-rolled span"
        )

    # 3) At least one banner or dialog footer uses Card or Separator.
    chrome_ok = False
    for p in _product_svelte(crate):
        text = p.read_text()
        names = _owned_imported_names(text, "card") + _owned_imported_names(
            text, "separator"
        )
        if not names:
            continue
        if "data-cloud-warning" in text:
            block = _lucide_attr_block(text, "data-cloud-warning") or ""
            tag = _hook_tag_name(text, "data-cloud-warning")
            if _owned_tag_match(tag, names) or _owned_used_in(block, names):
                chrome_ok = True
                break
        for footer in _DIALOG_FOOTER_BLOCK.findall(text):
            if _owned_used_in(footer, names):
                chrome_ok = True
                break
        if chrome_ok:
            break
        footer_hook = _lucide_attr_block(text, "data-dialog-footer")
        if footer_hook and _owned_used_in(footer_hook, names):
            chrome_ok = True
            break
    if not chrome_ok:
        fail(
            "#201: at least one banner (data-cloud-warning) or dialog footer "
            "must use owned Card or Separator from "
            "$lib/components/ui/{card,separator}"
        )

    # 4) No second component library; bits-ui stays a local dep.
    pkg_path = crate / "package.json"
    if not pkg_path.is_file():
        fail("#201: crates/interlace-tauri/package.json required (bits-ui local)")
    pkg = pkg_path.read_text()
    if '"bits-ui"' not in pkg:
        fail(
            "#201: package.json must keep bits-ui as a local dependency "
            "(do not load bits-ui from a CDN)"
        )
    if _SECOND_UI_KIT.search(pkg):
        fail(
            "#201: package.json must not add a second component library "
            "(@radix-ui / shadcn / @skeletonlabs / daisyui / flowbite / "
            "@ark-ui / melt-ui) — extend owned primitives; bits-ui stays"
        )

    # 5) No bits-ui / component kit from CDN.
    if _BITS_KIT_CDN.search(_web_chrome_blob(crate)):
        fail(
            "#201: no bits-ui / component kit from CDN "
            "(unpkg / jsdelivr / cdn. / esm.sh)"
        )

    # 6) Not: network avatars, Command palette (#215), Toast (#204).
    svelte_blob = "\n".join(p.read_text() for p in _product_svelte(crate))
    if _NETWORK_AVATAR_IMG.search(svelte_blob):
        fail(
            "#201: not in scope — no network avatar <img src=\"http…\"> "
            "on people / chrome"
        )
    if _CMD_PALETTE_PKG.search(pkg):
        fail(
            "#201: not in scope — Command palette is #215 "
            "(do not add cmdk / svelte-command)"
        )
    if _TOAST_SONNER_PKG.search(pkg):
        fail(
            "#201: not in scope — Toast / sonner is #204 "
            "(do not add sonner / svelte-sonner)"
        )

    # 7) D24: owned Badge/Card (or owned shadcn primitives) for chips/banners.
    dtxt = _typo_docs_blob()
    if not dtxt.strip():
        fail(
            "#201: docs/user/app.md (and/or docs/hacking/tauri.md) required "
            "(owned Badge/Card for chips/banners, not one-off chrome)"
        )
    if not _DOCS_OWNED_CHIPS_BANNERS.search(dtxt):
        fail(
            "#201: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "platform chips / banners use owned Badge / Card "
            "(or owned shadcn primitives)"
        )
    if not _DOCS_NOT_ONE_OFF_CHROME.search(dtxt):
        fail(
            "#201: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "chips / banners are owned primitives, not one-off chrome"
        )


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


def assert_empty_next_action(crate: Path) -> None:
    """#202: EmptyState next action on every major empty view, no mascot.

    Optional primary action uses owned Button. People / Search / Review /
    Timeline / Import idle / Doctor healthy wire a next action. Keep
    data-empty. No illustration / bg-gradient. Merge-picker EmptyState
    also needs an action if present. Not: skeletons (#203), toasts (#204),
    t() of imported bodies, command palette (#215). Docs: empty views
    have a next action, no mascot.
    """
    empty_path = crate / "web" / "lib" / "EmptyState.svelte"
    if not empty_path.is_file():
        fail("#202: EmptyState.svelte required (data-empty + optional Button action)")
    empty = empty_path.read_text()

    # 1) Keep data-empty / title / body (gates grep data-empty).
    if "data-empty" not in empty:
        fail("#202: EmptyState must keep data-empty")
    if not re.search(r"\{title\}", empty) or not re.search(r"\{body\}", empty):
        fail("#202: EmptyState must keep title / body text")

    # 2) Optional primary action rendered with owned Button.
    button_names = _owned_imported_names(empty, "button")
    if not button_names:
        fail(
            "#202: EmptyState must render an optional primary action with "
            "owned Button (import from $lib/components/ui/button or "
            "relative components/ui/button)"
        )
    empty_markup = _svelte_markup(empty)
    if not _owned_used_in(empty_markup, button_names) and not _owned_used_in(
        empty, button_names
    ):
        fail(
            "#202: EmptyState must render the optional primary action with "
            "owned Button (import from $lib/components/ui/button or "
            "relative components/ui/button)"
        )
    if not _EMPTY_OPTIONAL_ACTION.search(empty):
        fail(
            "#202: EmptyState primary action must be optional "
            "(label + handler, onclick, or snippet — not a required mascot CTA)"
        )

    # 3) No SVG mascot / illustration / gradient card on EmptyState.
    if _EMPTY_GRADIENT.search(empty):
        fail("#202: EmptyState must not use a gradient card (no bg-gradient)")
    if _EMPTY_MASCOT.search(_lucide_surface(empty)):
        fail(
            "#202: EmptyState must not use a mascot / illustration / <svg> "
            "scene / <img> (20px Lucide + next action; no marketing card)"
        )

    # 4) Listed views keep their empty copy and wire a next action.
    en_chrome = _chrome_en_text(crate)
    required_files = {fname for fname, _title, _why in _EMPTY_TITLES_202}
    file_text: dict[str, str] = {}
    for fname in required_files | {"ImportPane.svelte"} | {
        f for f, _t, _w in _EMPTY_TITLES_202_OPTIONAL_IF_ABSENT
    }:
        path = _empty_file(crate, fname)
        if not path.is_file():
            fail(f"#202: {fname} required (empty view with a next action)")
        file_text[fname] = path.read_text()

    for fname, title, why in _EMPTY_TITLES_202:
        blob = file_text[fname] + "\n" + en_chrome
        if title not in blob:
            fail(f"#202: keep {title!r} empty copy ({why})")
        all_blocks = _empty_state_blocks(file_text[fname])
        titled = [b for b in all_blocks if title in b]
        if not titled:
            # Title may live in the en pack; the file still needs EmptyState.
            if not all_blocks:
                fail(
                    f"#202: {why} must use EmptyState with a next action "
                    f"(keep {title!r}; keep data-empty grep-able)"
                )
            titled = all_blocks
        missing = [b for b in titled if not _empty_usage_has_action(b)]
        if missing:
            shown = _empty_block_title(missing[0]) or title
            fail(
                f"#202: {why} EmptyState ({shown!r}) must include a next action "
                "(action label / onclick / Button child)"
            )

    for fname, title, why in _EMPTY_TITLES_202_OPTIONAL_IF_ABSENT:
        titled = [b for b in _empty_state_blocks(file_text[fname]) if title in b]
        if not titled:
            continue
        missing = [b for b in titled if not _empty_usage_has_action(b)]
        if missing:
            fail(
                f"#202: {why} EmptyState ({title!r}) must include a next action "
                "(action label / onclick / Button child)"
            )

    # Every remaining EmptyState usage (merge-picker No match, …) needs an action.
    for p in _product_svelte(crate):
        if p.name == "EmptyState.svelte":
            continue
        text = p.read_text()
        for block in _empty_state_blocks(text):
            if _empty_usage_has_action(block):
                continue
            shown = _empty_block_title(block) or p.name
            fail(
                f"#202: EmptyState {shown!r} in {p.relative_to(crate)} must "
                "include a next action (action label / onclick / Button child)"
            )

    # 5) Import idle must gain EmptyState or data-empty with a next action.
    imp = file_text["ImportPane.svelte"]
    if "EmptyState" not in imp and "data-empty" not in imp:
        fail(
            "#202: Import idle must use EmptyState (or data-empty) with a "
            "next action (Pick file)"
        )
    import_ok = False
    for block in _empty_state_blocks(imp):
        if _empty_usage_has_action(block):
            import_ok = True
            break
    if not import_ok and "data-empty" in imp:
        hook = _lucide_attr_block(imp, "data-empty") or imp
        if _empty_usage_has_action(hook):
            import_ok = True
    if not import_ok:
        fail(
            "#202: Import idle EmptyState (or data-empty) must include a "
            "next action (Pick file)"
        )

    # 6) Not: skeletons (#203), toasts (#204), command palette (#215), t(bodies).
    pkg_path = crate / "package.json"
    pkg = pkg_path.read_text() if pkg_path.is_file() else ""
    if _SKELETON_PKG_202.search(pkg):
        fail("#202: not in scope — loading skeletons are #203")
    for p in _product_svelte(crate):
        stem = p.stem.lower()
        if stem.startswith("skeleton") or stem in {"skeleton", "skeletons"}:
            fail(
                "#202: not in scope — loading skeleton components are #203 "
                f"(found {p.relative_to(crate)})"
            )
    if _TOAST_SONNER_PKG.search(pkg):
        fail("#202: not in scope — toasts / sonner are #204")
    if _CMD_PALETTE_PKG.search(pkg):
        fail("#202: not in scope — command palette is #215")
    svelte_blob = "\n".join(p.read_text() for p in _product_svelte(crate))
    if _BODY_T_CALL.search(svelte_blob):
        fail(
            "#202: not in scope — do not t() imported bodies "
            "(body_text / preview / snippet)"
        )

    # 7) D24: empty views have a next action, no mascot.
    dtxt = _typo_docs_blob()
    if not dtxt.strip():
        fail(
            "#202: docs/user/app.md (and/or docs/hacking/tauri.md) required "
            "(empty views have a next action, no mascot)"
        )
    if not _DOCS_EMPTY_NEXT_ACTION.search(dtxt):
        fail(
            "#202: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "empty views have a next action (Import / clear filter / Pick file)"
        )
    if not _DOCS_EMPTY_NO_MASCOT.search(dtxt):
        fail(
            "#202: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "empty views have no mascot"
        )
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


def _docs_203_surfaces(dtxt: str) -> bool:
    for m in re.finditer(r"\bskeleton\b", dtxt, re.I):
        win = dtxt[max(0, m.start() - 220) : m.end() + 220]
        if (
            re.search(r"\bpeople\b", win, re.I)
            and re.search(r"\btimeline\b", win, re.I)
            and re.search(r"\bsearch\b", win, re.I)
        ):
            return True
    return False


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
    app = app_path.read_text()
    search = search_path.read_text()
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


# #203 follow-up — Load older must not mount the timeline skeleton; in-flight audible.
_APPEND_IDENT = re.compile(
    r"\b(tlAppending|isAppending|appending|tlAppend|appendFlag|appendMode|"
    r"loadingOlder|loadOlder|tlLoadOlder|olderLoading|isAppend|append)\b"
)
_REPLACE_IDENT = re.compile(
    r"\b(tlReplacing|isReplacing|replacing|tlReplace|fullReplace|isReplace)\b"
)
_LOAD_OLDER_SELECT_APPEND = re.compile(
    r"selectPerson\s*\(\s*[^,)]+\s*,\s*true\s*[,)]"
)


def _cond_hides_skeleton_on_append(cond: str) -> bool:
    """True if this {#if} is false while Load older / append is in flight."""
    code = _cond_code(cond)
    for ident in _APPEND_IDENT.findall(code):
        if _ident_negated(code, ident):
            return True
    for ident in _REPLACE_IDENT.findall(code):
        if not _ident_negated(code, ident):
            return True
    return False


def _cond_shows_skeleton_on_append(cond: str) -> bool:
    code = _cond_code(cond)
    for ident in _APPEND_IDENT.findall(code):
        if not _ident_negated(code, ident):
            return True
    for ident in _REPLACE_IDENT.findall(code):
        if _ident_negated(code, ident):
            return True
    return False


def _stack_hides_on_append(stack: list[tuple[str, str, str]]) -> bool:
    for kind, cond, _extra in stack:
        if kind == "if" and _cond_hides_skeleton_on_append(cond):
            return True
        if kind == "if-else" and _cond_shows_skeleton_on_append(cond):
            return True
    return False


def _guard_flags(stack: list[tuple[str, str, str]]) -> tuple[list[str], list[str]]:
    append_flags: list[str] = []
    replace_flags: list[str] = []
    for kind, cond, _extra in stack:
        code = _cond_code(cond)
        if kind == "if" and _cond_hides_skeleton_on_append(cond):
            for ident in _APPEND_IDENT.findall(code):
                if _ident_negated(code, ident):
                    append_flags.append(ident)
            for ident in _REPLACE_IDENT.findall(code):
                if not _ident_negated(code, ident):
                    replace_flags.append(ident)
        elif kind == "if-else" and _cond_shows_skeleton_on_append(cond):
            for ident in _APPEND_IDENT.findall(code):
                if not _ident_negated(code, ident):
                    append_flags.append(ident)
            for ident in _REPLACE_IDENT.findall(code):
                if _ident_negated(code, ident):
                    replace_flags.append(ident)
    return append_flags, replace_flags


def _svelte_if_true_branches(src: str, cond: str) -> list[str]:
    found: list[str] = []
    for m in re.finditer(rf"\{{#if\s+[^}}]*\b{re.escape(cond)}\b[^}}]*\}}", src):
        block = _svelte_if_true_branch(src[m.start() :], cond)
        if block:
            found.append(block)
    return found


def _select_person_append_param(src: str) -> str:
    m = re.search(r"(?:async\s+)?function\s+selectPerson\s*\(([^)]*)\)", src)
    if not m:
        return "append"
    params = [p.strip() for p in m.group(1).split(",") if p.strip()]
    if len(params) < 2:
        return "append"
    raw = re.sub(r":[^=]+", "", params[1])
    name = raw.split("=")[0].strip()
    return name or "append"


def _flag_assigned_from_append(fn: str, flag: str, append_param: str) -> bool:
    if re.search(
        rf"\b{re.escape(flag)}\s*=\s*(?:!!|Boolean\s*\(\s*)?{re.escape(append_param)}\b",
        fn,
    ):
        return True
    if re.search(
        rf"if\s*\(\s*{re.escape(append_param)}\s*\)\s*\{{[^}}]{{0,400}}"
        rf"\b{re.escape(flag)}\s*=\s*true",
        fn,
    ):
        return True
    if re.search(
        rf"if\s*\(\s*{re.escape(append_param)}\s*\)\s*{re.escape(flag)}\s*=\s*true",
        fn,
    ):
        return True
    return False


def _flag_cleared_on_append(fn: str, flag: str, append_param: str) -> bool:
    if re.search(rf"\b{re.escape(flag)}\s*=\s*!\s*{re.escape(append_param)}\b", fn):
        return True
    if re.search(
        rf"if\s*\(\s*{re.escape(append_param)}\s*\)[\s\S]{{0,200}}"
        rf"\b{re.escape(flag)}\s*=\s*(?:false|0|null)",
        fn,
    ):
        return True
    return False


def _flag_set_true_in(src: str, flag: str) -> bool:
    return bool(re.search(rf"\b{re.escape(flag)}\s*=\s*true\b", src))


def _open_person_clears_append_flag(src: str, flag: str) -> bool:
    body = _function_body(src, "openPersonAtMessage")
    if not body:
        return True
    if re.search(rf"\b{re.escape(flag)}\s*=\s*(?:false|0|null)", body):
        return True
    if re.search(r"\bselectPerson\s*\(", body):
        return True
    return False


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
    app = app_path.read_text()
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
