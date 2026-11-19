# V1 → V2 — o que mudou e por quê

> Leitura crítica do portfólio anterior (`output/portfolio/v1_baseline/`) e o
> plano que gerou a V2. A V1 continua preservada e válida.

---

## 1. O que a V1 fez bem — e foi mantido

| Acerto | Por que funciona |
|---|---|
| **"Mande uma fatura. A gente devolve o número exato."** | CTA de atrito zero. O cliente não precisa decidir nada, só enviar um PDF que já tem |
| **"Não somos uma revenda."** | Posicionamento em três palavras, e verificável |
| Estrutura de duas frentes espelhadas | Resolve em uma página a segmentação entre quem quer economia e quem quer patrimônio |
| Tabela de economia acumulada em 5 anos | Transforma "20%" em número que impressiona |
| Identidade visual navy + âmbar do logo | Coerente com a marca, sem parecer template |
| Régua âmbar como elemento de ritmo | Amarra as páginas visualmente |
| FAQ com respostas diretas | Derruba objeção antes que o vendedor precise |
| Nota legal com base regulatória | Protege a empresa e sinaliza seriedade |

---

## 2. O que a V1 não tinha — e agora tem

### Faltava prova concreta
A V1 falava de capacidade genericamente: "mais de 500 sistemas", "usinas em
solo e telhado". Nenhum projeto nomeado, nenhum número de obra real. Para um
cliente avaliando fornecedor, isso é fraco: qualquer empresa escreve o mesmo.

**V2:** página inteira dedicada ao **Atacarejo Cliente A** — 200 placas de 530 W,
~10.000 kWh/mês, R$ 100 mil por ano de economia [valores ilustrativos] — mais uma tabela com
projetos e seus números. São dados que a própria Engvoltaica publicou, com o
post de origem registrado.

### Faltava uma linha de negócio inteira
A V1 não mencionava **eletropostos**. A empresa opera essa frente desde 2025,
inclusive com infraestrutura para caminhão elétrico refrigerado. É a linha mais
diferenciada do portfólio e estava invisível.

**V2:** terceira frente, com card próprio na página 3.

### Faltava rastreabilidade
Os números da V1 vinham de contagem de pastas ou de informação verbal. Não havia
como um terceiro conferir.

**V2:** todo número tem linha em `factual_claims.csv` com fonte e status, e o
`qa_portfolio.py` confere o PDF contra essa base.

### Faltava controle do que não pode ser dito
A V1 dependia de eu lembrar de não publicar a rentabilidade mensal.

**V2:** `CASE_010` está marcado `publicar=NAO` no CSV e o gerador simplesmente
não o renderiza. A regra vive no dado, não na memória de quem escreve.

---

## 3. O que a V1 fez e a V2 corrigiu

### Números institucionais sem lastro
A V1 publicou **500+ sistemas, 30 usinas, 800+ adesões** — valores informados
verbalmente. O acervo comprova 311, 19 e 73.

**V2:** usa "+300 clientes", que é o número **publicado pela própria empresa**
no Instagram em jan/2024, com a data explícita. Menor e defensável. Se a empresa
fornecer relatório do sistema de gestão, os números maiores voltam com fonte.
Ver `docs/DATA_QUALITY.md · QD-006`.

### Afirmação forte demais sobre documentação
A V1 dizia que cada obra tem "rastreabilidade de protocolo, aprovação e vistoria".
Isso é verificável nas 311 pastas — mas foi escrito como se valesse para as 500.

**V2:** a afirmação passou a acompanhar os projetos citados, não o universo todo.

### Capa genérica
"Energia solar que gera economia e patrimônio" descreve o setor, não a empresa.

**V2:** *"Seis anos construindo geração própria em Goiás"* — tempo, ação e lugar.
Só a Engvoltaica pode assinar essa frase.

### Foto de capa em baixa resolução efetiva
A V1 usou uma cópia já reamostrada a 1600 px numa página de sangria total. Com
`object-fit: cover`, o dpi efetivo caía para ~77.

**V2:** capa e contracapa vêm dos **originais do OneDrive** (4000×2250), em
2800 px. O QA passou a checar dpi automaticamente.

---

## 4. Decisões de conteúdo da V2

| Decisão | Motivo |
|---|---|
| Case principal com página inteira | Um case com números bate dez menções genéricas |
| Eletropostos como terceira frente | Já existe, é diferenciada, ninguém comunica |
| Nenhuma rentabilidade mensal | Risco regulatório (`DEC-007`) |
| "Não trabalhamos com promessa de rentabilidade" | Transforma a restrição em argumento de seriedade |
| Só 6 cases com nome | São os que a empresa já divulgou (`DEC-006`) |
| Tabela de projetos com coluna de fonte implícita | Deixa claro que são resultados divulgados, não médias |
| Manteve 9 páginas | Além disso ninguém lê |

---

## 5. Comparação

| | V1 | V2 |
|---|---|---|
| Páginas | 9 | 9 |
| Peso | 3,94 MB | 6,92 MB |
| Frentes de negócio | 2 | **3** |
| Cases nomeados | 0 | **6** |
| Números de obra real | 0 | **27 afirmações com fonte** |
| Case com página própria | não | **sim** |
| Rastreabilidade | nenhuma | CSV + QA automático |
| Verificação automática | não | **14 checagens** |
| Resolução da capa | ~77 dpi efetivo | acima do limite do QA |
| Reprodutível por script | não | **sim** |

---

## 6. O que ainda pode melhorar na V3

Depende de coisas que ainda não temos:

1. **Mídia do Instagram em alta** — 245 posts, 63 reels, nunca usados em
   material impresso. Bloqueado pela sessão do navegador.
2. **Depoimento do Cliente E** (POST 169) — prova social em vídeo, dá uma
   página forte com frame + citação.
3. **Página inteira de eletropostos** — hoje é um card.
4. **Mapa de atuação** com pinos nas cidades.
5. **Linha do tempo 2019→2026** — 2022 foi o pico, com mais de 200 contratações.
6. **Nomes e logos** dos clientes do acervo técnico, após autorização.
7. **QR code** para a landing — depois que o 404 for corrigido.
