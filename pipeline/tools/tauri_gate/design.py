"""Design-token / typography / Lucide chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _BODY_T_CALL,
    _BUBBLE_ME_VARS,
    _BUBBLE_THEM_VARS,
    _TYPO_FONT_SANS,
    _VOID_HTML,
    _css_var,
    _product_svelte,
    _strip_html_comments,
    _svelte_markup,
    _timeline_block,
    _web_logic,
    _without_comments,
)

from tauri_gate.a11y import (
    _people_each_block,
    _people_list_a11y_surfaces,
)

from tauri_gate.import_boot import (
    _PRE_WRAP,
    _hue_findings,
)

from tauri_gate.status_toasts import (
    _DOCS_TYPO_NO_REMOTE_FONT,
    _THEME_CDN,
    _TYPO_REMOTE_FONT,
    _chrome_helper_names,
    _chrome_helper_on_body,
    _hue_surface,
    _typo_docs_blob,
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
