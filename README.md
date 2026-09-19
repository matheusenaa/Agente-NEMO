# NEMO — IDE de Agentes de IA

**NEMO** é o seu **coordenador pessoal de agentes de IA** com identidade visual de **Vasco da Gama** 🔵⚪ (o time adversário não aparece 👀).

Ele orquestra uma equipe especializada de agentes (cada um com personalidade, modelo padrão no OpenRouter e fallbacks automáticos) construída **por você, para o seu trabalho real**: finanças, dados, pesquisa, redação, revisão, design, vídeo, redes sociais, SEO, publicação e TI (o JARVIS, engenheiro de software sênior).

> ✌️ Duas formas de uso (ambas funcionam juntas):
> - **Chat + Escritório 2D** no dashboard React (Phaser)
> - **Chat pela IDE/terminal** no backend FastAPI

---

## 🗺️ Visão geral

```
NEMO/
├── nemo_server.py              # Backend FastAPI (porta 8798) — chat, arquivos, terminal, snapshot
├── openrouter_client.py        # Cliente OpenRouter (chat, modelos, fallbacks)
├── models_config.py            # Configuração dos modelos com fallbacks
├── agents/*.agent.md           # Personas completas de cada agente
├── requirements.txt
├── .env.example
├── NEMO_IDE.spec               # Build do executável (PyInstaller one-folder)
├── start_nemo.bat              # Produção 1-clique (backend + dashboard compilado)
├── start_nemo_dev.bat          # Dev: backend (8798) + Vite HMR (5173)
├── test_client_unit.py         # Testes unitários do backend
└── dashboard/                  # Frontend — a IDE NEMO
    ├── index.html
    ├── vite.config.ts          # alias @ + proxy /api/nemo
    └── src/
        ├── main.tsx / App.tsx / AppShell.tsx
        ├── api/nemo.ts         # Cliente HTTP do backend
        ├── store/              # useIdeStore (zustand), store do quclube, squads
        ├── data/               # agentes, temas, status/frases, agentes config
        ├── hooks/              # useNemoChat, useSquadSocket, useSquads
        ├── office/             # Cena Phaser do escritório 2D
        ├── components/ide/     # AppShell, TopBar, AgentSidebar, ChatView,
        │                       #   CodeEditor, FileExplorer, TerminalView,
        │                       #   TasksView, HistoryView, SettingsView,
        │                       #   ContextPanel, NotificationsLayer, OfficeView
        ├── lib/                # renderMarkdown, syntax highlighting, id
        └── styles/             # globals.css, themes.css, ide.css
```

---

## 🚀 Como rodar

> **Resumo rápido** — Terminal: `python nemo_server.py` • Produção 1-clique: `start_nemo.bat` • Executável: `dist\NEMO_IDE\NEMO_IDE.exe` (na raiz há também o `NEMO_IDE.spec` do build) • Antigravity: `python nemo_server.py --host 0.0.0.0`

### 0. Instalação

```powershell
pip install -r requirements.txt
cd dashboard; npm install; cd ..
```

> **Atenção (PowerShell)**: se o comando `npm` for bloqueado pela *Execution Policy* (erro de `npm.ps1`), use **`npm.cmd`** (ex.: `npm.cmd run build`, `npm.cmd run dev`).

### 1. Backend (Python)

```powershell
# chave da API (opcional — sem ela, respostas ficam em modo offline)
Copy-Item .env.example .env
# edite o .env com sua OPENROUTER_API_KEY

python nemo_server.py
```

O servidor sobe em `http://127.0.0.1:8798` e expõe: `/api/nemo/health`, `/api/nemo/chat`, `/api/nemo/files`, `/api/nemo/file`, `/api/nemo/file/save`, `/api/nemo/terminal`, `/api/nemo/models`, `/api/nemo/snapshot`, `/api/nemo/auth`, `/api/nemo/context`, `/api/nemo/agents`.

> **Sem `OPENROUTER_API_KEY`**: o chat responde com um aviso amigável e funcionam todas as telas da IDE (arquivos, terminal, tasks, escritório). **Com chave vencida/inválida (HTTP 401)**: o NEMO explica que precisa de uma chave nova. Com chave válida, conversa de verdade via OpenRouter.

### 2. Dashboard (IDE)

```powershell
cd dashboard
npm.cmd run dev        # http://localhost:5173 (proxy /api/nemo → 8798)
```

Build de produção: `npm.cmd run build` (gera `dashboard/dist/`, já embutido no executável).

### 3. Produção 1-clique (sempre atualizado)

- **`start_nemo.bat`** — sobe o backend com o dashboard compilado e abre o navegador em `http://127.0.0.1:8798/`.
- **`start_nemo_dev.bat`** — backend (8798) + Vite dev com HMR (5173).

### 4. Executável standalone (PyInstaller)

```powershell
dist\NEMO_IDE\NEMO_IDE.exe [--port 8798] [--host 127.0.0.1]
```

O build empacota o backend, os `agents/`, `squads/`, `skills/` e o `dashboard/dist/` (native no `NEMO_IDE.spec` — além de `python -m PyInstaller NEMO_IDE.spec --noconfirm`).

### 5. Antigravity (IDE de nuvem)

No terminal do workspace Antigravity (Linux):

```bash
pip install -r requirements.txt
cd dashboard && npm install && npm run build && cd ..
python nemo_server.py --host 0.0.0.0 --port 8798
```

Depois abra a porta 8798 no painel *Preview/Ports* do Antigravity (o `--host 0.0.0.0` expõe o servidor para preview).

---

## 🧭 A IDE

- **TopBar** — abas de view (Chat, Workspace, Escritório, Terminal, Tasks, Histórico, Config), botões de painéis (esquerda/direita/inferior), sino de notificações, badge de tasks e perfil.
- **AgentSidebar** (esquerda, colapsável) — rosters dos agentes com ícone, nome, cargo e **status ao vivo** + **squads ativos**.
- **ChatView** — mensagens em bubbles com ícone do agente, timestamps, **estado "typing" com status rotativos** e frases engraçadas, editor de mensagem com sugestões.
- **OfficeView** (Escritório) — **sala de reunião 2D** (Phaser) com a equipe NEMO completa: personagens por função, faixa "NEMO AI STUDIO" nas cores do Vasco, balões de fala com frases divertidas, animações por status (pensando/digitando/comemorando), **clique no agente → perfil → conversar** e seletor de squads.
- **WorkspaceView** — explorador de arquivos (navegação por breadcrumbs) + editor com abas, highlight de sintaxe (Python, TS/JS, JSON, YAML, CSS, HTML, shell, markdown), line numbers, sujar/salvar.
- **TerminalView** — painel inferior com abas ⌨️ Terminal / 🪵 Logs / ▶ Exec; execução segura com confirmação para comandos destrutivos.
- **TasksView** — tarefas com prioridades, adição rápida e progresso.
- **HistoryView** — histórico de ações (chat/file/terminal/task/config) com busca e filtro por tipo.
- **SettingsView** — **5 temas** (Ocean, Vasco, Cyber, Midnight, Graphite), 4 densidades, tamanho de fonte, animações, factory reset.
- **ContextPanel** (direita, colapsável) — contexto ao vivo: agente ativo + frase, squads conexão, tasks em aberto, arquivos abertos, logs recentes.
- **NotificationsLayer** — toasts com auto-dismiss, com painel de notificações no topo.
- Tudo persistido em `localStorage` (`nemo-ide`) + histórico/logs no estado.

---

## 🤖 Agentes

| Agente | Nome | Papel |
|--------|------|-------|
| 🐟 **NEMO** | Nemo | Assistente & Coordenador da equipe |
| 🛠️ JARVIS | Jarvis | Engenharia de software & TI (todas as linguagens, infra, jogos, segurança, redes) |
| 📊 Análisys | Ana | Analista de dados |
| 🔍 Rebeca | — | Pesquisadora |
| ✍️ Clara | — | Redatora |
| ✅ Vera | — | Revisora de qualidade |
| 🎨 Duda | — | Designer de slides/visuais |
| 🎬 Miguel | — | Criador de vídeo |
| 🎯 Igor | — | Estrategista de conteúdo |
| 📱 Sofia | — | Gestora de redes sociais |
| 📤 Paula | — | Editora & publicadora |
| 🔎 Otto | — | Especialista em SEO |

Cada agente tem **modelo padrão + fallbacks** (ex.: `openai/gpt-4o` → `anthropic/claude-3.5-sonnet` → `openai/gpt-4o-mini`). As personas completas estão em `agents/*.agent.md`.

---

## 🧪 Testes

```powershell
# Backend (unit)
python -m pytest test_client_unit.py -q
# ou
python test_client_unit.py

# Frontend
cd dashboard
npm.cmd run build    # type-check (tsc -b) + build
```

---

## 📝 Notas de ambiente

- **Windows PowerShell** exibe UTF-8 como mojibake (`n�o`) no console — as respostas HTTP estão corretas; o problema é só o console.
- **Python custom fuera do projeto** pode não adicionar o CWD ao `sys.path`; rode os scripts pela raiz do projeto ou insira o caminho manualmente.
- **Fallback de modelos**: se o modelo padrão falhar (rate limit / indisponível), o backend troca automaticamente para o fallback configurado.
