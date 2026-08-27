"""Design-token / typography / Lucide chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.design_lib import *


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
    search = _search_pane_blob(crate)

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

from tauri_gate.design_more import assert_lucide_icons
