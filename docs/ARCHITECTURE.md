# ARQUITETURA — Engvoltaica_Portfolio

> Como o dado entra, o que acontece com ele e onde sai. Caminhos reais, para
> eliminar ambiguidade em sessões futuras.

---

## 1. Fluxo geral

```
┌──────────────────────── FONTES (externas, READ-ONLY) ─────────────────────────┐
│                                                                               │
│  Instagram          OneDrive corporativo        Sites            Baseline V1  │
│  @engvoltaica       PastaCorporativa\      engvoltaica      Desktop\     │
│  245 posts          OneDrive (~29 mil arq.)     .com.br          Portfolio    │
│                                                 lp.  / lps.      Engvoltaica\ │
└───────┬───────────────────┬──────────────────────┬──────────────────┬─────────┘
        │                   │                      │                  │
        ▼                   ▼                      ▼                  ▼
┌───────────────────────────── INGESTÃO ────────────────────────────────────────┐
│  download_instagram.py    scan_onedrive.py     (WebFetch)     cópia manual     │
│  gallery-dl + sessão      os.walk filtrado     leitura        preservando V1   │
│  do navegador             por termo/extensão                                  │
└───────┬───────────────────┬──────────────────────┬──────────────────┬─────────┘
        │                   │                      │                  │
        ▼                   ▼                      ▼                  ▼
┌──────────────────────── RAW / INPUT (imutável) ───────────────────────────────┐
│  data/raw/instagram/          data/indexes/          data/input/              │
│    images/  videos/           onedrive_index.csv       chrome_audit/          │
│    metadata/                  onedrive_photos.csv      previous_portfolio/    │
│  data/raw/onedrive_selected/                                                  │
└───────────────────────────────────┬───────────────────────────────────────────┘
                                    ▼
┌──────────────────────────── PROCESSAMENTO ────────────────────────────────────┐
│  parse_chrome_catalog.py  → estrutura os 245 posts                            │
│  build_media_manifest.py  → organiza, mede, hasheia, detecta duplicata        │
│  build_cases.py           → agrupa posts por projeto real                     │
│  verify_company_data.py   → confere CNPJ/CREA na fonte primária               │
│  match_instagram_onedrive.py → liga mídia do IG ao original em alta           │
└───────────────────────────────────┬───────────────────────────────────────────┘
                                    ▼
┌──────────────────────── BASE ESTRUTURADA (data/processed/) ───────────────────┐
│  posts_master.csv      245 posts · categoria · relevância · dados técnicos     │
│  media_manifest.csv    cada arquivo · dimensão · duração · sha256             │
│  cases_master.csv      projetos reais deduplicados · publicabilidade          │
│  factual_claims.csv    cada número comercial · fonte · pode publicar?         │
│  company_identity.csv  CNPJ/razão social conferidos em documento oficial      │
└───────────────────────────────────┬───────────────────────────────────────────┘
                                    ▼
┌──────────────────────────── CURADORIA ────────────────────────────────────────┐
│  select_portfolio_images.py  → ranqueia por resolução, proporção, case        │
│  generate_contact_sheets.py  → folhas de contato para decisão humana          │
│  optimize_images.py          → derivados otimizados (RAW intacto)             │
│                                                                               │
│  Aqui entra julgamento humano/modelo: estética, narrativa, publicabilidade.   │
└───────────────────────────────────┬───────────────────────────────────────────┘
                                    ▼
┌──────────────────────────── PORTFÓLIO ────────────────────────────────────────┐
│  build_portfolio.py  → HTML A4 a partir do conteúdo + imagens aprovadas       │
│  render_pdf.py       → Edge headless → PDF                                    │
└───────────────────────────────────┬───────────────────────────────────────────┘
                                    ▼
┌───────────────────────────────── QA ──────────────────────────────────────────┐
│  qa_portfolio.py  → páginas, peso, texto cortado, resolução, CNPJ, %, links   │
│  docs/FACT_CHECK.md → cada dado publicado x fonte x status                    │
└───────────────────────────────────┬───────────────────────────────────────────┘
                                    ▼
┌──────────────────────────────── OUTPUT ───────────────────────────────────────┐
│  output/portfolio/v2/Portfolio_Engvoltaica_V2.pdf   ← entregável ao cliente    │
│  output/portfolio/v2/Portfolio_Engvoltaica_V2.html  ← fonte editável          │
│  output/claude_design/BRIEFING_..._V2.md + ASSET_MAP.md + assets/             │
│  output/reports/                                                              │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Princípios que sustentam a arquitetura

### Camada imutável separada da camada derivada
`data/raw/` e `data/input/` nunca mudam depois de gravados. Tudo que é
transformação vive em `derivados/` ou `data/processed/`. Consequência prática:
dá para apagar `derivados/` inteiro e regenerar sem perder nada.

### O shortcode é a chave estável
O Instagram muda legenda, capa e ordem — mas o shortcode de
`/p/<SHORTCODE>/` não muda. Ele é a chave primária que liga post → mídia →
case. Nomes de arquivo carregam sempre `POST_###_<SHORTCODE>_##`.

### Tudo que é mecânico é script
Baixar, medir, hashear, renomear, conferir carrossel, gerar folha de contato,
renderizar: nenhuma dessas tarefas precisa de modelo. Isso mantém o custo de
atualização perto de zero.

### Todo número publicado tem linha em `factual_claims.csv`
Se um número aparece no portfólio e não tem linha lá com fonte e
`publicar=SIM`, é bug — não licença poética.

### Idempotência
Todo script pode rodar de novo sem estragar o que já existe. O download usa
archive SQLite; o parser reconstrói do zero a partir da fonte; o manifesto
recalcula. Interromper no meio nunca corrompe estado.

---

## 3. Atualização incremental

Quando a Engvoltaica publicar posts novos:

```
1. Atualizar ENGVOLTAICA_URLS_245.txt (ou acrescentar as novas URLs)
2. python scripts/parse_chrome_catalog.py      # reconstrói posts_master
3. python scripts/download_instagram.py        # baixa SÓ o que falta
4. python scripts/build_media_manifest.py      # mede e registra o novo
5. python scripts/build_cases.py               # reagrupa por projeto
6. python scripts/build_portfolio.py && render_pdf.py && qa_portfolio.py
```

Nenhuma etapa recomeça do zero, e nenhuma depende de conversa anterior.
