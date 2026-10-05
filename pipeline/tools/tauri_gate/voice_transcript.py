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
