"""#321 — Doctor GC confirm shows reclaimable bytes.

Confirmed mix: GC CAS click → read-only estimate → existing owned
ConfirmDialog mentions the figure → today's doctorRun({ gcCas: true }).
Core helper estimate_unreferenced_cas_bytes next to gc_cas (same
walk_blobs + two-table COUNT; sum fs::metadata.len(); no delete).
New argument-free IPC (never fn backup; not a doctorRun dry-run).
Archive via with_arch / app state only. Estimate on GC click only,
before the dialog. busy while estimating; do not flip scanning.
New en+tr ChromeKey + Review-style .replace("{n}", …). Ok(0) is
still "0 B". Estimate Err → today's t("gcUnusedCasDesc"). Human
decimal SI in TS (1000). D24 doctor.md + app.md. Keep Integrity /
Rebuild / #136 / #205 / #221 / #274 / #320 / CAS3 / CLI --gc-cas.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.copy_archive import (
    _HTTP_CLIENT,
    _PLUGIN_SHELL,
    _REAL_HOME,
    _SHELL_CAP,
    _fn,
    _onclick_before,
)
from tauri_gate.import_reveal_more import (
    _DOCTOR_ISSUE_API,
    _DOCTOR_RUN_API,
    _GC_ON_OPEN,
    _QUICK_DOCTOR,
    _REVEAL_ARCHIVE_BACKUP_FN,
    _REVEAL_ARCHIVE_ENCRYPT,
    _core_rust_blob,
    _full_doctor_scan_body,
)
from tauri_gate.locale_more import _chrome_pack_entries
from tauri_gate.scan import (
    CSP,
    _ARBITRARY_SHELL,
    _FETCH_CALL,
    _LINKIFY_FETCH,
    _expand_fn_calls,
    _rust_fn_signature,
    _rust_function_body,
    _tauri_rust_blob,
    _ts_fn_body,
    _web_logic,
    _without_comments,
)
from tauri_gate.status import (
    _DOCTOR_HEAVY,
    _resolve_handler_blob,
    _retry_click_expr,
)
from tauri_gate.status_toasts_chrome import (
    _claim_without_negation,
    _invoke_payloads,
    _payload_has_path_or_url,
)

_ISSUE = "#321"
_CORE = "estimate_unreferenced_cas_bytes"
_TITLE_KEY = "gcUnusedCas"
_DESC_KEY = "gcUnusedCasDesc"
_LABEL_KEY = "deleteUnused"
_DESC_EN = (
    "Deletes blobs not referenced by attachments or contact photos. "
    "Cannot undo. Close other writers first."
)
_DESC_TR = (
    "Ekler veya kişi fotoğrafları tarafından başvurulmayan blob'ları siler. "
    "Geri alınamaz. Önce diğer yazıcıları kapatın."
)
_T_TITLE = re.compile(r"""\bt\s*\(\s*["']gcUnusedCas["']\s*\)""")
_T_DESC = re.compile(r"""\bt\s*\(\s*["']gcUnusedCasDesc["']\s*\)""")
_T_LABEL = re.compile(r"""\bt\s*\(\s*["']deleteUnused["']\s*\)""")
_T_DESC_REPLACE = re.compile(
    r"""t\s*\(\s*["']gcUnusedCasDesc["']\s*\)\s*\.replace"""
)
_T_CALL = re.compile(r"""\bt\s*\(\s*["']([A-Za-z_][\w]*)["']\s*\)""")
_REPLACE_N = re.compile(r"""\.replace\s*\(\s*["']\{n\}["']""")
_REPLACE_N_RAW = re.compile(
    r"""\.replace\s*\(\s*["']\{n\}["']\s*,\s*String\s*\("""
)
_T_SIZED = re.compile(
    r"""t\s*\(\s*["']((?!gcUnusedCasDesc)[A-Za-z_][\w]*)["']\s*\)"""
    r"""\s*\.replace\s*\(\s*["']\{n\}["']"""
)
_ASK = re.compile(r"\bask\s*\(|confirmOpen\s*=\s*true")
_ESTIMATE_INVOKE = re.compile(
    r"(?:api\.)?[A-Za-z_]*estimate[A-Za-z_]*(?:Cas|Gc|Bytes)[A-Za-z_]*\s*\("
    r"|invoke\s*(?:<[^>]*>)?\s*\(\s*[\"'][A-Za-z_]*estimate"
    r"[A-Za-z_]*(?:cas|gc|bytes)[A-Za-z_]*[\"']",
    re.I,
)
_ESTIMATE_FN = re.compile(
    r"\bfn\s+(?:(?:pub(?:\s*\([^)]*\))?\s+)?(?:async\s+)?)?"
    r"(?:doctor_)?estimate_unreferenced_cas_bytes(?:_cmd)?\b"
)
_ESTIMATE_NAME = re.compile(
    r"\b(?:doctor_)?estimate_unreferenced_cas_bytes(?:_cmd)?\b"
    r"|\b[A-Za-z_]*estimate[A-Za-z_]*(?:cas|gc|bytes)[A-Za-z_]*\b",
    re.I,
)
_CLIENT_PARAM = re.compile(
    r"\b(?:path|url|file|href|uri|dest|source|root)\s*:",
    re.I,
)
_OPEN_SECOND = re.compile(r"\bopen_archive\s*\(|LockMode\s*::\s*Exclusive")
_DROP_FLOCK = re.compile(
    r"("
    r"\bclose_archive\s*\("
    r"|archive\s*=\s*None"
    r"|\.archive\b[^=;\n]{0,80}=\s*None"
    r"|\barchive\b[^\n]{0,40}\.take\s*\("
    r")"
)
_REMOVE_FILE = re.compile(
    r"\b(?:(?:std\s*::\s*)?fs\s*::\s*)?(?:remove_file|unlink)\s*(?:!)?\s*\("
)
_CAS_WRITE = re.compile(
    r"DELETE\s+FROM\s+cas_blobs|UPDATE\s+cas_blobs",
    re.I,
)
_SUM_SIZE = re.compile(
    r"SUM\s*\(\s*(?:cas_blobs\.)?size\s*\)"
    r"|\.sum\s*\([^\)]*size",
    re.I,
)
_REFCOUNT0 = re.compile(r"\brefcount\b")
_COUNT_SQL = re.compile(r"\bCOUNT\s*\(", re.I)
_META = re.compile(r"(?:fs\s*::\s*)?metadata\s*\(|\.metadata\s*\(")
_META_OK = re.compile(
    r"(?:fs\s*::\s*)?metadata\s*\([^)]*\)\s*\?"
    r"|\.metadata\s*\(\s*\)\s*\?"
)
_META_SKIP = re.compile(
    r"("
    r"if\s+let\s+Ok\s*\("
    r"|\.ok\s*\(\s*\)"
    r"|unwrap_or\s*\(\s*0"
    r"|let\s+_\s*=\s*(?:fs\s*::\s*)?metadata"
    r")"
)
_ZERO_FALLBACK = re.compile(
    r"("
    r"(?:===|==)\s*0"
    r"|\b(?:n|bytes|size|total)\s*===\s*0n?"
    r"|\b(?:n|bytes|size|total)\s*==\s*0\b"
    r")",
)
_DRY_RUN = re.compile(r"\bdry_run\b|\bdryRun\b")
_WINDOW_CONFIRM = re.compile(r"\bwindow\s*\.\s*confirm\s*\(")
_PROGRESS = re.compile(
    r"<progress\b|role\s*=\s*[\"']progressbar|progress-bar|\bpercent\b",
    re.I,
)
_ESTIMATING_CHROME = re.compile(
    r">[^<{]*[Ee]stimat|t\s*\(\s*[\"']estimating",
)
_SI_1024 = re.compile(r"\b1024\b")
_SI_1000 = re.compile(r"\b1000\b")
_SI_IEC = re.compile(r"\b(?:KiB|MiB|GiB|TiB)\b")
_SI_UNIT = re.compile(r"""["'](?:B|KB|MB|GB)["']""")
_FRACTION = re.compile(r"toFixed\s*\(\s*1\s*\)|1\s*fraction|one fraction")
_ZERO_B = re.compile(r"""["']0 B["']|["']B["']""")
_FILE_COUNT_COPY = re.compile(
    r"("
    r"\bfiles?\s+(?:removed|deleted|unused)"
    r"|\{n\}\s*files?"
    r"|file count"
    r")",
    re.I,
)
_T_FN = re.compile(
    r"export\s+function\s+t\s*\(\s*key\s*:\s*ChromeKey"
    r"(?:\s*\)|\s*,)"
)
_DOCS_BYTES = re.compile(
    r"("
    r"(?:in-app|in app|Doctor).{0,80}GC.{0,80}"
    r"(?:confirm|dialog).{0,80}"
    r"(?:reclaimable |unused )?(?:bytes?|size)"
    r"|GC.{0,60}confirm.{0,80}(?:reclaimable |unused )?(?:bytes?|size)"
    r"|confirm.{0,80}(?:reclaimable |unused )?(?:bytes?|size)"
    r"|(?:reclaimable |unused )bytes?.{0,80}(?:confirm|dialog|GC)"
    r")",
    re.I | re.S,
)
_DOCS_ENCRYPT_OK = re.compile(
    r"not encrypted|FileVault",
    re.I,
)
_PARTIAL_TAG = re.compile(r"data-partial")
_RETRY = re.compile(r">\s*Retry\s*<")
_GC_CAS_FLAG = re.compile(r"gcCas\s*:\s*true")
_INTEGRITY_ASK = re.compile(
    r"""t\s*\(\s*["']runIntegrityCheck["']\s*\)"""
    r""".{0,200}t\s*\(\s*["']runIntegrityCheckDesc["']\s*\)"""
    r""".{0,200}t\s*\(\s*["']integrityCheck["']\s*\)""",
    re.S,
)
_REBUILD_ASK = re.compile(
    r"""t\s*\(\s*["']rebuildSearchIndex["']\s*\)"""
    r""".{0,200}t\s*\(\s*["']rebuildSearchIndexDesc["']\s*\)"""
    r""".{0,200}t\s*\(\s*["']rebuild["']\s*\)""",
    re.S,
)
_INTEGRITY_FLAGS = re.compile(
    r"integrity\s*:\s*true.{0,80}rebuildFts\s*:\s*false.{0,80}gcCas\s*:\s*false",
    re.S,
)
_REBUILD_FLAGS = re.compile(
    r"integrity\s*:\s*false.{0,80}rebuildFts\s*:\s*true.{0,80}gcCas\s*:\s*false",
    re.S,
)
_DISABLED_BUSY = re.compile(
    r"disabled\s*=\s*\{[^}]*\bbusy\b[^}]*\bscanning\b"
    r"|disabled\s*=\s*\{[^}]*\bscanning\b[^}]*\bbusy\b"
)
_BUSY_TRUE = re.compile(r"\bbusy\s*=\s*true\b")
_SCAN_TRUE = re.compile(r"\bscanning\s*=\s*true\b")
_HANDLER_NAMES = (
    "gcCas",
    "runGc",
    "askGc",
    "onGcCas",
    "handleGcCas",
    "gcUnused",
    "estimateThenAsk",
    "askGcCas",
    "runGcCas",
    "gcUnusedCas",
)


def _text(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


def _first(src: str, rx: re.Pattern[str]) -> int:
    m = rx.search(src)
    return m.start() if m else -1


def _button_click(src: str, label: str) -> str:
    m = re.search(rf">\s*{re.escape(label)}\s*<", src)
    if not m:
        return ""
    return _onclick_before(src, m.start())


def _named_and_click(doctor: str, click: str, extra: tuple[str, ...] = ()) -> str:
    raw = click or ""
    ident = raw.strip()
    if re.fullmatch(r"[A-Za-z_]\w*", ident):
        raw = raw + "\n" + _fn(doctor, ident)
    for name in extra:
        raw += "\n" + _fn(doctor, name)
    for name in re.findall(r"\b([A-Za-z_]\w*)\s*\(", click or ""):
        if name == "ask":
            continue
        raw += "\n" + _fn(doctor, name)
    return raw


def _gc_click_raw(doctor: str) -> str:
    click = _button_click(doctor, "GC CAS")
    if not click.strip():
        m = _T_TITLE.search(doctor)
        if m:
            click = _onclick_before(doctor, m.start())
    return _named_and_click(doctor, click, _HANDLER_NAMES)


def _integrity_click_raw(doctor: str) -> str:
    return _named_and_click(doctor, _button_click(doctor, "Integrity"))


def _rebuild_click_raw(doctor: str) -> str:
    return _named_and_click(doctor, _button_click(doctor, "Rebuild FTS"))


def _action_button_tag(doctor: str, label: str) -> str:
    m = re.search(rf">\s*{re.escape(label)}\s*<", doctor)
    if not m:
        return ""
    start = doctor.rfind("<Button", 0, m.start())
    if start < 0:
        return ""
    return doctor[start : m.start()]


def _handler_names(rust: str) -> list[str]:
    m = re.search(r"generate_handler!\s*\[(.*?)\]", rust, re.S)
    if not m:
        return []
    return re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", m.group(1))


def _estimate_cmd_name(rust: str) -> str:
    names = _handler_names(rust)
    for name in names:
        if re.search(r"estimate", name, re.I) and re.search(
            r"cas|gc|bytes", name, re.I
        ):
            return name
        body = _rust_function_body(rust, name)
        if body and _CORE in body:
            return name
    return ""


def _api_estimate_name(api: str) -> str:
    m = re.search(
        r"\b([A-Za-z_]*estimate[A-Za-z_]*(?:Cas|Gc|Bytes)[A-Za-z_]*)\s*:",
        api,
        re.I,
    )
    if m:
        return m.group(1)
    m = re.search(
        r"\b([A-Za-z_]*estimate[A-Za-z_]*(?:Cas|Gc|Bytes)[A-Za-z_]*)\s*\(",
        api,
        re.I,
    )
    return m.group(1) if m else ""


def _format_fn(src: str, surface: str) -> str:
    m = re.search(
        r"""\.replace\s*\(\s*["']\{n\}["']\s*,\s*([A-Za-z_]\w*)\s*\(""",
        surface,
    )
    names: list[str] = []
    if m:
        names.append(m.group(1))
    names.extend(
        re.findall(
            r"\b(format\w+|human\w*Bytes|bytesSi|siBytes|formatSi)\b",
            surface,
        )
    )
    out = ""
    for name in names:
        if name in {"String", "t", "ask", "replace"}:
            continue
        out += "\n" + (_fn(src, name) or _ts_fn_body(src, name) or "")
    return out


def _zero_uses_unsized(raw: str) -> bool:
    for m in _ZERO_FALLBACK.finditer(raw):
        win = raw[max(0, m.start() - 80) : m.end() + 160]
        if _T_DESC.search(win) and not _REPLACE_N.search(win):
            return True
    return False


def assert_gc_confirm_bytes(crate: Path) -> None:
    """#321: GC click estimates unreferenced CAS bytes, then confirms."""
    doctor_path = crate / "web" / "lib" / "DoctorPane.svelte"
    if not doctor_path.is_file():
        fail(f"{_ISSUE}: DoctorPane.svelte required (GC CAS confirm bytes)")
    doctor = doctor_path.read_text()
    gc_raw = _gc_click_raw(doctor)
    gc_exp = _expand_fn_calls(doctor, gc_raw, 3) if gc_raw.strip() else ""
    gc_surf = gc_raw + "\n" + gc_exp

    # 1) gc-confirm-bytes — primary red today: static t("gcUnusedCasDesc").
    if not gc_raw.strip() and not _T_TITLE.search(doctor):
        fail(
            f"{_ISSUE}: Doctor GC CAS control required "
            f'(t("{_TITLE_KEY}") / GC CAS)'
        )
    est_at = _first(gc_raw, _ESTIMATE_INVOKE)
    ask_at = _first(gc_raw, _ASK)
    sized = bool(_REPLACE_N.search(gc_surf) and _T_SIZED.search(gc_surf))
    if est_at < 0 or (ask_at >= 0 and est_at > ask_at) or not sized:
        fail(
            f"{_ISSUE}: Doctor GC CAS click must estimate reclaimable "
            "bytes before ConfirmDialog opens (success description "
            f'mentions a sized figure — not only static t("{_DESC_KEY}"))'
        )

    if not _T_TITLE.search(gc_surf) and not _T_TITLE.search(doctor):
        fail(
            f'{_ISSUE}: GC confirm title must stay t("{_TITLE_KEY}")'
        )
    if not _T_LABEL.search(gc_surf) and not _T_LABEL.search(doctor):
        fail(
            f'{_ISSUE}: GC confirm label must stay t("{_LABEL_KEY}")'
        )
    if _WINDOW_CONFIRM.search(doctor):
        fail(f"{_ISSUE}: keep the existing ConfirmDialog (no window.confirm)")
    if len(re.findall(r"<ConfirmDialog\b", doctor)) != 1:
        fail(
            f"{_ISSUE}: no extra ConfirmDialog / new pane — reuse the "
            "owned Doctor ConfirmDialog"
        )
    if _PROGRESS.search(doctor) or _ESTIMATING_CHROME.search(
        _without_comments(doctor)
    ):
        fail(
            f"{_ISSUE}: no progress bar / percent / Estimating… chrome "
            "(silent busy while the estimate walks)"
        )

    api_path = crate / "web" / "lib" / "api.ts"
    api = _text(api_path)
    rust = _tauri_rust_blob(crate)
    rust_c = _without_comments(rust)
    web = _web_logic(crate)
    i18n = _text(crate / "web" / "lib" / "i18n.ts")
    confirm = _text(crate / "web" / "lib" / "ConfirmDialog.svelte")
    en_path = crate / "web" / "lib" / "locales" / "en.ts"
    tr_path = crate / "web" / "lib" / "locales" / "tr.ts"
    en = _chrome_pack_entries(_text(en_path)) if en_path.is_file() else {}
    tr = _chrome_pack_entries(_text(tr_path)) if tr_path.is_file() else {}
    toml = _text(crate / "Cargo.toml")
    pkg = _text(crate / "package.json")
    caps = _text(crate / "capabilities" / "default.json")
    ent = _text(crate / "Interlace.entitlements")
    conf = _text(crate / "tauri.conf.json")
    root = repo_root()
    core_cas = _text(root / "crates" / "interlace-core" / "src" / "cas.rs")
    core_src = _core_rust_blob(root)
    cli = _text(root / "crates" / "interlace-core" / "src" / "cli.rs")
    cas_test = _text(root / "crates" / "interlace-core" / "tests" / "cas.rs")
    doctor_md = _text(root / "docs" / "user" / "doctor.md")
    app_md = _text(root / "docs" / "user" / "app.md")

    # 2) estimate-cmd — new argument-free IPC; never fn backup; not dry-run.
    if _REVEAL_ARCHIVE_BACKUP_FN.search(rust_c):
        fail(
            f"{_ISSUE}: estimate command is never fn backup / backup_zip / "
            "icloud_backup"
        )
    cmd = _estimate_cmd_name(rust)
    if not cmd or not _ESTIMATE_FN.search(rust) and _CORE not in rust:
        fail(
            f"{_ISSUE}: new argument-free IPC command required "
            f"(calls {_CORE}; never fn backup; not a doctorRun dry-run flag)"
        )
    if cmd not in _handler_names(rust):
        fail(f"{_ISSUE}: register {cmd} in generate_handler")
    run_sig = _rust_fn_signature(rust, "doctor_run_cmd")
    if _DRY_RUN.search(run_sig) or re.search(r"\bestimate\b", run_sig, re.I):
        fail(
            f"{_ISSUE}: do not add a dry-run / estimate flag on doctorRun "
            f"— new command (like {_CORE})"
        )
    if re.search(r"dryRun|estimate\s*:", api):
        fail(
            f"{_ISSUE}: api.doctorRun must stay "
            "{ integrity, rebuildFts, gcCas } — estimate is its own command"
        )
    api_name = _api_estimate_name(api)
    if not api_name and not _ESTIMATE_INVOKE.search(api):
        fail(
            f"{_ISSUE}: frontend api wrapper required "
            f'(invoke("{cmd}") — no path args)'
        )
    if not _ESTIMATE_INVOKE.search(gc_raw):
        fail(
            f"{_ISSUE}: Doctor GC click must invoke the estimate command "
            "before ask()"
        )

    # 3) estimate-no-client-path / estimate-archive-state.
    sig = _rust_fn_signature(rust, cmd)
    own = _rust_function_body(rust, cmd)
    if not own.strip():
        fail(
            f"{_ISSUE}: {cmd} must call {_CORE} via with_arch "
            "(open Archive from app state)"
        )
    if _CLIENT_PARAM.search(sig):
        fail(
            f"{_ISSUE}: {cmd} must take no path / root / URL from the "
            "webview (archive via with_arch / app state only)"
        )
    invoke_rx = re.compile(
        r"invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']" + re.escape(cmd) + r"[\"']"
    )
    for payload in _invoke_payloads(api + "\n" + doctor + "\n" + web, invoke_rx):
        if _payload_has_path_or_url(payload):
            fail(
                f"{_ISSUE}: do not pass path / root / URL from the webview "
                f"to {cmd}"
            )
    if api_name:
        api_fn = _fn(api, api_name) or _ts_fn_body(api, api_name)
        if _CLIENT_PARAM.search(api_fn) or re.search(
            r"\b(?:path|root|url)\b",
            re.search(
                rf"{re.escape(api_name)}\s*[:=]\s*(?:async\s*)?\(([^)]*)\)",
                api,
            ).group(1)
            if re.search(
                rf"{re.escape(api_name)}\s*[:=]\s*(?:async\s*)?\(([^)]*)\)",
                api,
            )
            else "",
        ):
            fail(
                f"{_ISSUE}: api.{api_name}() must take no path / root / URL args"
            )
    if not re.search(r"\bwith_arch\s*\(", own):
        fail(
            f"{_ISSUE}: {cmd} must use with_arch on the held Exclusive "
            '("no archive open" is an estimate failure)'
        )
    if re.search(r"\bwith_arch_mut\s*\(", own):
        fail(f"{_ISSUE}: estimate is read-only — with_arch, not with_arch_mut")
    if _OPEN_SECOND.search(own):
        fail(
            f"{_ISSUE}: do not open_archive a second Exclusive "
            "(use the held Archive; do not drop flock)"
        )
    if _DROP_FLOCK.search(own):
        fail(
            f"{_ISSUE}: do not drop flock / close_archive during estimate"
        )
    if _CORE not in own and not _ESTIMATE_NAME.search(own):
        fail(f"{_ISSUE}: {cmd} must call {_CORE} (read-only sibling of gc_cas)")

    # 4) estimate-walk / no-delete — same walk as gc_cas; metadata sum.
    if _CORE not in core_cas:
        fail(
            f"{_ISSUE}: core helper {_CORE} must live next to gc_cas in cas.rs"
        )
    est_own = _rust_function_body(core_cas, _CORE)
    if not est_own.strip():
        fail(
            f"{_ISSUE}: {_CORE} must walk cas/ like gc_cas and return u64 bytes"
        )
    if "walk_blobs" not in est_own:
        fail(
            f"{_ISSUE}: {_CORE} must use the same walk_blobs as gc_cas"
        )
    if not re.search(r"\battachments\b", est_own) or not re.search(
        r"\bphoto_cas_hash\b", est_own
    ):
        fail(
            f"{_ISSUE}: {_CORE} must use the same two-table COUNT "
            "(attachments.cas_hash + contacts_raw.photo_cas_hash)"
        )
    if not _COUNT_SQL.search(est_own):
        fail(
            f"{_ISSUE}: {_CORE} must COUNT attachment / photo refs "
            "(not refcount==0, not SUM(cas_blobs.size))"
        )
    if not _META.search(est_own) or not re.search(r"\.len\s*\(", est_own):
        fail(
            f"{_ISSUE}: {_CORE} must sum fs::metadata(path).len() "
            "for unreferenced 64-hex files"
        )
    if not re.search(r"\bparse_hash\b", est_own) and not (
        re.search(r"\b64\b", est_own) and re.search(r"hex", est_own, re.I)
    ):
        fail(
            f"{_ISSUE}: {_CORE} must skip non-64-hex names the way gc_cas does"
        )
    if _REMOVE_FILE.search(est_own):
        fail(f"{_ISSUE}: {_CORE} must not remove_file (gc_cas is the deleter)")
    if _CAS_WRITE.search(est_own):
        fail(
            f"{_ISSUE}: {_CORE} must not DELETE / UPDATE cas_blobs "
            "(no refcount repair)"
        )
    if _SUM_SIZE.search(est_own):
        fail(
            f"{_ISSUE}: {_CORE} must not SUM(cas_blobs.size) — filesystem walk"
        )
    if _REFCOUNT0.search(est_own):
        fail(
            f"{_ISSUE}: {_CORE} must not use refcount==0 "
            "(same COUNT as gc_cas, not the cache)"
        )
    if _META_SKIP.search(est_own) or not _META_OK.search(est_own):
        fail(
            f"{_ISSUE}: one metadata error must fail the whole estimate "
            "(do not skip a file)"
        )
    if not re.search(
        rf"fn\s+{_CORE}\s*\(\s*&self",
        core_cas,
    ):
        fail(
            f"{_ISSUE}: Archive must wrap {_CORE} "
            "(same shape as Archive::gc_cas)"
        )

    # 5) when-walk-runs — GC click only, before dialog; do not fold into scans.
    load_body = _fn(doctor, "load")
    if _ESTIMATE_INVOKE.search(load_body):
        fail(
            f"{_ISSUE}: do not estimate on Doctor load / Refresh "
            "(GC click only, before the dialog)"
        )
    if _ESTIMATE_INVOKE.search(_button_click(doctor, "Refresh")):
        fail(f"{_ISSUE}: Refresh must stay load() — no estimate")
    for name in ("applyStatus", "openPath", "createArchive", "openPicker"):
        body = _fn(web, name) or _ts_fn_body(web, name)
        if body and (
            _ESTIMATE_INVOKE.search(body) or _GC_ON_OPEN.search(body)
        ):
            fail(
                f"{_ISSUE}: no estimate / gcCas on open / {name} "
                "(keep #136 — GC click only)"
            )
    issues_body = _rust_function_body(core_src, "doctor_issues")
    quick_body = _rust_function_body(core_src, "doctor_issues_quick")
    if _CORE in issues_body or _ESTIMATE_NAME.search(issues_body):
        fail(
            f"{_ISSUE}: do not fold bytes into doctor_issues "
            "(referenced cas_get stays the full scan)"
        )
    if _CORE in quick_body or _ESTIMATE_NAME.search(quick_body) or re.search(
        r"\bwalk_blobs\b", quick_body
    ):
        fail(
            f"{_ISSUE}: doctor_issues_quick must still skip the CAS walk "
            "(#136) — do not hang the estimate off quick"
        )
    if re.search(r"confirmDesc\s*=", gc_raw) and ask_at >= 0:
        desc_at = _first(gc_raw, re.compile(r"confirmDesc\s*="))
        if desc_at > ask_at:
            fail(
                f"{_ISSUE}: do not live-patch an already-open dialog "
                "(estimate, then ask() with the sized copy)"
            )

    # 6) fallback + Ok(0) + still doctorRun({ gcCas: true }).
    if not _T_DESC.search(gc_surf):
        fail(
            f'{_ISSUE}: estimate Err must open today\'s exact t("{_DESC_KEY}") '
            "(GC still runnable)"
        )
    if _T_DESC_REPLACE.search(gc_surf):
        fail(
            f"{_ISSUE}: t(\"{_DESC_KEY}\") stays today's unsized copy "
            "(new ChromeKey + .replace for the sized success path)"
        )
    if en.get(_DESC_KEY, "") != _DESC_EN:
        fail(
            f"{_ISSUE}: en {_DESC_KEY} must stay today's exact fallback copy"
        )
    if tr.get(_DESC_KEY, "") != _DESC_TR:
        fail(
            f"{_ISSUE}: tr {_DESC_KEY} must stay today's exact fallback copy"
        )
    if _zero_uses_unsized(gc_raw):
        fail(
            f"{_ISSUE}: Ok(0) must still show a sized copy (0 B) — "
            f'do not fall back to unsized t("{_DESC_KEY}")'
        )
    run_pending = _fn(doctor, "runPending")
    if not _DOCTOR_RUN_API.search(run_pending) or not re.search(
        r"gcCas\s*:", run_pending
    ):
        fail(
            f"{_ISSUE}: confirm must still doctorRun({{ gcCas: true }}) "
            "(estimate Err must not block GC)"
        )
    if not _GC_CAS_FLAG.search(gc_surf):
        fail(
            f"{_ISSUE}: GC pending flags must still set gcCas: true"
        )

    # 7) busy while estimating; do not flip scanning.
    if not _BUSY_TRUE.search(gc_raw):
        fail(
            f"{_ISSUE}: set existing busy while estimating "
            "(Integrity / Rebuild / GC / Refresh stay disabled)"
        )
    if _SCAN_TRUE.search(gc_raw):
        fail(
            f"{_ISSUE}: do not flip scanning during estimate "
            "(that hides issues behind the SQLite scan line)"
        )
    for label in ("Integrity", "Rebuild FTS", "GC CAS", "Refresh"):
        tag = _action_button_tag(doctor, label)
        if not tag or not _DISABLED_BUSY.search(tag):
            fail(
                f"{_ISSUE}: {label} must stay disabled={{busy || scanning}} "
                "(reuse busy; do not invent a new disable)"
            )

    # 8) byte-format — human decimal SI in TS from the u64.
    fmt = _format_fn(doctor + "\n" + web, gc_surf)
    if not fmt.strip() and _SI_1000.search(gc_surf):
        fmt = gc_surf
    if not fmt.strip():
        fail(
            f"{_ISSUE}: format the u64 in TS "
            "(human decimal SI B/KB/MB/GB — not raw String(n), not Rust)"
        )
    if _REPLACE_N_RAW.search(gc_surf):
        fail(
            f"{_ISSUE}: {{n}} is the SI string (8 MB, 1.5 GB, 0 B), "
            "not String(n) raw bytes"
        )
    if not _SI_1000.search(fmt) or _SI_1024.search(fmt):
        fail(
            f"{_ISSUE}: byte format is 1000-based SI (B / KB / MB / GB), "
            "not 1024 / MiB"
        )
    if _SI_IEC.search(fmt) or _SI_IEC.search(gc_surf):
        fail(f"{_ISSUE}: SI units are B / KB / MB / GB — not KiB / MiB / GiB")
    if len(_SI_UNIT.findall(fmt)) < 4 and not (
        re.search(r"\bB\b", fmt)
        and re.search(r"\bKB\b", fmt)
        and re.search(r"\bMB\b", fmt)
        and re.search(r"\bGB\b", fmt)
    ):
        fail(
            f"{_ISSUE}: formatter must emit B / KB / MB / GB "
            "(whole when exact; one fraction digit otherwise)"
        )
    if not _FRACTION.search(fmt):
        fail(
            f"{_ISSUE}: whole numbers when exact; one fraction digit "
            "otherwise (8 MB, 1.5 GB)"
        )
    if not _ZERO_B.search(fmt) and not re.search(r"0\s*\+|<\s*1000", fmt):
        fail(f"{_ISSUE}: Ok(0) formats as 0 B")
    if _FILE_COUNT_COPY.search(gc_surf):
        fail(f"{_ISSUE}: confirm names bytes only — not a file count")

    # 9) locale — new en+tr ChromeKey; t() stays key-only; no encrypted.
    sized_key = ""
    sm = _T_SIZED.search(gc_surf)
    if sm:
        sized_key = sm.group(1)
    if not sized_key or sized_key == "linkThesePeopleDesc":
        fail(
            f"{_ISSUE}: new ChromeKey + .replace(\"{{n}}\", formatted) "
            "(do not reuse Review's linkThesePeopleDesc)"
        )
    if sized_key not in en or sized_key not in tr:
        fail(
            f"{_ISSUE}: {sized_key} must exist on both en.ts and tr.ts "
            "(same ChromeKey — #278)"
        )
    if "{n}" not in en.get(sized_key, "") or "{n}" not in tr.get(sized_key, ""):
        fail(
            f"{_ISSUE}: {sized_key} must include {{n}} on both packs "
            "(Review-style interpolation)"
        )
    if en.get(sized_key, "").strip() == tr.get(sized_key, "").strip():
        fail(
            f"{_ISSUE}: tr {sized_key} must not be an English copy (#278)"
        )
    extra_en = set(en) - set(tr)
    extra_tr = set(tr) - set(en)
    if extra_en or extra_tr:
        bits: list[str] = []
        if extra_en:
            bits.append("in en only: " + ", ".join(sorted(extra_en)))
        if extra_tr:
            bits.append("in tr only: " + ", ".join(sorted(extra_tr)))
        fail(
            f"{_ISSUE}: same ChromeKey on both en and tr packs — "
            + "; ".join(bits)
        )
    if not _T_FN.search(i18n) or re.search(
        r"export\s+function\s+t\s*\(\s*key\s*:\s*ChromeKey\s*,",
        i18n,
    ):
        fail(
            f"{_ISSUE}: t() stays key-only "
            "(ChromeKey → string; interpolate with .replace)"
        )
    locale_blob = en.get(sized_key, "") + "\n" + tr.get(sized_key, "")
    if _claim_without_negation(locale_blob + "\n" + gc_surf, _REVEAL_ARCHIVE_ENCRYPT):
        fail(
            f"{_ISSUE}: new GC copy must not claim SQLCipher / encrypted DB"
        )

    # 10) keep Integrity / Rebuild confirms and flags.
    integ = _integrity_click_raw(doctor)
    reb = _rebuild_click_raw(doctor)
    if not _INTEGRITY_ASK.search(integ) or not _INTEGRITY_FLAGS.search(integ):
        fail(
            f"{_ISSUE}: Integrity must stay "
            'ask(t("runIntegrityCheck"), t("runIntegrityCheckDesc"), '
            "t(\"integrityCheck\"), { integrity: true, gcCas: false }) "
            "with no estimate"
        )
    if _ESTIMATE_INVOKE.search(integ):
        fail(f"{_ISSUE}: Integrity click must not estimate")
    if not _REBUILD_ASK.search(reb) or not _REBUILD_FLAGS.search(reb):
        fail(
            f"{_ISSUE}: Rebuild FTS must stay "
            'ask(t("rebuildSearchIndex"), t("rebuildSearchIndexDesc"), '
            't("rebuild"), { rebuildFts: true, gcCas: false }) '
            "with no estimate"
        )
    if _ESTIMATE_INVOKE.search(reb):
        fail(f"{_ISSUE}: Rebuild FTS click must not estimate")

    # 11) keep-136 — full doctorIssues on tab load; quick skip; no GC on open.
    if not _DOCTOR_ISSUE_API.search(load_body) or _QUICK_DOCTOR.search(load_body):
        fail(
            f"{_ISSUE}: keep Doctor tab full doctorIssues "
            "(onMount / load / Refresh — do not rewrite #136)"
        )
    if not re.search(r"onMount\s*\(", doctor) or "load()" not in doctor:
        fail(
            f"{_ISSUE}: keep DoctorPane onMount → load() full scan (#136)"
        )
    if not re.search(r"onclick=\{[^}]*\bload\b", doctor):
        fail(f"{_ISSUE}: Refresh must still call load (#136)")
    full_body = _full_doctor_scan_body(core_src, rust)
    if not re.search(r"\bcas_get\b", full_body) or not re.search(
        r"cas_hash", full_body
    ):
        fail(
            f"{_ISSUE}: full doctor scan must still cas_get referenced hashes "
            "(#136) — estimate is a different walk"
        )

    # 12) keep-205 Retry = load.
    retry = ""
    for m in re.finditer(r"data-partial", doctor):
        win = doctor[m.start() : m.start() + 500]
        retry += "\n" + _resolve_handler_blob(doctor, _retry_click_expr(win))
    if not retry.strip():
        retry = _resolve_handler_blob(doctor, _retry_click_expr(doctor))
    if _DOCTOR_HEAVY.search(retry) or _ESTIMATE_INVOKE.search(retry):
        fail(
            f"{_ISSUE}: Doctor Retry must stay load / doctorIssues "
            "(#205) — not doctorRun / gcCas / estimate"
        )
    if not re.search(r"\b(?:load|doctorIssues)\b", retry + "\n" + doctor):
        fail(f"{_ISSUE}: keep Doctor Retry → load (#205)")
    if not _PARTIAL_TAG.search(doctor) or not _RETRY.search(doctor):
        fail(f"{_ISSUE}: keep in-pane Error + Retry (#205)")

    # 13) keep-221 close-first.
    go = _fn(confirm, "go") or _ts_fn_body(confirm, "go")
    if "open = false" not in go or not re.search(r"await\s+onconfirm", go):
        fail(
            f"{_ISSUE}: ConfirmDialog go() must still close first "
            "(open = false before await onconfirm — #221)"
        )
    if "onconfirm={runPending}" not in doctor and not re.search(
        r"onconfirm=\{runPending\}", doctor
    ):
        fail(f"{_ISSUE}: Doctor ConfirmDialog must still runPending (#221)")

    # 14) keep-274 Reveal + keep-320 Copy.
    if "data-reveal-archive" not in doctor:
        fail(f"{_ISSUE}: keep Doctor data-reveal-archive (#274)")
    if not re.search(r"\bfn\s+reveal_archive\b", rust):
        fail(f"{_ISSUE}: keep reveal_archive (#274)")
    if "data-copy-archive" not in doctor or not re.search(
        r"\bcopyArchiveTo\b", doctor + "\n" + api
    ):
        fail(f"{_ISSUE}: keep Doctor Copy archive to… (#320)")

    # 15) keep-cas3 — gc_cas still deletes unreferenced only.
    if "cas3_gc_unreferenced_only" not in cas_test:
        fail(
            f"{_ISSUE}: keep CAS3 cas3_gc_unreferenced_only "
            "(do not rewrite the file-count deleter)"
        )
    gc_own = _rust_function_body(core_cas, "gc_cas")
    if not _REMOVE_FILE.search(gc_own) or not _COUNT_SQL.search(gc_own):
        fail(
            f"{_ISSUE}: gc_cas must still delete unreferenced files "
            "(COUNT refs, not refcount==0 alone)"
        )
    if re.search(r"refcount\s*==\s*0", gc_own) and not _COUNT_SQL.search(gc_own):
        fail(f"{_ISSUE}: gc_cas must not GC from refcount==0 alone (CAS3)")

    # 16) CLI --gc-cas unchanged (no byte line).
    cmd_doc = _rust_function_body(cli, "cmd_doctor")
    if not re.search(r"--gc-cas", cli) or not re.search(r"\bgc_cas\b", cli):
        fail(f"{_ISSUE}: keep CLI interlace doctor --gc-cas")
    if _CORE in cmd_doc or _ESTIMATE_NAME.search(cmd_doc):
        fail(
            f"{_ISSUE}: CLI --gc-cas stays unsized "
            "(no estimate / no byte line)"
        )
    if re.search(r"println!\s*\([^)]*(?:byte|MB|GB|reclaim)", cmd_doc, re.I):
        fail(f"{_ISSUE}: CLI --gc-cas must not print reclaimable bytes")
    if 'println!("ok")' not in cmd_doc and "println!(\"ok\")" not in cmd_doc:
        if not re.search(r'println!\s*\(\s*"ok"', cmd_doc):
            fail(f"{_ISSUE}: CLI doctor must still print ok (no byte line)")

    # 17) bans — plugin-shell / HTTP / network.server / SQLCipher / CSP.
    if _PLUGIN_SHELL.search(toml) or _PLUGIN_SHELL.search(pkg):
        fail(f"{_ISSUE}: do not add tauri-plugin-shell / tauri-plugin-opener")
    if _SHELL_CAP.search(caps):
        fail(
            f"{_ISSUE}: capabilities must not add shell:allow-execute / opener"
        )
    if _FETCH_CALL.search(own) or _LINKIFY_FETCH.search(own):
        fail(f"{_ISSUE}: no fetch / HTTP from the estimate command")
    if _HTTP_CLIENT.search(toml) or _HTTP_CLIENT.search(own):
        fail(f"{_ISSUE}: no HTTP client / tauri-plugin-http")
    if "network.server" in ent:
        fail(f"{_ISSUE}: entitlements must omit network.server")
    if CSP not in conf:
        fail(f"{_ISSUE}: do not soften tauri CSP")
    if _ARBITRARY_SHELL.search(own) or _ARBITRARY_SHELL.search(est_own):
        fail(f"{_ISSUE}: no arbitrary shell — estimate is a local walk")
    product_claim = "\n".join((doctor, gc_surf, doctor_md, app_md))
    if _claim_without_negation(product_claim, _REVEAL_ARCHIVE_ENCRYPT):
        fail(
            f"{_ISSUE}: no “database is encrypted” / SQLCipher claim "
            "(keep not encrypted / FileVault)"
        )
    if _REAL_HOME.search(doctor + "\n" + gc_raw + "\n" + est_own):
        fail(f"{_ISSUE}: tests stay placeholders (Ada) — no real home paths")

    # 18) gc-d24 — doctor.md AND app.md name reclaimable bytes in the confirm.
    if not doctor_md.strip() or not app_md.strip():
        fail(
            f"{_ISSUE}: D24 both docs/user/doctor.md and docs/user/app.md"
        )
    if not _DOCS_BYTES.search(doctor_md):
        fail(
            f"{_ISSUE}: docs/user/doctor.md must say the in-app GC confirm "
            "names reclaimable bytes"
        )
    if not _DOCS_BYTES.search(app_md):
        fail(
            f"{_ISSUE}: docs/user/app.md must say the in-app GC confirm "
            "names reclaimable bytes"
        )
    if not _DOCS_ENCRYPT_OK.search(doctor_md + "\n" + app_md):
        fail(
            f"{_ISSUE}: keep “not encrypted / FileVault” in doctor.md / app.md"
        )
