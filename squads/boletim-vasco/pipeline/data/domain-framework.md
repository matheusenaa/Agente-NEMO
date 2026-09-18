# Domain Framework — Boletim do Vasco (Brasileirão Série A)

Framework operacional do squad boletim-vasco, derivado da pesquisa de domínio.

## 1. Coleta de dados (Pesquisador)

- Fonte primária: CBF (tabela oficial). Fontes de validação: ge.globo.com, ESPN, Estadão, FBref (estatísticas).
- Dados por rodada: resultado do Vasco (placar, gols e autores, cartões, local, data), tabela completa das 20 posições, estatísticas avançadas da partida (xG, xA, posse, finalizações no alvo, duelos, chutes), sequência de resultados recentes do Vasco, adversário da próxima rodada.
- Toda métrica com fonte + data de acesso + confiança (alta/média/baixa).

## 2. Consolidação e análise (Analista)

- Normalizar dados em estrutura tabular: rodada, time, posição, PTS, J, V, E, D, GP, GC, SG, aproveitamento %.
- Calcular variação de posição vs rodada anterior; comparar com benchmarks (média da liga, rodada anterior, linha de permanência).
- Gerar XLSX padronizado (abas: Resumo, Tabela, Rodada, Estatísticas, Prévia) — base para PBIX.
- Escrever insights com estrutura "O que aconteceu / O que significa / O que sugere" + nível de confiança.

## 3. Redação do boletim (Redator)

- Estrutura fixa de 5 seções: Resultado → Tabela e classificação → Estatísticas consolidadas → Prévia da próxima rodada → Análise comentada.
- Tom analítico e seco: conclusões ancoradas em dados, implicação prática ao fim de cada seção.

## 4. Revisão (Revisor)

- Veredito binário APPROVE/REJECT com score por critério; paridade de números entre texto/XLSX/dados; fix específico para cada reprovação; máx. 3 revisões antes de escalar ao usuário.

## 5. Publicação (Editor/Publicador)

- PDF (Markdown renderizado) + XLSX final + PBIX com abas por seção e medidas em camadas (Base → Negócio → Time Intelligence).
- Nomenclatura padrão dos arquivos: `{nome}-{rodada}-{YYYY-MM-DD}`.
- Dicionário único: mesmos números nas 3 entregas; conferência de paridade antes de publicar.