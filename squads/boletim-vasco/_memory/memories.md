# Squad Memory: Boletim Vasco

## Estilo de Escrita

- Verbatim do usuário: "Analítico e seco". Números com benchmark; seção encerra com implicação prática literal ("Implicação prática: ...").

## Design Visual

## Estrutura de Conteúdo

- Prévia por cenários segue as mesmas 5 seções do boletim pós-jogo; a seção "Prévia da próxima rodada" ganha subseção "Cenários de saída do Z4" (tabela cenário/resultado/condições alheias/fora do Z4).

## Proibições Explícitas

## Técnico (específico do squad)

- Saída do Z4 exige ancorar nos critérios CBF: pontos → vitórias → saldo → gols pró. Na posição disputável, o desempate (SG -12) joga contra o Vasco.
- PBIX não é compilável por CLI (formato proprietário Power BI Desktop). Pipeline gera PDF + XLSX + PBIT (fonte única); o PBIT é aberto no Power BI Desktop, clica-se em Atualizar e salva-se como .pbix. Power BI Desktop instalado em C:\Program Files\Microsoft Power BI Desktop\bin\PBIDesktop.exe (v). pbi-tools 1.2.0 instalado via download GitHub (pbi-tools.core.exe, .NET 9 runtime) — não é dotnet tool do NuGet.
- Geração do PBIT (validado): projeto PbixProj V3 (compat 1550, defaultPowerBIDataSourceVersion powerBI_V3) em pasta com Model/database.json + Model/queries/{Tabela}.m (queries viram partições M automaticamente) + Model/tables/{Tabela}/columns + Report/sections/{ordinal}_{nome}/visualContainers (textbox/table) + Report/config.json + Report/report.json + ReportMetadata.json + ReportSettings.json + Version.txt (1.25) + DiagramLayout.json + .pbixproj.json + StaticResources/SharedResources/BaseThemes/CY19SU12.json. Compilar: `pbi-tools.core.exe compile <pasta> <out>.pbit PBIT True`. PBIX compile só suporta "thin reports"; modelo de dados só compila para PBIT.
- XLSX do squad tem 6 abas quando há execução por cenários (Resumo, Tabela, Rodada, Estatísticas, Prévia, Cenários) — a aba Cenários é condicional.
- Ritmo de permanência na reta final: linha ~44 pts ≈ 1,33 pts/jogo em 12 jogos; modelo ValorFinal: 44 pts = risco 9,2%.
- Dados do PBIT são embutidos como literais `#table(...)` nas queries M (dados das 6 abas do XLSX) — nenhuma credencial/externa necessária no refresh; resultado confirmado Botafogo 3x2 Grêmio (16/09) registrado em dados-rodada.md.