"""Continuation of search_hits_jump."""
from __future__ import annotations

from __future__ import annotations

from __future__ import annotations
import re
from pathlib import Path
from common import fail, repo_root
from tauri_gate.scan import (
    _function_body,
    _HTML_BODY,
    _matching_each_end,
    _search_pane_blob,
    _svelte_interpolations,
    _svelte_markup,
    _ts_function_body,
    _web_logic,
    _without_comments,
)
from tauri_gate.import_boot_guards import _HUMAN_TIME_HELPERS
from tauri_gate.status_toasts_toast import _short_time_formatter_ok


# #126 — safe search snippet highlight: <mark> siblings, never innerHTML of body.
# Core FTS snippets already wrap hits with «…» (see docs/user/search.md).
_SEARCH_HIGHLIGHT_HELPER = re.compile(
    r"\b(?:"
    r"splitSnippet|snippetSegments|snippetParts|highlightSnippet|highlightSegments|"
    r"markSegments|markSnippet|segmentSnippet|parseSnippet|snippetMarks|"
    r"highlightSearch|searchHighlight|ftsSnippet|splitFtsSnippet|"
    r"splitMarkers|markerSegments|wrapMarks"
    r")\b",
    re.I,
)
# Split evidence: FTS guillemet markers or a snippet-aware split / segment helper.
_SEARCH_SNIPPET_SPLIT = re.compile(
    r"("
    r"[«»]"  # core FTS snippet markers
    r"|\\u00ab|\\u00bb"  # unicode escapes
    r"|\bsplit\s*\([^)]*(?:snippet|«|»|marker)"
    r"|\.split\s*\(\s*(?:/[«»]|[\"']«|new\s+RegExp\s*\(\s*[\"']«)"
    r"|\b(?:snippetSegments|snippetParts|markSegments|highlightSegments|"
    r"segmentSnippet|splitSnippet|splitMarkers|markerSegments)\b"
    r"|\b(?:segments?|parts)\s*(?:=|:)\s*(?:splitSnippet|highlightSnippet|"
    r"snippetSegments|markSegments|segmentSnippet)\b"
    r")",
    re.I,
)
# <mark> with yellow / highlight / mark class, or bare <mark> used as the hit wrap.
_SEARCH_MARK_TAG = re.compile(r"<mark\b", re.I)
_SEARCH_MARK_STYLE = re.compile(
    r"("
    r"<mark\b[^>]{0,200}\bclass\s*=\s*[\"'][^\"']*"
    r"(?:yellow|highlight|mark|bg-yellow|bg-amber|bg-\[|search-hit|hit-mark)"
    r"|<mark\b"  # intentional <mark> (UA default is yellow-ish; class optional)
    r"|\b(?:bg-yellow-\d+|bg-amber-\d+|text-yellow|highlight|hit-mark|search-mark)\b"
    r")",
    re.I,
)
# Dangerous HTML injection on search snippet/body path.
_SEARCH_UNSAFE_HTML = re.compile(
    r"("
    r"\{@html\b"
    r"|\.innerHTML\s*="
    r"|insertAdjacentHTML\s*\("
    r"|dangerouslySetInnerHTML"
    r")",
    re.I,
)
# Building an HTML string of <mark> via replace (regex highlight → inject path).
_SEARCH_REGEX_HTML_MARK = re.compile(
    r"("
    r"\.replace\s*\([^)]{0,200},\s*[`'\"][^`'\"]*<mark\b"
    r"|replace\s*\(\s*(?:new\s+)?RegExp\b[\s\S]{0,200}<mark\b"
    r"|return\s+[`'\"][^`'\"]*<mark\b[^`'\"]*[`'\"]"  # helper returns HTML string
    r")",
    re.I,
)
# HTML mail renderer (out of scope for #126).
_SEARCH_HTML_MAIL = re.compile(
    r"("
    r"\bDOMParser\b"
    r"|\bsrcdoc\s*="
    r"|\brenderHtmlMail\b|\bhtmlMail\b|\bMimeHtml\b|\brenderMime\b"
    r"|iframe[^>]{0,80}(?:body|snippet|mail|message)"
    r")",
    re.I,
)


def _search_highlight_surface(crate: Path) -> tuple[str, str, list[Path]]:
    """SearchPane + relative snippet/highlight helpers (not CasAttach / general UI)."""
    web = crate / "web"
    lib = web / "lib"
    search_path = lib / "SearchPane.svelte"
    paths: list[Path] = []
    seen: set[Path] = set()
    if search_path.is_file():
        paths.append(search_path)
        seen.add(search_path.resolve())
        text = search_path.read_text()
        for m in re.finditer(r"""from\s+["'](\.[^"']+)["']""", text):
            rel = m.group(1)
            base = (search_path.parent / rel).resolve()
            candidates = [base]
            if not base.suffix:
                candidates.extend(
                    [
                        Path(str(base) + ".ts"),
                        Path(str(base) + ".js"),
                        Path(str(base) + ".svelte"),
                        base / "index.ts",
                        base / "index.js",
                    ]
                )
            for c in candidates:
                if not c.is_file() or c.resolve() in seen:
                    continue
                try:
                    c.relative_to(web.resolve())
                except ValueError:
                    continue
                name = c.name.lower()
                body = c.read_text()
                # Only pull helpers involved in snippet split / mark render.
                if re.search(
                    r"snippet|highlight|mark.?segment|fts.?marker|split.?marker",
                    name + "\n" + body[:4000],
                    re.I,
                ) and not re.search(
                    r"CasAttach|EmptyState|DoctorPane|ImportPane|ReviewPane",
                    c.name,
                ):
                    # Skip pure API types modules unless they define a split helper.
                    if c.name in {"api.ts", "api.js"} and not _SEARCH_HIGHLIGHT_HELPER.search(
                        body
                    ):
                        continue
                    paths.append(c)
                    seen.add(c.resolve())
    blob = "\n".join(p.read_text() for p in paths)
    cleaned = _without_comments(blob)
    return blob, cleaned, paths


# #210 — search hit rows: short time + person/title, then highlighted snippet.
_HIT_TIME_EXTRA = ("utcTime",)
_HIT_SENT_AT_NO_DATE = re.compile(
    r"""(?:h\.)?sent_at\s*\|\|\s*["']no date["']""",
    re.I,
)
_HIT_LOG_JOIN = re.compile(
    r"""\.join\s*\(\s*["']\s*·\s*["']\s*\)""",
)
_HIT_PERSON_OR_TITLE = re.compile(
    r"\b(?:person_name|personName|conversation_title|conversationTitle)\b"
)
_HIT_DENSITY_META = re.compile(
    r"\btext-xs\b|text-\[(?:12|13)px\]",
    re.I,
)
_HIT_DENSITY_SNIP = re.compile(
    r"\btext-sm\b|text-\[(?:14|15)px\]",
    re.I,
)
_HIT_DENSITY_PAD = re.compile(
    r"\b(?:py-1\.5|py-2|gap-1\.5|gap-2)\b",
    re.I,
)
_DOCS_HIT_DENSITY = re.compile(
    r"("
    r"(?:search )?hits?"
    r".{0,200}short(?:er)?(?: UTC| human)? time"
    r".{0,120}person(?:/|\s+or\s+|\s+and/?or\s+)(?:conversation )?title"
    r".{0,100}(?:highlighted )?snippet"
    r")",
    re.I | re.S,
)
_DOCS_HIT_NOT_ISO = re.compile(
    r"("
    r"(?:search )?hits?.{0,220}not (?:a |the )?raw ISO"
    r"|not (?:a |the )?raw ISO dump"
    r")",
    re.I | re.S,
)


def _hit_time_helpers() -> tuple[str, ...]:
    return _HUMAN_TIME_HELPERS + _HIT_TIME_EXTRA


def _hit_time_call_rx() -> re.Pattern[str]:
    return re.compile(r"\b(?:" + "|".join(_hit_time_helpers()) + r")\s*\(")


def _hits_each_block(markup: str) -> str:
    m = re.search(r"\{#each\s+hits\b", markup)
    if not m:
        return ""
    end = _matching_each_end(markup, m.start())
    if end < 0:
        return markup[m.start() :]
    return markup[m.start() : end]


def _interp_dumps_iso_sent_at(expr: str) -> bool:
    """True if sent_at is stringified (raw ISO), not passed to a formatter.

    Jump payload `sentAt: h.sent_at` is API, not display — ignore those.
    """
    stripped = re.sub(r"\bsentAt\s*:\s*(?:[\w.$]+\.)?sent_at\b", "", expr)
    if not re.search(r"\bsent_at\b", stripped):
        return False
    names = "|".join(_hit_time_helpers())
    if re.search(rf"\b(?:{names})\s*\([^)]*\bsent_at\b", stripped):
        return False
    return True


def _hits_uses_short_time(hits_each: str) -> bool:
    if _hit_time_call_rx().search(hits_each):
        return True
    names = "|".join(_hit_time_helpers())
    for expr in _svelte_interpolations(hits_each):
        if re.search(rf"\b(?:{names})\s*\([^)]*\bsent_at\b", expr):
            return True
    return False

__all__ = [
    "_SEARCH_JUMP_FN",
    "_SEARCH_JUMP_PROP",
    "_VIEW_PEOPLE",
    "_HIT_PERSON_ID_READ",
    "_HIT_MESSAGE_ID_READ",
    "_SEARCH_EXPAND_BODY",
    "_SEARCH_JUMP_SCROLL_HL",
    "_SEARCH_JUMP_LOAD_WINDOW",
    "_SEARCH_JUMP_CALL_RE",
    "_HIT_ACTIVATES_JUMP",
    "_JUMP_BODY_SELECTS_PERSON",
    "_JUMP_BODY_USES_MESSAGE",
    "_HIT_PERSON_GUARD",
    "_IDX_NAME",
    "_LOADED_NAME",
    "_SEARCH_JUMP_LAST_ROW_FALLBACK",
    "_SEARCH_JUMP_TLINDEX_MISS_TERNARY",
    "_SEARCH_JUMP_MISS_ERROR",
    "_search_jump_handler_bodies",
    "_assert_search_jump_miss_path",
    "_SEARCH_HIGHLIGHT_HELPER",
    "_SEARCH_SNIPPET_SPLIT",
    "_SEARCH_MARK_TAG",
    "_SEARCH_MARK_STYLE",
    "_SEARCH_UNSAFE_HTML",
    "_SEARCH_REGEX_HTML_MARK",
    "_SEARCH_HTML_MAIL",
    "_search_highlight_surface",
    "_HIT_TIME_EXTRA",
    "_HIT_SENT_AT_NO_DATE",
    "_HIT_LOG_JOIN",
    "_HIT_PERSON_OR_TITLE",
    "_HIT_DENSITY_META",
    "_HIT_DENSITY_SNIP",
    "_HIT_DENSITY_PAD",
    "_DOCS_HIT_DENSITY",
    "_DOCS_HIT_NOT_ISO",
    "_hit_time_helpers",
    "_hit_time_call_rx",
    "_hits_each_block",
    "_interp_dumps_iso_sent_at",
    "_hits_uses_short_time",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_function_body",
    "_HTML_BODY",
    "_search_pane_blob",
    "_svelte_interpolations",
    "_svelte_markup",
    "_ts_function_body",
    "_web_logic",
    "_without_comments",
    "_short_time_formatter_ok",
    "annotations",
    "_matching_each_end",
    "_HUMAN_TIME_HELPERS",
]

__all__ = [
    "_SEARCH_HIGHLIGHT_HELPER",
    "_SEARCH_SNIPPET_SPLIT",
    "_SEARCH_MARK_TAG",
    "_SEARCH_MARK_STYLE",
    "_SEARCH_UNSAFE_HTML",
    "_SEARCH_REGEX_HTML_MARK",
    "_SEARCH_HTML_MAIL",
    "_search_highlight_surface",
    "_HIT_TIME_EXTRA",
    "_HIT_SENT_AT_NO_DATE",
    "_HIT_LOG_JOIN",
    "_HIT_PERSON_OR_TITLE",
    "_HIT_DENSITY_META",
    "_HIT_DENSITY_SNIP",
    "_HIT_DENSITY_PAD",
    "_DOCS_HIT_DENSITY",
    "_DOCS_HIT_NOT_ISO",
    "_hit_time_helpers",
    "_hit_time_call_rx",
    "_hits_each_block",
    "_interp_dumps_iso_sent_at",
    "_hits_uses_short_time",
    "__all__",
]
