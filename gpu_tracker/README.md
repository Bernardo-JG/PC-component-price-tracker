# GPU Deal Tracker

Tracks GPU listings on **Vinted.pt, OLX.pt, Wallapop, PCDiga** and (best-effort)
**Amazon.es**, stores everything in SQLite, computes per-model rolling median
prices, flags deals and defective repair candidates, and renders a static HTML
report.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py scrape --open      # scrape everything once, open the report
python main.py scrape --sites vinted olx   # only some sites
python main.py report             # regenerate report from existing DB
python main.py schedule --every 180        # loop every 3 hours
```

The report is written to `reports/latest.html` (plus a timestamped copy).
The database is `gpu_tracker.db` — a single SQLite file you can inspect with
any SQLite browser.

For a real schedule, prefer cron over `schedule` mode, e.g. every 4 hours:

```
0 */4 * * * cd /path/to/gpu_tracker && python main.py scrape
```

## How deals are decided

For each model, the **median price of used, non-defective listings** seen in
the last `STATS_WINDOW_DAYS` (45) is computed. A listing is a *deal* when its
price ≤ `DEAL_THRESHOLD` (80%) of that median. Median is used instead of mean
because second-hand sites are full of mislabelled junk that skews averages.
New retail prices (PCDiga / Amazon) appear in the overview table only as a
market ceiling — they never affect deal detection.

**Important:** medians need data. The first run or two will show few/no deals
because `MIN_SAMPLES_FOR_STATS` (4) used listings per model are required
before a median is trusted. Let it run for a few days.

## Repair candidates

Listings whose title/description contains defect terms ("avariada", "para
peças", "no signal", …) go to their own section. The model range is extended
downwards (GTX 10/16/20 series, RX 500/5000) and capped upwards via
`REPAIR_MAX_TIER` in `config.py` — by default nothing above ~3080/7800 XT
class, so no 4080s tempting you beyond your soldering pay grade.

## Tuning

Everything lives in `config.py`: model patterns, search queries, defect/junk
keywords, price bounds, deal threshold, delays, enabled sites.

## Maintenance reality check

These scrapers use the sites' internal APIs or HTML, which change without
notice:

- **Vinted / OLX** — JSON APIs, most stable.
- **Wallapop** — API shape changes occasionally; the scraper handles both
  known response formats. If it goes quiet, check the network tab on
  wallapop.com and update `scrapers/wallapop.py`.
- **PCDiga** — parsed via JSON-LD first (robust), HTML cards as fallback.
- **Amazon.es** — best effort. On captcha/block it logs a warning and skips
  the rest of the run. PCDiga alone is usually enough as a new-price
  reference.

All failures are logged and isolated: one broken site never kills a run.
Be a polite scraper — keep the random 2–5 s delays, don't run it every
5 minutes, and don't parallelize requests to the same site.
