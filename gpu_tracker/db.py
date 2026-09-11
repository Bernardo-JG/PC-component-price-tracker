"""SQLite storage for listings + price statistics."""

import sqlite3
import statistics
from datetime import datetime, timedelta

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site TEXT NOT NULL,
    listing_id TEXT NOT NULL,
    title TEXT NOT NULL,
    price REAL NOT NULL,
    currency TEXT DEFAULT 'EUR',
    url TEXT,
    model TEXT NOT NULL,
    condition TEXT NOT NULL,            -- 'used' | 'new'
    is_defective INTEGER DEFAULT 0,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    UNIQUE (site, listing_id)
);
CREATE INDEX IF NOT EXISTS idx_model ON listings(model);
CREATE INDEX IF NOT EXISTS idx_seen ON listings(last_seen);

CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_pk INTEGER NOT NULL REFERENCES listings(id),
    price REAL NOT NULL,
    seen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    new_listings INTEGER DEFAULT 0,
    updated_listings INTEGER DEFAULT 0,
    notes TEXT
);
"""


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Database:
    def __init__(self, path: str = config.DB_PATH):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    # -- writes -------------------------------------------------------------

    def start_run(self) -> int:
        cur = self.conn.execute(
            "INSERT INTO runs (started_at) VALUES (?)", (now(),))
        self.conn.commit()
        return cur.lastrowid

    def finish_run(self, run_id: int, new: int, updated: int, notes: str = ""):
        self.conn.execute(
            "UPDATE runs SET finished_at=?, new_listings=?, updated_listings=?, notes=? WHERE id=?",
            (now(), new, updated, notes, run_id))
        self.conn.commit()

    def upsert_listing(self, l: dict) -> str:
        """Insert or refresh a listing. Returns 'new' | 'updated'."""
        ts = now()
        row = self.conn.execute(
            "SELECT id, price FROM listings WHERE site=? AND listing_id=?",
            (l["site"], l["listing_id"])).fetchone()
        if row is None:
            cur = self.conn.execute(
                """INSERT INTO listings
                   (site, listing_id, title, price, currency, url, model,
                    condition, is_defective, first_seen, last_seen)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (l["site"], l["listing_id"], l["title"], l["price"],
                 l.get("currency", "EUR"), l.get("url"), l["model"],
                 l["condition"], int(l.get("is_defective", False)), ts, ts))
            self.conn.execute(
                "INSERT INTO price_history (listing_pk, price, seen_at) VALUES (?,?,?)",
                (cur.lastrowid, l["price"], ts))
            self.conn.commit()
            return "new"
        else:
            self.conn.execute(
                "UPDATE listings SET last_seen=?, price=?, title=? WHERE id=?",
                (ts, l["price"], l["title"], row["id"]))
            if abs(row["price"] - l["price"]) > 0.01:
                self.conn.execute(
                    "INSERT INTO price_history (listing_pk, price, seen_at) VALUES (?,?,?)",
                    (row["id"], l["price"], ts))
            self.conn.commit()
            return "updated"

    # -- reads --------------------------------------------------------------

    def _window_start(self) -> str:
        return (datetime.now()
                - timedelta(days=config.STATS_WINDOW_DAYS)).isoformat()

    def model_stats(self) -> dict:
        """Per-model stats over the rolling window.

        Returns {model: {median_used, mean_used, n_used, min_new, n_new}}.
        """
        start = self._window_start()
        stats: dict = {}
        rows = self.conn.execute(
            """SELECT model, price, condition, is_defective
               FROM listings WHERE last_seen >= ?""", (start,)).fetchall()
        buckets: dict = {}
        for r in rows:
            b = buckets.setdefault(r["model"], {"used": [], "new": []})
            if r["condition"] == "new":
                b["new"].append(r["price"])
            elif not r["is_defective"]:
                b["used"].append(r["price"])
        for model, b in buckets.items():
            used, new = b["used"], b["new"]
            stats[model] = {
                "median_used": statistics.median(used) if len(used) >= config.MIN_SAMPLES_FOR_STATS else None,
                "mean_used": statistics.fmean(used) if used else None,
                "n_used": len(used),
                "min_new": min(new) if new else None,
                "n_new": len(new),
            }
        return stats

    def active_listings(self) -> list:
        start = self._window_start()
        return [dict(r) for r in self.conn.execute(
            """SELECT * FROM listings WHERE last_seen >= ?
               ORDER BY model, price""", (start,)).fetchall()]

    def find_deals(self) -> list:
        """Used, non-defective listings priced below threshold * median."""
        stats = self.model_stats()
        deals = []
        for l in self.active_listings():
            if l["condition"] != "used" or l["is_defective"]:
                continue
            s = stats.get(l["model"])
            if not s or s["median_used"] is None:
                continue
            if l["price"] <= config.DEAL_THRESHOLD * s["median_used"]:
                l["median_used"] = s["median_used"]
                l["discount_pct"] = round(
                    100 * (1 - l["price"] / s["median_used"]))
                deals.append(l)
        deals.sort(key=lambda d: -d["discount_pct"])
        return deals

    def repair_candidates(self) -> list:
        import matcher
        out = []
        for l in self.active_listings():
            if l["is_defective"] and matcher.is_repair_candidate(l["model"], True):
                out.append(l)
        out.sort(key=lambda d: d["price"])
        return out

    def last_run(self):
        r = self.conn.execute(
            "SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()
        return dict(r) if r else None
