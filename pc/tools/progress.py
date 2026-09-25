"""Zivo pracenje eksperimenta u pregledacu.

Eksperimenti (bench_*.py) mogu trajati po vise minuta i pisu redove kako
napreduju. Ovaj alat te redove sluzi na http://localhost:8771 i osvjezava sam,
plus prikazuje koji su rezultati vec zapisani u results/.

Upotreba (iz pc/):
    ../.venv/Scripts/python.exe tools/progress.py --watch "putanja/do/izlaza.txt"

Bez --watch prati samo results/ folder. Prekid: Ctrl+C.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
WATCH: Path | None = None

NOISE = re.compile(r"tensorflow|oneDNN|XNNPACK|UserWarning|warnings\.warn|absl|"
                   r"it/s\]|To enable|TF 2\.20|migration|ai\.google|for details")


def tail(p: Path, n: int = 60) -> list[str]:
    if not p or not p.exists():
        return []
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:                                            # noqa: BLE001
        return []
    return [l for l in lines if l.strip() and not NOISE.search(l)][-n:]


def state() -> dict:
    files = []
    if RESULTS.exists():
        for p in sorted(RESULTS.glob("*.json"), key=lambda x: -x.stat().st_mtime)[:12]:
            files.append({
                "ime": p.name,
                "kb": round(p.stat().st_size / 1024, 1),
                "kad": time.strftime("%H:%M:%S", time.localtime(p.stat().st_mtime)),
            })
    lines = tail(WATCH) if WATCH else []
    running = bool(WATCH and WATCH.exists() and
                   time.time() - WATCH.stat().st_mtime < 90)
    return {"linije": lines, "fajlovi": files, "radi": running,
            "sada": time.strftime("%H:%M:%S")}


PAGE = """<!doctype html><html lang="sr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Napredak eksperimenta</title><style>
:root{--bg:#0c0d15;--panel:#14151f;--rule:#272839;--ink:#eceaf4;--ink2:#b3b0c4;
      --ink3:#7f7c93;--ok:#4ec49b;--amber:#f0a83c;--accent:#d95fa8;
      --mono:ui-monospace,"Cascadia Mono",Consolas,monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);padding:26px;
     font-family:ui-sans-serif,"Segoe UI",system-ui,sans-serif}
.wrap{max-width:1000px;margin:0 auto}
h1{font-size:21px;margin:0 0 4px;letter-spacing:-.02em}
.sub{font-family:var(--mono);font-size:11.5px;color:var(--ink3);
     letter-spacing:.08em;text-transform:uppercase;margin:0 0 22px}
.badge{font-family:var(--mono);font-size:11px;padding:3px 10px;border-radius:999px;
       text-transform:uppercase;letter-spacing:.07em}
.run{background:#33270f;color:var(--amber)} .done{background:#14312a;color:var(--ok)}
.panel{background:var(--panel);border:1px solid var(--rule);border-radius:12px;
       padding:18px;margin-bottom:16px}
h2{font-size:12px;font-family:var(--mono);letter-spacing:.1em;text-transform:uppercase;
   color:var(--ink3);font-weight:500;margin:0 0 12px}
pre{font-family:var(--mono);font-size:12.5px;line-height:1.7;margin:0;color:var(--ink2);
    white-space:pre-wrap;word-break:break-word;max-height:60vh;overflow:auto}
pre .hl{color:var(--ink);font-weight:600}
table{width:100%;border-collapse:collapse;font-family:var(--mono);font-size:12px}
td{padding:7px 10px 7px 0;border-bottom:1px solid var(--rule);color:var(--ink2)}
td:first-child{color:var(--ink)} td:last-child{text-align:right;color:var(--ink3)}
tr:last-child td{border-bottom:none}
</style></head><body><div class="wrap">
<h1>Napredak eksperimenta</h1>
<p class="sub">osvjezava se samo &middot; <span id="st" class="badge run">ucitavam</span>
 &middot; <span id="t"></span></p>
<div class="panel"><h2>Izlaz</h2><pre id="log">cekam...</pre></div>
<div class="panel"><h2>Zapisani rezultati</h2><table id="files"></table></div>
<script>
async function tick(){
  try{
    const s = await (await fetch('/data')).json();
    const st = document.getElementById('st');
    st.textContent = s.radi ? 'u toku' : 'zavrseno';
    st.className = 'badge ' + (s.radi ? 'run' : 'done');
    document.getElementById('t').textContent = s.sada;
    const esc = t => t.replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
    document.getElementById('log').innerHTML = s.linije.length
      ? s.linije.map(l => /±|hmean|auc|AUC|najbolji|zapisano/.test(l)
          ? '<span class="hl">'+esc(l)+'</span>' : esc(l)).join('\\n')
      : 'nema izlaza jos';
    document.getElementById('files').innerHTML = s.fajlovi.map(f =>
      '<tr><td>'+esc(f.ime)+'</td><td>'+f.kb+' KB</td><td>'+f.kad+'</td></tr>').join('');
  }catch(e){}
  setTimeout(tick, 2000);
}
tick();
</script></div></body></html>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/data"):
            body = json.dumps(state()).encode()
            ctype = "application/json"
        else:
            body = PAGE.encode("utf-8")
            ctype = "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    global WATCH
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", default=None, help="fajl sa izlazom eksperimenta")
    ap.add_argument("--port", type=int, default=8771)
    args = ap.parse_args()
    if args.watch:
        WATCH = Path(args.watch)
    print(f"pratilac: http://localhost:{args.port}   (Ctrl+C za prekid)")
    try:
        HTTPServer(("127.0.0.1", args.port), H).serve_forever()
    except KeyboardInterrupt:
        print("\nprekinuto")


if __name__ == "__main__":
    main()
