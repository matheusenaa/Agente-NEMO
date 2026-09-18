---
task: "Consolidar Dados da Rodada"
order: 1
input: |
  - dados_rodada: markdown estruturado do pesquisador (resultado, tabela, estatísticas)
  - quality_criteria: critérios de qualidade do squad
output: |
  - xlsx: planilha padronizada (abas Resumo/Tabela/Rodada/Estatísticas/Prévia)
  - insights: markdown com insights + confiança + implicação
---

# Consolidar Dados da Rodada

Converte os dados brutos da rodada em planilha XLSX padronizada (fonte única do boletim e do PBIX) e extrai insights analíticos com benchmark e confiança.

## Process

1. Ler `output/dados-rodada.md` e os critérios de qualidade do squad.
2. Normalizar em tabelas: rodada, time, posição, PTS, J, V, E, D, GP, GC, SG, aproveitamento %.
3. Calcular variação de posição do Vasco vs rodada anterior e benchmarks (média da liga, linha de permanência ~44 pts).
4. Identificar top/bottom métricas da partida (posse, xG, finalizações, disciplina) com contexto.
5. Gerar o XLSX com 5 abas padronizadas (Resumo, Tabela, Rodada, Estatísticas, Prévia).
6. Escrever insights na estrutura "O que aconteceu / O que significa / O que sugere" com confiança, salvando em `output/insights-rodada.md`.

## Output Format

```yaml
xlsx:
  arquivo: "vascobrasileirao-{rodada}-{YYYY-MM-DD}.xlsx"
  abas: [Resumo, Tabela, Rodada, Estatísticas, Prévia]
  resumo: {posicao, pts, jogos, sg, aproveitamento, variacao_posicao, linha_permanencia}
metrics:
  aproveitamento: "35.9"
  pontos_por_jogo: "1.08"
  xg_diferencial: ".."
  variacao_posicao: "estável|+N|-N"
insights:
  - {que_aconteceu, o_que_significa, o_que_sugere, confianca: "alta|media|baixa"}
```

## Output Example

```yaml
xlsx:
  arquivo: "vascobrasileirao-2026-27-2026-09-12.xlsx"
  abas: [Resumo, Tabela, Rodada, Estatísticas, Prévia]
  resumo: {posicao: 17, pts: 28, jogos: 26, sg: -12, aproveitamento: 35.9, variacao_posicao: "estável", linha_permanencia: 44}
metrics:
  aproveitamento: "35.9"
  pontos_por_jogo: "1.08"
  xg_diferencial: "+0.3"
  variacao_posicao: "estável"
insights:
  - que_aconteceu: "O Vasco pontuou em 8 das últimas 12 rodadas (66%)."
    o_que_significa: "Ritmo de ~44 pts ao fim — na linha de permanência."
    o_que_sugere: "Manter o ritmo basta; desempate (SG -12) é o fiel da balança."
    confianca: "alta"
    benchmark: "linha de permanência (44 pts)"
  - que_aconteceu: "Criou mais xG fora de casa (1.4) com apenas 42% de posse."
    o_que_significa: "Eficiência via transições, não domínio de jogo."
    o_que_sugere: "Padrão de virada no 2º tempo é recurso real a repetir."
    confianca: "media"
    benchmark: "posse média de mandantes x visitantes"
```

## Quality Criteria

- [ ] XLSX com as 5 abas definidas e aproveitamento calculado consistentemente.
- [ ] Cada insight tem implicação + nível de confiança.
- [ ] Nenhuma métrica aparece sem comparativo ou benchmark.
- [ ] Variação de posição usa a mesma rodada-base em toda a planilha.

## Veto Conditions

Reject and redo if ANY are true:
1. Insight sem confiança ou sem benchmark — métricas soltas distorcem o boletim.
2. XLSX com abas faltantes ou estrutura inconsistente — quebra a importação no Power BI.