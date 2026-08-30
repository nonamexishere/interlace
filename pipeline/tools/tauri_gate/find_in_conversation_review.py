"""#310 fold — PR #332 review bugs (haystack / URL mark / first-hit seek).

Sibling of find_in_conversation.py (471) and
find_in_conversation_count.py. Do not grow those files. Lock the three
review bugs only. Do **not** lock a joined subject+body phrase-span.

Must-IDs: find-haystack-visible, find-mail-quoted-open,
find-fields-not-joined, find-url-mark, find-seek-off-hit,
find-keep-people, find-keep-count, find-keep-no-fts, find-keep-text.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.find_in_conversation import (
    _FIND_HOOK,
    _FTS,
    _ISSUE,
    _MARK,
    _field_tag,
    _find_logic,
    _fn,
    _pane_blob,
    _read,
)
from tauri_gate.scan import (
    _HTML_BODY,
    _call_arg,
    _expand_fn_calls,
    _match_closer,
    _matched_inner,
    _svelte_markup,
    _without_comments,
)
from tauri_gate.search_field_keys import _API_SEARCH_CALL
from tauri_gate.search_hits_jump_rest import _SEARCH_UNSAFE_HTML

_MAIL_GATE = re.compile(
    r"\bisMailRow\b"
    r"|(?:platform|conversation_kind).{0,80}(?:gmail|email_thread)"
    r"|(?:gmail|email_thread).{0,80}(?:platform|conversation_kind)",
    re.I | re.S,
)
_BODY_OR_SUBJECT = re.compile(
    r"(?:body_text|\.body)\s*\|\|\s*(?:[\w.]+\.)?subject"
    r"|displayBody\s*\(\s*(?:[\w.]+\.)?(?:body_text|body)\s*\|\|",
    re.I,
)
# Joined `"subject body"` haystack — the phrase-span we must **not** lock.
_JOINED_PHRASE = re.compile(
    r"\$\{(?:subject|(?:row\.)?subject)[^}]{0,80}\}\s+\$\{"
    r"|\$\{(?:subject|(?:row\.)?subject)[^}]{0,160}"
    r"(?:displayBody|parts\.main)"
    r"|(?:subject|(?:row\.)?subject)\s*\+\s*[\"'`] [\"'`]"
    r"|\.join\s*\(\s*[\"'`] [\"'`]\s*\)\s*"
    r"(?:\.toLowerCase\s*\(\s*\)\s*)?\.includes\s*\(",
)
_QUOTED_OPEN = re.compile(r"\bquotedOpen\b")
_QUOTED_FIELD = re.compile(
    r"quotedOpen[\s\S]{0,280}(?:parts\.quoted|displayBody\s*\(\s*(?:parts\.)?quoted)"
    r"|(?:parts\.quoted|displayBody\s*\(\s*(?:parts\.)?quoted)[\s\S]{0,280}quotedOpen",
)
_HIT_FNS = ("findHitIndices", "findCount", "stepFindIndex")
_LAST_Q_ONLY = re.compile(
    r"if\s*\(\s*(?:findQ|findQuery|tlFind)\s*===?\s*lastFindQ\s*\)\s*return"
    r"|if\s*\(\s*lastFindQ\s*===?\s*(?:findQ|findQuery|tlFind)\s*\)\s*return"
)
_ON_HIT = re.compile(
    r"(?:hits|findHits)\.includes\s*\(\s*tlIndex"
    r"|indexOf\s*\(\s*tlIndex\s*\)\s*(?:<|===?)\s*(?:0|-1)"
    r"|!\s*(?:hits|findHits)\.includes\s*\(\s*tlIndex"
)
_HITS0 = re.compile(r"(?:hits|findHits)\s*\[\s*0\s*\]")
_URL_KIND = r"seg\.kind\s*===?\s*[\"']url[\"']"
_SPLIT_FIND_SEG = re.compile(r"\bsplitFind\s*\(\s*seg\.text")


def _hl(crate: Path) -> str:
    return _without_comments(_read(crate, "findHighlight.ts"))


def _linkify(crate: Path) -> str:
    return _read(crate, "LinkifyBody.svelte")


def _list(crate: Path) -> str:
    return _without_comments(_read(crate, "TimelineList.svelte"))


def _svelte_if_inner(markup: str, cond_rx: str) -> str:
    header = re.search(rf"\{{#if\s+[^}}]*?(?:{cond_rx})[^}}]*\}}", markup)
    if not header:
        return ""
    start = header.end()
    depth = 1
    i = start
    else_at = -1
    while i < len(markup) and depth:
        mm = re.search(r"\{#if\b|\{:else(?:\s+if\b)?|\{/if\}", markup[i:])
        if not mm:
            break
        tok = mm.group(0)
        pos = i + mm.start()
        if tok.startswith("{#if"):
            depth += 1
        elif tok == "{/if}":
            depth -= 1
            if depth == 0:
                return markup[start : (else_at if else_at >= 0 else pos)]
        elif tok.startswith("{:else") and depth == 1:
            else_at = pos
        i = pos + len(tok)
    return ""


def _if_blocks(src: str, header_rx: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(header_rx, src):
        brace = src.find("{", m.end() - 1)
        if brace < 0 or brace > m.end() + 80:
            stmt = re.match(r"\s*return\s+([^;]+);", src[m.end() :])
            if stmt:
                out.append(stmt.group(1))
            continue
        close = _match_closer(src, brace)
        if close > brace:
            out.append(src[brace + 1 : close])
    return out


def _non_mail_surface(src: str) -> str:
    arms = _if_blocks(src, r"if\s*\(\s*!\s*isMailRow\b")
    for m in re.finditer(r"if\s*\(\s*isMailRow\b[^)]*\)\s*\{", src):
        close = _match_closer(src, m.end() - 1)
        if close < 0:
            continue
        rest = src[close + 1 : close + 48]
        em = re.match(r"\s*else\s*\{", rest)
        if em:
            ebrace = src.find("{", close + 1)
            eclose = _match_closer(src, ebrace)
            if eclose > ebrace:
                arms.append(src[ebrace + 1 : eclose])
        elif re.search(r"\breturn\b", src[m.end() : close]):
            arms.append(src[close + 1 : close + 900])
    for m in re.finditer(r"!\s*isMailRow\s*\([^)]*\)\s*\?([\s\S]{0,360}?):", src):
        arms.append(m.group(1))
    for m in re.finditer(
        r"(?<!!)\bisMailRow\s*\([^)]*\)\s*\?[\s\S]{0,360}?:([\s\S]{0,360}?)(?:;|\)|\n)",
        src,
    ):
        arms.append(m.group(1))
    return "\n".join(arms)


def _anchor_inners(markup: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(r"<a\b", markup):
        inner = _matched_inner(markup, m.start())
        if inner:
            out.append(inner)
    return out


def _split_find_wraps_urls(markup: str) -> bool:
    m = re.search(r"\{#each\s+splitFind\s*\(\s*seg\.text", markup)
    if not m:
        return False
    return bool(re.search(_URL_KIND, markup[m.start() :]))


def _url_marks(markup: str) -> bool:
    url_if = _svelte_if_inner(markup, _URL_KIND)
    if url_if and (_SPLIT_FIND_SEG.search(url_if) or _MARK.search(url_if)):
        return True
    if _split_find_wraps_urls(markup):
        return True
    return any(
        _SPLIT_FIND_SEG.search(inner) or _MARK.search(inner)
        for inner in _anchor_inners(markup)
    )


def _seek_blobs(src: str) -> list[str]:
    blobs: list[str] = []
    for m in re.finditer(r"\$effect\s*\(\s*\(\s*\)\s*=>\s*\{", src):
        close = _match_closer(src, m.end() - 1)
        if close < 0:
            continue
        body = src[m.end() : close]
        if re.search(r"findQ|lastFindQ|findHitIndices", body):
            blobs.append(body)
    for name in (
        "snapFindIndex",
        "seekFind",
        "seekFirstHit",
        "snapToFindHit",
        "ensureFindHit",
        "snapFindHit",
    ):
        body = _fn(src, name)
        if body:
            blobs.append(body)
    return blobs


def _seek_surface(src: str) -> str:
    return "\n".join(_expand_fn_calls(src, b) for b in _seek_blobs(src))


def _last_q_only(body: str) -> bool:
    m = _LAST_Q_ONLY.search(body)
    if not m:
        return False
    cond = m.group(0)
    if _ON_HIT.search(cond):
        return False
    before = body[: m.start()]
    if re.search(r"findHitIndices|filteredTimeline", before) and _ON_HIT.search(
        body[m.start() : m.end() + 120]
    ):
        return False
    return True


def _seek_snaps_off_hit(body: str) -> bool:
    if not re.search(r"findHitIndices|filteredTimeline", body):
        return False
    if not _HITS0.search(body):
        return False
    return bool(_ON_HIT.search(body))


def _hit_calls_pass_quoted(src: str) -> bool:
    for m in re.finditer(rf"\b(?:{'|'.join(_HIT_FNS)})\s*\(", src):
        pre = src[max(0, m.start() - 48) : m.start()]
        if re.search(r"(?:export\s+)?function\s+$", pre):
            continue
        args = _call_arg(src, m.end() - 1)
        if "quotedOpen" not in args:
            return False
    return True


def assert_find_in_conversation_review(crate: Path) -> None:
    """#310 fold: haystack = visible fields; URL marks; seek off-hit."""
    pane_path = crate / "web" / "lib" / "TimelinePane.svelte"
    rows_path = crate / "web" / "lib" / "TimelineRows.svelte"
    link_path = crate / "web" / "lib" / "LinkifyBody.svelte"
    hl_path = crate / "web" / "lib" / "findHighlight.ts"
    if not pane_path.is_file():
        fail(f"{_ISSUE}: TimelinePane.svelte required (in-conversation find)")
    if not rows_path.is_file():
        fail(f"{_ISSUE}: TimelineRows.svelte required (visible bubble haystack)")
    if not link_path.is_file():
        fail(f"{_ISSUE}: LinkifyBody.svelte required (URL + text find marks)")
    if not hl_path.is_file():
        fail(f"{_ISSUE}: findHighlight.ts required (find haystack / seek)")

    pane = _without_comments(_pane_blob(crate))
    logic = _find_logic(crate)
    hl = _hl(crate)
    rows = _read(crate, "TimelineRows.svelte")
    linkify = _linkify(crate)
    markup = _svelte_markup(pane)
    link_mark = _svelte_markup(linkify)
    list_src = _list(crate)
    seek_src = pane + "\n" + list_src + "\n" + hl
    bodies = rows + "\n" + linkify + "\n" + pane

    # Keep existing #310 stay-on-People / count / no-FTS / no-innerHTML.
    tag = _field_tag(markup)
    if not tag and not _FIND_HOOK.search(markup):
        fail(
            f"{_ISSUE}: keep the People pane find field (data-tl-find) — "
            "⌘F stays on People"
        )
    if not re.search(r"\bfindCount\b|data-tl-hit-count|[\"'`]0/0[\"'`]", pane + logic):
        fail(f"{_ISSUE}: keep the find hit counter (findCount / 2/17)")
    if _API_SEARCH_CALL.search(logic) or _FTS.search(logic):
        fail(
            f"{_ISSUE}: keep client substring find — no api.search / second FTS"
        )
    if (
        _HTML_BODY.search(bodies)
        or _SEARCH_UNSAFE_HTML.search(bodies)
        or re.search(r"\.innerHTML\s*=|insertAdjacentHTML\s*\(", bodies)
    ):
        fail(
            f"{_ISSUE}: keep find marks as Svelte text siblings — no {{@html}} / "
            "innerHTML"
        )

    # Bug 1 — haystack is what that row actually displays.
    if not _MAIL_GATE.search(hl):
        fail(
            f"{_ISSUE}: non-mail haystack is displayBody(body || subject) "
            "(no splitQuotedBody) — a WhatsApp `>` line on screen must be a hit"
        )
    non_mail = _non_mail_surface(hl)
    if (
        not non_mail
        or re.search(r"\bsplitQuotedBody\b", non_mail)
        or not _BODY_OR_SUBJECT.search(non_mail)
    ):
        fail(
            f"{_ISSUE}: non-mail haystack is displayBody(body || subject) "
            "(no splitQuotedBody) — do not quote-split a WhatsApp `>` line"
        )
    if not _QUOTED_OPEN.search(hl) or not _QUOTED_FIELD.search(hl):
        fail(
            f"{_ISSUE}: mail Show quoted tail is a find hit only when "
            "quotedOpen[id] (displayBody(parts.quoted); 1/N updates)"
        )
    if not _hit_calls_pass_quoted(logic):
        fail(
            f"{_ISSUE}: findHitIndices / findCount / stepFindIndex must see "
            "quotedOpen so an open quoted tail updates 1/N"
        )
    if _JOINED_PHRASE.search(hl):
        fail(
            f"{_ISSUE}: match each visible field (subject, main, open quoted) "
            '— do not join a "subject body" phrase'
        )

    # Bug 2 — URL-only token counts and is marked inside the <a>.
    if "splitUrls" not in linkify:
        fail(f"{_ISSUE}: keep splitUrls first, then splitFind on url and text")
    if not _SPLIT_FIND_SEG.search(linkify) and not re.search(r"\bsplitFind\s*\(", linkify):
        fail(
            f"{_ISSUE}: splitFind must run on url and text LinkifyBody segments"
        )
    if not _url_marks(link_mark):
        fail(
            f"{_ISSUE}: splitFind must run on url and text LinkifyBody "
            "segments — a URL-only token needs <mark class=\"search-mark\"> "
            "inside the <a>"
        )

    # Bug 3 — first-hit seek after a late timeline replace.
    seek = _seek_surface(seek_src)
    if not seek:
        fail(
            f"{_ISSUE}: if findQ is nonempty and tlIndex is not in "
            "findHitIndices, snap to hits[0]"
        )
    if any(_last_q_only(b) for b in _seek_blobs(seek_src)):
        fail(
            f"{_ISSUE}: if findQ is nonempty and tlIndex is not in "
            "findHitIndices, snap to hits[0] (do not return solely on "
            "findQ === lastFindQ — a late timeline replace must land on 1/N)"
        )
    if not _seek_snaps_off_hit(seek):
        fail(
            f"{_ISSUE}: if findQ is nonempty and tlIndex is not in "
            "findHitIndices, snap to hits[0] (do not jump on a chip-filter "
            "tick if you are already on a hit)"
        )
    sel = _fn(pane, "selectPerson") or pane
    if re.search(r"\bapplyOpenPersonWindow\b", sel) and not re.search(
        r"\bfindQ\b", sel
    ):
        fail(
            f"{_ISSUE}: after a non-append timeline replace, nonempty findQ "
            "must skip open-person pin-latest (applyOpenPersonWindow / "
            "scrollHeight) so the viewport stays on 1/N"
        )

    if re.search(r"/Users/|/home/", pane + "\n" + hl + "\n" + linkify):
        fail(f"{_ISSUE}: tests stay placeholders (Ada) — no real home paths")
