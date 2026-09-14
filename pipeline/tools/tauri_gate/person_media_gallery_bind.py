"""#361 bind — scroller-bind $effect must not zero scrollTop.

Sibling of person_media_gallery_click.py (do not grow that file). One
review bug only. Do not reopen the #361 mix, the video-stack / scroll
folds, the race gen/open-gate, or the click overlay token.

The scroller-bind $effect (galleryEl / ResizeObserver / viewportH from
clientHeight) still does el.scrollTop = 0 and then measureRowH(), which
reads/writes rowH. Svelte 5 tracks that $state read, so a later pitch
change (first measure 232→real height, window resize, ResizeObserver)
re-runs the effect and yanks a scrolled virtualized grid back to the
top. Reload already zeros scrollTop / galleryEl.scrollTop in the
open / selectedId / includeGroups effect.

Must-IDs: gallery-bind-no-scroll-zero.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.person_media_gallery_fold import (
    _EL_SCROLL_ZERO,
    _STATE_SCROLL_ZERO,
    _VIEWPORT_ASSIGN,
    _reload_effects,
    _zeros_bound_scroller,
)
from tauri_gate.scan import _function_body, _match_closer, _without_comments
from tauri_gate.status_toasts_toast import _svelte_effect_args

_ISSUE = "#361"

_RO = re.compile(r"(?:new\s+)?\bResizeObserver\s*\(")
_UNTRACK = re.compile(r"\buntrack\s*\(")
_MEASURE = re.compile(r"\bmeasureRowH\s*\(")
_ROW_H = re.compile(r"\browH\b")
_GALLERY_EL = re.compile(r"\bgalleryEl\b|(?:const|let|var)\s+el\b")


def _strip_calls(src: str, open_rx: re.Pattern[str]) -> str:
    """Blank out `name(...)` argument blobs (ResizeObserver / untrack)."""
    out = src
    while True:
        m = open_rx.search(out)
        if not m:
            return out
        open_p = out.find("(", m.end() - 1)
        if open_p < 0:
            return out
        close = _match_closer(out, open_p)
        if close < 0:
            return out
        out = out[: m.start()] + " " * (close + 1 - m.start()) + out[close + 1 :]


def _assigns_scroll_zero(body: str) -> bool:
    return bool(_STATE_SCROLL_ZERO.search(body) or _zeros_bound_scroller(body))


def _is_reload(arg: str, reloads: list[str]) -> bool:
    return arg in reloads


def _is_bind_effect(arg: str) -> bool:
    """Scroller-bind / mount $effect: galleryEl + viewportH/clientHeight or RO."""
    has_ro = bool(_RO.search(arg))
    has_viewport = bool(_VIEWPORT_ASSIGN.search(arg) and re.search(r"\bclientHeight\b", arg))
    has_el = bool(_GALLERY_EL.search(arg) or _EL_SCROLL_ZERO.search(arg))
    return has_ro or (has_viewport and has_el)


def _bind_effects(src: str, reloads: list[str]) -> list[str]:
    out: list[str] = []
    for arg in _svelte_effect_args(src):
        if _is_reload(arg, reloads):
            continue
        if _is_bind_effect(arg):
            out.append(arg)
    return out


def _non_reload_scroll_zeros(src: str, reloads: list[str]) -> list[str]:
    out: list[str] = []
    for arg in _svelte_effect_args(src):
        if _is_reload(arg, reloads):
            continue
        if _assigns_scroll_zero(arg):
            out.append(arg)
    return out


def _rowh_untracked_in(body: str) -> bool:
    """True when every `rowH` sits inside untrack(...) (or rowH is absent)."""
    if not _ROW_H.search(body):
        return True
    return not _ROW_H.search(_strip_calls(body, _UNTRACK))


def _bind_tracks_rowh(arg: str, dlg: str) -> bool:
    """True when the bind effect can re-run because rowH is tracked."""
    tracked = _strip_calls(_strip_calls(arg, _RO), _UNTRACK)
    has_measure = bool(_MEASURE.search(tracked))
    has_rowh = bool(_ROW_H.search(tracked))
    if not has_measure and not has_rowh:
        return False
    if has_measure:
        measure = _function_body(dlg, "measureRowH")
        if measure and _rowh_untracked_in(measure) and not has_rowh:
            return False
    return True


def assert_person_media_gallery_bind(crate: Path) -> None:
    """#361 bind: scroller-bind $effect must not zero scrollTop / track rowH."""
    dlg_path = crate / "web" / "lib" / "PersonMediaDialog.svelte"
    if not dlg_path.is_file():
        fail(
            f"{_ISSUE}: PersonMediaDialog.svelte required "
            "(scroller-bind $effect must not assign el.scrollTop = 0; "
            "reload $effect still zeros on open / selectedId / includeGroups)"
        )
    dlg_raw = dlg_path.read_text()
    dlg = _without_comments(dlg_raw)

    reloads = _reload_effects(dlg) or _reload_effects(dlg_raw)
    bind_src = dlg if _svelte_effect_args(dlg) else dlg_raw

    # --- gallery-bind-no-scroll-zero (primary red today) ---
    zeros = _non_reload_scroll_zeros(bind_src, reloads)
    if not zeros and bind_src is dlg:
        zeros = _non_reload_scroll_zeros(dlg_raw, _reload_effects(dlg_raw))
    if zeros:
        fail(
            f"{_ISSUE}: scroller-bind $effect must not assign "
            "el.scrollTop = 0 (or galleryEl.scrollTop / scrollTop) — "
            "only read viewportH from clientHeight and observe resize; "
            "a later pitch measure or ResizeObserver re-run must not "
            "yank a scrolled virtualized grid to the top "
            "(reload $effect still zeros on open / selectedId / includeGroups)"
        )

    binds = _bind_effects(bind_src, reloads)
    if not binds and bind_src is dlg:
        binds = _bind_effects(dlg_raw, _reload_effects(dlg_raw))
        track_src = dlg_raw
    else:
        track_src = bind_src
    for arg in binds:
        if _bind_tracks_rowh(arg, track_src):
            fail(
                f"{_ISSUE}: scroller-bind $effect must not let "
                "measureRowH / rowH retrigger it — untrack the rowH "
                "read/write, or move measure out of the bind effect "
                "(a pitch change must not re-run the bind effect)"
            )

    # Reload must still zero — do not "fix" bind by deleting the fold reset.
    if not reloads:
        fail(
            f"{_ISSUE}: gallery reload $effect (open / selectedId / "
            "includeGroups) required — it must still zero scrollTop"
        )
    reload_blob = "\n".join(reloads)
    if not _STATE_SCROLL_ZERO.search(reload_blob) or not _zeros_bound_scroller(
        reload_blob
    ):
        fail(
            f"{_ISSUE}: gallery reload $effect (open / selectedId / "
            "includeGroups) must still assign scrollTop = 0 and zero "
            "the bound scroller (galleryEl.scrollTop = 0)"
        )
