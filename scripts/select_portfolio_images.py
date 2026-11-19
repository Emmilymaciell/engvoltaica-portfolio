#!/usr/bin/env python
"""
select_portfolio_images.py — Prepara as imagens aprovadas para o portfólio.

Origem por ordem de preferência (sempre a de maior resolução disponível):
  1. data/raw/onedrive_selected/   — originais em alta do OneDrive
  2. data/raw/instagram/images/    — quando o download do IG já rodou
  3. data/input/previous_portfolio/imagens/  — curadoria da V1 (já reamostrada)

Aplica recorte (para remover lote baldio), reamostra e otimiza. O original
nunca é tocado: tudo sai em derivados/portfolio_images/.

Saídas : derivados/portfolio_images/*.jpg
         data/processed/portfolio_images.csv
         logs/select_portfolio_images.log
"""
from __future__ import annotations

import csv
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OD_SEL = ROOT / "data" / "raw" / "onedrive_selected"
IG_IMG = ROOT / "data" / "raw" / "instagram" / "images"
V1_IMG = ROOT / "data" / "input" / "previous_portfolio" / "imagens"
OUT = ROOT / "derivados" / "portfolio_images"
MANIFEST = ROOT / "data" / "processed" / "portfolio_images.csv"
LOG = ROOT / "logs" / "select_portfolio_images.log"

MAX_PX = 1800              # páginas comuns: A4 a 200+ dpi
MAX_PX_FULLBLEED = 2800    # sangria total: `object-fit: cover` amplia a imagem
FULLBLEED = {"capa", "contracapa"}
QUALITY = 82

# slug -> (origem, recorte (l,t,r,b) em fração ou None, legenda, uso)
# Os recortes removem terreno vazio; ver docs/DATA_QUALITY.md · QD-009.
SELECTION = [
    ("capa",              "capa-original.jpg",        None,
     "Usina em solo · Goiás", "Capa (sangria total)"),
    ("quem-somos",        "quem-somos-original.jpg",  None,
     "Usina em solo executada pela Engvoltaica", "Página Quem somos"),
    ("case-hero",         "case-hero-original.jpg",   (0.10, 0.04, 0.90, 0.84),
     "Usina em solo de grande porte · Goiás", "Case principal — hero"),
    ("case-apoio-1",      "case-apoio1-original.jpg", (0.18, 0.02, 0.92, 0.96),
     "Fileiras em estrutura fixa sobre piso drenante", "Case principal — apoio"),
    ("case-apoio-2",      "case-apoio2-original.jpg", (0.00, 0.00, 1.00, 0.86),
     "Blocos geradores e casa de medição própria", "Case principal — apoio"),
    ("investimento",      "investimento-original.jpg", (0.04, 0.08, 0.96, 1.00),
     "Usina em solo · Goiás", "Página Investimento"),
    ("galeria-industria", "industria-original.jpg",   None,
     "Complexo industrial · Goiás", "Galeria"),
    ("galeria-posto",     "posto-original.jpg",       None,
     "Posto de combustíveis · Goiânia/GO", "Galeria"),
    ("galeria-condominio", "condominio-original.jpg", None,
     "Condomínio residencial · Goiânia/GO", "Galeria"),
    ("galeria-solo",      "aragoiania-original.jpg",  None,
     "Usina em solo · Aragoiânia/GO", "Galeria"),
    ("contracapa",        "contracapa-original.jpg",  (0.04, 0.10, 0.96, 1.00),
     "Usina em solo · Goiás", "Contracapa (sangria total)"),
    ("logo-branco",       "logo-branco.png",          None,
     "Logo Engvoltaica (branco)", "Capa"),
    ("logo-azul",         "logo-azul.png",            None,
     "Logo Engvoltaica (azul)", "Assets"),
]

_log: list[str] = []


def log(m: str) -> None:
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {m}"
    _log.append(line)
    print(line)


def localizar(nome: str) -> Path | None:
    """Primeira origem que tiver o arquivo, na ordem de preferência."""
    for base in (OD_SEL, IG_IMG, V1_IMG):
        p = base / nome
        if p.exists():
            return p
    return None


def main() -> int:
    from PIL import Image

    OUT.mkdir(parents=True, exist_ok=True)
    rows, ausentes = [], []

    for slug, fname, box, caption, uso in SELECTION:
        src = localizar(fname)
        if src is None:
            log(f"AUSENTE: {fname} — pulado")
            ausentes.append(fname)
            continue

        ext = ".png" if src.suffix.lower() == ".png" else ".jpg"
        dest = OUT / f"{slug}{ext}"

        if ext == ".png":                       # logo: preserva transparência
            shutil.copy2(src, dest)
            with Image.open(dest) as im:
                w, h = im.size
            w0, h0 = w, h
        else:
            with Image.open(src) as im:
                w0, h0 = im.size
                im = im.convert("RGB")
                if box:
                    l, t, r, b = box
                    im = im.crop((int(l * w0), int(t * h0), int(r * w0), int(b * h0)))
                lim = MAX_PX_FULLBLEED if slug in FULLBLEED else MAX_PX
                im.thumbnail((lim, lim))
                im.save(dest, quality=QUALITY, optimize=True, progressive=True)
                w, h = im.size

        rows.append({
            "slug": slug, "arquivo": dest.name,
            "origem": str(src.relative_to(ROOT)).replace("\\", "/"),
            "origem_px": f"{w0}x{h0}",
            "recorte": "sim" if box else "nao",
            "largura": w, "altura": h,
            "bytes": dest.stat().st_size,
            "legenda": caption, "uso": uso,
        })
        marca = " (recortada)" if box else ""
        log(f"OK {dest.name:24} {w0}x{h0} -> {w}x{h}{marca}  "
            f"{dest.stat().st_size // 1024} KB")

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=["slug", "arquivo", "origem", "origem_px",
                                           "recorte", "largura", "altura", "bytes",
                                           "legenda", "uso"])
        w.writeheader()
        w.writerows(rows)

    total = sum(r["bytes"] for r in rows) / 1048576
    log(f"{len(rows)} imagens preparadas · {total:.2f} MB"
        + (f" · {len(ausentes)} ausentes" if ausentes else ""))
    log(f"-> {OUT.relative_to(ROOT)}")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("\n".join(_log) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
