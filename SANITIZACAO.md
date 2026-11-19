# Sanitização desta versão pública

Cópia sanitizada de um projeto em uso real. Nada aqui é dado de cliente ou de terceiro: o que aparece como exemplo é inventado. Detalhe completo da sanitização: relatório interno da autora.

## O que foi removido

Mídias e exports do Instagram/OneDrive, dados processados, nomes de clientes.

## O que foi trocado

Clientes → `Cliente A…G`; CNPJ, CREA, endereço e telefone → fictícios; números de case (placas, kWp, geração, economia) → **valores ilustrativos**; nome de cliente num caminho de foto → `Cliente F`.

## O que é fictício

`examples/exemplo_cases_master.csv` e `exemplo_posts_master.csv` (linhas fictícias). Os testes que dependem de `data/processed/`, PDF ou mídias são pulados (`skipif`).

## Como verificar

```bat
py -3.12 -m pytest tests -q
```

Varreduras (2026-11-19): gitleaks `dir` só com falsos positivos justificados; busca por caminho local, e-mail, nomes do cliente e links privados sem ocorrências reais.
