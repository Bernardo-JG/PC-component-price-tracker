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
        columns = {r[1] for r in self.conn.execute('PRAGMA table_info(listings)')}
        for name, definition in [('category', "TEXT DEFAULT ''"), ('location', "TEXT DEFAULT ''"),
                                 ('description', "TEXT DEFAULT ''"), ('first_seen_run', 'INTEGER'), ('last_seen_run', 'INTEGER')]:
            if name not in columns:
                self.conn.execute(f'ALTER TABLE listings ADD COLUMN {name} {definition}')
        self.conn.commit()
        # Reclassify observations when recognition rules change; preserve history.
        import matcher
        for row in self.conn.execute("SELECT id,title,description,price FROM listings ").fetchall():
            parsed = matcher.classify(row['title'], row['description'])
            if parsed and not matcher.is_junk(row['title'], row['price']):
                self.conn.execute('UPDATE listings SET category=?,model=?,is_defective=? WHERE id=?', (*parsed,int(matcher.is_defective(row['title'],row['description'])),row['id']))
            else:
                self.conn.execute("UPDATE listings SET category='' WHERE id=?", (row['id'],))
        self.conn.commit()

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

    def upsert_listing(self, l: dict, run_id=None) -> str:
        ts = now()
        old = self.conn.execute("SELECT * FROM listings WHERE site=? AND listing_id=?",
                                (l['site'], l['listing_id'])).fetchone()
        fields = ['title','price','currency','url','model','condition','is_defective',
                  'category','location','description','last_seen','last_seen_run']
        values = [l.get(k, '') for k in fields]
        values[2] = l.get('currency', 'EUR')
        values[6] = int(l.get('is_defective', False))
        values[-2:] = [ts, run_id]
        if old is None:
            names = ['site','listing_id','first_seen','first_seen_run'] + fields
            args = [l['site'], l['listing_id'], ts, run_id] + values
            cur = self.conn.execute('INSERT INTO listings (' + ','.join(names) + ') VALUES (' + ','.join('?' for _ in names) + ')', args)
            pk = cur.lastrowid
            status = 'new'
        else:
            pk = old['id']
            self.conn.execute('UPDATE listings SET ' + ','.join(k+'=?' for k in fields) + ' WHERE id=?', values+[pk])
            status = 'changed' if old['price'] != l['price'] else 'unchanged'
        if status != 'unchanged':
            self.conn.execute('INSERT INTO price_history (listing_pk,price,seen_at) VALUES (?,?,?)', (pk,l['price'],ts))
        self.conn.commit()
        return status

    def active_listings(self):
        # "Observed recently" is not an availability or sold-status claim.
        start = (datetime.now()-timedelta(days=config.STATS_WINDOW_DAYS)).isoformat()
        return [dict(r) for r in self.conn.execute(
            """SELECT l.*, (SELECT h.price FROM price_history h WHERE h.listing_pk=l.id
                ORDER BY h.id DESC LIMIT 1 OFFSET 1) AS previous_price
                FROM listings l WHERE site='olx' AND last_seen>=?
                AND category IN ('GPU','CPU','RAM') ORDER BY model,price""", (start,))]

    def model_stats(self):
        buckets = {}
        for item in self.active_listings():
            if not item['is_defective']:
                buckets.setdefault((item['model'],item['condition']), []).append(item['price'])
        return {key:dict(median=statistics.median(prices) if len(prices)>=config.MIN_SAMPLES_FOR_STATS else None,
                         count=len(prices)) for key,prices in buckets.items()}

    def find_deals(self):
        stats = self.model_stats()
        deals = []
        for item in self.active_listings():
            med = stats.get((item['model'],item['condition']),{}).get('median')
            if med and not item['is_defective'] and item['price']<=config.DEAL_THRESHOLD*med:
                deals.append(dict(item,median_used=med,discount_pct=round(100*(1-item['price']/med))))
        return sorted(deals,key=lambda d:-d['discount_pct'])

    def last_run(self):
        row = self.conn.execute('SELECT * FROM runs ORDER BY id DESC LIMIT 1').fetchone()
        return dict(row) if row else None
