"""Owned primitives / empty / skeleton chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.primitives_lib import *


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
        if fname == "App.svelte":
            file_text[fname] = _web_logic(crate)
        elif fname == "SearchPane.svelte":
            file_text[fname] = _search_pane_blob(crate)
        else:
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

from tauri_gate.primitives_more import (
    assert_loading_skeletons,
    assert_timeline_append_skeleton_guard,
)
