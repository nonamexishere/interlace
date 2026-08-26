"""People sidebar collapse chrome assert. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    CSP,
    _CONFIG_TOML,
    _LAST_PATH_API,
    _LS_BRACKET,
    _MOD_EITHER,
    _PERSON_PANE_SKIP,
    _TMPL_TOKEN,
    _expand_fn_calls,
    _function_body,
    _match_closer,
    _matched_inner,
    _open_tag_around,
    _opening_tag,
    _rust_fn_body,
    _strip_html_comments,
    _svelte_markup,
    _tauri_rust_blob,
    _template_stack,
    _ts_fn_body,
    _web_logic,
    _web_sources,
    _without_comments,
)

from tauri_gate.a11y import _people_each_block

from tauri_gate.import_boot import (
    _app_keydown_body,
    _input_guard_span,
    _ls_pref_keys,
)

from tauri_gate.media_linkify import _OVERFLOW_X_HIDDEN

from tauri_gate.people_list import (
    _PEOPLE_ID_FALLBACK,
    _PEOPLE_ID_VISIBLE,
)

from tauri_gate.people_switcher_label import _strip_tag_attrs

from tauri_gate.status_toasts import (
    _has_mod_combo,
    _people_sidebar_regions,
    _split_people_only,
    _toml_keys_in_fn,
    _windows_around,
)




# #212 — collapsible people sidebar (fixed width, rail, ⌘\, local persist).
_MINMAX_PEOPLE_TRACK = re.compile(
    r"minmax\s*\(\s*0\s*,\s*(?:18|16)rem\s*\)",
    re.I,
)
_FIXED_PEOPLE_WIDTH = re.compile(
    r"("
    r"(?<![\w-])w-(?:72|64)\b"
    r"|(?<![\w-])w-\[[\"']?(?:18|16)rem[\"']?\]"
    r"|width\s*:\s*(?:18|16)rem"
    r"|grid-cols-\[[^\]]*?(?:18|16)rem"
    r"|grid-template-columns\s*:\s*(?:18|16)rem"
    r")",
    re.I,
)
_RAIL_WIDTH = re.compile(
    r"(?<![\w-])w-(?:12|14|16)\b|(?<![\w-])w-\[[\"']?(?:3(?:\.5)?|4)rem[\"']?\]",
    re.I,
)
_RAIL_ICON = re.compile(
    r"("
    r"@lucide/svelte/icons/(?:user|users|user-round|circle-user)"
    r"|<(?:User|Users|UserRound|CircleUser)\b"
    r"|(?:display_name|displayName|\.name)\s*(?:\?\.|\.)\s*"
    r"(?:charAt\s*\(\s*0\s*\)|slice\s*\(\s*0\s*,\s*1\s*\)|\[0\])"
    r"|\binitials?\b"
    r")",
    re.I,
)
_KEY_BACKSLASH = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"']\\\\[\"']"
    r"|[\"']\\\\[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?key\s*===?\s*[\"']Backslash[\"']"
    r"|[\"']Backslash[\"']\s*===?\s*(?:e\.)?key"
    r"|(?:e\.)?code\s*===?\s*[\"']Backslash[\"']"
    r"|[\"']Backslash[\"']\s*===?\s*(?:e\.)?code"
    r")"
)
_ALTGR_SAFE_MOD = re.compile(
    r"(?:e\.)?ctrlKey\s*&&\s*!(?:e\.)?altKey",
)
_COLLAPSE_WORD = re.compile(r"collaps", re.I)
_AUTO_WIDTH = re.compile(
    r"("
    r"\binnerWidth\b"
    r"|\bmatchMedia\s*\("
    r"|addEventListener\s*\(\s*[\"']resize[\"']"
    r"|\bonresize\b"
    r")",
    re.I,
)
_NARROW_PX = re.compile(r"\b(?:880|800)\b")
_SELECT_PERSON_CALL = re.compile(r"\b(?:selectPerson|personShow)\s*\(")
_DOCS_COLLAPSE = re.compile(
    r"(?:people|sidebar).{0,80}collaps|collaps.{0,80}(?:people|sidebar)",
    re.I | re.S,
)
_DOCS_BACKSLASH = re.compile(
    r"("
    r"⌘\s*\\"
    r"|Cmd(?:-|\s*|\+)\s*\\"
    r"|Command(?:-|\s*|\+)\s*\\"
    r"|Ctrl(?:-|\s*|\+)\s*\\"
    r"|ctrl(?:-|\s*|\+)\s*\\"
    r")",
    re.I,
)
_DOCS_LOCAL_PREF = re.compile(
    r"("
    r"local(?:Storage)?"
    r".{0,80}(?:not|never|isn.t).{0,24}iCloud"
    r"|(?:not|never|isn.t).{0,24}iCloud.{0,80}local"
    r"|preference is local"
    r"|local(?:ly)?(?: persist| only| pref)"
    r"|localStorage"
    r")",
    re.I | re.S,
)
_DOCS_NOT_ICLOUD = re.compile(
    r"(?:not|never|isn.t).{0,40}iCloud|iCloud.{0,40}(?:not|never)",
    re.I,
)
_DOCS_800 = re.compile(
    r"(?:~|about |around |near )?\s*800\s*(?:px|pixels)?",
    re.I,
)
_DOCS_EXPAND_NARROW = re.compile(
    r"("
    r"\bexpand(?:s|ed|ing)?\b.{0,120}(?:narrow|under\s*880|< ?880)"
    r"|(?:narrow|under\s*880|< ?880).{0,120}\bexpand(?:s|ed|ing)?\b"
    r")",
    re.I | re.S,
)
_DOCS_SLASH_RAIL = re.compile(
    r"("
    r"(?:^|[\s`])/[\s`].{0,140}(?:\brail\b|when\s+collaps|while\s+collaps)"
    r"|(?:\brail\b|when\s+collaps|while\s+collaps).{0,140}(?:^|[\s`])/"
    r"|person-filter.{0,100}(?:\brail\b|when\s+collaps|while\s+collaps)"
    r"|(?:\brail\b|collaps\w*).{0,80}(?:person-filter|people filter)"
    r"|still\s+filter.{0,80}(?:\brail\b|collaps)"
    r")",
    re.I | re.S,
)
_CLICK_ON = re.compile(
    r"(?:on:click|onclick)\s*=\s*\{",
    re.I,
)
_TITLE_DISPLAY = re.compile(
    r"\btitle\s*=\s*\{[^}]{0,200}(?:display_name|displayName|personLabel)",
    re.I,
)
_TITLE_RAW_ID = re.compile(
    r"\btitle\s*=\s*\{[^}]{0,80}(?:\bp\.id\b|\bperson\.id\b)",
    re.I,
)
_OWNED_TOOLTIP_IMPORT = re.compile(
    r"from\s+[\"']\$lib/components/ui/tooltip(?:/index(?:\.js|\.ts)?)?[\"']",
)
_TOOLTIP_OPEN = re.compile(r"<Tooltip(?:Content|Trigger|Provider|\.Root|\.Content)?\b")
_PERSON_FILTER_MARKUP = re.compile(
    r"""(?:id\s*=\s*(?:["']person-filter["']|\{\s*["']person-filter["']\s*\})|#person-filter)"""
)
_SESSION_OVERRIDE = re.compile(
    r"\b(?:"
    r"forceOpen|forceExpanded|force_open|forceWide|"
    r"sessionOpen|sessionExpanded|sessionOverride|"
    r"expandOverride|openOverride|overrideOpen|overrideNarrow|"
    r"pinnedOpen|stayOpen|stayExpanded|keepOpen|keepExpanded|"
    r"expandNow|force\w*Open|\w*Override"
    r")\b",
)
_CODE_BACKSLASH = re.compile(
    r"(?:e\.)?code\s*===?\s*[\"']Backslash[\"']"
    r"|[\"']Backslash[\"']\s*===?\s*(?:e\.)?code"
)
_CODE_INTL_BACKSLASH = re.compile(
    r"(?:e\.)?code\s*===?\s*[\"']IntlBackslash[\"']"
    r"|[\"']IntlBackslash[\"']\s*===?\s*(?:e\.)?code"
)
_CODE_BACKSLASH_EITHER = re.compile(
    r"("
    r"(?:e\.)?code\s*===?\s*[\"'](?:Intl)?Backslash[\"']"
    r"|[\"'](?:Intl)?Backslash[\"']\s*===?\s*(?:e\.)?code"
    r"|(?:e\.)?code\s*\.includes\s*\(\s*[\"']Backslash[\"']"
    r"|(?:e\.)?code\s*\.endsWith\s*\(\s*[\"']Backslash[\"']"
    r"|\[[^\]]*Backslash[^\]]*\]\s*\.includes\s*\(\s*(?:e\.)?code"
    r")"
)


def _people_collapse_shell(markup: str) -> str:
    """Parent grid + people pane open tag (expanded-width lives here)."""
    m = re.search(r"\bdata-people-sidebar\b", markup)
    if not m:
        return ""
    return markup[max(0, m.start() - 500) : m.end() + 480]


def _has_fixed_people_width(blob: str) -> bool:
    """True when expanded width is a fixed token, not only minmax(0,18rem)."""
    stripped = _MINMAX_PEOPLE_TRACK.sub("", blob)
    return bool(_FIXED_PEOPLE_WIDTH.search(stripped))


def _mentions_backslash_key(src: str) -> bool:
    return bool(_KEY_BACKSLASH.search(src)) or bool(
        re.search(r"[\"']Backslash[\"']", src)
    )


def _pref_key_ok(key: str) -> bool:
    low = key.lower()
    mentions = "sidebar" in low or "collapsed" in low
    namespaced = "interlace" in low or "." in key
    return mentions and namespaced


def _click_handler_names(tag: str) -> list[str]:
    names = re.findall(
        r"(?:on:click|onclick)\s*=\s*\{[^}]*?\b([A-Za-z_][\w]*)\s*\(",
        tag,
        re.I,
    )
    names += re.findall(
        r"(?:on:click|onclick)\s*=\s*\{([A-Za-z_][\w]*)\}",
        tag,
        re.I,
    )
    return names


def _toggle_collapse_surface(app: str, markup: str) -> str:
    """data-sidebar-toggle handlers + named collapse helpers."""
    parts: list[str] = []
    for m in re.finditer(r"\bdata-sidebar-toggle\b", markup):
        tag = _opening_tag(markup, m.start())
        parts.append(tag)
        parts.append(markup[max(0, m.start() - 80) : m.end() + 240])
        for name in _click_handler_names(tag):
            inner = _ts_fn_body(app, name) or _function_body(app, name)
            if inner:
                parts.append(_expand_fn_calls(app, inner))
        # Inline onclick={() => { ... }} body.
        cm = _CLICK_ON.search(tag)
        if cm:
            brace = tag.find("{", cm.end() - 1)
            if brace >= 0:
                parts.append(tag[brace:])
    for name in re.findall(
        r"(?:function|const|let)\s+"
        r"(toggle\w*(?:Sidebar|Collapse)|set\w*(?:Sidebar|Collapsed)\w*)",
        app,
        re.I,
    ):
        inner = _ts_fn_body(app, name) or _function_body(app, name)
        if inner:
            parts.append(_expand_fn_calls(app, inner))
    return "\n".join(parts)


def _gated_on_collapse(markup: str, pos: int) -> bool:
    for kind, cond, _extra in _template_stack(markup, pos):
        if kind not in {"if", "if-else"}:
            continue
        if _COLLAPSE_WORD.search(cond):
            return True
    return False


def _split_if_at(markup: str, if_start: int) -> tuple[str, str]:
    """Then / else bodies of the {#if} starting at if_start."""
    head = re.match(r"\{#if\s+[^}]+\}", markup[if_start:])
    if not head:
        return "", ""
    body_start = if_start + head.end()
    depth = 1
    else_body_start: int | None = None
    then_end: int | None = None
    for t in _TMPL_TOKEN.finditer(markup, body_start):
        tok = t.group(0)
        if tok.startswith("{#if"):
            depth += 1
        elif tok.startswith("{/if}"):
            depth -= 1
            if depth == 0:
                if then_end is None:
                    then_end = t.start()
                then = markup[body_start:then_end]
                els = markup[else_body_start : t.start()] if else_body_start is not None else ""
                return then, els
        elif depth == 1 and (tok.startswith("{:else}") or tok.startswith("{:else if")):
            if then_end is None:
                then_end = t.start()
                else_body_start = t.end()
    then = markup[body_start:then_end] if then_end is not None else markup[body_start:]
    els = markup[else_body_start:] if else_body_start is not None else ""
    return then, els


def _collapsed_people_surface(people_rows: str) -> str:
    """Always-on option tags plus the collapsed / rail {#if} branch."""
    parts: list[str] = []
    for m in re.finditer(
        r"<button\b[^>]*>|<[^>]*\brole\s*=\s*[\"']option[\"'][^>]*>",
        people_rows,
        re.I | re.S,
    ):
        parts.append(m.group(0))
    for m in re.finditer(r"\{#if\s+([^}]*)\}", people_rows):
        if not _COLLAPSE_WORD.search(m.group(1)):
            continue
        then, els = _split_if_at(people_rows, m.start())
        if re.search(r"!\s*[\w.]*collaps", m.group(1), re.I):
            parts.append(els)
        else:
            parts.append(then)
    return "\n".join(parts)


def _people_row_tooltip_ok(app: str, people_rows: str) -> bool:
    """Owned Tooltip on the row (wraps the option) or inside the rail branch."""
    if not _OWNED_TOOLTIP_IMPORT.search(app):
        return False
    if not _TOOLTIP_OPEN.search(people_rows):
        return False
    hover = _collapsed_people_surface(people_rows)
    for m in re.finditer(r"<Tooltip\b", people_rows):
        inner = _matched_inner(people_rows, m.start())
        tree = people_rows[m.start() : m.start() + 240] + "\n" + inner
        if not re.search(r"display_name|displayName|personLabel", tree):
            continue
        wraps_option = bool(re.search(r"\brole\s*=\s*[\"']option[\"']|<button\b", inner, re.I))
        in_rail = bool(_TOOLTIP_OPEN.search(hover)) and (
            people_rows[m.start() : m.start() + 40] in hover or inner[:80] in hover
        )
        if wraps_option or in_rail:
            return True
    return False


def _sidebar_collapsed_rhs(src: str) -> str:
    """RHS of sidebarCollapsed = … / $derived(…)."""
    m = re.search(r"\bsidebarCollapsed\s*=\s*", src)
    if not m:
        return ""
    rest = src[m.end() :]
    dm = re.match(r"\$derived(?:\.by)?\s*\(", rest)
    if dm:
        close = _match_closer(rest, dm.end() - 1)
        return rest[dm.end() : close] if close >= 0 else rest[dm.end() :]
    end = rest.find(";")
    return rest[:end] if end >= 0 else rest[:240]


def _hard_narrow_or_user(rhs: str) -> bool:
    compact = re.sub(r"\s+", "", rhs)
    return bool(
        re.fullmatch(
            r"\(?(narrow\|\|userCollapsed|userCollapsed\|\|narrow)\)?",
            compact,
        )
    )


def _backslash_codes_ok(src: str) -> bool:
    """True when onKey treats physical Backslash and IntlBackslash."""
    if re.search(
        r"(?:e\.)?code\s*\.\s*(?:includes|endsWith)\s*\(\s*[\"']Backslash[\"']",
        src,
    ):
        return True
    arr = re.search(r"\[([^\]]*)\]\s*\.includes\s*\(\s*(?:e\.)?code", src)
    if arr and "Backslash" in arr.group(1) and "IntlBackslash" in arr.group(1):
        return True
    return bool(_CODE_BACKSLASH.search(src) and _CODE_INTL_BACKSLASH.search(src))


def _auto_collapse_surface(app: str, logic: str) -> str:
    cleaned = _without_comments(app)
    blob = cleaned + "\n" + logic
    parts = [_windows_around(blob, _AUTO_WIDTH, before=220, after=520)]
    for m in re.finditer(
        r"addEventListener\s*\(\s*[\"']resize[\"']\s*,\s*([A-Za-z_][\w]*)",
        blob,
    ):
        inner = _ts_fn_body(app, m.group(1)) or _function_body(app, m.group(1))
        if inner:
            parts.append(inner)
    return "\n".join(parts)


def assert_people_sidebar_collapse(crate: Path) -> None:
    """#212: fixed-width people sidebar; collapse to a rail; persist locally.

    Expanded width is a token (w-72 / 18rem), not only shrinking
    minmax(0,18rem). data-sidebar-toggle + collapsed hook. ⌘\\ / Ctrl+\\
    in onKey (AltGr-safe, works from fields). localStorage persist — not
    write_last_path / config.toml. Auto-collapse at 880/800. Toggle must
    not remount the open person. Keep nav + chrome search. Follow-up:
    rail hover name, #person-filter stays mounted, forceOpen so Expand
    works under 880, e.code Backslash / IntlBackslash. Not: liquid
    multi-column, hiding Search/Review.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#212: App.svelte required (people sidebar collapse lives there)")
    app = app_path.read_text()
    markup = _strip_html_comments(_svelte_markup(app))
    app_clean = _without_comments(app)
    logic = _web_logic(crate)
    logic_clean = _without_comments(logic)
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = search_path.read_text() if search_path.is_file() else ""
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    session_path = repo_root() / "crates" / "interlace-core" / "src" / "session.rs"
    session = session_path.read_text() if session_path.is_file() else ""
    rust = _tauri_rust_blob(crate)
    conf_path = crate / "tauri.conf.json"
    conf = conf_path.read_text() if conf_path.is_file() else ""

    # 1) data-people-sidebar stays; expanded width is a fixed token.
    if re.search(r"\bdata-people-sidebar\b", app) and not re.search(
        r"\bdata-people-sidebar\b", markup
    ):
        fail(
            "#212: data-people-sidebar must stay on the people pane markup "
            "(not only a comment or script string)"
        )
    if not re.search(r"\bdata-people-sidebar\b", markup):
        fail(
            "#212: data-people-sidebar must stay on the left people pane "
            "(collapse is that column, not a new shell)"
        )
    shell = _people_collapse_shell(markup)
    if not _has_fixed_people_width(shell):
        fail(
            "#212: people sidebar expanded width must be a fixed token "
            "(w-72 / 18rem), not only shrinking minmax(0,18rem)"
        )

    # 2) Collapse control + collapsed hook.
    if re.search(r"\bdata-sidebar-toggle\b", app) and not re.search(
        r"\bdata-sidebar-toggle\b", markup
    ):
        fail(
            "#212: data-sidebar-toggle must be in App.svelte markup "
            "(not only a comment or script string)"
        )
    if not re.search(r"\bdata-sidebar-toggle\b", markup):
        fail(
            "#212: people sidebar needs a collapse control "
            "(data-sidebar-toggle) that collapses to a rail"
        )
    toggle_tag = _open_tag_around(markup, r"data-sidebar-toggle")
    pane_tag = _open_tag_around(markup, r"data-people-sidebar")
    has_pane_hook = bool(re.search(r"\bdata-people-sidebar-collapsed\b", markup))
    has_aria = bool(re.search(r"\baria-expanded\b", toggle_tag))
    if not has_pane_hook and not has_aria:
        fail(
            "#212: collapsed state must be visible in markup "
            "(data-people-sidebar-collapsed on the pane or aria-expanded "
            "on data-sidebar-toggle)"
        )
    if has_pane_hook and not re.search(
        r"\bdata-people-sidebar-collapsed\b", pane_tag + "\n" + shell
    ):
        # Hook may sit on the same pane tag or the people column wrapper.
        if not re.search(r"\bdata-people-sidebar-collapsed\b", markup):
            fail(
                "#212: data-people-sidebar-collapsed must sit on the people "
                "pane (or aria-expanded on the toggle)"
            )

    # 3) Rail / icons path; no raw person ids in list labels (#159 spirit).
    regions = _people_sidebar_regions(crate)
    region_blob = "\n".join(regions) if regions else shell
    rail_src = region_blob + "\n" + shell + "\n" + markup
    has_rail_w = bool(_RAIL_WIDTH.search(rail_src))
    has_rail_icon = bool(_RAIL_ICON.search(region_blob) or _RAIL_ICON.search(shell))
    has_collapsed_if = bool(
        re.search(r"\{#if\s+[^}]{0,120}collaps", markup, re.I)
    )
    if not (has_rail_w or has_rail_icon or has_collapsed_if):
        fail(
            "#212: collapsed people sidebar must be a rail / icons path "
            "(w-12 / w-14, or initials / Lucide person icon — not a hidden column)"
        )
    if re.search(
        r"(?:collaps[^;]{0,80}\b(?:hidden|w-0|invisible)\b"
        r"|\b(?:hidden|w-0|invisible)\b[^;]{0,80}collaps)",
        region_blob + "\n" + shell,
        re.I,
    ) and not (has_rail_w or has_rail_icon):
        fail(
            "#212: collapse must go to a rail (w-12 / icons), "
            "not hide the people column"
        )
    each_blocks: list[str] = []
    for p in _web_sources(crate):
        if p.suffix != ".svelte" or p.name in _PERSON_PANE_SKIP:
            continue
        block = _people_each_block(_svelte_markup(p.read_text()))
        if block:
            each_blocks.append(block)
    people_rows = "\n".join(each_blocks)
    label_src = people_rows + "\n" + region_blob
    visible_rows = _strip_tag_attrs(label_src)
    visible_rows = re.sub(r"\{[#/:@].*?\}", "", visible_rows, flags=re.S)
    if _PEOPLE_ID_VISIBLE.search(visible_rows):
        fail(
            "#212: no raw person ids in people-list / rail labels "
            "(show display name / initial; data-id attributes are fine)"
        )
    if _PEOPLE_ID_FALLBACK.search(label_src):
        fail("#212: do not fall back a missing person name to a raw id")

    # 4) ⌘\\ / Ctrl+\\ in existing onKey — AltGr-safe, works from fields.
    raw_body = _app_keydown_body(app_clean) or _app_keydown_body(app)
    if not raw_body.strip():
        fail(
            "#212: App.svelte must handle window keydown "
            "(onKey) so ⌘\\ / Ctrl+\\ can collapse the sidebar"
        )
    body = _expand_fn_calls(app_clean, raw_body)
    if body == raw_body:
        body = _expand_fn_calls(app, raw_body)
    prefix, tail = _split_people_only(raw_body)
    prefix_x = _expand_fn_calls(app_clean, prefix) if prefix.strip() else body
    if prefix_x == prefix:
        prefix_x = _expand_fn_calls(app, prefix) if prefix.strip() else body
    if not _KEY_BACKSLASH.search(raw_body) and not _KEY_BACKSLASH.search(body):
        fail(
            "#212: App key handler must treat metaKey/ctrlKey + \\ / Backslash "
            "as sidebar collapse (⌘\\ / Ctrl+\\)"
        )
    if tail and _KEY_BACKSLASH.search(tail) and not _KEY_BACKSLASH.search(prefix_x):
        fail(
            "#212: ⌘\\ / Ctrl+\\ must run like ⌘F "
            "(it is after `if (view !== \"people\") return` and would not "
            "fire from an input off People)"
        )
    bs_surface = _windows_around(prefix_x, _KEY_BACKSLASH)
    if not bs_surface.strip():
        bs_surface = _windows_around(body, _KEY_BACKSLASH)
    if not _has_mod_combo(bs_surface) and not _has_mod_combo(prefix_x):
        fail(
            "#212: sidebar collapse must accept metaKey or ctrlKey "
            "(⌘\\ on macOS; Ctrl+\\ so gates/tests see the fallback)"
        )
    if not _ALTGR_SAFE_MOD.search(prefix_x) and not _ALTGR_SAFE_MOD.search(bs_surface):
        fail(
            "#212: ⌘\\ / Ctrl+\\ must use the AltGr-safe mod "
            "(metaKey || (ctrlKey && !altKey)) — same as #132"
        )
    if not _MOD_EITHER.search(bs_surface) and not re.search(r"\bmod\b", bs_surface):
        fail("#212: \\ / Backslash collapse must be a metaKey/ctrlKey combo, not a bare key")
    guard_span = _input_guard_span(raw_body)
    handler = _KEY_BACKSLASH.search(raw_body) or _KEY_BACKSLASH.search(body)
    if guard_span and handler:
        guard = raw_body[guard_span[0] : guard_span[1] + 1]
        after_guard = handler.start() > guard_span[1]
        if after_guard and not _mentions_backslash_key(guard):
            fail(
                "#212: ⌘\\ / Ctrl+\\ must work from an INPUT like ⌘F "
                "(allow the combo through the INPUT/TEXTAREA/SELECT guard)"
            )

    # 5) Persist via namespaced localStorage — not write_last_path / config.toml.
    web_blob = app_clean + "\n" + logic_clean
    if not re.search(r"localStorage\s*\.\s*setItem\s*\(", web_blob):
        fail(
            "#212: persist collapse in localStorage.setItem "
            "(namespaced key; not iCloud, not write_last_path)"
        )
    if not re.search(r"localStorage\s*\.\s*getItem\s*\(", web_blob) and not _LS_BRACKET.search(
        web_blob
    ):
        fail(
            "#212: restore the persisted sidebar collapse from localStorage.getItem "
            "(same namespaced key)"
        )
    ls_keys = _ls_pref_keys(web_blob)
    if not any(_pref_key_ok(k) for k in ls_keys):
        fail(
            "#212: localStorage key must be namespaced and mention sidebar / "
            "collapsed (e.g. interlace.peopleSidebarCollapsed)"
        )
    if not session_path.is_file():
        fail("#212: crates/interlace-core/src/session.rs required (do not stash UI prefs there)")
    wl = _rust_fn_body(_without_comments(session), "write_last_path")
    if not wl.strip():
        fail(
            "#212: keep session.rs write_last_path as the last_archive_path writer "
            "(do not rewrite it to dump UI prefs)"
        )
    extra_keys = [k for k in _toml_keys_in_fn(wl) if k != "last_archive_path"]
    if extra_keys or re.search(r"\b(?:sidebar|collapsed|people_sidebar)\b", wl, re.I):
        fail(
            "#212: do not rewrite session.rs write_last_path to dump extra keys "
            "(sidebar collapse is not last_archive_path / config.toml)"
        )
    persist_bits = [
        _toggle_collapse_surface(app, markup),
        _windows_around(web_blob, re.compile(r"localStorage"), before=160, after=220),
        _windows_around(web_blob, _COLLAPSE_WORD, before=120, after=200),
    ]
    persist_surface = "\n".join(persist_bits)
    if _LAST_PATH_API.search(persist_surface) or _CONFIG_TOML.search(persist_surface):
        fail(
            "#212: do not persist the sidebar pref via write_last_path / "
            "read_last_path / config.toml (localStorage only)"
        )
    rust_clean = _without_comments(session + "\n" + rust)
    for m in re.finditer(r"sidebar|collapsed", rust_clean, re.I):
        window = rust_clean[max(0, m.start() - 360) : m.end() + 360]
        if _LAST_PATH_API.search(window) or _CONFIG_TOML.search(window):
            fail(
                "#212: do not persist the sidebar pref via write_last_path / "
                "read_last_path / config.toml (localStorage only)"
            )

    # 6) Auto-collapse on narrow windows (880 / 800).
    auto_src = _auto_collapse_surface(app, logic)
    if not _AUTO_WIDTH.search(app_clean) and not _AUTO_WIDTH.search(logic_clean):
        fail(
            "#212: auto-collapse the people sidebar on a narrow window "
            "(innerWidth / matchMedia / resize)"
        )
    if not _NARROW_PX.search(auto_src):
        fail(
            "#212: auto-collapse threshold must mention 880 or 800 "
            "(keep the timeline readable at ~800px)"
        )

    # 7) Toggle path does not remount the open person.
    toggle_src = _toggle_collapse_surface(app, markup)
    if _SELECT_PERSON_CALL.search(toggle_src):
        fail(
            "#212: collapse toggle must not call selectPerson / personShow "
            "(do not remount the open person)"
        )
    for m in re.finditer(
        r"""id\s*=\s*["']person-timeline["']|#person-timeline""",
        markup,
    ):
        if _gated_on_collapse(markup, m.start()):
            fail(
                "#212: {#if collapsed} must not wrap the timeline "
                "(#person-timeline stays mounted)"
            )
    for m in re.finditer(r"\{#key\s+([^}]*)\}", markup):
        if _COLLAPSE_WORD.search(m.group(1)) and re.search(
            r"person-timeline", markup[m.end() : m.end() + 8000]
        ):
            fail(
                "#212: {#key collapsed} must not wrap the timeline "
                "(toggling collapse must not remount the open person)"
            )

    # 8) Top nav + chrome search stay (do not hide Search/Review).
    if not re.search(r"<nav\b", markup):
        fail("#212: keep the top nav (People / Search / Review / Import / Doctor)")
    if not re.search(r"\bdata-chrome-search\b", markup):
        fail("#212: keep chrome search field data-chrome-search (do not hide Search chrome)")
    for rx, label in (
        (re.compile(r"<nav\b"), "top nav"),
        (re.compile(r"\bdata-chrome-search\b"), "data-chrome-search"),
    ):
        hit = rx.search(markup)
        if hit and _gated_on_collapse(markup, hit.start()):
            fail(
                f"#212: collapse must not hide the {label} "
                "(Search / Review chrome stays; collapse is the people column only)"
            )

    # 9) Docs: collapse + shortcut + local persist + readable ~800px.
    if not dtxt.strip():
        fail(
            "#212: docs/user/app.md required — people sidebar collapse, "
            "⌘\\ / Ctrl+\\, local persist, readable ~800px"
        )
    if not _DOCS_COLLAPSE.search(dtxt):
        fail(
            "#212: docs/user/app.md must say the people sidebar collapses "
            "(fixed width; control + shortcut)"
        )
    if not _DOCS_BACKSLASH.search(dtxt):
        fail("#212: docs/user/app.md must document ⌘\\ / Ctrl+\\ (collapse the people sidebar)")
    if not _DOCS_LOCAL_PREF.search(dtxt):
        fail(
            "#212: docs/user/app.md must say the collapse preference is local "
            "(localStorage / local, not iCloud)"
        )
    if not _DOCS_NOT_ICLOUD.search(dtxt):
        fail(
            "#212: docs/user/app.md must say the collapse preference is not iCloud"
        )
    if not _DOCS_800.search(dtxt):
        fail(
            "#212: docs/user/app.md must say the timeline stays readable "
            "around 800px"
        )

    # 10) Rail hover name: title={display_name} or owned Tooltip. aria-label stays.
    hover_src = _collapsed_people_surface(people_rows)
    if _TITLE_RAW_ID.search(people_rows) or _TITLE_RAW_ID.search(hover_src):
        fail(
            "#212: rail hover name must interpolate display_name "
            "(no raw person ids on title=)"
        )
    has_title = bool(_TITLE_DISPLAY.search(hover_src))
    has_tip = _people_row_tooltip_ok(app, people_rows)
    if not has_title and not has_tip:
        fail(
            "#212: collapsed / rail person rows must expose a hover name "
            "(title={p.display_name} or owned Tooltip); keep aria-label; "
            "no raw person ids"
        )
    if not re.search(
        r"aria-label\s*=\s*\{[^}]{0,240}(?:display_name|displayName|personLabel)",
        people_rows,
    ):
        fail(
            "#212: keep aria-label on person rows "
            "(hover title is extra; do not drop VoiceOver)"
        )

    # 11) #person-filter stays in the DOM when the rail is showing.
    pf = list(_PERSON_FILTER_MARKUP.finditer(markup))
    if not pf:
        fail(
            "#212: #person-filter must stay in the DOM when the rail is showing "
            "(/ still focuses it; do not unmount the filter)"
        )
    for m in pf:
        if _gated_on_collapse(markup, m.start()):
            fail(
                "#212: #person-filter must not sit inside a {#if …collaps…} block "
                "(/ still filters when the rail is showing; sr-only is OK)"
            )

    # 12) Session override so Expand opens while innerWidth < 880.
    rhs = _sidebar_collapsed_rhs(app_clean) or _sidebar_collapsed_rhs(app)
    if _hard_narrow_or_user(rhs):
        fail(
            "#212: visible collapse must not be only narrow || userCollapsed "
            "(need a session override so Expand can open while innerWidth < 880)"
        )
    if not _SESSION_OVERRIDE.search(rhs):
        fail(
            "#212: people sidebar needs a session override (forceOpen or "
            "equivalent) so Expand / ⌘\\ can open while innerWidth < 880"
        )
    persist_fn = _ts_fn_body(app, "persistSidebar") or _function_body(app, "persistSidebar")
    override_assign = "\n".join(
        [
            toggle_src,
            persist_fn,
            bs_surface,
            _windows_around(app_clean, _SESSION_OVERRIDE, before=80, after=120),
        ]
    )
    if not re.search(
        rf"{_SESSION_OVERRIDE.pattern}\s*=",
        override_assign,
    ):
        fail(
            "#212: Expand / toggle / ⌘\\ must set forceOpen (or equivalent) "
            "so the pane opens immediately under 880"
        )
    clear_bits = [
        auto_src,
        persist_fn,
        _ts_fn_body(app, "syncNarrow") or _function_body(app, "syncNarrow"),
        _windows_around(app_clean, _NARROW_PX, before=160, after=280),
    ]
    clear_surface = "\n".join(clear_bits)
    override_names = _SESSION_OVERRIDE.findall(rhs) or _SESSION_OVERRIDE.findall(app_clean)
    cleared = False
    for name in override_names:
        if re.search(rf"\b{re.escape(name)}\s*=\s*(?:false|0|!1)\b", clear_surface):
            cleared = True
            break
        if re.search(
            rf"if\s*\([^)]{{0,80}}(?:narrow|innerWidth\s*<)[^)]*\)\s*"
            rf"\{{[^}}]{{0,160}}\b{re.escape(name)}\s*=",
            clear_surface,
            re.I,
        ):
            cleared = True
            break
    if not cleared and not re.search(
        r"(?://|/\*)[^\n]{0,200}(?:forceOpen|force.?open|override).{0,80}"
        r"(?:clear|reset|false).{0,60}(?:narrow|880|cross)",
        app,
        re.I,
    ):
        fail(
            "#212: crossing into narrow must clear forceOpen (or equivalent) "
            "so auto-collapse still runs at innerWidth < 880"
        )

    # 13) Physical ⌘\\ : e.code Backslash / IntlBackslash (INPUT guard too).
    code_src = prefix_x + "\n" + body + "\n" + raw_body
    if not _backslash_codes_ok(code_src):
        fail(
            "#212: onKey must match e.code === \"Backslash\" or "
            "\"IntlBackslash\" (keep e.key === \"\\\\\" allowed; Turkish-Q / ISO)"
        )
    if guard_span:
        guard = raw_body[guard_span[0] : guard_span[1] + 1]
        guard_x = _expand_fn_calls(app_clean, guard)
        if guard_x == guard:
            guard_x = _expand_fn_calls(app, guard)
        if not _CODE_BACKSLASH_EITHER.search(guard_x) and not _backslash_codes_ok(guard_x):
            fail(
                "#212: INPUT guard must let the e.code Backslash / IntlBackslash "
                "path through, not only e.key === \"\\\\\""
            )

    # 14) Docs: Expand on a narrow window; / still filters when the rail shows.
    if not _DOCS_EXPAND_NARROW.search(dtxt):
        fail(
            "#212: docs/user/app.md must say Expand works on a narrow window "
            "(innerWidth < 880 is not a hard floor)"
        )
    if not _DOCS_SLASH_RAIL.search(dtxt):
        fail(
            "#212: docs/user/app.md must say / still filters when the rail "
            "is showing (#person-filter stays mounted)"
        )

    # 15) Do not soften #q, chrome search, sidebar, overflow-x, virtualizer,
    #     overlay titlebar, CSP.
    if not re.search(r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""", search):
        fail('#212: keep id="q" as the canonical query field (#208)')
    if not re.search(r"\bdata-chrome-search\b", app):
        fail("#212: keep chrome search field data-chrome-search (#208)")
    if not re.search(r"\bdata-people-sidebar\b", app):
        fail("#212: keep data-people-sidebar (#159 / #212)")
    if not _OVERFLOW_X_HIDDEN.search(shell) and not _OVERFLOW_X_HIDDEN.search(region_blob):
        fail(
            "#212: keep overflow-x-hidden on the people pane (#159) "
            "(do not rewrite assert_people_sidebar_no_x_scroll)"
        )
    if not re.search(r"\bvisibleRange\b", app + "\n" + logic):
        fail(
            "#212: keep the person-timeline virtualizer visibleRange "
            "(#120 / #224)"
        )
    if not re.search(r"titleBarStyle", conf) and not re.search(
        r"\bdata-tauri-drag-region\b", app
    ):
        fail("#212: keep the overlay titlebar (#211)")
    if CSP not in conf:
        fail("#212: do not soften tauri CSP")
