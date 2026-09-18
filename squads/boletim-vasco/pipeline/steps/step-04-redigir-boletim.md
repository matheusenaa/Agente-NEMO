---
execution: inline
agent: redator
inputFile: squads/boletim-vasco/output/insights-rodada.md
outputFile: squads/boletim-vasco/output/boletim-rodada.md
---

# Step 04: Redigir Boletim

## Context Loading

- `squads/boletim-vasco/output/insights-rodada.md` — insights do analista
- `squads/boletim-vasco/output/vascobrasileirao-{rodada}-{data}.xlsx` — fonte dos números
- `squads/boletim-vasco/agents/redator.agent.md` + `tasks/redigir-boletim.md` — persona e tarefa
- `squads/boletim-vasco/pipeline/data/tone-of-voice.md` — tom analítico e seco

## Instructions

### Process
1. Reunir insights e XLSX — fonte única de números.
2. Definir o fio narrativo da rodada.
3. Redigir as 5 seções em ordem fixa: Resultado → Tabela → Estatísticas → Prévia → Análise.
4. Aplicar tom analítico seco; fechar cada seção com implicação prática.
5. Salvar em `boletim-rodada.md`.

## Output Format

Markdown com as 5 seções na ordem: `## Resultado da rodada`, `## Tabela e classificação`, `## Estatísticas consolidadas`, `## Prévia da próxima rodada`, `## Análise comentada`, precedidas pelo cabeçalho `# Boletim Vasco — {RN}ª Rodada ({YYYY-MM-DD})`.

## Output Example

```markdown
# Boletim Vasco — 27ª Rodada (2026-09-12)

## Resultado da rodada

Grêmio 1 x 2 Vasco (Arena do Grêmio). Gols: Villasanti 39' (1T); Thiago Mendes 30' (2T)
e Colidio 34' (2T). Primeira vitória do Vasco em Porto Alegre em 20 anos.

## Tabela e classificação

O Vasco segue 17º com 28 pts (26 J; SG -12), ainda no Z4 pelo saldo de gols — empatado
com Grêmio (15º, -7) e Mirassol (16º, -11). Aproveitamento: 35,9%. Linha de permanência
projetada: ~44 pts — faltam 12 jogos e ~16 pontos (1,33/partida).

## Estatísticas consolidadas

Posse 58% x 42%; finalizações no alvo 3 x 5; xG ~1.1 x ~1.4. Nas últimas 12 rodadas
pontuou em 8 (66%) — ritmo de ~44 pts ao fim.

## Prévia da próxima rodada

Vasco x Coritiba (São Januário, 19/09). Confronto com candidato à região de corte:
vencer significa ultrapassar concorrente direto e sair do Z4.

## Análise comentada

Mais do que o placar, importa a construção: virada em 4 minutos com banco acionado.
Eficiência por transições (42% de posse, mais xG). O custo é o SG -12 — empatado em
pontos, o desempate joga contra. Cada empate futuro precisa ser tratado como derrota
nos critérios.
```

## Veto Conditions

Reject and redo if ANY are true:
1. Número citado que não consta nos insights/XLSX.
2. Falta uma das 5 seções obrigatórias ou ordem alterada.

## Quality Criteria

- [ ] 100% dos números citados existem nos dados fornecidos.
- [ ] As 5 seções em ordem fixa.
- [ ] Nenhum adjetivo emocional substitui dado.
- [ ] Cada seção termina com implicação prática.