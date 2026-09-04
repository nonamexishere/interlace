"""#304 — product inventory still present. Line count is not a gate."""
from __future__ import annotations

from pathlib import Path

from common import fail, repo_root

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


def assert_product_split(crate: Path) -> None:
    """Keep the #304 inventory files present. Line count is not a gate."""
    del crate
    root = repo_root()
    for rel in _REQUIRED:
        if not (root / rel).is_file():
            fail(f"#304: {rel} is required")
