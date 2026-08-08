# Stage 07 bench

Default 10k msgs; OUT.json p50/p95. No 1M in PR.

Nightly (not this gate):

```
INTERLACE_BENCH=1M cargo bench -p interlace-core --bench search
INTERLACE_BENCH=10M cargo bench -p interlace-core --bench search
```

High-DF `merhaba AND yarın` is recorded with the Spike 1 caveat; it is **not**
folded into the p95_ms that `bench_gate.py` checks.
