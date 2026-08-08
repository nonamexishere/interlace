# Spike 2 — WhatsApp locale / header coverage

**Date:** 2026-08-08  
**No real user chats.** Public parser metadata + invented golden lines only.

## Sources (license recorded)

| Source | License | What we used |
| --- | --- | --- |
| [whatstk](https://github.com/lucasrodes/whatstk) `header_format_support.json` (96 formats) | **GPL-3.0** | Format **strings only** as a census. Do **not** copy whatstk code into Interlace (GPL). |
| [chat-miner](https://github.com/joweich/chat-miner) `WhatsAppParser` | **MIT** | Header-detect regex + U+200E strip + “one format per file” inference. |
| Reddit report on German `01.04.26` + `Datei angehängt` | public post | Confirms dotted DE dates + attached suffix. https://www.reddit.com/r/whatsapp/comments/1r1a969 |

whatstk chat fixtures (`lorem.txt` etc.) were listed via GitHub API but **not copied** (GPL corpus).

## Census

whatstk documents **96** header format strings: permutations of

- date order `%y-%m-%d` / `%d-%m-%y` / `%m-%d-%y`
- separators `-` `/` `.`
- 12h `%I:%M %p` vs 24h `%H:%M` and optional seconds
- Android dash (` - %name:`) vs iOS brackets (`[%date] %name:`)

chat-miner uses one regex family:

```
^[\u200e]?\[?(\d{1,4})([./,-])\d{1,2}\2\d{2,4}(?:\s|,\s)(0?\d|1\d|2[0-4]):([0-5]?\d)
```

then infers day-first / year-first / bracket vs dash from the file. Mixed 12h/24h in one file is not voted mid-file.

## Invented golden lines (MIT/Apache-safe; not copied from GPL chats)

```
[2024-03-15, 14:32:18] John Doe: Hello
[3/15/24, 2:32:18 PM] John Doe: Hello
[15.03.2024, 14:32:18] John Doe: Hello
[15.03.2024 14:32:18] John Doe: Merhaba
3/15/24, 2:32 PM - John Doe: Hello
15/03/2024, 14:32 - John Doe: Hello
15.03.2024 14:32 - John Doe: Merhaba
15.03.2024, 14:32 - John: x
01.04.26, 09:15 - Anna: Datei angehängt
[15/03/2024, 14:32:18] ‎You: Hi
```

These match DESIGN.md locale families for en-US, en-GB, tr-TR, de-DE, pt-BR plus the chat-miner detector. `Yo`/`Vous` lines are **not** added (OQ2 decided).

## Coverage vs five Interlace packs

| Family | Covered by a shipped pack? |
| --- | --- |
| iOS bracket ISO / US / EU / TR | yes (en-*, tr-TR) |
| Android dash US / EU / TR / DE dotted | yes |
| AM/PM | en-US / en-GB |
| U+200E on sender | strip in parser (not locale-specific) |
| `%y-%d-%m` (year-day-month, rare) | **not** a named pack; chat-miner-style infer can still parse if we keep a generic detector |
| mixed 12h and 24h in one file | **unsupported** — abort, require `--locale` |

## Decision

- Keep **five** locale TOML packs as product locales (You tokens + media strings).
- Implement header detection as **chat-miner-like generic regex + per-file inference**, not 96 separate packs.
- If the first-50-line vote ties or 12h/24h mix → `--locale` mandatory (DESIGN fail path).
- ≥95% of the 96 whatstk **format strings** are generable by that regex; remaining odd orders (`%y-%d-%m`) go to unknown_row unless `--locale` forces day/month.

**Do not vendor GPL whatstk code.** Reimplement detector under MIT OR Apache-2.0.

## Verdict

**pass = true.** `blocked = false.`  
Caveat: year-day-month and mixed AM/PM files are explicit unsupported → warning / `--locale`.
