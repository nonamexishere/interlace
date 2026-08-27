"""Additional locale asserts."""
from __future__ import annotations

from tauri_gate.locale_menu import *
from tauri_gate.locale_pack import *


def assert_chrome_locale_panes(crate: Path) -> None:
    """#278: Review / Import / Doctor remaining chrome uses t().

    Empty states, ConfirmDialog titles (Link these people / Stop suggesting /
    Undo last link / doctor integrity / rebuild / GC), undo label, Pick file,
    and Import Cancel go through t(). New keys exist in both packs; tr values
    are not identical English copies. No t(body_text|snippet|display_name|
    preview). detectLocale stays OS-first (tr* → tr). No third pack. No fetch
    of locale files. Keep #131 Arşiv aç / Doktor. Docs: Review / Import /
    Doctor chrome follows OS language (en/tr); bodies stay as imported.
    Do not rewrite #131.
    """
    root = repo_root()
    panes: dict[str, str] = {}
    for name in _PANE_CHROME_FILES:
        path = _pane_file(crate, name)
        if not path.is_file():
            fail(
                f"#278: {name} required "
                "(Review / Import / Doctor remaining chrome uses t())"
            )
        panes[name] = path.read_text()
    logic = _web_logic(crate)
    cleaned = _without_comments(logic)
    helpers = _chrome_helper_names(logic)
    en_text = _chrome_en_text(crate)
    tr_text = _chrome_tr_text(crate)
    i18n_path = crate / "web" / "lib" / "i18n.ts"
    i18n = i18n_path.read_text() if i18n_path.is_file() else ""

    # 1) Remaining Review / Import / Doctor chrome uses t() — not hardcoded English.
    leftover = _pane_chrome_phrases(panes)
    if leftover:
        fail(
            "#278: Review / Import / Doctor remaining chrome must use t() — "
            "still hardcoded English: " + "; ".join(leftover)
        )
    unwired = _pane_chrome_unwired(panes, helpers)
    if unwired:
        fail(
            "#278: Review / Import / Doctor remaining chrome must use t() "
            "(empty states, ConfirmDialog titles, undo, Pick file, Import Cancel): "
            + "; ".join(unwired)
        )

    # 2) Those strings live in the en pack; same keys in tr; tr is not an English copy.
    if not en_text.strip() or not tr_text.strip():
        fail("#278: en + tr chrome packs required (do not drop #131 packs)")
    en_entries = _chrome_pack_entries(en_text)
    tr_entries = _chrome_pack_entries(tr_text)
    if not en_entries or not tr_entries:
        fail("#278: could not parse chrome pack key/value entries from en.ts / tr.ts")
    missing_en = [p for p in _PANE_EN_REQUIRED if not _keys_for_phrase(en_entries, p)]
    if "Cancel" not in en_entries.values() and not _keys_for_phrase(en_entries, "Cancel"):
        missing_en.append("Cancel")
    if missing_en:
        fail(
            "#278: new Review / Import / Doctor chrome keys must exist in the en pack "
            f"(missing values: {', '.join(missing_en)})"
        )
    extra_en = set(en_entries) - set(tr_entries)
    extra_tr = set(tr_entries) - set(en_entries)
    if extra_en or extra_tr:
        bits: list[str] = []
        if extra_en:
            bits.append("in en only: " + ", ".join(sorted(extra_en)))
        if extra_tr:
            bits.append("in tr only: " + ", ".join(sorted(extra_tr)))
        fail(
            "#278: same ChromeKey on both en and tr packs — " + "; ".join(bits)
        )
    copied: list[str] = []
    seen_keys: set[str] = set()
    for phrase in (*_PANE_EN_REQUIRED, "Cancel"):
        for key in _keys_for_phrase(en_entries, phrase):
            if key in seen_keys:
                continue
            seen_keys.add(key)
            ev = en_entries.get(key, "").strip()
            tv = tr_entries.get(key, "").strip()
            if not tv:
                copied.append(f"{key} missing in tr")
            elif tv == ev:
                copied.append(key)
    if copied:
        fail(
            "#278: for new Review / Import / Doctor keys, tr values must not be "
            "identical English copies: " + ", ".join(copied)
        )

    # 3) Never t(body_text|snippet|display_name|preview).
    body_blob = logic + "\n" + "\n".join(panes[n] for n in _PANE_CHROME_FILES)
    if _chrome_helper_on_body(body_blob, helpers):
        fail(
            "#278: do not pass body_text / snippet / display_name / preview "
            "through t() — message bodies stay as imported"
        )

    # 4) detectLocale still OS-first (tr* → tr). No third pack. No fetch of locale files.
    detect = _function_body(i18n, "detectLocale") or _function_body(cleaned, "detectLocale")
    resolver = detect or _locale_resolver_surface(cleaned) or _locale_resolver_surface(logic)
    if not _OS_LOCALE_READ.search(resolver) and not _OS_LOCALE_READ.search(i18n):
        fail(
            "#278: detectLocale must stay OS-first "
            "(navigator.language / navigator.languages / Intl / Tauri) — "
            "tr* → tr, else en"
        )
    if not _TR_STAR_PICK.search(resolver):
        fail("#278: detectLocale must still map OS locale tr* → tr")
    if not _EN_DEFAULT_PICK.search(resolver):
        fail("#278: detectLocale must still default every non-tr OS locale to en")
    third: list[str] = []
    locale_dir = crate / "web" / "lib" / "locales"
    if locale_dir.is_dir():
        for p in sorted(locale_dir.iterdir()):
            if not p.is_file() or p.name.endswith(".d.ts"):
                continue
            if p.suffix not in {".ts", ".json", ".toml"}:
                continue
            stem = p.stem.lower()
            if stem in {"en", "tr", "index"}:
                continue
            third.append(str(p.relative_to(crate)))
    for p in _web_pack_candidates(crate):
        lang = _stem_chrome_lang(p)
        if lang and lang not in {"en", "tr"}:
            rel = str(p.relative_to(crate))
            if rel not in third:
                third.append(rel)
        elif _THIRD_PACK_STEM.search(p.stem):
            rel = str(p.relative_to(crate))
            if rel not in third:
                third.append(rel)
    if third:
        fail(
            "#278: no third locale pack — en + tr only. Found: " + ", ".join(third)
        )
    fetch_hits: list[str] = []
    for label, src in (
        ("i18n.ts", i18n),
        ("en pack", en_text),
        ("tr pack", tr_text),
        ("ReviewPane", panes["ReviewPane.svelte"]),
        ("ImportPane", panes["ImportPane.svelte"]),
        ("DoctorPane", panes["DoctorPane.svelte"]),
    ):
        surface = _without_comments(src)
        if _FETCH_CALL.search(surface) and (
            label in {"i18n.ts", "en pack", "tr pack"} or _LOCALE_FETCH.search(surface)
        ):
            fetch_hits.append(label)
    if _LOCALE_FETCH.search(cleaned):
        fetch_hits.append("web logic")
    if fetch_hits:
        fail(
            "#278: no fetch( of locale files — chrome packs are bundled. Found in: "
            + ", ".join(dict.fromkeys(fetch_hits))
        )

    # 5) Keep #131 Arşiv aç / Doktor.
    if "Arşiv aç" not in tr_text:
        fail('#278: keep #131 “Arşiv aç” in the tr pack')
    if "Doktor" not in tr_text:
        fail('#278: keep #131 “Doktor” in the tr pack')

    # Leftover Doctor backup sentences (remaining chrome, after the listed panes).
    doctor = panes["DoctorPane.svelte"]
    backup_left = [p for p in _PANE_BACKUP_LEFTOVER if p in doctor]
    if backup_left:
        fail(
            "#278: leftover Doctor backup chrome must use t() — still hardcoded: "
            + ", ".join(backup_left)
        )

    # 6) Docs: Review / Import / Doctor chrome follows OS language; bodies stay imported.
    docs = root / "docs" / "user" / "app.md"
    if not docs.is_file():
        fail(
            "#278: docs/user/app.md required — Review / Import / Doctor chrome "
            "follows OS language (en/tr); bodies stay as imported"
        )
    dtxt = docs.read_text()
    if not _DOCS_PANE_CHROME_LOCALE.search(dtxt):
        fail(
            "#278: docs/user/app.md must say Review / Import / Doctor chrome "
            "follows OS language (en/tr)"
        )
    if not _DOCS_PANE_BODIES_STAY.search(dtxt):
        fail(
            "#278: docs/user/app.md must say message bodies stay as imported"
        )
