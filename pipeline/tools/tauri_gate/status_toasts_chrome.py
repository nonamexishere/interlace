"""Helpers extracted from status_toasts.py (status_toasts_chrome)."""
from __future__ import annotations

from __future__ import annotations

from __future__ import annotations

import re
from pathlib import Path

from common import (
    fail,
    repo_root,
)

from tauri_gate.scan import (
    _ancestor_tags,
    _call_arg,
    _CHROME_HELPER_NAMES,
    _CHROME_IMPORT_SPEC,
    _CHROME_NO_TRANSLATE_FIELDS,
    _DATA_PEOPLE_SIDEBAR,
    _function_body,
    _markup_open_tag,
    _match_closer,
    _open_tag_around,
    _PERSON_PANE_SKIP,
    _product_svelte,
    _SANDBOX_137,
    _search_pane_blob,
    _strip_html_comments,
    _ts_function_body,
    _web_logic,
    _web_sources,
    _web_ts_sources,
    _without_comments,
)

from tauri_gate.import_boot_guards import (
    _HUMAN_TIME_HELPERS,
    _if_gen_eq_contains,
    _input_guard_span,
    _owned_imported_names,
)
from tauri_gate.import_boot_guards_rest import (
    _assignment_gen_guarded,
    _same_block_gen_ne_return,
    _svelte_if_true_branch,
    _svelte_open_tag_at,
)
from tauri_gate.status_toasts_hues import _HUE_AMBER, _SPINNER_NAME, _hue_surface

_CONTRAST_HSL = re.compile(
    r"hsla?\(\s*(-?[\d.]+)\s*(?:deg)?\s*[,/\s]\s*"
    r"(-?[\d.]+)%\s*[,/\s]\s*(-?[\d.]+)%",
    re.I,
)
_HM_PART = re.compile(
    r"("
    r"getUTCHours"
    r"|getUTCMinutes"
    r"|getHours"
    r"|getMinutes"
    r"|getDate"
    r"|slice\s*\(\s*11\s*,\s*16\s*\)"
    r"|slice\s*\(\s*t\s*\+\s*1\s*,\s*t\s*\+\s*6\s*\)"
    r"|hour\s*:\s*[\"']2-digit[\"']"
    r"|minute\s*:\s*[\"']2-digit[\"']"
    r")",
)
_MOD_CTRL = re.compile(r"(?:e\.)?ctrlKey")
_MOD_META = re.compile(r"(?:e\.)?metaKey")
_NEGATED_SCOPE = re.compile(
    r"\b(?:not|no|never|out of scope|isn't|is not|don't|do not)\b",
    re.I,
)
_PEOPLE_ONLY_RETURN = re.compile(
    r"if\s*\(\s*view\s*!==?\s*[\"']people[\"']\s*\)\s*(?:\{\s*)?return\s*;"
)
_SEARCH_EFFECT = re.compile(r"\$effect(?:\.pre)?\s*\(")
_UTC_FMT = re.compile(
    r"("
    r"getUTC(?:Date|Month|Hours|Minutes|FullYear)"
    r"|timeZone\s*:\s*[\"']UTC[\"']"
    r"|slice\s*\(\s*[\"']T[\"']\s*\)"
    r"|indexOf\s*\(\s*[\"']T[\"']\s*\)"
    r"|\bUTC\b"
    r")",
)


def _chrome_import_names(logic: str) -> set[str]:
    names: set[str] = set()
    for m in re.finditer(
        r"import\s+(?:type\s+)?(?:(\w+)\s*,\s*)?\{([^}]+)\}\s+from\s+[\"']([^\"']+)[\"']",
        logic,
    ):
        if not _CHROME_IMPORT_SPEC.search(m.group(3)):
            continue
        if m.group(1):
            names.add(m.group(1))
        for part in m.group(2).split(","):
            bit = part.strip()
            if not bit or bit.startswith("type "):
                continue
            names.add(re.split(r"\s+as\s+", bit)[-1].strip())
    for m in re.finditer(
        r"import\s+(\w+)\s+from\s+[\"']([^\"']+)[\"']",
        logic,
    ):
        if _CHROME_IMPORT_SPEC.search(m.group(2)):
            names.add(m.group(1))
    for m in re.finditer(
        r"import\s+\*\s+as\s+(\w+)\s+from\s+[\"']([^\"']+)[\"']",
        logic,
    ):
        if _CHROME_IMPORT_SPEC.search(m.group(2)):
            names.add(m.group(1))
    return {n for n in names if n}


def _parse_if_chain(src: str, if_start: int) -> tuple[list[tuple[str, str]], int]:
    """Sibling branches of one {#if}…{/if}. Nested ifs stay inside bodies."""
    head = re.match(r"\{#if\s+([^}]+)\}", src[if_start:])
    if not head:
        return [], if_start
    cond = head.group(1).strip()
    i = if_start + head.end()
    body_start = i
    depth = 1
    branches: list[tuple[str, str]] = []
    n = len(src)
    while i < n:
        if src.startswith("{#if", i) or src.startswith("{#each", i) or src.startswith(
            "{#await", i
        ) or src.startswith("{#key", i):
            depth += 1
            i += 3
            continue
        if src.startswith("{/if}", i):
            depth -= 1
            if depth == 0:
                branches.append((cond, src[body_start:i]))
                return branches, i + 5
            i += 5
            continue
        if src.startswith("{/each}", i) or src.startswith("{/await}", i) or src.startswith(
            "{/key}", i
        ):
            depth -= 1
            i += 3
            continue
        if depth == 1 and src.startswith("{:else if", i):
            branches.append((cond, src[body_start:i]))
            em = re.match(r"\{:else\s+if\s+([^}]+)\}", src[i:])
            if not em:
                i += 1
                continue
            cond = em.group(1).strip()
            i += em.end()
            body_start = i
            continue
        if depth == 1 and src.startswith("{:else}", i):
            branches.append((cond, src[body_start:i]))
            cond = ":else"
            i += len("{:else}")
            body_start = i
            continue
        i += 1
    return branches, i


def _owned_skeleton_names(src: str) -> list[str]:
    return _owned_imported_names(src, "skeleton")


# #203 — quiet muted skeleton on people / timeline / search in-flight.
_SKELETON_HOOK = re.compile(r"\bdata-skeleton\b")


def _has_mod_combo(src: str) -> bool:
    return bool(_MOD_META.search(src) and _MOD_CTRL.search(src))


# #159 — people sidebar: vertical scroll only; long names/previews do not pan sideways.
_PEOPLE_EACH = re.compile(r"\{#each\s+filtered\b")
_CONTRAST_COLOR_SCHEME = re.compile(
    r"(?:^|[,}\s])(?::root|html)(?:\s*,\s*(?:html|body|#app|:root))*\s*\{"
    r"[^}]*color-scheme\s*:\s*light\s+dark\b",
    re.I | re.S,
)


def _cond_code(cond: str) -> str:
    """Drop quoted strings so 'append' inside \"append\" is not a flag."""
    return re.sub(r"""(['\"])(?:\\.|(?!\1).)*\1""", '""', cond)


def _first_substr_pos(body: str, needles: tuple[str, ...]) -> int:
    found = [body.find(n) for n in needles]
    found = [i for i in found if i >= 0]
    return min(found) if found else -1
_WRITE_TEXT = re.compile(
    r"("
    r"navigator\.clipboard\.writeText"
    r"|clipboard\.writeText"
    r")"
)


def _windows_around(src: str, rx: re.Pattern[str], before: int = 280, after: int = 640) -> str:
    return "\n".join(
        src[max(0, m.start() - before) : m.end() + after] for m in rx.finditer(src)
    )
_FOCUS_SEARCH_Q = re.compile(
    r"("
    r"getElementById\s*\(\s*[\"']q[\"']"
    r"|querySelector\s*\(\s*[\"']#q[\"']"
    r")",
)
_KEY_ESC = re.compile(
    r"("
    r"(?:e\.)?key\s*===?\s*[\"']Escape[\"']"
    r"|[\"']Escape[\"']\s*===?\s*(?:e\.)?key"
    r")",
)
_MOTION_DURATION_ZERO = re.compile(
    r"("
    r"\bduration\s*:\s*0\b"
    r"|\bduration\s*=\s*0\b"
    r"|\?\s*0\s*:"
    r")"
)


def _contrast_surface_tag(src: str, hook: str) -> str:
    at = src.find(hook)
    if at < 0:
        return ""
    return _markup_open_tag(src, src.rfind("<", 0, at + 1))


def _hsl_tuple(value: str) -> tuple[float, float, float] | None:
    m = _CONTRAST_HSL.search(value)
    if not m:
        return None
    return float(m.group(1)), float(m.group(2)), float(m.group(3))


def _toml_keys_in_fn(body: str) -> list[str]:
    keys: list[str] = []
    for s in re.findall(r'"(?:[^"\\]|\\.)*"', body):
        keys.extend(re.findall(r"([A-Za-z_][\w]*)\s*=", s))
    return keys
_MONTH_SHORT = re.compile(
    r"("
    r"[\"'](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\"']"
    r"|month\s*:\s*[\"']short[\"']"
    r")",
    re.I,
)


def _without_input_guard(body: str) -> str:
    span = _input_guard_span(body)
    if not span:
        return body
    return body[: span[0]] + body[span[1] + 1 :]
_CDN_HINT = re.compile(
    r"("
    r"cdn\.|unpkg\.com|jsdelivr|googleapis|gstatic|cloudflare"
    r"|fonts\.google"
    r")",
    re.I,
)
_MOTION_JS_REDUCE = re.compile(
    r"("
    r"\bmatchMedia\s*\("
    r"|\bMediaQuery\b"
    r"|\bprefersReducedMotion\b"
    r"|prefers-reduced-motion"
    r")"
)


def _split_people_only(body: str) -> tuple[str, str]:
    """Prefix always runs; suffix only runs on People (`view !== "people" return`)."""
    m = _PEOPLE_ONLY_RETURN.search(body)
    if not m:
        return body, ""
    return body[: m.start()], body[m.end() :]
_SERVER_PROGRESS = re.compile(
    r"("
    r"progress\s*%"
    r"|percent(?:age)?\s*(?:from|via|of)\s*(?:server|network|http)"
    r"|fetch(?:Progress|Percent)"
    r")",
    re.I,
)

from tauri_gate.status_toasts_chrome_rest import (
    _NET_IMG,
    _APPEARANCE_DOCS_NO_THEME,
    _claim_without_negation,
    _people_inflight_branch,
    _status_hook_blob,
    _APPEARANCE_DOCS_ARCHIVAL,
    _CONTRAST_DOCS_SYSTEM,
    _skeleton_hook_positions,
    _DOCS_TYPO_NO_REMOTE_FONT,
    _payload_has_path_or_url,
    _SPINNER_NAME,
    _APPEARANCE_THEME_UI,
    _typo_docs_blob,
    _TYPO_REMOTE_FONT,
    _THEME_CDN,
    _invoke_payloads,
    _chrome_helper_names,
    _SECOND_UI_KIT,
    __all__,
)

__all__ = [
    "_CONTRAST_HSL",
    "_HM_PART",
    "_MOD_CTRL",
    "_MOD_META",
    "_NEGATED_SCOPE",
    "_PEOPLE_ONLY_RETURN",
    "_SEARCH_EFFECT",
    "_UTC_FMT",
    "_chrome_import_names",
    "_parse_if_chain",
    "_owned_skeleton_names",
    "_SKELETON_HOOK",
    "_hue_surface",
    "_HUE_AMBER",
    "_has_mod_combo",
    "_PEOPLE_EACH",
    "_CONTRAST_COLOR_SCHEME",
    "_cond_code",
    "_assignment_gen_guarded",
    "_first_substr_pos",
    "_WRITE_TEXT",
    "_windows_around",
    "_FOCUS_SEARCH_Q",
    "_KEY_ESC",
    "_MOTION_DURATION_ZERO",
    "_contrast_surface_tag",
    "_hsl_tuple",
    "_toml_keys_in_fn",
    "_MONTH_SHORT",
    "_without_input_guard",
    "_CDN_HINT",
    "_MOTION_JS_REDUCE",
    "_split_people_only",
    "_SERVER_PROGRESS",
    "_NET_IMG",
    "_APPEARANCE_DOCS_NO_THEME",
    "_claim_without_negation",
    "_people_inflight_branch",
    "_status_hook_blob",
    "_APPEARANCE_DOCS_ARCHIVAL",
    "_CONTRAST_DOCS_SYSTEM",
    "_skeleton_hook_positions",
    "_DOCS_TYPO_NO_REMOTE_FONT",
    "_payload_has_path_or_url",
    "_SPINNER_NAME",
    "_APPEARANCE_THEME_UI",
    "_typo_docs_blob",
    "_TYPO_REMOTE_FONT",
    "_THEME_CDN",
    "_invoke_payloads",
    "_chrome_helper_names",
    "_SECOND_UI_KIT",
    "annotations",
    "re",
    "Path",
    "fail",
    "repo_root",
    "_ancestor_tags",
    "_call_arg",
    "_CHROME_HELPER_NAMES",
    "_CHROME_IMPORT_SPEC",
    "_CHROME_NO_TRANSLATE_FIELDS",
    "_DATA_PEOPLE_SIDEBAR",
    "_function_body",
    "_markup_open_tag",
    "_match_closer",
    "_open_tag_around",
    "_PERSON_PANE_SKIP",
    "_product_svelte",
    "_SANDBOX_137",
    "_search_pane_blob",
    "_strip_html_comments",
    "_ts_function_body",
    "_web_logic",
    "_web_sources",
    "_web_ts_sources",
    "_without_comments",
    "_HUMAN_TIME_HELPERS",
    "_if_gen_eq_contains",
    "_input_guard_span",
    "_owned_imported_names",
    "_same_block_gen_ne_return",
    "_svelte_if_true_branch",
    "_svelte_open_tag_at",
]
