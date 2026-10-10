"""AFTER: the optimised data generator.

Fixes, in order of impact (found by profiling the slow path):
  1. Concurrent API calls with a thread pool, capped so we don't overload the API.
  2. One shared requests.Session per thread, so connections are reused.
  3. Retries with backoff for transient network errors.
  4. All rows written with executemany() inside a single transaction.
  5. Maths vectorised with NumPy.
  6. --incremental: only regenerate configs whose inputs changed (hash cache).
"""
import argparse
import hashlib
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from common import API, config_ids, open_db, add_index, compute_speed_curve_fast

MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "30"))
CACHE_FILE = "input_hashes.json"
_local = threading.local()


def session():
    if not hasattr(_local, "s"):
        s = requests.Session()
        retry = Retry(total=3,
                       backoff_factor=0.5,
                       status_forcelist=[500, 502, 503, 504])
        s.mount("http://",
                 HTTPAdapter(max_retries=retry,
                            pool_maxsize=MAX_WORKERS))
        _local.s = s
    return _local.s


def fetch_inputs(cid):
    s = session()
    data = {}
    for kind in ("param1", "param2", "param3"):
        r = s.get(f"{API}/{kind}/{cid}", timeout=10)
        r.raise_for_status()
        data[kind] = r.json()
    return cid, data


def input_hash(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def main(db_path="fast.db", incremental=False):
    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        inputs = dict(pool.map(fetch_inputs, config_ids()))
    t_fetch = time.perf_counter() - start

    old_hashes = {}
    if incremental and os.path.exists(CACHE_FILE) and os.path.exists(db_path):
        with open(CACHE_FILE) as f:
            old_hashes = json.load(f)
    new_hashes = {str(cid): input_hash(d) for cid, d in inputs.items()}
    changed = [cid for cid in inputs if old_hashes.get(str(cid)) != new_hashes[str(cid)]]

    rows = []
    for cid in changed:
        d = inputs[cid]
        t, v = compute_speed_curve_fast(d["param1"], d["param2"], d["param3"])
        rows.extend(zip([cid] * len(t), t.tolist(), v.tolist()))
    t_compute = time.perf_counter() - start - t_fetch

    conn = open_db(db_path, fresh=not (incremental and old_hashes))
    with conn:
        if old_hashes and changed:
            conn.executemany("DELETE FROM speed_curves WHERE config_id = ?",
                              [(c,) for c in changed])
        conn.executemany("INSERT INTO speed_curves VALUES (?, ?, ?)",
                          rows)
    add_index(conn)
    conn.close()
    with open(CACHE_FILE, "w") as f:
        json.dump(new_hashes, f)

    elapsed = time.perf_counter() - start
    print(f"fast_generate: {elapsed:.1f} s  (fetch {t_fetch:.1f} s, compute {t_compute:.2f} s, "
          f"db {elapsed - t_fetch - t_compute:.2f} s, regenerated {len(changed)}/{len(inputs)} configs)")
    return elapsed


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--incremental", action="store_true", help="only regenerate changed configs")
    main(incremental=p.parse_args().incremental)
