"""Pokrece cijeli fizicki run jednom komandom: alat + panel, redom i povezano.

ZASTO POSTOJI. Rucno pokretanje ima cetiri koraka koji moraju da se poklope --
alat, ime run direktorija koje se sazna tek posle njegovog starta, panel koji
mora da gleda BAS taj `serial.log`, i gasenje starog panela sa istog porta.
16.08.2026 su tri odvojena pokusaja propala bas na tim spojevima: stari panel je
drzao port pa je novi tiho umro, a u pregledacu se i dalje vidjelo stanje iz
proslog runa.

SIGURNOSNA POTVRDA. `physical_fan_experiment.py` inace trazi da operater ukuca
`DA` -- potvrdu da je ventilator bezbjedno montiran, da radi normalno i da se
lopatice nece dodirivati. Ova skripta tu potvrdu NE izmislja: trazi je kao
`--montaza-potvrdio "<ime>"` i doslovno je upisuje u `events.csv` i u ovaj
konzolni ispis. Bez tog argumenta ne radi nista. Potvrdu daje covjek koji gleda
postavku; skripta je samo prenosi.

Primjer:

    python pc/tools/start_fan_run.py --session-id cold-start-07 \
        --montaza-potvrdio "Mihajlo, ventilator na punjacu, radi normalno"
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "physical_fan"
PANEL_PORT = 8772


def newest_run(before: set[Path]) -> Path | None:
    now = {p for p in RESULTS.glob("run_*") if p.is_dir()}
    fresh = now - before
    return max(fresh, key=lambda p: p.name) if fresh else None


def panel_port_busy(port: int) -> bool:
    import socket

    with socket.socket() as sock:
        return sock.connect_ex(("127.0.0.1", port)) == 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--session-id", required=True)
    parser.add_argument(
        "--montaza-potvrdio", required=True, metavar="POTVRDA",
        help="doslovna operaterova potvrda bezbjedne montaze; ide u zapis runa",
    )
    parser.add_argument("--fan-id", default="fan01")
    parser.add_argument("--port", default="COM3")
    parser.add_argument("--distance-cm", default="20")
    parser.add_argument("--angle-deg", default="90")
    parser.add_argument("--room", default="soba")
    parser.add_argument("--fan-speed-or-voltage", default="usb-5v-punjac")
    parser.add_argument("--plan", default="full", choices=("full", "short"))
    parser.add_argument("--http-port", type=int, default=PANEL_PORT)
    args = parser.parse_args(argv)

    if panel_port_busy(args.http_port):
        print(f"port {args.http_port} je zauzet -- stari panel jos radi. "
              "Ugasi ga pa pokreni ponovo.")
        return 2

    python = sys.executable
    command_file = RESULTS / f"cmd_{args.fan_id}.txt"
    if command_file.exists():
        # Alat cita command file od pocetka; zaostale komande iz proslog runa
        # bi se odmah izvrsile.
        command_file.unlink()

    before = {p for p in RESULTS.glob("run_*") if p.is_dir()}
    tool = subprocess.Popen([
        python, str(ROOT / "pc" / "tools" / "physical_fan_experiment.py"), "run",
        "--port", args.port,
        "--fan-id", args.fan_id,
        "--session-id", args.session_id,
        "--distance-cm", args.distance_cm,
        "--angle-deg", args.angle_deg,
        "--room", args.room,
        "--fan-speed-or-voltage", args.fan_speed_or_voltage,
        "--command-file", str(command_file),
        "--notes", f"montazu potvrdio: {args.montaza_potvrdio}",
        "--ready",
    ], cwd=str(ROOT))

    run_dir = None
    for _ in range(60):
        time.sleep(0.5)
        run_dir = newest_run(before)
        if run_dir is not None:
            break
        if tool.poll() is not None:
            print("alat je izasao prije nego sto je napravio run direktorij")
            return 1
    if run_dir is None:
        print("run direktorij se nije pojavio")
        tool.terminate()
        return 1

    print(f"run:   {run_dir}")
    print(f"potvrda montaze: {args.montaza_potvrdio}")

    panel = subprocess.Popen([
        python, str(ROOT / "pc" / "tools" / "asd_panel.py"),
        "--command-file", str(command_file),
        "--follow", str(run_dir / "serial.log"),
        "--plan", args.plan,
        "--http-port", str(args.http_port),
        "--no-browser",
    ], cwd=str(ROOT))

    print(f"panel: http://127.0.0.1:{args.http_port}/")
    print("spremno -- klikni 'Pokreni ucenje' u panelu")
    try:
        tool.wait()
    except KeyboardInterrupt:
        pass
    finally:
        panel.terminate()
    return tool.returncode or 0


if __name__ == "__main__":
    raise SystemExit(main())
