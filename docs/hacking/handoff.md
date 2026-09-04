# Agent / session handoff

**Date:** 2026-09-04. **Owner:** Mustafa. **Repo:** [nonamexishere/interlace](https://github.com/nonamexishere/interlace) (public).
HEAD `def774c` (merge #345).

Read this first in a new session, then `gh pr list` / `gh issue list` (this file rots).
Do **not** dump real chat bodies or real contact names into issues, PRs, tests, or this file.

How we work: [`docs/hacking/pipeline.md`](pipeline.md) — researcher →
test-author → impl → reviewer. Skip researcher only when the issue already
names helpers, files, and must-IDs. The parent chat sequences those roles as
**separate agents**. Children do not spawn children. After researcher,
present each research finding and recommended mix; Mustafa may type
`take X from A, Y from B`. Fill that mix into `IN.md` **before**
test-author. The orchestrator does **not** implement product code.
Ask before commit / push / merge.

## Keep this file current

Update `docs/hacking/handoff.md` in the **same session** when any of these change
(prefer one short PR or the same product PR’s docs commit):

- HEAD / last merge on `master`
- Open vs closed product issues that affect “now”
- Recommended next steps order
- Machine paths, published versions, or tags (`v*`, `app-v*`)
- Dogfood archive facts (counts only — no names, no chat text)

Do **not** leave a session that merged product work with a stale “Snapshot” or
“Recommended next steps” section. If you only touched code and skipped this
file, say so in the wrap-up so the next agent rewrites it before coding.

## What Interlace is

OSS local-first offline desktop archive. Rust workspace + Tauri 2 macOS app.
SQLite+FTS5, CAS BLAKE3 (`cas/ab/cd/<hash>`). No server, no sync, no outbound
HTTP client (cargo-deny bans `reqwest`/`hyper`/`tokio` on core+cli; Tauri may
use `tokio` without `net`). Phase 1 = CLI; Phase 2 = Svelte 5 desktop UI
(UI0–UI8 done). **Phase 2.1 is closed** (epic #108, milestone 6). First
unsigned app release is **`app-v0.1.1`**. **Phase 2.2 polish is done.**
**Phase 2.3 coding is done** (epic **#264** / [milestone 8](https://github.com/nonamexishere/interlace/milestone/8) closed).
Children **#265–#279**, **#297**, **#300** (PRs **#282–#301**) are done.
**#303**, **#304**, **#305**, **#306**, **#307**, **#308**, **#309**,
**#310**, **#311**, **#312**, **#313**, **#314**, and **#315** are done
(PRs **#323–#328**, **#330**, **#332**, **#336**, **#338**, **#340**,
**#343**, **#345**). Next coding **#316** only if asked. Do not start
1.1 / 3 / 4.
Ask before the first notarized `app-v*` (#267 is wired; that tag is not cut).
Normative:
[`docs/design/UI-DESIGN.md`](../design/UI-DESIGN.md). Do not start 1.1 / 3 / 4.

Normative spec: [`docs/design/DESIGN.md`](../design/DESIGN.md).
Roadmap index: [`docs/hacking/roadmap.md`](roadmap.md) and issue **#52**.
Workflow: one issue → one PR `Fixes #N` → merge when CI jobs **`check`** +
**`tauri`** are green. Small conventional commits.

## Non-negotiables

- No fake WhatsApp JID. Name-only identities **never auto-merge** (I2).
- `--phone-region` required at init (D20). D18: group vs DM; D18-C owner-name 1:1 → DM.
- D25 Gmail fold only on gmail/googlemail. No SQLCipher; do not claim encryption.
- CSP `connect-src` is IPC-only (`ipc:` / `ipc.localhost`), not `'none'`
  (that blanked the `.app`). No `protocol-asset` if it opens remote/http-range.
- Sandbox **keeps `network.client`** (WKWebView / `tauri://` will not paint
  without it) and **omits `network.server`**. No HTTP client crate, no updater.
- Tests use `interlace-fixtures` + **placeholder names** only.
- Confirm with Mustafa before another crates.io tag / `v*` / `app-v*` publish.
- Do not kill other projects’ Metro/Docker. Do not force-push `master`.

## Machine paths (this Mac)

| What | Path |
| --- | --- |
| Repo | `~/AllTogether/interlace/interlace` (this monorepo; not `~/Desktop/…`) |
| Live archive | `~/Interlace` (mode 0700, exclusive flock) |
| Archive backups | `~/Interlace.bak-2026-08-10`, `~/Interlace.bak-2026-08-11` (may exist) |
| WhatsApp exports | `~/Downloads/WhatsApp/*.zip` (3 official iOS ZIPs; glob, do not name people) |
| Installed CLI | `~/.cargo/bin/interlace` (rebuild from workspace; crates.io 0.1.1 may lag) |
| App support | `~/Library/Application Support/Interlace/` (`config.toml`, `last-archive.bookmark`, sibling `recent-archives.json`) |
| Owner | `init --phone-region TR --name Mustafa` |

App holds exclusive flock. **File → Switch archive** drops the flock
without quitting (returns to setup). Or close `interlace-app` /
`tauri:dev` before CLI `import` / `doctor --integrity` / wipe.

## Snapshot (2026-08-28)

Published: `interlace` / `interlace-core` / `interlace-cli` **0.1.1** (`v0.1.0`,
`v0.1.1` tags). Workspace version is still **0.1.1**. App crate
`interlace-tauri` is `publish = false`. **`app-v0.1.2` is the last shipped
app** (Apple Silicon `.app.zip` + `.dmg` on
[GitHub Releases](https://github.com/nonamexishere/interlace/releases/tag/app-v0.1.2);
ad-hoc, not notarized). **#267** / PR **#285** wired Developer ID + notarize
for the *next* `app-v*` tag; that tag is **not** cut. Ask before another
`app-v*` / `v*` / crates.io publish.

`master` is **protected**: required checks `check` + `tauri`, strict,
enforce_admins, no force-push, no delete, 0 required reviewers.
Do not flip the repo private without asking.

HEAD when this was rewritten: `def774c` (merge of PR **#345** / #315).
Tag **`app-v0.1.2`** (last shipped; still unsigned).
Epic **#108**, milestone 6, the Phase 1 CLI milestone, Phase 2.2 (#197),
and Phase **2.3** (epic **#264** / milestone 8) are **closed**.
#265–#279 / #297 / #300 / #303–#315 (PRs #282–#301 / #323–#328 / #330 /
#332 / #336 / #338 / #340 / #343 / #345) done.
First notarized `app-v*` is not cut.
Re-check with `git log -1` / `gh pr list`.

Live dogfood archive (`interlace --path ~/Interlace --json status`, counts only):

| Field | Value |
| --- | --- |
| messages | ~41k |
| identities | ~1.7k |
| persons_live | ~2.2k |
| review_open | 1 |
| region / owner | `TR` / Mustafa |
| last import | 2026-08-12 (done) |

Treat counts as approximate; never paste real names or message text here.

### Done — Phase 1 / 2 foundation (do not re-implement)

| # | What |
| --- | --- |
| #1 | Phase 1 epic — closed; CLI 0.1.0 / 0.1.1 published |
| #7 | Living pipeline prompts + `test_plan.json` map |
| #37 | Phase 2 epic — closed (UI0–UI8) |
| #44 | UI7 doctor + backup banner |
| #46 / PR #106 | UI8 unsigned `.app` / `.dmg` |
| #54 | Dogfood wipe + re-import 3 iOS WA ZIPs |
| #83 | Dogfood Takeout Contacts + Gmail |
| #88 / PR #139 | `--version` / `-V` |
| #100 / PR #142 | Later WA re-export unions (not duplicate) |
| #103 / PR #104 | `name_score` token align |
| UI0–UI6 | shell, search, people, review, import, empty states, shadcn, CAS photos |

### Done — Phase 2.1 + review polish (closed on/after 2026-08-11)

| # | What |
| --- | --- |
| #109 / PR #141 | Security-scoped bookmark; `.app` reopens last archive |
| #137 | Honest empty/error when sandbox denies remembered path |
| #110 / PR #145 | People list by last activity + preview |
| #111 / PR #153 | Chat bubbles (me right / them left), text nodes |
| #112 / PR #157 | UTC day headings on person timeline |
| #113 / PR #158 | Timeline opens at latest message |
| #114 / PR #160 | Compact conversation switcher for one person |
| #159 | People sidebar: no horizontal scroll (truncate / clip) |
| #156 | Boot: centered CSS spinner (pre-JS + Opening last archive) |
| #138 | People `/` filter matches linked phone/email identity values |
| #115 | Timeline platform chips + All / platform filter |
| #116 | Timeline kind filter (DMs / email / groups) AND platform |
| #117 | Gmail rows: subject title + fold quoted tails |
| #118 | In-window photo lightbox (local CAS) |
| #119 | Voice-note player chrome (local CAS; play/pause + time) |
| #120 | Virtualize person timeline (visible + overscan rows only) |
| #121 | Search platform closed select (Any / WhatsApp / Gmail / Contacts) |
| #122 | Search conversation-kind select (Any / DM / Group / Email thread) |
| #123 | Search person pick by display name (not numeric id) |
| #124 | Search hit jumps to that message on the person timeline |
| #125 / PR #177 | Search attachment filter (has:media / omitted / missing) |
| #126 / PR #178 | Search highlight tokens without innerHTML of the body |
| #127 / PR #146 | Merge by picking a person (no raw ids) |
| #128 / PR #179 | Review card shows both sides’ identifiers |
| #129 / PR #180 | Window title follows the open person / view |
| #130 / PR #181 | Native macOS menu (Open, Import, View, Quit; no updater) |
| #131 / PR #182 | en+tr chrome locale pack from OS language |
| #132 / PR #183 | Keyboard map ⌘F / Esc / ⌘1–5 (AltGr is not Ctrl) |
| #133 / PR #185 | a11y: people listbox, timeline articles, reduced motion |
| #134 / PR #186 | Drop local ZIP/mbox onto the window (reject URLs) |
| #135 / PR #188 | Copy bubble text; reveal CAS blob in Finder (hash only) |
| #136 / PR #190 | Defer doctor CAS walk until the Doctor tab |
| #170 / PR #192 | Voice-note seek bar (local scrub) |
| #184 / PR #194 | Short people-list time + VoiceOver (`11 Aug 14:32`) |
| #147 / PR #148 | Exact folded Contacts+WA names → review, never auto-merge |
| #149 / PR #150 | Review card: both sides’ samples / counts |
| #151 / PR #152 | Accept can fold every same-name person (n-way pick) |
| #143 / PR #144 | Takeout mbox split on `\nFrom ` (not blank-line-only) |
| #154 / PR #155 | Reviewer must score scope vs the issue |

Phase 2.1 milestone (#6): **closed**.

### Done — Phase 2.2 (started 2026-08-17)

| # | What |
| --- | --- |
| #198 / PR #225 | Design tokens — no raw `amber-*` / `yellow-*` / `black/80` in product Svelte |
| #199 / PR #226 | Typography — 14–15px bodies, 12–13px meta, system font; GitButler/NeoHtop visual refs |
| #200 / PR #228 | Lucide play/pause, lightbox close, empty-state icon |
| #201 / PR #231 | Owned Tooltip, Separator, Badge, Card primitives |
| #202 / PR #233 | EmptyState next action on every major view |
| #203 / PR #235 | Loading skeletons for people, timeline, and search |
| #204 / PR #237 | Recoverable errors + owned toast (copy / Reveal); blocking stay in-page |
| #205 / PR #239 | Partial states — one pane can fail without blanking the shell |
| #206 / PR #241 | Consecutive same-sender, same-conversation, same-UTC-day bubbles share one caption |
| #207 / PR #243 | Timeline hierarchy — identity/time, then body/subject, then attachments |
| #224 / PR #244 | Person timeline: ≤250 filtered rows mount fully; longer lists still window. Measure does not write `scrollTop` |
| #208 / PR #245 | Always-available chrome search field; ⌘F from every view including People focuses `#q` |
| #209 / PR #248 | Search filters secondary (disclosure) + optional `type=date` range; invalid dates do not search. Space/Enter on Filters `<summary>` must not steal hit keys |
| #210 / PR #249 | Search hits: short `humanTime` + person/title, then `splitSnippet` + `<mark>`; no raw ISO dump |
| #211 / PR #250 | Overlay titlebar — native traffic lights, `data-tauri-drag-region` on the top bar, no second Interlace wordmark. `setTitle` still follows view |
| #212 / PR #251 + #252 | People sidebar fixed `w-72`, rail, ⌘\\; follow-up: hover title, `/` on rail, expand-now under 880px, physical Backslash |
| #213 / PR #253 | Optional right inspector — identities + last activity; Merge / include-groups / unlink live there; not a second timeline |
| #214 / PR #254 | People listbox arrows change person; Tab is filter → selected person → timeline; j/k still messages |
| #215 / PR #255 | Command palette (⌘K) — views + jump to a loaded person; local only; people list capped; field keeps A/C/V |
| #216 / PR #256 | Focus rings and ARIA audit on chrome and dialogs |
| #217 / PR #257 | Contrast tokens — light and dark both readable |
| #218 / PR #258 | Appearance follows OS; dark is the intended archival look; named overlay / lightbox tokens; no Theme menu |
| #219 / PR #259 | Status tokens — `--color-warning` / `--color-success` (HSL); cloud + doctor use warning, not destructive; import done is quiet |
| #220 / PR #260 | Import progress — disabled Cancel while running (core has no stop); done stays quiet counts |
| #221 / PR #261 | Review queue chrome — Card + Separator; no raw person ids; Undo last link on the Review pane |
| #222 / PR #262 | Motion — 150–250ms fade/fly/slide on palette, inspector, toast; reduced motion is duration 0 |

### Done — Phase 2.3

| # | What |
| --- | --- |
| #265 / PR #282 | People list off the archive mutex — short lock to clone the root, then `person_list_on` on a read-only snapshot; stale replies discarded. Exclusive flock stays |
| #266 / PR #283 | Cooperative import cancel — Cancel stops the run (`interrupted`); committed rows stay; no thread kill |
| #267 / PR #285 | Developer ID + notarize `app-v*` — fail-closed `APPLE_*`; staple `.app`; `notarytool submit` then staple the DMG. Local `signingIdentity` stays `"-"`. Ask before the first notarized tag |
| #268 / PR #286 | Local-timezone day headings — display follows the Mac timezone; stored `sent_at` / JSON / FTS stay UTC |
| #269 / PR #287 | People sidebar undo chrome — name/op label, same undoable set as Review; skip `split_person` |
| #270 / PR #288 | Search-as-you-type on `#q`; people refresh does not block Search |
| #271 / PR #289 | Video / PDF / sticker CAS in the timeline — local in-window; no autoplay; stickers stay on the image path |
| #272 / PR #290 | Linkify http(s) URLs in timeline bubbles — sibling `<a>` / text; confirm before OS-open |
| #273 / PR #291 | Search from a timeline bubble — open Search with that person (name, not id); hits load |
| #274 / PR #292 | Reveal archive folder in Finder from Doctor / People |
| #275 / PR #293 | First-run one screen — offline / no account, required region, Create + Open; optional owner fields behind More |
| #276 / PR #294 | Local Default / Comfortable density — enlarges bubble bodies without a reload |
| #277 / PR #295 | Leftover chrome readable in system light; named `--chrome-*` vars; dark archival |
| #278 / PR #296 | Review / Import / Doctor chrome in en+tr packs; bodies stay as imported |
| #297 / PR #298 | Researcher role before test-author |
| #279 / PR #299 | Split `gate_tauri.py` asserts into `tauri_gate/` |
| #300 / PR #301 | `tauri_gate` buckets under ~1 200 lines |
| #305 / PR #323 | Reopen on last view and last person (localStorage, not iCloud) |
| #306 / PR #324 | Persist window size and position; off-screen clamped; skip zoomed |
| #303 / PR #325 | User install docs + changelog match unsigned 2.3 (`app-v0.1.2`) |
| #304 / PR #326 | Split product + gate files under 500 (`_SPLIT_MAX_LINES` 500) |
| #307 / PR #327 | File → Recent archives (sibling App Support list, cap 5, drop-on-pick) |
| #308 / PR #328 | File → Switch archive closes to setup; exclusive flock drops without quitting |
| #309 / PR #330 | Remember include-groups locally |
| #310 / PR #332 | Find in this conversation (`#tl-find`, hit count, quoted/URL haystack) |
| #311 / PR #336 | Jump to a sticky day heading from a pane date control |
| #312 / PR #338 | People list Recent | A–Z; choice remembered locally |
| #313 / PR #340 | Latest on a long thread (overlay + End / Fn+→) |
| #314 / PR #343 | Keyboard Load older (⌘↑ / Home at oldest bubble) |
| #315 / PR #345 | ⌘C copies the highlighted bubble’s plain text |

## Open — product now

Phase 2.3 coding is **done** (epic **#264** / milestone 8 closed). Phase 2.2
polish (#197) is **done**. Normative
[`docs/design/UI-DESIGN.md`](../design/UI-DESIGN.md).
Do **not** start Phase 1.1 (#57–#69) or Phase 3/4 (#72–#82). Prefer one
issue → one PR; thin chrome still uses the loop when load-bearing
(a11y, titlebar, search). Skip researcher only when the issue already
names helpers, files, and must-IDs.

### Suggested next

1. **#315** is done (PR **#345**). Next coding **#316** only if asked
   (Space play/pause a focused voice note). Do not invent a new 2.3
   ticket. Remaining parked dogfood UI (**#316–#322**) only if asked.
   **#342** (why Review is quiet; do not auto-merge names) stays
   parked until picked.
2. Do not start 1.1 / P3 / P4. Ask before the first notarized `app-v*` tag.

Phase 2.3 archive: [#264](https://github.com/nonamexishere/interlace/issues/264) / [milestone 8](https://github.com/nonamexishere/interlace/milestone/8).
Phase 2.2 archive: [#197](https://github.com/nonamexishere/interlace/issues/197) / [milestone 7](https://github.com/nonamexishere/interlace/milestone/7).

### Open — parked (not product coding)

| # | Note |
| --- | --- |
| **#17** | Phase 1.1 umbrella — parked; not blocked; do not start children |
| Phase 1.1 / 3 / 4 | Parked. Do not start. |

## Recommended next steps

1. #303–#315 are done (PRs #323–#328, #330, #332, #336, #338, #340,
   #343, #345). Next coding **#316** only if asked. Remaining parked
   dogfood UI (**#316–#322**) only if asked. **#342** stays parked
   until picked.
2. Phase 2.3 coding is done. Do not start 1.1 / P3 / P4.
3. Last shipped app tag is **`app-v0.1.2`** (unsigned). Workflow can
   Developer ID + notarize the next `app-v*` once Apple secrets exist.
   Ask before another `app-v*` / `v*` / crates.io.

## Commands (copy-paste)

```bash
# CLI with this tree (not crates.io 0.1.1)
cargo install --path crates/interlace --locked --force

# status / integrity (Switch archive or close the app first if flock busy)
interlace --path ~/Interlace --json status
interlace --path ~/Interlace doctor --integrity

# wipe + re-import only if Mustafa asks (archive is already post-#54)
# mv ~/Interlace ~/Interlace.bak-$(date +%Y-%m-%d)
# interlace init --path ~/Interlace --phone-region TR --name Mustafa
# for z in ~/Downloads/WhatsApp/*.zip; do
#   interlace --path ~/Interlace import whatsapp "$z"
# done

# desktop UI
cd ~/AllTogether/interlace/interlace/crates/interlace-tauri
npm install
npm run tauri:dev    # NOT bare `npm run tauri` (prints help only)
```

Folder of WA ZIPs: CLI is **one file per** `import whatsapp <FILE>`. The app
Import picker accepts the folder (UI5 fix).

Do **not** `gh pr merge` old PRs. Do **not** `cargo publish` / tag `v*` or
another `app-v*` without asking. `app-v0.1.2` is the last shipped (unsigned) app.

## Review tab

Not a chat view. Queue of “are these two identities the same person?”
Phone/email exact → auto. **Name never auto-merges.** Accept links identity →
person (`review_accepted`); Reject suppresses the pair. Sample lines are
evidence, not the timeline.

`name_score` (PR #104) aligns tokens: leftover tokens on both sides → 0.0;
one-letter typo still ≥ 0.40. Exact folded Contacts FN vs WA name still
**review-only** (#147). N-way Accept can fold every same-name person with a
picker (#151). Tests use placeholders only (`Cemre Yıldız` / `Berk Özdemir`).

## Stack cheatsheet

- Workspace: `interlace`, `interlace-core`, `interlace-cli`, `interlace-cli-common`,
  `interlace-fixtures`, `interlace-tauri`.
- UI: Svelte 5 + Vite 7 + Tailwind 4 + owned shadcn-svelte in
  `crates/interlace-tauri/web/`.
- Dev: `npm run tauri:dev` (Vite HMR + Tauri wrapping cargo).
- CI: `.github/workflows/ci.yml` — `check` (Ubuntu, includes `gate_tests.py`) +
  `tauri` (macOS, `gate_tauri.py`).
- Tauri deny: `crates/interlace-tauri/deny.toml` (darwin graph targets).
- Pipeline prompts: `pipeline/prompts/{orchestrator,researcher,test-author,impl,reviewer}.md`.

## What not to do next

- Do not start Phase 3 (Telegram/iMessage/export) or Phase 4 (pHash/echo/Tantivy).
- Do not put real ZIP filenames, display names, or message text in tickets.
- Do not `cargo publish` / tag without asking.
- Do not require PR reviewers (solo). Reviewer **role** is still required
  (`pipeline/prompts/reviewer.md`); GitHub review-required is not.
- Do not enable `dangerousRemoteDomainIpcAccess`, `network.server`, or an
  HTTP client. Keep `network.client`.
- Do not leave this handoff stale after merges (see **Keep this file current**).

## New session prompt (paste)

> Read `docs/hacking/handoff.md` and `docs/hacking/pipeline.md`. Sequence
> researcher → test-author → impl → reviewer as **separate agents** when
> load-bearing. Skip researcher only when the issue already names helpers,
> files, and must-IDs. After researcher, present each finding and a
> recommended mix; Mustafa may type take X from A, Y from B. Write the
> mix into IN.md before test-author. Do not spawn agents from a child. Orchestrator
> does not implement product code. Ask before commit / push / merge.
> Phase 2.3 coding is done (epic #264 / milestone 8 closed). Read
> `docs/design/UI-DESIGN.md`. Do not invent a new 2.3 ticket. #265–#279,
> #297, #300, #303–#315 done (PRs #323–#328, #330, #332, #336, #338, #340,
> #343, #345). Next coding **#316** only if asked. Parked dogfood
> #316–#322 only if asked. #342 stays parked until picked.
> Do not start 1.1 / P3 / P4.
> Do not dump chat bodies. Ask before crates.io, `v*`, or another `app-v*`
> tag (`app-v0.1.2` is current; first notarized tag is not cut). After
> merges, update this handoff in the same session.
