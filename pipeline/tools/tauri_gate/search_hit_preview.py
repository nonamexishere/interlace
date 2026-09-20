"""#371 — Search hit preview with body and attachments.

Confirmed mix (2026-09-20): right `data-search-preview` beside
`data-search-hits`. Query/filters above. Click + j/k select/preview; not
jump. Enter + `person_id` still #124 jump. No `person_id` never jumps.
Space does not jump / does not Search-play. `#q` still types a space.
Always `api.searchBody` on highlight + gen. `displayBody` text. Mail
`splitQuotedBody` + `data-show-quoted` collapsed. List snippet; one
`CasAttach` in preview still mounted from `SearchHits.svelte`. Empty
preview: quiet `t()` + focus `#q`. #270: do not clear `hits`/`hitIndex`
before `api.search`. No `{#key}` People. No second timeline.

Must-IDs: union of 371-a/b/c research as they match this mix.
Placeholders Ada / Berk. Additive chrome only.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.find_in_conversation import _FIND_HOOK
from tauri_gate.import_boot_guards import _input_guard_span
from tauri_gate.last_read import _LAST_KEY_RX, _REMOUNT, _text, _web_file
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.media_linkify_lib import _hook_element_blocks
from tauri_gate.scan import (
    _expand_fn_calls,
    _function_body,
    _match_closer,
    _search_pane_blob,
    _svelte_markup,
    _ts_fn_body,
    _web_logic,
    _without_comments,
)
from tauri_gate.search_field_keys import (
    _API_SEARCH_CALL,
    _SEARCH_PRE_IPC_BODY,
    _SEARCH_PRE_IPC_EXPANDED,
    _SEARCH_PRE_IPC_HITINDEX,
    _SEARCH_PRE_IPC_HITS_CLEAR,
    _run_before_ipc,
)
from tauri_gate.search_hits_jump import (
    _SEARCH_HTML_MAIL,
    _SEARCH_MARK_TAG,
    _SEARCH_REGEX_HTML_MARK,
    _SEARCH_UNSAFE_HTML,
    _VIEW_PEOPLE,
    _hits_each_block,
)
from tauri_gate.search_picker_lib import _SEARCH_FILTERS_HOOK, _SEARCH_Q_ID
from tauri_gate.space_voice_note import _ROW_AUDIO
from tauri_gate.status_toasts_chrome import _FOCUS_SEARCH_Q
from tauri_gate.status_toasts_toast import _svelte_effect_args

_ISSUE = "#371"

_PREVIEW_HOOK = re.compile(r"\bdata-search-preview\b")
_PREVIEW_EMPTY_HOOK = re.compile(r"\bdata-search-preview-empty\b")
_HITS_HOOK = re.compile(r"\bdata-search-hits\b")
_HIT_HOOK = re.compile(r"\bdata-search-hit\b")
_INSPECTOR = re.compile(r"\bdata-person-inspector\b")
_BORDER_L = re.compile(r"\bborder-l\b")
_W72 = re.compile(r"\bw-72\b")
_WIDER = re.compile(
    r"\b(?:w-80|w-96|w-\[|min-w-|min-w\[|flex-1|basis-)\b"
)
_ROOT_FLEX = re.compile(r"\bflex\b")
_MIN_H0 = re.compile(r"\bmin-h-0\b")
_FLEX_1 = re.compile(r"\bflex-1\b")
_FLEX_COL = re.compile(r"\bflex-col\b")
_FLEX_ROW = re.compile(r"\bflex-row\b")
_JUMP = re.compile(
    r"\b(?:onJumpToMessage|jumpToMessage|openPersonAtMessage|selectPerson|"
    r"persistLastPerson|persistLastRead|activateHit)\s*\("
)
_JUMP_OR_VIEW = re.compile(
    r"\b(?:onJumpToMessage|jumpToMessage|openPersonAtMessage|selectPerson|"
    r"persistLastPerson|persistLastRead|activateHit)\s*\("
    r"|view\s*=\s*[\"']people[\"']"
)
_SEARCH_BODY = re.compile(r"\b(?:api\.)?searchBody\s*\(")
_GEN_NAME = re.compile(
    r"\b(?:previewGen|bodyGen|searchBodyGen|previewToken|previewSeq)\b"
)
_STALE_GUARD = re.compile(
    r"if\s*\(\s*(?:gen|id|mid|got|want|previewGen|bodyGen|searchBodyGen|"
    r"previewMessageId|previewId|messageId|message_id)\b[^)]{0,80}"
    r"(?:!==?|===?)"
)
_PREVIEW_STATE = re.compile(
    r"\b(?:previewBody|previewMessageId|previewHit|previewText|"
    r"previewId|previewSrc|selectedPreview)\b"
)
_DISPLAY_BODY = re.compile(r"\bdisplayBody\s*\(")
_SPLIT_QUOTED = re.compile(r"\bsplitQuotedBody\s*\(")
_IS_MAIL = re.compile(r"\bisMailRow\s*\(")
_SHOW_QUOTED = re.compile(r"\bdata-show-quoted\b")
_QUOTED_MAP = re.compile(
    r"\b(?:quotedOpen|previewQuoted|showQuoted)\b"
)
_HUMAN_TIME = re.compile(r"\b(?:humanTime|utcTime)\s*\(")
_SUBJECT = re.compile(r"(?:h|hit|previewHit|selected)\s*\.\s*subject\b")
_CAS = re.compile(r"<CasAttach\b")
_CAS_NAME = re.compile(r"\bCasAttach\b")
_KEY_MSG = re.compile(
    r"\{#key\s+[^}]*\b(?:message_id|messageId|previewMessageId|previewId)\b"
)
_LINKIFY = re.compile(r"\bLinkifyBody\b")
_HTML_MAIL_FIELD = re.compile(r"\bbody_html\b")
_AT_HTML = re.compile(r"\{@html\b")
_INNER_HTML = re.compile(r"\.innerHTML\s*=")
_SMOOTH = re.compile(r"""behavior\s*:\s*["']smooth["']""")
_BOUNCE = re.compile(r"\b(?:bounce|spring|elastic)\b", re.I)
_VIRTUALIZE = re.compile(r"\bVIRTUALIZE_AFTER\b")
_EST = re.compile(r"\bESTIMATED_ROW_HEIGHT\b")
_TL_INDEX = re.compile(r"\bdata-tl-index\b|#person-timeline")
_LAST_TIME = re.compile(r"""t\(\s*["']lastTime["']\s*\)""")
_LOAD_OLDER = re.compile(r"\b(?:prependOlder|loadOlder|data-load-older)\b")
_MULTI = re.compile(r"\b(?:selectedIds|copyN|extendSelection)\b")
_TYPE_A_QUERY = re.compile(r"typeAQuery|Type a query")
_SKELETON = re.compile(r"<Skeleton\b")
_EMPTY_STATE = re.compile(r"<EmptyState\b")
_T_CALL = re.compile(r"""\bt\s*\(\s*["']([A-Za-z_][A-Za-z0-9_]*)["']\s*\)""")
_T_TYPE_A = re.compile(r"""\bt\s*\(\s*["']typeAQuery["']\s*\)""")
_KEY_ENTER = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']Enter[\"']"
    r"|[\"']Enter[\"']\s*===?\s*(?:e\.)?key"
)
_KEY_SPACE = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"'] [\"']"
    r"|[\"'] [\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?code\s*===?\s*[\"']Space(?:bar)?[\"']"
)
_ENTER_OR_SPACE = re.compile(
    r"(?:e\.)?(?:key|code)\s*===?\s*[\"']Enter[\"']\s*\|\|"
    r"\s*(?:e\.)?(?:key|code)\s*===?\s*[\"'](?: |Space(?:bar)?)[\"']"
    r"|(?:e\.)?(?:key|code)\s*===?\s*[\"'](?: |Space(?:bar)?)[\"']\s*\|\|"
    r"\s*(?:e\.)?(?:key|code)\s*===?\s*[\"']Enter[\"']"
)
_KEY_J = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']j[\"']|[\"']j[\"']\s*===?\s*(?:e\.)?key"
    r"|ArrowDown"
)
_KEY_K = re.compile(
    r"(?:e\.)?key\s*===?\s*[\"']k[\"']|[\"']k[\"']\s*===?\s*(?:e\.)?key"
    r"|ArrowUp"
)
_ACTIVATE = re.compile(r"\bactivateHit\s*\(")
_SENT_AT_PAYLOAD = re.compile(r"sentAt\s*:\s*(?:h\.)?sent_at\b")
_PERSON_GUARD = re.compile(
    r"(?:h|hit)\s*\.\s*(?:person_id|personId)\s*!=\s*null"
    r"|(?:h|hit)\s*\.\s*(?:person_id|personId)\s*!==?\s*(?:null|undefined)"
    r"|if\s*\(\s*(?:h|hit)\s*\.\s*(?:person_id|personId)\s*\)"
)
_TOGGLE_EXPAND = re.compile(
    r"expanded\s*===\s*(?:h\.)?message_id"
    r"|\{#if\s+expanded\b"
)
_LIST_BODY = re.compile(r"\{body\}")
_VOICE_PLAY = re.compile(
    r"\b(?:togglePlay|toggleVoice)\s*\("
    r"|data-voice-note[\s\S]{0,80}\.play\s*\("
    r"|\[data-voice-note\][\s\S]{0,80}\.play\s*\("
)
_HTTP_SRC = re.compile(r"""src\s*=\s*["']https?://""", re.I)
_AUTOPLAY = re.compile(r"\bautoplay\b", re.I)
_REVEAL_MENU = re.compile(r"\bdata-reveal-menu\b")
_CONFIRM = re.compile(r"\bConfirmDialog\b")
_OPEN_CAS = re.compile(r"\bopenCas\s*\(|\bopen_cas\b")
_TICK = re.compile(r"\b(?:await\s+)?tick\s*\(")
_OPEN_AT = re.compile(r"\bopenPersonAtMessage\s*\(")
_INCLUDE_GROUPS = re.compile(r"\bincludeGroups\s*=")
_COPY_TEXT = re.compile(r"""t\(\s*["']copyText["']\s*\)""")
_CHROME_SEARCH = re.compile(r"\bdata-chrome-search\b")
_SPLIT_SNIPPET = re.compile(r"\bsplitSnippet\b")
_SEARCH_HIT_TYPE = re.compile(r"export\s+type\s+SearchHit\s*=\s*\{")
_NEW_INVOKE = re.compile(
    r"""invoke\s*(?:<[^>]*>)?\s*\(\s*["'](?!search_cmd|search_body|labels_list)"""
)
_DOCS_PREVIEW = re.compile(
    r"(?:search|hit).{0,80}preview|preview.{0,80}(?:hit|body|attachment|photo)",
    re.I | re.S,
)
_DOCS_CLICK = re.compile(
    r"(?:click|selecting|highlight).{0,100}(?:preview|selects)"
    r"|(?:preview).{0,100}(?:click|j/k|highlight|select)",
    re.I | re.S,
)
_DOCS_ENTER = re.compile(
    r"Enter.{0,140}(?:People|timeline|Ada|jumps?|opens?)",
    re.I | re.S,
)
_DOCS_NO_PERSON = re.compile(
    r"(?:no person_id|without a (?:linked )?person|not linked).{0,200}"
    r"(?:preview|does not jump|never jumps?|stay(?:s)? on Search)"
    r"|(?:preview).{0,200}(?:no person_id|does not jump|never jumps?)",
    re.I | re.S,
)
_DOCS_CLICK_JUMPS = re.compile(
    r"Enter or click opens a hit that has a linked person on the \*\*People\*\* timeline",
    re.I,
)
_HITINDEX_SET = re.compile(r"\bhitIndex\s*=")
_ONCLICK = re.compile(r"(?:onclick|on:click)(?:\|\w+)*\s*=\s*\{")
_INPUT_TAG = re.compile(r"tagName\s*===?\s*[\"']INPUT[\"']")
_FILTERS_CLOSEST = re.compile(r"closest\s*\(\s*[\"']\[data-search-filters\][\"']")


def _fn(src: str, name: str) -> str:
    return _ts_fn_body(src, name) or _function_body(src, name) or ""


def _prop_assign(src: str, name: str) -> str:
    m = re.search(rf"\b{name}\s*=\s*\{{", src)
    if not m:
        return ""
    brace = src.find("{", m.start())
    if brace < 0:
        return ""
    end = _match_closer(src, brace)
    if end < 0:
        return src[brace + 1 : brace + 800]
    return src[brace + 1 : end]


def _onclick_bodies(markup: str) -> str:
    parts: list[str] = []
    for m in _ONCLICK.finditer(markup):
        brace = markup.find("{", m.start())
        if brace < 0:
            continue
        end = _match_closer(markup, brace)
        if end < 0:
            parts.append(markup[brace : brace + 400])
        else:
            parts.append(markup[brace : end + 1])
    return "\n".join(parts)


def _click_path(pane: str, hits_each: str) -> str:
    click = _onclick_bodies(hits_each)
    prop = _prop_assign(pane, "onActivate")
    blob = click + "\n" + prop
    return _expand_fn_calls(pane, blob)


def _space_branch(hits_key: str) -> str:
    """onHitsKey slice that handles Space (not the Enter-only arm)."""
    parts: list[str] = []
    for m in _KEY_SPACE.finditer(hits_key):
        start = hits_key.rfind("if", 0, m.start())
        if start < 0:
            start = max(0, m.start() - 80)
        brace = hits_key.find("{", m.start())
        if brace < 0:
            parts.append(hits_key[start : m.end() + 240])
            continue
        end = _match_closer(hits_key, brace)
        parts.append(hits_key[start : end if end > brace else brace + 400])
    return "\n".join(parts)


def _enter_branch(hits_key: str) -> str:
    parts: list[str] = []
    for m in _KEY_ENTER.finditer(hits_key):
        start = hits_key.rfind("if", 0, m.start())
        if start < 0:
            start = max(0, m.start() - 80)
        brace = hits_key.find("{", m.start())
        if brace < 0:
            parts.append(hits_key[start : m.end() + 240])
            continue
        end = _match_closer(hits_key, brace)
        parts.append(hits_key[start : end if end > brace else brace + 400])
    return "\n".join(parts)


def _preview_blocks(markup: str) -> str:
    blocks = _hook_element_blocks(markup, "data-search-preview")
    return "\n".join(blocks)


def _empty_blocks(markup: str) -> str:
    blocks = _hook_element_blocks(markup, "data-search-preview-empty")
    return "\n".join(blocks)


def _imported_svelte(src_path: Path) -> list[Path]:
    if not src_path.is_file():
        return []
    text = src_path.read_text()
    out: list[Path] = []
    seen: set[Path] = set()
    for m in re.finditer(r"""from\s+["'](\.[^"']+)["']""", text):
        base = (src_path.parent / m.group(1)).resolve()
        candidates = [base]
        if not base.suffix:
            candidates.append(Path(str(base) + ".svelte"))
        for c in candidates:
            if c.suffix == ".svelte" and c.is_file() and c not in seen:
                seen.add(c)
                out.append(c)
    return out


def _search_hit_type_body(api: str) -> str:
    m = _SEARCH_HIT_TYPE.search(api)
    if not m:
        return ""
    brace = api.find("{", m.start())
    if brace < 0:
        return ""
    end = _match_closer(api, brace)
    if end < 0:
        return api[brace : brace + 800]
    return api[brace : end + 1]


def _highlight_search_body(pane: str) -> bool:
    """True when searchBody runs on highlight, not only no-person toggle."""
    toggle = _fn(pane, "toggle")
    activate = _fn(pane, "activateHit")
    hits_key = _fn(pane, "onHitsKey")
    named = ""
    for name in (
        "selectHit",
        "loadPreview",
        "previewHit",
        "fillPreview",
        "showPreview",
        "onSelectHit",
        "previewSelected",
    ):
        named += "\n" + _fn(pane, name)
    effects = "\n".join(_svelte_effect_args(pane))
    others = named + "\n" + hits_key + "\n" + effects
    if _SEARCH_BODY.search(others):
        return True
    # searchBody in pane but not only inside toggle / activateHit.
    if not _SEARCH_BODY.search(pane):
        return False
    rest = pane
    if toggle:
        rest = rest.replace(toggle, " ", 1)
    if activate:
        rest = rest.replace(activate, " ", 1)
    return bool(_SEARCH_BODY.search(rest))


def _stale_guarded(pane: str) -> bool:
    if _GEN_NAME.search(pane):
        return True
    for m in _SEARCH_BODY.finditer(pane):
        around = pane[m.start() : m.end() + 500]
        if _STALE_GUARD.search(around) or _GEN_NAME.search(around):
            return True
        if re.search(
            r"if\s*\(\s*(?:id|mid|messageId|message_id|previewMessageId)"
            r"[^)]{0,60}(?:!==?|===?)",
            around,
        ):
            return True
    return False


def assert_search_hit_preview(crate: Path) -> None:
    """#371: selecting a Search hit fills a Search preview; Enter still jumps."""
    pane_path = crate / "web" / "lib" / "SearchPane.svelte"
    hits_path = crate / "web" / "lib" / "SearchHits.svelte"
    app_path = crate / "web" / "App.svelte"
    api_path = crate / "web" / "lib" / "api.ts"
    if not pane_path.is_file():
        fail(f"{_ISSUE}: SearchPane.svelte required (hit preview lives on Search)")
    if not hits_path.is_file():
        fail(
            f"{_ISSUE}: SearchHits.svelte required "
            "(data-search-preview beside the list)"
        )

    pane = pane_path.read_text()
    hits = hits_path.read_text()
    app = _text(app_path)
    api = _text(api_path)
    pane_c = _without_comments(pane)
    hits_c = _without_comments(hits)
    app_c = _without_comments(app)
    blob = _search_pane_blob(crate)
    markup = _svelte_markup(blob)
    pane_m = _svelte_markup(pane)
    hits_m = _svelte_markup(hits)
    hits_each = _hits_each_block(hits_m) or _hits_each_block(hits)
    children = _imported_svelte(hits_path)
    child_txt = "\n".join(p.read_text() for p in children)
    child_m = _svelte_markup(child_txt) if child_txt else ""
    surface = markup + "\n" + child_m
    preview = _preview_blocks(surface) or _preview_blocks(blob + "\n" + child_txt)
    empty = _empty_blocks(surface)
    hits_key = _fn(pane, "onHitsKey")
    activate = _fn(pane, "activateHit")
    run_body = _fn(pane, "run")
    idle = _fn(pane, "clearHitsIdle")
    click = _click_path(pane, hits_each)
    logic = pane_c + "\n" + hits_c + "\n" + child_txt

    docs_app = repo_root() / "docs" / "user" / "app.md"
    docs_search = repo_root() / "docs" / "user" / "search.md"
    dtxt = _text(docs_app) + "\n" + _text(docs_search)

    en_p = crate / "web" / "lib" / "locales" / "en.ts"
    tr_p = crate / "web" / "lib" / "locales" / "tr.ts"
    en = _chrome_pack_entries(_text(en_p)) if en_p.is_file() else {}
    tr = _chrome_pack_entries(_text(tr_p)) if tr_p.is_file() else {}

    # 1) preview-site — primary red today: no preview pane.
    if not _PREVIEW_HOOK.search(surface) and not _PREVIEW_HOOK.search(blob):
        fail(
            f"{_ISSUE}: Search must show a hit preview beside the list "
            "(data-search-preview)"
        )
    if _PREVIEW_HOOK.search(_text(_web_file(crate, "PeopleInspector.svelte"))):
        fail(
            f"{_ISSUE}: preview is Search chrome, not PeopleInspector "
            "(data-search-preview must not live on data-person-inspector)"
        )
    if _PREVIEW_HOOK.search(_text(_web_file(crate, "TimelinePane.svelte"))):
        fail(
            f"{_ISSUE}: preview is Search chrome, not TimelinePane "
            "(not a second timeline)"
        )
    if _INSPECTOR.search(preview):
        fail(f"{_ISSUE}: data-search-preview is not PeopleInspector")
    if not _HITS_HOOK.search(surface):
        fail(f"{_ISSUE}: keep data-search-hits on the hit list")
    if not _HIT_HOOK.search(hits_each):
        fail(f"{_ISSUE}: keep data-search-hit on each hit row")

    # Query + filters full width above the split; root flex min-h-0 flex-1 flex-col.
    if not _SEARCH_Q_ID.search(pane_m) and not _SEARCH_Q_ID.search(pane):
        fail(f"{_ISSUE}: keep #q above the hit list / preview split")
    q_at = pane_m.find('id="q"') if 'id="q"' in pane_m else pane_m.find("id={'q'}")
    prev_at = surface.find("data-search-preview")
    hits_at = surface.find("data-search-hits")
    if q_at >= 0 and prev_at >= 0 and q_at > prev_at and "data-search-preview" in pane_m:
        fail(f"{_ISSUE}: query + filters stay full width above the preview split")
    if _SEARCH_FILTERS_HOOK not in pane_m and _SEARCH_FILTERS_HOOK not in pane:
        fail(f"{_ISSUE}: keep data-search-filters above the split (#209)")
    if _SEARCH_Q_ID.search(preview) or _SEARCH_FILTERS_HOOK in preview:
        fail(f"{_ISSUE}: #q / filters stay above the split, not inside the preview")
    if not (_ROOT_FLEX.search(pane_m) and _MIN_H0.search(pane_m) and _FLEX_1.search(pane_m)):
        fail(
            f"{_ISSUE}: SearchPane root is flex min-h-0 flex-1 flex-col "
            "so the beside split stays on-screen"
        )
    if not _FLEX_COL.search(pane_m):
        fail(
            f"{_ISSUE}: SearchPane root is flex min-h-0 flex-1 flex-col "
            "(query above; list | preview below)"
        )
    # Beside, not stacked under the ol.
    split_src = pane_m + "\n" + hits_m
    if hits_at >= 0 and prev_at >= 0:
        lo, hi = sorted((hits_at, prev_at))
        between = surface[lo: hi + 80]
        # A below-the-list pane sits after </ol> in a column with no row flex.
        stacked = bool(re.search(r"</ol>", between, re.I)) and not (
            _FLEX_ROW.search(between)
            or re.search(r"""class\s*=\s*["'][^"']*\bflex\b(?![^"']*flex-col)""", between)
        )
        parent_flex_row = _FLEX_ROW.search(split_src) or re.search(
            r"""class\s*=\s*["'][^"']*\bflex\b[^"']*\bmin-h-0""",
            split_src,
        )
        if stacked and not parent_flex_row:
            fail(
                f"{_ISSUE}: preview is beside the hit list "
                "(flex row: data-search-hits | data-search-preview), not stacked under the ol"
            )
    if preview:
        if not _BORDER_L.search(preview):
            fail(
                f"{_ISSUE}: data-search-preview uses border-l "
                "(right pane beside the list, not a stacked card)"
            )
        if _W72.search(preview) and not _WIDER.search(preview):
            fail(
                f"{_ISSUE}: preview is wider than inspector w-72 "
                "(a max-h-64 photo must fit — not PeopleInspector)"
            )
        if not _WIDER.search(preview) and not _W72.search(preview):
            fail(
                f"{_ISSUE}: preview is wider than inspector w-72 "
                "(w-80 / w-96 / min-w- / flex-1 so a max-h-64 photo fits)"
            )

    # 2) preview-select / preview-click-not-jump — click still jumps today.
    if _JUMP_OR_VIEW.search(click):
        fail(
            f"{_ISSUE}: click selects a hit for preview — it must not jump "
            "(no onJumpToMessage / activateHit / selectPerson / view = \"people\")"
        )
    if not _HITINDEX_SET.search(click) and not _HITINDEX_SET.search(
        _prop_assign(pane, "onActivate")
    ):
        # bind:hitIndex on the row is also fine if click only sets via bind.
        if "bind:hitIndex" not in hits and not re.search(
            r"hitIndex\s*=\s*i\b", pane_c
        ):
            fail(f"{_ISSUE}: click must set hitIndex (select) without jumping")

    # 3) preview-jk / jk-not-open-person — j/k select + fill preview, never jump.
    if not hits_key:
        fail(f"{_ISSUE}: keep onHitsKey — j/k select for preview; Enter jumps")
    if not _KEY_J.search(hits_key):
        fail(f"{_ISSUE}: onHitsKey must still handle j / ArrowDown (select, not jump)")
    if not _KEY_K.search(hits_key):
        fail(f"{_ISSUE}: onHitsKey must still handle k / ArrowUp (select, not jump)")
    jk = hits_key
    # Strip the Enter arm so a shared activateHit on Enter does not poison j/k.
    enter_arm = _enter_branch(hits_key)
    space_arm = _space_branch(hits_key)
    jk_only = jk
    if enter_arm:
        jk_only = jk_only.replace(enter_arm, " ")
    if space_arm:
        jk_only = jk_only.replace(space_arm, " ")
    if _JUMP.search(jk_only) or _VIEW_PEOPLE.search(jk_only):
        fail(
            f"{_ISSUE}: j/k / arrows must not call onJumpToMessage / activateHit / "
            "selectPerson / openPersonAtMessage — they select for preview"
        )
    if not _highlight_search_body(pane):
        fail(
            f"{_ISSUE}: highlighting a hit (click / j/k) must call api.searchBody "
            "(not only no-person toggle after activateHit)"
        )

    # 4) preview-space / space-not-jump — Space shares Enter → activateHit today.
    if _ENTER_OR_SPACE.search(hits_key) and _ACTIVATE.search(hits_key):
        fail(
            f"{_ISSUE}: Space must not share Enter → activateHit "
            "(Space does not jump; #q still types a space)"
        )
    if _JUMP_OR_VIEW.search(space_arm):
        fail(
            f"{_ISSUE}: Space selects / previews — it must not jump "
            "(no activateHit / onJumpToMessage)"
        )
    if _VOICE_PLAY.search(hits_key) or _VOICE_PLAY.search(space_arm):
        fail(
            f"{_ISSUE}: Space does not Search-play — #316 stays People "
            "(#person-timeline [data-voice-note])"
        )
    guard = _input_guard_span(hits_key)
    if not guard or not _INPUT_TAG.search(hits_key[guard[0] : guard[1]]):
        fail(
            f"{_ISSUE}: onHitsKey must still return early on INPUT "
            "so #q types a space"
        )
    if not _FILTERS_CLOSEST.search(hits_key):
        fail(
            f"{_ISSUE}: onHitsKey still skips [data-search-filters] "
            "so filter fields type a space"
        )

    # 5) preview-enter-jump / enter-still-124 / preview-keep-124.
    if not _KEY_ENTER.search(hits_key):
        fail(f"{_ISSUE}: onHitsKey Enter must still jump when person_id is set (#124)")
    if not _ACTIVATE.search(hits_key) and not re.search(
        r"\bonJumpToMessage\s*\(", _enter_branch(hits_key)
    ):
        fail(f"{_ISSUE}: onHitsKey Enter must still call activateHit (#124)")
    if not activate:
        fail(f"{_ISSUE}: keep activateHit — Enter + person_id still #124 jump")
    if not _PERSON_GUARD.search(activate) and not _PERSON_GUARD.search(pane_c):
        fail(
            f"{_ISSUE}: Enter jumps only when person_id is set — "
            "no person_id never jumps (do not invent a person)"
        )
    if not re.search(r"\bonJumpToMessage\s*\(", activate):
        fail(
            f"{_ISSUE}: Enter + person_id still onJumpToMessage "
            "(jumpToMessage → tick() → openPersonAtMessage)"
        )
    if not _SENT_AT_PAYLOAD.search(activate):
        fail(f"{_ISSUE}: keep sentAt: h.sent_at on the jump payload (#210 / #124)")
    jump = _fn(app, "jumpToMessage")
    if not jump:
        fail(f"{_ISSUE}: keep App jumpToMessage (#124)")
    if not _VIEW_PEOPLE.search(jump):
        fail(f"{_ISSUE}: Enter jump still sets view = \"people\" (#124)")
    if not _TICK.search(jump):
        fail(f"{_ISSUE}: Enter jump still await tick() before openPersonAtMessage")
    if not _OPEN_AT.search(jump):
        fail(f"{_ISSUE}: Enter jump still openPersonAtMessage (Ada's timeline)")
    if not _INCLUDE_GROUPS.search(jump):
        fail(f"{_ISSUE}: group Enter jump may still set includeGroups (#124)")
    open_at = _fn(_text(_web_file(crate, "TimelinePane.svelte")), "openPersonAtMessage")
    if open_at and not re.search(
        r"selectedIds\s*=\s*new\s+Set\s*\(\s*\[\s*messageId",
        open_at,
    ):
        fail(
            f"{_ISSUE}: Enter jump still collapses #370 selectedIds to that message_id"
        )

    # 6) preview-no-person / no-person-id-no-jump.
    no_person = activate
    # The no-person branch must not jump.
    if re.search(
        r"(?:person_id|personId)[^\n]{0,80}(?:==\s*null|===\s*null|==\s*undefined)"
        r"[\s\S]{0,240}(?:onJumpToMessage|jumpToMessage|openPersonAtMessage|"
        r"selectPerson|view\s*=\s*[\"']people[\"'])",
        no_person,
    ):
        fail(
            f"{_ISSUE}: a hit with no person_id never jumps "
            "(Enter included — preview on Search, do not invent a person)"
        )
    if not _SEARCH_BODY.search(pane_c):
        fail(
            f"{_ISSUE}: keep api.searchBody — no person_id still previews on Search "
            "(no new IPC)"
        )

    # 7) preview-body-searchBody / gen guard / no new IPC.
    if not _stale_guarded(pane):
        fail(
            f"{_ISSUE}: api.searchBody on highlight needs a generation / "
            "message_id guard (stale replies ignored)"
        )
    hit_type = _search_hit_type_body(api)
    if re.search(r"\bbody_text\b", hit_type):
        fail(
            f"{_ISSUE}: do not put body_text on the hit RPC — "
            "always api.searchBody (no new IPC)"
        )
    if "searchBody" not in api:
        fail(f"{_ISSUE}: keep api.searchBody → search_body (no new IPC)")
    if _NEW_INVOKE.search(pane_c) or _NEW_INVOKE.search(hits_c):
        fail(f"{_ISSUE}: no new invoke name — searchBody is enough")

    # 8) preview-body-display / keep-126-text-nodes.
    preview_logic = preview + "\n" + child_txt + "\n" + hits_c
    if not _DISPLAY_BODY.search(logic) and not _DISPLAY_BODY.search(preview):
        fail(
            f"{_ISSUE}: preview body is displayBody of the searchBody string "
            "(strips <attached: …>; text node, not raw {{body}})"
        )
    unsafe = preview + "\n" + child_txt + "\n" + hits_c
    if (
        _AT_HTML.search(unsafe)
        or _INNER_HTML.search(unsafe)
        or _SEARCH_UNSAFE_HTML.search(unsafe)
    ):
        fail(
            f"{_ISSUE}: preview body stays a text node "
            "(no {{@html}} / innerHTML / insertAdjacentHTML)"
        )
    if _HTML_MAIL_FIELD.search(unsafe) or _SEARCH_HTML_MAIL.search(unsafe):
        fail(f"{_ISSUE}: no HTML mail / body_html / DOMParser / srcdoc in Search preview")
    if _SEARCH_REGEX_HTML_MARK.search(unsafe):
        fail(f"{_ISSUE}: no regex HTML mark inject on the preview body")
    if _LINKIFY.search(preview) or _LINKIFY.search(child_txt):
        fail(
            f"{_ISSUE}: preview body is displayBody text "
            "(no LinkifyBody — IN: text nodes or <mark> siblings)"
        )
    if _TOGGLE_EXPAND.search(hits_each) or (
        _LIST_BODY.search(hits_each) and "expanded" in hits_each
    ):
        fail(
            f"{_ISSUE}: drop in-list toggle / muted {{body}} expand — "
            "the preview is the body surface"
        )

    # 9) preview-quoted-fold.
    if not _IS_MAIL.search(logic) and not _IS_MAIL.search(preview):
        fail(
            f"{_ISSUE}: mail hits use isMailRow + splitQuotedBody "
            "(gmail / email_thread), not a WA fold"
        )
    if not _SPLIT_QUOTED.search(logic) and not _SPLIT_QUOTED.search(preview):
        fail(
            f"{_ISSUE}: mail preview uses splitQuotedBody + data-show-quoted "
            "(Show quoted / Hide quoted, collapsed default)"
        )
    if not _SHOW_QUOTED.search(preview) and not _SHOW_QUOTED.search(hits_m + "\n" + child_m):
        fail(
            f"{_ISSUE}: mail quoted tail sits behind data-show-quoted "
            "(Show quoted / Hide quoted, same idea as the timeline)"
        )
    if not _QUOTED_MAP.search(logic) and not _QUOTED_MAP.search(preview):
        fail(
            f"{_ISSUE}: quoted-fold is a local map keyed by message_id "
            "(collapsed default — not always-unfolded)"
        )

    # 10) preview-subject-time.
    if not _SUBJECT.search(preview) and not _SUBJECT.search(hits_m + "\n" + child_m):
        fail(
            f"{_ISSUE}: preview shows h.subject when present "
            "(from the hit — not from searchBody)"
        )
    if not _HUMAN_TIME.search(preview) and not _HUMAN_TIME.search(
        hits_m + "\n" + child_m
    ):
        fail(
            f"{_ISSUE}: preview short time is humanTime / utcTime "
            "(#210 helper — not raw ISO)"
        )

    # 11) preview-attach-cas / preview-attach-list / keep-317.
    if _CAS.search(hits_each):
        fail(
            f"{_ISSUE}: hit rows stay snippet + #210 meta "
            "(no per-row CasAttach — one CasAttach in the preview)"
        )
    if not _CAS_NAME.search(hits):
        fail(
            f"{_ISSUE}: SearchHits must still mount CasAttach "
            "(#317 — Open/Reveal come free; do not add a Search-only menu)"
        )
    if not _CAS.search(preview) and not _CAS.search(hits_m + "\n" + child_m):
        fail(
            f"{_ISSUE}: selected hit's attachments mount CasAttach in the preview "
            "(in-window photo / voice / video / PDF)"
        )
    if not _KEY_MSG.search(hits_m + "\n" + child_m) and not _KEY_MSG.search(preview):
        fail(
            f"{_ISSUE}: {{#key}} the preview CasAttach on message_id "
            "(voice/video must not leak across hits — not a People {{#key}})"
        )
    if _REVEAL_MENU.search(hits) or _CONFIRM.search(hits) or _OPEN_CAS.search(hits_c):
        fail(
            f"{_ISSUE}: SearchHits must not grow a second Reveal/Open menu "
            "(CasAttach reuse is enough — #317)"
        )
    if _HTTP_SRC.search(preview) or _AUTOPLAY.search(preview):
        fail(
            f"{_ISSUE}: preview CAS stays local casDataUrl / data: "
            "(no http(s) src, no autoplay)"
        )

    # 12) preview-empty.
    if not _PREVIEW_EMPTY_HOOK.search(surface) and not _PREVIEW_EMPTY_HOOK.search(blob):
        fail(
            f"{_ISSUE}: empty preview is data-search-preview-empty "
            "(quiet t() + next action — focus #q)"
        )
    if not empty:
        empty = _empty_blocks(blob + "\n" + child_txt)
    if _SKELETON.search(empty):
        fail(
            f"{_ISSUE}: empty preview is not a skeleton "
            "(#203 skeleton stays on the list)"
        )
    if _TYPE_A_QUERY.search(empty) or _T_TYPE_A.search(empty):
        fail(
            f"{_ISSUE}: empty preview is not the list EmptyState \"Type a query\" "
            "(quiet t() + focus #q)"
        )
    if not _T_CALL.search(empty) and not _T_CALL.search(preview):
        fail(
            f"{_ISSUE}: empty preview copy is t() "
            "(same ChromeKey on en.ts + tr.ts — not a wall of chrome)"
        )
    if not _FOCUS_SEARCH_Q.search(empty) and not _FOCUS_SEARCH_Q.search(preview):
        fail(
            f"{_ISSUE}: empty preview next action focuses #q "
            "(getElementById(\"q\") / querySelector(\"#q\"))"
        )
    if _EMPTY_STATE.search(empty) and _TYPE_A_QUERY.search(empty):
        fail(
            f"{_ISSUE}: list EmptyState \"Type a query\" stays on the list, "
            "not on data-search-preview-empty"
        )

    # 13) preview-new-search / keep-270.
    pre_ipc = _run_before_ipc(run_body) if run_body else ""
    if (
        _SEARCH_PRE_IPC_HITS_CLEAR.search(pre_ipc)
        or _SEARCH_PRE_IPC_HITINDEX.search(pre_ipc)
        or _SEARCH_PRE_IPC_EXPANDED.search(pre_ipc)
        or _SEARCH_PRE_IPC_BODY.search(pre_ipc)
    ):
        fail(
            f"{_ISSUE}: run() start may null the preview surface only — "
            "do not assign hits = [] / hitIndex / expanded / body before api.search (#270)"
        )
    if not _PREVIEW_STATE.search(pane_c) and not _GEN_NAME.search(pane_c):
        fail(
            f"{_ISSUE}: dedicated preview fields (previewBody / previewMessageId / "
            "previewGen) — do not reuse body / expanded / hitIndex as the pre-IPC clear"
        )
    if pre_ipc and not (
        _PREVIEW_STATE.search(pre_ipc)
        or re.search(r"\bpreview", pre_ipc, re.I)
        or _GEN_NAME.search(pre_ipc)
    ):
        fail(
            f"{_ISSUE}: at run() start, null the preview surface only "
            "(do not wait until hits replace to blank Ada's body)"
        )
    if not _API_SEARCH_CALL.search(run_body):
        fail(f"{_ISSUE}: keep run() → api.search (#270 / #208)")
    # When gen-guarded hits apply, hitIndex = 0 and fill that preview.
    apply = run_body
    ipc_at = apply.find("api.search") if apply else -1
    post = apply[ipc_at:] if ipc_at >= 0 else apply
    if not re.search(r"\bhitIndex\s*=\s*0\b", post):
        fail(
            f"{_ISSUE}: when gen-guarded hits apply, hitIndex = 0 "
            "and fill that preview"
        )
    if idle and not (
        _PREVIEW_STATE.search(idle)
        or _SEARCH_BODY.search(idle)
        or re.search(r"\bpreview", idle, re.I)
        or re.search(r"\bhits\s*=\s*\[\s*\]", idle)
    ):
        fail(f"{_ISSUE}: empty q / idle still wipes hits and the preview")

    # 14) preview-people-live / no-key-person-timeline / highlight-not-last-read.
    select_path = click + "\n" + jk_only + "\n" + space_arm
    if re.search(r"\bselectPerson\s*\(", select_path):
        fail(
            f"{_ISSUE}: highlight never selectPerson "
            "(People must not remount on click / j/k)"
        )
    if re.search(r"\bopenPersonAtMessage\s*\(", select_path):
        fail(f"{_ISSUE}: highlight never openPersonAtMessage (Enter jump still may)")
    if re.search(r"\bpersistLast(?:Read|Person)\s*\(", select_path):
        fail(
            f"{_ISSUE}: highlight does not persistLastRead / persistLastPerson "
            "(jump may still collapse #370 on Enter)"
        )
    if _LAST_KEY_RX.search(pane_c) or _LAST_KEY_RX.search(hits_c):
        fail(
            f"{_ISSUE}: highlight / preview does not write interlace.lastRead "
            "(#369 stays People caret)"
        )
    shell_m = _svelte_markup(_text(_web_file(crate, "PeopleShell.svelte")))
    pane_tl_m = _svelte_markup(_text(_web_file(crate, "TimelinePane.svelte")))
    list_m = _svelte_markup(_text(_web_file(crate, "TimelineList.svelte")))
    app_m = _svelte_markup(app)
    if _REMOUNT.search(shell_m + "\n" + pane_tl_m + "\n" + list_m):
        fail(
            f"{_ISSUE}: no {{#key}} remount of #person-timeline / "
            "PeopleShell / TimelinePane (#369 / #370)"
        )
    if re.search(r"\{#key\b[^}]*PeopleShell|\{#key\b[^}]*person-timeline", app_m):
        fail(f"{_ISSUE}: no {{#key}} on People / #person-timeline in App.svelte")

    # 15) preview-not-second-timeline / keep-369 / keep-370 / keep-310 / keep-204.
    banned = preview + "\n" + child_txt
    if (
        _VIRTUALIZE.search(banned)
        or _EST.search(banned)
        or _TL_INDEX.search(banned)
        or _LAST_TIME.search(banned)
        or _LOAD_OLDER.search(banned)
        or _MULTI.search(banned)
    ):
        fail(
            f"{_ISSUE}: preview is not a second timeline "
            "(no virtualizer / Load older / Last time / #370 multi-select / "
            "data-tl-index / #person-timeline)"
        )
    if re.search(r"\bTimelinePane\b|\bTimelineRows\b|\bTimelineList\b", preview):
        fail(f"{_ISSUE}: do not mount TimelinePane / TimelineRows in Search preview")
    find_src = _text(_web_file(crate, "TimelinePane.svelte"))
    if not _FIND_HOOK.search(find_src) and "#tl-find" not in find_src:
        fail(f"{_ISSUE}: keep #310 #tl-find on the person timeline (not this preview)")
    copy_src = _text(_web_file(crate, "TimelineList.svelte"))
    if not _COPY_TEXT.search(copy_src) and "copyText" not in copy_src:
        fail(f"{_ISSUE}: keep #204 copyText on People (Search preview is not Copy N)")
    if _MULTI.search(pane_c) or _MULTI.search(hits_c):
        fail(f"{_ISSUE}: Search preview must not grow #370 multi-select copy")

    # 16) preview-reduced-motion.
    if _SMOOTH.search(preview) or _SMOOTH.search(child_txt):
        fail(
            f"{_ISSUE}: no behavior: \"smooth\" on the preview itself "
            "(list scrollHitIntoView may stay; preview scroller is instant)"
        )
    if _BOUNCE.search(preview) or _BOUNCE.search(child_txt):
        fail(f"{_ISSUE}: no bounce / spring on the preview (reduced motion)")

    # 17) preview-locale.
    empty_keys = _T_CALL.findall(empty + "\n" + preview)
    for k in empty_keys:
        if k == "typeAQuery" or k == "noHits":
            fail(
                f"{_ISSUE}: empty preview is not t(\"typeAQuery\") / t(\"noHits\") "
                "(those stay on the list EmptyState)"
            )
        if k not in en or k not in tr:
            fail(
                f"{_ISSUE}: t(\"{k}\") must exist on both en.ts and tr.ts "
                "(same ChromeKey — #278)"
            )
        if en.get(k) and tr.get(k) and en[k].strip() == tr[k].strip():
            fail(
                f"{_ISSUE}: tr {k} is not an English copy of en "
                f"(en={en[k]!r})"
            )
    extra_en = set(en) - set(tr)
    extra_tr = set(tr) - set(en)
    if extra_en or extra_tr:
        bits: list[str] = []
        if extra_en:
            bits.append("in en only: " + ", ".join(sorted(extra_en)))
        if extra_tr:
            bits.append("in tr only: " + ", ".join(sorted(extra_tr)))
        fail(
            f"{_ISSUE}: same ChromeKey on both en and tr packs — " + "; ".join(bits)
        )

    # 18) keep-126 / keep-210 list snippet; keep-208 #q.
    if not _SPLIT_SNIPPET.search(hits_each) and not _SPLIT_SNIPPET.search(hits_c):
        fail(f"{_ISSUE}: keep splitSnippet + <mark> on the list (#126 / #210)")
    if not _SEARCH_MARK_TAG.search(hits_each):
        fail(f"{_ISSUE}: keep <mark> text children on the snippet path (#126)")
    if not re.search(r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""", pane_m):
        fail(f"{_ISSUE}: keep id=\"q\" as the canonical query field (#208)")
    nav = _text(_web_file(crate, "PeopleNav.svelte"))
    if not _CHROME_SEARCH.search(nav) and not _CHROME_SEARCH.search(_web_logic(crate)):
        fail(f"{_ISSUE}: keep data-chrome-search (#208)")
    if re.search(r"\bapi\.search\s*\(", app):
        fail(f"{_ISSUE}: App.svelte must not call api.search — SearchPane run() stays")

    # 19) keep-316 People Space play; keep-132 Search j/k.
    keys = _text(_web_file(crate, "PeopleKeys.ts"))
    if not _KEY_SPACE.search(keys) or not _ROW_AUDIO.search(keys):
        fail(
            f"{_ISSUE}: keep #316 PeopleKeys Space on "
            "[data-tl-index=\"${{tlIndex}}\"] [data-voice-note] audio"
        )

    # 20) preview-d24.
    if not dtxt.strip():
        fail(
            f"{_ISSUE}: docs/user/app.md required — selecting a hit fills a Search "
            "preview; Enter still opens Ada's timeline; no person_id does not jump"
        )
    if _DOCS_CLICK_JUMPS.search(dtxt):
        fail(
            f"{_ISSUE}: docs must not say Enter or click opens People — "
            "click selects; Enter jumps"
        )
    if not _DOCS_PREVIEW.search(dtxt) or not _DOCS_CLICK.search(dtxt):
        fail(
            f"{_ISSUE}: docs/user/app.md must say selecting a hit fills a Search "
            "preview (full body, mail quoted-fold, in-window attachments)"
        )
    if not _DOCS_ENTER.search(dtxt):
        fail(
            f"{_ISSUE}: docs must say Enter still opens Ada's timeline on that message"
        )
    if not _DOCS_NO_PERSON.search(dtxt):
        fail(
            f"{_ISSUE}: docs must say a hit with no person_id still previews "
            "and does not jump"
        )
    if re.search(r"\bCemre\b|\bMustafa\b", dtxt):
        fail(f"{_ISSUE}: placeholders Ada / Berk only (no real names in D24)")
