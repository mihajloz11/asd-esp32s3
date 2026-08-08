"""ZIVO PRACENJE: cita ESP32-S3 sa serijskog porta i crta u pregledacu.

Firmware mora biti build sa ASD_LIVE_ADAPT=1. Uredjaj prvo 60 s kalibrise
(budi tih), pa neprekidno detektuje i za svaki prozor od 2 s ispisuje:

    DET 17 score=48.51 thr=62.46 led=1 anom=0 total_anom=0 normal

Skript to prima, sluzi stranicu na http://localhost:8770 i crta uzivo:
grafik score-a naspram praga, stanje LED-a, i spisak dogadjaja. Lupi po stolu
ili pusti muziku i vidi kako score preskoci prag.

Upotreba (iz pc/):
    ../.venv/Scripts/python.exe tools/live_monitor.py --port COM4
    pa otvori http://localhost:8770

Prekid: Ctrl+C.
"""
from __future__ import annotations

import argparse
import json
import re
import threading
import time
import webbrowser
from collections import deque
from http.server import BaseHTTPRequestHandler, HTTPServer

try:
    import serial  # pyserial
except ImportError:
    raise SystemExit("nema pyserial: ../.venv/Scripts/python.exe -m pip install pyserial")

DET_RE = re.compile(
    r"DET (\d+) score=([-\d.]+) lo=([-\d.]+) hi=([-\d.]+) led=(\d+) anom=(\d+) "
    r"total_anom=(\d+)"
)
CAL_RE = re.compile(r"CAL\s+(\d+)/(\d+)\s+score=([-\d.]+)")
WAIT_RE = re.compile(r"WAIT (\d+)/(\d+) score=([-\d.]+) spread=([-\d.]+)")
THR_RE = re.compile(r"ADAPTTHR .*thr=([-\d.]+) lo=([-\d.]+) factory=([-\d.]+)")

STATE = {
    "phase": "cekam",          # cekam | kalibracija | detekcija
    "cal": [],                 # score-ovi kalibracije
    "cal_total": 0,
    "det": [],                 # zadnjih N score-ova detekcije
    "thr": None,
    "thr_lo": None,
    "factory": None,
    "led": 1,
    "anom_total": 0,
    "n": 0,
    "events": [],              # prelazi normal <-> anomalija
    "wait_i": 0,
    "wait_n": 0,
    "wait_score": 0.0,
    "last_update": 0.0,
}
LOCK = threading.Lock()
MAX_POINTS = 120


def serial_reader(port: str, baud: int) -> None:
    while True:
        try:
            ser = serial.Serial(port, baud, timeout=1.0)
        except Exception as e:                                  # noqa: BLE001
            print(f"ne mogu da otvorim {port}: {e} — pokusavam ponovo za 3 s")
            time.sleep(3)
            continue

        print(f"citam {port} @ {baud}. Otvori http://localhost:8770")
        # reset ploce da uhvatimo i fazu kalibracije od pocetka
        ser.dtr = False
        ser.rts = True
        time.sleep(0.15)
        ser.rts = False

        prev_anom = 0
        try:
            while True:
                raw = ser.readline()
                if not raw:
                    continue
                line = raw.decode("utf-8", "replace").strip()

                m = WAIT_RE.search(line)
                if m:
                    with LOCK:
                        STATE["phase"] = "umirivanje"
                        STATE["wait_i"] = int(m.group(1))
                        STATE["wait_n"] = int(m.group(2))
                        STATE["wait_score"] = float(m.group(3))
                        STATE["last_update"] = time.time()
                    print(line)
                    continue

                m = CAL_RE.search(line)
                if m:
                    with LOCK:
                        STATE["phase"] = "kalibracija"
                        STATE["cal"].append(float(m.group(3)))
                        STATE["cal_total"] = int(m.group(2))
                        STATE["last_update"] = time.time()
                    print(line)
                    continue

                m = THR_RE.search(line)
                if m:
                    with LOCK:
                        STATE["thr"] = float(m.group(1))
                        STATE["thr_lo"] = float(m.group(2))
                        STATE["factory"] = float(m.group(3))
                    print(line)
                    continue

                m = DET_RE.search(line)
                if m:
                    n = int(m.group(1))
                    score = float(m.group(2))
                    thr_lo = float(m.group(3))
                    thr = float(m.group(4))
                    led = int(m.group(5))
                    anom = int(m.group(6))
                    with LOCK:
                        STATE["phase"] = "detekcija"
                        STATE["n"] = n
                        STATE["thr"] = thr
                        STATE["thr_lo"] = thr_lo
                        STATE["led"] = led
                        STATE["anom_total"] = int(m.group(7))
                        STATE["det"].append(score)
                        if len(STATE["det"]) > MAX_POINTS:
                            del STATE["det"][0]
                        if anom != prev_anom:
                            STATE["events"].insert(0, {
                                "n": n,
                                "score": round(score, 2),
                                "kind": "anomalija" if anom else "povratak u normalu",
                                "t": time.strftime("%H:%M:%S"),
                            })
                            del STATE["events"][12:]
                        STATE["last_update"] = time.time()
                    prev_anom = anom
                    print(line)
                    continue
        except Exception as e:                                  # noqa: BLE001
            print(f"prekid veze: {e} — ponovo za 2 s")
            try:
                ser.close()
            except Exception:                                   # noqa: BLE001
                pass
            time.sleep(2)


PAGE = """<!doctype html><html lang="sr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Zivo pracenje - ASD na ESP32-S3</title>
<style>
:root{
  --bg:#0c0d15; --panel:#14151f; --panel2:#1b1c28; --ink:#eceaf4;
  --ink2:#b3b0c4; --ink3:#7f7c93; --rule:#272839;
  --accent:#d95fa8; --indigo:#8c79e0; --amber:#f0a83c;
  --ok:#4ec49b; --bad:#e2695f;
  --mono:ui-monospace,"Cascadia Mono",Consolas,monospace;
  --sans:ui-sans-serif,"Segoe UI",system-ui,sans-serif;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);padding:28px}
.wrap{max-width:1040px;margin:0 auto}
h1{font-size:22px;margin:0 0 4px;letter-spacing:-.02em}
.sub{font-family:var(--mono);font-size:12px;color:var(--ink3);letter-spacing:.08em;
     text-transform:uppercase;margin:0 0 24px}
.top{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:20px}
.tile{background:var(--panel);border:1px solid var(--rule);border-radius:10px;padding:16px 18px}
.tile .k{font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase;
         color:var(--ink3);margin-bottom:6px}
.tile .v{font-family:var(--mono);font-size:26px;font-weight:600;font-variant-numeric:tabular-nums;
         letter-spacing:-.02em}
.led-box{display:flex;align-items:center;gap:14px}
.led{width:34px;height:34px;border-radius:50%;background:#2a2b3a;
     box-shadow:inset 0 0 0 1px var(--rule);transition:background .15s,box-shadow .15s}
.led.on{background:var(--ok);box-shadow:0 0 22px rgba(78,196,155,.55),inset 0 0 0 1px rgba(255,255,255,.2)}
.led.off{background:#3a2020;box-shadow:inset 0 0 0 1px var(--bad)}
.led-txt{font-family:var(--mono);font-size:13px;color:var(--ink2)}
.panel{background:var(--panel);border:1px solid var(--rule);border-radius:12px;padding:18px;margin-bottom:16px}
canvas{width:100%;height:260px;display:block}
.legend{display:flex;gap:20px;font-family:var(--mono);font-size:11px;color:var(--ink3);margin-top:10px;flex-wrap:wrap}
.legend i{display:inline-block;width:14px;height:3px;border-radius:2px;margin-right:6px;vertical-align:middle}
.ev{font-family:var(--mono);font-size:12.5px;display:flex;justify-content:space-between;
    padding:8px 0;border-bottom:1px solid var(--rule);color:var(--ink2)}
.ev:last-child{border-bottom:none}
.ev .bad{color:var(--bad)} .ev .ok{color:var(--ok)}
.hint{font-size:13.5px;color:var(--ink3);margin:0}
.badge{font-family:var(--mono);font-size:11px;padding:3px 9px;border-radius:999px;
       text-transform:uppercase;letter-spacing:.07em}
.b-cal{background:#241f3d;color:var(--indigo)}
.b-det{background:#33270f;color:var(--amber)}
.b-wait{background:#1e1f2b;color:var(--ink3)}
h2{font-size:13px;font-family:var(--mono);letter-spacing:.1em;text-transform:uppercase;
   color:var(--ink3);font-weight:500;margin:0 0 12px}
</style></head><body><div class="wrap">
<h1>Zivo pracenje detekcije</h1>
<p class="sub">ESP32-S3 &middot; prozor 2 s &middot; <span id="phase" class="badge b-wait">cekam ploc&#117;</span></p>

<div class="top">
  <div class="tile"><div class="k">Score</div><div class="v" id="score">&mdash;</div></div>
  <div class="tile"><div class="k">Normalan opseg</div><div class="v" id="thr">&mdash;</div></div>
  <div class="tile"><div class="k">Anomalija ukupno</div><div class="v" id="anom">&mdash;</div></div>
  <div class="tile"><div class="k">LED (GPIO 2)</div>
    <div class="led-box"><div class="led" id="led"></div><div class="led-txt" id="ledtxt">&mdash;</div></div>
  </div>
</div>

<div class="panel">
  <canvas id="c"></canvas>
  <div class="legend">
    <span><i style="background:var(--indigo)"></i>kalibracija</span>
    <span><i style="background:var(--amber)"></i>detekcija</span>
    <span><i style="background:var(--bad)"></i>prag</span>
  </div>
</div>

<div class="panel">
  <h2>Dogadjaji</h2>
  <div id="events"><p class="hint">Jos nema prelaza. Lupi po stolu ili pusti muziku.</p></div>
</div>

<script>
const c=document.getElementById('c'),ctx=c.getContext('2d');
function css(n){return getComputedStyle(document.documentElement).getPropertyValue(n).trim()}
function draw(s){
  const dpr=window.devicePixelRatio||1,W=c.clientWidth,H=260;
  c.width=W*dpr;c.height=H*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.clearRect(0,0,W,H);
  const L=46,R=14,T=14,B=26,pw=W-L-R,ph=H-T-B;
  const pts=s.cal.concat(s.det);
  let mx=Math.max(70,s.thr?s.thr*1.25:70,...(pts.length?pts:[70]));
  const y=v=>T+ph-(v/mx)*ph, x=i=>L+(pts.length<2?0:(i/(pts.length-1))*pw);
  ctx.strokeStyle=css('--rule');ctx.fillStyle=css('--ink3');
  ctx.font='11px ui-monospace,monospace';ctx.textAlign='right';
  for(let g=0;g<=4;g++){const v=mx*g/4;
    ctx.beginPath();ctx.moveTo(L,y(v));ctx.lineTo(W-R,y(v));ctx.stroke();
    ctx.fillText(v.toFixed(0),L-8,y(v)+4);}
  if(s.thr){ctx.strokeStyle=css('--bad');ctx.setLineDash([7,4]);ctx.lineWidth=1.5;
    ctx.beginPath();ctx.moveTo(L,y(s.thr));ctx.lineTo(W-R,y(s.thr));ctx.stroke();
    if(s.thr_lo){ctx.beginPath();ctx.moveTo(L,y(s.thr_lo));ctx.lineTo(W-R,y(s.thr_lo));ctx.stroke();}
    ctx.setLineDash([]);
    if(s.thr_lo){ctx.fillStyle='rgba(78,196,155,.07)';
      ctx.fillRect(L,y(s.thr),W-R-L,y(s.thr_lo)-y(s.thr));}}
  const seg=(arr,off,col)=>{if(!arr.length)return;
    ctx.strokeStyle=col;ctx.lineWidth=2;ctx.beginPath();
    arr.forEach((v,i)=>{const px=x(i+off),py=y(v);i?ctx.lineTo(px,py):ctx.moveTo(px,py)});
    ctx.stroke();ctx.fillStyle=col;
    arr.forEach((v,i)=>{ctx.beginPath();ctx.arc(x(i+off),y(v),2.4,0,7);ctx.fill()});};
  seg(s.cal,0,css('--indigo'));seg(s.det,s.cal.length,css('--amber'));
}
async function tick(){
  try{
    const s=await (await fetch('/data')).json();
    const ph=document.getElementById('phase');
    ph.textContent=s.phase==='detekcija'?'detekcija'
      :s.phase==='kalibracija'?('kalibracija '+s.cal.length+'/'+(s.cal_total||30))
      :s.phase==='umirivanje'?('cekam da se soba umiri '+s.wait_i+'/'+s.wait_n)
      :'cekam plocu';
    ph.className='badge '+(s.phase==='detekcija'?'b-det':s.phase==='kalibracija'?'b-cal':'b-wait');
    const last=s.det.length?s.det[s.det.length-1]:(s.cal.length?s.cal[s.cal.length-1]:null);
    document.getElementById('score').textContent=last!==null?last.toFixed(2):'\\u2014';
    const outside=s.thr&&last!==null&&(last>s.thr||(s.thr_lo&&last<s.thr_lo));
    document.getElementById('score').style.color=outside?css('--bad'):css('--ink');
    document.getElementById('thr').textContent=s.thr
      ?((s.thr_lo?s.thr_lo.toFixed(1):'0')+' - '+s.thr.toFixed(1)):'\\u2014';
    document.getElementById('thr').style.fontSize='19px';
    document.getElementById('anom').textContent=s.phase==='detekcija'?s.anom_total:'\\u2014';
    const led=document.getElementById('led');
    if(s.phase==='detekcija'){led.className='led '+(s.led?'on':'off');
      document.getElementById('ledtxt').textContent=s.led?'normalno':'ANOMALIJA';}
    else{led.className='led';document.getElementById('ledtxt').textContent='ceka kalibraciju';}
    const ev=document.getElementById('events');
    if(s.events.length){ev.innerHTML=s.events.map(e=>
      '<div class="ev"><span class="'+(e.kind==='anomalija'?'bad':'ok')+'">'+e.kind+
      '</span><span>score '+e.score+' &middot; prozor '+e.n+' &middot; '+e.t+'</span></div>').join('');}
    draw(s);
  }catch(e){}
  setTimeout(tick,500);
}
tick();window.addEventListener('resize',()=>{});
</script></div></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):                                  # tisi log
        pass

    def do_GET(self):
        if self.path.startswith("/data"):
            with LOCK:
                body = json.dumps(STATE).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        else:
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="COM4")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--http-port", type=int, default=8770)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    threading.Thread(target=serial_reader, args=(args.port, args.baud),
                     daemon=True).start()

    url = f"http://localhost:{args.http_port}"
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    print(f"monitor: {url}   (Ctrl+C za prekid)")
    try:
        HTTPServer(("127.0.0.1", args.http_port), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nprekinuto")


if __name__ == "__main__":
    main()
