"""Listbox / focus / ARIA chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    CSP,
    _A11Y_ROLE_OPTION,
    _A11Y_TABINDEX_NEG,
    _PERSON_PANE_SKIP,
    _ancestor_tags,
    _css_without_comments,
    _markup_open_tag,
    _matching_each_end,
    _open_tag_around,
    _open_tag_before,
    _product_svelte,
    _strip_html_comments,
    _svelte_markup,
    _tag_name,
    _timeline_block,
    _web_sources,
    _without_comments,
)

from tauri_gate.import_boot import _boot_opening_block

from tauri_gate.status_toasts import _PEOPLE_EACH


_SPIN_ANIM = re.compile(
    r"("
    r"animate-spin\b"
    r"|@keyframes\s+[\w-]*spin[\w-]*"
    r"|animation\s*:\s*[^;\n}]*\bspin\b"
    r"|animation-name\s*:\s*[\w-]*spin[\w-]*"
    r")",
    re.I,
)


def _people_each_block(markup: str) -> str:
    """Innermost {#each filtered …} body for the people list (not switcher)."""
    m = _PEOPLE_EACH.search(markup)
    if not m:
        return ""
    end = _matching_each_end(markup, m.start())
    if end < 0:
        return markup[m.start() :]
    return markup[m.start() : end]


def _people_list_a11y_surfaces(crate: Path) -> tuple[str, str]:
    """Chrome around `{#each filtered}` plus the each body (not SearchPane)."""
    chromes: list[str] = []
    bodies: list[str] = []
    for p in _web_sources(crate):
        if p.suffix != ".svelte" or p.name in _PERSON_PANE_SKIP:
            continue
        text = p.read_text()
        markup = _strip_html_comments(_svelte_markup(text))
        if not _PEOPLE_EACH.search(markup):
            markup = _strip_html_comments(text)
        for m in _PEOPLE_EACH.finditer(markup):
            end = _matching_each_end(markup, m.start())
            if end < 0:
                end = min(len(markup), m.start() + 1600)
            chromes.append(markup[max(0, m.start() - 700) : end])
            bodies.append(markup[m.start() : end])
    return "\n".join(chromes), "\n".join(bodies)



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


# #133 — a11y: people listbox, timeline article/label, focus-visible, reduced motion.
_A11Y_ROLE_LISTBOX = re.compile(r"\brole\s*=\s*[\"']listbox[\"']", re.I)


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
