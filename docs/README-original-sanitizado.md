# Engvoltaica_Portfolio

Repositório de conhecimento comercial da **ENGVOLTAICA ENERGIA SOLAR LTDA**
(CNPJ 00.000.000/0001-00 (fictício) · Goiânia/GO) e da linha de produção do portfólio
enviado a clientes.

---

## Por que existe

A empresa tem seis anos de obra executada, mas a prova disso está espalhada em
três lugares que nunca conversaram: **o Instagram** (245 posts, 9.741
seguidores), **o OneDrive corporativo** (~29 mil arquivos) e **o site**. Além
de espalhada, é contraditória — o mesmo desconto aparece como 20%, 25% e 30%
conforme o material; o CNPJ circulava com um dígito errado; o link da bio do
Instagram está quebrado há meses.

O trabalho anterior produziu um PDF bom, mas dentro de uma pasta solta, sem
rastro de como cada número foi obtido. Aqui o PDF é a **saída** de um pipeline
onde toda afirmação tem fonte, todo arquivo tem hash, e atualizar não custa
milhares de tokens.

---

## O que tem aqui

| Entrega | Onde |
|---|---|
| Portfólio comercial V2 (PDF + fonte editável) | `output/portfolio/v2/` |
| Portfólio V1, preservado | `output/portfolio/v1_baseline/` |
| Briefing + assets para o Claude Design | `output/claude_design/` |
| Base dos 245 posts do Instagram | `data/processed/posts_master.csv` |
| Cases/usinas consolidados | `data/processed/cases_master.csv` · `docs/CASES_MASTER.md` |
| Cada número comercial, com fonte e status | `data/processed/factual_claims.csv` |
| Divergências encontradas | `docs/DATA_QUALITY.md` |
| Mapa de fontes | `docs/SOURCES.md` |

---

## Arquitetura

```
Engvoltaica_Portfolio/
├── .claude/         instruções e comandos do Claude Code para este projeto
├── config/          configuração dos pipelines (sem segredo algum)
├── data/
│   ├── input/       fontes recebidas (auditoria do Chrome, baseline V1)
│   ├── raw/         mídia bruta — IMUTÁVEL
│   ├── processed/   tabelas derivadas (posts, mídias, cases, claims)
│   └── indexes/     índices, hashes, duplicatas
├── derivados/       recortes, thumbnails, frames, otimizados para PDF
├── docs/            conhecimento durável do projeto
├── examples/        amostras para teste do pipeline
├── logs/            logs de execução
├── output/          entregáveis
├── scripts/         todo o trabalho mecânico
├── state/           estado de máquina dos pipelines
├── tests/           testes de parsing, naming, manifesto, integridade
└── tmp/             descartável
```

Fluxo detalhado em [`docs/ARCHITECTURE.md`](ARCHITECTURE.md).
Regras operacionais em [`CLAUDE.md`](../CLAUDE.md).
Estado atual em [`STATE.md`](../STATE.md).

---

## Como executar

### Preparar o ambiente (uma vez)

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install gallery-dl pillow imagehash pymupdf
```

### Base estruturada — rápido, sem rede

```bash
.venv\Scripts\python.exe scripts\parse_chrome_catalog.py
.venv\Scripts\python.exe scripts\build_cases.py
.venv\Scripts\python.exe scripts\verify_company_data.py
```

### Instagram — **exige o navegador fechado**

O gallery-dl lê a sessão do navegador para autenticar. Enquanto o Chrome
estiver aberto ele mantém o banco de cookies travado e o download falha com
`Permission denied`. Feche o Chrome por completo, rode, reabra.

```bash
.venv\Scripts\python.exe scripts\download_instagram.py --browser chrome --limit 3
.venv\Scripts\python.exe scripts\download_instagram.py --browser chrome
.venv\Scripts\python.exe scripts\build_media_manifest.py
```

Incremental e retomável: o que já baixou não baixa de novo, e interromper no
meio não corrompe nada.

### OneDrive

```bash
.venv\Scripts\python.exe scripts\scan_onedrive.py --no-hash
```

### Portfólio

```bash
.venv\Scripts\python.exe scripts\build_portfolio.py
.venv\Scripts\python.exe scripts\render_pdf.py
.venv\Scripts\python.exe scripts\qa_portfolio.py
```

---

## Dependências

- Python 3.12
- `gallery-dl` 1.32.12 · `pillow` · `imagehash` · `pymupdf`
- Microsoft Edge (headless) para renderizar o PDF — já vem no Windows
- `ffprobe` (opcional) para metadados de vídeo; sem ele há um fallback que lê
  a duração direto do header MP4

---

## Regras que não se quebram

1. **OneDrive e baseline V1 são read-only.** Só leitura e cópia.
2. **`data/raw/` é imutável.** Transformação só em `derivados/`.
3. **Nenhum número sem fonte.** Se não está em `factual_claims.csv` com
   `publicar=SIM`, não vai ao portfólio.
4. **Outra IA não é fonte.** A origem é o post, o documento, o site.
5. **Cookies nunca tocam o disco.** Sessão lida do navegador, em memória.
6. **Sem commit automático.** Versionar sim, commitar só quando autorizado.

Detalhamento e motivo de cada uma em [`docs/DECISIONS.md`](DECISIONS.md).

---

## Status

Ver [`STATE.md`](../STATE.md) — fase atual, o que está pronto, o que falta e qual
é a próxima tarefa.
