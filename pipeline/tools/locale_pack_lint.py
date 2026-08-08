#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root  # noqa: E402

ALLOWED = {"en-US", "en-GB", "tr-TR", "de-DE", "pt-BR"}
REQUIRED = ("you_tokens", "date_format", "header_family")


def main() -> None:
    root = repo_root()
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "crates" / "interlace-fixtures" / "locale"
    if not d.is_dir():
        fail(f"locale dir missing: {d}")
    packs = list(d.glob("*.toml"))
    if not packs:
        fail(f"no locale toml in {d}")
    for p in packs:
        pid = p.stem
        if pid not in ALLOWED:
            fail(f"locale id {pid} not in {sorted(ALLOWED)}")
        text = p.read_text()
        for key in REQUIRED:
            if key not in text:
                fail(f"{p} missing {key}")
    print(f"locale_pack_lint ok ({len(packs)} packs)")


if __name__ == "__main__":
    main()
