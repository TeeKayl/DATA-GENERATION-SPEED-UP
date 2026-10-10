import sqlite3
import time

import numpy as np

API = "http://127.0.0.1:8765"

_CONFIG_IDS = list(range(1, 6))


def config_ids():
    """Config ids to generate speed curves for."""
    return _CONFIG_IDS


def open_db(db_path, fresh=False):
    """Open (creating if needed) the sqlite db holding speed_curves.

    fresh=True drops any existing speed_curves table first, giving a
    clean slate. fresh=False (default, what slowdatagen.py uses) just
    ensures the table exists, leaving existing rows alone.
    """
    conn = sqlite3.connect(db_path)
    if fresh:
        conn.execute("DROP TABLE IF EXISTS speed_curves")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS speed_curves (
            config_id INTEGER NOT NULL,
            t REAL NOT NULL,
            v REAL NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def add_index(conn):
    """Index speed_curves by config_id for faster lookups."""
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_speed_curves_config_id ON speed_curves(config_id)"
    )
    conn.commit()


def compute_speed_curve_slow(param1, param2, param3, n_points=20):
    """Deliberately naive/slow curve computation.

    Combines the three fetched params into a simple speed curve,
    yielding (t, v) points one at a time with a small artificial delay
    per point to stand in for an unoptimized calculation.
    """
    v1 = param1["value"]
    v2 = param2["value"]
    v3 = param3["value"]
    for i in range(n_points):
        time.sleep(0.01)  # simulate slow per-point computation
        t = i / n_points
        v = v1 * t + v2 * (t ** 2) + v3
        yield (t, v)


def compute_speed_curve_fast(param1, param2, param3, n_points=20):
    """Vectorised equivalent of compute_speed_curve_slow.

    Same formula (v = v1*t + v2*t^2 + v3, t = i/n_points), computed as
    whole-array NumPy ops instead of a Python loop with a sleep per
    point, so the fast and slow paths produce identical numbers.
    Returns (t, v) as 1-D numpy arrays rather than yielding pairs.
    """
    v1 = param1["value"]
    v2 = param2["value"]
    v3 = param3["value"]
    t = np.linspace(0, 1, n_points, endpoint=False)
    v = v1 * t + v2 * (t ** 2) + v3
    return t, v
