"""Prost live dashboard za fan 5-seed progres. Pokretanje (iz pc/):
    python tools/fan_seed_dash.py   (pa otvori http://localhost:8770)
Cita results.csv, prikazuje mrezu seed x varijanta (gotovo/hmean) + napredak.
"""
from __future__ import annotations
import csv, json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VARIANTS = ["baseline", "tiny64", "tiny32", "tiny16", "tiny32b4"]
SEEDS = [1, 2, 3, 4]  # seed 0 vec imamo; 5-seed = 0..4


def status():
    rows = []
    p = ROOT / "results" / "results.csv"
    if p.exists():
        with open(p, newline="") as f:
            rows = list(csv.DictReader(f))
    grid = {}  # (seed,variant) -> hmean int8
    for r in rows:
        try:
            s = int(r["seed"])
        except (ValueError, KeyError):
            continue
        if r.get("precision") == "int8" and r.get("score") == "mse":
            grid[(s, r["variant"])] = round(float(r["hmean"]), 4)
    done = sum(1 for s in SEEDS for v in VARIANTS if (s, v) in grid)
    total = len(SEEDS) * len(VARIANTS)
    # seed 0 (vec gotov) za prikaz reference
    ref = {v: round(float(next((x["hmean"] for x in rows
              if x.get("seed") == "0" and x["variant"] == v
              and x.get("precision") == "int8" and x.get("score") == "mse"), 0) or 0), 4)
           for v in VARIANTS}
    return {"grid": {f"{s}|{v}": grid.get((s, v)) for s in SEEDS for v in VARIANTS},
            "ref": ref, "done": done, "total": total,
            "variants": VARIANTS, "seeds": SEEDS}


PAGE = """<!DOCTYPE html><html lang=sr><head><meta charset=utf-8>
<title>fan 5-seed</title><style>
:root{--bg:#f7f8fa;--card:#fff;--tx:#1f2328;--mut:#57606a;--acc:#0b57d0;--ok:#146c2e;--bar:#e3e8ee;--bd:#dce1e6}
@media(prefers-color-scheme:dark){:root{--bg:#15171b;--card:#1e2126;--tx:#e6e8eb;--mut:#9aa4af;--acc:#7cacf8;--ok:#6dd58c;--bar:#2a2f37;--bd:#333a42}}
body{font:15px/1.5 'Segoe UI',sans-serif;margin:0;background:var(--bg);color:var(--tx)}
.w{max-width:640px;margin:0 auto;padding:26px 18px}
h1{font-size:1.3rem;margin:0 0 2px}.s{color:var(--mut);font-size:.85rem;margin-bottom:16px}
.bar{height:20px;background:var(--bar);border-radius:10px;overflow:hidden;margin:10px 0}
.fill{height:100%;background:var(--acc);transition:width .6s}
table{border-collapse:collapse;width:100%;margin:14px 0;font-size:.86rem}
th,td{border:1px solid var(--bd);padding:6px 8px;text-align:center}
th{background:var(--bar)}td:first-child,th:first-child{text-align:left}
.d{background:color-mix(in srgb,var(--ok) 15%,transparent);color:var(--ok);font-weight:600}
.p{color:var(--mut)}.pulse{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--ok);animation:b 1.4s infinite}
@keyframes b{50%{opacity:.25}}
</style></head><body><div class=w>
<h1>fan 5-seed progres <span class=pulse></span></h1>
<div class=s id=ts></div>
<div class=bar><div class=fill id=fill></div></div>
<div id=cnt class=s></div>
<table id=tbl></table>
<div class=s>Zelena = gotovo (hmean int8). Kolona <b>ref</b> = seed 0 (raniji rezultat).</div>
<script>
async function tick(){
 const d=await(await fetch('/api/status')).json();
 document.getElementById('ts').textContent='osvjezeno '+new Date().toLocaleTimeString();
 const pct=d.total?100*d.done/d.total:0;
 document.getElementById('fill').style.width=pct.toFixed(1)+'%';
 document.getElementById('cnt').textContent=d.done+' / '+d.total+' modela gotovo ('+pct.toFixed(0)+'%)';
 let h='<tr><th>seed \\ varijanta</th>'+d.variants.map(v=>'<th>'+v+'</th>').join('')+'</tr>';
 h+='<tr><td>ref (seed 0)</td>'+d.variants.map(v=>'<td class=p>'+(d.ref[v]||'-')+'</td>').join('')+'</tr>';
 for(const s of d.seeds){h+='<tr><td>seed '+s+'</td>';
  for(const v of d.variants){const val=d.grid[s+'|'+v];
   h+=val!=null?'<td class=d>'+val+'</td>':'<td class=p>...</td>'}h+='</tr>'}
 document.getElementById('tbl').innerHTML=h;
}
tick();setInterval(tick,5000);
</script></div></body></html>"""


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api"):
            b = json.dumps(status()).encode(); ct = "application/json"
        else:
            b = PAGE.encode(); ct = "text/html; charset=utf-8"
        self.send_response(200); self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store"); self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a): pass


if __name__ == "__main__":
    print("fan 5-seed dashboard: http://localhost:8770")
    ThreadingHTTPServer(("127.0.0.1", 8770), H).serve_forever()
