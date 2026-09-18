---
type: checkpoint
outputFile: squads/boletim-vasco/output/research-focus.md
---

# Step 01: Checkpoint Foco

## Context Loading

- Antes de pesquisar, o usuário define o foco da rodada.

## Instructions

1. Apresentar o contexto do squad (boletim do Vasco — Brasileirão) e da empresa NEMO.
2. Perguntar o foco específico da pesquisa: "Qual rodada/jogo quer cobrir hoje?"
3. Perguntar o alcance temporal: 
   1. Última rodada jogada (padrão)
   2. Rodada específica (número)
   3. Outra data/contexto
4. Salvar a resposta do usuário no arquivo `outputFile` antes de seguir.

## Output Format

```
# Foco de Pesquisa — Boletim Vasco

Rodada: {número ou "última"}
Data limite: {YYYY-MM-DD}
Observações: {contexto adicional do usuário}
```

## Output Example

```
# Foco de Pesquisa — Boletim Vasco

Rodada: última
Data limite: 2026-09-17
Observações: cobrir a 27ª rodada (Grêmio x Vasco) e a prévia da 28ª (Vasco x Coritiba).
```