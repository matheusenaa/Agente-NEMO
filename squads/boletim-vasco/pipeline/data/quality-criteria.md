# Quality Criteria — Boletim Vasco

Critérios de qualidade do squad boletim-vasco. Usados pelo Revisor e pelas validações de cada etapa.

## Critérios de precisão de dados

- [ ] Resultado do jogo confirmado em 2+ fontes independentes ou fonte primária oficial (CBF).
- [ ] Tabela coletada cobre as 20 posições com PTS, J, V, E, D, GP, GC, SG.
- [ ] Cada dado registrado com fonte (URL) e data de acesso.
- [ ] Divergências entre fontes sinalizadas explicitamente, sem escolha arbitrária.
- [ ] Nenhum número citado no boletim está ausente do XLSX consolidado.

## Critérios de análise

- [ ] Toda métrica com benchmark ou comparativo (média da liga, rodada anterior, linha de permanência).
- [ ] Todo insight na estrutura "O que aconteceu / O que significa / O que sugere".
- [ ] Todo insight com nível de confiança (Alta/Média/Baixa).
- [ ] Variação de posição calculada sobre a mesma rodada-base em toda a planilha.
- [ ] Aproveitamento com 1 casa decimal; xG com 2 casas.

## Critérios de boletim (redação)

- [ ] As 5 seções obrigatórias presentes em ordem fixa: Resultado → Tabela → Estatísticas → Prévia → Análise.
- [ ] 100% dos números citados existem nos dados fornecidos.
- [ ] Nenhum adjetivo emocional substitui dado (nunca "foi azarado").
- [ ] Cada seção termina com implicação prática ("o que isso muda").
- [ ] Tom analítico e seco, frases curtas, voz ativa.

## Critérios de entregas (PDF/XLSX/PBIX)

- [ ] PDF, XLSX e PBIX apresentam os mesmos números (paridade).
- [ ] XLSX consumível diretamente no Power BI (abas + colunas consistentes).
- [ ] PBIX com medidas em camadas (Base → Negócio → Time Intelligence) e abas por seção.
- [ ] Nomenclatura padrão dos arquivos: `{nome}-{rodada}-{YYYY-MM-DD}`.
- [ ] PBIX com até ~8 visuais por página, barras para ranking, linhas para tendência.

## Critérios de revisão

- [ ] Veredito binário (APPROVE/REJECT) coerente com os scores.
- [ ] Todo score com justificativa; todo REJECT com fix específico localizado.
- [ ] Paridade de números confirmada entre texto, XLSX e dados brutos.
- [ ] Revisão numerada (N de 3); escalar ao usuário após 3 ciclos.