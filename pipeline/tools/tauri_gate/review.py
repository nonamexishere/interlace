"""Review queue chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations

from tauri_gate.review_queue import *
from tauri_gate.review_undo import *



def assert_review_identifiers(crate: Path) -> None:
    """#128: ReviewPane shows identifier kind+value_normalized on each side panel.

    A name_similarity card must be decidable without CLI `review show`: under
    the title, render identifiers (kind + value_normalized; platform optional),
    not only display_name / platforms. Samples stay text nodes (body_text;
    no {@html on sample body). Keep score, evidence list, Accept/Reject.
    Not: dump extra body lines, invent name_score UI changes.
    """
    review_path = crate / "web" / "lib" / "ReviewPane.svelte"
    api_path = crate / "web" / "lib" / "api.ts"
    if not review_path.is_file():
        fail("#128: ReviewPane.svelte required (review card identifier chrome lives there)")
    if not api_path.is_file():
        fail("#128: web/lib/api.ts required (ReviewPanel type surface)")

    src = review_path.read_text()
    cleaned = _without_comments(src)
    markup = _svelte_markup(src)
    surface = markup if markup.strip() else src
    api_src = api_path.read_text()

    # 1) Type surface: ReviewPanel carries identifiers with kind + value_normalized.
    # Nested braces inside ReviewPanel (inline object types) are allowed.
    panel_start = re.search(r"(?:export\s+)?type\s+ReviewPanel\s*=\s*\{", api_src)
    if not panel_start:
        fail("#128: api.ts must declare export type ReviewPanel = { … }")
    brace_i = panel_start.end() - 1
    depth = 0
    end_i = -1
    for j in range(brace_i, len(api_src)):
        c = api_src[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end_i = j
                break
    if end_i < 0:
        fail("#128: unclosed ReviewPanel type in api.ts")
    panel_body = api_src[brace_i + 1 : end_i]
    if not re.search(r"\bidentifiers\b", panel_body):
        fail(
            "#128: ReviewPanel must include identifiers[] "
            "(kind + value_normalized per entry — not only display_name / platforms)"
        )
    # Inline object type, field pair on ReviewPanel, or a named element type.
    ident_shape = (
        re.search(
            r"identifiers\s*[?]?\s*:\s*\{[^}]*\bkind\b[^}]*\bvalue_normalized\b",
            panel_body,
            re.I | re.S,
        )
        or re.search(
            r"identifiers\s*[?]?\s*:\s*\{[^}]*\bvalue_normalized\b[^}]*\bkind\b",
            panel_body,
            re.I | re.S,
        )
        or (
            re.search(r"\bidentifiers\b", panel_body)
            and re.search(r"\bkind\b", panel_body)
            and re.search(r"\bvalue_normalized\b", panel_body)
        )
        or re.search(
            r"(?:export\s+)?type\s+Review(?:Panel)?Ident(?:ifier)?\s*=\s*\{[^}]*\bkind\b[^}]*\bvalue_normalized\b",
            api_src,
            re.I | re.S,
        )
        or re.search(
            r"(?:export\s+)?type\s+Review(?:Panel)?Ident(?:ifier)?\s*=\s*\{[^}]*\bvalue_normalized\b[^}]*\bkind\b",
            api_src,
            re.I | re.S,
        )
    )
    if not ident_shape:
        named = re.search(
            r"identifiers\s*[?]?\s*:\s*([A-Za-z_]\w*)\s*\[\]",
            panel_body,
        )
        named_ok = False
        if named:
            tname = named.group(1)
            m = re.search(
                rf"(?:export\s+)?type\s+{re.escape(tname)}\s*=\s*\{{([^}}]*)\}}",
                api_src,
                re.S,
            )
            if m and re.search(r"\bkind\b", m.group(1)) and re.search(
                r"\bvalue_normalized\b", m.group(1)
            ):
                named_ok = True
        if not named_ok:
            fail(
                "#128: ReviewPanel.identifiers entries must expose kind + value_normalized "
                "(inline or named type; platform optional)"
            )

    # 2) Pane renders identifiers under the panel title — not only panelTitle / platforms.
    panel_each = re.search(
        r"\{#each\s+[^}]*panelsOf\([^)]*\)[^}]*\}[\s\S]{0,4000}?\{/each\}"
        r"|\{#each\s+(?:panel|panels|sides)\b[^}]*\}[\s\S]{0,4000}?\{/each\}",
        surface,
        re.I,
    )
    panel_region = panel_each.group(0) if panel_each else surface
    renders_idents = bool(
        re.search(
            r"("
            r"\{#each\s+[^}]*\bidentifiers\b"
            r"|\.identifiers\b"
            r"|panel\.identifiers"
            r"|identifiers\s*\?\."
            r")",
            panel_region + "\n" + cleaned,
            re.I,
        )
    )
    if not renders_idents:
        fail(
            "#128: ReviewPane must render panel.identifiers "
            "(kind + value_normalized under the title — not only display_name / platforms)"
        )
    has_kind_bind = bool(
        re.search(
            r"("
            r"\{[^}]{0,80}\.kind\b[^}]{0,40}\}"
            r"|\.kind\b"
            r"|ident(?:ifier)?\.kind"
            r"|id\.kind"
            r")",
            panel_region,
            re.I,
        )
    )
    has_norm_bind = bool(
        re.search(
            r"("
            r"\{[^}]{0,80}\.value_normalized\b[^}]{0,40}\}"
            r"|\.value_normalized\b"
            r"|valueNormalized"
            r"|ident(?:ifier)?\.value_normalized"
            r")",
            panel_region + "\n" + cleaned,
            re.I,
        )
    )
    helper_fmt = bool(
        re.search(
            r"("
            r"ident(?:ifier)?Label"
            r"|formatIdent"
            r"|idLabel"
            r"|kind\s*\+\s*"
            r"|value_normalized"
            r")",
            cleaned,
            re.I,
        )
    ) and re.search(r"\bkind\b", cleaned) and re.search(
        r"\bvalue_normalized\b|valueNormalized", cleaned
    )
    if not ((has_kind_bind and has_norm_bind) or helper_fmt):
        fail(
            "#128: ReviewPane must show identifier kind and value_normalized as text "
            "(bindings on the panel loop, or a small formatter used there) — "
            "not only panelTitle(display_name + platforms)"
        )
    if re.search(
        r"\{[^}]{0,40}panel\.person_id[^}]{0,40}\}",
        panel_region,
    ) and not renders_idents:
        fail("#128: do not use raw person_id as the primary identifier label")

    # 3) Samples remain text nodes — no {@html on sample body.
    if re.search(r"\{@html\b", surface):
        fail("#128: ReviewPane samples must stay text nodes — no {@html on sample body}")
    if not re.search(r"\bbody_text\b", surface + "\n" + cleaned):
        fail("#128: ReviewPane must still render sample body_text as text")
    if not re.search(
        r"("
        r"\{[^}]{0,40}body_text[^}]{0,40}\}"
        r"|whitespace-pre-wrap[^>]{0,80}body_text"
        r"|body_text[^;\n]{0,40}\}"
        r")",
        surface,
        re.I,
    ):
        fail("#128: sample bodies must remain text bindings of body_text (not HTML inject)")

    # 4) Keep score + evidence + Accept/Reject chrome (identifiers are additive).
    if not re.search(r"\bevidence\b", surface + "\n" + cleaned):
        fail("#128: keep the evidence list on the review card")
    if not re.search(r"\b(?:score|suggested_score)\b", surface + "\n" + cleaned):
        fail("#128: keep the score on the review card")
    if not re.search(r">\s*Accept\s*<", surface):
        fail("#128: keep Accept on the review card")
    if not re.search(r">\s*Reject\s*<", surface):
        fail("#128: keep Reject on the review card")
    if "panelTitle" not in cleaned and not re.search(r"\bdisplay_name\b", surface):
        fail("#128: keep display_name / panel title chrome; identifiers sit under it")
    if not re.search(r"\bplatforms\b", cleaned):
        fail("#128: keep platforms on the panel surface (identifiers are additive)")

    # 5) Not in scope: inventing name_score threshold UI.
    if re.search(
        r"("
        r"name_score\s*[<>]=?"
        r"|nameScoreThreshold"
        r"|raise.*name_score"
        r"|lower.*name_score"
        r")",
        cleaned,
        re.I,
    ):
        fail(
            "#128: do not invent name_score raise/lower UI "
            "(threshold policy is #103; this issue only surfaces identifiers)"
        )

from tauri_gate.review_more import (
    assert_review_chrome,
    assert_sidebar_undo_chrome,
)
