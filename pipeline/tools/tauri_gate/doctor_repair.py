"""#431 — Doctor repair plan and apply. Missing control fails closed."""

from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.scan_parse import _match_closer
from tauri_gate.scan_parse_rest import _ts_function_body
from tauri_gate.voice_transcript import _mount_path, _text, _uses_t

_EXACT = {
    "en": {
        "doctorRepair": "Repair",
        "doctorRepairApply": "Apply repairs",
        "doctorRepairTitle": "Apply these repairs?",
        "doctorRepairBody": (
            "Rebuilds search, reattaches matching files, and reclaims orphan files. "
            "Nothing else is changed."
        ),
        "doctorRepairDone": "Repairs applied.",
        "doctorRepairRebuild": "Rebuild search",
        "doctorRepairReattach": "Reattach {hash}",
        "doctorRepairReclaim": "Reclaim {hash}",
    },
    "tr": {
        "doctorRepair": "Onar",
        "doctorRepairApply": "Onarımları uygula",
        "doctorRepairTitle": "Bu onarımlar uygulansın mı?",
        "doctorRepairBody": (
            "Aramayı yeniden kurar, eşleşen dosyaları yeniden bağlar ve sahipsiz dosyaları geri alır. "
            "Başka bir şey değişmez."
        ),
        "doctorRepairDone": "Onarımlar uygulandı.",
        "doctorRepairRebuild": "Aramayı yeniden kur",
        "doctorRepairReattach": "Yeniden bağla {hash}",
        "doctorRepairReclaim": "Geri al {hash}",
    },
}

# DOC-USER-DOC. Missing text fails closed; it is not a skip.
_DOCTOR_USER_LINES = (
    "Repair lists rebuild search, reattach, and reclaim. It does not change the archive.",
    "Apply runs that list once. It refuses when a listed repair is no longer in its before-state or after-state.",
    "`--rebuild-fts` and `--gc-cas` still write immediately.",
)

_SKIP_CALLS = {
    "if",
    "for",
    "while",
    "switch",
    "catch",
    "return",
    "function",
    "await",
    "async",
    "new",
    "typeof",
    "of",
}


def _marker(src: str, token: str) -> re.Match[str] | None:
    return re.search(rf"(?<![\w-]){re.escape(token)}(?![\w-])", src)


def _element(src: str, token: str) -> str:
    match = _marker(src, token)
    if not match:
        return ""
    start = src.rfind("<", 0, match.start())
    if start < 0:
        start = match.start()
    close = src.find("</", match.end())
    if close < 0:
        close = min(len(src), match.end() + 500)
    return src[start:close]


def _attr_expr(src: str, attr_at: int) -> str:
    open_b = src.find("{", attr_at)
    if open_b < 0:
        return ""
    close_b = _match_closer(src, open_b)
    if close_b < 0:
        return src[open_b + 1 :]
    return src[open_b + 1 : close_b].strip()


def _called_names(body: str) -> list[str]:
    return [
        name
        for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", body)
        if name not in _SKIP_CALLS
    ]


def _expand_calls(src: str, body: str, depth: int) -> str:
    seen: set[str] = set()
    parts = [body]
    frontier = _called_names(body)
    for _ in range(depth):
        nxt: list[str] = []
        for name in frontier:
            if name in seen:
                continue
            seen.add(name)
            sub = _ts_function_body(src, name)
            if not sub:
                continue
            parts.append(sub)
            nxt.extend(_called_names(sub))
        frontier = nxt
    return "\n".join(parts)


def _handler_text(src: str, token: str) -> str:
    match = _marker(src, token)
    if not match:
        return ""
    start = src.rfind("<", 0, match.start())
    if start < 0:
        start = match.start()
    close = src.find("</", match.end())
    window = src[start : close if close >= 0 else match.end() + 800]
    click = re.search(r"onclick\s*=\s*\{", window)
    if not click:
        return window
    expr = _attr_expr(window, click.start())
    bare = re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", expr)
    if bare:
        return _expand_calls(src, _ts_function_body(src, expr) or expr, 4)
    named = re.search(
        r"(?:async\s*)?\(\s*\)\s*=>\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        expr,
    )
    if named and "{" not in expr:
        body = _ts_function_body(src, named.group(1)) or ""
        return _expand_calls(src, body + "\n" + expr, 4)
    return _expand_calls(src, expr, 4)


def _if_blocks(body: str) -> list[str]:
    blocks: list[str] = []
    for match in re.finditer(r"\bif\s*\(", body):
        cond_close = _match_closer(body, match.end() - 1)
        if cond_close < 0:
            continue
        i = cond_close + 1
        while i < len(body) and body[i] in " \t\n":
            i += 1
        if i < len(body) and body[i] == "{":
            end = _match_closer(body, i)
            blocks.append(body[i + 1 : end] if end >= 0 else body[i + 1 :])
            continue
        j = i
        while j < len(body) and body[j] not in ";\n":
            j += 1
        blocks.append(body[i:j])
    return blocks


def _onconfirm_expr(src: str) -> str:
    match = re.search(r"onconfirm\s*=\s*\{", src)
    if not match:
        return ""
    return _attr_expr(src, match.start())


def _confirm_bodies(src: str) -> list[str]:
    expr = _onconfirm_expr(src)
    if not expr:
        return []
    bodies: list[str] = []
    for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", expr):
        if name in {"true", "false", "null", "undefined", "async"}:
            continue
        body = _ts_function_body(src, name)
        if body:
            bodies.append(body)
    return bodies or [expr]


def _repair_arm(src: str, body: str) -> str:
    hits = [
        _expand_calls(src, block, 4)
        for block in _if_blocks(body)
        if re.search(r"\bdoctorApply\b", _expand_calls(src, block, 4))
    ]
    if hits:
        return "\n".join(hits)
    return _expand_calls(src, body, 4)


def _each_issues(src: str) -> str:
    match = re.search(r"\{#each\s+issues\b", src)
    if not match:
        return ""
    rest = src[match.start() :]
    depth = 0
    i = 0
    while i < len(rest):
        if rest.startswith("{#each", i):
            depth += 1
            i += 6
            continue
        if rest.startswith("{/each}", i):
            depth -= 1
            i += 7
            if depth == 0:
                return rest[:i]
            continue
        i += 1
    return rest


def _tag_block(src: str, token: str) -> str:
    match = _marker(src, token)
    if not match:
        return ""
    start = src.rfind("<", 0, match.start())
    tag_m = re.match(r"<([A-Za-z][\w:-]*)\b", src[start:])
    if not tag_m:
        return ""
    tag = tag_m.group(1)
    open_token = f"<{tag}"
    close_token = f"</{tag}"
    depth = 0
    i = start
    while i < len(src):
        if src.startswith(open_token, i) and not src[i + len(open_token) : i + len(open_token) + 1].isalnum():
            depth += 1
            i += len(open_token)
            continue
        if src.startswith(close_token, i):
            depth -= 1
            i += len(close_token)
            if depth == 0:
                end = src.find(">", i)
                return src[start : end + 1 if end >= 0 else i]
            continue
        i += 1
    return src[start:]


def _labeled_button(src: str, label: str) -> str:
    match = re.search(rf">\s*{re.escape(label)}\s*</Button>", src)
    if not match:
        return ""
    start = src.rfind("<Button", 0, match.start())
    if start < 0:
        return ""
    return src[start : match.end()]


def _outline_sm(el: str) -> bool:
    return bool(re.search(r"""variant\s*=\s*["']outline["']""", el)) and bool(
        re.search(r"""size\s*=\s*["']sm["']""", el)
    )


def _locale_bits(crate: Path) -> list[str]:
    bits: list[str] = []
    for lang, filename in (("en", "en.ts"), ("tr", "tr.ts")):
        entries = _chrome_pack_entries(_text(crate / "web" / "lib" / "locales" / filename))
        for key, exact in _EXACT[lang].items():
            got = entries.get(key)
            if got is None:
                bits.append(f"{filename} lacks {key}")
            elif got != exact:
                bits.append(f"{filename} {key} is not the exact string")
    return bits


def _has_long_flag(cli: str, name: str) -> bool:
    """Clap stores the flag as `long = "rebuild-fts"`, not always `--rebuild-fts`."""
    return (
        f"--{name}" in cli
        or f'long = "{name}"' in cli
        or f"long = '{name}'" in cli
    )


def _cli_bits(crate: Path) -> list[str]:
    path = crate.parent / "interlace-core" / "src" / "cli.rs"
    if not path.is_file():
        path = repo_root() / "crates" / "interlace-core" / "src" / "cli.rs"
    cli = _text(path)
    bits: list[str] = []
    if not _has_long_flag(cli, "rebuild-fts") or not _has_long_flag(cli, "gc-cas"):
        bits.append("cli.rs lost --rebuild-fts or --gc-cas")
    if re.search(r"\bdoctor_plan\b", cli):
        bits.append("cli.rs calls doctor_plan")
    return bits


def _old_button_bits(doctor: str) -> list[str]:
    bits: list[str] = []
    for label in ("Integrity", "Rebuild FTS"):
        el = _labeled_button(doctor, label)
        if "ask(" not in el:
            bits.append(f"{label} does not call ask(")
    if "estimateThenAsk" not in _labeled_button(doctor, "GC CAS"):
        bits.append("GC CAS does not call estimateThenAsk")
    return bits


def _calls_forbidden(body: str) -> list[str]:
    bad: list[str] = []
    if re.search(r"\bdoctorRun\b", body):
        bad.append("doctorRun")
    if re.search(r"\bdoctorIssues\b", body):
        bad.append("doctorIssues")
    if re.search(r"\bload\s*\(", body):
        bad.append("load")
    return bad


def _doctor_user_doc_bits() -> list[str]:
    path = repo_root() / "docs" / "user" / "doctor.md"
    if not path.is_file():
        return ["DOC-USER-DOC docs/user/doctor.md is absent"]
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    return [
        f"DOC-USER-DOC docs/user/doctor.md lacks exact line: {sentence}"
        for sentence in _DOCTOR_USER_LINES
        if sentence not in lines
    ]


def assert_doctor_repair(crate: Path) -> None:
    """#431: repair list and apply. Missing data-doctor-repair fails closed."""
    doctor = _text(crate / "web" / "lib" / "DoctorPane.svelte")
    if _marker(doctor, "data-doctor-repair") is None:
        fail("data-doctor-repair is absent")
        return

    bits: list[str] = []
    handler = _handler_text(doctor, "data-doctor-repair")
    if not re.search(r"\bdoctorPlan\b", handler):
        bits.append("data-doctor-repair does not call doctorPlan")
    forbidden = _calls_forbidden(handler)
    if forbidden:
        bits.append(
            "data-doctor-repair handler calls " + ", ".join(forbidden)
        )
    if re.search(r"\bdoctorPlan\b", _mount_path(doctor)):
        bits.append("data-doctor-repair runs from onMount or Refresh")
    repair_el = _element(doctor, "data-doctor-repair")
    if not _outline_sm(repair_el):
        bits.append("data-doctor-repair is not an outline small button")
    if not _uses_t(repair_el, "doctorRepair"):
        bits.append('data-doctor-repair does not use t("doctorRepair")')

    if _marker(doctor, "data-doctor-repair-list") is None:
        bits.append("data-doctor-repair-list is absent")
    else:
        list_el = _element(doctor, "data-doctor-repair-list")
        if not re.match(r"<ul\b", list_el.lstrip()):
            bits.append("data-doctor-repair-list is not a ul")
        if "data-doctor-repair-list" in _each_issues(doctor):
            bits.append("data-doctor-repair-list is inside {#each issues")
        if "data-doctor-repair-list" in _tag_block(doctor, "data-snapshot-list"):
            bits.append("data-doctor-repair-list is inside data-snapshot-list")
        list_at = doctor.find("data-doctor-repair-list")
        status_at = doctor.find("{#if lastOk}")
        integrity = re.search(r">\s*Integrity\s*</Button>", doctor)
        row_at = doctor.rfind("<div", 0, integrity.start()) if integrity else -1
        if not (status_at >= 0 and row_at > status_at and status_at < list_at < row_at):
            bits.append(
                "data-doctor-repair-list is not between the last status line and the button row"
            )
    for key in ("doctorRepairRebuild", "doctorRepairReattach", "doctorRepairReclaim"):
        if not _uses_t(doctor, key):
            bits.append(f'DoctorPane does not use t("{key}")')

    if _marker(doctor, "data-doctor-repair-apply") is None:
        bits.append("data-doctor-repair-apply is absent")
    else:
        apply_el = _element(doctor, "data-doctor-repair-apply")
        if not _outline_sm(apply_el):
            bits.append("data-doctor-repair-apply is not an outline small button")
        if not _uses_t(apply_el, "doctorRepairApply"):
            bits.append('data-doctor-repair-apply does not use t("doctorRepairApply")')
        apply_handler = _handler_text(doctor, "data-doctor-repair-apply")
        if re.search(r"\bdoctorRun\b", apply_handler):
            bits.append("data-doctor-repair-apply calls doctorRun")
        found = False
        calls_run = False
        for body in _confirm_bodies(doctor):
            arm = _repair_arm(doctor, body)
            if re.search(r"\bdoctorApply\b", arm):
                found = True
                if re.search(r"\bdoctorRun\b", arm):
                    calls_run = True
        if not found:
            bits.append("data-doctor-repair-apply confirm path does not call doctorApply")
        if calls_run:
            bits.append("data-doctor-repair-apply confirm path calls doctorRun")
    if len(re.findall(r"<ConfirmDialog\b", doctor)) != 1:
        bits.append("ConfirmDialog is not the one existing dialog")

    bits.extend(_old_button_bits(doctor))
    bits.extend(_cli_bits(crate))
    bits.extend(_locale_bits(crate))
    bits.extend(_doctor_user_doc_bits())
    if bits:
        fail("doctor repair: " + "; ".join(bits))
