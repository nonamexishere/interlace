#!/usr/bin/env python3
"""#267: Developer ID + notarize app-v* (fail closed; local signingIdentity stays "-").

app-release.yml must mention notarytool / Developer ID / Tauri notarize env.
The app-v* job fails when signing/notary secrets are missing (no ad-hoc upload
as if notarized). New-tag user docs are drag-and-open; xattr is fallback for
older ad-hoc tags. Entitlements stay sandbox + network.client, no network.server.
createUpdaterArtifacts false. No Sparkle / updater plugin / HTTP client.
docs/hacking/release.md names the secrets and says ask before the first
notarized app-v* tag. Committed signingIdentity may stay "-".
Empty APPLE_ID / APPLE_PASSWORD / APPLE_TEAM_ID must be unset (or only the
chosen notary method exported) before tauri:build so API-key auth is not shadowed.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fail, repo_root  # noqa: E402

# Tauri 2 signing / notary env (https://v2.tauri.app/distribute/sign/macos/).
_TAURI_NOTARY_ENV = (
    "APPLE_CERTIFICATE",
    "APPLE_CERTIFICATE_PASSWORD",
    "APPLE_SIGNING_IDENTITY",
    "APPLE_ID",
    "APPLE_PASSWORD",
    "APPLE_TEAM_ID",
    "APPLE_API_KEY",
    "APPLE_API_ISSUER",
    "APPLE_API_KEY_PATH",
)

_NOTARY_MENTION = re.compile(
    r"("
    r"notarytool"
    r"|Developer ID"
    r"|APPLE_CERTIFICATE"
    r"|APPLE_SIGNING_IDENTITY"
    r"|APPLE_API_KEY"
    r"|APPLE_API_ISSUER"
    r"|APPLE_API_KEY_PATH"
    r"|APPLE_ID\b"
    r"|APPLE_PASSWORD"
    r"|APPLE_TEAM_ID"
    r")",
)

_APPLE_SECRET_REF = re.compile(
    r"""secrets\.(APPLE_[A-Z_]+)|secrets\[['"]APPLE_[A-Z_]+['"]\]"""
)

# Empty-secret fail-closed: shell test / ${VAR:?} / GHA `secrets.APPLE_* == ''`.
_FAIL_CLOSED = re.compile(
    r"("
    r"test\s+-n\s+[\"']?\$\{?APPLE_[A-Z_]+"
    r"|\[\s+-[nz]\s+[\"']?\$\{?(?:-|APPLE_[A-Z_]+)"
    r"|\$\{APPLE_[A-Z_]+:\?"
    r"|secrets\.APPLE_[A-Z_]+\s*==\s*['\"]{2}"
    r")",
)

_UNSIGNED_ONLY_NOTES = re.compile(
    r"Unsigned macOS app \(ad-hoc\)",
)

_XATTR_CMD = re.compile(r"xattr\s+-dr\s+com\.apple\.quarantine")

# xattr is allowed only as fallback for older ad-hoc tags — not a tag
# comment elsewhere in the file ("Load older", `app-v0.1.1` header).
_XATTR_FALLBACK_NEAR = re.compile(
    r"("
    r"\bfallback\b"
    r"|older\s+(ad-hoc|unsigned|tags?|app-v)"
    r"|app-v0\.1\.[012]\s+and\s+earlier"
    r")",
    re.I,
)

_ASK_FIRST_NOTARY = re.compile(
    r"ask before.{0,80}(first\s+)?notarized",
    re.I,
)

_RELEASE_SECRET_NAME = re.compile(
    r"APPLE_(CERTIFICATE|SIGNING_IDENTITY|API_KEY|API_ISSUER|ID)\b"
)

_UPDATER_OR_HTTP = re.compile(
    r"("
    r"tauri-plugin-updater"
    r"|tauri-plugin-http"
    r"""|["']sparkle["']"""
    r"|@sparkle"
    r"|sparkle\s*="
    r")",
    re.I,
)

_HEDGE_NOTARY = re.compile(
    r"not\s+notarized|no\s+notarization",
    re.I,
)

# Job/step env: APPLE_ID: ${{ secrets.APPLE_ID }} (empty secret → "", not unset).
_APPLE_ID_TRIO = ("APPLE_ID", "APPLE_PASSWORD", "APPLE_TEAM_ID")
_ALWAYS_EXPORT_ID_TRIO_SECRET = re.compile(
    r"(?m)^[ \t]+(APPLE_ID|APPLE_PASSWORD|APPLE_TEAM_ID):\s*"
    r"\$\{\{\s*secrets\.(APPLE_ID|APPLE_PASSWORD|APPLE_TEAM_ID)\s*\}\}"
)
_UNSET_CMD = re.compile(r"\bunset\b([^\n#]*)")
_TAURI_BUILD_RUN = re.compile(
    r"(?ms)^[ \t]+run:\s*\|\n((?:[ \t]+.+\n)*?[ \t]+.*\btauri:build\b.*)"
)


def _positive_notarize(text: str) -> bool:
    """True if text claims a notarized / Developer ID install (not only 'not notarized')."""
    if "Developer ID" in text:
        return True
    stripped = _HEDGE_NOTARY.sub(" ", text)
    return bool(re.search(r"notariz", stripped, re.I))


def _xattr_without_fallback(text: str) -> bool:
    """True when an xattr command is present and not marked as old-tag fallback."""
    for m in _XATTR_CMD.finditer(text):
        window = text[max(0, m.start() - 400) : m.end() + 400]
        if _XATTR_FALLBACK_NEAR.search(window):
            return False
    return bool(_XATTR_CMD.search(text))


def _always_exports_apple_id_trio(wtxt: str) -> bool:
    """True when APPLE_ID / PASSWORD / TEAM_ID are always mapped from secrets."""
    mapped = {m.group(1) for m in _ALWAYS_EXPORT_ID_TRIO_SECRET.finditer(wtxt)}
    return set(_APPLE_ID_TRIO) <= mapped


def _tauri_build_run_script(wtxt: str) -> str:
    """The run: | block that invokes tauri:build, or empty."""
    m = _TAURI_BUILD_RUN.search(wtxt)
    return m.group(1) if m else ""


def _unsets_apple_id_trio(script: str) -> bool:
    """True if script unsets APPLE_ID / APPLE_PASSWORD / APPLE_TEAM_ID."""
    if not script:
        return False
    found: set[str] = set()
    for m in _UNSET_CMD.finditer(script):
        found.update(re.findall(r"APPLE_(?:ID|PASSWORD|TEAM_ID)\b", m.group(1)))
    if set(_APPLE_ID_TRIO) <= found:
        return True
    # for v in APPLE_ID APPLE_PASSWORD APPLE_TEAM_ID; do unset "$v"
    for m in re.finditer(r"\bunset\b", script):
        window = script[max(0, m.start() - 240) : m.end() + 40]
        if all(n in window for n in _APPLE_ID_TRIO):
            return True
    return False


def _assert_user_install_docs(label: str, text: str) -> None:
    if not text.strip():
        fail(f"#267: {label} required — notarized install is drag-and-open")
    if not _positive_notarize(text):
        fail(
            f"#267: {label} must document notarized install "
            "(drag-and-open; not unsigned-only)"
        )
    if not re.search(
        r"("
        r"drag-and-open"
        r"|drag\s+and\s+open"
        r"|drag-to-Applications"
        r"|drag\s+to\s+(?:/)?Applications"
        r"|drag\s+(?:the\s+)?(?:\.app|Interlace|app)\b"
        r")",
        text,
        re.I,
    ):
        fail(
            f"#267: {label} must say drag-and-open for new notarized app-v* "
            "(xattr is not the only path)"
        )
    if _xattr_without_fallback(text):
        fail(
            f"#267: {label} xattr must stay only as fallback for older "
            "ad-hoc tags (app-v0.1.2 and earlier)"
        )
    if re.search(r"Install the \.app \(unsigned\)", text):
        fail(
            f"#267: {label} must not title current install as unsigned-only"
        )
    if re.search(r"Desktop app \(macOS, unsigned\)", text):
        fail(
            f"#267: {label} must not present the current desktop app as unsigned-only"
        )


def assert_app_notarize(crate: Path) -> None:
    """#267: app-v* is Developer ID + notarized; local tauri.conf stays ad-hoc.

    Follow-up: empty APPLE_ID / APPLE_PASSWORD / APPLE_TEAM_ID must be unset
    (or not always exported) before tauri:build so API-key notary is not shadowed.
    """
    root = repo_root()
    wf = root / ".github" / "workflows" / "app-release.yml"
    wtxt = wf.read_text() if wf.is_file() else ""
    if not wtxt.strip():
        fail("#267: .github/workflows/app-release.yml missing")

    # 1) Workflow mentions notarize / notarytool / Developer ID / Tauri env.
    #    Bare "Not notarized" / "No notarization" does not count.
    if not _NOTARY_MENTION.search(wtxt):
        fail(
            "#267: app-release.yml must mention notarytool / Developer ID / "
            "Tauri notarize env (workflow is ad-hoc only)"
        )

    # 2) Fail closed when signing/notary secrets are missing.
    if not _APPLE_SECRET_REF.search(wtxt):
        fail(
            "#267: app-v* job must use signing/notary secrets "
            "(secrets.APPLE_*; fail closed — no silent ad-hoc upload)"
        )
    if not _FAIL_CLOSED.search(wtxt):
        fail(
            "#267: app-v* job must fail closed when signing/notary secrets "
            "are missing (no upload of ad-hoc as if notarized)"
        )

    # 3) New-tag notes / user docs are drag-and-open; xattr is old-tag fallback.
    if _UNSIGNED_ONLY_NOTES.search(wtxt):
        fail(
            "#267: app-v* release notes must not claim unsigned/ad-hoc "
            "as the only path"
        )
    if _xattr_without_fallback(wtxt):
        fail(
            "#267: app-v* extra notes must not require xattr as the only "
            "install (keep it as fallback for older ad-hoc tags)"
        )
    readme = root / "README.md"
    app_docs = root / "docs" / "user" / "app.md"
    _assert_user_install_docs(
        "README.md",
        readme.read_text() if readme.is_file() else "",
    )
    _assert_user_install_docs(
        "docs/user/app.md",
        app_docs.read_text() if app_docs.is_file() else "",
    )

    # 4) Entitlements unchanged; no updater / Sparkle / HTTP client.
    ent_path = crate / "Interlace.entitlements"
    ent = ent_path.read_text() if ent_path.is_file() else ""
    if "com.apple.security.app-sandbox" not in ent:
        fail("#267: entitlements must keep app-sandbox")
    if "network.client" not in ent:
        fail("#267: entitlements must keep network.client")
    if "network.server" in ent:
        fail("#267: entitlements must omit network.server")

    conf_path = crate / "tauri.conf.json"
    conf = conf_path.read_text() if conf_path.is_file() else ""
    if not conf.strip():
        fail("#267: tauri.conf.json missing")
    cfg = json.loads(conf)
    bundle = cfg.get("bundle") or {}
    if bundle.get("createUpdaterArtifacts"):
        fail("#267: createUpdaterArtifacts must stay false (no updater)")

    toml = (crate / "Cargo.toml").read_text() if (crate / "Cargo.toml").is_file() else ""
    pkg = (
        (crate / "package.json").read_text()
        if (crate / "package.json").is_file()
        else ""
    )
    dep_blob = "\n".join((toml, pkg, conf, wtxt))
    if _UPDATER_OR_HTTP.search(dep_blob):
        fail("#267: no Sparkle / updater plugin / HTTP client")

    # 5) release.md: secret names + ask before the first notarized tag.
    release = root / "docs" / "hacking" / "release.md"
    rtxt = release.read_text() if release.is_file() else ""
    if not rtxt.strip():
        fail("#267: docs/hacking/release.md required")
    if "Developer ID" not in rtxt:
        fail(
            "#267: docs/hacking/release.md must say app-v* is Developer ID "
            "+ notarized when secrets are set"
        )
    if not _RELEASE_SECRET_NAME.search(rtxt):
        fail(
            "#267: docs/hacking/release.md must list signing/notary secret names"
        )
    if not _ASK_FIRST_NOTARY.search(rtxt):
        fail(
            "#267: docs/hacking/release.md must say ask before the first "
            "notarized app-v* tag"
        )

    # 6) Empty Apple ID trio must not shadow API-key notary at tauri:build.
    #    Unset GitHub secrets become ""; Tauri 2.11 matches Some("") first.
    if _always_exports_apple_id_trio(wtxt) and not _unsets_apple_id_trio(
        _tauri_build_run_script(wtxt)
    ):
        fail(
            "#267: app-release.yml must unset empty APPLE_ID / APPLE_PASSWORD / "
            "APPLE_TEAM_ID (or only export the chosen notary method) before "
            "tauri:build"
        )


def main() -> None:
    root = repo_root()
    assert_app_notarize(root / "crates" / "interlace-tauri")
    print("gate_app_release ok")


if __name__ == "__main__":
    main()
