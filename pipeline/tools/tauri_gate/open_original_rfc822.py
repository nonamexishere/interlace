"""#373 — Open original rfc822 for a stored mail (People bubble).

Confirmed mix (2026-09-21): isMailRow; Open original always on mail;
missing = disabled calm label (not hide, not dialog); raw_cas_hash on
TimelineRow JSON; dedicated hash-only sibling that always writes .eml
(do not teach sniff); mail-specific confirm; People only; hide when
n>1; keep #317 and #372.

Placeholders Ada / Berk / Self. Same ChromeKey on en.ts + tr.ts.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.last_read import _text, _web_file
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.media_linkify_lib import _PLUGIN_SHELL, _SHELL_CAP, _hook_element_blocks
from tauri_gate.open_cas_attachment import (
    _CAS_MUTATE,
    _FS_COPY,
    _SAFE_EXT,
    _TEMP_DIR,
    _TITLE as _ATTACH_CONFIRM_TITLE,
    _TOAST_OPEN,
)
from tauri_gate.scan import (
    CSP,
    _ARBITRARY_SHELL,
    _expand_fn_calls,
    _match_closer,
    _rust_body_with_callees,
    _rust_call_arg,
    _rust_fn_signature,
    _rust_function_body,
    _svelte_markup,
    _tauri_rust_blob,
    _without_comments,
)
from tauri_gate.search_hit_preview import _fn
from tauri_gate.status_toasts_chrome import (
    _invoke_payloads,
    _payload_has_path_or_url,
    _windows_around,
)

_ISSUE = "#373"

_MENU_ORIG = re.compile(r"""t\s*\(\s*["']openOriginal["']\s*\)""")
_MENU_MISSING = re.compile(r"""t\s*\(\s*["']openOriginalMissing["']\s*\)""")
_MENU_THIS = re.compile(r"""t\s*\(\s*["']searchThisConversation["']\s*\)""")
_MENU_SEARCH = re.compile(r"""t\s*\(\s*["']search["']\s*\)""")
_MENU_COPY = re.compile(
    r"""t\s*\(\s*["']copyText["']\s*\)|t\s*\(\s*["']copyN["']\s*\)"""
)
_T_OPEN = re.compile(r"""\bt\s*\(\s*["']open["']\s*\)""")
_COPY_MENU_HOOK = re.compile(r"\bdata-copy-menu\b")
_IS_MAIL = re.compile(r"\bisMailRow\s*\(")
_N_HIDE = re.compile(
    r"\bn\s*(?:<=|<|===?)\s*1\b"
    r"|\bn\s*<\s*2\b"
    r"|!\s*\(?\s*n\s*>\s*1"
    r"|\bn\s*>\s*1\b"
)
_GMAIL_ONLY = re.compile(
    r"""(?:row\.)?platform\s*===?\s*["']gmail["']"""
)
_HASH_IF = re.compile(
    r"\{#if\s+[^}]*\b(?:raw_cas_hash|rawCasHash|hash)\b[^}]*\}"
)
_DISABLED = re.compile(r"\bdisabled\b")
_BUTTON = re.compile(r"<button\b[^>]*>[\s\S]{0,900}?</button>", re.I)
_HANDLER = re.compile(r"generate_handler!\s*\[(.*?)\]", re.S)
_OPEN_CAS_INVOKE = re.compile(
    r"""invoke\s*(?:<[^>]*>)?\s*\(\s*["']open_cas["']"""
    r"""|\.?\bopenCas\s*\("""
)
_LOOKUP_IPC = re.compile(
    r"""invoke\s*(?:<[^>]*>)?\s*\(\s*["'](?:"""
    r"message_raw(?:_cas(?:_hash)?)?"
    r"|raw_cas_hash"
    r"|get_raw(?:_cas|_mail)?"
    r"|lookup_raw"
    r"|open_original_message"
    r""")["']"""
)
_HEX64 = re.compile(r"\b[0-9a-fA-F]{64}\b")
_SNIFF_RFC = re.compile(r"rfc822|message/rfc822", re.I)
_EML_LIT = re.compile(r"""["']eml["']|\.eml\b""")
_INTERLACE_PREFIX = re.compile(r"interlace-")
_HTTP = re.compile(r"https?://", re.I)
_HTTP_CLIENT = re.compile(r"\b(?:reqwest|ureq|hyper::Client|tauri-plugin-http)\b")
_FILE_CSP = re.compile(r"(?:^|[;\s])file:", re.I)
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
    r")",
)
_DESC_BIND_LEAK = re.compile(
    r"description\s*=\s*\{[^}]{0,240}"
    r"(?:hash|path|url|file:|cas/|filename|cas_hash|casHash|archive)",
    re.I,
)
_TOAST_LEAK = re.compile(
    r"showToast\s*\(\s*(?:"
    r"e\b|err\b|error\b"
    r"|String\s*\("
    r"|`[^`]*\$\{"
    r"|[\"'][^\"']{0,40}(?:\$\{|\+)"
    r")"
)
_RECONSTRUCT = re.compile(
    r"("
    r"\breconstruct"
    r"|build_(?:rfc822|eml|raw_mail)"
    r"|fake_?(?:eml|rfc822)"
    r"|From:\s*\{"
    r")",
    re.I,
)
_VIEW = re.compile(r"\binnerWidth\b|\binnerHeight\b")
_BOX = re.compile(r"\bgetBoundingClientRect\s*\(")
_CLAMP_ADJ = re.compile(
    r"("
    r"(?:style\.)?(?:left|top)\s*="
    r"|copyMenu\.(?:x|y)\s*="
    r"|\b(?:x|y)\s*=\s*(?:Math\.(?:min|max)|[^;\n]{0,80}inner(?:Width|Height))"
    r"|Math\.(?:min|max)\s*\("
    r"|innerWidth\s*-"
    r"|innerHeight\s*-"
    r")"
)
_BANNED_CMDS = frozenset(
    {
        "open_cas",
        "reveal_cas",
        "reveal_archive",
        "open_url",
        "cas_data_url",
        "open",
    }
)
_SIBLING_SNAKE = (
    "open_raw_mail",
    "open_cas_eml",
    "open_raw",
    "open_original",
    "open_rfc822",
    "open_eml",
    "open_raw_cas",
    "open_mail_original",
    "open_original_rfc822",
)
_ATTACH_DESC = "Open this stored file with the default app."
_TOAST_COPY = "Could not open"
_DOCS_OPEN_ORIG = re.compile(r"Open original", re.I)
_DOCS_EML = re.compile(r"\.eml\b")
_DOCS_MISSING = re.compile(
    r"not stored|re-import|preserve-raw|preserve raw",
    re.I,
)
_DOCS_WA = re.compile(
    r"WhatsApp.{0,120}(?:no |not |does not|never).{0,60}Open original"
    r"|Open original.{0,120}WhatsApp.{0,60}(?:no |not |never|does not)",
    re.I | re.S,
)
_DOCS_SEARCH_THIS = re.compile(r"Search this conversation", re.I)
_DOCS_ATTACH_OPEN = re.compile(
    r"(?:right-click|context menu).{0,200}(?:stored )?(?:attachment|CAS).{0,200}Open"
    r"|Open.{0,160}default app",
    re.I | re.S,
)
_DOCS_NO_HTTP = re.compile(
    r"no http|not http|never http|still no http|not a remote",
    re.I,
)
_DOCS_DEFAULT_OFF = re.compile(
    r"preserve-raw.{0,80}(?:default|off|flag)"
    r"|(?:default|off).{0,80}preserve-raw",
    re.I | re.S,
)


def _snake_to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:] if p)


def _rust_struct_body(src: str, name: str) -> str:
    m = re.search(rf"(?:pub\s+)?struct\s+{re.escape(name)}\s*\{{", src)
    if not m:
        return ""
    start = src.find("{", m.start())
    if start < 0:
        return ""
    end = _match_closer(src, start)
    if end < 0:
        return src[start:]
    return src[start : end + 1]


def _brace_after(src: str, open_at: int) -> str:
    if open_at < 0 or open_at >= len(src) or src[open_at] != "{":
        return ""
    close = _match_closer(src, open_at)
    if close < 0:
        return src[open_at + 1 :]
    return src[open_at + 1 : close]


def _menu_button_for_t(src: str, key: str) -> str:
    for block in _BUTTON.findall(src):
        if re.search(rf"""t\s*\(\s*["']{re.escape(key)}["']\s*\)""", block):
            return block
    return ""


def _menu_onclick_for_t(src: str, key: str) -> str:
    block = _menu_button_for_t(src, key)
    if not block:
        return ""
    om = re.search(r"onclick\s*=\s*\{", block)
    if not om:
        return ""
    return _brace_after(block, om.end() - 1).strip()


def _prop_ident(expr: str) -> str:
    expr = expr.strip()
    m = re.match(r"([A-Za-z_][A-Za-z0-9_]*)", expr)
    return m.group(1) if m else ""


def _around(src: str, rx: re.Pattern[str], before: int = 420, after: int = 420) -> str:
    bits: list[str] = []
    for m in rx.finditer(src):
        bits.append(src[max(0, m.start() - before) : m.end() + after])
    return "\n".join(bits)


def _handler_names(rust: str) -> list[str]:
    m = _HANDLER.search(rust)
    if not m:
        return []
    return re.findall(r"\b([a-z][a-z0-9_]*)\b", m.group(1))


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


def _looks_like_eml_open(sig: str, own: str, body: str) -> bool:
    blob = own + "\n" + body
    if not re.search(r"\bhash\b", sig, re.I):
        return False
    if re.search(r"\b(?:path|url|file|href|uri|ext|message_id)\s*:", sig, re.I):
        return False
    if "cas_blob_path" not in blob:
        return False
    if "/usr/bin/open" not in blob:
        return False
    if re.search(r"""["']-R["']""", own):
        return False
    if not _EML_LIT.search(own) and not _EML_LIT.search(blob):
        return False
    return True


def _find_sibling_cmd(rust: str, web: str) -> str:
    ordered: list[str] = []
    for name in _SIBLING_SNAKE:
        if name not in ordered:
            ordered.append(name)
    for name in _handler_names(rust):
        if name not in ordered:
            ordered.append(name)
    for name in ordered:
        if name in _BANNED_CMDS:
            continue
        if not (
            re.search(rf"\bfn\s+{re.escape(name)}\b", rust)
            or re.search(
                rf"""invoke\s*(?:<[^>]*>)?\s*\(\s*["']{re.escape(name)}["']""",
                web,
            )
        ):
            continue
        sig = _rust_fn_signature(rust, name)
        own = _rust_function_body(rust, name)
        body = _rust_body_with_callees(rust, name)
        if _looks_like_eml_open(sig, own, body):
            return name
    return ""


def _confirm_block(src: str) -> str:
    markup = _svelte_markup(src)
    blocks = _hook_element_blocks(markup, "ConfirmDialog")
    if blocks:
        return "\n".join(blocks)
    i = src.find("<ConfirmDialog")
    if i < 0:
        return ""
    return src[i : i + 1100]


def _onconfirm_src(src: str, confirm: str) -> str:
    m = re.search(r"onconfirm\s*=\s*\{", confirm)
    if not m:
        return ""
    expr = _brace_after(confirm, m.end() - 1).strip()
    if not expr:
        return ""
    named = re.fullmatch(r"([A-Za-z_][\w]*)", expr)
    if named:
        return _fn(src, named.group(1)) or expr
    return _expand_fn_calls(src, expr, 2)


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
    for m in re.finditer(r"""\bt\s*\(\s*["']([A-Za-z_][\w]*)["']""", src):
        val = en.get(m.group(1))
        if val is not None:
            out.append(val)
    return out


def _handler_invokes(src: str, handler: str, cmd: str, camel: str) -> bool:
    if not handler.strip():
        return False
    exp = _expand_fn_calls(src, handler, 2)
    blob = handler + "\n" + exp
    if cmd and re.search(
        rf"""invoke\s*(?:<[^>]*>)?\s*\(\s*["']{re.escape(cmd)}["']""",
        blob,
    ):
        return True
    if camel and re.search(rf"\b(?:api\.)?{re.escape(camel)}\s*\(", blob):
        return True
    return bool(_OPEN_CAS_INVOKE.search(blob))


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


def _ts_type_body(src: str, name: str) -> str:
    m = re.search(
        rf"(?:export\s+)?(?:type|interface)\s+{re.escape(name)}\s*=?\s*\{{",
        src,
    )
    if not m:
        return ""
    start = src.find("{", m.start())
    if start < 0:
        return ""
    end = _match_closer(src, start)
    if end < 0:
        return src[start:]
    return src[start : end + 1]


def _clamp_blob(lst: str, menu: str) -> str:
    parts = [
        _fn(lst, "openCopyMenu"),
        _fn(lst, "clampCopyMenu"),
        _fn(lst, "placeCopyMenu"),
        _fn(lst, "positionCopyMenu"),
        _fn(menu, "clampCopyMenu"),
    ]
    for rx in (_VIEW, _BOX, _COPY_MENU_HOOK):
        for m in rx.finditer(lst):
            win = lst[max(0, m.start() - 220) : m.end() + 260]
            if _COPY_MENU_HOOK.search(win) or re.search(r"clientX|clientY|copyMenu", win):
                parts.append(win)
        for m in rx.finditer(menu):
            win = menu[max(0, m.start() - 220) : m.end() + 260]
            if _COPY_MENU_HOOK.search(win) or re.search(r"clientX|clientY", win):
                parts.append(win)
    return "\n".join(p for p in parts if p)


def assert_open_original_rfc822(crate: Path) -> None:
    """#373: mail bubble Open original opens a hash-only .eml temp after confirm."""
    root = repo_root()
    menu_path = _web_file(crate, "TimelineCopyMenu.svelte")
    list_path = _web_file(crate, "TimelineList.svelte")
    rows_path = _web_file(crate, "TimelineRows.svelte")
    mail_path = _web_file(crate, "TimelineMail.ts")
    hits_path = _web_file(crate, "SearchHits.svelte")
    cas_path = _web_file(crate, "CasAttach.svelte")
    import_path = _web_file(crate, "ImportPane.svelte")
    api_path = _web_file(crate, "api.ts")
    confirm_path = _web_file(crate, "ConfirmDialog.svelte")
    en_path = crate / "web" / "lib" / "locales" / "en.ts"
    tr_path = crate / "web" / "lib" / "locales" / "tr.ts"
    docs_path = root / "docs" / "user" / "app.md"
    people_path = root / "crates" / "interlace-core" / "src" / "people.rs"
    timeline_path = root / "crates" / "interlace-core" / "src" / "people" / "timeline.rs"
    model_path = root / "crates" / "interlace-core" / "src" / "model.rs"
    cas_rs_path = crate / "src" / "cas.rs"
    import_cmd_path = crate / "src" / "import_cmd.rs"

    menu_raw = _text(menu_path)
    lst_raw = _text(list_path)
    rows_raw = _text(rows_path)
    mail_raw = _text(mail_path)
    hits_raw = _text(hits_path)
    cas_raw = _text(cas_path)
    import_raw = _text(import_path)
    api_raw = _text(api_path)
    confirm_src = _text(confirm_path)
    docs_raw = _text(docs_path)
    people_raw = _text(people_path)
    timeline_raw = _text(timeline_path)
    model_raw = _text(model_path)
    cas_rs = _text(cas_rs_path)
    import_cmd = _text(import_cmd_path)
    rust = _tauri_rust_blob(crate)
    main_raw = _text(crate / "src" / "main.rs")
    toml = _text(crate / "Cargo.toml")
    pkg = _text(crate / "package.json")
    caps = _text(crate / "capabilities" / "default.json")
    ent = _text(crate / "Interlace.entitlements")
    conf = _text(crate / "tauri.conf.json")

    menu = _without_comments(menu_raw)
    lst = _without_comments(lst_raw)
    hits = _without_comments(hits_raw)
    cas = _without_comments(cas_raw)
    api = _without_comments(api_raw)
    mail = _without_comments(mail_raw)
    people = _without_comments(people_raw)
    timeline = _without_comments(timeline_raw)
    model = _without_comments(model_raw)
    menu_m = _svelte_markup(menu_raw)
    lst_m = _svelte_markup(lst_raw)
    hits_m = _svelte_markup(hits_raw)
    cas_m = _svelte_markup(cas_raw)
    surface = (menu_m or menu) + "\n" + (lst_m or lst)
    web = menu_raw + "\n" + lst_raw + "\n" + api_raw

    # 1) open-orig-menu — primary red today.
    if not menu_path.is_file() or not _MENU_ORIG.search(menu_m or menu):
        fail(
            f'{_ISSUE}: bubble context menu must add Open original '
            '(t("openOriginal")) after t("searchThisConversation")'
        )
    this_t = _MENU_THIS.search(menu_m or menu)
    orig_t = _MENU_ORIG.search(menu_m or menu)
    search_t = _MENU_SEARCH.search(menu_m or menu)
    if this_t and orig_t and orig_t.start() < this_t.start():
        fail(
            f'{_ISSUE}: t("openOriginal") must come after t("searchThisConversation") '
            "(keep #372; this is a new item)"
        )
    if search_t and this_t and this_t.start() < search_t.start():
        fail(
            f'{_ISSUE}: keep t("searchThisConversation") after t("search") (#372)'
        )
    if not _COPY_MENU_HOOK.search(menu_m or menu):
        fail(f"{_ISSUE}: keep data-copy-menu / data-context-menu for the bubble menu")
    if _T_OPEN.search(menu):
        fail(
            f'{_ISSUE}: Open original is t("openOriginal"), not t("open") '
            "(#317 attachment Open stays on CasAttach)"
        )
    orig_click = _menu_onclick_for_t(menu_m or menu, "openOriginal")
    this_click = _menu_onclick_for_t(menu_m or menu, "searchThisConversation")
    search_click = _menu_onclick_for_t(menu_m or menu, "search")
    orig_prop = _prop_ident(orig_click)
    this_prop = _prop_ident(this_click)
    search_prop = _prop_ident(search_click)
    if orig_prop and this_prop and orig_prop == this_prop:
        fail(
            f"{_ISSUE}: Open original must not replace Search this conversation "
            "(distinct handler)"
        )
    if orig_prop and search_prop and orig_prop == search_prop:
        fail(
            f"{_ISSUE}: Open original must not replace #273 Search "
            "(distinct handler)"
        )
    if re.search(r"\binvoke\s*\(|\bapi\.", menu):
        fail(
            f"{_ISSUE}: invoke lives in TimelineList, not TimelineCopyMenu "
            "(#317 keeps this file callback-only)"
        )

    # 2) keep Copy + #273 Search + #372 Search this conversation.
    if not _MENU_COPY.search(menu_m or menu):
        fail(f"{_ISSUE}: keep Copy on the bubble menu (#204 / #370)")
    if not _MENU_SEARCH.search(menu_m or menu):
        fail(f'{_ISSUE}: keep t("search") on the bubble menu (#273)')
    if not this_t:
        fail(
            f'{_ISSUE}: keep t("searchThisConversation") after t("search") (#372)'
        )

    # 3) mail-detect — isMailRow; WhatsApp never grows the item.
    if not re.search(
        r"""platform\s*===?\s*["']gmail["']""", mail
    ) or not re.search(r"""["']email_thread["']""", mail):
        fail(
            f"{_ISSUE}: keep isMailRow as platform === \"gmail\" or "
            "conversation_kind === \"email_thread\" (#117)"
        )
    if not _IS_MAIL.search(lst) and not _IS_MAIL.search(menu):
        fail(
            f"{_ISSUE}: Open original is gated by isMailRow "
            "(gmail or email_thread — not platform === \"gmail\" only, "
            "not any row with a hash)"
        )
    orig_win = _around(surface, _MENU_ORIG)
    if _GMAIL_ONLY.search(orig_win) and not _IS_MAIL.search(lst + "\n" + menu):
        fail(
            f"{_ISSUE}: mail-detect is isMailRow, not platform === \"gmail\" only"
        )
    if not re.search(
        r"\b(?:mail|isMail|isMailRow)\b", orig_win
    ) and not re.search(
        r"\{#if\s+[^}]*(?:mail|isMailRow)", surface
    ):
        fail(
            f"{_ISSUE}: WhatsApp / non-mail bubbles must not grow Open original "
            "(gate the item with isMailRow)"
        )

    # 4) missing-ui — always on mail; disabled calm label; not hide / dialog / toast.
    if not _MENU_MISSING.search(surface):
        fail(
            f"{_ISSUE}: mail row with null raw_cas_hash still has Open original "
            '— disabled menuitem + t("openOriginalMissing") (not hide)'
        )
    missing_btn = _menu_button_for_t(surface, "openOriginalMissing")
    orig_btn = _menu_button_for_t(surface, "openOriginal")
    if not _DISABLED.search(missing_btn) and not _DISABLED.search(orig_btn):
        fail(
            f"{_ISSUE}: missing raw is a disabled menuitem "
            "(calm label; no invoke, no crash, no #73 reconstruct)"
        )
    if _HASH_IF.search(surface):
        for m in _HASH_IF.finditer(surface):
            chunk = surface[m.start() : m.start() + 700]
            if _MENU_ORIG.search(chunk) and not _MENU_MISSING.search(chunk):
                if "{:else}" not in chunk and "{:else if" not in chunk:
                    fail(
                        f"{_ISSUE}: do not hide Open original when raw_cas_hash "
                        "is null — item always on mail; missing is disabled copy"
                    )
    if re.search(r"showToast\s*\(", _around(lst + "\n" + menu, _MENU_MISSING, 80, 200)):
        fail(
            f"{_ISSUE}: missing raw is a disabled menu label, not a toast"
        )

    # 5) multi-select — hide Open original when #370 n > 1; Copy N stays.
    if not _N_HIDE.search(orig_win) and not _N_HIDE.search(
        _around(surface, _MENU_MISSING)
    ):
        fail(
            f"{_ISSUE}: hide Open original when #370 n > 1 "
            "(Copy N stays; do not batch-OS-open)"
        )
    if not re.search(r"""t\s*\(\s*["']copyN["']\s*\)""", menu_m or menu):
        fail(f'{_ISSUE}: keep t("copyN") when n > 1 (#370)')
    if not re.search(r"stopPropagation", rows_raw):
        fail(
            f"{_ISSUE}: keep CasAttach stopPropagation so attachment Open/Reveal "
            "do not become Copy N (#370)"
        )

    # 6) hash-on-row — nullable raw_cas_hash on TimelineRow JSON; SELECT; api.ts.
    row_struct = _rust_struct_body(people, "TimelineRow")
    if not re.search(r"\braw_cas_hash\b", row_struct):
        fail(
            f"{_ISSUE}: person_timeline TimelineRow JSON must expose nullable "
            "raw_cas_hash (not extra IPC by message_id)"
        )
    if not re.search(r"raw_cas_hash\s*:\s*Option\s*<\s*String\s*>", row_struct):
        fail(
            f"{_ISSUE}: TimelineRow.raw_cas_hash is Option<String> "
            "(JSON null or 64-hex)"
        )
    if re.search(
        r"skip_serializing_if[^\n]{0,80}\n\s*(?:pub\s+)?raw_cas_hash",
        row_struct,
    ):
        fail(
            f"{_ISSUE}: raw_cas_hash serializes as JSON null when missing "
            "(do not skip_serializing_if)"
        )
    if not re.search(r"\bm\.raw_cas_hash\b", timeline):
        fail(
            f"{_ISSUE}: person_timeline SELECT must read m.raw_cas_hash"
        )
    if not re.search(r"\braw_cas_hash\s*:", timeline):
        fail(
            f"{_ISSUE}: map_row must fill TimelineRow.raw_cas_hash from the SELECT"
        )
    api_row = _ts_type_body(api, "TimelineRow")
    if not re.search(r"\braw_cas_hash\s*\??\s*:", api_row):
        fail(
            f"{_ISSUE}: api.ts TimelineRow must include raw_cas_hash "
            "(string | null)"
        )
    hit_type = _ts_type_body(api, "SearchHit")
    if re.search(r"\braw_cas_hash\b", hit_type):
        fail(
            f"{_ISSUE}: SearchHit stays without raw_cas_hash "
            "(People timeline only — not Search preview)"
        )

    open_fn = _fn(lst, "openCopyMenu") or _fn(lst_raw, "openCopyMenu")
    if not re.search(r"\braw_cas_hash\b", open_fn):
        fail(
            f"{_ISSUE}: copyMenu must snapshot the row raw_cas_hash "
            "(webview sends that hash; do not invent one)"
        )
    if _HEX64.search(lst) or _HEX64.search(menu):
        fail(
            f"{_ISSUE}: frontend must not invent a CAS hash "
            "(hash only from the row JSON)"
        )
    if _LOOKUP_IPC.search(lst) or _LOOKUP_IPC.search(api):
        fail(
            f"{_ISSUE}: no extra IPC lookup by message_id "
            "(hash is already on the TimelineRow)"
        )

    # 7) eml-ext — dedicated hash-only sibling; force .eml; do not teach sniff.
    sniff = _rust_function_body(cas_rs or rust, "sniff_mime")
    safe = _rust_function_body(cas_rs or rust, "mime_safe_ext")
    if _SNIFF_RFC.search(sniff):
        fail(
            f"{_ISSUE}: do not teach sniff_mime message/rfc822 "
            "(#317 attachment Open stays the sniff list)"
        )
    if re.search(r"""["']eml["']""", safe):
        fail(
            f"{_ISSUE}: do not add eml to mime_safe_ext "
            "(force .eml on the sibling only)"
        )
    open_cas_sig = _rust_fn_signature(cas_rs or rust, "open_cas")
    open_cas_own = _rust_function_body(cas_rs or rust, "open_cas")
    if re.search(r"\bext\b", open_cas_sig):
        fail(
            f"{_ISSUE}: do not add ext to open_cas "
            "(#317 stays hash-only sniff; this ticket is a sibling)"
        )
    if not re.search(r"\bsniff_mime\s*\(", open_cas_own):
        fail(
            f"{_ISSUE}: keep open_cas sniff_mime + typed temp for attachments (#317)"
        )
    if not _SAFE_EXT.search(open_cas_own) and not _SAFE_EXT.search(safe):
        fail(
            f"{_ISSUE}: keep #317 safe ext list "
            "(jpg/png/gif/webp/heic/mp4/mov/pdf/mp3/ogg/m4a/wav/webm/bin)"
        )
    if _OPEN_CAS_INVOKE.search(lst):
        fail(
            f"{_ISSUE}: People Open original must not call api.openCas / open_cas "
            "(dedicated hash-only sibling that always writes .eml)"
        )

    cmd = _find_sibling_cmd(rust, web)
    if not cmd or cmd in _BANNED_CMDS:
        fail(
            f"{_ISSUE}: dedicated hash-only sibling of open_cas required "
            "(always copy interlace-<hash>.eml — not open_cas sniff → .bin)"
        )
    if not re.search(
        r"generate_handler!\s*\[[^\]]*\b" + re.escape(cmd) + r"\b",
        rust,
        re.S,
    ) and not re.search(
        r"generate_handler!\s*\[[^\]]*\b" + re.escape(cmd) + r"\b",
        main_raw,
        re.S,
    ):
        fail(f"{_ISSUE}: register {cmd} in generate_handler")
    camel = _snake_to_camel(cmd)
    sig = _rust_fn_signature(rust, cmd)
    own = _rust_function_body(rust, cmd)
    body = _rust_body_with_callees(rust, cmd)
    if not re.search(r"\bhash\b", sig, re.I):
        fail(f"{_ISSUE}: {cmd} must take a hash (not a path, URL, ext, or message_id)")
    if re.search(r"\b(?:path|url|file|href|uri|ext|message_id)\s*:", sig, re.I):
        fail(
            f"{_ISSUE}: {cmd} is hash only from the webview — "
            "do not take path / url / file / ext / message_id"
        )
    if "cas_blob_path" not in body:
        fail(
            f"{_ISSUE}: {cmd} must resolve cas/ab/cd/<hash> via cas_blob_path "
            "(same resolve as #317)"
        )
    if not re.search(r"\bcanonicalize\s*\(", body):
        fail(f"{_ISSUE}: {cmd} must canonicalize the CAS path")
    if not _outside_cas(body):
        fail(f"{_ISSUE}: {cmd} must refuse anything outside cas/")
    if not re.search(r"\barchive_root\b", body):
        fail(f"{_ISSUE}: {cmd} must read archive_root from app state")
    if not re.search(r"\bparse_hash\b|len\(\)\s*!=\s*64|ascii_hexdigit", body):
        if not re.search(r"cas_blob_path", body):
            fail(f"{_ISSUE}: {cmd} must parse a 64-hex hash")
    if not _FS_COPY.search(own) and not _FS_COPY.search(body):
        fail(
            f"{_ISSUE}: {cmd} must fs::copy the blob to temp_dir as "
            "interlace-<hash>.eml"
        )
    if not _TEMP_DIR.search(own) and not _TEMP_DIR.search(body):
        fail(
            f"{_ISSUE}: {cmd} must copy into std::env::temp_dir() "
            "(interlace-<hash>.eml — not the cas/ blob)"
        )
    if not _INTERLACE_PREFIX.search(own) and not _INTERLACE_PREFIX.search(body):
        fail(
            f"{_ISSUE}: temp name must be interlace-<hash>.eml"
        )
    if not _EML_LIT.search(own) and not _EML_LIT.search(body):
        fail(
            f"{_ISSUE}: {cmd} always writes .eml "
            "(do not sniff; Mail/Preview must see an .eml)"
        )
    if _CAS_MUTATE.search(own) or _CAS_MUTATE.search(body):
        fail(
            f"{_ISSUE}: do not rename or set_extension the CAS blob "
            "(canon stays hash-named; copy to temp)"
        )
    if "/usr/bin/open" not in body:
        fail(
            f"{_ISSUE}: {cmd} must OS-open the temp with /usr/bin/open "
            "(default app, not Finder)"
        )
    launch = own if "/usr/bin/open" in own else body
    if re.search(r"""["']-R["']""", launch):
        fail(
            f"{_ISSUE}: {cmd} must run /usr/bin/open without -R "
            "(Reveal keeps -R)"
        )
    if not re.search(r"Command::new|std::process::Command", own or body):
        fail(
            f"{_ISSUE}: {cmd} must use std::process::Command "
            "(/usr/bin/open without -R)"
        )
    for m in re.finditer(r"Command::new\s*\(", launch):
        arg = _rust_call_arg(launch, m.end() - 1)
        if "/usr/bin/open" not in arg:
            fail(
                f"{_ISSUE}: no shell of arbitrary commands — "
                "Command::new must be /usr/bin/open on the temp .eml"
            )
    if _opens_only_cas_canon(launch):
        fail(
            f"{_ISSUE}: /usr/bin/open without -R must run on the temp "
            "interlace-<hash>.eml, not only the CAS canon blob"
        )
    if _HTTP.search(own):
        fail(f"{_ISSUE}: {cmd} must not open http(s) — local CAS file only")
    if _ARBITRARY_SHELL.search(own) or _ARBITRARY_SHELL.search(body):
        fail(
            f"{_ISSUE}: no shell of arbitrary commands — "
            "only /usr/bin/open on the temp .eml"
        )
    if _RECONSTRUCT.search(own) or _RECONSTRUCT.search(lst):
        fail(
            f"{_ISSUE}: do not reconstruct rfc822 from body_text / subject "
            "(#73 is out of scope; open the stored CAS blob)"
        )
    if re.search(r"\bbody_text\b|\bsubject\b", own) and not _FS_COPY.search(own):
        fail(
            f"{_ISSUE}: do not reconstruct rfc822 from body_text "
            "(copy the stored CAS blob)"
        )

    invoke_rx = re.compile(
        r"invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']" + re.escape(cmd) + r"[\"']"
    )
    camel_rx = re.compile(rf"\b(?:api\.)?{re.escape(camel)}\s*\(")
    if not invoke_rx.search(web) and not camel_rx.search(web):
        fail(
            f"{_ISSUE}: frontend must call api.{camel}(hash) / "
            f'invoke("{cmd}", {{ hash }}) — hash only'
        )
    payloads = _invoke_payloads(web, invoke_rx)
    if not payloads:
        call_win = _windows_around(web, invoke_rx, before=40, after=160)
        if not call_win:
            call_win = _windows_around(web, camel_rx, before=40, after=160)
        if not re.search(r"\bhash\b", call_win, re.I):
            fail(
                f"{_ISSUE}: frontend must send only the hash to {cmd} "
                "(do not pass a path, URL, ext, or message_id)"
            )
        if _payload_has_path_or_url(call_win):
            fail(
                f"{_ISSUE}: frontend must send only the hash to {cmd} "
                "(do not pass a path or URL from the webview)"
            )
        if re.search(r"\b(?:ext|message_id|messageId)\b", call_win):
            fail(
                f"{_ISSUE}: frontend must send only the hash to {cmd} "
                "(no ext / message_id from the webview)"
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
        if re.search(r"\b(?:ext|message_id|messageId|path|url|file)\b", payload):
            fail(
                f"{_ISSUE}: frontend must send only the hash to {cmd} "
                "(no path / url / ext / message_id)"
            )
    if re.search(
        rf"openCas\s*:\s*\([^)]*\bext\b"
        rf"""|invoke\s*(?:<[^>]*>)?\s*\(\s*["']open_cas["']\s*,\s*\{{[^}}]*\bext\b""",
        api,
    ):
        fail(f"{_ISSUE}: api.openCas stays hash-only — do not add ext")

    # 8) confirm — owned ConfirmDialog, mail-specific, only when hash is set.
    if not confirm_path.is_file():
        fail(f"{_ISSUE}: ConfirmDialog.svelte required (host it on the People bubble path)")
    if "ConfirmDialog" not in lst_raw:
        fail(
            f"{_ISSUE}: host ConfirmDialog in TimelineList "
            "(before OS-open when hash is set — do not plumb App ask)"
        )
    if not re.search(r"import\s+ConfirmDialog\b", lst_raw):
        fail(
            f"{_ISSUE}: import ConfirmDialog in TimelineList "
            "(mail-specific copy, not App ask)"
        )
    if re.search(r"\bask\s*\(", lst):
        fail(
            f"{_ISSUE}: host ConfirmDialog in TimelineList "
            "(do not plumb App ask)"
        )
    confirm = _confirm_block(lst_raw)
    if not confirm.strip():
        fail(
            f"{_ISSUE}: TimelineList must mount <ConfirmDialog> "
            "(mail-specific title; not #317 \"Open this file?\")"
        )
    if _ATTACH_CONFIRM_TITLE in lst_raw or _ATTACH_CONFIRM_TITLE in confirm:
        fail(
            f"{_ISSUE}: confirm is mail-specific copy — "
            f'do not reuse #317 "{_ATTACH_CONFIRM_TITLE}"'
        )
    if _ATTACH_DESC in lst_raw or _ATTACH_DESC in confirm:
        fail(
            f"{_ISSUE}: confirm description is mail-specific — "
            "do not reuse #317 \"Open this stored file with the default app.\""
        )
    if not (
        re.search(r"""t\s*\(\s*["']openOriginal""", confirm)
        or re.search(r"Open original", confirm, re.I)
    ):
        fail(
            f"{_ISSUE}: ConfirmDialog title must be mail-specific "
            "(Open original — not t(\"open\") / \"Open this file?\")"
        )
    if _DESC_BIND_LEAK.search(confirm):
        fail(
            f"{_ISSUE}: confirm description must be a generic local sentence "
            "— never a filesystem path, hash, or URL"
        )
    en = _chrome_pack_entries(_text(en_path))
    tr = _chrome_pack_entries(_text(tr_path))
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
    if _handler_invokes(lst, orig_click, cmd, camel):
        fail(
            f"{_ISSUE}: Open original menuitem must open ConfirmDialog first "
            f"— do not invoke {cmd} on the click (Cancel does nothing)"
        )
    onconfirm = _onconfirm_src(lst, confirm)
    if not _handler_invokes(lst, onconfirm, cmd, camel):
        fail(
            f"{_ISSUE}: ConfirmDialog onconfirm must invoke {cmd} "
            "(Cancel dismisses and does not invoke)"
        )
    missing_click = _menu_onclick_for_t(surface, "openOriginalMissing")
    if missing_click and (
        _handler_invokes(lst, missing_click, cmd, camel)
        or re.search(r"ConfirmDialog|confirmOpen|fileOpenConfirm", missing_click)
    ):
        fail(
            f"{_ISSUE}: missing raw does not confirm-to-do-nothing "
            "(disabled menu copy already explained it)"
        )
    if not re.search(r">\s*Cancel\s*<", confirm_src):
        fail(f"{_ISSUE}: ConfirmDialog Cancel must still dismiss")

    # 9) clamp the bubble copy menu (#317 pattern; do not rewrite data-reveal-menu).
    clamp = _clamp_blob(lst, menu)
    if not (_VIEW.search(clamp) or _BOX.search(clamp)):
        fail(
            f"{_ISSUE}: clamp data-copy-menu inside the window "
            "(innerWidth / innerHeight and/or getBoundingClientRect — "
            "#317 pattern on this menu, not a rewrite of data-reveal-menu)"
        )
    if not _CLAMP_ADJ.search(clamp):
        fail(
            f"{_ISSUE}: clamp data-copy-menu inside the window "
            "(adjust left/top from innerWidth / getBoundingClientRect)"
        )
    if not re.search(r"\bclampRevealMenu\b", cas_raw):
        fail(
            f"{_ISSUE}: keep CasAttach clampRevealMenu (#317) — "
            "clamp the bubble menu separately"
        )

    # 10) toast — chrome-only Could not open.
    open_handler = ""
    for name in (
        orig_prop,
        camel,
        "confirmOpenOriginal",
        "confirmOpen",
        "openOriginal",
        "doOpenOriginal",
    ):
        if not name:
            continue
        blob = _fn(lst, name)
        if blob:
            open_handler += blob + "\n"
    open_handler += onconfirm
    if not _TOAST_OPEN.search(lst_raw) and not _uses_phrase(lst_raw, en, _TOAST_COPY):
        fail(
            f"{_ISSUE}: Open original catch must toast \"{_TOAST_COPY}\" "
            "(chrome-only — no path / hash / body)"
        )
    if _TOAST_LEAK.search(open_handler):
        fail(
            f"{_ISSUE}: fail toast is chrome-only "
            f"(\"{_TOAST_COPY}\" — no path / hash / error body)"
        )

    # 11) keep #317 CasAttach Open / Reveal / sniff / SearchHits reuse.
    if not re.search(r"\bdata-reveal-menu\b", cas_m or cas):
        fail(f"{_ISSUE}: keep CasAttach data-reveal-menu (#317)")
    if not _T_OPEN.search(cas_m or cas):
        fail(f'{_ISSUE}: keep CasAttach t("open") (#317 attachment Open)')
    if not re.search(r"""t\s*\(\s*["']revealInFinder["']\s*\)""", cas_m or cas):
        fail(f"{_ISSUE}: keep CasAttach Reveal in Finder (#317 / #135)")
    if _ATTACH_CONFIRM_TITLE not in cas_raw:
        fail(
            f'{_ISSUE}: keep CasAttach confirm "{_ATTACH_CONFIRM_TITLE}" (#317)'
        )
    if _MENU_ORIG.search(cas_m or cas) or _MENU_MISSING.search(cas_m or cas):
        fail(
            f"{_ISSUE}: Open original is not a CasAttach menuitem "
            "(attachment hash ≠ messages.raw_cas_hash)"
        )
    if not re.search(r"""["']-R["']""", _rust_function_body(rust, "reveal_cas")):
        fail(f"{_ISSUE}: keep reveal_cas /usr/bin/open -R (#135 / #317)")

    # 12) People only — Search preview does not grow a bubble Open original.
    if _MENU_ORIG.search(hits) or _MENU_MISSING.search(hits):
        fail(
            f"{_ISSUE}: Search preview / hit menu does not grow Open original "
            "(People timeline bubble only)"
        )
    if "TimelineCopyMenu" in hits_raw:
        fail(
            f"{_ISSUE}: SearchHits must not mount TimelineCopyMenu "
            "(#371 preview is not a bubble timeline)"
        )
    if "CasAttach" not in hits_raw:
        fail(
            f"{_ISSUE}: SearchHits must keep mounting CasAttach "
            "(attachment Open/Reveal only — #317)"
        )
    if re.search(r"\braw_cas_hash\b", hits):
        fail(
            f"{_ISSUE}: SearchHits must not read raw_cas_hash "
            "(People timeline only)"
        )
    if invoke_rx.search(hits) or camel_rx.search(hits):
        fail(
            f"{_ISSUE}: SearchHits must not invoke {cmd} "
            "(People timeline only)"
        )

    # 13) no Import checkbox; --preserve-raw stays default off.
    if re.search(r"preserve.?raw|preserveRaw|preserve_raw", import_raw, re.I):
        fail(
            f"{_ISSUE}: no Import checkbox for --preserve-raw "
            "(CLI flag stays default off)"
        )
    if re.search(r"preserve_raw\s*:\s*true", import_cmd):
        fail(
            f"{_ISSUE}: Tauri import must not set preserve_raw: true "
            "(ImportOpts::default() stays off)"
        )
    if "ImportOpts::default()" not in import_cmd and "..ImportOpts::default()" not in import_cmd:
        fail(
            f"{_ISSUE}: keep Tauri import on ImportOpts::default() "
            "(preserve_raw stays off)"
        )
    if not re.search(r"preserve_raw\s*:\s*false", model):
        fail(
            f"{_ISSUE}: ImportOpts.preserve_raw default stays false (#79)"
        )

    # 14) locale — same ChromeKey on en.ts + tr.ts; tr is not an English copy.
    extra_en = set(en) - set(tr)
    extra_tr = set(tr) - set(en)
    if extra_en or extra_tr:
        bits: list[str] = []
        if extra_en:
            bits.append("in en only: " + ", ".join(sorted(extra_en)))
        if extra_tr:
            bits.append("in tr only: " + ", ".join(sorted(extra_tr)))
        fail(f"{_ISSUE}: same ChromeKey on both en and tr packs — " + "; ".join(bits))
    for key in ("openOriginal", "openOriginalMissing"):
        if key not in en or key not in tr:
            fail(
                f"{_ISSUE}: {key} ChromeKey on both en.ts and tr.ts (#278)"
            )
    if not re.search(r"Open original", en.get("openOriginal") or "", re.I):
        fail(f'{_ISSUE}: en openOriginal must be "Open original"')
    if not re.search(
        r"not stored|re-import|preserve",
        en.get("openOriginalMissing") or "",
        re.I,
    ):
        fail(
            f"{_ISSUE}: en openOriginalMissing must say raw was not stored "
            "(re-import with the flag)"
        )
    if (en.get("openOriginal") or "").strip() == (tr.get("openOriginal") or "").strip():
        fail(f"{_ISSUE}: tr openOriginal is not an English copy")
    if (en.get("openOriginalMissing") or "").strip() == (
        tr.get("openOriginalMissing") or ""
    ).strip():
        fail(f"{_ISSUE}: tr openOriginalMissing is not an English copy")
    for pack in (en, tr):
        for _key, val in pack.items():
            if re.search(r"\bAda\b|\bBerk\b", val):
                fail(
                    f"{_ISSUE}: locale packs stay chrome only — no placeholder "
                    "names in t() values"
                )
    if re.search(r"lucide", menu_raw, re.I):
        fail(
            f"{_ISSUE}: no Lucide on the bubble copy menu "
            "(match Copy / Search — no icon)"
        )
    if re.search(r"animate-bounce|@keyframes", menu_raw):
        fail(f"{_ISSUE}: reduced motion — no bounce on the copy menu")

    # 15) no HTTP / plugin-shell / network.server / path from the webview.
    if re.search(
        r"\bopen_url\s*\(|invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']open_url[\"']",
        lst,
    ) or re.search(r"\bopenUrl\s*\(", lst):
        fail(
            f"{_ISSUE}: do not reuse open_url for a local .eml "
            "(#272 stays http(s) only)"
        )
    if _PLUGIN_SHELL.search(toml) or _PLUGIN_SHELL.search(pkg):
        fail(
            f"{_ISSUE}: do not add tauri-plugin-shell / tauri-plugin-opener "
            "(std::process file-only open)"
        )
    if _PLUGIN_SHELL.search(own) or _PLUGIN_SHELL.search(lst):
        fail(
            f"{_ISSUE}: do not add tauri-plugin-shell / tauri-plugin-opener"
        )
    if _SHELL_CAP.search(caps):
        fail(
            f"{_ISSUE}: capabilities must not add shell:allow-execute / "
            "shell:allow-open / opener"
        )
    if _HTTP_CLIENT.search(toml) or _HTTP_CLIENT.search(own):
        fail(f"{_ISSUE}: no HTTP client / tauri-plugin-http")
    if "network.server" in ent:
        fail(f"{_ISSUE}: entitlements must omit network.server")
    if CSP not in conf:
        fail(f"{_ISSUE}: do not soften tauri CSP")
    if _FILE_CSP.search(conf):
        fail(f"{_ISSUE}: do not add file: to CSP")

    # 16) D24 — docs/user/app.md.
    if not _DOCS_OPEN_ORIG.search(docs_raw):
        fail(
            f"{_ISSUE}: docs/user/app.md must describe mail bubble Open original"
        )
    if not _DOCS_EML.search(docs_raw):
        fail(
            f"{_ISSUE}: docs must say preserve-raw mail opens an .eml "
            "(Mail / Preview; after confirm)"
        )
    if not _DOCS_MISSING.search(docs_raw):
        fail(
            f"{_ISSUE}: docs must say missing raw is calm copy "
            "(not stored / re-import with the flag)"
        )
    if not _DOCS_WA.search(docs_raw):
        fail(
            f"{_ISSUE}: docs must say a WhatsApp bubble has no Open original item"
        )
    if not _DOCS_SEARCH_THIS.search(docs_raw):
        fail(f"{_ISSUE}: keep docs for Search this conversation (#372)")
    if not _DOCS_ATTACH_OPEN.search(docs_raw):
        fail(f"{_ISSUE}: keep docs for attachment Open (#317)")
    if not _DOCS_NO_HTTP.search(docs_raw):
        fail(f"{_ISSUE}: docs must still say no http(s)")
    if not _DOCS_DEFAULT_OFF.search(docs_raw):
        fail(
            f"{_ISSUE}: docs must keep --preserve-raw default off "
            "(no Import checkbox)"
        )
    if re.search(r"Share sheet|AirDrop", _around(docs_raw, _DOCS_OPEN_ORIG, 200, 200)):
        fail(f"{_ISSUE}: still no Share / AirDrop")
