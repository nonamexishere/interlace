"""#320 — Copy archive to… (local backup unit).

Confirmed mix: one Rust command `copy_archive_to` (never `fn backup`).
Source is `archive_root` from app state. Dest is rfd inside that command
(no webview path). Copy toml + sqlite+wal+shm + cas/ + logs/; skip tmp/
and imports/*/spill. Refuse non-empty dest, dest == open root or inside
it, http(s)/URL dest, and import `running`. Doctor Backup owned Button
next to Reveal + File menu. Control stays clickable; calm chrome error;
success toast “Archive copied” (no path). Keep #274 / #266 / #130.

Must-IDs: copy-cmd, copy-source-archive-root, copy-no-client-source,
copy-dest-rfd, copy-refuse-url, copy-refuse-import, copy-empty-dest,
copy-skip-tmp-spill, copy-sqlite-wal, copy-doctor-control,
copy-file-menu, copy-keys-en-tr, copy-no-plugin-shell,
copy-no-zip-icloud, copy-d24, keep-274-reveal, keep-266-cancel,
keep-130-file, copy-opening-overlay, copy-dest-drop-shm,
keep-136-doctor-full, copy-recheck-after-picker, copy-in-progress,
copy-dest-rollback, copy-open-refuses, copy-second-walk-cas,
copy-import-recheck-take, copy-openpath-keep-doctor.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.import_boot_guards import _owned_imported_names
from tauri_gate.import_reveal_cmd import (
    _REVEAL_ARCHIVE_BACKUP_FN,
    _REVEAL_ARCHIVE_DOC,
    _REVEAL_ARCHIVE_DOC_COPY,
    _REVEAL_ARCHIVE_ENCRYPT,
    _REVEAL_ARCHIVE_ZIP_ICLOUD,
    _doctor_backup_section,
)
from tauri_gate.locale_menu import (
    _CHECK_UPDATES_ITEM,
    _FILE_SUBMENU,
    _ICLOUD_MENU_ITEM,
    _IMPORT_ITEM,
    _OPEN_ITEM,
    _PREFERENCES_ITEM,
    _menu_handler_surface,
)
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.media_linkify_lib import (
    _PLUGIN_SHELL,
    _SHELL_CAP,
    _hook_element_blocks,
)
from tauri_gate.recent_archives import _file_submenu, _read
from tauri_gate.scan import (
    CSP,
    _ARBITRARY_SHELL,
    _FETCH_CALL,
    _LINKIFY_FETCH,
    _expand_fn_calls,
    _function_body,
    _match_closer,
    _rust_body_with_callees,
    _rust_fn_signature,
    _rust_function_body,
    _svelte_markup,
    _tauri_rust_blob,
    _ts_fn_body,
    _web_logic,
    _without_comments,
)
from tauri_gate.status_toasts_chrome import (
    _claim_without_negation,
    _invoke_payloads,
    _parse_if_chain,
    _payload_has_path_or_url,
    _windows_around,
)

_ISSUE = "#320"
_CMD = "copy_archive_to"
_API = "copyArchiveTo"
_KEY = "copyArchiveTo"
_HOOK = "data-copy-archive"
_LABEL = "Copy archive to…"
_SUCCESS = "Archive copied"
_OPEN_TITLE = "Interlace archive folder"
_BANNED_CMDS = frozenset({"backup", "reveal_archive", "open_url", "open", "pick_folder"})
_T_COPY = re.compile(r"""\bt\s*\(\s*["']copyArchiveTo["']\s*\)""")
_T_CALL = re.compile(r"""\bt\s*\(\s*["']([A-Za-z_][\w]*)["']""")
_LABEL_RX = re.compile(r"Copy archive to(?:…|\.\.\.)")
_MENU_LABEL = re.compile(r"[\"']Copy archive to(?:…|\.\.\.)[\"']")
_MENU_ID = re.compile(
    r"[\"'](?:copy-archive-to|copy-archive|menu-copy-archive-to|"
    r"menu-copy-archive)[\"']"
)
_MENU_EVENT = re.compile(
    r"[\"'](?:menu-copy-archive-to|menu-copy-archive|copy-archive-to|"
    r"copy-archive)[\"']"
)
_COPY_INVOKE = re.compile(
    r"invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']copy_archive_to[\"']"
    r"|\.?copyArchiveTo\s*\("
)
_PATH_ARG = re.compile(r"\b(?:path|url|file|href|uri|dest|source)\s*:", re.I)
_CLIENT_ARG = re.compile(
    r"\b(?:path|url|file|href|uri|dest|source)\b",
    re.I,
)
_RFD = re.compile(r"\brfd\s*::\s*FileDialog\b|\bFileDialog\s*::\s*new\s*\(")
_PICK_FOLDER_CMD = re.compile(r"\bpick_folder\s*\(")
_OPEN_PICK_TITLE = re.compile(r"[\"']Interlace archive folder[\"']")
_MAIN_THREAD = re.compile(r"\brun_on_main_thread\s*\(")
_HTTP_DEST = re.compile(
    r"("
    r"https?://"
    r"|starts_with\s*\(\s*[\"']https?:"
    r"|[\"']https?:"
    r"|scheme\s*://"
    r")"
)
_REFUSE_URL = re.compile(
    r"("
    r"https?://"
    r"|only (?:a )?local"
    r"|not a url"
    r"|refuse.{0,40}url"
    r"|url.{0,40}refuse"
    r"|scheme"
    r")",
    re.I | re.S,
)
_IMPORT_RUN = re.compile(
    r"("
    r"import.{0,80}running"
    r"|running.{0,80}import"
    r"|status\s*==\s*[\"']running[\"']"
    r")",
    re.S | re.I,
)
_EMPTY_DEST = re.compile(
    r"("
    r"not empty"
    r"|non[- ]empty"
    r"|is_empty"
    r"|read_dir"
    r"|dest.{0,40}empty"
    r"|empty.{0,40}dest"
    r")",
    re.I | re.S,
)
_INSIDE_SRC = re.compile(
    r"("
    r"starts_with"
    r"|inside (?:the )?(?:open )?(?:archive|root|source)"
    r"|dest (?:is )?(?:the )?(?:open )?root"
    r"|same (?:as )?(?:the )?(?:open )?root"
    r"|sub(?:folder|dir) of"
    r")",
    re.I,
)
_TOML = re.compile(r"INTERLACE\.toml")
_SQLITE = re.compile(r"archive\.sqlite")
_WAL = re.compile(r"sqlite-wal|[\"']-wal[\"']|archive\.sqlite-wal")
_SHM = re.compile(r"sqlite-shm|[\"']-shm[\"']|archive\.sqlite-shm")
_CAS_DIR = re.compile(r"[\"']cas[\"']|[\"']cas/")
_LOGS_DIR = re.compile(r"[\"']logs[\"']|[\"']logs/")
_SKIP_TMP = re.compile(
    r"("
    r"skip.{0,40}tmp"
    r"|tmp.{0,40}skip"
    r"|ignore.{0,40}tmp"
    r"|!=\s*[\"']tmp[\"']"
    r"|==\s*[\"']tmp[\"']"
    r"|[\"']tmp[\"']"
    r")",
    re.I | re.S,
)
_SKIP_SPILL = re.compile(
    r"("
    r"spill"
    r")",
    re.I,
)
_SKIP_WORD = re.compile(r"\b(?:skip|ignore|continue|filter)\b", re.I)
_VACUUM = re.compile(r"VACUUM\s+INTO|\.backup\s*\(|Connection\s*::\s*backup")
_CLOSE_DURING = re.compile(
    r"("
    r"\bclose_archive\s*\("
    r"|archive\s*=\s*None"
    r"|archive_root[^=]{0,80}=\s*None"
    r")"
)
_STEAL_LAST = re.compile(
    r"("
    r"\bwrite_last_path\s*\("
    r"|\bpersist_bookmark\s*\("
    r"|\bwrite_last_bookmark\s*\("
    r"|last_archive_path"
    r"|last-archive\.bookmark"
    r")"
)
_AUTO_OPEN = re.compile(
    r"("
    r"\bopen_archive\s*\("
    r"|\bopen\s*\(\s*(?:app\s*,\s*)?(?:dest|picked|out)"
    r")"
)
_CLOUD_ERR = re.compile(
    r"return\s+Err\s*\([^;]{0,200}(?:iCloud|Dropbox|Google Drive)",
    re.I,
)
_HTTP_CLIENT = re.compile(r"\b(?:reqwest|ureq|hyper::Client|tauri-plugin-http)\b")
_ASK = re.compile(r"\bask\s*\(|confirmOpen\s*=\s*true")
_TOAST_CALL = re.compile(r"\b(?:showToast|onToast)\s*\??\s*\(")
_TOAST_LEAK = re.compile(
    r"("
    r"/Users/"
    r"|/home/"
    r"|file:"
    r"|https?://"
    r"|st\.path"
    r"|archive_root"
    r"|\$\{"
    r")"
)
_ERR_PATH = re.compile(
    r"format!\s*\(\s*[\"'][^\"']*(?:\{dest\}|\{path\}|\{picked\})"
    r"|Err\s*\([^)]{0,160}(?:to_string_lossy|display\s*\()"
)
_DISABLED_IMPORT = re.compile(
    r"disabled\s*=\s*\{[^}]{0,200}"
    r"(?:import|running)",
    re.I,
)
_SWITCH_ON = re.compile(
    r"open\s*&&\s*!\s*(?:running|import)|!\s*(?:running|import).{0,40}open",
    re.I | re.S,
)
_JOIN_ABORT = re.compile(
    r"("
    r"thread::[^\n]{0,60}\b(?:kill|terminate)\b"
    r"|JoinHandle::[^\n]{0,60}\babort\b"
    r"|\b(?:JoinHandle|join_handle|import_handle)\b[^\n]{0,80}\.abort\s*\("
    r"|\bpthread_kill\b"
    r")"
)
_DOCS_COPY = re.compile(r"Copy archive to(?:…|\.\.\.)", re.I)
_DOCS_WRITER = re.compile(
    r"("
    r"only writer"
    r"|this app (?:is|keeps|holds|remains) (?:the )?(?:only )?writer"
    r"|exclusive (?:flock|lock)"
    r"|writers? (?:are|is) this app"
    r"|while (?:this app|the app|it) (?:is )?(?:the )?only writer"
    r"|this app (?:is )?the only writer"
    r")",
    re.I | re.S,
)
_DOCS_OPENS = re.compile(
    r"("
    r"dest(?:ination)? (?:folder )?(?:Opens|opens)"
    r"|Opens as an archive"
    r"|open(?:s)? (?:that |the )?(?:dest|copied|empty) (?:folder|archive)"
    r"|that folder Opens"
    r")",
    re.I | re.S,
)
_DOCS_IMPORT = re.compile(
    r"("
    r"import (?:is )?running.{0,80}refus"
    r"|refus.{0,80}import (?:is )?running"
    r"|import running.{0,60}(?:error|refuse|calm)"
    r")",
    re.I | re.S,
)
_DOCS_AFTER = re.compile(
    r"("
    r"after (?:you )?clos"
    r"|clos(?:e|ing) (?:the )?(?:app|window)"
    r"|cp\s+-a"
    r")",
    re.I,
)
_REAL_HOME = re.compile(r"/Users/[A-Za-z]|/home/[A-Za-z]")
_PANE_TAG = re.compile(r"<(?:DoctorPane|PeopleShell|SearchPane)\b")
_REMOVE_FILE = re.compile(
    r"\b(?:(?:std\s*::\s*)?fs\s*::\s*)?(?:remove_file|unlink)\s*(?:!)?\s*\("
)
_DEST_SHM_IDENT = re.compile(r"\b(?:dest_shm|shm_dest|out_shm|dest_shm_path)\b")
_DEST_JOIN = re.compile(r"\b(?:to|dest|out|picked)\b")
_PICK_DEST = re.compile(
    r"("
    r"\b(?:pick_copy_dest|pick_copy_dest_rfd|pick_dest)\s*\("
    r"|FileDialog\s*::\s*new\s*\("
    r"|\.pick_folder\s*\("
    r"|\brfd\s*::\s*FileDialog\b"
    r")"
)
_STATE_ROOT = re.compile(
    r"state\s*\.\s*archive_root|\.archive_root\s*\.\s*lock"
)
_ROOT_GONE = re.compile(
    r"("
    r"no archive open"
    r"|ok_or(?:_else)?"
    r"|is_none\s*\("
    r"|root (?:is )?gone"
    r"|archive closed"
    r")",
    re.I,
)
_ROOT_CHANGED = re.compile(
    r"("
    r"no longer"
    r"|root changed"
    r"|archive (?:root )?changed"
    r"|not (?:the )?(?:same )?(?:source|open )?root"
    r"|\b(?:live|current|fresh|again|now|got|root2|new_root)\b.{0,60}(?:==|!=)"
    r"|(?:==|!=).{0,60}\b(?:live|current|fresh|again|now|got|root2|new_root)\b"
    r"|\b(?:archive_root|from|src|source)\s*!=\s*&?(?:archive_root|from|live|current|fresh|again|now|got|root)\b"
    r"|!=\s*&?(?:archive_root|from)\b"
    r")",
    re.I | re.S,
)
_DEST_VS_SRC = re.compile(
    r"("
    r"\b(?:to|picked|dest|out)\b\s*==\s*&?(?:from|archive_root)\b"
    r"|\b(?:from|archive_root)\b\s*==\s*&?(?:to|picked|dest|out)\b"
    r"|\.starts_with\s*\("
    r")"
)
_COPY_FLAG_NAME = re.compile(
    r"\b("
    r"copying|copy_in_progress|copy_running|is_copying|"
    r"copying_archive|copy_busy|archive_copying|copy_lock|"
    r"copy_in_flight|copying_to|copy_active|copy_guard|"
    r"copying_flag|CopyInProgress|Copying"
    r")\b"
)
_FLAG_SET = re.compile(
    r"("
    r"=\s*true\b"
    r"|=\s*Some\s*\("
    r"|\.store\s*\(\s*true"
    r"|swap\s*\(\s*true"
    r")"
)
_FLAG_CLEAR = re.compile(
    r"("
    r"=\s*false\b"
    r"|=\s*None\b"
    r"|\.store\s*\(\s*false"
    r"|swap\s*\(\s*false"
    r")"
)
_DROP_FOR = re.compile(r"\bimpl(?:\s*<[^>]+>)?\s+Drop\s+for\s+(\w+)")
_ROLLBACK_FN = re.compile(
    r"\bfn\s+(\w*(?:rollback|revert_dest|cleanup_dest|remove_partial|"
    r"wipe_dest|undo_copy|clear_partial)\w*)\b",
    re.I,
)
_REMOVE_DIR_ALL = re.compile(
    r"\b(?:(?:std\s*::\s*)?fs\s*::\s*)?remove_dir_all\s*(?:!)?\s*\("
)
_ERR_WRAP = re.compile(
    r"if\s+let\s+Err|inspect_err\s*\(|\.or_else\s*\(|\.is_err\s*\("
)
_RETURN_ERR = re.compile(r"return\s+Err\s*\(|\bErr\s*\(")
_PICKER_CALLEES = frozenset(
    {
        "pick_copy_dest",
        "pick_copy_dest_rfd",
        "pick_dest",
        "FileDialog",
        "pick_folder",
        "new",
        "set_title",
        "run_on_main_thread",
        "send",
        "recv",
        "Ok",
        "Err",
        "Some",
        "None",
        "drop",
        "clone",
        "lock",
        "map_err",
        "ok_or",
        "ok_or_else",
        "canonicalize",
        "starts_with",
        "join",
        "format",
    }
)
_ARCHIVE_DROP = re.compile(
    r"("
    r"\*\s*(?:state\s*\.\s*)?archive\b[^=;\n]{0,160}=\s*None"
    r"|\.archive\b[^=;\n]{0,160}=\s*None"
    r"|archive\s*=\s*None"
    r"|\barchive\b[^\n]{0,60}\.take\s*\("
    r")"
)
_COPY_IN_PROGRESS_ERR = re.compile(
    r"("
    r"[\"']copy in progress[\"']"
    r"|copy[- ]in[- ]progress"
    r"|already.{0,24}copy"
    r"|copy.{0,24}already"
    r")",
    re.I,
)
_CAS_SET = re.compile(
    r"\bcompare_exchange(?:_weak)?\b|\bcompare_and_swap\b"
)
_SWAP_TRUE = re.compile(r"\.swap\s*\(\s*true")
_CLAIM_IDENT = re.compile(r"\b(?:flag|copying|copy_in_progress|busy)\b")


def _fn(src: str, name: str) -> str:
    return _ts_fn_body(src, name) or _function_body(src, name) or ""


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
    for m in re.finditer(r"(?:onclick|on:click)\s*=\s*\{", head):
        last = m
    if not last:
        return ""
    return _brace_after(src, last.end() - 1)


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


def _copy_control_hit(section: str) -> bool:
    if _HOOK in section:
        return True
    if _T_COPY.search(section):
        return True
    return bool(_LABEL_RX.search(section))


def _owned_button_tag(doctor: str, section: str) -> str:
    names = _owned_imported_names(doctor, "button") or ["Button"]
    blocks: list[str] = []
    markup = _svelte_markup(section) if section else section
    host = markup or section
    for hook_blocks in _hook_element_blocks(host, _HOOK):
        blocks.append(hook_blocks)
    if not blocks:
        for name in names:
            for m in re.finditer(rf"<{re.escape(name)}\b", host):
                tag = host[m.start() : m.start() + 500]
                if _HOOK in tag or _T_COPY.search(tag) or _LABEL_RX.search(tag):
                    blocks.append(tag)
    return "\n".join(blocks)


def _is_owned_button(doctor: str, tag: str) -> bool:
    names = _owned_imported_names(doctor, "button")
    if not names:
        return False
    return any(re.search(rf"<{re.escape(n)}\b", tag) for n in names)


def _api_copy_args(api: str) -> str:
    m = re.search(
        rf"{re.escape(_API)}\s*:\s*(?:async\s*)?\(([^)]*)\)",
        api,
    )
    if m:
        return m.group(1)
    m = re.search(
        rf"(?:export\s+)?(?:async\s+)?function\s+{re.escape(_API)}\s*\(([^)]*)\)",
        api,
    )
    return m.group(1) if m else ""


def _payload_has_dest(payload: str) -> bool:
    if _payload_has_path_or_url(payload):
        return True
    return bool(re.search(r"\b(?:dest|source|path|url)\s*:", payload, re.I))


def _skip_tmp_spill(body: str) -> bool:
    tmp_ok = bool(_SKIP_TMP.search(body))
    spill_ok = bool(_SKIP_SPILL.search(body))
    if not tmp_ok or not spill_ok:
        return False
    spill_win = _windows_around(body, _SKIP_SPILL, before=80, after=80)
    tmp_win = _windows_around(body, re.compile(r"[\"']tmp[\"']|\btmp/"), before=80, after=80)
    return bool(_SKIP_WORD.search(tmp_win + "\n" + spill_win) or _SKIP_TMP.search(body))


def _copy_menu_enabled_swallows(file_menu: str, rust: str) -> bool:
    win = _windows_around(file_menu or rust, _MENU_LABEL, before=220, after=220)
    if not win.strip():
        win = _windows_around(file_menu or rust, _MENU_ID, before=220, after=220)
    if _SWITCH_ON.search(win):
        return True
    if re.search(r"\brunning\b", win) and re.search(
        r"enabled|set_enabled|switch_on", win, re.I
    ):
        return True
    return False


def _docs_blob() -> str:
    root = repo_root()
    out = ""
    for rel in ("docs/user/backup.md", "docs/user/app.md"):
        p = root / rel
        if p.is_file():
            out += p.read_text() + "\n"
    return out


def _cond_opening_positive(cond: str) -> bool:
    """True when the branch is taken while `opening` is true."""
    if cond == ":else" or not re.search(r"\bopening\b", cond):
        return False
    if re.search(r"!\s*opening\b", cond) or re.search(
        r"!\s*\([^)]*\bopening\b", cond
    ):
        return False
    return True


def _cond_opening_negated(cond: str) -> bool:
    """True when the branch is dropped while `opening` is true."""
    return bool(
        re.search(r"!\s*opening\b", cond)
        or re.search(r"!\s*\([^)]*\bopening\b", cond)
    )


def _opening_unmounts_main_panes(app: str) -> bool:
    """True when `opening` is an exclusive parent of Doctor / People / Search."""
    markup = _svelte_markup(app)
    i = 0
    n = len(markup)
    while i < n:
        m = re.search(r"\{#if\s+([^}]+)\}", markup[i:])
        if not m:
            return False
        start = i + m.start()
        chain, end = _parse_if_chain(markup, start)
        if not chain:
            i = start + 1
            continue
        for idx, (cond, _body) in enumerate(chain):
            if _cond_opening_positive(cond):
                later = "".join(body for _, body in chain[idx + 1 :])
                if _PANE_TAG.search(later):
                    return True
            if _cond_opening_negated(cond) and _PANE_TAG.search(_body):
                return True
        i = end if end > start else start + 1
    return False


def _drops_dest_shm(walker: str) -> bool:
    """True when dest archive.sqlite-shm is remove_file / unlink'd after copy."""
    if not walker.strip() or not _REMOVE_FILE.search(walker):
        return False
    win = _windows_around(walker, _REMOVE_FILE, before=240, after=160)
    if not _SHM.search(win) and not _DEST_SHM_IDENT.search(win):
        return False
    if re.search(r"\bfrom\.join\b", win) and not re.search(
        r"\b(?:to|dest|out|picked)\.join\b", win
    ):
        return False
    if not _DEST_JOIN.search(win) and not _DEST_SHM_IDENT.search(win):
        return False
    return True


def _after_picker(own: str) -> str:
    """Own-body suffix after the last dest picker call (pick_copy_dest / rfd)."""
    last_end = -1
    for m in _PICK_DEST.finditer(own):
        last_end = m.end()
    if last_end < 0:
        return ""
    return own[last_end:]


def _callees_of(rust: str, blob: str, skip: frozenset[str] | None = None) -> str:
    parts: list[str] = []
    seen: set[str] = set(skip or ())
    for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", blob):
        name = m.group(1)
        if name in seen:
            continue
        seen.add(name)
        inner = _rust_function_body(rust, name)
        if inner:
            parts.append(inner)
    return "\n".join(parts)


def _after_picker_surface(rust: str, own: str) -> str:
    after = _after_picker(own)
    if not after.strip():
        return ""
    return after + "\n" + _callees_of(rust, after, _PICKER_CALLEES)


def _copy_flag_names(rust: str) -> list[str]:
    out: list[str] = []
    for m in _COPY_FLAG_NAME.finditer(rust):
        name = m.group(1)
        if name not in out:
            out.append(name)
    return out


def _drop_bodies(rust: str) -> list[str]:
    bodies: list[str] = []
    i = 0
    n = len(rust)
    while i < n:
        m = _DROP_FOR.search(rust[i:])
        if not m:
            break
        start = i + m.end()
        brace = rust.find("{", start)
        if brace < 0:
            break
        bodies.append(_brace_after(rust, brace))
        i = brace + 1
    return bodies


def _flag_set_for_walk(own: str, rust: str, flag: str) -> bool:
    """True when the flag is set after the dest picker / on the copy walk."""
    after = _without_comments(_after_picker_surface(rust, own))
    walk = after + "\n" + _rust_function_body(rust, "copy_backup_unit")
    if not re.search(rf"\b{re.escape(flag)}\b", walk):
        return False
    win = _windows_around(
        walk, re.compile(rf"\b{re.escape(flag)}\b"), before=80, after=80
    )
    return bool(_FLAG_SET.search(win))


def _refuses_flag(own: str, rust: str, flag: str, before: str | None) -> bool:
    """True when own (or a callee) returns Err on the copy-in-progress flag."""
    if not own.strip():
        return False
    head = own
    if before:
        pos = own.find(before)
        if pos >= 0:
            head = own[:pos]
    surf = head + "\n" + _callees_of(rust, head)
    if not re.search(rf"\b{re.escape(flag)}\b", surf):
        return False
    win = _windows_around(
        surf, re.compile(rf"\b{re.escape(flag)}\b"), before=80, after=200
    )
    return bool(_RETURN_ERR.search(win) or _RETURN_ERR.search(surf))


def _flag_cleared_on_exit(own: str, rust: str, flag: str) -> bool:
    """True when the bit is cleared on every exit (Drop, or Err + ok)."""
    i = 0
    n = len(rust)
    while i < n:
        m = _DROP_FOR.search(rust[i:])
        if not m:
            break
        typ = m.group(1)
        start = i + m.end()
        brace = rust.find("{", start)
        if brace < 0:
            break
        blob = _without_comments(_brace_after(rust, brace))
        i = brace + 1
        if not _FLAG_CLEAR.search(blob):
            continue
        if re.search(rf"\b{re.escape(flag)}\b", blob):
            return True
        if re.search(r"copy|guard", typ, re.I):
            return True
    own_c = _without_comments(own)
    if not _FLAG_CLEAR.search(own_c):
        helpers = _callees_of(rust, own_c)
        help_c = _without_comments(helpers)
        if (
            re.search(rf"\b{re.escape(flag)}\b", help_c)
            and _FLAG_CLEAR.search(help_c)
            and _ERR_WRAP.search(own_c)
        ):
            return True
        return False
    # explicit clear must not be success-only after `copy_backup_unit(...)?`
    if _ERR_WRAP.search(own_c) or re.search(r"if\s+let\s+Err", own_c):
        return True
    return False


def _rollback_surface(rust: str, own: str) -> str:
    """Named dest-rollback / Drop / Err-arm that removes what copy wrote."""
    parts: list[str] = []
    for m in _ROLLBACK_FN.finditer(rust):
        inner = _rust_function_body(rust, m.group(1))
        if inner:
            parts.append(inner)
    for body in _drop_bodies(rust):
        if not (_REMOVE_FILE.search(body) or _REMOVE_DIR_ALL.search(body)):
            continue
        if _TOML.search(body) or _SQLITE.search(body) or _SHM.search(body):
            parts.append(body)
    for blob in (own, _rust_function_body(rust, "copy_backup_unit")):
        for wm in _ERR_WRAP.finditer(blob):
            win = blob[wm.start() : wm.start() + 900]
            if _REMOVE_FILE.search(win) or _REMOVE_DIR_ALL.search(win):
                parts.append(win)
    # callee named rollback called from own / copy_backup_unit
    walk = own + "\n" + _rust_function_body(rust, "copy_backup_unit")
    for m in re.finditer(
        r"\b([A-Za-z_][A-Za-z0-9_]*(?:rollback|revert|cleanup|wipe|undo)\w*)\s*\(",
        walk,
        re.I,
    ):
        inner = _rust_function_body(rust, m.group(1))
        if inner and inner not in parts:
            parts.append(inner)
    return "\n".join(parts)


def _rolls_back_dest(surf: str) -> bool:
    """True when dest toml / sqlite+wal+shm / cas/ / logs/ are removed."""
    if not surf.strip():
        return False
    if not _REMOVE_FILE.search(surf) and not _REMOVE_DIR_ALL.search(surf):
        return False
    if not _TOML.search(surf):
        return False
    if not _SQLITE.search(surf):
        return False
    if not _WAL.search(surf):
        return False
    if not _SHM.search(surf):
        return False
    if not _CAS_DIR.search(surf):
        return False
    if not _LOGS_DIR.search(surf):
        return False
    if not _REMOVE_DIR_ALL.search(surf):
        return False
    shm_win = _windows_around(surf, _SHM, before=120, after=80)
    if not _REMOVE_FILE.search(shm_win) and not _DEST_SHM_IDENT.search(shm_win):
        return False
    return True


def _before_picker(own: str) -> str:
    """Own-body prefix before the first dest picker call."""
    m = _PICK_DEST.search(own)
    if not m:
        return own
    return own[: m.start()]


def _archive_drop_pos(own: str) -> int:
    """Index of first `state.archive = None` / archive.take() in own, else -1."""
    m = _ARCHIVE_DROP.search(own)
    return m.start() if m else -1


def _looks_like_flag_refuse(win: str, flag: str) -> bool:
    """True when a window tests the bit and returns a calm copy-in-progress Err."""
    if not _COPY_IN_PROGRESS_ERR.search(win):
        return False
    if not _RETURN_ERR.search(win):
        return False
    return bool(
        re.search(
            rf"if\s+\*?\s*(?:state\s*\.\s*)?{re.escape(flag)}\b",
            win,
        )
        or _CAS_SET.search(win)
        or _SWAP_TRUE.search(win)
        or re.search(r"if\s+\*\s*\w+", win)
    )


def _has_copying_refuse(own_or_head: str, rust: str, flag: str) -> bool:
    """True when own/head (or one callee hop) refuses an already-true flag."""
    if not own_or_head.strip():
        return False
    surf = own_or_head + "\n" + _callees_of(rust, own_or_head)
    surf_c = _without_comments(surf)
    if re.search(rf"\b{re.escape(flag)}\b", surf_c):
        win = _windows_around(
            surf_c, re.compile(rf"\b{re.escape(flag)}\b"), before=100, after=240
        )
        if _looks_like_flag_refuse(win, flag):
            return True
    for name in re.findall(
        r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", _without_comments(own_or_head)
    ):
        inner = _without_comments(_rust_function_body(rust, name))
        if not inner.strip():
            continue
        if not _COPY_IN_PROGRESS_ERR.search(inner) or not _RETURN_ERR.search(inner):
            continue
        if (
            re.search(
                rf"if\s+\*?\s*(?:state\s*\.\s*)?{re.escape(flag)}\b",
                inner,
            )
            or re.search(r"if\s+\*\s*\w+", inner)
            or _CAS_SET.search(inner)
            or _SWAP_TRUE.search(inner)
        ):
            return True
    return False


def _refuses_copying_before_archive_drop(own: str, rust: str, flag: str) -> bool:
    """True when the flag is refused before the first archive drop (or at all)."""
    drop_at = _archive_drop_pos(own)
    head = own if drop_at < 0 else own[:drop_at]
    return _has_copying_refuse(head, rust, flag)


def _bare_lock_assign_true(src: str, flag: str) -> bool:
    """True when the bit is set with `*state.copying.lock()… = true` (no CAS)."""
    return bool(
        re.search(
            rf"\*\s*(?:state\s*\.\s*)?{re.escape(flag)}\s*\.\s*lock\s*\("
            rf"[^;]{{0,200}}=\s*true",
            src,
        )
        or re.search(
            rf"\b(?:state\s*\.\s*)?{re.escape(flag)}\s*\.\s*store\s*\(\s*true",
            src,
        )
    )


def _sets_bit_with_cas(own: str, rust: str, flag: str) -> bool:
    """True when the walk claims the bit via CAS / same-lock already-true refuse."""
    after = _without_comments(_after_picker_surface(rust, own))
    walk = after + "\n" + _without_comments(_rust_function_body(rust, "copy_backup_unit"))
    blob = walk + "\n" + _without_comments(_callees_of(rust, walk))
    if _bare_lock_assign_true(blob, flag):
        return False
    if _CAS_SET.search(blob):
        win = _windows_around(blob, _CAS_SET, before=160, after=220)
        if _COPY_IN_PROGRESS_ERR.search(win) or (
            _RETURN_ERR.search(win) and re.search(rf"\b{re.escape(flag)}\b", win)
        ):
            return True
    if _SWAP_TRUE.search(blob):
        win = _windows_around(blob, _SWAP_TRUE, before=80, after=240)
        if _COPY_IN_PROGRESS_ERR.search(win) or (
            re.search(r"\bif\s+", win) and _RETURN_ERR.search(win)
        ):
            return True
    for m in re.finditer(
        r"let\s+(?:mut\s+)?(\w+)\s*=\s*[^;]{0,200}lock\s*\(",
        blob,
    ):
        ident = m.group(1)
        lock_expr = m.group(0)
        if not (
            re.search(rf"\b{re.escape(flag)}\b", lock_expr)
            or _CLAIM_IDENT.search(lock_expr)
        ):
            continue
        after_let = blob[m.end() : m.end() + 500]
        if not re.search(rf"if\s+\*\s*{re.escape(ident)}\b", after_let):
            continue
        if not (
            _COPY_IN_PROGRESS_ERR.search(after_let)
            or _RETURN_ERR.search(after_let[:300])
        ):
            continue
        if not re.search(rf"\*\s*{re.escape(ident)}\s*=\s*true", after_let):
            continue
        return True
    return False


def _non_owner_clears_flag(own: str, rust: str, flag: str) -> bool:
    """True when own / a non-Drop callee assigns the bit false (only Drop may)."""
    own_c = _without_comments(own)
    clear_rx = re.compile(
        rf"\b{re.escape(flag)}\b[^\n]{{0,100}}"
        rf"(?:=\s*false|\.store\s*\(\s*false)"
    )
    if clear_rx.search(own_c):
        return True
    helpers = _without_comments(_callees_of(rust, own_c))
    return bool(clear_rx.search(helpers))


_IMPORT_TAKE = re.compile(r"\b(?:slot\s*\.\s*)?take\s*\(")
_SLOW_BEFORE_TAKE = re.compile(
    r"\b(?:plan_import|list_whatsapp_zips|ImporterRegistry\s*::\s*detect)\s*\("
)
_OPENPATH_DOCTOR_CLEAR = re.compile(r"\bdoctor\s*=\s*\[\s*\]")
_IMMEDIATE_TAKE_CHARS = 480


def _last_take_pos(own: str) -> int:
    """Index of last slot.take() / .take( in own, else -1."""
    last = -1
    for m in _IMPORT_TAKE.finditer(own):
        last = m.start()
    return last


def _take_host_body(own: str, rust: str) -> str:
    """Own body, or the callee that actually take()s Archive."""
    if _last_take_pos(_without_comments(own)) >= 0:
        return own
    for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", own):
        inner = _rust_function_body(rust, name)
        if inner and _last_take_pos(_without_comments(inner)) >= 0:
            return inner
    return own


def _window_immediately_before_take(own: str) -> str:
    """Suffix immediately before take() — after plan_import, not the fn head."""
    own_c = _without_comments(own)
    take_at = _last_take_pos(own_c)
    if take_at < 0:
        return ""
    start = max(0, take_at - _IMMEDIATE_TAKE_CHARS)
    last_slow = -1
    for m in _SLOW_BEFORE_TAKE.finditer(own_c[:take_at]):
        last_slow = m.end()
    if last_slow >= start:
        start = last_slow
    return own_c[start:take_at]


def _refuses_copying_immediately_before_take(
    own: str, rust: str, flag: str
) -> bool:
    """True when a copying refuse sits immediately before take() / slot.take()."""
    host = _take_host_body(own, rust)
    window = _window_immediately_before_take(host)
    if not window.strip():
        return False
    return _has_copying_refuse(window, rust, flag)


def _openpath_clears_doctor(body: str) -> bool:
    """True when openPath assigns doctor = [] (setup / leave-archive stay ok)."""
    return bool(_OPENPATH_DOCTOR_CLEAR.search(_without_comments(body)))


def assert_copy_archive_to(crate: Path) -> None:
    """#320: Copy archive to… — rfd dest in Rust, backup-unit copy.

    Doctor Backup owned Button next to Reveal + File menu. Same command.
    No webview path. Keep Reveal / import cancel / File Open+Import.
    File → Open dest must not unmount Doctor; dest shm is dropped after copy.
    After dest picker: re-read import/root, copy-in-progress bit, dest rollback.
    open / init refuse copying before dropping archive; second walk CAS.
    import_start re-checks copying immediately before take(); openPath
    does not wipe doctor.
    """
    doctor_path = crate / "web" / "lib" / "DoctorPane.svelte"
    if not doctor_path.is_file():
        fail(f"{_ISSUE}: DoctorPane.svelte required (Backup Copy archive to…)")
    doctor = doctor_path.read_text()
    section = _doctor_backup_section(doctor)

    # 1) copy-doctor-control — primary red today: no Copy next to Reveal.
    if not _copy_control_hit(section):
        fail(
            f"{_ISSUE}: Doctor Backup section must have a Copy archive to… "
            f'control (t("{_KEY}") / {_HOOK}) next to Reveal'
        )
    if _HOOK not in section:
        fail(
            f"{_ISSUE}: Doctor Backup Copy archive to… must set {_HOOK} "
            "(owned Button next to Reveal)"
        )
    if not _T_COPY.search(section):
        fail(
            f'{_ISSUE}: Doctor Backup Copy label must be t("{_KEY}") '
            f'("{_LABEL}")'
        )
    if "data-reveal-archive" not in section and not re.search(
        r"revealInFinder|Reveal archive", section
    ):
        fail(
            f"{_ISSUE}: keep Reveal on Doctor Backup "
            "(Copy archive to… sits next to it — do not drop #274)"
        )
    tag = _owned_button_tag(doctor, section)
    if not tag.strip() or not _is_owned_button(doctor, tag):
        fail(
            f"{_ISSUE}: Copy archive to… must be an owned Button "
            "(import from $lib/components/ui/button) next to Reveal"
        )
    if _DISABLED_IMPORT.search(tag):
        fail(
            f"{_ISSUE}: Copy archive to… must stay clickable while import "
            "is running (do not copy Switch’s disable-and-swallow)"
        )

    api_path = crate / "web" / "lib" / "api.ts"
    api = _read(api_path)
    rust = _tauri_rust_blob(crate)
    rust_c = _without_comments(rust)
    web = _web_logic(crate)
    web_c = _without_comments(web + "\n" + doctor + "\n" + api)
    menu_rs = _read(crate / "src" / "menu.rs")
    main_rs = _read(crate / "src" / "main.rs")
    file_menu = _file_submenu(menu_rs) or _file_submenu(rust)
    handlers = _menu_handler_surface(rust, web)
    en_path = crate / "web" / "lib" / "locales" / "en.ts"
    tr_path = crate / "web" / "lib" / "locales" / "tr.ts"
    en = _chrome_pack_entries(_read(en_path)) if en_path.is_file() else {}
    tr = _chrome_pack_entries(_read(tr_path)) if tr_path.is_file() else {}
    toml = _read(crate / "Cargo.toml")
    pkg = _read(crate / "package.json")
    caps = _read(crate / "capabilities" / "default.json")
    ent = _read(crate / "Interlace.entitlements")
    conf = _read(crate / "tauri.conf.json")
    dtxt = _docs_blob()

    # 2) copy-cmd — copy_archive_to, not fn backup / reveal_archive / open_url.
    if _REVEAL_ARCHIVE_BACKUP_FN.search(rust_c):
        fail(
            f"{_ISSUE}: command is {_CMD} — never fn backup / backup_zip / "
            "zip_backup / icloud_backup / copy_cas (#274)"
        )
    if not re.search(rf"\bfn\s+{re.escape(_CMD)}\b", rust):
        fail(
            f"{_ISSUE}: Rust command {_CMD} required "
            "(not fn backup, not reveal_archive, not open_url)"
        )
    if not re.search(
        r"generate_handler!\s*\[[^\]]*\b" + re.escape(_CMD) + r"\b", rust, re.S
    ):
        fail(f"{_ISSUE}: register {_CMD} in generate_handler")
    if not re.search(rf"\b{re.escape(_API)}\b", api) and not re.search(
        r"invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']" + re.escape(_CMD) + r"[\"']",
        api,
    ):
        fail(
            f"{_ISSUE}: frontend api.{_API}() required "
            f'(invoke("{_CMD}") — no path args)'
        )
    api_args = _api_copy_args(api)
    if _CLIENT_ARG.search(api_args):
        fail(
            f"{_ISSUE}: api.{_API}() must take no path / dest / source args "
            "(dest is rfd inside Rust)"
        )
    invoke_rx = re.compile(
        r"invoke\s*(?:<[^>]*>)?\s*\(\s*[\"']" + re.escape(_CMD) + r"[\"']"
    )
    for payload in _invoke_payloads(api + "\n" + web + "\n" + doctor, invoke_rx):
        if _payload_has_dest(payload):
            fail(
                f"{_ISSUE}: do not pass dest / path / source from the webview "
                f"to {_CMD} (rfd inside the command)"
            )
    if not _COPY_INVOKE.search(doctor) and not _COPY_INVOKE.search(web):
        fail(
            f"{_ISSUE}: Doctor Copy archive to… must call api.{_API}() / "
            f'invoke("{_CMD}")'
        )
    click = ""
    hm = _T_COPY.search(section) or re.search(re.escape(_HOOK), section)
    if hm:
        click = _onclick_before(section, hm.start())
    click_exp = _expand_fn_calls(doctor, click, 2) if click.strip() else ""
    handler = click + "\n" + click_exp
    for name in (_API, "copyArchive", "onCopyArchive", "handleCopyArchive"):
        handler += "\n" + _fn(doctor, name)
    if not _COPY_INVOKE.search(handler) and not _COPY_INVOKE.search(doctor):
        fail(
            f"{_ISSUE}: Doctor Copy click must invoke {_CMD} "
            f"(api.{_API}() — no path args)"
        )
    if _ASK.search(handler):
        fail(
            f"{_ISSUE}: no extra ConfirmDialog for Copy archive to… "
            "(picker cancel is quiet)"
        )

    # 3) copy-source-archive-root / copy-no-client-source.
    sig = _rust_fn_signature(rust, _CMD)
    own = _rust_function_body(rust, _CMD)
    body = _rust_body_with_callees(rust, _CMD)
    if not own.strip() and not body.strip():
        fail(
            f"{_ISSUE}: {_CMD} must read archive_root and copy that folder "
            "(fn taking no webview path)"
        )
    if not re.search(r"\barchive_root\b", body):
        fail(
            f"{_ISSUE}: {_CMD} must read archive_root from app state "
            "(do not take st.path from the webview)"
        )
    if _PATH_ARG.search(sig):
        fail(
            f"{_ISSUE}: {_CMD} must not take dest / path / source from the "
            "webview — dest is rfd inside this command"
        )
    if _CMD in _BANNED_CMDS:
        fail(f"{_ISSUE}: {_CMD} must not reuse reveal_archive / open_url / pick_folder")

    # 4) copy-dest-rfd — dest picker inside the command, not Open’s title.
    if not _RFD.search(own) and not _RFD.search(body):
        fail(
            f"{_ISSUE}: {_CMD} must pick dest with rfd inside Rust "
            "(not a webview path, not pick_folder then dest)"
        )
    if not _MAIN_THREAD.search(own) and not _MAIN_THREAD.search(body):
        fail(
            f"{_ISSUE}: dest rfd must run on the main thread "
            "(run_on_main_thread, like pick_folder)"
        )
    if _OPEN_PICK_TITLE.search(own) or _OPEN_PICK_TITLE.search(body):
        fail(
            f"{_ISSUE}: dest picker title must not be \"{_OPEN_TITLE}\" "
            "(that title is File → Open archive)"
        )
    if _PICK_FOLDER_CMD.search(own):
        fail(
            f"{_ISSUE}: do not call pick_folder for dest "
            "(Open’s picker returns a path to the webview)"
        )

    # 5) copy-refuse-url.
    if not _HTTP_DEST.search(own) and not _REFUSE_URL.search(own) and not (
        _HTTP_DEST.search(body) or _REFUSE_URL.search(body)
    ):
        fail(
            f"{_ISSUE}: {_CMD} must refuse http(s) / URL dest "
            "(local folder only)"
        )
    if re.search(r"[\"']https?://", own) and not re.search(
        r"starts_with|refuse|Err", own
    ):
        fail(f"{_ISSUE}: {_CMD} must not open http(s) — dest is a local folder")

    # 6) copy-empty-dest / dest == open root or inside it.
    if not _EMPTY_DEST.search(own) and not _EMPTY_DEST.search(body):
        fail(
            f"{_ISSUE}: {_CMD} must refuse a non-empty dest "
            "(empty folder is the archive root that Opens)"
        )
    if not _INSIDE_SRC.search(own) and not _INSIDE_SRC.search(body):
        fail(
            f"{_ISSUE}: {_CMD} must refuse dest == the open root or a "
            "subfolder of it"
        )

    # 7) copy-refuse-import — still clickable; command refuses.
    if not _IMPORT_RUN.search(own) and not _IMPORT_RUN.search(body):
        fail(
            f"{_ISSUE}: {_CMD} must refuse when import status is running "
            '(calm Err — same spirit as close_archive "import running")'
        )

    # 8) copy-sqlite-wal / copy-skip-tmp-spill / logs included.
    walker = own + "\n" + body
    if not _TOML.search(walker):
        fail(f"{_ISSUE}: {_CMD} must copy INTERLACE.toml")
    if not _SQLITE.search(walker):
        fail(f"{_ISSUE}: {_CMD} must copy archive.sqlite")
    if not _WAL.search(walker) or not _SHM.search(walker):
        fail(
            f"{_ISSUE}: {_CMD} must copy archive.sqlite-wal and "
            "archive.sqlite-shm as files (do not invent a closed-writer "
            "checkpoint)"
        )
    if not _CAS_DIR.search(walker):
        fail(f"{_ISSUE}: {_CMD} must copy cas/")
    if not _LOGS_DIR.search(walker):
        fail(f"{_ISSUE}: {_CMD} must copy logs/ (confirmed include)")
    if not _skip_tmp_spill(walker):
        fail(
            f"{_ISSUE}: {_CMD} must skip tmp/ and imports/*/spill"
        )
    if _VACUUM.search(walker):
        fail(
            f"{_ISSUE}: copy sqlite+wal+shm as files "
            "(not VACUUM INTO / rusqlite Online Backup)"
        )
    if _CLOSE_DURING.search(own):
        fail(
            f"{_ISSUE}: copy while this app keeps exclusive flock "
            "(do not close_archive / drop archive_root)"
        )
    if _STEAL_LAST.search(own):
        fail(
            f"{_ISSUE}: do not steal last_archive / persist_bookmark "
            "onto dest (user Opens the copy later)"
        )
    if _AUTO_OPEN.search(own):
        fail(
            f"{_ISSUE}: do not auto-open dest "
            "(that folder Opens later via File → Open archive)"
        )
    if _CLOUD_ERR.search(walker):
        fail(
            f"{_ISSUE}: iCloud/Dropbox dest: warn like Open, still copy "
            "if dest is empty (not a zip-to-iCloud refuse)"
        )
    if _ERR_PATH.search(own) or _ERR_PATH.search(body):
        fail(
            f"{_ISSUE}: rust errors must not embed the dest path "
            "(chrome-only toast / banner)"
        )

    # 9) copy-file-menu — English native label, same command, no path.
    menu_src = menu_rs + "\n" + rust
    if not _FILE_SUBMENU.search(menu_src):
        fail(f"{_ISSUE}: File submenu required (Copy archive to… lives there)")
    if not _MENU_LABEL.search(file_menu) and not _MENU_LABEL.search(menu_src):
        fail(
            f"{_ISSUE}: File menu must list {_LABEL} "
            "(English native label, like Open / Switch)"
        )
    if not _MENU_ID.search(menu_src) and not _MENU_EVENT.search(menu_src):
        fail(
            f"{_ISSUE}: File → {_LABEL} must have a menu id "
            "(copy-archive-to; not open-archive)"
        )
    if _copy_menu_enabled_swallows(file_menu, rust):
        fail(
            f"{_ISSUE}: File → {_LABEL} must stay clickable while import "
            "is running (command refuses; do not disable-and-swallow)"
        )
    menu_wired = bool(
        _COPY_INVOKE.search(handlers)
        or _MENU_EVENT.search(web)
        or re.search(rf"\b{re.escape(_CMD)}\b", handlers)
        or _COPY_INVOKE.search(web)
    )
    if not menu_wired:
        fail(
            f"{_ISSUE}: File → {_LABEL} must invoke {_CMD} "
            f"(emit + api.{_API}() or call the command — no path args)"
        )
    for payload in _invoke_payloads(handlers + "\n" + web, invoke_rx):
        if _payload_has_dest(payload):
            fail(
                f"{_ISSUE}: File menu must invoke {_CMD} with no dest / path "
                "(rfd inside Rust)"
            )

    # 10) import-refuse-surface + success toast (chrome-only, no dest path).
    surf = doctor + "\n" + handler + "\n" + web
    if not _TOAST_CALL.search(surf) and "onError" not in handler:
        fail(
            f"{_ISSUE}: import-running refuse must be a calm visible error "
            "(toast / banner) — control stays clickable"
        )
    toast_win = _windows_around(web_c + "\n" + doctor, _TOAST_CALL, before=40, after=120)
    copy_toast = ""
    if _COPY_INVOKE.search(handler) or _COPY_INVOKE.search(doctor):
        copy_toast = _windows_around(
            handler + "\n" + doctor, _TOAST_CALL, before=40, after=120
        )
    leak_src = copy_toast or toast_win
    if _COPY_INVOKE.search(handler + "\n" + doctor) and _TOAST_LEAK.search(leak_src):
        fail(
            f"{_ISSUE}: copy toasts are chrome-only "
            f'("{_SUCCESS}" / import-running — no dest path)'
        )
    if not _uses_phrase(doctor + "\n" + web, en, _SUCCESS) and _SUCCESS not in en.values():
        fail(
            f'{_ISSUE}: success toast must be chrome-only "{_SUCCESS}" '
            "(no dest path, no hash)"
        )
    if _SUCCESS not in en.values() and not _uses_phrase(doctor + "\n" + web, en, _SUCCESS):
        fail(f'{_ISSUE}: en pack must include "{_SUCCESS}" (chrome toast)')

    # 11) copy-keys-en-tr — same ChromeKeys; copyArchiveTo + success + import err.
    if _KEY not in en or _KEY not in tr:
        fail(
            f'{_ISSUE}: t("{_KEY}") must exist on both en.ts and tr.ts '
            "(same ChromeKey — #278)"
        )
    if en.get(_KEY, "").strip() not in {_LABEL, "Copy archive to..."}:
        fail(f'{_ISSUE}: en {_KEY} must be "{_LABEL}"')
    if _SUCCESS not in en.values():
        fail(f'{_ISSUE}: en must have a ChromeKey whose value is "{_SUCCESS}"')
    success_keys = [k for k, v in en.items() if v == _SUCCESS]
    if success_keys and any(k not in tr for k in success_keys):
        fail(
            f"{_ISSUE}: success toast key must exist on both en and tr packs"
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

    # 12) keep-274-reveal.
    if not re.search(r"\bfn\s+reveal_archive\b", rust):
        fail(f"{_ISSUE}: keep reveal_archive (argument-free) — do not soften #274")
    arch_sig = _rust_fn_signature(rust, "reveal_archive")
    arch_own = _rust_function_body(rust, "reveal_archive")
    if re.search(r"\b(?:path|url|file|href|uri|hash)\s*:", arch_sig, re.I):
        fail(
            f"{_ISSUE}: reveal_archive must stay argument-free "
            "(root from app state — do not soften #274)"
        )
    if not re.search(r"[\"']-R[\"']", arch_own):
        fail(f"{_ISSUE}: keep reveal_archive /usr/bin/open -R")
    if not re.search(
        r"generate_handler!\s*\[[^\]]*\breveal_archive\b", rust, re.S
    ):
        fail(f"{_ISSUE}: keep reveal_archive in generate_handler")
    if "data-reveal-archive" not in doctor:
        fail(f"{_ISSUE}: keep Doctor data-reveal-archive (#274)")

    # 13) keep-266-cancel — refuse running import; do not kill the thread.
    if not re.search(r"\bimport_cancel\b|\bimportCancel\b", rust_c):
        fail(f"{_ISSUE}: keep import_cancel (#266)")
    if not re.search(r"\bimport_cancel\b|\bimportCancel\b", api):
        fail(f"{_ISSUE}: keep api.importCancel (#266)")
    if _JOIN_ABORT.search(rust_c) or _JOIN_ABORT.search(own):
        fail(
            f"{_ISSUE}: no JoinHandle abort / thread::kill "
            "(refuse import running; cooperative Cancel stays #266)"
        )

    # 14) keep-130-file — Open + Import + Switch stay; no updater / iCloud menu.
    if not _OPEN_ITEM.search(menu_src):
        fail(f"{_ISSUE}: keep File → Open archive (#130)")
    if not _IMPORT_ITEM.search(menu_src):
        fail(f"{_ISSUE}: keep File → Import (#130)")
    if not re.search(r"[\"']Switch archive[\"']", menu_src):
        fail(f"{_ISSUE}: keep File → Switch archive (#308 / #130 family)")
    if _CHECK_UPDATES_ITEM.search(menu_src) or _PREFERENCES_ITEM.search(menu_src):
        fail(f"{_ISSUE}: no Check for Updates / Preferences (#130)")
    if _ICLOUD_MENU_ITEM.search(menu_src):
        fail(f"{_ISSUE}: no iCloud File menu item (not zip-to-iCloud)")

    # 15) bans — plugin-shell / opener / HTTP / zip-to-iCloud / encrypt / CSP.
    if _PLUGIN_SHELL.search(toml) or _PLUGIN_SHELL.search(pkg):
        fail(
            f"{_ISSUE}: do not add tauri-plugin-shell / tauri-plugin-opener"
        )
    if _PLUGIN_SHELL.search(rust_c) or _PLUGIN_SHELL.search(web_c):
        fail(
            f"{_ISSUE}: do not add tauri-plugin-shell / tauri-plugin-opener"
        )
    if _SHELL_CAP.search(caps):
        fail(
            f"{_ISSUE}: capabilities must not add shell:allow-execute / "
            "shell:allow-open / opener"
        )
    if _FETCH_CALL.search(own) or _LINKIFY_FETCH.search(own):
        fail(f'{_ISSUE}: no fetch("http — copy is a local folder copy')
    if _HTTP_CLIENT.search(toml) or _HTTP_CLIENT.search(own) or _HTTP_CLIENT.search(body):
        fail(f"{_ISSUE}: no HTTP client / tauri-plugin-http")
    if "network.server" in ent:
        fail(f"{_ISSUE}: entitlements must omit network.server")
    if CSP not in conf:
        fail(f"{_ISSUE}: do not soften tauri CSP")
    if _REVEAL_ARCHIVE_ZIP_ICLOUD.search(doctor + "\n" + rust + "\n" + dtxt):
        fail(f"{_ISSUE}: no zip-to-iCloud backup command")
    product_claim = "\n".join((doctor, rust, dtxt, handler))
    if _claim_without_negation(product_claim, _REVEAL_ARCHIVE_ENCRYPT):
        fail(
            f"{_ISSUE}: no “database is encrypted” / SQLCipher claim "
            "(folder is the backup unit; FileVault)"
        )
    if _ARBITRARY_SHELL.search(own) or _ARBITRARY_SHELL.search(body):
        fail(
            f"{_ISSUE}: no shell of arbitrary commands — dest is rfd + std::fs"
        )
    if _REAL_HOME.search(own + "\n" + doctor):
        fail(f"{_ISSUE}: tests stay placeholders (Ada) — no real home paths")

    # 16) copy-d24 — backup.md + app.md; keep Reveal + after-close cp.
    if not dtxt.strip():
        fail(
            f"{_ISSUE}: docs/user/backup.md and docs/user/app.md required — "
            "Copy archive to… while this app is the only writer; dest Opens; "
            "import running refuses; after-close cp still works; Reveal stays"
        )
    backup_docs = repo_root() / "docs" / "user" / "backup.md"
    app_docs = repo_root() / "docs" / "user" / "app.md"
    if not backup_docs.is_file() or not app_docs.is_file():
        fail(
            f"{_ISSUE}: D24 both docs/user/backup.md and docs/user/app.md"
        )
    if not _DOCS_COPY.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/backup.md + app.md must say "
            f"{_LABEL} (Doctor / File)"
        )
    if not _DOCS_WRITER.search(dtxt):
        fail(
            f"{_ISSUE}: docs must say Copy archive to… while this app is "
            "the only writer"
        )
    if not _DOCS_OPENS.search(dtxt):
        fail(
            f"{_ISSUE}: docs must say the dest folder Opens as an archive"
        )
    if not _DOCS_IMPORT.search(dtxt):
        fail(
            f"{_ISSUE}: docs must say import running refuses calmly"
        )
    copy_win = ""
    for m in _REVEAL_ARCHIVE_DOC_COPY.finditer(dtxt):
        i = m.start()
        copy_win += dtxt[max(0, i - 80) : m.end() + 160] + "\n"
    if not copy_win.strip() or not _DOCS_AFTER.search(copy_win + "\n" + dtxt):
        fail(
            f"{_ISSUE}: docs must keep after-close cp -a "
            "(backup is still copy that folder after closing the app — #274)"
        )
    doc_rev = ""
    for m in _REVEAL_ARCHIVE_DOC.finditer(dtxt):
        i = m.start()
        doc_rev += dtxt[max(0, i - 80) : m.end() + 200] + "\n"
    if not doc_rev.strip() or not re.search(r"\bDoctor\b", doc_rev):
        fail(
            f"{_ISSUE}: docs must keep Reveal archive from Doctor "
            "(do not drop #274)"
        )
    if not re.search(r"\bPeople\b", doc_rev):
        fail(
            f"{_ISSUE}: docs must keep Reveal archive from People "
            "(do not drop #274)"
        )

    # 17) copy-opening-overlay — File → Open dest must not unmount Doctor.
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail(
            f"{_ISSUE}: App.svelte required (opening must not unmount Doctor)"
        )
    app_src = app_path.read_text()
    if _opening_unmounts_main_panes(app_src):
        fail(
            f"{_ISSUE}: opening must not unmount Doctor / People / Search — "
            "{#if booting || opening} cannot be the exclusive parent of the "
            "main panes (overlay / sibling so File → Open dest does not remount Doctor)"
        )

    # 18) copy-dest-drop-shm — copy sqlite+wal+shm as files, then drop dest shm.
    if not _drops_dest_shm(walker):
        fail(
            f"{_ISSUE}: {_CMD} must remove_file / unlink dest "
            "archive.sqlite-shm after the file copy (copied shm is the live "
            "WAL-index; dest Open rebuilds a fresh one)"
        )

    # 19) keep-136-doctor-full — Doctor tab onMount / Refresh still full-scan.
    load_body = _fn(doctor, "load")
    if not re.search(r"onMount\s*\(", doctor):
        fail(
            f"{_ISSUE}: keep DoctorPane onMount → full doctorIssues "
            "(do not skip #136 to unstick Open dest)"
        )
    if not re.search(r"\b(?:api\.)?doctorIssues\s*\(", load_body or doctor):
        fail(
            f"{_ISSUE}: keep Doctor tab full doctorIssues "
            "(onMount / load — do not rewrite #136)"
        )
    if re.search(r"doctorIssuesQuick", load_body) and not re.search(
        r"\b(?:api\.)?doctorIssues\s*\(", load_body
    ):
        fail(
            f"{_ISSUE}: Doctor tab load must stay full doctorIssues "
            "(not doctorIssuesQuick only — keep #136)"
        )
    if not re.search(r"\bRefresh\b", doctor):
        fail(
            f"{_ISSUE}: keep Doctor Refresh (full doctorIssues — do not drop #136)"
        )
    if not re.search(r"onclick=\{[^}]*\bload\b", doctor):
        fail(
            f"{_ISSUE}: keep Doctor Refresh → load (full doctorIssues — #136)"
        )

    # 20) copy-recheck-after-picker — import running + archive_root after rfd.
    after_raw = _after_picker(own)
    after = _without_comments(_after_picker_surface(rust, own))
    if not after_raw.strip() or not after.strip():
        fail(
            f"{_ISSUE}: {_CMD} must re-read import running after the dest "
            "picker (pick_copy_dest / rfd) — File → Switch / Import during "
            "the picker is not frozen by the frontend await"
        )
    if not _IMPORT_RUN.search(after):
        fail(
            f"{_ISSUE}: {_CMD} must re-read import running after the dest "
            "picker (pick_copy_dest / rfd) — File → Switch / Import during "
            "the picker is not frozen by the frontend await"
        )
    if not _STATE_ROOT.search(after):
        fail(
            f"{_ISSUE}: {_CMD} must re-read archive_root after the dest "
            "picker (root gone or no longer the source being copied)"
        )
    if not _ROOT_GONE.search(after):
        fail(
            f"{_ISSUE}: {_CMD} must re-read archive_root after the dest "
            "picker and refuse if the root is gone (no archive open)"
        )
    after_no_dest = _DEST_VS_SRC.sub(" ", after)
    if not _ROOT_CHANGED.search(after_no_dest):
        fail(
            f"{_ISSUE}: {_CMD} must re-read archive_root after the dest "
            "picker and refuse if the root no longer matches the source "
            "being copied"
        )

    # 21) copy-in-progress — bit for the copy walk; close / import refuse it.
    flags = _copy_flag_names(rust_c)
    if not flags:
        fail(
            f"{_ISSUE}: set a copy-in-progress flag for the copy walk "
            "(close_archive / import_start must refuse it — same spirit as "
            "import running)"
        )
    flag = flags[0]
    if not _flag_set_for_walk(own, rust, flag):
        fail(
            f"{_ISSUE}: set a copy-in-progress flag for the copy walk "
            f"({flag} after the dest picker — picker cancel stays quiet)"
        )
    close_own = _rust_function_body(rust, "close_archive")
    if not _refuses_flag(close_own, rust, flag, "archive.lock"):
        fail(
            f"{_ISSUE}: close_archive must refuse the copy-in-progress flag "
            "(calm Err — same spirit as import running; do not drop flock "
            "mid-copy)"
        )
    import_own = _rust_function_body(rust, "import_start")
    if not _refuses_flag(import_own, rust, flag, ".take("):
        fail(
            f"{_ISSUE}: import_start must refuse the copy-in-progress flag "
            "(calm Err — same spirit as import already running; do not "
            "take() Archive mid-copy)"
        )
    if not _flag_cleared_on_exit(own, rust, flag):
        fail(
            f"{_ISSUE}: clear the copy-in-progress flag on the way out "
            "(ok / err / cancel after the bit was set — Drop or both paths)"
        )

    # 22) copy-dest-rollback — dest artifacts + dest shm on copy Err.
    rb = _without_comments(_rollback_surface(rust, own))
    if not _rolls_back_dest(rb):
        fail(
            f"{_ISSUE}: dest must be rolled back on copy Err — remove what "
            "the command wrote (INTERLACE.toml, archive.sqlite / -wal / "
            "-shm, cas/, logs/) via remove_file / remove_dir_all / unlink; "
            "drop dest archive.sqlite-shm on the failure path too"
        )

    # 23) copy-open-refuses — open (and init if it drops archive) before None.
    open_own = _rust_function_body(rust, "open")
    if not _refuses_copying_before_archive_drop(open_own, rust, flag):
        fail(
            f"{_ISSUE}: open must refuse the copy-in-progress flag with a "
            "calm Err before state.archive is set to None (File → Open / "
            "Recent stay enabled during the walk)"
        )
    init_own = _rust_function_body(rust, "init")
    if _archive_drop_pos(init_own) >= 0 and not _refuses_copying_before_archive_drop(
        init_own, rust, flag
    ):
        fail(
            f"{_ISSUE}: init must refuse the copy-in-progress flag with a "
            "calm Err before state.archive is set to None"
        )

    # 24) copy-second-walk-cas — already-true refuse + CAS; only owner Drop.
    before = _before_picker(own)
    if not _has_copying_refuse(before, rust, flag):
        fail(
            f"{_ISSUE}: copy_archive_to must refuse if the copy-in-progress "
            "flag is already true (pre-picker — a second walk must not start)"
        )
    if not _has_copying_refuse(_after_picker_surface(rust, own), rust, flag):
        fail(
            f"{_ISSUE}: copy_archive_to must refuse if the copy-in-progress "
            "flag is already true after the dest re-check (two overlapping "
            "pickers)"
        )
    if not _sets_bit_with_cas(own, rust, flag):
        fail(
            f"{_ISSUE}: copy_archive_to must set the copy-in-progress bit "
            "with a compare-and-swap / already-true refuse — not a bare "
            "= true (only the owner Drop may clear it)"
        )
    if _non_owner_clears_flag(own, rust, flag):
        fail(
            f"{_ISSUE}: only the owner Drop may clear the copy-in-progress "
            "bit (a second walk must not see the first Drop reset it)"
        )

    # 25) copy-import-recheck-take — refuse copying immediately before take().
    # Check 21 only requires a refuse somewhere before .take( — top-of-fn
    # then plan_import then take() still passes. This lock requires the
    # refuse in the same region as take() (after plan_import / detect).
    import_own = _rust_function_body(rust, "import_start")
    if not _refuses_copying_immediately_before_take(import_own, rust, flag):
        fail(
            f"{_ISSUE}: import_start must refuse the copy-in-progress flag "
            "immediately before take() (a top-of-function check only is not "
            "enough — re-check after plan_import / before slot.take())"
        )

    # 26) copy-openpath-keep-doctor — dest Open must not wipe Doctor.
    open_path = _fn(app_src, "openPath")
    if not open_path.strip():
        fail(
            f"{_ISSUE}: openPath required (must not assign doctor = [] "
            "before api.open — dest Open keeps the previous scan)"
        )
    if _openpath_clears_doctor(open_path):
        fail(
            f"{_ISSUE}: openPath must not assign doctor = [] "
            "(dest Open keeps the previous scan; clear doctor only when "
            "leaving the archive / setup)"
        )
