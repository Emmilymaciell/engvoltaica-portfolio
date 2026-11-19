# .claude/ — configuração do Claude Code neste projeto

Instruções operacionais da sessão. **Nada de negócio entra aqui** — conteúdo
institucional vive em `docs/`, dados em `data/`, entregáveis em `output/`.

## Arquivos

| Arquivo | Para que serve |
|---|---|
| `settings.json` | Permissões e variáveis do projeto |
| `commands/` | Comandos de barra específicos deste repositório |

## Como retomar o projeto numa sessão nova

1. Ler `CLAUDE.md` na raiz — regras permanentes e pipeline
2. Ler `STATE.md` — fase atual e próxima tarefa
3. `git status` — o que está sem commit
4. `state/*.json` — estado de máquina dos pipelines

Nunca é preciso recuperar conversa antiga. Se alguma informação só existe no
histórico de chat, ela está no lugar errado: mova para `docs/`.

## Lembretes que mais economizam retrabalho

- **OneDrive é read-only.** Só leitura e cópia.
- **`data/raw/` é imutável.** Transformação só em `derivados/`.
- **Número sem linha em `factual_claims.csv` não vai para o PDF.**
- **Commit só com autorização explícita da usuária.**
- **O navegador precisa estar fechado** para baixar do Instagram.
- **Use `.venv\Scripts\python.exe`**, não o Python global.
