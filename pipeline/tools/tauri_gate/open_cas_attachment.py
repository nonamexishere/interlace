"""#317 — Open a stored CAS attachment with the default app.

Open menuitem on CasAttach data-reveal-menu (same gate as Reveal).
New hash-only open_cas (not open_url / reveal_cas). ConfirmDialog
before invoke. /usr/bin/open without -R.

Fold: sniff_mime + fs::copy to temp_dir as interlace-<hash>.<ext>.
Do not rename the CAS blob. Menu clamp lives in the sibling fold.

Must-IDs: open-cas-menu, open-cas-omitted, open-cas-cmd,
open-cas-resolve, open-cas-open, open-cas-typed-temp,
open-cas-confirm, open-cas-keep-135, open-cas-keep-272,
open-cas-toast, open-cas-locale, open-cas-d24.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.media_bubble_lib import _SHARE_AIRDROP
from tauri_gate.media_lightbox_lib import (
    _HEIC_TRANSCODE,
    _VOICE_MISSING,
    _VOICE_OMITTED,
)
from tauri_gate.media_linkify_lib import (
    _PLUGIN_SHELL,
    _SHELL_CAP,
    _find_open_url_cmd,
    _hook_element_blocks,
    _rust_http_only,
)
from tauri_gate.scan import (
    CSP,
    _ARBITRARY_SHELL,
    _expand_fn_calls,
    _function_body,
    _match_closer,
    _rust_body_with_callees,
    _rust_call_arg,
    _rust_fn_signature,
    _rust_function_body,
    _svelte_markup,
    _tauri_rust_blob,
    _ts_fn_body,
    _without_comments,
)
from tauri_gate.status_toasts_chrome import (
    _invoke_payloads,
    _payload_has_path_or_url,
    _windows_around,
)

_ISSUE = "#317"
_T_OPEN = re.compile(r"""\bt\s*\(\s*["']open["']\s*\)""")
_T_REVEAL = re.compile(r"""\bt\s*\(\s*["']revealInFinder["']\s*\)""")
_T_CALL = re.compile(r"""\bt\s*\(\s*["']([A-Za-z_][\w]*)["']""")
_OPEN_CAS_SNAKE = (
    "open_cas",
    "open_attachment",
    "open_cas_blob",
    "open_cas_file",
    "open_cas_attachment",
)
_OPEN_CAS_CAMEL = (
    "openCas",
    "openAttachment",
    "openCasBlob",
    "openCasFile",
    "openCasAttachment",
)
_BANNED_CMDS = frozenset(
    {"open_url", "reveal_cas", "reveal_archive", "cas_data_url", "open"}
)
_OPEN_CAS_INVOKE = re.compile(
    r"invoke\s*(?:<[^>]*>)?\s*\(\s*[\"'](?:"
    + "|".join(re.escape(n) for n in _OPEN_CAS_SNAKE)
    + r")[\"']"
    r"|\.?(?:"
    + "|".join(re.escape(n) for n in _OPEN_CAS_CAMEL)
    + r")\s*\("
)
_KIND_ONLY = re.compile(
    r"\bisImage\b|\bisPdf\b|\bisVideo\b"
    r"|kind\s*===\s*[\"'](?:image|pdf|video)[\"']"
)
_CONTEXT_GATE = re.compile(
    r"(?:"
    r"!\s*(?:hash|h)\b"
    r"|omitted"
    r"|missing"
    r"|hashOf"
    r")"
)
_LEAK = re.compile(
    r"("
    r"/Users/"
    r"|/home/"
    r"|file:"
    r"|https?://"
    r"|cas/"
    r"|[0-9a-fA-F]{64}"
    r"|archive_root"
    r"|cas_blob"
    r"|cas_hash"
    r"|casHash"
    r"|revealMenu\.hash"
    r"|st\.path"
    r")",
)
_DESC_BIND_LEAK = re.compile(
    r"description\s*=\s*\{[^}]{0,240}"
    r"(?:hash|path|url|file:|cas/|filename|cas_hash|casHash|archive)",
    re.I,
)
_TOAST_OPEN = re.compile(r"""showToast\s*\(\s*["']Could not open["']\s*\)""")
_TOAST_LEAK = re.compile(
    r"showToast\s*\(\s*(?:"
    r"e\b|err\b|error\b"
    r"|String\s*\("
    r"|`[^`]*\$\{"
    r"|[\"'][^\"']{0,40}(?:\$\{|\+)"
    r")"
)
_SNIFF_MIME = re.compile(r"\bsniff_mime\s*\(")
_FS_COPY = re.compile(r"(?:std::)?fs::copy\s*\(")
_TEMP_DIR = re.compile(r"(?:std::env::)?temp_dir\s*\(")
_INTERLACE_PREFIX = re.compile(r"interlace-")
_SAFE_EXT = re.compile(
    r"""["'](?:jpg|jpeg|png|gif|webp|heic|heif|mp4|mov|pdf|mp3|ogg|oga|m4a|wav|webm|bin)["']"""
)
_FORMAT_TEMP = re.compile(
    r"format!\s*\(\s*[\"'][^\"']*interlace-"
    r"|format!\s*\(\s*[\"'][^\"']*\{\}[^\"']*\.\{"
)
_CAS_MUTATE = re.compile(
    r"("
    r"\bcanon\s*\.\s*(?:set_extension|with_extension|rename)\s*\("
    r"|(?:std::)?fs::rename\s*\(\s*&?canon"
    r")"
)
_HTTP_CLIENT = re.compile(r"\b(?:reqwest|ureq|hyper::Client|tauri-plugin-http)\b")
_FILE_CSP = re.compile(r"(?:^|[;\s])file:", re.I)
_DOCS_OPEN = re.compile(
    r"(?:right-click|context menu).{0,200}(?:stored )?(?:attachment|CAS).{0,200}Open"
    r"|Open.{0,160}default app",
    re.I | re.S,
)
_DOCS_CONFIRM = re.compile(r"confirm", re.I)
_DOCS_PLACEHOLDER = re.compile(
    r"(?:omitted|missing).{0,180}placeholder"
    r"|placeholder.{0,180}(?:omitted|missing)",
    re.I | re.S,
)
_DOCS_REVEAL = re.compile(r"Reveal in Finder")
_DOCS_NO_SHARE = re.compile(r"no Share|not Share|Share sheet|AirDrop", re.I)
_DOCS_NO_HTTP = re.compile(
    r"no http|not http|never http|still no http|not a remote",
    re.I,
)
_OPEN_LINK = re.compile(r"Open link")
_TITLE = "Open this file?"
_TOAST_COPY = "Could not open"
_REVEAL_TOAST = "Could not reveal"


def _fn(src: str, name: str) -> str:
    return _ts_fn_body(src, name) or _function_body(src, name) or ""


def _read(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


def _reveal_menu_markup(cas: str) -> str:
    markup = _svelte_markup(cas)
    return "\n".join(_hook_element_blocks(markup, "data-reveal-menu"))


def _brace_after(src: str, open_at: int) -> str:
    if open_at < 0 or open_at >= len(src) or src[open_at] != "{":
        return ""
    close = _match_closer(src, open_at)
    if close < 0:
        return src[open_at + 1 :]
    return src[open_at + 1 : close]


def _onclick_before(src: str, pos: int) -> str:
    head = src[:pos]
    last = None
    for m in re.finditer(r"onclick\s*=\s*\{", head):
        last = m
    if not last:
        return ""
    return _brace_after(src, last.end() - 1)


def _confirm_block(cas: str) -> str:
    markup = _svelte_markup(cas)
    blocks = _hook_element_blocks(markup, "ConfirmDialog")
    if blocks:
        return "\n".join(blocks)
    i = cas.find("<ConfirmDialog")
    if i < 0:
        return ""
    return cas[i : i + 900]


def _onconfirm_src(cas: str, confirm: str) -> str:
    m = re.search(r"onconfirm\s*=\s*\{", confirm)
    if not m:
        return ""
    expr = _brace_after(confirm, m.end() - 1).strip()
    if not expr:
        return ""
    named = re.fullmatch(r"([A-Za-z_][\w]*)", expr)
    if named:
        return _fn(cas, named.group(1)) or expr
    return _expand_fn_calls(cas, expr, 2)


def _uses_phrase(src: str, en: dict[str, str], phrase: str) -> bool:
    if phrase in src:
        return True
    for key, val in en.items():
        if val == phrase and re.search(
            rf"""\bt\s*\(\s*["']{re.escape(key)}["']""", src
        ):
            return True
    return False


def _t_values_in(src: str, en: dict[str, str]) -> list[str]:
    out: list[str] = []
    for m in _T_CALL.finditer(src):
        val = en.get(m.group(1))
        if val is not None:
            out.append(val)
    return out


def _find_open_cas_cmd(rust: str, web: str) -> str:
    for name in _OPEN_CAS_SNAKE:
        if name in _BANNED_CMDS:
            continue
        if re.search(rf"\bfn\s+{re.escape(name)}\b", rust) or re.search(
            rf"invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']{re.escape(name)}[\"']",
            web,
        ):
            return name
    for camel, snake in zip(_OPEN_CAS_CAMEL, _OPEN_CAS_SNAKE):
        if re.search(rf"\b{re.escape(camel)}\s*[:=(]", web):
            return snake
    gh = re.search(r"generate_handler!\s*\[([^\]]*)\]", rust, re.S)
    if not gh:
        return ""
    for name in re.findall(r"\b([a-z][a-z0-9_]*)\b", gh.group(1)):
        if name in _BANNED_CMDS:
            continue
        sig = _rust_fn_signature(rust, name)
        body = _rust_function_body(rust, name)
        if (
            re.search(r"\bhash\b", sig, re.I)
            and "cas_blob_path" in body
            and "/usr/bin/open" in body
            and not re.search(r"[\"']-R[\"']", body)
        ):
            return name
    return ""


def _handler_invokes_open(cas: str, handler: str) -> bool:
    if not handler.strip():
        return False
    exp = _expand_fn_calls(cas, handler, 2)
    return bool(_OPEN_CAS_INVOKE.search(handler) or _OPEN_CAS_INVOKE.search(exp))


def _outside_cas(body: str) -> bool:
    return bool(
        re.search(
            r"("
            r"starts_with"
            r"|outside cas"
            r"|join\(\s*[\"']cas[\"']"
            r"|[\"']cas/"
            r")",
            body,
        )
    )


def _sniffs_blob(own: str, body: str) -> bool:
    blob = own + "\n" + body
    if not _SNIFF_MIME.search(blob):
        return False
    if re.search(r"sniff_mime\s*\(\s*[\"']", blob):
        return False
    return bool(
        re.search(
            r"fs::read\s*\(|File::open\s*\(|read_exact\s*\("
            r"|sniff_mime\s*\(\s*&",
            blob,
        )
    )


def _typed_temp_name(blob: str) -> bool:
    has_hash = bool(re.search(r"\bhash\b", blob))
    has_interlace = bool(_INTERLACE_PREFIX.search(blob))
    has_ext = bool(_SAFE_EXT.search(blob))
    has_fmt = bool(
        _FORMAT_TEMP.search(blob)
        or re.search(
            r"format!\s*\([^;]{0,200}\bhash\b[^;]{0,80}\bext\b"
            r"|format!\s*\([^;]{0,200}\bext\b[^;]{0,80}\bhash\b",
            blob,
        )
    )
    if has_interlace and has_hash and (has_ext or has_fmt):
        return True
    return bool(has_fmt and has_hash and has_ext)


def _open_target_args(launch: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(r"\.arg\s*\(", launch):
        arg = _rust_call_arg(launch, m.end() - 1).strip()
        if re.search(r"""["']-R["']""", arg):
            continue
        if "/usr/bin/open" in arg:
            continue
        out.append(arg)
    return out


def _opens_only_cas_canon(launch: str) -> bool:
    args = _open_target_args(launch)
    if not args:
        return True
    return all(
        re.search(r"\bcanon\b", a)
        and not re.search(r"temp_dir|tempfile|\btmp\b|\bdest\b|\bnamed\b", a, re.I)
        for a in args
    )


def assert_open_cas_attachment(crate: Path) -> None:
    """#317: Open stored CAS in the default app after confirm.

    Fold: sniff_mime + temp copy `interlace-<hash>.<ext>`; do not rename cas/.
    """
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    if not cas_path.is_file():
        fail(f"{_ISSUE}: CasAttach.svelte required (Open on data-reveal-menu)")

    cas_raw = cas_path.read_text()
    cas_c = _without_comments(cas_raw)
    menu = _reveal_menu_markup(cas_raw)

    # 1) open-cas-menu — fail-today: Reveal only.
    if not menu.strip():
        fail(
            f"{_ISSUE}: keep data-reveal-menu "
            "(Open lives on the existing Reveal context menu)"
        )
    if not _T_OPEN.search(menu):
        fail(
            f"{_ISSUE}: CasAttach data-reveal-menu must include an Open "
            'menuitem (t("open")) next to Reveal'
        )
    if not _T_REVEAL.search(menu) and "revealInFinder" not in menu:
        fail(
            f"{_ISSUE}: Reveal in Finder menuitem must stay on "
            "data-reveal-menu (Open is additive)"
        )
    if _KIND_ONLY.search(menu):
        fail(
            f"{_ISSUE}: Open uses the same gate as Reveal "
            "(any stored hash, not omitted / missing) — "
            "do not lock photo / PDF / video-only"
        )

    api_path = crate / "web" / "lib" / "api.ts"
    api = _read(api_path)
    rust = _tauri_rust_blob(crate)
    web = cas_raw + "\n" + api
    hits_path = crate / "web" / "lib" / "SearchHits.svelte"
    hits = _read(hits_path)
    insp_path = crate / "web" / "lib" / "PeopleInspector.svelte"
    insp = _read(insp_path)
    app_path = crate / "web" / "App.svelte"
    app = _read(app_path)
    vid_path = crate / "web" / "lib" / "CasVideo.svelte"
    vid = _read(vid_path)
    pdf_path = crate / "web" / "lib" / "CasPdf.svelte"
    pdf = _read(pdf_path)
    copy_path = crate / "web" / "lib" / "TimelineCopyMenu.svelte"
    copy_menu = _read(copy_path)
    confirm_path = crate / "web" / "lib" / "ConfirmDialog.svelte"
    confirm_src = _read(confirm_path)
    en_path = crate / "web" / "lib" / "locales" / "en.ts"
    tr_path = crate / "web" / "lib" / "locales" / "tr.ts"
    en = _chrome_pack_entries(_read(en_path)) if en_path.is_file() else {}
    tr = _chrome_pack_entries(_read(tr_path)) if tr_path.is_file() else {}
    toml = _read(crate / "Cargo.toml")
    pkg = _read(crate / "package.json")
    caps = _read(crate / "capabilities" / "default.json")
    ent = _read(crate / "Interlace.entitlements")
    conf = _read(crate / "tauri.conf.json")
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""

    # 2) open-cas-omitted — no menu / no Open when omitted, missing, or no hash.
    ctx = _windows_around(
        cas_raw, re.compile(r"oncontextmenu|on:contextmenu"), before=40, after=280
    )
    if not _CONTEXT_GATE.search(ctx) or not re.search(r"omitted", ctx):
        fail(
            f"{_ISSUE}: omitted / missing / no hash must not offer Open "
            "(same oncontextmenu gate as Reveal — no menu, not a disabled item)"
        )
    if not re.search(r"missing", ctx) or not re.search(r"hashOf|cas_hash|casHash", ctx):
        fail(
            f"{_ISSUE}: omitted / missing / no hash must not offer Open "
            "(same oncontextmenu gate as Reveal)"
        )
    omitted_win = _windows_around(
        _svelte_markup(cas_raw), re.compile(r"a\.omitted|\.omitted"), before=40, after=220
    )
    missing_win = _windows_around(
        _svelte_markup(cas_raw),
        re.compile(r"a\.missing|\.missing|!hashOf"),
        before=40,
        after=280,
    )
    if _T_OPEN.search(omitted_win) or _T_OPEN.search(missing_win):
        fail(
            f"{_ISSUE}: omitted / missing stay placeholders — no Open "
            "(no menu, same as Reveal today)"
        )

    # 3) open-cas-cmd — new hash-only command, not open_url / reveal_cas.
    cmd = _find_open_cas_cmd(rust, web)
    if not cmd or cmd in _BANNED_CMDS:
        fail(
            f"{_ISSUE}: new Rust command open_cas (name may vary) required "
            "— not open_url / reveal_cas / reveal_archive"
        )
    if not re.search(
        r"generate_handler!\s*\[[^\]]*\b" + re.escape(cmd) + r"\b", rust, re.S
    ):
        fail(f"{_ISSUE}: register {cmd} in generate_handler")
    if not _OPEN_CAS_INVOKE.search(cas_c) and not _OPEN_CAS_INVOKE.search(api):
        fail(
            f"{_ISSUE}: frontend must call api.openCas(hash) / "
            f'invoke("{cmd}", {{ hash }}) — hash only'
        )
    invoke_rx = re.compile(
        r"invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']" + re.escape(cmd) + r"[\"']"
    )
    payloads = _invoke_payloads(web, invoke_rx)
    if not payloads:
        call_win = _windows_around(web, _OPEN_CAS_INVOKE, before=40, after=160)
        if not re.search(r"\bhash\b", call_win, re.I):
            fail(
                f"{_ISSUE}: frontend must send only the hash to {cmd} "
                "(do not pass a path or URL from the webview)"
            )
        if _payload_has_path_or_url(call_win):
            fail(
                f"{_ISSUE}: frontend must send only the hash to {cmd} "
                "(do not pass a path or URL from the webview)"
            )
    for payload in payloads:
        if not re.search(r"\bhash\b", payload, re.I):
            fail(
                f"{_ISSUE}: frontend must send only the hash to {cmd} "
                f'(invoke("{cmd}", {{ hash }}))'
            )
        if _payload_has_path_or_url(payload):
            fail(
                f"{_ISSUE}: frontend must send only the hash to {cmd} "
                "(do not pass a path or URL from the webview)"
            )

    # 4) open-cas-resolve — same CAS path as Reveal; hash only.
    sig = _rust_fn_signature(rust, cmd)
    own = _rust_function_body(rust, cmd)
    body = _rust_body_with_callees(rust, cmd)
    if not own.strip() and not body.strip():
        fail(
            f"{_ISSUE}: Rust command {cmd} must resolve cas/ab/cd/<hash> "
            "(fn taking the hash only)"
        )
    if not re.search(r"\bhash\b", sig, re.I):
        fail(f"{_ISSUE}: {cmd} must take a hash (not a path or URL)")
    if re.search(r"\b(?:path|url|file|href|uri)\s*:", sig, re.I):
        fail(
            f"{_ISSUE}: {cmd} must take the hash only — "
            "do not take a path or URL from the webview"
        )
    if "cas_blob_path" not in body:
        fail(
            f"{_ISSUE}: {cmd} must resolve cas/ab/cd/<hash> via cas_blob_path "
            "(same path Reveal uses)"
        )
    if not re.search(r"\bcanonicalize\s*\(", body):
        fail(f"{_ISSUE}: {cmd} must canonicalize the CAS path")
    if not _outside_cas(body):
        fail(f"{_ISSUE}: {cmd} must refuse anything outside cas/")
    if not re.search(r"\barchive_root\b", body):
        fail(f"{_ISSUE}: {cmd} must read archive_root from app state")

    # 5) open-cas-open — /usr/bin/open without -R; not open_url.
    if not re.search(r"std::process|\buse\s+std::process", rust):
        fail(
            f"{_ISSUE}: OS-open with std::process "
            "(not tauri-plugin-shell / plugin-opener)"
        )
    if "/usr/bin/open" not in body:
        fail(
            f"{_ISSUE}: {cmd} must OS-open the resolved blob with /usr/bin/open "
            "(default app, not Finder)"
        )
    if not re.search(r"Command::new|std::process::Command", own or body):
        fail(
            f"{_ISSUE}: {cmd} must use std::process::Command "
            "(/usr/bin/open without -R)"
        )
    launch = own if "/usr/bin/open" in own else body
    if re.search(r"[\"']-R[\"']", launch):
        fail(
            f"{_ISSUE}: {cmd} must run /usr/bin/open without -R "
            "(Reveal keeps -R; do not share reveal's Finder select)"
        )
    if re.search(r"[\"']https?://", own):
        fail(f"{_ISSUE}: {cmd} must not open http(s) — local CAS file only")
    if _ARBITRARY_SHELL.search(own) or _ARBITRARY_SHELL.search(body):
        fail(
            f"{_ISSUE}: no shell of arbitrary commands — "
            "only /usr/bin/open on the CAS file"
        )
    for m in re.finditer(r"Command::new\s*\(", launch):
        arg = _rust_call_arg(launch, m.end() - 1)
        if "/usr/bin/open" not in arg:
            fail(
                f"{_ISSUE}: no shell of arbitrary commands — "
                "Command::new must be /usr/bin/open on the CAS file"
            )
    if re.search(
        r"\bopen_url\s*\(|invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']open_url[\"']",
        cas_c,
    ) or re.search(r"\bopenUrl\s*\(", cas_c):
        fail(
            f"{_ISSUE}: do not reuse open_url for a local file "
            "(#272 stays http(s) only)"
        )

    # 5b) open-cas-typed-temp — sniff + copy to temp; do not rename cas/.
    if not _sniffs_blob(own, body):
        fail(
            f"{_ISSUE}: {cmd} must sniff_mime the blob bytes (or a short "
            "header) so the temp name gets a safe extension — do not "
            "/usr/bin/open the extensionless CAS path"
        )
    if not _FS_COPY.search(own) and not _FS_COPY.search(body):
        fail(
            f"{_ISSUE}: {cmd} must fs::copy (or std::fs::copy) the blob "
            "to std::env::temp_dir() as interlace-<hash>.<ext>"
        )
    if not _TEMP_DIR.search(own) and not _TEMP_DIR.search(body):
        fail(
            f"{_ISSUE}: {cmd} must copy into std::env::temp_dir() "
            "(interlace-<hash>.<safe-ext> — not the cas/ blob)"
        )
    if not _typed_temp_name(own) and not _typed_temp_name(body):
        fail(
            f"{_ISSUE}: temp name must be interlace-<hash>.<ext> "
            "(or format! with the hash + sniffed ext) — ext from "
            "sniffed MIME, not a webview filename"
        )
    if not _SAFE_EXT.search(own) and not _SAFE_EXT.search(body):
        fail(
            f"{_ISSUE}: safe ext from sniffed MIME only "
            "(jpg/png/gif/webp/heic/mp4/mov/pdf/mp3/ogg/m4a/wav/webm/bin)"
        )
    if _opens_only_cas_canon(launch):
        fail(
            f"{_ISSUE}: /usr/bin/open without -R must run on the temp "
            "copy, not only the CAS canon blob"
        )
    if _CAS_MUTATE.search(own) or _CAS_MUTATE.search(body):
        fail(
            f"{_ISSUE}: do not rename or set_extension the CAS blob "
            "(canon / cas_blob_path stays hash-named; copy to temp)"
        )

    # 6) open-cas-confirm — ConfirmDialog in CasAttach before invoke.
    if not confirm_path.is_file():
        fail(f"{_ISSUE}: ConfirmDialog.svelte required (host it in CasAttach)")
    if "ConfirmDialog" not in cas_raw or not re.search(
        r"import\s+ConfirmDialog\b", cas_raw
    ):
        fail(
            f"{_ISSUE}: host ConfirmDialog inside CasAttach "
            "(before invoke — do not plumb App ask through Search)"
        )
    if re.search(r"\bask\s*\(", cas_c):
        fail(
            f"{_ISSUE}: host ConfirmDialog inside CasAttach "
            "(do not plumb App ask through Search)"
        )
    confirm = _confirm_block(cas_raw)
    if not confirm.strip():
        fail(
            f"{_ISSUE}: CasAttach must mount <ConfirmDialog> "
            "(title Open this file?; confirmLabel Open)"
        )
    if not _uses_phrase(cas_raw, en, _TITLE) and not _uses_phrase(confirm, en, _TITLE):
        fail(f"{_ISSUE}: confirm title must be \"{_TITLE}\"")
    if _OPEN_LINK.search(confirm):
        fail(f"{_ISSUE}: confirmLabel is Open, not \"Open link\" (#272 keeps Open link)")
    has_open_label = bool(
        re.search(r"""confirmLabel\s*=\s*["']Open["']""", confirm)
        or re.search(r"""confirmLabel\s*=\s*\{["']Open["']\}""", confirm)
        or _T_OPEN.search(confirm)
        or _uses_phrase(confirm, en, "Open")
    )
    if not has_open_label:
        fail(f"{_ISSUE}: confirmLabel must be Open (not \"Open link\")")
    if _DESC_BIND_LEAK.search(confirm):
        fail(
            f"{_ISSUE}: confirm description must be a generic local sentence "
            "— never a filesystem path, hash, or URL"
        )
    for val in _t_values_in(confirm, en):
        if _LEAK.search(val):
            fail(
                f"{_ISSUE}: confirm description must be a generic local sentence "
                "— never a filesystem path, hash, or URL"
            )
    for m in re.finditer(r"""description\s*=\s*["'`]([^"'`]*)["'`]""", confirm):
        if _LEAK.search(m.group(1)):
            fail(
                f"{_ISSUE}: confirm description must be a generic local sentence "
                "— never a filesystem path, hash, or URL"
            )
    open_click = ""
    om = _T_OPEN.search(menu)
    if om:
        open_click = _onclick_before(menu, om.start())
    if _handler_invokes_open(cas_raw, open_click):
        fail(
            f"{_ISSUE}: Open menuitem must open ConfirmDialog first "
            f"— do not invoke {cmd} on the click (Cancel does nothing)"
        )
    onconfirm = _onconfirm_src(cas_raw, confirm)
    if not _handler_invokes_open(cas_raw, onconfirm):
        fail(
            f"{_ISSUE}: ConfirmDialog onconfirm must invoke {cmd} "
            "(Cancel dismisses and does not invoke)"
        )
    if not re.search(r">\s*Cancel\s*<", confirm_src):
        fail(f"{_ISSUE}: ConfirmDialog Cancel must still dismiss")
    if re.search(r"oncancel|onCancel", confirm) and _handler_invokes_open(
        cas_raw, confirm
    ):
        fail(f"{_ISSUE}: Cancel must not invoke {cmd}")

    # 7) open-cas-toast — chrome-only, no path / hash / body.
    open_fn = ""
    for name in (*_OPEN_CAS_CAMEL, "doOpen", "confirmOpen", "openAttachment"):
        blob = _fn(cas_c, name)
        if blob and (_OPEN_CAS_INVOKE.search(blob) or name in _OPEN_CAS_CAMEL):
            open_fn += blob + "\n"
    open_fn += onconfirm
    if not _TOAST_OPEN.search(cas_raw) and not _uses_phrase(cas_raw, en, _TOAST_COPY):
        fail(
            f"{_ISSUE}: Open catch must toast \"{_TOAST_COPY}\" "
            "(chrome-only — no path / hash / body)"
        )
    if _TOAST_LEAK.search(open_fn) or _TOAST_LEAK.search(
        _windows_around(cas_c, _OPEN_CAS_INVOKE, before=80, after=200)
    ):
        fail(
            f"{_ISSUE}: fail toast is chrome-only "
            f"(\"{_TOAST_COPY}\" — no path / hash / error body)"
        )
    if _LEAK.search(
        _windows_around(cas_c, re.compile(r"showToast\s*\("), before=20, after=80)
    ):
        toast_win = _windows_around(
            cas_c, re.compile(r"showToast\s*\("), before=20, after=80
        )
        if _OPEN_CAS_INVOKE.search(
            _windows_around(cas_c, re.compile(r"showToast\s*\("), before=200, after=40)
        ) or _TOAST_COPY in toast_win:
            if _LEAK.search(toast_win):
                fail(
                    f"{_ISSUE}: fail toast is chrome-only "
                    "(no path / hash / body)"
                )

    # 8) open-cas-locale — same new ChromeKey on both packs.
    if "open" not in en or "open" not in tr:
        fail(
            f"{_ISSUE}: t(\"open\") must exist on both en.ts and tr.ts "
            "(same ChromeKey — #278)"
        )
    if en.get("open", "").strip() != "Open":
        fail(f"{_ISSUE}: en open must be \"Open\" (not \"Open link\")")
    if en.get("open") == "Open link" or tr.get("open") == "Open link":
        fail(f"{_ISSUE}: t(\"open\") is the attachment menuitem, not \"Open link\"")
    extra_en = set(en) - set(tr)
    extra_tr = set(tr) - set(en)
    if extra_en or extra_tr:
        bits: list[str] = []
        if extra_en:
            bits.append("in en only: " + ", ".join(sorted(extra_en)))
        if extra_tr:
            bits.append("in tr only: " + ", ".join(sorted(extra_tr)))
        fail(f"{_ISSUE}: same ChromeKey on both en and tr packs — " + "; ".join(bits))

    # 9) SearchHits must not grow a second menu.
    if hits_path.is_file():
        if "CasAttach" not in hits:
            fail(
                f"{_ISSUE}: SearchHits must keep mounting CasAttach "
                "(Open comes free — do not add a Search-only menu)"
            )
        if "data-reveal-menu" in hits or _T_OPEN.search(hits):
            fail(
                f"{_ISSUE}: SearchHits must not grow a second menu "
                "(CasAttach reuse is enough)"
            )
        if "ConfirmDialog" in hits or _OPEN_CAS_INVOKE.search(hits):
            fail(
                f"{_ISSUE}: SearchHits must not grow a second menu / confirm "
                "(CasAttach reuse is enough)"
            )

    # 10) No PeopleInspector Open.
    if insp_path.is_file():
        if (
            _T_OPEN.search(insp)
            or _OPEN_CAS_INVOKE.search(insp)
            or "data-reveal-menu" in insp
            or re.search(r"\bcas_hash\b|\bcasHash\b", insp)
        ):
            fail(f"{_ISSUE}: do not add PeopleInspector Open (skip inspector)")

    if copy_menu and (_T_OPEN.search(copy_menu) or _OPEN_CAS_INVOKE.search(copy_menu)):
        fail(
            f"{_ISSUE}: do not put Open on TimelineCopyMenu "
            "(attachment menu is CasAttach data-reveal-menu)"
        )

    # 11) open-cas-keep-135 — reveal_cas still hash-only + -R.
    reveal_sig = _rust_fn_signature(rust, "reveal_cas")
    reveal_own = _rust_function_body(rust, "reveal_cas")
    if not reveal_sig.strip() or not reveal_own.strip():
        fail(f"{_ISSUE}: keep reveal_cas (hash only + -R) — do not soften #135")
    if not re.search(r"\bhash\b", reveal_sig, re.I):
        fail(f"{_ISSUE}: reveal_cas must still take a hash (do not soften #135)")
    if re.search(r"\b(?:path|url|file|href|uri)\s*:", reveal_sig, re.I):
        fail(
            f"{_ISSUE}: reveal_cas must still take the hash only — "
            "no path from the webview"
        )
    if "cas_blob_path" not in reveal_own:
        fail(
            f"{_ISSUE}: reveal_cas must still resolve cas/ab/cd/<hash> "
            "via cas_blob_path"
        )
    if not re.search(r"[\"']-R[\"']", reveal_own):
        fail(f"{_ISSUE}: keep reveal_cas /usr/bin/open -R (do not soften #135)")
    if not re.search(r"generate_handler!\s*\[[^\]]*\breveal_cas\b", rust, re.S):
        fail(f"{_ISSUE}: keep reveal_cas in generate_handler (do not soften #135)")
    if not re.search(
        r"revealCas\s*:\s*\(\s*hash\b|invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']reveal_cas[\"']\s*,\s*\{\s*hash",
        api,
    ):
        fail(f"{_ISSUE}: api.revealCas must still take hash only (do not soften #135)")
    if _REVEAL_TOAST not in cas_raw:
        fail(f"{_ISSUE}: keep Reveal fail toast \"{_REVEAL_TOAST}\"")

    # 12) open-cas-keep-272 — open_url http(s) only + Open link.
    url_cmd = _find_open_url_cmd(rust, app + "\n" + api)
    if not url_cmd or url_cmd == cmd:
        fail(
            f"{_ISSUE}: keep open_url for http(s) links "
            "(do not reuse it for CAS)"
        )
    url_body = _rust_body_with_callees(rust, url_cmd)
    if not _rust_http_only(url_body):
        fail(f"{_ISSUE}: {url_cmd} must still only accept http/https (do not soften #272)")
    app_c = _without_comments(app)
    if not _OPEN_LINK.search(app_c):
        fail(f"{_ISSUE}: App URL confirm must keep confirmLabel Open link (#272)")
    if "Open this link?" not in app:
        fail(f"{_ISSUE}: keep App ask(\"Open this link?\" …) for bubble URLs")

    # 13) keep #274 reveal_archive argument-free.
    arch_sig = _rust_fn_signature(rust, "reveal_archive")
    arch_own = _rust_function_body(rust, "reveal_archive")
    if not arch_sig.strip() or not arch_own.strip():
        fail(f"{_ISSUE}: keep reveal_archive (argument-free) — do not soften #274")
    if re.search(r"\b(?:path|url|file|href|uri|hash)\s*:", arch_sig, re.I):
        fail(
            f"{_ISSUE}: reveal_archive must stay argument-free "
            "(root from app state — do not soften #274)"
        )
    if "cas_blob_path" in arch_own:
        fail(f"{_ISSUE}: reveal_archive must still reveal the archive root, not a CAS blob")
    if not re.search(r"[\"']-R[\"']", arch_own):
        fail(f"{_ISSUE}: keep reveal_archive /usr/bin/open -R")

    # 14) keep #271 / #118 / #119 in-window viewers; menu only.
    if "casDataUrl" not in cas_raw:
        fail(f"{_ISSUE}: keep casDataUrl in-window viewers (#118 / #119 / #271)")
    if "data-photo-lightbox" not in cas_raw:
        fail(f"{_ISSUE}: keep the in-window photo lightbox (#118)")
    if not vid_path.is_file() or "data-cas-video" not in vid:
        fail(f"{_ISSUE}: keep CasVideo in-window playback (#271)")
    if not pdf_path.is_file() or "data-cas-pdf" not in pdf:
        fail(f"{_ISSUE}: keep CasPdf in-window viewer (#271)")
    if "data-voice-note" not in cas_raw or not re.search(r"<audio\b", cas_raw):
        fail(f"{_ISSUE}: keep the in-app voice-note player (#119)")
    if not _VOICE_OMITTED.search(cas_raw) or not _VOICE_MISSING.search(cas_raw):
        fail(f"{_ISSUE}: omitted / missing must stay placeholders")
    lightbox = "\n".join(_hook_element_blocks(_svelte_markup(cas_raw), "data-photo-lightbox"))
    if _T_OPEN.search(lightbox) or _OPEN_CAS_INVOKE.search(lightbox):
        fail(f"{_ISSUE}: no lightbox chrome Open button — menu only")
    if _T_OPEN.search(vid) or _OPEN_CAS_INVOKE.search(vid):
        fail(f"{_ISSUE}: no CasVideo chrome Open button — menu only")
    if _T_OPEN.search(pdf) or _OPEN_CAS_INVOKE.search(pdf):
        fail(f"{_ISSUE}: no CasPdf chrome Open button — menu only")

    # 15) bans — plugin-shell / opener / HTTP / network.server / file: CSP.
    if _PLUGIN_SHELL.search(toml) or _PLUGIN_SHELL.search(pkg):
        fail(
            f"{_ISSUE}: do not add tauri-plugin-shell / tauri-plugin-opener "
            "(std::process file-only open)"
        )
    if _PLUGIN_SHELL.search(rust) or _PLUGIN_SHELL.search(cas_c):
        fail(
            f"{_ISSUE}: do not add tauri-plugin-shell / tauri-plugin-opener "
            "(std::process file-only open)"
        )
    if _SHELL_CAP.search(caps):
        fail(
            f"{_ISSUE}: capabilities must not add shell:allow-execute / "
            "shell:allow-open / opener"
        )
    if _SHARE_AIRDROP.search(cas_c) or _SHARE_AIRDROP.search(rust):
        fail(f"{_ISSUE}: no Share sheet / AirDrop")
    if _HTTP_CLIENT.search(toml) or _HTTP_CLIENT.search(own) or _HTTP_CLIENT.search(body):
        fail(f"{_ISSUE}: no HTTP client / tauri-plugin-http")
    if "network.server" in ent:
        fail(f"{_ISSUE}: entitlements must omit network.server")
    if CSP not in conf:
        fail(f"{_ISSUE}: do not soften tauri CSP")
    if _FILE_CSP.search(conf):
        fail(f"{_ISSUE}: do not add file: to CSP")
    if _HEIC_TRANSCODE.search(cas_c) or _HEIC_TRANSCODE.search(own):
        fail(f"{_ISSUE}: do not transcode HEIC")
    if re.search(r"[\"']https?://", cas_c):
        fail(f"{_ISSUE}: CasAttach must not use remote http(s) URLs")

    # 16) open-cas-d24
    if not dtxt.strip():
        fail(
            f"{_ISSUE}: docs/user/app.md required — right-click a stored "
            "attachment → Open → default app after confirm"
        )
    doc_win = ""
    for m in re.finditer(
        r".{0,220}(?:"
        r"stored attachment"
        r"|Reveal in Finder"
        r"|default app"
        r"|omitted"
        r"|missing"
        r"|Share sheet"
        r"|AirDrop"
        r").{0,220}",
        dtxt,
        re.I | re.S,
    ):
        doc_win += m.group(0) + "\n"
    if not _DOCS_REVEAL.search(doc_win) and not _DOCS_REVEAL.search(dtxt):
        fail(f"{_ISSUE}: docs/user/app.md must keep Reveal in Finder")
    if not _DOCS_OPEN.search(doc_win) and not _DOCS_OPEN.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say right-click a stored "
            "attachment → Open → default app"
        )
    open_doc = ""
    for m in _DOCS_OPEN.finditer(dtxt):
        i = m.start()
        open_doc += dtxt[max(0, i - 80) : m.end() + 200] + "\n"
    if not _DOCS_CONFIRM.search(open_doc) and not re.search(
        r"Open.{0,200}confirm|confirm.{0,200}Open", dtxt, re.I | re.S
    ):
        fail(
            f"{_ISSUE}: docs/user/app.md must say Open runs after confirm"
        )
    if not _DOCS_PLACEHOLDER.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say omitted / missing stay placeholders"
        )
    if not _DOCS_NO_SHARE.search(doc_win) and not _DOCS_NO_SHARE.search(dtxt):
        fail(f"{_ISSUE}: docs/user/app.md must still say no Share / AirDrop")
    if not _DOCS_NO_HTTP.search(dtxt):
        fail(f"{_ISSUE}: docs/user/app.md must still say no http(s) / remote viewer")
    if re.search(r"/Users/|/home/", cas_c + "\n" + (own or "")):
        fail(f"{_ISSUE}: tests stay placeholders (Ada) — no real home paths")
