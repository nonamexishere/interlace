"""#375 — Review queue keyboard map (pane-local keys).

Confirmed mix (2026-09-21): ReviewPane local window keydown (Search
onHitsKey shape). Do not add Review j/k to handleAppKey. Keep
`if (ctx.view !== "people") return`. Stop App Esc (App.svelte onKey
and handleAppKey) while a confirm / [role="dialog"] is open; Dialog
still dismisses; stay on Review; do not run confirmRun. Esc with no
dialog still view = "people". j/k / arrows stop at ends. Open the
first card on load; after accept/reject if the open id vanished, open
the new first remaining. Enter opens detail if closed (first remaining);
no-op if detail is already open. a when !canAccept() is a no-op. No u.
data-review-open on the open list row; keep bg-accent; no aria-selected
/ listbox rewrite. N-way native checkboxes; Space when focused is
native; keys skip INPUT / TEXTAREA / SELECT. Existing confirm copy.
Search #q and People j/k unchanged. I2 unchanged. No bulk / auto-accept.

Not handleAppKey Review j/k. Not wait-for-Enter. Not wrap. Not u.

Placeholders Ada / Berk / Self. Same ChromeKey on en.ts + tr.ts if a
new string appears.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.import_boot_guards import _app_keydown_body, _input_guard_span
from tauri_gate.keyboard_lib import (
    _INPUT_TAG_GUARD,
    _KEY_ARROW_DOWN,
    _KEY_ARROW_UP,
    _KEY_J,
    _KEY_K,
    _PREVENT_DEFAULT,
    _VIEW_PEOPLE_ASSIGN,
)
from tauri_gate.last_read import _text, _web_file
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.review_queue import _review_fn_body
from tauri_gate.scan import (
    _expand_fn_calls,
    _function_body,
    _match_closer,
    _matching_each_end,
    _search_pane_blob,
    _svelte_markup,
    _ts_fn_body,
    _without_comments,
)
from tauri_gate.search_picker_lib import _SEARCH_Q_ID
from tauri_gate.status_toasts_chrome import _KEY_ESC, _windows_around
from tauri_gate.status_toasts_toast import _svelte_effect_args

_ISSUE = "#375"

_LISTEN = re.compile(
    r"addEventListener\s*\(\s*[\"']keydown[\"']\s*,\s*([A-Za-z_][\w]*)"
)
_LISTEN_ANON = re.compile(
    r"addEventListener\s*\(\s*[\"']keydown[\"']\s*,\s*(?:async\s*)?\("
)
_LISTEN_CAPTURE = re.compile(
    r"addEventListener\s*\(\s*[\"']keydown[\"']\s*,\s*[^,)]+?\s*,\s*"
    r"(?:true|\{[^}]{0,80}\bcapture\s*:\s*true)"
)
_REMOVE_LISTEN = re.compile(
    r"removeEventListener\s*\(\s*[\"']keydown[\"']"
)
_KEY_A = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']a[\"']|[\"']a[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*===?\s*[\"']A[\"']"
)
_KEY_R = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']r[\"']|[\"']r[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*===?\s*[\"']R[\"']"
)
_KEY_U = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']u[\"']|[\"']u[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*===?\s*[\"']U[\"']"
)
_KEY_ENTER = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']Enter[\"']"
    r"|[\"']Enter[\"']\s*===?\s*(?:e\.)?key"
)
_KEY_SPACE = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"'] [\"']"
    r"|[\"'] [\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*===?\s*[\"']Space(?:bar)?[\"']"
    r"|(?:e\.)?code\s*===?\s*[\"']Space(?:bar)?[\"']"
)
_OPEN_ROW = re.compile(r"\bopenRow\s*\(")
_ACCEPT_CALL = re.compile(r"\baccept\s*\(")
_REJECT_CALL = re.compile(r"\breject\s*\(")
_ASK_CALL = re.compile(r"\bask\s*\(")
_CAN_ACCEPT = re.compile(r"\bcanAccept\s*\(")
_REQUEST_UNDO = re.compile(r"\brequestUndo\s*\(")
_REVIEW_ACCEPT_IPC = re.compile(r"\breviewAccept\s*\(")
_REVIEW_REJECT_IPC = re.compile(r"\breviewReject\s*\(")
_CONFIRM_RUN = re.compile(r"\bconfirmRun\s*\(")
_LINK_COPY = re.compile(r"""t\s*\(\s*["']linkThesePeople["']\s*\)""")
_STOP_COPY = re.compile(r"""t\s*\(\s*["']stopSuggesting["']\s*\)""")
_LINK_DESC = re.compile(r"""t\s*\(\s*["']linkThesePeopleDesc["']\s*\)""")
_STOP_DESC = re.compile(r"""t\s*\(\s*["']stopSuggestingDesc["']\s*\)""")
_ROWS0 = re.compile(
    r"\brows\s*(?:\[\s*0\s*\]|\.at\s*\(\s*0\s*\))"
    r"|\brows\s*\[\s*0\s*\]\s*\.id"
)
_WRAP = re.compile(
    r"%\s*(?:rows|queue|list|visible)?\s*\.?\s*length"
    r"|\bwrap(?:Around|s)?\b"
    r"|\bmodulo\b",
    re.I,
)
_STOP_END = re.compile(
    r"length\s*-\s*1"
    r"|\bMath\.min\b"
    r"|next\s*<\s*0"
    r"|next\s*>=\s*"
    r"|<\s*0\s*\|\|"
    r"|>=\s*(?:rows|queue|list)?\s*\.?\s*length"
)
_STOP_START = re.compile(
    r">\s*0\b"
    r"|\bMath\.max\b"
    r"|next\s*<\s*0"
    r"|<\s*0\b"
    r"|pos\s*>\s*0"
    r"|i\s*>\s*0"
    r"|index\s*>\s*0"
)
_DETAIL_CLOSED = re.compile(
    r"!\s*detail\b"
    r"|\bdetail\s*===\s*null"
    r"|\bdetail\s*==\s*null"
    r"|\bdetail\s*===\s*undefined"
    r"|\b!detail\b"
)
_DIALOG_SKIP = re.compile(
    r"defaultPrevented"
    r"|\[role=[\"']dialog[\"']\]"
    r"|role\s*=\s*[\"']dialog[\"']"
    r"|querySelector\s*(?:<[^>]+>)?\s*\(\s*[`'\"][^`'\"]*role"
    r"[^`'\"]*dialog"
    r"|\bconfirmOpen\b"
)
_ROLE_DIALOG = re.compile(
    r"\[role=[\"']dialog[\"']\]"
    r"|querySelector\s*(?:<[^>]+>)?\s*\(\s*[`'\"][^`'\"]*dialog"
)
_DEFAULT_PREV = re.compile(r"\bdefaultPrevented\b")
_PEOPLE_RETURN = re.compile(
    r"if\s*\(\s*(?:ctx\.)?view\s*!==?\s*[\"']people[\"']\s*\)\s*"
    r"(?:\{\s*)?return\s*;"
)
_REVIEW_VIEW_EQ = re.compile(
    r"(?:ctx\.)?view\s*===?\s*[\"']review[\"']"
)
_SET_VIEW_PEOPLE = re.compile(
    r"\bsetView\s*\(\s*[\"']people[\"']\s*\)"
    r"|\bview\s*=\s*[\"']people[\"']"
)
_VOID_JK = re.compile(
    r"void\s*\(\s*(?:e\.)?key\s*===?\s*[\"']j[\"']\s*\|\|"
    r"\s*(?:e\.)?key\s*===?\s*[\"']k[\"']\s*\)"
)
_OPEN_HOOK = re.compile(r"\bdata-review-open\b")
_CARD_HOOK = re.compile(r"\bdata-review-card\b")
_UNDO_HOOK = re.compile(r"\bdata-review-undo\b")
_BG_ACCENT = re.compile(r"\bbg-accent\b")
_ARIA_SELECTED = re.compile(r"\baria-selected\b")
_LISTBOX = re.compile(r"""role\s*=\s*["']listbox["']""")
_OPTION_ROLE = re.compile(r"""role\s*=\s*["']option["']""")
_CHECKBOX = re.compile(
    r"<input\b[^>]*\btype\s*=\s*[\"']checkbox[\"']"
    r"|type\s*=\s*[\"']checkbox[\"'][^>]*>",
    re.I | re.S,
)
_SELECT_ALL = re.compile(r"\bselectAll\b")
_SELECT_NONE = re.compile(r"\bselectNone\b")
_TOGGLE = re.compile(r"\btoggle\s*\(")
_META = re.compile(r"\b(?:e\.)?(?:metaKey|ctrlKey|altKey)\b")
_NO_MOD = re.compile(
    r"!\s*(?:e\.)?(?:metaKey|ctrlKey|altKey)"
    r"|\bmetaKey\s*\|\|\s*(?:e\.)?ctrlKey\s*\|\|\s*(?:e\.)?altKey"
    r"|\bctrlKey\s*\|\|\s*(?:e\.)?metaKey\s*\|\|\s*(?:e\.)?altKey"
)
_PALETTE = re.compile(r"\[data-command-palette\]")
_CONFIRM_OPEN = re.compile(r"\bconfirmOpen\b")
_SMOOTH = re.compile(r"behavior\s*:\s*[\"']smooth[\"']")
_TRANSITION = re.compile(r"\btransition\s*:")
_BOUNCE = re.compile(r"\bbounce\b|\banimate-bounce\b")
_STOP_PROP = re.compile(r"\bstopPropagation\s*\(")
_T_CALL = re.compile(r"""\bt\s*\(\s*["']([A-Za-z_][A-Za-z0-9_]*)["']\s*\)""")
_VISIBLE_TL = re.compile(r"\bvisibleTlIndices\b")
_TL_INDEX = re.compile(r"\btlIndex\b")
_BULK = re.compile(
    r"\b(?:acceptAll|bulkAccept|reviewAcceptAll|autoAccept|autoMerge)\b"
    r"|for\s*\(\s*(?:const|let|var)\s+\w+\s+of\s+rows"
    r"|rows\.forEach\s*\("
    r"|for\s*\(\s*let\s+\w+\s*=\s*0\s*;\s*\w+\s*<\s*rows\.length"
)
_AUTO_MERGE = re.compile(
    r"\bauto[-_ ]?merge\b|\bauto[-_ ]?accept\b|\bname_score\b",
    re.I,
)
_RAW_ID = re.compile(
    r"#\{\s*r\.id\s*\}"
    r"|person\s+\$\{"
    r"|Accept review \$\{id\}"
)
_MAIL_TO = re.compile(r"\bdata-mail-to\b")
_INSPECTOR = re.compile(r"\bdata-person-inspector\b")
_ONHITS = re.compile(r"\bonHitsKey\b")
_CAN_ACCEPT_NWAY = re.compile(
    r"selected\.length\s*>=\s*2"
    r"|selected\.length\s*>\s*1"
)
_OPEN_FALSE = re.compile(r"\bopen\s*=\s*false\b")
_AWAIT_ONCONFIRM = re.compile(r"await\s+onconfirm\s*\(")
_FOCUS_ACCEPT = re.compile(
    r"\bfocus\s*\(\s*\)[\s\S]{0,80}Accept"
    r"|Accept[\s\S]{0,80}\.focus\s*\("
    r"|querySelector[\s\S]{0,80}Accept[\s\S]{0,40}\.focus"
)
_DOCS_REVIEW_JK = re.compile(
    r"("
    r"Review.{0,160}(?:j\s*/\s*k|`j`/`k`|j/k).{0,160}"
    r"(?:open card|queue|card)"
    r"|(?:j\s*/\s*k|`j`/`k`|j/k).{0,160}Review.{0,80}"
    r"(?:open card|queue|card)"
    r")",
    re.I | re.S,
)
_DOCS_AR = re.compile(
    r"("
    r"Review.{0,200}(?:\ba\b.{0,40}\br\b|\ba\s*/\s*r\b|`a`/`r`).{0,120}"
    r"(?:Accept|Reject|confirm)"
    r"|(?:\ba\s*/\s*r\b|`a`/`r`).{0,80}(?:Accept|Reject)"
    r")",
    re.I | re.S,
)
_DOCS_ENTER = re.compile(
    r"Review.{0,200}\bEnter\b.{0,160}(?:open|detail|card)",
    re.I | re.S,
)
_DOCS_ESC_CONFIRM = re.compile(
    r"("
    r"Esc(?:ape)?.{0,200}(?:confirm|dialog).{0,160}"
    r"(?:stay|stays|Review|dismiss|cancel)"
    r"|(?:confirm|dialog).{0,160}Esc(?:ape)?.{0,160}"
    r"(?:stay|stays|Review|dismiss|cancel)"
    r")",
    re.I | re.S,
)
_DOCS_ESC_LEAVE = re.compile(
    r"("
    r"Esc(?:ape)?.{0,200}(?:People|leave Review|back to People)"
    r"|back to People.{0,80}Review"
    r")",
    re.I | re.S,
)
_DOCS_Q = re.compile(
    r"("
    r"#q.{0,80}(?:never intercepted|types|unchanged)"
    r"|Typing in Search `#q` is never intercepted"
    r")",
    re.I | re.S,
)
_DOCS_PEOPLE_JK = re.compile(
    r"("
    r"`j`/`k` still move messages"
    r"|j/`k` still move messages"
    r"|People.{0,80}(?:j\s*/\s*k|`j`/`k`|j/k).{0,80}(?:message|timeline)"
    r")",
    re.I | re.S,
)
_DOCS_CHECKBOX = re.compile(
    r"("
    r"checkbox.{0,80}Space"
    r"|Space.{0,80}checkbox"
    r")",
    re.I | re.S,
)
_DOCS_FIRST = re.compile(
    r"("
    r"first card.{0,80}open"
    r"|opens the first"
    r"|k then j"
    r")",
    re.I | re.S,
)
_PLACEHOLDER_CHROME = re.compile(r"\bAda\b|\bBerk\b|\bSelf\b")
_HTTP = re.compile(r"https?://", re.I)
_PRIMARY = (
    f"{_ISSUE}: ReviewPane must listen for window keydown "
    "(Search onHitsKey shape) so j/k move the open card"
)


def _fn(src: str, name: str) -> str:
    return _ts_fn_body(src, name) or _function_body(src, name) or ""


def _near(src: str, m: re.Match[str], before: int = 220, after: int = 420) -> str:
    return src[max(0, m.start() - before) : m.end() + after]


def _if_block(src: str, m: re.Match[str]) -> str:
    start = src.rfind("if", 0, m.start())
    if start < 0:
        start = max(0, m.start() - 80)
    brace = src.find("{", m.start())
    semi = src.find(";", m.start())
    if brace < 0 or (semi >= 0 and semi < brace):
        return src[start : (semi + 1 if semi >= 0 else m.end() + 240)]
    end = _match_closer(src, brace)
    if end < brace:
        return src[start : brace + 400]
    return src[start : end + 1]


def _keydown_handler(src: str) -> str:
    m = _LISTEN.search(src)
    if m:
        body = _fn(src, m.group(1))
        if body:
            return body
    anon = _LISTEN_ANON.search(src)
    if anon:
        brace = src.find("{", anon.end() - 1)
        if brace >= 0:
            end = _match_closer(src, brace)
            if end > brace:
                return src[brace + 1 : end]
    return _app_keydown_body(src)


def _each_rows_block(markup: str) -> str:
    m = re.search(r"\{#each\s+rows\b", markup)
    if not m:
        return ""
    end = _matching_each_end(markup, m.start())
    if end < 0:
        return markup[m.start() : m.start() + 1200]
    return markup[m.start() : end]


def _open_first_blob(src: str) -> str:
    parts = [_fn(src, "reload")]
    for name in ("applyList", "afterReload", "ensureOpen", "openFirst"):
        inner = _fn(src, name)
        if inner:
            parts.append(inner)
    parts.extend(_svelte_effect_args(src))
    reload = parts[0]
    if reload:
        parts.append(_expand_fn_calls(src, reload, depth=2))
    return "\n".join(parts)


def _esc_leave_window(src: str) -> str:
    bits: list[str] = []
    for m in _KEY_ESC.finditer(src):
        bits.append(_if_block(src, m))
    if not bits:
        bits.append(_windows_around(src, _KEY_ESC, 80, 520))
    return "\n".join(bits)


def _letter_before_guard(handler: str, rx: re.Pattern[str]) -> bool:
    span = _input_guard_span(handler)
    if not span:
        return bool(rx.search(handler))
    pre = handler[: span[0]]
    for m in rx.finditer(pre):
        win = _near(handler, m, 70, 40)
        if re.search(r"\b(?:metaKey|ctrlKey)\b", win) and not re.search(
            r"!\s*(?:e\.)?(?:metaKey|ctrlKey)", win
        ):
            continue
        return True
    return False


def assert_review_keys(crate: Path) -> None:
    """#375: Review queue j/k / Enter / a / r; confirm Esc stays on Review."""
    root = repo_root()
    review_path = _web_file(crate, "ReviewPane.svelte")
    keys_path = _web_file(crate, "PeopleKeys.ts")
    app_path = crate / "web" / "App.svelte"
    confirm_path = _web_file(crate, "ConfirmDialog.svelte")
    search_path = _web_file(crate, "SearchPane.svelte")
    rows_path = _web_file(crate, "TimelineRows.svelte")
    insp_path = _web_file(crate, "PeopleInspector.svelte")
    en_path = crate / "web" / "lib" / "locales" / "en.ts"
    tr_path = crate / "web" / "lib" / "locales" / "tr.ts"
    docs_path = root / "docs" / "user" / "app.md"

    if not review_path.is_file():
        fail(f"{_ISSUE}: ReviewPane.svelte required (Review queue keyboard map)")

    review_raw = _text(review_path)
    review = _without_comments(review_raw)
    markup = _svelte_markup(review_raw)
    keys_raw = _text(keys_path)
    keys = _without_comments(keys_raw)
    app_raw = _text(app_path)
    app = _without_comments(app_raw)
    confirm_raw = _text(confirm_path)
    confirm = _without_comments(confirm_raw)
    search_raw = _search_pane_blob(crate) if search_path.is_file() else _text(search_path)
    search = _without_comments(search_raw)
    search_m = _svelte_markup(search_raw)
    docs = _text(docs_path)
    rows_raw = _text(rows_path)
    insp_raw = _text(insp_path)

    handler = _keydown_handler(review)
    handler_x = _expand_fn_calls(review, handler, depth=2) if handler else ""
    listen = _LISTEN.search(review) or _LISTEN_ANON.search(review)

    # 1) Primary red today — pane-local window keydown (Search onHitsKey).
    if not listen or not handler:
        fail(_PRIMARY)
    if not _KEY_J.search(handler) or not _KEY_K.search(handler):
        fail(_PRIMARY)
    if not _OPEN_ROW.search(handler) and not _OPEN_ROW.search(handler_x):
        fail(_PRIMARY)

    # 2) arrows move with j/k; preventDefault so the pane does not scroll.
    if not _KEY_ARROW_DOWN.search(handler) or not _KEY_ARROW_UP.search(handler):
        fail(
            f"{_ISSUE}: j/k and ArrowDown/Up must move the open card "
            "(unchorded; Search onHitsKey shape)"
        )
    j_win = "\n".join(_if_block(handler, m) for m in _KEY_J.finditer(handler))
    k_win = "\n".join(_if_block(handler, m) for m in _KEY_K.finditer(handler))
    down_win = "\n".join(
        _if_block(handler, m) for m in _KEY_ARROW_DOWN.finditer(handler)
    )
    up_win = "\n".join(
        _if_block(handler, m) for m in _KEY_ARROW_UP.finditer(handler)
    )
    move_blob = j_win + k_win + down_win + up_win + "\n" + handler_x
    if not _PREVENT_DEFAULT.search(j_win + down_win + handler):
        fail(
            f"{_ISSUE}: handled j / ArrowDown must preventDefault "
            "(webview must not scroll the pane)"
        )
    if not _PREVENT_DEFAULT.search(k_win + up_win + handler):
        fail(
            f"{_ISSUE}: handled k / ArrowUp must preventDefault "
            "(webview must not scroll the pane)"
        )

    # 3) wrap — stop at ends (Search / People). Not wrap.
    if _WRAP.search(handler) or _WRAP.search(handler_x):
        fail(f"{_ISSUE}: j/k / arrows stop at ends — do not wrap the queue")
    if not _STOP_END.search(move_blob) and not _STOP_END.search(handler_x):
        fail(
            f"{_ISSUE}: j / ArrowDown must stop on the last card "
            "(no wrap; bound on rows.length)"
        )
    if not _STOP_START.search(move_blob) and not _STOP_START.search(handler_x):
        fail(
            f"{_ISSUE}: k / ArrowUp must stop on the first card "
            "(no wrap; bound > 0 / next < 0)"
        )

    # 4) site — Review letters live in ReviewPane, not handleAppKey.
    if _LISTEN_CAPTURE.search(review):
        fail(
            f"{_ISSUE}: Review keydown is window bubble "
            "(Search onHitsKey) — not capture (bits-ui EscapeLayer)"
        )
    if not _REMOVE_LISTEN.search(review):
        fail(
            f"{_ISSUE}: remove the Review keydown listener on destroy "
            "(pane unmounts when leaving Review)"
        )
    handle = _fn(keys, "handleAppKey")
    if not handle:
        fail(f"{_ISSUE}: keep handleAppKey (People-only j/k stay there)")
    if _REVIEW_VIEW_EQ.search(handle):
        fail(
            f"{_ISSUE}: do not add Review j/k to handleAppKey "
            "(no view === \"review\" branch; pane-local listener owns the map)"
        )
    if _OPEN_ROW.search(handle) or _ACCEPT_CALL.search(handle):
        fail(
            f"{_ISSUE}: Review openRow / accept stay in ReviewPane — "
            "not handleAppKey"
        )
    people_gate = _PEOPLE_RETURN.search(handle)
    if not people_gate:
        fail(
            f"{_ISSUE}: keep if (ctx.view !== \"people\") return "
            "so timeline j/k stay People-only (#132)"
        )
    prefix, tail = handle[: people_gate.start()], handle[people_gate.end() :]
    if (_KEY_J.search(prefix) or _KEY_K.search(prefix)) and _TL_INDEX.search(
        prefix
    ):
        fail(
            f"{_ISSUE}: timeline j/k must stay after the people-only return "
            "(do not steal Search / Review)"
        )
    if not _KEY_J.search(tail) or not _KEY_K.search(tail):
        fail(f"{_ISSUE}: keep People timeline j/k after the people-only return")
    if not _VISIBLE_TL.search(tail) and not _VISIBLE_TL.search(handle):
        fail(
            f"{_ISSUE}: People j/k still walk visibleTlIndices "
            "(do not rewrite #132 / #214)"
        )
    if _WRAP.search(tail):
        fail(f"{_ISSUE}: People timeline j/k still stop at ends (no wrap)")
    on_key = _app_keydown_body(app) or _app_keydown_body(app_raw)
    if not _VOID_JK.search(on_key) and not _VOID_JK.search(app):
        fail(
            f"{_ISSUE}: keep App onKey void (e.key === \"j\" || e.key === \"k\")"
        )

    # 5) open-first — after load, non-empty queue with no detail opens first.
    first_blob = _open_first_blob(review)
    if not _OPEN_ROW.search(first_blob) or not _ROWS0.search(first_blob):
        fail(
            f"{_ISSUE}: after load, if the queue is non-empty and no detail, "
            "open the first card (so k then j needs no mouse)"
        )
    reload_body = _fn(review, "reload")
    reload_x = _expand_fn_calls(review, reload_body, depth=2) if reload_body else ""
    vanish = reload_x + "\n" + first_blob
    if not _OPEN_ROW.search(vanish) or not _ROWS0.search(vanish):
        fail(
            f"{_ISSUE}: after accept/reject, if the open id vanished, "
            "open the new first remaining (or none if empty)"
        )

    # 6) enter-open — Enter opens first remaining if !detail; no-op if open.
    enter_win = "\n".join(
        _if_block(handler, m) for m in _KEY_ENTER.finditer(handler)
    )
    if not _KEY_ENTER.search(handler):
        fail(
            f"{_ISSUE}: Enter opens the first remaining card when detail is "
            "closed (no-op if already open)"
        )
    enter_x = _expand_fn_calls(review, enter_win or handler, depth=2)
    if not _DETAIL_CLOSED.search(enter_win) and not _DETAIL_CLOSED.search(handler):
        fail(
            f"{_ISSUE}: Enter with detail already open is a no-op "
            "(do not focus Accept; open only when !detail)"
        )
    if _FOCUS_ACCEPT.search(enter_win) or _ACCEPT_CALL.search(enter_win):
        fail(
            f"{_ISSUE}: Enter with detail open must not focus Accept / call "
            "accept() — no-op"
        )
    if not _OPEN_ROW.search(enter_win) and not _OPEN_ROW.search(enter_x):
        fail(
            f"{_ISSUE}: Enter with no detail must openRow the first remaining "
            "card"
        )
    if not _ROWS0.search(enter_win) and not _ROWS0.search(enter_x) and not _ROWS0.search(
        handler_x
    ):
        fail(f"{_ISSUE}: Enter with no detail opens rows[0] (first remaining)")

    # 7) a / r — existing accept() / reject() + confirm copy. a-disabled no-op.
    a_win = "\n".join(_if_block(handler, m) for m in _KEY_A.finditer(handler))
    r_win = "\n".join(_if_block(handler, m) for m in _KEY_R.finditer(handler))
    if not _KEY_A.search(handler):
        fail(
            f"{_ISSUE}: unchorded a must call existing accept() "
            "(ask t(\"linkThesePeople\"); no-op when !canAccept())"
        )
    if not _ACCEPT_CALL.search(a_win) and not _ACCEPT_CALL.search(handler):
        fail(
            f"{_ISSUE}: unchorded a must call existing accept() "
            "(do not ask() a confirm that cannot complete)"
        )
    accept_body = _review_fn_body(review, "accept") or _fn(review, "accept")
    if not accept_body:
        fail(f"{_ISSUE}: keep accept() (a goes through it)")
    if not _CAN_ACCEPT.search(accept_body):
        fail(
            f"{_ISSUE}: a when !canAccept() is a no-op — keep accept() "
            "early-return on !canAccept()"
        )
    if not _ASK_CALL.search(accept_body) or not _LINK_COPY.search(accept_body):
        fail(
            f"{_ISSUE}: a still ask(t(\"linkThesePeople\"), …) — "
            "do not reviewAccept without confirm"
        )
    if _REVIEW_ACCEPT_IPC.search(a_win) and not _ASK_CALL.search(accept_body):
        fail(f"{_ISSUE}: a must not call reviewAccept until confirm")
    if not _KEY_R.search(handler):
        fail(
            f"{_ISSUE}: unchorded r must call existing reject() "
            "(ask t(\"stopSuggesting\"))"
        )
    if not _REJECT_CALL.search(r_win) and not _REJECT_CALL.search(handler):
        fail(f"{_ISSUE}: unchorded r must call existing reject()")
    reject_body = _review_fn_body(review, "reject") or _fn(review, "reject")
    if not reject_body:
        fail(f"{_ISSUE}: keep reject() (r goes through it)")
    if not _ASK_CALL.search(reject_body) or not _STOP_COPY.search(reject_body):
        fail(
            f"{_ISSUE}: r still ask(t(\"stopSuggesting\"), …) — "
            "existing Reject confirm copy"
        )
    if not _LINK_DESC.search(accept_body):
        fail(f"{_ISSUE}: keep t(\"linkThesePeopleDesc\") on Accept confirm")
    if not _STOP_DESC.search(reject_body):
        fail(f"{_ISSUE}: keep t(\"stopSuggestingDesc\") on Reject confirm")

    # 8) undo-key — no u. Undo stays data-review-undo click.
    u_win = "\n".join(_if_block(handler, m) for m in _KEY_U.finditer(handler))
    if _KEY_U.search(handler) and (
        _REQUEST_UNDO.search(u_win + handler) or _REQUEST_UNDO.search(handler_x)
    ):
        fail(
            f"{_ISSUE}: do not bind u to Undo last link "
            "(data-review-undo stays the click control)"
        )
    if not _UNDO_HOOK.search(review_raw):
        fail(f"{_ISSUE}: keep data-review-undo (#221) — click, not a letter")

    # 9) checkbox Space native — do not bind Space; INPUT guard first.
    if _KEY_SPACE.search(handler):
        fail(
            f"{_ISSUE}: Review handler must not bind Space "
            "(focused N-way checkbox keeps native Space; #316 stays People)"
        )
    if not _INPUT_TAG_GUARD.search(handler):
        fail(
            f"{_ISSUE}: Review handler must return on INPUT / TEXTAREA / SELECT "
            "before j/k/a/r/Enter (chrome search + checkbox)"
        )
    for rx, label in (
        (_KEY_J, "j"),
        (_KEY_K, "k"),
        (_KEY_A, "a"),
        (_KEY_R, "r"),
        (_KEY_ENTER, "Enter"),
    ):
        if _letter_before_guard(handler, rx):
            fail(
                f"{_ISSUE}: do not handle {label} before the "
                "INPUT/TEXTAREA/SELECT guard (do not steal from a field)"
            )
    if not _CHECKBOX.search(markup) and not _CHECKBOX.search(review_raw):
        fail(
            f"{_ISSUE}: keep native N-way <input type=\"checkbox\"> "
            "(Space when focused is native; still clickable)"
        )
    if not _SELECT_ALL.search(review) or not _SELECT_NONE.search(review):
        fail(f"{_ISSUE}: keep Select all / none (N-way stays clickable)")
    if not _TOGGLE.search(review):
        fail(f"{_ISSUE}: keep checkbox toggle() (no keyboard-only replacement)")

    # 10) ignore meta/ctrl/alt so ⌘K / ⌘A stay; skip dialog / palette.
    if not _NO_MOD.search(handler) and not _META.search(handler):
        fail(
            f"{_ISSUE}: ignore a/r/j/k/Enter when meta/ctrl/alt "
            "(⌘K / ⌘A stay App's)"
        )
    if not _CONFIRM_OPEN.search(handler) and not _ROLE_DIALOG.search(handler):
        fail(
            f"{_ISSUE}: Review handler returns while confirmOpen / "
            "[role=\"dialog\"] so a does not re-ask"
        )
    if not _PALETTE.search(handler) and "[data-command-palette]" not in handler:
        # Palette is optional if App already owns ⌘K; still skip if focused.
        if "command" not in handler.lower() and not _PALETTE.search(review):
            fail(
                f"{_ISSUE}: Review handler must skip [data-command-palette] "
                "(do not steal palette keys)"
            )

    # 11) queue-chrome — data-review-open on the open list row; keep bg-accent.
    each = _each_rows_block(markup) or _each_rows_block(review_raw)
    if not _OPEN_HOOK.search(each) and not _OPEN_HOOK.search(markup):
        fail(
            f"{_ISSUE}: open list row must set data-review-open "
            "(keep bg-accent; not detail-only)"
        )
    if not _OPEN_HOOK.search(each):
        fail(
            f"{_ISSUE}: data-review-open belongs on the queue <button> "
            "(each rows), not only data-review-card"
        )
    if not _BG_ACCENT.search(each) and not _BG_ACCENT.search(markup):
        fail(f"{_ISSUE}: keep bg-accent on the open queue row")
    if _ARIA_SELECTED.search(each) or _LISTBOX.search(markup) or _OPTION_ROLE.search(
        each
    ):
        fail(
            f"{_ISSUE}: do not add aria-selected / listbox rewrite "
            "(queue stays buttons; data-review-open only)"
        )
    if not _CARD_HOOK.search(review_raw):
        fail(f"{_ISSUE}: keep data-review-card on the detail Card (#221)")

    # 12) esc-confirm — stop App Esc while a dialog is open; stay on Review.
    if not on_key.strip():
        fail(f"{_ISSUE}: App.svelte onKey required (Esc must not leave Review)")
    app_esc = _esc_leave_window(on_key)
    if not _SET_VIEW_PEOPLE.search(app_esc) and not _VIEW_PEOPLE_ASSIGN.search(app_esc):
        fail(
            f"{_ISSUE}: Esc with no dialog still view = \"people\" from Review "
            "(#132; do not invent a Review Esc stack)"
        )
    if not _DIALOG_SKIP.search(app_esc) and not _DEFAULT_PREV.search(on_key):
        fail(
            f"{_ISSUE}: App onKey must not set view = \"people\" while a "
            "confirm / [role=\"dialog\"] is open (do not rely on the Dialog trap)"
        )
    if not (_ROLE_DIALOG.search(app_esc) or _DEFAULT_PREV.search(app_esc) or _ROLE_DIALOG.search(on_key) or _DEFAULT_PREV.search(on_key)):
        fail(
            f"{_ISSUE}: App onKey Esc skip must see [role=\"dialog\"] or "
            "defaultPrevented (Review confirmOpen is not App's URL dialog)"
        )
    keys_esc = _esc_leave_window(handle)
    if not _SET_VIEW_PEOPLE.search(keys_esc) and not _VIEW_PEOPLE_ASSIGN.search(
        keys_esc
    ):
        fail(
            f"{_ISSUE}: handleAppKey Esc with no dialog still setView(\"people\") "
            "(#132)"
        )
    if not (
        _ROLE_DIALOG.search(keys_esc)
        or _DEFAULT_PREV.search(keys_esc)
        or _DIALOG_SKIP.search(keys_esc)
    ):
        fail(
            f"{_ISSUE}: handleAppKey Esc must skip setView(\"people\") while "
            "[role=\"dialog\"] / defaultPrevented (stay on Review; Dialog dismisses)"
        )
    # Do not run confirmRun on Esc. Cancel path / trap closes; App must not go().
    if _CONFIRM_RUN.search(app_esc) or _REVIEW_ACCEPT_IPC.search(app_esc):
        fail(
            f"{_ISSUE}: Esc on the Accept confirm must not merge "
            "(do not run confirmRun / reviewAccept)"
        )
    if _CONFIRM_RUN.search(keys_esc) or _REVIEW_ACCEPT_IPC.search(keys_esc):
        fail(
            f"{_ISSUE}: handleAppKey Esc must not run confirmRun / reviewAccept"
        )
    if _KEY_ESC.search(handler) and _STOP_PROP.search(
        "\n".join(_if_block(handler, m) for m in _KEY_ESC.finditer(handler))
    ):
        fail(
            f"{_ISSUE}: do not stopPropagation Esc in the Review handler "
            "(bits-ui EscapeLayer must still dismiss; App skip is the stay rule)"
        )

    # 13) keep ConfirmDialog close-before-onconfirm (#221).
    go_body = _fn(confirm, "go")
    if not go_body:
        fail(
            f"{_ISSUE}: keep ConfirmDialog go() "
            "(close before await onconfirm(); #221)"
        )
    await_m = _AWAIT_ONCONFIRM.search(go_body)
    close_m = _OPEN_FALSE.search(go_body)
    if await_m and (not close_m or close_m.start() > await_m.start()):
        fail(
            f"{_ISSUE}: ConfirmDialog go() still sets open = false before "
            "await onconfirm() (#221; Esc cancel does not merge)"
        )
    cancel_body = _fn(confirm, "cancel")
    if cancel_body and _CONFIRM_RUN.search(cancel_body):
        fail(f"{_ISSUE}: ConfirmDialog cancel must not run confirmRun")
    if not re.search(r"""role\s*=\s*["']dialog["']""", confirm_raw) and "Dialog.Content" not in confirm_raw:
        fail(f"{_ISSUE}: keep bits-ui Dialog (role=dialog) — App skip queries it")

    # 14) keep Search #q + onHitsKey j/k (#132 / #318).
    hits_key = _fn(search, "onHitsKey")
    if not search_path.is_file():
        fail(f"{_ISSUE}: keep SearchPane.svelte (#q / onHitsKey unchanged)")
    if not _SEARCH_Q_ID.search(search_m) and not _SEARCH_Q_ID.search(search):
        fail(f"{_ISSUE}: keep Search #q id=\"q\" (never intercepted)")
    if not hits_key:
        fail(f"{_ISSUE}: keep SearchPane onHitsKey (j/k / arrows / Enter)")
    if not _KEY_J.search(hits_key) or not _KEY_K.search(hits_key):
        fail(f"{_ISSUE}: Search hit j/k stay on onHitsKey (unchanged)")
    if not _KEY_ARROW_DOWN.search(hits_key) or not _KEY_ARROW_UP.search(hits_key):
        fail(f"{_ISSUE}: Search hit arrows stay on onHitsKey (stop at ends)")
    if not _INPUT_TAG_GUARD.search(hits_key):
        fail(
            f"{_ISSUE}: onHitsKey still returns on INPUT so #q types j/k/Space"
        )
    if _ONHITS.search(review):
        fail(f"{_ISSUE}: Review keys do not live in SearchPane / onHitsKey")
    if _OPEN_ROW.search(search) or _KEY_A.search(hits_key):
        fail(f"{_ISSUE}: do not put Review a/openRow on Search hits")

    # 15) keep #316 People Space; Review does not bind it (checked above).
    space_tail = tail
    if not _KEY_SPACE.search(handle) and not _KEY_SPACE.search(space_tail):
        fail(f"{_ISSUE}: keep People Space voice after the people-only return (#316)")
    if _KEY_SPACE.search(prefix):
        fail(f"{_ISSUE}: People Space stays after view !== \"people\" return (#316)")

    # 16) keep I2 / no bulk / no auto-accept (chrome only; do not open identity.rs).
    can_body = _fn(review, "canAccept")
    if not can_body or not _CAN_ACCEPT_NWAY.search(can_body):
        fail(
            f"{_ISSUE}: keep canAccept N-way (≥2 checked) — I2 unchanged; "
            "no bulk / auto-accept"
        )
    if _BULK.search(handler) or _BULK.search(handler_x) or _BULK.search(accept_body):
        fail(
            f"{_ISSUE}: a does not walk the queue / accept all rows "
            "(no bulk accept; no auto-accept)"
        )
    if _AUTO_MERGE.search(handler) or _AUTO_MERGE.search(markup):
        fail(f"{_ISSUE}: no auto-merge / name_score UI (I2 name-only queue)")
    if _RAW_ID.search(markup):
        fail(f"{_ISSUE}: queue/detail still must not show raw person ids (#221)")
    if _REVIEW_ACCEPT_IPC.search(handler) and not _ASK_CALL.search(accept_body):
        fail(f"{_ISSUE}: a still goes through confirm + canAccept (I2)")

    # 17) keep #374 To line, #213 inspector, #318 query (already #q above).
    if rows_path.is_file() and not _MAIL_TO.search(rows_raw):
        fail(f"{_ISSUE}: keep mail bubble data-mail-to (#374)")
    if insp_path.is_file() and not _INSPECTOR.search(insp_raw):
        fail(f"{_ISSUE}: keep data-person-inspector (#213)")

    # 18) reduced motion — no bounce; scroll nearest is not smooth.
    if _SMOOTH.search(handler) or _SMOOTH.search(handler_x):
        fail(
            f"{_ISSUE}: do not copy Search behavior:\"smooth\" "
            "(reduced motion: scroll nearest, no bounce)"
        )
    if _BOUNCE.search(markup) or _TRANSITION.search(each):
        fail(f"{_ISSUE}: no bounce / new transition on the Review queue")

    # 19) locales — no new pack required; if a new t() key appears, both packs.
    en = _chrome_pack_entries(_text(en_path)) if en_path.is_file() else {}
    tr = _chrome_pack_entries(_text(tr_path)) if tr_path.is_file() else {}
    used = set(_T_CALL.findall(review_raw))
    missing_en = sorted(k for k in used if k not in en)
    missing_tr = sorted(k for k in used if k not in tr)
    if missing_en or missing_tr:
        bits = []
        if missing_en:
            bits.append("missing en: " + ", ".join(missing_en))
        if missing_tr:
            bits.append("missing tr: " + ", ".join(missing_tr))
        fail(
            f"{_ISSUE}: same ChromeKey on en.ts + tr.ts if new strings — "
            + "; ".join(bits)
        )
    for key in used:
        if not en.get(key) or not tr.get(key):
            continue
        if en[key].strip() == tr[key].strip() and key not in {
            "review",
            "accept",
            "reject",
        }:
            # Existing identical shorts (Accept) are chrome labels; skip those
            # already shared. New keyboard copy must not be an English clone.
            if key not in {
                "loadingReviewQueue",
            } and len(en[key]) > 12 and en[key] == tr[key]:
                fail(f"{_ISSUE}: tr {key} is not an English copy")
    for pack in (en, tr):
        for val in pack.values():
            if _PLACEHOLDER_CHROME.search(val):
                fail(
                    f"{_ISSUE}: locale packs stay chrome only — no Ada / Berk / "
                    "Self in t() values"
                )

    # 20) no http(s) / send on this keyboard surface.
    if _HTTP.search(handler) or re.search(r"\b(?:fetch|axios|XMLHttpRequest)\b", handler):
        fail(f"{_ISSUE}: Review keys are local — no http(s)")

    # 21) D24 — docs/user/app.md Review keyboard map.
    if not docs.strip():
        fail(
            f"{_ISSUE}: docs/user/app.md required — Review j/k / a / r / Enter; "
            "Esc confirm vs leave"
        )
    if not _DOCS_REVIEW_JK.search(docs):
        fail(
            f"{_ISSUE}: docs/user/app.md must say Review j/k (or arrows) move "
            "the open card"
        )
    if not _DOCS_AR.search(docs):
        fail(
            f"{_ISSUE}: docs/user/app.md must say a/r open existing "
            "Accept/Reject confirms"
        )
    if not _DOCS_ENTER.search(docs):
        fail(
            f"{_ISSUE}: docs/user/app.md must say Enter opens detail if it is "
            "not open"
        )
    if not _DOCS_ESC_CONFIRM.search(docs):
        fail(
            f"{_ISSUE}: docs/user/app.md must say Esc dismisses the Review "
            "confirm and stays on Review"
        )
    if not _DOCS_ESC_LEAVE.search(docs):
        fail(
            f"{_ISSUE}: docs/user/app.md must keep Esc with no dialog back to "
            "People from Review"
        )
    if not _DOCS_Q.search(docs):
        fail(f"{_ISSUE}: keep docs: typing in Search #q is never intercepted")
    if not _DOCS_PEOPLE_JK.search(docs):
        fail(f"{_ISSUE}: keep docs: People j/k still move messages")
    if not _DOCS_CHECKBOX.search(docs):
        fail(
            f"{_ISSUE}: docs/user/app.md must say a focused checkbox still uses "
            "Space"
        )
    if not _DOCS_FIRST.search(docs):
        fail(
            f"{_ISSUE}: docs/user/app.md must cover first card open / k then j "
            "without a mouse"
        )
