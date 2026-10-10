import time
import requests
from common import API, config_ids, open_db, add_index, compute_speed_curve_slow

def main(db_path="slow.db"):
    start = time.perf_counter()
    conn = open_db(db_path)
    cur = conn.cursor()
    for cid in config_ids():
        param1 = requests.get(f"{API}/param1/{cid}").json()
        param2 = requests.get(f"{API}/param2/{cid}").json()
        param3 = requests.get(f"{API}/param3/{cid}").json()
        for t,v in compute_speed_curve_slow(param1, param2, param3):
            cur.execute("INSERT INTO speed_curves VALUES (?, ?, ?)", (cid, t, v))
            conn.commit()
        add_index(conn)
    conn.close()
    elapsed = time.perf_counter() - start
    print(f"slow data gen: {elapsed:.1f} s")
    return elapsed

if __name__ == "__main__":
    main()
        