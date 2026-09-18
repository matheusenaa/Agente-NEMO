---
execution: subagent
agent: editor-publicador
inputFile: squads/boletim-vasco/output/boletim-rodada.md
outputFile: squads/boletim-vasco/output/boletim-vasco-2026-27-2026-09-12.pdf
model_tier: powerful
---

# Step 07: Gerar Artefatos

## Context Loading

- `squads/boletim-vasco/output/boletim-rodada.md` — boletim aprovado
- `squads/boletim-vasco/output/vascobrasileirao-{rodada}-{data}.xlsx` — modelo consolidado
- `squads/boletim-vasco/agents/editor-publicador.agent.md` + `tasks/gerar-artefatos.md` — persona e tarefa
- `squads/boletim-vasco/pipeline/data/output-examples.md` — exemplo de entrega esperada

## Instructions

### Process
1. Receber o boletim aprovado (Markdown) e o XLSX consolidado.
2. Renderizar o Markdown em PDF (`boletim-vasco-{rodada}-{YYYY-MM-DD}.pdf`).
3. Certificar o XLSX final com as 5 abas padrão.
4. Montar o PBIX (`vasco-dashboard-{rodada}-{YYYY-MM-DD}.pbix`) importando o XLSX, com abas Rodada/Tabela/Histórico/Prévia e medidas em camadas.
5. Conferir paridade (spot-check PTS, SG, posição, aproveitamento) entre as 3 entregas.
6. Listar os artefatos gerados no resumo final.

## Output Format

Esquema YAML do task `gerar-artefatos.md` (artefatos, paridade, pbix_medidas).

## Output Example

```yaml
artefatos:
  pdf: "boletim-vasco-2026-27-2026-09-12.pdf"
  xlsx: "vascobrasileirao-2026-27-2026-09-12.xlsx"
  pbix: "vasco-dashboard-2026-27-2026-09-12.pbix"
paridade:
  - {metrica: "PTS", pdf: 28, xlsx: 28, pbix: 28, ok: true}
  - {metrica: "SG", pdf: -12, xlsx: -12, pbix: -12, ok: true}
  - {metrica: "Posição", pdf: "17º", xlsx: "17º", pbix: "17º", ok: true}
  - {metrica: "Aproveitamento", pdf: "35.9", xlsx: "35.9", pbix: "35.9", ok: true}
pbix_medidas:
  base: [PTS, Jogos, Vitorias, SaldoGols]
  negocio: [AproveitamentoPct, PontosPorJogo, XgDiferencial]
  time_intelligence: [VariacaoPosicao, SeqResultados, PontosUltimasN]
```

## Veto Conditions

Reject and redo if ANY are true:
1. Paridade quebrada entre entregas (número divergente entre PDF/XLSX/PBIX).
2. Nome de arquivo sem rodada/data.

## Quality Criteria

- [ ] PDF, XLSX e PBIX apresentam os mesmos números (paridade confirmada).
- [ ] PBIX com medidas em camadas e abas por seção.
- [ ] Nomenclatura dos arquivos segue o padrão.
- [ ] XLSX consumível diretamente no Power BI.