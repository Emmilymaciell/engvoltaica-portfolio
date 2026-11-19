#!/usr/bin/env python
"""
build_media_manifest.py — Organiza o RAW baixado e monta o manifesto de mídia.

1. Move de data/raw/instagram/_staging/ para images/ ou videos/ renomeando para
   POST_###_<SHORTCODE>_##.<ext> (o shortcode é o elo estável com o Instagram).
2. Lê dimensões, duração, tamanho e SHA-256 de cada arquivo.
3. Detecta duplicatas exatas (sha256) e visuais (perceptual hash), sem apagar nada.
4. Confere a contagem de cada carrossel contra o esperado -> COMPLETO/INCOMPLETO.
5. Atualiza download_status em posts_master.csv.

Saídas : data/processed/media_manifest.csv
         data/processed/media_pending.csv
         data/indexes/duplicates.csv
         logs/build_media_manifest.log
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import struct
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "instagram"
STAGING, IMAGES, VIDEOS, META = RAW / "_staging", RAW / "images", RAW / "videos", RAW / "metadata"
POSTS = ROOT / "data" / "processed" / "posts_master.csv"
OUT = ROOT / "data" / "processed" / "media_manifest.csv"
PENDING = ROOT / "data" / "processed" / "media_pending.csv"
DUPES = ROOT / "data" / "indexes" / "duplicates.csv"
LOG = ROOT / "logs" / "build_media_manifest.log"

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
VID_EXT = {".mp4", ".mov", ".m4v", ".webm"}

COLUMNS = ["post_number", "shortcode", "media_index", "media_type", "source_url",
           "local_raw_path", "derived_path", "filename", "width", "height",
           "duration", "filesize", "sha256", "project", "category",
           "portfolio_relevance", "download_status", "notes"]

_log: list[str] = []


def log(m: str) -> None:
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {m}"
    _log.append(line)
    print(line)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def img_size(p: Path) -> tuple[str, str]:
    try:
        from PIL import Image
        with Image.open(p) as im:
            return str(im.width), str(im.height)
    except Exception:
        return "", ""


def phash(p: Path) -> str:
    try:
        import imagehash
        from PIL import Image
        with Image.open(p) as im:
            return str(imagehash.phash(im))
    except Exception:
        return ""


def video_info(p: Path) -> tuple[str, str, str]:
    """(duração_s, largura, altura). ffprobe se houver; senão lê o átomo mvhd do MP4."""
    ff = shutil.which("ffprobe")
    if ff:
        try:
            r = subprocess.run(
                [ff, "-v", "quiet", "-print_format", "json", "-show_format",
                 "-show_streams", str(p)],
                capture_output=True, text=True, timeout=45)
            d = json.loads(r.stdout)
            dur = str(round(float(d.get("format", {}).get("duration", 0)), 2))
            for s in d.get("streams", []):
                if s.get("codec_type") == "video":
                    return dur, str(s.get("width", "")), str(s.get("height", ""))
            return dur, "", ""
        except Exception:
            pass
    try:  # fallback: duração pelo header mvhd
        data = p.read_bytes()[:400_000]
        i = data.find(b"mvhd")
        if i > 0:
            ver = data[i + 4]
            if ver == 0:
                ts, dur = struct.unpack(">II", data[i + 16: i + 24])
            else:
                ts, dur = struct.unpack(">IQ", data[i + 24: i + 36])
            if ts:
                return str(round(dur / ts, 2)), "", ""
    except Exception:
        pass
    return "", "", ""


def load_posts() -> dict[str, dict]:
    with POSTS.open(encoding="utf-8-sig") as fh:
        return {r["shortcode"]: r for r in csv.DictReader(fh) if r.get("shortcode")}


def organize(by_shortcode: dict[str, dict]) -> int:
    """Renomeia e move o staging para a árvore raw definitiva. RAW nunca é alterado depois."""
    if not STAGING.exists():
        return 0
    IMAGES.mkdir(parents=True, exist_ok=True)
    VIDEOS.mkdir(parents=True, exist_ok=True)
    moved = 0
    for f in sorted(STAGING.rglob("*")):
        if not f.is_file() or f.suffix.lower() in {".part", ".json"}:
            continue
        m = re.match(r"([A-Za-z0-9_-]{5,20})_(\d{1,3})$", f.stem)
        if not m:
            log(f"AVISO: nome fora do padrão, mantido no staging: {f.name}")
            continue
        sc, idx = m.group(1), int(m.group(2))
        post = by_shortcode.get(sc)
        pn = post["post_number"] if post else "000"
        ext = f.suffix.lower()
        dest_dir = VIDEOS if ext in VID_EXT else IMAGES
        dest = dest_dir / f"POST_{pn}_{sc}_{idx:02d}{ext}"
        if dest.exists():
            f.unlink()          # já organizado numa execução anterior
            continue
        shutil.move(str(f), str(dest))
        moved += 1
    for d in sorted(STAGING.rglob("*"), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    log(f"Arquivos organizados do staging: {moved}")
    return moved


def caption_from_meta(sc: str) -> str:
    for j in META.glob(f"{sc}_*.json"):
        try:
            d = json.loads(j.read_text(encoding="utf-8"))
            cap = d.get("description") or d.get("caption") or ""
            if cap:
                return re.sub(r"\s+", " ", cap).strip()
        except Exception:
            continue
    return ""


def main() -> int:
    by_sc = load_posts()
    organize(by_sc)

    rows, phashes = [], defaultdict(list)
    for base, kind in ((IMAGES, "image"), (VIDEOS, "video")):
        if not base.exists():
            continue
        for f in sorted(base.iterdir()):
            if not f.is_file():
                continue
            m = re.match(r"POST_(\d{3})_([A-Za-z0-9_-]+)_(\d{2})", f.stem)
            if not m:
                continue
            pn, sc, idx = m.group(1), m.group(2), m.group(3)
            post = by_sc.get(sc, {})
            w = h = dur = ""
            if kind == "image":
                w, h = img_size(f)
                ph = phash(f)
                if ph:
                    phashes[ph].append(f.name)
            else:
                dur, w, h = video_info(f)
            rows.append({
                "post_number": pn, "shortcode": sc, "media_index": idx,
                "media_type": kind, "source_url": post.get("url", ""),
                "local_raw_path": str(f.relative_to(ROOT)).replace("\\", "/"),
                "derived_path": "", "filename": f.name,
                "width": w, "height": h, "duration": dur,
                "filesize": str(f.stat().st_size), "sha256": sha256(f),
                "project": post.get("project", ""), "category": post.get("category", ""),
                "portfolio_relevance": post.get("portfolio_relevance", ""),
                "download_status": "OK", "notes": "",
            })

    # ── carrosséis: conferir contagem ──
    got = defaultdict(int)
    for r in rows:
        got[r["shortcode"]] += 1
    for r in rows:
        post = by_sc.get(r["shortcode"], {})
        exp = (post.get("media_count_expected") or "").strip()
        if exp.isdigit() and got[r["shortcode"]] < int(exp):
            r["download_status"] = "INCOMPLETO"
            r["notes"] = f"esperado {exp}, recuperado {got[r['shortcode']]}"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)

    # ── pendentes ──
    with PENDING.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["post_number", "shortcode", "type", "url", "motivo"])
        for sc, p in sorted(by_sc.items(), key=lambda kv: kv[1]["post_number"]):
            if got.get(sc, 0) == 0:
                w.writerow([p["post_number"], sc, p["type"], p["url"], "nenhuma mídia recuperada"])

    # ── duplicatas (registradas, nunca apagadas) ──
    exact = defaultdict(list)
    for r in rows:
        exact[r["sha256"]].append(r["filename"])
    DUPES.parent.mkdir(parents=True, exist_ok=True)
    with DUPES.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["tipo", "chave", "arquivos"])
        for k, v in exact.items():
            if len(v) > 1:
                w.writerow(["sha256_identico", k[:16], " | ".join(v)])
        for k, v in phashes.items():
            if len(v) > 1:
                w.writerow(["visualmente_igual", k, " | ".join(v)])

    # ── atualizar posts_master ──
    with POSTS.open(encoding="utf-8-sig") as fh:
        pr = list(csv.DictReader(fh))
        cols = list(pr[0].keys()) if pr else []
    for r in pr:
        sc = r.get("shortcode", "")
        n = got.get(sc, 0)
        r["download_status"] = "PENDENTE" if n == 0 else "OK"
        if n:
            r["media_count_expected"] = r.get("media_count_expected") or str(n)
            cap = caption_from_meta(sc)
            if cap and not r.get("caption"):
                r["caption"] = cap
    if pr:
        with POSTS.open("w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(pr)

    imgs = sum(1 for r in rows if r["media_type"] == "image")
    vids = sum(1 for r in rows if r["media_type"] == "video")
    inc = sum(1 for r in rows if r["download_status"] == "INCOMPLETO")
    log(f"Mídias no manifesto: {len(rows)} (imagens={imgs} vídeos={vids})")
    log(f"Posts com mídia: {len(got)} / {len(by_sc)}  ·  itens incompletos: {inc}")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("\n".join(_log) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
