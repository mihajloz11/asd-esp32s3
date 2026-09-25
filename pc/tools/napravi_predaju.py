"""Pravi kopiju repoa za predaju, bez privatnog materijala.

Uzima samo commitovano stanje (zadano HEAD), pa necommitovane izmjene ne
mogu slucajno uci. Izbacuje `privatno/` i `radovi/` (isto kao `export-ignore`
u `.gitattributes`), brise `<!-- privatno:start -->...<!-- privatno:end -->`
blokove u Markdown fajlovima, a linkove ka izbacenim fajlovima pretvara u
obican tekst. Na kraju provjerava da nista privatno nije ostalo.

Pokretanje iz korijena repoa:
    python pc/tools/napravi_predaju.py                 # dist/predaja/asd-esp32s3/
    python pc/tools/napravi_predaju.py --zip           # i dist/predaja/asd-esp32s3.zip
    python pc/tools/napravi_predaju.py --sa-radovima   # i rukopisi, bez sablona i lista

Za javnu objavu iz ove kopije napraviti NOVI repo: istorija postojeceg
sadrzi i privatni materijal.
"""
from __future__ import annotations

import argparse
import json
import posixpath
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "dist" / "predaja"
NAME = "asd-esp32s3"

PRIVATE = ("privatno/",)
MANUSCRIPTS = "radovi/"
# ni uz --sa-radovima: sabloni fakulteta i IEEE, liste za predaju
MANUSCRIPT_PRIVATE = re.compile(r"^radovi/[^/]+/(sablon/|PREOSTALO-RAD\.md$|HANDOFF\.md$)")

PRIVATE_BLOCK = re.compile(r"\n?<!-- privatno:start -->.*?<!-- privatno:end -->\n?", re.S)
MD_LINK = re.compile(r"(!?)\[([^\]]*)\]\(([^)\s]+)\)")
HTML_LINK = re.compile(r"<a\s+[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", re.S)
TEXT_SUFFIXES = {".md", ".txt", ".py", ".c", ".h", ".cc", ".json", ".csv", ".ps1",
                 ".cmd", ".yml", ".yaml", ".html", ".log", ".cfg", ".defaults"}
EMAIL = re.compile(r"[\w.+-]+@(?!example\.)[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b")
USER_PATH = re.compile(r"[A-Za-z]:\\\\?Users\\\\?[^\\\"\s]+")


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, check=True,
                          capture_output=True).stdout


def list_files(ref: str, with_manuscripts: bool) -> list[tuple[str, str, str]]:
    entries = []
    for line in git("ls-tree", "-r", "-z", ref).split(b"\0"):
        if not line:
            continue
        meta, path = line.decode("utf-8").split("\t", 1)
        mode, kind, sha = meta.split()
        if kind != "blob" or path.startswith(PRIVATE) or path == ".gitattributes":
            continue
        if path.startswith(MANUSCRIPTS):
            if not with_manuscripts or MANUSCRIPT_PRIVATE.match(path):
                continue
        entries.append((path, mode, sha))
    return entries


def neutralize_links(text: str, path: str, exported: set[str], dirs: set[str]) -> tuple[str, int]:
    base = posixpath.dirname(path)
    changed = 0

    def missing(target: str) -> bool:
        if re.match(r"^[a-z]+:|^#|^/", target):
            return False
        rel = target.split("#")[0].replace("%20", " ")
        if not rel:
            return False
        resolved = posixpath.normpath(posixpath.join(base, rel))
        return resolved not in exported and resolved.rstrip("/") not in dirs

    def md(m):
        nonlocal changed
        if m.group(1) or not missing(m.group(3)):
            return m.group(0)
        changed += 1
        return m.group(2)

    def html(m):
        nonlocal changed
        if not missing(m.group(1)):
            return m.group(0)
        changed += 1
        return m.group(2)

    text = MD_LINK.sub(md, text)
    if path.endswith(".html"):
        text = HTML_LINK.sub(html, text)
    return text, changed


def export(ref: str, with_manuscripts: bool, make_zip: bool) -> int:
    commit = git("rev-parse", ref).decode().strip()
    entries = list_files(ref, with_manuscripts)
    exported = {path for path, _, _ in entries}
    dirs = set()
    for path in exported:
        d = posixpath.dirname(path)
        while d:
            dirs.add(d)
            d = posixpath.dirname(d)

    target = OUT_DIR / NAME
    if target.exists():
        if OUT_DIR not in target.parents:
            raise SystemExit(f"odbijam brisanje van {OUT_DIR}")
        shutil.rmtree(target)
    target.mkdir(parents=True)

    links = blocks = 0
    warnings: dict[str, list[str]] = {}
    for path, mode, sha in entries:
        data = git("cat-file", "blob", sha)
        if mode == "120000":
            warnings.setdefault("simbolicki link preskocen", []).append(path)
            continue
        suffix = Path(path).suffix.lower()
        if suffix in (".md", ".html"):
            text = data.decode("utf-8")
            text, n = PRIVATE_BLOCK.subn("", text)
            blocks += n
            text, n = neutralize_links(text, path, exported, dirs)
            links += n
            data = text.encode("utf-8")
        out = target / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        if mode == "100755":
            out.chmod(0o755)
        if suffix in TEXT_SUFFIXES:
            text = data.decode("utf-8", errors="ignore")
            for label, pattern in (("pominje privatno/", re.compile(r"\bprivatno/")),
                                   ("e-mail adresa", EMAIL),
                                   ("korisnicka Windows putanja", USER_PATH)):
                if pattern.search(text):
                    warnings.setdefault(label, []).append(path)

    # tvrde provjere: nijedan privatni fajl ni blok ne smije ostati
    leaked = [p for p in exported if p.startswith(PRIVATE)]
    leftover = [str(p.relative_to(target)) for p in target.rglob("*.md")
                if "privatno:start" in p.read_text(encoding="utf-8", errors="ignore")]
    manifest = {
        "ref": ref, "commit": commit, "files": len(entries),
        "with_manuscripts": with_manuscripts, "private_blocks_removed": blocks,
        "links_to_excluded_files_neutralized": links,
        "warnings": {k: sorted(v) for k, v in warnings.items()},
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                           encoding="utf-8")

    print(f"kopija: {target}  ({len(entries)} fajlova, commit {commit[:10]})")
    print(f"uklonjeno privatnih blokova: {blocks}; linkova ka izbacenom: {links}")
    for label, files in sorted(warnings.items()):
        shown = ", ".join(sorted(files)[:4]) + (" ..." if len(files) > 4 else "")
        print(f"upozorenje, {label}: {len(files)} fajl(a): {shown}")
    if make_zip:
        archive = shutil.make_archive(str(OUT_DIR / NAME), "zip", OUT_DIR, NAME)
        print(f"zip: {archive}")
    if leaked or leftover:
        print(f"GRESKA: privatni fajlovi {leaked} ili blokovi {leftover} u kopiji", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ref", default="HEAD", help="commit ili grana (zadano HEAD)")
    parser.add_argument("--zip", action="store_true", help="napravi i .zip")
    parser.add_argument("--sa-radovima", action="store_true",
                        help="ukljuci rukopise iz radovi/ (bez sablona i lista za predaju)")
    args = parser.parse_args()
    return export(args.ref, args.sa_radovima, args.zip)


if __name__ == "__main__":
    raise SystemExit(main())
