"""Host-C regression tests for the persisted ASD profile v1.0 blob."""
from __future__ import annotations

import ctypes
import math
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "firmware" / "esp32s3_asd" / "main"


class Profile(ctypes.Structure):
    _fields_ = [
        ("valid", ctypes.c_int), ("developmental", ctypes.c_int),
        ("center", ctypes.c_float * 96),
        ("level_mean_dbfs", ctypes.c_float),
        ("tonalness_reference", ctypes.c_float),
        ("threshold_enter", ctypes.c_float), ("threshold_exit", ctypes.c_float),
        ("center_windows", ctypes.c_uint32), ("derive_windows", ctypes.c_uint32),
        ("verify_windows", ctypes.c_uint32), ("policy_version", ctypes.c_uint32),
        ("policy_id", ctypes.c_uint32),
    ]


class Metadata(ctypes.Structure):
    _fields_ = [
        ("generation", ctypes.c_uint32),
        ("derive_mean", ctypes.c_float), ("derive_sd", ctypes.c_float),
        ("verify_alarm_time_percent", ctypes.c_float),
        ("verify_alarm_windows", ctypes.c_uint32),
        ("verify_episodes", ctypes.c_uint32), ("verify_chatter", ctypes.c_uint32),
        ("quality_policy_id", ctypes.c_uint32),
        ("commissioning_policy_id", ctypes.c_uint32),
        ("temporal_policy_id", ctypes.c_uint32),
        ("interference_policy_id", ctypes.c_uint32),
    ]


@pytest.fixture(scope="module")
def lib(tmp_path_factory: pytest.TempPathFactory):
    cc = shutil.which("gcc") or shutil.which("clang")
    if not cc:
        pytest.skip("nema host C kompajlera")
    suffix = "dll" if sys.platform == "win32" else "so"
    output = tmp_path_factory.mktemp("profile_store_c") / f"profile_store.{suffix}"
    command = [
        cc, "-std=c99", "-O1", "-shared", "-fPIC", "-I", str(MAIN),
        str(MAIN / "asd_profile_runtime.c"), str(MAIN / "asd_profile_store.c"),
        "-o", str(output), "-lm",
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    handle = ctypes.CDLL(str(output))
    handle.asd_profile_store_encode.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(Profile), ctypes.POINTER(Metadata), ctypes.c_void_p,
    ]
    handle.asd_profile_store_encode.restype = ctypes.c_int
    handle.asd_profile_store_decode.argtypes = [
        ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p,
        ctypes.POINTER(Profile), ctypes.POINTER(Metadata),
    ]
    handle.asd_profile_store_decode.restype = ctypes.c_int
    handle.asd_profile_store_crc32.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    handle.asd_profile_store_crc32.restype = ctypes.c_uint32
    return handle


def valid_profile() -> Profile:
    return Profile(
        1, 1, (ctypes.c_float * 96)(*[index / 10.0 for index in range(96)]),
        -32.0, 2.5, 900.0, 600.0, 10, 120, 60, 1, 0x434D5631,
    )


def valid_metadata() -> Metadata:
    return Metadata(7, 400.0, 20.0, 0.0, 0, 0, 0,
                    0x51555631, 0x434D5631, 0x54505632, 0x49505631)


def encoded(lib):
    # The v1 schema is intentionally fixed-size; allocate generously and let
    # decode reject both truncation and oversize independently of this fixture.
    raw = (ctypes.c_ubyte * 1024)()
    fingerprint = (ctypes.c_ubyte * 32)(*range(32))
    profile, metadata = valid_profile(), valid_metadata()
    assert lib.asd_profile_store_encode(
        raw, ctypes.byref(profile), ctypes.byref(metadata), fingerprint,
    ) == 1
    size = int.from_bytes(bytes(raw[8:12]), "little")
    return raw, size, fingerprint


def decode(lib, raw, size, fingerprint):
    profile, metadata = Profile(), Metadata()
    ok = lib.asd_profile_store_decode(
        raw, size, fingerprint, ctypes.byref(profile), ctypes.byref(metadata),
    )
    return ok, profile, metadata


def refresh_crc(lib, raw, size: int) -> None:
    crc = lib.asd_profile_store_crc32(raw, size - 4)
    raw[size - 4:size] = struct.pack("<I", crc)


def test_roundtrip_schema_and_runtime_profile(lib) -> None:
    raw, size, fingerprint = encoded(lib)
    ok, profile, metadata = decode(lib, raw, size, fingerprint)
    assert ok == 1
    assert size < len(raw)
    assert (profile.valid, profile.developmental) == (1, 1)
    assert (profile.threshold_enter, profile.threshold_exit) == (900.0, 600.0)
    assert list(profile.center) == pytest.approx([index / 10.0 for index in range(96)])
    assert metadata.generation == 7


@pytest.mark.parametrize("delta", [-1, 1, 64])
def test_truncated_and_oversize_are_rejected(lib, delta: int) -> None:
    raw, size, fingerprint = encoded(lib)
    assert decode(lib, raw, size + delta, fingerprint)[0] == 0


def test_corruption_and_model_fingerprint_mismatch_are_rejected(lib) -> None:
    raw, size, fingerprint = encoded(lib)
    raw[64] ^= 0x01
    assert decode(lib, raw, size, fingerprint)[0] == 0
    raw, size, fingerprint = encoded(lib)
    wrong = (ctypes.c_ubyte * 32)(*([0xA5] * 32))
    assert decode(lib, raw, size, wrong)[0] == 0


def test_unknown_schema_and_nonfinite_payload_reject_even_with_valid_crc(lib) -> None:
    raw, size, fingerprint = encoded(lib)
    raw[4:6] = struct.pack("<H", 2)
    refresh_crc(lib, raw, size)
    assert decode(lib, raw, size, fingerprint)[0] == 0

    raw, size, fingerprint = encoded(lib)
    raw[48:52] = struct.pack("<f", math.nan)  # center[0]
    refresh_crc(lib, raw, size)
    assert decode(lib, raw, size, fingerprint)[0] == 0

    raw, size, fingerprint = encoded(lib)
    raw[444:448] = struct.pack("<f", 900.0)  # exit == enter
    refresh_crc(lib, raw, size)
    assert decode(lib, raw, size, fingerprint)[0] == 0


def test_nan_and_invalid_threshold_relation_never_encode(lib) -> None:
    raw = (ctypes.c_ubyte * 1024)()
    fingerprint = (ctypes.c_ubyte * 32)(*range(32))
    metadata = valid_metadata()
    profile = valid_profile()
    profile.center[4] = math.nan
    assert lib.asd_profile_store_encode(
        raw, ctypes.byref(profile), ctypes.byref(metadata), fingerprint,
    ) == 0
    profile = valid_profile()
    metadata.quality_policy_id = 0
    assert lib.asd_profile_store_encode(
        raw, ctypes.byref(profile), ctypes.byref(metadata), fingerprint,
    ) == 0
    profile = valid_profile()
    profile.threshold_exit = profile.threshold_enter
    assert lib.asd_profile_store_encode(
        raw, ctypes.byref(profile), ctypes.byref(metadata), fingerprint,
    ) == 0


def test_nvs_wrapper_has_narrow_ownership_and_no_partition_erase() -> None:
    source = (MAIN / "asd_profile_nvs.c").read_text(encoding="utf-8")
    header = (MAIN / "asd_profile_nvs.h").read_text(encoding="utf-8")
    assert '#define ASD_PROFILE_NVS_NAMESPACE "asd"' in header
    assert '#define ASD_PROFILE_NVS_KEY "profile_v1"' in header
    assert "nvs_flash_erase" not in source
    assert "nvs_erase_all" not in source
    assert "nvs_erase_key(handle, ASD_PROFILE_NVS_KEY)" in source
    assert "INA226" not in source


def test_development_live_path_cannot_load_save_or_emit_profile_store() -> None:
    source = (MAIN / "psd_live.c").read_text(encoding="utf-8")
    header = (MAIN / "asd_commissioning.h").read_text(encoding="utf-8")
    assert "#define ASD_PROFILE_PERSISTENCE_ALLOWED 0" in header
    assert "int restored = profile_persistence_allowed &&" in source
    assert re.search(
        r"if \(profile_persistence_allowed\) \{.*?asd_profile_nvs_save\(",
        source, re.DOTALL,
    )
    assert re.search(
        r"if \(profile_persistence_allowed\) \{.*?asd_profile_nvs_init\(\)"
        r".*?asd_profile_nvs_load\(",
        source, re.DOTALL,
    )
    assert "DEVELOPMENT policy: NVS profile load/save je zabranjen" in source
