"""LIVE dashboard: mali HTTP server (samo stdlib) koji uzivo prati sweep-ove.

Pokretanje (iz pc/):  python tools/live_dashboard.py   [--port 8765]
Onda otvori:          http://localhost:8765
Stranica se sama osvjezava svakih 5 s (fetch /api/status).
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
MACHINES = ["fan", "bearingEmu", "gearboxEmu", "sliderEmu", "ToyCar", "ToyCarEmu", "valveEmu"]
VARIANTS = ["baseline", "tiny64", "tiny32", "tiny16", "tiny32b4"]

RE_EPOCH = re.compile(r"Epoch (\d+)/(\d+)")
RE_VAR = re.compile(r"=== \w+ / (\w+) : trening")
RE_QUANT = re.compile(r"=== \w+ / (\w+) : PTQ")
RE_LOSS = re.compile(r"loss: ([\d.]+) - val_loss: ([\d.]+)")
RE_SEC = re.compile(r"- (\d+)s -")


def machine_status(m: str) -> dict:
    log = RESULTS / f"sweep_{m}.log"
    st = {"machine": m, "state": "queued", "variant": None, "epoch": 0, "epochs": 100,
          "done_variants": 0, "progress": 0.0, "eta_min": None, "loss": [], "val_loss": []}
    if not log.exists():
        return st
    try:
        raw = log.read_bytes()
        # PowerShell *>> pise UTF-16 LE sa BOM-om
        txt = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") \
            else raw.decode("utf-8", "ignore")
    except (OSError, UnicodeDecodeError):
        return st
    if "GOTOVO" in txt:
        st.update(state="done", progress=1.0, done_variants=len(VARIANTS))
        return st
    st["state"] = "running"
    quants = RE_QUANT.findall(txt)
    st["done_variants"] = len(quants)
    variants = RE_VAR.findall(txt)
    st["variant"] = variants[-1] if variants else None
    eps = RE_EPOCH.findall(txt)
    if eps:
        st["epoch"], st["epochs"] = int(eps[-1][0]), int(eps[-1][1])
    losses = RE_LOSS.findall(txt)[-60:]
    st["loss"] = [float(a) for a, _ in losses]
    st["val_loss"] = [float(b) for _, b in losses]
    secs = [int(s) for s in RE_SEC.findall(txt)[-20:]]
    if secs and eps:
        med = sorted(secs)[len(secs) // 2]
        st["eta_min"] = round(med * (st["epochs"] - st["epoch"]) / 60, 1)
    frac_var = st["epoch"] / max(st["epochs"], 1)
    st["progress"] = min(1.0, (st["done_variants"] + frac_var) / len(VARIANTS))
    return st


def read_results() -> list[dict]:
    p = RESULTS / "results.csv"
    if not p.exists():
        return []
    try:
        with open(p, newline="") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


PAGE = """<!DOCTYPE html><html lang="sr"><head><meta charset="utf-8">
<title>ASD live dashboard</title><style>
:root{--bg:#fafafa;--card:#fff;--tx:#1f2328;--mut:#57606a;--bd:#d8dee4;--acc:#0b57d0;--ok:#146c2e;--bar:#e3e8ee}
@media (prefers-color-scheme:dark){:root{--bg:#16181c;--card:#1e2126;--tx:#e6e8eb;--mut:#9aa4af;--bd:#343a42;--acc:#7cacf8;--ok:#6dd58c;--bar:#2a2f37}}
body{font:15px/1.5 'Segoe UI',sans-serif;margin:0;background:var(--bg);color:var(--tx)}
.wrap{max-width:1060px;margin:0 auto;padding:22px 16px}
h1{font-size:1.4rem;margin:0 0 2px} .sub{color:var(--mut);font-size:.85rem;margin-bottom:18px}
.card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:12px 16px;margin:10px 0}
.mrow{display:flex;align-items:center;gap:12px;padding:7px 0;border-bottom:1px solid var(--bd)}
.mrow:last-child{border-bottom:0}
.mname{width:110px;font-weight:600}
.bar{flex:1;height:16px;background:var(--bar);border-radius:8px;overflow:hidden}
.fill{height:100%;background:var(--acc);transition:width .8s}
.fill.done{background:var(--ok)}
.stat{width:290px;font-size:.82rem;color:var(--mut);text-align:right}
table{border-collapse:collapse;font-size:.84rem;margin:6px 0}
th,td{border:1px solid var(--bd);padding:4px 9px;text-align:right}
th{background:var(--bar)} td:first-child,th:first-child{text-align:left}
.neg{background:#fde7e9;color:#8b1a1a}@media (prefers-color-scheme:dark){.neg{background:#4a2326;color:#f2b8b5}}
svg{display:block} h2{font-size:1.05rem;margin:20px 0 4px}
.pulse{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--ok);animation:p 1.5s infinite}
@keyframes p{50%{opacity:.25}}
</style></head><body><div class="wrap">
<h1>ASD eksperimenti — live <span class="pulse"></span></h1>
<div class="sub">Osvjezava se svakih 5 s · <span id="ts"></span></div>
<div class="card" id="progress"></div>
<div class="card"><b>Loss tekuceg treninga</b> (plavo=train, zeleno=val)<div id="spark"></div></div>
<h2>hmean po masini (zadnji red po varijanti)</h2><div class="card" id="tbl"></div>
<h2>&Delta;hmean (int8 &minus; fp32)</h2><div class="card" id="delta"></div>
<script>
function spark(a,b){if(!a.length)return '<i style="color:var(--mut)">nema podataka</i>';
 const W=980,H=90,all=a.concat(b),mn=Math.min(...all),mx=Math.max(...all),r=mx-mn||1;
 const pts=s=>s.map((v,i)=>`${(i/(s.length-1||1)*W).toFixed(1)},${(H-8-(v-mn)/r*(H-16)).toFixed(1)}`).join(' ');
 return `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  <polyline points="${pts(a)}" fill="none" stroke="#0b57d0" stroke-width="2"/>
  <polyline points="${pts(b)}" fill="none" stroke="#146c2e" stroke-width="2"/>
  <text x="4" y="12" font-size="10" fill="currentColor">${mx.toFixed(4)}</text>
  <text x="4" y="${H-2}" font-size="10" fill="currentColor">${mn.toFixed(4)}</text></svg>`}
function pivot(rows,prec){const ms=[...new Set(rows.map(r=>r.machine))];
 let h='<table><tr><th>'+prec+'</th>'+ms.map(m=>`<th>${m}</th>`).join('')+'</tr>';
 for(const v of ["baseline","tiny64","tiny32","tiny32b4","tiny16"]){h+=`<tr><td>${v}</td>`;
  for(const m of ms){const c=rows.filter(r=>r.machine==m&&r.variant==v&&r.precision==prec).pop();
   h+=`<td>${c?(+c.hmean).toFixed(4):'—'}</td>`}h+='</tr>'}return h+'</table>'}
function deltaTbl(rows){const ms=[...new Set(rows.map(r=>r.machine))];
 let h='<table><tr><th>&Delta;</th>'+ms.map(m=>`<th>${m}</th>`).join('')+'</tr>';
 for(const v of ["baseline","tiny64","tiny32","tiny32b4","tiny16"]){h+=`<tr><td>${v}</td>`;
  for(const m of ms){const f=rows.filter(r=>r.machine==m&&r.variant==v&&r.precision=='fp32').pop();
   const i=rows.filter(r=>r.machine==m&&r.variant==v&&r.precision=='int8').pop();
   if(f&&i){const d=(+i.hmean)-(+f.hmean);h+=`<td class="${d<-0.005?'neg':''}">${d>=0?'+':''}${d.toFixed(4)}</td>`}
   else h+='<td>—</td>'}h+='</tr>'}return h+'</table>'}
async function tick(){try{
 const s=await (await fetch('/api/status')).json();
 document.getElementById('ts').textContent='zadnje: '+new Date().toLocaleTimeString();
 document.getElementById('progress').innerHTML=s.machines.map(m=>{
  let txt=m.state=='done'?'zavrseno ✔':m.state=='queued'?'u redu cekanja':
   `${m.variant||'?'} · epoha ${m.epoch}/${m.epochs}`+(m.eta_min!=null?` · ~${m.eta_min} min do kraja varijante`:'')+` · ${m.done_variants}/5 varijanti`;
  return `<div class="mrow"><div class="mname">${m.machine}</div>
   <div class="bar"><div class="fill ${m.state=='done'?'done':''}" style="width:${(m.progress*100).toFixed(1)}%"></div></div>
   <div class="stat">${txt}</div></div>`}).join('');
 const run=s.machines.find(m=>m.state=='running');
 document.getElementById('spark').innerHTML=run?spark(run.loss,run.val_loss):'<i style="color:var(--mut)">nista se trenutno ne trenira</i>';
 document.getElementById('tbl').innerHTML=pivot(s.results,'fp32')+pivot(s.results,'int8');
 document.getElementById('delta').innerHTML=deltaTbl(s.results);
}catch(e){document.getElementById('ts').textContent='greska: '+e}}
tick();setInterval(tick,5000);
</script></div></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/status"):
            body = json.dumps({"machines": [machine_status(m) for m in MACHINES],
                               "results": read_results()}).encode()
            ctype = "application/json"
        else:
            body = PAGE.encode()
            ctype = "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):  # tisina u konzoli
        pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"LIVE dashboard: http://localhost:{args.port}  (Ctrl+C za kraj)")
    srv.serve_forever()


if __name__ == "__main__":
    main()
