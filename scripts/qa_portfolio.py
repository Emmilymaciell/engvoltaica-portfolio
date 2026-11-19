#!/usr/bin/env python
"""
qa_portfolio.py — Verificação automática do PDF antes de enviar a cliente.

Checagens:
  FACTUAL  — todo número do PDF tem linha em factual_claims.csv com publicar=SIM?
             nenhum dado bloqueado vazou? CNPJ e percentual corretos?
  VISUAL   — texto invadindo o rodapé, imagem de baixa resolução, página vazia
  TÉCNICO  — contagem de páginas, tamanho A4, peso, texto selecionável, links

Saída : output/reports/qa_portfolio.md   (+ código de saída 1 se houver erro)
"""
from __future__ import annotations

import csv
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "output" / "portfolio" / "v2" / "Portfolio_Engvoltaica_V2.pdf"
CLAIMS = ROOT / "data" / "processed" / "factual_claims.csv"
IMGDIR = ROOT / "output" / "portfolio" / "v2" / "imagens"
REPORT = ROOT / "output" / "reports" / "qa_portfolio.md"

CNPJ_OK = "00.000.000/0001-00"
CNPJ_ERRADO = "00.000.100/0001-00"
DESCONTO_OK = "20"
DESCONTOS_PROIBIDOS = ["25%", "30%"]
LINK_QUEBRADO = "lps.engvoltaica.com.br"
A4 = (595, 842)                 # pontos, tolerância de ±3
MARGEM_RODAPE_MM = 7            # texto abaixo disso encosta no rodapé
MIN_DPI_A4 = 120

achados: list[tuple[str, str, str]] = []   # (severidade, categoria, mensagem)


def erro(cat: str, msg: str) -> None:
    achados.append(("ERRO", cat, msg))


def aviso(cat: str, msg: str) -> None:
    achados.append(("AVISO", cat, msg))


def ok(cat: str, msg: str) -> None:
    achados.append(("OK", cat, msg))


def main() -> int:
    if not PDF.exists():
        sys.exit(f"ERRO: {PDF} não existe. Rode render_pdf.py antes.")
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz

    doc = fitz.open(PDF)
    paginas = len(doc)
    texto_total = "\n".join(p.get_text() for p in doc)
    mb = PDF.stat().st_size / 1048576

    # ── TÉCNICO ──
    if 8 <= paginas <= 12:
        ok("TECNICO", f"{paginas} páginas (faixa alvo 8–12)")
    else:
        aviso("TECNICO", f"{paginas} páginas — fora da faixa alvo de 8 a 12")

    r = doc[0].rect
    if abs(r.width - A4[0]) <= 3 and abs(r.height - A4[1]) <= 3:
        ok("TECNICO", f"formato A4 retrato ({r.width:.0f}x{r.height:.0f} pt)")
    else:
        erro("TECNICO", f"página não é A4: {r.width:.0f}x{r.height:.0f} pt")

    if mb <= 8:
        ok("TECNICO", f"peso {mb:.2f} MB (limite prático de WhatsApp: 8 MB)")
    else:
        erro("TECNICO", f"peso {mb:.2f} MB — acima do limite prático de 8 MB")

    if len(texto_total.strip()) > 2000:
        ok("TECNICO", "texto selecionável (cliente consegue copiar telefone e e-mail)")
    else:
        erro("TECNICO", "PDF praticamente sem texto — virou imagem?")

    # ── FACTUAL ──
    if CNPJ_OK in texto_total:
        ok("FACTUAL", f"CNPJ correto presente ({CNPJ_OK})")
    else:
        erro("FACTUAL", f"CNPJ confirmado {CNPJ_OK} não aparece no documento")
    if CNPJ_ERRADO in texto_total:
        erro("FACTUAL", f"CNPJ INCORRETO {CNPJ_ERRADO} aparece no documento")

    if re.search(rf"\b{DESCONTO_OK}\s*%", texto_total):
        ok("FACTUAL", f"desconto comunicado como {DESCONTO_OK}%")
    else:
        aviso("FACTUAL", f"não encontrei '{DESCONTO_OK}%' no texto")
    for d in DESCONTOS_PROIBIDOS:
        if d in texto_total:
            erro("FACTUAL", f"percentual histórico '{d}' aparece no documento "
                            "(ver docs/DECISIONS.md · DEC-004)")

    if LINK_QUEBRADO in texto_total:
        erro("FACTUAL", f"o documento aponta para '{LINK_QUEBRADO}', que retorna 404")
    else:
        ok("FACTUAL", "nenhum link para a LP quebrada")

    # claims bloqueadas não podem ter vazado
    if CLAIMS.exists():
        with CLAIMS.open(encoding="utf-8-sig") as fh:
            claims = list(csv.DictReader(fh))
        bloq = [c for c in claims if c["publicar"] == "NAO"]
        vazou = []
        for c in bloq:
            for tok in re.findall(r"[><~]?\s*\d{1,2}(?:[.,]\d+)?\s*%\s*a\.?\s*m\.?",
                                  c["valor"] or "", re.I):
                if re.sub(r"\s", "", tok) in re.sub(r"\s", "", texto_total):
                    vazou.append(f"{c['claim_id']} ({tok.strip()})")
        if vazou:
            erro("FACTUAL", "dado BLOQUEADO vazou para o PDF: " + ", ".join(vazou))
        else:
            ok("FACTUAL", f"{len(bloq)} afirmação(ões) bloqueada(s) — nenhuma no documento")

        publicaveis = sum(1 for c in claims if c["publicar"].startswith("SIM"))
        ok("FACTUAL", f"{publicaveis} afirmações com fonte e liberadas para publicação")

    # ── VISUAL ──
    limite = MARGEM_RODAPE_MM * 2.834645
    for i, page in enumerate(doc, 1):
        h = page.rect.height
        corpo = [b for b in page.get_text("blocks")
                 if b[4].strip() and len(b[4].strip()) > 45]
        for b in corpo:
            if b[3] > h - limite:
                aviso("VISUAL", f"pág. {i}: bloco de texto a {h - b[3]:.1f} pt do fim "
                                f"— confira se não encosta no rodapé")
                break
        if len(page.get_text().strip()) < 40 and not page.get_images():
            erro("VISUAL", f"pág. {i}: praticamente vazia")

        for img in page.get_images(full=True):
            try:
                info = doc.extract_image(img[0])
                w, hh = info["width"], info["height"]
                for r_ in page.get_image_rects(img[0]):
                    dpi_w = w / (r_.width / 72) if r_.width else 999
                    if dpi_w < MIN_DPI_A4 and r_.width > 120:
                        aviso("VISUAL", f"pág. {i}: imagem {w}x{hh} renderizada a "
                                        f"~{dpi_w:.0f} dpi — baixa para impressão")
                    break
            except Exception:
                continue

    # ── contatos ──
    for rot, val in (("WhatsApp", "00000-0000"), ("e-mail", "@engvoltaica.com.br"),
                     ("site", "engvoltaica.com.br"), ("CREA", "00000/RF")):
        (ok if val in texto_total else aviso)("CONTATO",
            f"{rot} {'presente' if val in texto_total else 'AUSENTE'} ({val})")

    # ── imagens de origem ──
    if IMGDIR.exists():
        pequenas = []
        try:
            from PIL import Image
            for f in IMGDIR.glob("*.jpg"):
                with Image.open(f) as im:
                    if max(im.size) < 1000:
                        pequenas.append(f"{f.name} ({im.width}x{im.height})")
        except Exception:
            pass
        if pequenas:
            aviso("VISUAL", "imagens de origem pequenas: " + ", ".join(pequenas))
        else:
            ok("VISUAL", "todas as imagens de origem com resolução adequada")

    # ── relatório ──
    erros = [a for a in achados if a[0] == "ERRO"]
    avisos = [a for a in achados if a[0] == "AVISO"]
    oks = [a for a in achados if a[0] == "OK"]
    veredito = ("REPROVADO" if erros else ("APROVADO COM RESSALVAS" if avisos else "APROVADO"))

    L = ["# QA — Portfólio Engvoltaica V2", "",
         f"Executado em {datetime.now():%d/%m/%Y %H:%M} por `scripts/qa_portfolio.py`.", "",
         f"## Veredito: **{veredito}**", "",
         f"| | |", "|---|---|",
         f"| Erros | **{len(erros)}** |", f"| Avisos | {len(avisos)} |",
         f"| Verificações OK | {len(oks)} |", f"| Páginas | {paginas} |",
         f"| Peso | {mb:.2f} MB |", ""]
    for titulo, grupo, marca in (("Erros", erros, "❌"), ("Avisos", avisos, "⚠️"),
                                 ("Verificações aprovadas", oks, "✅")):
        if grupo:
            L += [f"## {titulo}", ""]
            for _, cat, msg in grupo:
                L.append(f"- {marca} **{cat}** — {msg}")
            L.append("")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(L), encoding="utf-8")

    print(f"VEREDITO: {veredito}  ({len(erros)} erros, {len(avisos)} avisos, {len(oks)} ok)")
    for sev, cat, msg in erros + avisos:
        print(f"  [{sev}] {cat}: {msg}")
    print(f"-> {REPORT.relative_to(ROOT)}")
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
