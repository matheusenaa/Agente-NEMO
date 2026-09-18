---
task: "Revisar Boletim"
order: 1
input: |
  - boletim_rodada: markdown do boletim a ser revisado
  - insights_rodada: dados/insights de referência (XLSX)
  - quality_criteria: critérios de qualidade do squad
output: |
  - veredito: APPROVE | REJECT
  - scores: por critério com justificativa
  - fixes: listagem de requeridos e sugestões
---

# Revisar Boletim

Avalia o boletim contra os critérios de qualidade do squad e emite veredito binário com scores justificados e fixes específicos.

## Process

1. Carregar `pipeline/data/quality-criteria.md` e o boletim pronto (`output/boletim-rodada.md`).
2. Conferir precisão: cada número do texto vs insights/XLSX vs dados brutos do pesquisador.
3. Conferir as 5 seções obrigatórias em ordem fixa.
4. Conferir tom analítico (ausência de adjetivos emocionais e previsões sem benchmark).
5. Conferir implicação prática ao fim de cada seção.
6. Emitir veredito: score por critério (1-10), fixes requeridos e caminho (REJECT → redator/step 4; APPROVE → checkpoint de aprovação), salvar `output/revisao-boletim.md`.

## Output Format

```yaml
veredito: "APPROVE" | "REJECT"
overall: "7.5"
revisao: "Revisão N de 3"
scores:
  - {criterio: "precisão de dados", score: 9, justificativa: "..."}
  - {criterio: "seções completas", score: 8, justificativa: "..."}
  - {criterio: "tom analítico", score: 8, justificativa: "..."}
  - {criterio: "implicação prática", score: 7, justificativa: "..."}
requeridos:
  - {localizacao: "seção/parágrafo", problema: "...", fix: "..."}
sugestoes:
  - {localizacao: "...", sugestao: "..."}
caminho: "reenviar redator (step 4)" | "checkpoint de aprovação"
```

## Output Example

```yaml
veredito: "REJECT"
overall: "5.0"
revisao: "Revisão 1 de 3"
scores:
  - {criterio: "precisão de dados", score: 6, justificativa: "'28 pts' e 'SG -12' corretos; seção Estatísticas cita posse 62% vs XLSX (58%)"}
  - {criterio: "seções completas", score: 8, justificativa: "5/5 em ordem; prévia sem horário/local"}
  - {criterio: "tom analítico", score: 9, justificativa: "seco, sem adjetivos emocionais"}
  - {criterio: "implicação prática", score: 7, justificativa: "presente mas fraca na seção Tabela"}
requeridos:
  - {localizacao: "seção Estatísticas, 3º parágrafo", problema: "posse 62% diverge do XLSX", fix: "corrigir para 58%"}
  - {localizacao: "seção Prévia", problema: "sem horário/local", fix: "adicionar São Januário, 19/09"}
sugestoes:
  - {localizacao: "rodapé PDF", sugestao: "nota de metodologia com fontes e datas de acesso"}
caminho: "reenviar redator (step 4)"
```

## Quality Criteria

- [ ] Veredito binário coerente com os scores (overall ≥ 7 = APPROVE; algum < 4 = REJECT).
- [ ] Todo score tem justificativa; todo REJECT tem fix localizado.
- [ ] Paridade de números confirmada entre texto, XLSX e dados brutos.
- [ ] Revisão numerada (N de 3) registrada.

## Veto Conditions

Reject and redo if ANY are true:
1. Aprovação emitida sem conferência explícita de números com a fonte — erro passaria ao PDF/PBIX.
2. Veredito sem justificativa por critério — revisão não pode ser executada nem auditada.