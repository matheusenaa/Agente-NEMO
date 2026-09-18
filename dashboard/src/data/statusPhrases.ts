/** Frases de status rotativas dos agentes (português do Brasil). */

export const STATUS_LABELS: string[] = [
  "🟢 Online",
  "🧠 Pensando...",
  "🔎 Investigando...",
  "📂 Lendo arquivos...",
  "💻 Codificando...",
  "🧪 Testando...",
  "🐛 Caçando bugs...",
  "🚀 Executando...",
  "☕ Trabalhando...",
  "😎 Tudo sob controle",
  "🤨 Isso aqui está estranho...",
  "😂 Eu achei o problema",
  "🔥 Quase lá",
  "🎯 Resolvido",
];

/** Frases engraçadas rotativas mostradas durante trabalho pesado. */
export const FUNNY_PHRASES: string[] = [
  "Caçando aquele bug que jurou que não existia.",
  "Calma, estou investigando.",
  "Se funcionar de primeira, desconfie.",
  "Estou conversando com o código.",
  "Esse erro acabou de ficar pessoal.",
  "Não mexe em nada. Estou testando.",
  "Quase terminando... provavelmente.",
  "Encontrando problemas antes que eles encontrem você.",
  "Rodando testes para evitar aquela famosa surpresa.",
  "Já vi esse filme. Era uma dependência.",
  "NEMO mergulhou no código.",
  "Descendo mais fundo no problema...",
  "São Januário aprovaria esse código. 😎",
  "Respira, o problema já está mapeado.",
  "Duplicatas hoje, paz de espírito amanhã.",
  "Deixa eu perguntar pro dado quem está certo.",
  "Testando sem pressa para não ter desgaste depois.",
  "O código até reclama, mas você não vê.",
  "Estou fazendo a engrenagem girar bonito.",
  "Consertando isso com um toque de estilo.",
  "Vasco tá em primeiro? Então tá tudo certo. 🔵⚪",
  "Otimizando para você não perder tempo.",
  "Separando o sinal do ruído.",
  "Validando números — não invento nada.",
  "Investigando a causa raiz, não os sintomas.",
  "Dando uma turbinada nessa análise.",
  "Quase lá — só conferindo os detalhes.",
  "Em terra de dados duplicados, quem tem método é... eu.",
];

export function pickPhrase(pool: string[], avoid?: string): string {
  const candidates = pool.filter((p) => p !== avoid);
  return candidates[Math.floor(Math.random() * candidates.length)];
}