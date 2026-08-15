"""Panel u pregledacu: virtuelni taster i virtuelne lampice.

ZASTO POSTOJI. Fizicki taster (GPIO10) i dvije diode (GPIO2, GPIO11) nisu
zalemljeni, a bez tastera `ASD_PSD_LIVE` nikad ne pocne ucenje. Panel daje isti
ulaz i isti izlaz preko konzole: klik salje `PRESS`/`HOLD` firmveru
(`firmware/esp32s3_asd/main/asd_cmd.c`), a lampice se crtaju iz `FLAGS` zapisa
koji emituje isti UI task koji pali diode. Ako su diode zalemljene, rade
paralelno i pokazuju isto -- panel ih ne zamjenjuje nego duplira.

DVA REZIMA.

  1. Samostalni (`--port COM3`): panel drzi serijski port. Za bring-up i probe,
     kad `physical_fan_experiment.py` ne radi.

  2. Uz zakljucani protokol (`--command-file ... --follow ...`): port drzi
     `physical_fan_experiment.py`; panel mu dopisuje `press`/`hold` u command
     file, a lampice cita iz `serial.log` tog runa. Tako se panel koristi i
     tokom valjanog mjerenja, bez drugog procesa na portu.

Panel nista ne odlucuje i ne ulazi u metrike. Mjerodavan zapis ostaje
telemetrija uredjaja (`BUTTON`, `STATE`, `EVENT`, `DET`).

Primjeri:

    python pc/tools/asd_panel.py --port COM3
    python pc/tools/asd_panel.py --command-file results/physical_fan/cmd.txt \
        --follow results/physical_fan/run_.../serial.log
"""
from __future__ import annotations

import argparse
import json
import re
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FLAGS_RE = re.compile(r"\bFLAGS\s+(?P<body>.*)$")
VBUTTON_RE = re.compile(r"\bVBUTTON\s+.*?result=(?P<result>\S+)")
DET_RE = re.compile(
    r"^DET\s+(?P<window>\d+)\s+score=(?P<score>\S+)\s+lo=\S+\s+"
    r"hi=(?P<threshold>\S+)\s+.*?\(uzastopnih=(?P<consecutive>\d+)\s+"
    r"nivo=(?P<level>\S+)\s+dBFS"
)
KV_RE = re.compile(r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>\S+)")

DEFAULT_PORT = 8772
LOG_LINES = 14

# Sto se pokazuje u logu panela. WAIT/CAL/QUALITY se namjerno preskacu -- ima ih
# stotine po sesiji i izgurali bi ono zbog cega se log i gleda.
LOGGED_RECORDS = {"VBUTTON", "BUTTON", "SESSION", "STATE", "EVENT", "ADAPTTHR"}


class PanelState:
    """Sve sto panel zna. Jedan lock, jer HTTP handleri idu u vise niti."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.flags: dict[str, str] = {}
        self.det: dict[str, str] = {}
        self.log: list[str] = []
        self.source = "ceka podatke"
        self.last_line_at = 0.0
        self.last_command = ""

    def feed(self, line: str) -> None:
        line = line.rstrip("\r\n").strip()
        if not line:
            return
        with self.lock:
            self.last_line_at = time.time()
            match = FLAGS_RE.search(line)
            if match:
                flags = {
                    m.group("key"): m.group("value")
                    for m in KV_RE.finditer(match.group("body"))
                }
                # Uredjaj ponavlja FLAGS na 5 s zbog hosta koji se kasno zakaci;
                # u log ide samo stvarna promjena, da se ostalo ne izgura.
                changed = flags != self.flags
                self.flags = flags
                if changed:
                    self._log(line)
                return
            det = DET_RE.match(line)
            if det:
                self.det = det.groupdict()
                self._log(line)
                return
            if line.split(" ", 1)[0] in LOGGED_RECORDS:
                self._log(line)

    def _log(self, line: str) -> None:
        self.log.append(line)
        del self.log[:-LOG_LINES]

    def snapshot(self) -> dict:
        with self.lock:
            age = time.time() - self.last_line_at if self.last_line_at else None
            return {
                "flags": dict(self.flags),
                "det": dict(self.det),
                "log": list(self.log),
                "source": self.source,
                "age_s": None if age is None else round(age, 1),
                "last_command": self.last_command,
            }


class SerialLink:
    """Rezim 1: panel drzi port i sam salje komande."""

    def __init__(self, state: PanelState, port: str, baud: int) -> None:
        import serial  # lokalno, da rezim 2 radi i bez pyseriala

        self.state = state
        self.ser = serial.Serial(port, baud, timeout=0.5)
        state.source = f"serijski port {port}"
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self) -> None:
        while True:
            try:
                raw = self.ser.readline()
            except Exception as exc:  # port otkacen usred rada
                self.state.feed(f"[panel] citanje prekinuto: {exc}")
                return
            if raw:
                self.state.feed(raw.decode("utf-8", errors="replace"))

    def send(self, verb: str) -> str:
        wire = b"PRESS\n" if verb == "press" else b"HOLD\n"
        self.ser.write(wire)
        self.ser.flush()
        return f"poslato {wire.decode().strip()} na port"


class CommandFileLink:
    """Rezim 2: komande idu u command file, telemetrija se cita iz serial.log.

    Time port ostaje kod `physical_fan_experiment.py`, koji je jedini koji
    smije da ga drzi tokom valjanog mjerenja.
    """

    def __init__(self, state: PanelState, command_file: Path,
                 follow: Path | None) -> None:
        self.state = state
        self.command_file = command_file
        command_file.parent.mkdir(parents=True, exist_ok=True)
        command_file.touch(exist_ok=True)
        state.source = f"command file {command_file.name}"
        if follow is not None:
            state.source += f" + {follow.name}"
            threading.Thread(target=self._tail, args=(follow,), daemon=True).start()

    def _tail(self, path: Path) -> None:
        offset = 0
        while True:
            try:
                if path.exists():
                    with path.open("r", encoding="utf-8", errors="replace") as handle:
                        handle.seek(offset)
                        for line in handle:
                            # serial.log je "utc<TAB>elapsed<TAB>linija"
                            self.state.feed(line.split("\t")[-1])
                        offset = handle.tell()
            except OSError:
                pass
            time.sleep(0.3)

    def send(self, verb: str) -> str:
        with self.command_file.open("a", encoding="utf-8") as handle:
            handle.write(f"{verb} panel\n")
        return f"upisano '{verb}' u {self.command_file.name}"


PAGE = """<!doctype html>
<meta charset="utf-8"><title>ASD panel</title>
<style>
 body{background:#14171c;color:#dfe4ea;font:15px/1.5 system-ui,sans-serif;
      margin:0;padding:28px;display:flex;justify-content:center}
 .wrap{width:min(680px,100%)}
 h1{font-size:17px;font-weight:600;margin:0 0 4px}
 .sub{color:#8b949e;font-size:13px;margin-bottom:22px}
 .lamps{display:flex;gap:34px;align-items:center;background:#1b1f26;
        border-radius:10px;padding:22px 26px;margin-bottom:16px}
 .lamp{text-align:center;flex:0 0 auto}
 .bulb{width:54px;height:54px;border-radius:50%;margin:0 auto 8px;
       border:2px solid #2c323c;background:#22262e;transition:none}
 .bulb.green{background:#2ee06a;border-color:#2ee06a;box-shadow:0 0 22px #2ee06a88}
 .bulb.red{background:#ff4d4d;border-color:#ff4d4d;box-shadow:0 0 22px #ff4d4d88}
 .lamp span{font-size:12px;color:#8b949e}
 .verdict{margin-left:auto;text-align:right}
 .verdict b{font-size:20px;display:block}
 .chips{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px}
 .chip{padding:5px 11px;border-radius:20px;background:#1b1f26;color:#5c636d;
       font-size:12.5px;border:1px solid #262b33}
 .chip.on{background:#1f3d2b;color:#7ee2a4;border-color:#2f5d40}
 .chip.alarm{background:#43201f;color:#ff8e8e;border-color:#6d2f2d}
 .btns{display:flex;gap:10px;margin-bottom:16px}
 button{flex:1;padding:13px;border:0;border-radius:8px;font-size:14.5px;
        font-weight:600;cursor:pointer;background:#2f6feb;color:#fff}
 button.alt{background:#2b313a;color:#dfe4ea}
 button:active{transform:translateY(1px)}
 table{width:100%;border-collapse:collapse;margin-bottom:16px;font-size:13.5px}
 td{padding:5px 0;border-bottom:1px solid #232830;color:#8b949e}
 td+td{text-align:right;color:#dfe4ea;font-variant-numeric:tabular-nums}
 pre{background:#101318;border-radius:8px;padding:12px;font-size:11.5px;
     color:#7d8896;max-height:190px;overflow:auto;margin:0}
 .foot{color:#5c636d;font-size:12px;margin-top:10px}
</style>
<div class="wrap">
 <h1>ASD panel &mdash; virtuelni taster i lampice</h1>
 <div class="sub" id="source">&nbsp;</div>

 <div class="lamps">
  <div class="lamp"><div class="bulb" id="green"></div><span>zelena / GPIO2</span></div>
  <div class="lamp"><div class="bulb" id="red"></div><span>crvena / GPIO11</span></div>
  <div class="verdict"><b id="mode">&mdash;</b><span id="state">&nbsp;</span></div>
 </div>

 <div class="chips">
  <div class="chip" id="c-waiting">ceka taster</div>
  <div class="chip" id="c-learning">uci</div>
  <div class="chip" id="c-learned">naucio</div>
  <div class="chip" id="c-anomaly">ANOMALIJA</div>
  <div class="chip" id="c-fault">kvar</div>
 </div>

 <div class="btns">
  <button onclick="send('press')">Kratak pritisak &mdash; pokreni ucenje</button>
  <button class="alt" onclick="send('hold')">Dug pritisak &mdash; nova kalibracija</button>
 </div>

 <table>
  <tr><td>prozor</td><td id="d-window">&mdash;</td></tr>
  <tr><td>score / prag</td><td id="d-score">&mdash;</td></tr>
  <tr><td>uzastopnih iznad praga</td><td id="d-cons">&mdash;</td></tr>
  <tr><td>nivo</td><td id="d-level">&mdash;</td></tr>
 </table>

 <pre id="log"></pre>
 <div class="foot" id="foot">&nbsp;</div>
</div>
<script>
let flags = {}, t0 = performance.now();

function send(verb){
  fetch('/'+verb, {method:'POST'})
    .then(r => r.json())
    .then(j => document.getElementById('foot').textContent = j.message)
    .catch(e => document.getElementById('foot').textContent = 'greska: '+e);
}

/* Obrasci su isti kao u asd_operator.c, pa lampica na ekranu titra kao dioda. */
function level(pattern, t){
  switch(pattern){
    case 'on': return true;
    case 'off': return false;
    case 'blink_5hz': return Math.floor(t/100) % 2 === 0;
    case 'flash_2s': return (t % 2000) < 60;
    case 'double_blink': {const p = t % 1000; return p < 120 || (p > 240 && p < 360);}
    default: return false;
  }
}

function paint(){
  const t = performance.now() - t0;
  document.getElementById('green').className =
    'bulb' + (level(flags.green || 'off', t) ? ' green' : '');
  document.getElementById('red').className =
    'bulb' + (level(flags.red || 'off', t) ? ' red' : '');
  requestAnimationFrame(paint);
}
requestAnimationFrame(paint);

function chip(id, on, alarm){
  const el = document.getElementById(id);
  el.className = 'chip' + (on ? (alarm ? ' alarm' : ' on') : '');
}

function poll(){
  fetch('/state').then(r => r.json()).then(s => {
    flags = s.flags || {};
    document.getElementById('mode').textContent = flags.mode || '—';
    document.getElementById('state').textContent = flags.state || '';
    document.getElementById('source').textContent =
      s.source + (s.age_s === null ? '' : '  ·  zadnji red prije ' + s.age_s + ' s');
    chip('c-waiting',  flags.waiting  === '1');
    chip('c-learning', flags.learning === '1');
    chip('c-learned',  flags.learned  === '1');
    chip('c-anomaly',  flags.anomaly  === '1', true);
    chip('c-fault',    flags.fault    === '1', true);
    const d = s.det || {};
    document.getElementById('d-window').textContent = d.window || '—';
    document.getElementById('d-score').textContent =
      d.score ? (d.score + '  /  ' + d.threshold) : '—';
    document.getElementById('d-cons').textContent = d.consecutive || '—';
    document.getElementById('d-level').textContent = d.level ? d.level + ' dBFS' : '—';
    document.getElementById('log').textContent = (s.log || []).join('\\n');
  }).catch(() => {});
}
setInterval(poll, 400); poll();
</script>
"""


def make_handler(state: PanelState, link):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # bez pristupnog loga u konzoli
            pass

        def _json(self, payload: dict, code: int = 200) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path.startswith("/state"):
                self._json(state.snapshot())
                return
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            verb = self.path.strip("/").lower()
            if verb not in ("press", "hold"):
                self._json({"message": "nepoznata komanda"}, 404)
                return
            try:
                message = link.send(verb)
            except Exception as exc:
                self._json({"message": f"greska: {exc}"}, 500)
                return
            with state.lock:
                state.last_command = verb
            print(message)
            self._json({"message": message})

    return Handler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", help="serijski port (rezim 1: panel drzi port)")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument(
        "--command-file", type=Path,
        help="rezim 2: dopisuj komande za physical_fan_experiment.py",
    )
    parser.add_argument(
        "--follow", type=Path,
        help="rezim 2: serial.log runa iz kojeg se citaju lampice",
    )
    parser.add_argument("--http-port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if bool(args.port) == bool(args.command_file):
        print("izaberi tacno jedno: --port (rezim 1) ili --command-file (rezim 2)")
        return 2

    state = PanelState()
    if args.port:
        link = SerialLink(state, args.port, args.baud)
    else:
        link = CommandFileLink(state, args.command_file, args.follow)

    url = f"http://127.0.0.1:{args.http_port}/"
    server = ThreadingHTTPServer(("127.0.0.1", args.http_port),
                                 make_handler(state, link))
    print(f"panel: {url}   ({state.source})")
    if not args.no_browser:
        threading.Timer(0.4, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nzatvaram panel")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
