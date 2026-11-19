#!/usr/bin/env python
"""
parse_chrome_catalog.py — Converte a auditoria do Claude in Chrome em dados estruturados.

Entradas  : data/input/chrome_audit/CATALOGO_INSTAGRAM_ENGVOLTAICA.md
            data/input/chrome_audit/ENGVOLTAICA_URLS_245.txt
Saídas    : data/processed/posts_master.csv
            data/indexes/shortcode_index.csv
            logs/parse_chrome_catalog.log

Regra do projeto: não inventa valores. Campo sem dado na fonte fica vazio.
Reexecutável e idempotente — sempre reconstrói a partir da fonte.
"""
from __future__ import annotations

import csv
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "data" / "input" / "chrome_audit"
CATALOG = AUDIT / "CATALOGO_INSTAGRAM_ENGVOLTAICA.md"
URLS = AUDIT / "ENGVOLTAICA_URLS_245.txt"
OUT_POSTS = ROOT / "data" / "processed" / "posts_master.csv"
OUT_INDEX = ROOT / "data" / "indexes" / "shortcode_index.csv"
LOG = ROOT / "logs" / "parse_chrome_catalog.log"

COLUMNS = [
    "post_number", "shortcode", "date", "type", "url",
    "caption", "summary", "category", "project", "city", "state",
    "power_kwp", "module_count", "generation", "economy", "investment",
    "return_claim", "portfolio_relevance", "portfolio_usage",
    "media_count_expected", "download_status", "verification_status", "notes",
]

# Municípios de GO citados na auditoria. Usado só para separar cidade/UF do
# campo livre "Projeto/local"; nunca para inferir local onde a fonte não diz.
GO_CITIES = [
    "Aparecida de Goiânia", "Santo Antônio de Goiás", "Caldas Novas",
    "Fazenda Nova", "Goiânia", "Anápolis", "Nerópolis", "Planalmira",
    "Trindade", "Vianópolis", "Serrinha", "Aragoiânia", "Senador Canedo",
]

_log_lines: list[str] = []


def log(msg: str) -> None:
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    _log_lines.append(line)
    print(line)


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def shortcode_from_url(url: str) -> str:
    m = re.search(r"/(?:p|reel|tv)/([A-Za-z0-9_-]+)", url or "")
    return m.group(1) if m else ""


def norm_type(raw: str) -> str:
    """Normaliza o tipo para: reel | carousel_or_image | unknown."""
    r = strip_accents((raw or "").lower())
    if "reel" in r or "video" in r:
        return "reel"
    if "carrossel" in r or "imagem" in r or "post" in r or "foto" in r:
        return "carousel_or_image"
    return "unknown"


def iso_date(br: str) -> str:
    """dd/mm/aaaa -> aaaa-mm-dd. Devolve vazio se não parsear."""
    m = re.match(r"\s*(\d{2})/(\d{2})/(\d{4})\s*$", br or "")
    if not m:
        return ""
    d, mo, y = m.groups()
    try:
        return datetime(int(y), int(mo), int(d)).strftime("%Y-%m-%d")
    except ValueError:
        return ""


def clean(v: str) -> str:
    """Normaliza espaços e converte marcadores de ausência em string vazia."""
    v = re.sub(r"\s+", " ", (v or "")).strip().strip("*").strip()
    if v in {"—", "-", "–", ""}:
        return ""
    low = strip_accents(v.lower())
    if low.startswith("nao informado") or low.startswith("nao ha") or low == "n/a":
        return ""
    return v


# ─────────────────────────── extratores numéricos ───────────────────────────
# Cada um devolve o TRECHO LITERAL da fonte, não um número reinterpretado.

def x_power(t: str) -> str:
    m = re.search(r"(\d{1,3}(?:[.,]\d+)?)\s*(?:k[wW]p|KWP|kWp|kwp)", t or "")
    return m.group(1).replace(",", ".") if m else ""


def x_modules(t: str) -> str:
    m = re.search(r"(\d{1,4})\s*(?:m[óo]dulos?|placas?|painei?s?)", t or "", re.I)
    return m.group(1) if m else ""


def x_generation(t: str) -> str:
    m = re.search(r"([\d.,]+)\s*kWh\s*/?\s*m[êe]s", t or "", re.I)
    return f"{m.group(1)} kWh/mês" if m else ""


def x_money(t: str, *keywords: str) -> str:
    """Primeiro valor em R$ que apareça próximo de uma das palavras-chave."""
    if not t:
        return ""
    low = strip_accents(t.lower())
    for kw in keywords:
        for m in re.finditer(strip_accents(kw.lower()), low):
            win = t[m.start(): m.start() + 160]
            mv = re.search(r"R\$\s*[\d.,]+(?:\s*(?:mil|milh[õo]es))?", win, re.I)
            if mv:
                return re.sub(r"\s+", " ", mv.group(0)).strip()
    return ""


def x_return_claim(t: str) -> str:
    """Alegação de rentabilidade — sensível, sempre marcada para revisão."""
    m = re.search(r"[><~]?\s*\d{1,2}(?:[.,]\d+)?\s*%\s*(?:a\.?\s*m\.?|ao m[êe]s|a\.?\s*a\.?|ao ano)",
                  t or "", re.I)
    return re.sub(r"\s+", " ", m.group(0)).strip() if m else ""


def split_place(project_field: str) -> tuple[str, str, str]:
    """'Atacarejo Cliente A, Cidade Exemplo' -> (projeto, cidade, uf)."""
    txt = clean(project_field)
    if not txt:
        return "", "", ""
    city = ""
    for c in GO_CITIES:                       # lista já ordenada: mais específico primeiro
        if strip_accents(c.lower()) in strip_accents(txt.lower()):
            city = c
            break
    uf = "GO" if city else ("GO" if re.search(r"\bGO\b|Goi[áa]s", txt) else "")
    project = txt
    if city:
        project = re.sub(rf",?\s*{re.escape(city)}\s*(/\s*GO)?", "", txt).strip(" ,/-")
    return project, city, uf


# ─────────────────────────────── parsers ────────────────────────────────────

def parse_urls(path: Path) -> dict[int, dict]:
    """ENGVOLTAICA_URLS_245.txt — a lista canônica de permalinks."""
    out: dict[int, dict] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        parts = raw.split("\t") if "\t" in raw else raw.split(None, 2)
        if len(parts) < 3:
            continue
        num, tp, url = parts[0].strip(), parts[1].strip(), parts[2].strip()
        if not num.isdigit():
            continue
        out[int(num)] = {"type_urls": tp, "url": url,
                         "shortcode": shortcode_from_url(url)}
    log(f"URLs canônicas lidas: {len(out)}")
    return out


ROW_RE = re.compile(r"^\|\s*(\d{1,3})\s*\|(.*)\|\s*$")


def parse_index_table(text: str) -> dict[int, dict]:
    """Tabela-índice: Nº | Data | Tipo | Projeto/Local | Categoria | Relev. | URL"""
    out: dict[int, dict] = {}
    for line in text.splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        num = int(m.group(1))
        cells = [c.strip() for c in m.group(2).split("|")]
        if len(cells) < 6:
            continue
        date_br, tp, project, category, relev, url = cells[:6]
        if not re.search(r"instagram\.com", url):
            continue
        proj, city, uf = split_place(project)
        out[num] = {
            "date": iso_date(date_br),
            "type_table": tp.strip(),
            "project": proj, "city": city, "state": uf,
            "category": clean(category),
            "portfolio_relevance": clean(relev).upper(),
            "url_table": url.strip(),
        }
    log(f"Linhas da tabela-índice: {len(out)}")
    return out


FICHA_RE = re.compile(r"^###\s+POST\s+(\d{1,3})\s*[—–-]", re.M)


def parse_fichas(text: str) -> dict[int, dict]:
    """Fichas '### POST NNN' com bullets '- **Campo:** valor'."""
    marks = [(int(m.group(1)), m.start()) for m in FICHA_RE.finditer(text)]
    out: dict[int, dict] = {}
    for i, (num, start) in enumerate(marks):
        end = marks[i + 1][1] if i + 1 < len(marks) else len(text)
        block = text[start:end]
        fields: dict[str, str] = {}
        for bm in re.finditer(r"^-\s*\*\*(.+?):?\*\*\s*(.*)$", block, re.M):
            fields[strip_accents(bm.group(1).lower()).strip(" :")] = bm.group(2).strip()

        def f(*keys: str) -> str:
            for k in keys:
                for fk, fv in fields.items():
                    if fk.startswith(k):
                        return clean(fv)
            return ""

        tech = f("dados tecnicos")
        summary = f("legenda (resumo)", "legenda")
        blob = f"{summary} {tech}"
        proj, city, uf = split_place(f("projeto/local citado", "projeto/local", "projeto"))

        out[num] = {
            "summary": summary,
            "caption_tech": tech,
            "category_ficha": f("categoria"),
            "project_ficha": proj, "city_ficha": city, "state_ficha": uf,
            "relev_ficha": f("relevancia portfolio", "relevancia").upper(),
            "power_kwp": x_power(blob),
            "module_count": x_modules(blob),
            "generation": x_generation(blob),
            "economy": x_money(blob, "economia", "economiza", "poupa"),
            "investment": x_money(blob, "investimento", "investir", "aporte"),
            "return_claim": x_return_claim(blob),
            "notes_ficha": f("deep-dive visual", "observacao", "obs"),
        }
    log(f"Fichas de post lidas: {len(out)}")
    return out


def main() -> int:
    for p in (CATALOG, URLS):
        if not p.exists():
            log(f"ERRO: fonte ausente: {p}")
            return 1

    text = CATALOG.read_text(encoding="utf-8")
    urls = parse_urls(URLS)
    table = parse_index_table(text)
    fichas = parse_fichas(text)

    numbers = sorted(set(urls) | set(table) | set(fichas))
    log(f"Posts distintos encontrados: {len(numbers)}")

    rows = []
    for n in numbers:
        u = urls.get(n, {})
        t = table.get(n, {})
        fi = fichas.get(n, {})

        url = u.get("url") or t.get("url_table", "")
        shortcode = u.get("shortcode") or shortcode_from_url(url)
        tp = norm_type(u.get("type_urls") or t.get("type_table", ""))

        # Tipo manda na expectativa de mídia: reel = 1 vídeo; feed = desconhecido
        # (o Instagram só revela o tamanho do carrossel no download).
        expected = "1" if tp == "reel" else ""

        notes = []
        if n not in urls:
            notes.append("sem URL canônica na lista 245")
        if n not in fichas:
            notes.append("sem ficha detalhada no catálogo")
        if t.get("url_table") and u.get("url") and t["url_table"] != u["url"]:
            notes.append("URL divergente entre tabela e lista canônica")

        rc = fi.get("return_claim", "")
        verification = "PENDENTE"
        if rc:
            verification = "NAO_PUBLICAR_SEM_REVISAO"
            notes.append(f"alegação de rentabilidade na fonte: {rc}")

        rows.append({
            "post_number": f"{n:03d}",
            "shortcode": shortcode,
            "date": t.get("date", ""),
            "type": tp,
            "url": url,
            "caption": "",                     # preenchido pelo gallery-dl (metadata)
            "summary": fi.get("summary", ""),
            "category": fi.get("category_ficha") or t.get("category", ""),
            "project": fi.get("project_ficha") or t.get("project", ""),
            "city": fi.get("city_ficha") or t.get("city", ""),
            "state": fi.get("state_ficha") or t.get("state", ""),
            "power_kwp": fi.get("power_kwp", ""),
            "module_count": fi.get("module_count", ""),
            "generation": fi.get("generation", ""),
            "economy": fi.get("economy", ""),
            "investment": fi.get("investment", ""),
            "return_claim": rc,
            "portfolio_relevance": fi.get("relev_ficha") or t.get("portfolio_relevance", ""),
            "portfolio_usage": "",             # preenchido na curadoria
            "media_count_expected": expected,
            "download_status": "PENDENTE",
            "verification_status": verification,
            "notes": "; ".join(notes),
        })

    OUT_POSTS.parent.mkdir(parents=True, exist_ok=True)
    OUT_INDEX.parent.mkdir(parents=True, exist_ok=True)
    with OUT_POSTS.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)

    with OUT_INDEX.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["shortcode", "post_number", "type", "url"])
        for r in rows:
            if r["shortcode"]:
                w.writerow([r["shortcode"], r["post_number"], r["type"], r["url"]])

    # ── resumo ──
    reels = sum(1 for r in rows if r["type"] == "reel")
    feed = sum(1 for r in rows if r["type"] == "carousel_or_image")
    alta = sum(1 for r in rows if r["portfolio_relevance"] == "ALTA")
    tech = sum(1 for r in rows if r["power_kwp"] or r["module_count"])
    flag = sum(1 for r in rows if r["verification_status"] == "NAO_PUBLICAR_SEM_REVISAO")
    dup = len(rows) - len({r["shortcode"] for r in rows if r["shortcode"]})

    log(f"posts_master.csv escrito: {len(rows)} linhas")
    log(f"  reels={reels}  feed={feed}  relevância ALTA={alta}")
    log(f"  com dado técnico={tech}  marcados p/ revisão={flag}  shortcodes duplicados={dup}")
    log(f"  -> {OUT_POSTS}")

    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("\n".join(_log_lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
