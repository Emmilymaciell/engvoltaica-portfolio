#!/usr/bin/env python
"""
build_cases.py — Consolida projetos/usinas reais a partir da auditoria.

Um projeto pode aparecer em vários posts: aqui ele vira UMA linha, com os
posts relacionados listados. Isso evita contar 5 posts como 5 usinas.

Entradas : data/input/chrome_audit/CATALOGO_INSTAGRAM_ENGVOLTAICA.md
           data/processed/posts_master.csv
Saídas   : data/processed/cases_master.csv
           data/processed/factual_claims.csv
           docs/CASES_MASTER.md
           logs/build_cases.log

Política de publicação (docs/DECISIONS.md · DEC-006):
  PUBLICO_IG      → a própria Engvoltaica divulgou o nome no Instagram oficial.
  INTERNO         → nome só aparece em arquivo técnico; não publicar sem autorização.
  AUTORIZACAO_NEC → precisa de autorização expressa do cliente.
"""
from __future__ import annotations

import csv
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "input" / "chrome_audit" / "CATALOGO_INSTAGRAM_ENGVOLTAICA.md"
POSTS = ROOT / "data" / "processed" / "posts_master.csv"
OUT_CASES = ROOT / "data" / "processed" / "cases_master.csv"
OUT_CLAIMS = ROOT / "data" / "processed" / "factual_claims.csv"
OUT_DOC = ROOT / "docs" / "CASES_MASTER.md"
LOG = ROOT / "logs" / "build_cases.log"

CASE_COLUMNS = [
    "case_id", "nome_publico", "nome_interno", "cidade", "estado", "tipo",
    "status", "potencia_kwp", "modulos", "geracao", "economia", "investimento",
    "dados_financeiros", "posts_relacionados", "arquivos_instagram",
    "arquivos_onedrive", "publishability", "verification_status",
    "portfolio_priority", "notes",
]
CLAIM_COLUMNS = [
    "claim_id", "escopo", "afirmacao", "valor", "fonte_tipo", "fonte_ref",
    "data_fonte", "status", "publicar", "observacao",
]

GO_CITIES = [
    "Aparecida de Goiânia", "Santo Antônio de Goiás", "Caldas Novas",
    "Fazenda Nova", "Goiânia", "Anápolis", "Nerópolis", "Planalmira",
    "Trindade", "Vianópolis", "Serrinha", "Aragoiânia",
]
_log: list[str] = []


def log(m: str) -> None:
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {m}"
    _log.append(line)
    print(line)


def sa(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def clean(v: str) -> str:
    v = re.sub(r"\s+", " ", (v or "")).strip()
    v = re.sub(r"\*\*", "", v).strip(" .·-—")
    return "" if v in {"—", "-", "–"} else v


def posts_in(text: str) -> list[str]:
    """Todos os números de POST citados no bloco, normalizados para 3 dígitos."""
    nums = re.findall(r"POSTS?\s*[:\s]?\s*([\d,\s·e]+)", text, re.I)
    found: set[int] = set()
    for grp in nums:
        for d in re.findall(r"\d{1,3}", grp):
            if 1 <= int(d) <= 245:
                found.add(int(d))
    # também captura "- **Posts:** 101 (…) · 75 (…)"
    for d in re.findall(r"\bPOST\s+(\d{1,3})\b", text, re.I):
        if 1 <= int(d) <= 245:
            found.add(int(d))
    return [f"{n:03d}" for n in sorted(found)]


def split_place(s: str) -> tuple[str, str]:
    for c in GO_CITIES:
        if sa(c.lower()) in sa(s.lower()):
            return c, "GO"
    return "", "GO" if re.search(r"\bGO\b|Goi[áa]s", s) else ""


def num_after(text: str, *kw: str) -> str:
    low = sa(text.lower())
    for k in kw:
        m = re.search(sa(k.lower()), low)
        if m:
            win = text[m.start(): m.start() + 170]
            mv = re.search(r"R\$\s*[\d.,]+(?:\s*(?:mil|milh[õo]es))?", win, re.I)
            if mv:
                return re.sub(r"\s+", " ", mv.group(0))
    return ""


PROJ_RE = re.compile(r"^###\s+PROJETO\s+(\d{1,3})\s*[—–-]\s*(.+?)\s*$", re.M)


def parse_projects(text: str) -> list[dict]:
    marks = [(m.group(1), m.group(2), m.start()) for m in PROJ_RE.finditer(text)]
    end_section = text.find("### OUTRAS USINAS COM DADOS")
    if end_section == -1:
        end_section = len(text)
    cases = []
    for i, (num, title, start) in enumerate(marks):
        stop = marks[i + 1][2] if i + 1 < len(marks) else end_section
        block = text[start:stop]

        # "Atacarejo Cliente A (Comercial) — Cidade Exemplo/UF"
        title = clean(title)
        tipo_paren = ""
        mt = re.search(r"\(([^)]+)\)", title)
        if mt:
            tipo_paren = mt.group(1)
        nome = clean(re.sub(r"\([^)]*\)", "", title).split("—")[0])
        cidade, uf = split_place(title + " " + block)

        def field(*keys: str) -> str:
            for k in keys:
                m = re.search(rf"^-\s*\*\*{k}[^:]*:?\*\*\s*(.+)$", block, re.M | re.I)
                if m:
                    return clean(m.group(1))
            return ""

        tipo = field("Tipo") or tipo_paren
        status = field("Status")
        tecnico = field("Potência/técnico", "Potencia/tecnico", "Técnico", "Tecnico")
        resultado = field("Resultado")
        uso = field("Uso no portfólio", "Uso")
        blob = f"{tecnico} {resultado} {block}"

        mp = re.search(r"([\d.,]+)\s*(?:KWP|kWp|kwp|k[wW]p)", blob)
        mm = re.search(r"(\d{1,4})\s*(?:m[óo]dulos?|placas?)", blob, re.I)
        mg = re.search(r"([\d.,]+)\s*kWh\s*/?\s*m[êe]s", blob, re.I)
        rc = re.search(r"[><~]?\s*\d{1,2}(?:[.,]\d+)?\s*%\s*(?:a\.?\s*m\.?|ao m[êe]s)", blob, re.I)

        econ = num_after(blob, "economia media anual", "economia anual", "economia")
        inv = num_after(blob, "investimento")

        # Nome citado pela própria Engvoltaica no IG oficial => publicável.
        publishability = "PUBLICO_IG" if nome and not re.match(
            r"^(Usina|Projeto|Eletropostos?)\b", nome) else "GENERICO_SEM_NOME"

        verification = "NAO_PUBLICAR_SEM_REVISAO" if rc else (
            "CONFIRMADO_IG" if (econ or mp or mm) else "PARCIALMENTE_CONFIRMADO")

        cases.append({
            "case_id": f"CASE_{int(num):03d}",
            "nome_publico": nome,
            "nome_interno": "",
            "cidade": cidade, "estado": uf,
            "tipo": tipo, "status": status,
            "potencia_kwp": mp.group(1).replace(",", ".") if mp else "",
            "modulos": mm.group(1) if mm else "",
            "geracao": f"{mg.group(1)} kWh/mês" if mg else "",
            "economia": econ, "investimento": inv,
            "dados_financeiros": clean(resultado),
            "posts_relacionados": "|".join(posts_in(block)),
            "arquivos_instagram": "", "arquivos_onedrive": "",
            "publishability": publishability,
            "verification_status": verification,
            "portfolio_priority": "",
            "notes": clean(uso),
        })
    log(f"Projetos nomeados extraídos: {len(cases)}")
    return cases


def parse_other_plants(text: str) -> list[dict]:
    """'### OUTRAS USINAS COM DADOS TÉCNICOS' — bullets soltos, um por usina."""
    start = text.find("### OUTRAS USINAS COM DADOS")
    if start == -1:
        return []
    stop = text.find("## SELEÇÃO FINAL", start)
    block = text[start: stop if stop != -1 else len(text)]
    out = []
    seq = 0
    for line in block.splitlines():
        m = re.match(r"^-\s*POST\s*(\d{1,3})\s*[—–-]\s*(.+)$", line.strip(), re.I)
        if not m:
            continue
        seq += 1
        pn, desc = int(m.group(1)), clean(m.group(2))
        mp = re.search(r"([\d.,]+)\s*(?:KWP|kWp|kwp)", desc)
        mm = re.search(r"(\d{1,4})\s*(?:m[óo]dulos?|placas?)", desc, re.I)
        mg = re.search(r"([\d.,]+)\s*kWh\s*/?\s*m[êe]s", desc, re.I)
        cidade, uf = split_place(desc)
        out.append({
            "case_id": f"PLANT_{seq:03d}",
            "nome_publico": "", "nome_interno": "",
            "cidade": cidade, "estado": uf,
            "tipo": "Usina com dados técnicos publicados", "status": "",
            "potencia_kwp": mp.group(1).replace(",", ".") if mp else "",
            "modulos": mm.group(1) if mm else "",
            "geracao": f"{mg.group(1)} kWh/mês" if mg else "",
            "economia": num_after(desc, "economia"),
            "investimento": "", "dados_financeiros": desc,
            "posts_relacionados": f"{pn:03d}",
            "arquivos_instagram": "", "arquivos_onedrive": "",
            "publishability": "GENERICO_SEM_NOME",
            "verification_status": "CONFIRMADO_IG" if (mp or mm) else "PARCIALMENTE_CONFIRMADO",
            "portfolio_priority": "",
            "notes": "Usina individual citada no catálogo, sem nome de cliente.",
        })
    log(f"Usinas individuais extraídas: {len(out)}")
    return out


def build_claims(cases: list[dict]) -> list[dict]:
    """Cada número comercial vira uma linha auditável com fonte e status."""
    claims, i = [], 0
    for c in cases:
        posts = c["posts_relacionados"].split("|") if c["posts_relacionados"] else []
        ref = "POST " + ", ".join(posts) if posts else "catálogo IG"
        for campo, valor, desc in (
            ("potencia_kwp", c["potencia_kwp"], "Potência instalada (kWp)"),
            ("modulos", c["modulos"], "Quantidade de módulos"),
            ("geracao", c["geracao"], "Geração mensal"),
            ("economia", c["economia"], "Economia divulgada"),
            ("investimento", c["investimento"], "Investimento divulgado"),
        ):
            if not valor:
                continue
            i += 1
            sensivel = campo in {"economia", "investimento"}
            claims.append({
                "claim_id": f"CLM_{i:03d}",
                "escopo": c["case_id"],
                "afirmacao": desc,
                "valor": valor,
                "fonte_tipo": "INSTAGRAM",
                "fonte_ref": ref,
                "data_fonte": "",
                "status": "CONFIRMADO_IG",
                "publicar": "SIM_COM_FRAMING" if sensivel else "SIM",
                "observacao": ("Publicar como 'resultado divulgado pela empresa em [data]', "
                               "nunca como média ou garantia.") if sensivel else "",
            })
        if c["verification_status"] == "NAO_PUBLICAR_SEM_REVISAO":
            i += 1
            claims.append({
                "claim_id": f"CLM_{i:03d}",
                "escopo": c["case_id"],
                "afirmacao": "Alegação de rentabilidade mensal",
                "valor": c["dados_financeiros"],
                "fonte_tipo": "INSTAGRAM",
                "fonte_ref": ref,
                "data_fonte": "",
                "status": "NAO_CONFIRMADO",
                "publicar": "NAO",
                "observacao": "Rentabilidade prometida: exige revisão jurídica/comercial antes de qualquer uso.",
            })
    log(f"Afirmações factuais catalogadas: {len(claims)}")
    return claims


def write_doc(cases: list[dict], claims: list[dict]) -> None:
    named = [c for c in cases if c["case_id"].startswith("CASE_")]
    plants = [c for c in cases if c["case_id"].startswith("PLANT_")]
    L = ["# CASES MASTER — Engvoltaica", "",
         f"> Gerado por `scripts/build_cases.py` em {datetime.now():%d/%m/%Y %H:%M}.",
         "> Fonte: auditoria do Instagram oficial (`data/input/chrome_audit/`).",
         "> **Não editar à mão** — reexecute o script.", "",
         f"**{len(named)} projetos nomeados · {len(plants)} usinas individuais · "
         f"{len(claims)} afirmações factuais catalogadas**", "",
         "## Legenda de publicabilidade", "",
         "| Código | Significado |", "|---|---|",
         "| `PUBLICO_IG` | A própria Engvoltaica divulgou o nome no Instagram oficial — pode publicar. |",
         "| `GENERICO_SEM_NOME` | Não há nome de cliente envolvido; seguro por natureza. |",
         "| `INTERNO` | Nome só existe em arquivo técnico — **não publicar** sem autorização. |", "",
         "---", "", "## Projetos nomeados", ""]
    for c in named:
        L.append(f"### {c['case_id']} — {c['nome_publico'] or '(sem nome público)'}")
        L.append("")
        for rot, val in (("Tipo", c["tipo"]), ("Cidade", f"{c['cidade']}/{c['estado']}".strip("/")),
                         ("Status", c["status"]), ("Potência", f"{c['potencia_kwp']} kWp" if c["potencia_kwp"] else ""),
                         ("Módulos", c["modulos"]), ("Geração", c["geracao"]),
                         ("Economia divulgada", c["economia"]), ("Investimento", c["investimento"]),
                         ("Posts", ", ".join(c["posts_relacionados"].split("|")) if c["posts_relacionados"] else ""),
                         ("Publicabilidade", c["publishability"]), ("Verificação", c["verification_status"]),
                         ("Uso sugerido", c["notes"])):
            if val:
                L.append(f"- **{rot}:** {val}")
        L.append("")
    L += ["---", "", "## Usinas individuais com dados técnicos publicados", "",
          "| ID | Potência | Módulos | Geração | Economia | Post |", "|---|---|---|---|---|---|"]
    for c in plants:
        L.append(f"| {c['case_id']} | {c['potencia_kwp'] or '—'} | {c['modulos'] or '—'} | "
                 f"{c['geracao'] or '—'} | {c['economia'] or '—'} | {c['posts_relacionados']} |")
    blocked = [c for c in claims if c["publicar"] == "NAO"]
    if blocked:
        L += ["", "---", "", "## ⚠️ Bloqueados para publicação", "",
              "Exigem revisão jurídica/comercial antes de qualquer uso comercial:", ""]
        for c in blocked:
            L.append(f"- **{c['escopo']}** — {c['afirmacao']}: {c['valor']} (fonte: {c['fonte_ref']})")
    L.append("")
    OUT_DOC.parent.mkdir(parents=True, exist_ok=True)
    OUT_DOC.write_text("\n".join(L), encoding="utf-8")


def main() -> int:
    if not CATALOG.exists():
        log(f"ERRO: catálogo ausente: {CATALOG}")
        return 1
    text = CATALOG.read_text(encoding="utf-8")

    cases = parse_projects(text) + parse_other_plants(text)
    claims = build_claims(cases)

    OUT_CASES.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CASES.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=CASE_COLUMNS)
        w.writeheader()
        w.writerows(cases)
    with OUT_CLAIMS.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=CLAIM_COLUMNS)
        w.writeheader()
        w.writerows(claims)
    write_doc(cases, claims)

    blocked = sum(1 for c in claims if c["publicar"] == "NAO")
    log(f"cases_master.csv: {len(cases)} linhas")
    log(f"factual_claims.csv: {len(claims)} linhas ({blocked} bloqueadas)")
    log(f"docs/CASES_MASTER.md escrito")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("\n".join(_log) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
