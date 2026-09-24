"""#378 — jump to a year from the inspector (confirmed mix, 2026-09-22).

Wired immediately after assert_group_participant_open (#377).

Year buttons sit under last activity (`data-activity-years` before
`data-mail-recipients`). Counts only: `person_year_counts(person_id,
include_groups)` → `{ year, count, first_local_day }`. Click calls
`jumpToDayKey(first_local_day)` → existing `goToJumpDay` / `jumpToLocalDay`.
Quiet miss. No chart, heatmap, bodies, or `$effect` on `includeGroups`.

Placeholders Ada / Berk / Self. Same ChromeKey on en.ts + tr.ts.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail, repo_root
from tauri_gate.include_groups import _arrow_prop
from tauri_gate.include_groups_fold import (
    _fn_params,
    _has_include_groups_effect,
)
from tauri_gate.last_read import _text, _web_file
from tauri_gate.locale_pack import _chrome_pack_entries
from tauri_gate.scan import (
    _call_arg,
    _match_closer,
    _rust_body_with_callees,
    _rust_fn_signature,
    _rust_function_body,
    _rust_match_delim,
    _rust_next,
    _svelte_interpolations,
    _svelte_markup,
    _without_comments,
)
from tauri_gate.timeline_gmail_labels import _rust_struct_body

_ISSUE = "#378"
_PRIMARY = (
    f"{_ISSUE}: inspector year list is missing "
    "(data-activity-years under last activity, before data-mail-recipients)"
)

_COPY = {
    "activityYears": ("Years", "Yıllar"),
    "activityYearsFailed": ("Could not load years", "Yıllar yüklenemedi"),
    "activityYearsRetry": ("Retry", "Yeniden dene"),
}
_PLACEHOLDER = re.compile(r"\bAda\b|\bBerk\b|\bSelf\b")
_T_KEY = re.compile(r"""\bt\(\s*["']([A-Za-z_][A-Za-z0-9_]*)["']\s*\)""")
_BANNED_FIELDS = (
    "body_text",
    "body_html",
    "subject",
    "snippet",
    "title",
    "attachment",
    "filename",
)
_SKIP_CALL = frozenset(
    """
    if for while switch catch function return await void typeof instanceof
    of in new throw try else true false null undefined
    map filter forEach reduce some every find findIndex includes
    trim slice toLowerCase toUpperCase Number String Boolean Object Array
    preventDefault stopPropagation then catch finally
    querySelector closest console log warn
    """.split()
)
_WALL = re.compile(
    r"whatsapp|is\s+null|=\s*''|=\s*\"\"|trim\s*\(|ifnull\s*\(|coalesce\s*\(",
    re.I,
)
_SUBSTR = re.compile(r"\bsubstr\s*\(|\bsubstring\s*\(", re.I)
_LOCALTIME = re.compile(r"localtime", re.I)
_UTC_YEAR = re.compile(
    r"strftime\s*\(\s*(['\"])%Y\1\s*,([^)]*)\)",
    re.I,
)
_SHAPE = re.compile(
    r"GLOB|LIKE\s+['\"]_|"
    r"\[0-9\]|\\d\{4\}|is_ascii_digit|ascii_digit",
    re.I,
)
_SQL_KW = re.compile(r"\b(?:CASE|WHEN|THEN|ELSE|END)\b", re.I)
_JAN1 = re.compile(r"-01-01")
_GEN_INC = re.compile(
    r"\+\+\s*([A-Za-z_]\w*)|([A-Za-z_]\w*)\s*\+\+|([A-Za-z_]\w*)\s*\+=\s*1"
)


def _without_rust_comments(src: str) -> str:
    out: list[str] = []
    i = 0
    n = len(src)
    while i < n:
        nxt = _rust_next(src, i)
        if nxt != i:
            if src.startswith("//", i) or src.startswith("/*", i):
                out.append("\n" if "\n" in src[i:nxt] else " ")
            else:
                out.append(src[i:nxt])
            i = nxt
            continue
        out.append(src[i])
        i += 1
    return "".join(out)


def _end_of_tag(src: str, start: int) -> int:
    i = start
    n = len(src)
    while i < n:
        c = src[i]
        if c == "{":
            end = _match_closer(src, i)
            if end < 0:
                return -1
            i = end + 1
            continue
        if c in "'\"":
            q = c
            i += 1
            while i < n and src[i] != q:
                if src[i] == "\\":
                    i += 2
                    continue
                i += 1
            i += 1
            continue
        if c == ">":
            return i + 1
        i += 1
    return -1


def _elements(markup: str, name: str) -> list[str]:
    out: list[str] = []
    token = f"<{name}"
    i = 0
    n = len(markup)
    low = markup.lower()
    name_l = name.lower()
    while True:
        j = low.find(token.lower(), i)
        if j < 0:
            break
        after = j + len(token)
        if after < n and (markup[after].isalnum() or markup[after] in "-_"):
            i = after
            continue
        end_open = _end_of_tag(markup, j)
        if end_open < 0:
            break
        close = f"</{name_l}>"
        k = low.find(close, end_open)
        if k < 0:
            out.append(markup[j:end_open])
            i = end_open
        else:
            out.append(markup[j : k + len(close)])
            i = k + len(close)
    return out


def _attr_exprs(src: str, name: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(rf"\b{re.escape(name)}\s*=\s*\{{", src):
        close = _match_closer(src, m.end() - 1)
        if close > m.end():
            out.append(src[m.end() : close])
    return out


def _year_region(markup: str) -> str:
    m = re.search(r"""t\(\s*["']lastActivity["']\s*\)""", markup)
    if not m:
        return ""
    p_end = markup.find("</p>", m.end())
    if p_end < 0:
        return ""
    mail = markup.find("data-mail-recipients", p_end)
    if mail < 0:
        return ""
    return markup[p_end:mail]


def _if_ranges(markup: str) -> list[tuple[int, int, str]]:
    token = re.compile(r"\{#if\s+([^}]*)\}|\{/if\}")
    stack: list[tuple[int, str]] = []
    ranges: list[tuple[int, int, str]] = []
    for m in token.finditer(markup):
        if m.group(0).startswith("{#if"):
            stack.append((m.start(), m.group(1).strip()))
        elif stack:
            start, cond = stack.pop()
            ranges.append((start, m.end(), cond))
    return ranges


def _branch_bodies(src: str) -> list[tuple[str, str]]:
    token = re.compile(
        r"\{#if\s+([^}]*)\}|\{:else\s+if\s+([^}]*)\}|\{:else\}|\{/if\}"
    )
    stack: list[tuple[str, int]] = []
    out: list[tuple[str, str]] = []
    for m in token.finditer(src):
        raw = m.group(0)
        if raw.startswith("{#if"):
            stack.append((m.group(1).strip(), m.end()))
        elif raw.startswith("{:else if"):
            if stack:
                cond, start = stack.pop()
                out.append((cond, src[start : m.start()]))
            stack.append(((m.group(2) or "").strip(), m.end()))
        elif raw.startswith("{:else}"):
            if stack:
                cond, start = stack.pop()
                out.append((cond, src[start : m.start()]))
            stack.append(("", m.end()))
        elif stack:
            cond, start = stack.pop()
            out.append((cond, src[start : m.start()]))
    return out


def _derived_expr(script: str, name: str) -> str:
    parts: list[str] = []
    for m in re.finditer(rf"\b{re.escape(name)}\s*=\s*", script):
        rest = script[m.end() :]
        if rest.startswith("$derived"):
            paren = rest.find("(")
            if paren >= 0:
                parts.append(_call_arg(script, m.end() + paren))
            continue
        line = rest.split(";")[0].split("\n")[0]
        if line and "function" not in line:
            parts.append(line)
    return "\n".join(parts)


def _resolved_cond(cond: str, script: str) -> str:
    text = cond
    for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", cond):
        if name in {"true", "false", "null", "undefined", "showPersonChrome"}:
            continue
        extra = _derived_expr(script, name)
        if extra:
            text += "\n" + extra
    return text


def _guard_conds(markup: str, script: str) -> list[str]:
    ranges = _if_ranges(markup)
    conds: list[str] = []
    for m in re.finditer(r"\bdata-activity-years\b", markup):
        pos = m.start()
        inner = [
            r
            for r in ranges
            if r[0] < pos < r[1] and r[2].strip() != "showPersonChrome"
        ]
        if not inner:
            conds.append("")
            continue
        smallest = min(inner, key=lambda r: r[1] - r[0])
        conds.append(_resolved_cond(smallest[2], script))
    return conds


def _fn_body(src: str, name: str) -> str:
    """Function body, including a TypeScript return type before `{`."""
    m = re.search(
        rf"(?:export\s+)?(?:async\s+)?function\s+{re.escape(name)}\b\s*\("
        rf"|(?:export\s+)?(?:const|let|var)\s+{re.escape(name)}\s*=\s*"
        rf"(?:async\s*)?(?:function\s*)?\(",
        src,
    )
    if not m:
        return ""
    close = _match_closer(src, m.end() - 1)
    if close < 0:
        return ""
    i = close + 1
    n = len(src)
    angle = 0
    while i < n:
        c = src[i]
        if c in "'\"`":
            q = c
            i += 1
            while i < n and src[i] != q:
                if src[i] == "\\":
                    i += 2
                    continue
                i += 1
            i += 1
            continue
        if c == "<":
            angle += 1
        elif c == ">":
            angle = max(0, angle - 1)
        elif c == "{" and angle == 0:
            end = _match_closer(src, i)
            if end < 0:
                return src[i + 1 :]
            return src[i + 1 : end]
        if c == ";" and angle == 0:
            return ""
        i += 1
    return ""


def _bare_body(expr: str, sources: list[str]) -> str:
    m = re.fullmatch(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*", expr or "")
    if not m or m.group(1) in _SKIP_CALL:
        return expr
    for src in sources:
        body = _fn_body(src, m.group(1))
        if body:
            return body
        arrow = _arrow_prop(src, m.group(1))
        if arrow:
            return arrow
    return expr


def _follow(expr: str, sources: list[str], depth: int = 4) -> str:
    expr = _bare_body(expr, sources)
    blob = expr
    seen: set[str] = set()
    frontier = [expr]
    for _ in range(depth):
        nxt: list[str] = []
        for text in frontier:
            for name in re.findall(
                r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:\?\.)?\s*\(",
                text,
            ):
                if name in seen or name in _SKIP_CALL:
                    continue
                seen.add(name)
                for src in sources:
                    added = ""
                    body = _fn_body(src, name)
                    if body:
                        added += "\n" + body
                    arrow = _arrow_prop(src, name)
                    if arrow:
                        added += "\n" + arrow
                    if not added:
                        continue
                    blob += added
                    nxt.append(added)
                    break
        frontier = nxt
        if not frontier:
            break
    return blob


def _parse_case(text: str, case_at: int) -> tuple[list[tuple[str, str]], str, int]:
    """Split one CASE at `case_at` into (when, then) pairs, else, and end index."""
    whens: list[tuple[str, str]] = []
    else_body = ""
    depth = 0
    cond_start = -1
    then_start = -1
    else_start = -1
    cond = ""
    i = case_at
    first = True
    while True:
        m = _SQL_KW.search(text, i)
        if not m:
            return whens, else_body, len(text)
        kw = m.group(0).upper()
        if first:
            first = False
            if kw != "CASE":
                return whens, else_body, m.end()
            depth = 1
            i = m.end()
            continue
        if kw == "CASE":
            depth += 1
            i = m.end()
            continue
        if kw == "END":
            depth -= 1
            if depth == 0:
                if else_start >= 0:
                    else_body = text[else_start : m.start()]
                elif then_start >= 0:
                    whens.append((cond, text[then_start : m.start()]))
                return whens, else_body, m.end()
            i = m.end()
            continue
        if depth != 1:
            i = m.end()
            continue
        if kw == "WHEN":
            if then_start >= 0:
                whens.append((cond, text[then_start : m.start()]))
                then_start = -1
            cond_start = m.end()
            i = m.end()
        elif kw == "THEN":
            cond = text[cond_start:m.start()] if cond_start >= 0 else ""
            then_start = m.end()
            i = m.end()
        elif kw == "ELSE":
            if then_start >= 0:
                whens.append((cond, text[then_start : m.start()]))
                then_start = -1
            else_start = m.end()
            i = m.end()
        else:
            i = m.end()


def _wall_cond(cond: str) -> bool:
    c = cond.lower()
    if "whatsapp" in c:
        return True
    if "platform" not in c:
        return False
    return bool(
        re.search(r"is\s+null|''|trim\s*\(|ifnull\s*\(|coalesce\s*\(", c, re.I)
    )


def _blank_cond(cond: str) -> bool:
    if "platform" not in cond.lower() and "whatsapp" not in cond.lower():
        return False
    return bool(
        re.search(
            r"is\s+null|=\s*''|=\s*\"\"|trim\s*\(|ifnull\s*\(|coalesce\s*\(",
            cond,
            re.I,
        )
    )


def _cases_touching_whatsapp(text: str) -> list[tuple[list[tuple[str, str]], str]]:
    found: list[tuple[list[tuple[str, str]], str]] = []
    i = 0
    while True:
        m = re.search(r"\bCASE\b", text[i:], re.I)
        if not m:
            break
        start = i + m.start()
        whens, else_body, end = _parse_case(text, start)
        span = text[start:end]
        if re.search(r"whatsapp", span, re.I):
            found.append((whens, else_body))
        i = max(end, start + 4)
    return found


def _rust_strings(src: str) -> list[str]:
    out: list[str] = []
    i = 0
    n = len(src)
    while i < n:
        if src.startswith('r#"', i):
            end = src.find('"#"', i + 3)
            if end < 0:
                break
            out.append(src[i + 3 : end])
            i = end + 3
            continue
        if src[i] != '"':
            i += 1
            continue
        j = i + 1
        chars: list[str] = []
        while j < n:
            if src[j] == "\\":
                chars.append(src[j : j + 2])
                j += 2
                continue
            if src[j] == '"':
                out.append("".join(chars))
                j += 1
                break
            chars.append(src[j])
            j += 1
        else:
            break
        i = j
    return out


def _kind_limit(blob: str) -> bool:
    return bool(re.search(r"""['"]dm['"]""", blob) and re.search(r"""['"]email_thread['"]""", blob))


def _groups_filter_problem(body: str) -> str | None:
    if "include_groups" not in body:
        return (
            "person_year_counts must take include_groups and apply the D18 "
            "kind filter (groups only when the flag is true)"
        )
    if "sender_identity_id" not in body or "conversation_participants" not in body:
        return (
            "year SQL must keep sender OR participant, the same D18 "
            "membership as person_timeline_rows_for"
        )
    if "person_identities" not in body:
        return (
            "year SQL must use person_identities for sender and participant "
            "(same D18 predicate as person_timeline_rows_for)"
        )
    if not re.search(r"\bOR\b", body):
        return "year SQL must be sender or participant, not sender-only"
    found = False
    for m in re.finditer(r"if\s+(!)?\s*include_groups\b", body):
        neg = m.group(1) is not None
        brace = body.find("{", m.end())
        if brace < 0:
            continue
        end = _rust_match_delim(body, brace)
        if end < 0:
            continue
        then_b = body[brace + 1 : end]
        rest = body[end + 1 :]
        em = re.match(r"\s*else\s*\{", rest)
        else_b = ""
        if em:
            open_else = end + 1 + rest.find("{", em.start())
            else_end = _rust_match_delim(body, open_else)
            if else_end > open_else:
                else_b = body[open_else + 1 : else_end]
        limited_then = _kind_limit(then_b)
        limited_else = _kind_limit(else_b)
        if not neg and not limited_then and limited_else:
            found = True
        if neg and limited_then and not limited_else:
            found = True
    if not found:
        return (
            "include_groups must change the D18 kind filter: "
            "dm / email_thread only when the flag is false; groups when it is true"
        )
    for lit in _rust_strings(body):
        if re.search(r"\bSELECT\b", lit, re.I) and "email_thread" in lit:
            return (
                "do not bake AND kind IN ('dm','email_thread') into the year "
                "SELECT; groups are included when include_groups is true"
            )
    return None


def _bucket_problem(body: str) -> str | None:
    cases = _cases_touching_whatsapp(body)
    if not cases:
        return (
            "WhatsApp / blank platform must use the stored YYYY-MM-DD prefix "
            "(substr / digit check), not localtime; other platforms use localtime"
        )
    saw_wa = False
    saw_blank = False
    saw_local = False
    for whens, else_body in cases:
        wall = [(c, r) for c, r in whens if _wall_cond(c)]
        other = [(c, r) for c, r in whens if not _wall_cond(c)]
        if not wall:
            return (
                "bucket WhatsApp / blank platform with stored date digits "
                "(substr), not the same localtime path as Gmail"
            )
        for cond, result in wall:
            if "whatsapp" in cond.lower():
                saw_wa = True
            if _blank_cond(cond):
                saw_blank = True
            if not _SUBSTR.search(result) or _LOCALTIME.search(result):
                return (
                    "WhatsApp / blank platform uses substr of sent_at "
                    "(stored YYYY-MM-DD), not localtime"
                )
        other_text = "\n".join(r for _, r in other) + "\n" + else_body
        if _LOCALTIME.search(other_text):
            saw_local = True
    if not saw_wa or not saw_blank:
        return (
            "null or blank platform uses the same stored date digits as "
            "WhatsApp (not localtime)"
        )
    if not saw_local:
        return "other platforms must use strftime(..., 'localtime'), not UTC"
    if not _SHAPE.search(body):
        return (
            "reject a WhatsApp / blank sent_at that is not YYYY-MM-DD "
            "(digit check / GLOB around the substr)"
        )
    for m in _UTC_YEAR.finditer(body):
        if "localtime" not in m.group(2).lower():
            return (
                "do not bucket with UTC strftime('%Y', sent_at); "
                "other platforms use localtime"
            )
    return None


def _year_sql_problem(body: str) -> str | None:
    if not body.strip():
        return (
            "person_year_counts must live in people/timeline.rs or people.rs "
            "(counts only; no person_timeline paging)"
        )
    if re.search(r"\bperson_timeline", body):
        return (
            "do not build years by paging person_timeline "
            "(that SELECT includes body_text)"
        )
    for bad in ("body_text", "body_html", "subject", "snippet"):
        if re.search(rf"\b{bad}\b", body):
            return f"year SQL must not select {bad}"
    if re.search(r"\btitle\b", body):
        return "year SQL must not select a title"
    bucket = _bucket_problem(body)
    if bucket:
        return bucket
    groups = _groups_filter_problem(body)
    if groups:
        return groups
    if _JAN1.search(body):
        return "first_local_day is MIN(day), not a hard-coded -01-01"
    if re.search(r"generate_series", body, re.I):
        return "do not generate_series filler years (a year with no messages is absent)"
    if re.search(r"\bcount\s*:\s*0\b", body):
        return "do not emit count 0"
    if not re.search(
        r"COUNT\s*\(\s*(?:\*\s*|m\.id\s*|messages\.id\s*)\)",
        body,
        re.I,
    ):
        return "count is message rows (COUNT(*)), not distinct days or conversations"
    if re.search(r"COUNT\s*\(\s*DISTINCT\b", body, re.I):
        return "count is COUNT(*) per message, not COUNT(DISTINCT …)"
    if not re.search(r"\bMIN\s*\(", body, re.I):
        return "first_local_day is the minimum day key (MIN), not 1 January"
    if not re.search(r"\bGROUP\s+BY\b", body, re.I):
        return "group message rows by the local year"
    newest = bool(re.search(r"ORDER\s+BY\s+year\s+DESC\b", body, re.I)) or bool(
        re.search(r"\.reverse\s*\(|cmp::Reverse|\.rev\s*\(", body)
    )
    if not newest:
        return "newest year first (ORDER BY year DESC, or an equivalent reverse)"
    if not re.search(r"IS\s+NOT\s+NULL|!=\s*''|<>\s*''", body, re.I):
        return "drop null / rejected day keys (no undated year bucket)"
    if re.search(r"\battach_kind\b|:conv\b|m\.conversation_id\s*=", body):
        return (
            "year SQL takes only person_id and include_groups "
            "(no conversation, attachment, or chip filter)"
        )
    if re.search(r"\bfrom_me\b", body):
        return "the from-me chip does not change the year query"
    if re.search(r"chrono[-_]tz|tzdata|chrono_tz", body, re.I):
        return "no chrono-tz / tzdata (#268); host localtime plus stored WhatsApp digits"
    if re.search(r"@s\.whatsapp\.net|\bwhatsapp_jid\b", body, re.I):
        return "no JIDs in the year path (placeholders Ada / Berk / Self)"
    return None


def _struct_fields(body: str) -> list[str]:
    fields: list[str] = []
    for line in body.splitlines():
        if line.strip().startswith("#") or line.strip().startswith("//"):
            continue
        m = re.search(r"\b(?:pub\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*:", line)
        if m and m.group(1) not in {"serde", "derive"}:
            fields.append(m.group(1))
    return fields


def _json_struct_problem(src: str) -> str | None:
    name = ""
    for m in re.finditer(r"(?:pub\s+)?struct\s+([A-Za-z0-9_]+)\s*\{", src):
        chunk = _rust_struct_body(src, m.group(1))
        if "first_local_day" in chunk:
            name = m.group(1)
            break
    if not name:
        return (
            "year JSON is a struct with year, count, and first_local_day only "
            "(snake_case)"
        )
    chunk = _rust_struct_body(src, name)
    attr = src[max(0, src.find(f"struct {name}") - 240) : src.find(f"struct {name}")]
    if re.search(r"rename_all\s*=\s*\"camelCase\"", attr + chunk):
        return "year JSON fields stay snake_case (year, count, first_local_day)"
    fields = _struct_fields(chunk)
    allowed = {"year", "count", "first_local_day"}
    extra = [f for f in fields if f not in allowed]
    if extra or set(fields) != allowed:
        return (
            "year JSON fields are year, count, first_local_day only "
            f"(saw {', '.join(fields) or 'none'})"
        )
    if not re.search(r"\byear\s*:\s*(?:i16|i32|i64|u16|u32|u64|usize)\b", chunk):
        return "year is a number, not a string"
    if not re.search(r"\bcount\s*:\s*(?:i16|i32|i64|u16|u32|u64|usize)\b", chunk):
        return "count is a number"
    if not re.search(r"\bfirst_local_day\s*:\s*String\b", chunk):
        return "first_local_day is a YYYY-MM-DD string"
    for bad in _BANNED_FIELDS:
        if re.search(rf"\b{bad}\b", chunk):
            return f"year payload must not include {bad}"
    return None


def _ts_payload_problem(api: str) -> str | None:
    at = api.find("personYearCounts")
    if at < 0:
        return (
            "api.ts must expose personYearCounts({ id, includeGroups }) "
            '→ invoke "person_year_counts"'
        )
    win = api[at : at + 700]
    if "includeGroups" not in win or not re.search(r"\bid\b", win):
        return "personYearCounts takes id and includeGroups"
    if "person_year_counts" not in win:
        return 'personYearCounts must invoke "person_year_counts"'
    chunk = ""
    idx = 0
    while True:
        j = api.find("first_local_day", idx)
        if j < 0:
            break
        b = api.rfind("{", 0, j)
        if b >= 0:
            end = _match_closer(api, b)
            if end > j:
                piece = api[b : end + 1]
                if re.search(r"\byear\b", piece) and re.search(r"\bcount\b", piece):
                    chunk = piece
                    break
        idx = j + 1
    if not chunk:
        return (
            "api.ts year row type is { year: number, count: number, "
            "first_local_day: string } only"
        )
    if not re.search(r"\byear\s*\??\s*:\s*number\b", chunk):
        return "api.ts year is number"
    if not re.search(r"\bcount\s*\??\s*:\s*number\b", chunk):
        return "api.ts count is number"
    if not re.search(r"\bfirst_local_day\s*\??\s*:\s*string\b", chunk):
        return "api.ts first_local_day is string"
    for bad in _BANNED_FIELDS:
        if re.search(rf"\b{bad}\b", chunk):
            return f"api.ts year payload must not include {bad}"
    return None


def _locale_problem(en: dict[str, str], tr: dict[str, str]) -> str | None:
    for key, (ev, tv) in _COPY.items():
        if key not in en or key not in tr:
            return f"same ChromeKey {key} on en.ts and tr.ts"
        if (en.get(key) or "").strip() != ev:
            return f"en {key} must be {ev!r}"
        got = (tr.get(key) or "").strip()
        if got != tv:
            return f"tr {key} must be {tv!r}"
        if got == (en.get(key) or "").strip():
            return f"tr {key} must not be a copy of the English sentence"
    for pack in (en, tr):
        for val in pack.values():
            if _PLACEHOLDER.search(val):
                return "locale packs must not contain Ada / Berk / Self"
    return None


def _docs_problem(docs: str) -> str | None:
    for m in re.finditer(r"years?", docs, re.I):
        w = docs[max(0, m.start() - 180) : m.end() + 480]
        lw = w.lower()
        if (
            re.search(r"counts?", lw)
            and "last activity" in lw
            and re.search(r"no messages|without messages|zero messages", lw)
            and re.search(r"absent|omitted|not shown|not listed", lw)
            and "jump" in lw
            and re.search(r"\bday\b", lw)
        ):
            return None
    return (
        "docs/user/app.md inspector paragraph must say the open inspector "
        "lists years with counts under last activity, a year with no messages "
        "is absent, and a click jumps like the day control"
    )


def _gen_names(before: str) -> set[str]:
    names: set[str] = set()
    for m in _GEN_INC.finditer(before):
        names.add(next(g for g in m.groups() if g))
    return names


def _clears_before_await(before: str) -> bool:
    return bool(
        re.search(r"=\s*\[\s*\]", before)
        or re.search(r"\.length\s*=\s*0\b", before)
        or re.search(r"\.splice\s*\(\s*0\b", before)
    )


def _date_tags(markup: str) -> list[str]:
    tags: list[str] = []
    i = 0
    while True:
        j = markup.find("<Input", i)
        if j < 0:
            break
        end = _end_of_tag(markup, j)
        if end < 0:
            break
        tags.append(markup[j:end])
        i = end
    return tags


def _is_date_input(tag: str) -> bool:
    return bool(re.search(r"""type\s*=\s*\{?\s*["']date["']\s*\}?""", tag))


def _is_month_input(tag: str) -> bool:
    return bool(re.search(r"""type\s*=\s*\{?\s*["']month["']\s*\}?""", tag))


def _handler_blobs(src: str, prop: str) -> list[str]:
    blobs: list[str] = []
    for expr in _attr_exprs(src, prop):
        blobs.append(expr)
        bare = re.fullmatch(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*", expr)
        names = [bare.group(1)] if bare else []
        names += re.findall(
            r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:\?\.)?\s*\(",
            expr,
        )
        for name in names:
            if name in _SKIP_CALL:
                continue
            body = _fn_body(src, name)
            if body:
                blobs.append(body)
    return blobs


def _passes_years_true(blob: str) -> bool:
    if re.search(r"\bloadActivityYears\s*\(\s*true\s*\)", blob):
        return True
    if re.search(r"\bincludeGroups\s*=\s*true\b", blob) and re.search(
        r"\bloadActivityYears\s*\(\s*includeGroups\s*\)",
        blob,
    ):
        return True
    return False


def _core_year_blob(root: Path) -> tuple[str, str, str]:
    """Return (defining source, signature, expanded body) for person_year_counts."""
    timeline = root / "crates" / "interlace-core" / "src" / "people" / "timeline.rs"
    people = root / "crates" / "interlace-core" / "src" / "people.rs"
    parts = [(p, _text(p)) for p in (timeline, people) if p.is_file()]
    for path, raw in parts:
        if not _rust_function_body(raw, "person_year_counts"):
            continue
        others = "\n".join(text for p, text in parts if p != path)
        combined = raw + "\n" + others
        sig = _rust_fn_signature(raw, "person_year_counts")
        body = _without_rust_comments(
            _rust_body_with_callees(combined, "person_year_counts", depth=2)
        )
        return combined, sig, body
    return "", "", ""


def _cmd_name_registered(main_src: str, name: str) -> bool:
    m = re.search(r"generate_handler!\s*\[(.*?)\]", main_src, re.S)
    if not m:
        return False
    return bool(re.search(rf"\b{re.escape(name)}\b", m.group(1)))


def assert_inspector_year_jump(crate: Path) -> None:
    """#378: inspector lists years under last activity; click jumps to that day."""
    root = repo_root()
    insp_path = _web_file(crate, "PeopleInspector.svelte")
    insp_raw = _text(insp_path)
    insp = _without_comments(insp_raw) if insp_raw else ""

    # 1) Primary red today — the year list is not in the inspector at all.
    if "data-activity-years" not in insp:
        fail(_PRIMARY)

    markup = _svelte_markup(insp_raw)
    region = _year_region(markup)
    shell_path = _web_file(crate, "PeopleShell.svelte")
    tl_path = _web_file(crate, "TimelinePane.svelte")
    app_path = crate / "web" / "App.svelte"
    jump_path = _web_file(crate, "jumpDay.ts")
    api_path = _web_file(crate, "api.ts")
    en_path = crate / "web" / "lib" / "locales" / "en.ts"
    tr_path = crate / "web" / "lib" / "locales" / "tr.ts"
    docs_path = root / "docs" / "user" / "app.md"
    cmd_path = crate / "src" / "people_cmd.rs"
    main_path = crate / "src" / "main.rs"
    i18n_path = crate / "web" / "lib" / "i18n.ts"

    shell_raw = _text(shell_path)
    shell = _without_comments(shell_raw)
    tl_raw = _text(tl_path)
    tl = _without_comments(tl_raw)
    app = _without_comments(_text(app_path))
    jump = _without_comments(_text(jump_path))
    api = _text(api_path)
    docs = _text(docs_path)
    cmd_raw = _text(cmd_path)
    main_src = _text(main_path)
    i18n = _text(i18n_path)
    sources = [insp, shell, tl]

    # 2) Slot — immediately after last activity, before mail recipients.
    if "data-mail-recipients" not in insp:
        fail(f"{_ISSUE}: keep data-mail-recipients (#374) as the mail block")
    if not region or "data-activity-years" not in region:
        fail(
            f"{_ISSUE}: data-activity-years must sit immediately after the "
            "last-activity paragraph and before data-mail-recipients"
        )
    mail_if = region.find("isMailRow")
    years_at = region.find("data-activity-years")
    if mail_if >= 0 and years_at >= 0 and mail_if < years_at:
        fail(
            f"{_ISSUE}: do not put the year list inside the mail-row if "
            "(it is under last activity for every open inspector)"
        )
    mail_blocks = [
        el for el in _elements(markup, "div") if "data-mail-recipients" in el[:400]
    ]
    part_blocks = [
        el
        for el in _elements(markup, "ul")
        if "data-group-participants" in el[:400]
    ]
    if any("data-activity-year" in el for el in mail_blocks):
        fail(f"{_ISSUE}: year rows are not inside data-mail-recipients (#374)")
    if any("data-activity-year" in el for el in part_blocks):
        fail(
            f"{_ISSUE}: year rows are not inside data-group-participants "
            "(#377 / #322)"
        )

    # 3) Each year is one native button: digits, tabular-nums count, focus ring.
    buttons = [
        el
        for el in _elements(region, "button")
        if "data-activity-year" in el
    ]
    if not buttons:
        fail(
            f"{_ISSUE}: each year is a native type=\"button\" with "
            "data-activity-year (not a Badge, not dead text)"
        )
    for button in buttons:
        open_end = _end_of_tag(button, 0)
        open_tag = button[:open_end] if open_end > 0 else button
        if not re.search(r"""type\s*=\s*["']button["']""", open_tag):
            fail(f'{_ISSUE}: year row is a native type="button"')
        if "<Button" in button:
            fail(f"{_ISSUE}: year row is a native button, not the Button primitive")
        if "focus-visible:ring-2" not in button or "focus-visible:ring-ring" not in button:
            fail(
                f"{_ISSUE}: year button needs focus-visible:ring-2 "
                "focus-visible:ring-ring"
            )
        if "tabular-nums" not in button or "text-muted-foreground" not in button:
            fail(
                f"{_ISSUE}: the count in the year button uses "
                "tabular-nums text-muted-foreground (plain digits, no grouping)"
            )
        if re.search(r"\bmessages\b|toLocaleString|Intl\.NumberFormat", button):
            fail(
                f"{_ISSUE}: the year count is plain integer digits, "
                "not a “messages” word and not grouped"
            )
        interps = _svelte_interpolations(button)
        if not any(re.search(r"(?:^|\.)year\b", expr) for expr in interps):
            fail(f"{_ISSUE}: the year button shows the year digits")
        if not any(re.search(r"(?:^|\.)count\b", expr) for expr in interps):
            fail(f"{_ISSUE}: the same year button shows the count")
        if re.search(r"\bdisabled\b", open_tag):
            fail(
                f"{_ISSUE}: the year button stays enabled "
                "(re-click is not a no-op, including the current year)"
            )
        if re.search(r"""t\(\s*["']activityYears["']\s*\)""", button):
            fail(f"{_ISSUE}: the section label is not the year button")
    if re.search(r"<Badge\b", region):
        fail(f"{_ISSUE}: year hit target is not a Badge")
    if re.search(r"lucide-svelte|<Calendar\b|<BarChart\b|<Chart\b", region):
        fail(f"{_ISSUE}: no Lucide icon on the year list")
    if re.search(r"heatmap|recharts|bar-width|sparkline|<svg\b", region, re.I):
        fail(f"{_ISSUE}: no heatmap, chart, or bar-width on the year list")
    if re.search(r"\btransition:", region):
        fail(f"{_ISSUE}: no extra transition: on the year list")
    if re.search(r"animate-pulse|animate-bounce|\bbounce\b", region):
        fail(f"{_ISSUE}: year skeletons are static (no bounce, no animate-pulse)")
    if "aria-current" in region:
        fail(f"{_ISSUE}: no aria-current on a year (the day heading already marks place)")
    if re.search(r"overflow-(?:y-)?(?:auto|scroll)", region):
        fail(f"{_ISSUE}: the year list is not a nested scroller")
    if re.search(r"""key\s*===?\s*["'][jkJK]["']""", region):
        fail(f"{_ISSUE}: no j / k on the year list")
    label_at = re.search(r"""t\(\s*["']activityYears["']\s*\)""", region)
    if not label_at:
        fail(f'{_ISSUE}: section label is t("activityYears")')
    label_win = region[max(0, label_at.start() - 220) : label_at.end()]
    if "text-xs" not in label_win or "font-medium" not in label_win:
        fail(
            f'{_ISSUE}: t("activityYears") uses text-xs font-medium '
            "(same weight as the identities label)"
        )
    if "<EmptyState" in region:
        fail(
            f"{_ISSUE}: a successful empty year list omits data-activity-years "
            "(no EmptyState)"
        )

    # 4) Empty omits the section; in-flight and failure keep it.
    guards = _guard_conds(markup, insp)
    if not guards or any(not g for g in guards):
        fail(
            f"{_ISSUE}: successful empty omits data-activity-years "
            "(the section is conditional, not always mounted)"
        )
    joined = "\n".join(guards)
    if not re.search(r"\.length\b|length\s*[><=!]", joined):
        fail(
            f"{_ISSUE}: a successful empty list omits data-activity-years "
            "(no zero row, no EmptyState)"
        )
    if not re.search(r"busy|loading|pending|fetch|inflight", joined, re.I):
        fail(
            f"{_ISSUE}: in-flight keeps data-activity-years "
            '(aria-busy="true"), it does not unmount the section'
        )
    if not re.search(r"fail|error|\berr\b", joined, re.I):
        fail(
            f"{_ISSUE}: failure keeps data-activity-years and shows "
            't("activityYearsFailed")'
        )
    if "aria-busy" not in region or not re.search(
        r"""aria-busy\s*=\s*(?:"true"|\{[^}]*\})""",
        region,
    ):
        fail(
            f'{_ISSUE}: in-flight data-activity-years sets aria-busy="true"'
        )
    branches = _branch_bodies(region)
    skel = [
        body
        for _cond, body in branches
        if ("<Skeleton" in body or "data-skeleton" in body) and "{#if" not in body
    ]
    if not skel or not any(
        body.count("<Skeleton") >= 2 or body.count("data-skeleton") >= 2
        for body in skel
    ):
        fail(
            f"{_ISSUE}: in-flight year list shows two static Skeleton "
            "bars (data-skeleton) and no year buttons"
        )
    if any("data-activity-year" in body for body in skel):
        fail(
            f"{_ISSUE}: clear year buttons while the request is in flight "
            "(skeletons replace data-activity-year)"
        )
    if not re.search(r"""t\(\s*["']activityYearsFailed["']\s*\)""", region):
        fail(f'{_ISSUE}: failure shows t("activityYearsFailed") in the year section')
    if not re.search(r"""t\(\s*["']activityYearsRetry["']\s*\)""", region):
        fail(f'{_ISSUE}: failure shows a retry t("activityYearsRetry")')
    failed_at = region.find("activityYearsFailed")
    failed_win = region[max(0, failed_at - 900) : failed_at + 500] if failed_at >= 0 else ""
    if "data-activity-years" not in failed_win:
        fail(f"{_ISSUE}: failure keeps the data-activity-years section")
    retry_buttons = [
        el
        for el in _elements(region, "button")
        if "activityYearsRetry" in el
    ]
    retry_blob = _follow("\n".join(retry_buttons), sources, depth=2)
    if "loadActivityYears" not in retry_blob:
        fail(f"{_ISSUE}: the retry button calls loadActivityYears again")

    # 5) loadActivityYears(groups) from the checkbox and from onMount.
    if not _fn_body(insp, "loadActivityYears") and not _fn_body(
        shell, "loadActivityYears"
    ):
        fail(
            f"{_ISSUE}: loadActivityYears(groups) loads personYearCounts "
            "for the open inspector"
        )
    defined_in = insp if _fn_body(insp, "loadActivityYears") else shell
    params = _fn_params(defined_in, "loadActivityYears")
    param = params.split(":")[0].split(",")[0].strip()
    loader = _fn_body(defined_in, "loadActivityYears")
    if not param:
        fail(
            f"{_ISSUE}: loadActivityYears takes the include-groups flag "
            "(not a $effect read)"
        )
    if "personYearCounts" not in loader or param not in loader:
        fail(
            f"{_ISSUE}: loadActivityYears(groups) passes that boolean into "
            "personYearCounts (includeGroups)"
        )
    if "jumpGen" in loader:
        fail(
            f"{_ISSUE}: the year request has its own generation, not jumpGen"
        )
    await_at = loader.find("await")
    if await_at < 0:
        fail(f"{_ISSUE}: loadActivityYears awaits personYearCounts")
    before, after = loader[:await_at], loader[await_at:]
    if not _clears_before_await(before):
        fail(
            f"{_ISSUE}: clear the previous person's year buttons before the await"
        )
    gens = _gen_names(before)
    if not gens or not any(re.search(rf"\b{re.escape(n)}\b", after) for n in gens):
        fail(
            f"{_ISSUE}: drop a stale year reply with a generation counter "
            "(not jumpGen)"
        )
    if not re.search(r"!==|!=", after):
        fail(f"{_ISSUE}: a stale year reply must not paint")
    if re.search(r"\bshowErr\s*\(", loader) or re.search(r"\bshowToast\s*\(", loader):
        fail(
            f"{_ISSUE}: year failure is t(\"activityYearsFailed\") plus retry, "
            "not showErr and not showToast"
        )
    if _JAN1.search(loader):
        fail(f"{_ISSUE}: do not jump to ${{year}}-01-01; pass first_local_day")
    onchange_blobs = [
        b
        for b in _handler_blobs(insp, "onchange")
        if "onReloadPerson" in b or "writeIncludeGroupsPref" in b
    ]
    onchange = "\n".join(onchange_blobs)
    if "writeIncludeGroupsPref" not in onchange or "onReloadPerson" not in onchange:
        fail(
            f"{_ISSUE}: the include-groups checkbox still "
            "writeIncludeGroupsPref and onReloadPerson(includeGroups)"
        )
    reload_m = re.search(r"\bonReloadPerson\s*\(", onchange)
    years_m = re.search(r"\bloadActivityYears\s*\(", onchange)
    if not reload_m or not years_m:
        fail(
            f"{_ISSUE}: the include-groups onchange also calls "
            "loadActivityYears with the same boolean as onReloadPerson"
        )
    reload_arg = _call_arg(onchange, reload_m.end() - 1).strip()
    years_arg = _call_arg(onchange, years_m.end() - 1).strip()
    if not reload_arg or reload_arg.split(",")[0].strip() != years_arg.split(",")[0].strip():
        fail(
            f"{_ISSUE}: loadActivityYears gets the same boolean already passed "
            "to onReloadPerson"
        )
    mounts = [
        _call_arg(insp, m.end() - 1)
        for m in re.finditer(r"\bonMount\s*\(", insp)
    ]
    if not any(re.search(r"\bloadActivityYears\s*\(", m) for m in mounts):
        fail(
            f"{_ISSUE}: onMount fetches years once "
            "(the inspector unmounts when showPersonChrome is false)"
        )

    # 6) #309 — no $effect callback source mentions includeGroups.
    if _has_include_groups_effect(app, tl, shell, insp):
        fail(
            f"{_ISSUE}: do not put includeGroups inside a $effect / $effect.pre "
            "in App, TimelinePane, PeopleShell, or PeopleInspector (#309)"
        )

    # 7) Click passes first_local_day into jumpToDayKey. Not Jan 1. Not chrome-on.
    click_exprs: list[str] = []
    for button in buttons:
        for expr in _attr_exprs(button, "onclick") + _attr_exprs(button, "click"):
            click_exprs.append(expr)
    if not click_exprs:
        fail(f"{_ISSUE}: the year button passes first_local_day to jumpToDayKey")
    click = "\n".join(_follow(expr, sources, depth=3) for expr in click_exprs)
    if "first_local_day" not in click:
        fail(
            f"{_ISSUE}: the year click passes first_local_day "
            "(a day that has a message)"
        )
    if "jumpToDayKey" not in click:
        fail(
            f"{_ISSUE}: the year click calls jumpToDayKey "
            "(a shell callback into TimelinePane is fine)"
        )
    if _JAN1.search(click):
        fail(
            f"{_ISSUE}: do not pass ${{year}}-01-01 unless that string is "
            "the payload first_local_day"
        )
    if click.find("first_local_day") < 0 or not re.search(
        r"first_local_day[\s\S]*personDayMessage[\s\S]*openPersonAtMessage",
        click,
    ):
        fail(
            f"{_ISSUE}: a year click passes first_local_day, then personDayMessage, "
            "then openPersonAtMessage"
        )
    if re.search(r"showPersonChrome\s*=\s*true", click):
        fail(f"{_ISSUE}: a year click does not set showPersonChrome = true (#213)")
    if re.search(r"jumpDay\s*===|===?\s*jumpDay", "\n".join(click_exprs)):
        fail(f"{_ISSUE}: re-clicking a year always calls jumpToDayKey")

    # 8) Keep inspector chrome. Years are not fetched from selectPerson.
    if "data-group-participants" not in insp or not re.search(
        r"""type\s*=\s*["']button["']""",
        "\n".join(part_blocks),
    ):
        fail(
            f"{_ISSUE}: keep data-group-participants type=\"button\" "
            "(#377 / #322)"
        )
    if "scrollTo(0, 0)" not in insp and "scrollTo(0,0)" not in insp:
        fail(f"{_ISSUE}: keep scrollTo(0, 0) on the inspector aside")
    if "bind:this" not in insp:
        fail(f"{_ISSUE}: keep bind:this on the inspector aside")
    if "transition:fly" not in insp or "chromeMotionMs" not in insp:
        fail(f"{_ISSUE}: keep the aside fly / chromeMotionMs (#222)")
    if "w-72" not in insp:
        fail(f"{_ISSUE}: keep the inspector w-72")
    if not re.search(r"\{#if\s+showPersonChrome\s*\}", shell):
        fail(f"{_ISSUE}: PeopleShell keeps {{#if showPersonChrome}} around the inspector")
    if "PeopleInspector" not in shell:
        fail(f"{_ISSUE}: the year list stays on PeopleInspector")
    select_body = _fn_body(tl, "selectPerson")
    load_body = _fn_body(shell, "loadPerson")
    for label, body in (("selectPerson", select_body), ("loadPerson", load_body)):
        if re.search(r"\b(?:personYearCounts|loadActivityYears|person_year_counts)\b", body):
            fail(
                f"{_ISSUE}: do not fetch years from {label} "
                "(the append path must not call personYearCounts)"
            )

    # 9) jumpToDayKey + the existing date control. Quiet miss. No newer page.
    if not re.search(
        r"export\s+(?:async\s+)?function\s+jumpToDayKey\b"
        r"|export\s+(?:const|let)\s+jumpToDayKey\b",
        tl_raw,
    ):
        fail(
            f"{_ISSUE}: TimelinePane must export jumpToDayKey "
            "(assign jumpDay, call goToJumpDay)"
        )
    jump_key = _fn_body(tl, "jumpToDayKey")
    if not jump_key:
        fail(f"{_ISSUE}: jumpToDayKey assigns jumpDay and calls goToJumpDay")
    if not re.search(r"\bjumpDay\s*=", jump_key) or "goToJumpDay" not in jump_key:
        fail(f"{_ISSUE}: jumpToDayKey sets jumpDay and calls goToJumpDay")
    if re.search(r"jumpDay\s*===|===?\s*jumpDay", jump_key):
        fail(
            f"{_ISSUE}: re-clicking a year always calls goToJumpDay "
            "(jumpToDayKey must not return early when that day is already current)"
        )
    if ".trim()" not in jump_key or "selectedId" not in jump_key:
        fail(
            f"{_ISSUE}: jumpToDayKey trims the day and returns when it is "
            "empty or there is no selectedId"
        )
    if _JAN1.search(jump_key):
        fail(f"{_ISSUE}: jumpToDayKey does not invent YYYY-01-01")
    if re.search(r"showPersonChrome\s*=\s*true", jump_key):
        fail(f"{_ISSUE}: jumpToDayKey does not force the inspector")
    year_path = jump_key + "\n" + _fn_body(tl, "goToJumpDay")
    if not re.search(
        r"personDayMessage[\s\S]*openPersonAtMessage",
        year_path,
    ):
        fail(
            f"{_ISSUE}: jumpToDayKey reaches personDayMessage, then openPersonAtMessage"
        )
    tl_markup = _svelte_markup(tl_raw)
    if any(_is_month_input(tag) for tag in _date_tags(tl_markup)):
        fail(f"{_ISSUE}: do not add type=\"month\" or a year control on the date field")
    date_tags = [tag for tag in _date_tags(tl_markup) if _is_date_input(tag)]
    if len(date_tags) != 1:
        fail(
            f"{_ISSUE}: keep a single Input type=\"date\" next to find "
            "(do not add a second date input)"
        )
    date = date_tags[0]
    if "goToJumpDay" not in date or not re.search(
        r"""t\(\s*["']jumpToDay["']\s*\)""",
        date,
    ):
        fail(
            f"{_ISSUE}: the date Input stays onchange={{goToJumpDay}} "
            'and aria-label={t("jumpToDay")}'
        )
    find_at = tl_markup.find("tl-find")
    date_at = tl_markup.find(date)
    if find_at < 0 or date_at < find_at or date_at - find_at > 900:
        fail(f"{_ISSUE}: the day control stays next to find (no year UI on that row)")
    if "data-activity-year" in tl or "data-activity-years" in tl:
        fail(f"{_ISSUE}: year buttons stay in the inspector, not on the date control")
    go = _fn_body(tl, "goToJumpDay")
    local = _fn_body(jump, "jumpToLocalDay")
    for name, body in (("goToJumpDay", go), ("jumpToLocalDay", local)):
        if not body:
            fail(f"{_ISSUE}: keep {name} (#311 quiet day jump)")
        if re.search(r"\bshowToast\s*\(|\bshowErr\s*\(", body):
            fail(f"{_ISSUE}: {name} stays a quiet miss (no showToast, no showErr)")
        if name == "jumpToLocalDay" and "openPersonAtMessage" in body:
            fail(f"{_ISSUE}: {name} must not call openPersonAtMessage")
        if name == "goToJumpDay" and (
            "jumpToLocalDay" in body
            or "pinDayAtTop" in body
            or "shouldLoadOlderForJump" in body
            or not re.search(
                r"personDayMessage[\s\S]*openPersonAtMessage[\s\S]*pinJump",
                body,
            )
        ):
            fail(
                f"{_ISSUE}: goToJumpDay calls personDayMessage, then "
                "openPersonAtMessage, then pinJump — not the older-only walk"
            )
    if "shouldLoadOlderForJump" in go or "jumpToLocalDay" in go:
        fail(
            f"{_ISSUE}: the year window is the day lookup, not an older-only walk"
        )
    if re.search(r"selectPerson\s*\([^)]*\bfalse\b", local):
        fail(f"{_ISSUE}: the day jump must not load a page newer than the hit (#403)")

    # 10) Empty-state and media include-groups also reload years with true.
    group_handlers = _attr_exprs(tl_raw, "onIncludeGroups")
    if len(group_handlers) < 2:
        fail(
            f"{_ISSUE}: keep the timeline empty-state and media "
            "onIncludeGroups handlers"
        )
    for expr in group_handlers:
        blob = _follow(expr, sources, depth=3)
        if "writeIncludeGroupsPref" not in blob or "selectPerson" not in blob:
            fail(
                f"{_ISSUE}: include-groups force-on still writes the pref "
                "and calls selectPerson"
            )
        if not _passes_years_true(blob):
            fail(
                f"{_ISSUE}: empty-state and media onIncludeGroups also call "
                "loadActivityYears(true)"
            )

    # 11) Counts-only command. Host-local year. No bodies. No tz crate.
    _core_src, sig, year_body = _core_year_blob(root)
    sql_problem = _year_sql_problem(year_body)
    if sql_problem:
        fail(f"{_ISSUE}: {sql_problem}")
    if re.search(r"\bconversation_id\b|\battach_kind\b|\bplatform\b", sig):
        fail(
            f"{_ISSUE}: person_year_counts arguments are person_id and "
            "include_groups only"
        )
    if "include_groups" not in sig:
        fail(f"{_ISSUE}: person_year_counts takes include_groups")
    struct_src = _without_rust_comments(_core_src + "\n" + cmd_raw)
    struct_problem = _json_struct_problem(struct_src)
    if struct_problem:
        fail(f"{_ISSUE}: {struct_problem}")
    cmd_body = _rust_function_body(cmd_raw, "person_year_counts")
    if not cmd_body:
        fail(
            f"{_ISSUE}: add Tauri command person_year_counts in people_cmd.rs "
            "next to person_timeline"
        )
    if "include_groups" not in cmd_body or "person_year_counts" not in cmd_raw:
        fail(
            f"{_ISSUE}: the Tauri command passes id and include_groups into "
            "core person_year_counts"
        )
    if any(re.search(rf"\b{bad}\b", cmd_body) for bad in ("body_text", "body_html", "subject", "snippet")):
        fail(f"{_ISSUE}: the year command must not return message bodies")
    if not _cmd_name_registered(main_src, "person_year_counts"):
        fail(f"{_ISSUE}: register person_year_counts in main.rs generate_handler")
    ts_problem = _ts_payload_problem(api)
    if ts_problem:
        fail(f"{_ISSUE}: {ts_problem}")
    for rel in (
        root / "crates" / "interlace" / "src" / "main.rs",
        root / "crates" / "interlace-cli" / "src" / "main.rs",
        root / "crates" / "interlace-core" / "src" / "cli" / "person.rs",
    ):
        if "person_year_counts" in _text(rel):
            fail(f"{_ISSUE}: no CLI change for year counts")
    for rel in (
        root / "Cargo.toml",
        root / "crates" / "interlace-core" / "Cargo.toml",
        root / "crates" / "interlace-tauri" / "Cargo.toml",
    ):
        if re.search(r"chrono[-_]tz|tzdata|chrono_tz", _text(rel), re.I):
            fail(f"{_ISSUE}: no chrono-tz / tzdata dependency (#268)")

    # 12) Locales.
    en = _chrome_pack_entries(_text(en_path)) if en_path.is_file() else {}
    tr = _chrome_pack_entries(_text(tr_path)) if tr_path.is_file() else {}
    loc = _locale_problem(en, tr)
    if loc:
        fail(f"{_ISSUE}: {loc}")
    for key in _COPY:
        if not re.search(rf"""\bt\(\s*["']{key}["']\s*\)""", insp):
            fail(f'{_ISSUE}: inspector must t("{key}") (key-only)')
    if "export function t" in i18n and "ChromeKey" not in i18n:
        fail(f"{_ISSUE}: t() stays key-only (ChromeKey)")

    # 13) User docs. Handoff / roadmap stay with impl.
    doc = _docs_problem(docs)
    if doc:
        fail(f"{_ISSUE}: {doc}")
