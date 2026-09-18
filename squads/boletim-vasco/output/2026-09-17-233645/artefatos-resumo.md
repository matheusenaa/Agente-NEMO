# Artefatos — 28ª Rodada (prévia, 2026-09-17)

## Artefatos gerados

- boletim-vasco-2026-28-2026-09-17.pdf (5 seções renderizadas + tabela de cenários)
- vascobrasileirao-2026-28-2026-09-17.xlsx (abas: Resumo, Tabela, Rodada, Estatísticas, Prévia, Cenários)
- vasco-dashboard-2026-28-2026-09-17.pbit (Power BI template — modelo completo com as 6 abas embutidas como queries M + relatório 3 páginas) → GERADO via pbi-tools 1.2.0 (compile do projeto PbixProj). Para obter o .pbix: abrir no Power BI Desktop → Atualizar → Salvar como → .pbix (dados são literais #table, sem credenciais).

## Conferência de paridade (spot-check PDF x XLSX)

| Métrica | PDF | XLSX | OK |
| PTS | 28 | 28 | ✅ |
| SG | -12 | -12 | ✅ |
| Posição | 17º | 17º | ✅ |
| Aproveitamento | 35,9% | 35,9% | ✅ |
| xG R27 | 0,88 x 1,77 | 0,88 x 1,77 | ✅ |

## PBIX — medidas sugeridas (camadas)

- Base: [PTS], [Jogos], [Vitorias], [SaldoGols]
- Negócio: [AproveitamentoPct] = DIVIDE([PTS],[Jogos]*3), [PontosPorJogo] = DIVIDE([PTS],[Jogos]), [XgDiferencial] = [XgFora]-[XgCasa]
- Time Intelligence: [VariacaoPosicao], [SeqResultados], [PontosUltimasN] = CALCULATE(SUM('Rodada'[PTS]), LASTN(6,'Rodada'[Rodada]))

## Nota de divergência de formato PBIX
- PBIX não versiona via texto; o squad mantém o padrão de nome vasco-dashboard-{rodada}-{YYYY-MM-DD}.pbix para quando montado no Desktop.