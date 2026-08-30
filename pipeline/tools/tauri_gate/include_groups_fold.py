"""#309 fold — inspector tick/untick must reload with the new flag.

Sibling of include_groups.py (do not grow that file). Inspector onchange
still setItems interlace.includeGroups. Reload passes the new
includeGroups into selectPerson / loadPerson as an argument (not only
TimelinePane’s stale $bindable). That argument is what
personConversations / personTimeline receive on the inspector reload
path. No $effect on includeGroups (jump / #308 must not persist).

Must-IDs: groups-fold-reload-arg, groups-fold-forward,
groups-fold-select-param, groups-fold-api-arg, groups-fold-write,
groups-fold-no-effect, groups-fold-empty-reload.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import fail
from tauri_gate.include_groups import _arrow_prop, _writes_groups_pref
from tauri_gate.reopen_last_lib import _fn_body
from tauri_gate.scan import (
    _call_arg,
    _svelte_markup,
    _without_comments,
)
from tauri_gate.status_toasts_toast import _svelte_effect_args

_RELOAD_CALLEES = ("onReloadPerson", "loadPerson", "selectPerson")
_GROUPS_NAME = re.compile(
    r"\b(includeGroups|include_groups|nextIncludeGroups|includeGroupsArg|"
    r"includeGroupsFlag|nextGroups|groupsFlag|groups)\b"
)
_API_CONV = re.compile(r"\b(?:api\s*\.\s*)?personConversations\s*\(")
_API_TL = re.compile(r"\b(?:api\s*\.\s*)?personTimeline\s*\(")
_FN_HEAD = (
    r"(?:export\s+)?(?:async\s+)?function\s+{name}\s*\("
    r"|(?:const|let|var)\s+{name}\s*=\s*(?:async\s*)?(?:function\s*)?\("
)


def _call_args_named(src: str, name: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(rf"\b{re.escape(name)}\s*\(", src):
        out.append(_call_arg(src, m.end() - 1))
    return out


def _arrow_params(src: str, name: str) -> str:
    m = re.search(
        rf"{re.escape(name)}\s*(?::|=)\s*\{{?\s*(?:async\s*)?\(([^)]*)\)\s*=>",
        src,
    )
    return (m.group(1) if m else "").strip()


def _fn_params(src: str, name: str) -> str:
    rx = re.compile(_FN_HEAD.format(name=re.escape(name)))
    m = rx.search(src)
    if not m:
        return ""
    return _call_arg(src, m.end() - 1)


def _groups_name(blob: str) -> str:
    m = _GROUPS_NAME.search(blob)
    return m.group(1) if m else ""


def _markup_prop(src: str, name: str) -> str:
    mark = _svelte_markup(src)
    return _arrow_prop(mark, name) if mark.strip() else ""


def _reload_passes_groups(blob: str) -> bool:
    for name in _RELOAD_CALLEES:
        for args in _call_args_named(blob, name):
            if _GROUPS_NAME.search(args):
                return True
    return False


def _assigns_bindable_from(body: str, param: str) -> bool:
    """True when includeGroups = param happens before the first API load."""
    assign = re.search(
        rf"\bincludeGroups\s*=\s*{re.escape(param)}\b",
        body,
    )
    if not assign:
        return False
    first_api = None
    for rx in (_API_CONV, _API_TL):
        m = rx.search(body)
        if m and (first_api is None or m.start() < first_api):
            first_api = m.start()
    if first_api is None:
        return False
    return assign.start() < first_api


def _api_uses_param(arg: str, param: str) -> bool:
    if param == "includeGroups" and re.search(r"\bincludeGroups\b", arg):
        return True
    if re.search(rf"\bincludeGroups\s*:\s*{re.escape(param)}\b", arg):
        return True
    return bool(param != "includeGroups" and re.search(rf"\b{re.escape(param)}\b", arg))


def _select_apis_use_param(body: str, param: str) -> bool:
    if _assigns_bindable_from(body, param):
        return bool(_API_CONV.search(body) and _API_TL.search(body))
    conv = [_call_arg(body, m.end() - 1) for m in _API_CONV.finditer(body)]
    tls = [_call_arg(body, m.end() - 1) for m in _API_TL.finditer(body)]
    if not conv or not tls:
        return False
    return all(_api_uses_param(a, param) for a in conv) and all(
        _api_uses_param(a, param) for a in tls
    )


def _has_include_groups_effect(*blobs: str) -> bool:
    for blob in blobs:
        for arg in _svelte_effect_args(blob):
            if re.search(r"\bincludeGroups\b", arg):
                return True
    return False


def assert_remember_include_groups_fold(crate: Path) -> None:
    """#309 fold: inspector tick reloads with the new includeGroups argument."""
    insp_path = crate / "web" / "lib" / "PeopleInspector.svelte"
    shell_path = crate / "web" / "lib" / "PeopleShell.svelte"
    tl_path = crate / "web" / "lib" / "TimelinePane.svelte"
    app_path = crate / "web" / "App.svelte"
    if not insp_path.is_file():
        fail("#309: PeopleInspector.svelte required (inspector include-groups fold)")
    if not shell_path.is_file():
        fail("#309: PeopleShell.svelte required (inspector include-groups fold)")
    if not tl_path.is_file():
        fail("#309: TimelinePane.svelte required (inspector include-groups fold)")
    insp = _without_comments(insp_path.read_text())
    shell = _without_comments(shell_path.read_text())
    tl = _without_comments(tl_path.read_text())
    app = _without_comments(app_path.read_text()) if app_path.is_file() else ""

    onchange = _markup_prop(insp, "onchange") or _arrow_prop(insp, "onchange")
    reload_h = _markup_prop(shell, "onReloadPerson")
    empty = _markup_prop(tl, "onIncludeGroups") or _arrow_prop(tl, "onIncludeGroups")
    load_params = _fn_params(shell, "loadPerson")
    load_body = _fn_body(shell, "loadPerson")
    select_params = _fn_params(tl, "selectPerson")
    select_body = _fn_body(tl, "selectPerson")

    # 1) groups-fold-reload-arg — inspector onchange passes the new flag.
    if not onchange.strip():
        fail(
            "#309: inspector include-groups onchange must reload the person "
            "with the new includeGroups (tick/untick in the same click)"
        )
    if not _reload_passes_groups(onchange):
        fail(
            "#309: inspector include-groups tick/untick must pass the new "
            "includeGroups into onReloadPerson / loadPerson / selectPerson "
            "(argument — TimelinePane’s $bindable is stale on this click)"
        )

    # 2) groups-fold-forward — shell handler receives that flag and forwards it.
    handler_param = _groups_name(_arrow_params(_svelte_markup(shell), "onReloadPerson"))
    if not handler_param:
        fail(
            "#309: PeopleShell onReloadPerson must take the inspector’s new "
            "includeGroups and pass it into loadPerson / selectPerson "
            "(do not reload from the pane’s stale bindable)"
        )
    forwarded = False
    for name in ("loadPerson", "selectPerson"):
        for args in _call_args_named(reload_h, name):
            if re.search(rf"\b{re.escape(handler_param)}\b", args):
                forwarded = True
    if not forwarded:
        fail(
            "#309: PeopleShell onReloadPerson must forward the inspector’s new "
            "includeGroups into loadPerson / selectPerson (argument)"
        )

    # 3) groups-fold-select-param — loadPerson hop + selectPerson take the arg.
    if _call_args_named(reload_h, "loadPerson"):
        load_param = _groups_name(load_params)
        if not load_param:
            fail(
                "#309: loadPerson must take the caller’s includeGroups "
                "(argument, not only TimelinePane’s $bindable)"
            )
        if not any(
            re.search(rf"\b{re.escape(load_param)}\b", args)
            for args in _call_args_named(load_body, "selectPerson")
        ):
            fail(
                "#309: loadPerson must pass the caller’s includeGroups into "
                "selectPerson (inspector reload path)"
            )
    select_param = _groups_name(select_params)
    if not select_param:
        fail(
            "#309: selectPerson must take the caller’s includeGroups "
            "(argument, not only TimelinePane’s $bindable)"
        )

    # 4) groups-fold-api-arg — that argument is what the APIs receive.
    if not select_body.strip():
        fail("#309: TimelinePane selectPerson required (inspector reload path)")
    if not _select_apis_use_param(select_body, select_param):
        fail(
            "#309: selectPerson must pass the caller’s includeGroups argument "
            "into api.personConversations / api.personTimeline "
            "(inspector reload path; do not read the pane’s stale bindable)"
        )

    # 5) groups-fold-write — inspector onchange still setItems the pref.
    if not _writes_groups_pref(onchange):
        fail(
            "#309: inspector include-groups onchange must still setItem "
            "interlace.includeGroups"
        )

    # 6) groups-fold-no-effect — jump / #308 must not persist via $effect.
    if _has_include_groups_effect(app, tl, shell, insp):
        fail(
            "#309: do not put a $effect on includeGroups "
            "(jumpToMessage auto-enable and #308 setSetup must not persist; "
            "reload from the inspector tick argument, not an effect)"
        )

    # 7) groups-fold-empty-reload — empty-state still writes and reloads.
    if not _writes_groups_pref(empty):
        fail(
            "#309: empty-state Include groups must still setItem "
            "interlace.includeGroups"
        )
    if not re.search(r"\b(?:selectPerson|loadPerson)\s*\(", empty):
        fail(
            "#309: empty-state Include groups must still reload the person "
            "(write and selectPerson / loadPerson)"
        )
