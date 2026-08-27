"""#304 — product-file line-count lock (cap 500). Imported by gate_tauri.py."""
from __future__ import annotations

from pathlib import Path

from common import fail, repo_root

# Same style as gate_tauri._split_line_count / #300. Do not share
# _SPLIT_MAX_LINES (that cap stays 1_200 for tauri_gate modules).
_PRODUCT_MAX_LINES = 500

_REQUIRED = (
    "crates/interlace-tauri/web/App.svelte",
    "crates/interlace-core/src/identity.rs",
    "crates/interlace-tauri/src/main.rs",
    "crates/interlace-core/src/import/whatsapp.rs",
    "crates/interlace-core/src/import/locale.rs",
    "crates/interlace-core/src/import/context.rs",
    "crates/interlace-core/src/import/gmail.rs",
    "crates/interlace-core/src/cli.rs",
    "crates/interlace-core/src/people.rs",
    "crates/interlace-tauri/web/lib/SearchPane.svelte",
)

_SIBLING_GLOBS = (
    "crates/interlace-core/src/identity/**/*.rs",
    "crates/interlace-core/src/identity_*.rs",
    "crates/interlace-tauri/src/*.rs",
    "crates/interlace-core/src/import/whatsapp/**/*.rs",
    "crates/interlace-core/src/import/whatsapp_*.rs",
    "crates/interlace-core/src/import/locale/**/*.rs",
    "crates/interlace-core/src/import/locale_*.rs",
    "crates/interlace-core/src/import/context/**/*.rs",
    "crates/interlace-core/src/import/context_*.rs",
    "crates/interlace-core/src/import/gmail/**/*.rs",
    "crates/interlace-core/src/import/gmail_*.rs",
    "crates/interlace-core/src/cli/**/*.rs",
    "crates/interlace-core/src/cli_*.rs",
    "crates/interlace-core/src/people/**/*.rs",
    "crates/interlace-core/src/people_*.rs",
    "crates/interlace-tauri/web/lib/Search*.svelte",
    "crates/interlace-tauri/web/lib/Search*.ts",
)

_APP_EXTRACT_STEMS = ("Setup", "People", "Timeline", "Merge")
_APP_EXTRACT_EXTS = (".svelte", ".ts")


def _line_count(path: Path) -> int:
    return sum(1 for _ in path.open(encoding="utf-8"))


def _assert_under_cap(rel: str, path: Path) -> None:
    n = _line_count(path)
    if n >= _PRODUCT_MAX_LINES:
        fail(f"#304: {rel} is {n} lines (>= 500)")


def _sibling_files(root: Path) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        if not path.is_file():
            return
        key = path.resolve()
        if key in seen:
            return
        seen.add(key)
        found.append(path)

    for pattern in _SIBLING_GLOBS:
        for path in sorted(root.glob(pattern)):
            add(path)
    lib = root / "crates" / "interlace-tauri" / "web" / "lib"
    for stem in _APP_EXTRACT_STEMS:
        for ext in _APP_EXTRACT_EXTS:
            for path in sorted(lib.glob(f"{stem}*{ext}")):
                add(path)
    return found


def assert_product_split(crate: Path) -> None:
    """Fail when an inventory product file (or a later sibling) is >= 500 lines."""
    del crate
    root = repo_root()
    required: set[Path] = set()
    for rel in _REQUIRED:
        path = root / rel
        if not path.is_file():
            fail(f"#304: {rel} is required")
        required.add(path.resolve())
        _assert_under_cap(rel, path)
    for path in _sibling_files(root):
        if path.resolve() in required:
            continue
        _assert_under_cap(path.relative_to(root).as_posix(), path)
