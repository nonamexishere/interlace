"""Design-token / motion / a11y chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    CSP,
    _A11Y_ROLE_LISTBOX,
    _A11Y_ROLE_OPTION,
    _A11Y_TABINDEX_NEG,
    _APPEARANCE_DOCS_ARCHIVAL,
    _APPEARANCE_DOCS_NO_THEME,
    _APPEARANCE_FETCH,
    _APPEARANCE_MENU_LABEL,
    _APPEARANCE_SCRIM_NAMES,
    _APPEARANCE_THEME_UI,
    _BODY_T_CALL,
    _BUBBLE_ME_VARS,
    _BUBBLE_THEM_VARS,
    _CDN_HINT,
    _CMD_PALETTE_PKG,
    _CONTRAST_COLOR_SCHEME,
    _CONTRAST_DOCS_SYSTEM,
    _CONTRAST_SEARCH_MARK_NAMES,
    _DOCS_TYPO_NO_REMOTE_FONT,
    _HUE_AMBER,
    _HUE_YELLOW,
    _INSPECTOR_HOOK,
    _MOTION_DURATION_ZERO,
    _MOTION_JS_REDUCE,
    _NET_IMG,
    _PALETTE_HOOK,
    _PEOPLE_EACH,
    _PRE_WRAP,
    _SECOND_UI_KIT,
    _SERVER_PROGRESS,
    _SKELETON_HOOK,
    _SPINNER_NAME,
    _SPIN_ANIM,
    _SPLASH_VIDEO,
    _STATUS_CELEBRATION,
    _STATUS_CONFETTI,
    _STATUS_GRADIENT,
    _STATUS_WARNING_NAMES,
    _THEME_CDN,
    _TOAST_SONNER_PKG,
    _TYPO_FONT_SANS,
    _TYPO_REMOTE_FONT,
    _VOID_HTML,
    _ancestor_tags,
    _appearance_class_names,
    _boot_opening_block,
    _chrome_en_text,
    _chrome_helper_names,
    _chrome_helper_on_body,
    _cond_code,
    _contrast_dark_blob,
    _contrast_light_blob,
    _contrast_surface_tag,
    _css_brace_body,
    _css_var,
    _css_without_comments,
    _empty_state_blocks,
    _function_body,
    _has_css_spinner,
    _hsl_tuple,
    _hue_findings,
    _hue_surface,
    _ident_negated,
    _markup_open_tag,
    _motion_js_blob,
    _open_tag_around,
    _open_tag_before,
    _owned_imported_names,
    _owned_skeleton_names,
    _people_each_block,
    _people_inflight_branch,
    _people_list_a11y_surfaces,
    _people_sidebar_regions,
    _product_svelte,
    _skeleton_hook_positions,
    _status_hook_blob,
    _strip_html_comments,
    _svelte_if_true_branch,
    _svelte_markup,
    _tag_name,
    _template_stack,
    _timeline_block,
    _typo_docs_blob,
    _web_chrome_blob,
    _web_logic,
    _web_sources,
    _without_comments,
)


_A11Y_ROLE_LIST = re.compile(r"\brole\s*=\s*[\"']list[\"']", re.I)
_A11Y_ACTIVEDESC = re.compile(r"\baria-activedescendant\s*=", re.I)
_A11Y_SELECTED = re.compile(r"\baria-selected\s*=", re.I)
_A11Y_SELECTED_STATE = re.compile(
    r"aria-selected\s*=\s*\{[^}]{0,120}"
    r"(?:selectedId|selected_id|selectedPerson|p\.id|person\.id)",
    re.I,
)
_A11Y_ARTICLE = re.compile(r"<article\b|\brole\s*=\s*[\"']article[\"']", re.I)
_A11Y_ARIA_LABEL = re.compile(r"\baria-label(?:ledby)?\s*=", re.I)
_A11Y_FOCUS_VISIBLE = re.compile(
    r"("
    r"focus-visible:(?:ring|outline)"
    r"|:focus-visible\b"
    r")",
    re.I,
)
_A11Y_REDUCED_MOTION = re.compile(
    r"@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)",
    re.I,
)
_A11Y_MOTION_REDUCE_TW = re.compile(r"\bmotion-reduce:", re.I)
_A11Y_ANIM_NONE = re.compile(
    r"("
    r"animation\s*:\s*none\b"
    r"|animation-duration\s*:\s*0(?:s|ms|px)?\b"
    r"|animate-none\b"
    r"|motion-reduce:animate-none\b"
    r")",
    re.I,
)
_A11Y_TRANS_NONE = re.compile(
    r"("
    r"transition\s*:\s*none\b"
    r"|transition-duration\s*:\s*0(?:s|ms)?\b"
    r"|transition-none\b"
    r"|motion-reduce:transition-none\b"
    r")",
    re.I,
)
_A11Y_SCROLL_AUTO = re.compile(
    r"("
    r"scroll-behavior\s*:\s*auto\b"
    r"|scroll-auto\b"
    r"|motion-reduce:scroll-auto\b"
    r")",
    re.I,
)
_A11Y_WCAG_CERT = re.compile(
    r"("
    r"WCAG.{0,80}(?:certificate|certified|conformance\s+certificate)"
    r"|(?:full|complete|official)\s+WCAG\s+(?:2\.[0-2]\s+)?(?:audit\s+)?certificate"
    r"|WCAG\s*2\.[0-2].{0,40}(?:AAA|AA).{0,40}(?:certified|certificate)"
    r"|certified\s+WCAG"
    r")",
    re.I,
)
_A11Y_INERT = re.compile(r"(?:\s|/|\{)\binert\b", re.I)
_A11Y_PERSON_ID_LABEL = re.compile(
    r"aria-label\s*=\s*\{[^}]{0,80}"
    r"(?:person_id|personId|selectedId|\bp\.id\b|\bperson\.id\b|(?:item\.)?row\.id)"
    r"[^}]*\}",
    re.I,
)
_A11Y_NAME_IN_LABEL = re.compile(
    r"aria-label\s*=\s*\{[^}]{0,160}"
    r"(?:display_name|displayName|sent_at|body_text|displayBody|utcTime|subject|preview)"
    r"[^}]*\}",
    re.I,
)


def _css_prefers_reduced_blocks(blob: str) -> list[str]:
    """Bodies of `@media (prefers-reduced-motion: reduce) { … }` (nested braces)."""
    out: list[str] = []
    for m in _A11Y_REDUCED_MOTION.finditer(blob):
        brace = blob.find("{", m.end() - 1)
        if brace < 0:
            continue
        depth = 0
        j = brace
        while j < len(blob):
            c = blob[j]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    out.append(blob[brace + 1 : j])
                    break
            j += 1
    return out


def _css_focus_visible_for(css: str, tokens: tuple[str, ...]) -> bool:
    """True when a :focus-visible rule's selector mentions one of tokens."""
    for m in re.finditer(r"([^{}@][^{]*)\{([^{}]*)\}", css):
        sel, body = m.group(1), m.group(2)
        if ":focus-visible" not in sel and "focus-visible" not in body:
            continue
        low = sel.lower()
        if any(tok.lower() in low for tok in tokens):
            return True
    return False


def assert_a11y_listbox_focus_motion(crate: Path) -> None:
    """#133: people listbox, timeline article/label, focus rings, reduced motion.

    VoiceOver can move through people and hear the selected name. Tab order is
    not a trap. Not a full WCAG audit / certificate.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#133: App.svelte required (people list + timeline a11y)")
    app = app_path.read_text()
    markup = _strip_html_comments(_svelte_markup(app))
    chrome, people_each = _people_list_a11y_surfaces(crate)
    if not chrome.strip():
        chrome = markup
    if not people_each.strip():
        people_each = _people_each_block(markup)
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = search_path.read_text() if search_path.is_file() else ""
    css_blob = _css_without_comments(
        "\n".join(p.read_text() for p in _web_sources(crate) if p.suffix == ".css")
    )
    index_html = ""
    index_path = crate / "index.html"
    if index_path.is_file():
        index_html = _css_without_comments(index_path.read_text())
    button_src = ""
    button_path = (
        crate / "web" / "lib" / "components" / "ui" / "button" / "button.svelte"
    )
    if button_path.is_file():
        button_src = button_path.read_text()
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    docs_blob = ""
    docs_root = repo_root() / "docs"
    if docs_root.is_dir():
        docs_blob = "\n".join(
            p.read_text()
            for p in sorted(docs_root.rglob("*.md"))
            if p.is_file()
        )
    readme = repo_root() / "README.md"
    if readme.is_file():
        docs_blob += "\n" + readme.read_text()
    tl_block = _timeline_block(crate)
    boot = _boot_opening_block(app)

    # 1) People list: listbox + option, or list + aria-activedescendant.
    #    Prefer this as the pre-impl red — today is <ul><li><button> with neither.
    if not _PEOPLE_EACH.search(markup) and not _PEOPLE_EACH.search(chrome):
        fail(
            "#133: people sidebar must still {#each filtered …} "
            "(listbox/option wraps that list, not SearchPane)"
        )
    has_listbox = bool(_A11Y_ROLE_LISTBOX.search(chrome))
    has_option = bool(_A11Y_ROLE_OPTION.search(people_each) or _A11Y_ROLE_OPTION.search(chrome))
    has_activedesc = bool(_A11Y_ACTIVEDESC.search(chrome))
    has_list = bool(
        _A11Y_ROLE_LIST.search(chrome)
        or re.search(r"<ul\b|<ol\b", chrome, re.I)
    )
    listbox_pattern = has_listbox and has_option
    activedesc_pattern = has_list and has_activedesc
    if not listbox_pattern and not activedesc_pattern:
        fail(
            "#133: people list must be role=\"listbox\" + role=\"option\" "
            "(or a list + aria-activedescendant). "
            "Today's <ul><li><button> is not a listbox — VoiceOver cannot "
            "move through people as options and hear the selected name"
        )
    if has_listbox and not has_option and not has_activedesc:
        fail(
            "#133: people listbox must have role=\"option\" on each person "
            "(or aria-activedescendant pointing at the active option)"
        )

    # 2) aria-selected on the selected person (VoiceOver hears selected name).
    if not _A11Y_SELECTED.search(people_each) and not _A11Y_SELECTED.search(chrome):
        fail(
            "#133: selected person must set aria-selected "
            "(VoiceOver hears the selected name — bind to selectedId === p.id)"
        )
    if not _A11Y_SELECTED_STATE.search(people_each) and not _A11Y_SELECTED_STATE.search(
        chrome
    ):
        fail(
            "#133: aria-selected must follow the selected person "
            "(selectedId === p.id / equivalent), not a constant true"
        )
    if not re.search(r"\bdisplay_name\b", people_each):
        fail(
            "#133: people options must expose display_name "
            "(VoiceOver hears the selected name; not a raw person id)"
        )
    if _A11Y_PERSON_ID_LABEL.search(people_each) and not _A11Y_NAME_IN_LABEL.search(
        people_each
    ):
        fail(
            "#133: people option accessible name must be the display name, "
            "not a raw person id"
        )

    # 3) Timeline message rows: <article> and/or aria-label — not a bare clickable div.
    #    Accessible name is time + preview/snippet, never a raw person id.
    has_article = bool(_A11Y_ARTICLE.search(tl_block))
    has_row_label = bool(_A11Y_ARIA_LABEL.search(tl_block))
    if not has_article and not has_row_label:
        fail(
            "#133: timeline message rows must be <article> (or role=\"article\") "
            "and/or have an accessible name (aria-label) — not a raw clickable <div>"
        )
    # Article must sit on the message (time / body / data-tl-index), not only .day-heading.
    if has_article:
        article_on_row = bool(
            re.search(
                r"<article\b[^>]{0,500}(?:data-tl-index|data-from-me|body_text|displayBody)",
                tl_block,
                re.I | re.S,
            )
            or re.search(
                r"(?:data-tl-index|data-from-me).{0,240}<article\b",
                tl_block,
                re.I | re.S,
            )
            or re.search(
                r"<article\b.{0,900}(?:<time\b|body_text|displayBody|whitespace-pre-wrap)",
                tl_block,
                re.I | re.S,
            )
        )
        if not article_on_row:
            fail(
                "#133: <article> must be the message row (time + body / snippet), "
                "not only a day heading"
            )
    if _A11Y_PERSON_ID_LABEL.search(tl_block) and not _A11Y_NAME_IN_LABEL.search(tl_block):
        fail(
            "#133: timeline accessible name must be time + preview/snippet, "
            "not a raw person id"
        )

    # 4) Visible focus rings on people options and timeline rows (not only j/k ring-2).
    people_surface = chrome + "\n" + people_each
    people_focus = bool(_A11Y_FOCUS_VISIBLE.search(people_surface))
    if not people_focus and re.search(r"<Button\b", people_each) and _A11Y_FOCUS_VISIBLE.search(
        button_src
    ):
        people_focus = True
    if not people_focus:
        people_focus = _css_focus_visible_for(
            css_blob,
            (
                "[role='option']",
                '[role="option"]',
                "[role=option]",
                "listbox",
                "people-option",
                "person-option",
                "data-people-sidebar",
            ),
        )
    if not people_focus:
        fail(
            "#133: people options need a visible focus-visible ring "
            "(focus-visible:ring / :focus-visible) — browser default outline "
            "on a raw <button> is not enough; j/k selection ring is not focus"
        )
    tl_focus = bool(_A11Y_FOCUS_VISIBLE.search(tl_block))
    if not tl_focus:
        tl_focus = _css_focus_visible_for(
            css_blob,
            (
                "article",
                "[role='article']",
                '[role="article"]',
                "timeline",
                "data-tl-index",
                "bubble-me",
                "bubble-them",
            ),
        )
    if not tl_focus:
        fail(
            "#133: timeline message rows need a visible focus-visible ring "
            "(focus-visible:ring on the article) — the j/k ring-2 highlight "
            "is selection, not keyboard focus"
        )
    if button_src and not _A11Y_FOCUS_VISIBLE.search(button_src):
        fail(
            "#133: nav Button primitive must keep focus-visible:ring "
            "(do not drop visible focus on chrome)"
        )

    # 5) prefers-reduced-motion: disable spin / animation / transitions; scroll auto.
    #    Sticky .day-heading has no animation today — still wrap transitions.
    reduce_css = "\n".join(_css_prefers_reduced_blocks(css_blob))
    reduce_html = "\n".join(_css_prefers_reduced_blocks(index_html))
    reduce_all = reduce_css + "\n" + reduce_html
    has_reduce_media = bool(reduce_css.strip() or reduce_html.strip())
    has_motion_tw = bool(
        _A11Y_MOTION_REDUCE_TW.search(app)
        or _A11Y_MOTION_REDUCE_TW.search(boot)
        or _A11Y_MOTION_REDUCE_TW.search(css_blob)
    )
    if not has_reduce_media and not has_motion_tw:
        fail(
            "#133: must honor prefers-reduced-motion "
            "(@media (prefers-reduced-motion: reduce) in CSS, or Tailwind "
            "motion-reduce) — disable spin / animation / sticky-date animation"
        )
    if not _A11Y_ANIM_NONE.search(reduce_all) and not _A11Y_ANIM_NONE.search(app) and not (
        has_motion_tw and re.search(r"motion-reduce:animate-none", app + "\n" + boot + "\n" + css_blob)
    ):
        fail(
            "#133: prefers-reduced-motion must disable animation "
            "(animation: none / animate-none / motion-reduce:animate-none) "
            "so the boot spinner does not spin"
        )
    if not _A11Y_TRANS_NONE.search(reduce_all) and not re.search(
        r"motion-reduce:transition-none", app + "\n" + css_blob
    ):
        fail(
            "#133: prefers-reduced-motion must disable or zero transitions "
            "(transition: none / motion-reduce:transition-none) — including "
            "any sticky-date animation"
        )
    if not _A11Y_SCROLL_AUTO.search(reduce_all) and not re.search(
        r"motion-reduce:scroll-auto", app + "\n" + css_blob
    ):
        fail(
            "#133: prefers-reduced-motion must set scroll-behavior: auto "
            "(or motion-reduce:scroll-auto)"
        )
    # Pre-JS splash spinner is inline in index.html — app.css cannot stop it.
    if _SPIN_ANIM.search(index_html) and not _A11Y_ANIM_NONE.search(reduce_html):
        fail(
            "#133: index.html boot spinner must honor prefers-reduced-motion "
            "(disable boot-spin / animation under reduce — app.css does not apply pre-JS)"
        )
    if re.search(r"animate-spin", boot) or re.search(r"animate-spin", app):
        covered = bool(
            re.search(r"motion-reduce:animate-none", boot)
            or re.search(r"motion-reduce:animate-none", app)
            or _A11Y_ANIM_NONE.search(reduce_css)
        )
        if not covered:
            fail(
                "#133: Opening-last-archive animate-spin must stop under "
                "prefers-reduced-motion (motion-reduce:animate-none or "
                "animation: none in the reduce media query)"
            )

    # 6) Keep the existing SearchPane person-picker listbox (do not steal it).
    if not search_path.is_file():
        fail("#133: SearchPane.svelte required (keep its listbox/option picker)")
    search_markup = _strip_html_comments(_svelte_markup(search))
    if not _A11Y_ROLE_LISTBOX.search(search) and not _A11Y_ROLE_LISTBOX.search(search_markup):
        fail(
            "#133: keep SearchPane's existing role=\"listbox\" "
            "(people sidebar is a second listbox; do not remove the picker)"
        )
    if not _A11Y_ROLE_OPTION.search(search) and not _A11Y_ROLE_OPTION.search(search_markup):
        fail(
            "#133: keep SearchPane's existing role=\"option\" on person picker rows"
        )

    # 7) Ban claiming a WCAG audit certificate (out of scope).
    if _A11Y_WCAG_CERT.search(docs_blob) or _A11Y_WCAG_CERT.search(dtxt):
        fail(
            "#133: do not claim a WCAG certificate / certified audit in docs "
            "(this issue is listbox + focus + reduced motion, not a full audit)"
        )

    # 8) Tab order is not a trap: filter → people options → timeline/chrome.
    #    Lightbox/dialogs may trap (already). Do not inert the people+timeline grid.
    grid_tag = _open_tag_around(
        markup,
        r"grid-cols-\[minmax\(0,18rem\)_minmax\(0,1fr\)\]",
    )
    if not grid_tag:
        grid_tag = _open_tag_around(markup, r"data-people-sidebar")
    sidebar_tag = _open_tag_around(markup, r"data-people-sidebar")
    timeline_tag = _open_tag_around(markup, r"id=[\"']person-timeline[\"']")
    for tag, where in (
        (grid_tag, "people+timeline grid"),
        (sidebar_tag, "people sidebar"),
        (timeline_tag, "person timeline"),
    ):
        if tag and _A11Y_INERT.search(tag):
            fail(
                f"#133: do not put inert on the {where} "
                "(tab order must reach people filter → people options → timeline; "
                "dialogs/lightbox may still trap)"
            )
    filter_win = ""
    fm = re.search(r"id=[\"']person-filter[\"']", markup)
    if fm:
        filter_win = markup[max(0, fm.start() - 160) : fm.end() + 160]
    if filter_win and _A11Y_TABINDEX_NEG.search(filter_win):
        fail(
            "#133: #person-filter must stay in tab order "
            "(do not tabindex=\"-1\" the people filter)"
        )
    # tabindex="-1" on every person skips the list unless the listbox uses
    # aria-activedescendant (roving focus stays on the listbox).
    if _A11Y_TABINDEX_NEG.search(people_each) and not has_activedesc:
        dynamic_tab = bool(re.search(r"tabindex\s*=\s*\{", people_each))
        if not dynamic_tab:
            fail(
                "#133: do not tabindex=\"-1\" every person "
                "(that skips the list). Use listbox + options in tab order, "
                "or roving tabindex with aria-activedescendant"
            )

    # 9) User-visible: one line in docs (keyboard + VoiceOver). Not a certificate.
    if not dtxt.strip():
        fail("#133: docs/user/app.md required (VoiceOver / people list; not a WCAG certificate)")
    if not re.search(r"VoiceOver", dtxt):
        fail(
            "#133: docs/user/app.md must mention VoiceOver on the people list "
            "(hear the selected name; keyboard tab order) — not a WCAG certificate"
        )
_HEAVY_SHADOW = re.compile(r"(?<![\w-])shadow-(?:lg|xl|2xl)\b")
_GRADIENT = re.compile(
    r"("
    r"(?<![\w-])bg-gradient-"
    r"|(?<![\w-])(?:from|to|via)-(?:"
    r"zinc|slate|gray|neutral|stone|red|orange|amber|yellow|lime|green|"
    r"emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|"
    r"black|white|transparent|current|inherit"
    r")"
    r")",
)
_NEW_BRAND_VAR = re.compile(r"--(?:color-)?brand\b|--palette-")
_SQL_DDL = re.compile(r"""['\"][^'\"]*\b(?:ALTER|CREATE)\s+TABLE\b""", re.I)
_DOCS_DESIGN_TOKENS = re.compile(
    r"("
    r"(?:design tokens?|CSS variables?).{0,260}(?:chrome|colou?rs?|hues?)"
    r"|(?:chrome|colou?rs?|hues?).{0,260}(?:design tokens?|CSS variables?)"
    r")",
    re.I | re.S,
)
_DOCS_NOT_RAW_HUES = re.compile(
    r"("
    r"not raw (?:Tailwind )?hues?"
    r"|not (?:a |the )?raw Tailwind hues?"
    r"|not raw Tailwind"
    r"|CSS variables?, not raw"
    r"|design tokens?, not raw"
    r")",
    re.I,
)
_SHADCN_TOKEN_DEFS = (
    "--color-background",
    "--color-foreground",
    "--color-muted-foreground",
    "--color-border",
    "--color-destructive",
)
_SHADCN_TOKEN_USES = (
    "bg-background",
    "text-foreground",
    "text-muted-foreground",
    "border-border",
)


def _token_hits(crate: Path, files: list[Path], rx: re.Pattern[str]) -> list[str]:
    hits: list[str] = []
    for p in files:
        found = sorted({m.group(0) for m in rx.finditer(_hue_surface(p.read_text()))})
        if found:
            hits.append(f"{p.relative_to(crate)}: {', '.join(found)}")
    return hits


def assert_design_tokens(crate: Path) -> None:
    """#198: product Svelte chrome uses existing tokens, not raw hues.

    No hex / amber-* / yellow-* / black/80 in web/**/*.svelte (defs may stay
    in app.css). Map chrome onto existing shadcn names (background, foreground,
    muted-foreground, border, destructive) plus --bubble-me / --bubble-them.
    Bubbles stay distinct. No new brand palette, gradients, CDN theme, or
    stored-data rewrite. Do not require --warning / --success (#219). Keep
    <mark> highlight chrome (#126). Docs: tokens / CSS variables, not raw hues.
    """
    svelte_files = _product_svelte(crate)
    if not svelte_files:
        fail("#198: crates/interlace-tauri/web/**/*.svelte required (token chrome)")

    # 1) Hard acceptance: no raw hues in product Svelte (first fail on master).
    offenders: list[str] = []
    for p in svelte_files:
        hits = _hue_findings(p.read_text())
        if hits:
            offenders.append(f"{p.relative_to(crate)}: {'; '.join(hits)}")
    if offenders:
        fail(
            "#198: product Svelte must not contain hex / amber-* / yellow-* / "
            "black/80 (token definitions may live in app.css only). Found:\n  "
            + "\n  ".join(offenders)
        )

    css_path = crate / "web" / "app.css"
    if not css_path.is_file():
        fail("#198: web/app.css required (shadcn + bubble token definitions)")
    css = css_path.read_text()

    # 2) Existing shadcn token names still defined in app.css.
    missing_defs = [name for name in _SHADCN_TOKEN_DEFS if name not in css]
    if missing_defs:
        fail(
            "#198: app.css must keep existing shadcn tokens "
            f"({', '.join(missing_defs)} missing) — do not invent a new brand palette"
        )

    # 3) Bubbles stay distinct via existing --bubble-me / --bubble-them
    #    (or --color-bubble-*). Do not soften #111.
    me = _css_var(css, _BUBBLE_ME_VARS)
    them = _css_var(css, _BUBBLE_THEM_VARS)
    if not me or not them:
        fail(
            "#198: keep distinct bubble tokens --bubble-me / --bubble-them "
            "(or --color-bubble-*) in app.css"
        )
    if me == them:
        fail("#198: --bubble-me and --bubble-them must stay distinct colors")

    svelte_blob = "\n".join(p.read_text() for p in svelte_files)

    # 4) Product Svelte uses token / variable classes, not raw hues.
    missing_uses = [tok for tok in _SHADCN_TOKEN_USES if tok not in svelte_blob]
    if missing_uses:
        fail(
            "#198: product Svelte must use existing token/variable classes "
            f"({', '.join(missing_uses)} missing) rather than raw hues"
        )

    # 5) Targeted shadow language (not a full Tailwind linter; p-1 leftovers OK).
    shadow_hits = _token_hits(crate, svelte_files, _HEAVY_SHADOW)
    if shadow_hits:
        fail(
            "#198: product Svelte shadows must be shadow-sm / shadow-md only "
            "(no shadow-lg / shadow-xl / shadow-2xl). Found:\n  "
            + "\n  ".join(shadow_hits)
        )

    # 6) Not: gradients / new brand palette / CDN theme.
    gradient_hits = _token_hits(crate, svelte_files, _GRADIENT)
    if gradient_hits:
        fail(
            "#198: not in scope — no gradients (bg-gradient-* / from-* / to-* "
            "hero) in product Svelte. Found:\n  " + "\n  ".join(gradient_hits)
        )
    if _NEW_BRAND_VAR.search(css) or _NEW_BRAND_VAR.search(svelte_blob):
        fail(
            "#198: not in scope — no new brand palette "
            "(keep existing shadcn + bubble vars; do not add --brand)"
        )
    cdn_blob = svelte_blob + "\n" + css
    splash = crate / "index.html"
    if splash.is_file():
        cdn_blob += "\n" + splash.read_text()
    if _THEME_CDN.search(cdn_blob):
        fail(
            "#198: not in scope — no CDN theme "
            "(fonts.googleapis / cdn. / remote @import of a theme)"
        )

    # 7) Not: changing stored data (no SQLite migration / timestamp rewrite).
    rust_blob = ""
    src_dir = crate / "src"
    if src_dir.is_dir():
        rust_blob = "\n".join(p.read_text() for p in sorted(src_dir.rglob("*.rs")))
    api_path = crate / "web" / "lib" / "api.ts"
    api = api_path.read_text() if api_path.is_file() else ""
    if _SQL_DDL.search(rust_blob) or _SQL_DDL.search(svelte_blob) or _SQL_DDL.search(api):
        fail(
            "#198: not in scope — no SQLite migration / stored-data change "
            "(do not ALTER/CREATE TABLE from Tauri chrome)"
        )
    if api and not re.search(
        r"export type Person\s*=\s*\{[^}]*\blast_activity_at\??\s*:\s*string",
        api,
        re.S,
    ):
        fail(
            "#198: not in scope — do not rewrite last_activity_at / message "
            "timestamps (Person.last_activity_at stays ISO string on the API)"
        )

    # 8) D24: chrome colors come from design tokens / CSS variables, not raw hues.
    user_docs = repo_root() / "docs" / "user" / "app.md"
    hack_docs = repo_root() / "docs" / "hacking" / "tauri.md"
    dtxt = ""
    if user_docs.is_file():
        dtxt += user_docs.read_text()
    if hack_docs.is_file():
        dtxt += "\n" + hack_docs.read_text()
    if not dtxt.strip():
        fail(
            "#198: docs/user/app.md (and/or docs/hacking/tauri.md) required "
            "(chrome colors from design tokens / CSS variables)"
        )
    if not _DOCS_DESIGN_TOKENS.search(dtxt):
        fail(
            "#198: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "chrome colors come from design tokens / CSS variables"
        )
    if not _DOCS_NOT_RAW_HUES.search(dtxt):
        fail(
            "#198: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "chrome colors are not raw Tailwind hues"
        )


# #199 — typography: 14–15px bodies, 12–13px meta, system font, no remote font.
_TYPO_BODY_TW = re.compile(
    r"(?<![\w-])(text-sm|text-base|text-\[(?:14|15)(?:\.\d+)?px\])(?![\w-])"
)
_TYPO_META_TW = re.compile(
    r"(?<![\w-])(text-xs|text-\[(?:12|13)(?:\.\d+)?px\])(?![\w-])"
)
_TYPO_LEADING_NAMED = re.compile(
    r"(?<![\w-])(?:leading-normal|leading-relaxed)(?![\w-])"
)
_TYPO_LEADING_ARB = re.compile(r"(?<![\w-])leading-\[([^\]]+)\]")
_TYPO_LINE_HEIGHT = re.compile(r"line-height\s*:\s*([^;}]+)", re.I)
_TYPO_FONT_SIZE = re.compile(r"font-size\s*:\s*([^;}]+)", re.I)
_TYPO_GIANT = re.compile(
    r"(?<![\w-])text-(?:3xl|4xl|5xl|6xl|7xl|8xl|9xl)(?![\w-])"
)
_TYPO_MUTED = re.compile(
    r"("
    r"text-muted-foreground"
    r"|text-\[var\(--(?:color-)?muted-foreground\)\]"
    r"|var\(--(?:color-)?muted-foreground\)"
    r")"
)
_DOCS_TYPO_BODY = re.compile(
    r"("
    r"14\s*[–\-]\s*15\s*px"
    r"|(?:message )?bod(?:y|ies).{0,80}\bsizes?\b"
    r")",
    re.I,
)
_DOCS_TYPO_META = re.compile(
    r"("
    r"12\s*[–\-]\s*13\s*px"
    r"|\bmeta\b.{0,80}\bsizes?\b"
    r")",
    re.I,
)


def _typo_tag_class(attrs: str) -> str:
    m = re.search(r"\bclass\s*=\s*\"([^\"]*)\"", attrs)
    if m:
        return m.group(1)
    m = re.search(r"\bclass\s*=\s*'([^']*)'", attrs)
    if m:
        return m.group(1)
    m = re.search(r"\bclass\s*=\s*\{([^}]*)\}", attrs)
    if not m:
        return ""
    inner = m.group(1).strip()
    if len(inner) >= 2 and inner[0] == inner[-1] and inner[0] in "'\"`":
        return inner[1:-1]
    return "{" + inner + "}"


def _typo_tag_style(attrs: str) -> str:
    m = re.search(r"\bstyle\s*=\s*\"([^\"]*)\"", attrs)
    if m:
        return m.group(1)
    m = re.search(r"\bstyle\s*=\s*'([^']*)'", attrs)
    return m.group(1) if m else ""


def _typo_resolve_class(class_str: str, logic: str) -> str:
    parts = [class_str]
    for m in re.finditer(r"\{([A-Za-z_]\w*)\}", class_str):
        name = m.group(1)
        am = re.search(
            rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*[\"']([^\"']+)[\"']",
            logic,
        )
        if am:
            parts.append(am.group(1))
        am = re.search(
            rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*`([^`]+)`",
            logic,
        )
        if am:
            parts.append(am.group(1))
    return " ".join(parts)


def _typo_classes(class_str: str) -> list[str]:
    out: list[str] = []
    for tok in class_str.split():
        if tok and not tok.startswith("{") and not tok.startswith(":"):
            out.append(tok)
    return out


def _typo_css_blocks(css: str, classname: str) -> list[str]:
    return [
        m.group(1)
        for m in re.finditer(
            rf"\.{re.escape(classname)}\b[^{{]*\{{([^}}]*)\}}",
            css,
        )
    ]


def _typo_unitless_lh(raw: str) -> float | None:
    val = raw.strip().lower().rstrip(";")
    if val.endswith("%"):
        try:
            return float(val[:-1]) / 100.0
        except ValueError:
            return None
    if re.fullmatch(r"1\.\d+", val):
        return float(val)
    return None


def _typo_lh_in_range(raw: str) -> bool:
    n = _typo_unitless_lh(raw)
    return n is not None and 1.5 <= n <= 1.625


def _typo_px(raw: str) -> float | None:
    val = raw.strip().lower()
    m = re.fullmatch(r"([\d.]+)\s*px", val)
    if m:
        return float(m.group(1))
    m = re.fullmatch(r"([\d.]+)\s*rem", val)
    if m:
        return float(m.group(1)) * 16.0
    return None


def _typo_size_token(class_str: str, css: str, kind: str) -> str | None:
    rx = _TYPO_BODY_TW if kind == "body" else _TYPO_META_TW
    m = rx.search(class_str)
    if m:
        return m.group(1)
    lo, hi = (14.0, 15.0) if kind == "body" else (12.0, 13.0)
    for cls in _typo_classes(class_str):
        for block in _typo_css_blocks(css, cls):
            fm = _TYPO_FONT_SIZE.search(block)
            if not fm:
                continue
            px = _typo_px(fm.group(1).strip())
            if px is not None and lo <= px <= hi:
                return f".{cls}"
    return None


def _typo_theme_lh_ok(css: str, tw_token: str) -> bool:
    key = {"text-sm": "sm", "text-base": "base", "text-xs": "xs"}.get(tw_token)
    if not key:
        return False
    m = re.search(
        rf"--text-{re.escape(key)}--line-height\s*:\s*([^;]+);",
        css,
    )
    return bool(m) and _typo_lh_in_range(m.group(1))


def _typo_leading_ok(class_str: str, style: str, css: str) -> bool:
    if _TYPO_LEADING_NAMED.search(class_str):
        return True
    for m in _TYPO_LEADING_ARB.finditer(class_str):
        if _typo_lh_in_range(m.group(1)):
            return True
    if style:
        hm = _TYPO_LINE_HEIGHT.search(style)
        if hm and _typo_lh_in_range(hm.group(1)):
            return True
    tw = _TYPO_BODY_TW.search(class_str)
    if tw and _typo_theme_lh_ok(css, tw.group(1)):
        return True
    for cls in _typo_classes(class_str):
        for block in _typo_css_blocks(css, cls):
            hm = _TYPO_LINE_HEIGHT.search(block)
            if hm and _typo_lh_in_range(hm.group(1)):
                return True
    return False


def _typo_muted_ok(class_str: str, css: str) -> bool:
    if _TYPO_MUTED.search(class_str):
        return True
    for cls in _typo_classes(class_str):
        for block in _typo_css_blocks(css, cls):
            if _TYPO_MUTED.search(block) or re.search(
                r"color\s*:\s*var\(--(?:color-)?muted-foreground\)",
                block,
                re.I,
            ):
                return True
    return False


def _typo_prewrap_attrs(src: str, inner_rx: re.Pattern[str]) -> list[str]:
    found: list[str] = []
    for m in _PRE_WRAP.finditer(src):
        if inner_rx.search(m.group(3)):
            found.append(m.group(2))
    return found


def assert_typography(crate: Path) -> None:
    """#199: 14–15px bodies with line-height 1.5–1.6; 12–13px meta.

    Timeline bodies and search snippets share one body size. People-row
    time/preview and bubble captions share one meta size + muted-foreground.
    Headings stay restrained (no text-3xl+). --font-sans stays system UI.
    No remote font. Do not t() bodies. Docs: 14–15px bodies, 12–13px meta,
    no remote font.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#199: App.svelte required (timeline body / people-row typography)")
    css_path = crate / "web" / "app.css"
    if not css_path.is_file():
        fail("#199: web/app.css required (--font-sans system UI stack)")
    css = css_path.read_text()
    logic = _web_logic(crate)
    timeline = _timeline_block(crate)
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#199: SearchPane.svelte required (search snippet typography)")
    search = search_path.read_text()

    # 1) Timeline + search bodies exist and share one 14–15px size.
    tl_attrs = _typo_prewrap_attrs(
        timeline,
        re.compile(r"displayBody|body_text|bodyText"),
    )
    if not tl_attrs:
        fail(
            "#199: timeline message bodies must stay whitespace-pre-wrap "
            "text nodes (14–15px body size)"
        )
    search_attrs = _typo_prewrap_attrs(
        search,
        re.compile(r"splitSnippet|\.snippet\b|\{body\}"),
    )
    if not search_attrs:
        fail(
            "#199: search snippets / expanded hits must stay "
            "whitespace-pre-wrap text nodes (14–15px body size)"
        )

    body_tokens: list[str] = []
    body_surfaces: list[tuple[str, str, str]] = []
    for label, attrs in (
        *[("timeline", a) for a in tl_attrs],
        *[("search snippet / expanded hit", a) for a in search_attrs],
    ):
        class_str = _typo_resolve_class(_typo_tag_class(attrs), logic)
        tok = _typo_size_token(class_str, css, "body")
        if not tok:
            fail(
                "#199: timeline message bodies and search snippets must use "
                "one body size in the 14–15px range (text-sm / text-base / "
                "text-[14px] / text-[15px])"
            )
        body_tokens.append(tok)
        body_surfaces.append((label, class_str, _typo_tag_style(attrs)))
    if len(set(body_tokens)) != 1:
        fail(
            "#199: timeline bodies and search snippets must share one body "
            "size class (14–15px: text-sm / text-base / text-[14px] / "
            "text-[15px]). Found: " + ", ".join(sorted(set(body_tokens)))
        )

    # 2) Those bodies use line-height 1.5–1.6 (the gap on current master).
    missing_lh = []
    for label, class_str, style in body_surfaces:
        if not _typo_leading_ok(class_str, style, css):
            if label not in missing_lh:
                missing_lh.append(label)
    if missing_lh:
        fail(
            "#199: timeline + search snippet bodies must use line-height "
            "1.5–1.6 (leading-normal / leading-relaxed / leading-[1.5] / "
            "leading-[1.6] / CSS line-height: 1.5–1.6)"
        )

    # 3) People-row time/preview + bubble caption share one 12–13px meta.
    _, people_each = _people_list_a11y_surfaces(crate)
    if not people_each.strip():
        markup = _strip_html_comments(_svelte_markup(app_path.read_text()))
        people_each = _people_each_block(markup)
    if not people_each.strip():
        fail("#199: people list {#each filtered} required (time / preview meta)")
    people_meta: list[str] = []
    for m in re.finditer(r"<span\b([^>]*)>(.*?)</span>", people_each, re.S):
        attrs, inner = m.group(1), m.group(2)
        if re.search(r"last_activity_at|humanTime|\.preview\b", inner):
            people_meta.append(attrs)
    if not people_meta:
        fail(
            "#199: people-list rows must show time / preview as 12–13px meta "
            "(text-xs / text-[12px] / text-[13px])"
        )
    caption_meta: list[str] = []
    for m in re.finditer(
        r"<([a-zA-Z][\w:-]*)\b([^>]*\bclass\s*=\s*[\"'][^\"']*\bcaption\b[^\"']*[\"'][^>]*)>",
        timeline,
    ):
        caption_meta.append(m.group(2))
    if not caption_meta:
        fail(
            "#199: bubble captions (time + platform chip) must keep a caption "
            "element with 12–13px meta"
        )

    meta_tokens: list[str] = []
    for attrs in (*people_meta, *caption_meta):
        class_str = _typo_resolve_class(_typo_tag_class(attrs), logic)
        tok = _typo_size_token(class_str, css, "meta")
        if not tok:
            fail(
                "#199: people-list rows (time / preview) and bubble captions "
                "must use one meta size in the 12–13px range (text-xs / "
                "text-[12px] / text-[13px])"
            )
        if not _typo_muted_ok(class_str, css):
            fail(
                "#199: people-list rows (time / preview) and bubble captions "
                "must use muted-foreground for meta"
            )
        meta_tokens.append(tok)
    if len(set(meta_tokens)) != 1:
        fail(
            "#199: people-list rows and bubble captions must share one meta "
            "size class (12–13px: text-xs / text-[12px] / text-[13px]). "
            "Found: " + ", ".join(sorted(set(meta_tokens)))
        )

    # 4) Headings stay restrained — no display type in product Svelte.
    svelte_files = _product_svelte(crate)
    giant = _token_hits(crate, svelte_files, _TYPO_GIANT)
    if giant:
        fail(
            "#199: headings stay restrained — no text-3xl / text-4xl / "
            "text-5xl / text-6xl / text-7xl / text-8xl / text-9xl in product "
            "Svelte (text-xl / text-2xl on setup is OK). Found:\n  "
            + "\n  ".join(giant)
        )

    # 5) --font-sans stays system UI; no remote font load.
    fm = _TYPO_FONT_SANS.search(css)
    if not fm:
        fail("#199: app.css must keep --font-sans as the system UI stack")
    stack = fm.group(1)
    if "ui-sans-serif" not in stack or "-apple-system" not in stack:
        fail(
            "#199: --font-sans must stay system UI "
            "(ui-sans-serif and -apple-system still present)"
        )
    font_blob = css + "\n" + "\n".join(p.read_text() for p in svelte_files)
    splash = crate / "index.html"
    if splash.is_file():
        font_blob += "\n" + splash.read_text()
    if _TYPO_REMOTE_FONT.search(font_blob) or _THEME_CDN.search(font_blob):
        fail(
            "#199: no Google Fonts / CDN / remote @import of a font "
            "(fonts.googleapis / fonts.gstatic / remote url())"
        )

    # 6) Not: t() of message bodies / previews.
    helpers = _chrome_helper_names(logic)
    body_blob = logic + "\n" + app_path.read_text() + "\n" + search
    if _chrome_helper_on_body(body_blob, helpers) or _BODY_T_CALL.search(body_blob):
        fail("#199: do not t() message bodies or previews (t(body_text) / t(preview))")

    # 7) D24: 14–15px bodies, 12–13px meta, no remote font.
    dtxt = _typo_docs_blob()
    if not dtxt.strip():
        fail(
            "#199: docs/user/app.md (and/or docs/hacking/tauri.md) required "
            "(14–15px bodies, 12–13px meta, no remote font)"
        )
    if not _DOCS_TYPO_BODY.search(dtxt):
        fail(
            "#199: docs/user/app.md (and/or docs/hacking/tauri.md) must mention "
            "14–15px bodies (or body size)"
        )
    if not _DOCS_TYPO_META.search(dtxt):
        fail(
            "#199: docs/user/app.md (and/or docs/hacking/tauri.md) must mention "
            "12–13px meta (or meta size)"
        )
    if not _DOCS_TYPO_NO_REMOTE_FONT.search(dtxt):
        fail(
            "#199: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "system font / no remote font"
        )


# #200 — Lucide chrome icons: play/pause, lightbox close, empty-state.
# Conservative emoji-as-icon ban on those surfaces only (not message bodies).
_ICON_EMOJI_GLYPH = re.compile(r"[▶❚✓✕✖❌✨]")
_LUCIDE_DEFAULT = re.compile(
    r"import\s+(\w+)\s+from\s+[\"']@lucide/svelte/icons/([\w-]+)[\"']"
)
_LUCIDE_NAMED = re.compile(
    r"import\s+\{([^}]+)\}\s+from\s+[\"']@lucide/svelte[\"']"
)
_LUCIDE_BARE = re.compile(
    r"import\s+(\w+)\s+from\s+[\"']@lucide/svelte[\"']"
)
_ICON_SIZE_16 = re.compile(
    r"("
    r"(?<![\w-])(?:size-4|w-4|h-4)(?![\w-])"
    r"|size\s*=\s*(?:\{\s*16\s*\}|[\"']16[\"'])"
    r"|(?:width|height)\s*=\s*(?:\{\s*16\s*\}|[\"']16(?:px)?[\"'])"
    r"|(?:width|height)\s*:\s*16px"
    r")"
)
_ICON_SIZE_20 = re.compile(
    r"("
    r"(?<![\w-])(?:size-5|w-5|h-5)(?![\w-])"
    r"|size\s*=\s*(?:\{\s*20\s*\}|[\"']20[\"'])"
    r"|(?:width|height)\s*=\s*(?:\{\s*20\s*\}|[\"']20(?:px)?[\"'])"
    r"|(?:width|height)\s*:\s*20px"
    r")"
)
_OTHER_ICON_PKG = re.compile(
    r"[\"']("
    r"react-icons(?:/[^\"']+)?"
    r"|@heroicons/[^\"']+"
    r"|heroicons"
    r"|@fortawesome/[^\"']+"
    r"|font-?awesome(?:/[^\"']+)?"
    r"|@tabler/[^\"']+"
    r"|@iconify(?:-[a-z]+)?/[^\"']+"
    r"|@iconify-json/[^\"']+"
    r"|iconify(?:-[a-z]+)?"
    r")[\"']",
    re.I,
)
_OTHER_ICON_IMPORT = re.compile(
    r"from\s+[\"']("
    r"react-icons"
    r"|@heroicons/"
    r"|heroicons"
    r"|@fortawesome/"
    r"|font-?awesome"
    r"|@tabler/"
    r"|@iconify"
    r"|iconify"
    r")",
    re.I,
)
_ICON_CDN = re.compile(
    r"("
    r"fonts\.googleapis"
    r"|cdn\."
    r"|unpkg(?:\.com)?"
    r"|jsdelivr"
    r"|api\.iconify"
    r"|iconify\.design"
    r")",
    re.I,
)
_EMPTY_MASCOT = re.compile(
    r"("
    r"\billustration\b"
    r"|\bmascot\b"
    r"|<svg\b"
    r"|<img\b"
    r")",
    re.I,
)
_BRAND_LOGO_IMG = re.compile(
    r"("
    r"<img\b[^>]*(?:whatsapp|gmail|gstatic|googleusercontent)[^>]*>"
    r"|src\s*=\s*[\"']https?://[^\"']*(?:whatsapp|gmail|gstatic)"
    r")",
    re.I,
)
_DOCS_LUCIDE_CHROME = re.compile(
    r"("
    r"lucide.{0,280}(?:play|pause|lightbox|empty)"
    r"|(?:play|pause|lightbox|empty|chrome icons?).{0,280}lucide"
    r")",
    re.I | re.S,
)
_DOCS_LUCIDE_NOT_EMOJI = re.compile(
    r"("
    r"not emoji(?:[- ]as[- ]icon)?(?: glyphs?)?"
    r"|not.{0,80}emoji glyphs?"
    r"|lucide.{0,80}not emoji"
    r"|chrome icons?.{0,80}not emoji"
    r"|not.{0,48}(?:▶|❚❚|text glyphs?)"
    r")",
    re.I,
)
_NAV_LABEL_KEYS = ("people", "search", "review", "import", "doctor")


def _lucide_surface(text: str) -> str:
    return _without_comments(_strip_html_comments(text))


def _lucide_bindings(src: str) -> list[tuple[str, str]]:
    """Local name + lucide icon id from `@lucide/svelte` imports."""
    out: list[tuple[str, str]] = []
    for m in _LUCIDE_DEFAULT.finditer(src):
        out.append((m.group(1), m.group(2).lower()))
    for m in _LUCIDE_NAMED.finditer(src):
        for part in m.group(1).split(","):
            part = part.strip()
            if not part:
                continue
            bits = re.split(r"\s+as\s+", part)
            export = bits[0].strip()
            local = bits[-1].strip()
            if export and local:
                out.append((local, export.lower()))
    for m in _LUCIDE_BARE.finditer(src):
        out.append((m.group(1), m.group(1).lower()))
    return out


def _lucide_ids(bindings: list[tuple[str, str]]) -> set[str]:
    return {path for _, path in bindings}


def _lucide_open_tags(block: str, names: set[str]) -> list[str]:
    if not names:
        return []
    alt = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
    return re.findall(rf"<(?:{alt})\b([^>]*?)/?>", block, re.S)


def _lucide_used(block: str, names: set[str]) -> set[str]:
    return {n for n in names if re.search(rf"<{re.escape(n)}\b", block)}


def _lucide_attr_block(src: str, attr: str) -> str:
    m = re.search(
        rf"<([A-Za-z][\w:.-]*)\b([^>]*\b{re.escape(attr)}\b[^>]*)>",
        src,
        re.S,
    )
    if not m:
        return ""
    open_tag = m.group(0)
    name = m.group(1)
    if open_tag.rstrip().endswith("/>") or name.lower() in _VOID_HTML:
        return open_tag
    close = re.search(rf"</{re.escape(name)}\s*>", src[m.end() :], re.I)
    if not close:
        return src[m.start() : m.end() + 480]
    return src[m.start() : m.end() + close.end()]


def _lucide_files_with(crate: Path, needle: str) -> list[tuple[Path, str]]:
    found: list[tuple[Path, str]] = []
    for p in _product_svelte(crate):
        text = p.read_text()
        if needle in text:
            found.append((p, text))
    return found


def assert_lucide_icons(crate: Path) -> None:
    """#200: chrome icons are Lucide (@lucide/svelte), not glyphs / CDN.

    Voice play/pause and lightbox close are 16px Lucide. EmptyState shows a
    20px Lucide. Keep data-voice-play / data-lightbox-close / data-empty and
    play-pause behavior. No emoji-as-icon on those surfaces. No second icon
    package or CDN icon kit. Nav icons optional — text labels stay. Not:
    mascots, brand-logo images, #201/#202/#224. Docs: Lucide chrome icons,
    not emoji glyphs.
    """
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    if not cas_path.is_file():
        fail("#200: CasAttach.svelte required (voice play/pause + lightbox close)")
    empty_path = crate / "web" / "lib" / "EmptyState.svelte"
    if not empty_path.is_file():
        fail("#200: EmptyState.svelte required (20px Lucide on data-empty)")
    pkg_path = crate / "package.json"
    if not pkg_path.is_file():
        fail("#200: crates/interlace-tauri/package.json required (@lucide/svelte)")

    # 1) Keep voice play/pause behavior; replace ▶ / ❚❚ with Lucide 16px.
    voice_files = _lucide_files_with(crate, "data-voice-play")
    if not voice_files:
        fail("#200: keep data-voice-play on the voice play/pause control")
    voice_blob = "\n".join(text for _, text in voice_files)
    if not re.search(
        r"("
        r"togglePlay"
        r"|\.play\s*\("
        r"|\.pause\s*\("
        r"|aria-label\s*=\s*\{[^}]*(?:[Pp]lay|[Pp]ause)"
        r")",
        voice_blob,
    ):
        fail(
            "#200: keep voice play/pause behavior "
            "(togglePlay / .play()/.pause() / aria-label Play or Pause)"
        )
    if _ICON_EMOJI_GLYPH.search(_lucide_surface(voice_blob)):
        fail(
            "#200: voice play/pause must be Lucide, not ▶ / ❚❚ text glyphs "
            "(keep data-voice-play)"
        )
    voice_bindings = _lucide_bindings(voice_blob)
    voice_ids = _lucide_ids(voice_bindings)
    if "play" not in voice_ids or "pause" not in voice_ids:
        fail(
            "#200: voice play/pause must import Lucide Play / Pause "
            "from @lucide/svelte (keep data-voice-play)"
        )
    voice_names = {local for local, path in voice_bindings if path in {"play", "pause"}}
    voice_blocks = [
        _lucide_attr_block(text, "data-voice-play") or text for _, text in voice_files
    ]
    voice_used = set()
    for block in voice_blocks:
        voice_used |= _lucide_used(block, voice_names)
    if voice_used != voice_names:
        fail(
            "#200: data-voice-play must render Lucide Play / Pause "
            "(not ▶ / ❚❚ text glyphs)"
        )
    voice_tags = []
    for block in voice_blocks:
        voice_tags.extend(_lucide_open_tags(block, voice_used))
    if not voice_tags or any(not _ICON_SIZE_16.search(tag) for tag in voice_tags):
        fail(
            "#200: voice play/pause Lucide icons must be 16px default "
            "(size-4 / w-4 h-4 / size={16})"
        )

    # 2) Lightbox close is Lucide (dialog X is the pattern) at 16px.
    close_files = _lucide_files_with(crate, "data-lightbox-close")
    if not close_files:
        fail("#200: keep data-lightbox-close on the lightbox close control")
    close_blob = "\n".join(text for _, text in close_files)
    if not re.search(
        r"aria-label\s*=\s*[\"'][^\"']*[Cc]lose[^\"']*[\"']",
        close_blob,
    ):
        fail(
            "#200: lightbox close must keep an accessible name "
            "(aria-label \"Close photo\")"
        )
    close_bindings = _lucide_bindings(close_blob)
    close_names = {local for local, _ in close_bindings}
    if not close_names:
        fail(
            "#200: lightbox close (data-lightbox-close) must use a Lucide icon "
            "imported from @lucide/svelte (dialog X is the pattern)"
        )
    close_blocks = [
        _lucide_attr_block(text, "data-lightbox-close") or text
        for _, text in close_files
    ]
    close_used: set[str] = set()
    for block in close_blocks:
        close_used |= _lucide_used(block, close_names)
    if not close_used:
        fail(
            "#200: data-lightbox-close must render a Lucide icon "
            "(import from @lucide/svelte; dialog X is the pattern)"
        )
    close_tags: list[str] = []
    for block in close_blocks:
        close_tags.extend(_lucide_open_tags(block, close_used))
    if not close_tags or any(not _ICON_SIZE_16.search(tag) for tag in close_tags):
        fail(
            "#200: lightbox close Lucide icon must be 16px "
            "(size-4 / w-4 h-4 / size={16})"
        )

    # 3) EmptyState: 20px Lucide; keep title/body; not a mascot / network img.
    empty = empty_path.read_text()
    if "data-empty" not in empty:
        fail("#200: EmptyState must keep data-empty")
    if not re.search(r"\{title\}", empty) or not re.search(r"\{body\}", empty):
        fail("#200: EmptyState must keep title / body text")
    empty_bindings = _lucide_bindings(empty)
    empty_names = {local for local, _ in empty_bindings}
    if not empty_names:
        fail(
            "#200: EmptyState (data-empty) must import a Lucide icon "
            "from @lucide/svelte at 20px (size-5 / w-5 h-5 / 20)"
        )
    empty_block = _lucide_attr_block(empty, "data-empty") or empty
    empty_used = _lucide_used(empty_block, empty_names) or _lucide_used(
        empty, empty_names
    )
    if not empty_used:
        fail(
            "#200: EmptyState (data-empty) must render a Lucide icon "
            "at 20px (size-5 / w-5 h-5 / 20)"
        )
    empty_tags = _lucide_open_tags(empty, empty_used)
    if not empty_tags or any(not _ICON_SIZE_20.search(tag) for tag in empty_tags):
        fail(
            "#200: EmptyState Lucide icon must be 20px "
            "(size-5 / w-5 h-5 / size={20}) — not a mascot / illustration"
        )
    # Ban illustrated mascots / network <img> in EmptyState. Lucide is a
    # component import, not a raw <svg> scene or remote <img>.
    if _EMPTY_MASCOT.search(_lucide_surface(empty)):
        fail(
            "#200: EmptyState must not use a mascot / illustration / <svg> "
            "scene / <img> (20px Lucide only; no network image)"
        )

    # 4) No emoji-as-icon on play/pause / close / empty (not message bodies).
    surface_blob = "\n".join(
        [
            *[block for block in voice_blocks if block],
            *[block for block in close_blocks if block],
            empty_block,
        ]
    )
    if _ICON_EMOJI_GLYPH.search(_lucide_surface(surface_blob)):
        fail(
            "#200: no emoji-as-icon on play/pause / lightbox close / empty "
            "(▶ ❚ ✓ ✕ ✖ ❌ ✨) — message bodies are not this check"
        )

    # 5) @lucide/svelte stays; no second icon pack.
    pkg = pkg_path.read_text()
    if '"@lucide/svelte"' not in pkg:
        fail(
            "#200: package.json must keep @lucide/svelte "
            "(do not add a second icon package)"
        )
    if _OTHER_ICON_PKG.search(pkg):
        fail(
            "#200: do not add a second icon package "
            "(react-icons / heroicons / fontawesome / @tabler / iconify) — "
            "use @lucide/svelte already in the crate"
        )
    svelte_blob = "\n".join(p.read_text() for p in _product_svelte(crate))
    if _OTHER_ICON_IMPORT.search(svelte_blob):
        fail(
            "#200: product Svelte must import icons from @lucide/svelte only "
            "(no react-icons / heroicons / fontawesome / @tabler / iconify)"
        )

    # 6) No CDN icon kit; no WhatsApp/Gmail CDN brand logos as icons.
    cdn_blob = svelte_blob
    css_path = crate / "web" / "app.css"
    if css_path.is_file():
        cdn_blob += "\n" + css_path.read_text()
    splash = crate / "index.html"
    if splash.is_file():
        cdn_blob += "\n" + splash.read_text()
    if _ICON_CDN.search(_lucide_surface(cdn_blob)):
        fail(
            "#200: no CDN icon kit "
            "(fonts.googleapis / cdn. / unpkg / jsdelivr / iconify API)"
        )
    if _BRAND_LOGO_IMG.search(_lucide_surface(svelte_blob)):
        fail(
            "#200: not in scope — no WhatsApp / Gmail CDN brand logos as icons"
        )

    # 7) Nav icons are optional; text labels must stay.
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#200: App.svelte required (nav text labels stay; icons optional)")
    app = app_path.read_text()
    nav_m = re.search(r"<nav\b[^>]*>[\s\S]*?</nav>", app, re.I)
    if not nav_m:
        fail("#200: App.svelte nav required (keep text labels; icons optional)")
    nav = nav_m.group(0)
    for key in _NAV_LABEL_KEYS:
        if not re.search(rf"""t\(\s*["']{key}["']\s*\)""", nav):
            fail(
                f"#200: nav must keep the {key} text label "
                "(icons are optional; do not replace labels with icon-only chrome)"
            )

    # 8) D24: Lucide chrome icons (play/pause / lightbox / empty), not emoji.
    dtxt = _typo_docs_blob()
    if not dtxt.strip():
        fail(
            "#200: docs/user/app.md (and/or docs/hacking/tauri.md) required "
            "(Lucide chrome icons, not emoji glyphs)"
        )
    if not _DOCS_LUCIDE_CHROME.search(dtxt):
        fail(
            "#200: docs/user/app.md (and/or docs/hacking/tauri.md) must mention "
            "Lucide chrome icons (play/pause, lightbox, empty)"
        )
    if not _DOCS_LUCIDE_NOT_EMOJI.search(dtxt):
        fail(
            "#200: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "chrome icons are Lucide, not emoji glyphs"
        )


# #201 — owned Tooltip, Separator, Badge, Card (no one-off chrome).
_OWNED_PRIMITIVES_201 = ("tooltip", "separator", "badge", "card")
_BITS_KIT_CDN = re.compile(
    r"("
    r"(?:unpkg(?:\.com)?|jsdelivr(?:\.net)?|esm\.sh|cdn\.)[^\"'\s)]*bits-ui"
    r"|bits-ui[^\"'\s)]*(?:unpkg|jsdelivr|esm\.sh)"
    r"|https?://[^\"'\s)]*(?:unpkg|jsdelivr|esm\.sh|cdn\.)[^\"'\s)]*"
    r"(?:bits-ui|@radix-ui|shadcn|daisyui|flowbite|melt-ui|skeletonlabs|ark-ui)"
    r")",
    re.I,
)
_NETWORK_AVATAR_IMG = re.compile(
    r"<img\b[^>]{0,400}\bsrc\s*=\s*[\"']https?://",
    re.I | re.S,
)
_DOCS_OWNED_CHIPS_BANNERS = re.compile(
    r"("
    r"(?:platform[- ]?chips?|banners?).{0,200}"
    r"(?:owned.{0,60})?(?:badge|card|shadcn[- ]?(?:svelte )?primitives?)"
    r"|(?:owned.{0,60})?(?:badge|card|shadcn[- ]?(?:svelte )?primitives?).{0,200}"
    r"(?:platform[- ]?chips?|banners?)"
    r")",
    re.I | re.S,
)
_DOCS_NOT_ONE_OFF_CHROME = re.compile(
    r"("
    r"not one-off(?: chrome)?"
    r"|not.{0,48}one-off chrome"
    r"|rather than one-off"
    r"|instead of one-off"
    r"|not hand-?rolled chrome"
    r")",
    re.I,
)
_DIALOG_FOOTER_BLOCK = re.compile(
    r"<Dialog\.Footer\b[^>]*>[\s\S]*?</Dialog\.Footer>",
    re.I,
)


def _owned_tag_match(tag: str, names: list[str]) -> bool:
    tag_l = tag.lower()
    for n in names:
        nl = n.lower()
        if tag_l == nl or tag_l.startswith(nl + "."):
            return True
    return False


def _owned_used_in(block: str, names: list[str]) -> bool:
    for n in names:
        if re.search(rf"<{re.escape(n)}(?:\.\w+)?\b", block):
            return True
    return False


def _hook_tag_name(src: str, hook: str) -> str:
    m = re.search(
        rf"<([A-Za-z][\w:.-]*)\b[^>]*\b{re.escape(hook)}\b",
        src,
        re.S,
    )
    return m.group(1) if m else ""


def _chip_hook_files(crate: Path) -> list[tuple[Path, str]]:
    found: list[tuple[Path, str]] = []
    for p in _product_svelte(crate):
        text = p.read_text()
        if re.search(r"\bdata-platform-chip\b|\bplatform-chip\b", text):
            found.append((p, text))
    return found


def assert_owned_primitives(crate: Path) -> None:
    """#201: own Tooltip, Separator, Badge, Card — no one-off chrome.

    Four primitive dirs under web/lib/components/ui/ (svelte + index.ts).
    Platform chip is Badge. A banner or dialog footer uses Card/Separator.
    bits-ui stays the local kit (no second library, no CDN). Not: network
    avatars, Command (#215), Toast (#204). Docs: owned Badge/Card for
    chips/banners, not one-off chrome.
    """
    ui = crate / "web" / "lib" / "components" / "ui"
    if not ui.is_dir():
        fail("#201: web/lib/components/ui/ required for owned primitives")

    # 1) Owned tooltip / separator / badge / card files exist.
    missing: list[str] = []
    for name in _OWNED_PRIMITIVES_201:
        d = ui / name
        if not d.is_dir():
            missing.append(f"{name}/")
            continue
        if not any(d.glob("*.svelte")):
            missing.append(f"{name}/*.svelte")
        if not (d / "index.ts").is_file():
            missing.append(f"{name}/index.ts")
    if missing:
        fail(
            "#201: missing owned primitives under web/lib/components/ui/ "
            "(tooltip, separator, badge, card — each needs at least one "
            ".svelte and index.ts). Missing: " + ", ".join(missing)
        )

    # 2) Platform chip is the Badge primitive (keep existing hooks).
    chip_files = _chip_hook_files(crate)
    if not chip_files:
        fail(
            "#201: keep data-platform-chip / platform-chip on the platform "
            "chip (implemented with the Badge primitive)"
        )
    badge_ok = False
    for _p, text in chip_files:
        names = _owned_imported_names(text, "badge")
        if not names:
            continue
        tag = _hook_tag_name(text, "data-platform-chip") or _hook_tag_name(
            text, "platform-chip"
        )
        if tag and _owned_tag_match(tag, names):
            badge_ok = True
            break
    if not badge_ok:
        fail(
            "#201: platform chip (data-platform-chip / platform-chip) must "
            "be the Badge primitive (import from $lib/components/ui/badge "
            "or relative components/ui/badge) — not a hand-rolled span"
        )

    # 3) At least one banner or dialog footer uses Card or Separator.
    chrome_ok = False
    for p in _product_svelte(crate):
        text = p.read_text()
        names = _owned_imported_names(text, "card") + _owned_imported_names(
            text, "separator"
        )
        if not names:
            continue
        if "data-cloud-warning" in text:
            block = _lucide_attr_block(text, "data-cloud-warning") or ""
            tag = _hook_tag_name(text, "data-cloud-warning")
            if _owned_tag_match(tag, names) or _owned_used_in(block, names):
                chrome_ok = True
                break
        for footer in _DIALOG_FOOTER_BLOCK.findall(text):
            if _owned_used_in(footer, names):
                chrome_ok = True
                break
        if chrome_ok:
            break
        footer_hook = _lucide_attr_block(text, "data-dialog-footer")
        if footer_hook and _owned_used_in(footer_hook, names):
            chrome_ok = True
            break
    if not chrome_ok:
        fail(
            "#201: at least one banner (data-cloud-warning) or dialog footer "
            "must use owned Card or Separator from "
            "$lib/components/ui/{card,separator}"
        )

    # 4) No second component library; bits-ui stays a local dep.
    pkg_path = crate / "package.json"
    if not pkg_path.is_file():
        fail("#201: crates/interlace-tauri/package.json required (bits-ui local)")
    pkg = pkg_path.read_text()
    if '"bits-ui"' not in pkg:
        fail(
            "#201: package.json must keep bits-ui as a local dependency "
            "(do not load bits-ui from a CDN)"
        )
    if _SECOND_UI_KIT.search(pkg):
        fail(
            "#201: package.json must not add a second component library "
            "(@radix-ui / shadcn / @skeletonlabs / daisyui / flowbite / "
            "@ark-ui / melt-ui) — extend owned primitives; bits-ui stays"
        )

    # 5) No bits-ui / component kit from CDN.
    if _BITS_KIT_CDN.search(_web_chrome_blob(crate)):
        fail(
            "#201: no bits-ui / component kit from CDN "
            "(unpkg / jsdelivr / cdn. / esm.sh)"
        )

    # 6) Not: network avatars, Command palette (#215), Toast (#204).
    svelte_blob = "\n".join(p.read_text() for p in _product_svelte(crate))
    if _NETWORK_AVATAR_IMG.search(svelte_blob):
        fail(
            "#201: not in scope — no network avatar <img src=\"http…\"> "
            "on people / chrome"
        )
    if _CMD_PALETTE_PKG.search(pkg):
        fail(
            "#201: not in scope — Command palette is #215 "
            "(do not add cmdk / svelte-command)"
        )
    if _TOAST_SONNER_PKG.search(pkg):
        fail(
            "#201: not in scope — Toast / sonner is #204 "
            "(do not add sonner / svelte-sonner)"
        )

    # 7) D24: owned Badge/Card (or owned shadcn primitives) for chips/banners.
    dtxt = _typo_docs_blob()
    if not dtxt.strip():
        fail(
            "#201: docs/user/app.md (and/or docs/hacking/tauri.md) required "
            "(owned Badge/Card for chips/banners, not one-off chrome)"
        )
    if not _DOCS_OWNED_CHIPS_BANNERS.search(dtxt):
        fail(
            "#201: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "platform chips / banners use owned Badge / Card "
            "(or owned shadcn primitives)"
        )
    if not _DOCS_NOT_ONE_OFF_CHROME.search(dtxt):
        fail(
            "#201: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "chips / banners are owned primitives, not one-off chrome"
        )


# #202 — EmptyState next action on every major empty view (no mascot).
# Titles stay English-grepable (#131). Action may be a label + handler,
# onclick, snippet, or Button/button child. Import idle may use data-empty
# instead of <EmptyState> if that hook still carries a next action.
_EMPTY_TITLES_202 = (
    ("App.svelte", "No people yet", "People: no people yet"),
    ("App.svelte", "No match", "People: no filter match"),
    ("SearchPane.svelte", "Type a query", "Search: no query"),
    ("SearchPane.svelte", "No hits", "Search: no hits"),
    ("ReviewPane.svelte", "Nothing to review", "Review: nothing to review"),
    ("App.svelte", "No messages in this view", "Timeline: no messages"),
    ("DoctorPane.svelte", "No doctor issues", "Doctor healthy"),
)
# IN.md: Select a person still needs a next action if that EmptyState stays.
_EMPTY_TITLES_202_OPTIONAL_IF_ABSENT = (
    ("App.svelte", "Select a person", "Timeline: select a person"),
)
_EMPTY_NEXT_ACTION = re.compile(
    r"("
    r"\baction(?:Label|Text|Click|Handler)?\s*="
    r"|\bprimaryAction\s*="
    r"|\bnextAction\s*="
    r"|\bcta(?:Label)?\s*="
    r"|\bonAction\s*="
    r"|\bonaction\s*="
    r"|\bonclick\s*="
    r"|\bon:click\s*="
    r"|\{#snippet\s+(?:action|children|cta)\b"
    r"|\{@render\s+(?:action|children|cta)\b"
    r"|<(?:Button|button)\b"
    r"|Pick file"
    r"|Clear filter"
    r")",
    re.I,
)
_EMPTY_OPTIONAL_ACTION = re.compile(
    r"("
    r"\baction(?:Label|Text|Click|Handler)?\s*\??\s*:"
    r"|\bprimaryAction\s*\??\s*:"
    r"|\bnextAction\s*\??\s*:"
    r"|\bcta(?:Label)?\s*\??\s*:"
    r"|\bonAction\s*\??\s*:"
    r"|\bonclick\s*\??\s*:"
    r"|children\s*\??\s*:"
    r"|\{#if\s+[^}]{0,120}(?:action|onclick|onAction|cta|children)\b"
    r"|\{@render\s+(?:action|children|cta)\b"
    r"|\{#snippet\s+(?:action|children|cta)\b"
    r")",
    re.I,
)
_EMPTY_GRADIENT = re.compile(r"\bbg-gradient(?:-|to-|\b)", re.I)
_SKELETON_PKG_202 = re.compile(
    r"[\"'](?:svelte-skeleton|skeleton-svelte|@skeletonlabs(?:/[^\"']*)?)[\"']",
    re.I,
)
_DOCS_EMPTY_NEXT_ACTION = re.compile(
    r"("
    r"empty(?:[- ]states?| views?)?.{0,120}(?:next action|helpful action)"
    r"|(?:next action|helpful action).{0,120}empty(?:[- ]states?| views?)?"
    r"|empty(?:[- ]states?| views?)?.{0,80}(?:import|clear filter|pick file)"
    r")",
    re.I | re.S,
)
_DOCS_EMPTY_NO_MASCOT = re.compile(
    r"("
    r"(?:empty(?:[- ]states?| views?)?).{0,80}(?:no |not |without ).{0,40}mascot"
    r"|no mascot.{0,80}empty"
    r"|not.{0,40}(?:a )?mascot"
    r")",
    re.I | re.S,
)


def _empty_block_title(block: str) -> str:
    m = re.search(r"\btitle\s*=\s*[\"']([^\"']+)[\"']", block)
    if m:
        return m.group(1)
    m = re.search(r"\btitle\s*=\s*\{[\"']([^\"']+)[\"']\}", block)
    if m:
        return m.group(1)
    return ""


def _empty_usage_has_action(block: str) -> bool:
    return bool(_EMPTY_NEXT_ACTION.search(block))


def _empty_file(crate: Path, name: str) -> Path:
    if name == "App.svelte":
        return crate / "web" / "App.svelte"
    return crate / "web" / "lib" / name


def assert_empty_next_action(crate: Path) -> None:
    """#202: EmptyState next action on every major empty view, no mascot.

    Optional primary action uses owned Button. People / Search / Review /
    Timeline / Import idle / Doctor healthy wire a next action. Keep
    data-empty. No illustration / bg-gradient. Merge-picker EmptyState
    also needs an action if present. Not: skeletons (#203), toasts (#204),
    t() of imported bodies, command palette (#215). Docs: empty views
    have a next action, no mascot.
    """
    empty_path = crate / "web" / "lib" / "EmptyState.svelte"
    if not empty_path.is_file():
        fail("#202: EmptyState.svelte required (data-empty + optional Button action)")
    empty = empty_path.read_text()

    # 1) Keep data-empty / title / body (gates grep data-empty).
    if "data-empty" not in empty:
        fail("#202: EmptyState must keep data-empty")
    if not re.search(r"\{title\}", empty) or not re.search(r"\{body\}", empty):
        fail("#202: EmptyState must keep title / body text")

    # 2) Optional primary action rendered with owned Button.
    button_names = _owned_imported_names(empty, "button")
    if not button_names:
        fail(
            "#202: EmptyState must render an optional primary action with "
            "owned Button (import from $lib/components/ui/button or "
            "relative components/ui/button)"
        )
    empty_markup = _svelte_markup(empty)
    if not _owned_used_in(empty_markup, button_names) and not _owned_used_in(
        empty, button_names
    ):
        fail(
            "#202: EmptyState must render the optional primary action with "
            "owned Button (import from $lib/components/ui/button or "
            "relative components/ui/button)"
        )
    if not _EMPTY_OPTIONAL_ACTION.search(empty):
        fail(
            "#202: EmptyState primary action must be optional "
            "(label + handler, onclick, or snippet — not a required mascot CTA)"
        )

    # 3) No SVG mascot / illustration / gradient card on EmptyState.
    if _EMPTY_GRADIENT.search(empty):
        fail("#202: EmptyState must not use a gradient card (no bg-gradient)")
    if _EMPTY_MASCOT.search(_lucide_surface(empty)):
        fail(
            "#202: EmptyState must not use a mascot / illustration / <svg> "
            "scene / <img> (20px Lucide + next action; no marketing card)"
        )

    # 4) Listed views keep their empty copy and wire a next action.
    en_chrome = _chrome_en_text(crate)
    required_files = {fname for fname, _title, _why in _EMPTY_TITLES_202}
    file_text: dict[str, str] = {}
    for fname in required_files | {"ImportPane.svelte"} | {
        f for f, _t, _w in _EMPTY_TITLES_202_OPTIONAL_IF_ABSENT
    }:
        path = _empty_file(crate, fname)
        if not path.is_file():
            fail(f"#202: {fname} required (empty view with a next action)")
        file_text[fname] = path.read_text()

    for fname, title, why in _EMPTY_TITLES_202:
        blob = file_text[fname] + "\n" + en_chrome
        if title not in blob:
            fail(f"#202: keep {title!r} empty copy ({why})")
        all_blocks = _empty_state_blocks(file_text[fname])
        titled = [b for b in all_blocks if title in b]
        if not titled:
            # Title may live in the en pack; the file still needs EmptyState.
            if not all_blocks:
                fail(
                    f"#202: {why} must use EmptyState with a next action "
                    f"(keep {title!r}; keep data-empty grep-able)"
                )
            titled = all_blocks
        missing = [b for b in titled if not _empty_usage_has_action(b)]
        if missing:
            shown = _empty_block_title(missing[0]) or title
            fail(
                f"#202: {why} EmptyState ({shown!r}) must include a next action "
                "(action label / onclick / Button child)"
            )

    for fname, title, why in _EMPTY_TITLES_202_OPTIONAL_IF_ABSENT:
        titled = [b for b in _empty_state_blocks(file_text[fname]) if title in b]
        if not titled:
            continue
        missing = [b for b in titled if not _empty_usage_has_action(b)]
        if missing:
            fail(
                f"#202: {why} EmptyState ({title!r}) must include a next action "
                "(action label / onclick / Button child)"
            )

    # Every remaining EmptyState usage (merge-picker No match, …) needs an action.
    for p in _product_svelte(crate):
        if p.name == "EmptyState.svelte":
            continue
        text = p.read_text()
        for block in _empty_state_blocks(text):
            if _empty_usage_has_action(block):
                continue
            shown = _empty_block_title(block) or p.name
            fail(
                f"#202: EmptyState {shown!r} in {p.relative_to(crate)} must "
                "include a next action (action label / onclick / Button child)"
            )

    # 5) Import idle must gain EmptyState or data-empty with a next action.
    imp = file_text["ImportPane.svelte"]
    if "EmptyState" not in imp and "data-empty" not in imp:
        fail(
            "#202: Import idle must use EmptyState (or data-empty) with a "
            "next action (Pick file)"
        )
    import_ok = False
    for block in _empty_state_blocks(imp):
        if _empty_usage_has_action(block):
            import_ok = True
            break
    if not import_ok and "data-empty" in imp:
        hook = _lucide_attr_block(imp, "data-empty") or imp
        if _empty_usage_has_action(hook):
            import_ok = True
    if not import_ok:
        fail(
            "#202: Import idle EmptyState (or data-empty) must include a "
            "next action (Pick file)"
        )

    # 6) Not: skeletons (#203), toasts (#204), command palette (#215), t(bodies).
    pkg_path = crate / "package.json"
    pkg = pkg_path.read_text() if pkg_path.is_file() else ""
    if _SKELETON_PKG_202.search(pkg):
        fail("#202: not in scope — loading skeletons are #203")
    for p in _product_svelte(crate):
        stem = p.stem.lower()
        if stem.startswith("skeleton") or stem in {"skeleton", "skeletons"}:
            fail(
                "#202: not in scope — loading skeleton components are #203 "
                f"(found {p.relative_to(crate)})"
            )
    if _TOAST_SONNER_PKG.search(pkg):
        fail("#202: not in scope — toasts / sonner are #204")
    if _CMD_PALETTE_PKG.search(pkg):
        fail("#202: not in scope — command palette is #215")
    svelte_blob = "\n".join(p.read_text() for p in _product_svelte(crate))
    if _BODY_T_CALL.search(svelte_blob):
        fail(
            "#202: not in scope — do not t() imported bodies "
            "(body_text / preview / snippet)"
        )

    # 7) D24: empty views have a next action, no mascot.
    dtxt = _typo_docs_blob()
    if not dtxt.strip():
        fail(
            "#202: docs/user/app.md (and/or docs/hacking/tauri.md) required "
            "(empty views have a next action, no mascot)"
        )
    if not _DOCS_EMPTY_NEXT_ACTION.search(dtxt):
        fail(
            "#202: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "empty views have a next action (Import / clear filter / Pick file)"
        )
    if not _DOCS_EMPTY_NO_MASCOT.search(dtxt):
        fail(
            "#202: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "empty views have no mascot"
        )
_SKELETON_MUTED_BAR = re.compile(
    r"("
    r"\bbg-muted\b"
    r"|var\(--(?:color-)?muted\)"
    r")"
)
_SKELETON_ANIM = re.compile(
    r"("
    r"\banimate-(?:pulse|shimmer|skeleton)\b"
    r"|@keyframes\s+[\w-]*(?:shimmer|pulse|skeleton)[\w-]*"
    r"|animation\s*:\s*[^;\n}]*(?:shimmer|pulse|skeleton)"
    r")",
    re.I,
)
_SKELETON_JS_SHIMMER = re.compile(
    r"("
    r"requestAnimationFrame\s*\([^)]{0,80}(?:shimmer|skeleton|pulse)"
    r"|setInterval\s*\([^)]{0,80}(?:shimmer|skeleton|pulse)"
    r")",
    re.I,
)
_SKELETON_PKG_203 = re.compile(
    r"[\"'](?:svelte-skeleton|skeleton-svelte|@skeletonlabs(?:/[^\"']*)?"
    r"|react-loading-skeleton|react-content-loader)[\"']",
    re.I,
)
_SKELETON_SVG_ANIM = re.compile(r"<animate(?:Transform|Motion)?\b", re.I)
_DOCS_203_SKELETON = re.compile(
    r"("
    r"(?:quiet\s+)?(?:muted\s+)?skeleton.{0,240}(?:people|timeline|search)"
    r"|(?:people|timeline|search).{0,240}(?:quiet\s+)?(?:muted\s+)?skeleton"
    r")",
    re.I | re.S,
)
_DOCS_203_BOOT_STAYS = re.compile(
    r"("
    r"boot(?:\s*/\s*opening)?\s+spinner.{0,48}stay"
    r"|spinner stay"
    r"|boot spinner stays"
    r"|keep.{0,48}(?:boot|opening).{0,24}spinner"
    r")",
    re.I | re.S,
)
_DOCS_203_REDUCE_STATIC = re.compile(
    r"("
    r"reduced[- ]motion.{0,80}static"
    r"|static.{0,48}(?:bars|skeleton)"
    r")",
    re.I | re.S,
)
_SKELETON_REDUCE_STATIC = re.compile(
    r"("
    r"animation\s*:\s*none\b"
    r"|animation-duration\s*:\s*0(?:\.\d+)?(?:s|ms)?\b"
    r"|animation-iteration-count\s*:\s*1\b"
    r"|animate-none\b"
    r"|motion-reduce:animate-none\b"
    r")",
    re.I,
)


def _has_skeleton_hook(block: str, owned_names: list[str]) -> bool:
    if not block:
        return False
    if _SKELETON_HOOK.search(block):
        return True
    return bool(owned_names) and _owned_used_in(block, owned_names)


def _skeleton_owned_files(crate: Path) -> list[Path]:
    ui = crate / "web" / "lib" / "components" / "ui" / "skeleton"
    if not ui.is_dir():
        return []
    return [p for p in ui.rglob("*") if p.suffix in {".svelte", ".ts", ".css"}]


def _docs_203_surfaces(dtxt: str) -> bool:
    for m in re.finditer(r"\bskeleton\b", dtxt, re.I):
        win = dtxt[max(0, m.start() - 220) : m.end() + 220]
        if (
            re.search(r"\bpeople\b", win, re.I)
            and re.search(r"\btimeline\b", win, re.I)
            and re.search(r"\bsearch\b", win, re.I)
        ):
            return True
    return False


def assert_loading_skeletons(crate: Path) -> None:
    """#203: quiet muted skeleton on people / timeline / search in-flight.

    Token bars (bg-muted / muted), data-skeleton and/or owned Skeleton.
    Keep #156 boot CSS spinner + “Opening last archive”. Search in-flight
    is not EmptyState “No hits” / “Type a query”. Reduced-motion: static
    bars (existing app.css reduce may count). Not: server %, every
    virtualized row, video splash, skeleton npm/CDN. Docs: quiet muted
    skeleton; boot spinner stays; reduced-motion is static.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#203: App.svelte required (people list + person timeline in-flight)")
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    if not search_path.is_file():
        fail("#203: SearchPane.svelte required (search hits in-flight)")
    app = app_path.read_text()
    search = search_path.read_text()
    css_path = crate / "web" / "app.css"
    css = css_path.read_text() if css_path.is_file() else ""
    pkg_path = crate / "package.json"
    pkg = pkg_path.read_text() if pkg_path.is_file() else ""

    people_flag, people_branch = _people_inflight_branch(app)
    if not people_branch:
        for region in _people_sidebar_regions(crate):
            flag, block = _people_inflight_branch(region)
            if block:
                people_flag, people_branch = flag, block
                break
    tl_branch = _svelte_if_true_branch(app, "tlLoading")
    search_branch = _svelte_if_true_branch(search, "searching")

    people_names = _owned_skeleton_names(app)
    search_names = _owned_skeleton_names(search)
    # 1) Three surfaces show a muted skeleton while in-flight.
    missing: list[str] = []
    if not _has_skeleton_hook(people_branch, people_names):
        missing.append("people list")
    if not _has_skeleton_hook(tl_branch, people_names):
        missing.append("person timeline")
    if not _has_skeleton_hook(search_branch, search_names):
        missing.append("search hits")
    if missing:
        fail(
            "#203: "
            + ", ".join(missing)
            + " must show a quiet muted skeleton while in-flight "
            "(data-skeleton and/or owned $lib/components/ui/skeleton)"
        )

    owned_files = _skeleton_owned_files(crate)
    skel_chrome = people_branch + "\n" + tl_branch + "\n" + search_branch
    for p in owned_files:
        skel_chrome += "\n" + p.read_text()

    # 2) Token bars — muted, not a raw amber/yellow shimmer.
    if not _SKELETON_MUTED_BAR.search(skel_chrome):
        fail(
            "#203: skeleton bars must use the muted token "
            "(bg-muted / var(--muted)), not a raw hue"
        )
    if _HUE_AMBER.search(skel_chrome) or _HUE_YELLOW.search(skel_chrome):
        fail("#203: skeleton must not use a raw amber/yellow shimmer")
    if _NET_IMG.search(skel_chrome) or _CDN_HINT.search(skel_chrome):
        fail("#203: skeleton must not load a CDN / network shimmer")

    # 3) Keep #156 boot / opening CSS spinner + exact copy. Do not require a skeleton.
    boot = _boot_opening_block(app)
    en_pack = _chrome_en_text(crate)
    if "Opening last archive" not in boot and "Opening last archive" not in app:
        if "Opening last archive" not in en_pack:
            fail(
                "#203: keep the #156 copy substring “Opening last archive” "
                "(do not replace the boot spinner with a skeleton)"
            )
    css_blob = "\n".join(p.read_text() for p in _web_sources(crate) if p.suffix == ".css")
    boot_with_css = boot + "\n" + css_blob
    if boot and not _has_css_spinner(boot) and not (
        (_SPINNER_NAME.search(boot) or re.search(r"animate-spin", boot))
        and _SPIN_ANIM.search(boot_with_css)
    ):
        fail(
            "#203: keep the #156 boot / opening CSS spinner — "
            "do not replace it with a skeleton"
        )

    # 4) Search in-flight is not EmptyState “No hits” / “Type a query”.
    if re.search(r"\bNo hits\b", search_branch):
        fail("#203: search in-flight must not be the EmptyState “No hits”")
    if re.search(r"\bType a query\b", search_branch):
        fail("#203: search in-flight must not be “Type a query” while searching")
    if "No hits" not in search and "No hits" not in en_pack:
        fail("#203: keep EmptyState “No hits” for the empty (not searching) branch")

    # People in-flight is not the #202 empty copy.
    if re.search(r"\bNo people yet\b", people_branch) or re.search(
        r"\bNo match\b", people_branch
    ):
        fail(
            "#203: people list must not show “No people yet” / “No match” while in-flight"
        )
    refresh = _function_body(app, "refreshPeople")
    if people_flag and refresh and not re.search(
        rf"\b{re.escape(people_flag)}\s*=\s*true\b", refresh
    ):
        fail(
            f"#203: refreshPeople must set {people_flag} = true while "
            "api.people() is in flight so the people skeleton can show"
        )

    # 5) prefers-reduced-motion → static bars. Existing app.css reduce may count.
    reduce_css = "\n".join(_css_prefers_reduced_blocks(css + "\n" + css_blob))
    has_skel_anim = bool(
        _SKELETON_ANIM.search(skel_chrome) or re.search(r"animate-pulse", skel_chrome)
    )
    if _SKELETON_JS_SHIMMER.search(skel_chrome) or _SKELETON_SVG_ANIM.search(skel_chrome):
        fail(
            "#203: prefers-reduced-motion: reduce → no animated shimmer on the "
            "skeletons (static bars; no JS / SVG shimmer that bypasses CSS)"
        )
    if has_skel_anim and not _SKELETON_REDUCE_STATIC.search(reduce_css):
        fail(
            "#203: prefers-reduced-motion: reduce → no animated shimmer on the "
            "skeletons (static bars; existing app.css reduce may count if it "
            "kills the CSS animation)"
        )

    # 6) Not in scope: server %, every virtualized row, video splash, npm/CDN kit.
    if _SERVER_PROGRESS.search(skel_chrome):
        fail("#203: not in scope — no percent progress from a server")
    if _SPLASH_VIDEO.search(skel_chrome) or _SPLASH_VIDEO.search(boot):
        fail("#203: not in scope — no video splash")
    if _SKELETON_PKG_203.search(pkg) or _SKELETON_PKG_202.search(pkg):
        fail("#203: not in scope — do not add a skeleton npm package / CDN shimmer kit")
    tl_rows = _timeline_block(crate)
    tl_owned = people_names
    if _SKELETON_HOOK.search(tl_rows) or _owned_used_in(tl_rows, tl_owned):
        fail(
            "#203: not in scope — do not skeleton every virtualized timeline row at once"
        )

    # 7) D24: quiet muted skeleton on people / timeline / search; boot spinner
    # stays; reduced-motion is static.
    dtxt = _typo_docs_blob()
    if not dtxt.strip():
        fail(
            "#203: docs/user/app.md (and/or docs/hacking/tauri.md) required "
            "(quiet muted skeleton on people / timeline / search)"
        )
    if not _docs_203_surfaces(dtxt) or not _DOCS_203_SKELETON.search(dtxt):
        fail(
            "#203: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "people / timeline / search show a quiet muted skeleton while loading "
            "(boot spinner stays; reduced-motion is static)"
        )
    if not _DOCS_203_BOOT_STAYS.search(dtxt):
        fail(
            "#203: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "the boot spinner stays"
        )
    if not _DOCS_203_REDUCE_STATIC.search(dtxt):
        fail(
            "#203: docs/user/app.md (and/or docs/hacking/tauri.md) must say "
            "reduced-motion is static"
        )


# #203 follow-up — Load older must not mount the timeline skeleton; in-flight audible.
_APPEND_IDENT = re.compile(
    r"\b(tlAppending|isAppending|appending|tlAppend|appendFlag|appendMode|"
    r"loadingOlder|loadOlder|tlLoadOlder|olderLoading|isAppend|append)\b"
)
_REPLACE_IDENT = re.compile(
    r"\b(tlReplacing|isReplacing|replacing|tlReplace|fullReplace|isReplace)\b"
)
_LOAD_OLDER_SELECT_APPEND = re.compile(
    r"selectPerson\s*\(\s*[^,)]+\s*,\s*true\s*[,)]"
)


def _cond_hides_skeleton_on_append(cond: str) -> bool:
    """True if this {#if} is false while Load older / append is in flight."""
    code = _cond_code(cond)
    for ident in _APPEND_IDENT.findall(code):
        if _ident_negated(code, ident):
            return True
    for ident in _REPLACE_IDENT.findall(code):
        if not _ident_negated(code, ident):
            return True
    return False


def _cond_shows_skeleton_on_append(cond: str) -> bool:
    code = _cond_code(cond)
    for ident in _APPEND_IDENT.findall(code):
        if not _ident_negated(code, ident):
            return True
    for ident in _REPLACE_IDENT.findall(code):
        if _ident_negated(code, ident):
            return True
    return False


def _stack_hides_on_append(stack: list[tuple[str, str, str]]) -> bool:
    for kind, cond, _extra in stack:
        if kind == "if" and _cond_hides_skeleton_on_append(cond):
            return True
        if kind == "if-else" and _cond_shows_skeleton_on_append(cond):
            return True
    return False


def _guard_flags(stack: list[tuple[str, str, str]]) -> tuple[list[str], list[str]]:
    append_flags: list[str] = []
    replace_flags: list[str] = []
    for kind, cond, _extra in stack:
        code = _cond_code(cond)
        if kind == "if" and _cond_hides_skeleton_on_append(cond):
            for ident in _APPEND_IDENT.findall(code):
                if _ident_negated(code, ident):
                    append_flags.append(ident)
            for ident in _REPLACE_IDENT.findall(code):
                if not _ident_negated(code, ident):
                    replace_flags.append(ident)
        elif kind == "if-else" and _cond_shows_skeleton_on_append(cond):
            for ident in _APPEND_IDENT.findall(code):
                if not _ident_negated(code, ident):
                    append_flags.append(ident)
            for ident in _REPLACE_IDENT.findall(code):
                if _ident_negated(code, ident):
                    replace_flags.append(ident)
    return append_flags, replace_flags


def _svelte_if_true_branches(src: str, cond: str) -> list[str]:
    found: list[str] = []
    for m in re.finditer(rf"\{{#if\s+[^}}]*\b{re.escape(cond)}\b[^}}]*\}}", src):
        block = _svelte_if_true_branch(src[m.start() :], cond)
        if block:
            found.append(block)
    return found


def _select_person_append_param(src: str) -> str:
    m = re.search(r"(?:async\s+)?function\s+selectPerson\s*\(([^)]*)\)", src)
    if not m:
        return "append"
    params = [p.strip() for p in m.group(1).split(",") if p.strip()]
    if len(params) < 2:
        return "append"
    raw = re.sub(r":[^=]+", "", params[1])
    name = raw.split("=")[0].strip()
    return name or "append"


def _flag_assigned_from_append(fn: str, flag: str, append_param: str) -> bool:
    if re.search(
        rf"\b{re.escape(flag)}\s*=\s*(?:!!|Boolean\s*\(\s*)?{re.escape(append_param)}\b",
        fn,
    ):
        return True
    if re.search(
        rf"if\s*\(\s*{re.escape(append_param)}\s*\)\s*\{{[^}}]{{0,400}}"
        rf"\b{re.escape(flag)}\s*=\s*true",
        fn,
    ):
        return True
    if re.search(
        rf"if\s*\(\s*{re.escape(append_param)}\s*\)\s*{re.escape(flag)}\s*=\s*true",
        fn,
    ):
        return True
    return False


def _flag_cleared_on_append(fn: str, flag: str, append_param: str) -> bool:
    if re.search(rf"\b{re.escape(flag)}\s*=\s*!\s*{re.escape(append_param)}\b", fn):
        return True
    if re.search(
        rf"if\s*\(\s*{re.escape(append_param)}\s*\)[\s\S]{{0,200}}"
        rf"\b{re.escape(flag)}\s*=\s*(?:false|0|null)",
        fn,
    ):
        return True
    return False


def _flag_set_true_in(src: str, flag: str) -> bool:
    return bool(re.search(rf"\b{re.escape(flag)}\s*=\s*true\b", src))


def _open_person_clears_append_flag(src: str, flag: str) -> bool:
    body = _function_body(src, "openPersonAtMessage")
    if not body:
        return True
    if re.search(rf"\b{re.escape(flag)}\s*=\s*(?:false|0|null)", body):
        return True
    if re.search(r"\bselectPerson\s*\(", body):
        return True
    return False


def assert_timeline_append_skeleton_guard(crate: Path) -> None:
    """#203 follow-up: timeline skeleton only on replace, never Load older.

    {#if tlLoading} may stay true so Load older stays disabled. Bars
    (data-skeleton / owned Skeleton) must sit behind an append /
    tlAppending (or equivalent) guard. selectPerson(..., true) must
    actually set that flag. openPersonAtMessage is a full replace.
    Do not require bars on Load older. Existing people / search hooks
    stay in assert_loading_skeletons.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#203: App.svelte required (timeline append must not mount the skeleton)")
    app = app_path.read_text()
    markup = _svelte_markup(app)
    names = _owned_skeleton_names(app)
    branches = _svelte_if_true_branches(markup, "tlLoading")
    if not branches:
        branches = _svelte_if_true_branches(app, "tlLoading")

    hooked = [(b, _skeleton_hook_positions(b, names)) for b in branches]
    hooked = [(b, pos) for b, pos in hooked if pos]
    if not hooked:
        # Replace path still needs a skeleton hook — existing #203 assert.
        return

    append_flags: list[str] = []
    replace_flags: list[str] = []
    unguarded = False
    for block, positions in hooked:
        for pos in positions:
            stack = _template_stack(block, pos)
            if _stack_hides_on_append(stack):
                af, rf = _guard_flags(stack)
                append_flags.extend(af)
                replace_flags.extend(rf)
                continue
            unguarded = True

    if unguarded:
        fail(
            "#203: {#if tlLoading} must not mount data-skeleton / <Skeleton> "
            "on Load older — guard with !append / !tlAppending (or equivalent)"
        )

    select_fn = _function_body(app, "selectPerson")
    append_param = _select_person_append_param(app)
    load_win = ""
    i = app.find("Load older")
    if i >= 0:
        load_win = app[max(0, i - 500) : i + 80]
    load_calls_append = bool(_LOAD_OLDER_SELECT_APPEND.search(load_win) or _LOAD_OLDER_SELECT_APPEND.search(app))

    wired = False
    for flag in dict.fromkeys(append_flags):
        if _flag_assigned_from_append(select_fn, flag, append_param):
            wired = True
        elif _flag_set_true_in(select_fn, flag) or _flag_set_true_in(load_win, flag):
            wired = True
        if not _open_person_clears_append_flag(app, flag):
            fail(
                "#203: openPersonAtMessage is a full replace — do not inherit "
                "a stale append / hide-bars flag (clear tlAppending or equivalent)"
            )
    for flag in dict.fromkeys(replace_flags):
        if _flag_cleared_on_append(select_fn, flag, append_param):
            wired = True
        if re.search(
            rf"\b{re.escape(flag)}\s*=\s*(?:true|!\s*{re.escape(append_param)})",
            select_fn,
        ):
            wired = True

    if load_calls_append and not wired:
        fail(
            "#203: Load older / selectPerson(..., true) must not show the "
            "timeline skeleton bars (set the append / tlAppending guard)"
        )


# #216 — focus rings + ARIA on chrome/dialogs (builds on #133; do not rewrite it).
_OWNED_RING_PRIMITIVES = (
    "web/lib/components/ui/button/button.svelte",
    "web/lib/components/ui/input/input.svelte",
)
_RAW_FOCUS_TAG = re.compile(r"<(button|input|textarea|select|summary)\b")
_HIDDEN_INPUT_TYPE = re.compile(
    r"""type\s*=\s*(?:["']hidden["']|\{\s*["']hidden["']\s*\})""",
    re.I,
)
_DIALOG_CLOSE_OPEN = re.compile(r"<(?:DialogPrimitive\.Close|Dialog\.Close)\b")
_COMMAND_INPUT_OPEN = re.compile(r"<(?:CommandPrimitive\.Input|Command\.Input)\b")
_COMMAND_ITEM_OPEN = re.compile(r"<(?:CommandPrimitive\.Item|Command\.Item)\b")
_TRAP_FOCUS_FALSE = re.compile(r"\btrapFocus\s*=\s*\{\s*false\s*\}")
_DOCS_FOCUS_RING = re.compile(r"focus[- ]?(?:visible[- ]?)?rings?", re.I)
_DOCS_KB_MERGE = re.compile(
    r"keyboard.{0,400}Merge|Merge.{0,400}keyboard",
    re.I | re.S,
)
_DOCS_KB_CONFIRM = re.compile(
    r"keyboard.{0,400}\bconfirm\b|\bconfirm\b.{0,400}keyboard",
    re.I | re.S,
)
_DOCS_KB_DISMISS = re.compile(
    r"keyboard.{0,400}\bdismiss\b|\bdismiss\b.{0,400}keyboard",
    re.I | re.S,
)
_DOCS_VOICE_SEEK_ANN = re.compile(
    r"(?:voice.{0,80}(?:seek|scrub)|(?:seek|scrub).{0,40}voice)"
    r".{0,200}announc"
    r"|announc.{0,200}"
    r"(?:voice.{0,80}(?:seek|scrub)|(?:seek|scrub).{0,40}voice)",
    re.I | re.S,
)


def _has_focus_visible_ring2(src: str) -> bool:
    """True when src has focus-visible:ring-2 and ring-ring (#216)."""
    return (
        bool(_A11Y_FOCUS_VISIBLE.search(src))
        and "focus-visible:ring-2" in src
        and "ring-ring" in src
    )


def _iter_raw_focus_tags(markup: str) -> list[str]:
    """Native <button>/<input>/<textarea>/<select>/<summary> opening tags."""
    out: list[str] = []
    for m in _RAW_FOCUS_TAG.finditer(markup):
        tag = _markup_open_tag(markup, m.start())
        if tag:
            out.append(tag)
    return out


def _iter_component_open_tags(markup: str, rx: re.Pattern[str]) -> list[str]:
    out: list[str] = []
    for m in rx.finditer(markup):
        tag = _markup_open_tag(markup, m.start())
        if tag:
            out.append(tag)
    return out


def _person_title_is_button(markup: str) -> bool:
    for m in re.finditer(r"\{personTitle\}", markup):
        tags = _ancestor_tags(markup, m.start(), limit=6)
        if any(_tag_name(t) == "button" for t in tags):
            return True
    return False


def _merge_ellipsis_is_button(src: str) -> bool:
    m = re.search(r">\s*Merge(?:…|\.\.\.)\s*<", src)
    if not m:
        return False
    found = _open_tag_before(src, m.start())
    if found and found[1].startswith("<Button"):
        return True
    for tag in _ancestor_tags(src, m.start(), limit=6):
        if tag.startswith("<Button"):
            return True
    return False


def assert_focus_aria_audit(crate: Path) -> None:
    """#216: visible focus rings + ARIA on chrome/dialogs (not a WCAG certificate)."""
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#216: App.svelte required (focus rings + ARIA on chrome/dialogs)")
    app = app_path.read_text()
    app_markup = _strip_html_comments(_svelte_markup(app))
    button_path = (
        crate / "web" / "lib" / "components" / "ui" / "button" / "button.svelte"
    )
    input_path = crate / "web" / "lib" / "components" / "ui" / "input" / "input.svelte"
    button_src = button_path.read_text() if button_path.is_file() else ""
    input_src = input_path.read_text() if input_path.is_file() else ""
    confirm_path = crate / "web" / "lib" / "ConfirmDialog.svelte"
    confirm_src = confirm_path.read_text() if confirm_path.is_file() else ""
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    cas = cas_path.read_text() if cas_path.is_file() else ""
    pal_path = crate / "web" / "lib" / "CommandPalette.svelte"
    pal = pal_path.read_text() if pal_path.is_file() else ""
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = search_path.read_text() if search_path.is_file() else ""
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    conf = (crate / "tauri.conf.json").read_text()

    # 1) Button + Input primitives still have focus-visible:ring-2 + ring-ring.
    if not button_path.is_file():
        fail("#216: owned Button primitive required (keep focus-visible:ring-2 ring-ring)")
    if not input_path.is_file():
        fail("#216: owned Input primitive required (keep focus-visible:ring-2 ring-ring)")
    if not _has_focus_visible_ring2(_without_comments(button_src)):
        fail(
            "#216: Button primitive must keep focus-visible:ring-2 ring-ring "
            "(do not drop visible focus on chrome)"
        )
    if not _has_focus_visible_ring2(_without_comments(input_src)):
        fail(
            "#216: Input primitive must keep focus-visible:ring-2 ring-ring "
            "(do not drop visible focus on fields)"
        )

    # 2) Product raw <button> / visible <input> / <textarea> / <select> /
    #    <summary> each have focus-visible:ring-2 + ring-ring on that tag
    #    (or are the owned Button/Input primitive).
    missing: list[str] = []
    seen: set[str] = set()
    for p in _product_svelte(crate):
        rel = p.relative_to(crate).as_posix()
        if rel in _OWNED_RING_PRIMITIVES:
            continue
        markup = _strip_html_comments(_svelte_markup(p.read_text()))
        for tag in _iter_raw_focus_tags(markup):
            name = _tag_name(tag)
            if name == "input" and _HIDDEN_INPUT_TYPE.search(tag):
                continue
            if _has_focus_visible_ring2(tag):
                continue
            key = f"{rel} <{name}>"
            if key in seen:
                continue
            seen.add(key)
            missing.append(key)
    if missing:
        shown = ", ".join(missing[:8])
        extra = f" (+{len(missing) - 8} more)" if len(missing) > 8 else ""
        fail(
            "#216: every product raw <button> / visible <input> / <textarea> / "
            "<select> / <summary> must have focus-visible:ring-2 ring-ring on "
            "that tag (or use the owned Button/Input primitive). Missing: "
            f"{shown}{extra}"
        )

    # 3) Dialog Close has the ring; Command.Input + Command.Item have the ring.
    close_tags: list[str] = []
    cmd_input_src = ""
    cmd_item_src = ""
    for p in _product_svelte(crate):
        markup = _strip_html_comments(_svelte_markup(p.read_text()))
        close_tags.extend(_iter_component_open_tags(markup, _DIALOG_CLOSE_OPEN))
        rel = p.relative_to(crate).as_posix()
        if rel.endswith("/command/command-input.svelte"):
            cmd_input_src = p.read_text()
        elif rel.endswith("/command/command-item.svelte"):
            cmd_item_src = p.read_text()
    if not close_tags:
        fail("#216: Dialog Close (X) must exist and have focus-visible:ring-2 ring-ring")
    if not any(_has_focus_visible_ring2(tag) for tag in close_tags):
        fail(
            "#216: Dialog Close must have focus-visible:ring-2 ring-ring "
            "on that tag"
        )
    if not cmd_input_src.strip():
        fail("#216: Command.Input primitive required (keep #215 command/)")
    if not _has_focus_visible_ring2(_without_comments(cmd_input_src)):
        fail("#216: Command.Input must have focus-visible:ring-2 ring-ring")
    if not cmd_item_src.strip():
        fail("#216: Command.Item primitive required (keep #215 command/)")
    if not _has_focus_visible_ring2(_without_comments(cmd_item_src)):
        fail("#216: Command.Item must have focus-visible:ring-2 ring-ring")

    # 4) ConfirmDialog + Merge dialog exist; no trapFocus={false}.
    if not confirm_path.is_file():
        fail("#216: ConfirmDialog.svelte required (focus stays trapped)")
    if not re.search(r"<Dialog\.Root\b", confirm_src):
        fail("#216: ConfirmDialog must use Dialog.Root (bits-ui trapFocus stays on)")
    if not re.search(r"<Dialog\.Root\b", app):
        fail("#216: Merge dialog required (Dialog.Root)")
    if not re.search(r"\bmergeOpen\b", app) and not re.search(r"Merge into", app):
        fail("#216: Merge dialog required")
    for p in _product_svelte(crate):
        cleaned = _without_comments(p.read_text())
        if _TRAP_FOCUS_FALSE.search(cleaned):
            fail(
                "#216: do not set trapFocus={false} "
                "(Confirm + Merge keep focus trapped until closed)"
            )

    # 5) data-voice-seek has aria-valuenow + a name (aria-label / labelled-by).
    if not cas_path.is_file():
        fail("#216: CasAttach.svelte required (voice seek aria-valuenow + name)")
    seek_at = cas.find("data-voice-seek")
    if seek_at < 0:
        fail("#216: data-voice-seek required (voice seek aria-valuenow + name)")
    seek_tag = _markup_open_tag(cas, cas.rfind("<", 0, seek_at + 1))
    if not seek_tag:
        fail("#216: data-voice-seek must sit on an input/range tag")
    if not re.search(r"\baria-valuenow\b", seek_tag, re.I):
        fail(
            "#216: data-voice-seek must set aria-valuenow "
            "(current time — same value as the range)"
        )
    if not _A11Y_ARIA_LABEL.search(seek_tag):
        fail(
            "#216: data-voice-seek must have an accessible name "
            "(aria-label or aria-labelledby)"
        )

    # 6) displayBody / message whitespace-pre-wrap <p>s are not aria-hidden.
    for p in _product_svelte(crate):
        markup = _strip_html_comments(_svelte_markup(p.read_text()))
        for m in re.finditer(r"<p\b", markup, re.I):
            tag = _markup_open_tag(markup, m.start())
            if not tag:
                continue
            close = markup.find("</p>", m.start())
            inner = markup[m.start() : close if close >= 0 else m.start() + 400]
            is_msg = "whitespace-pre-wrap" in tag or "displayBody" in inner
            if is_msg and re.search(r"\baria-hidden\b", tag, re.I):
                fail(
                    "#216: message displayBody / whitespace-pre-wrap <p>s "
                    "must not be aria-hidden "
                    f"({p.relative_to(crate).as_posix()})"
                )

    # 7) person-title is a <button>; Merge… is a Button; Confirm Cancel/confirm stay.
    if not _person_title_is_button(app_markup):
        fail(
            "#216: person-title must be a <button> "
            "(keyboard path to the inspector / Merge)"
        )
    if not _merge_ellipsis_is_button(app):
        fail("#216: Merge… must be a Button (owned primitive, keyboard confirm path)")
    if not re.search(r"<Button\b[^>]*>\s*Cancel", confirm_src):
        fail("#216: ConfirmDialog Cancel must stay a Button")
    if not (
        re.search(r"<Button\b[^>]*>\s*\{confirmLabel\}", confirm_src)
        or re.search(r"<Button\b[^>]{0,240}onclick=\{go\}", confirm_src)
    ):
        fail("#216: ConfirmDialog confirm must stay a Button")

    # 8) Docs: focus rings, keyboard Merge / confirm / dismiss, voice seek announced.
    if not dtxt.strip():
        fail(
            "#216: docs/user/app.md required — visible focus rings, "
            "keyboard Merge / confirm / dismiss, voice seek announced"
        )
    if not _DOCS_FOCUS_RING.search(dtxt):
        fail(
            "#216: docs/user/app.md must mention visible focus rings "
            "on chrome/dialogs"
        )
    if not _DOCS_KB_MERGE.search(dtxt):
        fail(
            "#216: docs/user/app.md must say keyboard can open Merge, "
            "confirm, and dismiss"
        )
    if not _DOCS_KB_CONFIRM.search(dtxt):
        fail(
            "#216: docs/user/app.md must say keyboard can confirm "
            "(Merge / ConfirmDialog)"
        )
    if not _DOCS_KB_DISMISS.search(dtxt):
        fail(
            "#216: docs/user/app.md must say keyboard can dismiss "
            "Merge / confirm"
        )
    if not _DOCS_VOICE_SEEK_ANN.search(dtxt):
        fail("#216: docs/user/app.md must say voice seek is announced")

    # 9) Docs must not claim WCAG certified / certificate.
    if _A11Y_WCAG_CERT.search(dtxt):
        fail(
            "#216: docs/user/app.md must not claim WCAG certified / certificate "
            "(reuse #133 — this is a focus/ARIA audit, not a certificate)"
        )

    # 10) Do not soften #133 listbox/article, #q, sidebar, overlay, inspector,
    #     CSP, #215 data-command-palette.
    if not re.search(r"""\brole\s*=\s*["']listbox["']""", app):
        fail('#216: keep people role="listbox" (#133)')
    if not re.search(r"""\brole\s*=\s*["']option["']""", app):
        fail('#216: keep people role="option" (#133)')
    if not re.search(r"<article\b", app):
        fail("#216: keep timeline <article> (#133)")
    if not re.search(r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""", search):
        fail('#216: keep id="q" as the canonical query field (#208)')
    if not re.search(r"\bdata-people-sidebar\b", app):
        fail("#216: keep data-people-sidebar (#159 / #212)")
    if not re.search(r"\bdata-person-inspector\b", app):
        fail("#216: keep data-person-inspector (#213)")
    if not re.search(r"titleBarStyle", conf) and not re.search(
        r"\bdata-tauri-drag-region\b", app
    ):
        fail("#216: keep the overlay titlebar (#211)")
    if CSP not in conf:
        fail("#216: do not soften tauri CSP")
    if not re.search(r"\bdata-command-palette\b", app + "\n" + pal):
        fail("#216: keep data-command-palette (#215)")
_CONTRAST_SEARCH_MARK_VAR = re.compile(
    r"var\(\s*--(?:color-)?search-mark\s*\)",
    re.I,
)
_CONTRAST_MARK_FOREGROUND = re.compile(
    r"color\s*:\s*var\(\s*--(?:color-)?foreground\s*\)",
    re.I,
)
_CONTRAST_TOKEN_CLASS = re.compile(
    r"(?<![\w-])(?:text-muted-foreground|bg-muted|bg-background|"
    r"text-foreground|border-border|"
    r"bg-warning|text-warning|text-warning-foreground|border-warning|"
    r"bg-success|text-success|text-success-foreground|border-success|"
    r"status-warning|status-success)(?![\w-])"
)
_CONTRAST_THEME_PICKER = re.compile(
    r"("
    r"\bdata-theme\b"
    r"|theme-picker"
    r"|Theme menu"
    r"|Appearance menu"
    r"|high-contrast"
    r"|highContrast"
    r")",
    re.I,
)
_CONTRAST_DOCS_NO_RELOAD = re.compile(
    r"("
    r"without (?:a |an )?(?:reload|restart|relaunch)"
    r"|no reload"
    r"|does not (?:require|need) (?:a )?(?:reload|restart|relaunch)"
    r"|updates?(?: the (?:app|chrome|window))? without (?:a )?(?:reload|restart)"
    r")",
    re.I,
)
_CONTRAST_DOCS_READABLE = re.compile(
    r"("
    r"readable.{0,80}(?:on both|in both|light and dark|both (?:light|appearances|modes))"
    r"|(?:on both|light and dark|both (?:appearances|modes)).{0,80}readable"
    r"|preview.{0,80}readable"
    r")",
    re.I | re.S,
)
_CONTRAST_DOCS_MARKS = re.compile(
    r"("
    r"(?:search[- ]?)?marks?.{0,100}"
    r"(?:still work|on both|light and dark|both (?:appearances|modes)|stay yellow|yellow-enough)"
    r"|(?:yellow|highlighted).{0,80}mark.{0,80}"
    r"(?:both|light and dark|still work|without.{0,20}reload)"
    r")",
    re.I | re.S,
)


def _search_mark_rule_bodies(css: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(r"\.search-mark\b[^{]*\{", css):
        body = _css_brace_body(css, css.find("{", m.start()))
        if body:
            out.append(body)
    return out


def _contrast_tag_ok(tag: str) -> bool:
    if not tag:
        return False
    surface = _hue_surface(tag)
    if _HUE_AMBER.search(surface) or _HUE_YELLOW.search(surface):
        return False
    return bool(_CONTRAST_TOKEN_CLASS.search(tag))


def assert_contrast_tokens(crate: Path) -> None:
    """#217: light + dark contrast via tokens (not a third theme / WCAG cert)."""
    svelte_files = _product_svelte(crate)
    if not svelte_files:
        fail("#217: crates/interlace-tauri/web/**/*.svelte required (contrast tokens)")

    # 1) No text-amber-900 / amber-* / yellow-* in product Svelte (#198 finder).
    offenders: list[str] = []
    for p in svelte_files:
        hits = [
            h
            for h in _hue_findings(p.read_text())
            if h.startswith("amber") or h.startswith("yellow")
        ]
        if hits:
            offenders.append(f"{p.relative_to(crate)}: {'; '.join(hits)}")
    if offenders:
        fail(
            "#217: product Svelte must not contain text-amber-900 / amber-* / "
            "yellow-* (CSS variables only; reuse #198). Found:\n  "
            + "\n  ".join(offenders)
        )

    css_path = crate / "web" / "app.css"
    if not css_path.is_file():
        fail("#217: web/app.css required (light/dark contrast tokens)")
    css = css_path.read_text()
    light_blob = _contrast_light_blob(css)
    dark_blob = _contrast_dark_blob(css)

    # 2) Light --color-muted-foreground L ≤ 40; dark (prefers-color-scheme) L ≥ 62.
    light_muted = _css_var(light_blob, ("--color-muted-foreground",))
    if not light_muted:
        fail(
            "#217: light --color-muted-foreground required in @theme / "
            "non-dark :root (do not make tokens dark-only)"
        )
    light_hsl = _hsl_tuple(light_muted)
    if not light_hsl:
        fail(
            "#217: light --color-muted-foreground must be HSL so lightness "
            "can be checked (≤ 40)"
        )
    if light_hsl[2] > 40:
        fail(
            "#217: light --color-muted-foreground HSL lightness must be ≤ 40 "
            "(@theme / non-dark :root) so people preview and chips stay "
            f"readable; found L={light_hsl[2]:g}"
        )
    dark_muted = _css_var(dark_blob, ("--color-muted-foreground",))
    if not dark_muted:
        fail(
            "#217: dark --color-muted-foreground required inside "
            "@media (prefers-color-scheme: dark)"
        )
    dark_hsl = _hsl_tuple(dark_muted)
    if not dark_hsl:
        fail(
            "#217: dark --color-muted-foreground must be HSL so lightness "
            "can be checked (≥ 62)"
        )
    if dark_hsl[2] < 62:
        fail(
            "#217: dark --color-muted-foreground HSL lightness must be ≥ 62 "
            "(inside prefers-color-scheme: dark); "
            f"found L={dark_hsl[2]:g}"
        )

    # 3) --search-mark or --color-search-mark in light + dark; .search-mark
    #    uses the var; both hues 40–60 (yellow-enough). Keep foreground color.
    light_mark = _css_var(light_blob, _CONTRAST_SEARCH_MARK_NAMES)
    dark_mark = _css_var(dark_blob, _CONTRAST_SEARCH_MARK_NAMES)
    if not light_mark:
        fail(
            "#217: define --search-mark or --color-search-mark for light "
            "(@theme / :root) — .search-mark must not be a one-off hsl"
        )
    if not dark_mark:
        fail(
            "#217: define --search-mark or --color-search-mark inside "
            "@media (prefers-color-scheme: dark)"
        )
    mark_rules = _search_mark_rule_bodies(css)
    if not mark_rules:
        fail("#217: .search-mark rule required (named search-mark token)")
    if not any(_CONTRAST_SEARCH_MARK_VAR.search(body) for body in mark_rules):
        fail(
            "#217: .search-mark must use var(--search-mark) or "
            "var(--color-search-mark) (not a one-off hsl)"
        )
    if not any(_CONTRAST_MARK_FOREGROUND.search(body) for body in mark_rules):
        fail(
            "#217: .search-mark must keep color: var(--color-foreground) "
            "(or --foreground)"
        )
    light_mark_hsl = _hsl_tuple(light_mark)
    dark_mark_hsl = _hsl_tuple(dark_mark)
    if not light_mark_hsl or not dark_mark_hsl:
        fail(
            "#217: --search-mark / --color-search-mark must be HSL "
            "(hue 40–60, yellow-enough on both)"
        )
    if not (40 <= light_mark_hsl[0] <= 60):
        fail(
            "#217: light search-mark hue must be 40–60 (yellow-enough); "
            f"found H={light_mark_hsl[0]:g}"
        )
    if not (40 <= dark_mark_hsl[0] <= 60):
        fail(
            "#217: dark search-mark hue must be 40–60 (yellow-enough); "
            f"found H={dark_mark_hsl[0]:g}"
        )

    # 4) color-scheme: light dark on :root or html; dark media still overrides.
    if not _CONTRAST_COLOR_SCHEME.search(css):
        fail(
            "#217: :root or html must set color-scheme: light dark "
            "(macOS appearance flips the app without a reload)"
        )
    if not dark_blob.strip():
        fail(
            "#217: keep @media (prefers-color-scheme: dark) so tokens "
            "still override in dark"
        )
    if not _css_var(dark_blob, ("--color-background", "--color-foreground", "--color-muted-foreground")):
        fail(
            "#217: prefers-color-scheme: dark must still override tokens "
            "(background / foreground / muted-foreground)"
        )

    # 5) Preview / chips / cloud / toast / doctor issue box stay on tokens.
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#217: App.svelte required (people preview / chips / banners)")
    app = app_path.read_text()
    toast_path = crate / "web" / "lib" / "components" / "ui" / "toast" / "toast.svelte"
    toast_src = toast_path.read_text() if toast_path.is_file() else ""
    doctor_path = crate / "web" / "lib" / "DoctorPane.svelte"
    doctor_src = doctor_path.read_text() if doctor_path.is_file() else ""
    svelte_blob = "\n".join(p.read_text() for p in svelte_files)

    preview_tag = ""
    for src in (app, svelte_blob):
        m = re.search(r"\{p\.preview\b", src)
        if not m:
            continue
        found = _open_tag_before(src, m.start())
        if found:
            preview_tag = found[1]
        for tag in _ancestor_tags(src, m.start(), limit=6):
            if _CONTRAST_TOKEN_CLASS.search(tag):
                preview_tag = tag
                break
        if preview_tag:
            break
    if not preview_tag:
        fail(
            "#217: people preview / last-activity line required "
            "(token classes, not raw amber)"
        )
    if not _contrast_tag_ok(preview_tag):
        fail(
            "#217: people preview / last-activity line must use token classes "
            "(text-muted-foreground / bg-muted / bg-background / "
            "text-foreground / border-border), not raw amber"
        )

    chip_tag = _contrast_surface_tag(svelte_blob, "data-platform-chip")
    if not chip_tag:
        fail("#217: data-platform-chip required (token classes, not raw amber)")
    if not _contrast_tag_ok(chip_tag):
        fail(
            "#217: data-platform-chip must use token classes "
            "(text-muted-foreground / bg-muted / bg-background / "
            "text-foreground / border-border), not raw amber"
        )

    cloud_tag = _contrast_surface_tag(app, "data-cloud-warning")
    if not cloud_tag:
        fail("#217: data-cloud-warning required (token classes, not raw amber)")
    if not _contrast_tag_ok(cloud_tag):
        fail(
            "#217: data-cloud-warning must use token classes "
            "(text-muted-foreground / bg-muted / bg-background / "
            "text-foreground / border-border), not raw amber"
        )

    toast_tag = _contrast_surface_tag(toast_src or svelte_blob, "data-toast")
    if not toast_tag:
        fail("#217: data-toast required (token classes, not raw amber)")
    if not _contrast_tag_ok(toast_tag):
        fail(
            "#217: data-toast must use token classes "
            "(text-muted-foreground / bg-muted / bg-background / "
            "text-foreground / border-border), not raw amber"
        )

    doctor_box = ""
    for src in (app, doctor_src):
        at = src.find("Doctor found")
        if at < 0:
            continue
        for tag in _ancestor_tags(src, at, limit=8):
            if _CONTRAST_TOKEN_CLASS.search(tag) or re.search(
                r"\b(?:rounded-md|border|bg-)\b", tag
            ):
                doctor_box = tag
                break
        if doctor_box:
            break
    if not doctor_box:
        fail("#217: doctor issue box required (token classes, not raw amber)")
    if not _contrast_tag_ok(doctor_box):
        fail(
            "#217: doctor issue box must use token classes "
            "(text-muted-foreground / bg-muted / bg-background / "
            "text-foreground / border-border), not raw amber"
        )

    # 6) No Theme menu / data-theme / high-contrast third theme; light tokens stay.
    if _CONTRAST_THEME_PICKER.search(svelte_blob):
        fail(
            "#217: not in scope — no Theme menu / data-theme / high-contrast "
            "third theme (system appearance only; #218 is later)"
        )
    if not light_blob.strip() or not _css_var(
        light_blob,
        ("--color-background", "--color-foreground", "--color-muted-foreground"),
    ):
        fail(
            "#217: light @theme / :root tokens must still exist "
            "(do not force dark-only)"
        )

    # 8) Docs: system light/dark without a reload; readable on both; marks work.
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    if not dtxt.strip():
        fail(
            "#217: docs/user/app.md required — system light/dark without a "
            "reload; readable on both; marks still work"
        )
    if not _CONTRAST_DOCS_SYSTEM.search(dtxt):
        fail(
            "#217: docs/user/app.md must say chrome follows system light/dark"
        )
    if not _CONTRAST_DOCS_NO_RELOAD.search(dtxt):
        fail(
            "#217: docs/user/app.md must say appearance updates without a reload"
        )
    if not _CONTRAST_DOCS_READABLE.search(dtxt):
        fail(
            "#217: docs/user/app.md must say preview / chips / marks / banners "
            "stay readable on both"
        )
    if not _CONTRAST_DOCS_MARKS.search(dtxt):
        fail(
            "#217: docs/user/app.md must say search marks still work on both"
        )
    if _A11Y_WCAG_CERT.search(dtxt):
        fail(
            "#217: docs/user/app.md must not claim WCAG certified / certificate"
        )

    # 9) Do not soften #q, sidebar, overlay, inspector, CSP, #198, #216 rings.
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = search_path.read_text() if search_path.is_file() else ""
    conf = (crate / "tauri.conf.json").read_text()
    if not re.search(r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""", search):
        fail('#217: keep id="q" as the canonical query field (#208)')
    if not re.search(r"\bdata-people-sidebar\b", app):
        fail("#217: keep data-people-sidebar (#159 / #212)")
    if not re.search(r"titleBarStyle", conf) and not re.search(
        r"\bdata-tauri-drag-region\b", app
    ):
        fail("#217: keep the overlay titlebar (#211)")
    if not re.search(r"\bdata-person-inspector\b", app):
        fail("#217: keep data-person-inspector (#213)")
    if CSP not in conf:
        fail("#217: do not soften tauri CSP")
    missing_defs = [name for name in _SHADCN_TOKEN_DEFS if name not in css]
    if missing_defs:
        fail(
            "#217: keep #198 shadcn tokens "
            f"({', '.join(missing_defs)} missing)"
        )
    missing_uses = [tok for tok in _SHADCN_TOKEN_USES if tok not in svelte_blob]
    if missing_uses:
        fail(
            "#217: keep #198 token/variable classes "
            f"({', '.join(missing_uses)} missing)"
        )
    button_path = (
        crate / "web" / "lib" / "components" / "ui" / "button" / "button.svelte"
    )
    input_path = crate / "web" / "lib" / "components" / "ui" / "input" / "input.svelte"
    if not button_path.is_file() or not _has_focus_visible_ring2(
        _without_comments(button_path.read_text())
    ):
        fail("#217: keep #216 Button focus-visible:ring-2 ring-ring")
    if not input_path.is_file() or not _has_focus_visible_ring2(
        _without_comments(input_path.read_text())
    ):
        fail("#217: keep #216 Input focus-visible:ring-2 ring-ring")
_APPEARANCE_SCRIM_VAR = re.compile(
    r"var\(\s*--(?:overlay|scrim|lightbox-scrim)\s*\)",
    re.I,
)
_APPEARANCE_THEME_HTTP = re.compile(
    r"("
    r"(?:theme|appearance|stylesheet)[^;\n]{0,100}https://"
    r"|https://[^;\n]{0,100}(?:theme|appearance|stylesheet)"
    r"|@import\s+(?:url\s*\(\s*)?['\"]https?://"
    r")",
    re.I,
)
_APPEARANCE_BLACK_WASH = re.compile(
    r"(?<![\w-])(?:bg-)?black/(?:50|70|80)(?![\w-])"
)
_APPEARANCE_DOCS_MATCH = re.compile(
    r"("
    r"(?:lightbox|dialogs?).{0,120}(?:lightbox|dialogs?).{0,80}"
    r"(?:match|same (?:tokens?|variables?)|follow)"
    r"|(?:lightbox|dialogs?).{0,80}"
    r"(?:match|same (?:tokens?|variables?)).{0,80}"
    r"(?:lightbox|dialogs?)"
    r")",
    re.I | re.S,
)


def _appearance_tag_uses_scrim(tag: str, css: str) -> bool:
    if _APPEARANCE_SCRIM_VAR.search(tag):
        return True
    for cls in _appearance_class_names(tag):
        for m in re.finditer(rf"\.{re.escape(cls)}\b[^{{]*\{{", css):
            body = _css_brace_body(css, css.find("{", m.start()))
            if body and _APPEARANCE_SCRIM_VAR.search(body):
                return True
    return False


def _photo_lightbox_rule_bodies(css: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(r"\.photo-lightbox\b[^{]*\{", css):
        body = _css_brace_body(css, css.find("{", m.start()))
        if body:
            out.append(body)
    return out


def _appearance_overlay_tag(dialog_src: str) -> str:
    m = re.search(r"Dialog(?:Primitive)?\.Overlay\b", dialog_src)
    if not m:
        return ""
    return _markup_open_tag(dialog_src, dialog_src.rfind("<", 0, m.start() + 1))


def assert_appearance_os(crate: Path) -> None:
    """#218: OS appearance only — named overlay/scrim, no Theme menu / network theme."""
    svelte_files = _product_svelte(crate)
    if not svelte_files:
        fail("#218: crates/interlace-tauri/web/**/*.svelte required (OS appearance)")

    svelte_blob = "\n".join(p.read_text() for p in svelte_files)
    rust_path = crate / "src" / "main.rs"
    rust = rust_path.read_text() if rust_path.is_file() else ""
    css_path = crate / "web" / "app.css"
    if not css_path.is_file():
        fail("#218: web/app.css required (named overlay / lightbox scrim)")
    css = css_path.read_text()
    index_path = crate / "index.html"
    index = index_path.read_text() if index_path.is_file() else ""

    # 1) No Theme / Appearance menu / data-theme / theme-picker.
    theme_hits: list[str] = []
    for p in svelte_files:
        surface = _hue_surface(p.read_text())
        if _APPEARANCE_THEME_UI.search(surface) or _APPEARANCE_MENU_LABEL.search(surface):
            theme_hits.append(str(p.relative_to(crate)))
    rust_surface = _without_comments(rust)
    if _APPEARANCE_THEME_UI.search(rust_surface) or _APPEARANCE_MENU_LABEL.search(
        rust_surface
    ):
        theme_hits.append("src/main.rs")
    if theme_hits:
        fail(
            "#218: no Theme / Appearance menu / data-theme / theme-picker "
            "(system appearance is the only switch). Found in: "
            + ", ".join(theme_hits)
        )

    # 2) No fetch( / HTTP / https:// theme load.
    net_blob = (
        _hue_surface(svelte_blob)
        + "\n"
        + _css_without_comments(css)
        + "\n"
        + _without_comments(index)
        + "\n"
        + rust_surface
    )
    if _APPEARANCE_FETCH.search(net_blob):
        fail(
            "#218: do not fetch( a theme — appearance is OS-only "
            "(no HTTP theme load)"
        )
    if _THEME_CDN.search(net_blob) or _APPEARANCE_THEME_HTTP.search(net_blob):
        fail(
            "#218: do not load a theme from https:// / CDN / @import "
            "(system appearance only)"
        )

    # 3) --overlay or --scrim / --lightbox-scrim; dialog + .photo-lightbox use var(...).
    if not _css_var(css, _APPEARANCE_SCRIM_NAMES):
        fail(
            "#218: app.css must define --overlay or --scrim / --lightbox-scrim "
            "so dialog overlay and .photo-lightbox use var(...) "
            "(not bg-black/50 or a one-off hsl scrim)"
        )
    lightbox_rules = _photo_lightbox_rule_bodies(css)
    if not lightbox_rules:
        fail("#218: .photo-lightbox rule required (named overlay / lightbox scrim)")
    if not any(_APPEARANCE_SCRIM_VAR.search(body) for body in lightbox_rules):
        fail(
            "#218: .photo-lightbox must use var(--overlay) / var(--scrim) / "
            "var(--lightbox-scrim) (not a one-off hsl scrim)"
        )
    dialog_path = (
        crate / "web" / "lib" / "components" / "ui" / "dialog" / "dialog-content.svelte"
    )
    if not dialog_path.is_file():
        fail("#218: dialog-content.svelte required (dialog overlay uses var(...))")
    dialog_src = dialog_path.read_text()
    overlay_tag = _appearance_overlay_tag(dialog_src)
    if not overlay_tag:
        fail(
            "#218: Dialog overlay (DialogPrimitive.Overlay) required "
            "(use var(--overlay) / var(--scrim) / var(--lightbox-scrim))"
        )
    if not _appearance_tag_uses_scrim(overlay_tag, css):
        fail(
            "#218: dialog overlay (dialog-content.svelte) must use "
            "var(--overlay) / var(--scrim) / var(--lightbox-scrim)"
        )

    # 4) No bg-black/50 / black/70 / bg-black/80 on overlay or lightbox buttons.
    if _APPEARANCE_BLACK_WASH.search(overlay_tag):
        fail(
            "#218: Dialog overlay must not use bg-black/50 / black/70 / "
            "bg-black/80 (use the named overlay / scrim token)"
        )
    cas_path = crate / "web" / "lib" / "CasAttach.svelte"
    if not cas_path.is_file():
        fail("#218: CasAttach.svelte required (lightbox buttons, no bg-black/50)")
    cas = cas_path.read_text()
    wash_hits: list[str] = []
    for hook in ("data-lightbox-close", "data-lightbox-prev", "data-lightbox-next"):
        at = cas.find(hook)
        if at < 0:
            continue
        tag = _markup_open_tag(cas, cas.rfind("<", 0, at + 1))
        if _APPEARANCE_BLACK_WASH.search(tag):
            wash_hits.append(hook)
    if wash_hits:
        fail(
            "#218: lightbox buttons (CasAttach.svelte) must not use "
            "bg-black/50 / black/70 / bg-black/80 "
            "(use a CSS class from app.css). Found on: "
            + ", ".join(wash_hits)
        )

    # 5) Toast stays bg-background + text-foreground.
    toast_path = crate / "web" / "lib" / "components" / "ui" / "toast" / "toast.svelte"
    toast_src = toast_path.read_text() if toast_path.is_file() else ""
    toast_tag = _contrast_surface_tag(toast_src or svelte_blob, "data-toast")
    if not toast_tag:
        fail("#218: data-toast required (bg-background + text-foreground)")
    if "bg-background" not in toast_tag or "text-foreground" not in toast_tag:
        fail(
            "#218: data-toast must use bg-background and text-foreground "
            "(same tokens as the rest of chrome)"
        )

    # 6) Boot splash still flips on prefers-color-scheme: dark.
    if not index.strip():
        fail("#218: index.html required (keep prefers-color-scheme: dark on the splash)")
    if not re.search(r"prefers-color-scheme\s*:\s*dark", index):
        fail(
            "#218: index.html must keep prefers-color-scheme: dark "
            "(splash matches OS before JS)"
        )

    # 7) Keep color-scheme: light dark + dark media token overrides.
    if not _CONTRAST_COLOR_SCHEME.search(css):
        fail(
            "#218: keep color-scheme: light dark on :root / html "
            "(#217; OS appearance flips without a reload)"
        )
    dark_blob = _contrast_dark_blob(css)
    if not dark_blob.strip():
        fail("#218: keep @media (prefers-color-scheme: dark) token overrides")
    if not _css_var(
        dark_blob,
        ("--color-background", "--color-foreground", "--color-muted-foreground"),
    ):
        fail(
            "#218: prefers-color-scheme: dark must still override tokens "
            "(background / foreground / muted-foreground)"
        )

    # 8) Docs: follow OS; dark archival; lightbox + dialogs match; no Theme menu.
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    if not dtxt.strip():
        fail(
            "#218: docs/user/app.md required — follow OS / system appearance; "
            "dark archival look; lightbox + dialogs match; no Theme menu"
        )
    if not _CONTRAST_DOCS_SYSTEM.search(dtxt):
        fail(
            "#218: docs/user/app.md must say the app follows OS / system appearance"
        )
    if not _APPEARANCE_DOCS_ARCHIVAL.search(dtxt):
        fail(
            "#218: docs/user/app.md must say dark is the intended archival look"
        )
    if not _APPEARANCE_DOCS_MATCH.search(dtxt):
        fail(
            "#218: docs/user/app.md must say lightbox and dialogs match "
            "(same tokens / appearance)"
        )
    if not _APPEARANCE_DOCS_NO_THEME.search(dtxt):
        fail("#218: docs/user/app.md must say there is no Theme menu")

    # 10) Do not soften #q, sidebar, overlay titlebar, inspector, CSP, #217.
    app_path = crate / "web" / "App.svelte"
    app = app_path.read_text() if app_path.is_file() else ""
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = search_path.read_text() if search_path.is_file() else ""
    conf = (crate / "tauri.conf.json").read_text()
    if not re.search(r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""", search):
        fail('#218: keep id="q" as the canonical query field (#208)')
    if not re.search(r"\bdata-people-sidebar\b", app):
        fail("#218: keep data-people-sidebar (#159 / #212)")
    if not re.search(r"titleBarStyle", conf) and not re.search(
        r"\bdata-tauri-drag-region\b", app
    ):
        fail("#218: keep the overlay titlebar (#211)")
    if not re.search(r"\bdata-person-inspector\b", app):
        fail("#218: keep data-person-inspector (#213)")
    if CSP not in conf:
        fail("#218: do not soften tauri CSP")
    light_blob = _contrast_light_blob(css)
    light_muted = _css_var(light_blob, ("--color-muted-foreground",))
    light_hsl = _hsl_tuple(light_muted) if light_muted else None
    if not light_hsl or light_hsl[2] > 40:
        fail(
            "#218: keep #217 light --color-muted-foreground HSL L ≤ 40 "
            "(@theme / non-dark :root)"
        )
    dark_muted = _css_var(dark_blob, ("--color-muted-foreground",))
    dark_hsl = _hsl_tuple(dark_muted) if dark_muted else None
    if not dark_hsl or dark_hsl[2] < 62:
        fail(
            "#218: keep #217 dark --color-muted-foreground HSL L ≥ 62 "
            "(inside prefers-color-scheme: dark)"
        )
    if not _css_var(light_blob, _CONTRAST_SEARCH_MARK_NAMES) or not _css_var(
        dark_blob, _CONTRAST_SEARCH_MARK_NAMES
    ):
        fail("#218: keep #217 --search-mark / --color-search-mark on both sides")
    mark_rules = _search_mark_rule_bodies(css)
    if not mark_rules or not any(
        _CONTRAST_SEARCH_MARK_VAR.search(body) for body in mark_rules
    ):
        fail("#218: keep #217 .search-mark on var(--search-mark)")
_STATUS_WARNING_FG_NAMES = ("--warning-foreground", "--color-warning-foreground")
_STATUS_SUCCESS_NAMES = ("--success", "--color-success")
_STATUS_SUCCESS_FG_NAMES = ("--success-foreground", "--color-success-foreground")
_STATUS_WARNING_USE = re.compile(
    r"("
    r"(?<![\w-])(?:bg-warning|text-warning|text-warning-foreground|"
    r"border-warning|status-warning)(?![\w-])"
    r"|var\(\s*--(?:color-)?warning(?:-foreground)?\s*\)"
    r")"
)
_STATUS_SUCCESS_USE = re.compile(
    r"("
    r"(?<![\w-])(?:bg-success|text-success|text-success-foreground|"
    r"border-success|status-success)(?![\w-])"
    r"|var\(\s*--(?:color-)?success(?:-foreground)?\s*\)"
    r")"
)
_STATUS_MUTED_USE = re.compile(
    r"(?<![\w-])(?:text-muted-foreground|bg-muted|bg-background|"
    r"text-foreground|border-border)(?![\w-])"
)
_STATUS_RAW_HUE = re.compile(r"(?<![\w-])(?:amber|yellow|emerald|green)-\d+")
_STATUS_AUDIO_CTOR = re.compile(r"\bAudio\s*\(")
_STATUS_SVELTE_TRANSITION = re.compile(r"\b(?:transition|in|out)\s*:\s*([A-Za-z_]\w*)")
_STATUS_DOCS_WARNING = re.compile(
    r"("
    r"warning token"
    r"|--(?:color-)?warning"
    r"|(?:cloud|doctor).{0,120}warning token"
    r"|warnings?.{0,80}warning token"
    r")",
    re.I | re.S,
)
_STATUS_DOCS_QUIET_DONE = re.compile(
    r"("
    r"import done.{0,100}(?:quiet|muted|success)"
    r"|(?:quiet|muted|success).{0,80}import done"
    r"|import (?:done|success).{0,80}(?:quiet|muted|success token)"
    r"|quiet import done"
    r")",
    re.I | re.S,
)
_STATUS_TOAST_FADE_180 = re.compile(
    r"transition\s*:\s*fade\s*=\s*\{\{?\s*duration\s*:\s*180\s*\}"
)


def _status_selector_bodies(css: str, hook: str) -> list[str]:
    """Rule bodies whose selector mentions a data-* hook or a .class."""
    if hook.startswith("data-"):
        sel = rf"\[{re.escape(hook)}\]"
    else:
        sel = rf"\.{re.escape(hook)}\b"
    out: list[str] = []
    for m in re.finditer(rf"{sel}[^{{]*\{{", css):
        body = _css_brace_body(css, css.find("{", m.start()))
        if body:
            out.append(body)
    return out


def _status_surface_uses(
    blob: str,
    css: str,
    use_rx: re.Pattern[str],
    names: tuple[str, ...],
    hooks: tuple[str, ...] = (),
) -> bool:
    if use_rx.search(blob):
        return True
    for hook in hooks:
        for body in _status_selector_bodies(css, hook):
            if use_rx.search(body) or _css_var(body, names):
                return True
    for cls in _appearance_class_names(blob):
        if use_rx.search(cls):
            return True
        for body in _status_selector_bodies(css, cls):
            if use_rx.search(body) or _css_var(body, names):
                return True
    return False


def _status_doctor_box(src: str) -> str:
    """Non-partial doctor issues card (App 'Doctor found' / DoctorPane list)."""
    for needle in ("Doctor found issues", "Doctor found", "{#each issues"):
        at = src.find(needle)
        if at < 0:
            continue
        for tag in _ancestor_tags(src, at, limit=8):
            if "data-partial" in tag:
                continue
            if (
                _CONTRAST_TOKEN_CLASS.search(tag)
                or _STATUS_WARNING_USE.search(tag)
                or re.search(r"\b(?:rounded-md|border|bg-)\b", tag)
            ):
                return tag
    return ""


def _status_require_pair(
    light_blob: str,
    dark_blob: str,
    names: tuple[str, ...],
    fg_names: tuple[str, ...],
    *,
    label: str,
    hue_lo: float,
    hue_hi: float,
) -> None:
    pretty = " / ".join(names)
    pretty_fg = " / ".join(fg_names)
    light = _css_var(light_blob, names)
    if not light:
        fail(
            f"#219: {pretty} required in light (@theme / non-dark :root)"
        )
    dark = _css_var(dark_blob, names)
    if not dark:
        fail(
            f"#219: {pretty} required inside "
            "@media (prefers-color-scheme: dark)"
        )
    light_fg = _css_var(light_blob, fg_names)
    if not light_fg:
        fail(
            f"#219: {pretty_fg} required in light (@theme / non-dark :root)"
        )
    dark_fg = _css_var(dark_blob, fg_names)
    if not dark_fg:
        fail(
            f"#219: {pretty_fg} required inside "
            "@media (prefers-color-scheme: dark)"
        )
    for side, val in (
        ("light", light),
        ("dark", dark),
        ("light foreground", light_fg),
        ("dark foreground", dark_fg),
    ):
        if not _hsl_tuple(val):
            fail(f"#219: {label} tokens must be HSL ({side})")
    light_hsl = _hsl_tuple(light)
    dark_hsl = _hsl_tuple(dark)
    if light_hsl is None or dark_hsl is None:
        fail(f"#219: {label} tokens must be HSL (hue {hue_lo:g}–{hue_hi:g})")
    if not (hue_lo <= light_hsl[0] <= hue_hi):
        fail(
            f"#219: light {pretty} hue must be {hue_lo:g}–{hue_hi:g}; "
            f"found H={light_hsl[0]:g}"
        )
    if not (hue_lo <= dark_hsl[0] <= hue_hi):
        fail(
            f"#219: dark {pretty} hue must be {hue_lo:g}–{hue_hi:g}; "
            f"found H={dark_hsl[0]:g}"
        )


def assert_status_tokens(crate: Path) -> None:
    """#219: status colors via tokens (warning / optional success; no raw amber)."""
    svelte_files = _product_svelte(crate)
    if not svelte_files:
        fail("#219: crates/interlace-tauri/web/**/*.svelte required (status tokens)")

    css_path = crate / "web" / "app.css"
    if not css_path.is_file():
        fail("#219: web/app.css required (warning / success status tokens)")
    css = css_path.read_text()
    light_blob = _contrast_light_blob(css)
    dark_blob = _contrast_dark_blob(css)
    svelte_blob = "\n".join(p.read_text() for p in svelte_files)

    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#219: App.svelte required (cloud banner + Doctor found box)")
    app = app_path.read_text()
    doctor_path = crate / "web" / "lib" / "DoctorPane.svelte"
    if not doctor_path.is_file():
        fail("#219: DoctorPane.svelte required (issues card uses warning token)")
    doctor_src = doctor_path.read_text()
    import_path = crate / "web" / "lib" / "ImportPane.svelte"
    import_src = import_path.read_text() if import_path.is_file() else ""

    # 1) --warning / --color-warning + foreground pair in light and dark; HSL;
    #    warning hue 30–55 both sides.
    _status_require_pair(
        light_blob,
        dark_blob,
        _STATUS_WARNING_NAMES,
        _STATUS_WARNING_FG_NAMES,
        label="warning",
        hue_lo=30,
        hue_hi=55,
    )

    # 2) If import-done uses success (not muted): --success pair both sides;
    #    HSL; hue 120–160. Missing success is OK when check 5 stays muted.
    done_src = ""
    done_tag = ""
    for src in (import_src, app, svelte_blob):
        tag = _contrast_surface_tag(src, "data-import-done")
        if tag:
            done_src = src
            done_tag = tag
            break
    done_blob = (
        _status_hook_blob(done_src, "data-import-done") if done_src else done_tag
    )
    done_uses_success = _status_surface_uses(
        done_blob,
        css,
        _STATUS_SUCCESS_USE,
        _STATUS_SUCCESS_NAMES,
        ("data-import-done", "status-success"),
    )
    done_uses_muted = bool(_STATUS_MUTED_USE.search(done_blob))
    if done_uses_success:
        _status_require_pair(
            light_blob,
            dark_blob,
            _STATUS_SUCCESS_NAMES,
            _STATUS_SUCCESS_FG_NAMES,
            label="success",
            hue_lo=120,
            hue_hi=160,
        )

    # 3) data-cloud-warning uses a warning token (not muted-only, not amber-*).
    cloud_tag = _contrast_surface_tag(app, "data-cloud-warning")
    if not cloud_tag:
        fail(
            "#219: data-cloud-warning required (warning token, not muted-only)"
        )
    cloud_blob = _status_hook_blob(app, "data-cloud-warning")
    if _STATUS_RAW_HUE.search(_hue_surface(cloud_blob)):
        fail(
            "#219: data-cloud-warning must not use amber-* / yellow-* / "
            "emerald-* / green-* (warning token only)"
        )
    if not _status_surface_uses(
        cloud_blob,
        css,
        _STATUS_WARNING_USE,
        _STATUS_WARNING_NAMES,
        ("data-cloud-warning", "status-warning"),
    ):
        fail(
            "#219: data-cloud-warning must use a warning token class / "
            "var(--warning) / var(--color-warning) (not muted-only, not amber-*)"
        )

    # 4) App.svelte “Doctor found” box and DoctorPane issues card use warning
    #    (not text-destructive as the status color). Scan/partial may stay.
    app_doctor = _status_doctor_box(app)
    if not app_doctor:
        fail(
            "#219: App.svelte “Doctor found” box required "
            "(warning token, not text-destructive)"
        )
    app_doctor_blob = app_doctor + "\n" + _status_hook_blob(app, "Doctor found")
    if re.search(r"(?<![\w-])text-destructive(?![\w-])", app_doctor):
        fail(
            "#219: App.svelte “Doctor found” box must use a warning token "
            "(not text-destructive as the status color)"
        )
    if not _status_surface_uses(
        app_doctor_blob,
        css,
        _STATUS_WARNING_USE,
        _STATUS_WARNING_NAMES,
        ("status-warning",),
    ):
        fail(
            "#219: App.svelte “Doctor found” box must use a warning token "
            "(not text-destructive as the status color)"
        )

    pane_doctor = _status_doctor_box(doctor_src)
    if not pane_doctor:
        fail(
            "#219: DoctorPane.svelte issues card required "
            "(warning token, not text-destructive)"
        )
    pane_blob = pane_doctor + "\n" + _status_hook_blob(doctor_src, "Doctor found")
    if re.search(r"(?<![\w-])text-destructive(?![\w-])", pane_doctor):
        fail(
            "#219: DoctorPane.svelte issues card must use a warning token "
            "(not text-destructive as the status color)"
        )
    if not _status_surface_uses(
        pane_blob,
        css,
        _STATUS_WARNING_USE,
        _STATUS_WARNING_NAMES,
        ("status-warning",),
    ):
        fail(
            "#219: DoctorPane.svelte issues card must use a warning token "
            "(not text-destructive as the status color)"
        )

    # 5) data-import-done exists; muted token classes or success tokens;
    #    no bg-gradient / confetti / celebration.
    if "data-import-done" not in svelte_blob:
        fail(
            "#219: data-import-done required (muted token classes or success "
            "tokens; no bg-gradient / confetti / celebration)"
        )
    if not done_tag:
        fail(
            "#219: data-import-done required (muted token classes or success "
            "tokens; no bg-gradient / confetti / celebration)"
        )
    if not (done_uses_muted or done_uses_success):
        fail(
            "#219: data-import-done must use muted token classes or success "
            "tokens (no bg-gradient / confetti / celebration)"
        )
    if _STATUS_GRADIENT.search(done_blob) or _STATUS_CONFETTI.search(done_blob):
        fail(
            "#219: data-import-done must not use bg-gradient / confetti / "
            "celebration"
        )
    if _STATUS_CELEBRATION.search(_hue_surface(done_blob)):
        fail(
            "#219: data-import-done must not use bg-gradient / confetti / "
            "celebration"
        )

    # 6) No amber-* / yellow-* / emerald-* / green-* on those three surfaces.
    surface_hits: list[str] = []
    for label, blob in (
        ("data-cloud-warning", cloud_blob),
        ("App.svelte Doctor found", app_doctor_blob),
        ("DoctorPane issues card", pane_blob),
        ("data-import-done", done_blob),
    ):
        found = sorted(set(_STATUS_RAW_HUE.findall(_hue_surface(blob))))
        if found:
            surface_hits.append(f"{label}: {', '.join(found)}")
    if surface_hits:
        fail(
            "#219: no amber-* / yellow-* / emerald-* / green-* on cloud / "
            "doctor / import-done surfaces. Found:\n  "
            + "\n  ".join(surface_hits)
        )

    # 7) No confetti / Audio( / celebration copy.
    chrome_hits: list[str] = []
    for p in svelte_files:
        surface = _hue_surface(p.read_text())
        found: list[str] = []
        if _STATUS_CONFETTI.search(surface):
            found.append("confetti")
        if _STATUS_AUDIO_CTOR.search(surface):
            found.append("Audio(")
        celeb = sorted({m.group(0) for m in _STATUS_CELEBRATION.finditer(surface)})
        if celeb:
            found.append("celebration (" + ", ".join(celeb) + ")")
        if found:
            chrome_hits.append(f"{p.relative_to(crate)}: {', '.join(found)}")
    if chrome_hits:
        fail(
            "#219: no confetti / Audio( / celebration copy. Found:\n  "
            + "\n  ".join(chrome_hits)
        )

    # 8) docs/user/app.md: warning token + quiet import done.
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    if not dtxt.strip():
        fail(
            "#219: docs/user/app.md required — warning token + quiet import done"
        )
    if not _STATUS_DOCS_WARNING.search(dtxt):
        fail(
            "#219: docs/user/app.md must say cloud / doctor warnings use the "
            "warning token"
        )
    if not _STATUS_DOCS_QUIET_DONE.search(dtxt):
        fail(
            "#219: docs/user/app.md must say import done is quiet "
            "(muted or success)"
        )

    # 9) No review-queue chrome rewrite (#221).
    #    Svelte transition durations are #222 (`assert_motion`).
    #    “Loading review queue” may live in the pane or the en pack (#278).
    review_path = crate / "web" / "lib" / "ReviewPane.svelte"
    review = review_path.read_text() if review_path.is_file() else ""
    en_pack = _chrome_en_text(crate)
    if (
        not review
        or "Accept" not in review
        or "Reject" not in review
        or (
            "Loading review queue" not in review
            and "Loading review queue" not in en_pack
        )
        or (
            "identifierLabel" not in review
            and "value_normalized" not in review
        )
        or "reviewList" not in review
        or "reviewAccept" not in review
        or "reviewReject" not in review
    ):
        fail("#219: not in scope — no review-queue chrome rewrite (#221)")

    # 10) Do not soften #q, sidebar, overlay titlebar, inspector, CSP,
    #     #217 muted / search-mark, #218 overlay / no Theme.
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = search_path.read_text() if search_path.is_file() else ""
    conf = (crate / "tauri.conf.json").read_text()
    if not re.search(r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""", search):
        fail('#219: keep id="q" as the canonical query field (#208)')
    if not re.search(r"\bdata-people-sidebar\b", app):
        fail("#219: keep data-people-sidebar (#159 / #212)")
    if not re.search(r"titleBarStyle", conf) and not re.search(
        r"\bdata-tauri-drag-region\b", app
    ):
        fail("#219: keep the overlay titlebar (#211)")
    if not re.search(r"\bdata-person-inspector\b", app):
        fail("#219: keep data-person-inspector (#213)")
    if CSP not in conf:
        fail("#219: do not soften tauri CSP")
    light_muted = _css_var(light_blob, ("--color-muted-foreground",))
    light_hsl = _hsl_tuple(light_muted) if light_muted else None
    if not light_hsl or light_hsl[2] > 40:
        fail(
            "#219: keep #217 light --color-muted-foreground HSL L ≤ 40 "
            "(@theme / non-dark :root)"
        )
    dark_muted = _css_var(dark_blob, ("--color-muted-foreground",))
    dark_hsl = _hsl_tuple(dark_muted) if dark_muted else None
    if not dark_hsl or dark_hsl[2] < 62:
        fail(
            "#219: keep #217 dark --color-muted-foreground HSL L ≥ 62 "
            "(inside prefers-color-scheme: dark)"
        )
    if not _css_var(light_blob, _CONTRAST_SEARCH_MARK_NAMES) or not _css_var(
        dark_blob, _CONTRAST_SEARCH_MARK_NAMES
    ):
        fail("#219: keep #217 --search-mark / --color-search-mark on both sides")
    mark_rules = _search_mark_rule_bodies(css)
    if not mark_rules or not any(
        _CONTRAST_SEARCH_MARK_VAR.search(body) for body in mark_rules
    ):
        fail("#219: keep #217 .search-mark on var(--search-mark)")
    if not _css_var(css, _APPEARANCE_SCRIM_NAMES):
        fail("#219: keep #218 --overlay / --scrim / --lightbox-scrim")
    if _APPEARANCE_THEME_UI.search(svelte_blob) or _APPEARANCE_MENU_LABEL.search(
        svelte_blob
    ):
        fail("#219: keep #218 — no Theme / Appearance menu / data-theme")


# #222 — 150–250ms fade/fly/slide on palette, inspector, toast; reduced = 0.
_MOTION_IMPORT = re.compile(
    r"import\s*\{[^}]*\b(?:fade|fly|slide)\b[^}]*\}\s*from\s*"
    r"[\"']svelte/transition[\"']",
    re.S,
)
_MOTION_DIRECTIVE = re.compile(r"\b(?:transition|in|out)\s*:\s*(fade|fly|slide)\b")
_MOTION_DIRECTIVE_CALL = re.compile(
    r"\b(?:transition|in|out)\s*:\s*(fade|fly|slide)"
    r"(?:\s*=\s*(\{\{?.*?\}?\}))?",
    re.S,
)
_MOTION_DURATION_NUM = re.compile(r"\bduration\s*:\s*(\d+)\b")
_MOTION_DURATION_EXPR = re.compile(r"\bduration\s*:\s*([^,}\n]+)")
_MOTION_BANNED = re.compile(
    r"("
    r"\bspring\b"
    r"|\bbounce\b"
    r"|\belastic\b"
    r"|\blottie\b"
    r"|\bcelebrat(?:e|ion|ing|ory)\b"
    r"|\bconfetti\b"
    r")",
    re.I,
)
_MOTION_DOCS_FADE = re.compile(r"\b(?:fade|slide|fly)\b", re.I)
_MOTION_DOCS_REDUCED = re.compile(
    r"("
    r"reduced[\s-]*motion.{0,80}"
    r"(?:instant|immediately|no transition|duration\s*0|appear instantly)"
    r"|(?:instant|immediately|appear instantly).{0,80}reduced[\s-]*motion"
    r")",
    re.I | re.S,
)
_MOTION_DOCS_NO_CELEB = re.compile(r"\bno\s+celebration\b", re.I)
_MOTION_DOCS_NO_AUTOPLAY = re.compile(
    r"\bno\s+auto-?play(?:ing)?(?:\s+media)?\b",
    re.I,
)
_MOTION_COMMAND_OPEN = re.compile(r"\{#if\s+commandOpen\b[^}]*\}")
_MOTION_TOAST_FADE = re.compile(r"\b(?:transition|in|out)\s*:\s*fade\b")


def _motion_has_import(src: str) -> bool:
    return bool(_MOTION_IMPORT.search(src))


def _motion_duration_ok(params: str) -> bool:
    """Literal 150–250 or 0, or a var (0 when reduced — checked separately)."""
    nums = [int(n) for n in _MOTION_DURATION_NUM.findall(params)]
    if nums:
        return all(n == 0 or 150 <= n <= 250 for n in nums)
    return bool(_MOTION_DURATION_EXPR.search(params))


def _motion_ok_on(blob: str) -> bool:
    if not _MOTION_DIRECTIVE.search(blob):
        return False
    for m in _MOTION_DIRECTIVE_CALL.finditer(blob):
        if _motion_duration_ok(m.group(2) or ""):
            return True
    return False


def _motion_first_tag(src: str) -> str:
    i = src.find("<")
    if i < 0:
        return ""
    found = _open_tag_before(src, i + 1)
    if found and found[0] == i:
        return found[1]
    m = re.search(r"<[^>]+>", src, re.S)
    return m.group(0) if m else ""


def _motion_hook_tag(src: str, hook: str) -> str:
    at = src.find(hook)
    if at < 0:
        return ""
    found = _open_tag_before(src, at + 1)
    if found:
        return found[1]
    return _open_tag_around(src, re.escape(hook))


def _motion_command_open_root(src: str) -> str:
    m = _MOTION_COMMAND_OPEN.search(src)
    if not m:
        return ""
    return _motion_first_tag(src[m.end() :])


def _motion_palette_blobs(crate: Path) -> list[str]:
    blobs: list[str] = []
    for p in _product_svelte(crate):
        text = p.read_text()
        if _PALETTE_HOOK.search(text):
            blobs.append(_motion_hook_tag(text, "data-command-palette"))
        if _MOTION_COMMAND_OPEN.search(text):
            blobs.append(_motion_command_open_root(text))
    return [b for b in blobs if b]


def _motion_inspector_blobs(crate: Path) -> list[str]:
    blobs: list[str] = []
    for p in _product_svelte(crate):
        text = p.read_text()
        if _INSPECTOR_HOOK.search(text):
            blobs.append(_motion_hook_tag(text, "data-person-inspector"))
    return [b for b in blobs if b]


def assert_motion(crate: Path) -> None:
    """#222: 150–250ms fade/fly/slide; reduced motion is duration 0."""
    svelte_files = _product_svelte(crate)
    if not svelte_files:
        fail("#222: crates/interlace-tauri/web/**/*.svelte required (motion)")

    app_path = crate / "web" / "App.svelte"
    app = app_path.read_text() if app_path.is_file() else ""
    pal_path = crate / "web" / "lib" / "CommandPalette.svelte"
    pal = pal_path.read_text() if pal_path.is_file() else ""
    toast_path = crate / "web" / "lib" / "components" / "ui" / "toast" / "toast.svelte"
    toast = toast_path.read_text() if toast_path.is_file() else ""

    # 1) Palette + inspector import fade/fly/slide from svelte/transition.
    palette_srcs = [
        text
        for text in (app, pal)
        if text
        and (
            _PALETTE_HOOK.search(text)
            or _MOTION_COMMAND_OPEN.search(text)
            or "CommandPalette" in text
        )
    ]
    inspector_srcs = [
        p.read_text()
        for p in svelte_files
        if _INSPECTOR_HOOK.search(p.read_text())
    ]
    if not any(_motion_has_import(s) for s in palette_srcs):
        fail(
            "#222: palette must import fade / fly / slide from "
            "svelte/transition (App.svelte and/or CommandPalette.svelte)"
        )
    if not any(_motion_has_import(s) for s in inspector_srcs):
        fail(
            "#222: inspector must import fade / fly / slide from "
            "svelte/transition"
        )

    # 2) data-command-palette (or commandOpen root) fade/fly/slide 150–250
    #    (or a var that is 0 when reduced).
    palette_blobs = _motion_palette_blobs(crate)
    if not palette_blobs:
        fail(
            "#222: data-command-palette (or commandOpen root) required "
            "for fade / fly / slide"
        )
    if not any(_motion_ok_on(b) for b in palette_blobs):
        fail(
            "#222: data-command-palette (or commandOpen root) must use "
            "transition:fade / fly / slide with duration 150–250 "
            "(or 0 when reduced)"
        )

    # 3) data-person-inspector same duration rule.
    inspector_blobs = _motion_inspector_blobs(crate)
    if not inspector_blobs:
        fail("#222: data-person-inspector required for fade / fly / slide")
    if not any(_motion_ok_on(b) for b in inspector_blobs):
        fail(
            "#222: data-person-inspector must use transition:fade / fly / "
            "slide with duration 150–250 (or 0 when reduced)"
        )

    # 4) Toast still fade, duration 150–250 or 0 if reduced.
    if not toast.strip():
        fail("#222: toast.svelte required (keep transition:fade 150–250)")
    toast_tag = _motion_hook_tag(toast, "data-toast") or toast
    if not _MOTION_TOAST_FADE.search(toast_tag):
        fail("#222: toast must still use transition:fade")
    if not _motion_ok_on(toast_tag):
        fail(
            "#222: toast transition:fade duration must be 150–250 "
            "(or 0 if reduced)"
        )

    # 5) No spring / bounce / elastic / lottie / celebration / confetti.
    banned_hits: list[str] = []
    for p in svelte_files:
        found = sorted(
            {m.group(0) for m in _MOTION_BANNED.finditer(_hue_surface(p.read_text()))}
        )
        if found:
            banned_hits.append(f"{p.relative_to(crate)}: {', '.join(found)}")
    if banned_hits:
        fail(
            "#222: no spring / bounce / elastic / lottie / celebration / "
            "confetti in product Svelte. Found:\n  " + "\n  ".join(banned_hits)
        )

    # 6) JS reduced-motion + duration 0 (or skip) for those transitions.
    #    CSS-only transition-duration: 0.01ms is not enough for Svelte JS.
    js_blob = _motion_js_blob(crate)
    if not _MOTION_JS_REDUCE.search(js_blob):
        fail(
            "#222: reduced-motion path must use matchMedia / MediaQuery / "
            "prefersReducedMotion in JS (CSS transition-duration: 0.01ms "
            "is not enough for Svelte transitions)"
        )
    svelte_blob = "\n".join(p.read_text() for p in svelte_files)
    if not _MOTION_DURATION_ZERO.search(js_blob + "\n" + svelte_blob):
        fail(
            "#222: palette / inspector / toast Svelte transitions must use "
            "duration 0 (or skip) when reduced motion"
        )

    # 7) Keep #133 CSS reduce media + boot spinner reduced-motion.
    css_path = crate / "web" / "app.css"
    css = css_path.read_text() if css_path.is_file() else ""
    css_blob = _css_without_comments(css)
    index_html = ""
    index_path = crate / "index.html"
    if index_path.is_file():
        index_html = _css_without_comments(index_path.read_text())
    reduce_css = "\n".join(_css_prefers_reduced_blocks(css_blob))
    reduce_html = "\n".join(_css_prefers_reduced_blocks(index_html))
    reduce_all = reduce_css + "\n" + reduce_html
    has_reduce_media = bool(reduce_css.strip() or reduce_html.strip())
    has_motion_tw = bool(
        _A11Y_MOTION_REDUCE_TW.search(app)
        or _A11Y_MOTION_REDUCE_TW.search(css_blob)
    )
    if not has_reduce_media and not has_motion_tw:
        fail(
            "#222: keep #133 @media (prefers-reduced-motion: reduce) "
            "in CSS (or Tailwind motion-reduce)"
        )
    if not _A11Y_ANIM_NONE.search(reduce_all) and not (
        has_motion_tw
        and re.search(r"motion-reduce:animate-none", app + "\n" + css_blob)
    ):
        fail(
            "#222: keep #133 reduced-motion animation: none "
            "(boot spinner must not spin)"
        )
    if not _A11Y_TRANS_NONE.search(reduce_all) and not re.search(
        r"motion-reduce:transition-none", app + "\n" + css_blob
    ):
        fail(
            "#222: keep #133 prefers-reduced-motion CSS "
            "(transition: none / transition-duration: 0)"
        )
    if _SPIN_ANIM.search(index_html) and not _A11Y_ANIM_NONE.search(reduce_html):
        fail(
            "#222: keep boot spinner reduced-motion "
            "(#133 / #156 — disable boot-spin under reduce)"
        )

    # 8) Docs: fade/slide + reduced motion instant + no celebration /
    #    no auto-play.
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    if not dtxt.strip():
        fail(
            "#222: docs/user/app.md required — fade/slide + reduced motion "
            "instant + no celebration / no auto-play"
        )
    if not _MOTION_DOCS_FADE.search(dtxt):
        fail(
            "#222: docs/user/app.md must say palette / inspector / toast "
            "use a short fade / slide"
        )
    if not _MOTION_DOCS_REDUCED.search(dtxt):
        fail(
            "#222: docs/user/app.md must say reduced motion makes them instant"
        )
    if not _MOTION_DOCS_NO_CELEB.search(dtxt):
        fail("#222: docs/user/app.md must say no celebration")
    if not _MOTION_DOCS_NO_AUTOPLAY.search(dtxt):
        fail("#222: docs/user/app.md must say no auto-playing media")

    # 9) Do not soften #q, sidebar, overlay, inspector hook, CSP,
    #    #219 tokens, #220 data-import-cancel, #221 data-review-card / undo.
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = search_path.read_text() if search_path.is_file() else ""
    conf = (crate / "tauri.conf.json").read_text()
    light_blob = _contrast_light_blob(css)
    dark_blob = _contrast_dark_blob(css)
    if not re.search(r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""", search):
        fail('#222: keep id="q" as the canonical query field (#208)')
    if not re.search(r"\bdata-people-sidebar\b", app):
        fail("#222: keep data-people-sidebar (#159 / #212)")
    if not re.search(r"titleBarStyle", conf) and not re.search(
        r"\bdata-tauri-drag-region\b", app
    ):
        fail("#222: keep the overlay titlebar (#211)")
    if not re.search(r"\bdata-person-inspector\b", app):
        fail("#222: keep data-person-inspector (#213)")
    if CSP not in conf:
        fail("#222: do not soften tauri CSP")
    if not _css_var(light_blob, _STATUS_WARNING_NAMES) or not _css_var(
        dark_blob, _STATUS_WARNING_NAMES
    ):
        fail("#222: keep #219 --warning / --color-warning in light and dark")
    if "data-import-cancel" not in svelte_blob:
        fail("#222: keep #220 data-import-cancel")
    if "data-review-card" not in svelte_blob:
        fail("#222: keep #221 data-review-card")
    if "data-review-undo" not in svelte_blob:
        fail("#222: keep #221 data-review-undo")
