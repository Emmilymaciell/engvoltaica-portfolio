# STATE — Engvoltaica Portfolio (versão pública)

> Snapshot público. O estado operacional do projeto privado (caminhos da máquina, pendências comerciais da
> empresa, nomes de clientes, dados cadastrais) foi retirado desta cópia.

## Fase (no projeto privado, set/2026)

```
[✔] Fase 0  Repositório, arquitetura, documentação
[✔] Fase 1  Ingestão da auditoria, cases, verificação documental, varredura do acervo corporativo
[◐] Fase 2  Portfólio V2 + pacote de design  ← entregue
[ ] Fase 3  Mídias do Instagram              ← bloqueada (download exige navegador fechado)
```

## Números do projeto privado (fonte: STATE de 17/09/2026)

| Item | Valor |
|---|---|
| Posts catalogados | 245 (63 reels, 182 feed) |
| Projetos consolidados | 20 (10 nomeados + 10 usinas individuais) |
| Afirmações factuais com fonte | 28 (27 liberadas, 1 bloqueada) |
| Arquivos relevantes indexados no acervo corporativo | 31.067 (30.337 só na nuvem) |
| Portfólio V2 | 9 páginas, 6,92 MB, QA sem erros |
| Testes | 28 passaram, 5 pulados (dependem do download de mídia) |
| Scripts | 13 |

## Nesta cópia

- `data/`, `derivados/`, `output/`, `logs/`, `state/`, fichas de cases e documentos de evidência foram removidos.
- Sem os dados, os testes de dados/PDF/mídia ficam **pulados** (`skipif`); os de parsing e segurança rodam.
- `examples/` traz linhas fictícias no formato de `posts_master.csv` e `cases_master.csv`.

## Aviso

*Dados fictícios. Versão sanitizada de um sistema em uso real; identificadores de clientes foram substituídos.*
