#!/usr/bin/env python
"""
build_docs.py — Gera a documentação que deriva dos dados.

Estes arquivos não são escritos à mão: são projeção das tabelas em
data/processed/. Reexecute sempre que os CSVs mudarem.

Saídas : docs/FACT_CHECK.md
         docs/INSTAGRAM_ANALYSIS.md
"""
from __future__ import annotations

import csv
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "data" / "processed" / "posts_master.csv"
CASES = ROOT / "data" / "processed" / "cases_master.csv"
CLAIMS = ROOT / "data" / "processed" / "factual_claims.csv"
IDENT = ROOT / "data" / "processed" / "company_identity.csv"
PDF = ROOT / "output" / "portfolio" / "v2" / "Portfolio_Engvoltaica_V2.pdf"


def read(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def pdf_text() -> str:
    if not PDF.exists():
        return ""
    try:
        import pymupdf
        with pymupdf.open(PDF) as d:
            return "\n".join(p.get_text() for p in d)
    except Exception:
        return ""


def fact_check(claims, cases, ident, texto) -> str:
    L = ["# FACT CHECK — Portfólio Engvoltaica V2", "",
         f"> Gerado por `scripts/build_docs.py` em {datetime.now():%d/%m/%Y %H:%M}.",
         "> Cada dado, sua fonte, seu status e se foi publicado. Coluna *Publicado*",
         "> conferida contra o texto extraído do PDF — não contra intenção.", "",
         "## Identidade da empresa", "",
         "| Dado | Valor | Fonte | Status | Publicado |", "|---|---|---|---|---|"]

    principais = [r for r in ident if "ENGVOLTAICA ENERGIA SOLAR" in (r.get("razao_social") or "").upper()]
    cnpj = principais[0]["cnpj"] if principais else "—"
    docs_n = len([r for r in ident if r.get("encontrado") == "SIM"])
    for dado, valor, fonte, status in (
        ("CNPJ", cnpj, f"{docs_n} documentos oficiais", "CONFIRMADO"),
        ("CNPJ informado inicialmente", "00.000.100/0001-00", "usuária", "INCORRETO"),
        ("Razão social", "ENGVOLTAICA ENERGIA SOLAR LTDA", "cartão CNPJ", "CONFIRMADO"),
        ("Registro CREA-GO", "00000/RF", "Certidão de Registro e Quitação", "CONFIRMADO"),
        ("Responsável técnico", "Engenheiro(a) Responsável", "CRQ do CREA", "CONFIRMADO"),
        ("Abertura", "04/11/2019", "cartão CNPJ", "CONFIRMADO"),
        ("Capital social", "R$ 0,00", "consulta QSA", "CONFIRMADO"),
    ):
        pub = "SIM" if valor and valor in texto else "não"
        if status == "INCORRETO":
            pub = "**VAZOU**" if valor in texto else "não (correto)"
        L.append(f"| {dado} | `{valor}` | {fonte} | {status} | {pub} |")

    L += ["", "## Números comerciais", "",
          "| ID | Escopo | Afirmação | Valor | Fonte | Status | Pode publicar | Publicado |",
          "|---|---|---|---|---|---|---|---|"]
    for c in claims:
        val = c["valor"]
        pub = "SIM" if val and val.replace(" ", "") in texto.replace(" ", "") else "não"
        if c["publicar"] == "NAO":
            pub = "❌ **VAZOU**" if pub == "SIM" else "✅ bloqueado"
        L.append(f"| {c['claim_id']} | {c['escopo']} | {c['afirmacao']} | {val} | "
                 f"{c['fonte_tipo']} · {c['fonte_ref']} | {c['status']} | "
                 f"{c['publicar']} | {pub} |")

    bloq = [c for c in claims if c["publicar"] == "NAO"]
    vazou = [c for c in bloq if c["valor"] and c["valor"].replace(" ", "") in texto.replace(" ", "")]
    L += ["", "## Veredito", "",
          f"- Afirmações catalogadas: **{len(claims)}**",
          f"- Liberadas para publicação: **{sum(1 for c in claims if c['publicar'].startswith('SIM'))}**",
          f"- Bloqueadas: **{len(bloq)}**",
          f"- Bloqueadas que vazaram para o PDF: **{len(vazou)}**"
          + ("  ✅" if not vazou else "  ❌ CORRIGIR"), "",
          "### Percentual de desconto", ""]
    for p in ("20%", "25%", "30%"):
        presente = p in texto
        esperado = (p == "20%")
        marca = "✅" if presente == esperado else "❌"
        L.append(f"- {marca} `{p}` {'presente' if presente else 'ausente'} — "
                 f"{'esperado' if esperado else 'não deve aparecer (histórico)'}")
    L += ["", "### Link quebrado", "",
          ("- ✅ nenhuma referência a `lps.engvoltaica.com.br`" if "lps.engvoltaica" not in texto
           else "- ❌ o PDF referencia a LP que retorna 404"), ""]
    return "\n".join(L)


def instagram_analysis(posts, cases) -> str:
    cat = Counter(p["category"] or "(sem categoria)" for p in posts)
    rel = Counter(p["portfolio_relevance"] or "(sem)" for p in posts)
    tipo = Counter(p["type"] for p in posts)
    anos = Counter((p["date"] or "----")[:4] for p in posts)
    baixados = sum(1 for p in posts if p["download_status"] == "OK")
    com_tec = [p for p in posts if p["power_kwp"] or p["module_count"]]

    L = ["# ANÁLISE DO INSTAGRAM — @engvoltaica", "",
         f"> Gerado por `scripts/build_docs.py` em {datetime.now():%d/%m/%Y %H:%M}.",
         "> Base: `data/processed/posts_master.csv`, derivado da auditoria do navegador.", "",
         "## Panorama", "",
         "| Métrica | Valor |", "|---|---|",
         f"| Posts catalogados | **{len(posts)}** |",
         f"| Reels | {tipo.get('reel', 0)} |",
         f"| Feed (foto/carrossel) | {tipo.get('carousel_or_image', 0)} |",
         f"| Relevância ALTA | **{rel.get('ALTA', 0)}** |",
         f"| Relevância MÉDIA | {rel.get('MÉDIA', 0) + rel.get('MEDIA', 0)} |",
         f"| Relevância BAIXA | {rel.get('BAIXA', 0)} |",
         f"| Com dado técnico na legenda | {len(com_tec)} |",
         f"| Mídias já recuperadas | **{baixados}** de {len(posts)} |", "",
         "## Distribuição por categoria", "",
         "| Categoria | Posts |", "|---|---|"]
    for c, n in cat.most_common():
        L.append(f"| {c} | {n} |")

    L += ["", "## Volume por ano", "", "| Ano | Posts |", "|---|---|"]
    for a in sorted(anos, reverse=True):
        L.append(f"| {a} | {anos[a]} |")

    named = [c for c in cases if c["case_id"].startswith("CASE_")]
    L += ["", "## Projetos identificados", "",
          f"{len(named)} projetos nomeados e "
          f"{len([c for c in cases if c['case_id'].startswith('PLANT_')])} usinas individuais "
          "com dados técnicos publicados.", "",
          "| Case | Nome | Local | Publicável | Verificação |", "|---|---|---|---|---|"]
    for c in named:
        local = f"{c['cidade']}/{c['estado']}".strip("/") or "—"
        L.append(f"| {c['case_id']} | {c['nome_publico'] or '—'} | {local} | "
                 f"`{c['publishability']}` | `{c['verification_status']}` |")

    alta = [p for p in posts if p["portfolio_relevance"] == "ALTA"]
    L += ["", "## Posts de relevância ALTA", "",
          "Prioridade na fila de download e na curadoria.", "",
          "| POST | Data | Tipo | Categoria | URL |", "|---|---|---|---|---|"]
    for p in alta[:30]:
        L.append(f"| {p['post_number']} | {p['date'] or '—'} | {p['type']} | "
                 f"{p['category'][:34]} | {p['url']} |")

    L += ["", "## Observações de método", "",
          "- A numeração POST 001 = mais recente é fixa e vem da auditoria. POSTS 001–003",
          "  são fixados no perfil, por isso as datas fogem da ordem cronológica.",
          "- 64 posts do lote inicial de set/2020 não têm legenda: são fotos avulsas de",
          "  instalação. Valem como imagem, não como case documentado.",
          "- O shortcode é a chave estável. Legenda e capa mudam; o shortcode não.",
          "- Contagem de carrossel só é confiável após o download (`DEC-012`).", ""]
    return "\n".join(L)


def fichas_de_case(cases, claims, posts) -> int:
    """Uma ficha por projeto nomeado, em docs/cases/."""
    dest = ROOT / "docs" / "cases"
    dest.mkdir(parents=True, exist_ok=True)
    por_post = {p["post_number"]: p for p in posts}
    n = 0
    for c in cases:
        if not c["case_id"].startswith("CASE_") or not c["nome_publico"]:
            continue
        slug = (c["nome_publico"].upper()
                .replace(" ", "_").replace("/", "_").replace(",", "")
                .replace("Á", "A").replace("Â", "A").replace("Ã", "A")
                .replace("É", "E").replace("Ê", "E").replace("Í", "I")
                .replace("Ó", "O").replace("Ô", "O").replace("Õ", "O")
                .replace("Ú", "U").replace("Ç", "C"))
        rel = [p for p in c["posts_relacionados"].split("|") if p]
        meus = [cl for cl in claims if cl["escopo"] == c["case_id"]]
        bloq = [cl for cl in meus if cl["publicar"] == "NAO"]
        local = f"{c['cidade']}/{c['estado']}".strip("/") or "Goiás"

        L = [f"# {c['case_id']} — {c['nome_publico']}", "",
             f"> Gerado por `scripts/build_docs.py` em {datetime.now():%d/%m/%Y %H:%M}.",
             "> **Não editar à mão** — reexecute o script.", ""]
        if bloq:
            L += ["> ⛔ **ESTE CASE ESTÁ BLOQUEADO PARA PUBLICAÇÃO.**",
                  "> Contém alegação que exige revisão jurídica (`DEC-007`).", ""]
        L += ["## O que é", "",
              f"- **Tipo:** {c['tipo'] or '—'}",
              f"- **Local:** {local}",
              f"- **Status:** {c['status'] or '—'}",
              f"- **Publicabilidade:** `{c['publishability']}`"
              + ("  ← a Engvoltaica divulgou o nome no Instagram oficial"
                 if c["publishability"] == "PUBLICO_IG" else ""),
              f"- **Verificação:** `{c['verification_status']}`", "",
              "## Números técnicos", ""]
        tem = False
        for rot, val, un in (("Potência", c["potencia_kwp"], " kWp"),
                             ("Módulos", c["modulos"], ""),
                             ("Geração", c["geracao"], ""),
                             ("Economia divulgada", c["economia"], ""),
                             ("Investimento", c["investimento"], "")):
            if val:
                tem = True
                L.append(f"- **{rot}:** {val.replace('.', ',') if un else val}{un}")
        if not tem:
            L.append("Nenhum dado técnico publicado nas legendas deste projeto.")

        L += ["", "## Posts de origem", ""]
        if rel:
            for p in rel:
                info = por_post.get(p, {})
                L.append(f"- **POST {p}** — {info.get('date', 'data n/d')} · "
                         f"{info.get('type', '')} · {info.get('url', '')}")
        else:
            L.append("Nenhum post associado.")

        L += ["", "## Afirmações catalogadas", "",
              "| ID | Afirmação | Valor | Pode publicar | Observação |", "|---|---|---|---|---|"]
        for cl in meus:
            L.append(f"| {cl['claim_id']} | {cl['afirmacao']} | {cl['valor']} | "
                     f"`{cl['publicar']}` | {cl['observacao'] or '—'} |")
        if not meus:
            L.append("| — | nenhuma | — | — | — |")

        L += ["", "## Melhor uso comercial", "", c["notes"] or "Não definido.", "",
              "## Como citar", ""]
        if bloq:
            L.append("**Não citar.** Aguardando liberação jurídica.")
        elif c["economia"]:
            L.append(f"> {c['nome_publico']} — {local}. {c['tipo'] or 'Usina executada pela Engvoltaica'}. "
                     f"Economia de {c['economia']} **divulgada pela empresa** "
                     f"(POST {rel[0] if rel else '—'}).")
            L.append("")
            L.append("Sempre com o enquadramento *\"resultado divulgado pela empresa\"*, "
                     "nunca como média, projeção ou garantia.")
        else:
            L.append(f"> {c['nome_publico']} — {local}. {c['tipo'] or 'Usina executada pela Engvoltaica'}.")
        L.append("")
        (dest / f"{c['case_id']}_{slug}.md").write_text("\n".join(L), encoding="utf-8")
        n += 1
    return n


def main() -> int:
    posts, cases = read(POSTS), read(CASES)
    claims, ident = read(CLAIMS), read(IDENT)
    if not posts:
        sys.exit("ERRO: posts_master.csv vazio. Rode parse_chrome_catalog.py antes.")
    texto = pdf_text()
    if not texto:
        print("AVISO: PDF ausente — coluna 'Publicado' do FACT_CHECK ficará em 'não'.")

    for nome, conteudo in (("FACT_CHECK.md", fact_check(claims, cases, ident, texto)),
                           ("INSTAGRAM_ANALYSIS.md", instagram_analysis(posts, cases))):
        p = ROOT / "docs" / nome
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(conteudo, encoding="utf-8")
        print(f"OK docs/{nome}")

    n = fichas_de_case(cases, claims, posts)
    print(f"OK docs/cases/ — {n} fichas de projeto")
    return 0


if __name__ == "__main__":
    sys.exit(main())
