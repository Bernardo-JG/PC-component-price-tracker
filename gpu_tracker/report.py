"""Static HTML report generation."""

import html
import os
from datetime import datetime

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

SITE_LABEL = {"vinted": "Vinted", "olx": "OLX", "wallapop": "Wallapop",
              "pcdiga": "PCDiga", "amazon": "Amazon.es"}


def _e(s):
    return html.escape(str(s or ""))


def _eur(v):
    return f"{v:,.0f} €".replace(",", " ") if v is not None else "—"


def _listing_row(l, stats):
    s = stats.get(l["model"], {})
    med = s.get("median_used")
    deal = (l["condition"] == "used" and not l["is_defective"] and med
            and l["price"] <= config.DEAL_THRESHOLD * med)
    tag = '<span class="tag deal">deal</span>' if deal else (
        '<span class="tag">defective</span>' if l["is_defective"] else
        f'<span class="tag">{_e(l["condition"])}</span>')
    link = f'<a href="{_e(l["url"])}" target="_blank" rel="noopener">{_e(l["title"][:90])}</a>' \
        if l.get("url") else _e(l["title"][:90])
    return (f"<tr><td>{link}</td><td>{_e(SITE_LABEL.get(l['site'], l['site']))}</td>"
            f"<td class='num'>{_eur(l['price'])}</td><td>{tag}</td>"
            f"<td class='mono' style='color:var(--muted);font-size:12px'>"
            f"{_e(l['last_seen'][:10])}</td></tr>")


def _deal_card(d):
    return f"""<div class="card">
      <div class="pct">−{d['discount_pct']}%<small>vs {_eur(d['median_used'])} median</small></div>
      <div class="title">{_e(d['title'])}</div>
      <div class="meta">{_e(SITE_LABEL.get(d['site'], d['site']))} ·
        <span class="mono">{_eur(d['price'])}</span></div>
      {f'<a href="{_e(d["url"])}" target="_blank" rel="noopener">Open listing →</a>' if d.get('url') else ''}
    </div>"""


def _repair_card(r):
    return f"""<div class="card repair">
      <div class="pct mono">{_eur(r['price'])}</div>
      <div class="title">{_e(r['title'])}</div>
      <div class="meta">{_e(r['model'])} · {_e(SITE_LABEL.get(r['site'], r['site']))}</div>
      {f'<a href="{_e(r["url"])}" target="_blank" rel="noopener">Open listing →</a>' if r.get('url') else ''}
    </div>"""


def generate(database, out_dir: str = config.REPORTS_DIR) -> str:
    os.makedirs(out_dir, exist_ok=True)
    stats = database.model_stats()
    listings = database.active_listings()
    deals = database.find_deals()
    repairs = database.repair_candidates()
    run = database.last_run() or {}

    # group listings per model for the browser section
    by_model: dict = {}
    for l in listings:
        by_model.setdefault(l["model"], []).append(l)

    deal_html = ("<div class='cards'>" + "".join(_deal_card(d) for d in deals[:24])
                 + "</div>") if deals else \
        "<p class='empty'>No deals below the threshold right now. Medians need a few runs of data to become meaningful.</p>"

    repair_html = ("<div class='cards'>" + "".join(_repair_card(r) for r in repairs[:24])
                   + "</div>") if repairs else \
        "<p class='empty'>No defective listings found in the current window.</p>"

    stats_rows = ""
    for model in sorted(stats):
        s = stats[model]
        stats_rows += (f"<tr><td>{_e(model)}</td>"
                       f"<td class='num'>{_eur(s['median_used'])}</td>"
                       f"<td class='num'>{_eur(s['mean_used'])}</td>"
                       f"<td class='num'>{s['n_used']}</td>"
                       f"<td class='num'>{_eur(s['min_new'])}</td></tr>")

    model_sections = ""
    for model in sorted(by_model):
        rows = "".join(_listing_row(l, stats) for l in by_model[model][:60])
        model_sections += f"""<details><summary>{_e(model)}
          <span class="mono">{len(by_model[model])} listings</span></summary>
          <div class="inner"><table>
          <tr><th>Listing</th><th>Site</th><th class="num">Price</th><th>Status</th><th>Seen</th></tr>
          {rows}</table></div></details>"""

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GPU Price Tracker — {stamp}</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><div class="wrap">
<header><h1>GPU <b>price tracker</b></h1>
<div class="sub mono">generated {stamp} · window {config.STATS_WINDOW_DAYS}d ·
deal threshold ≤{int(config.DEAL_THRESHOLD * 100)}% of median ·
{len(listings)} active listings</div></header>

<div class="trace"></div><h2>Deals</h2>{deal_html}
<div class="trace"></div><h2>Repair candidates (defective)</h2>{repair_html}
<div class="trace"></div><h2>Market overview</h2>
<table><tr><th>Model</th><th class="num">Median used</th><th class="num">Mean used</th>
<th class="num"># used</th><th class="num">Min new (retail)</th></tr>{stats_rows}</table>
<div class="trace"></div><h2>All listings by model</h2>{model_sections}
<footer class="mono">last run: {_e(run.get('finished_at', '—'))} ·
new {run.get('new_listings', 0)} / updated {run.get('updated_listings', 0)}</footer>
</div></body></html>"""

    latest = os.path.join(out_dir, "latest.html")
    dated = os.path.join(out_dir,
                         f"report_{datetime.now():%Y%m%d_%H%M}.html")
    for path in (latest, dated):
        with open(path, "w", encoding="utf-8") as f:
            f.write(page)
    return latest
