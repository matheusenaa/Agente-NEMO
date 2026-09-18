---
task: "Gerar Artefatos"
order: 1
input: |
  - boletim_rodada: markdown aprovado do boletim
  - xlsx: planilha consolidada do analista
  - output_examples: exemplo de entrega esperada
output: |
  - pdf: boletim renderizado
  - xlsx_final: planilha final padronizada
  - pbix: dashboard Power BI
---

# Gerar Artefatos

Compila os artefatos finais do boletim: PDF (Markdown renderizado), XLSX final e PBIX (Power BI), garantindo que os mesmos números apareçam nas 3 entregas.

## Process

1. Receber o boletim aprovado (Markdown) e o XLSX consolidado.
2. Renderizar o Markdown em PDF com nomenclatura `boletim-vasco-{rodada}-{YYYY-MM-DD}.pdf`.
3. Certificar o XLSX final (`vascobrasileirao-{rodada}-{data}.xlsx`) com as 5 abas padrão.
4. Montar o PBIX (`vasco-dashboard-{rodada}-{data}.pbix`) importando o XLSX: abas Rodada, Tabela, Histórico, Prévia; medidas em camadas (Base → Negócio → Time Intelligence).
5. Conferir paridade de números (spot-check PTS, SG, posição, aproveitamento) entre PDF/XLSX/PBIX.
6. Listar os artefatos gerados no resumo final.

## Output Format

```yaml
artefatos:
  pdf: "boletim-vasco-{rodada}-{YYYY-MM-DD}.pdf"
  xlsx: "vascobrasileirao-{rodada}-{YYYY-MM-DD}.xlsx"
  pbix: "vasco-dashboard-{rodada}-{YYYY-MM-DD}.pbix"
paridade:
  - {metrica: "PTS", pdf: 28, xlsx: 28, pbix: 28, ok: true}
  - {metrica: "SG", pdf: -12, xlsx: -12, pbix: -12, ok: true}
  - {metrica: "Aproveitamento", pdf: "35.9", xlsx: "35.9", pbix: "35.9", ok: true}
pbix_medidas:
  base: [PTS, Jogos, Vitorias, SaldoGols]
  negocio: [AproveitamentoPct, PontosPorJogo, XgDiferencial]
  time_intelligence: [VariacaoPosicao, SeqResultados, PontosUltimasN]
```

## Output Example

```yaml
artefatos:
  pdf: "boletim-vasco-2026-27-2026-09-12.pdf"
  xlsx: "vascobrasileirao-2026-27-2026-09-12.xlsx"
  pbix: "vasco-dashboard-2026-27-2026-09-12.pbix"
paridade:
  - {metrica: "PTS", pdf: 28, xlsx: 28, pbix: 28, ok: true}
  - {metrica: "SG", pdf: -12, xlsx: -12, pbix: -12, ok: true}
  - {metrica: "Posição", pdf: "17º", xlsx: "17º", pbix: "17º", ok: true}
  - {metrica: "Aproveitamento", pdf: "35.9", xlsx: "35.9", pbix: "35.9", ok: true}
pbix_medidas:
  base: [PTS, Jogos, Vitorias, SaldoGols]
  negocio: [AproveitamentoPct, PontosPorJogo, XgDiferencial]
  time_intelligence: [VariacaoPosicao, SeqResultados, PontosUltimasN]
```

## Quality Criteria

- [ ] PDF, XLSX e PBIX apresentam os mesmos números (paridade confirmada).
- [ ] PBIX contém medidas em camadas e abas por seção do boletim.
- [ ] Nomenclatura dos arquivos segue o padrão definido.
- [ ] XLSX consumível diretamente no Power BI.

## Veto Conditions

Reject and redo if ANY are true:
1. Paridade quebrada entre entregas — algum número divergente entre PDF/XLSX/PBIX.
2. Nome de arquivo sem rodada/data — impede rastreamento de versões.