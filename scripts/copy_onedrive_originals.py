#!/usr/bin/env python
"""
copy_onedrive_originals.py — Traz os originais em alta do OneDrive.

A V1 usou cópias já reamostradas (1600 px). Para páginas de sangria total
(capa e contracapa) isso não basta: o `object-fit: cover` amplia a imagem
muito além da largura da página e o dpi efetivo despenca.

Este script copia os ORIGINAIS do OneDrive para data/raw/onedrive_selected/,
sem alterar a origem (docs/DECISIONS.md · DEC-002).

Saída : data/raw/onedrive_selected/*.jpg
        data/processed/onedrive_originals.csv
"""
from __future__ import annotations

import csv
import hashlib
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Pasta corporativa sincronizada (somente leitura). Configure ENGV_ONEDRIVE_DIR.
ONEDRIVE = Path(__import__("os").environ.get("ENGV_ONEDRIVE_DIR", r"C:\caminho\exemplo\PastaCorporativa\OneDrive"))
DEST = ROOT / "data" / "raw" / "onedrive_selected"
MANIFEST = ROOT / "data" / "processed" / "onedrive_originals.csv"
LOG = ROOT / "logs" / "copy_onedrive_originals.log"

BASE = r"5_FOTOVOLTAICO_RESTAURADO\Imagens\18_Marketing\Videos Engvoltaica"

# nome de destino -> (caminho no OneDrive, para que serve)
ORIGINAIS = {
    "capa-original.jpg":        (rf"{BASE}\Usinas\DJI_0036.JPG", "Capa — usina em solo, sangria total"),
    "contracapa-original.jpg":  (rf"{BASE}\Usinas\DJI_0032.JPG", "Contracapa — usina em solo com caminhonete"),
    "case-hero-original.jpg":   (rf"{BASE}\Usinas\WhatsApp Image 2024-11-19 at 14.10.17 (1).jpeg", "Case principal — hero"),
    "case-apoio1-original.jpg": (rf"{BASE}\Usinas\WhatsApp Image 2024-11-19 at 14.10.17.jpeg", "Case — apoio vertical"),
    "case-apoio2-original.jpg": (rf"{BASE}\Usinas\WhatsApp Image 2024-11-19 at 14.09.54.jpeg", "Case — apoio, usina com cidade ao fundo"),
    "quem-somos-original.jpg":  (rf"{BASE}\Imagem do WhatsApp de 2024-01-17 à(s) 10.42.01_06dfd5e0.jpg", "Quem somos"),
    "industria-original.jpg":   (rf"{BASE}\Excel\DJI_0010.JPG", "Galeria — complexo industrial"),
    "posto-original.jpg":       (rf"{BASE}\USINA COMERCIAL POSTO CLIENTE D 176 PLACAS DE 450w ECONOMIA ANUAL R$ 135.575,76.jpg", "Galeria — posto de combustíveis"),
    "condominio-original.jpg":  (rf"{BASE}\Cliente E.jpg", "Galeria — condomínio Cliente E"),
    "aragoiania-original.jpg":  (rf"{BASE}\Usina Cliente F\DJI_0007.JPG", "Galeria — usina em solo"),
    "investimento-original.jpg": (rf"{BASE}\Usinas\DJI_0033.JPG", "Página investimento"),
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    from PIL import Image
    DEST.mkdir(parents=True, exist_ok=True)
    rows, faltando = [], []

    for nome, (rel, uso) in ORIGINAIS.items():
        src = ONEDRIVE / rel
        if not src.exists():
            print(f"AUSENTE: {rel}")
            faltando.append(rel)
            continue
        dst = DEST / nome
        if not dst.exists():
            shutil.copy2(src, dst)          # cópia; a origem não é tocada
        try:
            with Image.open(dst) as im:
                w, h = im.size
        except Exception:
            w = h = 0
        rows.append({
            "arquivo": nome, "origem_onedrive": rel.replace("\\", "/"),
            "largura": w, "altura": h,
            "megapixels": round(w * h / 1e6, 2) if w and h else "",
            "bytes": dst.stat().st_size, "sha256": sha256(dst), "uso": uso,
        })
        print(f"OK {nome:28} {w}x{h}  {dst.stat().st_size // 1024} KB")

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=["arquivo", "origem_onedrive", "largura",
                                           "altura", "megapixels", "bytes", "sha256", "uso"])
        w.writeheader()
        w.writerows(rows)

    total = sum(r["bytes"] for r in rows) / 1048576
    print(f"\n{len(rows)} originais copiados · {total:.1f} MB")
    if faltando:
        print(f"{len(faltando)} não localizados (ver log)")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(f"{datetime.now():%Y-%m-%d %H:%M:%S}\n"
                   f"copiados={len(rows)} faltando={len(faltando)}\n"
                   + "\n".join(faltando), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
