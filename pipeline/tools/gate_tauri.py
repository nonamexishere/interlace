#!/usr/bin/env python3
"""UI0 + chrome gate for interlace-tauri.

Entry stays `python3 pipeline/tools/gate_tauri.py`. Chrome asserts live in
`pipeline/tools/tauri_gate/` (area modules + scan.py readers). G1–G3 / G5
lock is `assert_gate_tauri_split`. G4 is the rest of this script (npm ci /
build, clippy, deny). Do not add `python3 -m tauri_gate`.

Protected homes: review.py (#128 / #221), contrast.py (#219),
import_doctor.py (#220), motion.py (#222). Move those bodies; do not
rewrite their fail prefixes.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root, run  # noqa: E402
from gate_app_release import assert_app_notarize  # noqa: E402

from tauri_gate.scan import (  # noqa: E402
    CSP,
    _chrome_en_text,
)
from tauri_gate.timeline_rows import (  # noqa: E402
    assert_chat_bubbles,
    assert_day_separators,
    assert_local_tz_display,
    assert_gmail_timeline_rows,
)
from tauri_gate.timeline_scroll import (  # noqa: E402
    assert_timeline_latest,
    assert_virtualized_timeline,
    assert_variable_height_timeline,
)
from tauri_gate.timeline_filters import (  # noqa: E402
    assert_timeline_platform_chips,
    assert_timeline_kind_filter,
)
from tauri_gate.timeline_hierarchy import (  # noqa: E402
    assert_timeline_grouped_runs,
    assert_timeline_bubble_hierarchy,
    assert_timeline_attach_slot,
)
from tauri_gate.people_switcher import assert_conversation_switcher  # noqa: E402
from tauri_gate.people_list import (  # noqa: E402
    assert_people_filter_identity,
    assert_people_list_lock,
    assert_people_sidebar_no_x_scroll,
    assert_human_time_people,
)
from tauri_gate.people_collapse import assert_people_sidebar_collapse  # noqa: E402
from tauri_gate.people_inspector import assert_person_inspector  # noqa: E402
from tauri_gate.media_lightbox import (  # noqa: E402
    assert_photo_lightbox,
    assert_voice_note_player,
    assert_voice_note_seek,
)
from tauri_gate.media_cas import assert_cas_video_pdf  # noqa: E402
from tauri_gate.media_linkify import assert_bubble_linkify  # noqa: E402
from tauri_gate.media_bubble import (  # noqa: E402
    assert_bubble_search,
    assert_copy_reveal_cas,
)
from tauri_gate.search_filters import (  # noqa: E402
    assert_search_platform_select,
    assert_search_conversation_kind,
    assert_search_attachment_filter,
)
from tauri_gate.search_field import (  # noqa: E402
    assert_chrome_search_field,
    assert_search_as_you_type,
)
from tauri_gate.search_hits import (  # noqa: E402
    assert_search_jump_to_message,
    assert_search_safe_highlight,
    assert_search_hit_density,
)
from tauri_gate.search_picker import (  # noqa: E402
    assert_search_person_picker,
    assert_search_filters_secondary,
)
from tauri_gate.import_boot import (  # noqa: E402
    assert_boot_spinner,
    assert_first_run,
)
from tauri_gate.import_reveal import (  # noqa: E402
    assert_reveal_archive,
    assert_defer_doctor_cas,
)
from tauri_gate.import_doctor import (  # noqa: E402
    assert_drag_drop_import,
    assert_import_progress,
    assert_import_cancel,
)
from tauri_gate.review import (  # noqa: E402
    assert_review_identifiers,
    assert_review_chrome,
    assert_sidebar_undo_chrome,
)
from tauri_gate.titlebar import (  # noqa: E402
    assert_window_title,
    assert_custom_titlebar,
)
from tauri_gate.locale import (  # noqa: E402
    assert_macos_menu,
    assert_chrome_locale,
    assert_chrome_locale_panes,
)
from tauri_gate.keyboard import (  # noqa: E402
    assert_keyboard_map,
    assert_keyboard_list_arrows,
)
from tauri_gate.palette import (  # noqa: E402
    assert_command_palette,
    assert_command_palette_people_cap,
    assert_command_palette_field_keys,
    assert_command_palette_clipboard,
)
from tauri_gate.density import (  # noqa: E402
    assert_font_density,
    assert_light_chrome,
)
from tauri_gate.a11y import (  # noqa: E402
    assert_a11y_listbox_focus_motion,
    assert_focus_aria_audit,
)
from tauri_gate.design import (  # noqa: E402
    assert_design_tokens,
    assert_typography,
    assert_lucide_icons,
)
from tauri_gate.primitives import (  # noqa: E402
    assert_owned_primitives,
    assert_empty_next_action,
    assert_loading_skeletons,
    assert_timeline_append_skeleton_guard,
)
from tauri_gate.contrast import (  # noqa: E402
    assert_contrast_tokens,
    assert_appearance_os,
    assert_status_tokens,
)
from tauri_gate.motion import assert_motion  # noqa: E402
from tauri_gate.status_toasts import (  # noqa: E402
    assert_inflight_audible_status,
    assert_recoverable_toasts,
)
from tauri_gate.status import (  # noqa: E402
    assert_partial_pane_errors,
    assert_partial_retry_generation,
)

_SPLIT_ENTRY_CMD = "python3 pipeline/tools/gate_tauri.py"
_SPLIT_MAX_LINES = 1_200
_SPLIT_AREA_MIN = 8
_SPLIT_SELF = "assert_gate_tauri_split"
_SPLIT_PKG = "tauri_gate"
_SPLIT_PROTECTED_HOMES = ("review.py", "contrast.py", "import_doctor.py", "motion.py")
# scan.py public surface. Parse walkers may stay private. One-assert keep-checks leave.
_SPLIT_SCAN_READERS = (
    "_web_sources",
    "_web_logic",
    "_timeline_block",
    "_css_var",
    "_chrome_en_text",
)
_SPLIT_SCAN_KEEP_OUT = (
    "_PRETTY_WHATSAPP",
    "_CHROME_SEARCH_HOOK",
    "_A11Y_ROLE_LISTBOX",
    "_STATUS_CELEBRATION",
)
_SPLIT_EXISTING_TOOL_ASSERTS = {
    "assert_blind.py",
    "assert_matrix_not_ignored.py",
    "assert_no_crate.py",
    "assert_no_test_edits.py",
    "assert_no_todo.py",
}

# main() assert_* calls on master today (including assert_app_notarize).
_SPLIT_MAIN_ASSERTS = (
    "assert_app_notarize",
    "assert_chat_bubbles",
    "assert_day_separators",
    "assert_local_tz_display",
    "assert_timeline_latest",
    "assert_conversation_switcher",
    "assert_timeline_platform_chips",
    "assert_timeline_kind_filter",
    "assert_gmail_timeline_rows",
    "assert_people_sidebar_no_x_scroll",
    "assert_people_filter_identity",
    "assert_people_list_lock",
    "assert_boot_spinner",
    "assert_photo_lightbox",
    "assert_voice_note_player",
    "assert_voice_note_seek",
    "assert_cas_video_pdf",
    "assert_bubble_linkify",
    "assert_bubble_search",
    "assert_reveal_archive",
    "assert_first_run",
    "assert_font_density",
    "assert_light_chrome",
    "assert_chrome_locale_panes",
    "assert_virtualized_timeline",
    "assert_variable_height_timeline",
    "assert_search_platform_select",
    "assert_search_conversation_kind",
    "assert_search_person_picker",
    "assert_search_jump_to_message",
    "assert_search_attachment_filter",
    "assert_search_safe_highlight",
    "assert_search_filters_secondary",
    "assert_search_hit_density",
    "assert_review_identifiers",
    "assert_window_title",
    "assert_macos_menu",
    "assert_chrome_locale",
    "assert_keyboard_map",
    "assert_chrome_search_field",
    "assert_search_as_you_type",
    "assert_custom_titlebar",
    "assert_people_sidebar_collapse",
    "assert_person_inspector",
    "assert_keyboard_list_arrows",
    "assert_command_palette",
    "assert_command_palette_people_cap",
    "assert_command_palette_field_keys",
    "assert_command_palette_clipboard",
    "assert_focus_aria_audit",
    "assert_contrast_tokens",
    "assert_appearance_os",
    "assert_status_tokens",
    "assert_import_progress",
    "assert_import_cancel",
    "assert_review_chrome",
    "assert_sidebar_undo_chrome",
    "assert_motion",
    "assert_a11y_listbox_focus_motion",
    "assert_human_time_people",
    "assert_drag_drop_import",
    "assert_copy_reveal_cas",
    "assert_defer_doctor_cas",
    "assert_design_tokens",
    "assert_typography",
    "assert_lucide_icons",
    "assert_owned_primitives",
    "assert_empty_next_action",
    "assert_loading_skeletons",
    "assert_timeline_append_skeleton_guard",
    "assert_inflight_audible_status",
    "assert_recoverable_toasts",
    "assert_partial_pane_errors",
    "assert_partial_retry_generation",
    "assert_timeline_grouped_runs",
    "assert_timeline_bubble_hierarchy",
    "assert_timeline_attach_slot",
)

_SPLIT_BOOTSTRAP_NEEDLES = (
    "publish = false",
    "tauri-plugin-http",
    "tauri-plugin-updater",
    "CSP",
    "Interlace.entitlements",
    "signingIdentity",
    "network.server",
    "network.client",
    "allow-jit",
    "assert_app_notarize",
    '["npm", "ci"]',
    '["npm", "run", "build"]',
    '"clippy"',
    '"deny"',
    '"reqwest"',
    '"hyper"',
)

# #219 keep-check that #278 folded (pane or en pack).
_SPLIT_219_FOLD_TOKENS = (
    "Loading review queue",
    "identifierLabel",
    "reviewList",
    "reviewAccept",
    "reviewReject",
)

_SPLIT_PROTECTED_PREFIXES: dict[str, tuple[str, ...]] = {
    "assert_review_identifiers": (
        "#128: ReviewPane.svelte required (review card identifier chrome lives there)",
        "#128: web/lib/api.ts required (ReviewPanel type surface)",
        "#128: api.ts must declare export type ReviewPanel = { … }",
        "#128: unclosed ReviewPanel type in api.ts",
        "#128: ReviewPanel must include identifiers[] (kind + value_normalized per entry — not only display_name / platforms)",
        "#128: ReviewPane must render panel.identifiers (kind + value_normalized under the title — not only display_name / platforms)",
        "#128: ReviewPane must show identifier kind and value_normalized as text (bindings on the panel loop, or a small formatter used there) — not only panelTitle(display_name + platforms)",
        "#128: do not use raw person_id as the primary identifier label",
        "#128: ReviewPane samples must stay text nodes — no {@html on sample body}",
        "#128: ReviewPane must still render sample body_text as text",
        "#128: sample bodies must remain text bindings of body_text (not HTML inject)",
        "#128: keep the evidence list on the review card",
        "#128: keep the score on the review card",
        "#128: keep Accept on the review card",
        "#128: keep Reject on the review card",
        "#128: keep display_name / panel title chrome; identifiers sit under it",
        "#128: keep platforms on the panel surface (identifiers are additive)",
        "#128: do not invent name_score raise/lower UI (threshold policy is #103; this issue only surfaces identifiers)",
        "#128: ReviewPanel.identifiers entries must expose kind + value_normalized (inline or named type; platform optional)",
    ),
    "assert_status_tokens": (
        "#219: crates/interlace-tauri/web/**/*.svelte required (status tokens)",
        "#219: web/app.css required (warning / success status tokens)",
        "#219: App.svelte required (cloud banner + Doctor found box)",
        "#219: DoctorPane.svelte required (issues card uses warning token)",
        "#219: data-cloud-warning required (warning token, not muted-only)",
        "#219: data-cloud-warning must not use amber-* / yellow-* / emerald-* / green-* (warning token only)",
        "#219: data-cloud-warning must use a warning token class / var(--warning) / var(--color-warning) (not muted-only, not amber-*)",
        "#219: App.svelte “Doctor found” box required (warning token, not text-destructive)",
        "#219: App.svelte “Doctor found” box must use a warning token (not text-destructive as the status color)",
        "#219: DoctorPane.svelte issues card required (warning token, not text-destructive)",
        "#219: DoctorPane.svelte issues card must use a warning token (not text-destructive as the status color)",
        "#219: data-import-done required (muted token classes or success tokens; no bg-gradient / confetti / celebration)",
        "#219: data-import-done must use muted token classes or success tokens (no bg-gradient / confetti / celebration)",
        "#219: data-import-done must not use bg-gradient / confetti / celebration",
        "#219: no amber-* / yellow-* / emerald-* / green-* on cloud / doctor / import-done surfaces. Found:\n  ",
        "#219: no confetti / Audio( / celebration copy. Found:\n  ",
        "#219: docs/user/app.md required — warning token + quiet import done",
        "#219: docs/user/app.md must say cloud / doctor warnings use the warning token",
        "#219: docs/user/app.md must say import done is quiet (muted or success)",
        "#219: not in scope — no review-queue chrome rewrite (#221)",
        '#219: keep id="q" as the canonical query field (#208)',
        "#219: keep data-people-sidebar (#159 / #212)",
        "#219: keep the overlay titlebar (#211)",
        "#219: keep data-person-inspector (#213)",
        "#219: do not soften tauri CSP",
        "#219: keep #217 light --color-muted-foreground HSL L ≤ 40 (@theme / non-dark :root)",
        "#219: keep #217 dark --color-muted-foreground HSL L ≥ 62 (inside prefers-color-scheme: dark)",
        "#219: keep #217 --search-mark / --color-search-mark on both sides",
        "#219: keep #217 .search-mark on var(--search-mark)",
        "#219: keep #218 --overlay / --scrim / --lightbox-scrim",
        "#219: keep #218 — no Theme / Appearance menu / data-theme",
    ),
    "assert_import_progress": (
        "#220: data-import-cancel required in ImportPane.svelte (Cancel while running)",
        "#220: no thread:: kill / JoinHandle:: abort as cancel (do not kill the import thread)",
        "#220: Status running must still be rendered in the import pane",
        "#220: keep data-import-done (quiet counts; no Dialog / bg-gradient / confetti)",
        "#220: data-import-done must not be wrapped in a Dialog",
        "#220: data-import-done must not use bg-gradient / confetti / celebration",
        "#220: do not console.log the import path",
        "#220: do not toast the import path",
        "#220: no parallel-import UI",
        "#220: no fetch( / HTTP import",
        "#220: no background GC button on Import",
        "#220: docs/user/app.md required — progress visible + quiet done",
        "#220: docs/user/app.md must say import progress is visible",
        "#220: docs/user/app.md must say import done stays quiet",
        '#220: keep id="q" as the canonical query field (#208)',
        "#220: keep data-people-sidebar (#159 / #212)",
        "#220: keep the overlay titlebar (#211)",
        "#220: keep data-person-inspector (#213)",
        "#220: do not soften tauri CSP",
        "#220: keep #219 --warning / --color-warning in light and dark",
        "#220: keep #219 data-import-done",
        "#220: keep #218 --overlay / --scrim / --lightbox-scrim",
        "#220: keep #218 — no Theme / Appearance menu / data-theme",
    ),
    "assert_review_chrome": (
        "#221: ReviewPane.svelte required (review queue chrome lives there)",
        "#221: ReviewPane.svelte must import Card from $lib/components/ui/card and Separator from $lib/components/ui/separator",
        "#221: data-review-card required on the open review card",
        "#221: keep Accept on the review card (explicit >Accept<)",
        "#221: keep Reject on the review card (explicit >Reject<)",
        "#221: queue/detail markup must not show #{r.id} / person ${ / person ${r.right_person_id / Accept review ${id} (found ",
        "#221: keep identifierLabel or value_normalized on the review card",
        "#221: ReviewPane samples must stay text nodes — no {@html",
        "#221: sample bodies must remain text bindings of body_text",
        "#221: ReviewPane must call linkEvents (undo lives on the pane)",
        "#221: ReviewPane must call undo (api.undo after Accept)",
        "#221: data-review-undo required on the Review pane Undo control",
        "#221: do not undo events[0] blindly — skip split_person / already-undone / system import links",
        "#221: Review undo must skip split_person and already-undone events (undo_of)",
        "#221: ConfirmDialog.svelte required (go() must close before await onconfirm())",
        "#221: ConfirmDialog.svelte go() required (set open = false before await onconfirm())",
        "#221: ReviewPane must not await onChanged() after undo (People refresh must not block the confirm callback)",
        "#221: ConfirmDialog must refuse open = true while busy (or leave Cancel enabled so a resurrected overlay is dismissable)",
        "#221: ConfirmDialog go() must catch onconfirm and have an onerror / onError prop",
        "#221: App.svelte ConfirmDialog required",
        "#221: App.svelte ConfirmDialog must pass onerror / onError / showErr",
        "#221: Review Undo disabled must mention resolving (not only undoing)",
        "#221: ReviewPane requestUndo() required",
        "#221: requestUndo() must return early when resolving",
        "#221: do not invent name_score raise/lower UI (threshold policy is not this issue)",
        "#221: sample loop must stay {#each panel.samples (do not add a second body dump)",
        "#221: do not add a second body dump — keep the existing panel.samples loop",
        "#221: docs/user/app.md required — Review + undo / reversible / no raw person id (or identifiers + undo)",
        "#221: docs/user/app.md must say Review + undo / reversible / no raw person id (or identifiers + undo)",
        '#221: keep id="q" as the canonical query field (#208)',
        "#221: keep data-people-sidebar (#159 / #212)",
        "#221: keep the overlay titlebar (#211)",
        "#221: keep data-person-inspector (#213)",
        "#221: do not soften tauri CSP",
        "#221: keep #219 --warning / --color-warning in light and dark",
        "#221: keep #220 data-import-cancel",
        "#221: keep #218 --overlay / --scrim / --lightbox-scrim",
        "#221: keep #218 — no Theme / Appearance menu / data-theme",
        "#221: ConfirmDialog go() must set open = false before await onconfirm() (or not await onconfirm)",
        "#221: Accept/Reject callbacks must try/catch and call onError (same as runUndo)",
    ),
    "assert_motion": (
        "#222: crates/interlace-tauri/web/**/*.svelte required (motion)",
        "#222: palette must import fade / fly / slide from svelte/transition (App.svelte and/or CommandPalette.svelte)",
        "#222: inspector must import fade / fly / slide from svelte/transition",
        "#222: data-command-palette (or commandOpen root) required for fade / fly / slide",
        "#222: data-command-palette (or commandOpen root) must use transition:fade / fly / slide with duration 150–250 (or 0 when reduced)",
        "#222: data-person-inspector required for fade / fly / slide",
        "#222: data-person-inspector must use transition:fade / fly / slide with duration 150–250 (or 0 when reduced)",
        "#222: toast.svelte required (keep transition:fade 150–250)",
        "#222: toast must still use transition:fade",
        "#222: toast transition:fade duration must be 150–250 (or 0 if reduced)",
        "#222: no spring / bounce / elastic / lottie / celebration / confetti in product Svelte. Found:\n  ",
        "#222: reduced-motion path must use matchMedia / MediaQuery / prefersReducedMotion in JS (CSS transition-duration: 0.01ms is not enough for Svelte transitions)",
        "#222: palette / inspector / toast Svelte transitions must use duration 0 (or skip) when reduced motion",
        "#222: keep #133 @media (prefers-reduced-motion: reduce) in CSS (or Tailwind motion-reduce)",
        "#222: keep #133 reduced-motion animation: none (boot spinner must not spin)",
        "#222: keep #133 prefers-reduced-motion CSS (transition: none / transition-duration: 0)",
        "#222: keep boot spinner reduced-motion (#133 / #156 — disable boot-spin under reduce)",
        "#222: docs/user/app.md required — fade/slide + reduced motion instant + no celebration / no auto-play",
        "#222: docs/user/app.md must say palette / inspector / toast use a short fade / slide",
        "#222: docs/user/app.md must say reduced motion makes them instant",
        "#222: docs/user/app.md must say no celebration",
        "#222: docs/user/app.md must say no auto-playing media",
        '#222: keep id="q" as the canonical query field (#208)',
        "#222: keep data-people-sidebar (#159 / #212)",
        "#222: keep the overlay titlebar (#211)",
        "#222: keep data-person-inspector (#213)",
        "#222: do not soften tauri CSP",
        "#222: keep #219 --warning / --color-warning in light and dark",
        "#222: keep #220 data-import-cancel",
        "#222: keep #221 data-review-card",
        "#222: keep #221 data-review-undo",
    ),
}


def _split_line_count(path: Path) -> int:
    return sum(1 for _ in path.open(encoding="utf-8"))


def _split_yaml_job(wf: str, name: str) -> str:
    m = re.search(rf"(?m)^  {re.escape(name)}:\n", wf)
    if not m:
        return ""
    rest = wf[m.end() :]
    nxt = re.search(r"(?m)^  [A-Za-z0-9_-]+:\n", rest)
    return wf[m.start() : m.end() + (nxt.start() if nxt else len(rest))]


def _split_job_run_lines(job: str) -> list[str]:
    lines: list[str] = []
    for m in re.finditer(r"(?m)^[ \t]+run:[ \t]*(.*)$", job):
        val = m.group(1).strip()
        if val in {"|", ">"}:
            continue
        if val:
            lines.append(val)
    return lines


def _split_const_str(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _split_fold_str(node: ast.AST) -> str | None:
    direct = _split_const_str(node)
    if direct is not None:
        return direct
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _split_fold_str(node.left)
        right = _split_fold_str(node.right)
        if left is not None and right is not None:
            return left + right
        return left if left is not None else right
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            chunk = _split_const_str(value)
            if chunk is None:
                break
            parts.append(chunk)
        return "".join(parts) if parts else None
    return None


def _split_fail_prefixes(fn_src: str) -> list[str]:
    try:
        tree = ast.parse(fn_src)
    except SyntaxError:
        return []
    out: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Name) or func.id != "fail" or not node.args:
            continue
        folded = _split_fold_str(node.args[0])
        if folded and folded not in out:
            out.append(folded)
    return out


def _split_fn_sources(paths: list[Path]) -> dict[str, str]:
    found: dict[str, str] = {}
    for path in paths:
        src = path.read_text()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            seg = ast.get_source_segment(src, node)
            if not seg:
                continue
            if node.name in found:
                found[node.name] = found[node.name] + "\n" + seg
            else:
                found[node.name] = seg
    return found


def _split_main_calls(main_src: str) -> list[str]:
    try:
        tree = ast.parse(main_src)
    except SyntaxError:
        return []
    fn = next(
        (
            n
            for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "main"
        ),
        None,
    )
    if fn is None:
        return []
    names: list[str] = []
    for stmt in fn.body:
        if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Call):
            continue
        func = stmt.value.func
        if isinstance(func, ast.Name) and func.id.startswith("assert_"):
            names.append(func.id)
    return names


def _split_gate_paths() -> tuple[Path, Path, Path]:
    root = repo_root()
    tools = root / "pipeline" / "tools"
    return root, tools / "gate_tauri.py", tools / _SPLIT_PKG


def assert_gate_tauri_split(crate: Path) -> None:
    """#279 / #300: split assert_* into tauri_gate/; entry + CI command unchanged.

    G1 CI one-liner. G2 main() call order + bootstrap. G3 #128 / #219–#222
    fail prefixes (and the #219 keep-check #278 folded). G5 package + size
    (no file ≥ 1_200) + scan surface + docs. G4 is the existing full gate
    (do not re-run npm/clippy here).
    """
    root, entry, pkg = _split_gate_paths()
    if not entry.is_file():
        fail("#279: G5 — pipeline/tools/gate_tauri.py must stay the entry")
    entry_src = entry.read_text()
    try:
        entry_tree = ast.parse(entry_src)
    except SyntaxError as exc:
        fail(f"#279: G5 — pipeline/tools/gate_tauri.py must parse: {exc}")

    # G1 — CI tauri job is still exactly the one-liner.
    ci = root / ".github" / "workflows" / "ci.yml"
    if not ci.is_file():
        fail("#279: G1 — .github/workflows/ci.yml required")
    wf = ci.read_text()
    if "python3 -m tauri_gate" in wf:
        fail("#279: G1 — no python3 -m tauri_gate")
    job = _split_yaml_job(wf, "tauri")
    if not job:
        fail("#279: G1 — ci.yml tauri job required")
    gate_runs = [
        line
        for line in _split_job_run_lines(job)
        if "gate_tauri" in line or "tauri_gate" in line
    ]
    if gate_runs != [_SPLIT_ENTRY_CMD]:
        fail(
            "#279: G1 — ci.yml tauri job step must stay exactly "
            f"`{_SPLIT_ENTRY_CMD}`"
        )
    for m in re.finditer(r"(?m)^  ([A-Za-z0-9_-]+):\n", wf):
        other = m.group(1)
        if other == "tauri":
            continue
        block = _split_yaml_job(wf, other)
        if "gate_tauri.py" in block or "tauri_gate" in block:
            fail("#279: G1 — no new CI job for the tauri gate")

    # G2 — same main() assert_* calls (order) + bootstrap.
    main_node = next(
        (
            n
            for n in entry_tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "main"
        ),
        None,
    )
    if main_node is None:
        fail("#279: G2 — gate_tauri.py main() required")
    main_src = ast.get_source_segment(entry_src, main_node) or ""
    calls = [n for n in _split_main_calls(main_src) if n != _SPLIT_SELF]
    frozen = list(_SPLIT_MAIN_ASSERTS)
    idx = 0
    for name in calls:
        if idx < len(frozen) and name == frozen[idx]:
            idx += 1
    if idx != len(frozen):
        missing = [n for n in frozen if n not in calls]
        if missing:
            fail(
                "#279: G2 — main() must still call "
                + ", ".join(missing)
                + " (same order as master; a missing call is a softened gate)"
            )
        expected = frozen[idx]
        prev = frozen[idx - 1] if idx else "(start)"
        fail(
            f"#279: G2 — main() assert_* order drifted: expected {expected} "
            f"after {prev}"
        )
    for needle in _SPLIT_BOOTSTRAP_NEEDLES:
        if needle not in main_src:
            fail(f"#279: G2 — main() bootstrap must still include {needle!r}")

    scan_paths = [entry]
    if pkg.is_dir():
        scan_paths.extend(sorted(p for p in pkg.glob("*.py") if p.is_file()))
    fn_sources = _split_fn_sources(scan_paths)
    for name in frozen:
        if name == "assert_app_notarize":
            continue
        if name not in fn_sources:
            fail(
                f"#279: G2 — {name} must still exist "
                "(moved body, not dropped)"
            )

    # G3 — protected fail prefixes still live on the five functions.
    for name, prefixes in _SPLIT_PROTECTED_PREFIXES.items():
        body = fn_sources.get(name, "")
        if not body:
            fail(
                f"#279: G3 — {name} required "
                "(move #128 / #219–#222; do not drop)"
            )
        messages = _split_fail_prefixes(body)
        for prefix in prefixes:
            if not any(msg == prefix or msg.startswith(prefix) for msg in messages):
                fail(
                    f"#279: G3 — {name} must keep fail prefix {prefix!r} "
                    "(move, do not rewrite)"
                )
    status_src = fn_sources.get("assert_status_tokens", "")
    for token in _SPLIT_219_FOLD_TOKENS:
        if token not in status_src:
            fail(
                "#279: G3 — assert_status_tokens must keep #219/#278 token "
                f"{token!r}"
            )

    # G5 — package + size + entry + docs. G4 is the rest of this script.
    clash = entry.parent / "gate_tauri"
    if clash.is_dir():
        fail(
            "#279: G5 — do not name the package gate_tauri "
            "(clash with the entry script)"
        )
    entry_lines = _split_line_count(entry)
    g5_bits: list[str] = []
    if not pkg.is_dir():
        g5_bits.append(f"package pipeline/tools/{_SPLIT_PKG}/ is missing")
    if entry_lines >= _SPLIT_MAX_LINES:
        g5_bits.append(
            f"gate_tauri.py is still {entry_lines:,} lines "
            f"(≥ {_SPLIT_MAX_LINES:,})"
        )
    if g5_bits:
        fail("#279: G5 — " + "; ".join(g5_bits))

    if not (pkg / "__init__.py").is_file():
        fail("#279: G5 — pipeline/tools/tauri_gate/__init__.py required")
    if not (pkg / "scan.py").is_file():
        fail(
            "#279: G5 — pipeline/tools/tauri_gate/scan.py required "
            "(shared readers + one _tag_name)"
        )
    missing_homes = [n for n in _SPLIT_PROTECTED_HOMES if not (pkg / n).is_file()]
    if missing_homes:
        fail(
            "#279: G5 — review.py / tokens.py / import_doctor.py required "
            "(homes for #128 / #219 / #220 / #221 / #222)"
        )
    area_py = [
        p
        for p in pkg.glob("*.py")
        if p.is_file() and p.name not in {"__init__.py", "scan.py"}
    ]
    if len(area_py) < _SPLIT_AREA_MIN:
        fail(
            "#279: G5 — ~8–10 area modules required under tauri_gate/ "
            "(not one file per assert_*)"
        )
    one_each = [p for p in area_py if p.name.startswith("assert_")]
    if len(one_each) >= 20:
        fail("#279: G5 — do not split one file per assert_* (approach B)")
    tools = entry.parent
    chrome_files = {
        f"{name}.py"
        for name in frozen
        if name != "assert_app_notarize"
    }
    flat = [
        p.name
        for p in tools.glob("assert_*.py")
        if p.is_file()
        and p.name in chrome_files
        and p.name not in _SPLIT_EXISTING_TOOL_ASSERTS
    ]
    if flat:
        fail(
            "#279: G5 — do not add flat pipeline/tools/assert_*.py "
            "siblings (approach C)"
        )
    for py in sorted(p for p in pkg.glob("*.py") if p.is_file()):
        n = _split_line_count(py)
        if n >= _SPLIT_MAX_LINES:
            fail(
                f"#279: G5 — {py.relative_to(root)} is {n:,} lines — "
                f"no tauri_gate module may be ≥ {_SPLIT_MAX_LINES:,}"
            )

    # #300 — scan.py public surface: five readers + one _tag_name + CSP.
    # Parse walkers may stay private. One-assert keep-checks must leave.
    scan_src = (pkg / "scan.py").read_text()
    try:
        scan_tree = ast.parse(scan_src)
    except SyntaxError as exc:
        fail(f"#300: G5 — pipeline/tools/tauri_gate/scan.py must parse: {exc}")
    scan_fns = [
        n.name for n in scan_tree.body if isinstance(n, ast.FunctionDef)
    ]
    for reader in _SPLIT_SCAN_READERS:
        if reader not in scan_fns:
            fail(
                f"#300: G5 — scan.py must define {reader} "
                "(shared reader; do not drop)"
            )
    tag_defs = scan_fns.count("_tag_name")
    if tag_defs != 1:
        fail(
            f"#300: G5 — scan.py must define exactly one _tag_name "
            f"(found {tag_defs})"
        )
    scan_binds: set[str] = set()
    for node in scan_tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    scan_binds.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(
            node.target, ast.Name
        ):
            scan_binds.add(node.target.id)
    if "CSP" not in scan_binds:
        fail(
            "#300: G5 — scan.py must keep CSP next to the readers (do not copy)"
        )
    leftover = [n for n in _SPLIT_SCAN_KEEP_OUT if n in scan_binds]
    if leftover:
        fail(
            "#300: G5 — scan.py must not define one-assert keep-check "
            + ", ".join(leftover)
            + " (move next to the owning assert; do not copy)"
        )

    doc = ast.get_docstring(entry_tree) or ""
    if "def main(" not in entry_src or not doc:
        fail(
            "#279: G5 — gate_tauri.py must stay the entry "
            "(module docstring + def main)"
        )

    pipe_docs = root / "docs" / "hacking" / "pipeline.md"
    tauri_docs = root / "docs" / "hacking" / "tauri.md"
    for label, path in (("pipeline.md", pipe_docs), ("tauri.md", tauri_docs)):
        text = path.read_text() if path.is_file() else ""
        if _SPLIT_ENTRY_CMD not in text:
            fail(
                f"#279: G5 — docs/hacking/{label} must keep "
                f"`{_SPLIT_ENTRY_CMD}`"
            )
    named = ""
    if pipe_docs.is_file():
        named += pipe_docs.read_text()
    if tauri_docs.is_file():
        named += "\n" + tauri_docs.read_text()
    if "tauri_gate" not in named:
        fail(
            "#279: G5 — docs/hacking/pipeline.md and/or docs/hacking/tauri.md "
            "must name the tauri_gate package"
        )

    compile_paths = [entry, *sorted(p for p in pkg.glob("*.py") if p.is_file())]
    compiled = run(
        [sys.executable, "-m", "py_compile", *[str(p) for p in compile_paths]],
        check=False,
    )
    if compiled.returncode != 0:
        fail(
            "#279: G5 — py_compile failed:\n"
            + (compiled.stderr or compiled.stdout or "")
        )


def main() -> None:
    root = repo_root()
    crate = root / "crates" / "interlace-tauri"
    toml = (crate / "Cargo.toml").read_text()
    if "publish = false" not in toml:
        fail("interlace-tauri must set publish = false")
    for plug in ("tauri-plugin-http", "tauri-plugin-updater"):
        if plug in toml:
            fail(f"{plug} must not be a dependency")

    ws = (root / "Cargo.toml").read_text()
    if '"crates/interlace-tauri"' not in ws:
        fail("interlace-tauri must be a workspace member")
    dm = ws[ws.find("default-members") : ws.find("[workspace.package]")]
    if "interlace-tauri" in dm:
        fail("interlace-tauri must not be a default-member")

    conf = (crate / "tauri.conf.json").read_text()
    if CSP not in conf:
        fail(f"tauri.conf.json missing exact CSP:\n{CSP}")
    import json

    cfg = json.loads(conf)
    bundle = cfg.get("bundle") or {}
    if bundle.get("active") is not True:
        fail("bundle.active must be true (UI8 unsigned .app/.dmg)")
    targets = bundle.get("targets") or []
    if "app" not in targets or "dmg" not in targets:
        fail("bundle.targets must include app and dmg")
    if bundle.get("createUpdaterArtifacts"):
        fail("createUpdaterArtifacts must stay false (no updater)")
    mac = bundle.get("macOS") or {}
    if mac.get("entitlements") != "Interlace.entitlements":
        fail("bundle.macOS.entitlements must be Interlace.entitlements")
    if mac.get("signingIdentity") != "-":
        fail('signingIdentity must be "-" (ad-hoc / unsigned)')
    icons = bundle.get("icon") or []
    if "icons/icon.icns" not in icons:
        fail("bundle.icon must include icons/icon.icns")
    if not (crate / "icons" / "icon.icns").is_file():
        fail("icons/icon.icns missing")

    ent = (crate / "Interlace.entitlements").read_text()
    if "com.apple.security.app-sandbox" not in ent:
        fail("sandbox entitlement required")
    if "network.server" in ent:
        fail("entitlements must omit network.server")
    # WKWebView will not paint tauri://localhost in a sandbox without this.
    # Measured 2026-08-10: sandbox-only and sandbox+JIT = blank .app;
    # sandbox+network.client shows the UI. Still no HTTP client crate.
    if "network.client" not in ent:
        fail("entitlements must include network.client (WKWebView local UI)")
    if "allow-jit" not in ent:
        fail("entitlements must include cs.allow-jit for WKWebView")

    assert_app_notarize(crate)

    app = (crate / "web" / "App.svelte").read_text()
    if "phones home" not in app or "HTTP" not in app:
        fail("Svelte UI must state no phone-home and no HTTP client")
    if "confirm(" in app:
        fail("App.svelte must not use window.confirm after UI primitives")
    for rel in (
        "web/lib/components/ui/button/button.svelte",
        "web/lib/components/ui/input/input.svelte",
        "web/lib/components/ui/dialog/dialog.svelte",
        "web/lib/components/ui/scroll-area/scroll-area.svelte",
    ):
        if not (crate / rel).is_file():
            fail(f"missing owned primitive {rel}")
    empty = crate / "web" / "lib" / "EmptyState.svelte"
    if not empty.is_file():
        fail("EmptyState.svelte required for UI empty/loading copy")
    en_chrome = app + "\n" + _chrome_en_text(crate)
    if "Opening last archive" not in en_chrome:
        fail("boot screen must say Opening last archive (no blank flash)")
    doctor = crate / "web" / "lib" / "DoctorPane.svelte"
    if not doctor.is_file():
        fail("DoctorPane.svelte required for UI7")
    dtxt = doctor.read_text()
    doctor_en = dtxt + "\n" + _chrome_en_text(crate)
    if "Not encrypted at rest" not in doctor_en or "FileVault" not in doctor_en:
        fail("Doctor pane must say not encrypted at rest; FileVault is encryption")
    if "database is encrypted" in dtxt or "your data is encrypted" in dtxt.lower():
        fail("UI must not claim the DB is encrypted at rest")
    if "doctorRun" not in dtxt:
        fail("Doctor pane must call doctorRun (not only CLI copy)")
    if "data-cloud-warning" not in app:
        fail("App.svelte must show a persistent cloud-path banner")
    if "UI7 will run doctor" in app:
        fail("placeholder UI7 CLI-only copy must be gone")
    assert_chat_bubbles(crate)
    assert_day_separators(crate)
    assert_local_tz_display(crate)
    assert_timeline_latest(crate)
    assert_conversation_switcher(crate)
    assert_timeline_platform_chips(crate)
    assert_timeline_kind_filter(crate)
    assert_gmail_timeline_rows(crate)
    assert_people_sidebar_no_x_scroll(crate)
    assert_people_filter_identity(crate)
    assert_people_list_lock(crate)
    assert_boot_spinner(crate)
    assert_photo_lightbox(crate)
    assert_voice_note_player(crate)
    assert_voice_note_seek(crate)
    assert_cas_video_pdf(crate)
    assert_bubble_linkify(crate)
    assert_bubble_search(crate)
    assert_reveal_archive(crate)
    assert_first_run(crate)
    assert_font_density(crate)
    assert_light_chrome(crate)
    assert_chrome_locale_panes(crate)
    assert_gate_tauri_split(crate)
    assert_virtualized_timeline(crate)
    assert_variable_height_timeline(crate)
    assert_search_platform_select(crate)
    assert_search_conversation_kind(crate)
    assert_search_person_picker(crate)
    assert_search_jump_to_message(crate)
    assert_search_attachment_filter(crate)
    assert_search_safe_highlight(crate)
    assert_search_filters_secondary(crate)
    assert_search_hit_density(crate)
    assert_review_identifiers(crate)
    assert_window_title(crate)
    assert_macos_menu(crate)
    assert_chrome_locale(crate)
    assert_keyboard_map(crate)
    assert_chrome_search_field(crate)
    assert_search_as_you_type(crate)
    assert_custom_titlebar(crate)
    assert_people_sidebar_collapse(crate)
    assert_person_inspector(crate)
    assert_keyboard_list_arrows(crate)
    assert_command_palette(crate)
    assert_command_palette_people_cap(crate)
    assert_command_palette_field_keys(crate)
    assert_command_palette_clipboard(crate)
    assert_focus_aria_audit(crate)
    assert_contrast_tokens(crate)
    assert_appearance_os(crate)
    assert_status_tokens(crate)
    assert_import_progress(crate)
    assert_import_cancel(crate)
    assert_review_chrome(crate)
    assert_sidebar_undo_chrome(crate)
    assert_motion(crate)
    assert_a11y_listbox_focus_motion(crate)
    assert_human_time_people(crate)
    assert_drag_drop_import(crate)
    assert_copy_reveal_cas(crate)
    assert_defer_doctor_cas(crate)
    assert_design_tokens(crate)
    assert_typography(crate)
    assert_lucide_icons(crate)
    assert_owned_primitives(crate)
    assert_empty_next_action(crate)
    assert_loading_skeletons(crate)
    assert_timeline_append_skeleton_guard(crate)
    assert_inflight_audible_status(crate)
    assert_recoverable_toasts(crate)
    assert_partial_pane_errors(crate)
    assert_partial_retry_generation(crate)
    assert_timeline_grouped_runs(crate)
    assert_timeline_bubble_hierarchy(crate)
    assert_timeline_attach_slot(crate)
    cas = (crate / "web" / "lib" / "CasAttach.svelte").read_text()
    if "casDataUrl" not in cas:
        fail("CAS viewer must load bytes via casDataUrl (data: URL; Vite cannot fetch cas://)")
    if "http://" in cas or "https://" in cas:
        fail("CAS viewer must not use remote URLs")
    if "protocol-asset" in toml or "dangerousRemoteDomainIpcAccess" in conf:
        fail("must not enable remote asset IPC")
    if (crate / "ui" / "app.js").is_file():
        fail("vanilla ui/app.js must be gone after UI-FE")
    if not (crate / "package-lock.json").is_file():
        fail("package-lock.json must be committed")
    pkg = (crate / "package.json").read_text()
    if "bits-ui" not in pkg:
        fail("bits-ui must be a local dependency (no CDN theme)")
    vite = (crate / "vite.config.ts").read_text()
    if 'base: "./"' not in vite and "base: './'" not in vite:
        fail("vite.config.ts must set base: './' so the .app loads JS")
    if "tauri:build" not in pkg:
        fail("package.json must expose tauri:build")

    wf = root / ".github" / "workflows" / "app-release.yml"
    if not wf.is_file():
        fail("app-release.yml missing (UI8 app-v* tags)")
    wtxt = wf.read_text()
    if "app-v*" not in wtxt:
        fail("app-release.yml must trigger on app-v* tags only")
    if "cargo publish" in wtxt or "CARGO_REGISTRY_TOKEN" in wtxt:
        fail("app-release.yml must not publish crates (D3)")
    if "tauri-plugin-updater" in wtxt or "plugin-updater" in wtxt:
        fail("app-release.yml must not install an updater")
    pub = (root / ".github" / "workflows" / "publish.yml").read_text()
    if "tauri:build" in pub or "bundle/dmg" in pub or "Interlace.app" in pub:
        fail("publish.yml is crates.io v* only; do not attach the .dmg there")

    npm = run(
        ["npm", "ci"],
        cwd=crate,
        check=False,
    )
    if npm.returncode != 0:
        fail(npm.stderr or npm.stdout)
    built = run(["npm", "run", "build"], cwd=crate, check=False)
    if built.returncode != 0:
        fail(built.stderr or built.stdout)
    dist = (crate / "dist" / "index.html").read_text()
    if "cdn." in dist or "unpkg.com" in dist:
        fail("production bundle must not load a CDN")
    if 'src="/assets/' in dist or "href=\"/assets/" in dist:
        fail("dist/index.html must use relative asset URLs (vite base ./); absolute /assets blanks the .app")
    if "connect-src 'none'" in conf:
        fail("connect-src 'none' blocks Tauri IPC and blanks the bundled .app")

    chk = run(["cargo", "check", "-p", "interlace-tauri"], cwd=root, check=False)
    if chk.returncode != 0:
        fail(chk.stderr or chk.stdout)

    clip = run(
        ["cargo", "clippy", "-p", "interlace-tauri", "--", "-D", "warnings"],
        cwd=root,
        check=False,
    )
    if clip.returncode != 0:
        fail(clip.stderr or clip.stdout)

    for kind in ("bans", "licenses"):
        d = run(
            [
                "cargo",
                "deny",
                "--manifest-path",
                str(crate / "Cargo.toml"),
                "check",
                kind,
            ],
            cwd=root,
            check=False,
        )
        if d.returncode != 0:
            fail(f"cargo deny check {kind} interlace-tauri failed\n{d.stdout}\n{d.stderr}")

    for name in ("reqwest", "hyper"):
        t = run(
            [
                "cargo",
                "tree",
                "-p",
                "interlace-tauri",
                "-i",
                name,
                "--target",
                "aarch64-apple-darwin",
            ],
            cwd=root,
            check=False,
        )
        out = (t.stdout or "") + (t.stderr or "")
        if "warning: nothing to print" not in out and f"{name} v" in out:
            fail(f"{name} is in the macOS tauri graph\n{out}")

    print("gate_tauri ok")


if __name__ == "__main__":
    main()
