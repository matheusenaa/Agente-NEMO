---
type: checkpoint
---

# Step 06: Checkpoint Aprovação

## Context Loading

- `squads/boletim-vasco/output/revisao-boletim.md` — veredito da revisora (APPROVE/REJECT)
- `squads/boletim-vasco/output/boletim-rodada.md` — conteúdo a ser aprovado

## Instructions

1. Apresentar ao usuário o veredito da revisão (scores e requeridos, se houver).
2. Exibir o boletim pronto para aprovação de conteúdo.
3. Pedir decisão explícita:
   - Aprovar o boletim para geração dos artefatos (PDF/XLSX/PBIX)
   - Rejeitar e pedir ajustes (retorna ao pipeline de redação/revisão)
4. Registrar a decisão do usuário antes de seguir.

## Output Format

```
# Checkpoint de Aprovação — Boletim Vasco

Veredito da revisão: {APPROVE/REJECT}
Decisão do usuário: {aprovar | ajustar}
Observações: {ajustes solicitados, se houver}
```

## Output Example

```
# Checkpoint de Aprovação — Boletim Vasco

Veredito da revisão: APPROVE (8,4/10)
Decisão do usuário: aprovar
Observações: seguir para geração dos artefatos (PDF, XLSX, PBIX).
```