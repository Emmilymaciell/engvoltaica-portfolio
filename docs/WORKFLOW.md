# WORKFLOW — como operar o projeto

> Receitas prontas para as tarefas que se repetem. Cada bloco pode ser copiado
> e colado. Todos os comandos rodam a partir da raiz do projeto.

O executável do projeto é `.venv\Scripts\python.exe` — use sempre esse, não o
Python global.

---

## Setup inicial (uma vez por máquina)

```bash
cd "C:\caminho\exemplo\Engvoltaica_Portfolio"
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install gallery-dl pillow imagehash pymupdf
.venv\Scripts\gallery-dl.exe --version     # registre a versão em DECISIONS.md
```

---

## Receita 1 — reconstruir a base a partir da auditoria

Rápido, offline, sem efeito colateral. Rode depois de qualquer mudança nos
arquivos de `data/input/chrome_audit/`.

```bash
.venv\Scripts\python.exe scripts\parse_chrome_catalog.py
.venv\Scripts\python.exe scripts\build_cases.py
.venv\Scripts\python.exe scripts\build_docs.py
```

Produz: `posts_master.csv`, `cases_master.csv`, `factual_claims.csv`,
`docs/CASES_MASTER.md`, `docs/FACT_CHECK.md`, `docs/INSTAGRAM_ANALYSIS.md`.

---

## Receita 2 — baixar as mídias do Instagram

> ⚠️ **O navegador precisa estar fechado.** Enquanto o Chrome roda, ele mantém
> um lock exclusivo no banco de cookies e o download falha com
> `Permission denied`. Fechar o Chrome por completo libera o arquivo.
> Nada é copiado: a sessão é lida em memória (`DEC-010`).

```bash
# 1. feche o Chrome (todas as janelas)

# 2. teste com 3 posts antes do lote
.venv\Scripts\python.exe scripts\download_instagram.py --browser chrome --only 054,136,169

# 3. se passou, o lote inteiro — incremental e retomável
.venv\Scripts\python.exe scripts\download_instagram.py --browser chrome

# 4. organize, meça e registre
.venv\Scripts\python.exe scripts\build_media_manifest.py
```

Variações úteis:

```bash
--status        # só relata quanto falta, não baixa nada
--priority      # apenas os posts de relevância ALTA
--limit 25      # teto de posts nesta execução
```

**Se parar sozinho**, o motivo vai para `state/instagram_download.json`:

| Parada | O que fazer |
|---|---|
| `COOKIES_BLOQUEADOS` | O navegador está aberto. Feche e rode de novo |
| `SESSAO_INVALIDA` | Refaça o login do Instagram no navegador |
| `RATE_LIMIT` | Espere algumas horas. Não insista — o archive guarda o progresso |
| `CHECKPOINT` | O Instagram pediu verificação. Resolva no navegador, no braço |

Nunca tente contornar. Rodar de novo depois retoma exatamente de onde parou.

---

## Receita 3 — reindexar o OneDrive

```bash
.venv\Scripts\python.exe scripts\scan_onedrive.py --no-hash
```

Leva cerca de 1 minuto para ~44 mil arquivos. Só leitura (`DEC-002`).

> **Por que `--no-hash`:** calcular SHA-256 obriga a ler o conteúdo, e a maior
> parte do OneDrive é placeholder do Files On-Demand. Ler dispara download da
> nuvem e a varredura passa de 1 minuto para horas. O script já pula
> automaticamente arquivos não hidratados na hora de medir dimensão.
> Use `--no-dims` para evitar qualquer acesso a conteúdo.

Para hashear de verdade (só quando precisar de prova de integridade), rode sem
a flag e espere.

---

## Receita 4 — regenerar o portfólio

```bash
.venv\Scripts\python.exe scripts\copy_onedrive_originals.py   # só se as fotos mudarem
.venv\Scripts\python.exe scripts\select_portfolio_images.py
.venv\Scripts\python.exe scripts\build_portfolio.py
.venv\Scripts\python.exe scripts\render_pdf.py
.venv\Scripts\python.exe scripts\qa_portfolio.py
```

O QA devolve código 1 se houver erro — dá para encadear com `&&` num script de
release.

### Trocar uma foto
Edite a tabela `SELECTION` em `scripts/select_portfolio_images.py`: slug,
arquivo de origem, recorte em fração `(esq, topo, dir, base)`, legenda e uso.
Depois rode a Receita 4. O original nunca é alterado.

### Mudar um texto
`scripts/build_portfolio.py`. Os **números** não ficam lá — vêm dos CSVs. Se um
número está errado no PDF, corrija o CSV, não o HTML.

### Bloquear um dado
Em `data/processed/factual_claims.csv`, ponha `publicar = NAO` na linha. O case
inteiro deixa de ser renderizado na próxima execução.

---

## Receita 5 — atualizar o pacote do Claude Design

```bash
.venv\Scripts\python.exe scripts\build_design_package.py
```

Copia os assets aprovados e regenera o `ASSET_MAP.md` a partir do manifesto —
o mapa nunca fica dessincronizado da pasta.

---

## Receita 6 — ciclo completo após novos posts

```bash
# 1. acrescente as URLs novas em data/input/chrome_audit/ENGVOLTAICA_URLS_245.txt
# 2. feche o Chrome
.venv\Scripts\python.exe scripts\parse_chrome_catalog.py
.venv\Scripts\python.exe scripts\download_instagram.py --browser chrome
.venv\Scripts\python.exe scripts\build_media_manifest.py
.venv\Scripts\python.exe scripts\build_cases.py
.venv\Scripts\python.exe scripts\build_docs.py
.venv\Scripts\python.exe scripts\select_portfolio_images.py
.venv\Scripts\python.exe scripts\build_portfolio.py
.venv\Scripts\python.exe scripts\render_pdf.py
.venv\Scripts\python.exe scripts\qa_portfolio.py
```

Nenhuma etapa recomeça do zero: só o que é novo é processado.

---

## Receita 7 — rodar os testes

```bash
.venv\Scripts\python.exe -m pytest tests -q
```

Cobrem parsing, nomenclatura, integridade dos manifestos e as regras de
publicabilidade.

---

## Solução de problemas

| Sintoma | Causa provável | Solução |
|---|---|---|
| `Unsupported URL '\ufeffhttps://…'` | BOM no arquivo de URLs | Gravar em UTF-8 sem BOM. Os scripts já fazem isso |
| `Permission denied: …\Cookies` | Navegador aberto | Feche o Chrome por completo |
| `Failed to decrypt cookie (DPAPI)` | Perfil de navegador sem sessão válida | Use o navegador onde você realmente está logada |
| Varredura do OneDrive não termina | Hidratação de arquivos na nuvem | Use `--no-hash` (e `--no-dims` se persistir) |
| PDF não é gerado | Edge não encontrado | Confira os caminhos em `scripts/render_pdf.py` |
| PDF acima de 8 MB | Imagens grandes demais | Reduza `MAX_PX`/`QUALITY` em `select_portfolio_images.py` |
| QA acusa dado bloqueado no PDF | Texto escrito à mão no HTML | Remova do HTML; dado bloqueado não se digita |

---

## O que nunca fazer

- Editar, mover ou renomear qualquer coisa no OneDrive corporativo
- Alterar arquivo dentro de `data/raw/`
- Salvar, copiar ou commitar cookies
- Publicar número sem linha em `factual_claims.csv`
- `git commit` sem autorização explícita da usuária
- Contornar rate limit, checkpoint ou challenge do Instagram
