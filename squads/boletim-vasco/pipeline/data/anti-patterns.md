# Anti-Patterns — Boletim Vasco

Erros comuns na geração de boletins esportivos analíticos e como o squad os evita.

## Nunca fazer (pesquisa)

1. **Fonte única sem validação**: dado sem segunda fonte polui o boletim com confiança falsa. Sempre corroborar (CBF + ge/ESPN).
2. **Dado sem data de acesso**: tabela muda a cada rodada — sem data, impossível reproduzir a análise.
3. **Inventar estatística**: qualquer número sem fonte verificável invalida o boletim inteiro.
4. **Confundir fato e opinião**: deixar interpretação entrar como dado coletado.

## Nunca fazer (análise)

1. **Métrica sem benchmark**: número solto ("80 passes", "0.5 xG") sem comparativo não orienta decisão.
2. **Variação sobre rodadas diferentes**: calcular variação de posição com tabelas de rodadas distintas quebra comparabilidade.
3. **Vanity metrics**: posse alta sem conversão em chances; números que impressionam mas não decidem.
4. **Correlação tratada como causalidade**: "posse alta causou a vitória" sem suporte de processo.

## Nunca fazer (redação)

1. **Citar número que não está nos dados consolidados**: erro fatal de credibilidade.
2. **Adjetivação emocional**: "épico", "sofrido", "foi azarado" — substitui dado por opinião.
3. **Previsão sem respaldo**: "vai cair" ou "vai ganhar" sem benchmark (linha de permanência, sequência).
4. **Boletim-relatório**: despejar tabelas sem narrativa que responda "so what?".

## Nunca fazer (entregas)

1. **Paridade quebrada entre entregas**: PDF, XLSX e PBIX com números divergentes — o dicionário único é a regra.
2. **Nome de arquivo sem rodada/data**: impossibilita rastrear versões entre rodadas.
3. **PBIX com dados crus sem medidas**: dashboard vira "visual dumping ground" sem valor analítico.
4. **Pizza/gauge/3D para comparar categoria**: humanos comparam melhor comprimentos — usar barras.

## Sempre fazer

1. **Contexto em toda métrica**: benchmark (média da liga, rodada anterior, linha de permanência) — número sem referência é ruído.
2. **Implicação prática em toda seção**: fechar com "o que isso muda na próxima rodada".
3. **Rastreabilidade**: fontes + acesso + confiança em todo dado; revisão numerada (N de 3) com escalação.