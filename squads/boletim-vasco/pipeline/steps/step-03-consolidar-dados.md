---
execution: subagent
agent: analista
inputFile: squads/boletim-vasco/output/dados-rodada.md
outputFile: squads/boletim-vasco/output/insights-rodada.md
model_tier: powerful
---

# Step 03: Consolidar Dados

## Context Loading

- `squads/boletim-vasco/output/dados-rodada.md` — dados estruturados da rodada
- `squads/boletim-vasco/agents/analista.agent.md` + `tasks/consolidar-dados-rodada.md` — persona e tarefa
- `squads/boletim-vasco/pipeline/data/quality-criteria.md` — critérios de análise

## Instructions

### Process
1. Ler os dados brutos e os critérios de qualidade.
2. Normalizar em tabelas: rodada, time, posição, PTS, J, V, E, D, GP, GC, SG, aproveitamento %.
3. Calcular variação de posição do Vasco vs rodada anterior e benchmarks (média da liga, linha de permanência ~44 pts).
4. Identificar top/bottom métricas da partida (posse, xG, finalizações, disciplina) com contexto.
5. Gerar o XLSX (5 abas: Resumo, Tabela, Rodada, Estatísticas, Prévia).
6. Escrever insights com implicação + confiança em `insights-rodada.md`.

## Output Format

Arquivo de saída no esquema YAML do task `consolidar-dados-rodada.md` (xlsx, metrics, insights). O XLSX é também gerado como artefato intermediário (consumido pelo boletim e pelo PBIX).

## Output Example

```yaml
xlsx:
  arquivo: "vascobrasileirao-2026-27-2026-09-12.xlsx"
  abas: [Resumo, Tabela, Rodada, Estatísticas, Prévia]
  resumo: {posicao: 17, pts: 28, jogos: 26, sg: -12, aproveitamento: 35.9, variacao_posicao: "estável", linha_permanencia: 44}
insights:
  - que_aconteceu: "O Vasco pontuou em 8 das últimas 12 rodadas (66%)."
    o_que_significa: "Ritmo de ~44 pts ao fim — na linha de permanência."
    o_que_sugere: "Manter o ritmo basta; desempate (SG -12) é o fiel da balança."
    confianca: "alta"
```

## Veto Conditions

Reject and redo if ANY are true:
1. Insight sem confiança ou sem benchmark.
2. XLSX com abas faltantes ou estrutura inconsistente.

## Quality Criteria

- [ ] XLSX com as 5 abas e aproveitamento calculado consistentemente.
- [ ] Cada insight com implicação + nível de confiança.
- [ ] Nenhuma métrica sem comparativo ou benchmark.
- [ ] Variação de posição com a mesma rodada-base.