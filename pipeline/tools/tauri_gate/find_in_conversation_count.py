"""#310 fold — find hit counter `2/17`.

Sibling of find_in_conversation.py (do not grow that file). Quiet
current/total next to the pane find field. First hit as you type is
1/N. Enter increments; Shift+Enter decrements (wrap). Empty query
hides the count. Zero hits is 0/0 (no Search EmptyState, no
“No messages in this view”). Spoken copy (`2 of 17` / aria) en+tr.

Must-IDs: find-count-surface, find-count-empty-hide, find-count-zero,
find-count-first-1, find-count-enter, find-count-shift-wrap,
find-count-quiet, find-count-spoken.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.find_in_conversation import (
    _ENTER,
    _FIND_HOOK,
    _FIND_Q,
    _ISSUE,
    _SHIFT_ENTER,
    _field_tag,
    _find_logic,
    _pane_blob,
    _read,
)
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.scan import _svelte_markup, _template_stack, _without_comments

_FIELD = re.compile(
    r"id=[\"']tl-find[\"']|data-tl-find(?:\s|=|[\"'/>])",
    re.I,
)
# Visible `2/17` / `1/N` — not {#if} / {:else} / {/if}.
_SLASH_INTERP = re.compile(
    r"\{(?!#|/|:)[^}]{1,80}\}\s*/\s*\{(?!#|/|:)[^}]{1,80}\}"
)
_SLASH_TEMPLATE = re.compile(
    r"`\$\{[^}]{1,80}\}\s*/\s*\$\{[^}]{1,80}\}`"
    r"|[\"']\$\{[^}]{1,80}\}\s*/\s*\$\{[^}]{1,80}\}[\"']"
)
_ZERO_ZERO = re.compile(r"[\"'`]0/0[\"'`]")
# Hooks that do not steal parent `_FIND_HOOK` (`data-tl-find` / id tl-find).
_COUNT_HOOK = re.compile(
    r"data-(?:tl-)?(?:find-)?hit-count"
    r"|id=[\"'](?:tl-)?(?:find-count|hit-count)[\"']",
    re.I,
)
_COUNT_FN = re.compile(
    r"\b(?:findCount|formatFindCount|findHitCount|findPosLabel|"
    r"findCountLabel|hitCountLabel|formatHitCount|findCountParts)\b"
)
_ONE_BASED = re.compile(
    r"indexOf\s*\([^)]{0,60}\)\s*\+\s*1"
    r"|\bi\s*<\s*0\s*\?\s*1"
    r"|(?:current|findPos|findHit|findCur|findIndex)\s*[:=]\s*1\b"
)
_INDEX_OF_TL = re.compile(r"indexOf\s*\(\s*tlIndex\b")
_POS_INC = re.compile(
    r"(?:findPos|findHit|findCur|findHitIndex)\s*(?:\+\+|=\s*[^;\n]{0,24}\+\s*1)"
)
_WRAP = re.compile(r"%\s*(?:hits|findHits)\.length")
_T_CALL = re.compile(r"""\bt\s*\(\s*["']([A-Za-z_][\w]*)["']""")
_SPOKEN = re.compile(
    r"\bof\s*\$\{|\$\{[^}]+\}\s+of\b"
    r"|[\"'`][^\"'`]{0,24}\bof\b[^\"'`]{0,24}[\"'`]",
    re.I,
)
_ATTR = re.compile(
    r"""(?:aria-label|aria-valuetext|title|placeholder)\s*=\s*\{?[^>\n]+""",
    re.I,
)
_INPUT = re.compile(r"<(?:Input|input)\b[^>]*>", re.I)
_NEAR = 520


def _near_field(markup: str) -> str:
    m = _FIELD.search(markup) or _FIND_HOOK.search(markup)
    if not m:
        return ""
    a = max(0, m.start() - _NEAR)
    b = min(len(markup), m.end() + _NEAR)
    return markup[a:b]


def _visible_near(near: str) -> str:
    return _ATTR.sub(" ", _INPUT.sub(" ", near))


def _slash_in(src: str) -> bool:
    return bool(_SLASH_INTERP.search(src) or _SLASH_TEMPLATE.search(src))


def _has_count_surface(near: str, logic: str) -> bool:
    vis = _visible_near(near)
    if _slash_in(vis):
        return True
    if _COUNT_HOOK.search(vis) and (_slash_in(near) or _slash_in(logic) or _ZERO_ZERO.search(logic)):
        return True
    if _COUNT_FN.search(vis) and (_slash_in(logic) or _ZERO_ZERO.search(logic)):
        return True
    return False


def _count_pos(markup: str) -> int:
    m = _FIELD.search(markup) or _FIND_HOOK.search(markup)
    start = m.start() if m else 0
    lo = max(0, start - _NEAR)
    hi = min(len(markup), start + _NEAR)
    chunk = markup[lo:hi]
    for rx in (_SLASH_INTERP, _SLASH_TEMPLATE, _COUNT_HOOK, _COUNT_FN):
        hit = rx.search(chunk)
        if hit:
            return lo + hit.start()
    return -1


def _empty_hides(markup: str, logic: str, near: str) -> bool:
    pos = _count_pos(markup)
    if pos >= 0:
        for kind, cond, _ in _template_stack(markup, pos):
            if kind not in {"if", "if-else"}:
                continue
            if not _FIND_Q.search(cond):
                continue
            if re.search(r"!(?:findQ|findQuery|tlFind)", cond):
                continue
            return True
    blob = near + "\n" + logic
    if re.search(
        r"(?:findQ|findQuery|tlFind)\b[^?\n]{0,48}\?[^:]{0,120}:\s*[\"'][\"']",
        blob,
    ):
        return True
    if re.search(
        r"if\s*\(\s*!(?:q|findQ|findQuery|tlFind)\b[\s\S]{0,120}return\s+[\"'][\"']",
        logic,
    ):
        return True
    if re.search(
        r"(?:findQ|findQuery|tlFind|q)\s*(?:===?|\.trim\(\)[^\n]{0,40}===?)\s*[\"'][\"']"
        r"[\s\S]{0,120}return\s+[\"'][\"']",
        logic,
    ):
        return True
    return False


def _has_zero_zero(near: str, logic: str) -> bool:
    if _ZERO_ZERO.search(near) or _ZERO_ZERO.search(logic):
        return True
    empty_hits = re.search(
        r"(?:hits|findHits)\.length\s*(?:===?|==)\s*0"
        r"|!\s*(?:hits|findHits)\.length",
        logic,
    )
    zero_cur = re.search(
        r"(?:current|pos|findPos|findHit|total)\s*[:=]\s*0\b"
        r"|return\s*\{\s*(?:current|pos)\s*:\s*0",
        logic,
    )
    return bool(empty_hits and zero_cur and _slash_in(near + "\n" + logic))


def _count_follows_step(logic: str) -> bool:
    if _INDEX_OF_TL.search(logic) or _ONE_BASED.search(logic):
        return True
    if _ENTER.search(logic) and _POS_INC.search(logic):
        return True
    return False


def _count_wraps(logic: str) -> bool:
    if _WRAP.search(logic) and (_INDEX_OF_TL.search(logic) or _COUNT_FN.search(logic)):
        return True
    if re.search(r"\bstepFindIndex\b", logic) and (
        _INDEX_OF_TL.search(logic) or _ONE_BASED.search(logic)
    ):
        return True
    return False


def _spoken_keys(near: str) -> list[str]:
    chrome = _visible_near(near)
    return [m.group(1) for m in _T_CALL.finditer(chrome)]


def assert_find_in_conversation_count(crate: Path) -> None:
    """#310 fold: quiet current/total (`2/17`) next to the pane find field."""
    pane_path = crate / "web" / "lib" / "TimelinePane.svelte"
    if not pane_path.is_file():
        fail(f"{_ISSUE}: TimelinePane.svelte required (find hit counter 2/17)")
    pane = _without_comments(_pane_blob(crate))
    logic = _find_logic(crate)
    markup = _svelte_markup(pane)
    near = _near_field(markup)
    empty = _read(crate, "TimelineEmpty.svelte")
    tag = _field_tag(markup)

    # 1) find-count-surface — quiet `2/17` / `1/N` next to #tl-find.
    if not _has_count_surface(near, logic):
        fail(
            f"{_ISSUE}: pane find field must show a quiet current/total "
            "next to the field (e.g. 2/17 or 1/N)"
        )
    if tag and _slash_in(tag) and not _slash_in(_visible_near(near)):
        fail(
            f"{_ISSUE}: current/total must be visible next to the pane find "
            "field (e.g. 2/17) — not only a title / aria on the input"
        )

    # 2) find-count-empty-hide
    if not _empty_hides(markup, logic, near):
        fail(
            f"{_ISSUE}: empty find query must hide the current/total "
            "(no leftover 2/17 / 0/0 when the field is cleared)"
        )

    # 3) find-count-zero
    if not _has_zero_zero(near, logic):
        fail(
            f"{_ISSUE}: zero in-conversation hits must show 0/0 "
            "(quiet — not Search EmptyState, not “No messages in this view”)"
        )

    # 4) find-count-first-1
    if not _ONE_BASED.search(logic):
        fail(
            f"{_ISSUE}: first hit as you type must show 1/N "
            "(1-based current among loaded hits)"
        )

    # 5) find-count-enter
    if not _ENTER.search(logic) and not _ENTER.search(pane):
        fail(f"{_ISSUE}: Enter must increment the find count (1/N → 2/N)")
    if not _count_follows_step(logic):
        fail(
            f"{_ISSUE}: Enter must increment current/total (1/N → 2/N) — "
            "count follows the stepped hit (indexOf(tlIndex)+1 or findPos++)"
        )

    # 6) find-count-shift-wrap
    if not _SHIFT_ENTER.search(logic) and not _SHIFT_ENTER.search(pane):
        fail(
            f"{_ISSUE}: Shift+Enter must decrement the find count "
            "(wrap 1/N → N/N)"
        )
    if not _count_wraps(logic):
        fail(
            f"{_ISSUE}: Shift+Enter from 1/N must wrap current/total to N/N "
            "(same wrap as today’s step)"
        )

    # 7) find-count-quiet — 0/0 is not a Search / timeline empty CTA.
    if re.search(r"No hits", pane) or (
        re.search(r"No hits", empty) and _FIND_Q.search(empty)
    ):
        fail(
            f"{_ISSUE}: zero hits is 0/0 — do not mount Search EmptyState "
            "\"No hits\""
        )
    if _FIND_Q.search(empty) and re.search(r"No messages in this view", empty):
        fail(
            f"{_ISSUE}: zero hits is 0/0 — do not show "
            "\"No messages in this view\""
        )

    # 8) find-count-spoken — words (`2 of 17` / aria) need t() + en+tr.
    chrome = _visible_near(near)
    if _SPOKEN.search(chrome) or _SPOKEN.search(logic):
        keys = _spoken_keys(near)
        if not keys and not _T_CALL.search(logic):
            fail(
                f"{_ISSUE}: spoken find count (`2 of 17` / aria) must use t() "
                "(en+tr, #131)"
            )
        en_p = crate / "web" / "lib" / "locales" / "en.ts"
        tr_p = crate / "web" / "lib" / "locales" / "tr.ts"
        en = _chrome_pack_entries(en_p.read_text()) if en_p.is_file() else {}
        tr = _chrome_pack_entries(tr_p.read_text()) if tr_p.is_file() else {}
        for key in keys:
            if key == "findInThread":
                continue
            if key not in en or key not in tr:
                fail(
                    f"{_ISSUE}: spoken find-count key {key!r} must exist in "
                    "en.ts and tr.ts (#131)"
                )
            if re.search(r"\bof\b", en.get(key, ""), re.I) and tr.get(key) == en.get(key):
                fail(
                    f"{_ISSUE}: spoken find-count key {key!r} must differ in "
                    "tr.ts (en+tr, #131)"
                )
    if re.search(r"/Users/|/home/", pane + "\n" + logic):
        fail(f"{_ISSUE}: tests stay placeholders (Ada) — no real home paths")
