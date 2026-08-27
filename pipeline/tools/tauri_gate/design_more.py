"""Additional design asserts."""
from __future__ import annotations

from tauri_gate.design_lib import *


def assert_lucide_icons(crate: Path) -> None:
    """#200: chrome icons are Lucide (@lucide/svelte), not glyphs / CDN.

    Voice play/pause and lightbox close are 16px Lucide. EmptyState shows a
    20px Lucide. Keep data-voice-play / data-lightbox-close / data-empty and
    play-pause behavior. No emoji-as-icon on those surfaces. No second icon
    package or CDN icon kit. Nav icons optional — text labels stay. Not:
    mascots, brand-logo images, #201/#202/#224. Docs: Lucide chrome icons,
    not emoji glyphs.
    """
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    if not cas_path.is_file():
        fail("#200: CasAttach.svelte required (voice play/pause + lightbox close)")
    empty_path = crate / "web" / "lib" / "EmptyState.svelte"
    if not empty_path.is_file():
        fail("#200: EmptyState.svelte required (20px Lucide on data-empty)")
    pkg_path = crate / "package.json"
    if not pkg_path.is_file():
        fail("#200: crates/interlace-tauri/package.json required (@lucide/svelte)")

    # 1) Keep voice play/pause behavior; replace ▶ / ❚❚ with Lucide 16px.
    voice_files = _lucide_files_with(crate, "data-voice-play")
    if not voice_files:
        fail("#200: keep data-voice-play on the voice play/pause control")
    voice_blob = "\n".join(text for _, text in voice_files)
    if not re.search(
        r"("
        r"togglePlay"
        r"|\.play\s*\("
        r"|\.pause\s*\("
        r"|aria-label\s*=\s*\{[^}]*(?:[Pp]lay|[Pp]ause)"
        r")",
        voice_blob,
    ):
        fail(
            "#200: keep voice play/pause behavior "
            "(togglePlay / .play()/.pause() / aria-label Play or Pause)"
        )
    if _ICON_EMOJI_GLYPH.search(_lucide_surface(voice_blob)):
        fail(
            "#200: voice play/pause must be Lucide, not ▶ / ❚❚ text glyphs "
            "(keep data-voice-play)"
        )
    voice_bindings = _lucide_bindings(voice_blob)
    voice_ids = _lucide_ids(voice_bindings)
    if "play" not in voice_ids or "pause" not in voice_ids:
        fail(
            "#200: voice play/pause must import Lucide Play / Pause "
            "from @lucide/svelte (keep data-voice-play)"
        )
    voice_names = {local for local, path in voice_bindings if path in {"play", "pause"}}
    voice_blocks = [
        _lucide_attr_block(text, "data-voice-play") or text for _, text in voice_files
    ]
    voice_used = set()
    for block in voice_blocks:
        voice_used |= _lucide_used(block, voice_names)
    if voice_used != voice_names:
        fail(
            "#200: data-voice-play must render Lucide Play / Pause "
            "(not ▶ / ❚❚ text glyphs)"
        )
    voice_tags = []
    for block in voice_blocks:
        voice_tags.extend(_lucide_open_tags(block, voice_used))
    if not voice_tags or any(not _ICON_SIZE_16.search(tag) for tag in voice_tags):
        fail(
            "#200: voice play/pause Lucide icons must be 16px default "
            "(size-4 / w-4 h-4 / size={16})"
        )

    # 2) Lightbox close is Lucide (dialog X is the pattern) at 16px.
    close_files = _lucide_files_with(crate, "data-lightbox-close")
    if not close_files:
        fail("#200: keep data-lightbox-close on the lightbox close control")
    close_blob = "\n".join(text for _, text in close_files)
    if not re.search(
        r"aria-label\s*=\s*[\"'][^\"']*[Cc]lose[^\"']*[\"']",
        close_blob,
    ):
        fail(
            "#200: lightbox close must keep an accessible name "
            "(aria-label \"Close photo\")"
        )
    close_bindings = _lucide_bindings(close_blob)
    close_names = {local for local, _ in close_bindings}
    if not close_names:
        fail(
            "#200: lightbox close (data-lightbox-close) must use a Lucide icon "
            "imported from @lucide/svelte (dialog X is the pattern)"
        )
    close_blocks = [
        _lucide_attr_block(text, "data-lightbox-close") or text
        for _, text in close_files
    ]
    close_used: set[str] = set()
    for block in close_blocks:
        close_used |= _lucide_used(block, close_names)
    if not close_used:
        fail(
            "#200: data-lightbox-close must render a Lucide icon "
            "(import from @lucide/svelte; dialog X is the pattern)"
        )
    close_tags: list[str] = []
    for block in close_blocks:
        close_tags.extend(_lucide_open_tags(block, close_used))
    if not close_tags or any(not _ICON_SIZE_16.search(tag) for tag in close_tags):
        fail(
            "#200: lightbox close Lucide icon must be 16px "
            "(size-4 / w-4 h-4 / size={16})"
        )

    # 3) EmptyState: 20px Lucide; keep title/body; not a mascot / network img.
    empty = empty_path.read_text()
    if "data-empty" not in empty:
        fail("#200: EmptyState must keep data-empty")
    if not re.search(r"\{title\}", empty) or not re.search(r"\{body\}", empty):
        fail("#200: EmptyState must keep title / body text")
    empty_bindings = _lucide_bindings(empty)
    empty_names = {local for local, _ in empty_bindings}
    if not empty_names:
        fail(
            "#200: EmptyState (data-empty) must import a Lucide icon "
            "from @lucide/svelte at 20px (size-5 / w-5 h-5 / 20)"
        )
    empty_block = _lucide_attr_block(empty, "data-empty") or empty
    empty_used = _lucide_used(empty_block, empty_names) or _lucide_used(
        empty, empty_names
    )
    if not empty_used:
        fail(
            "#200: EmptyState (data-empty) must render a Lucide icon "
            "at 20px (size-5 / w-5 h-5 / 20)"
        )
    empty_tags = _lucide_open_tags(empty, empty_used)
    if not empty_tags or any(not _ICON_SIZE_20.search(tag) for tag in empty_tags):
        fail(
            "#200: EmptyState Lucide icon must be 20px "
            "(size-5 / w-5 h-5 / size={20}) — not a mascot / illustration"
        )
    # Ban illustrated mascots / network <img> in EmptyState. Lucide is a
    # component import, not a raw <svg> scene or remote <img>.
    if _EMPTY_MASCOT.search(_lucide_surface(empty)):
        fail(
            "#200: EmptyState must not use a mascot / illustration / <svg> "
            "scene / <img> (20px Lucide only; no network image)"
        )

    # 4) No emoji-as-icon on play/pause / close / empty (not message bodies).
    surface_blob = "\n".join(
        [
            *[block for block in voice_blocks if block],
            *[block for block in close_blocks if block],
            empty_block,
        ]
    )
    if _ICON_EMOJI_GLYPH.search(_lucide_surface(surface_blob)):
        fail(
            "#200: no emoji-as-icon on play/pause / lightbox close / empty "
            "(▶ ❚ ✓ ✕ ✖ ❌ ✨) — message bodies are not this check"
        )

    # 5) @lucide/svelte stays; no second icon pack.
    pkg = pkg_path.read_text()
    if '"@lucide/svelte"' not in pkg:
        fail(
            "#200: package.json must keep @lucide/svelte "
            "(do not add a second icon package)"
        )
    if _OTHER_ICON_PKG.search(pkg):
        fail(
            "#200: do not add a second icon package "
            "(react-icons / heroicons / fontawesome / @tabler / iconify) — "
            "use @lucide/svelte already in the crate"
        )
    svelte_blob = "\n".join(p.read_text() for p in _product_svelte(crate))
    if _OTHER_ICON_IMPORT.search(svelte_blob):
        fail(
            "#200: product Svelte must import icons from @lucide/svelte only "
            "(no react-icons / heroicons / fontawesome / @tabler / iconify)"
        )

    # 6) No CDN icon kit; no WhatsApp/Gmail CDN brand logos as icons.
    cdn_blob = svelte_blob
    css_path = crate / "web" / "app.css"
    if css_path.is_file():
        cdn_blob += "\n" + css_path.read_text()
    splash = crate / "index.html"
    if splash.is_file():
        cdn_blob += "\n" + splash.read_text()
    if _ICON_CDN.search(_lucide_surface(cdn_blob)):
        fail(
            "#200: no CDN icon kit "
            "(fonts.googleapis / cdn. / unpkg / jsdelivr / iconify API)"
        )
    if _BRAND_LOGO_IMG.search(_lucide_surface(svelte_blob)):
        fail(
            "#200: not in scope — no WhatsApp / Gmail CDN brand logos as icons"
        )

    # 7) Nav icons are optional; text labels must stay.
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#200: App.svelte required (nav text labels stay; icons optional)")
    app = _web_logic(crate)
    nav_m = re.search(r"<nav\b[^>]*>[\s\S]*?</nav>", app, re.I)
    if not nav_m:
        fail("#200: App.svelte nav required (keep text labels; icons optional)")
    nav = nav_m.group(0)
    for key in _NAV_LABEL_KEYS:
        if not re.search(rf"""t\(\s*["']{key}["']\s*\)""", nav):
            fail(
                f"#200: nav must keep the {key} text label "
                "(icons are optional; do not replace labels with icon-only chrome)"
            )

    # 8) D24: Lucide chrome icons (play/pause / lightbox / empty), not emoji.
    dtxt = _typo_docs_blob()
    if not dtxt.strip():
        fail(
            "#200: docs/user/app.md (and/or docs/hacking/tauri.md) required "
            "(Lucide chrome icons, not emoji glyphs)"
        )
    if not _DOCS_LUCIDE_CHROME.search(dtxt):
        fail(
            "#200: docs/user/app.md (and/or docs/hacking/tauri.md) must mention "
            "Lucide chrome icons (play/pause, lightbox, empty)"
        )
    if not _DOCS_LUCIDE_NOT_EMOJI.search(dtxt):
        fail(
            "#200: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "chrome icons are Lucide, not emoji glyphs"
        )
