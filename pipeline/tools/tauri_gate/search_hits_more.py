"""Additional search_hits asserts."""
from __future__ import annotations

from tauri_gate.search_hits_jump import *
from tauri_gate.search_hits_mark import *


def assert_search_hit_density(crate: Path) -> None:
    """#210: hit rows show short time + person/title, then a highlighted snippet.

    Format `h.sent_at` with existing `humanTime` / `utcTime` (or another name
    in `_HUMAN_TIME_HELPERS`). Quiet meta is short time + person name and/or
    conversation title — not a five-field `sent_at · platform · kind · name ·
    title` dump. Snippet stays splitSnippet + <mark> text children. Keep
    #124 j/k+Enter, #126 mark path, #208 chrome search, #209 filters. Not:
    regex HTML inject, HTML mail renderer, FTS «» rewrite.
    """
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#210: SearchPane.svelte required (search hit rows live there)")
    src = _search_pane_blob(crate)
    cleaned = _without_comments(src)
    markup = _svelte_markup(src)
    surface = markup if markup.strip() else src
    hits_each = _hits_each_block(surface)
    if not hits_each.strip():
        hits_each = _hits_each_block(src)
    app_path = crate / "web" / "App.svelte"
    app = _web_logic(crate) if app_path.is_file() else ""
    logic = _web_logic(crate)
    docs_search = repo_root() / "docs" / "user" / "search.md"
    docs_app = repo_root() / "docs" / "user" / "app.md"
    dtxt = ""
    if docs_search.is_file():
        dtxt += docs_search.read_text() + "\n"
    if docs_app.is_file():
        dtxt += docs_app.read_text()

    # 1) Hits list hooks stay.
    if not re.search(r"\{#each\s+hits\b", surface) and not re.search(
        r"\{#each\s+hits\b", src
    ):
        fail("#210: SearchPane must still list hits ({#each hits})")
    if not hits_each.strip():
        fail("#210: search hits {#each hits} body missing")
    if not re.search(r"\bdata-search-hits\b", surface):
        fail("#210: keep data-search-hits on the hits list")
    if not re.search(r"\bdata-search-hit\b", hits_each):
        fail("#210: keep data-search-hit on each hit row")

    # 2) Still show sent_at — as a short time, not dropped (jump payload alone
    #    does not count; that stays API).
    if not re.search(r"\bsent_at\b", hits_each):
        fail(
            "#210: hit rows must still show sent_at "
            "(as a short time, not drop the timestamp)"
        )

    # 3) Visible hit meta is not the raw ISO T…Z string.
    raw_dump = any(
        _interp_dumps_iso_sent_at(expr) for expr in _svelte_interpolations(hits_each)
    )
    if raw_dump or _HIT_SENT_AT_NO_DATE.search(hits_each):
        fail(
            "#210: hit rows must not display raw ISO sent_at "
            "(T…Z / h.sent_at || \"no date\" in a join); "
            "use humanTime / utcTime (e.g. 11 Aug 14:32)"
        )

    # 4) Five-field log dump is gone (sent_at · platform · kind · name · title).
    if _hits_meta_is_five_field_log(hits_each):
        fail(
            "#210: hit meta must not join sent_at with platform and "
            "conversation_kind as one ` · ` log line; quiet meta is "
            "short time + person/title, then the snippet"
        )

    # 5) A formatter exists and the hit row actually calls it.
    if not _short_time_formatter_ok(logic):
        fail(
            "#210: format sent_at as a short UTC time "
            "(e.g. 11 Aug 14:32) — month + hour:minute, not YYYY-MM-DDTHH:MM:SSZ"
        )
    if not _hits_uses_short_time(hits_each):
        fail(
            "#210: hit meta must pass sent_at through a short-time helper "
            "(humanTime / utcTime / another name in _HUMAN_TIME_HELPERS), "
            "not interpolate the ISO"
        )

    # 6) Person name and/or conversation title stay on the row.
    if not _HIT_PERSON_OR_TITLE.search(hits_each):
        fail(
            "#210: hit rows must show a person name and/or conversation title "
            "(quiet meta is short time + person/title)"
        )

    # 7) Snippet stays splitSnippet + <mark> text children (#126).
    if not re.search(r"\bsplitSnippet\b", hits_each + "\n" + cleaned):
        fail(
            "#210: keep splitSnippet (or the existing #126 helper) so the "
            "snippet is text + <mark> siblings"
        )
    if not _SEARCH_MARK_TAG.search(hits_each):
        fail(
            "#210: keep <mark> text children on the snippet path "
            "(no {@html} / innerHTML of snippet or body)"
        )
    if re.search(
        r"<mark\b[^>]*>\s*\{(?:\(?\s*)?(?:h\.)?snippet\b[^}]{0,120}\}\s*</mark>",
        hits_each,
        re.I,
    ) and not re.search(r"\{#each\s+", hits_each):
        fail(
            "#210: do not wrap the entire raw snippet in one <mark> — "
            "keep splitSnippet + text / <mark> siblings"
        )

    # 8) No {@html} / innerHTML / regex HTML inject / HTML mail on search path.
    blob = hits_each + "\n" + cleaned
    if _SEARCH_UNSAFE_HTML.search(blob) or _SEARCH_UNSAFE_HTML.search(surface):
        unsafe = re.search(
            r"(?:snippet|body_text|searchBody|\bbody\b|highlight|mark)[\s\S]{0,160}"
            r"(?:\{@html\b|\.innerHTML\s*=|insertAdjacentHTML\s*\()"
            r"|(?:\{@html\b|\.innerHTML\s*=|insertAdjacentHTML\s*\()[\s\S]{0,160}"
            r"(?:snippet|body_text|searchBody|\bbody\b|highlight)",
            blob,
            re.I,
        )
        bare_html = _HTML_BODY.search(blob) or re.search(r"\.innerHTML\s*=", blob)
        if unsafe or bare_html:
            fail(
                "#210: never assign innerHTML / {@html on the search snippet or "
                "body path (a body containing <script> must stay text)"
            )
    if re.search(r"\{@html\s+(?:body|body_text|snippet)\b", blob):
        fail(
            "#210: expanded search body / snippet must stay text-safe — "
            "no {@html body} / {@html snippet}"
        )
    if _SEARCH_REGEX_HTML_MARK.search(blob):
        fail(
            "#210: not in scope — regex highlight that builds HTML mark strings "
            "(no FTS marker rewrite; use text + <mark> siblings)"
        )
    if _SEARCH_HTML_MAIL.search(blob):
        fail(
            "#210: not in scope — HTML mail renderer "
            "(DOMParser / srcdoc / htmlMail on search path)"
        )

    # 9) j/k (or arrows) + Enter/Space still activateHit (#124).
    hits_key = _ts_function_body(src, "onHitsKey") or _function_body(src, "onHitsKey")
    if not hits_key:
        fail("#210: keep onHitsKey (#124) — j/k + Enter jump")
    if not re.search(r"""["']j["']""", hits_key) and not re.search(
        r"ArrowDown", hits_key
    ):
        fail("#210: onHitsKey must still handle j / ArrowDown")
    if not re.search(r"""["']k["']""", hits_key) and not re.search(
        r"ArrowUp", hits_key
    ):
        fail("#210: onHitsKey must still handle k / ArrowUp")
    if not re.search(r"""["']Enter["']""", hits_key) and not re.search(
        r"""["'] ["']""", hits_key
    ):
        fail("#210: onHitsKey must still handle Enter / Space → activateHit")
    if not re.search(r"\bactivateHit\b", hits_key):
        fail("#210: onHitsKey Enter / Space must still call activateHit (#124)")

    # 10) Jump payload still carries ISO sent_at (API, not display).
    act = _ts_function_body(src, "activateHit") or _function_body(src, "activateHit")
    if act and not re.search(r"sentAt\s*:\s*(?:h\.)?sent_at\b", act):
        fail(
            "#210: keep sentAt: h.sent_at on the jump payload — "
            "that is API, not display (do not drop the ISO field)"
        )

    # 11) Light people-list density (do not over-constrain Tailwind).
    if not _HIT_DENSITY_META.search(hits_each):
        fail(
            "#210: hit meta should stay people-list scale "
            "(text-xs / 12–13px), not giant cards"
        )
    if not _HIT_DENSITY_SNIP.search(hits_each):
        fail(
            "#210: hit snippet should stay people-list scale "
            "(text-sm / 14–15px)"
        )
    if not _HIT_DENSITY_PAD.search(hits_each):
        fail(
            "#210: hit rows should stay tight (py-2 / gap-2), not giant cards"
        )

    # 12) Do not soften #121–#126 / #205 / #208 / #209.
    if not re.search(r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""", surface):
        fail("#210: keep id=\"q\" as the canonical query field (#208 / #209)")
    if not re.search(r"\bdata-search-filters\b", surface):
        fail("#210: keep data-search-filters (#209)")
    if not re.search(r"\bdata-chrome-search\b", app):
        fail("#210: keep chrome search field data-chrome-search (#208)")
    if re.search(r"\bapi\.search\s*\(", app_path.read_text() if app_path.is_file() else ""):
        fail(
            "#210: App.svelte must not call api.search — SearchPane run() stays "
            "the only caller (#208)"
        )
    if not re.search(r"data-person-picker|personFilter|personId", cleaned):
        fail("#210: keep the search person picker (#123)")
    if not re.search(r"\bdata-partial\b", surface):
        fail("#210: keep search data-partial Error+Retry (#205)")

    # 13) Docs (D24): short time + person/title, then highlighted snippet.
    if not _DOCS_HIT_DENSITY.search(dtxt):
        fail(
            "#210: docs/user/search.md and/or docs/user/app.md must say "
            "search hits show a short time + person/title, then a "
            "highlighted snippet"
        )
    if not _DOCS_HIT_NOT_ISO.search(dtxt):
        fail(
            "#210: docs/user/search.md and/or docs/user/app.md must say "
            "search hits are not a raw ISO dump"
        )
