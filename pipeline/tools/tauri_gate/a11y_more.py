"""Additional a11y asserts."""
from __future__ import annotations

from tauri_gate.a11y_lib import *


def assert_focus_aria_audit(crate: Path) -> None:
    """#216: visible focus rings + ARIA on chrome/dialogs (not a WCAG certificate)."""
    app_path = crate / "web" / "App.svelte"
    if not app_path.is_file():
        fail("#216: App.svelte required (focus rings + ARIA on chrome/dialogs)")
    app = _web_logic(crate)
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
    search = _search_pane_blob(crate) if search_path.is_file() else ""
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
