# Release 0.1.x

## First real crates.io publish

Versions stay **0.0.1** (name-squat) until this line of work. **0.1.0** is the
first usable CLI.

1. `CARGO_REGISTRY_TOKEN` must exist as a GitHub Actions secret on
   `nonamexishere/interlace` (crates.io API token; never commit it).
2. Merge the version-bump PR to `master` with gates green.
3. Annotated tags (D7). One `vX.Y.Z` tag publishes **all three** crates in order
   `interlace-core` → `interlace-cli` → `interlace`:

```bash
git checkout master
git pull
git tag -a v0.1.1 -m "interlace 0.1.1"
git push origin v0.1.1
```

`.github/workflows/publish.yml` then `cargo publish -p` each package and
attaches **unsigned** macOS `interlace` / `interlace-cli` binaries to a GitHub
Release. Notes come from the matching `CHANGELOG.md` section (not Unreleased).
Codesign is later.

Do **not** publish 0.0.1 again. Do **not** invent a fourth crates.io name
(`interlace-cli-common` and `interlace-fixtures` stay `publish = false`).
`interlace-tauri` stays unpublished. The macOS **.app / .dmg** is a different
tag (`app-v*`); see below.

## Desktop app (`app-v*`) — Developer ID + notarized

Separate from crates.io. When Apple signing/notary secrets are set,
`.github/workflows/app-release.yml` Developer ID signs and notarizes
(via notarytool / Tauri 2 env) the `.app` / `.dmg`.

GitHub Actions secrets (never commit these):

- `APPLE_CERTIFICATE` — base64-encoded Developer ID Application `.p12`
- `APPLE_CERTIFICATE_PASSWORD` — p12 password
- `APPLE_SIGNING_IDENTITY` — e.g. `Developer ID Application: …`
- notary: `APPLE_API_KEY` + `APPLE_API_ISSUER` + `APPLE_API_KEY_PATH`
  (App Store Connect API key id / issuer / `.p8` contents), **or**
  `APPLE_ID` + `APPLE_PASSWORD` + `APPLE_TEAM_ID`

The job **fails closed** if those secrets are empty. It does not upload
an ad-hoc build as if it were notarized.

Local `tauri:dev` / `tauri:build` stay ad-hoc (`signingIdentity: "-"`
in the committed `tauri.conf.json`). CI injects the real identity.

**Ask before the first notarized `app-v*` tag.** #267 / PR #285 wired
the workflow; the tag is not cut.

```bash
git checkout master
git pull
git tag -a app-v0.1.3 -m "Interlace.app 0.1.3"
git push origin app-v0.1.3
```

The workflow checks the `.app` still has sandbox + `network.client` and
**no** `network.server` entitlement, staples the notary ticket, and
attaches `Interlace.app.zip` + `.dmg` to that GitHub Release. No updater.

Users: drag Interlace.app to Applications and open. Fallback for older
ad-hoc tags (`app-v0.1.2` and earlier):
`xattr -dr com.apple.quarantine`. CLI remains `cargo install interlace`.

Do **not** put the `.dmg` on a `v*` crates.io tag.

## Patch releases

1. Bump `[workspace.package] version` and the path `version =` pins in the
   root `Cargo.toml` (e.g. `0.1.0` → `0.1.1`).
2. Move shipped bullets out of `[Unreleased]` into a dated `## [0.1.1]` section.
3. Merge that PR to `master` with gates green.
4. Annotated tag `v0.1.1` as above. Do not retag; if publish fails mid-way,
   retry the remaining `-p` (see below).

## Mirror READMEs (satellite GitHub repos)

After 0.1.0 is on crates.io (so `repository` URLs point at this monorepo),
replace the README of `nonamexishere/interlace-core` and
`nonamexishere/interlace-cli` with the text in
[mirrors.md](mirrors.md). Leave those remotes **un-archived** for ~6 months
(D2). Do **not** git-subtree-split.

## Retry a single crate

If index lag fails `interlace` after core succeeded, wait and:

```bash
cargo publish -p interlace --locked
```

or retag is not needed; re-run the failed job / publish that `-p` locally with
the same token.
