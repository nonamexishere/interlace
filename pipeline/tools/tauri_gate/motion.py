"""Motion chrome assert. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _contrast_dark_blob,
    _css_var,
    _css_without_comments,
    _INSPECTOR_HOOK,
    _open_tag_around,
    _open_tag_before,
    _PALETTE_HOOK,
    _product_svelte,
    _search_pane_blob,
    _STATUS_WARNING_NAMES,
    _web_logic,
    CSP,
)

from tauri_gate.a11y_lib import (
    _A11Y_ANIM_NONE,
    _A11Y_MOTION_REDUCE_TW,
    _A11Y_TRANS_NONE,
    _SPIN_ANIM,
    _css_prefers_reduced_blocks,
)

from tauri_gate.import_boot_guards import _contrast_light_blob

from tauri_gate.status_toasts_chrome import (
    _MOTION_DURATION_ZERO,
    _MOTION_JS_REDUCE,
    _hue_surface,
)
from tauri_gate.status_toasts_toast import _motion_js_blob




# #222 — 150–250ms fade/fly/slide on palette, inspector, toast; reduced = 0.
_MOTION_IMPORT = re.compile(
    r"import\s*\{[^}]*\b(?:fade|fly|slide)\b[^}]*\}\s*from\s*"
    r"[\"']svelte/transition[\"']",
    re.S,
)
_MOTION_DIRECTIVE = re.compile(r"\b(?:transition|in|out)\s*:\s*(fade|fly|slide)\b")
_MOTION_DIRECTIVE_CALL = re.compile(
    r"\b(?:transition|in|out)\s*:\s*(fade|fly|slide)"
    r"(?:\s*=\s*(\{\{?.*?\}?\}))?",
    re.S,
)
_MOTION_DURATION_NUM = re.compile(r"\bduration\s*:\s*(\d+)\b")
_MOTION_DURATION_EXPR = re.compile(r"\bduration\s*:\s*([^,}\n]+)")
_MOTION_BANNED = re.compile(
    r"("
    r"\bspring\b"
    r"|\bbounce\b"
    r"|\belastic\b"
    r"|\blottie\b"
    r"|\bcelebrat(?:e|ion|ing|ory)\b"
    r"|\bconfetti\b"
    r")",
    re.I,
)
_MOTION_DOCS_FADE = re.compile(r"\b(?:fade|slide|fly)\b", re.I)
_MOTION_DOCS_REDUCED = re.compile(
    r"("
    r"reduced[\s-]*motion.{0,80}"
    r"(?:instant|immediately|no transition|duration\s*0|appear instantly)"
    r"|(?:instant|immediately|appear instantly).{0,80}reduced[\s-]*motion"
    r")",
    re.I | re.S,
)
_MOTION_DOCS_NO_CELEB = re.compile(r"\bno\s+celebration\b", re.I)
_MOTION_DOCS_NO_AUTOPLAY = re.compile(
    r"\bno\s+auto-?play(?:ing)?(?:\s+media)?\b",
    re.I,
)
_MOTION_COMMAND_OPEN = re.compile(r"\{#if\s+commandOpen\b[^}]*\}")
_MOTION_TOAST_FADE = re.compile(r"\b(?:transition|in|out)\s*:\s*fade\b")


def _motion_has_import(src: str) -> bool:
    return bool(_MOTION_IMPORT.search(src))


def _motion_duration_ok(params: str) -> bool:
    """Literal 150–250 or 0, or a var (0 when reduced — checked separately)."""
    nums = [int(n) for n in _MOTION_DURATION_NUM.findall(params)]
    if nums:
        return all(n == 0 or 150 <= n <= 250 for n in nums)
    return bool(_MOTION_DURATION_EXPR.search(params))


def _motion_ok_on(blob: str) -> bool:
    if not _MOTION_DIRECTIVE.search(blob):
        return False
    for m in _MOTION_DIRECTIVE_CALL.finditer(blob):
        if _motion_duration_ok(m.group(2) or ""):
            return True
    return False


def _motion_first_tag(src: str) -> str:
    i = src.find("<")
    if i < 0:
        return ""
    found = _open_tag_before(src, i + 1)
    if found and found[0] == i:
        return found[1]
    m = re.search(r"<[^>]+>", src, re.S)
    return m.group(0) if m else ""


def _motion_hook_tag(src: str, hook: str) -> str:
    at = src.find(hook)
    if at < 0:
        return ""
    found = _open_tag_before(src, at + 1)
    if found:
        return found[1]
    return _open_tag_around(src, re.escape(hook))


def _motion_command_open_root(src: str) -> str:
    m = _MOTION_COMMAND_OPEN.search(src)
    if not m:
        return ""
    return _motion_first_tag(src[m.end() :])


def _motion_palette_blobs(crate: Path) -> list[str]:
    blobs: list[str] = []
    for p in _product_svelte(crate):
        text = p.read_text()
        if _PALETTE_HOOK.search(text):
            blobs.append(_motion_hook_tag(text, "data-command-palette"))
        if _MOTION_COMMAND_OPEN.search(text):
            blobs.append(_motion_command_open_root(text))
    return [b for b in blobs if b]


def _motion_inspector_blobs(crate: Path) -> list[str]:
    blobs: list[str] = []
    for p in _product_svelte(crate):
        text = p.read_text()
        if _INSPECTOR_HOOK.search(text):
            blobs.append(_motion_hook_tag(text, "data-person-inspector"))
    return [b for b in blobs if b]


def assert_motion(crate: Path) -> None:
    """#222: 150–250ms fade/fly/slide; reduced motion is duration 0."""
    svelte_files = _product_svelte(crate)
    if not svelte_files:
        fail("#222: crates/interlace-tauri/web/**/*.svelte required (motion)")

    app_path = crate / "web" / "App.svelte"
    app = _web_logic(crate) if app_path.is_file() else ""
    pal_path = crate / "web" / "lib" / "CommandPalette.svelte"
    pal = pal_path.read_text() if pal_path.is_file() else ""
    toast_path = crate / "web" / "lib" / "components" / "ui" / "toast" / "toast.svelte"
    toast = toast_path.read_text() if toast_path.is_file() else ""

    # 1) Palette + inspector import fade/fly/slide from svelte/transition.
    palette_srcs = [
        text
        for text in (app, pal)
        if text
        and (
            _PALETTE_HOOK.search(text)
            or _MOTION_COMMAND_OPEN.search(text)
            or "CommandPalette" in text
        )
    ]
    inspector_srcs = [
        p.read_text()
        for p in svelte_files
        if _INSPECTOR_HOOK.search(p.read_text())
    ]
    if not any(_motion_has_import(s) for s in palette_srcs):
        fail(
            "#222: palette must import fade / fly / slide from "
            "svelte/transition (App.svelte and/or CommandPalette.svelte)"
        )
    if not any(_motion_has_import(s) for s in inspector_srcs):
        fail(
            "#222: inspector must import fade / fly / slide from "
            "svelte/transition"
        )

    # 2) data-command-palette (or commandOpen root) fade/fly/slide 150–250
    #    (or a var that is 0 when reduced).
    palette_blobs = _motion_palette_blobs(crate)
    if not palette_blobs:
        fail(
            "#222: data-command-palette (or commandOpen root) required "
            "for fade / fly / slide"
        )
    if not any(_motion_ok_on(b) for b in palette_blobs):
        fail(
            "#222: data-command-palette (or commandOpen root) must use "
            "transition:fade / fly / slide with duration 150–250 "
            "(or 0 when reduced)"
        )

    # 3) data-person-inspector same duration rule.
    inspector_blobs = _motion_inspector_blobs(crate)
    if not inspector_blobs:
        fail("#222: data-person-inspector required for fade / fly / slide")
    if not any(_motion_ok_on(b) for b in inspector_blobs):
        fail(
            "#222: data-person-inspector must use transition:fade / fly / "
            "slide with duration 150–250 (or 0 when reduced)"
        )

    # 4) Toast still fade, duration 150–250 or 0 if reduced.
    if not toast.strip():
        fail("#222: toast.svelte required (keep transition:fade 150–250)")
    toast_tag = _motion_hook_tag(toast, "data-toast") or toast
    if not _MOTION_TOAST_FADE.search(toast_tag):
        fail("#222: toast must still use transition:fade")
    if not _motion_ok_on(toast_tag):
        fail(
            "#222: toast transition:fade duration must be 150–250 "
            "(or 0 if reduced)"
        )

    # 5) No spring / bounce / elastic / lottie / celebration / confetti.
    banned_hits: list[str] = []
    for p in svelte_files:
        found = sorted(
            {m.group(0) for m in _MOTION_BANNED.finditer(_hue_surface(p.read_text()))}
        )
        if found:
            banned_hits.append(f"{p.relative_to(crate)}: {', '.join(found)}")
    if banned_hits:
        fail(
            "#222: no spring / bounce / elastic / lottie / celebration / "
            "confetti in product Svelte. Found:\n  " + "\n  ".join(banned_hits)
        )

    # 6) JS reduced-motion + duration 0 (or skip) for those transitions.
    #    CSS-only transition-duration: 0.01ms is not enough for Svelte JS.
    js_blob = _motion_js_blob(crate)
    if not _MOTION_JS_REDUCE.search(js_blob):
        fail(
            "#222: reduced-motion path must use matchMedia / MediaQuery / "
            "prefersReducedMotion in JS (CSS transition-duration: 0.01ms "
            "is not enough for Svelte transitions)"
        )
    svelte_blob = "\n".join(p.read_text() for p in svelte_files)
    if not _MOTION_DURATION_ZERO.search(js_blob + "\n" + svelte_blob):
        fail(
            "#222: palette / inspector / toast Svelte transitions must use "
            "duration 0 (or skip) when reduced motion"
        )

    # 7) Keep #133 CSS reduce media + boot spinner reduced-motion.
    css_path = crate / "web" / "app.css"
    css = css_path.read_text() if css_path.is_file() else ""
    css_blob = _css_without_comments(css)
    index_html = ""
    index_path = crate / "index.html"
    if index_path.is_file():
        index_html = _css_without_comments(index_path.read_text())
    reduce_css = "\n".join(_css_prefers_reduced_blocks(css_blob))
    reduce_html = "\n".join(_css_prefers_reduced_blocks(index_html))
    reduce_all = reduce_css + "\n" + reduce_html
    has_reduce_media = bool(reduce_css.strip() or reduce_html.strip())
    has_motion_tw = bool(
        _A11Y_MOTION_REDUCE_TW.search(app)
        or _A11Y_MOTION_REDUCE_TW.search(css_blob)
    )
    if not has_reduce_media and not has_motion_tw:
        fail(
            "#222: keep #133 @media (prefers-reduced-motion: reduce) "
            "in CSS (or Tailwind motion-reduce)"
        )
    if not _A11Y_ANIM_NONE.search(reduce_all) and not (
        has_motion_tw
        and re.search(r"motion-reduce:animate-none", app + "\n" + css_blob)
    ):
        fail(
            "#222: keep #133 reduced-motion animation: none "
            "(boot spinner must not spin)"
        )
    if not _A11Y_TRANS_NONE.search(reduce_all) and not re.search(
        r"motion-reduce:transition-none", app + "\n" + css_blob
    ):
        fail(
            "#222: keep #133 prefers-reduced-motion CSS "
            "(transition: none / transition-duration: 0)"
        )
    if _SPIN_ANIM.search(index_html) and not _A11Y_ANIM_NONE.search(reduce_html):
        fail(
            "#222: keep boot spinner reduced-motion "
            "(#133 / #156 — disable boot-spin under reduce)"
        )

    # 8) Docs: fade/slide + reduced motion instant + no celebration /
    #    no auto-play.
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    if not dtxt.strip():
        fail(
            "#222: docs/user/app.md required — fade/slide + reduced motion "
            "instant + no celebration / no auto-play"
        )
    if not _MOTION_DOCS_FADE.search(dtxt):
        fail(
            "#222: docs/user/app.md must say palette / inspector / toast "
            "use a short fade / slide"
        )
    if not _MOTION_DOCS_REDUCED.search(dtxt):
        fail(
            "#222: docs/user/app.md must say reduced motion makes them instant"
        )
    if not _MOTION_DOCS_NO_CELEB.search(dtxt):
        fail("#222: docs/user/app.md must say no celebration")
    if not _MOTION_DOCS_NO_AUTOPLAY.search(dtxt):
        fail("#222: docs/user/app.md must say no auto-playing media")

    # 9) Do not soften #q, sidebar, overlay, inspector hook, CSP,
    #    #219 tokens, #220 data-import-cancel, #221 data-review-card / undo.
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = _search_pane_blob(crate) if search_path.is_file() else ""
    conf = (crate / "tauri.conf.json").read_text()
    light_blob = _contrast_light_blob(css)
    dark_blob = _contrast_dark_blob(css)
    if not re.search(r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""", search):
        fail('#222: keep id="q" as the canonical query field (#208)')
    if not re.search(r"\bdata-people-sidebar\b", app):
        fail("#222: keep data-people-sidebar (#159 / #212)")
    if not re.search(r"titleBarStyle", conf) and not re.search(
        r"\bdata-tauri-drag-region\b", app
    ):
        fail("#222: keep the overlay titlebar (#211)")
    if not re.search(r"\bdata-person-inspector\b", app):
        fail("#222: keep data-person-inspector (#213)")
    if CSP not in conf:
        fail("#222: do not soften tauri CSP")
    if not _css_var(light_blob, _STATUS_WARNING_NAMES) or not _css_var(
        dark_blob, _STATUS_WARNING_NAMES
    ):
        fail("#222: keep #219 --warning / --color-warning in light and dark")
    if "data-import-cancel" not in svelte_blob:
        fail("#222: keep #220 data-import-cancel")
    if "data-review-card" not in svelte_blob:
        fail("#222: keep #221 data-review-card")
    if "data-review-undo" not in svelte_blob:
        fail("#222: keep #221 data-review-undo")
