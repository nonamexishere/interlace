"""Import / first-run / Doctor chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

import re
import html
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    CSP,
    _APPEARANCE_FETCH,
    _APPEARANCE_MENU_LABEL,
    _APPEARANCE_SCRIM_NAMES,
    _APPEARANCE_THEME_UI,
    _ARBITRARY_SHELL,
    _CDN_HINT,
    _FETCH_CALL,
    _LINKIFY_FETCH,
    _NET_IMG,
    _PLUGIN_SHELL,
    _SANDBOX_137,
    _SCROLL_HELPER_SKIP,
    _SERVER_PROGRESS,
    _SHELL_CAP,
    _SPINNER_NAME,
    _SPIN_ANIM,
    _SPLASH_VIDEO,
    _STATUS_CELEBRATION,
    _STATUS_CONFETTI,
    _STATUS_GRADIENT,
    _STATUS_WARNING_NAMES,
    _ancestor_tags,
    _boot_opening_block,
    _call_arg,
    _chrome_en_text,
    _chrome_helper_names,
    _claim_without_negation,
    _contrast_dark_blob,
    _contrast_light_blob,
    _contrast_surface_tag,
    _css_var,
    _element_block_at,
    _expand_fn_calls,
    _function_body,
    _has_css_spinner,
    _hook_element_blocks,
    _hue_surface,
    _invoke_payloads,
    _js_next,
    _markup_uses_chrome_helper,
    _match_closer,
    _payload_has_path_or_url,
    _product_svelte,
    _rust_body_with_callees,
    _rust_call_arg,
    _rust_fn_body,
    _rust_fn_signature,
    _rust_function_body,
    _status_hook_blob,
    _svelte_if_true_branch,
    _svelte_markup,
    _tauri_rust_blob,
    _tauri_rust_sources,
    _ts_fn_body,
    _ts_function_body,
    _web_logic,
    _web_sources,
    _web_ts_sources,
    _windows_around,
    _without_comments,
)


_VIEWPORT_FILL = re.compile(
    r"("
    r"min-h-(?:screen|dvh|svh|full)"
    r"|h-(?:screen|dvh|svh|full)"
    r"|min-height\s*:\s*100(?:vh|dvh|svh|%)"
    r"|height\s*:\s*100(?:vh|dvh|svh|%)"
    r"|(?:fixed|absolute)\s+inset-0"
    r"|inset\s*:\s*0"
    r")",
    re.I,
)
_CENTER_AXIS = re.compile(
    r"("
    r"items-center"
    r"|justify-center"
    r"|place-items-center"
    r"|place-content-center"
    r"|align-items\s*:\s*center"
    r"|justify-content\s*:\s*center"
    r"|place-items\s*:\s*center"
    r"|place-content\s*:\s*center"
    r")",
    re.I,
)
_FLEX_OR_GRID = re.compile(
    r"("
    r"\bflex\b"
    r"|\bgrid\b"
    r"|display\s*:\s*(?:flex|grid|inline-flex)"
    r")",
    re.I,
)
_LIGHT_DARK = re.compile(
    r"("
    r"\bdark:"
    r"|prefers-color-scheme"
    r"|--color-(?:background|foreground|muted)"
    r"|color-scheme\s*:"
    r")",
    re.I,
)


def _is_viewport_centered(blob: str) -> bool:
    """True when layout fills the viewport and centers content (not corner text)."""
    if not blob:
        return False
    if re.search(r"place-items-center|place-content-center", blob) and _VIEWPORT_FILL.search(
        blob
    ):
        return True
    return bool(
        _VIEWPORT_FILL.search(blob)
        and _CENTER_AXIS.search(blob)
        and _FLEX_OR_GRID.search(blob)
    )


def _plain_corner_loading(html: str) -> bool:
    """True when splash is only plain Loading text with no spinner chrome."""
    body = re.search(r"<body\b[^>]*>(.*)</body>", html, re.I | re.S)
    blob = body.group(1) if body else html
    # Strip scripts — they are not the visible splash.
    blob = re.sub(r"<script\b[^>]*>.*?</script>", "", blob, flags=re.I | re.S)
    if _has_css_spinner(html):
        return False
    if re.search(r"Loading Interlace", blob, re.I) and not _is_viewport_centered(html):
        return True
    # Bare #app text node, no spinner markup.
    if re.search(
        r"""id=["']app["'][^>]*>\s*Loading\b[^<]*\s*</""",
        blob,
        re.I,
    ) and not _has_css_spinner(html):
        return True
    return False


def assert_boot_spinner(crate: Path) -> None:
    """#156: centered CSS spinner on pre-JS splash and Opening-last-archive.

    Cold launch must not be a blank page with a corner Loading line. Spinner is
    CSS-only (no network images / CDN). Keep exact copy “Opening last archive”.
    Light/dark aware. Not: splash video, server progress %, people skeleton.
    """
    index = crate / "index.html"
    if not index.is_file():
        fail("#156: crates/interlace-tauri/index.html missing (pre-JS splash)")
    html = index.read_text()
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#156: App.svelte missing (Opening-last-archive boot state)")
    app = app_path.read_text()
    css_blob = "\n".join(
        p.read_text() for p in _web_sources(crate) if p.suffix == ".css"
    )
    boot = _boot_opening_block(app)

    # 1) Pre-JS splash: centered CSS spinner in index.html (inline — Vite CSS
    # loads with JS, so corner text-only “Loading Interlace…” is not enough).
    if _plain_corner_loading(html):
        fail(
            "#156: pre-JS splash must not be a plain corner Loading line — "
            "index.html needs a centered CSS spinner (inline <style> / classes) "
            "plus short status, not only “Loading Interlace…”"
        )
    # Spinner styles for pre-JS must live in index.html itself (not only app.css).
    if not _has_css_spinner(html):
        fail(
            "#156: pre-JS splash (index.html) must include a CSS-only rotating "
            "spinner (@keyframes / animate-spin / border ring) — no network image"
        )
    if not _is_viewport_centered(html):
        fail(
            "#156: pre-JS splash must center the spinner in the viewport "
            "(flex/grid + items/justify center + min-h-screen/full), "
            "not leave status text in the corner"
        )
    if _NET_IMG.search(html) or _CDN_HINT.search(html):
        fail(
            "#156: pre-JS spinner must be CSS-only — no http(s) image URLs or CDN"
        )
    if _SPLASH_VIDEO.search(html):
        fail("#156: no branded splash <video> (out of scope)")

    # 2) Post-mount boot: booting || opening UI — centered spinner + copy.
    if not boot:
        fail(
            "#156: App.svelte must keep a {#if booting || opening} (or opening || booting) "
            "branch for the Opening-last-archive state"
        )
    en_pack = _chrome_en_text(crate)
    boot_has_copy = "Opening last archive" in boot
    pack_has_copy = "Opening last archive" in en_pack
    boot_uses_chrome = _markup_uses_chrome_helper(boot, _chrome_helper_names(_web_logic(crate)))
    if not boot_has_copy and "Opening last archive" not in app:
        if not (pack_has_copy and boot_uses_chrome):
            fail(
                "#156: boot screen must keep the exact copy substring "
                "“Opening last archive” (existing gate string; English default / en pack)"
            )
    if not boot_has_copy:
        if not (pack_has_copy and boot_uses_chrome):
            fail(
                "#156: “Opening last archive” must appear in the booting/opening branch "
                "(literal English, or chrome helper + en pack — default stays English)"
            )
    # Spinner may use Tailwind utilities in the branch and/or shared CSS.
    boot_with_css = boot + "\n" + css_blob
    if not _has_css_spinner(boot) and not (
        _has_css_spinner(boot_with_css) and _SPINNER_NAME.search(boot)
    ):
        # Accept spinner markup in branch that relies on global .spinner / animate-spin CSS.
        if not (
            (_SPINNER_NAME.search(boot) or re.search(r"animate-spin", boot))
            and _SPIN_ANIM.search(boot_with_css)
        ):
            fail(
                "#156: Opening-last-archive state must show a CSS rotating spinner "
                "(animate-spin / @keyframes spin / spinner class), not status text only"
            )
    if not _is_viewport_centered(boot):
        fail(
            "#156: Opening-last-archive state must be viewport-centered "
            "(flex/grid + center + full height), not a left-aligned loading line"
        )
    if _NET_IMG.search(boot) or _CDN_HINT.search(boot):
        fail(
            "#156: boot spinner must not load network images or CDN assets"
        )
    if _SPLASH_VIDEO.search(boot):
        fail("#156: no splash <video> on the Opening-last-archive state")
    if _SERVER_PROGRESS.search(boot):
        fail(
            "#156: boot status must not show server/network progress percent "
            "(out of scope)"
        )

    # 3) Light/dark aware — soft: dark: utilities, prefers-color-scheme, or theme vars.
    theme_blob = html + "\n" + app + "\n" + css_blob
    if not _LIGHT_DARK.search(theme_blob):
        fail(
            "#156: boot chrome must follow light/dark "
            "(dark: classes, prefers-color-scheme, or --color-background/foreground)"
        )


# #274 — Reveal archive folder in Finder from Doctor / People.
_REVEAL_ARCHIVE_HOOK = re.compile(
    r"data-(?:reveal-archive|reveal-root|reveal-folder|"
    r"reveal-archive-root|archive-reveal)"
)
_REVEAL_ARCHIVE_HOOK_NAMES = (
    "data-reveal-archive",
    "data-reveal-root",
    "data-reveal-folder",
    "data-reveal-archive-root",
    "data-archive-reveal",
)
_REVEAL_ARCHIVE_LABEL = re.compile(
    r"("
    r">\s*Reveal(?:\s+in\s+Finder|\s+archive(?:\s+folder)?)?\s*<"
    r"|t\(\s*[\"']reveal(?:InFinder|Archive|Folder|Root|ArchiveFolder)[\"']\s*\)"
    r"|aria-label\s*=\s*[\"']Reveal(?: in Finder| archive(?: folder)?)?[\"']"
    r")"
)
_REVEAL_ARCHIVE_FN = re.compile(
    r"\b(?:"
    r"revealArchive|revealArchiveRoot|revealRoot|revealFolder|"
    r"revealOpenArchive|onRevealArchive|handleRevealArchive|"
    r"openArchiveInFinder|revealArchiveFolder"
    r")\b"
)
_REVEAL_ARCHIVE_COMPONENT = re.compile(
    r"<Reveal(?:Archive|Folder|Root|ArchiveRoot|ArchiveFolder)\b"
)
_REVEAL_ARCHIVE_CMD_SNAKE = (
    "reveal_archive",
    "reveal_archive_root",
    "reveal_root",
    "reveal_folder",
    "reveal_open_archive",
    "reveal_archive_folder",
)
_REVEAL_ARCHIVE_CAMEL = (
    "revealArchive",
    "revealArchiveRoot",
    "revealRoot",
    "revealFolder",
    "revealOpenArchive",
    "revealArchiveFolder",
)
_REVEAL_ARCHIVE_SKIP_EXTRA = frozenset(
    {
        "App.svelte",
        "DoctorPane.svelte",
        "CasAttach.svelte",
        "SearchPane.svelte",
        "CommandPalette.svelte",
        "ConfirmDialog.svelte",
        "ReviewPane.svelte",
        "ImportPane.svelte",
        "EmptyState.svelte",
        "api.ts",
    }
)
_REVEAL_ARCHIVE_HANDLER_SKIP = frozenset(
    {
        "t",
        "e",
        "event",
        "true",
        "false",
        "void",
        "undefined",
        "null",
        "console",
        "preventDefault",
        "stopPropagation",
        "Button",
        "ask",
    }
)
_REVEAL_ARCHIVE_DOC = re.compile(
    r"("
    r"Reveal(?: in Finder)?(?: the)? archive folder"
    r"|Reveal archive"
    r"|reveal the (?:open )?archive"
    r"|archive folder.{0,80}Finder"
    r"|Finder.{0,80}archive folder"
    r")",
    re.I | re.S,
)
_REVEAL_ARCHIVE_DOC_COPY = re.compile(
    r"("
    r"copy (?:that |the )folder"
    r"|folder is the backup unit"
    r"|copy.{0,80}after (?:you )?clos"
    r"|after (?:you )?clos(?:e|ing).{0,80}(?:app|window)"
    r")",
    re.I | re.S,
)
_REVEAL_ARCHIVE_ENCRYPT = re.compile(
    r"("
    r"database is encrypted"
    r"|your data is encrypted"
    r"|is encrypted at rest"
    r"|SQLCipher"
    r")",
    re.I,
)
_REVEAL_ARCHIVE_UPLOAD = re.compile(r"\bupload\b", re.I)
_REVEAL_ARCHIVE_ZIP_ICLOUD = re.compile(
    r"("
    r"zip[- ]to[- ]icloud"
    r"|icloud[- ](?:drive[- ])?backup"
    r"|backup[- _]zip"
    r"|zip[- _]backup"
    r")",
    re.I,
)
_REVEAL_ARCHIVE_SECOND_CAS = re.compile(
    r"("
    r"second (?:copy of )?CAS"
    r"|duplicate(?:d)? (?:the )?CAS"
    r"|backup_cas|copy_cas|cas_copy"
    r")",
    re.I,
)
_REVEAL_ARCHIVE_BACKUP_FN = re.compile(
    r"\bfn\s+(?:backup|backup_zip|zip_backup|icloud_backup|copy_cas|backup_cas)\b"
)


def _looks_like_reveal_archive(block: str) -> bool:
    if _REVEAL_ARCHIVE_HOOK.search(block):
        return True
    if _REVEAL_ARCHIVE_FN.search(block):
        return True
    if _REVEAL_ARCHIVE_COMPONENT.search(block):
        return True
    return bool(_REVEAL_ARCHIVE_LABEL.search(block))


def _doctor_backup_section(src: str) -> str:
    """Doctor Backup <section> (heading + copy + controls)."""
    markup = _svelte_markup(src)
    i = 0
    while True:
        m = re.search(r"<section\b", markup[i:], re.I)
        if not m:
            break
        start = i + m.start()
        block = _element_block_at(markup, start)
        if re.search(r">\s*Backup\s*<", block) or re.search(
            r"<h[1-6][^>]*>\s*Backup\s*</h[1-6]>", block, re.I
        ):
            return block
        i = start + max(len(block), 1)
    m = re.search(r"<h[1-6][^>]*>\s*Backup\s*</h[1-6]>", markup, re.I)
    if m:
        rest = markup[m.start() :]
        nxt = re.search(r"<h[1-6]\b|<section\b", rest[m.end() - m.start() :])
        if nxt:
            return rest[: m.end() - m.start() + nxt.start()]
        return rest[:2000]
    return _windows_around(markup, re.compile(r"\bBackup\b"), before=40, after=1600)


def _reveal_archive_extra(crate: Path, host: str) -> str:
    """Helpers Doctor / People actually mount. CasAttach Reveal-CAS does not count."""
    web = crate / "web"
    if not web.is_dir():
        return ""
    extra: list[str] = []
    for p in sorted(web.rglob("*")):
        if "node_modules" in p.parts:
            continue
        if p.suffix not in {".svelte", ".ts"}:
            continue
        if p.name in _REVEAL_ARCHIVE_SKIP_EXTRA:
            continue
        text = p.read_text()
        name_hit = bool(re.search(r"revealArchive|RevealArchive|reveal.?root", p.name, re.I))
        hook = bool(
            _REVEAL_ARCHIVE_HOOK.search(text)
            or _REVEAL_ARCHIVE_FN.search(text)
            or _REVEAL_ARCHIVE_COMPONENT.search(text)
        )
        if not name_hit and not hook:
            continue
        stem = p.stem
        if stem in host or re.search(rf"\b{re.escape(stem)}\b|{re.escape(p.name)}", host):
            extra.append(text)
    return "\n".join(extra)


def _reveal_archive_mounted_extra(surface: str, extra: str) -> str:
    """Extra sources the surface actually references (unwired drafts do not count)."""
    if not extra.strip():
        return ""
    # Split on typical Svelte file starts is unreliable; treat as one blob
    # only when the surface names a reveal-archive helper.
    if _REVEAL_ARCHIVE_COMPONENT.search(surface) or _REVEAL_ARCHIVE_FN.search(surface):
        return extra
    for hook in _REVEAL_ARCHIVE_HOOK_NAMES:
        if hook in surface:
            return extra
    return ""


def _people_path_window(app: str) -> str:
    """People sidebar around the shown archive path (st.path)."""
    markup = _svelte_markup(app)
    blocks = _hook_element_blocks(markup, "data-people-sidebar")
    sidebar = "\n".join(blocks) if blocks else markup
    return _windows_around(sidebar, re.compile(r"\{st\.path\}"), before=280, after=560)


def _people_reveal_control_src(app: str, extra: str) -> str:
    markup = _svelte_markup(app)
    extra_m = _svelte_markup(extra) if extra else extra
    blocks = _hook_element_blocks(markup, "data-people-sidebar")
    sidebar = "\n".join(blocks) if blocks else markup
    parts: list[str] = []
    path_win = _people_path_window(app)
    mounted = _reveal_archive_mounted_extra(path_win + "\n" + sidebar, extra_m)
    if _looks_like_reveal_archive(path_win) or _looks_like_reveal_archive(mounted):
        parts.append(path_win)
        if mounted.strip():
            parts.append(mounted)
    for hook in _REVEAL_ARCHIVE_HOOK_NAMES:
        parts.extend(_hook_element_blocks(sidebar, hook))
        if extra:
            parts.extend(_hook_element_blocks(extra, hook))
    if not parts and _looks_like_reveal_archive(sidebar):
        parts.append(sidebar)
    seen: set[str] = set()
    uniq: list[str] = []
    for p in parts:
        if p and p not in seen:
            seen.add(p)
            uniq.append(p)
    return "\n".join(uniq)


def _doctor_reveal_control_src(doctor: str, extra: str) -> str:
    section = _doctor_backup_section(doctor)
    extra_m = _svelte_markup(extra) if extra else extra
    mounted = _reveal_archive_mounted_extra(section, extra_m)
    parts: list[str] = []
    if _looks_like_reveal_archive(section) or _looks_like_reveal_archive(mounted):
        parts.append(section)
        if mounted.strip():
            parts.append(mounted)
    for hook in _REVEAL_ARCHIVE_HOOK_NAMES:
        parts.extend(_hook_element_blocks(section, hook))
        if mounted:
            parts.extend(_hook_element_blocks(mounted, hook))
    seen: set[str] = set()
    uniq: list[str] = []
    for p in parts:
        if p and p not in seen:
            seen.add(p)
            uniq.append(p)
    return "\n".join(uniq)


def _reveal_archive_handler_src(host: str, control: str) -> str:
    names: set[str] = set(_REVEAL_ARCHIVE_FN.findall(host))
    names.update(_REVEAL_ARCHIVE_FN.findall(control))
    for m in re.finditer(r"(?:onclick|on:click)\s*=\s*\{([^}]{0,400})\}", control):
        names.update(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", m.group(1)))
    chunks = [control]
    for name in sorted(names):
        if name in _REVEAL_ARCHIVE_HANDLER_SKIP:
            continue
        fn = (
            _ts_function_body(host, name)
            or _ts_fn_body(host, name)
            or _function_body(host, name)
        )
        if fn:
            chunks.append(fn)
            chunks.append(_expand_fn_calls(host, fn))
    return "\n".join(chunks)


def _find_reveal_archive_cmd(rust: str, web: str) -> str:
    """Rust command that reveals the open archive root (not reveal_cas / open_url)."""
    for name in _REVEAL_ARCHIVE_CMD_SNAKE:
        if re.search(rf"\bfn\s+{re.escape(name)}\b", rust):
            return name
    for camel, snake in zip(_REVEAL_ARCHIVE_CAMEL, _REVEAL_ARCHIVE_CMD_SNAKE, strict=True):
        if re.search(rf"\b{re.escape(camel)}\b", web) and re.search(
            rf"\bfn\s+{re.escape(snake)}\b", rust
        ):
            return snake
    for name in _REVEAL_ARCHIVE_CMD_SNAKE:
        if re.search(
            rf"invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']{re.escape(name)}[\"']",
            web,
        ) and re.search(rf"\bfn\s+{re.escape(name)}\b", rust):
            return name
    gh = re.search(r"generate_handler!\s*\[([^\]]*)\]", rust, re.S)
    if not gh:
        return ""
    for name in re.findall(r"\b([a-z][a-z0-9_]*)\b", gh.group(1)):
        if name in {"reveal_cas", "open_url", "cas_data_url"}:
            continue
        body = _rust_function_body(rust, name)
        if not body:
            continue
        if "cas_blob_path" in body:
            continue
        if (
            "/usr/bin/open" in body
            and re.search(r"[\"']-R[\"']", body)
            and re.search(r"\barchive_root\b", body)
        ):
            return name
    return ""


def _reveal_archive_cmd_invoke(cmd: str) -> re.Pattern[str]:
    names = {cmd, _REVEAL_ARCHIVE_CAMEL[_REVEAL_ARCHIVE_CMD_SNAKE.index(cmd)]} if cmd in _REVEAL_ARCHIVE_CMD_SNAKE else {cmd}
    # camelCase of an unknown snake name
    if cmd not in _REVEAL_ARCHIVE_CMD_SNAKE:
        parts = cmd.split("_")
        names.add(parts[0] + "".join(p.title() for p in parts[1:]))
    alt = "|".join(re.escape(n) for n in sorted(names))
    return re.compile(
        r"(?:"
        r"invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']" + re.escape(cmd) + r"[\"']"
        r"|api\.(?:" + alt + r")\s*\("
        r")"
    )


_REVEAL_ARCHIVE_CANON_CMP = re.compile(
    r"("
    r"\bcanon\b.{0,40}(?:!=|==).{0,40}\bexpected\b"
    r"|\bexpected\b.{0,40}(?:!=|==).{0,40}\bcanon\b"
    r")"
)
_REVEAL_ARCHIVE_CANON_BIND = re.compile(
    r"\blet\s+(?:mut\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=;]+)?="
    r"\s*[^;]*\bcanonicalize\s*\("
)


def _reveal_archive_canon_self_cmp(body: str) -> bool:
    """True if two canonicalize() results are compared with != / ==."""
    if _REVEAL_ARCHIVE_CANON_CMP.search(body):
        return True
    names: list[str] = []
    seen: set[str] = set()
    for name in _REVEAL_ARCHIVE_CANON_BIND.findall(body):
        if name not in seen:
            seen.add(name)
            names.append(name)
    if len(names) < 2:
        return False
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            if re.search(
                rf"\b{re.escape(a)}\b.{{0,40}}(?:!=|==).{{0,40}}\b{re.escape(b)}\b"
                rf"|\b{re.escape(b)}\b.{{0,40}}(?:!=|==).{{0,40}}\b{re.escape(a)}\b",
                body,
            ):
                return True
    return False


def assert_reveal_archive(crate: Path) -> None:
    """#274: Reveal archive folder in Finder from Doctor / People.

    Doctor Backup and People (near st.path) have a Reveal control.
    A Rust command (not reveal_cas, not open_url) reads archive_root
    from app state and runs /usr/bin/open -R. No path from the webview
    (or a client path is ignored). Canonicalize; refuse if not the
    open root. reveal_cas stays hash-only. No plugin-shell / opener /
    fetch("http / upload / zip-to-iCloud / encryption claim / second
    CAS copy. Docs: Reveal archive folder; copy after close.
    Do not rewrite #135 / #204 / #272 / #273.
    Follow-up: exactly one canonicalize on the archive root; fail
    if two canonicalize() results are compared (!= / ==). Keep
    /usr/bin/open -R, archive_root from app state, no webview path.
    """
    doctor_path = crate / "web" / "lib" / "DoctorPane.svelte"
    if not doctor_path.is_file():
        fail("#274: DoctorPane.svelte required (Backup Reveal archive)")
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#274: App.svelte required (People Reveal near archive path)")
    doctor = doctor_path.read_text()
    app = app_path.read_text()
    extra_doc = _reveal_archive_extra(crate, doctor)
    extra_people = _reveal_archive_extra(crate, app)
    doctor_control = _doctor_reveal_control_src(doctor, extra_doc)

    # 1) Primary red: Doctor Backup has no Reveal archive control.
    if not doctor_control.strip():
        fail(
            "#274: Doctor Backup section must have a Reveal control "
            "(Reveal in Finder / Reveal archive / data-reveal-archive)"
        )

    people_control = _people_reveal_control_src(app, extra_people)
    if not people_control.strip():
        fail(
            "#274: People sidebar must have a Reveal control near the "
            "shown archive path (st.path)"
        )

    web = _web_logic(crate)
    rust = _tauri_rust_blob(crate)
    api_path = crate / "web" / "lib" / "api.ts"
    api = api_path.read_text() if api_path.is_file() else ""
    toml = (crate / "Cargo.toml").read_text() if (crate / "Cargo.toml").is_file() else ""
    pkg = (crate / "package.json").read_text() if (crate / "package.json").is_file() else ""
    caps_path = crate / "capabilities" / "default.json"
    caps = caps_path.read_text() if caps_path.is_file() else ""
    app_docs = repo_root() / "docs" / "user" / "app.md"
    backup_docs = repo_root() / "docs" / "user" / "backup.md"
    dtxt = ""
    if app_docs.is_file():
        dtxt += app_docs.read_text() + "\n"
    if backup_docs.is_file():
        dtxt += backup_docs.read_text()

    host = doctor + "\n" + extra_doc + "\n" + app + "\n" + extra_people + "\n" + api
    handler = _reveal_archive_handler_src(host, doctor_control + "\n" + people_control)

    # 3) Rust command reveals the open archive root (not reveal_cas / open_url).
    cmd = _find_reveal_archive_cmd(rust, web + "\n" + handler)
    if not cmd or cmd in {"reveal_cas", "open_url"}:
        fail(
            "#274: a Rust command (not reveal_cas, not open_url) must "
            "reveal the open archive root via /usr/bin/open -R"
        )
    sig = _rust_fn_signature(rust, cmd)
    body = _rust_body_with_callees(rust, cmd)
    if not body.strip():
        fail(
            f"#274: Rust command {cmd} must read archive_root and "
            "reveal that folder (fn taking no webview path)"
        )
    if not re.search(r"\barchive_root\b", body):
        fail(
            f"#274: {cmd} must read archive_root from app state "
            "(do not take st.path from the webview)"
        )
    has_path_arg = bool(re.search(r"\b(?:path|url|file|href|uri)\s*:", sig, re.I))
    if has_path_arg and not re.search(r"\barchive_root\b", body):
        fail(
            f"#274: {cmd} must not take a path from the webview — "
            "read archive_root (or ignore a client path)"
        )
    if not re.search(r"std::process|\buse\s+std::process", rust):
        fail(
            "#274: open Finder with std::process "
            "(not tauri-plugin-shell / plugin-opener)"
        )
    if not re.search(r"Command::new|std::process::Command", body):
        fail(
            f"#274: {cmd} must reveal the folder with std::process::Command "
            "(/usr/bin/open -R)"
        )
    if "/usr/bin/open" not in body:
        fail(f"#274: {cmd} must use /usr/bin/open -R on the archive root")
    if not re.search(r"[\"']-R[\"']", body):
        fail(
            f"#274: {cmd} must pass -R so Finder selects the archive folder "
            "(not a file inside cas/)"
        )
    if "cas_blob_path" in body:
        fail(
            f"#274: {cmd} must reveal the archive root, not a CAS blob "
            "(do not reuse reveal_cas / cas_blob_path)"
        )
    if not re.search(r"\bcanonicalize\s*\(", body):
        fail(f"#274: {cmd} must canonicalize the open archive root")
    if has_path_arg and not re.search(
        r"("
        r"starts_with"
        r"|not the open root"
        r"|outside (?:the )?(?:open )?archive"
        r"|is not the open"
        r")",
        body,
    ):
        fail(
            f"#274: {cmd} must refuse a client path that is not the "
            "open archive root"
        )
    if re.search(r"[\"']https?://", body):
        fail(f"#274: {cmd} must not open http(s) — folder only")
    if _ARBITRARY_SHELL.search(body) or _ARBITRARY_SHELL.search(rust):
        fail("#274: no shell of arbitrary commands — only /usr/bin/open on the archive root")
    for m in re.finditer(r"Command::new\s*\(", body):
        arg = _rust_call_arg(body, m.end() - 1)
        if "/usr/bin/open" not in arg:
            fail(
                "#274: no shell of arbitrary commands — "
                "Command::new must be /usr/bin/open on the archive root"
            )
    if not re.search(
        r"generate_handler!\s*\[[^\]]*\b" + re.escape(cmd) + r"\b", rust, re.S
    ):
        fail(f"#274: register {cmd} in generate_handler")

    # Frontend invokes that command — not reveal_cas (hash) / open_url.
    invoke_rx = _reveal_archive_cmd_invoke(cmd)
    if not invoke_rx.search(handler) and not invoke_rx.search(web):
        fail(
            f"#274: Doctor / People Reveal must invoke {cmd} "
            "(not reveal_cas, not open_url)"
        )
    if re.search(r"\brevealCas\s*\(|invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']reveal_cas[\"']", handler):
        fail(
            "#274: do not reuse reveal_cas (CAS hash) to reveal the "
            "archive folder"
        )
    if re.search(r"\bopenUrl\s*\(|invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']open_url[\"']", handler):
        fail("#274: do not reuse open_url for a folder (#272 is http(s) only)")
    payloads = _invoke_payloads(web + "\n" + handler, invoke_rx)
    for payload in payloads:
        if _payload_has_path_or_url(payload) and has_path_arg:
            if not re.search(r"\barchive_root\b", body):
                fail(
                    f"#274: do not pass st.path from the webview to {cmd} "
                    "(read archive_root)"
                )

    # 4) reveal_cas still takes hash only (do not soften #135).
    cas_sig = _rust_fn_signature(rust, "reveal_cas")
    cas_body = _rust_function_body(rust, "reveal_cas")
    if not cas_sig.strip() or not cas_body.strip():
        fail("#274: keep reveal_cas (hash only) — do not soften #135")
    if not re.search(r"\bhash\b", cas_sig, re.I):
        fail("#274: reveal_cas must still take a hash (do not soften #135)")
    if re.search(r"\b(?:path|url|file|href|uri)\s*:", cas_sig, re.I):
        fail(
            "#274: reveal_cas must still take the hash only — "
            "no path from the webview"
        )
    if "cas_blob_path" not in cas_body:
        fail("#274: reveal_cas must still resolve cas/ab/cd/<hash> via cas_blob_path")
    if not re.search(
        r"generate_handler!\s*\[[^\]]*\breveal_cas\b", rust, re.S
    ):
        fail("#274: keep reveal_cas in generate_handler (do not soften #135)")
    if not re.search(
        r"revealCas\s*:\s*\(\s*hash\b|invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']reveal_cas[\"']\s*,\s*\{\s*hash",
        api,
    ):
        fail("#274: api.revealCas must still take hash only (do not soften #135)")

    # 5) Bans: plugin-shell / opener / fetch / upload / zip-iCloud / encrypt / second CAS.
    if _PLUGIN_SHELL.search(toml) or _PLUGIN_SHELL.search(pkg):
        fail(
            "#274: do not add tauri-plugin-shell / tauri-plugin-opener "
            "(std::process file-only open)"
        )
    if _PLUGIN_SHELL.search(rust) or _PLUGIN_SHELL.search(web):
        fail(
            "#274: do not add tauri-plugin-shell / tauri-plugin-opener "
            "(std::process file-only open)"
        )
    if _SHELL_CAP.search(caps):
        fail(
            "#274: capabilities must not add shell:allow-execute / "
            "shell:allow-open / opener (no arbitrary Command)"
        )
    reveal_surf = _without_comments(handler + "\n" + doctor_control + "\n" + people_control + "\n" + body)
    if _FETCH_CALL.search(reveal_surf) or _LINKIFY_FETCH.search(reveal_surf):
        fail('#274: no fetch("http — reveal is local /usr/bin/open -R')
    if _REVEAL_ARCHIVE_UPLOAD.search(reveal_surf):
        fail("#274: no upload")
    if _REVEAL_ARCHIVE_ZIP_ICLOUD.search(doctor + "\n" + app + "\n" + rust + "\n" + handler):
        fail("#274: no zip-to-iCloud backup command")
    if _REVEAL_ARCHIVE_BACKUP_FN.search(rust):
        fail("#274: no zip-to-iCloud / interlace backup command")
    product_claim = "\n".join((doctor, app, rust, dtxt, handler))
    if _claim_without_negation(product_claim, _REVEAL_ARCHIVE_ENCRYPT):
        fail(
            "#274: no “database is encrypted” / SQLCipher claim "
            "(folder is the backup unit; FileVault)"
        )
    if _REVEAL_ARCHIVE_SECOND_CAS.search(handler + "\n" + body) or re.search(
        r"\bfn\s+(?:copy_cas|backup_cas|duplicate_cas)\b", rust
    ):
        fail("#274: no second CAS copy — backup is copy the archive folder")

    # 6) Docs: Reveal archive folder from Doctor / People; copy after close.
    if not dtxt.strip():
        fail(
            "#274: docs/user/app.md and/or docs/user/backup.md required — "
            "Reveal archive folder in Finder from Doctor / People; "
            "backup is still copy that folder after closing the app"
        )
    doc_win = ""
    for m in _REVEAL_ARCHIVE_DOC.finditer(dtxt):
        i = m.start()
        doc_win += dtxt[max(0, i - 80) : m.end() + 200] + "\n"
    if not doc_win.strip():
        fail(
            "#274: docs/user/app.md and/or docs/user/backup.md must say "
            "Reveal archive folder in Finder from Doctor / People"
        )
    if not re.search(r"\bDoctor\b", doc_win):
        fail(
            "#274: docs must say Reveal archive folder from Doctor "
            "(and People)"
        )
    if not re.search(r"\bPeople\b", doc_win):
        fail(
            "#274: docs must say Reveal archive folder from People "
            "(and Doctor)"
        )
    copy_win = ""
    for m in _REVEAL_ARCHIVE_DOC_COPY.finditer(dtxt):
        i = m.start()
        copy_win += dtxt[max(0, i - 80) : m.end() + 160] + "\n"
    if not copy_win.strip() or not re.search(
        r"("
        r"copy (?:that |the )folder"
        r"|folder is the backup unit"
        r")",
        copy_win,
        re.I,
    ):
        fail(
            "#274: docs must say backup is still copy that folder "
            "after closing the app"
        )
    if not re.search(
        r"("
        r"after (?:you )?clos"
        r"|clos(?:e|ing) (?:the )?(?:app|window)"
        r")",
        copy_win,
        re.I,
    ):
        fail(
            "#274: docs must say copy that folder after closing the app"
        )

    # 7) Follow-up: exactly one canonicalize; no dead self-comparison.
    own = _rust_function_body(rust, cmd)
    surf = own if own.strip() else body
    n_canon = len(re.findall(r"\bcanonicalize\s*\(", surf))
    if n_canon != 1 or _reveal_archive_canon_self_cmp(surf):
        fail(
            f"#274: {cmd} must canonicalize the archive root once — "
            "do not compare two canonicalize() results (!= / ==); "
            "drop the dead canon != expected self-check"
        )


# #275 — first-run is one calm screen, not a four-field form wall.
_SETUP_BRANCH_OPEN = re.compile(
    r"\{:else\s+if\s+setup\b|\{#if\s+setup\b"
)
_SETUP_OWNER_FIELDS = ("name", "emails", "phones")
_SETUP_SKIP_TAGS = frozenset(
    {
        "Button",
        "Input",
        "Label",
        "Card",
        "Separator",
        "Badge",
        "ScrollArea",
        "Skeleton",
        "Toast",
        "Dialog",
        "ConfirmDialog",
        "EmptyState",
        "CommandPalette",
        "SearchPane",
        "ReviewPane",
        "ImportPane",
        "DoctorPane",
        "CasAttach",
        "LinkifyBody",
        "main",
        "div",
        "p",
        "h1",
        "h2",
        "h3",
        "span",
        "form",
        "section",
        "header",
        "footer",
    }
)
_SETUP_DISCLOSURE_TAG = re.compile(
    r"<(details|Disclosure|Collapsible|Accordion)(?:\.\w+)?\b",
    re.I,
)
_SETUP_DISCLOSURE_IF = re.compile(
    r"\{#if\s+([^}]*\b(?:showMore|moreOpen|ownerOpen|showOwner|"
    r"ownerFields|showDetails|advanced|optionalOwner|extraFields|"
    r"moreFields|ownerMore|disclose|disclosure|showExtra|"
    r"ownerDetails|more)\b[^}]*)\}",
    re.I,
)
_SETUP_HIDDEN_ATTR = re.compile(
    r"("
    r"\bhidden\s*="
    r"|class:hidden\b"
    r"|aria-hidden\b"
    r"|(?<=\s)hidden(?=[\s/>])"
    r")"
)
_SETUP_CAROUSEL = re.compile(r"\b(?:carousel|swiper|onboarding)\b", re.I)
_SETUP_ACCOUNT_ACTION = re.compile(
    r"\b(?:sign[\s-]*in|sign[\s-]*up|log[\s-]*in|create account|oauth)\b",
    re.I,
)
_SETUP_SAMPLE_CLOUD = re.compile(
    r"("
    r"\b(?:sample|demo|cloud)\s+archive\b"
    r"|try a sample"
    r"|sample cloud"
    r")",
    re.I,
)
_SETUP_URL_FIELD = re.compile(
    r"<input\b[^>]*\btype\s*=\s*[\"']url[\"']|bind:value=\{[^}]*archiveUrl",
    re.I,
)
_SETUP_REQUIRE_OWNER = re.compile(
    r"("
    r"if\s*\(\s*!\s*(?:name|emails|phones)\b"
    r"|(?:name|emails|phones)\s+is required"
    r"|err\s*=\s*[\"'][^\"']*\b(?:name|emails?|phones?)\b[^\"']*required"
    r")",
    re.I,
)
_SETUP_DOC_ONE_SCREEN = re.compile(
    r"("
    r"first[- ]run.{0,80}one (?:calm )?screen"
    r"|one (?:calm )?screen.{0,80}first[- ](?:run|open)"
    r"|first[- ](?:run|open) is one"
    r")",
    re.I | re.S,
)
_SETUP_DOC_OPTIONAL = re.compile(
    r"("
    r"optional.{0,80}(?:owner|name|emails?|phones?).{0,80}"
    r"(?:not required|later|disclosure|not .{0,24}up front|not .{0,24}first)"
    r"|(?:owner )?(?:name|emails?|phones?).{0,60}"
    r"(?:not required|optional).{0,40}(?:first|up front|setup)"
    r"|optional owner.{0,40}(?:not required|disclosure|later|inspector)"
    r")",
    re.I | re.S,
)


def _svelte_closed_block_at(src: str, start: int) -> str:
    """{#if}/{#each}/{#await}/{#key} starting at start, through its close."""
    if start < 0 or start >= len(src) or not src.startswith("{#", start):
        return ""
    rest = src[start:]
    depth = 1
    i = 2
    while i < len(rest):
        if rest.startswith("{#if", i) or rest.startswith("{#each", i) or rest.startswith(
            "{#await", i
        ) or rest.startswith("{#key", i):
            depth += 1
            i += 3
            continue
        if rest.startswith("{/if}", i) or rest.startswith("{/each}", i) or rest.startswith(
            "{/await}", i
        ) or rest.startswith("{/key}", i):
            depth -= 1
            if depth == 0:
                close = 5 if rest.startswith("{/if}", i) else 7
                if rest.startswith("{/await}", i) or rest.startswith("{/key}", i):
                    close = 8 if rest.startswith("{/await}", i) else 6
                return rest[: i + close]
            i += 3
            continue
        i += 1
    return rest


def _setup_branch(app: str) -> str:
    """Markup of the setup / first-run branch ({:else if setup} or {#if setup})."""
    markup = _svelte_markup(app)
    m = _SETUP_BRANCH_OPEN.search(markup)
    src = markup
    if not m:
        return ""
    rest = src[m.end() :]
    depth = 1
    i = 0
    while i < len(rest):
        if rest.startswith("{#if", i) or rest.startswith("{#each", i) or rest.startswith(
            "{#await", i
        ) or rest.startswith("{#key", i):
            depth += 1
            i += 3
            continue
        if rest.startswith("{/if}", i) or rest.startswith("{/each}", i) or rest.startswith(
            "{/await}", i
        ) or rest.startswith("{/key}", i):
            depth -= 1
            if depth == 0:
                return rest[:i]
            i += 3
            continue
        if depth == 1 and (
            rest.startswith("{:else", i)
            or rest.startswith("{:then", i)
            or rest.startswith("{:catch", i)
        ):
            return rest[:i]
        i += 1
    return rest


def _setup_mounted_extra(crate: Path, setup: str) -> str:
    """Svelte files the setup branch actually mounts (FirstRun / SetupScreen)."""
    web = crate / "web"
    if not web.is_dir() or not setup.strip():
        return ""
    extra: list[str] = []
    seen: set[str] = set()
    for m in re.finditer(r"<([A-Z][A-Za-z0-9]*)\b", setup):
        name = m.group(1)
        if name in _SETUP_SKIP_TAGS or name in seen:
            continue
        seen.add(name)
        for p in sorted(web.rglob(f"{name}.svelte")):
            if "node_modules" in p.parts:
                continue
            extra.append(p.read_text())
    return "\n".join(extra)


def _strip_setup_disclosures(markup: str) -> str:
    """Primary wall: drop <details> / disclosure {#if} / hidden wrappers."""
    text = markup
    changed = True
    while changed:
        changed = False
        m = _SETUP_DISCLOSURE_TAG.search(text)
        if m:
            block = _element_block_at(text, m.start())
            if block:
                text = text[: m.start()] + text[m.start() + len(block) :]
                changed = True
                continue
        m = _SETUP_DISCLOSURE_IF.search(text)
        if m:
            block = _svelte_closed_block_at(text, m.start())
            if block:
                text = text[: m.start()] + text[m.start() + len(block) :]
                changed = True
                continue
        for mm in re.finditer(r"<([A-Za-z][\w:.-]*)\b[^>]*>", text):
            tag = mm.group(0)
            if not _SETUP_HIDDEN_ATTR.search(tag):
                continue
            block = _element_block_at(text, mm.start())
            if block:
                text = text[: mm.start()] + text[mm.start() + len(block) :]
                changed = True
                break
    return text


def _setup_has_field(markup: str, field: str) -> bool:
    if re.search(rf"""\bid\s*=\s*["']{re.escape(field)}["']""", markup):
        return True
    if re.search(rf"""\bfor\s*=\s*["']{re.escape(field)}["']""", markup):
        return True
    if re.search(rf"bind:value\s*=\s*\{{\s*{re.escape(field)}\s*\}}", markup):
        return True
    return False


def _setup_visible_owner_fields(wall: str) -> list[str]:
    found: list[str] = []
    labels = {
        "name": re.compile(r"Your name|>\s*Name\s*<|Owner name", re.I),
        "emails": re.compile(r">\s*Emails?\b|owner emails", re.I),
        "phones": re.compile(r">\s*Phones?\b|owner phones", re.I),
    }
    for field in _SETUP_OWNER_FIELDS:
        if _setup_has_field(wall, field) or labels[field].search(wall):
            found.append(field)
    return found


def _setup_fn(app: str, extra: str, name: str) -> str:
    blob = app + "\n" + extra
    body = (
        _ts_function_body(blob, name)
        or _function_body(blob, name)
        or _ts_fn_body(blob, name)
    )
    if not body:
        return ""
    return body + "\n" + _expand_fn_calls(blob, body)


def assert_first_run(crate: Path) -> None:
    """#275: first-run is one calm screen, not a form wall.

    Setup: offline / no account, required #region, Create + Open.
    Owner name / emails / phones are not always-visible primary
    fields (disclosure or absent). createArchive still requires
    region and calls api.init; empty optional owner fields OK.
    FileVault / not encrypted; folder picker only; no carousel /
    account / sample cloud archive. Keep #137 sandbox sentence
    and #156 “Opening last archive”. Docs: one first-run screen;
    optional owner fields not required first.
    Do not rewrite #137 / #156 / #274.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#275: App.svelte required (setup / first-run screen)")
    app = app_path.read_text()
    setup = _setup_branch(app)
    if not setup.strip():
        fail(
            "#275: App.svelte must have a setup / first-run branch "
            "({:else if setup} or {#if setup})"
        )
    extra = _setup_mounted_extra(crate, setup)
    extra_m = _svelte_markup(extra) if extra else extra
    surface = setup + ("\n" + extra_m if extra_m else "")
    wall = _strip_setup_disclosures(surface)

    # 1) Form wall — name / emails / phones must not be always-visible
    #    siblings of #region. Disclosure or absent is OK.
    visible = _setup_visible_owner_fields(wall)
    if visible:
        listed = " / ".join(visible)
        fail(
            "#275: setup must not be a form wall — owner "
            f"{listed} "
            "are still always-visible primary fields next to #region; "
            "put them behind a disclosure (`<details>` / More) or leave "
            "them for the inspector"
        )

    # 2) Offline / no account copy on the setup screen.
    if not re.search(r"\boffline\b", surface, re.I):
        fail("#275: setup screen must say this is an offline archive")
    if not re.search(r"\bno account\b", surface, re.I):
        fail("#275: setup screen must say no account")

    # 3) Required phone-region field (#region).
    if not _setup_has_field(surface, "region"):
        fail(
            "#275: setup must have a required phone-region field (#region)"
        )
    if not re.search(r"required|phone-region|ISO", surface, re.I):
        fail(
            "#275: #region must be marked required "
            "(ISO-2 phone-region, no silent default)"
        )

    # 4) Create + Open actions.
    if not re.search(r"\bcreateArchive\b", surface):
        fail("#275: setup must have a Create action (createArchive)")
    if not re.search(r"\bopenPicker\b", surface):
        fail("#275: setup must have an Open action (openPicker)")

    # 5) createArchive still requires region and calls api.init.
    create = _setup_fn(app, extra, "createArchive")
    if not create.strip():
        fail("#275: createArchive required (init still needs a region)")
    if not re.search(r"\bapi\.init\s*\(", create):
        fail("#275: createArchive must call api.init")
    region_required = bool(
        re.search(r"phone-region is required", create, re.I)
        or (
            re.search(r"\bregion\b", create)
            and re.search(r"if\s*\(\s*!", create)
            and re.search(r"\breturn\b", create)
        )
    )
    if not region_required:
        fail(
            "#275: createArchive must require phone-region "
            "(no silent default; empty region errors)"
        )
    if _SETUP_REQUIRE_OWNER.search(create):
        fail(
            "#275: createArchive must not require owner name / emails / "
            "phones — empty or null optional owner fields are OK"
        )
    if not re.search(r"\bapplyStatus\s*\(", create):
        fail("#275: createArchive must applyStatus after api.init (land on People)")

    # 6) FileVault / not encrypted; folder picker only; no carousel /
    #    account / sample cloud archive.
    if not re.search(r"\bFileVault\b", surface):
        fail("#275: setup must keep FileVault (not encrypted at rest)")
    if not re.search(r"not encrypted", surface, re.I):
        fail("#275: setup must keep “not encrypted at rest”")
    open_p = _setup_fn(app, extra, "openPicker")
    pick_src = create + "\n" + open_p + "\n" + surface
    if not re.search(r"\bpickFolder\b|\bpick_folder\b", pick_src):
        fail(
            "#275: Create / Open must use the folder picker "
            "(pickFolder / pick_folder) — no URLs"
        )
    if not re.search(r"folder picker|no URLs", surface, re.I):
        fail("#275: setup must say folder picker only — no URLs")
    if _SETUP_URL_FIELD.search(surface):
        fail("#275: setup must not take an archive URL (folder picker only)")
    if _SETUP_CAROUSEL.search(surface):
        fail("#275: no onboarding carousel (one first-run screen)")
    if _SETUP_ACCOUNT_ACTION.search(surface):
        fail("#275: no account / sign-in on first-run")
    if _SETUP_SAMPLE_CLOUD.search(surface):
        fail("#275: no sample / cloud archive on first-run")

    # 7) Keep #137 sandbox-denied sentence on setup / err.
    #    Keep #156 “Opening last archive”.
    if not _SANDBOX_137.search(app) and "SANDBOX_DENIED" not in app:
        fail(
            "#275: keep the #137 sandbox-denied sentence on setup / err: "
            "macOS blocked that folder. Use Open existing… once so Interlace "
            "can remember it."
        )
    err_branch = _svelte_if_true_branch(app, "err")
    if not err_branch or not re.search(r"\{err\}", err_branch):
        fail(
            "#275: keep the in-page {#if err} banner so the #137 sandbox "
            "sentence can show on setup"
        )
    if "Opening last archive" not in app:
        fail('#275: keep #156 “Opening last archive”')

    # 8) docs/user/app.md — one first-run screen; optional fields not first.
    docs_path = repo_root() / "docs" / "user" / "app.md"
    if not docs_path.is_file():
        fail("#275: docs/user/app.md required (first-run is one screen)")
    docs = docs_path.read_text()
    if not _SETUP_DOC_ONE_SCREEN.search(docs):
        fail(
            "#275: docs/user/app.md must say first-run is one screen "
            "(offline / no account, required region, Create / Open)"
        )
    if not re.search(r"\boffline\b", docs, re.I) or not re.search(
        r"\bno account\b", docs, re.I
    ):
        fail("#275: docs/user/app.md must say offline / no account")
    if not re.search(r"phone-region|required.{0,40}region|region.{0,40}required", docs, re.I):
        fail("#275: docs/user/app.md must say phone-region is required")
    if not re.search(r"create.{0,40}open|open.{0,40}create", docs, re.I):
        fail("#275: docs/user/app.md must say Create / Open")
    if not _SETUP_DOC_OPTIONAL.search(docs):
        fail(
            "#275: docs/user/app.md must say optional owner fields "
            "(name / emails / phones) are not required first"
        )


# #134 — drag-drop local ZIP/mbox onto the window → existing importStart + progress.
_TAURI_DRAG_DROP_API = re.compile(
    r"("
    r"\.onDragDropEvent\s*\("
    r"|\bon_drag_drop_event\s*\("
    r"|tauri://drag-drop"
    r"|tauri://file-drop"
    r")",
)
_TAURI_DRAG_DROP_TYPE = re.compile(r"\bDragDropEvent\b")
_TAURI_DRAG_DROP_PLUGIN = re.compile(
    r"("
    r"@tauri-apps/plugin-fs"
    r"|tauri-plugin-fs"
    r"|plugin-file-drop"
    r"|tauri-plugin-drag"
    r")",
)
_HTML_DROP_ATTR = re.compile(
    r"("
    r"\bon:?drop\b"
    r"|\bondrop\b"
    r"|\bon:?dragover\b"
    r"|\bondragover\b"
    r"|\bon:?dragenter\b"
    r")",
    re.I,
)
_DROP_EVENT_TYPE = re.compile(
    r"("
    r"(?:payload\.)?type\s*===?\s*[\"']drop[\"']"
    r"|[\"']drop[\"']\s*===?\s*(?:[\w$.]+\.)?type"
    r"|DragDropEvent::Drop"
    r"|DragDrop::Drop"
    r"|WindowEvent::DragDrop"
    r")",
)
_DROP_PATHS = re.compile(
    r"("
    r"(?:payload\.)?paths\b"
    r"|\.paths\s*\["
    r")"
)
_IMPORT_START_CALL = re.compile(r"\b(?:api\.)?importStart\s*\(")
_IMPORT_START_KIND_AUTO = re.compile(
    r"("
    r"kind\s*:\s*null"
    r"|kind\s*:\s*(?:undefined|kind\s*===?\s*[\"']auto[\"']\s*\?\s*null)"
    r")"
)
_VIEW_IMPORT_ASSIGN = re.compile(r"\bview\s*=\s*[\"']import[\"']")
_URL_SCHEME_REJECT = re.compile(
    r"("
    r"https?://"
    r"|/?\\^https\\?:"
    r"|\\bhttps?:"
    r"|startsWith\s*\(\s*[\"']https?"
    r"|includes\s*\(\s*[\"']https?"
    r"|protocol\s*===?\s*[\"']https?:"
    r"|[\"']https?://"
    r"|isRemote(?:Url|Path)?"
    r"|isHttps?"
    r"|isUrl\b"
    r"|looksLikeUrl"
    r"|hasUrlScheme"
    r"|urlScheme"
    r"|reject(?:Http|Url|Remote)"
    r")",
    re.I,
)
_HTTPS_TOKEN = re.compile(r"https://|[\"']https://|https\\?:|[\"']https[\"']", re.I)
_HTTP_TOKEN = re.compile(r"http://|[\"']http://|[\"']http[\"']|https\\?:", re.I)
_SHOW_ERR = re.compile(
    r"("
    r"\bonError\s*\("
    r"|\bshowErr\s*\("
    r"|\berr\s*="
    r"|progress\.error"
    r")",
)
_XHR = re.compile(r"\bXMLHttpRequest\b|\baxios\s*\.")
_DATATRANSFER = re.compile(r"\bdataTransfer\b")
_DROP_WALK = re.compile(
    r"("
    r"\bwalkDir\b"
    r"|\bwalkSync\b"
    r"|\bfs\.walk\b"
    r"|\breadDir\s*\("
    r"|\bread_dir\s*\("
    r"|\breaddir\s*\("
    r"|recursive\s*:\s*true"
    r"|@tauri-apps/plugin-fs"
    r"|\bfolderOfFolders\b"
    r"|\bwalkImport\b"
    r"|\bimportWalk\b"
    r"|\brglob\s*\("
    r")",
)
_HTTP_CAP = re.compile(
    r"("
    r"http:default"
    r"|http:allow-fetch"
    r"|http:allow-request"
    r"|tauri-plugin-http"
    r"|allow-http"
    r")",
    re.I,
)
_IMPORT_PANE_PATH_PROP = re.compile(
    r"<ImportPane\b[^>]{0,500}(?:"
    r"bind:path"
    r"|droppedPath|dropPath|startPath|importPath|queuedPath|pendingPath"
    r"|autoStart|dropQueued"
    r")",
    re.I | re.S,
)
_DROP_CALL_SKIP = frozenset(
    {
        "if",
        "for",
        "while",
        "switch",
        "catch",
        "function",
        "return",
        "typeof",
        "new",
        "await",
        "void",
        "Promise",
        "Math",
        "Number",
        "String",
        "Boolean",
        "parseInt",
        "document",
        "getElementById",
        "querySelector",
        "querySelectorAll",
        "Error",
        "setTimeout",
        "setInterval",
        "clearInterval",
        "requestAnimationFrame",
        "getCurrentWebview",
        "getCurrentWindow",
        "onDragDropEvent",
        "listen",
        "console",
        "JSON",
        "Array",
        "Object",
        "RegExp",
        "Date",
        "Map",
        "Set",
        "unlisten",
        "onMount",
        "tick",
    }
)


def _import_pane_conditionally_mounted(app: str) -> bool:
    """True when every ImportPane mounts only under view === \"import\"."""
    seen = False
    only_conditional = True
    for m in re.finditer(r"<ImportPane\b", app):
        seen = True
        window = app[max(0, m.start() - 400) : m.start()]
        if not re.search(r"view\s*===?\s*[\"']import[\"']", window):
            only_conditional = False
    return seen and only_conditional


def _drop_api_files(crate: Path) -> list[Path]:
    found: list[Path] = []
    for p in _web_ts_sources(crate) + _tauri_rust_sources(crate):
        text = p.read_text()
        if _TAURI_DRAG_DROP_API.search(text) or (
            _TAURI_DRAG_DROP_TYPE.search(text) and re.search(r"\.paths\b", text)
        ):
            found.append(p)
    return found


def _extract_call_callback(src: str, call_rx: re.Pattern[str]) -> list[str]:
    bodies: list[str] = []
    for m in call_rx.finditer(src):
        open_paren = src.find("(", m.start())
        if open_paren < 0:
            continue
        arg = _call_arg(src, open_paren)
        if not arg:
            continue
        bodies.append(arg)
        named = re.match(r"\s*([A-Za-z_][\w]*)\s*$", arg.strip())
        if named and named.group(1) not in _DROP_CALL_SKIP:
            inner = _ts_fn_body(src, named.group(1)) or _function_body(src, named.group(1))
            if inner:
                bodies.append(inner)
    return bodies


def _expand_drop_calls(src: str, body: str, depth: int = 3) -> str:
    chunks = [body]
    seen: set[str] = set()

    def walk(blob: str, left: int) -> None:
        for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", blob):
            if name in seen or name in _DROP_CALL_SKIP:
                continue
            seen.add(name)
            inner = _ts_fn_body(src, name) or _function_body(src, name)
            if not inner:
                continue
            chunks.append(inner)
            if left > 0:
                walk(inner, left - 1)

    walk(body, depth)
    return "\n".join(chunks)


def _drop_handler_surface(crate: Path) -> str:
    """Bodies that run on Tauri drag-drop (and named callees)."""
    chunks: list[str] = []
    sources: list[str] = []
    for p in _web_ts_sources(crate) + _tauri_rust_sources(crate):
        text = p.read_text()
        cleaned = _without_comments(text)
        sources.append(text)
        sources.append(cleaned)
        chunks.extend(_extract_call_callback(cleaned, re.compile(r"\.onDragDropEvent\s*\(")))
        chunks.extend(_extract_call_callback(text, re.compile(r"\.onDragDropEvent\s*\(")))
        chunks.extend(_extract_call_callback(cleaned, re.compile(r"\bon_drag_drop_event\s*\(")))
        chunks.extend(_extract_call_callback(text, re.compile(r"\bon_drag_drop_event\s*\(")))
        for src in (cleaned, text):
            for m in re.finditer(
                r"listen\s*(?:<[^>]*>)?\s*\(\s*[\"']tauri://(?:drag-drop|file-drop)[\"']",
                src,
            ):
                open_paren = src.find("(", m.start())
                arg = _call_arg(src, open_paren) if open_paren >= 0 else ""
                if arg:
                    chunks.append(arg)
    joined = "\n".join(chunks)
    if not joined.strip():
        return ""
    whole = "\n".join(sources)
    return _expand_drop_calls(whole, joined)


def _drop_rejects_url_scheme(surface: str) -> bool:
    """True if http and https (or a generic URL-scheme helper) are rejected."""
    if not _URL_SCHEME_REJECT.search(surface):
        return False
    has_http = bool(_HTTP_TOKEN.search(surface))
    has_https = bool(_HTTPS_TOKEN.search(surface))
    generic = bool(
        re.search(
            r"("
            r"urlScheme"
            r"|hasUrlScheme"
            r"|looksLikeUrl"
            r"|isUrl\b"
            r"|isRemote"
            r"|reject(?:Http|Url|Remote)"
            r"|/?\\^[a-zA-Z][a-zA-Z0-9+.\-]*:"
            r")",
            surface,
        )
    )
    return (has_http and has_https) or generic


def _drop_starts_import(crate: Path, surface: str, app: str, import_pane: str) -> bool:
    if _IMPORT_START_CALL.search(surface):
        return True
    if re.search(r"\bstart\s*\(", surface) and _IMPORT_START_CALL.search(import_pane):
        return True
    if _IMPORT_PANE_PATH_PROP.search(app) and _IMPORT_START_CALL.search(import_pane):
        if re.search(
            r"("
            r"droppedPath|dropPath|startPath|importPath|queuedPath|pendingPath"
            r"|\$effect"
            r")",
            import_pane,
        ) and _IMPORT_START_CALL.search(import_pane):
            return True
    return False


def assert_drag_drop_import(crate: Path) -> None:
    """#134: drop local ZIP/mbox → existing importStart + progress; reject URLs.

    Tauri file-drop (onDragDropEvent), not HTML ondrop of remote URLs and not
    fetch. First local path into importStart (auto-detect). Switch to Import
    so the existing progress UI shows. No new folder-of-folders walker.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#134: App.svelte required (window-level drop must reach Import)")
    app = app_path.read_text()
    import_path = crate / "web" / "lib" / "ImportPane.svelte"
    import_pane = import_path.read_text() if import_path.is_file() else ""
    web = _web_logic(crate)
    rust = _tauri_rust_blob(crate)
    blob = web + "\n" + rust
    cleaned = _without_comments(blob)
    caps_path = crate / "capabilities" / "default.json"
    caps = caps_path.read_text() if caps_path.is_file() else ""
    pkg = (crate / "package.json").read_text() if (crate / "package.json").is_file() else ""
    toml = (crate / "Cargo.toml").read_text() if (crate / "Cargo.toml").is_file() else ""
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 1) Tauri drag-drop API — not a raw http fetch, not HTML ondrop alone.
    if "@tauri-apps/api" not in pkg:
        fail("#134: @tauri-apps/api must remain a dependency (onDragDropEvent)")
    if not _TAURI_DRAG_DROP_API.search(cleaned) and not _TAURI_DRAG_DROP_API.search(blob):
        fail(
            "#134: must listen for Tauri file-drop "
            "(getCurrentWebview/Window().onDragDropEvent or on_drag_drop_event), "
            "not a raw http fetch / HTML ondrop of remote URLs"
        )
    api_files = _drop_api_files(crate)
    if not api_files:
        fail(
            "#134: must listen for Tauri file-drop "
            "(getCurrentWebview/Window().onDragDropEvent or on_drag_drop_event)"
        )
    only_import_pane = api_files and all(p.name == "ImportPane.svelte" for p in api_files)
    if only_import_pane and _import_pane_conditionally_mounted(app):
        fail(
            "#134: drop listener must run on any tab "
            "(App / always-mounted helper), not only inside the Import view "
            "(ImportPane unmounts when view !== \"import\")"
        )

    surface = _drop_handler_surface(crate)
    if not surface.strip():
        surface = "\n".join(p.read_text() for p in api_files)

    # 2) Drop branch reads Tauri local paths (payload.paths), not dataTransfer URLs.
    if not _DROP_PATHS.search(surface):
        fail(
            "#134: drop handler must read Tauri local paths "
            "(event.payload.paths) — not HTML dataTransfer of a remote URL"
        )
    if _DATATRANSFER.search(surface) and not _DROP_PATHS.search(surface):
        fail(
            "#134: do not import from HTML dataTransfer URLs; "
            "use Tauri payload.paths (local filesystem only)"
        )
    if not _DROP_EVENT_TYPE.search(surface) and not re.search(
        r"\bpaths\b", surface
    ):
        fail(
            "#134: handle the drop event (payload.type === \"drop\" / "
            "DragDropEvent::Drop), not hover/enter"
        )

    # 3) First local path starts existing import (not only fills the path field).
    if not import_pane.strip():
        fail("#134: ImportPane.svelte required (existing progress UI)")
    if not _drop_starts_import(crate, surface, app, import_pane):
        fail(
            "#134: drop of a local path must call existing importStart "
            "(or ImportPane start / path prop that starts import) — "
            "filling the path field alone is not enough"
        )
    start_win = _windows_around(surface, _IMPORT_START_CALL, before=200, after=240)
    if not start_win.strip():
        start_win = surface
    if _IMPORT_START_CALL.search(surface) and re.search(
        r"kind\s*:\s*[\"']whatsapp[\"']", start_win
    ) and not _IMPORT_START_KIND_AUTO.search(start_win):
        fail(
            "#134: drop must use the picker auto-detect path "
            "(importStart({ path, kind: null })) — not a WhatsApp-only kind"
        )

    # 4) Switch to Import so importProgress / Status running→done is visible.
    if not _VIEW_IMPORT_ASSIGN.search(surface) and not _VIEW_IMPORT_ASSIGN.search(app):
        fail(
            "#134: drop on another tab must set view = \"import\" "
            "so the existing import progress UI is visible"
        )
    if not _VIEW_IMPORT_ASSIGN.search(surface):
        # Assignment exists somewhere in App (⌘4 / nav). Require it on the drop path.
        fail(
            "#134: drop handler must set view = \"import\" "
            "(progress UI is the Import tab; drop may land on People/Search/…)"
        )
    if "importProgress" not in import_pane:
        fail(
            "#134: keep ImportPane importProgress polling "
            "(drop starts the existing progress UI, not a new one)"
        )
    if not re.search(r"progress\.status|Status:", import_pane):
        fail("#134: keep the Import status / progress UI (running → done)")

    # 5) Reject http(s) / URL-scheme drops: show error, do not import.
    if not _drop_rejects_url_scheme(surface):
        fail(
            "#134: drop handler must reject http:// and https:// "
            "(and other URL schemes) — local filesystem paths only"
        )
    if not _SHOW_ERR.search(surface):
        fail(
            "#134: rejected URL drops must show an error "
            "(onError / showErr) and must not call importStart"
        )

    # 6) Bans: fetch of the dropped file, remote URL as import path, new walker.
    if _FETCH_CALL.search(surface) or _XHR.search(surface):
        fail(
            "#134: do not fetch() the dropped file "
            "(no remote URLs as the import path)"
        )
    if re.search(r"importStart\s*\(\s*\{[^}]{0,200}https?://", surface, re.I | re.S):
        fail("#134: importStart path must not be a remote http(s) URL")
    walk_src = surface
    for p in api_files:
        if p.suffix in {".svelte", ".ts", ".js", ".rs"}:
            walk_src += "\n" + p.read_text()
    if _DROP_WALK.search(walk_src) or _DROP_WALK.search(surface):
        fail(
            "#134: do not add a new folder-of-folders walker "
            "(UI5 folder-of-zips via existing importStart auto-detect is OK)"
        )
    if _TAURI_DRAG_DROP_PLUGIN.search(toml) or _TAURI_DRAG_DROP_PLUGIN.search(pkg):
        if "plugin-fs" in toml or "plugin-fs" in pkg or "@tauri-apps/plugin-fs" in web:
            fail(
                "#134: do not add @tauri-apps/plugin-fs / a recursive walk "
                "for drop — pass the local path to existing importStart"
            )
    if _HTTP_CAP.search(caps) or "tauri-plugin-http" in toml:
        fail("#134: no HTTP client capability / tauri-plugin-http (local paths only)")
    if re.search(r"network\.server", caps):
        fail("#134: capabilities must not add network.server")

    # Optional: smallest drag-drop ACL if the generated schema lists one.
    schema_blob = ""
    schemas = crate / "gen" / "schemas"
    if schemas.is_dir():
        for p in schemas.glob("*.json"):
            schema_blob += p.read_text()
    if re.search(r"allow-on-drag-drop-event", schema_blob) and not re.search(
        r"allow-on-drag-drop-event", caps
    ):
        fail(
            "#134: capabilities/default.json must include the smallest "
            "drag-drop permission (core:webview:allow-on-drag-drop-event "
            "or core:window:allow-on-drag-drop-event)"
        )

    # 7) HTML ondrop of remote URLs is not a substitute.
    if _HTML_DROP_ATTR.search(cleaned) and not _TAURI_DRAG_DROP_API.search(cleaned):
        fail(
            "#134: HTML ondrop/ondragover is not enough — "
            "use Tauri onDragDropEvent for local paths"
        )

    # 8) Docs: drop a local ZIP/mbox; no URLs.
    if not dtxt.strip():
        fail("#134: docs/user/app.md required (drop a local ZIP/mbox; no URLs)")
    drop_win = ""
    for m in re.finditer(
        r".{0,160}(?:\bdrop(?:ping|ped)?\b|drag-and-drop|drag and drop).{0,160}",
        dtxt,
        re.I | re.S,
    ):
        drop_win += m.group(0) + "\n"
    if not drop_win.strip():
        fail(
            "#134: docs/user/app.md must say you can drop a local ZIP/mbox "
            "onto the window"
        )
    if not re.search(r"\blocal\b", drop_win, re.I):
        fail("#134: docs/user/app.md must say the drop is a local path (not a URL)")
    if not re.search(r"\bZIP\b|\.zip\b", drop_win, re.I):
        fail("#134: docs/user/app.md must mention dropping a local ZIP")
    if not re.search(r"\bmbox\b", drop_win, re.I):
        fail("#134: docs/user/app.md must mention dropping a local mbox")
    if not re.search(r"URL", drop_win, re.I):
        fail(
            "#134: docs/user/app.md drop line must say no URLs "
            "(local ZIP/mbox only)"
        )
    if not re.search(
        r"("
        r"no URLs"
        r"|not a URL"
        r"|URLs not"
        r"|not URLs"
        r"|never a URL"
        r"|local.{0,40}not.{0,20}URL"
        r")",
        drop_win,
        re.I | re.S,
    ):
        fail("#134: docs/user/app.md must say drop is local ZIP/mbox, no URLs")


# #136 — defer doctor CAS scan so large archives open fast.
_DOCTOR_ISSUE_API = re.compile(
    r"("
    r"(?:api\.)?doctorIssues\b"
    r"|(?:api\.)?doctor_issues\b"
    r"|invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']doctor_issues"
    r")",
)
_DOCTOR_RUN_API = re.compile(r"(?:api\.)?doctorRun\b|doctor_run_cmd|\bdoctor_run\b")
_QUICK_DOCTOR = re.compile(
    r"("
    r"doctorIssuesQuick"
    r"|doctor_issues_quick"
    r"|quick\s*:\s*true"
    r"|mode\s*:\s*[\"']quick[\"']"
    r"|doctorIssues\s*\(\s*true\s*\)"
    r")",
    re.I,
)
_GC_ON_OPEN = re.compile(r"\bgc_cas\b|\bgcCas\s*:\s*true")
_GC_THREAD = re.compile(
    r"("
    r"thread::spawn"
    r"|std::thread"
    r"|Builder::new\s*\(\s*\)\s*\.name\s*\(\s*[\"'][^\"']*gc"
    r")",
    re.I,
)
_OPEN_AWAIT_SKIP = _SCROLL_HELPER_SKIP | {
    "api",
    "invoke",
    "doctorIssues",
    "doctorIssuesQuick",
    "doctorRun",
    "people",
    "linkEvents",
    "status",
    "open",
    "init",
    "pickFolder",
    "rememberedPath",
    "showErr",
    "csv",
    "trim",
}


def _await_expression(src: str, start: int) -> str:
    """Expression after `await` at `start`, up to `;` / newline at depth 0."""
    n = len(src)
    i = start
    while i < n and src[i] in " \t":
        i += 1
    depth = 0
    j = i
    while j < n:
        nxt = _js_next(src, j)
        if nxt != j:
            j = nxt
            continue
        c = src[j]
        if c in "({[":
            depth += 1
        elif c in ")}]":
            if depth == 0:
                break
            depth -= 1
        elif c in ";,\n" and depth == 0:
            break
        j += 1
    return src[i:j].strip()


def _doctor_expr_is_quick(expr: str) -> bool:
    return bool(_QUICK_DOCTOR.search(expr))


def _doctor_expr_is_full_scan(expr: str) -> bool:
    if not _DOCTOR_ISSUE_API.search(expr):
        return False
    return not _doctor_expr_is_quick(expr)


def _open_awaited_surface(web: str, roots: tuple[str, ...]) -> str:
    """Bodies of `roots` plus only functions they `await` (not fire-and-forget)."""
    parts: list[str] = []
    seen: set[str] = set()

    def walk(name: str) -> None:
        if name in seen or name in _OPEN_AWAIT_SKIP:
            return
        seen.add(name)
        body = _ts_function_body(web, name) or _function_body(web, name)
        if not body:
            return
        parts.append(body)
        for m in re.finditer(r"\bawait\s+", body):
            expr = _await_expression(body, m.end())
            ident = re.match(r"(?:api\.)?([A-Za-z_]\w*)", expr)
            if ident:
                walk(ident.group(1))

    for root_name in roots:
        walk(root_name)
    return "\n".join(parts)


def _awaited_exprs(src: str) -> list[str]:
    return [_await_expression(src, m.end()) for m in re.finditer(r"\bawait\s+", src)]


def _core_rust_blob(root: Path) -> str:
    src = root / "crates" / "interlace-core" / "src"
    if not src.is_dir():
        return ""
    return "\n".join(p.read_text() for p in sorted(src.rglob("*.rs")) if p.is_file())


def _full_doctor_scan_body(core_src: str, rust: str) -> str:
    """Archive::doctor_issues (full) plus callees — not the quick path."""
    blob = core_src + "\n" + rust
    body = _rust_body_with_callees(blob, "doctor_issues")
    if body.strip():
        return body
    return _rust_function_body(blob, "doctor_issues")


def assert_defer_doctor_cas(crate: Path) -> None:
    """#136: open shows People without awaiting a full CAS walk.

    Doctor badge may load async or stay empty until the Doctor tab.
    Doctor tab (load / Refresh) still runs the full scan that walks
    referenced CAS hashes. A missing blob still surfaces. No background
    GC on open.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#136: App.svelte required (open / applyStatus must show People first)")
    doctor_path = crate / "web" / "lib" / "DoctorPane.svelte"
    if not doctor_path.is_file():
        fail("#136: DoctorPane.svelte required (full CAS scan on the Doctor tab)")
    app = app_path.read_text()
    doctor_txt = doctor_path.read_text()
    web = _web_logic(crate)
    rust = _tauri_rust_blob(crate)
    root = repo_root()
    core_src = _core_rust_blob(root)
    docs_app = root / "docs" / "user" / "app.md"
    dtxt = docs_app.read_text() if docs_app.is_file() else ""
    docs_doc = root / "docs" / "user" / "doctor.md"
    ddoc = docs_doc.read_text() if docs_doc.is_file() else ""

    apply_body = _ts_function_body(web, "applyStatus") or _function_body(web, "applyStatus")
    if not apply_body.strip():
        fail("#136: applyStatus required (open / create / reopen last archive)")
    if not re.search(r"\b(?:api\.)?people\s*\(|\brefreshPeople\s*\(", apply_body):
        fail(
            "#136: applyStatus must still load People "
            "(people list + status) when opening clears"
        )

    open_path = _ts_function_body(web, "openPath") or _function_body(web, "openPath")
    if not open_path.strip():
        fail("#136: openPath required (opening must clear before a full CAS walk)")
    if not re.search(r"\bopening\s*=\s*true\b", open_path):
        fail("#136: openPath must set opening = true while the archive opens")
    if not re.search(r"\bopening\s*=\s*false\b", open_path):
        fail("#136: opening must clear so People can render (do not wait on CAS)")
    if not re.search(r"\bapplyStatus\s*\(", open_path):
        fail("#136: openPath must apply status / people (applyStatus) when opening")

    create_body = _ts_function_body(web, "createArchive") or _function_body(
        web, "createArchive"
    )
    if not create_body.strip():
        fail("#136: createArchive required (create must show People without a CAS walk)")
    if not re.search(r"\bapplyStatus\s*\(", create_body):
        fail("#136: createArchive must apply status / people without waiting on CAS")

    if not re.search(r"rememberedPath|openPath\s*\(", app):
        fail("#136: reopen last archive must go through openPath / applyStatus")

    # 1) Open / applyStatus does not await a full CAS walk before People / opening.
    open_surface = _open_awaited_surface(
        web, ("applyStatus", "openPath", "createArchive", "openPicker")
    )
    if not open_surface.strip():
        open_surface = apply_body + "\n" + open_path + "\n" + create_body
    open_clean = _without_comments(open_surface)
    for expr in _awaited_exprs(open_clean):
        if _DOCTOR_RUN_API.search(expr):
            fail(
                "#136: open / applyStatus must not await doctorRun "
                "(People must not wait on a doctor action / GC)"
            )
        if _doctor_expr_is_full_scan(expr):
            fail(
                "#136: open / applyStatus must show People without awaiting a full "
                "CAS walk (cas_get / every attachments.cas_hash) before opening "
                "clears — Doctor badge may be async or empty until the Doctor tab"
            )
    if re.search(r"\bcas_get\b", open_clean) and re.search(r"cas_hash", open_clean):
        fail(
            "#136: applyStatus / open must not walk every attachments.cas_hash / "
            "cas_get before People render"
        )

    # Rust open / create / status must not themselves walk CAS or start GC.
    for name in ("open", "init", "hold", "status"):
        body = _rust_body_with_callees(rust, name)
        if not body.strip():
            continue
        if _GC_ON_OPEN.search(body):
            fail(
                f"#136: no background GC on open "
                f"(gc_cas must not run from Rust {name}())"
            )
        if re.search(r"\bcas_get\b", body) and re.search(
            r"cas_hash|attachments", body
        ):
            fail(
                f"#136: Rust {name}() must not walk attachments.cas_hash / cas_get "
                "(opening must not wait on a full CAS scan)"
            )
        if re.search(r"\bdoctor_issues\s*\(", body) and not _doctor_expr_is_quick(body):
            fail(
                f"#136: Rust {name}() must not run the full doctor_issues CAS walk "
                "(People stay behind opening if open/status awaits it)"
            )

    # People render when opening clears — not inside the spinner, not gated on doctor.
    if not re.search(r"booting\s*\|\|\s*opening|opening\s*\|\|\s*booting", app):
        fail(
            "#136: opening must gate the spinner so People render when opening clears"
        )
    boot = _boot_opening_block(app)
    if re.search(r"data-people-sidebar|{#each\s+people\b", boot):
        fail(
            "#136: People list must render after opening clears, "
            "not inside the opening spinner"
        )
    if not re.search(r"data-people-sidebar|{#each\s+people\b", app):
        fail("#136: People list must still render after open (sidebar / people rows)")

    # 2) Doctor tab still runs the full scan (load / Refresh / doctorIssues).
    load_body = _ts_function_body(doctor_txt, "load") or _function_body(doctor_txt, "load")
    if not load_body.strip():
        fail("#136: DoctorPane load must run the full doctor scan")
    load_clean = _without_comments(load_body)
    if not any(_doctor_expr_is_full_scan(expr) for expr in _awaited_exprs(load_clean)):
        # Fire-and-forget still counts if load calls the full API (Refresh / tab).
        if not _DOCTOR_ISSUE_API.search(load_clean) or _doctor_expr_is_quick(load_clean):
            fail(
                "#136: Doctor tab (DoctorPane load) must run a full scan "
                "(doctorIssues / doctor_issues) that walks referenced CAS hashes "
                "— not only a quick SQLite+FTS check"
            )
        if _doctor_expr_is_quick(load_clean) and not any(
            _doctor_expr_is_full_scan(expr) for expr in _awaited_exprs(load_clean)
        ):
            fail(
                "#136: Doctor tab must invoke the full doctorIssues scan "
                "(not doctorIssuesQuick / quick: true only)"
            )
    if not re.search(r"\bRefresh\b", doctor_txt):
        fail("#136: Doctor tab must keep Refresh (full scan)")
    if not re.search(r"onclick=\{[^}]*\bload\b", doctor_txt):
        fail("#136: Refresh must call load (full doctorIssues scan)")
    if not re.search(r"onMount\s*\(\s*\(\s*\)\s*=>\s*\{[^}]*\bload\s*\(", doctor_txt, re.S):
        if "load()" not in doctor_txt:
            fail("#136: DoctorPane must load the full scan when the Doctor tab opens")

    # IPC used by the Doctor tab still calls the full Archive::doctor_issues.
    cmd_body = _rust_body_with_callees(rust, "doctor_issues_cmd")
    if not cmd_body.strip():
        fail(
            "#136: doctor_issues_cmd must still run the full doctor_issues scan "
            "(Doctor tab / Refresh)"
        )
    if not re.search(r"\bdoctor_issues\s*\(", cmd_body):
        fail(
            "#136: doctor_issues_cmd must call doctor_issues() "
            "(full scan, not only a quick flag)"
        )
    if re.search(r"doctor_issues_quick", cmd_body) and not re.search(
        r"\bdoctor_issues\s*\(", cmd_body
    ):
        fail("#136: Doctor-tab IPC must run the full doctor_issues path")

    full_body = _full_doctor_scan_body(core_src, rust)
    if not full_body.strip():
        fail("#136: Archive::doctor_issues (full) must still exist for the Doctor tab")
    if not re.search(r"\bcas_get\b", full_body):
        fail(
            "#136: full doctor scan must cas_get referenced hashes "
            "(Doctor tab still walks CAS)"
        )
    if not re.search(r"cas_hash", full_body):
        fail(
            "#136: full doctor scan must walk attachments.cas_hash "
            "(referenced CAS hashes)"
        )
    if not re.search(r"CAS blob missing", full_body):
        fail(
            "#136: a missing blob must still surface as a doctor issue "
            "on the full path (Doctor tab / doctor_issues)"
        )

    # CLI with no flag stays a full scan.
    cli = root / "crates" / "interlace-core" / "src" / "cli.rs"
    if cli.is_file():
        cli_txt = cli.read_text()
        if not re.search(r"\bdoctor_issues\s*\(\s*\)", cli_txt):
            fail(
                "#136: CLI `interlace doctor` (no flag) must keep a full "
                "doctor_issues() scan"
            )

    # 3) No background GC on open (applyStatus / open / create / boot).
    if _GC_ON_OPEN.search(open_clean):
        fail(
            "#136: no background GC on open "
            "(gc_cas / GC thread not started from applyStatus/open)"
        )
    if _GC_THREAD.search(open_clean) and _GC_ON_OPEN.search(open_clean + "\n" + rust):
        fail("#136: no background GC thread on open")
    boot_src = _without_comments(app)
    if _GC_ON_OPEN.search(boot_src) and re.search(
        r"rememberedPath|opening\s*=\s*true", boot_src
    ):
        # gcCas: true on the Doctor tab is fine; fail only if it sits on the open path.
        for name in ("applyStatus", "openPath", "createArchive", "openPicker"):
            body = _ts_function_body(web, name) or _function_body(web, name)
            if body and _GC_ON_OPEN.search(_without_comments(body)):
                fail(
                    "#136: no background GC on open "
                    f"(gc_cas must not start from {name})"
                )
    if re.search(r"thread::spawn", rust) and re.search(
        r"gc_cas", _rust_body_with_callees(rust, "open") + _rust_body_with_callees(rust, "init")
    ):
        fail("#136: no background GC thread started from open/init")

    # 4) Docs (D24): open is not blocked on hashing cas/; Doctor tab finds missing blobs.
    if not dtxt.strip():
        fail(
            "#136: docs/user/app.md required "
            "(open is not blocked on hashing cas/; Doctor tab still finds missing blobs)"
        )
    if not re.search(
        r"("
        r"not blocked on hashing"
        r"|without (?:waiting|blocking).{0,60}(?:hash|cas/|CAS)"
        r"|open(?:ing)?(?:ing an archive| of (?:an? )?archive)?.{0,80}"
        r"not.{0,40}(?:hash|walk|scan|blocked).{0,40}cas"
        r"|People.{0,60}(?:immediately|without waiting).{0,60}(?:cas|doctor|hash)"
        r"|does not wait.{0,40}(?:hash|cas/|CAS)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail("#136: docs/user/app.md must say open is not blocked on hashing cas/")
    if not re.search(
        r"("
        r"Doctor tab.{0,100}(?:missing blob|referenced.{0,20}blob|walk.{0,40}cas)"
        r"|missing blob.{0,80}Doctor"
        r"|Doctor.{0,80}(?:still )?(?:walk|find).{0,40}(?:missing|referenced|cas|blob)"
        r")",
        dtxt,
        re.I | re.S,
    ):
        fail(
            "#136: docs/user/app.md must say the Doctor tab still finds a missing blob "
            "(full scan of referenced CAS hashes)"
        )
    if not ddoc.strip():
        fail(
            "#136: docs/user/doctor.md required "
            "(Doctor tab still walks referenced CAS / finds missing blobs)"
        )
    if not re.search(
        r"("
        r"Doctor tab.{0,120}(?:missing|referenced|cas_hash|CAS)"
        r"|CAS file missing"
        r"|missing blob"
        r"|cas_hash"
        r"|referenced.{0,40}(?:CAS|blob|hash|attachments)"
        r")",
        ddoc,
        re.I | re.S,
    ):
        fail(
            "#136: docs/user/doctor.md must say the Doctor tab still walks "
            "referenced CAS hashes / finds a missing blob"
        )


# #220 — import progress: Cancel hook + calm done (no thread kill).
# #266 owns enabled Cancel + import_cancel (surgical: this block no
# longer requires disabled / forbids the command / “cannot be stopped”).
_IMPORT_HONEST_COPY = re.compile(
    r"("
    r"cannot stop"
    r"|cannot be stopped"
    r"|no stop"
    r"|cannot be cancelled"
    r"|cannot be canceled"
    r"|not implemented"
    r")",
    re.I,
)
_IMPORT_FAKE_CMD = re.compile(r"\b(?:import_cancel|cancelImport|importCancel)\b")
_IMPORT_THREAD_KILL = re.compile(
    r"("
    r"thread::[^\n]{0,60}\b(?:kill|terminate)\b"
    r"|JoinHandle::[^\n]{0,60}\babort\b"
    r"|\b(?:JoinHandle|join_handle|import_handle)\b[^\n]{0,80}\.abort\s*\("
    r"|\bpthread_kill\b"
    r")"
)
_IMPORT_STATUS_RUNNING = re.compile(
    r"Status[\s\S]{0,160}(?:progress\.status|\brunning\b)",
    re.I,
)
_IMPORT_CONSOLE_PATH = re.compile(
    r"console\.log\s*\((?:[^)]|\n){0,240}(?:\bpath\b|progress\.path|\bprogress\b)",
    re.I,
)
_IMPORT_TOAST_PATH = re.compile(
    r"(?:onToast|toast)\s*\??\s*\((?:[^)]|\n){0,240}(?:\bpath\b|progress\.path)",
    re.I,
)
_IMPORT_PARALLEL = re.compile(
    r"("
    r"parallel[\s_-]*import"
    r"|import[\s_-]*in[\s_-]*parallel"
    r"|concurrent[\s_-]*import"
    r"|data-parallel-import"
    r")",
    re.I,
)
_IMPORT_GC_BTN = re.compile(
    r"("
    r">\s*(?:GC(?:\s+CAS)?|gc_cas|Run GC)\s*<"
    r"|\bgcCas\b"
    r"|\bgc_cas\b"
    r"|background\s+GC"
    r")",
    re.I,
)
_IMPORT_DOCS_PROGRESS = re.compile(
    r"("
    r"progress.{0,40}visible"
    r"|visible.{0,40}progress"
    r"|progress in-window"
    r"|import progress"
    r")",
    re.I | re.S,
)
_IMPORT_DOCS_NO_STOP = re.compile(
    r"("
    r"cannot stop"
    r"|cannot be stopped"
    r"|no stop"
    r"|cannot be cancelled"
    r"|cannot be canceled"
    r"|disabled cancel"
    r"|cancel.{0,80}disabled"
    r"|disabled.{0,80}cancel"
    r")",
    re.I | re.S,
)
_IMPORT_DOCS_QUIET = re.compile(
    r"("
    r"quiet done"
    r"|import done.{0,100}(?:quiet|muted|success)"
    r"|(?:quiet|muted|success).{0,80}import done"
    r")",
    re.I | re.S,
)
_IMPORT_DISABLED = re.compile(
    r"("
    r"(?<![\w-])disabled(?:=\{[^}]*\}|=[\"'][^\"']*[\"'])?(?=[\s/>])"
    r"|aria-disabled\s*=\s*(?:\{true\}|[\"']true[\"'])"
    r")"
)
_IMPORT_DIALOG = re.compile(r"^<(?:Dialog|AlertDialog)\b")
_IMPORT_DESCRIBEDBY = re.compile(
    r"aria-describedby\s*=\s*(?:[\"']([^\"']+)[\"']|\{\s*[\"']([^\"']+)[\"']\s*\})",
    re.I,
)


def _import_describedby_blob(src: str, tag: str) -> str:
    """Text of the element referenced by aria-describedby on the cancel control."""
    m = _IMPORT_DESCRIBEDBY.search(tag)
    if not m:
        return ""
    ident = m.group(1) or m.group(2)
    if not ident:
        return ""
    found = re.search(
        rf"""\bid\s*=\s*(?:["']{re.escape(ident)}["']"""
        rf"""|\{{\s*["']{re.escape(ident)}["']\s*\}})""",
        src,
    )
    if not found:
        return ""
    start = src.rfind("<", 0, found.start() + 1)
    if start < 0:
        start = found.start()
    return src[start : found.end() + 360]


def _import_honest_blob(src: str, tag: str) -> str:
    """Cancel tag + nearby window + described-by target (honest no-stop copy)."""
    return "\n".join(
        (
            tag,
            _status_hook_blob(src, "data-import-cancel"),
            _import_describedby_blob(src, tag),
        )
    )


def assert_import_progress(crate: Path) -> None:
    """#220: import progress — Cancel hook + calm done (no thread kill)."""
    import_path = crate / "web" / "lib" / "ImportPane.svelte"
    import_src = import_path.read_text() if import_path.is_file() else ""

    # 1) data-import-cancel exists in ImportPane.svelte
    if "data-import-cancel" not in import_src:
        fail(
            "#220: data-import-cancel required in ImportPane.svelte "
            "(Cancel while running)"
        )

    rust_path = crate / "src" / "main.rs"
    rust = rust_path.read_text() if rust_path.is_file() else ""
    rust_surf = _without_comments(rust)

    # 2) No thread:: kill / JoinHandle:: abort as “cancel”.
    if _IMPORT_THREAD_KILL.search(rust_surf):
        fail(
            "#220: no thread:: kill / JoinHandle:: abort as cancel "
            "(do not kill the import thread)"
        )

    # 3) Status running still rendered in the import pane.
    if not _IMPORT_STATUS_RUNNING.search(import_src):
        fail("#220: Status running must still be rendered in the import pane")

    # 4) data-import-done still present; no Dialog wrapping done;
    #    no bg-gradient / confetti / celebration on done.
    if "data-import-done" not in import_src:
        fail(
            "#220: keep data-import-done "
            "(quiet counts; no Dialog / bg-gradient / confetti)"
        )
    done_tag = _contrast_surface_tag(import_src, "data-import-done")
    done_at = import_src.find("data-import-done")
    wrap_tags = ([done_tag] if done_tag else []) + _ancestor_tags(
        import_src, done_at, limit=10
    )
    if any(_IMPORT_DIALOG.search(t) for t in wrap_tags):
        fail("#220: data-import-done must not be wrapped in a Dialog")
    done_blob = _status_hook_blob(import_src, "data-import-done")
    if (
        _STATUS_GRADIENT.search(done_blob)
        or _STATUS_CONFETTI.search(done_blob)
        or _STATUS_CELEBRATION.search(_hue_surface(done_blob))
    ):
        fail(
            "#220: data-import-done must not use bg-gradient / confetti / "
            "celebration"
        )

    # 5) No console.log of path; no toast of the import path.
    import_surf = _hue_surface(import_src)
    if _IMPORT_CONSOLE_PATH.search(import_surf):
        fail("#220: do not console.log the import path")
    if _IMPORT_TOAST_PATH.search(import_surf):
        fail("#220: do not toast the import path")

    # 6) No parallel-import UI, no fetch( / HTTP import,
    #    no background GC button on Import.
    if _IMPORT_PARALLEL.search(import_surf):
        fail("#220: no parallel-import UI")
    if _APPEARANCE_FETCH.search(import_surf):
        fail("#220: no fetch( / HTTP import")
    if _IMPORT_GC_BTN.search(import_surf):
        fail("#220: no background GC button on Import")

    # 7) docs/user/app.md: progress visible + quiet done.
    #    (#266 owns “Cancel stops”; do not require “cannot be stopped”.)
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    if not dtxt.strip():
        fail(
            "#220: docs/user/app.md required — progress visible + quiet done"
        )
    if not _IMPORT_DOCS_PROGRESS.search(dtxt):
        fail("#220: docs/user/app.md must say import progress is visible")
    if not _IMPORT_DOCS_QUIET.search(dtxt):
        fail("#220: docs/user/app.md must say import done stays quiet")

    # 8) Do not soften #q, sidebar, overlay titlebar, inspector, CSP,
    #     #219 tokens / data-import-done, #218 overlay / no Theme.
    svelte_files = _product_svelte(crate)
    svelte_blob = "\n".join(p.read_text() for p in svelte_files)
    app_path = crate / "web" / "App.svelte"
    app = app_path.read_text() if app_path.is_file() else ""
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = search_path.read_text() if search_path.is_file() else ""
    conf = (crate / "tauri.conf.json").read_text()
    css_path = crate / "web" / "app.css"
    css = css_path.read_text() if css_path.is_file() else ""
    light_blob = _contrast_light_blob(css)
    dark_blob = _contrast_dark_blob(css)
    if not re.search(r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""", search):
        fail('#220: keep id="q" as the canonical query field (#208)')
    if not re.search(r"\bdata-people-sidebar\b", app):
        fail("#220: keep data-people-sidebar (#159 / #212)")
    if not re.search(r"titleBarStyle", conf) and not re.search(
        r"\bdata-tauri-drag-region\b", app
    ):
        fail("#220: keep the overlay titlebar (#211)")
    if not re.search(r"\bdata-person-inspector\b", app):
        fail("#220: keep data-person-inspector (#213)")
    if CSP not in conf:
        fail("#220: do not soften tauri CSP")
    if not _css_var(light_blob, _STATUS_WARNING_NAMES) or not _css_var(
        dark_blob, _STATUS_WARNING_NAMES
    ):
        fail("#220: keep #219 --warning / --color-warning in light and dark")
    if "data-import-done" not in svelte_blob:
        fail("#220: keep #219 data-import-done")
    if not _css_var(css, _APPEARANCE_SCRIM_NAMES):
        fail("#220: keep #218 --overlay / --scrim / --lightbox-scrim")
    if _APPEARANCE_THEME_UI.search(svelte_blob) or _APPEARANCE_MENU_LABEL.search(
        svelte_blob
    ):
        fail("#220: keep #218 — no Theme / Appearance menu / data-theme")


# #266 — real import cancel (cooperative flag; Cancel enabled while running).
_IMPORT_CANCEL_CMD = _IMPORT_FAKE_CMD
_IMPORT_CANCEL_UNCOND_DISABLED = re.compile(
    r"("
    r"(?<![\w-])disabled(?:=\{true\}|=[\"']true[\"'])?(?=[\s/>])"
    r"|aria-disabled\s*=\s*(?:\{true\}|[\"']true[\"'])"
    r")"
)
_IMPORT_CANCEL_CLICK = re.compile(r"\b(?:onclick|on:click)\s*=")
_IMPORT_CANCEL_API_CALL = re.compile(
    r"("
    r"\bapi\s*\.\s*importCancel\s*\("
    r"|\bapi\s*\.\s*import_cancel\s*\("
    r"|\bapi\s*\.\s*cancelImport\s*\("
    r"|invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']import_cancel[\"']"
    r")"
)
_IMPORT_CANCEL_FLAG = re.compile(
    r"("
    r"\bAtomicBool\b"
    r"|\bImportCancel\b"
    r"|\bcancel\s*:"
    r"|\bis_cancelled\b"
    r"|\bis_canceled\b"
    r")"
)
_IMPORT_TICK_INTERRUPTED = re.compile(
    r"("
    r"""status\s*===\s*["']interrupted["']"""
    r"""|["']interrupted["']\s*===\s*[\w.]*status"""
    r"""|\.includes\s*\(\s*["']interrupted["']"""
    r"""|["']interrupted["']"""
    r")",
)
_IMPORT_DOCS_STOPS = re.compile(
    r"cancel.{0,120}stop",
    re.I | re.S,
)
_IMPORT_SELF_PROBE = re.compile(r"self\s*\.\s*probe\s*\(")
_IMPORT_CANCEL_WORD = re.compile(r"\b(?:Cancelled|is_cancelled|is_canceled)\b")
_IMPORT_STOPS_AFTER_FILE = re.compile(r"Stops after this file")
_IMPORT_AFTER_THIS_FILE = re.compile(r"after this file", re.I)
_IMPORT_CANCEL_OPEN = re.compile(r"\bopen\b", re.I)


def _import_fn_checks_cancel(src: str, name: str) -> bool:
    """`fn name(..., cancel...)` body mentions Cancelled / is_cancelled."""
    if not re.search(rf"fn\s+{re.escape(name)}\s*\([^)]*\bcancel\b", src, re.S):
        return False
    body = _rust_fn_body(src, name)
    return bool(body and _IMPORT_CANCEL_WORD.search(body))


_UPSERT_UPDATE_BLAKE3 = re.compile(
    r"UPDATE\s+sources\b[\s\S]{0,500}\bfile_blake3\b",
    re.I,
)
_UPSERT_SELECT_BLAKE3 = re.compile(r"SELECT\b[^;]{0,200}file_blake3", re.I)
_UPSERT_SELECT_ORIGIN = re.compile(r"SELECT\b[^;]{0,200}origin_path", re.I)


def _upsert_origin_fallback_or_hash_update(upsert: str, abort: str) -> bool:
    """Reuse a hashless sources row: UPDATE file_blake3, or origin_path after a blake3 miss."""
    blob = f"{upsert}\n{abort}"
    if _UPSERT_UPDATE_BLAKE3.search(blob):
        return True
    blake3_sel = _UPSERT_SELECT_BLAKE3.search(upsert)
    if not blake3_sel:
        return False
    for origin_sel in _UPSERT_SELECT_ORIGIN.finditer(upsert):
        if origin_sel.start() <= blake3_sel.start():
            continue
        between = upsert[blake3_sel.end() : origin_sel.start()]
        if "else" not in between:
            return True
    return False


def _wa_media_zip_match_body(wa: str) -> str:
    """`match read_zip_entry_capped(...) { ... }` body (media read, not fn def)."""
    m = re.search(r"match\s+read_zip_entry_capped\s*\(", wa)
    if not m:
        return ""
    paren = wa.find("(", m.start())
    if paren < 0:
        return ""
    close_paren = _match_closer(wa, paren)
    if close_paren < 0:
        return ""
    brace = wa.find("{", close_paren)
    if brace < 0:
        return ""
    close_b = _match_closer(wa, brace)
    if close_b < 0:
        return wa[brace + 1 :]
    return wa[brace + 1 : close_b]


def _import_cancel_struct_docs(model: str) -> str:
    """Rustdoc / attributes immediately above `pub struct ImportCancel`."""
    m = re.search(r"pub struct ImportCancel\b", model)
    if not m:
        return ""
    docs: list[str] = []
    for line in reversed(model[: m.start()].splitlines()):
        s = line.strip()
        if (
            s.startswith("///")
            or s.startswith("//!")
            or s.startswith("//")
            or s.startswith("#[")
            or not s
        ):
            docs.append(line)
            continue
        break
    docs.reverse()
    return "\n".join(docs)


def assert_import_cancel(crate: Path) -> None:
    """#266: cooperative Cancel — enabled while running; in-file abort; sources reuse."""
    root = repo_root()
    import_path = crate / "web" / "lib" / "ImportPane.svelte"
    import_src = import_path.read_text() if import_path.is_file() else ""
    rust_path = crate / "src" / "main.rs"
    rust = rust_path.read_text() if rust_path.is_file() else ""
    api_path = crate / "web" / "lib" / "api.ts"
    api = api_path.read_text() if api_path.is_file() else ""
    rust_surf = _without_comments(rust)
    api_surf = _without_comments(api)

    # 1) import_cancel / importCancel in main.rs AND api.ts (first fail today).
    if not _IMPORT_CANCEL_CMD.search(rust_surf):
        fail(
            "#266: import_cancel (or importCancel) required in "
            "crates/interlace-tauri/src/main.rs"
        )
    if not _IMPORT_CANCEL_CMD.search(api_surf):
        fail(
            "#266: import_cancel (or importCancel) required in "
            "crates/interlace-tauri/web/lib/api.ts"
        )

    # 2) ImportPane click / handler calls that API.
    if "data-import-cancel" not in import_src:
        fail("#266: keep #220 data-import-cancel")
    cancel_tag = _contrast_surface_tag(import_src, "data-import-cancel")
    if not cancel_tag or not _IMPORT_CANCEL_CLICK.search(cancel_tag):
        fail(
            "#266: data-import-cancel must have a click / handler "
            "(onclick / on:click)"
        )
    if not _IMPORT_CANCEL_API_CALL.search(import_src):
        fail(
            "#266: ImportPane must call api.importCancel "
            "(or invoke import_cancel) from the Cancel handler"
        )

    # 3) Cancel is enabled while running (not a bare disabled / {true}).
    if _IMPORT_CANCEL_UNCOND_DISABLED.search(cancel_tag):
        fail(
            "#266: data-import-cancel must be enabled while running "
            "(not a bare disabled / disabled={true}; "
            "disabled={…} only when not running / already cancelling)"
        )

    # 4) Core or Tauri mentions a cancel flag.
    model = (root / "crates" / "interlace-core" / "src" / "model.rs").read_text()
    import_mod = (root / "crates" / "interlace-core" / "src" / "import" / "mod.rs")
    import_txt = import_mod.read_text() if import_mod.is_file() else ""
    ctx_path = root / "crates" / "interlace-core" / "src" / "import" / "context.rs"
    ctx_txt = ctx_path.read_text() if ctx_path.is_file() else ""
    flag_blob = _without_comments(model + "\n" + import_txt + "\n" + ctx_txt + "\n" + rust)
    if not _IMPORT_CANCEL_FLAG.search(flag_blob) and not re.search(
        r"\binterrupted\b", rust_surf
    ):
        fail(
            "#266: core or Tauri must mention a cancel flag "
            "(AtomicBool / ImportCancel / cancel / interrupted)"
        )

    # 5) tick / progress treats interrupted as terminal (not only done/failed).
    tick = _ts_fn_body(import_src, "tick") or _function_body(import_src, "tick")
    if not tick or not _IMPORT_TICK_INTERRUPTED.search(tick):
        fail(
            "#266: tick / progress must treat interrupted "
            "(or failed-on-cancel) as terminal (not only done/failed)"
        )

    # 6) No JoinHandle abort / thread::kill.
    if _IMPORT_THREAD_KILL.search(rust_surf):
        fail(
            "#266: no JoinHandle abort / thread::kill "
            "(cooperative flag only)"
        )

    # 7) docs: Cancel stops the import (not “cannot be stopped”).
    docs = root / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    if not dtxt.strip():
        fail("#266: docs/user/app.md required — Cancel stops the import")
    if _IMPORT_DOCS_NO_STOP.search(dtxt):
        fail(
            "#266: docs/user/app.md must not say Cancel is disabled / "
            "the import cannot be stopped"
        )
    if not _IMPORT_DOCS_STOPS.search(dtxt):
        fail("#266: docs/user/app.md must say Cancel stops the import")

    # 8) WhatsApp import() must not call self.probe( (second full ZIP hash/open).
    wa_path = root / "crates" / "interlace-core" / "src" / "import" / "whatsapp.rs"
    wa = wa_path.read_text() if wa_path.is_file() else ""
    import_body = _rust_fn_body(wa, "import")
    if not import_body.strip():
        fail("#266: crates/interlace-core/src/import/whatsapp.rs fn import required")
    if _IMPORT_SELF_PROBE.search(import_body):
        fail(
            "#266: WhatsApp import() must not call self.probe( "
            "(second full ZIP hash/open)"
        )

    # 9) Cancel on ZIP open / list / hash — not only maybe_commit.
    if not _import_fn_checks_cancel(import_txt, "hash_file"):
        fail(
            "#266: hash_file must check cancel "
            "(Cancelled / is_cancelled), not only maybe_commit"
        )
    if not _import_fn_checks_cancel(wa, "open_zip_cancellable"):
        fail(
            "#266: ZIP open must be cancellable "
            "(open_zip_cancellable + Cancelled / is_cancelled)"
        )
    if not _import_fn_checks_cancel(wa, "list_zip"):
        fail(
            "#266: list_zip must check cancel "
            "(Cancelled / is_cancelled), not only maybe_commit"
        )

    # 10) ImportPane must not promise only “Stops after this file”.
    help_blob = _import_describedby_blob(import_src, cancel_tag)
    pane_cancel = help_blob + "\n" + import_src
    if _IMPORT_STOPS_AFTER_FILE.search(pane_cancel):
        fail(
            "#266: ImportPane must not promise only “Stops after this file”"
        )
    if _IMPORT_AFTER_THIS_FILE.search(help_blob) and not re.search(
        r"\b(?:hash|open|checkpoint)\b", help_blob, re.I
    ):
        fail(
            "#266: ImportPane must not promise only “after this file”"
        )
    if not help_blob.strip() or not _IMPORT_CANCEL_OPEN.search(help_blob):
        fail(
            "#266: ImportPane cancel help must mention ZIP open "
            "(hash / open / checkpoint), not “Stops after this file”"
        )

    # 11) Still no JoinHandle abort / thread::kill (keep #220 / earlier #266).
    if _IMPORT_THREAD_KILL.search(rust_surf):
        fail(
            "#266: no JoinHandle abort / thread::kill "
            "(cooperative flag only)"
        )

    # 12) upsert_source / abort_cancelled: origin_path fallback or UPDATE file_blake3.
    upsert_body = _rust_fn_body(import_txt, "upsert_source")
    abort_body = _rust_fn_body(import_txt, "abort_cancelled")
    if not upsert_body.strip():
        fail("#266: upsert_source required in crates/interlace-core/src/import/mod.rs")
    if not _upsert_origin_fallback_or_hash_update(upsert_body, abort_body):
        fail(
            "#266: upsert_source / abort_cancelled must fall back to "
            "origin_path when blake3 misses, or UPDATE file_blake3 "
            "on the existing row (not a hashless-only insert)"
        )

    # 13) WhatsApp media Err arm near read_zip_entry_capped returns Cancelled.
    media_match = _without_comments(_wa_media_zip_match_body(wa))
    if (
        not media_match.strip()
        or not re.search(r"\bCancelled\b", media_match)
        or not re.search(r"\breturn\b", media_match)
    ):
        fail(
            "#266: WhatsApp media Err arm near read_zip_entry_capped "
            "must return Cancelled (not only ctx.warn / media_read)"
        )

    # 14) ImportCancel docs must not embed #266.
    cancel_docs = _import_cancel_struct_docs(model)
    if "#266" in cancel_docs:
        fail("#266: ImportCancel docs in model.rs must not contain #266")
