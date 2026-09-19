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
├── nemo_server.py              # Backend FastAPI — chat, arquivos, terminal, snapshot e dashboard
├── openrouter_client.py        # Cliente OpenRouter (chat, modelos, fallbacks)
├── models_config.py            # Configuração dos modelos com fallbacks
├── start_nemo.py               # Launcher universal (Windows/Linux/Antigravity) + diagnóstico
├── agents/*.agent.md           # Personas completas de cada agente
├── requirements.txt
├── .env.example
├── render.yaml                  # Configuração de deploy (Render)
├── Procfile                     # Web: uvicorn ... (Render/Railway/etc)
├── runtime.txt                  # Versão do Python para produção
├── NEMO_IDE.spec                # Build do executável (PyInstaller one-folder)
├── NEMO_START.bat               # Launcher 1-clique no Windows
├── NEMO_DIAGNOSTICO.bat         # Diagnóstico 1-clique no Windows
├── start_nemo.bat               # Produção 1-clique (backend + dashboard compilado)
├── start_nemo_dev.bat           # Dev: backend (8798) + Vite HMR (5173)
├── test_client_unit.py          # Testes unitários do backend
└── dashboard/                   # Frontend — a IDE NEMO
    ├── index.html
    ├── vite.config.ts           # alias @ + proxy /api/nemo
    └── src/
        ├── main.tsx / App.tsx / AppShell.tsx
        ├── api/nemo.ts          # Cliente HTTP do backend
        ├── store/               # useIdeStore (zustand), store do quclube, squads
        ├── data/                # agentes, temas, status/frases, agentes config
        ├── hooks/               # useNemoChat, useSquadSocket, useSquads
        ├── office/              # Cena Phaser do escritório 2D
        ├── components/ide/      # AppShell, TopBar, AgentSidebar, ChatView,
        │                       #   CodeEditor, FileExplorer, TerminalView,
        │                       #   TasksView, HistoryView, SettingsView,
        │                       #   ContextPanel, NotificationsLayer, OfficeView
        ├── lib/                 # renderMarkdown, syntax highlighting, id
        └── styles/              # globals.css, themes.css, ide.css
```

---

## 🚀 Como rodar

> **Resumo rápido**
> - Terminal: `python nemo_server.py`
> - Launcher universal: `python start_nemo.py` (abre o navegador sozinho)
> - Produção 1-clique Windows: `NEMO_START.bat` ou `start_nemo.bat`
> - Executável: `dist\NEMO_IDE\NEMO_IDE.exe`
> - Antigravity/Linux: `python start_nemo.py --host 0.0.0.0`

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

O servidor sobe em `http://127.0.0.1:8798` e expõe: `/api/nemo/health`, `/api/nemo/chat`, `/api/nemo/files`, `/api/nemo/file`, `/api/nemo/file/save`, `/api/nemo/terminal`, `/api/nemo/models`, `/api/nemo/snapshot`, `/api/nemo/auth`, `/api/nemo/context`, `/api/nemo/agents` — e, em produção, também serve o dashboard compilado na raiz `/`.

> **Sem `OPENROUTER_API_KEY`**: o chat responde com um aviso amigável e funcionam todas as telas da IDE (arquivos, terminal, tasks, escritório). **Com chave vencida/inválida (HTTP 401)**: o NEMO explica que precisa de uma chave nova. Com chave válida, conversa de verdade via OpenRouter.

### 2. Dashboard (IDE)

```powershell
cd dashboard
npm.cmd run dev        # http://localhost:5173 (proxy /api/nemo → 8798)
```

Build de produção: `npm.cmd run build` (gera `dashboard/dist/`, já embutido no executável).

### 3. Launcher universal — `python start_nemo.py`

A forma mais simples de rodar (Windows, Linux ou Antigravity):

```bash
python start_nemo.py                  # verifica ambiente, inicia e abre o navegador
python start_nemo.py --host 0.0.0.0   # escuta em todas as interfaces (nuvem/preview)
python start_nemo.py --port 9000      # porta customizada
python start_nemo.py --check          # modo diagnóstico (não inicia o servidor)
python start_nemo.py --no-browser
```

Também pelo npm (se preferir):

```bash
npm run nemo         # = python start_nemo.py
npm run nemo:server  # = python nemo_server.py
npm run nemo:check   # = diagnóstico
```

### 4. Produção 1-clique (Windows)

- **`NEMO_START.bat`** — launcher robusto: verifica Python, instala dependências se faltarem, compila o dashboard se necessário, copia `.env.example`→`.env` se não existir, sobe o backend e abre o navegador em `http://127.0.0.1:8798/`.
- **`start_nemo.bat`** — sobe o backend com o dashboard compilado e abre o navegador.
- **`start_nemo_dev.bat`** — backend (8798) + Vite dev com HMR (5173).

### 5. Executável standalone (PyInstaller)

```powershell
dist\NEMO_IDE\NEMO_IDE.exe [--port 8798] [--host 127.0.0.1]
```

Para reconstruir o executável com o código atual:

```powershell
cd dashboard; npm.cmd run build; cd ..
python -m PyInstaller NEMO_IDE.spec --noconfirm
```

O build empacota o backend, os `agents/`, `squads/`, `skills/` e o `dashboard/dist/`.

### 6. Diagnóstico do sistema

```powershell
python start_nemo.py --check      # qualquer sistema
NEMO_DIAGNOSTICO.bat              # 1-clique no Windows
```

Mostra: Python, Node, npm, dependências, dashboard, agentes, chave OpenRouter, porta e internet.

---

## 🌐 Deploy (online)

O projeto está preparado para **Render** (e serve para Railway/Railway/Heroku com pequenos ajustes).

Arquivos de deploy:
- `render.yaml` — Blueprint do serviço (build: `pip install` + `npm install + npm run build`; start: `uvicorn nemo_server:app --host 0.0.0.0 --port $PORT`).
- `Procfile` — `web: uvicorn nemo_server:app --host 0.0.0.0 --port $PORT`.
- `runtime.txt` — pin do Python 3.12.10.

### Passos no Render

1. Faça push deste repositório no GitHub (`git push origin main`).
2. No [Render.com](https://render.com), entre em **Dashboard → New → Blueprint** (usa o `render.yaml` automaticamente) **ou crie um Web Service** apontando para o repositório `Agente-NEMO`.
3. Campos do Web Service (se não usar Blueprint):
   - **Build Command**: `pip install -r requirements.txt && cd dashboard && npm install && npm run build && cd ..`
   - **Start Command**: `uvicorn nemo_server:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/api/nemo/health`
   - **Python Version**: `3.12.10`
4. Em **Environment**, adicione a variável **`OPENROUTER_API_KEY`** com uma chave válida de https://openrouter.ai/keys (o deploy compila sem ela, mas o chat fica em modo offline).
5. Aguarde o build e abra a URL `https://nemo-ide.onrender.com/`.

> **Nota**: o backend lê `PORT` automaticamente da plataforma (`os.environ["PORT"]`), serve o dashboard compilado na raiz e o frontend chama a API pelo mesmo domínio (`/api/nemo/...`) — sem configurações extras de CORS em produção.

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

## 🗄️ Persistência

- **Interface/estado**: `localStorage` no navegador (chave `nemo-ide`) — temas, tasks, histórico, abas abertas.
- **Squads**: arquivos `yaml`/`csv` em `squads/` + `state.json` por squad (lido pelo snapshot).
- **Sem banco externo**: o projeto é intencionalmente self-contained (nenhuma dependência de SQL/NoSQL) — escolha que simplifica deploy e instalação em qualquer máquina.

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
- **`PORT`/`HOST`**: o servidor respeita as variáveis de ambiente `PORT` e `HOST` (usadas por plataformas de deploy). Local: padrão `127.0.0.1:8798`.
- **`CORS_ORIGINS`**: origens extras separadas por vírgula (útil com domínio custom — ver `.env.example`).
- **Segurança**: `.env` (com chave real) **não** é versionado — apenas `.env.example` com placeholder, ver `.gitignore`.