# Satellite GitHub repo READMEs

Paste this (adjust the crate name in the title) into
`nonamexishere/interlace-core` and `nonamexishere/interlace-cli`.

```markdown
# interlace-core

**Development moved.** This repository is a crates.io / name mirror only.

All issues, PRs, and source live in the monorepo:

**https://github.com/nonamexishere/interlace**

```toml
# crates/interlace-core in the monorepo
interlace-core = "0.1.1"
```

Do not open PRs here. `cargo publish` runs from annotated tags on the monorepo
(`.github/workflows/publish.yml`).
```

For `interlace-cli`, same body with title `# interlace-cli` and
`cargo install interlace-cli` pointing at the monorepo README.

The original `nonamexishere/interlace` tree **is** the monorepo; do not replace
its README with this redirect.
