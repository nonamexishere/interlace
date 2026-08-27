"""Shared readers and parse walkers for tauri_gate area modules."""
from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)




# IPC-only connect-src (no general http/https). 'none' blanks the .app (#107).
# frame-src data: lets CasPdf load a local casDataUrl iframe; no http(s) frames.
CSP = (
    "default-src 'self'; img-src 'self' asset: data: cas:; media-src 'self' cas: data:; "
    "style-src 'self' 'unsafe-inline'; "
    "connect-src ipc: http://ipc.localhost https://ipc.localhost; "
    "frame-src data:; font-src 'self'"
)
# Names accepted as the person-timeline {#each} source (#111–#113 / #120).
_TIMELINE_EACH_NAMES = (
    "timeline",
    "dayGroups",
    "windowedDayGroups",
    "windowedGroups",
    "visibleDayGroups",
    "visibleGroups",
    "virtualDayGroups",
    "virtualGroups",
    "renderedDayGroups",
    "renderedGroups",
    "windowedRows",
    "visibleRows",
    "virtualRows",
    "renderedRows",
    "windowedTimeline",
    "visibleTimeline",
    "virtualTimeline",
    "renderedTimeline",
    "windowedItems",
    "visibleItems",
    "virtualItems",
)


def _web_sources(crate: Path) -> list[Path]:
    web = crate / "web"
    return [
        p
        for p in sorted(web.rglob("*"))
        if p.suffix in {".svelte", ".css"} and "node_modules" not in p.parts
    ]


def _web_logic(crate: Path) -> str:
    """Svelte + TS sources (helpers may live next to App.svelte)."""
    web = crate / "web"
    parts: list[str] = []
    for p in sorted(web.rglob("*")):
        if p.suffix in {".svelte", ".ts"} and "node_modules" not in p.parts:
            parts.append(p.read_text())
    return "\n".join(parts)


def _timeline_block(crate: Path) -> str:
    found: list[str] = []
    for p in _web_sources(crate):
        if p.suffix != ".svelte":
            continue
        text = p.read_text()
        i = 0
        while True:
            start = -1
            for name in _TIMELINE_EACH_NAMES:
                idx = text.find(f"{{#each {name}", i)
                if idx >= 0 and (start < 0 or idx < start):
                    start = idx
            if start < 0:
                break
            end = text.find("{/each}", start)
            if end < 0:
                fail(f"#111: unclosed {{#each timeline}} in {p.relative_to(crate)}")
            found.append(text[start:end])
            i = end + len("{/each}")
    if not found:
        fail(
            "#111: person timeline must {#each timeline}, {#each dayGroups}, "
            "or a windowed row list as chat rows"
        )
    return "\n".join(found)


def _css_var(blob: str, names: tuple[str, ...]) -> str | None:
    for name in names:
        m = re.search(rf"{re.escape(name)}\s*:\s*([^;]+);", blob)
        if m:
            return m.group(1).strip()
    return None

from tauri_gate.scan_parse import *
from tauri_gate.scan_rust import *
from tauri_gate.scan_tokens import *



def _chrome_en_text(crate: Path) -> str:
    return _chrome_lang_text(crate, "en")


def _tag_name(tag: str) -> str:
    m = re.match(r"</?([A-Za-z][\w-]*)", tag)
    return m.group(1) if m else ""
