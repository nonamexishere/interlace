"""#429 — Doctor can read text in photos. The bubble cannot.

Checkbox `data-ocr-enabled`, button `data-ocr-run`, exact en/tr strings.
Opening Doctor does not OCR. No cloud client and no runtime download.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.scan_parse_rest import _ts_function_body
from tauri_gate.scan_rust_rest import _rust_function_body
from tauri_gate.voice_transcript import (
    _T_CALL,
    _call_at,
    _control_window,
    _guarded_before_call,
    _mount_path,
    _text,
    _uses_t,
    _with_arch_closures,
)

_EXACT = {
    "en": {
        "ocrImagesLabel": "Read text in photos",
        "ocrImages": "Read photos",
        "ocrImagesDesc": (
            "Writes the text of each new photo into search. "
            "The image stays on this Mac. Photos that already have text "
            "are left as they are. Turning this off keeps existing text."
        ),
        "ocrImagesFinished": "Photo text is in search.",
    },
    "tr": {
        "ocrImagesLabel": "Fotoğraflardaki metni oku",
        "ocrImages": "Fotoğrafları oku",
        "ocrImagesDesc": (
            "Her yeni fotoğrafın metnini aramaya yazar. Görüntü bu Mac'te kalır. "
            "Metni olan fotoğraflara dokunulmaz. Bunu kapatmak mevcut metinleri yerinde bırakır."
        ),
        "ocrImagesFinished": "Fotoğraf metni aramada.",
    },
}

_FOCUS = "focus-visible:ring-2 focus-visible:ring-ring"
_BANNED = (
    "CasAttach.svelte",
    "TimelineLightbox.svelte",
    "PersonMediaDialog.svelte",
)
_OCR_CALL = re.compile(
    r"(?i)(?:\b(?:api\s*\.\s*)?[A-Za-z_][A-Za-z0-9_]*ocr[A-Za-z0-9_]*\s*\()"
    r"""|(?:\binvoke\s*\(\s*['\"][^'\"]*ocr)"""
)


def _control_bits(doctor: str) -> list[str]:
    bits: list[str] = []
    enabled = _control_window(doctor, "data-ocr-enabled")
    if not _uses_t(enabled, "ocrImagesLabel"):
        bits.append('data-ocr-enabled does not use t("ocrImagesLabel")')
    if _FOCUS not in enabled:
        bits.append(
            "data-ocr-enabled lacks class focus-visible:ring-2 focus-visible:ring-ring"
        )
    run = _control_window(doctor, "data-ocr-run")
    if not _uses_t(run, "ocrImages"):
        bits.append('data-ocr-run does not use t("ocrImages")')
    return bits


def _banned_bits(crate: Path) -> list[str]:
    bits: list[str] = []
    for name in _BANNED:
        src = _text(crate / "web" / "lib" / name)
        if "data-ocr-enabled" in src or "data-ocr-run" in src:
            bits.append(f"{name} has data-ocr-enabled or data-ocr-run")
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


def _mount_calls_ocr(src: str) -> bool:
    text = _T_CALL.sub("", _mount_path(src))
    return _OCR_CALL.search(text) is not None


def _confirm_bits(doctor: str) -> list[str]:
    bits: list[str] = []
    if len(re.findall(r"<ConfirmDialog\b", doctor)) != 1:
        bits.append("ConfirmDialog is not exactly one")
    if not re.search(r"onconfirm\s*=\s*\{\s*runPending\s*\}", doctor):
        bits.append("onconfirm is not {runPending}")
    body = _ts_function_body(doctor, "runPending")
    if "gcCas:" not in body:
        bits.append("runPending lacks gcCas:")
    return bits


def _resource_bits(root: Path, crate: Path) -> list[str]:
    bits: list[str] = []
    try:
        conf = json.loads(_text(crate / "tauri.conf.json") or "{}")
    except json.JSONDecodeError:
        conf = {}
    resources = conf.get("bundle", {}).get("resources") if isinstance(conf, dict) else None
    if not isinstance(resources, dict):
        bits.append("tauri.conf.json bundle.resources is not an object")
    else:
        saw = False
        for dest in resources.values():
            if not isinstance(dest, str) or ".." in dest or "_up_" in dest:
                bits.append(
                    "tauri.conf.json bundle.resources destination contains .. or _up_"
                )
                saw = False
                break
            if dest == "tur.traineddata":
                saw = True
        if not any("destination contains" in bit for bit in bits) and not saw:
            bits.append(
                "tauri.conf.json bundle.resources has no destination tur.traineddata"
            )
    weight = root / "assets" / "tur.traineddata"
    if not weight.is_file() or weight.stat().st_size != 7456265:
        bits.append("assets/tur.traineddata is missing or its size is not 7456265")
    return bits


def _ocr_decodes_while_holding(crate: Path) -> bool:
    ipc = _text(crate / "src" / "ipc.rs")
    body = _rust_function_body(ipc, "ocr_images_cmd")
    if not re.search(r"\bfn\s+ocr_images_cmd\b", ipc) or not body:
        return True
    if "ocr_image_attachments(" in body:
        return True
    closures = _with_arch_closures(body)
    if any("decode(" in closure for closure in closures):
        return True
    cas = [c for c in closures if _call_at(c, "cas_get") >= 0]
    if not cas or any(not _guarded_before_call(c, "cas_get") for c in cas):
        return True
    store = [c for c in closures if _call_at(c, "store_ocr_text") >= 0]
    if not store or any(not _guarded_before_call(c, "store_ocr_text") for c in store):
        return True
    return False


def assert_photo_ocr(crate: Path) -> None:
    """#429: Doctor checkbox and button, bundled weights, IPC drops the archive."""
    doctor = _text(crate / "web" / "lib" / "DoctorPane.svelte")
    if "data-ocr-enabled" not in doctor or "data-ocr-run" not in doctor:
        fail("photo OCR controls are missing")
        return
    bits = _control_bits(doctor)
    bits.extend(_banned_bits(crate))
    bits.extend(_locale_bits(crate))
    if _mount_calls_ocr(doctor):
        bits.append("Doctor onMount calls an ocr command")
    bits.extend(_confirm_bits(doctor))
    bits.extend(_resource_bits(repo_root(), crate))
    if bits:
        fail("photo OCR: " + "; ".join(bits))
    if _ocr_decodes_while_holding(crate):
        fail("ocr command decodes while holding the archive mutex")
