# Research Brief — Boletim Vasco

## Domínio 1: Análise de dados esportivos

### Frameworks/Metodologia
- **Hierarquia métrica → contexto**: resultado/placar primeiro, depois métricas de processo (xG, posse, finalizações), depois métricas condicionais de contexto (jogo equilibrado vs decidido). Estatísticas brutas sem segmentação por contexto distorcem a leitura.
- **Preferir métricas "esperadas" (xG/xA) ao placar cru**: xG mede a chance antes do chute; xGOT/PSxG mede o chute na direção do gol; xA mede a qualidade da assistência.
- **Interpretar em blocos**: xG total vs gols (sorte/finalização), xG diferencial (xG − xGA), npxG (sem pênaltis), desempenho de goleiro (gols vs xGOT).
- **Triangulação tática**: números + posse, PPDA, duelos, grandes chances, cartões — métricas isoladas não contam a história.
- **Vocabulário único** (FIFA Football Language): coletar data points de forma consistente em todas as fontes do pipeline.

### Vocabulário profissional
- xG (Expected Goals), npxG, xGOT/PSxG, xA (Expected Assists), PPDA, duelos (aéreos/ganhos), grandes chances, finalizações no alvo, aproveitamento (%), SG, sequência de resultados.

### Erros comuns / anti-patterns
- Correlação tratada como causalidade; xG cru fora de contexto; per-90 mal calculado; vanity metrics (posse sem conversão); generalizar modelos de outras ligas.

### Critérios de qualidade
- Consistência de fonte e definição (Opta/FBref/CBF); contexto sempre presente (benchmark); rastreabilidade; tom analítico seco.

## Domínio 2: Estrutura de boletins de rodada

### Estrutura recomendada
1. Cabeçalho/metadados — rodada, datas, contexto.
2. Resultado da rodada — placares completos.
3. Tabela e classificação — posição, PTS, J, V/E/D, GP/GC/SG, aproveitamento %, sequência, variação de posição.
4. Estatísticas consolidadas — agregados da rodada e temporada (xG, finalizações, disciplina), sempre com benchmark.
5. Prévia da próxima rodada — confrontos, contexto, o que está em jogo.
6. Análise comentada — narrativa fria ligando números a acontecimentos.

### Exemplos de alta qualidade
- ESPN "Resenha da Rodada" (Brasileirão): rodada narrada por dados + contexto.
- FIFA Matchday round-up/review: placares → destaque → prévia → cenário classificatório.

### Erros comuns
- Boletim = despejo de relatório de dados; ordem invertida (detalhes antes da síntese); números soltos sem benchmark; viés emocional disfarçado de análise.

## Domínio 3: Dashboards Power BI

### Boas práticas
- Star schema: fatos (eventos) + dimensões (Time, Rodada, Data); medidas a colunas calculadas; tabela de datas marcada.
- 1 página/aba por seção; KPI principal no canto superior esquerdo; ≤8 visuais por página.
- Medidas em camadas: Base → Negócio → Time Intelligence.
- DAX essencial: CALCULATE, DIVIDE, TOTALYTD, SAMEPERIODLASTYEAR, DATEADD, PREVIOUSMONTH.
- Barras p/ ranking, linhas p/ tendência, scatter p/ relações; evitar pizza/gauge/3D.

### Vocabulário BI
- Medida vs coluna calculada, time intelligence, slicer, contexto de filtro/linha, KPI card, bookmark/drill-through, star schema, RLS.

### Anti-patterns
- Dashboard vitrine (visual dumping ground); métricas sem contexto; pizza/donut/gauge para comparar categorias; excesso de slicers; colunas calculadas no lugar de medidas; escalas misturadas.

## Síntese
1. Um pipeline, um dicionário único: mesmas métricas nas 3 entregas (PDF, XLSX, PBIX).
2. Estrutura fixa de rodada (Resultados → Tabela → Estatísticas → Prévia → Análise).
3. Contexto é a qualidade: todo número com benchmark.
4. PBIX orientado a modelo, não a visual (star schema, medidas em camadas, DAX CALCULATE/DIVIDE).
5. Tom seco e conclusivo: "criou 2.4 xG e não converteu" em vez de "foi azarado".