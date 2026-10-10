"""Verify that slowdatagen.py and fastdatagen.py produce the same data.

Compares every (config_id, t, v) row between the two databases. t and v
are compared with a small tolerance since float sums done in a different
order (per-point loop vs vectorised NumPy) can differ in the last
decimal places even when the underlying maths is identical.
"""
import argparse
import sqlite3
import sys

TOLERANCE = 1e-6


def load_rows(db_path):
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT config_id, t, v FROM speed_curves ORDER BY config_id, t"
    ).fetchall()
    conn.close()
    return rows


def main(slow_path="slow.db", fast_path="fast.db"):
    slow_rows = load_rows(slow_path)
    fast_rows = load_rows(fast_path)

    if len(slow_rows) != len(fast_rows):
        print(f"MISMATCH: {slow_path} has {len(slow_rows)} rows, {fast_path} has {len(fast_rows)} rows")
        return False

    mismatches = []
    for i, ((s_cid, s_t, s_v), (f_cid, f_t, f_v)) in enumerate(zip(slow_rows, fast_rows)):
        if s_cid != f_cid or abs(s_t - f_t) > TOLERANCE or abs(s_v - f_v) > TOLERANCE:
            mismatches.append((i, (s_cid, s_t, s_v), (f_cid, f_t, f_v)))

    if mismatches:
        print(f"MISMATCH: {len(mismatches)}/{len(slow_rows)} rows differ (tolerance {TOLERANCE})")
        for i, slow_row, fast_row in mismatches[:10]:
            print(f"  row {i}: slow={slow_row}  fast={fast_row}")
        return False

    print(f"OK: {len(slow_rows)} rows match between {slow_path} and {fast_path} (tolerance {TOLERANCE})")
    return True


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--slow", default="slow.db")
    p.add_argument("--fast", default="fast.db")
    args = p.parse_args()
    ok = main(args.slow, args.fast)
    sys.exit(0 if ok else 1)
