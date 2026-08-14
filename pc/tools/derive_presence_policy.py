r"""Izvodi prag za test prisustva masine SAMO iz normalnih podataka.

Faza 2 treba da razlikuje "masina radi" od "masine nema / stala je" prije nego
Faza 3 (f0) i Faza 5 (near/far) daju bilo kakav dokaz o rezimu ili buci. Jedina
velicina koja je za to dostupna sada je NIVO signala, koji uredjaj vec mjeri po
Fazi 1 (`rms_dbfs`).

Prag se ne smije izvesti iz target anomalija. Zato se mjeri koliko NORMALAN rad
prirodno varira po nivou, i margina se postavlja ispod tog rasipanja:

    prisutna_masina  <=>  rms_dbfs >= kalibrisana_sredina - K

`K` mora biti veci od prirodne varijacije normalnog rada, inace bi normalan rad
sam sebe prijavio kao odsutnu masinu. Mjeri se u tri nivoa:

  1. unutar jedne brzine  -- najstroze, odgovara ustaljenom rezimu;
  2. preko svih brzina    -- ako se kalibrise na vise rezima;
  3. unutar jednog klipa  -- varijacija po 10 s prozorima, jer uredjaj odlucuje
     po prozoru, ne po klipu.

Upotreba (iz korijena repozitorija):

    .venv\Scripts\python.exe pc\tools\derive_presence_policy.py
    .venv\Scripts\python.exe pc\tools\derive_presence_policy.py --write
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import soundfile as sf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
FAN = ROOT / "data" / "dcase2026_dev" / "fan"
OUT = ROOT / "pc" / "config" / "asd_presence_policy_v1.json"
SR = 16000
WIN = 4096          # isti hop kao psd_live (256 ms)
SCHEMA = "asd-presence-policy-v1.0.0"


def rms_dbfs(x: np.ndarray) -> float:
    x = x.astype(np.float64)
    dc = x.mean()
    var = np.mean((x - dc) ** 2)
    return 20.0 * np.log10(np.sqrt(var)) if var > 0 else -np.inf


def clip_levels(paths: list[Path], n_consec: int = 3
                ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Vraca (nivo po klipu, odstupanje prozora, odstupanje trojki prozora).

    Treca velicina je ono na cemu se odluka STVARNO donosi: uredjaj trazi
    `n_consec` uzastopnih prozora ispod praga, pa je relevantna najniza sredina
    po `n_consec` uzastopnih prozora, a ne najnizi pojedinacni prozor. Sam
    prozor ima tezak rep koji trojka usrednji.
    """
    per_clip = []
    within = []
    runs = []
    for p in paths:
        y, sr = sf.read(p, dtype="float32", always_2d=True)
        if sr != SR:
            raise SystemExit(f"{p}: {sr} Hz")
        ch = y[:, 0]
        c = rms_dbfs(ch)
        if not np.isfinite(c):
            continue
        per_clip.append(c)
        n = len(ch) // WIN
        w = np.array([rms_dbfs(ch[i * WIN:(i + 1) * WIN]) for i in range(n)])
        w = w[np.isfinite(w)]
        if w.size == 0:
            continue
        # odstupanje prozora od sredine SVOG klipa: varijacija koju uredjaj vidi
        # kroz jedan neprekidan rad, bez uticaja razlike klipova
        d = w - c
        within.extend(d.tolist())
        if d.size >= n_consec:
            kernel = np.ones(n_consec) / n_consec
            runs.extend(np.convolve(d, kernel, mode="valid").tolist())
    return np.array(per_clip), np.array(within), np.array(runs)


def describe(name: str, v: np.ndarray) -> dict:
    d = {
        "n": int(v.size),
        "mean": float(np.mean(v)),
        "sd": float(np.std(v, ddof=1)) if v.size > 1 else 0.0,
        "min": float(np.min(v)),
        "max": float(np.max(v)),
        "p01": float(np.percentile(v, 1)),
        "p99": float(np.percentile(v, 99)),
    }
    print(f"{name:34s} n={d['n']:5d}  sredina {d['mean']:7.2f}  sd {d['sd']:5.2f}  "
          f"opseg {d['min']:7.2f}..{d['max']:7.2f}  p1 {d['p01']:7.2f}")
    return d


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true",
                    help="zapisi verzionisani JSON u pc/config/")
    args = ap.parse_args()

    target = sorted(list(FAN.glob("train/*target_train_normal*.wav")) +
                    list(FAN.glob("test/*target_test_normal*.wav")))
    source = sorted(FAN.glob("train/*source_train_normal*.wav"))
    if not target or not source:
        raise SystemExit("nema fan klipova — provjeri data/dcase2026_dev/fan")

    print(f"target normalnih: {len(target)}   source normalnih: {len(source)}\n")

    stats: dict = {}
    n_consec = 3

    # 1. unutar jedne brzine
    per_speed = {}
    for spd in ("spd_1", "spd_2", "spd_3"):
        paths = [p for p in target if spd in p.name]
        if len(paths) < 3:
            continue
        c, w, r = clip_levels(paths, n_consec)
        per_speed[spd] = {
            "per_clip": describe(f"target {spd} (po klipu)", c),
            "within_clip": describe(f"target {spd} (prozor - klip)", w),
            "consec_runs": describe(f"target {spd} (trojke prozora)", r),
        }
    stats["per_speed"] = per_speed

    # 2. preko svih brzina
    c_all, w_all, r_all = clip_levels(target, n_consec)
    stats["all_speeds"] = {
        "per_clip": describe("target sve brzine (po klipu)", c_all),
        "within_clip": describe("target sve brzine (prozor - klip)", w_all),
        "consec_runs": describe("target sve brzine (trojke)", r_all),
    }

    # 3. source korpus kao kontrola: 200 klipova, drugi fizicki primjerci.
    # Ovo je najveci uzorak i najtezi rep, pa je on mjerodavan za marginu.
    c_src, w_src, r_src = clip_levels(source[:200], n_consec)
    stats["source_control"] = {
        "per_clip": describe("source kontrola (po klipu)", c_src),
        "within_clip": describe("source kontrola (prozor - klip)", w_src),
        "consec_runs": describe("source kontrola (trojke)", r_src),
    }

    # --- izbor margine ---
    #
    # VAZNO: nivo PO KLIPU se NE koristi. DCASE klipovi su normalizovani po
    # nivou -- izmjereno sd 0,02 dB preko 60 target klipova, sto je artefakt
    # skupa podataka, ne fizika. Stvarni ventilator na stvarnoj udaljenosti
    # varira mnogo vise. Zato u marginu ulazi samo varijacija UNUTAR klipa,
    # koja je stvarna akusticka varijacija normalnog rada.
    #
    # Odluka se donosi po `n_consec` uzastopnih prozora, pa je mjerodavna
    # statistika najniza sredina po trojki, a ne najnizi pojedinacni prozor.
    # Sigma racun se ne koristi sam, jer raspodjela ima tezak rep u oba smjera
    # (source kontrola: pojedinacni prozori od -8,3 do +13,0 dB).
    sd_run = max(
        stats["source_control"]["consec_runs"]["sd"],
        stats["all_speeds"]["consec_runs"]["sd"],
    )
    worst_run = min(
        stats["source_control"]["consec_runs"]["min"],
        stats["all_speeds"]["consec_runs"]["min"],
    )
    worst_window = min(
        stats["source_control"]["within_clip"]["min"],
        stats["all_speeds"]["within_clip"]["min"],
    )
    margin_6s = 6.0 * sd_run
    # Najgori vidjeni normalan pad po trojki, plus 3 dB rezerve.
    margin_observed = abs(worst_run) + 3.0
    absent_margin = float(np.ceil(max(margin_6s, margin_observed)))

    print(f"\nsd po klipu se NE koristi (DCASE je normalizovao nivo, sd 0,02 dB)")
    print(f"sd po trojki prozora (max):          {sd_run:5.2f} dB")
    print(f"6 sigma po trojki:                   {margin_6s:5.2f} dB")
    print(f"najgori normalan pojedinacni prozor: {worst_window:5.2f} dB")
    print(f"najgori normalan pad po trojki:      {worst_run:5.2f} dB")
    print(f"najgori + 3 dB rezerve:              {margin_observed:5.2f} dB")
    print(f"\nMARGINA ODSUSTVA MASINE:             {absent_margin:5.1f} dB")
    print("interpretacija: prozor je 'masina prisutna' dok je nivo iznad")
    print(f"                (kalibrisana sredina - {absent_margin:.1f} dB),")
    print(f"                a odsutna tek poslije {n_consec} uzastopna takva prozora")
    print("\nOGRANICENJE: margina je izvedena iz snimaka, ne iz fizickog")
    print("ventilatora. Mora se ponoviti kad ventilator bude dostupan.")

    policy = {
        "schema_version": SCHEMA,
        "derived_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": ("machine-presence gate for Faza 2 event semantics; not an "
                  "anomaly threshold and not a fault diagnosis"),
        "target_anomalies_used": False,
        "derivation": {
            "data": "DCASE 2026 dev fan, target normal (train+test) and source normal control",
            "window_samples": WIN,
            "rule": ("present <=> rms_dbfs >= calibrated_mean_dbfs - absent_margin_db, "
                     "sustained for min_consecutive_windows"),
            "margin_rule": ("max(6 * sd_of_n_consec_window_runs, "
                            "abs(worst_observed_normal_run_dip) + 3 dB), "
                            "rounded up to whole dB"),
            "per_clip_level_excluded": (
                "DCASE clips are level-normalised: sd across 60 target normal clips "
                "is 0.02 dB. That is a dataset artefact, not physical variation, so "
                "cross-clip level contributes nothing to the margin. Only "
                "within-clip window variation is used."),
            "decision_statistic": (
                "lowest mean over n_consec consecutive windows, because the device "
                "requires n_consec consecutive windows below the gate; single-window "
                "tails (source control: -8.3 to +13.0 dB) are averaged out by the run."),
            "limitation": (
                "Derived from recordings, not from a physical fan. Must be "
                "re-derived once a physical fan is available."),
        },
        "policy": {
            "absent_margin_db": absent_margin,
            "min_consecutive_windows": n_consec,
            "min_consecutive_origin": ("isti N_CONSEC kao anomaly odluka u psd_live.c; "
                                       "trajna promjena, ne pojedinacni prozor"),
        },
        "measured": stats,
        "change_rule": ("Any change requires a new schema version and evidence from "
                        "normal-only data before any target-anomaly evaluation."),
    }

    if args.write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(policy, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        print(f"\nzapisano: {OUT.relative_to(ROOT)}")
    else:
        print("\n(--write da se zapise JSON)")


if __name__ == "__main__":
    main()
