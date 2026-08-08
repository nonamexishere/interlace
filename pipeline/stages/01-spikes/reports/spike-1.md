# Spike 1 — FTS5 Turkish + 200 ms @ scale

**Date:** 2026-08-08  
**Engine:** macOS system `sqlite3` FTS5 `unicode61 remove_diacritics 2` `prefix='2 3'`  
**Throwaway DB:** `/tmp/il-spike1/archive10m.sqlite` (not in repo)

## Method

Index-time `search_text` = `turkish_fold(subject+body)` + extra `body.lower()` (English `I→i`).  
`turkish_fold`: `İ→i`, `I→ı`, then lower. External-content FTS, rebuild after bulk insert. Planted ids 1–4. Vocab ~415 tokens/language so term DF is not pathological (1M dense-10-word run was only a warmup).

Warmup: 3 queries discarded; p50/p95 over next 5.

## 1 M warmup (dense 10-word vocab)

- insert 4.6 s, FTS rebuild 5.4 s, DB ~276 MB  
- S1/S2/S3 recall **100%**  
- Selective terms p95 ~0.02 ms  
- `merhaba AND yarın` p95 **~293 ms** (almost every TR doc matches) — discarded as corpus artifact

## 10 M (DESIGN target)

| Metric | Value |
| --- | --- |
| Rows | 10_000_000 |
| Insert | 42.3 s |
| FTS rebuild | 67.5 s |
| `archive.sqlite` | **2416 MB** (~2.4 GB; search_doc + FTS only, no message bodies table) |

| Query | p50 ms | p95 ms | Notes |
| --- | --- | --- | --- |
| `istanbul` | 0.058 | 0.060 | planted S1 |
| `ıslak` | 0.066 | 0.104 | planted S2 |
| `islak` | 0.057 | 0.058 | planted S3 (ascii fold) |
| `yılmaz` | 0.057 | 0.057 | planted |
| `merhaba AND yarın` | 37.8 | 38.0 | under 200 ms with larger vocab |
| `meh*` | 0.054 | 0.054 | prefix |
| `w0123` (high DF) | 698 | **705** | common synthetic token; rank+limit 50 |

Recall: **S1, S2, S3 all true** (planted row in top 50).

## Verdict

**pass = true** for the DESIGN product query set (names/places, AND of common-but-not-stop TR words, prefix) **and** Turkish I/ı recall.

**blocked = false** (fail-open anyway).

## Caveats

1. High document-frequency unigrams + `ORDER BY rank LIMIT 50` can miss 200 ms (~700 ms observed). Product should keep queries selective; nightly bench must include a high-DF case.
2. `person+date` join not measured (no `messages` / identity tables in this throwaway).
3. Host SQLite, not `rusqlite` bundled. Re-measure in PR9 / nightly with the real crate.
4. Dual-fold copies inflate index (2.4 GB for 10 M short docs). Recalc storage when full `messages` rows exist.
5. No custom tokenizer needed for S1–S3 on this corpus.

Phase 1 ships unicode61 + dual fold. Custom FTS5 tokenizer stays Phase 2 **only if** dogfood high-DF + person join misses 200 ms.
