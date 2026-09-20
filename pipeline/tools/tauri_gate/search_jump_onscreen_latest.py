"""#400 fold — PR #404 review (Latest/End yank during jump settle).

Sibling of search_jump_onscreen.py (do not grow that file). Parent mix
unchanged: one lander inside openPersonAtMessage, post-mount top-inset
pinJump, clip-only ensureTlIndexVisible for j/k. This fold locks the
Latest fight only.

Must-IDs: search-jump-onscreen-latest-clear,
search-jump-onscreen-latest-no-pin, search-jump-onscreen-latest-else,
search-jump-onscreen-latest-keep-400-313-jk.
Placeholders Ada / Berk. Additive chrome only.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.last_read import _text, _web_file
from tauri_gate.scan import (
    _expand_fn_calls,
    _match_closer,
    _svelte_markup,
    _without_comments,
)
from tauri_gate.search_jump_onscreen import (
    _CLIP_BOT,
    _CLIP_TOP,
    _DOUBLE_RAF,
    _ENSURE,
    _KEY_JK,
    _fn,
    _has_measured_top_pin,
    _writes_outside_clip,
)

_ISSUE = "#400"

_PIN_JUMP = re.compile(r"\bpinJump\s*\(")
_CLEAR_JUMP = re.compile(
    r"\bclearJumpPin\s*\("
    r"|\bjumpPinIndex\s*=\s*-1\b"
    r"|\bstopPin\s*\("
)
_LATEST_BAIL = re.compile(
    r"if\s*\(\s*pinLatestObs\s*\)[\s\S]{0,120}?return"
    r"|if\s*\(\s*pinLatestObs\s*!=\s*null\s*\)[\s\S]{0,120}?return"
    r"|if\s*\(\s*!\s*pinLatestObs\s*\)"
)
_WRITE = re.compile(r"\bwriteScrollTop\s*\(|\.scrollTop\s*=")
_ADJ_REPIN = re.compile(
    r"if\s*\(\s*jumpPinIndex\s*>=\s*0\s*\)\s*pinJump\s*\(\s*jumpPinIndex\s*\)"
)
_WATCH_600 = re.compile(r"setTimeout\s*\(\s*stopPinLatest\s*,\s*600\s*\)")
_END_KEY = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']End[\"']"
    r"|[\"']End[\"']\s*===?\s*(?:e\.)?key"
)
_T_LATEST = re.compile(r"""\bt\s*\(\s*["']latest["']\s*\)""")
_OVERLAY = re.compile(r"<TimelineLatest\b")
_FAMILY = (
    "clearJumpPin",
    "stopPinLatest",
    "watchPinLatest",
    "scrollToLatest",
    "stopPin",
)
_PRIMARY = (
    f"{_ISSUE}: Latest / End must clearJumpPin (scrollToLatest / "
    "watchPinLatest / stopPinLatest) so pinJump cannot yank back to the "
    "hit while pinLatestObs is set"
)


def _family_blob(list_src: str, name: str) -> str:
    """Body plus Latest-family callees (clearJumpPin / stopPinLatest / …)."""
    seen: set[str] = set()
    chunks: list[str] = []
    stack = [name]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        body = _fn(list_src, n)
        if not body:
            continue
        chunks.append(body)
        for callee in _FAMILY:
            if callee in seen:
                continue
            if re.search(rf"\b{re.escape(callee)}\s*\(", body):
                stack.append(callee)
    return "\n".join(chunks)


def _clears_jump_pin(blob: str) -> bool:
    return bool(_CLEAR_JUMP.search(blob))


def _bails_when_latest(body: str) -> bool:
    m = _WRITE.search(body)
    prefix = body[: m.start()] if m else body
    return bool(_LATEST_BAIL.search(prefix))


def _else_if_pinjump_unguarded(flush: str) -> bool:
    """True when an else-if calls pinJump with no pinLatestObs on that arm."""
    i = 0
    while True:
        m = re.search(r"else\s+if\s*\(", flush[i:])
        if not m:
            return False
        abs_start = i + m.start()
        open_p = flush.find("(", abs_start)
        if open_p < 0:
            return False
        close_p = _match_closer(flush, open_p)
        if close_p < 0:
            return False
        cond = flush[open_p : close_p + 1]
        after = flush[close_p + 1 :].lstrip()
        if after.startswith("{"):
            brace = flush.find("{", close_p)
            end = _match_closer(flush, brace)
            if end < 0:
                return False
            body = flush[brace + 1 : end]
            nxt = end + 1
        else:
            semi = flush.find(";", close_p)
            end = semi if semi >= 0 else close_p + 80
            body = flush[close_p + 1 : end + 1]
            nxt = end + 1
        if (
            _PIN_JUMP.search(body)
            and "pinLatestObs" not in cond
            and "pinLatestObs" not in body
        ):
            return True
        i = nxt


def assert_search_jump_onscreen_latest(crate: Path) -> None:
    """#400 fold: Latest/End cancel the jump pin; no pinJump while Latest."""
    list_path = _web_file(crate, "TimelineList.svelte")
    pane_path = _web_file(crate, "TimelinePane.svelte")
    keys_path = _web_file(crate, "PeopleKeys.ts")
    if not list_path.is_file():
        fail(f"{_ISSUE}: TimelineList.svelte required (pinJump / Latest overlay)")
    if not pane_path.is_file():
        fail(f"{_ISSUE}: TimelinePane.svelte required (openPersonAtMessage lander)")
    if not keys_path.is_file():
        fail(f"{_ISSUE}: PeopleKeys.ts required (j/k clip-only; End → Latest)")

    list_raw = list_path.read_text()
    pane_raw = pane_path.read_text()
    keys_raw = _text(keys_path)
    list_src = _without_comments(list_raw)
    pane = _without_comments(pane_raw)
    keys = _without_comments(keys_raw)
    list_m = _svelte_markup(list_raw)

    open_at = _fn(pane, "openPersonAtMessage") or _fn(
        pane_raw, "openPersonAtMessage"
    )
    pin = _fn(list_src, "pinJump") or _fn(list_raw, "pinJump")
    flush = _fn(list_src, "flushRowMeasures") or _fn(list_raw, "flushRowMeasures")
    ensure = _fn(list_src, "ensureTlIndexVisible") or _fn(
        list_raw, "ensureTlIndexVisible"
    )
    scroll = _fn(list_src, "scrollToLatest") or _fn(list_raw, "scrollToLatest")
    watch = _fn(list_src, "watchPinLatest") or _fn(list_raw, "watchPinLatest")
    stop = _fn(list_src, "stopPinLatest") or _fn(list_raw, "stopPinLatest")

    # --- keep-checks (pass today) ---

    # search-jump-onscreen-latest-keep-400
    if not open_at:
        fail(f"{_ISSUE}: keep openPersonAtMessage — post-mount top-inset pinJump")
    if not _PIN_JUMP.search(open_at):
        fail(
            f"{_ISSUE}: keep #400 — openPersonAtMessage still pinJump after "
            "the mounted [data-tl-index] (Search Enter / gallery lander)"
        )
    if not _DOUBLE_RAF.search(open_at):
        fail(
            f"{_ISSUE}: keep #400 — openPersonAtMessage still tick + double "
            "requestAnimationFrame then pinJump"
        )
    if not pin:
        fail(f"{_ISSUE}: keep pinJump — measured top inset of #person-timeline")
    if not _has_measured_top_pin(pin):
        fail(
            f"{_ISSUE}: keep #400 pinJump — after [data-tl-index] is mounted, "
            "small top inset from the measured rect (Ada's hit on screen)"
        )

    # search-jump-onscreen-latest-keep-313
    if not _OVERLAY.search(list_m) or not _T_LATEST.search(list_m):
        fail(
            f"{_ISSUE}: keep #313 TimelineLatest overlay "
            "(t(\"latest\") — still goes to newest)"
        )
    if "scrollToLatest" not in list_m and "scrollToLatest" not in list_src:
        fail(f"{_ISSUE}: keep #313 TimelineLatest onclick={{scrollToLatest}}")
    if not re.search(r"\bshowLatest\b", list_src):
        fail(f"{_ISSUE}: keep #313 showLatest (hide at the bottom; show when not)")
    if not scroll:
        fail(f"{_ISSUE}: keep #313 scrollToLatest")
    if not watch:
        fail(f"{_ISSUE}: keep #313 watchPinLatest")
    if "watchPinLatest" not in scroll and "pinTimelineLatest" not in scroll:
        fail(
            f"{_ISSUE}: keep #313 scrollToLatest → watchPinLatest "
            "(Latest overlay still pins newest)"
        )
    if not _WATCH_600.search(watch) and not _WATCH_600.search(list_src):
        fail(
            f"{_ISSUE}: keep #313 watchPinLatest setTimeout(stopPinLatest, 600)"
        )
    if not _END_KEY.search(keys) or "scrollToLatest" not in keys:
        fail(f"{_ISSUE}: keep #313 End → scrollToLatest (same Latest pin)")

    # search-jump-onscreen-latest-keep-jk
    if not ensure:
        fail(
            f"{_ISSUE}: keep ensureTlIndexVisible — clip-only for j/k / Find / "
            "Last time jump"
        )
    if not (_CLIP_TOP.search(ensure) and _CLIP_BOT.search(ensure)):
        fail(
            f"{_ISSUE}: keep ensureTlIndexVisible clip-only "
            "(rowTop < viewTop / rowBottom > viewBottom) for j/k"
        )
    if _writes_outside_clip(ensure):
        fail(
            f"{_ISSUE}: keep ensureTlIndexVisible clip-only — do not top-inset "
            "inside ensure (j/k stay a nudge)"
        )
    if not _KEY_JK.search(keys) or not _ENSURE.search(keys):
        fail(
            f"{_ISSUE}: keep j/k → ensureTlIndexVisible "
            "(clip-only nudge, not a top pin)"
        )

    # Last time re-pin stays on the adj branch (not the unguarded else)
    if not flush:
        fail(f"{_ISSUE}: keep flushRowMeasures — Last time re-pin on adj branch")
    if not _ADJ_REPIN.search(flush):
        fail(
            f"{_ISSUE}: keep Last time re-pin — adj branch still "
            "if (jumpPinIndex >= 0) pinJump(jumpPinIndex) when Latest is not live"
        )

    # --- new behavior (fail today) ---

    # search-jump-onscreen-latest-clear
    for name, body in (
        ("scrollToLatest", scroll),
        ("watchPinLatest", watch),
        ("stopPinLatest", stop),
    ):
        if not body:
            fail(
                f"{_ISSUE}: {name} required — Latest / End must clearJumpPin "
                "so pinJump cannot yank back while pinLatestObs is set"
            )
        blob = _family_blob(list_src, name) or body
        if name == "scrollToLatest":
            blob = blob + "\n" + _expand_fn_calls(list_src, body, 3)
        if not _clears_jump_pin(blob):
            fail(_PRIMARY)

    # search-jump-onscreen-latest-no-pin
    if not _bails_when_latest(pin):
        fail(
            f"{_ISSUE}: pinJump must not write while pinLatestObs is set "
            "(Latest / End 600ms settle; pending double-rAF retry included)"
        )

    # search-jump-onscreen-latest-else
    if _else_if_pinjump_unguarded(flush):
        fail(
            f"{_ISSUE}: flushRowMeasures must not else if (pin >= 0) "
            "pinJump(pin) while Latest is live — no unguarded else; keep "
            "adj-branch jumpPinIndex >= 0 re-pin; skip while pinLatestObs"
        )
