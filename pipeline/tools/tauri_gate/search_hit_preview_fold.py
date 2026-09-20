"""#371 fold — PR #401 review (stale preview body, Space snap-back, tr copy).

Sibling of search_hit_preview.py (do not grow that file). Parent mix
unchanged: right data-search-preview, click/j/k select, Enter + person_id
still #124 jump. This fold locks three review items only.

Must-IDs: search-preview-fold-blank-body, search-preview-fold-space-noop,
search-preview-fold-tr-sorguya.
Placeholders Ada / Berk. Additive chrome only.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.import_boot_guards import _input_guard_span
from tauri_gate.last_read import _text, _web_file
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.scan import _match_closer, _without_comments
from tauri_gate.search_hit_preview import (
    _ACTIVATE,
    _JUMP_OR_VIEW,
    _KEY_ENTER,
    _KEY_SPACE,
    _SEARCH_BODY,
    _VOICE_PLAY,
    _enter_branch,
    _fn,
    _space_branch,
    _stale_guarded,
)
from tauri_gate.space_voice_note import _ROW_AUDIO

_ISSUE = "#371"

_BLANK_BODY = re.compile(r"\bpreviewBody\s*=\s*(?:[\"'][\"']|``)")
_PREVIEW_ID_SET = re.compile(r"\bpreviewMessageId\s*=")
_GEN_GUARD = re.compile(
    r"if\s*\(\s*(?:gen|id|mid|got|want|previewGen|bodyGen|searchBodyGen|"
    r"previewMessageId|previewId|messageId|message_id)\b[^)]{0,80}"
    r"(?:!==?|===?)"
)
_ON_ACTIVATE = re.compile(r"\bonActivate\s*\(")
_PREVENT = re.compile(r"\bpreventDefault\s*\(")
_INPUT_TAG = re.compile(r"tagName\s*===?\s*[\"']INPUT[\"']")
_FOCUS_KEY = "searchPreviewFocusQuery"
_TR_WANT = "Sorguya odaklan"
_TR_OLD = "Soruya odaklan"
_EN_WANT = "Focus query"
_FILL_NAMES = (
    "fillPreview",
    "loadPreview",
    "previewHit",
    "showPreview",
    "selectHit",
    "onSelectHit",
    "previewSelected",
)


def _fill_body(pane: str) -> str:
    for name in _FILL_NAMES:
        body = _fn(pane, name)
        if body and _SEARCH_BODY.search(body):
            return body
    return _fn(pane, "fillPreview")


def _drop_missing_hit_early(prefix: str) -> str:
    """clearPreview() on if (!h) must not count as blanking before searchBody."""
    early = re.search(r"if\s*\(\s*!h\s*\)\s*\{", prefix)
    if not early:
        early = re.search(
            r"if\s*\(\s*!h\s*\|\|\s*h\s*==\s*null\s*\)\s*\{",
            prefix,
        )
    if not early:
        return prefix
    brace = prefix.find("{", early.start())
    if brace < 0:
        return prefix
    end = _match_closer(prefix, brace)
    if end < 0:
        return prefix
    return prefix[: early.start()] + prefix[end + 1 :]


def _before_search_body(fill: str) -> str:
    m = _SEARCH_BODY.search(fill)
    if not m:
        return ""
    return _drop_missing_hit_early(fill[: m.start()])


def _after_search_body(fill: str) -> str:
    m = _SEARCH_BODY.search(fill)
    return fill[m.end() :] if m else ""


def _space_after_input(hits_key: str, guard: tuple[int, int] | None) -> str:
    rest = hits_key
    if guard:
        rest = hits_key[: guard[0]] + "\n" + hits_key[guard[1] :]
    return _space_branch(rest)


def assert_search_hit_preview_fold(crate: Path) -> None:
    """#371 fold: blank previewBody before searchBody; Space no-op; Sorguya."""
    pane_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not pane_path.is_file():
        fail(f"{_ISSUE}: SearchPane.svelte required (fillPreview / onHitsKey)")
    pane = pane_path.read_text()
    pane_c = _without_comments(pane)
    fill = _fill_body(pane_c) or _fill_body(pane)
    hits_key = _fn(pane_c, "onHitsKey") or _fn(pane, "onHitsKey")

    en_p = crate / "web" / "lib" / "locales" / "en.ts"
    tr_p = crate / "web" / "lib" / "locales" / "tr.ts"
    en = _chrome_pack_entries(_text(en_p)) if en_p.is_file() else {}
    tr = _chrome_pack_entries(_text(tr_p)) if tr_p.is_file() else {}

    # Keep: fillPreview + searchBody + gen / previewMessageId guard (pass today).
    if not fill:
        fail(
            f"{_ISSUE}: keep fillPreview — always api.searchBody on highlight "
            "(gen / previewMessageId guard stays)"
        )
    if not _SEARCH_BODY.search(fill):
        fail(
            f"{_ISSUE}: fillPreview must still await api.searchBody "
            "(no new IPC; stale replies still gen-guarded)"
        )
    if not _PREVIEW_ID_SET.search(fill):
        fail(
            f"{_ISSUE}: fillPreview still sets previewMessageId "
            "(attachments may paint immediately; body must not)"
        )
    post = _after_search_body(fill)
    if not (_GEN_GUARD.search(post) or _stale_guarded(fill)):
        fail(
            f"{_ISSUE}: keep the previewGen / previewMessageId guard after "
            "api.searchBody (stale Ada reply must not overwrite Berk)"
        )

    # 1) stale preview body — fail today: previewMessageId before blank body.
    prefix = _before_search_body(fill)
    if not prefix:
        fail(
            f"{_ISSUE}: fillPreview must await api.searchBody "
            "(blank previewBody before that await)"
        )
    if not _BLANK_BODY.search(prefix):
        fail(
            f"{_ISSUE}: fillPreview must assign previewBody = \"\" before "
            "await api.searchBody (switching Ada → Berk must not keep Ada's "
            "body under Berk's photo)"
        )

    # Keep: Enter still #124; INPUT early-return so #q types; #316 People Space.
    if not hits_key:
        fail(f"{_ISSUE}: keep onHitsKey — Enter jumps; Space is a no-op")
    if not _KEY_ENTER.search(hits_key):
        fail(f"{_ISSUE}: keep onHitsKey Enter → activateHit when person_id is set (#124)")
    enter_arm = _enter_branch(hits_key)
    if not _ACTIVATE.search(hits_key) and not re.search(
        r"\bonJumpToMessage\s*\(", enter_arm
    ):
        fail(f"{_ISSUE}: keep onHitsKey Enter → activateHit (#124)")
    guard = _input_guard_span(hits_key)
    if not guard or not _INPUT_TAG.search(hits_key[guard[0] : guard[1]]):
        fail(
            f"{_ISSUE}: onHitsKey must still return early on INPUT "
            "so #q types a space"
        )
    keys = _text(_web_file(crate, "PeopleKeys.ts"))
    if not _KEY_SPACE.search(keys) or not _ROW_AUDIO.search(keys):
        fail(
            f"{_ISSUE}: keep #316 PeopleKeys Space on "
            "[data-tl-index=\"${{tlIndex}}\"] [data-voice-note] audio "
            "(do not invent Search Space-play)"
        )

    # 2) Space snap-back — fail today: no preventDefault on Space.
    if guard:
        pre = hits_key[: guard[0]]
        inner = hits_key[guard[0] : guard[1]]
        if _KEY_SPACE.search(pre) and _PREVENT.search(pre):
            fail(
                f"{_ISSUE}: #q INPUT still types a space — preventDefault Space "
                "after the INPUT early-return"
            )
        if _KEY_SPACE.search(inner) and _PREVENT.search(inner):
            fail(
                f"{_ISSUE}: #q INPUT still types a space — do not preventDefault "
                "Space inside the INPUT guard"
            )
    space_arm = _space_after_input(hits_key, guard)
    if not space_arm.strip():
        fail(
            f"{_ISSUE}: Space on the hit list must preventDefault (no-op) so a "
            "focused row button does not snap back via onActivate — do not "
            "activateHit / jump; #q INPUT still types a space"
        )
    if not _PREVENT.search(space_arm):
        fail(
            f"{_ISSUE}: Space on the hit list must preventDefault (no-op) so a "
            "focused row button does not snap back via onActivate — do not "
            "activateHit / jump; #q INPUT still types a space"
        )
    if (
        _ACTIVATE.search(space_arm)
        or _ON_ACTIVATE.search(space_arm)
        or _JUMP_OR_VIEW.search(space_arm)
    ):
        fail(
            f"{_ISSUE}: Space on the hit list is a no-op — do not activateHit / "
            "onActivate / jump (Enter still #124; do not invent Search Space-play)"
        )
    if _VOICE_PLAY.search(space_arm) or _VOICE_PLAY.search(hits_key):
        fail(
            f"{_ISSUE}: Space does not Search-play — #316 stays People "
            "(do not invent Search Space-play)"
        )

    # 3) tr copy — fail today: "Soruya odaklan".
    if _FOCUS_KEY not in en or _FOCUS_KEY not in tr:
        fail(
            f"{_ISSUE}: {_FOCUS_KEY} stays the same ChromeKey on en.ts + tr.ts"
        )
    en_val = (en.get(_FOCUS_KEY) or "").strip()
    tr_val = (tr.get(_FOCUS_KEY) or "").strip()
    if en_val != _EN_WANT:
        fail(
            f"{_ISSUE}: en {_FOCUS_KEY} stays \"{_EN_WANT}\" "
            f"(tr is \"{_TR_WANT}\")"
        )
    if tr_val == _TR_OLD or tr_val != _TR_WANT:
        fail(
            f"{_ISSUE}: tr {_FOCUS_KEY} must be \"{_TR_WANT}\" "
            f"(query, matching typeAQuery \"Bir sorgu yazın\") — not \"{_TR_OLD}\""
        )
