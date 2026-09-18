```yaml
rodada: "28"
data: "2026-09-17"
contexto: "prévia por cenários (jogo não disputado)"
campeonato: "Brasileirão Série A 2026"

# ---------------------------------------------------------------
# RESULTADO RODADA 27 (já disputado)
# ---------------------------------------------------------------
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

# ---------------------------------------------------------------
# TABELA APÓS A RODADA 27 (20 posições)
# ---------------------------------------------------------------
# FONTE PRIMÁRIA: exa.ai/standings (publicação 18/09/2026, acesso 17/09/2026).
# Estrutura de posições confirmada por PIRANOT, PORTALRONDONIA, DIÁRIO DO PEIXE.
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

# ---------------------------------------------------------------
# DIVERGÊNCIAS DE TABELA ENTRE FONTES (não ocultadas)
# ---------------------------------------------------------------
divergencias_tabela:
  - {fonte: "piranot/Football-Data.org + portalrondonia (publicação 14/09/2026, ANTES do encerramento da R27: Bahia x Remo ainda não jogado e antes do atrasado Botafogo x Grêmio de 16/09)", notas: ["Bahia 43 pts / 26j (11V 10E 5D) - após vitória 2x1 sobre o Remo (14/09) soma 46 pts / 27j", "Grêmio 28 pts / 26j, GP 28 GC 35 (SG -7) - exa.ai traz 27j, GP 30 GC 38 (SG -8)", "Botafogo 32 pts / 26j (8V 8E 10D) - exa.ai traz 35 pts / 27j (9V 8E 10D)"]}
  - {fonte: "LANCE! (tabela/brasileirao) e ESPN (classificacao)", notas: "amostras desatualizadas/mistas (LANCE: Flamengo 54/26j e Palmeiras 56/27j em 1º; ESPN: snapshot ~R25 com jogos=25) - não usadas como fonte primária"}
  - {fonte: "golsstats.com.br", notas: "lista São Paulo x Internacional (R28) como domingo 20/09 - conflita com CBF/ge/gazeta/cartolanews (sábado 19/09, 21h); usada data da CBF", confianca: "baixa"}
  - {fonte: "veto/qualidade", confianca: "média", notas: "GP/GC das faixas intermediárias (12º-16º) divergem entre fontes; posições/PTS/SG do bloco Z4 (Vasco, Internacional, Remo, Chapecoense) e topo (Flamengo 57, Palmeiras 56, Athletico 46, Bahia/Fluminense 45-46) são consistentes em 3+ fontes"}

# ---------------------------------------------------------------
# RESULTADOS DA RODADA 27 (referência)
# ---------------------------------------------------------------
resultados_27:
  - {jogo: "Coritiba 3 x 3 Athletico-PR", local: "Couto Pereira"}
  - {jogo: "Atlético-MG 3 x 1 Fluminense", local: "Arena MRV"}
  - {jogo: "Grêmio 1 x 2 Vasco", local: "Arena do Grêmio"}
  - {jogo: "Chapecoense 1 x 2 Internacional", local: "Arena Condá"}
  - {jogo: "Palmeiras 2 x 0 São Paulo", local: "Allianz Parque"}
  - {jogo: "Botafogo 1 x 1 Bragantino", local: "Nilton Santos"}
  - {jogo: "Santos 2 x 1 Cruzeiro", local: "Vila Belmiro"}
  - {jogo: "Mirassol 2 x 2 Vitória", local: "Maião"}
  - {jogo: "Flamengo 2 x 1 Corinthians", local: "Maracanã"}
  - {jogo: "Bahia 2 x 1 Remo", local: "Arena Fonte Nova"}

# ---------------------------------------------------------------
# POSIÇÃO DO VASCO (confirmada por piranot, portalrondonia, exa.ai)
# ---------------------------------------------------------------
posicao_vasco: {posicao: 17, pts: 28, jogos: 26, sg: -12, aproveitamento: 35.9}

# ---------------------------------------------------------------
# SEQUÊNCIA DE RESULTADOS DO VASCO
# ---------------------------------------------------------------
sequencia_vasco: ["D", "D", "V", "D", "V"]   # últimos 5 (R23-R27, cronológica - portalrondonia)
ultimos_jogos:
  - {rodada: 17, data: "2026-05-24", jogo: "Vasco 0 x 3 Bragantino", resultado: "D"}
  - {rodada: 18, data: "2026-05-31", jogo: "Vasco 0 x 1 Atlético-MG", resultado: "D"}
  - {rodada: 19, data: "2026-07-16", jogo: "Vitória 1 x 0 Vasco", resultado: "D"}
  - {rodada: 20, data: "2026-07-25", jogo: "Vasco 1 x 1 Mirassol", resultado: "E"}
  - {rodada: 21, data: "29/30-07-2026", jogo: "Chapecoense x Vasco - ADIADO (sem data)", resultado: "-"}
  - {rodada: 22, data: "2026-08-09", jogo: "Bahia 0 x 0 Vasco", resultado: "E"}
  - {rodada: 23, data: "2026-08-16", jogo: "Vasco 0 x 3 Santos", resultado: "D"}
  - {rodada: 24, data: "2026-08-23", jogo: "Palmeiras 4 x 1 Vasco", resultado: "D"}
  - {rodada: 25, data: "2026-08-29", jogo: "Vasco 3 x 1 Cruzeiro", resultado: "V"}
  - {rodada: 26, data: "2026-09-05", jogo: "Fluminense 1 x 0 Vasco", resultado: "D"}
  - {rodada: 27, data: "2026-09-12", jogo: "Grêmio 1 x 2 Vasco", resultado: "V"}
sequencia_historica_destaques:
  - "8 rodadas seguidas sem vitória (R16-R23, até R24/ESPN); última vitória antes da R25 havia sido na R15 (10/05, 1x0 Athletico-PR em São Januário, O Globo)"
  - "Vitória da R27 foi a 1ª do Vasco como visitante no Brasileirão desde 26/10/2025 (1x2 sobre Bragantino) e 1ª sobre o Grêmio em Porto Alegre em 20 anos (Estadão/SBT)"

# ---------------------------------------------------------------
# PRÓXIMA RODADA - VASCO x CORITIBA (R28)
# ---------------------------------------------------------------
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

# ---------------------------------------------------------------
# RODADA 28 COMPLETA (19-20/09/2026) - CBF
# ---------------------------------------------------------------
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

# ---------------------------------------------------------------
# CONFRONTOS DA R28 PARA RIVAIS DO Z4
# ---------------------------------------------------------------
confrontos_28_rivais:
  gremio: {adversario: "Palmeiras", local: "Arena do Grêmio (Porto Alegre)", data: "2026-09-20", horario: "11h", mando: "casa"}
  mirassol: {adversario: "Botafogo", local: "Maião (Mirassol)", data: "2026-09-19", horario: "17h", mando: "casa"}
  internacional: {adversario: "São Paulo", local: "Morumbis (São Paulo)", data: "2026-09-19", horario: "21h", mando: "fora"}
  remo: {adversario: "Santos", local: "Mangueirão (Belém)", data: "2026-09-19", horario: "18h30", mando: "casa"}
  chapecoense: {adversario: "Atlético-MG", local: "Arena MRV (Belo Horizonte)", data: "2026-09-19", horario: "16h", mando: "fora"}

# ---------------------------------------------------------------
# JOGOS ATRASADOS PENDENTES (UOL, 02/09/2026; situação mantida)
# ---------------------------------------------------------------
jogos_atrasados:
  - {jogo: "Chapecoense x Vasco", rodada: "21ª", situacao: "sem data definida", motivo: "jogo de volta dos playoffs da Sul-Americana (29/07)"}
  - {jogo: "São Paulo x Santos", rodada: "21ª", situacao: "sem data definida"}
  - {jogo: "Atlético-MG x Bragantino", rodada: "21ª", situacao: "sem data definida"}
  - {jogo: "Botafogo x Grêmio", rodada: "21ª", situacao: "agendado para 16/09/2026, 19h30, Nilton Santos (UOL/Correio do Povo) - placar não confirmado nas fontes consultadas"}

# ---------------------------------------------------------------
# ESTATÍSTICAS DA PARTIDA GREMIO 1 X 2 VASCO (R27)
# ---------------------------------------------------------------
estatisticas_27:
  # Fonte A - SuperVasco / OFStats
  posse_casa_pct: "51"
  posse_fora_pct: "49"
  finalizacoes_totais: "14 x 17"
  finalizacoes_alvo: "4 x 5"
  escanteios: "3 x 5"
  passes_totais: "484 x 463"
  passes_certos: "396 x 387"
  faltas: "10 x 14"
  impedimentos: "0 x 1"
  # Fonte B - FOX Sports (boxscore FOX Opta)
  xg_casa: "0.88"
  xg_fora: "1.77"
  posse_casa_fox_pct: "49"
  posse_fora_fox_pct: "51"
  finalizacoes_totais_fox: "13 x 20"
  finalizacoes_alvo_fox: "não informado x 6"
  # DIVERGÊNCIA de posse/chutes entre SuperVasco/OFStats (51%-49%; 14x17) e FOX Sports (49%-51%; 13x20) - ambas listadas
  chutes_dentro_area: "7 x 12"
  chutes_fora_area: "7 x 5"
  defesas_goleiro: "3 x 3"
  cartoes_amarelos_estat: "3 x 3"

# ---------------------------------------------------------------
# JOGOS RESTANTES DO VASCO - BRASILEIRÃO 2026
# ---------------------------------------------------------------
# Bases: LANCE!, Itatiaia (tabela completa CBF), ESPN (calendário времени), brasilemfolhas (R27-R30)
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
outras_competicoes_atual:
  - "Copa do Brasil: eliminado (quartas de final vs Vitória, jogos 28/08 ida 1x0 e 02/09 volta - eliminado; Trafermarkt): total 2 jogos em 2026 (1V 1E)"
  - "Copa Sul-Americana 2026: ativo - semifinal vs Santa Fe (Estadão), século com sequência internacional no meio de semana da R27/R28"

# ---------------------------------------------------------------
# PROBABILIDADES DE REBAIXAMENTO / LINHA DE PERMANÊNCIA (MODELOS)
# ---------------------------------------------------------------
probabilidades_rebaixamento:
  # FONTE: mat.ufmg.br, acesso 17/09/2026 - RODADA DE REFERÊNCIA NÃO INFORMADA NA PÁGINA (conflita com imprensa)
  ufmg_pagina_oficial:
    - {time: "Chapecoense", risco_pct: 82.7}
    - {time: "Remo", risco_pct: 59.3}
    - {time: "Mirassol", risco_pct: 51.8}
    - {time: "Grêmio", risco_pct: 27.7}
    - {time: "Atlético-MG", risco_pct: 23.0}
    - {time: "Santos", risco_pct: 21.2}
    - {time: "Internacional", risco_pct: 20.0}
    - {time: "Corinthians", risco_pct: 17.2}
    - {time: "Cruzeiro", risco_pct: 16.2}
    - {time: "Bragantino", risco_pct: 16.1}
    - {time: "Botafogo", risco_pct: 15.4}
    - {time: "Coritiba", risco_pct: 13.9}
    - {time: "Vitória", risco_pct: 11.1}
    - {time: "Vasco da Gama", risco_pct: 10.3}
    - {time: "Bahia", risco_pct: 5.1}
    - {time: "Athletico-PR", risco_pct: 4.9}
    - {time: "São Paulo", risco_pct: 3.4}
    - {time: "Fluminense", risco_pct: 0.91}
    - {time: "Flamengo", risco_pct: 0.035}
    - {time: "Palmeiras", risco_pct: 0.007}
  # CONFLITO EXPLÍCITO: página UFMG mostra Vasco 10.3%, PORÉM imprensa divulgou valores UFMG bem superiores
  ufmg_divulgado_pela_imprensa:
    - {fonte: "Lance! (07/09/2026, após R26)", valores: "Vasco 59,5%; Chapecoense 97,4%; Remo 83,6%; Internacional 73,1%; Mirassol 25,6%; Grêmio 20,5%"}
    - {fonte: "Folha do Leste (06/09/2026, após R26)", valores: "Vasco 60,4%"}
    - {fonte: "Exame (17/08/2026, após R23)", valores: "Vasco 63,8%; Chapecoense 99,38%; Remo 56,3%"}
  valorfinal_apos_r26:
    - {time: "Vasco", risco_queda_pct: 58, projecao_posicao: "17º", projecao_pontos: 41}
    - {time: "Chapecoense", risco_queda_pct: 99, projecao_pontos: 31}
    - {time: "Remo", risco_queda_pct: 83, projecao_pontos: 38}
    - {time: "Internacional", risco_queda_pct: 65, projecao_pontos: 40}
    - {time: "Mirassol", risco_queda_pct: 35, projecao_pontos: 43}
    - {time: "Grêmio", risco_queda_pct: 28, projecao_pontos: 44}
  linha_permanencia:
    - "Medianas do modelo ValorFinal: 16º colocado termina com 43 pts (intervalo típico 40-45); 1º rebaixado com 41 pts"
    - "Risco de queda por pontuação final (ValorFinal): 44 pts = 9,2%; 45 pts = 2,5%; risco <1% a partir de 46 pts"
  # MERCADO / MODELOS DE PROBABILIDADE DA PARTIDA VASCO x CORITIBA (R28) - cartolanews e Beira do Campo
  probabilidades_partida_r28:
    - {fonte: "CartolaNews (17/09/2026)", casa_vasco_pct: 26.37, empate_pct: 34.39, fora_coritiba_pct: 39.24}
    - {fonte: "Beira do Campo", casa_vasco_pct: 32, empate_pct: 25, fora_coritiba_pct: 43, placar_mais_provavel: "1-1"}

# ---------------------------------------------------------------
# FONTES
# ---------------------------------------------------------------
fontes:
  - {dado: "resultado_27 (placar, gols, arbitragem, público, renda)", fonte: "CBF - Súmula Online (via NetVasco PDF)", url: "https://www.netvasco.com.br/news/noticias16/arquivos/20260912-210147-1-.pdf", acesso: "2026-09-17", confianca: "alta"}
  - {dado: "resultado_27 (corroboração)", fonte: "Estadão", url: "https://www.estadao.com.br/esportes/futebol/vasco-vira-em-duelo-direto-contra-z-4-e-vence-o-gremio-em-porto-alegre-apos-20-anos/", acesso: "2026-09-17", confianca: "alta"}
  - {dado: "resultado_27 (corroboração, escalações, cartões)", fonte: "SBT Sports", url: "https://sports.sbt.com.br/noticia/sbt-sports/vasco-quebra-tabu-historico-vence-o-gremio-de-virada-e-respira-no-z4", acesso: "2026-09-17", confianca: "alta"}
  - {dado: "resultado_27 (corroboração, cartões reg adicionais)", fonte: "Gazeta Esportiva", url: "https://www.gazetaesportiva.com/campeonatos/brasileiro-serie-a/gremio-vasco-brasileirao-12-09-2026/", acesso: "2026-09-17", confianca: "alta"}
  - {dado: "resultado_27 (corroboração)", fonte: "CNN Brasil", url: "https://www.cnnbrasil.com.br/esportes/brasileirao/vasco-bate-gremio-de-virada-fora-de-casa-e-fica-perto-de-deixar-z4/", acesso: "2026-09-17", confianca: "alta"}
  - {dado: "resultado_27 (corroboração, atrasado Grêmio x Botafogo)", fonte: "Correio do Povo", url: "https://www.correiodopovo.com.br/esportes/gr%C3%AAmio/gremio-perde-de-virada-para-o-vasco-e-fica-proximo-do-z4-do-brasileirao-1.1747334", acesso: "2026-09-17", confianca: "alta"}
  - {dado: "tabela_atual (fluxo primário pós-R27)", fonte: "exa.ai Brasileirão Standings", url: "https://exa.ai/library/sports/brasileirao/standings", acesso: "2026-09-17", confianca: "média"}
  - {dado: "tabela (pré-encerramento R27, Football-Data.org)", fonte: "PIRANOT", url: "https://www.piranot.com.br/esporte/tabela-brasileirao-hoje-classificacao-27-rodada/", acesso: "2026-09-17", confianca: "média"}
  - {dado: "tabela + sequências (pré-encerramento R27)", fonte: "Portal Rondonia (rodada 27)", url: "https://futebol.portalrondonia.com/campeonato/campeonato-brasileiro/2026/rodada/27", acesso: "2026-09-17", confianca: "média"}
  - {dado: "tabela e Z4 pós-R27 (corroboração)", fonte: "Diário do Peixe", url: "https://www.diariodopeixe.com.br/noticias/confira-a-classificacao-apos-a-27a-rodada-do-brasileirao-2026/", acesso: "2026-09-17", confianca: "alta"}
  - {dado: "resultados_27 (completa)", fonte: "Diário do Peixe", url: "https://www.diariodopeixe.com.br/noticias/confira-a-classificacao-apos-a-27a-rodada-do-brasileirao-2026/", acesso: "2026-09-17", confianca: "alta"}
  - {dado: "rodada 28 completa (datas/horários CBF)", fonte: "ge.globo.com", url: "https://ge.globo.com/pr/futebol/brasileirao-serie-a/noticia/2026/08/31/cbf-detalha-datas-e-horarios-dos-jogos-das-rodadas-27-a-30-do-brasileirao-veja-a-tabela.ghtml", acesso: "2026-09-17", confianca: "alta"}
  - {dado: "rodada 28 completa (corroboração)", fonte: "Gazeta Esportiva", url: "https://www.gazetaesportiva.com/campeonatos/brasileiro-serie-a/cbf-divulga-tabela-detalhada-das-rodadas-27-a-30-do-brasileirao-veja-datas-e-jogos/", acesso: "2026-09-17", confianca: "alta"}
  - {dado: "rodada 28 + probabilidades (modelo CartolaNews)", fonte: "CartolaNews", url: "https://cartolanews.com.br/analise-rodada-28-brasileirao/", acesso: "2026-09-17", confianca: "média"}
  - {dado: "próxima rodada Vasco x Coritiba (19/09, São Januário, Amazon Prime)", fonte: "MKT Esportivo", url: "https://www.mktesportivo.com/2026/09/vasco-x-coritiba-onde-assistir-a-partida-da-28a-rodada-do-brasileirao/", acesso: "2026-09-17", confianca: "alta"}
  - {dado: "Vasco x Coritiba (H2H, desfalques, horários)", fonte: "FotMob", url: "https://www.fotmob.com/matches/coritiba-vs-vasco-da-gama/3blkjt", acesso: "2026-09-17", confianca: "média"}
  - {dado: "Vasco x Coritiba (corroboração + placar mais provável)", fonte: "Beira do Campo", url: "https://beiradocampo.com.br/onde-assistir/vasco-da-gama-x-coritiba-2026-09-19", acesso: "2026-09-17", confianca: "média"}
  - {dado: "Vasco x Coritiba (corroboração)", fonte: "Gazeta Esportiva (minuto a minuto)", url: "https://www.gazetaesportiva.com/minuto-a-minuto/brasileiro-serie-a-2026/vasco-x-coritiba/237854/", acesso: "2026-09-17", confianca: "alta"}
  - {dado: "estatísticas R27 (posse, chutes, passes)", fonte: "SuperVasco", url: "https://www.supervasco.com/noticias/estatisticas-de-gremio-1-x-2-vasco-455726.html", acesso: "2026-09-17", confianca: "alta"}
  - {dado: "estatísticas R27 (xG, posse FOX)", fonte: "FOX Sports Boxscore", url: "https://www.foxsports.com/soccer/brazil-serie-a-gremio-vs-vasco-da-gama-sep-12-2026-game-boxscore-648329", acesso: "2026-09-17", confianca: "média"}
  - {dado: "estatísticas R27 (corroboração)", fonte: "OFStats", url: "https://ofstats.com/matches/view/gremio-vasco-da-gama-2026-09-12", acesso: "2026-09-17", confianca: "média"}
  - {dado: "estatísticas R27 (disponibilidade xG)", fonte: "Flashscore", url: "https://www.flashscore.com.br/jogo/futebol/gremio-E1EFmhVh/vasco-2RABlYFn/resumo/estatisticas/", acesso: "2026-09-17", confianca: "média"}
  - {dado: "sequencia_vasco R17-R27", fonte: "UOL + No Ataque + O Globo + NETVASCO + O Dia + ESPN + UOL/Flu (por rodada)", urls: ["https://noataque.com.br/futebol/brasileirao-serie-a/time/vasco/noticia/2026/05/24/no-rio-bragantino-faz-3-e-atropela-vasco-que-cola-no-z4-do-brasileiro/", "https://www.uol.com.br/esporte/futebol/ultimas-noticias/2026/05/31/vasco-atletico-mg-brasileirao-2026.ghtm", "https://www.uol.com.br/esporte/futebol/ultimas-noticias/2026/07/16/brasileirao-vitoria-x-vasco-19-rodada.ghtm", "https://oglobo.globo.com/esportes/futebol/vasco/noticia/2026/07/25/vasco-empata-com-o-mirassol-em-sao-januario-e-segue-na-zona-de-rebaixamento-do-brasileirao.ghtml", "https://www.cnnbrasil.com.br/esportes/brasileirao/vasco-e-bahia-empatam-pelo-brasileirao-em-jogo-de-gols-anulados-e-lesoes/", "https://www.netvasco.com.br/n/390534/vasco-perde-para-o-santos-em-sao-januario-e-segue-no-z4-3-a-0", "https://www.espn.com.br/futebol/brasileirao/artigo/_/id/17157658/palmeiras-acorda-segundo-tempo-vence-vasco-aumenta-vantagem-lideranca-brasileirao", "https://odia.ig.com.br/esporte/vasco/2026/08/7296650-vasco-vence-cruzeiro-em-sao-januario-e-dorme-fora-do-z4-do-brasileirao.html", "https://www.uol.com.br/esporte/futebol/ultimas-noticias/2026/09/05/fluminense-x-vasco---brasileirao-2026.ghtm"], acesso: "2026-09-17", confianca: "alta"}
  - {dado: "jogos_atrasados (R21: Chapecoense x Vasco, Botafogo x Grêmio etc.)", fonte: "UOL", url: "https://www.uol.com.br/esporte/futebol/ultimas-noticias/2026/09/02/jogos-atrasados-brasileirao.ghtm", acesso: "2026-09-17", confianca: "alta"}
  - {dado: "jogos_atrasados (contexto, R21)", fonte: "Beira do Campo", url: "https://beiradocampo.com.br/brasileirao-2026-jogos-atrasados-calendario-agosto", acesso: "2026-09-17", confianca: "média"}
  - {dado: "jogos_restantes_vasco (tabela completa)", fonte: "LANCE!", url: "https://www.lance.com.br/vasco/proximos-jogos-do-vasco-veja-calendario-datas-e-horarios-das-partidas.html", acesso: "2026-09-17", confianca: "alta"}
  - {dado: "jogos_restantes_vasco (corroboração R29)", fonte: "Itatiaia (tabela CBF)", url: "https://www.itatiaia.com.br/esportes/futebol/futebol-nacional/futebol-carioca/vasco/vasco-no-brasileirao-2026-cbf-divulga-tabela-com-todas-as-rodadas-veja-os-jogos/", acesso: "2026-09-17", confianca: "alta"}
  - {dado: "jogos_restantes_vasco (corroboração R28-R30)", fonte: "Brasil em Folhas", url: "https://www.brasilemfolhas.com.br/2026/09/cbf-divulga-datas-e-horarios-do-vasco-no-brasileirao/", acesso: "2026-09-17", confianca: "alta"}
  - {dado: "jogos_restantes_vasco (corroboração horários)", fonte: "ESPN (calendário Vasco)", url: "https://www.espn.com.br/futebol/time/calendario/_/id/3454/vasco-da-gama", acesso: "2026-09-17", confianca: "alta"}
  - {dado: "Copa do Brasil: eliminação nas quartas vs Vitória", fonte: "O Dia (jogo de ida 1x0) + SuperVasco/Trafermarkt (balanço 2 jogos)", url: "https://odia.ig.com.br/esporte/vasco/2026/08/7296650-vasco-vence-cruzeiro-em-sao-januario-e-dorme-fora-do-z4-do-brasileirao.html", acesso: "2026-09-17", confianca: "média"}
  - {dado: "probabilidade UFMG (página oficial)", fonte: "UFMG - Departamento de Matemática", url: "https://www.mat.ufmg.br/futebol/rebaixamento_seriea/", acesso: "2026-09-17", confianca: "baixa (rodada de referência não informada; conflita com imprensa)"}
  - {dado: "probabilidade UFMG divulgada (após R26)", fonte: "Lance!", url: "https://www.lance.com.br/futebol-nacional/vasco-aparece-entre-os-grandes-com-maior-risco-de-rebaixamento-no-brasileirao-veja-os-numeros.html", acesso: "2026-09-17", confianca: "média"}
  - {dado: "probabilidade UFMG divulgada (após R26)", fonte: "Folha do Leste", url: "https://folhadoleste.com.br/vasco-risco-rebaixamento-60-4-ufmg-brasileirao/", acesso: "2026-09-17", confianca: "média"}
  - {dado: "probabilidade UFMG divulgada (após R23)", fonte: "Exame", url: "https://exame.com/esporte/quem-vai-cair-no-brasileirao-2026-veja-a-probabilidade-de-rebaixamento-de-cada-time/", acesso: "2026-09-17", confianca: "média"}
  - {dado: "probabilidade + linha de permanência (modelo ValorFinal, após R26)", fonte: "ValorFinal", url: "https://valorfinal.com.br/brasileirao/vasco", acesso: "2026-09-17", confianca: "média"}
  - {dado: "probabilidade + linha de permanência (geral)", fonte: "ValorFinal", url: "https://valorfinal.com.br/brasileirao/chances-rebaixamento", acesso: "2026-09-17", confianca: "média"}
  - {dado: "resultado Vasco x Santos R23 (corroboração)", fonte: "FutVasco", url: "https://www.futvasco.com.br/jogo/vasco-da-gama-x-santos-16-08-2026-1", acesso: "2026-09-17", confianca: "alta"}
  - {dado: "resultado Fluminense x Vasco R26 (corroboração)", fonte: "Fluminense FC (site oficial)", url: "https://www.fluminense.com.br/noticia/fluminense-vence-o-vasco-no-maracana-com-gol-de-lucho-acosta-pelo-brasileirao", acesso: "2026-09-17", confianca: "alta"}

# ---------------------------------------------------------------
# NOTAS DE DIVERGÊNCIA ENTRE FONTES (detalhamento)
# ---------------------------------------------------------------
notas:
  - "Posse de bola R27: SuperVasco/OFStats 51% (Grêmio) x 49% (Vasco); FOX Sports 49% x 51%. Chutes totais: SuperVasco/OFStats 14 x 17; FOX 13 x 20. Divergência não reconciliada."
  - "xG R27 disponível apenas na FOX Sports (Opta): Grêmio 0.88 x Vasco 1.77."
  - "Horário do Grêmio x Vasco: CBF súmula e VEJA informam 16h; um metadado da Gazeta Esportiva informa 21h30. Usado 16h (fonte primária)."
  - "Cartões amarelos R27: SBT lista 3 por lado (Pedro Gabriel, Wallace / Tchê Tchê, Cuiabano, Robert Renan); Estadão adiciona Diego Caito (GRE). Divergência sinalizada."
  - "Atlético x Vasco (R37): Itatiaia lista 'Atlético x Vasco'; LANCE! lista 'Atlético-MG x Vasco'. Considerado Atlético-MG."
  - "UFMG página oficial (acesso 17/09) traz Vasco com 10,3% de risco, mas a imprensa divulgou 59,5-60,4% (UFMG) após a R26. A página UFMG não informa a rodada de referência; ambos os valores são listados sem ocultar o conflito."
  - "O de linha de permanência de 44 pts corresponde a risco de 9,2% no modelo ValorFinal (44 pts) - abaixo de 1% apenas a partir de 46 pts; mediana do 16º colocado = 43 pts."
  - "Vasco jogou 26 de 27 rodadas (uma a menos); jogo pendente: Chapecoense x Vasco (R21), sem data na data de acesso."
  - "Jogo atrasado Botafogo x Grêmio (R21) agendado para 16/09/2026 (UOL/Correio do Povo); placar do jogo não localizado nas fontes consultadas - a publicação exa.ai (18/09) já indica tabela com GRE/BOT em 27 jogos, sugerindo disputa em 16/09."
```