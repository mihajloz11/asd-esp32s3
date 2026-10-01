"""Replay final trial decisions with the original temporal C implementation.

Run from the repository root. Requires numpy and gcc on PATH.
Writes verification/decision_replay.json; does not modify trial artifacts.
"""
from pathlib import Path
import ctypes as C
import hashlib
import json
import re
import subprocess
import sys
import tempfile

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "pc/tools"))
from analyze_trial_features import Model, Session


class Policy(C.Structure):
    _fields_ = [("min_consecutive", C.c_int)] + [(n, C.c_float) for n in
        ("ewma_alpha", "enter_scale", "exit_scale", "cusum_k", "cusum_h", "fast_scale")]


class Detector(C.Structure):
    _fields_ = [("ewma", C.c_float), ("ewma_valid", C.c_int), ("run", C.c_int),
                ("cusum", C.c_float), ("active", C.c_int), ("policy", Policy)]


def main():
    source = ROOT / "firmware/esp32s3_asd/main/asd_temporal.c"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    # Windows keeps a loaded DLL locked; explicitly unload before temp cleanup.
    with tempfile.TemporaryDirectory(prefix="telfor-replay-") as temporary:
        dll = Path(temporary) / "temporal.dll"
        subprocess.run(["gcc", "-shared", "-O2", str(source), "-o", str(dll)], check=True)
        lib = C.CDLL(str(dll))
        lib.asd_temporal_init.argtypes = [C.POINTER(Detector), C.POINTER(Policy)]
        lib.asd_temporal_suspend.argtypes = [C.POINTER(Detector)]
        lib.asd_temporal_update.argtypes = [C.POINTER(Detector), C.c_float, C.c_float, C.c_float]
        lib.asd_temporal_update.restype = C.c_int
        model = Model()
        report = {"scope": "post-hoc replay; no new physical measurements",
                  "temporal_c_sha256": digest, "runs": {}}
        try:
            for key in ("paper", "tone"):
                session = Session(model, key)
                provenance = (session.run_dir / "provenance.json").read_text(encoding="utf-8")
                assert digest in provenance, "Temporal C hash differs from trial provenance"
                log = (session.run_dir / "serial.log").read_text(encoding="utf-8")
                temporal = next(line for line in log.splitlines() if "TEMPORAL protocol=" in line)
                interference = next(line for line in log.splitlines() if "INTERFERENCE protocol=" in line)
                enter = float(re.search(r"threshold_enter=([\d.e+-]+)", temporal)[1])
                leave = float(re.search(r"threshold_exit=([\d.e+-]+)", temporal)[1])
                gate = float(re.search(r"threshold=([\d.e+-]+)", interference)[1])
                data = np.load(session.run_dir / "window_features.npz")
                detector = Detector()
                lib.asd_temporal_init(C.byref(detector), None)
                hold_errors, alarm_errors, relative_errors = [], [], []
                for i in session.det:
                    window = int(session.window[i])
                    row = session.rows[window]
                    score = model.score(session.features[i], session.center)
                    relative_errors.append(abs(score - session.device_score[i]) / session.device_score[i])
                    instability = np.std(model.z(data["subseg96"][i].astype(float)), axis=0).mean()
                    hold = score > enter and instability > gate
                    if int(hold) != int(row["hold"]):
                        hold_errors.append(window)
                    if hold:
                        lib.asd_temporal_suspend(C.byref(detector))
                        alarm = detector.active
                    else:
                        alarm = lib.asd_temporal_update(C.byref(detector), score, enter, leave)
                    if alarm != int(row["alarm"]):
                        alarm_errors.append(window)
                result = {"run": session.run_dir.name, "monitoring_windows": len(session.det),
                          "source_hash_matches_provenance": True,
                          "hold_mismatches": hold_errors, "alarm_mismatches": alarm_errors,
                          "max_relative_score_error": max(relative_errors)}
                report["runs"][key] = result
                assert not hold_errors and not alarm_errors and max(relative_errors) < 1e-6, result
        finally:
            import _ctypes
            _ctypes.FreeLibrary(lib._handle)
    output = HERE / "verification/decision_replay.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
