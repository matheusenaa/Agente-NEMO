rodada: "28"
data: "2026-09-17"
contexto: "prévia por cenários (jogo não disputado)"
campeonato: "Brasileirão Série A 2026"

# RESULTADO RODADA 27 (já disputado)
resultado_27:
  mandante: "Grêmio"
  visitante: "Vasco"
  placar: "1 x 2"
  gols:
    - {autor: "Villasanti", minuto: "39' 1T", time: "GRE"}
    - {autor: "Thiago Mendes", minuto: "30' 2T (76')", time: "VAS"}
    - {autor: "Colidio", minuto: "34' 2T (80')", time: "VAS"}
  cartoes_amarelos:
    - {jogador: "Pedro Gabriel", time: "GRE"}
    - {jogador: "Wallace", time: "GRE"}
    - {jogador: "Tchê Tchê", time: "VAS"}
    - {jogador: "Cuiabano", time: "VAS"}
    - {jogador: "Robert Renan", time: "VAS"}
  cartoes_vermelhos: "0"
  local: "Arena do Grêmio (Porto Alegre/RS)"
  data: "2026-09-12"
  horario: "16h (CBF súmula)"
  arbitro: "Raphael Claus (SP)"
  publico: "34.297"
  renda: "R$ 2.032.486,81"
  primeiro_tempo: "1 x 0 (Grêmio)"

# TABELA APÓS A RODADA 27 (20 posições)
# FONTE PRIMÁRIA: exa.ai/standings (publicação 18/09/2026, acesso 17/09/2026).
# [posicao, time, pts, jogos, vitorias, empates, derrotas, gp, gc, sg, aproveitamento_pct]
tabela_atual:
  - [1, Flamengo, 57, 27, 17, 6, 4, 53, 22, +31, 70.4]
  - [2, Palmeiras, 56, 27, 16, 8, 3, 47, 21, +26, 69.1]
  - [3, Athletico-PR, 46, 27, 13, 7, 7, 41, 31, +10, 56.8]
  - [4, Bahia, 46, 27, 12, 10, 5, 42, 33, +9, 56.8]
  - [5, Fluminense, 45, 27, 12, 9, 6, 41, 35, +6, 55.6]
  - [6, Cruzeiro, 42, 27, 12, 6, 9, 39, 39, 0, 51.9]
  - [7, Atlético-MG, 39, 26, 11, 6, 9, 35, 31, +4, 50.0]
  - [8, Coritiba, 38, 27, 10, 8, 9, 37, 38, -1, 46.9]
  - [9, Bragantino, 36, 26, 10, 6, 10, 32, 29, +3, 46.2]
  - [10, Santos, 35, 26, 9, 8, 9, 39, 39, 0, 44.9]
  - [11, Botafogo, 35, 27, 9, 8, 10, 41, 43, -2, 43.2]
  - [12, São Paulo, 33, 26, 9, 6, 11, 31, 30, +1, 42.3]
  - [13, Vitória, 33, 27, 9, 6, 12, 27, 39, -12, 40.7]
  - [14, Corinthians, 32, 27, 8, 8, 11, 28, 29, -1, 39.5]
  - [15, Mirassol, 29, 27, 7, 8, 12, 31, 42, -11, 35.8]
  - [16, Grêmio, 28, 27, 7, 7, 13, 30, 38, -8, 34.6]
  - [17, Vasco, 28, 26, 7, 7, 12, 29, 41, -12, 35.9]
  - [18, Internacional, 28, 27, 6, 10, 11, 30, 35, -5, 34.6]
  - [19, Remo, 23, 27, 5, 8, 14, 31, 45, -14, 28.4]
  - [20, Chapecoense, 17, 26, 3, 8, 15, 28, 52, -24, 21.8]

zonas:
  g4_libertadores: "1º-4º (Flamengo, Palmeiras, Athletico-PR, Bahia)"
  pre_libertadores: "5º-6º (Fluminense, Cruzeiro)"
  sul_americana: "7º-12º (Atlético-MG a São Paulo)"
  z4_rebaixamento: "17º-20º (Vasco, Internacional, Remo, Chapecoense)"

# POSIÇÃO DO VASCO (confirmada por piranot, portalrondonia, exa.ai)
posicao_vasco: {posicao: 17, pts: 28, jogos: 26, sg: -12, aproveitamento: 35.9}

# SEQUÊNCIA DE RESULTADOS DO VASCO (últimos 5, R23-R27, cronológica)
sequencia_vasco: ["D", "D", "V", "D", "V"]
ultimos_jogos:
  - {rodada: 23, data: "2026-08-16", jogo: "Vasco 0 x 3 Santos", resultado: "D"}
  - {rodada: 24, data: "2026-08-23", jogo: "Palmeiras 4 x 1 Vasco", resultado: "D"}
  - {rodada: 25, data: "2026-08-29", jogo: "Vasco 3 x 1 Cruzeiro", resultado: "V"}
  - {rodada: 26, data: "2026-09-05", jogo: "Fluminense 1 x 0 Vasco", resultado: "D"}
  - {rodada: 27, data: "2026-09-12", jogo: "Grêmio 1 x 2 Vasco", resultado: "V"}

# PRÓXIMA RODADA - VASCO x CORITIBA (R28)
proxima_rodada:
  adversario: "Coritiba"
  local: "São Januário (Rio de Janeiro/RJ)"
  data: "2026-09-19"
  horario: "20h30 (de Brasília)"
  mando: "Vasco"
  rodada: "28ª"
  transmissao: "Amazon Prime Video (exclusivo)"
  turno_ida: {placar: "Coritiba 1 x 1 Vasco", data: "2026-04-01", competicao: "Brasileirão R9"}
  desfalques_divulgados_antes_do_jogo:
    - {time: "Vasco", jogador: "Jair", motivo: "lesão (FotMob)"}
    - {time: "Coritiba", jogadores: ["Tinga", "Maicon", "Keno", "Pedro Morisco", "Rodrigo Rodrigues"], motivo: "lesão (FotMob)"}

# RODADA 28 COMPLETA (19-20/09/2026) - CBF
rodada_28_completa:
  - {data: "19/09 16h", jogo: "Atlético-MG x Chapecoense", local: "Arena MRV (Belo Horizonte)"}
  - {data: "19/09 17h", jogo: "Mirassol x Botafogo", local: "Maião (Mirassol)"}
  - {data: "19/09 18h30", jogo: "Remo x Santos", local: "Mangueirão (Belém)"}
  - {data: "19/09 20h30", jogo: "Vasco x Coritiba", local: "São Januário (Rio de Janeiro)"}
  - {data: "19/09 21h", jogo: "São Paulo x Internacional", local: "Morumbis (São Paulo)"}
  - {data: "20/09 11h", jogo: "Grêmio x Palmeiras", local: "Arena do Grêmio (Porto Alegre)"}
  - {data: "20/09 16h", jogo: "Corinthians x Fluminense", local: "Neo Química Arena (São Paulo)"}
  - {data: "20/09 16h", jogo: "Vitória x Cruzeiro", local: "Barradão (Salvador)"}
  - {data: "20/09 18h30", jogo: "Flamengo x Bragantino", local: "Maracanã (Rio de Janeiro)"}
  - {data: "20/09 19h30", jogo: "Athletico-PR x Bahia", local: "Arena da Baixada (Curitiba)"}

# CONFRONTOS DA R28 PARA RIVAIS DO Z4
confrontos_28_rivais:
  gremio: {adversario: "Palmeiras", local: "Arena do Grêmio", data: "2026-09-20", horario: "11h", mando: "casa"}
  mirassol: {adversario: "Botafogo", local: "Maião", data: "2026-09-19", horario: "17h", mando: "casa"}
  internacional: {adversario: "São Paulo", local: "Morumbis", data: "2026-09-19", horario: "21h", mando: "fora"}
  remo: {adversario: "Santos", local: "Mangueirão", data: "2026-09-19", horario: "18h30", mando: "casa"}
  chapecoense: {adversario: "Atlético-MG", local: "Arena MRV", data: "2026-09-19", horario: "16h", mando: "fora"}

# JOGOS ATRASADOS PENDENTES
jogos_atrasados:
  - {jogo: "Botafogo x Grêmio", rodada: "21ª", situacao: "JOGADO 16/09: Botafogo 3 x 2 Grêmio (confirmado pelo usuário 17/09)"}
  - {jogo: "Chapecoense x Vasco", rodada: "21ª", situacao: "sem data definida"}
  - {jogo: "São Paulo x Santos", rodada: "21ª", situacao: "sem data definida"}
  - {jogo: "Atlético-MG x Bragantino", rodada: "21ª", situacao: "sem data definida"}

# ESTATÍSTICAS DA PARTIDA GREMIO 1 x 2 VASCO (R27)
estatisticas_27:
  posse_casa_pct: "51"
  posse_fora_pct: "49"
  finalizacoes_totais: "14 x 17"
  finalizacoes_alvo: "4 x 5"
  escanteios: "3 x 5"
  passes_totais: "484 x 463"
  xg_casa: "0.88"
  xg_fora: "1.77"
  chutes_dentro_area: "7 x 12"
  chutes_fora_area: "7 x 5"
  defesas_goleiro: "3 x 3"
  cartoes_amarelos_estat: "3 x 3"

# JOGOS RESTANTES DO VASCO - BRASILEIRÃO 2026
jogos_restantes_vasco:
  - {rodada: 28, data: "2026-09-19", jogo: "Vasco x Coritiba", local: "São Januário", horario: "20h30"}
  - {rodada: 29, data: "2026-10-07", jogo: "Botafogo x Vasco", local: "Nilton Santos (Engenhão)", horario: "20h30"}
  - {rodada: 30, data: "2026-10-10", jogo: "Vasco x Remo", local: "São Januário", horario: "17h"}
  - {rodada: 31, data: "2026-10-17", jogo: "São Paulo x Vasco", local: "a definir", horario: "a definir"}
  - {rodada: 32, data: "2026-10-24", jogo: "Vasco x Corinthians", local: "a definir", horario: "a definir"}
  - {rodada: 33, data: "2026-10-28", jogo: "Vasco x Flamengo", local: "a definir", horario: "a definir"}
  - {rodada: 34, data: "2026-11-04", jogo: "Athletico-PR x Vasco", local: "a definir", horario: "a definir"}
  - {rodada: 35, data: "2026-11-18", jogo: "Vasco x Internacional", local: "a definir", horario: "a definir"}
  - {rodada: 36, data: "2026-11-22", jogo: "Bragantino x Vasco", local: "a definir", horario: "a definir"}
  - {rodada: 37, data: "2026-11-29", jogo: "Atlético-MG x Vasco", local: "a definir", horario: "a definir"}
  - {rodada: 38, data: "2026-12-02", jogo: "Vasco x Vitória", local: "a definir", horario: "a definir"}
  - {atrasado: "21ª", data: "a definir", jogo: "Chapecoense x Vasco", local: "a definir"}

# PROBABILIDADES DE REBAIXAMENTO / LINHA DE PERMANÊNCIA (MODELOS - referência R26 em imprensa)
probabilidades_rebaixamento:
  ufmg_apos_r26:
    - {time: "Vasco", risco_queda_pct: 59.5}
    - {time: "Chapecoense", risco_queda_pct: 97.4}
    - {time: "Remo", risco_queda_pct: 83.6}
    - {time: "Internacional", risco_queda_pct: 73.1}
    - {time: "Mirassol", risco_queda_pct: 25.6}
    - {time: "Grêmio", risco_queda_pct: 20.5}
  valorfinal_apos_r26:
    - {time: "Vasco", risco_queda_pct: 58, projecao_posicao: "17º", projecao_pontos: 41}
    - {time: "Chapecoense", risco_queda_pct: 99, projecao_pontos: 31}
    - {time: "Remo", risco_queda_pct: 83, projecao_pontos: 38}
    - {time: "Internacional", risco_queda_pct: 65, projecao_pontos: 40}
    - {time: "Mirassol", risco_queda_pct: 35, projecao_pontos: 43}
    - {time: "Grêmio", risco_queda_pct: 28, projecao_pontos: 44}
  linha_permanencia:
    - "16º colocado termina com 43 pts (intervalo típico 40-45); 1º rebaixado com 41 pts (ValorFinal)"
    - "44 pts = risco de queda 9,2%; 45 pts = 2,5%; <1% a partir de 46 pts"
  probabilidades_partida_r28:
    - {fonte: "CartolaNews (17/09/2026)", casa_vasco_pct: 26.37, empate_pct: 34.39, fora_coritiba_pct: 39.24}
    - {fonte: "Beira do Campo", casa_vasco_pct: 32, empate_pct: 25, fora_coritiba_pct: 43, placar_mais_provavel: "1-1"}

# FONTES
fontes:
  - {dado: "resultado_27", fonte: "CBF - Súmula Online (via NetVasco)", url: "https://www.netvasco.com.br", acesso: "2026-09-17", confianca: "alta"}
  - {dado: "tabela_atual", fonte: "exa.ai Brasileirão Standings", url: "https://exa.ai/library/sports/brasileirao/standings", acesso: "2026-09-17", confianca: "media"}
  - {dado: "rodada 28 completa", fonte: "ge.globo.com (CBF datas/horários)", url: "https://ge.globo.com", acesso: "2026-09-17", confianca: "alta"}
  - {dado: "probabilidades partida R28", fonte: "CartolaNews", url: "https://cartolanews.com.br/analise-rodada-28-brasileirao/", acesso: "2026-09-17", confianca: "media"}
  - {dado: "jogos_restantes_vasco", fonte: "LANCE! + Itatiaia + ESPN", url: "https://www.lance.com.br/vasco/proximos-jogos-do-vasco-veja-calendario-datas-e-horarios-das-partidas.html", acesso: "2026-09-17", confianca: "alta"}
  - {dado: "probabilidades queda", fonte: "UFMG (após R26 via Lance!/Folha do Leste) + ValorFinal", url: "https://www.mat.ufmg.br/futebol/rebaixamento_seriea/", acesso: "2026-09-17", confianca: "media"}

# NOTAS DE DIVERGÊNCIA ENTRE FONTES
notas:
  - "Posse de bola R27: SuperVasco/OFStats 51% (Grêmio) x 49% (Vasco); FOX Sports 49% x 51%. Divergência não reconciliada (usado SuperVasco)."
  - "xG R27: FOX Opta Grêmio 0.88 x Vasco 1.77 (fonte única)."
  - "UFMG página oficial traz Vasco 10,3% (rodada de referência não informada); imprensa divulgou 59,5-60,4% após R26. Usado valor divulgado pós-R26."
  - "Mirassol subiu para 15º após R27 (29 pts); Grêmio 16º (28 pts) após atrasado de 16/09 (Botafogo 3x2 Grêmio, confirmado pelo usuário)."