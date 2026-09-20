"""#400 — Search Enter / #124 jump must land the selected bubble on screen.

Confirmed mix (2026-09-20): one lander inside openPersonAtMessage (Search
Enter and PersonMediaDialog). After [data-tl-index] is mounted, pin a small
top inset (one ESTIMATED_ROW_HEIGHT or similar). estimateScrollToIndex may
stay as the first guess (* 2); final scroll is the measured rect. tick +
double rAF until mounted; re-pin after Last time / flushRowMeasures. No
{#key}. ensureTlIndexVisible stays clip-only for j/k / Find / Last time.

Must-IDs: union of 400-a/b/c research as they match this mix.
Placeholders Ada / Berk. Additive chrome only.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.find_in_conversation import _FIND_HOOK
from tauri_gate.last_read import (
    _EST,
    _LAST_TIME_T,
    _REMOUNT,
    _VIRTUALIZE,
    _text,
    _web_file,
)
from tauri_gate.scan import (
    _function_body,
    _match_closer,
    _svelte_markup,
    _ts_fn_body,
    _without_comments,
)
from tauri_gate.search_hit_preview import (
    _ACTIVATE,
    _JUMP_OR_VIEW,
    _KEY_ENTER,
    _KEY_J,
    _KEY_K,
    _OPEN_AT,
    _PERSON_GUARD,
    _SENT_AT_PAYLOAD,
    _TICK,
    _click_path,
    _enter_branch,
    _prop_assign,
)
from tauri_gate.search_hits_jump import _VIEW_PEOPLE
from tauri_gate.space_voice_note import _KEY_SPACE, _ROW_AUDIO
from tauri_gate.timeline_virtual import _FIXED_INDEX_TIMES_EST, _uses_prefix_sum

_ISSUE = "#400"

_ESTIMATE = re.compile(r"\bestimateScrollToIndex\s*\(")
_ENSURE = re.compile(r"\bensureTlIndexVisible\s*\(")
_WRITE = re.compile(r"\bwriteScrollTop\s*\(|\.scrollTop\s*=")
_MEASURE = re.compile(r"\bgetBoundingClientRect\s*\(|\browOffsetInPane\s*\(")
_TL_SEL = re.compile(r"data-tl-index")
_TIMES_TWO = re.compile(
    r"ESTIMATED_ROW_HEIGHT\s*\*\s*2|2\s*\*\s*ESTIMATED_ROW_HEIGHT"
)
_CLIP_TOP = re.compile(r"rowTop\s*<\s*viewTop")
_CLIP_BOT = re.compile(r"rowBottom\s*>\s*viewBottom")
_CENTER = re.compile(
    r"clientHeight\s*-\s*(?:rowH|rowHeight|\bh\b)\s*\)\s*/\s*2"
    r"|(?:clientHeight\s*-\s*(?:rowH|rowHeight))\s*/\s*2"
)
_INSET = re.compile(
    r"(?:rowTop|\btop\b|rowOffset)\s*-\s*"
    r"(?:ESTIMATED_ROW_HEIGHT|\b88\b|\b16\b|\b12\b|\b8\b|"
    r"[A-Za-z_]*(?:INSET|PAD|Inset|Pad)[A-Za-z_]*)"
)
_RAF = re.compile(r"\brequestAnimationFrame\s*\(")
_DOUBLE_RAF = re.compile(
    r"requestAnimationFrame\s*\(\s*(?:async\s*)?(?:function\s*\([^)]*\)\s*|"
    r"\(\s*[^)]*\)\s*=>\s*)?\{"
    r"[\s\S]{0,900}?requestAnimationFrame\s*\("
    r"|requestAnimationFrame\s*\(\s*(?:\(\s*\)\s*=>\s*)?requestAnimationFrame\s*\("
)
_SMOOTH = re.compile(r"""behavior\s*:\s*["']smooth["']""")
_SCROLL_INTO = re.compile(r"\bscrollIntoView\s*\(")
_SHOW_ERR = re.compile(r"\bshowErr\s*\(")
_TL_NEG = re.compile(r"tlIndex\s*=\s*-1\b")
_COLLAPSE = re.compile(r"selectedIds\s*=\s*new\s+Set\s*\(\s*\[\s*messageId")
_MESSAGE_SEEK = re.compile(r"\bmessage_id\s*===\s*messageId\b")
_APPLY_OPEN = re.compile(r"\bapplyOpenPersonWindow\s*\(")
_JUMP_MSG = re.compile(r"\bjumpToMessageId\s*\(")
_SET_TL = re.compile(r"\bsetTlIndex\s*\(")
_LOAD_OLDER = re.compile(r"\b(?:prependOlder|loadOlder|data-load-older)\b")
_FLUSH = re.compile(
    r"\b(?:flushRowMeasures|scheduleMeasureFlush|applyRowMeasure|"
    r"measureEpoch|pendingMeasures)\b"
)
_JUMP_TOKEN = re.compile(
    r"\b(?:jumpPin|jumpAlign|jumpToken|pinJump|landJump|jumpInset|"
    r"jumpPinIndex|alignJump|jumpLand|pinTlIndex)\b"
)
_UNMOUNTED = re.compile(
    r"if\s*\(\s*!\s*\(?\s*(?:mounted|row|el|node|found|hit|target)\b"
    r"|if\s*\(\s*(?:mounted|row|el|node|found)\s*==\s*null"
    r"|if\s*\(\s*!\s*\(\s*(?:mounted|row|el|node)\s+instanceof"
    r"|instanceof\s+HTMLElement"
)
_KEY_JK = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']j[\"']"
    r"|(?:e\.)?key\s*===?\s*[\"']J[\"']"
    r"|ArrowDown"
)

_EXPAND_SKIP = {
    "if",
    "for",
    "while",
    "switch",
    "catch",
    "function",
    "return",
    "Math",
    "Number",
    "String",
    "Boolean",
    "Error",
    "Set",
    "Map",
    "Promise",
    "parseInt",
    "parseFloat",
    "isFinite",
    "isNaN",
    "setTimeout",
    "clearTimeout",
    "setInterval",
    "clearInterval",
    "requestAnimationFrame",
    "cancelAnimationFrame",
    "tick",
    "document",
    "window",
    "console",
    "JSON",
    "Object",
    "Array",
    "getElementById",
    "querySelector",
    "querySelectorAll",
    "showErr",
    "friendly",
    "stopPin",
    "resetHeights",
    "ensureTlIndexVisible",
    "selectPerson",
    "applyOpenPersonWindow",
    "persistLastPerson",
    "persistLastRead",
    "personShow",
    "personConversations",
    "personTimeline",
    "findIndex",
    "some",
    "every",
    "map",
    "filter",
    "concat",
    "slice",
    "toReversed",
    "trim",
    "toLowerCase",
    "toUpperCase",
    "replace",
    "max",
    "min",
    "abs",
    "floor",
    "ceil",
    "round",
    "shiftHeightsForPrepend",
    "preserveScrollAfterPrepend",
    "stopPinLatest",
    "watchPinLatest",
    "pinTimelineLatest",
    "scrollToLatest",
    "pinDayAtTop",
    "jumpToMessageId",
    "jumpToLocalDay",
    "closeCopy",
    "copySelected",
    "oldestSentAt",
}

_PRIMARY = (
    f"{_ISSUE}: jump still uses * 2 as the final land / no post-mount pin — "
    "after [data-tl-index] is mounted, pin a small top inset from the measured "
    "rect (not estimateScrollToIndex * 2; not clip-only ensureTlIndexVisible)"
)


def _fn(src: str, name: str) -> str:
    return _ts_fn_body(src, name) or _function_body(src, name) or ""


def _post_hit(open_at: str) -> str:
    """Success path after the loaded window contains message_id."""
    miss = re.search(
        r"if\s*\(\s*(?:idx|index|found)\s*<\s*0\s*\)",
        open_at,
    )
    if miss:
        brace = open_at.find("{", miss.start())
        if brace >= 0:
            end = _match_closer(open_at, brace)
            if end >= 0:
                return open_at[end + 1 :]
    for pat in (
        r"tlIndex\s*=\s*idx\b",
        r"estimateScrollToIndex\s*\(",
        r"\btlIndex\s*=",
    ):
        m = re.search(pat, open_at)
        if m:
            return open_at[m.start() :]
    return open_at


def _called_names(blob: str) -> list[str]:
    return [
        n
        for n in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", blob)
        if n not in _EXPAND_SKIP
    ]


def _expand_land(list_src: str, pane_src: str, extra: str, post: str) -> str:
    chunks = [post]
    seen: set[str] = set()
    blob = post
    for _ in range(3):
        added = False
        for name in _called_names(blob):
            if name in seen or name in _EXPAND_SKIP:
                continue
            seen.add(name)
            body = _fn(list_src, name) or _fn(pane_src, name) or _fn(extra, name)
            if body:
                chunks.append(body)
                blob += "\n" + body
                added = True
        if not added:
            break
    return "\n".join(chunks)


def _writes_outside_clip(body: str) -> bool:
    if not _WRITE.search(body):
        return False
    if not (_CLIP_TOP.search(body) and _CLIP_BOT.search(body)):
        return True
    m = _CLIP_TOP.search(body)
    return bool(_WRITE.search(body[: m.start()]))


def _has_measured_top_pin(body: str) -> bool:
    if not _WRITE.search(body):
        return False
    if not _MEASURE.search(body):
        return False
    if not _TL_SEL.search(body):
        return False
    if not _writes_outside_clip(body):
        return False
    if _CENTER.search(body) and not _INSET.search(body):
        return False
    return True


def _measured_final_is_times_two(body: str) -> bool:
    """* 2 next to a measured write — not the estimateScrollToIndex first guess."""
    for m in _MEASURE.finditer(body):
        window = body[max(0, m.start() - 80) : m.start() + 280]
        if _TIMES_TWO.search(window) and _WRITE.search(window):
            return True
    return False


def _strip_estimate(land: str, est_body: str) -> str:
    return land.replace(est_body, "\n") if est_body else land


def _between_tl_and_article(src: str) -> str:
    m = re.search(r"<div\b[^>]*\bdata-tl-index\b[^>]*>", src, re.I)
    if not m:
        return ""
    art = src.find("<article", m.end())
    return src[m.end() : art] if art >= 0 else src[m.end() : m.end() + 800]


def _after_open_call(jump: str) -> str:
    m = re.search(r"\bopenPersonAtMessage\s*\(", jump)
    if not m:
        return ""
    paren = jump.find("(", m.start())
    if paren < 0:
        return jump[m.end() :]
    end = _match_closer(jump, paren)
    return jump[end + 1 :] if end >= 0 else jump[m.end() :]


def _retries_unmounted(blob: str) -> bool:
    if not _UNMOUNTED.search(blob):
        return False
    if not (_RAF.search(blob) or _TICK.search(blob)):
        return False
    # Missing node must not be the last word — rAF / tick retry after the check.
    for m in _UNMOUNTED.finditer(blob):
        window = blob[m.start() : m.start() + 500]
        if _RAF.search(window) or _TICK.search(window):
            return True
    return False


def _repins_after_measure(
    post: str, land: str, list_src: str, lander_names: list[str]
) -> bool:
    flush = _fn(list_src, "flushRowMeasures")
    named = [n for n in lander_names if n != "estimateScrollToIndex"]
    for name in named:
        if re.search(rf"\b{re.escape(name)}\s*\(", flush):
            return True
    if _JUMP_TOKEN.search(flush) and _WRITE.search(flush):
        return True
    if _TL_SEL.search(flush) and _WRITE.search(flush) and _MEASURE.search(flush):
        return True
    for name in named:
        if len(re.findall(rf"\b{re.escape(name)}\s*\(", post)) >= 2:
            return True
    m = _FLUSH.search(land)
    if m and _WRITE.search(land[m.start() :]):
        return True
    writes = list(_WRITE.finditer(land))
    if len(writes) >= 2 and _MEASURE.search(land):
        mid = land[writes[0].start() : writes[-1].start() + 1]
        if _RAF.search(mid) or _TICK.search(mid) or _FLUSH.search(mid):
            return True
    return False


def assert_search_jump_onscreen(crate: Path) -> None:
    """#400: Enter / gallery jump pins the mounted [data-tl-index] on screen."""
    pane_path = _web_file(crate, "TimelinePane.svelte")
    list_path = _web_file(crate, "TimelineList.svelte")
    search_path = _web_file(crate, "SearchPane.svelte")
    hits_path = _web_file(crate, "SearchHits.svelte")
    app_path = crate / "web" / "App.svelte"
    gallery_path = _web_file(crate, "PersonMediaDialog.svelte")
    keys_path = _web_file(crate, "PeopleKeys.ts")
    jump_path = _web_file(crate, "jumpDay.ts")
    rows_path = _web_file(crate, "TimelineRows.svelte")
    virt_path = _web_file(crate, "TimelineVirtual.ts")
    shell_path = _web_file(crate, "PeopleShell.svelte")
    if not pane_path.is_file():
        fail(f"{_ISSUE}: TimelinePane.svelte required (openPersonAtMessage lander)")
    if not list_path.is_file():
        fail(f"{_ISSUE}: TimelineList.svelte required (jump pin / ensure clip-only)")
    if not search_path.is_file():
        fail(f"{_ISSUE}: SearchPane.svelte required (Enter still #124; click does not jump)")
    if not app_path.is_file():
        fail(f"{_ISSUE}: App.svelte required (jumpToMessage → openPersonAtMessage)")
    if not gallery_path.is_file():
        fail(f"{_ISSUE}: PersonMediaDialog.svelte required (same #124 lander)")

    pane_raw, list_raw = pane_path.read_text(), list_path.read_text()
    search_raw = search_path.read_text()
    hits_raw = _text(hits_path)
    app_raw = app_path.read_text()
    gallery_raw = gallery_path.read_text()
    keys_raw = _text(keys_path)
    jump_raw = _text(jump_path)
    rows_raw = _text(rows_path)
    virt_raw = _text(virt_path)
    shell_raw = _text(shell_path)

    pane = _without_comments(pane_raw)
    list_src = _without_comments(list_raw)
    search = _without_comments(search_raw)
    hits = _without_comments(hits_raw)
    app = _without_comments(app_raw)
    gallery = _without_comments(gallery_raw)
    keys = _without_comments(keys_raw)
    jump_src = _without_comments(jump_raw)
    virt = _without_comments(virt_raw)

    pane_m = _svelte_markup(pane_raw)
    list_m = _svelte_markup(list_raw)
    shell_m = _svelte_markup(shell_raw) if shell_raw else ""
    rows_m = _svelte_markup(rows_raw) if rows_raw else ""
    hits_m = _svelte_markup(hits_raw) if hits_raw else ""

    open_at = _fn(pane, "openPersonAtMessage") or _fn(pane_raw, "openPersonAtMessage")
    if not open_at:
        fail(f"{_ISSUE}: keep openPersonAtMessage — one lander for Search Enter and gallery")
    post = _post_hit(open_at)
    virt_src = virt
    land = _expand_land(list_src, pane, virt_src, post)
    est_body = _fn(list_src, "estimateScrollToIndex") or _fn(
        list_raw, "estimateScrollToIndex"
    )
    ensure = _fn(list_src, "ensureTlIndexVisible") or _fn(
        list_raw, "ensureTlIndexVisible"
    )
    land_no_est = _strip_estimate(land, est_body)
    lander_names = _called_names(post)

    activate = _fn(search, "activateHit") or _fn(search_raw, "activateHit")
    hits_key = _fn(search, "onHitsKey") or _fn(search_raw, "onHitsKey")
    jump = _fn(app, "jumpToMessage") or _fn(app_raw, "jumpToMessage")
    show = _fn(gallery, "showInTimeline") or _fn(gallery_raw, "showInTimeline")
    sel = _fn(pane, "selectPerson") or _fn(pane_raw, "selectPerson")
    step = _fn(pane, "stepFind") or _fn(pane_raw, "stepFind")
    jmp = _fn(jump_src, "jumpToMessageId") or _fn(jump_raw, "jumpToMessageId")
    wst = _fn(list_src, "writeScrollTop") or _fn(list_raw, "writeScrollTop")
    click = _click_path(search, hits_m)
    on_act = _prop_assign(search_raw, "onActivate") or _prop_assign(search, "onActivate")

    # --- keep-checks (pass today) ---

    # jump-keep-124 / 124-sentAt
    if not activate:
        fail(f"{_ISSUE}: keep activateHit — Enter + person_id still #124 jump")
    if not _PERSON_GUARD.search(activate):
        fail(
            f"{_ISSUE}: keep #124 — jump only when person_id is set "
            "(no person_id never jumps)"
        )
    if not re.search(r"\bonJumpToMessage\s*\(", activate):
        fail(f"{_ISSUE}: keep #124 Enter → onJumpToMessage (tick() → openPersonAtMessage)")
    if not _SENT_AT_PAYLOAD.search(activate):
        fail(f"{_ISSUE}: keep sentAt: h.sent_at on the jump payload (#124)")
    if not jump:
        fail(f"{_ISSUE}: keep App jumpToMessage (#124)")
    if not _VIEW_PEOPLE.search(jump):
        fail(f"{_ISSUE}: keep jumpToMessage view = \"people\" (#124)")
    if not _TICK.search(jump):
        fail(f"{_ISSUE}: keep jumpToMessage await tick() before openPersonAtMessage")
    if not _OPEN_AT.search(jump):
        fail(f"{_ISSUE}: keep jumpToMessage → openPersonAtMessage")
    if not hits_key or not _KEY_ENTER.search(hits_key):
        fail(f"{_ISSUE}: keep onHitsKey Enter → activateHit when person_id is set (#124)")
    enter_arm = _enter_branch(hits_key) if hits_key else ""
    if not _ACTIVATE.search(hits_key or "") and not re.search(
        r"\bonJumpToMessage\s*\(", enter_arm
    ):
        fail(f"{_ISSUE}: keep onHitsKey Enter → activateHit (#124)")
    if not _MESSAGE_SEEK.search(open_at):
        fail(
            f"{_ISSUE}: keep #124 seek — load a window that contains that message_id "
            "(not last-row fallback)"
        )
    if not _TL_NEG.search(open_at) or not _SHOW_ERR.search(open_at):
        fail(f"{_ISSUE}: keep #124 miss → tlIndex = -1 + showErr (not last loaded row)")

    # jump-keep-371 / 371-click-no-jump / 371-no-person
    if _JUMP_OR_VIEW.search(click) or _ACTIVATE.search(on_act):
        fail(
            f"{_ISSUE}: keep #371 — click selects for preview; it must not jump "
            "(no activateHit / onJumpToMessage / openPersonAtMessage)"
        )
    if not hits_key:
        fail(f"{_ISSUE}: keep onHitsKey — j/k select; Enter jumps")
    if not _KEY_J.search(hits_key) or not _KEY_K.search(hits_key):
        fail(f"{_ISSUE}: keep #371 j/k / arrows select for preview (they do not jump)")
    jk_only = hits_key
    if enter_arm:
        jk_only = jk_only.replace(enter_arm, " ")
    if _JUMP_OR_VIEW.search(jk_only) or _VIEW_PEOPLE.search(jk_only):
        fail(
            f"{_ISSUE}: keep #371 — j/k / arrows must not call onJumpToMessage / "
            "activateHit / openPersonAtMessage"
        )
    if re.search(
        r"(?:person_id|personId)[^\n]{0,80}(?:==\s*null|===\s*null)"
        r"[\s\S]{0,240}(?:onJumpToMessage|jumpToMessage|openPersonAtMessage|"
        r"selectPerson|view\s*=\s*[\"']people[\"'])",
        activate,
    ):
        fail(
            f"{_ISSUE}: keep #371 — a hit with no person_id never jumps "
            "(Enter included)"
        )

    # jump-keep-370 / 370-collapse
    if not _COLLAPSE.search(open_at):
        fail(
            f"{_ISSUE}: keep #370 — openPersonAtMessage still "
            "selectedIds = new Set([messageId])"
        )

    # 369-no-key
    if _REMOUNT.search(pane_m + "\n" + list_m + "\n" + shell_m):
        fail(
            f"{_ISSUE}: keep #369 / #370 — no {{#key}} on #person-timeline / "
            "PeopleShell / TimelinePane"
        )

    # 369-last-time-row / jump-last-time-height wrapper
    inner = _between_tl_and_article(rows_m or rows_raw)
    if not _LAST_TIME_T.search(inner) and not _LAST_TIME_T.search(rows_m or rows_raw):
        fail(
            f"{_ISSUE}: keep #369 t(\"lastTime\") inside the outer [data-tl-index] "
            "(sibling of <article> — jump measures that wrapper)"
        )

    # jump-keep-ensure-jk — ensure stays clip-only; j/k / Find / Last time use it
    if not ensure:
        fail(
            f"{_ISSUE}: keep ensureTlIndexVisible — clip-only for j/k / Find / "
            "Last time jump"
        )
    if not (_CLIP_TOP.search(ensure) and _CLIP_BOT.search(ensure)):
        fail(
            f"{_ISSUE}: keep ensureTlIndexVisible clip-only "
            "(rowTop < viewTop / rowBottom > viewBottom) for j/k / Find / Last time"
        )
    if _writes_outside_clip(ensure):
        fail(
            f"{_ISSUE}: keep ensureTlIndexVisible clip-only — do not top-inset "
            "inside ensure (j/k / Find / Last time stay a nudge)"
        )
    if not keys_path.is_file():
        fail(f"{_ISSUE}: PeopleKeys.ts required (j/k still clip-only ensure)")
    if not _KEY_JK.search(keys) or not _ENSURE.search(keys) or not _SET_TL.search(keys):
        fail(
            f"{_ISSUE}: keep j/k → setTlIndex + ensureTlIndexVisible "
            "(clip-only nudge, not a top pin)"
        )
    if not _FIND_HOOK.search(pane_m) and not _FIND_HOOK.search(pane):
        fail(f"{_ISSUE}: keep #310 find (data-tl-find) — Find still clip-only ensure")
    if step and not _ENSURE.search(step):
        fail(f"{_ISSUE}: keep #310 Find step → ensureTlIndexVisible (clip-only)")
    if not jmp:
        fail(f"{_ISSUE}: keep jumpToMessageId — Last time button is not this lander")
    if not _ENSURE.search(jmp):
        fail(
            f"{_ISSUE}: keep Last time button → jumpToMessageId + ensureTlIndexVisible"
        )
    if _OPEN_AT.search(jmp) or _ESTIMATE.search(jmp):
        fail(
            f"{_ISSUE}: Last time button still jumpToMessageId + clip-only ensure "
            "(not openPersonAtMessage)"
        )

    # jump-keep-224 / 224-virtualizer
    if not virt_path.is_file():
        fail(f"{_ISSUE}: TimelineVirtual.ts required (#224 window stays)")
    if not _VIRTUALIZE.search(virt) and not re.search(
        r"\bVIRTUALIZE_AFTER\s*=\s*250\b", virt_raw
    ):
        fail(f"{_ISSUE}: keep #224 VIRTUALIZE_AFTER = 250")
    if not _EST.search(virt) and not re.search(
        r"\bESTIMATED_ROW_HEIGHT\s*=\s*88\b", virt_raw
    ):
        fail(f"{_ISSUE}: keep #224 ESTIMATED_ROW_HEIGHT = 88")
    if _FIXED_INDEX_TIMES_EST.search(ensure):
        fail(
            f"{_ISSUE}: keep #224 — ensureTlIndexVisible uses prefix sums, "
            "not pos * ESTIMATED_ROW_HEIGHT"
        )
    if not _uses_prefix_sum(ensure):
        fail(
            f"{_ISSUE}: keep #224 — ensureTlIndexVisible still prefix sums "
            "(offsetOf / heightOf), not pos * 88"
        )

    # latest-selectPerson / jump-keep-latest-last-older
    if not sel or not _APPLY_OPEN.search(sel):
        fail(
            f"{_ISSUE}: keep Latest pin on non-append selectPerson "
            "(applyOpenPersonWindow / scrollHeight)"
        )
    if _APPLY_OPEN.search(open_at):
        fail(
            f"{_ISSUE}: pin-latest stays on selectPerson — "
            "openPersonAtMessage is the jump lander, not Latest"
        )
    if not _LOAD_OLDER.search(pane + "\n" + list_src + "\n" + (rows_m or rows_raw)):
        fail(f"{_ISSUE}: keep Load older (#113) — jump does not rewrite prepend")

    # jump-no-smooth (writeScrollTop stays instant; Search hit-list may stay smooth)
    if not wst:
        fail(f"{_ISSUE}: keep writeScrollTop — jump writes are instant (not smooth)")
    if _SMOOTH.search(wst):
        fail(f"{_ISSUE}: jump writeScrollTop is not behavior: \"smooth\" (no bounce)")
    if not re.search(r"\.scrollTop\s*=", wst):
        fail(f"{_ISSUE}: writeScrollTop still assigns scrollTop instantly")

    # jump-gallery-same (call site keep — lander itself is the new check)
    if not show:
        fail(f"{_ISSUE}: keep PersonMediaDialog showInTimeline")
    if not _OPEN_AT.search(show):
        fail(
            f"{_ISSUE}: keep gallery Show in timeline → openPersonAtMessage "
            "(same lander as Search Enter)"
        )
    if _ESTIMATE.search(show) or _WRITE.search(show):
        fail(
            f"{_ISSUE}: gallery still uses the same openPersonAtMessage lander "
            "(no second scroller)"
        )
    after_jump = _after_open_call(jump)
    if (
        _WRITE.search(after_jump)
        or _ESTIMATE.search(after_jump)
        or _ENSURE.search(after_jump)
        or _MEASURE.search(after_jump)
    ):
        fail(
            f"{_ISSUE}: land inside openPersonAtMessage (Search Enter and gallery) "
            "— not a Search-only patch in jumpToMessage"
        )

    # jump-keep-316 Space stays People
    if not _KEY_SPACE.search(keys) or not _ROW_AUDIO.search(keys):
        fail(
            f"{_ISSUE}: keep #316 PeopleKeys Space on "
            "[data-tl-index=\"${{tlIndex}}\"] [data-voice-note] audio"
        )

    # --- new behavior (fail today) ---

    # jump-onscreen / jump-land-onscreen / jump-land-top / jump-onscreen-top-inset
    if not _has_measured_top_pin(land) or _measured_final_is_times_two(land_no_est):
        fail(_PRIMARY)
    if not _INSET.search(land_no_est) and not _INSET.search(land):
        fail(
            f"{_ISSUE}: after [data-tl-index] is mounted, pin a small top inset "
            "(rowTop - ESTIMATED_ROW_HEIGHT or similar — not center, not * 2)"
        )
    if _CENTER.search(land_no_est) and not _INSET.search(land_no_est):
        fail(
            f"{_ISSUE}: land-where is a small top inset of #person-timeline, "
            "not center"
        )
    if _SMOOTH.search(land) or (
        _SCROLL_INTO.search(land) and _SMOOTH.search(land)
    ):
        fail(
            f"{_ISSUE}: jump write is not behavior: \"smooth\" "
            "(Search hit-list smooth may stay)"
        )

    # jump-wait-mount / jump-onscreen-wait-mounted
    if not _TICK.search(open_at) and not _TICK.search(land):
        fail(f"{_ISSUE}: jump still await tick() then wait until [data-tl-index] is mounted")
    if not _DOUBLE_RAF.search(post) and not _DOUBLE_RAF.search(land):
        fail(
            f"{_ISSUE}: wait until [data-tl-index] is mounted — tick + double "
            "requestAnimationFrame (one rAF lands short; do not {{#key}} remount)"
        )
    if not _TL_SEL.search(land_no_est) and not _TL_SEL.search(land):
        fail(
            f"{_ISSUE}: jump pin queries [data-tl-index] (the wrapper, so Last time "
            "height cannot clip the article)"
        )
    if not _retries_unmounted(land):
        fail(
            f"{_ISSUE}: if [data-tl-index] is still unmounted, pin from "
            "tlChromeHeight + offsetOf then retry once after measure — do not "
            "treat an 88px offsetOf box as already visible"
        )

    # jump-onscreen-remeasure / last-time extra height
    if not _repins_after_measure(post, land, list_src, lander_names):
        fail(
            f"{_ISSUE}: re-pin the same top inset after Last time / "
            "flushRowMeasures so extra marker height cannot push the hit off-screen"
        )

    # jump-land-shared / jump-onscreen-all-callers
    if not re.search(
        r"\b(?:estimateScrollToIndex|pinJump|landJump|alignJump|pinTl|"
        r"landOnscreen|scrollJump|pinMounted|alignTl|jumpPin|pinHit|"
        r"ensureJump|landTl|pinOpen|alignOpen)\w*\s*\(",
        post,
    ) and not _has_measured_top_pin(post):
        # Lander must be invoked from openPersonAtMessage (inlined pin also ok).
        if not _WRITE.search(post) and not any(
            n not in {"estimateScrollToIndex"} for n in lander_names
        ):
            fail(
                f"{_ISSUE}: one lander inside openPersonAtMessage — Search Enter "
                "and PersonMediaDialog; do not fork a Search-only scroll"
            )
