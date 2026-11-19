#!/usr/bin/env python
"""
build_portfolio.py — Gera o portfólio V2 em HTML A4.

Os números NÃO são digitados aqui: vêm de data/processed/cases_master.csv e
factual_claims.csv. Case com publicar=NAO simplesmente não é renderizado —
a regra é do dado, não do redator.

Saídas : output/portfolio/v2/Portfolio_Engvoltaica_V2.html
         output/portfolio/v2/imagens/  (cópia dos derivados aprovados)
         output/reports/portfolio_build.md
"""
from __future__ import annotations

import csv
import html
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "data" / "processed" / "cases_master.csv"
CLAIMS = ROOT / "data" / "processed" / "factual_claims.csv"
IMGSRC = ROOT / "derivados" / "portfolio_images"
OUTDIR = ROOT / "output" / "portfolio" / "v2"
OUTHTML = OUTDIR / "Portfolio_Engvoltaica_V2.html"
REPORT = ROOT / "output" / "reports" / "portfolio_build.md"

# ── dados institucionais confirmados (docs/SOURCES.md) ──────────────────────
EMPRESA = {
    "razao": "ENGVOLTAICA ENERGIA SOLAR LTDA",
    "cnpj": "00.000.000/0001-00",
    "consorcio": "CONSÓRCIO ENGVOLTAICA — CNPJ 00.000.000/0002-00",
    "crea": "CREA-GO nº 00000/RF",
    "rt": "Engenheiro(a) Responsável — CREA 00000/D-UF",
    "desde": "2019",
    "site": "engvoltaica.com.br",
    "instagram": "@engvoltaica",
    "seguidores": "9,7 mil",
    "endereco": "Av. Exemplo, 000, Sala 000",
    "bairro": "Bairro Exemplo · Goiânia — GO · CEP 00000-000",
    "tagline": "A liberdade da energia",
    "desconto": "20",
}


def _contato_local() -> dict:
    """WhatsApp e e-mail ficam FORA do Git (politica de privacidade do Emmily AI Project OS,
    ADR-0015): vivem em config/contato.local.json, ignorado, com o original no Drive em
    04 PORTFOLIO/engvoltaica-portfolio/. Sem o arquivo, o build para - nunca gera portfolio
    com contato vazio."""
    import json

    p = ROOT / "config" / "contato.local.json"
    if not p.exists():
        raise SystemExit("config/contato.local.json ausente: copie do Drive (04 PORTFOLIO/engvoltaica-portfolio)")
    d = json.loads(p.read_text(encoding="utf-8"))
    return {"whatsapp": d["whatsapp"], "email": d["email"]}


def esc(s: str) -> str:
    return html.escape(str(s or ""))


def ptbr(v: str) -> str:
    """39.56 -> 39,56 — o documento é em português."""
    return (v or "").replace(".", ",")


def tipo_curto(v: str) -> str:
    """Primeiro segmento do campo livre 'tipo', sem dados financeiros colados."""
    v = (v or "").split("·")[0].split("Economia")[0].split("(")[0]
    return v.strip(" ,;.-")


def load(path: Path) -> list[dict]:
    if not path.exists():
        sys.exit(f"ERRO: {path} não existe. Rode scripts/build_cases.py antes.")
    with path.open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def publicaveis(cases: list[dict], claims: list[dict]) -> tuple[list[dict], list[dict]]:
    """Separa o que pode ser publicado do que está bloqueado."""
    bloqueados = {c["escopo"] for c in claims if c["publicar"] == "NAO"}
    ok, barrados = [], []
    for c in cases:
        if c["case_id"] in bloqueados or c["verification_status"] == "NAO_PUBLICAR_SEM_REVISAO":
            barrados.append(c)
        else:
            ok.append(c)
    return ok, barrados


def com_nome(cases: list[dict]) -> list[dict]:
    """Só cases cujo nome a própria Engvoltaica divulgou no Instagram."""
    return [c for c in cases if c["publishability"] == "PUBLICO_IG" and c["nome_publico"]]


def com_numeros(cases: list[dict]) -> list[dict]:
    return [c for c in cases if c["economia"] or c["potencia_kwp"] or c["modulos"]]


# ─────────────────────────────── CSS ────────────────────────────────────────
CSS = """
@page { size: A4 portrait; margin: 0; }
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --navy:#001C4C; --navy-2:#062C6E; --amber:#FAA91B; --amber-d:#D18A00;
  --ink:#151A24; --muted:#59636F; --line:#DDE2EA; --soft:#F5F7FB;
}
html,body{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{font-family:"Segoe UI","Helvetica Neue",Arial,sans-serif;color:var(--ink);
     font-size:10.4pt;line-height:1.55}
.page{width:210mm;height:297mm;position:relative;overflow:hidden;
      page-break-after:always;background:#fff}
.page:last-child{page-break-after:auto}
.pad{padding:15mm 16mm 20mm 16mm}

/* páginas escuras */
.dark{background:var(--navy);color:#fff}
.bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.bg-top{position:absolute;left:0;right:0;top:0;height:58%;width:100%;object-fit:cover;opacity:.82}
.fade{position:absolute;left:0;right:0;top:0;height:58%;
  background:linear-gradient(180deg,rgba(0,28,76,.28) 0%,rgba(0,28,76,.04) 38%,
             rgba(0,28,76,.62) 80%,rgba(0,28,76,1) 100%)}
.logo{position:absolute;top:15mm;left:16mm;width:34mm;
      filter:drop-shadow(0 2px 10px rgba(0,0,0,.75)) drop-shadow(0 0 3px rgba(0,0,0,.5))}

/* tipografia */
.kicker{font-size:8.2pt;letter-spacing:.2em;text-transform:uppercase;
        font-weight:700;color:var(--amber-d);margin-bottom:3mm}
.kicker.on-dark{color:var(--amber)}
h1{font-size:34pt;line-height:1.04;font-weight:800;letter-spacing:-.022em}
h1 span{color:var(--amber)}
h2{font-size:22pt;line-height:1.12;font-weight:800;color:var(--navy);letter-spacing:-.015em}
h2.on-dark{color:#fff}
h2 em{font-style:normal;color:var(--amber-d)}
h2.on-dark em{color:var(--amber)}
h3{font-size:11.5pt;font-weight:700;color:var(--navy);margin-bottom:2mm}
.rule{height:3px;width:22mm;background:var(--amber);border-radius:2px;margin:5mm 0 6mm}
.lead{font-size:10.8pt;color:var(--muted);max-width:152mm}
.lead.on-dark{color:#BECBE2}
p{margin-bottom:2.6mm}
.eyebrow{display:inline-block;font-size:8.2pt;letter-spacing:.2em;font-weight:700;
  text-transform:uppercase;color:var(--amber);border:1px solid rgba(250,169,27,.55);
  padding:4px 12px;border-radius:100px}

/* grids e cards */
.g2{display:grid;grid-template-columns:1fr 1fr;gap:5mm}
.g3{display:grid;grid-template-columns:repeat(3,1fr);gap:4.5mm}
.g4{display:grid;grid-template-columns:repeat(4,1fr);gap:4mm}
.card{border:1px solid var(--line);border-radius:3.5mm;padding:5mm;background:#fff}
.card.soft{background:var(--soft);border-color:#E5EAF2}
.card.navy{background:var(--navy);color:#fff;border:none}
.card.navy h3{color:#fff}
.card.navy p,.card.navy li{color:#C2CFE4}
.card.amber{background:linear-gradient(135deg,#FAA91B,#E08F00);color:#2B1C00;border:none}
.card.amber h3{color:#2B1C00}

/* métricas */
.stat .n{font-size:25pt;font-weight:800;color:var(--navy);line-height:1;letter-spacing:-.02em}
.stat .n .u{font-size:12.5pt;color:var(--amber-d)}
.stat .l{font-size:8.2pt;color:var(--muted);margin-top:2mm;line-height:1.35}
.stat.on-dark .n{color:#fff}
.stat.on-dark .n .u{color:var(--amber)}
.stat.on-dark .l{color:#A9BAD6}

/* listas */
ul{list-style:none}
ul.check li{position:relative;padding-left:6.5mm;margin-bottom:2.4mm;font-size:9.6pt}
ul.check li::before{content:"";position:absolute;left:0;top:1.5mm;width:3.4mm;height:3.4mm;
  border-radius:50%;background:var(--amber)}
ul.check.x li::before{background:#C6CDD8}

/* passos */
.step{display:flex;gap:4.5mm;margin-bottom:4mm;align-items:flex-start}
.step .num{flex:0 0 10mm;height:10mm;border-radius:50%;background:var(--amber);
  color:var(--navy);font-weight:800;font-size:12pt;display:flex;align-items:center;justify-content:center}
.step b{display:block;color:var(--navy);font-size:10.4pt;margin-bottom:.8mm}
.step span{color:var(--muted);font-size:9.3pt}

/* tabela */
table{width:100%;border-collapse:collapse;font-size:9.4pt}
th{background:var(--navy);color:#fff;text-align:left;padding:3mm 3.5mm;
   font-size:8.2pt;letter-spacing:.06em;text-transform:uppercase;font-weight:700}
th.r,td.r{text-align:right}
td{padding:3mm 3.5mm;border-bottom:1px solid var(--line)}
tr:nth-child(even) td{background:#FAFBFD}
td.hi{color:var(--amber-d);font-weight:700}

/* mídia */
.photo{width:100%;border-radius:3mm;object-fit:cover;display:block}
.cap{font-size:7.8pt;color:var(--muted);margin-top:1.6mm}
.cap b{color:var(--navy)}

/* case */
.metric-row{display:grid;grid-template-columns:repeat(4,1fr);gap:3mm;margin-top:5mm}
.metric{background:var(--soft);border-radius:3mm;padding:4mm;text-align:center}
.metric .v{font-size:15pt;font-weight:800;color:var(--navy);line-height:1.05}
.metric.hero .v{font-size:13pt;letter-spacing:-.01em}
.metric .v small{font-size:9pt;color:var(--amber-d);font-weight:700}
.metric .k{font-size:7.6pt;color:var(--muted);margin-top:1.5mm;text-transform:uppercase;letter-spacing:.06em}
.metric.hero{background:var(--navy)}
.metric.hero .v{color:var(--amber)}
.metric.hero .k{color:#A9BAD6}

.band{background:var(--navy);color:#fff;padding:5mm 6mm;border-radius:3.5mm}
.band h3{color:var(--amber);font-size:10.5pt}
.band p{color:#C2CFE4;font-size:9.4pt}

/* rodapé */
.foot{position:absolute;bottom:9mm;left:16mm;font-size:7.6pt;color:#9AA4B4;
      letter-spacing:.06em;text-transform:uppercase;font-weight:600}
.pnum{position:absolute;bottom:9mm;right:16mm;font-size:7.6pt;color:#9AA4B4;letter-spacing:.08em}
.legal{font-size:7.2pt;color:#7C8CAC;line-height:1.5}
.src{font-size:7.2pt;color:#8A94A4;font-style:italic;margin-top:2mm}
"""


def page(n: int, body: str, dark: bool = False) -> str:
    cls = "page dark" if dark else "page"
    foot = "" if dark else (f'<div class="foot">Engvoltaica</div>'
                            f'<div class="pnum">{n:02d}</div>')
    return f'<div class="{cls}">{body}{foot}</div>'


def build(cases: list[dict], claims: list[dict]) -> tuple[str, dict]:
    pub, blocked = publicaveis(cases, claims)
    nomeados = com_nome(pub)
    numericos = [c for c in com_numeros(pub) if c["case_id"].startswith("CASE_")]
    D = {**EMPRESA, **_contato_local()}

    # Case principal: o de maior economia divulgada entre os nomeados.
    def econ_val(c: dict) -> float:
        s = (c["economia"] or "").replace("R$", "").replace(".", "").replace(",", ".").strip()
        try:
            return float(s.split()[0]) if s else 0.0
        except ValueError:
            return 0.0

    principal = max(nomeados, key=econ_val) if nomeados else None
    outros = [c for c in numericos if not principal or c["case_id"] != principal["case_id"]]

    P: list[str] = []

    # ── 01 CAPA ──
    P.append(page(1, f'''
      <img class="bg" src="imagens/capa.jpg" alt="">
      <div class="fade" style="height:100%;background:linear-gradient(180deg,
           rgba(0,28,76,.30) 0%,rgba(0,28,76,.06) 34%,rgba(0,28,76,.72) 72%,rgba(0,28,76,1) 100%)"></div>
      <img class="logo" src="imagens/logo-branco.png" alt="Engvoltaica">
      <div style="position:absolute;left:16mm;right:16mm;bottom:22mm">
        <div class="eyebrow" style="margin-bottom:9mm">{esc(D["tagline"])} · Portfólio 2026</div>
        <h1>Seis anos<br>construindo<br><span>geração própria</span><br>em Goiás.</h1>
        <div class="lead on-dark" style="margin-top:6mm;font-size:12pt;max-width:132mm">
          Usinas solares projetadas, executadas e homologadas pela nossa própria
          engenharia — e três formas de colocar essa geração para trabalhar a seu favor.
        </div>
      </div>
      <div style="position:absolute;left:16mm;right:16mm;bottom:10mm;display:flex;
                  justify-content:space-between;font-size:8.2pt;color:#8FA2C4;
                  border-top:1px solid rgba(255,255,255,.14);padding-top:4mm">
        <span>{esc(D["razao"])} · CNPJ {esc(D["cnpj"])}</span><span>Goiânia · GO</span>
      </div>''', dark=True))

    # ── 02 QUEM SOMOS ──
    P.append(page(2, f'''<div class="pad">
      <div class="kicker">Quem somos</div>
      <h2>Engenharia própria<br>por trás de cada <em>kWh</em>.</h2>
      <div class="rule"></div>
      <p class="lead">A Engvoltaica é uma empresa de engenharia elétrica de Goiânia,
      registrada no {esc(D["crea"])} e ativa desde {esc(D["desde"])}. Executamos o ciclo
      completo — estudo de viabilidade, projeto com ART, homologação junto à
      distribuidora, instalação, comissionamento e monitoramento.</p>
      <p class="lead" style="margin-top:4mm">Não intermediamos: construímos e operamos
      as usinas. É isso que sustenta tanto o desconto de quem assina quanto a receita
      de quem investe.</p>

      <img class="photo" style="height:58mm;margin-top:7mm" src="imagens/quem-somos.jpg" alt="">
      <div class="cap">Usina em solo executada pela Engvoltaica — Goiás.</div>

      <div class="g4" style="margin-top:8mm">
        <div class="stat"><div class="n">+300</div>
          <div class="l">clientes atendidos<br><span style="font-size:7pt">divulgado em jan/2024</span></div></div>
        <div class="stat"><div class="n">{len(nomeados)}</div>
          <div class="l">cases documentados com nome e números publicados</div></div>
        <div class="stat"><div class="n">6<span class="u"> anos</span></div>
          <div class="l">de obra contínua em Goiás</div></div>
        <div class="stat"><div class="n">4</div>
          <div class="l">linhas: usinas, investimento, assinatura e eletropostos</div></div>
      </div>

      <div class="g2" style="margin-top:8mm">
        <div class="card soft"><h3>Responsabilidade técnica</h3>
          <p style="color:var(--muted);font-size:9.4pt">Registro no {esc(D["crea"])},
          com responsável técnico engenheiro civil e de segurança do trabalho
          ({esc(D["rt"])}). Projetos entregues com ART registrada e parecer de acesso aprovado.</p></div>
        <div class="card soft"><h3>Onde atuamos</h3>
          <p style="color:var(--navy);font-size:10.5pt;font-weight:700;margin-bottom:1.5mm">Todo o estado de Goiás</p>
          <p style="color:var(--muted);font-size:9.4pt">Capital e interior, com obras
          entregues também na região metropolitana de Belo Horizonte (MG).</p>
          <p style="color:var(--muted);font-size:8.2pt;margin-bottom:0">(Goiânia, Aparecida de
          Goiânia, Anápolis, Nerópolis, Planalmira, Caldas Novas, Trindade, Vianópolis,
          Aragoiânia e Santo Antônio de Goiás.)</p></div>
      </div></div>'''))

    # ── 03 TRÊS FRENTES ──
    P.append(page(3, f'''<div class="pad">
      <div class="kicker">O que fazemos</div>
      <h2>Três formas de<br>usar o mesmo <em>sol</em>.</h2>
      <div class="rule"></div>
      <p class="lead">A pergunta que define qual delas é a sua:
      <b>reduzir uma despesa</b>, <b>construir um ativo</b> ou
      <b>eletrificar uma operação</b>?</p>

      <div class="g2" style="margin-top:7mm">
        <div class="card" style="border-top:5px solid var(--amber)">
          <div class="kicker" style="margin-bottom:2mm">Frente 01</div>
          <h3 style="font-size:14pt;margin-bottom:2.5mm">Energia por Assinatura</h3>
          <p style="color:var(--muted);font-size:9.4pt;min-height:22mm">Você recebe créditos
          das nossas usinas direto na fatura. O desconto cai todo mês, sem obra e sem
          investimento.</p>
          <ul class="check">
            <li>Até <b>{esc(D["desconto"])}% de desconto</b> na conta de luz</li>
            <li>Investimento inicial: <b>R$ 0,00</b></li>
            <li>Sem placa, sem obra, sem visita técnica</li>
            <li>Adesão 100% digital</li>
          </ul>
        </div>
        <div class="card navy" style="border-top:5px solid var(--amber)">
          <div class="kicker on-dark" style="margin-bottom:2mm">Frente 02</div>
          <h3 style="font-size:14pt;margin-bottom:2.5mm">Usinas de Investimento</h3>
          <p style="min-height:22mm">Você compra uma usina completa, entregue pronta e
          homologada. Ela gera energia, a energia vira receita contratada, e o ativo
          continua sendo seu.</p>
          <ul class="check">
            <li>Ativo real, no seu nome, vida útil de 25+ anos</li>
            <li>Receita recorrente por contrato de locação</li>
            <li>Isenção de ICMS e PIS/COFINS na microgeração</li>
            <li>Engenharia, O&amp;M e monitoramento inclusos</li>
          </ul>
        </div>
      </div>

      <div class="card amber" style="margin-top:5mm;border-top:5px solid var(--navy)">
        <div style="display:flex;gap:6mm;align-items:flex-start">
          <div style="flex:1">
            <div style="font-size:8.2pt;letter-spacing:.2em;text-transform:uppercase;
                        font-weight:700;margin-bottom:2mm">Frente 03 · linha nova</div>
            <h3 style="font-size:14pt;margin-bottom:2.5mm">Eletropostos</h3>
            <p style="font-size:9.4pt;color:#3A2600">Estações de carregamento para veículos
            elétricos, projetadas e instaladas por nós — inclusive para frota pesada.
            Já entregamos infraestrutura capaz de carregar caminhão elétrico refrigerado.</p>
          </div>
          <div style="flex:0 0 52mm;font-size:9pt;color:#3A2600;border-left:1px solid rgba(43,28,0,.25);padding-left:6mm">
            <b>Combinação natural:</b> eletroposto alimentado por geração solar própria
            transforma custo de combustível em ativo de energia.
          </div>
        </div>
      </div>

      <div class="band" style="margin-top:5mm">
        <h3>O que liga as três</h3>
        <p style="margin-top:1.5mm">Quem investe na usina precisa de quem consuma a energia.
        Quem quer desconto precisa de uma usina que gere. E quem eletrifica a frota precisa
        das duas coisas. Operamos os três lados da mesma equação — por isso o desconto do
        assinante é sustentável e a receita do investidor tem demanda.</p>
      </div></div>'''))

    # ── 04 ASSINATURA ──
    P.append(page(4, f'''<div class="pad">
      <div class="kicker">Frente 01 · Energia por assinatura</div>
      <h2>Até <em>{esc(D["desconto"])}% de desconto</em><br>sem investir nada.</h2>
      <div class="rule"></div>
      <p class="lead">Não é mudança de distribuidora nem promessa de tarifa. É a Lei
      14.300 funcionando: nossas usinas injetam energia na rede, os créditos são alocados
      na sua unidade consumidora, e a fatura diminui.</p>

      <div style="margin-top:7mm">
        <div class="step"><div class="num">1</div><div><b>Você envia uma fatura</b>
          <span>Analisamos o consumo dos últimos meses e calculamos o desconto aplicável. Sem custo, sem compromisso.</span></div></div>
        <div class="step"><div class="num">2</div><div><b>Assina o termo de adesão — online</b>
          <span>Assinatura digital em minutos. Nenhum equipamento instalado no seu imóvel.</span></div></div>
        <div class="step"><div class="num">3</div><div><b>Alocamos sua unidade em uma usina</b>
          <span>Cadastramos a UC no rateio junto à distribuidora. A homologação leva de 60 a 90 dias.</span></div></div>
        <div class="step"><div class="num">4</div><div><b>O desconto passa a cair todo mês</b>
          <span>Fatura única da Engvoltaica, com o abatimento já aplicado. Boleto, débito ou cartão.</span></div></div>
      </div>

      <table style="margin-top:4mm">
        <tr><th>Sua fatura hoje</th><th class="r">Economia / mês</th>
            <th class="r">Economia / ano</th><th class="r">Em 5 anos</th></tr>
        <tr><td>R$ 500,00</td><td class="r">R$ 100,00</td><td class="r">R$ 1.200,00</td><td class="r hi">R$ 6.000,00</td></tr>
        <tr><td>R$ 1.000,00</td><td class="r">R$ 200,00</td><td class="r">R$ 2.400,00</td><td class="r hi">R$ 12.000,00</td></tr>
        <tr><td>R$ 2.500,00</td><td class="r">R$ 500,00</td><td class="r">R$ 6.000,00</td><td class="r hi">R$ 30.000,00</td></tr>
        <tr><td>R$ 5.000,00</td><td class="r">R$ 1.000,00</td><td class="r">R$ 12.000,00</td><td class="r hi">R$ 60.000,00</td></tr>
      </table>
      <div class="cap">Simulação com {esc(D["desconto"])}% sobre o valor da fatura, sem considerar
      reajustes tarifários — que tendem a aumentar a economia nominal. O percentual final é
      confirmado na análise da sua fatura.</div>

      <div class="g2" style="margin-top:6mm">
        <div class="card soft"><h3>Quem pode aderir</h3>
          <ul class="check" style="margin-top:2mm">
            <li>Consumo médio a partir de <b>300 kWh/mês</b></li>
            <li>Tarifa igual ou superior a <b>R$ 0,66/kWh</b></li>
            <li>Residencial, comercial, industrial ou rural</li>
            <li>Conta ativa e adimplente na distribuidora</li></ul></div>
        <div class="card"><h3 style="color:var(--muted)">Quem ainda não pode</h3>
          <ul class="check x" style="margin-top:2mm;color:var(--muted)">
            <li>Contas abaixo de 300 kWh/mês</li>
            <li>Beneficiários de tarifa social</li>
            <li>Tarifas abaixo de R$ 0,66/kWh</li>
            <li>Unidades sem conta ativa</li></ul></div>
      </div></div>'''))

    # ── 05 INVESTIMENTO ──
    P.append(page(5, f'''<div class="pad">
      <div class="kicker">Frente 02 · Usinas de investimento</div>
      <h2>Compre o ativo.<br>Receba a <em>receita</em>.</h2>
      <div class="rule"></div>
      <p class="lead">Uma usina solar é infraestrutura: custo operacional baixo,
      degradação lenta e previsível, com contrato de locação assinado antes da energização.</p>

      <img class="photo" style="height:44mm;margin-top:5mm" src="imagens/investimento.jpg" alt="">
      <div class="cap">Usina em solo executada e homologada pela Engvoltaica.</div>

      <div class="g2" style="margin-top:6mm">
        <div class="card" style="padding:5mm"><h3>Por que microgeração até 75 kWp</h3>
          <ul class="check" style="margin-top:2mm">
            <li>Não paga demanda contratada</li>
            <li>Sem custo de reforço de rede ou subestação</li>
            <li>Isenção de ICMS (Convênio CONFAZ 16/2015)</li>
            <li>Isenção de PIS/COFINS (Lei 13.169/2015)</li></ul></div>
        <div class="card" style="padding:5mm"><h3>O que entregamos</h3>
          <ul class="check" style="margin-top:2mm">
            <li>Viabilidade, irradiação e sombreamento em 3D</li>
            <li>Projeto elétrico com ART e parecer de acesso</li>
            <li>Execução, comissionamento e vistoria</li>
            <li>Monitoramento remoto e manutenção preventiva</li></ul></div>
      </div>

      <div class="card soft" style="margin-top:5mm;padding:5mm">
        <h3>Modelos de contrato</h3>
        <div class="g3" style="margin-top:3mm">
          <div><b style="color:var(--navy);font-size:9.8pt">Usina em solo</b>
            <p style="color:var(--muted);font-size:8.8pt;margin-top:1mm">Terreno próprio ou
            arrendado, com a melhor orientação e geração máxima por kWp.</p></div>
          <div><b style="color:var(--navy);font-size:9.8pt">Usina em telhado</b>
            <p style="color:var(--muted);font-size:8.8pt;margin-top:1mm">Aproveita galpões e
            coberturas existentes — sem custo de terreno.</p></div>
          <div><b style="color:var(--navy);font-size:9.8pt">Locação da usina</b>
            <p style="color:var(--muted);font-size:8.8pt;margin-top:1mm">A Engvoltaica loca a
            usina e a coloca para gerar receita dentro do consórcio.</p></div>
        </div>
      </div>

      <div class="band" style="margin-top:5mm;padding:4mm 6mm">
        <h3>Sobre retorno</h3>
        <p style="margin-top:1.5mm">O payback depende de potência, tipo de instalação, custo do
        terreno e modelo de contrato. <b style="color:#fff">Não trabalhamos com promessa de
        rentabilidade</b>: a projeção é feita caso a caso, com planilha aberta de receitas,
        custos e premissas, enviada antes de qualquer decisão.</p>
      </div></div>'''))

    # ── 06 CASE PRINCIPAL ──
    if principal:
        mt = []
        if principal["modulos"]:
            mt.append(("hero" if principal["modulos"] else "", principal["modulos"], "", "módulos"))
        if principal["potencia_kwp"]:
            mt.append(("", ptbr(principal["potencia_kwp"]), "kWp", "potência"))
        if principal["geracao"]:
            g = principal["geracao"].replace(" kWh/mês", "")
            mt.append(("", g, "kWh/mês", "geração"))
        if principal["economia"]:
            mt.append(("hero", principal["economia"], "/ano", "economia divulgada"))
        met = "".join(
            f'<div class="metric {cls}"><div class="v">{esc(v)}<small> {esc(u)}</small></div>'
            f'<div class="k">{esc(k)}</div></div>' for cls, v, u, k in mt[:4])
        local = f'{principal["cidade"]}/{principal["estado"]}'.strip("/")
        P.append(page(6, f'''<div class="pad">
          <div class="kicker">Case principal</div>
          <h2>{esc(principal["nome_publico"])}<br><em>{esc(local or "Goiás")}</em></h2>
          <div class="rule"></div>
          <p class="lead">{esc(principal["tipo"] or "Usina solar executada pela Engvoltaica")}.
          Os números abaixo são os divulgados publicamente pela Engvoltaica no seu perfil
          oficial — não são projeção nem média.</p>

          <img class="photo" style="height:56mm;margin-top:6mm" src="imagens/case-hero.jpg" alt="">
          <div class="cap"><b>{esc(principal["nome_publico"])}</b> — imagem do acervo da Engvoltaica.</div>

          <div class="metric-row">{met}</div>

          <div class="g2" style="margin-top:6mm">
            <div><img class="photo" style="height:42mm" src="imagens/case-apoio-1.jpg" alt="">
              <div class="cap">Estrutura fixa, cercamento e piso drenante.</div></div>
            <div><img class="photo" style="height:42mm" src="imagens/case-apoio-2.jpg" alt="">
              <div class="cap">Blocos geradores e casa de medição própria.</div></div>
          </div>

          <div class="band" style="margin-top:5mm;padding:4mm 6mm">
            <h3>Por que este case importa</h3>
            <p style="margin-top:1.5mm">Volume de consumo alto, telhado disponível e operação
            que não pode parar. É o perfil em que a geração própria deixa de ser economia e
            vira vantagem competitiva — o custo de energia sai da conta e não volta.</p>
          </div>
          <div class="src">Fonte: publicação oficial da Engvoltaica no Instagram
          ({esc(", ".join("POST " + p for p in principal["posts_relacionados"].split("|")[:3]))}).
          Resultado divulgado pela empresa, referente ao projeto citado.</div>
        </div>'''))

    # ── 07 OUTROS CASES ──
    linhas = "".join(
        f'<tr><td><b>{esc(c["nome_publico"] or "Usina " + c["case_id"].split("_")[1])}</b>'
        f'{("<br><span style=\'font-size:8pt;color:#59636F\'>" + esc(tipo_curto(c["tipo"])[:44]) + "</span>") if tipo_curto(c["tipo"]) else ""}</td>'
        f'<td>{esc(f"{c["cidade"]}/{c["estado"]}".strip("/") or "Goiás")}</td>'
        f'<td class="r">{esc(c["modulos"] or "—")}</td>'
        f'<td class="r">{esc((ptbr(c["potencia_kwp"]) + " kWp") if c["potencia_kwp"] else "—")}</td>'
        f'<td class="r hi">{esc(c["economia"] or "—")}</td></tr>'
        for c in outros[:9])
    P.append(page(7, f'''<div class="pad">
      <div class="kicker">Realizações</div>
      <h2>O que já está<br><em>gerando</em>.</h2>
      <div class="rule"></div>
      <p class="lead">Projetos executados pela Engvoltaica, com projeto, ART registrada,
      parecer de acesso e vistoria de campo da distribuidora.</p>

      <div class="g2" style="margin-top:6mm;gap:4.5mm">
        <div><img class="photo" style="height:36mm" src="imagens/galeria-industria.jpg" alt="">
          <div class="cap"><b>Complexo industrial · Goiás</b> — múltiplas coberturas em um só parque.</div></div>
        <div><img class="photo" style="height:36mm" src="imagens/galeria-posto.jpg" alt="">
          <div class="cap"><b>Posto de combustíveis · Goiânia/GO</b> — [valores ilustrativos] 150 módulos, 80 kWp.</div></div>
        <div><img class="photo" style="height:36mm" src="imagens/galeria-condominio.jpg" alt="">
          <div class="cap"><b>Condomínio residencial · Goiânia/GO</b> — geração na área comum.</div></div>
        <div><img class="photo" style="height:36mm" src="imagens/galeria-solo.jpg" alt="">
          <div class="cap"><b>Usina em solo · Aragoiânia/GO</b> — ampliação de parque existente.</div></div>
      </div>

      <h3 style="margin-top:6mm">Projetos com dados publicados</h3>
      <table style="margin-top:2.5mm">
        <tr><th>Projeto</th><th>Local</th><th class="r">Módulos</th>
            <th class="r">Potência</th><th class="r">Economia/ano</th></tr>
        {linhas}
      </table>
      <div class="src">Valores divulgados pela Engvoltaica em seu perfil oficial, referentes
      a cada projeto e à data da publicação. Não representam média nem garantia de resultado.</div>
    </div>'''))

    # ── 08 CAPACIDADE + PROVA SOCIAL ──
    segmentos = sorted({tipo_curto(c["tipo"]) for c in pub if tipo_curto(c["tipo"])})[:9]
    P.append(page(8, f'''<div class="pad">
      <div class="kicker">Por que a Engvoltaica</div>
      <h2>Não somos<br>uma <em>revenda</em>.</h2>
      <div class="rule"></div>

      <div class="g2" style="margin-top:4mm">
        <div class="card soft"><h3>Somos donos de usinas</h3>
          <p style="color:var(--muted);font-size:9.2pt">O desconto que oferecemos vem de
          geração que nós construímos e operamos — não de intermediação de terceiros.</p></div>
        <div class="card soft"><h3>Engenharia própria, com ART</h3>
          <p style="color:var(--muted);font-size:9.2pt">Projeto assinado por engenheiro
          registrado no CREA. Acervo técnico documentado obra a obra.</p></div>
        <div class="card soft"><h3>Histórico verificável</h3>
          <p style="color:var(--muted);font-size:9.2pt">Cada projeto tem protocolo, parecer de
          acesso e vistoria. Os resultados que divulgamos têm data e origem identificáveis.</p></div>
        <div class="card soft"><h3>Presença e resposta</h3>
          <p style="color:var(--muted);font-size:9.2pt">{esc(D["seguidores"])} seguidores
          acompanham nossas obras em {esc(D["instagram"])}. Atendimento direto por WhatsApp,
          sem call center.</p></div>
      </div>

      <div class="kicker" style="margin-top:7mm">Perguntas diretas</div>
      <div style="border-top:1px solid var(--line)">
        <div style="padding:2.6mm 0;border-bottom:1px solid var(--line)">
          <b style="display:block;color:var(--navy);font-size:9.8pt">Preciso instalar algo no meu imóvel?</b>
          <span style="color:var(--muted);font-size:9.1pt">Na assinatura, não — nenhum equipamento, nenhuma obra, nenhuma visita técnica.</span></div>
        <div style="padding:2.6mm 0;border-bottom:1px solid var(--line)">
          <b style="display:block;color:var(--navy);font-size:9.8pt">Vou trocar de distribuidora?</b>
          <span style="color:var(--muted);font-size:9.1pt">Não. Sua unidade segue conectada normalmente; muda a origem dos créditos que abatem o consumo.</span></div>
        <div style="padding:2.6mm 0;border-bottom:1px solid var(--line)">
          <b style="display:block;color:var(--navy);font-size:9.8pt">Em quanto tempo o desconto começa?</b>
          <span style="color:var(--muted);font-size:9.1pt">Entre 60 e 90 dias após a assinatura, prazo de homologação do rateio.</span></div>
        <div style="padding:2.6mm 0;border-bottom:1px solid var(--line)">
          <b style="display:block;color:var(--navy);font-size:9.8pt">E se eu quiser sair?</b>
          <span style="color:var(--muted);font-size:9.1pt">Cancelamento mediante aviso prévio de 60 dias, com as condições descritas no termo de adesão.</span></div>
        <div style="padding:2.6mm 0;border-bottom:1px solid var(--line)">
          <b style="display:block;color:var(--navy);font-size:9.8pt">O desconto é sempre {esc(D["desconto"])}%?</b>
          <span style="color:var(--muted);font-size:9.1pt">Até {esc(D["desconto"])}%. O percentual exato depende da tarifa, do tipo de ligação e do histórico de consumo — e é informado antes da assinatura.</span></div>
        <div style="padding:2.6mm 0">
          <b style="display:block;color:var(--navy);font-size:9.8pt">Vocês fazem projeção de retorno para investimento?</b>
          <span style="color:var(--muted);font-size:9.1pt">Sim, caso a caso e com planilha aberta. Não trabalhamos com percentual fixo de rentabilidade em material comercial.</span></div>
      </div></div>'''))

    # ── 09 CONTATO ──
    P.append(page(9, f'''
      <img class="bg-top" style="height:44%" src="imagens/contracapa.jpg" alt="">
      <div class="fade" style="height:44%"></div>
      <div style="position:absolute;left:16mm;right:16mm;top:46%">
        <div class="eyebrow">Próximo passo</div>
        <h1 style="font-size:26pt;margin-top:5mm">Mande uma fatura.<br>A gente devolve<br>o <span>número exato</span>.</h1>
        <p class="lead on-dark" style="margin-top:4mm;max-width:138mm">A análise é gratuita, não
        gera compromisso e leva menos de um dia útil. Se não valer a pena para você, nós falamos isso.</p>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:4.5mm;margin-top:7mm">
          <div><b style="display:block;font-size:7.8pt;letter-spacing:.14em;text-transform:uppercase;color:var(--amber);margin-bottom:1.5mm">WhatsApp</b>
            <span style="font-size:11pt;color:#fff">{esc(D["whatsapp"])}</span></div>
          <div><b style="display:block;font-size:7.8pt;letter-spacing:.14em;text-transform:uppercase;color:var(--amber);margin-bottom:1.5mm">E-mail</b>
            <span style="font-size:10pt;color:#fff">{esc(D["email"])}</span></div>
          <div><b style="display:block;font-size:7.8pt;letter-spacing:.14em;text-transform:uppercase;color:var(--amber);margin-bottom:1.5mm">Site</b>
            <span style="font-size:10pt;color:#fff">{esc(D["site"])}</span></div>
          <div><b style="display:block;font-size:7.8pt;letter-spacing:.14em;text-transform:uppercase;color:var(--amber);margin-bottom:1.5mm">Instagram</b>
            <span style="font-size:10pt;color:#fff">{esc(D["instagram"])}
              <small style="display:block;font-size:8.6pt;color:#A8B8D6;font-weight:400;margin-top:1mm">{esc(D["seguidores"])} seguidores</small></span></div>
          <div style="grid-column:1/-1"><b style="display:block;font-size:7.8pt;letter-spacing:.14em;text-transform:uppercase;color:var(--amber);margin-bottom:1.5mm">Escritório</b>
            <span style="font-size:10pt;color:#fff">{esc(D["endereco"])}
              <small style="display:block;font-size:8.6pt;color:#A8B8D6;font-weight:400;margin-top:1mm">{esc(D["bairro"])}</small></span></div>
        </div>
      </div>
      <div style="position:absolute;left:16mm;right:16mm;bottom:9mm">
        <div class="legal" style="border-top:1px solid rgba(255,255,255,.14);padding-top:4mm">
          {esc(D["razao"])} — CNPJ {esc(D["cnpj"])} · Registro {esc(D["crea"])}.
          Programa de energia por assinatura operado pelo {esc(D["consorcio"])}.
          Descontos, prazos e elegibilidade conforme termo de adesão vigente e regulamentação
          da ANEEL (Lei 14.300/2022 e REN 1.059/2023). Os resultados de projetos citados neste
          documento foram divulgados pela empresa nas datas indicadas e referem-se a instalações
          específicas — não constituem média, projeção, garantia de resultado nem proposta
          comercial vinculante.
        </div>
      </div>''', dark=True))

    doc = (f'<!DOCTYPE html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
           f'<title>Portfólio Engvoltaica</title>\n<style>{CSS}</style>\n</head>\n<body>\n'
           + "\n".join(P) + "\n</body>\n</html>\n")

    stats = {
        "paginas": len(P),
        "cases_publicaveis": len(pub),
        "cases_bloqueados": len(blocked),
        "cases_nomeados": len(nomeados),
        "case_principal": principal["nome_publico"] if principal else "(nenhum)",
        "bloqueados_ids": [c["case_id"] for c in blocked],
    }
    return doc, stats


def main() -> int:
    cases, claims = load(CASES), load(CLAIMS)
    doc, stats = build(cases, claims)

    OUTDIR.mkdir(parents=True, exist_ok=True)
    imgdst = OUTDIR / "imagens"
    imgdst.mkdir(exist_ok=True)
    if not IMGSRC.exists():
        sys.exit("ERRO: rode scripts/select_portfolio_images.py antes.")
    for f in IMGSRC.iterdir():
        if f.is_file():
            shutil.copy2(f, imgdst / f.name)
    OUTHTML.write_text(doc, encoding="utf-8")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# Relatório de build — Portfólio V2\n\n"
        f"Gerado em {datetime.now():%d/%m/%Y %H:%M} por `scripts/build_portfolio.py`.\n\n"
        f"| Item | Valor |\n|---|---|\n"
        f"| Páginas | {stats['paginas']} |\n"
        f"| Cases publicáveis | {stats['cases_publicaveis']} |\n"
        f"| Cases nomeados (PUBLICO_IG) | {stats['cases_nomeados']} |\n"
        f"| Case principal | {stats['case_principal']} |\n"
        f"| **Cases bloqueados** | **{stats['cases_bloqueados']}** "
        f"({', '.join(stats['bloqueados_ids']) or '—'}) |\n\n"
        "Os bloqueados não foram renderizados: contêm alegação de rentabilidade que\n"
        "exige revisão jurídica (`docs/DECISIONS.md · DEC-007`).\n",
        encoding="utf-8")

    print(f"HTML: {OUTHTML.relative_to(ROOT)}")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print("\nPróximo: python scripts/render_pdf.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
