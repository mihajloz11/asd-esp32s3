r"""Faza 4 — izvodjenje vremenske odluke SAMO iz normalnih podataka.

PITANJE NA KOJE ODGOVARA. Uredjaj danas pali alarm poslije 3 uzastopna prozora
iznad praga. To je bila razumna pretpostavka, ali nikad izmjerena. Ovdje se
mjeri sta razlicita pravila vremenske odluke stvarno rade:

  1. koliko LAZNIH alarma daju na cistom normalnom toku;
  2. da li propuste KRATKU pobudu -- govor, udarac, prolaznu buku;
  3. koliko im treba da uhvate TRAJNU promjenu.

GRANICA PODATAKA. Ni jedan target anomalan klip se ne otvara. Standardizacija i
Ledoit-Wolf precision uce se na `source/train/normal`, centar i prag na
kalibracionom dijelu target normalnog poola, a tokovi score-a dolaze iskljucivo
iz normalnih klipova. Kratka pobuda i trajna promjena su SINTETICKI pomjeraji
score-a, izrazeni u jedinicama normalnog rasipanja tog istog splita -- to je
provjera osobine pravila, a NE tvrdnja o stvarnom kvaru.

Prag se racuna istom formulom kao u `psd_live.c`: veca od p90 LOO i
sredina + 3 sd LOO. Ako se ta formula promijeni, mora se promijeniti i ovdje.

Upotreba (iz korijena repozitorija):

    .venv\Scripts\python.exe pc\tools\derive_temporal_policy.py
    .venv\Scripts\python.exe pc\tools\derive_temporal_policy.py --n-splits 20
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import welch
from sklearn.covariance import LedoitWolf

PC_DIR = Path(__file__).resolve().parents[1]
ROOT = PC_DIR.parent
sys.path.insert(0, str(PC_DIR))

from asd import features  # noqa: E402

FAN = ROOT / "data" / "dcase2026_dev" / "fan"
CONFIG = ROOT / "pc" / "config" / "asd_temporal_policy_v1.json"
CACHE = ROOT / "results" / "advanced" / "cache_psd_shape.npz"

SCHEMA_VERSION = "asd-temporal-policy-v1.0.0"
N_CAL = 10                 # isto kao N_CAL u psd_live.c
CAL_P_HI = 0.90            # isto kao CAL_P_HI
CAL_K_SIGMA = 3.0          # isto kao CAL_K_SIGMA
WINDOW_SECONDS = 10.0      # jedan DCASE klip = jedan prozor uredjaja
DEFAULT_SPLITS = 40
SPLIT_SEED = 20260814


# --- feature front-end: isti kao kanonski `psd_shape` ------------------------

def band_log_power(freq: np.ndarray, power: np.ndarray, edges: np.ndarray) -> np.ndarray:
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (freq >= lo) & (freq < hi)
        out.append(np.log10(float(power[mask].mean()) + 1e-20) if np.any(mask) else -20.0)
    return np.asarray(out, np.float64)


def psd_shape(path: Path) -> np.ndarray:
    audio, sample_rate = sf.read(path, dtype="float32", always_2d=True)
    if sample_rate != features.SR:
        raise ValueError(f"{path}: ocekivano {features.SR} Hz, dobijeno {sample_rate}")
    signal = audio[:, 0].astype(np.float64)
    signal -= signal.mean()
    frequencies, power = welch(signal, fs=features.SR, window="hann", nperseg=8192,
                               noverlap=4096, detrend=False, scaling="spectrum")
    raw = band_log_power(frequencies, power, np.geomspace(10.0, 4000.0, 97))
    return raw - raw.mean()


def load_features(paths: list[Path], label: str) -> np.ndarray:
    print(f"  {label}: {len(paths)} klipova", flush=True)
    return np.stack([psd_shape(p) for p in paths])


def normal_pools() -> dict[str, np.ndarray]:
    """Iskljucivo normalni klipovi. Anomalni se ovdje ni ne izlistavaju."""
    if CACHE.exists():
        data = np.load(CACHE)
        print(f"  cache: {CACHE.name}")
        return {key: data[key] for key in data.files}
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    pools = {
        "source_train_normal": load_features(
            sorted(FAN.glob("train/*source_train_normal*.wav")), "source/train/normal"),
        "target_train_normal": load_features(
            sorted(FAN.glob("train/*target_train_normal*.wav")), "target/train/normal"),
        "target_test_normal": load_features(
            sorted(FAN.glob("test/*target_test_normal*.wav")), "target/test/normal"),
        "source_test_normal": load_features(
            sorted(FAN.glob("test/*source_test_normal*.wav")), "source/test/normal"),
    }
    np.savez_compressed(CACHE, **pools)
    return pools


# --- model: isto sto uredjaj radi -------------------------------------------

def fit_source_only(values: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = values.mean(axis=0)
    scale = values.std(axis=0)
    scale = np.where(scale < 1e-8, 1.0, scale)
    standardized = (values - mean) / scale
    precision = LedoitWolf().fit(standardized).precision_
    return mean, scale, precision


def mahalanobis(values: np.ndarray, center: np.ndarray, precision: np.ndarray) -> np.ndarray:
    difference = values - center
    return np.einsum("ij,jk,ik->i", difference, precision, difference)


def device_threshold(loo: np.ndarray) -> float:
    """Ista formula kao psd_live.c: veca od p90 LOO i sredina + 3 sd LOO."""
    p_hi = float(np.percentile(loo, CAL_P_HI * 100.0))
    sigma = float(loo.mean() + CAL_K_SIGMA * loo.std(ddof=1))
    return max(p_hi, sigma)


# --- pravila vremenske odluke ------------------------------------------------

@dataclass(frozen=True)
class Rule:
    name: str
    min_consecutive: int = 3
    ewma_alpha: float = 0.0        # 0 = iskljucen
    enter_scale: float = 1.0
    exit_scale: float = 1.0        # < enter_scale = histereza
    cusum_k: float = 0.0           # 0 = iskljucen; u jedinicama praga
    cusum_h: float = 0.0
    fast_scale: float = 0.0        # 0 = iskljucen

    def describe(self) -> str:
        parts = [f"n={self.min_consecutive}"]
        if self.ewma_alpha:
            parts.append(f"ewma={self.ewma_alpha:g}")
        if self.exit_scale != self.enter_scale:
            parts.append(f"hist={self.enter_scale:g}/{self.exit_scale:g}")
        if self.cusum_h:
            parts.append(f"cusum k={self.cusum_k:g} h={self.cusum_h:g}")
        if self.fast_scale:
            parts.append(f"fast={self.fast_scale:g}")
        return " ".join(parts)


def run_rule(rule: Rule, scores: np.ndarray, threshold: float) -> np.ndarray:
    """Vraca niz 0/1 -- da li je uredjaj u alarmu poslije svakog prozora.

    Ovo je referentna implementacija; C verzija u `asd_temporal.c` mora dati
    identican niz na istim ulazima.
    """
    alarm = np.zeros(len(scores), dtype=np.int8)
    ewma = math.nan
    run = 0
    cusum = 0.0
    active = False
    enter = threshold * rule.enter_scale
    leave = threshold * rule.exit_scale
    for index, raw in enumerate(scores):
        statistic = raw
        if rule.ewma_alpha > 0.0:
            ewma = raw if math.isnan(ewma) else (
                rule.ewma_alpha * raw + (1.0 - rule.ewma_alpha) * ewma)
            statistic = ewma
        if rule.cusum_h > 0.0:
            cusum = max(0.0, cusum + (raw / threshold - 1.0) - rule.cusum_k)

        if active:
            # Histereza: izlazi se tek ispod NIZEG praga, da alarm ne treperi.
            if statistic <= leave:
                active = False
                run = 0
                cusum = 0.0
        else:
            run = run + 1 if statistic > enter else 0
            fired = run >= rule.min_consecutive
            if rule.cusum_h > 0.0 and cusum > rule.cusum_h:
                fired = True
            if rule.fast_scale > 0.0 and raw > threshold * rule.fast_scale:
                fired = True
            if fired:
                active = True
        alarm[index] = int(active)
    return alarm


def episodes(alarm: np.ndarray) -> int:
    return int(np.sum((alarm == 1) & (np.concatenate([[0], alarm[:-1]]) == 0)))


# --- eksperiment -------------------------------------------------------------

@dataclass
class SplitResult:
    threshold: float
    normal_scores: np.ndarray      # ista masina, klipovi koje kalibracija nije cula
    foreign_scores: np.ndarray     # DRUGI fizicki ventilator: domenski pomak
    normal_sd: float


def build_split(rng: np.random.Generator, target_normal: np.ndarray,
                foreign_pool: np.ndarray, mean: np.ndarray, scale: np.ndarray,
                precision: np.ndarray) -> SplitResult:
    order = rng.permutation(len(target_normal))
    cal = target_normal[order[:N_CAL]]
    cal_z = (cal - mean) / scale
    center = cal_z.mean(axis=0)

    # Leave-one-out, isto kao na uredjaju: klip se ocjenjuje centrom bez sebe.
    loo = np.empty(N_CAL)
    for i in range(N_CAL):
        others = np.delete(cal_z, i, axis=0).mean(axis=0)
        loo[i] = mahalanobis(cal_z[i : i + 1], others, precision)[0]
    threshold = device_threshold(loo)

    # KLJUCNO: tok se pravi SAMO od klipova iste masine.
    #
    # Prvi prolaz ovog alata je u tok ubacivao i `source` normalne klipove "radi
    # vise podataka" i dobio 14,3 lazna alarma na sat za sadasnje pravilo. To je
    # bila greska postavke, ne nalaz o pravilu: `source` klipovi su DRUGI
    # fizicki ventilator, a uredjaj se kalibrise na masini koju ce i nadzirati.
    # Ono sto se tu mjerilo je domenski pomak, pa se sada mjeri odvojeno i ne
    # ulazi u izbor pravila.
    held_out = target_normal[order[N_CAL:]]
    stream = held_out[rng.permutation(len(held_out))]
    scores = mahalanobis((stream - mean) / scale, center, precision)
    foreign = mahalanobis((foreign_pool - mean) / scale, center, precision)
    return SplitResult(threshold, scores, foreign, float(scores.std(ddof=1)))


def evaluate(rules: list[Rule], splits: list[SplitResult],
             spike_sigmas: tuple[float, ...], shift_sigma: float,
             rng: np.random.Generator) -> list[dict]:
    rows = []
    for rule in rules:
        false_episodes = 0
        total_windows = 0
        foreign_episodes = 0
        foreign_windows = 0
        spike_alarms = {k: 0 for k in (1, 2)}
        spike_trials = {k: 0 for k in (1, 2)}
        latencies: list[int] = []
        never_caught = 0

        for split in splits:
            base = split.normal_scores
            alarm = run_rule(rule, base, split.threshold)
            false_episodes += episodes(alarm)
            total_windows += len(base)

            # Odvojeno: drugi fizicki ventilator. Ovo NIJE lazni alarm nego
            # mjera domenskog pomaka i ne ulazi u izbor pravila.
            foreign_episodes += episodes(
                run_rule(rule, split.foreign_scores, split.threshold))
            foreign_windows += len(split.foreign_scores)

            # Kratka pobuda: k prozora podignutih za spike_sigma * sd.
            for k in (1, 2):
                for sigma in spike_sigmas:
                    for _ in range(3):
                        start = int(rng.integers(3, len(base) - k - 3))
                        probe = base.copy()
                        probe[start : start + k] += sigma * split.normal_sd
                        fired = run_rule(rule, probe, split.threshold)
                        baseline = run_rule(rule, base, split.threshold)
                        # Racuna se samo alarm koji kratka pobuda DODAJE.
                        spike_alarms[k] += int(
                            episodes(fired) > episodes(baseline))
                        spike_trials[k] += 1

            # Trajna promjena: pomjeraj od prozora `start` do kraja.
            start = len(base) // 2
            probe = base.copy()
            probe[start:] += shift_sigma * split.normal_sd
            fired = run_rule(rule, probe, split.threshold)
            hit = np.flatnonzero(fired[start:] == 1)
            if hit.size:
                latencies.append(int(hit[0]) + 1)
            else:
                never_caught += 1

        hours = total_windows * WINDOW_SECONDS / 3600.0
        foreign_hours = foreign_windows * WINDOW_SECONDS / 3600.0
        rows.append({
            "rule": rule.name,
            "config": rule.describe(),
            "params": asdict(rule),
            "normal_windows": total_windows,
            "false_alarm_episodes": false_episodes,
            "false_alarms_per_hour": false_episodes / hours if hours else float("nan"),
            "foreign_machine_episodes_per_hour":
                foreign_episodes / foreign_hours if foreign_hours else float("nan"),
            "short_spike_1_window_alarm_rate":
                spike_alarms[1] / max(spike_trials[1], 1),
            "short_spike_2_window_alarm_rate":
                spike_alarms[2] / max(spike_trials[2], 1),
            "sustained_shift_median_latency_windows":
                float(np.median(latencies)) if latencies else float("nan"),
            "sustained_shift_missed_splits": never_caught,
        })
    return rows


RULES = [
    Rule("baseline_3_consecutive"),
    Rule("consecutive_2", min_consecutive=2),
    Rule("consecutive_4", min_consecutive=4),
    Rule("ewma_0.4_n2", min_consecutive=2, ewma_alpha=0.4),
    Rule("ewma_0.4_n3", min_consecutive=3, ewma_alpha=0.4),
    Rule("ewma_0.25_n3", min_consecutive=3, ewma_alpha=0.25),
    Rule("hysteresis_1.0_0.7_n3", min_consecutive=3, exit_scale=0.7),
    Rule("ewma_0.4_n3_hyst_0.7", min_consecutive=3, ewma_alpha=0.4, exit_scale=0.7),
    Rule("cusum_k0.5_h2", min_consecutive=3, cusum_k=0.5, cusum_h=2.0),
    Rule("cusum_k1.0_h3", min_consecutive=3, cusum_k=1.0, cusum_h=3.0),
    Rule("ewma_0.4_n3_hyst_0.7_fast5", min_consecutive=3, ewma_alpha=0.4,
         exit_scale=0.7, fast_scale=5.0),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--n-splits", type=int, default=DEFAULT_SPLITS)
    parser.add_argument("--shift-sigma", type=float, default=3.0,
                        help="trajna promjena, u jedinicama normalnog sd score-a")
    parser.add_argument("--out", default=str(CONFIG))
    args = parser.parse_args()

    print("ucitavanje normalnih klipova (anomalni se ne otvaraju):")
    pools = normal_pools()
    mean, scale, precision = fit_source_only(pools["source_train_normal"])
    target_normal = np.concatenate(
        [pools["target_train_normal"], pools["target_test_normal"]])
    foreign_pool = pools["source_test_normal"]
    print(f"  target normalnih (ista masina): {len(target_normal)}, "
          f"drugi ventilator za domenski pomak: {len(foreign_pool)}")

    rng = np.random.default_rng(SPLIT_SEED)
    splits = [build_split(rng, target_normal, foreign_pool, mean, scale, precision)
              for _ in range(args.n_splits)]
    print(f"  splitova: {len(splits)}, prozora po splitu: "
          f"{len(splits[0].normal_scores)}")

    rows = evaluate(RULES, splits, spike_sigmas=(3.0, 6.0),
                    shift_sigma=args.shift_sigma,
                    rng=np.random.default_rng(SPLIT_SEED + 1))

    header = (f"{'pravilo':<30} {'konfig':<34} {'lazni/h':>8} {'tudji/h':>8} "
              f"{'spike1':>7} {'spike2':>7} {'kasnjenje':>10} {'promasaj':>9}")
    print("\n" + header)
    print("-" * len(header))
    for row in rows:
        print(f"{row['rule']:<30} {row['config']:<34} "
              f"{row['false_alarms_per_hour']:8.2f} "
              f"{row['foreign_machine_episodes_per_hour']:8.2f} "
              f"{row['short_spike_1_window_alarm_rate']:7.3f} "
              f"{row['short_spike_2_window_alarm_rate']:7.3f} "
              f"{row['sustained_shift_median_latency_windows']:10.1f} "
              f"{row['sustained_shift_missed_splits']:9d}")

    # IZBOR PRAVILA.
    #
    # Prvi kriterij je trazio APSOLUTNU nulu: nijedan lazni alarm, nikakva
    # reakcija na kratku pobudu, nijedan propusten trajni pomak. Nijedno
    # pravilo ga nije proslo, i to nije slucajnost nego posljedica dvije
    # stvari koje kriterij nije uzeo u obzir:
    #
    #   1. kratka pobuda koja padne TIK UZ prozor koji je ionako iznad praga
    #      moze dopuniti niz od tri i tako proizvesti alarm; nijedno pravilo
    #      koje broji uzastopne prozore to ne moze iskljuciti;
    #   2. prag `sredina + 3 sd LOO` je u dijelu splitova toliko visok da ga
    #      pomjeraj od 3 sd uopste ne dosegne, pa "propusten pomak" ne mjeri
    #      pravilo nego prag.
    #
    # Zamjenski kriterij je zato relativan i mjerljiv, i biran je tako da
    # odgovara na pitanje zbog kojeg faza postoji -- manje laznih alarma uz
    # manju osjetljivost na kratku pobudu:
    #
    #   1. najmanji broj laznih alarmnih epizoda na normalnom toku;
    #   2. medju pravilima unutar 1,5x od najboljeg, najmanja reakcija na
    #      pobudu od jednog prozora;
    #   3. na izjednacenje, najmanje kasnjenje na trajnu promjenu.
    #
    # Oba kriterija se zapisuju u izlaz, da se vidi sta je probano i zasto je
    # promijenjeno.
    strict = [row for row in rows
              if row["false_alarm_episodes"] == 0
              and row["short_spike_1_window_alarm_rate"] == 0.0
              and row["short_spike_2_window_alarm_rate"] == 0.0
              and row["sustained_shift_missed_splits"] == 0]

    best_false = min(row["false_alarms_per_hour"] for row in rows)
    tolerance = best_false * 1.5 if best_false > 0 else 0.0
    eligible = [row for row in rows if row["false_alarms_per_hour"] <= tolerance] or rows
    chosen = min(eligible,
                 key=lambda row: (row["short_spike_1_window_alarm_rate"],
                                  row["sustained_shift_median_latency_windows"],
                                  row["rule"]))

    record = {
        "schema_version": SCHEMA_VERSION,
        "derived_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": "temporal decision rule for the deviation level; not a fault diagnosis",
        "target_anomalies_used": False,
        "derivation": {
            "data": "DCASE 2026 dev fan, normal clips only (source train/test, target train/test)",
            "feature": "psd_shape, identical to canonical-evaluation-v1.1.0",
            "threshold_rule": "max(p90 LOO, mean + 3 sd LOO), identical to psd_live.c",
            "window_seconds": WINDOW_SECONDS,
            "n_splits": args.n_splits,
            "split_seed": SPLIT_SEED,
            "short_disturbance": "synthetic +3 and +6 sd score bump over 1 or 2 windows; "
                                 "a property probe of the rule, NOT a claim about a real fault",
            "sustained_change": f"synthetic +{args.shift_sigma} sd score shift held to the end of the stream",
            "stream_composition": "held-out normal clips of the SAME machine only; clips of a "
                                  "different physical fan are scored separately as a "
                                  "domain-shift measure and never counted as false alarms",
            "selection_criterion": "lowest false-alarm episodes on the normal stream; among "
                                   "rules within 1.5x of the best, lowest response to a "
                                   "one-window disturbance; ties broken by latency",
            "rejected_criterion": {
                "criterion": "zero false alarms AND zero response to 1-2 window disturbances "
                             "AND no missed sustained shift",
                "outcome": "no rule satisfied it",
                "why": [
                    "a one-window disturbance adjacent to a window already above the threshold "
                    "can complete a run of three; no consecutive-window rule can exclude that",
                    "the mean + 3 sd LOO threshold is high enough in some splits that a 3 sd "
                    "shift never reaches it, so 'missed shift' measures the threshold, not the rule",
                ],
            },
        },
        "strict_criterion_survivors": [row["rule"] for row in strict],
        "candidates": rows,
        "policy": (
            {
                "rule": chosen["rule"],
                **{key: value for key, value in chosen["params"].items() if key != "name"},
                "measured_false_alarms_per_hour": chosen["false_alarms_per_hour"],
                "measured_sustained_latency_windows":
                    chosen["sustained_shift_median_latency_windows"],
            }
            if chosen else None
        ),
        "limitation": "Derived from recordings, not from a physical fan. The short-disturbance "
                      "and sustained-change probes are synthetic score shifts, so they measure "
                      "the rule's temporal behaviour, not acoustic detectability.",
        "change_rule": "Any change requires a new schema version and normal-only evidence "
                       "before any target-anomaly evaluation.",
    }
    Path(args.out).write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nizabrano: {chosen['rule'] if chosen else 'NIJEDNO PRAVILO NE PROLAZI KRITERIJ'}")
    print(f"zapisano: {args.out}")


if __name__ == "__main__":
    main()
