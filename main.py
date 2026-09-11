#!/usr/bin/env python3
"""Run once, save observations and open the local HTML shortlist."""
import argparse
from pathlib import Path
import sys
import config
from db import Database
from scrapers import OlxScraper
import report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',nargs='?',default='scrape',choices=['scrape','report'])
    parser.add_argument('--queries',nargs='+',help='Override configured OLX searches')
    parser.add_argument('--pages',type=int,default=config.MAX_PAGES_PER_QUERY)
    parser.add_argument('--threshold',type=float,default=config.DEAL_THRESHOLD,help='0.8 means at least 20%% below median')
    parser.add_argument('--top',type=int,default=config.TOP_N)
    parser.add_argument('--db',default=config.DB_PATH)
    parser.add_argument('--out',default=config.REPORTS_DIR)
    parser.add_argument('--no-open',action='store_true')
    parser.add_argument('--open',action='store_true',help='Compatibility option; opening is already the default')
    args=parser.parse_args()
    if args.pages<1 or args.top<1 or not 0<args.threshold<1:
        parser.error('pages/top must be positive and threshold must be between 0 and 1')
    config.MAX_PAGES_PER_QUERY=args.pages; config.DEAL_THRESHOLD=args.threshold; config.TOP_N=args.top
    database=Database(args.db)
    code=0
    try:
        if args.command=='scrape':
            run=database.start_run()
            scraper=OlxScraper()
            print('Scanning OLX. Broad searches can take several minutes; Ctrl+C cancels.',flush=True)
            new=changed=unchanged=0
            try:
                for item in scraper.scrape(args.queries):
                    result=database.upsert_listing(item,run)
                    new+=result=='new'; changed+=result=='changed'; unchanged+=result=='unchanged'
                status='FAILED' if not scraper.successful else ('PARTIAL' if scraper.failed else 'FINISHED (within configured scope)')
                code=1 if scraper.failed else 0
            except KeyboardInterrupt:
                status='CANCELLED'; code=130
            notes=f'{status}\n{unchanged} unchanged ads; {scraper.successful} queries completed; {scraper.failed} failed\n'+'\n'.join(scraper.diagnostics)
            database.finish_run(run,new,changed,notes)
            print(notes,flush=True)
        path=report.generate(database,args.out)
        print('Report:',path)
        if not args.no_open:
            import webbrowser
            webbrowser.open(Path(path).resolve().as_uri())
    finally:
        database.conn.close()
    return code


if __name__=='__main__':
    sys.exit(main())
