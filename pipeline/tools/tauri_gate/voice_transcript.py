"""#428 — Doctor can transcribe voice notes. The bubble cannot.

Checkbox `data-vt-enabled`, button `data-vt-run`, exact en/tr strings.
Opening Doctor does not transcribe. No cloud client and no runtime download.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.scan import _web_sources
from tauri_gate.scan_parse import _call_arg, _function_body, _match_closer
from tauri_gate.scan_parse_rest import _ts_function_body
from tauri_gate.scan_rust_rest import _rust_function_body, _rust_match_delim, _rust_next

_EXACT = {
    "en": {
        "transcribeVoiceLabel": "Transcribe voice notes",
        "transcribeVoice": "Transcribe",
        "transcribeVoiceDesc": (
            "Writes a transcript of each new voice note into search. "
            "Audio stays on this Mac. Notes that already have a transcript "
            "are left as they are. Turning this off keeps existing transcripts."
        ),
        "transcribeVoiceFinished": "Transcription finished.",
    },
    "tr": {
        "transcribeVoiceLabel": "Sesli notları yazıya dök",
        "transcribeVoice": "Yazıya dök",
        "transcribeVoiceDesc": (
            "Her yeni sesli notun metnini aramaya yazar. Ses bu Mac'te kalır. "
            "Metni olan notlara dokunulmaz. Bunu kapatmak mevcut metinleri yerinde bırakır."
        ),
        "transcribeVoiceFinished": "Yazıya dökme bitti.",
    },
}

_T_CALL = re.compile(r"""\bt\s*\(\s*(['"])(?:\\.|(?!\1).)*\1\s*\)""")
_CHECKBOX = re.compile(
    r"type\s*=\s*['\"]checkbox['\"]|role\s*=\s*['\"]checkbox['\"]|<Checkbox\b|bind:checked",
    re.I,
)
_BUTTON = re.compile(r"<Button\b|<button\b|role\s*=\s*['\"]button['\"]")
_CAS_CONTROL = re.compile(
    r"(?i)\btranscri(?:be|ption|pt)\b|data-transcribe\b|data-voice-transcript\b"
    r"|showTranscript|voiceTranscript|data-vt-(?:enabled|run)\b"
)
_DATA_ATTR = re.compile(r"data-transcribe\b|data-voice-transcript\b")
_CARGO_DEP = re.compile(
    r"(?m)^[ \t]*(reqwest|hf-hub|whisper-rs|tauri-plugin-http)(?:\.workspace)?[ \t]*="
)
_TRANSCRIBE_CALL = re.compile(
    r"(?i)(?:\b(?:api\s*\.\s*)?[A-Za-z_][A-Za-z0-9_]*transcribe[A-Za-z0-9_]*\s*\()"
    r"""|(?:\binvoke\s*\(\s*['\"][^'\"]*transcribe)"""
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _uses_t(window: str, key: str) -> bool:
    return bool(re.search(rf"""\bt\s*\(\s*['\"]{re.escape(key)}['\"]\s*\)""", window))


def _control_window(src: str, marker: str) -> str:
    at = src.find(marker)
    if at < 0:
        return ""
    start = src.rfind("<", 0, at)
    if start < 0:
        start = max(0, at - 240)
    return src[start : at + 700]


def _doctor_control_bits(src: str) -> list[str]:
    bits: list[str] = []
    if "data-vt-enabled" not in src:
        bits.append("DoctorPane has no data-vt-enabled checkbox")
    else:
        window = _control_window(src, "data-vt-enabled")
        if not _CHECKBOX.search(window):
            bits.append("data-vt-enabled is not a checkbox")
        if not _uses_t(window, "transcribeVoiceLabel"):
            bits.append('data-vt-enabled does not use t("transcribeVoiceLabel")')
    if "data-vt-run" not in src:
        bits.append("DoctorPane has no data-vt-run button")
    else:
        window = _control_window(src, "data-vt-run")
        if not _BUTTON.search(window):
            bits.append("data-vt-run is not a button")
        if not _uses_t(window, "transcribeVoice"):
            bits.append('data-vt-run does not use t("transcribeVoice")')
    return bits


def _locale_bits(crate: Path) -> list[str]:
    bits: list[str] = []
    for lang, filename in (("en", "en.ts"), ("tr", "tr.ts")):
        entries = _chrome_pack_entries(
            _text(crate / "web" / "lib" / "locales" / filename)
        )
        for key, exact in _EXACT[lang].items():
            got = entries.get(key)
            if got is None:
                bits.append(f"{filename} lacks {key}")
            elif got != exact:
                bits.append(f"{filename} {key} is not the exact string")
    return bits


def _on_mount_body(src: str) -> str:
    match = re.search(r"\bonMount\s*\(", src)
    if not match:
        return ""
    arg = _call_arg(src, match.end() - 1)
    brace = arg.find("{")
    if brace < 0:
        return arg
    close = _match_closer(arg, brace)
    if close < 0:
        return arg[brace + 1 :]
    return arg[brace + 1 : close]


def _mount_path(src: str) -> str:
    pending = [name for name in re.findall(r"\b([A-Za-z_]\w*)\s*\(", _on_mount_body(src))]
    # `onMount(load)` has no call parentheses inside the callback.
    bare = _on_mount_body(src).strip()
    if re.fullmatch(r"[A-Za-z_]\w*", bare):
        pending.append(bare)
    seen: set[str] = set()
    parts = [_on_mount_body(src)]
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        body = _ts_function_body(src, name) or _function_body(src, name)
        if not body:
            continue
        parts.append(body)
        pending.extend(re.findall(r"\b([A-Za-z_]\w*)\s*\(", body))
    return "\n".join(parts)


def _mount_calls_transcribe(src: str) -> bool:
    text = _T_CALL.sub("", _mount_path(src))
    return _TRANSCRIBE_CALL.search(text) is not None


def _cas_and_attr_bits(crate: Path) -> list[str]:
    bits: list[str] = []
    cas = _text(crate / "web" / "lib" / "CasAttach.svelte")
    if _CAS_CONTROL.search(cas):
        bits.append("CasAttach voice player gained a transcribe control")
    named = [
        path.name
        for path in _web_sources(crate)
        if _DATA_ATTR.search(_text(path))
    ]
    if named:
        bits.append(
            "svelte/css contains data-transcribe or data-voice-transcript: "
            + ", ".join(named)
        )
    return bits


def _cargo_bits(root: Path) -> list[str]:
    bits: list[str] = []
    for path in sorted(root.rglob("Cargo.toml")):
        if "target" in path.parts:
            continue
        found = sorted(set(_CARGO_DEP.findall(_text(path))))
        for name in found:
            bits.append(f"{path.relative_to(root)} gains {name}")
    return bits


def _resources_map_weights(resources: object) -> bool:
    """Object destinations only. A list path is copied under `_up_`, not the resource root."""
    if not isinstance(resources, dict):
        return False
    saw = False
    for dest in resources.values():
        if not isinstance(dest, str):
            return False
        if ".." in dest or "_up_" in dest:
            return False
        if dest == "ggml-tiny.bin":
            saw = True
    return saw


def _weight_bits(root: Path, crate: Path) -> list[str]:
    bits: list[str] = []
    if not (root / "assets" / "ggml-tiny.bin").is_file():
        bits.append("assets/ggml-tiny.bin is missing")
    try:
        conf = json.loads(_text(crate / "tauri.conf.json") or "{}")
    except json.JSONDecodeError:
        conf = {}
    resources = conf.get("bundle", {}).get("resources") if isinstance(conf, dict) else None
    blob = json.dumps(resources) if resources is not None else ""
    if "ggml-tiny.bin" not in blob:
        bits.append("tauri.conf.json bundle.resources does not name ggml-tiny.bin")
    if not _resources_map_weights(resources):
        bits.append(
            "tauri.conf.json bundle.resources must map the weights onto ggml-tiny.bin"
        )
    return bits


def _skip_rust_gap(src: str, i: int) -> int:
    n = len(src)
    while i < n:
        nxt = _rust_next(src, i)
        if nxt != i:
            i = nxt
            continue
        if src[i].isspace():
            i += 1
            continue
        break
    return i


def _ident_at(src: str, i: int, name: str) -> bool:
    if not src.startswith(name, i):
        return False
    if i > 0 and (src[i - 1].isalnum() or src[i - 1] == "_"):
        return False
    end = i + len(name)
    return end >= len(src) or not (src[end].isalnum() or src[end] == "_")


def _argument_braces(src: str) -> list[str]:
    """Brace groups in a call's argument list. Nested braces stay inside the outer group."""
    out: list[str] = []
    i = 0
    n = len(src)
    while i < n:
        nxt = _rust_next(src, i)
        if nxt != i:
            i = nxt
            continue
        if src[i] == "{":
            close = _rust_match_delim(src, i)
            if close < 0:
                out.append(src[i + 1 :])
                break
            out.append(src[i + 1 : close])
            i = close + 1
            continue
        i += 1
    return out


def _with_arch_closures(body: str) -> list[str]:
    """Argument braces of `with_arch(...)` calls in this body only."""
    found: list[str] = []
    i = 0
    n = len(body)
    while i < n:
        nxt = _rust_next(body, i)
        if nxt != i:
            i = nxt
            continue
        if _ident_at(body, i, "with_arch"):
            j = _skip_rust_gap(body, i + len("with_arch"))
            if j < n and body[j] == "(":
                close = _rust_match_delim(body, j)
                if close < 0:
                    found.extend(_argument_braces(body[j + 1 :]))
                    break
                found.extend(_argument_braces(body[j + 1 : close]))
                i = close + 1
                continue
        i += 1
    return found


def _transcribe_cmd_body(ipc: str) -> str:
    """Interior of `fn transcribe_voice_notes_cmd`, matched from its opening `{`."""
    return _rust_function_body(ipc, "transcribe_voice_notes_cmd")


def _decodes_while_holding_archive(body: str) -> bool:
    if "transcribe_voice_notes(" in body:
        return True
    if "store_voice_transcript" not in body:
        return True
    if "decode(" not in body:
        return True
    return any("decode(" in closure for closure in _with_arch_closures(body))


def _transcribe_cmd_decodes_while_holding(crate: Path) -> bool:
    return _decodes_while_holding_archive(_transcribe_cmd_body(_text(crate / "src" / "ipc.rs")))


def _skip_ws_comments(src: str, i: int, limit: int) -> int:
    while i < limit:
        nxt = _rust_next(src, i)
        if nxt != i:
            if not (src.startswith("//", i) or src.startswith("/*", i)):
                return i
            if nxt > limit:
                return i
            i = nxt
            continue
        if src[i].isspace():
            i += 1
            continue
        return i
    return i


def _has_ident(src: str, name: str) -> bool:
    i = 0
    n = len(src)
    while i < n:
        nxt = _rust_next(src, i)
        if nxt != i:
            i = nxt
            continue
        if _ident_at(src, i, name):
            return True
        i += 1
    return False


def _has_arch_root(src: str, limit: int | None = None) -> bool:
    end = len(src) if limit is None else limit
    name = "arch"
    i = 0
    while i < end:
        nxt = _rust_next(src, i)
        if nxt != i:
            if nxt > end:
                break
            i = nxt
            continue
        if i + len(name) <= end and _ident_at(src, i, name):
            j = i + len(name)
            while j < end and src[j].isspace():
                j += 1
            if j < end and src[j] == ".":
                k = j + 1
                while k < end and src[k].isspace():
                    k += 1
                if (
                    k + len("root") <= end
                    and _rust_next(src, k) == k
                    and _ident_at(src, k, "root")
                ):
                    return True
            i += len(name)
            continue
        i += 1
    return False


def _call_at(src: str, name: str) -> int:
    i = 0
    n = len(src)
    while i < n:
        nxt = _rust_next(src, i)
        if nxt != i:
            i = nxt
            continue
        if _ident_at(src, i, name):
            j = i + len(name)
            while j < n and src[j].isspace():
                j += 1
            if j < n and src[j] == "(":
                return i
            i += len(name)
            continue
        i += 1
    return -1


def _has_archive_changed_lit(src: str, limit: int) -> bool:
    needle = '"archive changed"'
    i = 0
    while i < limit:
        nxt = _rust_next(src, i)
        if nxt != i:
            if nxt <= limit and src[i:nxt] == needle:
                return True
            if nxt > limit:
                break
            i = nxt
            continue
        i += 1
    return False


def _has_return_err(src: str, limit: int) -> bool:
    i = 0
    while i < limit:
        nxt = _rust_next(src, i)
        if nxt != i:
            if nxt > limit:
                break
            i = nxt
            continue
        if i + len("return") <= limit and _ident_at(src, i, "return"):
            j = _skip_ws_comments(src, i + len("return"), limit)
            if j + len("Err") <= limit and _ident_at(src, j, "Err"):
                return True
            i += len("return")
            continue
        i += 1
    return False


def _guarded_before_call(closure: str, name: str) -> bool:
    at = _call_at(closure, name)
    if at < 0:
        return False
    return (
        _has_arch_root(closure, at)
        and _has_archive_changed_lit(closure, at)
        and _has_return_err(closure, at)
    )


def _transcribe_can_store_into_different_archive(body: str) -> bool:
    """True unless row, byte, and store closures all prove the same archive."""
    closures = _with_arch_closures(body)
    pending = [c for c in closures if _has_ident(c, "pending_voice_note_rows")]
    if not pending or any(not _has_arch_root(c) for c in pending):
        return True
    cas = [c for c in closures if _call_at(c, "cas_get") >= 0]
    if not cas or any(not _guarded_before_call(c, "cas_get") for c in cas):
        return True
    store = [c for c in closures if _call_at(c, "store_voice_transcript") >= 0]
    if not store or any(not _guarded_before_call(c, "store_voice_transcript") for c in store):
        return True
    return False


def _transcribe_cmd_can_store_into_different_archive(crate: Path) -> bool:
    return _transcribe_can_store_into_different_archive(
        _transcribe_cmd_body(_text(crate / "src" / "ipc.rs"))
    )


def assert_voice_transcript(crate: Path) -> None:
    """#428: Doctor checkbox and button, bundled weights, no bubble control."""
    doctor = _text(crate / "web" / "lib" / "DoctorPane.svelte")
    bits = _doctor_control_bits(doctor)
    bits.extend(_locale_bits(crate))
    if _mount_calls_transcribe(doctor):
        bits.append("DoctorPane mount path calls the transcribe command")
    bits.extend(_cas_and_attr_bits(crate))
    root = repo_root()
    bits.extend(_cargo_bits(root))
    bits.extend(_weight_bits(root, crate))
    if bits:
        fail("VOICE-TRANSCRIPT: " + "; ".join(bits))
    if _transcribe_cmd_decodes_while_holding(crate):
        fail("transcribe command decodes while holding the archive mutex")
    if _transcribe_cmd_can_store_into_different_archive(crate):
        fail("transcribe command can store into a different archive")
