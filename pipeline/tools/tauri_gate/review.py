"""Review queue chrome asserts. Imported by gate_tauri.py."""
from __future__ import annotations
import re
from pathlib import Path
from common import fail, repo_root
from tauri_gate.scan import (
    CSP, _APPEARANCE_MENU_LABEL, _APPEARANCE_SCRIM_NAMES, _STATUS_WARNING_NAMES,
    _ancestor_tags, _contrast_dark_blob, _css_var, _expand_fn_calls,
    _function_body, _js_next, _match_closer, _open_tag_before,
    _product_svelte, _svelte_markup, _ts_fn_body, _without_comments,
)
from tauri_gate.import_boot import (
    _contrast_light_blob, _review_if_return_conds,
)
from tauri_gate.status_toasts import (
    _APPEARANCE_THEME_UI, _hue_surface,
)



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


# #221 — review queue chrome: Card/Separator, no raw ids, undo on the pane.
_REVIEW_CARD_IMPORT = re.compile(
    r"import\s+(?:\{[^}]*\bCard\b[^}]*\}|\bCard\b)\s+from\s+"
    r"[\"']\$lib/components/ui/card(?:/[^\"']*)?[\"']",
    re.S,
)
_REVIEW_SEP_IMPORT = re.compile(
    r"import\s+(?:\{[^}]*\bSeparator\b[^}]*\}|\bSeparator\b)\s+from\s+"
    r"[\"']\$lib/components/ui/separator(?:/[^\"']*)?[\"']",
    re.S,
)
_REVIEW_ACCEPT = re.compile(r">\s*Accept\s*<")
_REVIEW_REJECT = re.compile(r">\s*Reject\s*<")
_REVIEW_RAW_VISIBLE = re.compile(
    r"("
    r"#\{\s*r\.id\s*\}"
    r"|person\s+\$\{"
    r"|person\s+\$\{\s*r\.right_person_id"
    r"|Accept review \$\{id\}"
    r")"
)
_REVIEW_NAME_SCORE_UI = re.compile(
    r"("
    r"name_score\s*[<>]=?"
    r"|nameScoreThreshold"
    r"|raise.*name_score"
    r"|lower.*name_score"
    r")",
    re.I,
)
_REVIEW_SAMPLE_EACH = re.compile(r"\{#each\s+panel\.samples\b")
_REVIEW_SECOND_BODY = re.compile(
    r"\{#each\s+(?!panel\.samples\b)[^}]*\b(?:samples|bodies|body_lines|body_text)\b"
)
_REVIEW_LINK_EVENTS = re.compile(r"\blinkEvents\b")
_REVIEW_UNDO_USE = re.compile(r"(?:\bapi\s*\.\s*)?\bundo\s*\(")
_REVIEW_AWAIT_ONCONFIRM = re.compile(r"await\s+onconfirm\s*\(")
_REVIEW_OPEN_FALSE = re.compile(r"\bopen\s*=\s*false\b")
_REVIEW_AWAIT_CHANGED = re.compile(r"await\s+onChanged\s*\(")
_REVIEW_ONERROR_PROP = re.compile(r"\b(?:onerror|onError)\b")
_REVIEW_APP_CONFIRM_ERR = re.compile(r"\b(?:onerror|onError|showErr)\b")
_REVIEW_INFLIGHT_TOKEN = re.compile(
    r"\b(?:resolving|undoing|busy|accepting|rejecting|"
    r"inFlight|inflight|isBusy|working|pending|acting)\b"
)
_REVIEW_BOOL_STATE = re.compile(
    r"\b(?:let|const|var)\s+(\w+)\s*=\s*\$state\(\s*(?:false|true)\s*\)"
)
_REVIEW_ONERROR_SKIP = frozenset(
    {
        "reload",
        "onChanged",
        "ask",
        "canAccept",
        "api",
        "requestUndo",
        "runUndo",
        "void",
        "if",
        "await",
        "Promise",
        "Set",
        "Array",
        "Boolean",
        "Number",
        "String",
    }
)
_REVIEW_INFLIGHT_SKIP_FLAGS = frozenset({"confirmOpen", "loading", "selected"})
_REVIEW_DOCS_UNDO = re.compile(r"\bundo(?:able)?\b|\breversible\b", re.I)
_REVIEW_DOCS_NO_RAW = re.compile(
    r"("
    r"no raw person id"
    r"|not raw person id"
    r"|without raw person"
    r"|raw person ids?"
    r")",
    re.I,
)
_REVIEW_DOCS_IDENTS = re.compile(r"\bidentifiers?\b", re.I)


def _review_action_tag(markup: str, label: str) -> str:
    """Opening <Button>/<button> that wraps >Label<."""
    m = re.search(rf">\s*{re.escape(label)}\s*<", markup)
    if not m:
        return ""
    for tag in _ancestor_tags(markup, m.start(), limit=8):
        if re.match(r"<(?:Button|button)\b", tag):
            return tag
    return ""


def _review_docs_blob(dtxt: str) -> str:
    """Copy window starting at the Review heading / mention (not Merge/unlink/undo)."""
    m = re.search(r"\*\*Review\*\*.{0,1200}", dtxt, re.S | re.I)
    if m:
        return m.group(0)
    m = re.search(r"\bReview\b.{0,1200}", dtxt, re.S)
    return m.group(0) if m else ""


def _review_undo_action_blob(src: str) -> str:
    """Undo action script: named helpers + callees + api.undo windows."""
    parts: list[str] = []
    for name in ("runUndo", "requestUndo", "undoLast", "undoLink", "doUndo"):
        body = _ts_fn_body(src, name) or _function_body(src, name)
        if body:
            parts.append(_expand_fn_calls(src, body, depth=2))
    for m in _REVIEW_UNDO_USE.finditer(src):
        start = max(0, m.start() - 400)
        end = min(len(src), m.end() + 500)
        parts.append(src[start:end])
    return "\n".join(parts)


def _review_attr_expr(tag: str, name: str) -> str:
    """Value inside attr={...} on an opening tag."""
    m = re.search(rf"\b{re.escape(name)}\s*=\s*\{{", tag)
    if not m:
        return ""
    open_i = m.end() - 1
    close = _match_closer(tag, open_i)
    if close < 0:
        return ""
    return tag[open_i + 1 : close]


def _review_top_args(src: str, open_paren: int) -> list[str]:
    close = _match_closer(src, open_paren)
    if close < 0:
        return []
    args = src[open_paren + 1 : close]
    parts: list[str] = []
    start = 0
    depth = 0
    i = 0
    n = len(args)
    while i < n:
        nxt = _js_next(args, i)
        if nxt != i:
            i = nxt
            continue
        c = args[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "," and depth == 0:
            parts.append(args[start:i])
            start = i + 1
        i += 1
    parts.append(args[start:])
    return [p.strip() for p in parts if p.strip()]


def _review_expr_fn_body(src: str, expr: str) -> str:
    """Body of an inline arrow/function expr, or a named helper it calls."""
    expr = expr.strip().rstrip(";")
    m = re.search(
        r"(?:async\s*)?(?:function\s*)?\([^)]*\)\s*(?::\s*[^{=]+)?=>\s*\{",
        expr,
    )
    if not m:
        m = re.search(r"(?:async\s+)?function\s*\([^)]*\)\s*\{", expr)
    if m:
        brace = expr.find("{", m.end() - 1)
        if brace >= 0:
            close = _match_closer(expr, brace)
            if close > brace:
                return expr[brace + 1 : close]
    ident = re.fullmatch(r"([A-Za-z_]\w*)", expr)
    if ident:
        return _ts_fn_body(src, ident.group(1)) or _function_body(
            src, ident.group(1)
        )
    call = re.fullmatch(
        r"(?:async\s*)?\([^)]*\)\s*(?::\s*[^=]+)?=>\s*([A-Za-z_]\w*)\s*\(.*\)",
        expr,
        re.S,
    )
    if call:
        return _ts_fn_body(src, call.group(1)) or _function_body(
            src, call.group(1)
        )
    return expr


def _review_derived_body(src: str, name: str) -> str:
    m = re.search(
        rf"\b(?:let|const|var)\s+{re.escape(name)}\s*=\s*"
        rf"\$derived(?:\.by)?\s*\(",
        src,
    )
    if not m:
        return ""
    close = _match_closer(src, m.end() - 1)
    if close < 0:
        return ""
    return src[m.end() : close]


def _review_mentions_inflight(src: str, expr: str, tokens: set[str]) -> bool:
    if not expr or not tokens:
        return False
    blob = expr + "\n" + _expand_fn_calls(src, expr, depth=2)
    for name in re.findall(r"\b([A-Za-z_]\w*)\b", expr):
        derived = _review_derived_body(src, name)
        if derived:
            blob += "\n" + derived
    return any(re.search(rf"\b{re.escape(t)}\b", blob) for t in tokens)


def _review_fn_body(src: str, name: str) -> str:
    return _ts_fn_body(src, name) or _function_body(src, name)


def _review_inflight_tokens(src: str) -> set[str]:
    """resolving/undoing/similar, plus $state flags set true on accept/reject."""
    tokens = set(_REVIEW_INFLIGHT_TOKEN.findall(src))
    action: list[str] = []
    for name in ("accept", "reject", "ask"):
        body = _review_fn_body(src, name)
        if body:
            action.append(body)
            for callee in re.findall(r"\b([A-Za-z_]\w*)\s*\(", body):
                if callee in _REVIEW_ONERROR_SKIP:
                    continue
                inner = _review_fn_body(src, callee)
                if inner:
                    action.append(inner)
    blob = "\n".join(action)
    for name in _REVIEW_BOOL_STATE.findall(src):
        if name in _REVIEW_INFLIGHT_SKIP_FLAGS:
            continue
        if re.search(rf"\b{re.escape(name)}\s*=\s*true\b", blob):
            tokens.add(name)
    return tokens


def _review_ask_callback_bodies(src: str, fn_body: str) -> list[str]:
    """Last arg to ask(...) and confirmRun = ... inside fn_body (+ one helper)."""
    blobs = [fn_body]
    for callee in re.findall(r"\b([A-Za-z_]\w*)\s*\(", fn_body):
        if callee in _REVIEW_ONERROR_SKIP | {"confirmRun"}:
            continue
        inner = _review_fn_body(src, callee)
        if inner:
            blobs.append(inner)
    cbs: list[str] = []
    for blob in blobs:
        for m in re.finditer(r"\bask\s*\(", blob):
            args = _review_top_args(blob, m.end() - 1)
            if args:
                body = _review_expr_fn_body(src, args[-1])
                if body:
                    cbs.append(body)
        for m in re.finditer(r"\bconfirmRun\s*=", blob):
            rest = blob[m.end() :]
            body = _review_expr_fn_body(src, rest)
            if body:
                cbs.append(body)
    return cbs


def _review_has_try_onerror(src: str, blob: str, depth: int = 1) -> bool:
    if re.search(r"\btry\s*\{", blob) and re.search(
        r"\bcatch\b", blob
    ) and re.search(r"\bonError\s*\(", blob):
        return True
    if depth <= 0:
        return False
    for name in re.findall(r"\b([A-Za-z_]\w*)\s*\(", blob):
        if name in _REVIEW_ONERROR_SKIP:
            continue
        inner = _review_fn_body(src, name)
        if inner and _review_has_try_onerror(src, inner, depth - 1):
            return True
    return False


def _review_onconfirm_blob(src: str) -> str:
    m = re.search(r"\bonconfirm\s*=\s*\{", src)
    if not m:
        return ""
    open_i = m.end() - 1
    close = _match_closer(src, open_i)
    if close < 0:
        return ""
    return src[open_i + 1 : close]


def _confirm_refuses_open_while_busy(src: str) -> bool:
    """True if open=true is ignored / forced false while busy."""
    for m in re.finditer(r"\bif\s*\(", src):
        close = _match_closer(src, m.end() - 1)
        if close < 0:
            continue
        cond = src[m.end() : close]
        if not re.search(r"\bbusy\b", cond):
            continue
        rest = src[close + 1 :].lstrip()
        then = rest
        if rest.startswith("{"):
            open_b = src.find("{", close)
            close_b = _match_closer(src, open_b) if open_b >= 0 else -1
            then = src[open_b + 1 : close_b] if close_b > open_b else rest
        if re.search(r"\breturn\b", then) or _REVIEW_OPEN_FALSE.search(then):
            return True
    for m in re.finditer(r"\$effect(?:\.pre)?\s*\(", src):
        close = _match_closer(src, m.end() - 1)
        if close < 0:
            continue
        body = src[m.end() : close]
        if re.search(r"\bbusy\b", body) and (
            _REVIEW_OPEN_FALSE.search(body) or re.search(r"\bopen\b", body)
        ):
            return True
    return False


def _confirm_go_catches_onconfirm(go_body: str) -> bool:
    """True if onconfirm is in try/catch, chained .catch, or onerror call."""
    if re.search(r"\b(?:onerror|onError)\s*\(", go_body) and re.search(
        r"\bonconfirm\s*\(", go_body
    ):
        return True
    for m in re.finditer(r"\bonconfirm\s*\(", go_body):
        close = _match_closer(go_body, m.end() - 1)
        if close < 0:
            continue
        rest = go_body[close + 1 :].lstrip()
        if rest.startswith(".catch"):
            return True
    for m in re.finditer(r"\btry\s*\{", go_body):
        open_b = m.end() - 1
        close_b = _match_closer(go_body, open_b)
        if close_b < 0:
            continue
        if not re.search(r"\bonconfirm\s*\(", go_body[open_b + 1 : close_b]):
            continue
        rest = go_body[close_b + 1 :].lstrip()
        if rest.startswith("catch"):
            return True
    return False


def _review_component_tag(src: str, name: str) -> str:
    """First <Name ...> opening tag, including {nested} attrs."""
    m = re.search(rf"<{re.escape(name)}\b", src)
    if not m:
        return ""
    found = _open_tag_before(src, min(len(src), m.end() + 1))
    if found and found[0] == m.start():
        return found[1]
    return ""


def _review_undo_control_tag(markup: str) -> str:
    """Opening tag of the Review Undo control (`data-review-undo`)."""
    m = re.search(r"\bdata-review-undo\b", markup)
    if not m:
        return ""
    for tag in _ancestor_tags(markup, m.start(), limit=8):
        if re.match(r"<(?:Button|button)\b", tag, re.I):
            return tag
        if _review_attr_expr(tag, "disabled"):
            return tag
    found = _open_tag_before(markup, m.start() + 1)
    return found[1] if found else ""


def assert_review_chrome(crate: Path) -> None:
    """#221: ReviewPane Card chrome — safe, reversible, still no raw ids.

    Follow-up (undo freeze): skip split_person / undo_of; ConfirmDialog
    sets open = false before await onconfirm(); undo does not await
    onChanged().
    Follow-up (in-flight Accept/Reject): disable Accept/Reject while
    resolving/undoing; accept/reject/ask return early on that flag;
    callbacks call onError.
    Follow-up (onerror + undo-while-resolving): ConfirmDialog go()
    catches onconfirm and has onerror/onError; App ConfirmDialog
    passes onerror/onError/showErr; Undo disabled + requestUndo
    honor resolving.
    """
    review_path = crate / "web" / "lib" / "ReviewPane.svelte"
    if not review_path.is_file():
        fail("#221: ReviewPane.svelte required (review queue chrome lives there)")
    src = review_path.read_text()
    cleaned = _without_comments(src)
    markup = _svelte_markup(src)
    surface = markup if markup.strip() else src
    visible = _hue_surface(src)

    # 1) Owned Card + Separator imports.
    if not _REVIEW_CARD_IMPORT.search(src) or not _REVIEW_SEP_IMPORT.search(src):
        fail(
            "#221: ReviewPane.svelte must import Card from "
            "$lib/components/ui/card and Separator from "
            "$lib/components/ui/separator"
        )

    # 2) data-review-card on the open-card root.
    if "data-review-card" not in src:
        fail("#221: data-review-card required on the open review card")

    # 3) Explicit Accept / Reject; neither button tag is destructive.
    if not _REVIEW_ACCEPT.search(surface):
        fail("#221: keep Accept on the review card (explicit >Accept<)")
    if not _REVIEW_REJECT.search(surface):
        fail("#221: keep Reject on the review card (explicit >Reject<)")
    for label in ("Accept", "Reject"):
        tag = _review_action_tag(surface, label)
        if tag and re.search(r"\bdestructive\b", tag, re.I):
            fail(
                f"#221: {label} button must not use destructive "
                "(Reject is suppress; Accept is a link you can undo)"
            )

    # 4) No raw review / person id visible-string patterns.
    raw = _REVIEW_RAW_VISIBLE.search(visible)
    if raw:
        fail(
            "#221: queue/detail markup must not show #{r.id} / "
            "person ${ / person ${r.right_person_id / Accept review ${id} "
            f"(found {raw.group(0)!r})"
        )

    # 5) Identifiers + sample text nodes stay (#128).
    if not (
        re.search(r"\bidentifierLabel\b", cleaned + "\n" + surface)
        or re.search(r"\bvalue_normalized\b", surface + "\n" + cleaned)
    ):
        fail(
            "#221: keep identifierLabel or value_normalized on the review card"
        )
    if re.search(r"\{@html\b", surface):
        fail("#221: ReviewPane samples must stay text nodes — no {@html")
    if not re.search(
        r"("
        r"\{[^}]{0,40}body_text[^}]{0,40}\}"
        r"|whitespace-pre-wrap[^>]{0,80}body_text"
        r"|body_text[^;\n]{0,40}\}"
        r")",
        surface,
        re.I,
    ):
        fail("#221: sample bodies must remain text bindings of body_text")

    # 6) Undo on the Review pane (link events), not only the People sidebar.
    if not _REVIEW_LINK_EVENTS.search(cleaned):
        fail("#221: ReviewPane must call linkEvents (undo lives on the pane)")
    if not _REVIEW_UNDO_USE.search(cleaned):
        fail("#221: ReviewPane must call undo (api.undo after Accept)")
    if "data-review-undo" not in src:
        fail("#221: data-review-undo required on the Review pane Undo control")
    if re.search(r"events\s*\[\s*0\s*\]", cleaned) and not re.search(
        r"split_person|undo_of|lastUndoable", cleaned
    ):
        fail(
            "#221: do not undo events[0] blindly — skip split_person / "
            "already-undone / system import links"
        )
    if "split_person" not in cleaned or "undo_of" not in cleaned:
        fail(
            "#221: Review undo must skip split_person and already-undone "
            "events (undo_of)"
        )

    # 6b) Follow-up (undo freeze): ConfirmDialog closes before onconfirm;
    #     Review undo must not await onChanged() (People person_list).
    confirm_path = crate / "web" / "lib" / "ConfirmDialog.svelte"
    if not confirm_path.is_file():
        fail(
            "#221: ConfirmDialog.svelte required "
            "(go() must close before await onconfirm())"
        )
    confirm_src = _without_comments(confirm_path.read_text())
    go_body = _ts_fn_body(confirm_src, "go") or _function_body(confirm_src, "go")
    if not go_body:
        fail(
            "#221: ConfirmDialog.svelte go() required "
            "(set open = false before await onconfirm())"
        )
    await_onconfirm = _REVIEW_AWAIT_ONCONFIRM.search(go_body)
    if await_onconfirm:
        close_open = _REVIEW_OPEN_FALSE.search(go_body)
        if not close_open or close_open.start() > await_onconfirm.start():
            fail(
                "#221: ConfirmDialog go() must set open = false before "
                "await onconfirm() (or not await onconfirm)"
            )
    undo_blob = _review_undo_action_blob(cleaned)
    if _REVIEW_AWAIT_CHANGED.search(undo_blob):
        fail(
            "#221: ReviewPane must not await onChanged() after undo "
            "(People refresh must not block the confirm callback)"
        )

    # 6c) Follow-up (in-flight Accept/Reject): disable + no-op + onError.
    tokens = _review_inflight_tokens(cleaned)
    for label in ("Accept", "Reject"):
        tag = _review_action_tag(surface, label)
        expr = _review_attr_expr(tag, "disabled") if tag else ""
        if not _review_mentions_inflight(cleaned, expr, tokens):
            fail(
                f"#221: {label} button must be disabled while "
                "resolving/undoing (not only !canAccept())"
            )
    for name in ("accept", "reject", "ask"):
        body = _review_fn_body(cleaned, name)
        if not body:
            fail(f"#221: ReviewPane {name}() required")
        conds = _review_if_return_conds(body)
        cond_blob = "\n".join(
            _expand_fn_calls(cleaned, c, depth=2) for c in conds
        )
        if not _review_mentions_inflight(cleaned, cond_blob, tokens):
            fail(
                f"#221: {name}() must return early when resolving/undoing "
                "(or a similar in-flight flag) is set"
            )
    onconfirm = _review_onconfirm_blob(cleaned)
    wrapped = _review_has_try_onerror(cleaned, onconfirm) if onconfirm else False
    if not wrapped:
        for name in ("accept", "reject"):
            body = _review_fn_body(cleaned, name)
            cbs = _review_ask_callback_bodies(cleaned, body) if body else []
            if not cbs or not any(
                _review_has_try_onerror(cleaned, cb) for cb in cbs
            ):
                fail(
                    "#221: Accept/Reject callbacks must try/catch and "
                    "call onError (same as runUndo)"
                )
    cancel_tag = _review_action_tag(
        _svelte_markup(confirm_path.read_text()) or confirm_src, "Cancel"
    )
    cancel_disabled = _review_attr_expr(cancel_tag, "disabled") if cancel_tag else ""
    if re.search(r"\bbusy\b", cancel_disabled) and not (
        _confirm_refuses_open_while_busy(confirm_src)
    ):
        fail(
            "#221: ConfirmDialog must refuse open = true while busy "
            "(or leave Cancel enabled so a resurrected overlay is dismissable)"
        )

    # 6d) Follow-up (onerror + undo-while-resolving): catch + banner;
    #     Undo disabled / requestUndo honor resolving.
    has_onerror = bool(_REVIEW_ONERROR_PROP.search(confirm_src))
    if not has_onerror or not _confirm_go_catches_onconfirm(go_body):
        fail(
            "#221: ConfirmDialog go() must catch onconfirm "
            "and have an onerror / onError prop"
        )
    app_confirm_path = crate / "web" / "App.svelte"
    app_confirm_src = (
        app_confirm_path.read_text() if app_confirm_path.is_file() else ""
    )
    app_confirm_tag = _review_component_tag(app_confirm_src, "ConfirmDialog")
    if not app_confirm_tag:
        fail("#221: App.svelte ConfirmDialog required")
    if not _REVIEW_APP_CONFIRM_ERR.search(app_confirm_tag):
        fail(
            "#221: App.svelte ConfirmDialog must pass "
            "onerror / onError / showErr"
        )
    undo_tag = _review_undo_control_tag(surface)
    undo_disabled = _review_attr_expr(undo_tag, "disabled") if undo_tag else ""
    if not _review_mentions_inflight(cleaned, undo_disabled, {"resolving"}):
        fail(
            "#221: Review Undo disabled must mention resolving "
            "(not only undoing)"
        )
    undo_req = _review_fn_body(cleaned, "requestUndo")
    if not undo_req:
        fail("#221: ReviewPane requestUndo() required")
    undo_conds = _review_if_return_conds(undo_req)
    undo_cond_blob = "\n".join(
        _expand_fn_calls(cleaned, c, depth=2) for c in undo_conds
    )
    if not _review_mentions_inflight(cleaned, undo_cond_blob, {"resolving"}):
        fail(
            "#221: requestUndo() must return early when resolving"
        )

    # 7) No name_score threshold UI; sample loop stays panel.samples.
    if _REVIEW_NAME_SCORE_UI.search(cleaned):
        fail(
            "#221: do not invent name_score raise/lower UI "
            "(threshold policy is not this issue)"
        )
    if not _REVIEW_SAMPLE_EACH.search(surface):
        fail(
            "#221: sample loop must stay {#each panel.samples "
            "(do not add a second body dump)"
        )
    if _REVIEW_SECOND_BODY.search(surface):
        fail(
            "#221: do not add a second body dump — keep the existing "
            "panel.samples loop"
        )

    # 8) docs/user/app.md: Review + undo / reversible / no raw person id
    #    (or identifiers + undo).
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    review_docs = _review_docs_blob(dtxt)
    if not dtxt.strip() or not review_docs:
        fail(
            "#221: docs/user/app.md required — Review + undo / reversible / "
            "no raw person id (or identifiers + undo)"
        )
    has_undo = bool(_REVIEW_DOCS_UNDO.search(review_docs))
    has_no_raw = bool(_REVIEW_DOCS_NO_RAW.search(review_docs))
    has_idents = bool(_REVIEW_DOCS_IDENTS.search(review_docs))
    if not (has_undo and (has_no_raw or has_idents)):
        fail(
            "#221: docs/user/app.md must say Review + undo / reversible / "
            "no raw person id (or identifiers + undo)"
        )

    # 9) Do not soften #q, sidebar, overlay, inspector, CSP,
    #    #219 tokens, #220 data-import-cancel, #218 no Theme.
    svelte_files = _product_svelte(crate)
    svelte_blob = "\n".join(p.read_text() for p in svelte_files)
    app_path = crate / "web" / "App.svelte"
    app = app_path.read_text() if app_path.is_file() else ""
    search_path = crate / "web" / "lib" / "SearchPane.svelte"
    search = search_path.read_text() if search_path.is_file() else ""
    conf = (crate / "tauri.conf.json").read_text()
    css_path = crate / "web" / "app.css"
    css = css_path.read_text() if css_path.is_file() else ""
    light_blob = _contrast_light_blob(css)
    dark_blob = _contrast_dark_blob(css)
    if not re.search(r"""\bid\s*=\s*(?:["']q["']|\{\s*["']q["']\s*\})""", search):
        fail('#221: keep id="q" as the canonical query field (#208)')
    if not re.search(r"\bdata-people-sidebar\b", app):
        fail("#221: keep data-people-sidebar (#159 / #212)")
    if not re.search(r"titleBarStyle", conf) and not re.search(
        r"\bdata-tauri-drag-region\b", app
    ):
        fail("#221: keep the overlay titlebar (#211)")
    if not re.search(r"\bdata-person-inspector\b", app):
        fail("#221: keep data-person-inspector (#213)")
    if CSP not in conf:
        fail("#221: do not soften tauri CSP")
    if not _css_var(light_blob, _STATUS_WARNING_NAMES) or not _css_var(
        dark_blob, _STATUS_WARNING_NAMES
    ):
        fail("#221: keep #219 --warning / --color-warning in light and dark")
    if "data-import-cancel" not in svelte_blob:
        fail("#221: keep #220 data-import-cancel")
    if not _css_var(css, _APPEARANCE_SCRIM_NAMES):
        fail("#221: keep #218 --overlay / --scrim / --lightbox-scrim")
    if _APPEARANCE_THEME_UI.search(svelte_blob) or _APPEARANCE_MENU_LABEL.search(
        svelte_blob
    ):
        fail("#221: keep #218 — no Theme / Appearance menu / data-theme")


# #269 — people sidebar undo chrome (names, skip split_person). Sibling of #221.
_SIDEBAR_UNDO_EACH_SRC = re.compile(
    r"\b(?:events|undoableEvents|undoEvents|sidebarEvents|sidebarUndo|"
    r"undoable|lastUndoable|filteredEvents|linkEvents|undoList)\b",
    re.I,
)
_SIDEBAR_RAW_ID_TITLE = re.compile(
    r"("
    r"#\{\s*(?:e|ev|event|row)\s*\.\s*id\s*\}"
    r"|#\{\s*id\s*\}"
    r")"
)
_SIDEBAR_BARE_ID_TEXT = re.compile(
    r"\{\s*(?:e|ev|event|row)\s*\.\s*id\s*\}"
)
_SIDEBAR_CONFIRM_RAW = re.compile(
    r"("
    r"Undo event\s*\$\{"
    r"|Undo event\s*['\"`]\s*\+"
    r"|event\s+\$\{\s*id"
    r"|event\s+\$\{\s*(?:e|ev|event)\s*\.\s*id"
    r")"
)
_SIDEBAR_UNDO_FN_NAMES = (
    "doUndo",
    "requestUndo",
    "undoLast",
    "undoEvent",
    "askUndo",
    "runUndo",
)
_SIDEBAR_DOCS_UNDO = re.compile(
    r"("
    r"(?:people\s+)?sidebar.{0,160}\bundo\b"
    r"|\bundo\b.{0,160}(?:people\s+)?sidebar"
    r")",
    re.I | re.S,
)
_SIDEBAR_DOCS_SKIP = re.compile(
    r"("
    r"split_person"
    r"|undo-log"
    r"|undo log"
    r"|already[- ]undone"
    r"|skip(?:s|ping)?\s+(?:the\s+)?(?:undo[- ]log|split)"
    r")",
    re.I,
)
_SIDEBAR_DOCS_NO_RAW = re.compile(
    r"("
    r"raw event ids?"
    r"|no raw event"
    r"|not raw event"
    r"|without raw event"
    r"|not.{0,40}(?:raw )?event id"
    r"|event id as (?:the )?(?:title|label|only)"
    r"|name/?op(?: label)?"
    r")",
    re.I,
)


def _svelte_each_blocks(text: str) -> list[tuple[str, str]]:
    """`(source as alias …, inner)` for each `{#each}` in markup (nested-aware)."""
    out: list[tuple[str, str]] = []
    i = 0
    n = len(text)
    while i < n:
        m = re.search(r"\{#each\s+([^}]+)\}", text[i:])
        if not m:
            break
        inner_start = i + m.end()
        depth = 1
        j = inner_start
        while j < n and depth:
            nxt = re.search(r"\{#each\b|\{/each\}", text[j:])
            if not nxt:
                j = n
                break
            tok = nxt.group(0)
            j = j + nxt.end()
            if tok.startswith("{#each"):
                depth += 1
            else:
                depth -= 1
        inner_end = j - len("{/each}") if depth == 0 else n
        out.append((m.group(1).strip(), text[inner_start:inner_end]))
        i = inner_start
    return out


def _markup_text_nodes(block: str) -> str:
    """Drop attribute values so `{e.id}` in onclick / bind does not count."""
    out = re.sub(r"\b[\w:.-]+\s*=\s*\{(?:[^{}]|\{[^{}]*\})*\}", " ", block)
    out = re.sub(r"\b[\w:.-]+\s*=\s*\"[^\"]*\"", " ", out)
    out = re.sub(r"\b[\w:.-]+\s*=\s*'[^']*'", " ", out)
    return out


def _people_sidebar_region(markup: str) -> str:
    """People sidebar slice (data-people-sidebar → timeline / inspector)."""
    m = re.search(r"\bdata-people-sidebar\b", markup)
    if not m:
        return ""
    start = m.start()
    rest = markup[start + 20 :]
    end_m = re.search(
        r"("
        r"id\s*=\s*[\"']person-timeline[\"']"
        r"|data-person-inspector"
        r"|data-conversation-switcher"
        r")",
        rest,
    )
    end = start + 20 + end_m.start() if end_m else min(len(markup), start + 16000)
    return markup[start:end]


def _sidebar_undo_fn_blob(cleaned: str) -> str:
    chunks: list[str] = []
    for name in _SIDEBAR_UNDO_FN_NAMES:
        body = _ts_fn_body(cleaned, name) or _function_body(cleaned, name)
        if body:
            chunks.append(body)
    return "\n".join(chunks)


def _sidebar_each_guard_blob(cleaned: str, inner: str) -> str:
    """Each-block plus named helpers it calls (isUndoable / lastUndoable)."""
    parts = [inner]
    for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", inner):
        if name in {"doUndo", "undo", "api"}:
            continue
        body = _ts_fn_body(cleaned, name) or _function_body(cleaned, name)
        if body:
            parts.append(body)
    return "\n".join(parts)


def assert_sidebar_undo_chrome(crate: Path) -> None:
    """#269: people sidebar undo — human label, skip split_person.

    Same undoable set as Review lastUndoable. No raw event id as the title.
    Confirm has no Undo event ${id}. ConfirmDialog close-first + App
    onerror stay (#221). Do not rewrite #221 / #265.
    """
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#269: App.svelte required (people sidebar undo chrome lives there)")
    app_src = app_path.read_text()
    cleaned = _without_comments(app_src)
    markup = _svelte_markup(app_src)
    sidebar = _people_sidebar_region(markup) or markup

    # 1) Visible title is not #{e.id} / raw event id.
    title_blobs: list[str] = [_markup_text_nodes(sidebar)]
    for src, inner in _svelte_each_blocks(markup):
        if _SIDEBAR_UNDO_EACH_SRC.search(src):
            title_blobs.append(_markup_text_nodes(inner))
    title_blob = "\n".join(title_blobs)
    raw_title = _SIDEBAR_RAW_ID_TITLE.search(title_blob) or _SIDEBAR_BARE_ID_TEXT.search(
        title_blob
    )
    if raw_title:
        fail(
            "#269: people sidebar undo list must not show #{e.id} / raw "
            "event id as the title (use a short human op + name label; "
            f"found {raw_title.group(0)!r})"
        )

    # 2) Undo path mentions split_person + undo_of (or lastUndoable).
    has_split = "split_person" in cleaned
    has_undo_of = "undo_of" in cleaned
    has_last = "lastUndoable" in cleaned
    if not (has_split and (has_undo_of or has_last)):
        fail(
            "#269: App.svelte undo path must mention split_person and "
            "undo_of (or lastUndoable) — skip the leftover undo-log"
        )

    # 3) Do not call doUndo / api.undo on every events row / split_person.
    for src, inner in _svelte_each_blocks(markup):
        head = src.split(" as ", 1)[0].strip()
        if not re.fullmatch(r"events", head):
            continue
        if not re.search(r"\b(?:doUndo|api\s*\.\s*undo)\s*\(", inner):
            continue
        guard = _sidebar_each_guard_blob(cleaned, inner)
        if not re.search(r"split_person|undo_of|lastUndoable", guard):
            fail(
                "#269: do not call doUndo / api.undo on every events row "
                "including split_person — filter to the Review lastUndoable "
                "set (user merge/link/unlink, not already undone)"
            )

    # 4) Confirm title/body for sidebar undo has no Undo event ${id}.
    undo_fn_blob = _sidebar_undo_fn_blob(cleaned)
    confirm_blob = undo_fn_blob if undo_fn_blob.strip() else cleaned
    raw_confirm = _SIDEBAR_CONFIRM_RAW.search(confirm_blob)
    if raw_confirm:
        fail(
            "#269: sidebar undo confirm must not say Undo event ${id} / "
            "event ${id} (Undo last link? / Undo this merge? is fine; "
            f"found {raw_confirm.group(0)!r})"
        )

    # 5) Keep #221: ConfirmDialog close-first + App onerror; Review
    #    lastUndoable / data-review-undo / skip split_person.
    confirm_path = crate / "web" / "lib" / "ConfirmDialog.svelte"
    if not confirm_path.is_file():
        fail(
            "#269: keep #221 — ConfirmDialog.svelte required "
            "(go() must close before await onconfirm())"
        )
    confirm_src = _without_comments(confirm_path.read_text())
    go_body = _ts_fn_body(confirm_src, "go") or _function_body(confirm_src, "go")
    if not go_body:
        fail(
            "#269: keep #221 — ConfirmDialog.svelte go() required "
            "(set open = false before await onconfirm())"
        )
    await_onconfirm = _REVIEW_AWAIT_ONCONFIRM.search(go_body)
    if await_onconfirm:
        close_open = _REVIEW_OPEN_FALSE.search(go_body)
        if not close_open or close_open.start() > await_onconfirm.start():
            fail(
                "#269: keep #221 — ConfirmDialog go() must set open = false "
                "before await onconfirm() (or not await onconfirm)"
            )
    has_onerror = bool(_REVIEW_ONERROR_PROP.search(confirm_src))
    if not has_onerror or not _confirm_go_catches_onconfirm(go_body):
        fail(
            "#269: keep #221 — ConfirmDialog go() must catch onconfirm "
            "and have an onerror / onError prop"
        )
    app_confirm_tag = _review_component_tag(app_src, "ConfirmDialog")
    if not app_confirm_tag:
        fail("#269: keep #221 — App.svelte ConfirmDialog required")
    if not _REVIEW_APP_CONFIRM_ERR.search(app_confirm_tag):
        fail(
            "#269: keep #221 — App.svelte ConfirmDialog must pass "
            "onerror / onError / showErr"
        )
    review_path = crate / "web" / "lib" / "ReviewPane.svelte"
    review_src = review_path.read_text() if review_path.is_file() else ""
    if "data-review-undo" not in review_src or "lastUndoable" not in review_src:
        fail("#269: keep #221 — Review data-review-undo / lastUndoable")
    if "split_person" not in review_src or "undo_of" not in review_src:
        fail("#269: keep #221 — Review undo must still skip split_person / undo_of")

    # 6) Docs: sidebar undo + skip split / no raw event id.
    docs = repo_root() / "docs" / "user" / "app.md"
    dtxt = docs.read_text() if docs.is_file() else ""
    if not dtxt.strip():
        fail(
            "#269: docs/user/app.md required — people sidebar undo uses a "
            "name/op label, skips split_person / undo-log, no raw event id"
        )
    if not _SIDEBAR_DOCS_UNDO.search(dtxt):
        fail(
            "#269: docs/user/app.md must say people sidebar undo "
            "(name/op label, matches Review)"
        )
    if not _SIDEBAR_DOCS_SKIP.search(dtxt):
        fail(
            "#269: docs/user/app.md must say sidebar undo skips "
            "split_person / undo-log / already-undone"
        )
    if not _SIDEBAR_DOCS_NO_RAW.search(dtxt):
        fail(
            "#269: docs/user/app.md must say sidebar undo does not use a "
            "raw event id as the title (name/op label)"
        )
