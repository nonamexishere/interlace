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

## Unsigned desktop app (`app-v*`)

Separate from crates.io. After UI8 is on `master`:

```bash
git checkout master
git pull
git tag -a app-v0.1.1 -m "Interlace.app 0.1.1"
git push origin app-v0.1.1
```

`.github/workflows/app-release.yml` runs `npm run tauri:build` on macOS,
checks the `.app` still has sandbox + `network.client` and **no**
`network.server`
entitlement, and attaches `Interlace.app.zip` + `.dmg` to that GitHub
Release. Ad-hoc sign (`signingIdentity: "-"`). No notarization, no updater.

Users: `xattr -dr com.apple.quarantine` then open. CLI remains
`cargo install interlace`.

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
