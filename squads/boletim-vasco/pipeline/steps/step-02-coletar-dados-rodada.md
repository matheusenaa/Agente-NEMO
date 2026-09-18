---
execution: subagent
agent: pesquisador
inputFile: squads/boletim-vasco/output/research-focus.md
outputFile: squads/boletim-vasco/output/dados-rodada.md
model_tier: powerful
---

# Step 02: Coletar Dados da Rodada

## Context Loading

- `squads/boletim-vasco/output/research-focus.md` — foco definido pelo usuário (rodada/data)
- `squads/boletim-vasco/agents/pesquisador.agent.md` + `tasks/coletar-dados-rodada.md` — persona e tarefa
- `squads/boletim-vasco/pipeline/data/research-brief.md` — boas práticas de pesquisa

## Instructions

### Process
1. Ler o foco de pesquisa e confirmar qual partida do Vasco está em pauta.
2. Coletar resultado oficial (placar, gols e autores, cartões, local, data) na CBF/súmula, corroborando em ge/ESPN.
3. Coletar a tabela completa (20 posições: PTS, J, V, E, D, GP, GC, SG) e a posição do Vasco.
4. Coletar estatísticas da partida (xG, posse, finalizações no alvo) em FBref/ge.
5. Coletar sequência de resultados e dados da próxima rodada (adversário, local, data).
6. Validar cada grupo em fonte secundária, registrar URL + data de acesso e salvar `dados-rodada.md`.

## Output Format

O arquivo de saída segue o esquema YAML definido no task file `coletar-dados-rodada.md` (seções: rodada, resultado, tabela, posicao_vasco, sequencia_vasco, estatisticas_partida, proxima_rodada, fontes).

## Output Example

```yaml
rodada: "27"
data: "2026-09-12"
resultado:
  mandante: "Grêmio"
  visitante: "Vasco"
  placar: "1 x 2"
  gols:
    - {autor: "Villasanti", minuto: 39, tempo: "1T", time: "GRE"}
    - {autor: "Thiago Mendes", minuto: 30, tempo: "2T", time: "VAS"}
    - {autor: "Colidio", minuto: 34, tempo: "2T", time: "VAS"}
  local: "Arena do Grêmio"
tabela:
  - [16, Mirassol, 28, 26, 7, 7, 12, 29, 40, -11, 35.9]
  - [17, Vasco, 28, 26, 7, 7, 12, 29, 41, -12, 35.9]
  - [18, Internacional, 28, 27, 6, 10, 11, 30, 35, -5, 34.6]
posicao_vasco: {posicao: 17, pts: 28, jogos: 26, sg: -12, aproveitamento: 35.9}
sequencia_vasco: ["V", "E", "D", "V", "V", "E"]
estatisticas_partida:
  xg_casa: "1.1"
  xg_fora: "1.4"
  posse_casa_pct: "58"
  posse_fora_pct: "42"
  finalizacoes_alvo: "3 x 5"
proxima_rodada:
  adversario: "Coritiba"
  local: "São Januário"
  data: "2026-09-19"
fontes:
  - {dado: "resultado", fonte: "CBF", url: "https://cbf.com.br", acesso: "2026-09-17", confianca: "alta"}
```

## Veto Conditions

Reject and redo if ANY are true:
1. Qualquer métrica sem fonte e data de acesso — impossível validar o boletim.
2. Tabela com menos de 20 posições ou colunas faltando.

## Quality Criteria

- [ ] Todos os dados vêm de 2+ fontes independentes ou fonte primária oficial.
- [ ] Tabela coletada cobre as 20 posições com PTS, J, V, E, D, GP, GC, SG.
- [ ] Cada dado registra fonte (URL) e data de acesso.
- [ ] Divergências entre fontes sinalizadas explicitamente.