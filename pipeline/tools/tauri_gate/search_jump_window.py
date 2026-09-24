"""#403 — Search jump loads messages after the hit, not only older ones.

Static scan of openPersonAtMessage, api.personTimeline, the Tauri
person_timeline command, and person_timeline_rows_for. No network.
Does not soften #124 / #400 / #371. Placeholders Ada / Berk / Self
only if a name is required.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.include_groups_fold import _has_include_groups_effect
from tauri_gate.last_read import _web_file
from tauri_gate.scan import _match_closer, _svelte_markup, _without_comments
from tauri_gate.scan_rust_rest import _rust_fn_signature
from tauri_gate.scan_tokens import _rust_fn_body
from tauri_gate.search_jump_onscreen import _DOUBLE_RAF, _fn
from tauri_gate.status_toasts_toast import _svelte_effect_args

_ISSUE = "#403"
_MISS = (
    "Could not find that message on the person timeline "
    "(too far back or not in this view)."
)
_DOC = (
    "Search Enter opens that message with messages after it, "
    "not only older ones."
)
_AFTER_KEY = re.compile(r"\bafter\s*:")
_AFTER_HIT = re.compile(r"\bafter\s*:\s*(?:seekAt|sentAt|sent_at)\b")
_ASC = re.compile(r"sent_at\s+ASC\s*,\s*(?:m\.)?id\s+ASC")
_AFTER_PRED = re.compile(r"sent_at\s*>\s*:after")
_BEFORE_PRED = re.compile(r"sent_at\s*<\s*:before")
_DESC = re.compile(r"sent_at\s+DESC\s*,\s*(?:m\.)?id\s+DESC")
_LOAD_NEWER = re.compile(r"data-load-newer|>\s*Load newer\s*<")
_CALL_SKIP = frozenset(
    {
        "if",
        "for",
        "while",
        "switch",
        "catch",
        "return",
        "function",
        "await",
        "typeof",
        "new",
    }
)


def _strip_rust_comments(src: str) -> str:
    src = re.sub(r"/\*[\s\S]*?\*/", "", src)
    return re.sub(r"//.*?$", "", src, flags=re.M)


def _call_objects(src: str, name: str) -> list[str]:
    """Argument objects (or raw arg text) of each `name(` call."""
    out: list[str] = []
    start = 0
    needle = name
    while True:
        i = src.find(needle, start)
        if i < 0:
            break
        paren = src.find("(", i + len(needle))
        if paren < 0 or paren - (i + len(needle)) > 8:
            start = i + len(needle)
            continue
        j = paren + 1
        while j < len(src) and src[j] in " \n\t":
            j += 1
        if j < len(src) and src[j] == "{":
            end = _match_closer(src, j)
            if end > j:
                out.append(src[j : end + 1])
                start = end + 1
                continue
        end = _match_closer(src, paren)
        if end > paren:
            out.append(src[paren + 1 : end])
            start = end + 1
            continue
        start = i + len(needle)
    return out


def _for_loop_span(src: str) -> tuple[int, int]:
    """Body span of the older page walk (`page < maxPages` / `page < 80`)."""
    m = re.search(
        r"\bfor\s*\([^)]*(?:maxPages|\b80\b)[^)]*\)\s*\{",
        src,
    )
    if not m:
        return (-1, -1)
    brace = src.find("{", m.start())
    if brace < 0:
        return (-1, -1)
    end = _match_closer(src, brace)
    if end < 0:
        return (-1, -1)
    return (brace, end)


def _in_loop(src: str, idx: int) -> bool:
    depth = 0
    i = idx
    while i > 0:
        c = src[i]
        if c == "}":
            depth += 1
        elif c == "{":
            if depth == 0:
                pre = src[max(0, i - 120) : i]
                if re.search(r"\b(?:for|while)\s*\([^)]*\)\s*$", pre):
                    return True
            else:
                depth -= 1
        i -= 1
    return False


def _after_sql_resorts(body: str) -> bool:
    """True when one SQL literal limits ASC on `> :after` then re-sorts DESC."""
    for lit in re.findall(r'"(?:[^"\\]|\\.)*"|`(?:[^`\\]|\\.)*`', body):
        if not _AFTER_PRED.search(lit) or not _ASC.search(lit):
            continue
        asc_at = lit.find("ASC")
        if asc_at >= 0 and "DESC" in lit[asc_at:]:
            return True
    return False


def _newer_returned_newest_first(body: str) -> bool:
    return (
        "reverse()" in body
        or ".rev()" in body
        or _after_sql_resorts(body)
    )


def _callee_names(blob: str) -> list[str]:
    return [
        n
        for n in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", blob)
        if n not in _CALL_SKIP
    ]


def _follow_calls(body: str) -> list[str]:
    """personTimeline calls that page forward (after, no before, not seekAt)."""
    out: list[str] = []
    for call in _call_objects(body, "personTimeline"):
        if not _AFTER_KEY.search(call) or re.search(r"\bbefore\s*:", call):
            continue
        if re.search(r"\bseekAt\b", call):
            continue
        out.append(call)
    return out


def _named_follow(src: str) -> tuple[str, str]:
    """Function outside openPersonAtMessage that issues the next after page."""
    for name in re.findall(
        r"(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("
        r"|(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?\(",
        src,
    ):
        fn = name[0] or name[1]
        if fn == "openPersonAtMessage":
            continue
        body = _fn(src, fn)
        if body and _follow_calls(body):
            return fn, body
    return "", ""


def _bind_text(markup: str, callee: str) -> str:
    m = re.search(rf"\b{re.escape(callee)}\s*=\s*\{{[^}}]*\}}", markup)
    return m.group(0) if m else ""


def _scroll_calls(list_src: str, pane: str, scroll: str, fn_name: str) -> bool:
    """True when a near-bottom branch of onTimelineScroll reaches fn_name."""
    if not scroll or not fn_name:
        return False
    mark = _svelte_markup(pane)
    blocks: list[str] = []
    for m in re.finditer(r"if\s*\(([^)]*scrollHeight[^)]*)\)\s*\{", scroll):
        brace = scroll.find("{", m.start())
        end = _match_closer(scroll, brace)
        if end > brace:
            blocks.append(scroll[m.start() : end + 1])
    for m in re.finditer(
        r"if\s*\([^)]*scrollHeight[^)]*\)\s*[A-Za-z_][A-Za-z0-9_]*\s*\(",
        scroll,
    ):
        blocks.append(m.group(0))
    for block in blocks:
        if "scrollHeight" not in block:
            continue
        blob = block
        for callee in _callee_names(block):
            blob += "\n" + _fn(list_src, callee) + _fn(pane, callee)
            blob += "\n" + _bind_text(mark, callee)
        if re.search(rf"\b{re.escape(fn_name)}\s*\(", blob):
            near = re.search(
                r"scrollTop[\s\S]{0,80}scrollHeight|scrollHeight\s*-\s*\d+|scrollHeight\s*-\s*\w*\.?clientHeight",
                block,
            )
            if near and fn_name not in _fn(list_src, "stopPinLatest"):
                return True
    return False


def _if_around(markup: str, token: re.Match[str]) -> str:
    head = markup[: token.start()]
    start = head.rfind("{#if")
    if start < 0:
        return ""
    end = markup.find("}", start)
    if end < 0:
        return ""
    return markup[start : end + 1]


def _flag_name(condition: str) -> str:
    names = re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", condition)
    skip = {"if", "true", "false", "null", "undefined", "length"}
    for name in names:
        if name not in skip:
            return name
    return ""


def _hides_flag(body: str, flag: str) -> bool:
    """Short, empty, or no-new-id path assigns the control flag off. No toast."""
    if not flag or not re.search(rf"\b{re.escape(flag)}\s*=\s*false\b", body):
        return False
    if not re.search(r"TIMELINE_PAGE_LIMIT", body):
        return False
    if not re.search(r"<\s*TIMELINE_PAGE_LIMIT|length\s*===\s*0|!\s*\w+\.length", body):
        return False
    if not re.search(r"message_id", body):
        return False
    if "showErr" in body or "showToast" in body or _MISS in body:
        return False
    return True


def _assert_load_newer(pane: str, list_src: str, rows: str) -> None:
    """Follow-on: one newer page per gesture. Fails until that path exists."""
    mark = "\n".join(
        part
        for part in (_svelte_markup(rows), _svelte_markup(list_src), _svelte_markup(pane))
        if part
    )
    ctrl = _LOAD_NEWER.search(mark)
    scroll = _fn(list_src, "onTimelineScroll")
    fn_name, follow = _named_follow(pane)
    scroll_hits = _scroll_calls(list_src, pane, scroll, fn_name)
    if not ctrl or not scroll_hits:
        fail(
            f"{_ISSUE}: no Load newer control (data-load-newer or button text "
            '"Load newer"), and scrolling the bottom of #person-timeline does not '
            "request another after page"
        )
    guard = _if_around(mark, ctrl)
    flag = _flag_name(guard)
    if not guard or not flag or re.search(r"\btrue\b", guard):
        fail(
            f"{_ISSUE}: Load newer must be shown only while a further page may exist"
        )
    calls = _follow_calls(follow)
    if len(calls) != 1:
        fail(
            f"{_ISSUE}: pressing Load newer or scrolling near the bottom requests "
            "exactly one personTimeline with after set to the newest loaded sent_at "
            "(not seekAt), limit TIMELINE_PAGE_LIMIT, and no before"
        )
    call = calls[0]
    if not re.search(r"\blimit\s*:\s*TIMELINE_PAGE_LIMIT\b", call):
        fail(
            f"{_ISSUE}: the follow-on page limit is TIMELINE_PAGE_LIMIT (80), not another size"
        )
    if not re.search(r"\bafter\s*:[^,\n}]*(?:sent_at|newest)", call):
        fail(
            f"{_ISSUE}: follow-on after must be the newest loaded sent_at, not seekAt"
        )
    if "includeGroups" not in call or not re.search(r"\bconversationId\s*:", call):
        fail(
            f"{_ISSUE}: the follow-on page keeps the timeline's includeGroups and conversationId"
        )
    open_at = _fn(pane, "openPersonAtMessage")
    if re.search(rf"\b{re.escape(fn_name)}\s*\(", open_at):
        fail(
            f"{_ISSUE}: the next after page is not inside openPersonAtMessage "
            "(that function keeps one after: seekAt call)"
        )
    onclick = mark[ctrl.start() : ctrl.start() + 500]
    if fn_name not in onclick and fn_name not in mark:
        fail(f"{_ISSUE}: the Load newer control must call {fn_name}")
    if not _hides_flag(follow, flag):
        fail(
            f"{_ISSUE}: a short page, an empty page, or a page that adds no new "
            "message_id hides Load newer — no toast for that end"
        )
    if "toReversed" not in follow or not re.search(
        r"timeline\s*=\s*(?:timeline\.concat\s*\(|\[\s*\.\.\.\s*timeline\b)",
        follow,
    ):
        fail(
            f"{_ISSUE}: append the follow-on page with toReversed() under the rows "
            "already loaded (not a prepend)"
        )
    if not re.search(r"message_id", follow) or not re.search(
        r"\b(?:Set|filter|has)\b", follow
    ):
        fail(f"{_ISSUE}: skip message_ids already in the list")
    if re.search(r"\b(?:tlIndex|selectedIds|anchorId)\s*=", follow):
        fail(
            f"{_ISSUE}: later pages must not assign tlIndex, selectedIds, or anchorId"
        )
    if re.search(r"\+\+\s*tlGen|\btlGen\s*\+\+|\btlGen\s*\+=", follow):
        fail(f"{_ISSUE}: the follow-on fetch must not bump tlGen (copy it)")
    assigned = follow.find("timeline =")
    if assigned < 0 or "gen !== tlGen" not in follow[:assigned]:
        fail(
            f"{_ISSUE}: a stale tlGen returns without assigning timeline"
        )
    call_at = follow.find("personTimeline")
    head = follow[:call_at] if call_at >= 0 else ""
    if not re.search(
        r"if\s*\([^)]*(?:InFlight|tlLoading|newerLoading|loadingNewer)[^)]*\)\s*return",
        head,
    ):
        fail(
            f"{_ISSUE}: one in-flight guard — a second gesture must not start "
            "another personTimeline before the first returns"
        )
    if not re.search(
        r"(?:newerInFlight|newerLoading|loadingNewer|tlLoading)\s*=\s*true",
        head,
    ):
        fail(
            f"{_ISSUE}: the in-flight guard is set before the follow-on personTimeline"
        )
    for blob in _svelte_effect_args(pane) + _svelte_effect_args(list_src):
        if re.search(rf"\b{re.escape(fn_name)}\s*\(", blob):
            fail(
                f"{_ISSUE}: sitting still must not fetch — no $effect calls the follow-on"
            )
    tail = open_at[open_at.find("pinJump") :] if "pinJump" in open_at else ""
    merged = open_at[: open_at.find("pinJump")] if "pinJump" in open_at else open_at
    if flag not in merged or "TIMELINE_PAGE_LIMIT" not in merged[merged.find("after") :]:
        fail(
            f"{_ISSUE}: a full first after page that added a new id leaves Load newer "
            "visible; a short or empty first page hides it"
        )
    if flag in tail and re.search(rf"\b{re.escape(flag)}\s*=", tail):
        fail(f"{_ISSUE}: pinJump stays once, before any later-page flag write")
    latest = _fn(list_src, "scrollToLatest") + _fn(pane, "scrollToLatest")
    if "++tlGen" not in latest and "tlGen++" not in latest and "tlGen +=" not in latest:
        cancel = re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=\s*true\b", latest)
        if not any(tok in follow and "return" in follow for tok in cancel):
            fail(
                f"{_ISSUE}: Latest must bump tlGen or otherwise cancel an in-flight "
                "newer fetch (person switch and a new jump already bump tlGen)"
            )


def assert_search_jump_window(crate: Path) -> None:
    """#403: jump keeps the older walk, then one newer page, then pins once."""
    pane_path = _web_file(crate, "TimelinePane.svelte")
    app_path = crate / "web" / "App.svelte"
    gallery_path = _web_file(crate, "PersonMediaDialog.svelte")
    api_path = _web_file(crate, "api.ts")
    list_path = _web_file(crate, "TimelineList.svelte")
    keys_path = _web_file(crate, "PeopleKeys.ts")
    search_path = _web_file(crate, "SearchPane.svelte")
    walk_path = _web_file(crate, "threadWalk.ts")
    shell_path = _web_file(crate, "PeopleShell.svelte")
    insp_path = _web_file(crate, "PeopleInspector.svelte")
    core = crate.parent / "interlace-core" / "src" / "people" / "timeline.rs"
    cmd_path = crate / "src" / "people_cmd.rs"
    docs = repo_root() / "docs" / "user" / "app.md"
    for path, label in (
        (pane_path, "TimelinePane.svelte"),
        (app_path, "App.svelte"),
        (gallery_path, "PersonMediaDialog.svelte"),
        (api_path, "api.ts"),
        (list_path, "TimelineList.svelte"),
        (keys_path, "PeopleKeys.ts"),
        (search_path, "SearchPane.svelte"),
        (walk_path, "threadWalk.ts"),
        (shell_path, "PeopleShell.svelte"),
        (insp_path, "PeopleInspector.svelte"),
        (core, "people/timeline.rs"),
        (cmd_path, "people_cmd.rs"),
        (docs, "docs/user/app.md"),
    ):
        if not path.is_file():
            fail(f"{_ISSUE}: {label} required")

    pane = _without_comments(pane_path.read_text())
    app = _without_comments(app_path.read_text())
    gallery = _without_comments(gallery_path.read_text())
    api = _without_comments(api_path.read_text())
    list_src = _without_comments(list_path.read_text())
    keys = _without_comments(keys_path.read_text())
    search = _without_comments(search_path.read_text())
    walk = _without_comments(walk_path.read_text())
    shell = _without_comments(shell_path.read_text())
    insp = _without_comments(insp_path.read_text())
    rust = _strip_rust_comments(core.read_text())
    cmd = _strip_rust_comments(cmd_path.read_text())

    open_at = _fn(pane, "openPersonAtMessage")
    select = _fn(pane, "selectPerson")
    last_read = _fn(pane, "goToLastRead")
    jump_day = _fn(pane, "goToJumpDay")
    prev = _fn(pane, "onThreadPrev")
    jump = _fn(app, "jumpToMessage")
    show = _fn(gallery, "showInTimeline")
    scroll = _fn(list_src, "scrollToLatest")
    watch = _fn(list_src, "watchPinLatest")
    fill = _fn(search, "fillPreview")
    activate = _fn(search, "activateHit")
    rows_for = _rust_fn_body(rust, "person_timeline_rows_for")
    rows_wrap = _rust_fn_body(rust, "person_timeline_rows")
    rows_sig = _rust_fn_signature(rust, "person_timeline_rows_for")
    cmd_sig = _rust_fn_signature(cmd, "person_timeline")
    cmd_body = _rust_fn_body(cmd, "person_timeline")

    # --- keep-checks (pass on current master; do not soften #124 / #400 / #371) ---

    if not open_at or not select or not jump or not show:
        fail(
            f"{_ISSUE}: keep openPersonAtMessage, selectPerson, "
            "jumpToMessage, and showInTimeline"
        )
    sig = re.search(r"function\s+openPersonAtMessage\s*\(([^)]*)\)", pane)
    if not sig:
        fail(f"{_ISSUE}: keep openPersonAtMessage (personId, messageId, sentAt)")
    params = [p.strip() for p in sig.group(1).split(",") if p.strip()]
    if len(params) != 3:
        fail(
            f"{_ISSUE}: keep one lander — openPersonAtMessage stays "
            "personId, messageId, sentAt (no older-only flag)"
        )
    if not re.search(
        r"openPersonAtMessage\s*\(\s*selectedId\s*,\s*row\.message_id\s*,\s*row\.sent_at\s*\)",
        show,
    ):
        fail(
            f"{_ISSUE}: gallery showInTimeline must call openPersonAtMessage"
            " with that cell's message_id and sent_at (no older-only flag)"
        )
    if re.search(r"\bincludeGroups\s*=", show):
        fail(f"{_ISSUE}: gallery showInTimeline must not flip include-groups")
    if "openPersonAtMessage" not in jump:
        fail(f"{_ISSUE}: Search Enter stays jumpToMessage → openPersonAtMessage")
    if not re.search(r"===\s*[\"']group[\"']", jump) or "includeGroups = true" not in jump:
        fail(
            f"{_ISSUE}: jumpToMessage still sets includeGroups = true "
            "only for a group hit"
        )
    if "writeIncludeGroupsPref" in jump:
        fail(f"{_ISSUE}: jumpToMessage must not write include-groups to prefs")
    if "selectedConversationId = null" not in open_at:
        fail(f"{_ISSUE}: jump still clears selectedConversationId (merged person stream)")
    if not re.search(r"conversationId\s*:\s*null", open_at):
        fail(f"{_ISSUE}: jump still queries conversationId: null")
    if not re.search(r"\b200\b", open_at) or not re.search(r"\b80\b", open_at):
        fail(
            f"{_ISSUE}: keep the older walk — page 200, cap 80, "
            "stop once message_id is present"
        )
    if not re.search(r"\$\{seekAt\}~|seekAt\s*\+\s*[\"']~[\"']", open_at):
        fail(f"{_ISSUE}: keep the older walk's before: sentAt~ cursor")
    loop_a, loop_b = _for_loop_span(open_at)
    if loop_a < 0:
        fail(f"{_ISSUE}: keep the older page loop (cap 80)")
    loop = open_at[loop_a : loop_b + 1]
    if "personTimeline" not in loop or not re.search(r"\bbefore\b", loop):
        fail(f"{_ISSUE}: older walk still calls personTimeline with before")
    if not re.search(r"message_id\s*===\s*messageId", loop) or "break" not in loop:
        fail(f"{_ISSUE}: older walk still stops once message_id is in the loaded rows")
    if re.search(r"\bafter\b", loop):
        fail(f"{_ISSUE}: do not pass after on the older before-walk")
    if _MISS not in open_at:
        fail(f"{_ISSUE}: keep the miss sentence unchanged")
    if open_at.count("showErr") != 1 or "tlIndex = -1" not in open_at:
        fail(
            f"{_ISSUE}: miss stays a single showErr and tlIndex = -1 "
            "(do not ring the last loaded row; an empty newer page is not that miss)"
        )
    miss = re.search(r"if\s*\(\s*idx\s*<\s*0\s*\)\s*\{", open_at)
    if not miss:
        fail(f"{_ISSUE}: miss stays if (idx < 0) then tlIndex = -1 and showErr")
    miss_end = _match_closer(open_at, miss.end() - 1)
    miss_body = open_at[miss.start() : miss_end + 1] if miss_end > miss.start() else ""
    if "showErr" not in miss_body or "return" not in miss_body or re.search(r"\bafter\b", miss_body):
        fail(
            f"{_ISSUE}: showErr stays on the missed id only "
            "(an empty newer page must not take that path)"
        )
    if not re.search(r"selectedIds\s*=\s*new\s+Set\s*\(\s*\[\s*messageId", open_at):
        fail(f"{_ISSUE}: ring stays selectedIds on that message_id")
    if not re.search(r"\banchorId\s*=\s*messageId\b", open_at):
        fail(f"{_ISSUE}: anchorId stays that message_id")
    if not re.search(r"\btlIndex\s*=\s*idx\b", open_at):
        fail(f"{_ISSUE}: tlIndex stays findIndex of message_id, not a neighbor")
    if re.search(
        r"tlIndex\s*=\s*(?:loaded|timeline|chrono)\.length\s*-\s*1",
        open_at,
    ) or re.search(
        r"pinJump\s*\(\s*(?:loaded|timeline|chrono)\.length\s*-\s*1",
        open_at,
    ):
        fail(f"{_ISSUE}: do not pin the last row")
    if "scrollHeight" in open_at or "scrollToLatest" in open_at or "applyOpenPersonWindow" in open_at:
        fail(
            f"{_ISSUE}: do not scroll the hit to the bottom "
            "(pinJump top inset, not Latest)"
        )
    if open_at.count("pinJump") != 1:
        fail(f"{_ISSUE}: pin once — one pinJump in openPersonAtMessage")
    est = open_at.find("estimateScrollToIndex")
    tick_at = open_at.find("tick(")
    pin_at = open_at.find("pinJump")
    if est < 0 or tick_at < 0 or pin_at < 0 or not (est < tick_at < pin_at):
        fail(
            f"{_ISSUE}: keep #400 — estimateScrollToIndex, tick, then pinJump"
        )
    if not _DOUBLE_RAF.search(open_at[est : pin_at + 1]):
        fail(f"{_ISSUE}: keep #400 — tick + double requestAnimationFrame then pinJump")
    if "const gen = ++tlGen" not in open_at and "const gen = ++tlGen;" not in open_at:
        fail(f"{_ISSUE}: entry still bumps tlGen")
    if "gen !== tlGen" not in open_at:
        fail(
            f"{_ISSUE}: a stale tlGen returns without assigning timeline "
            "and without showErr"
        )
    if "clearVoiceHost" not in open_at:
        fail(f"{_ISSUE}: openPersonAtMessage still stops the voice host")
    if "openPersonAtMessage" in select:
        fail(f"{_ISSUE}: Latest / load older must not call openPersonAtMessage")
    if not re.search(
        r"append\s*\?\s*oldestSentAt\s*\(\s*timeline\s*\)\s*:\s*null",
        select,
    ):
        fail(
            f"{_ISSUE}: selectPerson keeps before null when not appending "
            "(Latest) and the oldest cursor when appending"
        )
    if not re.search(r"\.concat\(\s*timeline\s*\)", select):
        fail(f"{_ISSUE}: load older still prepends")
    if _AFTER_KEY.search(select) or (prev and _AFTER_KEY.search(prev)) or _AFTER_KEY.search(walk):
        fail(f"{_ISSUE}: do not pass after from selectPerson or threadWalk")
    if not scroll or "openPersonAtMessage" in scroll or "openPersonAtMessage" in (watch or ""):
        fail(f"{_ISSUE}: Latest scrollToLatest must not call openPersonAtMessage")
    if "scrollToLatest" not in keys or "openPersonAtMessage" in keys:
        fail(f"{_ISSUE}: End stays scrollToLatest and must not call the jump")
    if not last_read or "jumpToMessageId" not in last_read or "openPersonAtMessage" in last_read:
        fail(f"{_ISSUE}: last-read stays jumpToMessageId, not openPersonAtMessage")
    if not jump_day or "jumpToLocalDay" not in jump_day or "openPersonAtMessage" in jump_day:
        fail(f"{_ISSUE}: year/day jump stays jumpToLocalDay, not openPersonAtMessage")
    if not fill or "onJumpToMessage" in fill or "openPersonAtMessage" in fill:
        fail(f"{_ISSUE}: Search preview must not select or jump by itself")
    if not activate or "onJumpToMessage" not in activate:
        fail(f"{_ISSUE}: Enter still activates the hit (keep #124 / #371)")
    if _has_include_groups_effect(app, pane, shell, insp):
        fail(
            f"{_ISSUE}: no $effect whose body mentions includeGroups "
            "in App, TimelinePane, PeopleShell, or PeopleInspector"
        )
    if "toReversed" not in open_at:
        fail(f"{_ISSUE}: keep oldest-at-top (toReversed / prepend)")

    # --- fail today: the jump never requests messages newer than the hit ---

    calls = _call_objects(open_at, "personTimeline")
    newer = [c for c in calls if _AFTER_KEY.search(c)]
    if len(newer) != 1:
        fail(
            f"{_ISSUE}: openPersonAtMessage never requests messages newer than "
            "the hit — one personTimeline with after set to that sent_at "
            "(limit TIMELINE_PAGE_LIMIT), and no second newer page"
        )
    newer_call = newer[0]
    newer_at = open_at.find(newer_call)
    if re.search(r"\bbefore\b", newer_call):
        fail(f"{_ISSUE}: do not pass after and before on one personTimeline call")
    if not _AFTER_HIT.search(newer_call):
        fail(
            f"{_ISSUE}: after must be the hit sent_at "
            "(seekAt / sentAt), not another cursor"
        )
    if not re.search(r"\blimit\s*:\s*TIMELINE_PAGE_LIMIT\b", newer_call):
        fail(
            f"{_ISSUE}: the newer page limit is TIMELINE_PAGE_LIMIT (80), "
            "not the older seek page of 200"
        )
    if not re.search(r"conversationId\s*:\s*null", newer_call):
        fail(f"{_ISSUE}: the newer page stays the merged person stream (conversationId: null)")
    if _in_loop(open_at, newer_at):
        fail(f"{_ISSUE}: one newer request — do not page after inside a loop")
    tail = open_at[loop_b + 1 :]
    if not _AFTER_KEY.search(tail):
        fail(
            f"{_ISSUE}: request the newer page after the older walk stops, "
            "not instead of it"
        )
    if not re.search(
        r"if\s*\(\s*!?\s*(?:seekAt|sentAt)\b"
        r"|seekAt\s*\?\s*\{[^}]*\bafter\s*:"
        r"|sentAt\s*\?\s*\{[^}]*\bafter\s*:"
        r"|(?:seekAt|sentAt)\s*&&",
        tail,
    ):
        fail(f"{_ISSUE}: null or empty sent_at must not issue after")
    pin_tail = tail.find("pinJump")
    if pin_tail < 0:
        fail(f"{_ISSUE}: pinJump once after the newer page is part of the window")
    merged = tail[:pin_tail]
    if "toReversed" not in merged or not re.search(r"\.concat\s*\(|\[\s*\.\.\.", merged):
        fail(
            f"{_ISSUE}: toReversed() the newest-first newer page and append it "
            "under the hit before pinJump (oldest at the top; not the last row)"
        )
    after_rel = tail.find(newer_call)
    assigned = tail.find("timeline =", after_rel if after_rel >= 0 else 0)
    if after_rel < 0 or assigned < 0 or "tlGen" not in tail[after_rel:assigned]:
        fail(
            f"{_ISSUE}: after the newer await, a stale tlGen returns "
            "without assigning timeline and without showErr"
        )

    if not rows_sig or not re.search(r"\bafter\s*:", rows_sig):
        fail(f"{_ISSUE}: person_timeline_rows_for must take optional after")
    if not rows_for or not _BEFORE_PRED.search(rows_for) or not _DESC.search(rows_for):
        fail(
            f"{_ISSUE}: after unset keeps today's before SQL "
            "(sent_at < :before, ORDER BY sent_at DESC, id DESC)"
        )
    if not rows_for or not _AFTER_PRED.search(rows_for):
        fail(
            f"{_ISSUE}: when after is set and before is not, "
            "predicate is sent_at > :after"
        )
    if "IS NOT NULL" not in (rows_for or ""):
        fail(f"{_ISSUE}: the after predicate requires sent_at IS NOT NULL")
    if not rows_for or not _ASC.search(rows_for):
        fail(
            f"{_ISSUE}: the newer page is limited oldest-first "
            "(ORDER BY sent_at ASC, id ASC, then LIMIT)"
        )
    if not rows_for or not _newer_returned_newest_first(rows_for):
        fail(
            f"{_ISSUE}: return that page newest-first "
            "(reverse the ASC limit, or re-sort DESC) so toReversed() still appends"
        )
    if not rows_wrap or (rows_wrap.count("None") < 3 and "after:" not in rows_wrap):
        fail(
            f"{_ISSUE}: person_timeline_rows passes after unset (None) "
            "so today's before SQL stays"
        )
    if not cmd_sig or not re.search(r"\bafter\s*:", cmd_sig):
        fail(f"{_ISSUE}: the person_timeline command must take optional after")
    if not cmd_body or not re.search(r"\bafter\b", cmd_body):
        fail(f"{_ISSUE}: person_timeline must pass after into person_timeline_rows_for")
    api_args = re.search(r"personTimeline\s*:\s*\(args\s*:\s*\{([^}]*)\}", api)
    if not api_args or not re.search(r"\bafter\s*\?", api_args.group(1)):
        fail(f"{_ISSUE}: api.personTimeline must accept optional after")
    if _DOC not in docs.read_text():
        fail(f"{_ISSUE}: docs/user/app.md must say {_DOC!r}")

    rows_path = _web_file(crate, "TimelineRows.svelte")
    rows = _without_comments(rows_path.read_text()) if rows_path.is_file() else ""
    _assert_load_newer(pane, list_src, rows)
