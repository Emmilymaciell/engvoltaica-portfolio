# CLAUDE.md — Manual operacional do projeto Engvoltaica_Portfolio

> Manual permanente do Claude Code para este repositório.
> **Leia este arquivo e `STATE.md` antes de qualquer ação.** Juntos eles
> reconstroem o contexto completo sem depender de nenhuma conversa anterior.

---

## 1. O que é este projeto

Repositório de conhecimento comercial da **ENGVOLTAICA ENERGIA SOLAR LTDA**
(Goiânia/GO). Reúne, de forma rastreável:

- o acervo de mídias do Instagram oficial (@engvoltaica, 245 posts);
- os cases/usinas reais executados;
- o material relevante do OneDrive corporativo;
- uma base única de fatos com fonte para cada afirmação;
- o portfólio comercial (V2) pronto para envio a clientes;
- o briefing e os assets para o Claude Design produzir uma versão alternativa.

O projeto existe porque a empresa tem provas de execução espalhadas em três
lugares que nunca conversaram entre si — Instagram, OneDrive e site — e
material comercial com números divergentes entre si.

**Raiz:** `C:\caminho\exemplo\Engvoltaica_Portfolio\`
Projeto **independente**, no mesmo nível de `PROG_Cerebro_Documental` e
`PROG_Dashboard`. Nunca aninhar dentro de outro repositório.

---

## 2. Regras permanentes — não negociáveis

### 2.1 Fontes externas são READ-ONLY

O OneDrive corporativo (`C:\caminho\exemplo\PastaCorporativa\OneDrive`)
contém os arquivos originais da empresa. **Nunca** mover, renomear, apagar,
reorganizar, editar ou sobrescrever nada lá. Permitido apenas: ler, extrair
metadados, calcular hash e **copiar** para dentro deste workspace.

O mesmo vale para `C:\caminho\exemplo\Desktop\Portfolio Engvoltaica\`
(baseline V1): é fonte histórica, não destino.

### 2.2 RAW é imutável

`data/raw/` nunca é editado depois de gravado. Não recortar, redimensionar,
converter ou sobrescrever. Toda transformação produz arquivo novo em
`derivados/`. Se um derivado ficou errado, apaga-se o derivado e regenera-se —
o RAW permanece.

### 2.3 Nunca inventar número

Potência, quantidade de projetos, clientes, economia, retorno, módulos,
localização, tempo de atuação, MW instalados: **se não houver fonte, não
publica.** Toda afirmação comercial relevante entra em
`data/processed/factual_claims.csv` com origem e status.

### 2.4 Outra IA não é fonte

O fato de um Claude anterior ter escrito algo não transforma aquilo em fato.
A origem real é o post, o documento, o site ou o arquivo. A auditoria em
`data/input/chrome_audit/` é **dado de entrada**, não verdade estabelecida.

### 2.5 Alegação financeira sensível não sai sem revisão

Qualquer promessa de rentabilidade (ex.: `>4% a.m.`) fica marcada
`NAO_PUBLICAR_SEM_REVISAO` e **não entra no portfólio** até a usuária
confirmar com o jurídico/comercial. Resultados históricos podem aparecer,
mas sempre com o enquadramento *"resultado divulgado pela empresa em [data]"* —
nunca como média, projeção ou garantia.

### 2.6 Nome de cliente não se publica por conta própria

Classificação em `cases_master.csv` → coluna `publishability`:

| Valor | Significado |
|---|---|
| `PUBLICO_IG` | A própria Engvoltaica divulgou o nome no Instagram oficial — pode publicar |
| `GENERICO_SEM_NOME` | Não há nome de cliente envolvido |
| `INTERNO` | Nome só existe em arquivo técnico — **não publicar** sem autorização |

### 2.7 Segurança de sessão

A sessão do Instagram vem do navegador via `--cookies-from-browser`, **em
memória**. Nunca: exibir, imprimir em log, salvar, copiar, commitar ou enviar
cookies para qualquer lugar. Nunca pedir a senha da usuária. Nunca tentar
contornar rate limit, checkpoint ou challenge do Instagram — ao detectar,
parar de forma segura e registrar onde parou.

### 2.8 Git — sem commit automático

Versionar sim; commitar **só com autorização explícita** da usuária.
Proibido sem pedido expresso: `git reset --hard`, `git clean -fd`,
`git checkout --`, `push --force`, rebase destrutivo, reescrita de histórico.

### 2.9 Código primeiro

Trabalho mecânico (parsing, download, hash, dimensão, renomeação, manifesto,
contact sheet, render) vive em `scripts/` e roda em Python. Modelo/visão só
onde código não resolve bem: curadoria estética, redação comercial,
julgamento de publicabilidade. Atualizar o portfólio não pode custar milhares
de tokens.

### 2.10 Cada coisa no seu lugar

| Conteúdo | Destino |
|---|---|
| Código | `scripts/` |
| Dados de entrada | `data/input/` |
| Mídia bruta | `data/raw/` (imutável) |
| Tabelas derivadas | `data/processed/` |
| Índices e hashes | `data/indexes/` |
| Imagens/frames tratados | `derivados/` |
| Conhecimento durável | `docs/` |
| Entregáveis | `output/` |
| Logs | `logs/` |
| Estado de máquina | `state/` · estado humano: `STATE.md` |
| Temporários descartáveis | `tmp/` |

Nada importante pode existir **apenas** em `tmp/`. Não espalhar arquivos pelo
Desktop, Downloads ou raiz do usuário.

---

## 3. Fontes do projeto

| Fonte | Caminho / URL | Regime |
|---|---|---|
| OneDrive corporativo | `C:\caminho\exemplo\PastaCorporativa\OneDrive` | READ-ONLY |
| Baseline V1 | `C:\caminho\exemplo\Desktop\Portfolio Engvoltaica\` | READ-ONLY |
| Auditoria do Chrome | `data/input/chrome_audit/` | entrada imutável |
| Instagram oficial | https://www.instagram.com/engvoltaica | via gallery-dl |
| Site institucional | https://engvoltaica.com.br/ | leitura |
| Landing de assinatura | https://lp.engvoltaica.com.br/ | leitura |
| LP de investimento | `lps.engvoltaica.com.br/usinas-de-investimento-lp1/` | **404 — quebrado** |

---

## 4. Pipeline

```
scripts/parse_chrome_catalog.py     auditoria .md  → posts_master.csv
scripts/build_cases.py              auditoria .md  → cases_master.csv + factual_claims.csv
scripts/download_instagram.py       Instagram      → data/raw/instagram/_staging/
scripts/build_media_manifest.py     staging        → raw organizado + media_manifest.csv
scripts/scan_onedrive.py            OneDrive       → onedrive_index.csv + onedrive_photos.csv
scripts/select_portfolio_images.py  índices        → derivados/portfolio_images/
scripts/build_portfolio.py          conteúdo+fotos → output/portfolio/v2/*.html
scripts/render_pdf.py               HTML           → PDF A4
scripts/qa_portfolio.py             PDF            → output/reports/qa_*.md
```

Detalhes em `docs/WORKFLOW.md`. Arquitetura em `docs/ARCHITECTURE.md`.

### Comandos

```bash
# ambiente (uma vez)
python -m venv .venv
.venv\Scripts\python.exe -m pip install gallery-dl pillow imagehash pymupdf

# base estruturada (rápido, sem rede)
.venv\Scripts\python.exe scripts\parse_chrome_catalog.py
.venv\Scripts\python.exe scripts\build_cases.py

# Instagram — exige o navegador FECHADO (libera o banco de cookies)
.venv\Scripts\python.exe scripts\download_instagram.py --browser chrome --limit 3   # teste
.venv\Scripts\python.exe scripts\download_instagram.py --browser chrome             # lote
.venv\Scripts\python.exe scripts\build_media_manifest.py

# OneDrive
.venv\Scripts\python.exe scripts\scan_onedrive.py --no-hash

# portfólio
.venv\Scripts\python.exe scripts\build_portfolio.py
.venv\Scripts\python.exe scripts\render_pdf.py
.venv\Scripts\python.exe scripts\qa_portfolio.py
```

`download_instagram.py` é incremental e idempotente: o archive SQLite em
`state/` guarda o que já veio, então reexecutar pega só o que falta. Seguro
para interromper a qualquer momento.

---

## 5. Decisões comerciais vigentes

| Tema | Decisão | Origem |
|---|---|---|
| **CNPJ** | `00.000.000/0001-00` (fictício) | Confirmado em 4 documentos oficiais — `docs/evidence/` |
| **Desconto da assinatura** | **até 20%** | Site atual + bio do Instagram. 25% e 30% são históricos: não usar |
| **Rentabilidade `>4% a.m.`** | **bloqueado** | Precisa de revisão jurídica antes de qualquer uso |
| **Nome de cliente** | só `PUBLICO_IG` | Demais exigem autorização |
| **LP de investimento** | não linkar | Retorna 404 |

Divergências completas em `docs/DATA_QUALITY.md`. Fontes em `docs/SOURCES.md`.

---

## 6. Onde ficam os entregáveis

```
output/portfolio/v1_baseline/   portfólio anterior, preservado como referência
output/portfolio/v2/            Portfolio_Engvoltaica_V2.pdf + .html
output/claude_design/           briefing + ASSET_MAP.md + assets/
output/reports/                 QA e relatórios de execução
```

---

## 7. Como retomar em uma sessão nova

1. Ler este arquivo.
2. Ler `STATE.md` — fase atual e próxima tarefa.
3. `git status` para ver o que está sem commit.
4. Conferir `state/*.json` para o estado de máquina dos pipelines.
5. Continuar pela "Próxima tarefa" do `STATE.md`.

Nunca é preciso recuperar conversa antiga. Se alguma informação só existe no
histórico de chat, ela está no lugar errado — mova para `docs/`.
