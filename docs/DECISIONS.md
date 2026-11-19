# DECISÕES — Engvoltaica_Portfolio

> Registro de decisões de arquitetura e de conteúdo, com o motivo. Uma sessão
> futura que discordar de algo aqui deve **acrescentar uma decisão nova que
> supera a anterior**, nunca reescrever o histórico.

Formato: `DEC-NNN · data · status · decisão · motivo`

---

## DEC-001 — Repositório próprio e independente
**17/09/2026 · VIGENTE**

O projeto vive em `C:\caminho\exemplo\Engvoltaica_Portfolio\`, no mesmo
nível de `PROG_Cerebro_Documental` e `PROG_Dashboard`.

**Motivo:** o trabalho anterior produziu só um PDF numa pasta do Desktop, o que
tornou tudo dependente do histórico da conversa. Um repositório com estado,
documentação e scripts permite retomar em qualquer sessão. Independente porque
o domínio não tem relação com os projetos Programa — aninhar criaria repositório
dentro de repositório e misturaria contextos.

---

## DEC-002 — OneDrive corporativo é READ-ONLY
**17/09/2026 · VIGENTE**

Nada em `C:\caminho\exemplo\PastaCorporativa\OneDrive` é movido,
renomeado, apagado ou editado. Só leitura, metadados, hash e cópia para o
workspace.

**Motivo:** é o acervo operacional vivo da empresa, sincronizado, com contratos
e documentos fiscais. Qualquer alteração se propaga para todos os dispositivos
e pode quebrar processos de terceiros. O custo de um erro é alto e
irreversível; o benefício de "organizar" é zero para este projeto.

---

## DEC-003 — RAW é imutável
**17/09/2026 · VIGENTE**

`data/raw/` nunca é alterado depois de gravado. Recorte, redimensionamento e
conversão produzem arquivo novo em `derivados/`.

**Motivo:** baixar de novo custa tempo, rede e risco de rate limit do
Instagram. E um recorte ruim feito sobre o original é perda definitiva. Com
RAW intacto, dá para apagar `derivados/` inteiro e regenerar.

---

## DEC-004 — Desconto comercial vigente: até 20%
**17/09/2026 · VIGENTE**

O portfólio comunica **até 20%**. Materiais com 25% ou 30% são históricos e
não devem ser usados como promessa atual.

**Motivo:** três fontes divergem (site 20% · LP antiga 25% · PPT do OneDrive
30%). O site institucional e a bio do Instagram — as fontes públicas vigentes —
dizem 20%, e a empresa confirmou 20% como padrão atual. Prometer mais do que se
entrega gera reclamação e risco de publicidade enganosa. Ver
`docs/DATA_QUALITY.md · QD-002`.

---

## DEC-005 — CNPJ: 00.000.000/0001-00 (fictício)
**17/09/2026 · VIGENTE**

A empresa principal é **ENGVOLTAICA ENERGIA SOLAR LTDA — 00.000.000/0001-00**.
O valor informado inicialmente (`00.000.100/0001-00`, com `100`) está errado.

**Motivo:** confirmado em 4 documentos oficiais independentes — dois cartões
CNPJ, a consulta de QSA e a Certidão de Registro e Quitação do CREA-GO.
Evidência em `docs/evidence/company_identity_evidence.txt`, verificável por
`scripts/verify_company_data.py`.

---

## DEC-006 — Nome de cliente só se a Engvoltaica já publicou
**17/09/2026 · VIGENTE**

Um case só vai ao portfólio com nome se a própria Engvoltaica divulgou esse
nome no Instagram oficial (`publishability = PUBLICO_IG`). Nome que existe
apenas em contrato ou projeto técnico do OneDrive fica `INTERNO` e não é
publicado sem autorização expressa.

**Motivo:** publicar cliente sem autorização é problema contratual e de
imagem. Já o que a empresa publicou no próprio perfil é, na prática,
autorizado. Isso dá uma regra objetiva em vez de julgamento caso a caso.

---

## DEC-007 — Alegação de rentabilidade fica bloqueada
**17/09/2026 · VIGENTE**

Promessas de rendimento (ex.: `>4% a.m.`, no POST 008) ficam marcadas
`NAO_PUBLICAR_SEM_REVISAO` e **não entram** no portfólio V2.

**Motivo:** anunciar rentabilidade mensal em material de captação aproxima o
texto de oferta de investimento, com exposição regulatória (CVM) e de
publicidade enganosa. Números históricos de economia de energia são outra
coisa e podem aparecer com o enquadramento "resultado divulgado em [data]".
Cabe à usuária, com o jurídico, liberar ou não.

---

## DEC-008 — Mídia pesada fora do Git
**17/09/2026 · VIGENTE**

`data/raw/instagram/{images,videos}/`, `data/raw/onedrive_selected/` e os
derivados pesados ficam no `.gitignore`. Os **manifests** (caminho, sha256,
dimensão, duração) são versionados.

**Motivo:** 245 posts com carrosséis e 63 reels chegam facilmente a vários GB.
Git não lida bem com isso e o repositório ficaria inutilizável. O manifesto
versionado preserva a rastreabilidade: dá para provar qual arquivo existia,
com que hash, sem carregar o binário. Os `.json` de metadados são leves e
**ficam** versionados, porque são a prova documental da legenda original.

---

## DEC-009 — gallery-dl em .venv do projeto
**17/09/2026 · VIGENTE**

Ferramentas instaladas em `.venv/` na raiz do projeto, fora do Git.
Versão registrada: **gallery-dl 1.32.12**.

**Motivo:** não poluir o Python global da máquina, que é compartilhado com
outros projetos. Registrar a versão permite reproduzir o comportamento se um
extractor mudar.

---

## DEC-010 — Sessão do Instagram só em memória
**17/09/2026 · VIGENTE**

A autenticação vem de `--cookies-from-browser`, lida em memória a cada
execução. Nenhum cookie é exportado, salvo ou copiado para o projeto. O log
tem filtro que omite qualquer linha com aparência de dado de sessão.

**Motivo:** um arquivo de cookies em disco é credencial permanente da conta —
se vazar ou for commitado por engano, dá acesso total ao Instagram da empresa.
Ler do navegador a cada vez elimina o artefato persistente. Custo: o navegador
precisa estar fechado durante o download.

---

## DEC-011 — V1 preservada como baseline
**17/09/2026 · VIGENTE**

`C:\caminho\exemplo\Desktop\Portfolio Engvoltaica\` não é alterado. Cópia
em `data/input/previous_portfolio/` e `output/portfolio/v1_baseline/`.

**Motivo:** a V1 é entregável aprovado pela usuária, que pode já ter sido
enviado a cliente. Serve de referência de comparação e de recuo se a V2 não
agradar.

---

## DEC-012 — Tipo do post define expectativa de mídia
**17/09/2026 · VIGENTE**

Reel ⇒ 1 mídia esperada. Post de feed ⇒ expectativa vazia até o download
revelar o tamanho real do carrossel.

**Motivo:** a auditoria do navegador não conseguiu contar de forma confiável
quantas imagens tem cada carrossel. Preencher com palpite criaria falso
"INCOMPLETO" no manifesto. Campo vazio é honesto; o `build_media_manifest.py`
preenche com o real após o download.
