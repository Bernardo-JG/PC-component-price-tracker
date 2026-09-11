# OLX component deal finder

Python 3.10+; no third-party packages required. Extract this entire folder first.
On Windows, double-click `run_tracker.bat` (requires the Python launcher), or run:

```
python main.py
```

One run fetches configured OLX searches, updates `gpu_tracker.db`, and opens
`reports/latest.html`. There is no background scheduler. For Windows login startup,
press Win+R, enter `shell:startup`, and place a shortcut to `run_tracker.bat` there.
The app stays in its extracted folder. Do not run two scans concurrently.

## Scope
GPU, CPU and RAM only. Complete PCs and CPU/motherboard bundles are skipped.
Older working cards are included. Text only: no photo analysis or seller scoring.
Untested ads are eligible. Explicit defect wording is shown in expandable lists
and excluded from the median; this heuristic is not a diagnosis.
Location comes from OLX's city/region fields, with Unknown as the fallback.
Bare 6600 and 2060 are recognised; ambiguous 5600/7600 require CPU/GPU context.
Recognition is heuristic; obscure models, vague ads and some shorthand will be missed.
Edit model lists and queries in `config.py` to extend coverage.

## Results and comparison
The shortlist flags prices at or below 80% of the observed asking-price median.
The ten cheapest ads are also shown per model/specification and condition, even
without a median. Four comparable ads are required for a median.
One current price per OLX listing ID contributes; repeated scans never duplicate it.
Price history records only changes, with first/last seen and new-this-scan badges.
OLX's stable numeric ad ID deduplicates short and descriptive URLs. Relisted ads
with a new ID cannot reliably be identified as duplicates.
Comparisons use a 30-day last-observed window. Disappeared ads are not labelled sold;
previously observed ads show 'not seen this scan'. Old stored ads may no longer be
available. Delivery and actual transaction prices are unknown.
GPU VRAM variants and RAM capacity/layout/speed/form factor are separate cohorts;
unknown specifications stay in their own groups. New/used ads never share a median.

## Controls
```
python main.py --queries 6600 2060 --pages 3
python main.py --threshold 0.75 --top 10
python main.py report
python main.py --no-open
```
Default searches cover GPUs, CPUs and RAM with ten pages per query, 40 results/page.
This is bounded coverage, not all OLX ads. Capped searches, repeated pages, failures
and fetched/recognised counts appear in Scan status. API behaviour may change.
Requests are sequential with 2–5 second delays and a timeout; no access bypasses.
No retail, Vinted, Wallapop, Facebook, cloud hosting, messages or purchases.

## Existing database
Back up your original `gpu_tracker.db`, then copy it into this folder before running.
Existing tables/history are preserved; additive columns store location/category/run
identity. Old titles are reclassified. Legacy non-OLX records remain in the database
but do not appear in this OLX-only report. Do not use the new database with the old app.

## Checks
```
python -m unittest discover -s tests -v
```
The included database and report contain 299 eligible listings from a limited
validation scan of 6600, 2060, Ryzen 5600 and DDR4 16GB (five-page cap per query).
The RAM search reached that cap. The default app run searches more broadly.
To start without these observations, rename `gpu_tracker.db` before the first run.
The included report uses real observations from that limited validation scan;
its collection details are in the report, and it is not a complete market survey.
