"""Record the built image and verify the protected model sources before flash."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def main():
    folder = Path(__file__).resolve().parent
    repo = folder.parents[1]
    build = folder / "build"
    image = build / "esp32s3_asd.bin"
    original = json.loads((folder / "backup/manifest.json").read_text(encoding="utf-8"))
    for name, expected in original["protected_source_sha256_lf"].items():
        content = (repo / "firmware/esp32s3_asd/main" / name).read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(content).hexdigest() != expected:
            raise SystemExit(f"Protected model/audio file changed: {name}")
    commands = json.loads((build / "compile_commands.json").read_text(encoding="utf-8"))
    e5 = next(c for c in commands if Path(c["file"]).name == "e5_measure.c")
    for flag in ("-DASD_E5_MEASURE", "-DASD_PSD_LIVE", "-DASD_RESEARCH_TELEMETRY"):
        if flag not in e5["command"]:
            raise SystemExit(f"Missing build flag: {flag}")
    data = image.read_bytes()
    if not data or data[0] != 0xE9 or len(data) > 4 * 1024 * 1024:
        raise SystemExit("Invalid or oversized ESP app image")
    shutil.copyfile(image, folder / "firmware-e5.bin")
    files = list((repo / "firmware/esp32s3_asd/main").iterdir())
    source_hashes = {str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(files) if p.is_file()}
    for name in ("sdkconfig", "dependencies.lock"):
        shutil.copyfile(repo / "firmware/esp32s3_asd" / name, folder / (name + ".snapshot"))
    manifest = {
        "app_sha256": hashlib.sha256(data).hexdigest(), "app_bytes": len(data),
        "flash_offset": "0x10000", "hardware_verified": False,
        "base_commit": original["base_commit"],
        "git_head_at_build": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
        "protected_sources_match_baseline": True,
        "firmware_source_sha256": source_hashes,
        "project": json.loads((build / "project_description.json").read_text(encoding="utf-8")),
    }
    # Project description includes large generated component lists; keep relevant identity only.
    manifest["project"] = {k: manifest["project"].get(k) for k in
                           ("project_name", "project_version", "git_revision", "target", "idf_path")}
    (folder / "firmware-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Image ready for flash: {len(data)} bytes, SHA256 {manifest['app_sha256']}")
    print("Protected model/audio files match baseline. Hardware verification remains pending.")


if __name__ == "__main__":
    main()
