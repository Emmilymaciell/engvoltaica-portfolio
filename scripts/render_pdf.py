#!/usr/bin/env python
"""
render_pdf.py — Renderiza o HTML do portfólio em PDF A4 via Edge headless.

O Edge já vem no Windows, respeita @page/CSS de impressão e produz PDF com
texto selecionável (importante: um cliente consegue copiar o telefone).

Uso: python scripts/render_pdf.py [--html CAMINHO] [--pdf CAMINHO]
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HTML = ROOT / "output" / "portfolio" / "v2" / "Portfolio_Engvoltaica_V2.html"
DEFAULT_PDF = ROOT / "output" / "portfolio" / "v2" / "Portfolio_Engvoltaica_V2.pdf"
LOG = ROOT / "logs" / "portfolio_render.log"

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_edge() -> str:
    for c in EDGE_CANDIDATES:
        if Path(c).exists():
            return c
    found = shutil.which("msedge") or shutil.which("chrome")
    if found:
        return found
    sys.exit("ERRO: Edge/Chrome não encontrado para renderizar o PDF.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", type=Path, default=DEFAULT_HTML)
    ap.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    args = ap.parse_args()

    if not args.html.exists():
        sys.exit(f"ERRO: {args.html} não existe. Rode scripts/build_portfolio.py antes.")

    edge = find_edge()
    # Perfil isolado: não interfere no navegador da usuária nem depende dele.
    profile = ROOT / "tmp" / "edge_render_profile"
    profile.mkdir(parents=True, exist_ok=True)

    args.pdf.parent.mkdir(parents=True, exist_ok=True)
    before = args.pdf.stat().st_mtime if args.pdf.exists() else 0

    cmd = [edge, "--headless=new", "--disable-gpu",
           f"--user-data-dir={profile}",
           "--no-pdf-header-footer",
           "--run-all-compositor-stages-before-draw",
           "--virtual-time-budget=15000",
           f"--print-to-pdf={args.pdf}", str(args.html)]

    print(f"Renderizando {args.html.name} …")
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=240)

    for _ in range(30):                     # o Edge escreve o arquivo de forma assíncrona
        if args.pdf.exists() and args.pdf.stat().st_mtime > before:
            break
        time.sleep(0.5)

    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text((proc.stdout or "") + "\n" + (proc.stderr or ""), encoding="utf-8")

    if not args.pdf.exists():
        print((proc.stderr or "")[-1500:])
        sys.exit("ERRO: o PDF não foi gerado.")

    mb = args.pdf.stat().st_size / 1048576
    print(f"PDF : {args.pdf.relative_to(ROOT)}  ({mb:.2f} MB)")
    if mb > 8:
        print("AVISO: acima de 8 MB — reduza a qualidade em select_portfolio_images.py")
    print("\nPróximo: python scripts/qa_portfolio.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
