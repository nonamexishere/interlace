# Governance

## Maintainer

Single maintainer: GitHub [`nonamexishere`](https://github.com/nonamexishere)
until a second owner is named **in this file**.

Contact for CoC reports: open a private GitHub advisory or email the address
on that GitHub profile.

## Decision process

- Architecture: `docs/design/DESIGN.md` is normative.
- Changes that touch Key Decisions require an ADR under `docs/design/adr/`
  **and** a DESIGN.md edit in the same PR.
- Open Questions 1–10 in DESIGN.md are decided. Contributors implement them;
  they do not re-open them in drive-by PRs.

## Crates.io publishing

`cargo publish` only from annotated tags via `.github/workflows/publish.yml`
(tag `vX.Y.Z`). Do not publish 0.0.1 again. See [docs/hacking/release.md](docs/hacking/release.md).

## Archive of satellites

`nonamexishere/interlace-core` and `nonamexishere/interlace-cli` are name/publish
mirrors (redirect READMEs), not contribution targets. Send PRs here.
