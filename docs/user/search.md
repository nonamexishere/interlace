# Search

Interlace search is **local FTS5** over imported messages. There is no cloud
index.

```bash
interlace search "fatura" \
  --person 42 \
  --from 2019-01-01 --to 2021-01-01 \
  --platform whatsapp \
  --include-groups \
  --limit 50 \
  --json
```

## Query syntax

SQLite FTS5 `MATCH` with a thin expander in front:

- Bare tokens are rewritten to `(token OR turkish_fold OR unicode_lower)`.
- `AND` / `OR` / `NOT` / `NEAR` pass through.
- `"quoted phrases"` are folded as a unit, not expanded into OR.
- Prefix: `fat*` (prefix index `2 3`).
- **No Turkish stemmer.** `gidiyorum` does not match `gitmek`.
- Unknown punctuation is stripped from bare tokens (FTS lexer otherwise errors).

Display text always comes from `messages.body_text`, never from the folded
`search_text` column. Snippets use FTS `snippet(…, '«', '»', '…', 12)`.
Search hits show a short time + person or conversation title, then a
highlighted snippet — not a raw ISO dump.

## Filters

| Flag | Column |
| --- | --- |
| `--from` / `--to` | `search_doc.sent_at` (RFC3339) |
| `--platform` | `whatsapp` / `gmail` / `contacts` |
| `--kind` | `dm` / `group` / `email_thread` (group still needs `--include-groups`) |
| `--attachment` | `has_file` / `omitted` / `missing` (message has ≥1 matching attachment row) |
| `--conversation` | `conversation_id` |
| `--limit` | default 50, max 200 |

In the desktop Search pane the query is the primary control. Filters are
secondary (person, platform, kind, attachment, date range, include groups)
under a Filters disclosure. The date range is optional (empty = any).
Invalid dates do not search.

### Attachment presence

Closed filter (UI select or CLI `--attachment`), not free-text FTS tokens and
not MIME-type taxonomy:

| Value | SQL (message has ≥1 row) |
| --- | --- |
| *(empty / any)* | no attachment predicate |
| `has_file` | `attachments.cas_hash IS NOT NULL` (stored CAS blob) |
| `omitted` | `attachments.omitted != 0` |
| `missing` | `attachments.missing != 0` |

## `--person` and `--include-groups` (D18)

`--person` is **not** sender-only. A hit counts if the person is the sender **or**
is a participant of a `dm` / `email_thread`. Groups stay out unless you pass
`--include-groups`.

The same predicate is used by `person_timeline` (no FTS, ordered by `sent_at`).

## Ranking

`bm25(messages_fts)` then `sent_at DESC`. Dual-fold stores most tokens twice, so
absolute BM25 is inflated; compare scores only inside this corpus.

## Turkish I/ı

Index-time `search_text` is dual-fold:

1. **Turkish fold:** `İ→i`, `I→ı`, then lower → `ISLAK` becomes `ıslak`,
   `İstanbul` becomes `istanbul`.
2. **ASCII fold:** plain Unicode lower (`I→i`) so query `islak` still hits
   `ISLAK`.

Tokenizer is `unicode61 remove_diacritics 2` (helps `İstanbul ≈ istanbul`; does
**not** fix dotless I by itself).

Must-pass: **S1** `istanbul` → `İstanbul`; **S2** `ıslak` → `ISLAK`; **S3**
`islak` → `ISLAK`.

## JSON redaction

`--json` redacts `body_text` / snippets unless `--verbose`. Hits still include
ids, timestamps, conversation id, and score.

## Performance

Target: **warm p95 < 200 ms** on 1–2 term product queries, LIMIT 50 (Spike 1:
~50–100 ms at 1 M / 10 M on this machine class). Cold start after reboot with a
multi-GB DB may exceed 200 ms on the first mmap fault-in; benches warm up first.

PR CI uses a **10k** fixture proxy (S4): `cargo bench -p interlace-core --bench search`
then `gate_bench.py` (p95 ≤ 50 ms). 1 M / 10 M benches are **nightly**, not PR:

```bash
INTERLACE_BENCH=1M cargo bench -p interlace-core --bench search
INTERLACE_BENCH=10M cargo bench -p interlace-core --bench search
```

Nightly fails if 1M p95 > 200 ms after 3 warmups. High-DF `merhaba AND yarın` is
recorded with the Spike 1 caveat (almost every TR doc can match) and is **not**
part of the gated p95. Adversarial `NOT` / huge `OR` / unanchored `*` are not
the gate.

Triggers stay installed (D17). Import bulk-inserts `search_doc` then
`messages_fts … 'rebuild'`. `doctor --rebuild-fts` rebuilds without DROP.
