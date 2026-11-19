---
description: Regenera o portfólio V2 do zero — imagens, HTML, PDF, QA e pacote do Claude Design
---

Regenere o portfólio Engvoltaica executando o pipeline completo, nesta ordem,
a partir da raiz do projeto:

```bash
.venv\Scripts\python.exe scripts\select_portfolio_images.py
.venv\Scripts\python.exe scripts\build_portfolio.py
.venv\Scripts\python.exe scripts\render_pdf.py
.venv\Scripts\python.exe scripts\qa_portfolio.py
.venv\Scripts\python.exe scripts\build_design_package.py
.venv\Scripts\python.exe scripts\build_docs.py
```

Depois:

1. Se o QA acusar **erro**, corrija antes de relatar como pronto. Aviso pode
   ser reportado sem corrigir, mas explique o que é.
2. Renderize algumas páginas em imagem e **confira visualmente** — o QA pega
   texto invadindo rodapé e dpi baixo, não pega layout feio.
3. Atualize `STATE.md`: fase, o que mudou, próxima tarefa.
4. **Não faça commit.** Relate o que mudou e pergunte se ela quer versionar.

Lembre-se: números vêm de `data/processed/`, não do HTML. Se um valor está
errado no PDF, corrija o CSV e rode de novo.
