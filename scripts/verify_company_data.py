#!/usr/bin/env python
"""
verify_company_data.py — Confere dados cadastrais direto nos documentos oficiais.

Resolve divergências abrindo a fonte primária (cartão CNPJ, contrato social,
certidão do CREA) em vez de confiar em memória ou em texto de outra IA.

Saídas : data/processed/company_identity.csv
         docs/evidence/company_identity_evidence.txt
         logs/verify_company_data.log
"""
from __future__ import annotations

import csv
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Pasta corporativa sincronizada (somente leitura). Configure ENGV_ONEDRIVE_DIR.
ONEDRIVE = Path(__import__("os").environ.get("ENGV_ONEDRIVE_DIR", r"C:\caminho\exemplo\PastaCorporativa\OneDrive"))
OUT = ROOT / "data" / "processed" / "company_identity.csv"
EVID = ROOT / "docs" / "evidence" / "company_identity_evidence.txt"
LOG = ROOT / "logs" / "verify_company_data.log"

# Documentos oficiais localizados no OneDrive (somente leitura).
DOCS = [
    ("cartao_cnpj_engvoltaica",
     r"5_FOTOVOLTAICO_RESTAURADO\09_Documentos ENGVOLTAICA\1_CNPJ\CNPJ ENGVOLTAICA.pdf"),
    ("cartao_cnpj_engvoltaica_2",
     r"5_FOTOVOLTAICO_RESTAURADO\09_Documentos ENGVOLTAICA\1_CNPJ\CNPJ.pdf"),
    ("qsa_engvoltaica",
     r"5_FOTOVOLTAICO_RESTAURADO\09_Documentos ENGVOLTAICA\1_CNPJ\Consulta Quadro de Sócios e Administradores - QSA (1).pdf"),
    ("certidao_crea",
     r"5_FOTOVOLTAICO_RESTAURADO\09_Documentos ENGVOLTAICA\1_CNPJ\C.R.Q. de Empresa.pdf"),
    ("cartao_cnpj_consorcio",
     r"1_Consórcio de Usinas\7_Documentos Consorcio Engvoltaica\CNPJ Consórcio Engvoltaica\0_Documentos e Contrato\Cartão CNPJ_Consórcio Engvoltaica.pdf"),
    ("cartao_cnpj_parceira1",
     r"1_Consórcio de Usinas\7_Documentos Consorcio Engvoltaica\Contrato Social - PARCEIRA1\0_Documentos e Contratos\CNPJ.pdf"),
    ("cartao_cnpj_parceira2",
     r"1_Consórcio de Usinas\7_Documentos Consorcio Engvoltaica\Contrato Social - PARCEIRA2\CNPJ (4).pdf"),
]

CNPJ_RE = re.compile(r"\b(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\b")
FIELDS = {
    "razao_social": r"NOME EMPRESARIAL\s*\n(.+)",
    "nome_fantasia": r"NOME DE FANTASIA\)\s*\n(.+)",
    "abertura": r"DATA DE ABERTURA\s*\n(\d{2}/\d{2}/\d{4})",
    "situacao": r"SITUAÇÃO CADASTRAL\s*\n(ATIVA|BAIXADA|SUSPENSA|INAPTA)",
    "capital_social": r"CAPITAL SOCIAL:\s*\n?(R\$[\d\.,]+)",
    "crea_registro": r"Registro nr\.\.:\s*(\S+)",
    "crea_rt": r"Nome\.+:\s*([A-ZÁÂÃÉÊÍÓÔÕÚÇ\s]+?)\s*\n",
}
_log: list[str] = []


def log(m: str) -> None:
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {m}"
    _log.append(line)
    print(line)


def read_pdf(p: Path) -> str:
    try:
        import fitz
        with fitz.open(p) as d:
            return "\n".join(pg.get_text() for pg in d)
    except Exception as e:
        log(f"  ! falha ao ler {p.name}: {e}")
        return ""


def main() -> int:
    rows, evidence = [], []
    evidence.append("EVIDÊNCIA DOCUMENTAL — IDENTIDADE DA EMPRESA")
    evidence.append(f"Gerado por scripts/verify_company_data.py em {datetime.now():%d/%m/%Y %H:%M}")
    evidence.append("Fonte: documentos oficiais no OneDrive (lidos, nunca alterados).")
    evidence.append("=" * 78)

    for tag, rel in DOCS:
        p = ONEDRIVE / rel
        if not p.exists():
            log(f"AUSENTE: {rel}")
            rows.append({"documento": tag, "arquivo": rel, "encontrado": "NAO",
                         "cnpj": "", "razao_social": "", "detalhes": "arquivo não localizado"})
            continue
        text = read_pdf(p)
        cnpjs = list(dict.fromkeys(CNPJ_RE.findall(text)))
        campos = {}
        for k, pat in FIELDS.items():
            m = re.search(pat, text)
            if m:
                campos[k] = re.sub(r"\s+", " ", m.group(1)).strip()

        log(f"OK {tag}: CNPJ={cnpjs} razao={campos.get('razao_social','')[:45]}")
        rows.append({
            "documento": tag, "arquivo": rel, "encontrado": "SIM",
            "cnpj": " | ".join(cnpjs),
            "razao_social": campos.get("razao_social", ""),
            "detalhes": "; ".join(f"{k}={v}" for k, v in campos.items() if k != "razao_social"),
        })
        evidence.append("")
        evidence.append(f"### {tag}")
        evidence.append(f"Arquivo: {rel}")
        evidence.append(f"CNPJ encontrado: {', '.join(cnpjs) or '(nenhum)'}")
        for k, v in campos.items():
            evidence.append(f"  {k}: {v}")

    # ── veredito sobre a divergência de dígito (valores fictícios) ──
    principais = [r for r in rows
                  if r["encontrado"] == "SIM"
                  and "ENGVOLTAICA ENERGIA SOLAR" in (r["razao_social"] or "").upper()]
    achados = {c for r in principais for c in r["cnpj"].split(" | ") if c}
    crea = next((r for r in rows if r["documento"] == "certidao_crea" and r["encontrado"] == "SIM"), None)
    if crea:
        achados |= {c for c in crea["cnpj"].split(" | ") if c}

    evidence += ["", "=" * 78, "VEREDITO — CNPJ DA ENGVOLTAICA ENERGIA SOLAR LTDA", "=" * 78,
                 f"Informado originalmente pela usuária : 00.000.100/0001-00",
                 f"Encontrado nos documentos oficiais   : {', '.join(sorted(achados)) or '(nenhum)'}",
                 f"Documentos que confirmam             : {len(principais) + (1 if crea else 0)}"]
    if achados == {"00.000.000/0001-00"}:
        veredito = "CONFIRMADO: 00.000.000/0001-00 (o valor informado, com 100, está incorreto)"
    elif len(achados) == 1:
        veredito = f"CONFIRMADO: {achados.pop()}"
    else:
        veredito = f"INCONCLUSIVO — múltiplos valores: {sorted(achados)}"
    evidence += [f"VEREDITO: {veredito}", ""]
    log(f"VEREDITO: {veredito}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=["documento", "arquivo", "encontrado",
                                           "cnpj", "razao_social", "detalhes"])
        w.writeheader()
        w.writerows(rows)
    EVID.parent.mkdir(parents=True, exist_ok=True)
    EVID.write_text("\n".join(evidence), encoding="utf-8")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("\n".join(_log) + "\n", encoding="utf-8")
    log(f"-> {OUT.relative_to(ROOT)} · {EVID.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
