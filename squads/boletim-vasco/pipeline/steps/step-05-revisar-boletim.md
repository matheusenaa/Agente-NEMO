---
execution: subagent
agent: revisor
inputFile: squads/boletim-vasco/output/boletim-rodada.md
outputFile: squads/boletim-vasco/output/revisao-boletim.md
model_tier: powerful
on_reject: 4
---

# Step 05: Revisar Boletim

## Context Loading

- `squads/boletim-vasco/output/boletim-rodada.md` — boletim a ser revisado
- `squads/boletim-vasco/output/insights-rodada.md` + XLSX — dados de referência
- `squads/boletim-vasco/agents/revisor.agent.md` + `tasks/revisar-boletim.md` — persona e tarefa
- `squads/boletim-vasco/pipeline/data/quality-criteria.md` — rubrica

## Instructions

### Process
1. Carregar critérios de qualidade e o boletim pronto.
2. Conferir precisão: números do texto vs insights/XLSX vs dados brutos.
3. Conferir as 5 seções em ordem fixa.
4. Conferir tom analítico (sem adjetivos emocionais, sem previsões sem benchmark).
5. Conferir implicação prática ao fim de cada seção.
6. Emitir veredito APPROVE/REJECT com scores, requeridos e caminho (REJECT → step 4, redator).

## Output Format

Esquema YAML do task `revisar-boletim.md` (veredito, overall, revisao, scores, requeridos, sugestoes, caminho).

## Output Example

```yaml
veredito: "REJECT"
overall: "5.0"
revisao: "Revisão 1 de 3"
scores:
  - {criterio: "precisão de dados", score: 6, justificativa: "posse 62% diverge do XLSX (58%)"}
  - {criterio: "tom analítico", score: 9, justificativa: "seco, sem adjetivos emocionais"}
requeridos:
  - {localizacao: "seção Estatísticas, 3º parágrafo", problema: "posse 62%", fix: "corrigir para 58%"}
  - {localizacao: "seção Prévia", problema: "sem horário/local", fix: "adicionar São Januário, 19/09"}
caminho: "reenviar redator (step 4)"
```

## Veto Conditions

Reject and redo if ANY are true:
1. Aprovação emitida sem conferência explícita de números com a fonte.
2. Veredito sem justificativa por critério.

## Quality Criteria

- [ ] Veredito binário coerente com os scores (overall ≥ 7 = APPROVE; algum < 4 = REJECT).
- [ ] Todo score com justificativa; todo REJECT com fix localizado.
- [ ] Paridade de números confirmada entre texto, XLSX e dados brutos.
- [ ] Revisão numerada (N de 3).