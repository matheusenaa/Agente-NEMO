/** Highlighter leve de sintaxe (read-only) para o editor/visualizador. */

const TOKENIZERS: Record<string, (src: string) => string> = {
  py: (s) =>
    s
      .replace(/(#.*)$/gm, `<span class="tok-c">$1</span>`)
      .replace(/\b(def|class|return|import|from|for|while|if|elif|else|try|except|with|as|in|not|and|or|lambda|None|True|False|yield|global|pass|break|continue)\b/g, `<span class="tok-k">$1</span>`)
      .replace(/\b([A-Za-z_]\w*)(?=\()/g, `<span class="tok-f">$1</span>`)
      .replace(/(".*?"|'.*?')/g, `<span class="tok-s">$1</span>`),
  ts: (s) =>
    s
      .replace(/(\/\/.*)$/gm, `<span class="tok-c">$1</span>`)
      .replace(/\b(export|import|from|const|let|var|function|return|if|else|for|while|interface|type|class|new|async|await|extends|implements|enum|switch|case|default|null|undefined|true|false)\b/g, `<span class="tok-k">$1</span>`)
      .replace(/\b([A-Za-z_$]\w*)(?=\()/g, `<span class="tok-f">$1</span>`)
      .replace(/(".*?"|'.*?'|`.*?`)/g, `<span class="tok-s">$1</span>`)
      .replace(/\b(\d+)\b/g, `<span class="tok-n">$1</span>`),
  js: (s) => TOKENIZERS.ts(s),
  json: (s) =>
    s
      .replace(/(".*?")(\s*:)/g, `<span class="tok-k">$1</span>$2`)
      .replace(/:\s*(".*?")/g, `: <span class="tok-s">$1</span>`)
      .replace(/\b(\d+)\b/g, `<span class="tok-n">$1</span>`)
      .replace(/\b(true|false|null)\b/g, `<span class="tok-t">$1</span>`),
  yaml: (s) =>
    s
      .replace(/(#.*)$/gm, `<span class="tok-c">$1</span>`)
      .replace(/^([A-Za-z_][\w-]*)(\s*:)/gm, `<span class="tok-k">$1</span>$2`)
      .replace(/(["'].*?["'])/g, `<span class="tok-s">$1</span>`)
      .replace(/-\s+([A-Za-z0-9_][\w.-]*)/g, `- <span class="tok-v">$1</span>`),
  css: (s) =>
    s
      .replace(/(\/\*.*?\*\/)/gs, `<span class="tok-c">$1</span>`)
      .replace(/([.#]?[A-Za-z_][\w-]*)\s*\{/g, `<span class="tok-t">$1</span> {`)
      .replace(/:([a-z-]+)([;])/gi, `:<span class="tok-n">$1</span>$2`)
      .replace(/(#[0-9a-fA-F]{3,8})/g, `<span class="tok-v">$1</span>`),
  html: (s) =>
    s
      .replace(/(&lt;!--.*?--&gt;)/gs, `<span class="tok-c">$1</span>`)
      .replace(/&lt;(\/?)\s*([A-Za-z][\w-]*)/g, `&lt;$1<span class="tok-t">$2</span>`)
      .replace(/([A-Za-z-]+)=&quot;(.*?)&quot;/g, `<span class="tok-f">$1</span>=&quot;<span class="tok-s">$2</span>&quot;`),
  sh: (s) =>
    s
      .replace(/(#.*)$/gm, `<span class="tok-c">$1</span>`)
      .replace(/^(\s*[$›]\s*)/gm, `<span class="tok-v">$1</span>`)
      .replace(/\b(cd|ls|dir|python|pip|npm|node|git|echo|cat|mkdir|rm|cp|mv|run|test)\b/g, `<span class="tok-k">$1</span>`),
  md: (s) =>
    s
      .replace(/(^#{1,6}\s.*$)/gm, `<span class="tok-k">$1</span>`)
      .replace(/(`.*?`)/g, `<span class="tok-s">$1</span>`),
};

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

const KNOWN: Record<string, string> = {
  "": "plain",
  plain: "plain",
  txt: "plain",
  text: "plain",
  md: "md",
  markdown: "md",
  py: "py",
  python: "py",
  ts: "ts",
  tsx: "ts",
  js: "js",
  jsx: "js",
  mjs: "js",
  json: "json",
  yaml: "yaml",
  yml: "yaml",
  css: "css",
  html: "html",
  htm: "html",
  xml: "html",
  sh: "sh",
  bash: "sh",
  ps1: "sh",
};

export function highlight(code: string, language: string): string {
  const esc = escapeHtml(code);
  const canonical = KNOWN[language] ?? "plain";
  const tokenizer = canonical === "plain" ? (x: string) => x : TOKENIZERS[canonical];
  try {
    return tokenizer(esc);
  } catch {
    return esc;
  }
}