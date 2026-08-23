"""Granice `asd_interference.c` iz normal-only prozora, bez ijedne ciljne anomalije.

ZASTO. Gate koji razlikuje nepouzdan prozor od stvarne promjene na masini je u
firmveru odavno napisan i povezan (`asd_events.c` ga zove za svaki DET prozor),
ali su mu granice bile `0.0` uz `enabled = 0`, jer ih nije imalo iz cega izvesti.
Ovaj alat ih izvodi, po istom obrascu kao `derive_presence_policy.py` i
`derive_temporal_policy.py`.

STA SE MJERI. Dvije velicine koje gate koristi, obje po prozoru od 10 s:

  tonalness_delta          koliko tonalnost prozora odstupa od one naucene pri
                           kalibraciji; ventilator ima stabilan tonalni potpis
                           od rotacije, a tudji zvuk ga razvodnjava

  subsegment_instability   koliko se pet podsegmenata unutar istog prozora
                           medjusobno razlikuju, u normalizovanim jedinicama
                           modela:

                             z_g[d] = (grupa_g[d] - norm_mean[d]) / norm_std[d]
                             instability = mean_d( std_g( z_g[d] ) )

                           Fizika iza toga: trajna promjena na masini izgleda
                           isto kroz cijeli prozor, pa su podsegmenti slozni.
                           Govor, vrata i koraci nisu -- ima pauza, ima udara.

KOJI PROZORI SMIJU DA UDJU. Samo normal-only: sve `phase=CAL` prozore (K1 ih
prihvata tek kad je masina potvrdjeno normalna) i, ako se eksplicitno zatrazi,
`DET` prozore uslova `normal_baseline`. Papiric, govor i vrata se **ne otvaraju**
-- granica se postavlja na gornji kvantil normalnog rasipanja, a ne na procjep
prema ciljnim anomalijama. Zato izlaz nosi `target_anomalies_used_for_fit: false`
i prolazi `check_schema_consistency.py`.

    python pc/tools/derive_interference_policy.py results/physical_fan/run_*/serial.log
    python pc/tools/derive_interference_policy.py --write results/.../serial.log
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "models" / "fan_psd_shape.npz"
OUT_PATH = ROOT / "pc" / "config" / "asd_interference_policy_v2.json"

BANDS = 96
GROUPS = 5
SCHEMA = "asd-interference-policy-v2.0.0-development"

# Granica je NAJVECI izmjereni normalni prozor puta rezerva. Uzorak je reda
# desetina prozora, pa bi "p99" na njemu bio samo drugo ime za maksimum -- ovako
# je bar posteno receno sta se racuna. p99 se svejedno biljezi kao dokaz.
# Uslovi koji su po planu normalni; DET prozori pod njima smiju u korpus, jer
# nisu ciljne anomalije. Papiric, govor i vrata se nikad ne otvaraju.
NORMAL_CONDITIONS = ("normal_baseline", "final_recovery")

QUANTILE = 99.0
# Rezerva iznad najveceg izmjerenog normalnog prozora.
MARGIN = 1.25
# Ispod ovoga se granica ne izvodi; radije nema politike nego izmisljena.
MIN_WINDOWS = 15

FEATURE_RE = re.compile(
    r"FEATURE96 .*?\bphase=(?P<phase>\S+)\s.*?\btonalness_proxy=(?P<ton>\S+)\s"
    r".*?\bvalues=(?P<values>\S+)$")
SUBSEG_RE = re.compile(
    r"SUBSEG96 .*?\bphase=(?P<phase>\S+)\s.*?\bwindow=(?P<window>\d+)\s"
    r"group=(?P<group>\d+)\s.*?\bvalues=(?P<values>\S+)$")
WINDOW_RE = re.compile(r"\bwindow=(?P<window>\d+)\b")


def parse_log(path: Path) -> dict:
    """FEATURE96 tonalnost i pet SUBSEG96 vektora po prozoru, po fazama."""
    features: dict[tuple[str, int], float] = {}
    groups: dict[tuple[str, int], dict[int, np.ndarray]] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.split("\t")[-1]
        if line.startswith("FEATURE96 "):
            match = FEATURE_RE.search(line)
            window = WINDOW_RE.search(line)
            if match and window:
                features[(match.group("phase"), int(window.group("window")))] = \
                    float(match.group("ton"))
        elif line.startswith("SUBSEG96 "):
            match = SUBSEG_RE.search(line)
            if not match:
                continue
            values = np.fromstring(match.group("values"), sep=",", dtype=np.float64)
            if values.size != BANDS:
                continue          # isprepletan red se ne racuna
            key = (match.group("phase"), int(match.group("window")))
            groups.setdefault(key, {})[int(match.group("group"))] = values
    return {"tonalness": features, "groups": groups}


def subsegment_instability(group_features: np.ndarray, mean: np.ndarray,
                           std: np.ndarray) -> float:
    """Ista formula koju firmver racuna u `psd_live.c`."""
    z = (group_features - mean) / std
    return float(np.mean(np.std(z, axis=0)))


def normal_windows(log_path: Path) -> set[int]:
    """DET prozori koji su po planu normalni, iz `detections.csv` istog runa."""
    table = log_path.parent / "detections.csv"
    if not table.exists():
        return set()
    normal: set[int] = set()
    with table.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if (row.get("condition") in NORMAL_CONDITIONS
                    and int(row.get("transition_window", 0)) == 0):
                normal.add(int(row["window"]))
    return normal


def collect(paths: list[Path], include_baseline: bool) -> dict:
    model = np.load(MODEL_PATH)
    mean = model["mean"].astype(np.float64)
    std = model["std"].astype(np.float64)
    deltas: list[float] = []
    instabilities: list[float] = []
    per_log: list[dict] = []
    for path in paths:
        parsed = parse_log(path)
        # Referenca tonalnosti je ono sto firmver zamrzne na kraju CAL faze:
        # srednja tonalnost prihvacenih kalibracionih klipova tog runa.
        cal = [value for (phase, _), value in parsed["tonalness"].items()
               if phase == "CAL"]
        if not cal:
            per_log.append({"log": str(path), "windows": 0,
                            "note": "nema CAL prozora"})
            continue
        reference = float(np.mean(cal))
        det_normal = normal_windows(path) if include_baseline else set()
        used = 0
        for (phase, window), tonalness in sorted(parsed["tonalness"].items()):
            if phase == "DET" and window not in det_normal:
                continue
            if phase not in ("CAL", "DET"):
                continue
            found = parsed["groups"].get((phase, window), {})
            if len(found) != GROUPS:
                continue          # nepotpun prozor se ne racuna
            stacked = np.array([found[index] for index in sorted(found)])
            deltas.append(abs(tonalness - reference))
            instabilities.append(subsegment_instability(stacked, mean, std))
            used += 1
        per_log.append({"log": path.parent.name, "windows": used,
                        "tonalness_reference": round(reference, 6)})
    return {"abs_tonalness_delta": np.array(deltas),
            "subsegment_instability": np.array(instabilities),
            "sources": per_log}


def summarise(name: str, values: np.ndarray) -> dict:
    quantile = float(np.percentile(values, QUANTILE))
    return {
        "name": name,
        "count": int(values.size),
        "median": round(float(np.median(values)), 6),
        "p90": round(float(np.percentile(values, 90)), 6),
        "p99": round(quantile, 6),
        "max": round(float(values.max()), 6),
        "rule": "max(normal) * margin",
        "threshold": round(float(values.max()) * MARGIN, 6),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("logs", nargs="+", type=Path)
    parser.add_argument(
        "--include-baseline", action="store_true",
        help="uzmi i DET prozore (koristi samo ako su svi normal-only)")
    parser.add_argument("--write", action="store_true",
                        help=f"upisi {OUT_PATH.relative_to(ROOT)}")
    args = parser.parse_args(argv)

    data = collect([Path(p) for p in args.logs], args.include_baseline)
    if data["abs_tonalness_delta"].size < MIN_WINDOWS:
        print(f"premalo normal-only prozora: {data['abs_tonalness_delta'].size}")
        return 2

    tonalness = summarise("abs_tonalness_delta", data["abs_tonalness_delta"])
    instability = summarise("subsegment_instability", data["subsegment_instability"])
    for item in (tonalness, instability):
        print(f"{item['name']:24s} n={item['count']:<4d} med={item['median']:8.4f} "
              f"p90={item['p90']:8.4f} p99={item['p99']:8.4f} "
              f"max={item['max']:8.4f}  ->  granica {item['threshold']:.4f}")
    for source in data["sources"]:
        print(f"   {source.get('log','?'):48s} prozora {source.get('windows', 0)}")

    policy = {
        "schema_version": SCHEMA,
        "developmental": True,
        "numeric_status": "derived_from_normal_only_windows",
        "target_anomalies_used_for_fit": False,
        "public_state": "OBSERVATION_HOLD",
        "forbidden_single_microphone_diagnosis": "AMBIENT_NOISE",
        "policy": {
            "enabled": True,
            # Tonalnost NE ulazi u odluku, i to nije numericko stelovanje nego
            # posljedica onoga sto ta velicina mjeri: koliko se tonalni potpis
            # prozora razlikuje od kalibracionog. Stvarna promjena na masini ga
            # pomjera isto kao i tudji zvuk, pa je to detektor PROMJENE, a to
            # skor vec radi -- ne detektor POUZDANOSTI. Kapija pouzdanosti mora
            # gledati nesto ortogonalno: slaganje podsegmenata unutar istog
            # prozora. Granica se svejedno racuna i biljezi kao dokaz.
            "use_tonalness_delta": False,
            "max_abs_tonalness_delta": tonalness["threshold"],
            "max_subsegment_instability": instability["threshold"],
            "long_hold_windows": 6,
        },
        "derivation": {
            "normal_conditions_admitted": list(NORMAL_CONDITIONS),
            "quantile": QUANTILE,
            "margin": MARGIN,
            "windows_used": tonalness["count"],
            "sources": data["sources"],
            "abs_tonalness_delta": tonalness,
            "subsegment_instability": instability,
        },
        "semantics": {
            "hold_suspends_alarm_buildup": True,
            "hold_clears_active_alarm": False,
            "hold_changes_profile": False,
            "stable_high_after_hold_starts_fresh_run": True,
            "long_hold_is_warning_not_normal": True,
        },
        "change_rule": (
            "Granice se izvode iskljucivo iz normal-only prozora. Ciljne "
            "anomalije se ne otvaraju; svaka izmjena trazi bump verzije i novi "
            "preregistrovani retest."),
    }
    if args.write:
        OUT_PATH.write_text(json.dumps(policy, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
        print(f"upisano {OUT_PATH.relative_to(ROOT)}")
    else:
        print("\n(pokreni sa --write da se politika upise)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
