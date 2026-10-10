# data-gen-speedup

A small, self-contained demo of profiling and speeding up a naive data-generation
pipeline: fetch 3 inputs per config from an API, compute a speed curve, write every
point to a database.

## Results

| | time | vs. baseline |
|---|---|---|
| `slowdatagen.py` (baseline) | 13.4 s | — |
| `fastdatagen.py` (full regenerate) | 1.2 s | ~11x |
| `fastdatagen.py --incremental` (nothing changed) | 0.2 s | ~67x |

Verified row-for-row identical between the two outputs (`verify.py`, 1e-6 tolerance).
Demo scale: 5 configs, 20 points/config (100 rows), 50 ms simulated API latency.

Profiling the baseline first showed that SQLite's per-row `commit()` was 80% of the
runtime — not the network (7%) or the per-point computation (8%). The optimizations
below target that in order of actual measured impact, not assumed impact.

## Files

- `mock_server.py` — local stand-in API (`GET /param1|param2|param3/<config_id>`),
  with a small simulated per-request delay so the demo behaves like a real upstream
  service without needing one.
- `common.py` — shared DB helpers and both curve implementations (naive loop vs.
  vectorised NumPy).
- `slowdatagen.py` — the naive baseline: serial requests, commit after every row,
  per-point Python loop.
- `fastdatagen.py` — the optimised version:
  1. Concurrent API calls via a capped thread pool.
  2. One shared `requests.Session` per thread (connection reuse).
  3. Retries with backoff for transient errors.
  4. All rows written with `executemany()` inside a single transaction.
  5. Maths vectorised with NumPy.
  6. `--incremental`: skip configs whose inputs haven't changed (SHA-256 hash cache).
- `verify.py` — compares `slow.db` and `fast.db` row by row to prove the optimised
  path produces the same data, not just faster output.

## Usage

```bash
# terminal 1
python mock_server.py

# terminal 2
python slowdatagen.py          # baseline -> slow.db
python fastdatagen.py          # optimised -> fast.db
python fastdatagen.py --incremental   # re-run, nothing changed -> near-instant
python verify.py               # confirm slow.db and fast.db match
```

## Why

Written to demonstrate a profile-first approach to speeding up slow pipelines:
measure where time actually goes before optimizing, fix the biggest measured cost
first, and prove the faster version produces identical output rather than just
trusting it.
