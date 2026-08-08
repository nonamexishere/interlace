# Security policy

Interlace stores the user's private correspondence on disk, unencrypted at rest
in Phase 1 or Phase 2 (no SQLCipher; do not claim encryption).

## Supported versions

| Version | Supported |
| --- | --- |
| 0.0.1 name-squat | no (hello-world / workspace) |
| 0.1.x (first real CLI) | yes |
| git `master` | best effort |

## What to report

Please report privately (GitHub Security Advisory on `nonamexishere/interlace`):

- Zip-slip / path traversal in ZIP/Takeout import
- SQLite corruption via malicious mbox/chat lines
- FTS `MATCH` injection that executes unintended SQL
- Ability of the binary to open a network socket / ship an HTTP client
- Lock bypass allowing concurrent writers
- Identity auto-merge that fires on name-only evidence (product + security)

## What not to report as a vuln

- “I merged the wrong people” after accepting a review item — use `person undo`
- WhatsApp native export truncating history (~40k) — platform limit
- World-readable archive after the user `chmod 777` — `open` warns; not a remote vuln

## Threat model (summary)

Single-user local archive. Assume a malicious export file. Assume local malware
can read the folder if modes allow. We mitigate zip-slip, zip-bombs (D23 caps),
FTS lexer escaping, exclusive flock, mode 0700 on init. We do **not** mitigate
a root user reading `~/Interlace`.

## Disclosure

90 days unless a fix ships earlier. No bounty program in Phase 1.
