#!/usr/bin/env python3
"""Run once, save observations and open the local HTML shortlist."""
import argparse
from pathlib import Path
import sys
import config
from db import Database
from scrapers import SCRAPERS
from classification import ClassificationPipeline, enrich
import report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',nargs='?',default='scrape',choices=['scrape','report','reclassify'])
    parser.add_argument('--sites', nargs='+', choices=sorted(SCRAPERS), default=config.ENABLED_SITES)
    parser.add_argument('--limit', type=int, default=20, help='Maximum stored ads to reclassify')
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
        if args.command in ('scrape', 'reclassify'):
            pipeline = ClassificationPipeline()
            run=database.start_run()
            new=changed=unchanged=errors=0
            diagnostics=[]
            try:
                if args.command == 'reclassify':
                    import json
                    if args.limit < 1:
                        parser.error('--limit must be positive')
                    rows = database.conn.execute('SELECT * FROM listings ORDER BY last_seen DESC LIMIT ?', (args.limit,)).fetchall()
                    for row in rows:
                        item = dict(row)
                        item['images'] = json.loads(item.pop('images_json') or '[]')
                        result = pipeline.classify(item)
                        # Reclassification does not falsely refresh collection timestamps/history.
                        cmp = result['comparison']
                        database.conn.execute('UPDATE listings SET classification_json=?,comparison_key=?,comparison_eligible=?,exclusion_reason=?,category=?,model=?,is_defective=? WHERE id=?',
                            (json.dumps(result, ensure_ascii=False), cmp['key'], int(cmp['eligible']), cmp['exclusion_reason'], result['category'] or '', result['model'] or 'Unknown', int(result['functional_condition']=='defective'), item['id']))
                        database.conn.commit()
                        errors += bool(result['error'])
                        print(item['listing_id'], cmp['exclusion_reason'] or 'eligible', flush=True)
                else:
                    for site in args.sites:
                        scraper=SCRAPERS[site]()
                        for item in scraper.scrape(args.queries):
                            classification = pipeline.classify(item)
                            errors += bool(classification['error'])
                            result=database.upsert_listing(enrich(item, classification),run)
                            new+=result=='new'; changed+=result=='changed'; unchanged+=result=='unchanged'
                            print(site, item['listing_id'], classification['comparison']['exclusion_reason'] or 'eligible', flush=True)
                        diagnostics.extend(scraper.diagnostics)
                        if scraper.failed:
                            code=1
                status='PARTIAL / CHECK ERRORS' if code or errors else 'FINISHED (within configured scope)'
                if errors:
                    code=1
            except KeyboardInterrupt:
                status='CANCELLED'; code=130
            notes=f'{status}\n{unchanged} unchanged ads; {errors} classification errors\n'+'\n'.join(diagnostics)
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
