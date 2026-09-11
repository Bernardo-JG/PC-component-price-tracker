#!/usr/bin/env python3
"""GPU deal tracker.

Usage:
  python main.py scrape                 # run all scrapers once + report
  python main.py scrape --sites vinted olx
  python main.py report                 # regenerate report from DB only
  python main.py schedule --every 180   # loop: scrape every 180 minutes
"""

import argparse
import logging
import time
import webbrowser

import config
import report as report_mod
from db import Database
from scrapers import SCRAPERS

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)-7s %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("main")


def run_scrape(sites: list[str], open_report: bool) -> None:
    database = Database()
    run_id = database.start_run()
    new = updated = 0
    notes = []
    for site in sites:
        cls = SCRAPERS.get(site)
        if cls is None:
            log.warning("unknown site '%s'", site)
            continue
        log.info("=== scraping %s ===", site)
        try:
            listings = cls().scrape()
        except Exception as e:  # noqa: BLE001
            log.error("%s failed entirely: %s", site, e)
            notes.append(f"{site}: FAILED ({e})")
            continue
        for l in listings:
            if database.upsert_listing(l) == "new":
                new += 1
            else:
                updated += 1
        notes.append(f"{site}: {len(listings)} listings")
    database.finish_run(run_id, new, updated, "; ".join(notes))
    log.info("run done — %d new, %d updated", new, updated)

    path = report_mod.generate(database)
    log.info("report written to %s", path)

    deals = database.find_deals()
    if deals:
        log.info("*** %d DEAL(S) FOUND ***", len(deals))
        for d in deals[:10]:
            log.info("  -%d%%  %s €%.0f  (median €%.0f)  %s",
                     d["discount_pct"], d["model"], d["price"],
                     d["median_used"], d["url"] or "")
    if open_report:
        webbrowser.open(f"file://{__import__('os').path.abspath(path)}")


def main():
    p = argparse.ArgumentParser(description="GPU deal tracker")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("scrape", help="scrape all sites once and report")
    sp.add_argument("--sites", nargs="+", default=config.ENABLED_SITES)
    sp.add_argument("--open", action="store_true",
                    help="open the HTML report when done")

    sub.add_parser("report", help="regenerate the report from the database")

    sc = sub.add_parser("schedule", help="scrape on a fixed interval")
    sc.add_argument("--every", type=int, default=180,
                    help="interval in minutes (default 180)")
    sc.add_argument("--sites", nargs="+", default=config.ENABLED_SITES)

    args = p.parse_args()

    if args.cmd == "scrape":
        run_scrape(args.sites, args.open)
    elif args.cmd == "report":
        path = report_mod.generate(Database())
        log.info("report written to %s", path)
    elif args.cmd == "schedule":
        log.info("scheduled mode: every %d min (Ctrl+C to stop)", args.every)
        while True:
            try:
                run_scrape(args.sites, open_report=False)
            except Exception as e:  # noqa: BLE001
                log.error("scheduled run failed: %s", e)
            time.sleep(args.every * 60)


if __name__ == "__main__":
    main()
