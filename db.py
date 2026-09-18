"""SQLite storage for listings + price statistics."""

import sqlite3
import statistics
import json
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
                                 ('description', "TEXT DEFAULT ''"), ('images_json', "TEXT DEFAULT '[]'"),
                                 ('classification_json', 'TEXT'), ('comparison_key', 'TEXT'),
                                 ('comparison_eligible', 'INTEGER DEFAULT 0'), ('exclusion_reason', "TEXT DEFAULT 'not_classified'"), ('first_seen_run', 'INTEGER'), ('last_seen_run', 'INTEGER')]:
            if name not in columns:
                self.conn.execute(f'ALTER TABLE listings ADD COLUMN {name} {definition}')
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
        l = dict(l)
        classification = l.get('classification')
        comparison = {}
        if classification:
            # Revalidate at the storage boundary instead of trusting a caller's eligible flag.
            from classification import comparison as eligibility, guards
            from classification.schema import SCHEMA, decode
            try:
                core = {k: classification[k] for k in SCHEMA['required']}
                verified = decode(json.dumps(core), l, allow_images=True)
                if not classification.get('error'):
                    comparison = eligibility(verified, l, guards(l))
                l['category'] = verified['category'] or ''
                l['model'] = verified['model'] or 'Unknown'
                l['is_defective'] = verified['functional_condition'] == 'defective' or guards(l) == 'defective'
            except (ValueError, KeyError, TypeError):
                comparison = {'eligible': False, 'exclusion_reason': 'invalid_stored_classification', 'key': None}
            if not comparison:
                comparison = {'eligible': False, 'exclusion_reason': 'classification_error', 'key': None}
            classification = dict(classification, comparison=comparison)
        l['images_json'] = json.dumps(l.get('images', []))
        l['classification_json'] = json.dumps(classification, ensure_ascii=False) if classification else None
        l['comparison_key'] = comparison.get('key')
        l['comparison_eligible'] = int(comparison.get('eligible') is True and bool(comparison.get('key')) and not classification.get('error')) if classification else 0
        l['exclusion_reason'] = comparison.get('exclusion_reason') or (None if l['comparison_eligible'] else 'not_classified')
        old = self.conn.execute("SELECT * FROM listings WHERE site=? AND listing_id=?",
                                (l['site'], l['listing_id'])).fetchone()
        fields = ['title','price','currency','url','model','condition','is_defective',
                  'category','location','description','images_json','classification_json','comparison_key',
                  'comparison_eligible','exclusion_reason','last_seen','last_seen_run']
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
                FROM listings l WHERE site IN ('olx','vinted') AND last_seen>=? ORDER BY model,price""", (start,))]

    def model_stats(self):
        buckets = {}
        for item in self.active_listings():
            if item['comparison_eligible'] and not item['is_defective']:
                buckets.setdefault(item['comparison_key'], []).append(item['price'])
        return {key:dict(median=statistics.median(prices) if len(prices)>=config.MIN_SAMPLES_FOR_STATS else None,
                         count=len(prices)) for key,prices in buckets.items()}

    def find_deals(self):
        stats = self.model_stats()
        deals = []
        for item in self.active_listings():
            med = stats.get(item['comparison_key'],{}).get('median')
            if med and item['comparison_eligible'] and not item['is_defective'] and item['price']<=config.DEAL_THRESHOLD*med:
                deals.append(dict(item,median_used=med,discount_pct=round(100*(1-item['price']/med))))
        return sorted(deals,key=lambda d:-d['discount_pct'])

    def last_run(self):
        row = self.conn.execute('SELECT * FROM runs ORDER BY id DESC LIMIT 1').fetchone()
        return dict(row) if row else None
