---
type: checkpoint
---

# Step 08: Checkpoint Final

## Context Loading

- `squads/boletim-vasco/output/revisao-boletim.md` — veredito da revisora
- `squads/boletim-vasco/output/boletim-vasco-{rodada}-{data}.pdf`, `xlsx`, `pbix` — artefatos gerados
- `squads/boletim-vasco/_memory/runs.md` — histórico de execuções

## Instructions

1. Revisar com o usuário os artefatos gerados (PDF, XLSX, PBIX) e o resumo de paridade.
2. Confirmar encerramento da execução da rodada.
3. Atualizar `_memory/runs.md` com a linha da rodada executada (Data, Run ID, Tema, Output, Resultado).
4. Atualizar `_memory/memories.md` com aprendizados relevantes da rodada (se houver).

## Output Format

```
# Checkpoint Final — Boletim Vasco

Rodada: {RN}
Artefatos: [{lista de arquivos}]
Paridade: {OK/detalhe de divergência}
Aprovado pelo usuário: {sim | não}
Apreendizado da rodada: {breve}
```

## Output Example

```
# Checkpoint Final — Boletim Vasco

Rodada: 27
Artefatos: [boletim-vasco-2026-27-2026-09-12.pdf, vascobrasileirao-2026-27-2026-09-12.xlsx, vasco-dashboard-2026-27-2026-09-12.pbix]
Paridade: OK
Aprovado pelo usuário: sim
Apreendizado da rodada: confirmado padrão de virada no 2º tempo do Vasco como recurso de análise.
```