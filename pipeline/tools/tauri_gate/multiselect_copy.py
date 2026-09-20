"""#370 — multi-select bubbles and copy the range (confirmed mix).

Wired immediately after assert_last_read_fold (#369 family).

Confirmed mix (2026-09-20): contiguous range from last plain click /
current tlIndex to the Shift target, frozen Set<message_id> at extend
time. Not Shift-toggle. Not live re-range. Session-only. Clear on person
switch + leftover archive. Keep across chips / prepend. ring-1 selected,
ring-2 caret (caret wins). Grow copySelected: in-memory rows,
displayBody(body_text || subject), sent_at then message_id, "\\n\\n".
N=1 still #315. Menu N>1 copyN; N=1 copyText. Do not add "c" to the steal
list. Space still tlIndex audio. Shift hops still persist last-read caret.

#315 / #316 / #224 / #369 / #310 stay as their own asserts (#315
copy-not-multi + copy* allowlist: targeted keep-evolves only).
Placeholders only (Ada / Berk).
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.copy_selected_bubble import (
    _DOM,
    _HTML,
    _PAYLOAD,
    _SKIP_EMPTY,
    _steal_has_c,
)
from tauri_gate.find_in_conversation import _FIND_HOOK
from tauri_gate.import_boot_guards import _ls_pref_keys
from tauri_gate.last_read import (
    _article_span,
    _BOUNCE,
    _CLEAR_CHIPS,
    _EST,
    _LAST_KEY_RX,
    _LAST_TIME_T,
    _MESSAGE_ID,
    _REMOUNT,
    _SMOOTH,
    _text,
    _VIRTUALIZE,
    _web_file,
)
from tauri_gate.last_read_fold import _LOADED_CMP
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.palette_lib import _CLIPBOARD_PLUGIN
from tauri_gate.reopen_last_lib import _fn_body
from tauri_gate.scan import _expand_fn_calls, _svelte_markup, _web_logic, _without_comments
from tauri_gate.space_voice_note import _ROW_AUDIO
from tauri_gate.status_toasts_chrome import _WRITE_TEXT
from tauri_gate.status_toasts_extra2 import _toast_args_include_body
from tauri_gate.status_toasts_toast import _svelte_effect_args

_ISSUE = "#370"
_SET_NAME = re.compile(
    r"\b(?:selectedIds|selectedMessageIds|selectedSet|messageIdSet|"
    r"selIds|selectedIdSet|multiSelectedIds)\b"
)
_SHIFT = re.compile(r"\b(?:e\.)?shiftKey\b")
_RING1 = re.compile(r"(?<![\w-])ring-1(?![\w-])")
_RING2 = re.compile(r"(?<![\w-])ring-2(?![\w-])")
_RING_RING = re.compile(r"(?<![\w-])ring-ring(?![\w-])")
_NEW_SET = re.compile(r"\bnew\s+Set\s*(?:<[^>\n]+>)?\s*\(")
_COPY_N_T = re.compile(r"""t\(\s*["']copyN["']\s*\)""")
_COPY_TEXT_T = re.compile(r"""t\(\s*["']copyText["']\s*\)""")
_SEARCH_T = re.compile(r"""t\(\s*["']search["']\s*\)""")
_JOIN = re.compile(r"""["']\\n\\n["']|`\\n\\n`""")
_SENT_AT = re.compile(r"\bsent_at\b")
_DISPLAY = re.compile(r"\bdisplayBody\s*\(")
_HAS_ID = re.compile(r"\.has\s*\(\s*(?:item\.)?row\.message_id|message_id\s*\)")
_HAS_INDEX = re.compile(
    r"\.has\s*\(\s*(?:item\.)?index\b|\.add\s*\(\s*(?:item\.)?index\b"
    r"|selectedIds\.has\s*\(\s*tlIndex|\.has\s*\(\s*data-tl-index"
)
_RANGE_FILL = re.compile(
    r"\.slice\s*\(|Math\.min\s*\(|Math\.max\s*\(|\bfilteredTimeline\b"
)
_TOGGLE = re.compile(r"\.delete\s*\(|\.add\s*\(")
_CLEAR_SET = re.compile(
    r"\.clear\s*\(\s*\)"
    r"|\b(?:selectedIds|selectedMessageIds|selectedSet|messageIdSet|"
    r"selIds|selectedIdSet|multiSelectedIds)\s*=\s*new\s+Set"
)
_ID_NE_SEL = re.compile(r"id\s*!==?\s*selectedId|selectedId\s*!==?\s*id")
_EXTEND = re.compile(
    r"\b(?:extendSelection|extendRange|selectRange|applyRange|"
    r"rangeIds|fillRange|onShiftSelect)\b"
)
_ANCHOR = re.compile(
    r"\b(?:anchorId|rangeAnchor|selAnchor|lastPlainId|anchorMessageId)\b"
)
_PREPEND_SHIFT = re.compile(r"tlIndex\s*\+=|\btlIndex\s*=\s*tlIndex\s*\+")
_HEIGHT_SHIFT = re.compile(r"\bshiftHeightsForPrepend\b")
_INNER_TEXT = re.compile(r"querySelectorAll\s*\(|\binnerText\b|\btextContent\b")
_COPY_EVT = re.compile(r"addEventListener\s*\(\s*[\"']copy[\"']")
_GET_SEL = re.compile(r"\bgetSelection\s*\(")
_FADE = re.compile(r"\b(?:transition|in|out)\s*:\s*(?:fade|fly|slide)\b")
_CAP = re.compile(
    r"\b(?:MAX_SELECT|SELECT_CAP|MULTI_SELECT_CAP|MAX_MULTI|maxSelected)\b"
)
_CMD_A = re.compile(
    r"(?:metaKey|ctrlKey|mod)\s*&&[\s\S]{0,40}(?:e\.)?key\s*===?\s*[\"']a[\"']"
    r"|(?:e\.)?key\s*===?\s*[\"']a[\"'][\s\S]{0,60}\b(?:selectAll|selectedIds)\b"
)
_CMD_CLICK = re.compile(r"(?:metaKey|ctrlKey)\s*&&[\s\S]{0,40}click|cmd-click|metaKey.*toggle")
_FORWARD = re.compile(r"""t\(\s*["'](?:forward|deleteMessages|deleteSelected)["']\s*\)""")
_BODY_CACHE = re.compile(
    r"(?:selectedIds|selectedMessageIds).{0,80}body_text"
    r"|Map\s*<\s*number\s*,\s*string"
)
_N_GT1 = re.compile(
    r"\b(?:selectedIds|selectedMessageIds|selectedSet|messageIdSet|"
    r"selIds|selectedIdSet|multiSelectedIds)\b"
    r"[\s\S]{0,160}(?:\.size|\.length)\s*(?:>\s*1|>=\s*2|<=\s*1|< \s*2)"
)
_REPLACE_N = re.compile(r"""\.replace\(\s*["']\{n\}["']""")
_KEY_J = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']j[\"']|[\"']j[\"']\s*===?\s*(?:e\.)?key"
)
_KEY_K = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']k[\"']|[\"']k[\"']\s*===?\s*(?:e\.)?key"
)
_ARROW_DOWN = re.compile(r"ArrowDown")
_ARROW_UP = re.compile(r"ArrowUp")
_WALK = re.compile(r"\b(?:setTlIndex|ensureTlIndexVisible|visibleTlIndices)\b")
_DOCS_SHIFT = re.compile(r"Shift(?:-|\s+)?(?:click|select|j)", re.I)
_DOCS_COPY_N = re.compile(r"Copy\s*\{?n\}?\s*messages|Copy N messages", re.I)
_DOCS_BLANK = re.compile(r"blank[- ]line|time order|sent_at", re.I)
_DOCS_FIELD = re.compile(
    r"(?:#q|people filter|#person-filter).{0,200}(?:native|field|still cop)"
    r"|(?:native|field).{0,200}(?:#q|people filter|#person-filter)",
    re.I | re.S,
)
_HELPERS = (
    "TimelineSelect.ts",
    "timelineSelect.ts",
    "TimelineRange.ts",
    "selectRange.ts",
)
_PREF_NEW = re.compile(
    r"interlace\.(?:multiSelect|selectedIds|selection|messageSelection)"
)
_MAX94 = "max-w-[94%]"


def _helper_src(crate: Path) -> str:
    return "\n".join(_text(_web_file(crate, n)) for n in _HELPERS)


def _on_sel(list_raw: str, lst: str, pane: str) -> str:
    out = []
    for m in re.finditer(
        r"onSelectIndex\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}",
        list_raw + "\n" + lst,
    ):
        out.append(m.group(1))
    out.append(_fn_body(lst, "onSelectIndex"))
    out.append(_fn_body(pane, "onSelectIndex"))
    out.append(_fn_body(lst, "onSelect"))
    return "\n".join(out)


def _article_click(src: str) -> str:
    art = _article_span(src)
    m = re.search(r"onclick\s*=\s*\{", art)
    if not m:
        return ""
    depth, i = 1, m.end()
    while i < len(art) and depth:
        if art[i] == "{":
            depth += 1
        elif art[i] == "}":
            depth -= 1
        i += 1
    return art[m.end() : i - 1]


def _shift_windows(src: str) -> str:
    return "\n".join(
        src[max(0, m.start() - 220) : m.end() + 480] for m in _SHIFT.finditer(src)
    )


def _set_windows(src: str) -> str:
    return "\n".join(
        src[max(0, m.start() - 180) : m.end() + 360] for m in _SET_NAME.finditer(src)
    )


def _jk_block(keys: str) -> str:
    m = _KEY_J.search(keys)
    if not m:
        return keys
    return keys[max(0, m.start() - 80) : m.end() + 520]


def _escape_block(keys: str) -> str:
    m = re.search(
        r"(?:e\.)?key\s*===?\s*[\"']Escape[\"']|[\"']Escape[\"']\s*===?\s*(?:e\.)?key",
        keys,
    )
    return keys[m.start() : m.start() + 500] if m else ""


def _has_id_set(src: str) -> bool:
    if _SET_NAME.search(src) and _MESSAGE_ID.search(src):
        return True
    return bool(_NEW_SET.search(src) and _HAS_ID.search(src))


def assert_multiselect_copy(crate: Path) -> None:
    """#370: Shift-select a frozen message_id set; ⌘C copies N in sent_at order."""
    root = repo_root()
    rows_path = _web_file(crate, "TimelineRows.svelte")
    list_path = _web_file(crate, "TimelineList.svelte")
    pane_path = _web_file(crate, "TimelinePane.svelte")
    keys_path = _web_file(crate, "PeopleKeys.ts")
    if not rows_path.is_file():
        fail(f"{_ISSUE}: TimelineRows.svelte required (Shift-click + quiet ring)")
    if not list_path.is_file():
        fail(f"{_ISSUE}: TimelineList.svelte required (id set + copySelected)")
    if not pane_path.is_file():
        fail(f"{_ISSUE}: TimelinePane.svelte required (session Set + clear/keep)")
    if not keys_path.is_file():
        fail(f"{_ISSUE}: PeopleKeys.ts required (Shift+j/k + field-native ⌘C)")

    rows_raw, list_raw, pane_raw = (
        rows_path.read_text(),
        list_path.read_text(),
        pane_path.read_text(),
    )
    rows, lst, pane = (
        _without_comments(rows_raw),
        _without_comments(list_raw),
        _without_comments(pane_raw),
    )
    rows_m, list_m, pane_m = (
        _svelte_markup(rows_raw),
        _svelte_markup(list_raw),
        _svelte_markup(pane_raw),
    )
    keys = _without_comments(keys_path.read_text())
    app = _without_comments(_text(crate / "web" / "App.svelte"))
    shell_raw = _text(_web_file(crate, "PeopleShell.svelte"))
    shell, shell_m = _without_comments(shell_raw), _svelte_markup(shell_raw)
    prefs = _without_comments(_text(_web_file(crate, "PeoplePrefs.ts")))
    mail = _without_comments(_text(_web_file(crate, "TimelineMail.ts")))
    virt = _text(_web_file(crate, "TimelineVirtual.ts"))
    menu = _text(_web_file(crate, "TimelineCopyMenu.svelte"))
    attach = _text(_web_file(crate, "CasAttach.svelte"))
    helper = _without_comments(_helper_src(crate))
    en = _text(_web_file(crate, "locales/en.ts"))
    tr = _text(_web_file(crate, "locales/tr.ts"))
    docs = _text(root / "docs" / "user" / "app.md")
    handle = _fn_body(keys, "handleAppKey") or keys
    on_key = _fn_body(app, "onKey") or app
    sel_copy = _fn_body(lst, "copySelected") or _fn_body(pane, "copySelected")
    exp_copy = _expand_fn_calls(lst + "\n" + mail + "\n" + helper + "\n" + pane, sel_copy, 3)
    on_sel = _on_sel(list_raw, lst, pane)
    click = _article_click(rows_m) or _article_click(rows)
    art = _article_span(rows_m) or _article_span(rows)
    sel_person = _fn_body(pane, "selectPerson") or _fn_body(pane_raw, "selectPerson")
    open_at = _fn_body(pane, "openPersonAtMessage") or _fn_body(pane_raw, "openPersonAtMessage")
    go_last = _fn_body(pane, "goToLastRead") or _fn_body(pane_raw, "goToLastRead")
    opened = _fn_body(lst, "openCopyMenu")
    copy_text = _fn_body(lst, "copyText")
    chrome = "\n".join((pane, lst, rows, helper, keys, on_sel, click))
    web = _without_comments(_web_logic(crate))

    # --- keep #310 / #224 / #369 / #315 N=1 / #316 (pass today) ---
    if not _FIND_HOOK.search(pane_m):
        fail(f"{_ISSUE}: keep #310 find (data-tl-find / id=tl-find)")
    if not _VIRTUALIZE.search(virt) and not _VIRTUALIZE.search(lst):
        fail(f"{_ISSUE}: keep #224 VIRTUALIZE_AFTER = 250")
    if not _EST.search(virt) and not _EST.search(lst):
        fail(f"{_ISSUE}: keep #224 ESTIMATED_ROW_HEIGHT = 88")
    row_src = rows_m if _LAST_TIME_T.search(rows_m) else rows
    if not _LAST_TIME_T.search(row_src):
        fail(f"{_ISSUE}: keep #369 quiet t(\"lastTime\") sibling of <article>")
    if art and _LAST_TIME_T.search(art):
        fail(f"{_ISSUE}: keep #369 t(\"lastTime\") as a sibling of <article>")
    if _MAX94 not in (rows_m + rows):
        fail(f"{_ISSUE}: keep #111 / #206 hugging bubbles (max-w-[94%])")
    if "persistLastRead" not in on_sel and "persistLastRead" not in lst:
        fail(f"{_ISSUE}: keep #369 article click persistLastRead (caret)")
    if not re.search(r"setTlIndex[\s\S]{0,120}persistLastRead", app):
        fail(f"{_ISSUE}: keep #369 j/k setTlIndex persistLastRead (caret)")
    if not sel_copy or not re.search(r"\btlIndex\b", sel_copy):
        fail(f"{_ISSUE}: keep #315 N=1 copySelected of the in-memory tlIndex row")
    if not _DISPLAY.search(exp_copy):
        fail(f"{_ISSUE}: keep #315 displayBody(body_text || subject) on copy")
    if not _PAYLOAD.search(exp_copy) and not _PAYLOAD.search(sel_copy):
        fail(f"{_ISSUE}: keep #315 payload body_text || subject || \"\"")
    if not _WRITE_TEXT.search(exp_copy):
        fail(f"{_ISSUE}: keep #315 navigator.clipboard.writeText")
    if _steal_has_c(handle) or _steal_has_c(on_key):
        fail(
            f"{_ISSUE}: do not add \"c\" to the ⌘F/⌘K/digits steal list "
            "(#q / #person-filter keep native copy)"
        )
    if not _ROW_AUDIO.search(keys):
        fail(
            f"{_ISSUE}: keep #316 Space on [data-tl-index=\"${{tlIndex}}\"] "
            "[data-voice-note] audio"
        )
    if _COPY_TEXT_T.search(sel_copy + handle):
        fail(f"{_ISSUE}: keyboard copy path stays copySelected (no t() on ⌘C)")
    if not _fn_body(lst, "copyText"):
        fail(f"{_ISSUE}: keep the menu function named copyText (#204)")
    if not _COPY_TEXT_T.search(menu) or not _SEARCH_T.search(menu):
        fail(f"{_ISSUE}: keep t(\"copyText\") and t(\"search\") on the bubble menu")
    if "stopPropagation" not in attach:
        fail(f"{_ISSUE}: keep CasAttach stopPropagation (Reveal/Open, not Copy N)")
    if _REMOUNT.search(pane_m + "\n" + list_m + "\n" + shell_m):
        fail(f"{_ISSUE}: no {{#key}} remount of #person-timeline / TimelinePane")
    jk = _jk_block(keys)
    if not _ARROW_DOWN.search(jk) or not _WALK.search(jk):
        fail(f"{_ISSUE}: keep j / ArrowDown walking visibleTlIndices + setTlIndex")
    if not _KEY_K.search(keys) or not _ARROW_UP.search(keys):
        fail(f"{_ISSUE}: keep k / ArrowUp on the same walk as j")
    if _LAST_KEY_RX.search(prefs) is None:
        fail(f"{_ISSUE}: keep #369 interlace.lastRead (do not reuse it for the set)")

    # --- primary red today: Shift-click / frozen message_id set ---
    click_blob = click + "\n" + on_sel + "\n" + lst + "\n" + helper
    if not _SHIFT.search(click_blob) or not _has_id_set(chrome):
        fail(
            f"{_ISSUE}: Shift-click must fill a frozen Set of message_id "
            "(not tlIndex)"
        )

    # select-message-id — never tlIndex / data-tl-index.
    if _HAS_INDEX.search(chrome):
        fail(
            f"{_ISSUE}: the multi-select set is row.message_id, "
            "never tlIndex / data-tl-index"
        )
    if not _HAS_ID.search(rows + "\n" + lst + "\n" + helper):
        fail(
            f"{_ISSUE}: paint / extend must key the set with row.message_id "
            "(so scroll-off remounts the ring)"
        )

    # shift-click-range — contiguous filteredTimeline slice, frozen, not toggle.
    shift_blob = _shift_windows(click_blob + "\n" + keys + "\n" + pane)
    if not _RANGE_FILL.search(shift_blob + "\n" + helper):
        fail(
            f"{_ISSUE}: Shift-click fills a contiguous filteredTimeline range "
            "into the frozen id set (not a live re-range)"
        )
    if _TOGGLE.search(shift_blob) and not _RANGE_FILL.search(shift_blob):
        fail(f"{_ISSUE}: contiguous range, not Shift-toggle / free set")
    if not _ANCHOR.search(chrome) and not re.search(r"tlIndex", shift_blob):
        fail(
            f"{_ISSUE}: range anchor is the last plain click's message_id "
            "(first Shift+j/k uses the current tlIndex row)"
        )

    # shift-jk-range — Shift+j/k / ArrowDown/Up still setTlIndex + extend.
    if not _SHIFT.search(jk):
        fail(
            f"{_ISSUE}: Shift+j/k (and the existing ArrowDown/Up walk) must "
            "extend the id set and still setTlIndex / ensureTlIndexVisible"
        )
    if not _WALK.search(jk):
        fail(f"{_ISSUE}: Shift+j/k still walks visibleTlIndices")
    if not (_EXTEND.search(jk + "\n" + keys) or _SET_NAME.search(jk + "\n" + keys)):
        fail(f"{_ISSUE}: Shift+j/k must extend the frozen message_id set")

    # click-collapse — no-Shift click → set size 1 (that id), new anchor.
    if not re.search(r"!\s*(?:e\.)?shiftKey", click_blob):
        fail(
            f"{_ISSUE}: click without Shift collapses the set to that "
            "message_id (new anchor)"
        )

    # quiet-ring — selected ring-1 ring-ring; caret ring-2; both → caret wins.
    if not _RING1.search(art) or not _RING_RING.search(art):
        fail(
            f"{_ISSUE}: selected bubbles get a quiet ring-1 ring-ring "
            "(caret keeps ring-2 ring-ring)"
        )
    if not _RING2.search(art) or not re.search(r"\btlIndex\b", art):
        fail(f"{_ISSUE}: caret stays ring-2 ring-ring on item.index === tlIndex")
    if _SMOOTH.search(art) or _BOUNCE.search(art) or _FADE.search(art):
        fail(f"{_ISSUE}: no bounce / spring / behavior: \"smooth\" on the ring")
    if "data-bubble-body" in art and re.search(
        r"data-bubble-body[\s\S]{0,80}ring-1", art
    ):
        fail(f"{_ISSUE}: ring sits on <article>, not inside data-bubble-body")

    # copy-n-join — in-memory timeline[] by message_id; sent_at then id; \\n\\n.
    if not _N_GT1.search(sel_copy + "\n" + exp_copy):
        fail(
            f"{_ISSUE}: copySelected joins N>1 in-memory rows by message_id "
            "(N=1 still the #315 tlIndex row)"
        )
    if _INNER_TEXT.search(sel_copy):
        fail(
            f"{_ISSUE}: copy looks up loaded timeline[] by message_id — "
            "not article innerText / querySelectorAll"
        )
    if not re.search(r"\btimeline\b", exp_copy):
        fail(
            f"{_ISSUE}: ⌘C of N ids looks up in-memory timeline[] "
            "(chip-hidden ids still in timeline[] are in the paste; "
            "virtualizer unmount must not drop them)"
        )
    if not _SENT_AT.search(exp_copy) or not _MESSAGE_ID.search(exp_copy):
        fail(
            f"{_ISSUE}: sort copied bodies by sent_at then message_id "
            "(plain displayBody strings)"
        )
    if not _JOIN.search(exp_copy):
        fail(f"{_ISSUE}: join selected displayBody strings with a blank line (\\n\\n)")
    if not _DISPLAY.search(exp_copy):
        fail(f"{_ISSUE}: each slot is displayBody(body_text || subject || \"\")")
    if _SKIP_EMPTY.search(sel_copy) or _SKIP_EMPTY.search(exp_copy):
        fail(
            f"{_ISSUE}: empty displayBody still a blank paragraph "
            "(same as N=1 writeText(\"\"))"
        )
    if _HTML.search(exp_copy) or _GET_SEL.search(sel_copy):
        fail(f"{_ISSUE}: plain text only — not text/html / ClipboardItem / getSelection()")
    if _BODY_CACHE.search(chrome):
        fail(
            f"{_ISSUE}: set stores message_id only — copy skips rows missing "
            "from timeline[] (no cached body)"
        )
    if not re.search(r"\bcatch\b", exp_copy) or not re.search(r"\bonCopyFail\s*\(", exp_copy):
        fail(f"{_ISSUE}: writeText catch still onCopyFail")
    if _toast_args_include_body(shell + "\n" + exp_copy):
        fail(f"{_ISSUE}: keep #204 chrome toast only (no body_text in the toast)")
    if "Could not copy" not in shell and "onCopyFail" not in shell:
        fail(f"{_ISSUE}: keep PeopleShell onCopyFail chrome toast")

    # copy-n-menu — N>1 t("copyN").replace("{n}"); N=1 copyText; keep search.
    menu_blob = menu + "\n" + lst + "\n" + opened + "\n" + copy_text
    if not _COPY_N_T.search(menu_blob) or not _REPLACE_N.search(menu_blob):
        fail(
            f"{_ISSUE}: context menu N>1 is t(\"copyN\").replace(\"{{n}}\", String(n)) "
            "(Copy N messages)"
        )
    if not _COPY_TEXT_T.search(menu_blob):
        fail(f"{_ISSUE}: N=1 menu stays t(\"copyText\")")
    if not _SEARCH_T.search(menu):
        fail(f"{_ISSUE}: keep t(\"search\") on the bubble menu")
    if _FORWARD.search(menu):
        fail(f"{_ISSUE}: no Forward / Delete on the bubble menu")
    if not re.search(r"!\s*(?:selectedIds|selectedMessageIds).{0,80}\.has|collapse", opened, re.S):
        if not (
            _SET_NAME.search(opened)
            and re.search(r"message_id", opened)
            and _CLEAR_SET.search(opened + "\n" + copy_text)
        ):
            fail(
                f"{_ISSUE}: right-click a bubble outside the set collapses to "
                "that row then Copy text"
            )

    # session set: scroll/prepend keep; person/archive clear; chips keep.
    if _SET_NAME.search(lst + "\n" + pane) and re.search(
        r"computeVisibleRange|visibleRange|VIRTUALIZE_AFTER", lst + "\n" + virt
    ):
        vis = _fn_body(lst, "computeVisibleRange") + virt
        if _CLEAR_SET.search(vis):
            fail(
                f"{_ISSUE}: scrolling a selected row out of the window must not "
                "drop the id set"
            )
    if not _HEIGHT_SHIFT.search(sel_person) or not _PREPEND_SHIFT.search(sel_person):
        fail(f"{_ISSUE}: keep Load older tlIndex += n + shiftHeightsForPrepend")
    prepend_win = ""
    pm = _HEIGHT_SHIFT.search(sel_person)
    if pm:
        prepend_win = sel_person[max(0, pm.start() - 80) : pm.end() + 240]
    if _CLEAR_SET.search(prepend_win) or re.search(
        r"selectedIds[\s\S]{0,80}\+\s*(?:chrono|n)\b", sel_person
    ):
        fail(
            f"{_ISSUE}: prepend shifts tlIndex but must not drop or rewrite "
            "the message_id set (ids are not indices)"
        )
    if not _ID_NE_SEL.search(sel_person) or not _CLEAR_SET.search(sel_person):
        fail(
            f"{_ISSUE}: person switch (id !== selectedId) clears the set; "
            "same-person append / chips do not"
        )
    id_block = ""
    im = _ID_NE_SEL.search(sel_person)
    if im:
        id_block = sel_person[im.start() : im.start() + 500]
    if im and not _CLEAR_SET.search(id_block):
        fail(f"{_ISSUE}: clear the set inside id !== selectedId (Ada → Berk)")
    if _CLEAR_SET.search(open_at) is None and not re.search(
        r"messageId|message_id", open_at
    ):
        fail(
            f"{_ISSUE}: openPersonAtMessage / Last-time jump collapse the set "
            "to that id (seek, like click without Shift)"
        )
    if go_last and _SET_NAME.search(chrome) and not (
        _CLEAR_SET.search(go_last) or _SET_NAME.search(go_last) or "collapse" in go_last
    ):
        fail(f"{_ISSUE}: Last-time jump collapses the set to that message_id")
    if not _LOADED_CMP.search(pane + "\n" + rows + "\n" + helper):
        fail(
            f"{_ISSUE}: leftover File → Open (loadedArchiveId !== archive_id) "
            "must not paint rings from Ada's leftover rows"
        )
    for arg in _svelte_effect_args(pane) + _svelte_effect_args(lst):
        if _SET_NAME.search(arg) and (
            "nearestVisibleTlIndex" in arg or "snapFindHit" in arg or "filteredTimeline" in arg
        ):
            fail(
                f"{_ISSUE}: chip / find $effect must not insert the nearest "
                "visible id into the set (frozen; keep hidden ids)"
            )
    if _CLEAR_CHIPS.search(shift_blob + "\n" + on_sel):
        fail(f"{_ISSUE}: chip-hidden ids stay in the set — do not auto-clear chips")
    if _CLEAR_SET.search(_fn_body(pane, "onAttachKindChange")):
        fail(
            f"{_ISSUE}: attach-kind reload keeps the set; copy skips ids missing "
            "from timeline[]"
        )

    # last-read caret: Shift still persist; do not persist the set.
    if re.search(r"if\s*\(\s*!\s*(?:e\.)?shiftKey[\s\S]{0,100}persistLastRead", click_blob):
        fail(f"{_ISSUE}: Shift-click still persistLastRead of the caret (every hop)")
    if re.search(r"if\s*\(\s*!\s*(?:e\.)?shiftKey[\s\S]{0,100}setTlIndex", jk):
        fail(f"{_ISSUE}: Shift+j/k still setTlIndex (last-read follows the caret)")
    if _SET_NAME.search(prefs) or _PREF_NEW.search(prefs + "\n" + pane + "\n" + lst):
        fail(
            f"{_ISSUE}: session-only — not localStorage / PeoplePrefs / "
            "interlace.lastRead"
        )
    ls_keys = _ls_pref_keys(web + "\n" + prefs + "\n" + pane + "\n" + lst)
    extra_ls = [
        k
        for k in ls_keys
        if k.startswith("interlace.")
        and k
        not in {
            "interlace.lastRead",
            "interlace.peoplePins",
            "interlace.lastView",
            "interlace.lastPerson",
            "interlace.includeGroups",
            "interlace.sidebarCollapsed",
            "interlace.peopleSort",
            "interlace.density",
            "interlace.windowFrame",
            "interlace.recentArchives",
        }
        and re.search(r"select|multi|range", k, re.I)
    ]
    if extra_ls:
        fail(
            f"{_ISSUE}: no new prefs key for the selection set "
            f"({', '.join(sorted(set(extra_ls)))})"
        )

    # fields / Space / no extras.
    if _COPY_EVT.search(keys) or _COPY_EVT.search(lst):
        fail(f"{_ISSUE}: no window copy listener (PeopleKeys keydown ⌘C only)")
    space_m = re.search(
        r"(?:e\.)?key\s*===?\s*[\"'] [\"']|(?:e\.)?code\s*===?\s*[\"']Space",
        keys,
    )
    if space_m and _SET_NAME.search(keys[max(0, space_m.start() - 40) : space_m.end() + 280]):
        fail(f"{_ISSUE}: Space is not a playlist — still the tlIndex voice note")
    if _CMD_A.search(keys) or _CMD_A.search(handle):
        fail(f"{_ISSUE}: no Cmd-A select-all of a 40k thread")
    if _CMD_CLICK.search(click + "\n" + on_sel):
        fail(f"{_ISSUE}: no Cmd-click toggle")
    esc = _escape_block(handle)
    if _CLEAR_SET.search(esc) or _SET_NAME.search(esc):
        fail(f"{_ISSUE}: no Esc-collapse of the id set")
    if _CAP.search(chrome):
        fail(f"{_ISSUE}: cap is unnamed — do not invent 500 / MAX_SELECT")
    pkg = _text(crate / "package.json")
    toml = _text(crate / "Cargo.toml")
    if _CLIPBOARD_PLUGIN.search(pkg) or _CLIPBOARD_PLUGIN.search(toml):
        fail(f"{_ISSUE}: do not add a clipboard plugin (navigator.clipboard only)")

    # locale + D24.
    en_pack, tr_pack = _chrome_pack_entries(en), _chrome_pack_entries(tr)
    if "copyN" not in en_pack or "copyN" not in tr_pack:
        fail(f"{_ISSUE}: chrome key copyN must exist in both locales/en.ts and locales/tr.ts")
    ev, tv = en_pack.get("copyN", ""), tr_pack.get("copyN", "")
    if "{n}" not in ev or not re.search(r"message", ev, re.I):
        fail(f'{_ISSUE}: en.ts copyN is "Copy {{n}} messages"')
    if ev and tv and ev == tv:
        fail(f"{_ISSUE}: tr.ts copyN must not be an English copy (#131 / #278)")
    if re.search(r"\bCopy\b", tv):
        fail(f"{_ISSUE}: tr.ts copyN must not be an English copy")
    loc = crate / "web" / "lib" / "locales"
    extra = [
        p.name
        for p in loc.iterdir()
        if p.is_file() and p.suffix in {".ts", ".json"} and p.stem not in {"en", "tr"}
    ]
    if extra:
        fail(f"{_ISSUE}: no third locale pack ({', '.join(sorted(extra))})")
    if not docs.strip():
        fail(f"{_ISSUE}: docs/user/app.md required — Shift-select / Copy N")
    if not _DOCS_SHIFT.search(docs):
        fail(f"{_ISSUE}: docs/user/app.md must say Shift-click / Shift-select")
    if not _DOCS_COPY_N.search(docs):
        fail(f"{_ISSUE}: docs/user/app.md must say Copy N messages")
    if not _DOCS_BLANK.search(docs):
        fail(
            f"{_ISSUE}: docs/user/app.md must say ⌘C pastes N bodies in time "
            "order, blank-line separated"
        )
    if not _DOCS_FIELD.search(docs):
        fail(f"{_ISSUE}: docs/user/app.md must say #q / people filter keep native copy")
    if re.search(r"/Users/|/home/", chrome + "\n" + docs):
        fail(f"{_ISSUE}: tests stay placeholders (Ada / Berk) — no real home paths")
