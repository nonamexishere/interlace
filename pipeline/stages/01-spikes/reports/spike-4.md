# Spike 4 — Takeout multi-part layout

**Date:** 2026-08-08  
**No real user Takeout dumps.**

## Question

Are Takeout splits independent zips, spanned `.zip`+`.z01`, or same-basename mbox fragments to concatenate?

## Public evidence (URLs)

- Google Drive Community, 2025-02-07: multi zip extract each `Takeout/` tree then merge directories  
  https://support.google.com/drive/thread/323504938/best-way-to-reorganize-google-drive-files-from-multiple-takeout-zip-files?hl=en
- Takeout UI lets users pick ZIP chunk size 1/2/4/10/50 GB (independent archives, not PKWare spanned sets)  
  https://www.recoverytools.com/blog/how-to-open-google-takeout-files-step-by-step/
- User reports of `takeout-001.zip`, `takeout-002.zip` as separate download buttons (not `.z01`)  
  https://discussions.apple.com/thread/252397751  
  https://www.reddit.com/r/google/comments/3v5cyj/google_takeout_archives_downloading_all_the_zip/
- How-to videos: extract each zip’s `Takeout/` folder into one merged tree  
  https://www.youtube.com/watch?v=-use8DXiKfs (Mac)

No public doc found that Takeout emits PKWare spanned `.zip`+`.z01` for Mail. That layout still appears in other tools; probe must fatal it.

## Synthetic probe (this spike)

Three layouts under `/tmp/il-spike4` (not committed):

| Layout | Contents | Probe result |
| --- | --- | --- |
| 1 disjoint | `001.zip` → Mail mbox; `002.zip` → Contacts vcf | **ok_merge_listing** — import both paths |
| 2 same path | both zips contain `Takeout/Mail/All mail Including Spam and Trash.mbox` | **fatal** — extract and merge dirs |
| 3 spanned | `archive.zip` + `archive.z01` | **fatal** — spanned not supported |

## Decision (updates M5)

**Supported Phase 1 paths:**

1. A single extracted `Takeout/` directory (documented happy path).
2. One or more **independent** `.zip` files whose `Takeout/**` entry names are **disjoint** — open each zip, import listed entries; do not concatenate zip bytes.

**Fatal probe (never silent):**

- Any sibling `*.z01` / `*.z02` (spanned).
- Same logical `Takeout/...` path in more than one zip (including split mbox with identical basename). User must extract-and-merge, then `import takeout <dir>`.

Do **not** concatenate same-path mbox fragments. Safer than guessing Google’s split rule; matches official “extract all parts into one tree” guidance.

M5 (Phase 1.1) = layout 1 (disjoint independent zips) must succeed. Same-path multi-zip remains fatal + message (not a concat fixture).

## Verdict

**pass = true.** `blocked = false.`
