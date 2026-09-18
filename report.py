"""Local HTML report: text-only shortlist with observed asking prices."""
import html
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import config

CSS = """
:root{
  --bg:#10161d; --panel:#171f29; --panel2:#1c2632; --line:#26313f;
  --text:#d7dde4; --muted:#8a96a3; --copper:#d98a4b; --copper-dim:#9a6234;
  --teal:#5ba8a0; --red:#c96a5a;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);
  font:15px/1.55 "Space Grotesk",system-ui,Segoe UI,sans-serif;padding:0 0 80px}
.mono{font-family:"IBM Plex Mono",ui-monospace,Consolas,monospace}
.wrap{max-width:1060px;margin:0 auto;padding:0 24px}
header{padding:46px 0 10px;border-bottom:1px solid var(--line)}
header h1{font-size:30px;margin:0;letter-spacing:.5px}
header h1 b{color:var(--copper);font-weight:600}
header .sub{color:var(--muted);font-size:13px;margin-top:6px}
.trace{height:1px;background:var(--line);position:relative;margin:42px 0 26px}
.trace::after{content:"";position:absolute;left:0;top:-3px;width:7px;height:7px;
  border-radius:50%;background:var(--copper)}
h2{font-size:14px;text-transform:uppercase;letter-spacing:2.5px;
  color:var(--muted);margin:0 0 16px;font-weight:600}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;
  padding:16px 18px;display:flex;flex-direction:column;gap:6px}
.card .pct{font-size:34px;font-weight:600;color:var(--copper);line-height:1}
.card .pct small{font-size:13px;color:var(--muted);font-weight:400;margin-left:8px}
.card.repair .pct{color:var(--teal);font-size:26px}
.card .title{font-size:14px;overflow:hidden;text-overflow:ellipsis;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.card .meta{color:var(--muted);font-size:12.5px}
.card a{color:var(--copper);text-decoration:none;font-size:13px}
.card a:hover{text-decoration:underline}
table{width:100%;border-collapse:collapse;font-size:14px}
th{color:var(--muted);text-transform:uppercase;font-size:11px;letter-spacing:1.5px;
  text-align:left;padding:8px 12px;border-bottom:1px solid var(--line)}
td{padding:9px 12px;border-bottom:1px solid var(--line)}
tr:hover td{background:var(--panel2)}
td.num,th.num{text-align:right;font-family:"IBM Plex Mono",ui-monospace,monospace}
.tag{display:inline-block;padding:1px 8px;border-radius:20px;font-size:11px;
  border:1px solid var(--line);color:var(--muted)}
.tag.deal{border-color:var(--copper-dim);color:var(--copper)}
.empty{color:var(--muted);font-size:14px;padding:14px 0}
details{margin-bottom:10px}
summary{cursor:pointer;padding:10px 14px;background:var(--panel);
  border:1px solid var(--line);border-radius:8px;font-weight:600;font-size:14px}
summary .mono{color:var(--muted);font-weight:400;font-size:12.5px;margin-left:10px}
details[open] summary{border-radius:8px 8px 0 0}
details .inner{border:1px solid var(--line);border-top:0;border-radius:0 0 8px 8px;
  background:var(--panel)}
footer{margin-top:60px;color:var(--muted);font-size:12px}
@media (prefers-reduced-motion:no-preference){
  .card{transition:border-color .15s}.card:hover{border-color:var(--copper-dim)}}
"""


def esc(value):
    return html.escape(str(value if value is not None else '—'))


def eur(value):
    return f'{value:.2f} €' if value is not None else '—'


def row(item, run):
    url = item.get('url') or ''
    parsed = urlparse(url)
    title = esc(item['title'])
    if parsed.scheme == 'https' and parsed.hostname in {'olx.pt','www.olx.pt','vinted.pt','www.vinted.pt'}:
        title = f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{title}</a>'
    tags = []
    if item.get('first_seen_run') == run.get('id') and run.get('id') is not None:
        tags.append('NEW this scan')
    if item.get('last_seen_run') != run.get('id'):
        tags.append('not seen this scan')
    prev = item.get('previous_price')
    if prev is not None and prev != item['price']:
        tags.append(f'last recorded change: {eur(prev)} → {eur(item["price"])}')
    if not item.get('comparison_eligible'):
        tags.append('excluded: ' + (item.get('exclusion_reason') or 'not classified'))
    if item['is_defective']:
        tags.append('defect wording in text')
    return (f'<tr><td>{title}<div class="meta">{esc(" · ".join(tags))}</div></td>'
            f'<td>{esc(item.get("location") or "Unknown")}</td><td class="num">{eur(item["price"])}</td>'
            f'<td>{esc(item["condition"])}</td><td>{esc(item["last_seen"].replace("T"," "))}</td></tr>')


def table(items, run):
    return '<div class="scroll"><table><tr><th>Listing</th><th>Location</th><th>Price</th><th>State</th><th>Last seen locally</th></tr>' + ''.join(row(i,run) for i in items) + '</table></div>'


def generate(database, out_dir=config.REPORTS_DIR):
    out = Path(out_dir); out.mkdir(parents=True,exist_ok=True)
    run = database.last_run() or {}
    stats = database.model_stats()
    items = database.active_listings()
    deals = database.find_deals()
    groups = {}
    for item in items:
        groups.setdefault((item['category'],item['model'],item['condition'],item.get('comparison_key') or ''),[]).append(item)
    sections = []
    for (category,model,condition,comparison_key), listings in sorted(groups.items()):
        st = stats.get(comparison_key,{})
        clean = [i for i in listings if i.get('comparison_eligible')]
        flagged = [i for i in listings if not i.get('comparison_eligible')]
        body = table(clean[:config.TOP_N],run) if clean else '<p>No eligible comparisons.</p>'
        if len(clean)>config.TOP_N:
            body += f'<details><summary>Remaining {len(clean)-config.TOP_N} listings</summary>{table(clean[config.TOP_N:],run)}</details>'
        if flagged:
            body += f'<details><summary>Manual review: {len(flagged)} listings (excluded from median)</summary>{table(flagged,run)}</details>'
        sections.append(f'<details class="model" data-category="{category}" open><summary>{esc(model)} · {condition} · {len(listings)} listings'
                        f'<span class="mono">median {eur(st.get("median"))} · n={st.get("count",0)}</span></summary>{body}</details>')
    cards = ''.join(f'<div class="card"><div class="pct">−{d["discount_pct"]}%</div><div>{esc(d["model"])}</div>'
                    f'<div class="meta">vs {eur(d["median_used"])} observed median</div>{table([d],run)}</div>' for d in deals)
    stamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    notes = esc(run.get('notes','No scan has run yet.')).replace('\n','<br>')
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hardware component deals</title><style>{CSS}
.wrap{{max-width:1400px}}a{{color:var(--copper)}}.scroll{{overflow-x:auto}}.meta,small{{color:var(--muted);font-size:12px}}
input,select{{padding:10px;margin:6px;background:var(--panel);color:var(--text);border:1px solid var(--line)}}
.cards{{grid-template-columns:1fr}}.model{{margin-top:14px}}.notice{{padding:16px;background:var(--panel);border:1px solid var(--line)}}
</style><body><div class="wrap"><header><h1>Hardware <b>component deals</b></h1><p>{stamp} · GPU / CPU / RAM</p></header>
<p class="notice">Candidate listings for manual review. Prices are asking prices, excluding delivery.
Statistics use one latest price per platform ad from the past {config.STATS_WINDOW_DAYS} days, separated by platform, model/specifications and declared condition.
Not seeing an ad again does not establish that it sold. Only validated classifications with explicit working condition enter medians. Unknown, untested, defective and ambiguous ads require manual review. Images may supplement missing identification; they cannot establish function.</p>
<details><summary>Scan status · {esc(run.get('finished_at') or 'not completed')} · {run.get('new_listings',0)} new / {run.get('updated_listings',0)} price changes</summary><p>{notes}</p></details>
<div class="trace"></div><h2>At least {round((1-config.DEAL_THRESHOLD)*100)}% below median</h2>
{cards or '<p>No qualifying deals in the stored sample. Check scan status and the cheapest listings below.</p>'}
<div class="trace"></div><h2>Cheapest {config.TOP_N} per model / specification</h2>
<p>A median needs {config.MIN_SAMPLES_FOR_STATS} comparable ads. Cheapest lists work immediately. Missing required specifications exclude ads from medians.</p>
<label>Category <select id="category"><option value="">All</option><option>GPU</option><option>CPU</option><option>RAM</option></select></label>
<label>Search model, title or location <input id="search" placeholder="6600, Gaia, Porto…"></label>
<p><small>Filters below apply to the per-model lists.</small></p>
{''.join(sections) or '<p>No recognised components stored yet.</p>'}
<footer>Run again to refresh. Scan scope is the configured queries and page limit, not all platform inventory.</footer></div>
<script>
function filter(){{const q=document.getElementById('search').value.toLowerCase();const c=document.getElementById('category').value;
for(const e of document.querySelectorAll('.model')) e.hidden=!!((c&&e.dataset.category!==c)||!e.textContent.toLowerCase().includes(q));}}
document.getElementById('search').addEventListener('input',filter);document.getElementById('category').addEventListener('change',filter);
</script></body></html>'''
    path = out/'latest.html'
    path.write_text(page,encoding='utf-8')
    return str(path)
