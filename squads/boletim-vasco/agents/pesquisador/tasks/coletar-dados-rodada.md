---
task: "Coletar Dados da Rodada"
order: 1
input: |
  - research_focus: arquivo com rodada/data em pauta
  - fontes_primarias: CBF, ge.globo.com, ESPN, Estadão, FBref
output: |
  - dados_rodada: arquivo markdown com dados estruturados da rodada
  - confianca: nível de confiança por grupo de dados
  - fontes: lista com URL e data de acesso
---

# Coletar Dados da Rodada

Coleta e estrutura os dados oficiais da rodada mais recente do Vasco no Brasileirão. É a fonte exclusiva de dados do squad — tudo passa por aqui.

## Process

1. Ler `output/research-focus.md` para confirmar rodada/data em pauta.
2. Buscar o resultado oficial da partida do Vasco (placar, gols e autores, cartões, local, data) na CBF/súmula e corroborar em ge/ESPN.
3. Coletar a tabela completa do Brasileirão (20 posições com PTS, J, V, E, D, GP, GC, SG) e a posição do Vasco.
4. Coletar estatísticas da partida (xG, posse, finalizações no alvo, chutes, duelos) em FBref/ge.
5. Coletar sequência de resultados recentes do Vasco e dados da próxima rodada (adversário, local, data).
6. Validar cada grupo em fonte secundária, registrar URL + data de acesso e montar `output/dados-rodada.md`.

## Output Format

```yaml
rodada: "N da rodada"
data: "YYYY-MM-DD"
resultado:
  mandante: "Time A"
  visitante: "Time B"
  placar: "X x Y"
  gols: [{autor, minuto, tempo}]
  cartoes: [{jogador, time, tipo}]
  local: "..."
tabela:
  - [posicao, time, pts, jogos, vitorias, empates, derrotas, gp, gc, sg, aproveitamento]
posicao_vasco: {posicao, pts, jogos, sg, aproveitamento}
sequencia_vasco: ["V", "E", "D", "..."]
estatisticas_partida:
  xg_casa: ".."
  xg_fora: ".."
  posse_casa_pct: ".."
  posse_fora_pct: ".."
  finalizacoes_alvo: ".."
proxima_rodada:
  adversario: "..."
  local: "..."
  data: "..."
fontes: [{dado, fonte, url, acesso, confianca}]
```

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
  cartoes: [{jogador: "Tchê Tchê", time: "VAS", tipo: "amarelo"}]
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
  - {dado: "resultado", fonte: "CBF - súmula 27ª rodada", url: "https://cbf.com.br", acesso: "2026-09-17", confianca: "alta"}
  - {dado: "tabela", fonte: "ge.globo.com", url: "https://ge.globo.com", acesso: "2026-09-17", confianca: "alta"}
  - {dado: "xG/posse", fonte: "FBref", url: "https://fbref.com", acesso: "2026-09-17", confianca: "media"}
```

## Quality Criteria

- [ ] Todos os dados vêm de 2+ fontes independentes ou fonte primária oficial.
- [ ] Tabela coletada cobre as 20 posições com PTS, J, V, E, D, GP, GC, SG.
- [ ] Cada dado registra fonte (URL) e data de acesso.
- [ ] Divergências entre fontes sinalizadas explicitamente.

## Veto Conditions

Reject and redo if ANY are true:
1. Qualquer métrica sem fonte e data de acesso — impossível validar o boletim.
2. Tabela com menos de 20 posições ou colunas faltando — alimenta análise e XLSX quebrados.