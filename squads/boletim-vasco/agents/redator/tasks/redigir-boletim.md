---
task: "Redigir Boletim"
order: 1
input: |
  - insights_rodada: markdown com insights do analista
  - xlsx: planilha consolidada (fonte dos números)
  - tone_of_voice: tom analítico e seco do squad
output: |
  - boletim_rodada: markdown com o boletim completo em 5 seções
---

# Redigir Boletim

Escreve o boletim completo do Vasco em Markdown no tom analítico e seco, com as 5 seções obrigatórias e implicação prática ao fim de cada uma.

## Process

1. Reunir insights e XLSX do analista — fonte única de verdade (nunca inventar número).
2. Definir o fio narrativo da rodada (o fato que explica o resultado e sua consequência).
3. Redigir seção 1 (Resultado da rodada): placar, gols, autores, cartões, local, data.
4. Redigir seção 2 (Tabela e classificação): posição, PTS, pontos perdidos, SG, desempate, aproveitamento, linha de permanência.
5. Redigir seção 3 (Estatísticas consolidadas) com benchmark e seção 4 (Prévia da próxima rodada) com adversário/local/data/o que está em jogo.
6. Redigir seção 5 (Análise comentada) ligando números à tática; fechar com implicação prática em cada seção; salvar `output/boletim-rodada.md`.

## Output Format

```markdown
# Boletim Vasco — {RN}ª Rodada ({YYYY-MM-DD})

## Resultado da rodada
...

## Tabela e classificação
...

## Estatísticas consolidadas
...

## Prévia da próxima rodada
...

## Análise comentada
...
```

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

Posse 58% x 42%; finalizações no alvo 3 x 5; xG ~1.1 x ~1.4. O Vasco criou mais apesar de
menos bola — eficiência por transições. Nas últimas 12 rodadas pontuou em 8 (66%).

## Prévia da próxima rodada

Vasco x Coritiba (São Januário, 19/09). Confronto com candidato à região de corte: vencer
significa ultrapassar concorrente direto e sair do Z4.

## Análise comentada

Mais do que o placar, importa a construção: virada em 4 minutos com banco acionado. O
custo é o SG -12 — empatado em pontos, o desempate joga contra. Cada empate futuro precisa
ser tratado como derrota nos critérios.
```

## Quality Criteria

- [ ] 100% dos números citados existem nos dados fornecidos.
- [ ] As 5 seções estão presentes em ordem fixa.
- [ ] Nenhum adjetivo emocional substitui dado.
- [ ] Cada seção termina com implicação prática.

## Veto Conditions

Reject and redo if ANY are true:
1. Número citado que não consta nos insights/XLSX — quebra a credibilidade do boletim.
2. Falta uma das 5 seções obrigatórias ou a ordem foi alterada.