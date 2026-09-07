"""#317 fold — bound sniff_mime ftyp + Open fail toast docs.

Typed-open / menu-clamp stay in the earlier #317 modules. This sibling
only locks the ISO-BMFF ftyp scan (box size + 4-byte-aligned brands,
capped) and docs/user/app.md “Could not open”.

cas_data_url / cas_response may still pass the full blob to sniff_mime;
the helper itself must not walk mdat.

Must-IDs: open-cas-ftyp-bound, open-cas-open-toast-docs.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.scan import (
    _match_closer,
    _rust_function_body,
    _tauri_rust_blob,
    _without_comments,
)

_ISSUE = "#317"
_FTYP = re.compile(r"""(?:b"ftyp"|b'ftyp'|\*b"ftyp")""")
_WINDOWS4 = re.compile(r"\.windows\s*\(\s*4\s*\)")
_STEP_BY_4 = re.compile(r"\bstep_by\s*\(\s*4\s*\)")
_UNBOUNDED_TAIL = re.compile(
    r"bytes\s*(?:\.\s*get\s*)?\[\s*8\s*\.\.\s*\]"
    r"|bytes\s*\.\s*get\s*\(\s*8\s*\.\.\s*\)"
    r"|bytes\s*\[\s*8\s*\.\.\s*bytes\s*\.\s*len\s*\(\s*\)\s*\]"
)
_WHOLE_BYTES = re.compile(
    r"\bwindows\s*\(\s*4\s*\)\s*\.\s*any"
    r"|bytes\s*\[\s*8\s*\.\.\s*\]"
)
_MDAT_SCAN = re.compile(r"""(?:b"mdat"|b'mdat'|\*b"mdat")""")
_FROM_BE = re.compile(r"\bfrom_be_bytes\b")
_U32 = re.compile(r"\bu32\b")
_HEAD4 = re.compile(
    r"bytes\s*\[\s*0\s*\.\.\s*4\s*\]"
    r"|bytes\s*\[\s*0\s*\]\s*,\s*bytes\s*\[\s*1\s*\]"
    r"\s*,\s*bytes\s*\[\s*2\s*\]\s*,\s*bytes\s*\[\s*3\s*\]"
)
_MAJOR8 = re.compile(
    r"bytes\s*\[\s*8\s*\.\.\s*12\s*\]"
    r"|8\s*\.\.\s*12"
)
_SKIP_MINOR = re.compile(
    r"12\s*\.\.\s*16"
    r"|16\s*\.\."
    r"|i\s*==\s*12"
    r"|==\s*12\b"
)
_ALIGNED = re.compile(
    r"chunks_exact\s*\(\s*4\s*\)"
    r"|chunks\s*\(\s*4\s*\)"
    r"|step_by\s*\(\s*4\s*\)"
    r"|\b(?:i|idx|off|at|pos)\s*\+=\s*4\b"
)
_CAP = re.compile(r"\b(?:64|128|256|512)\b")
_MIN = re.compile(r"\.min\s*\(|\bmin\s*!")
_HEIC = re.compile(r"""b"heic"|b'heic'|image/heic""")
_M4A = re.compile(r"""b"M4A "|b'M4A '|audio/mp4""")
_MP4 = re.compile(r"video/mp4")
_DOCS_COULD_NOT_OPEN = re.compile(r"Could not open")
_DOCS_OPEN_TOAST = re.compile(
    r"Open.{0,160}(?:fail|toast)|(?:fail|toast).{0,160}Open",
    re.I | re.S,
)
_DOCS_CHROME = re.compile(
    r"chrome(?:-|\s+)?only|no path|not.{0,40}(?:path|hash)",
    re.I,
)
_CALL_SKIP = frozenset(
    {
        "len",
        "has",
        "starts_with",
        "Some",
        "Ok",
        "Err",
        "vec",
        "format",
        "min",
        "get",
        "any",
        "from_be_bytes",
        "try_into",
        "as_ref",
        "to_vec",
        "copy_from_slice",
    }
)


def _sniff_src(crate: Path) -> str:
    cas = crate / "src" / "cas.rs"
    blob = cas.read_text() if cas.is_file() else ""
    if "fn sniff_mime" not in blob:
        blob = _tauri_rust_blob(crate)
    return _without_comments(blob)


def _ftyp_arm(body: str) -> str:
    m = _FTYP.search(body)
    if not m:
        return ""
    if_pos = body.rfind("if", 0, m.start())
    start = if_pos if if_pos >= 0 else m.start()
    brace = body.find("{", start)
    if brace < 0:
        return body[start:]
    close = _match_closer(body, brace)
    if close < 0:
        return body[start:]
    return body[start : close + 1]


def _ftyp_path(src: str) -> str:
    """sniff_mime ftyp arm plus one callee hop (ftyp helpers)."""
    own = _rust_function_body(src, "sniff_mime")
    if not own:
        return ""
    arm = _ftyp_arm(own) or own
    parts = [arm]
    for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", arm):
        name = m.group(1)
        if name in _CALL_SKIP:
            continue
        inner = _rust_function_body(src, name)
        if inner:
            parts.append(inner)
    return "\n".join(parts)


def _unbounded_ftyp(ftyp: str) -> bool:
    """True when the ftyp path still walks the whole tail / mdat."""
    if _MDAT_SCAN.search(ftyp):
        return True
    if _UNBOUNDED_TAIL.search(ftyp):
        return True
    if _WINDOWS4.search(ftyp) and not _STEP_BY_4.search(ftyp):
        return True
    return bool(_WINDOWS4.search(ftyp) and _WHOLE_BYTES.search(ftyp))


def _parses_box_size(ftyp: str) -> bool:
    if not _FROM_BE.search(ftyp):
        return False
    if not _U32.search(ftyp):
        return False
    return bool(_HEAD4.search(ftyp))


def _aligned_brands(ftyp: str) -> bool:
    if not _ALIGNED.search(ftyp):
        return False
    if not _MAJOR8.search(ftyp):
        return False
    return bool(_SKIP_MINOR.search(ftyp))


def _has_scan_cap(ftyp: str) -> bool:
    if not _CAP.search(ftyp):
        return False
    return bool(_MIN.search(ftyp) or re.search(r"bytes\s*\[\s*\d+\s*\.\.\s*\w+", ftyp))


def assert_open_cas_ftyp(crate: Path) -> None:
    """#317 fold: bound sniff_mime ftyp; document Open fail toast."""
    src = _sniff_src(crate)
    if not src.strip():
        fail(f"{_ISSUE}: crates/interlace-tauri/src/cas.rs required (sniff_mime)")
    own = _rust_function_body(src, "sniff_mime")
    if not own.strip():
        fail(
            f"{_ISSUE}: sniff_mime required in cas.rs "
            "(Open ext + in-window Content-Type share the helper)"
        )
    if not _FTYP.search(own):
        fail(
            f"{_ISSUE}: sniff_mime must keep the ftyp matcher "
            "(HEIC / M4A / mp4 brands)"
        )
    ftyp = _ftyp_path(src)
    if not ftyp.strip():
        fail(f"{_ISSUE}: sniff_mime ftyp branch required")

    # 1) open-cas-ftyp-bound — fail-today: brands = &bytes[8..]; windows(4).
    if _unbounded_ftyp(ftyp):
        fail(
            f"{_ISSUE}: sniff_mime ftyp path must not windows(4) "
            "&bytes[8..] / the whole tail — parse the box size and scan "
            "4-byte-aligned brands only"
        )
    if not _parses_box_size(ftyp):
        fail(
            f"{_ISSUE}: sniff_mime ftyp path must parse the box size "
            "(u32::from_be_bytes on bytes[0..4])"
        )
    if not _aligned_brands(ftyp):
        fail(
            f"{_ISSUE}: sniff_mime ftyp brands are 4-byte-aligned "
            "(major at 8..12, skip minor_version 12..16, then 16..end) "
            "— chunks_exact(4) / step_by(4), not windows(4)"
        )
    if not _has_scan_cap(ftyp):
        fail(
            f"{_ISSUE}: sniff_mime ftyp scan must cap at "
            "min(size, bytes.len(), 256) so a lying size cannot walk mdat"
        )
    if not _HEIC.search(ftyp):
        fail(
            f"{_ISSUE}: HEIC ftyp brands (heic / heix / mif1 / msf1 / hevc) "
            "must still map to image/heic"
        )
    if not _M4A.search(ftyp):
        fail(f"{_ISSUE}: M4A ftyp brand must still map to audio/mp4")
    if not _MP4.search(ftyp):
        fail(f"{_ISSUE}: default ftyp must still map to video/mp4")

    # 2) open-cas-open-toast-docs — fail-today: Copy/Reveal only.
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    if not dtxt.strip():
        fail(
            f"{_ISSUE}: docs/user/app.md required — Open failures toast "
            '(chrome-only — “Could not open”)'
        )
    if not _DOCS_COULD_NOT_OPEN.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say Open failures toast "
            '(chrome-only — “Could not open”)'
        )
    toast_win = ""
    for m in _DOCS_COULD_NOT_OPEN.finditer(dtxt):
        toast_win += dtxt[max(0, m.start() - 160) : m.end() + 120] + "\n"
    if not re.search(r"toast|fail", toast_win, re.I) and not _DOCS_OPEN_TOAST.search(
        toast_win
    ):
        fail(
            f"{_ISSUE}: docs/user/app.md must mention Open with the "
            "fail toast (Copy / Reveal / Open)"
        )
    if not _DOCS_CHROME.search(toast_win) and not _DOCS_CHROME.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md Open toast is chrome-only "
            "(no path / hash)"
        )
    if re.search(r"/Users/|/home/|[0-9a-fA-F]{64}", toast_win):
        fail(f"{_ISSUE}: Open toast docs must not quote a path or hash")
