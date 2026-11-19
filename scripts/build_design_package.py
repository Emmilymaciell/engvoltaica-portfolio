#!/usr/bin/env python
"""
build_design_package.py — Monta o pacote de entrega para o Claude Design.

Copia apenas assets APROVADOS (os que o portfólio V2 usa) e gera o ASSET_MAP
automaticamente a partir de portfolio_images.csv — assim o mapa nunca fica
dessincronizado do que existe na pasta.

Saídas : output/claude_design/assets/*
         output/claude_design/ASSET_MAP.md
"""
from __future__ import annotations

import csv
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "derivados" / "portfolio_images"
MANIFEST = ROOT / "data" / "processed" / "portfolio_images.csv"
CASES = ROOT / "data" / "processed" / "cases_master.csv"
DEST = ROOT / "output" / "claude_design" / "assets"
MAP = ROOT / "output" / "claude_design" / "ASSET_MAP.md"

# slug -> nome de entrega (nome que comunica o papel, não a origem)
RENAME = {
    "capa": "CAPA_01.jpg",
    "quem-somos": "INSTITUCIONAL_01.jpg",
    "case-hero": "CASE_01_HERO.jpg",
    "case-apoio-1": "CASE_01_APOIO_A.jpg",
    "case-apoio-2": "CASE_01_APOIO_B.jpg",
    "investimento": "INVESTIMENTO_01.jpg",
    "galeria-industria": "GALERIA_01_INDUSTRIA.jpg",
    "galeria-posto": "GALERIA_02_POSTO.jpg",
    "galeria-condominio": "GALERIA_03_CONDOMINIO.jpg",
    "galeria-solo": "GALERIA_04_USINA_SOLO.jpg",
    "contracapa": "CONTRACAPA_01.jpg",
    "logo-branco": "LOGO_BRANCO.png",
    "logo-azul": "LOGO_AZUL.png",
}


def main() -> int:
    if not MANIFEST.exists():
        sys.exit("ERRO: rode scripts/select_portfolio_images.py antes.")
    DEST.mkdir(parents=True, exist_ok=True)

    with MANIFEST.open(encoding="utf-8-sig") as fh:
        imgs = {r["slug"]: r for r in csv.DictReader(fh)}
    cases = []
    if CASES.exists():
        with CASES.open(encoding="utf-8-sig") as fh:
            cases = list(csv.DictReader(fh))

    rows = []
    for slug, novo in RENAME.items():
        r = imgs.get(slug)
        if not r:
            print(f"AUSENTE no manifesto: {slug}")
            continue
        src = SRC / r["arquivo"]
        if not src.exists():
            print(f"AUSENTE em disco: {src.name}")
            continue
        dst = DEST / novo
        shutil.copy2(src, dst)
        rows.append({**r, "entrega": novo, "bytes_final": dst.stat().st_size})
        print(f"OK {novo:28} {r['largura']}x{r['altura']}")

    # ── ASSET_MAP.md ──
    L = ["# ASSET MAP — Portfólio Engvoltaica V2", "",
         f"> Gerado por `scripts/build_design_package.py` em {datetime.now():%d/%m/%Y %H:%M}.",
         "> Todo arquivo aqui está **aprovado para uso comercial**: são obras executadas",
         "> pela Engvoltaica, do acervo próprio da empresa.", "",
         "## Regras de uso", "",
         "- Recortar é permitido **nestes derivados**; os originais em alta ficam em",
         "  `data/raw/onedrive_selected/` e não devem ser sobrescritos.",
         "- `CAPA_01` e `CONTRACAPA_01` já vêm em 2800 px porque ocupam a página inteira",
         "  em `object-fit: cover` — usar versão menor derruba o dpi efetivo.",
         "- Nenhuma imagem aqui mostra telhado **antes** da instalação. Se precisar de mais",
         "  material, ver a lista de pastas proibidas no briefing.", "",
         "## Arquivos", "",
         "| Arquivo | Dimensão | Peso | Onde usar | O que mostra |",
         "|---|---|---|---|---|"]
    for r in rows:
        kb = int(r["bytes_final"]) // 1024
        L.append(f"| `{r['entrega']}` | {r['largura']}×{r['altura']} | {kb} KB | "
                 f"{r['uso']} | {r['legenda']} |")

    L += ["", "## Origem de cada imagem", "",
          "| Arquivo | Origem | Original | Recortada |", "|---|---|---|---|"]
    for r in rows:
        L.append(f"| `{r['entrega']}` | `{r['origem']}` | {r.get('origem_px','—')} | "
                 f"{'sim' if r['recorte'] == 'sim' else 'não'} |")

    nomeados = [c for c in cases if c["publishability"] == "PUBLICO_IG" and c["nome_publico"]]
    if nomeados:
        L += ["", "## Cases que podem ser citados pelo nome", "",
              "A própria Engvoltaica divulgou estes nomes no Instagram oficial —",
              "por isso são publicáveis. Qualquer outro nome exige autorização.", "",
              "| Case | Local | Potência | Módulos | Economia divulgada |", "|---|---|---|---|---|"]
        for c in nomeados:
            local = f"{c['cidade']}/{c['estado']}".strip("/") or "Goiás"
            L.append(f"| **{c['nome_publico']}** | {local} | "
                     f"{(c['potencia_kwp'] + ' kWp').replace('.', ',') if c['potencia_kwp'] else '—'} | "
                     f"{c['modulos'] or '—'} | {c['economia'] or '—'} |")

    L.append("")
    MAP.parent.mkdir(parents=True, exist_ok=True)
    MAP.write_text("\n".join(L), encoding="utf-8")

    total = sum(r["bytes_final"] for r in rows) / 1048576
    print(f"\n{len(rows)} assets · {total:.2f} MB -> {DEST.relative_to(ROOT)}")
    print(f"Mapa: {MAP.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
