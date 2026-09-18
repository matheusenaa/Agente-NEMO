/* NEMO IDE — motor de demonstração compartilhado dos protótipos.
   Cria o enredo de 10 passos com estado interno e atualiza o DOM
   dos elementos identificados por data-attributes no HTML. */

window.NEMODemo = (function () {
  const STATUSES = [
    "🟢 Online", "🧠 Pensando...", "🔎 Investigando...", "📂 Lendo arquivos...",
    "💻 Codificando...", "🧪 Testando...", "🚀 Executando...", "☕ Trabalhando...",
    "😎 Tudo sob controle", "🤨 Isso aqui está estranho...", "😂 Eu achei o problema", "🔥 Quase lá",
  ];
  const FUNNY = [
    "Caçando aquele bug que jurou que não existia.",
    "Calma, estou investigando.",
    "Já vi esse filme. Era uma dependência.",
    "Estou conversando com o código…",
    "Encontrando problemas antes que eles encontrem você.",
    "NEMO mergulhou no código.",
    "São Januário aprovaria esse código. 😎",
    "Descendo mais fundo no problema...",
  ];

  const scenario = [
    { t: 300,  act: "open" },
    { t: 1400, act: "greet" },
    { t: 3200, act: "type" },
    { t: 5200, act: "think" },
    { t: 7000, act: "investigate" },
    { t: 9000, act: "reply" },
    { t: 11800, act: "delegate" },
    { t: 13600, act: "file" },
    { t: 15600, act: "done" },
    { t: 17600, act: "summary" },
  ];

  let timers = [];
  let phase = 0;

  function clear() {
    timers.forEach(clearTimeout);
    timers = [];
  }

  function at(ms, fn) { timers.push(setTimeout(fn, ms)); }

  function start() {
    clear();
    document.body.classList.add("running");
    phase = 0;
    scenario.forEach((s) => at(s.t, () => (phase = dispatch(s.act))));
  }

  /* Elementos padrão usados pelos protótipos via data-demo="..." */
  function el(name) { return document.querySelector('[data-demo="' + name + '"]'); }
  function html(name, val) { const e = el(name); if (e) e.innerHTML = val; return e; }

  function pushEnable(name) {
    const e = el(name);
    if (e && e.classList.contains("demo-off")) e.classList.remove("demo-off");
  }

  const MSG_NEMO_START =
    'Bom dia! 👋 Sou o <b>NEMO</b>, coordenador da sua equipe de agentes. ' +
    'Quer analisar dados, montar um relatório ou resolver algo na IDE?';
  const USER_MSG = 'Analise a planilha de gastos de setembro e encontre duplicados.';
  const REPLY_TEXT =
    '<div class="status"><span class="dot work"></span><span>Analisando a planilha…</span><span class="phrase">"Caçando duplicados antes que eles se multipliquem."</span></div>' +
    '<div style="margin-top:8px">Encontrei <b>1 duplicata</b> na linha 12 (pedágio R$ 18,00 lançado 2x) e um total superestimado em <b>R$ 18,00</b>. Corrigindo…</div>';

  function dispatch(act) {
    switch (act) {
      case "open": {
        const a = el("app");
        if (a) a.classList.add("open");
        break;
      }
      case "greet": {
        const a = el("app");
        if (a) a.classList.add("open");
        pushEnable("msgA"); if (el("whoA")) html("whoA", "🐟 NEMO") ;
        pushEnable("msgB-0");
        const sel = el("agentItem"); if (sel) sel.classList.add("sel");
        const st = el("agentStatus"); if (st) { st.classList.add("on"); st.textContent = "🟢 Online"; }
        break;
      }
      case "type": {
        const inp = el("input");
        if (inp) { let i = 0; const iv = setInterval(() => { i++; inp.textContent = USER_MSG.slice(0, i); if (i >= USER_MSG.length) clearInterval(iv); }, 28); timers.push({ cancel: () => clearInterval(iv) }); }
        break;
      }
      case "think": {
        const inp = el("input"); if (inp) inp.textContent = USER_MSG;
        pushEnable("msgU"); if (el("whoU")) html("whoU", "Você");
        const st = el("agentStatus"); if (st) { st.classList.remove("on"); st.className = "dot work"; st.textContent = "🧠 Pensando..."; }
        const w = el("working"); if (w) w.classList.add("show");
        break;
      }
      case "investigate": {
        const st = el("agentStatus"); if (st) { st.textContent = "🔎 Investigando..."; }
        const ph = el("phrase"); if (ph) ph.textContent = FUNNY[5];
        pushEnable("msgB-1");
        break;
      }
      case "reply": {
        const w = el("working"); if (w) w.classList.remove("show");
        pushEnable("msgB-2");
        const st = el("agentStatus"); if (st) { st.textContent = "💻 Codificando..."; }
        break;
      }
      case "delegate": {
        const st = el("agentStatus"); if (st) { st.textContent = "🤝 Delegando para 📊 DATA"; }
        const agent2 = el("agent2"); if (agent2) { agent2.classList.add("sel"); }
        const st2 = el("agent2Status"); if (st2) { st2.classList.add("work"); st2.textContent = "Processando..."; }
        break;
      }
      case "file": {
        const f = el("fileView"); if (f) f.classList.add("show");
        const fb = el("fileBar"); if (fb) { fb.classList.add("show"); }
        break;
      }
      case "done": {
        const t = el("toast"); if (t) t.classList.add("show");
        const st = el("agentStatus"); if (st) st.textContent = "✅ Tarefa concluída";
        const st2 = el("agent2Status"); if (st2) { st2.classList.remove("work"); st2.textContent = "✅ Pronto"; }
        const ck = el("checkRow"); if (ck) ck.classList.add("show");
        break;
      }
      case "summary": {
        pushEnable("msgB-3");
        const ta = el("tasksCheck");
        if (ta) { ta.innerHTML = 'Tasks <span class="badge act">2/2 ✓</span>'; }
        break;
      }
    }
    return phase;
  }

  return { start, clear };
})();

document.addEventListener("DOMContentLoaded", function () {
  setTimeout(() => window.NEMODemo.start(), 250);
});