# NEMO — IDE de Agentes de IA

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python: 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Render Deploy](https://img.shields.io/badge/Render-deploy-green.svg)](https://render.com)
[![GitHub](https://img.shields.io/badge/GitHub-repo-black.svg)](https://github.com/matheusenaa/Agente-NEMO)
[![PWA Ready](https://img.shields.io/badge/PWA-ready-purple.svg)](https://web.dev/progressive-web-apps/)
[![Offline First](https://img.shields.io/badge/Offline--First-enabled-orange.svg)](OFFLINE.md)
[![Mobile Ready](https://img.shields.io/badge/Mobile-Capacitor-blue.svg)](MOBILE.md)

**NEMO** é o seu **coordenador pessoal de agentes de IA** com identidade visual de **Vasco da Gama** 🔵⚪ (o time adversário não aparece 👀).

Ele orquestra uma equipe especializada de agentes (cada um com personalidade, modelo padrão no OpenRouter e fallbacks automáticos) construída **por você, para o seu trabalho real**: finanças, dados, pesquisa, redação, revisão, design, vídeo, redes sociais, SEO, publicação e TI (o JARVIS, engenheiro de software sênior).

> ✌️ Três formas de uso (todas funcionam juntas):
> - **Web PWA** — Instalável, offline-first, sync automático
> - **Desktop** — PyInstaller (Windows) ou Tauri (planejado)
> - **Mobile** — Capacitor (Android APK/AAB + iOS)

---

## 🗺️ Visão geral da Arquitetura

```
NEMO/
├── BACKEND (FastAPI)
│   ├── nemo_server.py              # API principal: chat, files, terminal, auth, sync
│   ├── ai_providers.py             # Camada abstrata: Gemini, Groq, OpenAI, OpenRouter
│   ├── ai_keys.py                  # Cofre criptografado (Fernet)
│   ├── data_store.py               # DataStore: Supabase + LocalStore (offline-first)
│   ├── openrouter_client.py        # Cliente OpenRouter com fallbacks
│   ├── models_config.py            # 10 modelos + fallbacks inteligentes
│   ├── auth.py / auth_supabase.py  # Auth multi-user + OAuth (Google/Microsoft/Apple)
│   ├── supabase/migrations/        # Schema PostgreSQL + RLS + Sync metadata
│   └── requirements.txt / render.yaml / Procfile
│
├── FRONTEND (React 19 + Vite + TypeScript)
│   ├── dashboard/
│   │   ├── src/
│   │   │   ├── lib/offline/        # IndexedDB + Repository + Sync Engine
│   │   │   ├── hooks/useNetworkStatus.ts  # Detecção online/offline
│   │   │   ├── hooks/useCapacitor.ts      # Plugins nativos mobile
│   │   │   ├── components/ide/NetworkStatusIndicator.tsx
│   │   │   └── api/nemo.ts              # Cliente API + sync endpoints
│   │   ├── public/
│   │   │   ├── sw.js                 # Service Worker customizado
│   │   │   └── manifest.webmanifest  # PWA Manifest
│   │   └── vite.config.ts            # VitePWA + code splitting
│   │
├── MOBILE (Capacitor)
│   ├── dashboard/android/           # Projeto Android (Kotlin)
│   ├── dashboard/ios/               # Projeto iOS (Swift)
│   └── capacitor.config.ts          # Config plugins (Splash, Notifications, etc.)
│
├── DESKTOP
│   ├── NEMO_IDE.spec               # PyInstaller one-folder (Windows)
│   └── start_nemo.bat              # Launcher produção
│
├── DOCS
│   ├── OFFLINE.md                  # Guia offline-first + sync
│   ├── MOBILE.md                   # Guia Capacitor (Android/iOS)
│   ├── DEPLOY.md                   # Guia deploy Render + Supabase
│   └── README.md                   # Este arquivo
│
└── AGENTS (12 personas .agent.md)
    ├── nemo, jarvis, analista, pesquisador, redator, revisor
    ├── designer, criador-video, estrategista, gestor-redes
    ├── editor-publicador, seo
```

---

## ✨ Novidades da Migração Multiplataforma

| Feature | Status | Detalhes |
|---------|--------|----------|
| **PWA (Progressive Web App)** | ✅ | Service Worker, Manifest, Install prompt, Cache offline |
| **Offline-First** | ✅ | IndexedDB (IndexedDBManager), Repository Pattern, Sync Engine |
| **Sincronização** | ✅ | Push/Pull/Conflicts via `/api/nemo/sync/*` |
| **Resolução de Conflitos** | ✅ | Local-wins / Remote-wins / Merge / Manual |
| **Mobile (Capacitor)** | ✅ | Android + iOS, 7 plugins nativos |
| **Desktop (PyInstaller)** | ✅ | One-folder, launcher 1-clique |
| **Tauri (Desktop Leve)** | 📋 | Planejado para substituir PyInstaller |
| **Segurança** | ✅ | CSP, Rate Limits, Origin Guard, CSP Headers |
| **Code Splitting** | ✅ | Chunks: phaser, zustand, yaml, vendor |

---

## 🚀 Como rodar

> **Resumo rápido**
> - Terminal: `python nemo_server.py`
> - Launcher universal: `python start_nemo.py` (abre o navegador sozinho)
> - Produção 1-clique Windows: `NEMO_START.bat` ou `start_nemo.bat`
> - Executável: `dist\NEMO_IDE\NEMO_IDE.exe`
> - Antigravity/Linux: `python start_nemo.py --host 0.0.0.0`
> - Primeiro administrador: `python start_nemo.py --create-admin`
> - **PWA**: `cd dashboard && npm run build` → abre `dist/` no navegador → "Instalar NEMO"
> - **Mobile**: `cd dashboard && npm run build && npx cap sync && npx cap open android`

### 0. Instalação

```powershell
pip install -r requirements.txt
cd dashboard; npm install; cd ..
```

> **Atenção (PowerShell)**: se o comando `npm` for bloqueado pela *Execution Policy* (erro de `npm.ps1`), use **`npm.cmd`** (ex.: `npm.cmd run build`, `npm.cmd run dev`).

### 1. Criar o primeiro ADM

Em uma instalação nova, rode o comando abaixo na raiz do projeto:

```powershell
python start_nemo.py --create-admin
```

O comando solicita nome, e-mail e senha de forma interativa. Se o e-mail já estiver cadastrado, a senha atual é exigida para promover a conta. Nenhuma credencial é fixa no código; a operação é recusada quando já existe um administrador.

Também é possível informar nome e e-mail sem abrir esses prompts:

```powershell
python start_nemo.py --create-admin --admin-name "Seu Nome" --admin-email "seu-email@exemplo.com"
```

### 2. Backend (Python)

```powershell
# chaves de IA (opcional — sem elas, respostas ficam em modo offline)
Copy-Item .env.example .env
# edite o .env com pelo menos uma das chaves: GEMINI_API_KEY, GROQ_API_KEY,
# OPENAI_API_KEY ou OPENROUTER_API_KEY (+ opcional NEMO_AI_PROVIDER)

python nemo_server.py
```

O servidor sobe em `http://127.0.0.1:8798` e expõe: `/api/nemo/health`, `/api/nemo/chat`, `/api/nemo/files`, `/api/nemo/file`, `/api/nemo/file/save`, `/api/nemo/terminal`, `/api/nemo/models`, `/api/nemo/snapshot`, `/api/nemo/auth`, `/api/nemo/context`, `/api/nemo/agents`, `/api/nemo/ai/config|keys|test|search|memories`, `/api/nemo/conversations` (+ `DELETE` por id e busca com `?q=`), `/api/nemo/conversations/{id}/messages`, `/api/nemo/profile` (GET/POST), `/api/nemo/tasks` — e, em produção, também serve o dashboard compilado na raiz `/`.

> **Sem nenhuma chave de IA**: o chat responde com um aviso amigável e funcionam todas as telas da IDE (arquivos, terminal, tasks, escritório). **Com chave vencida/inválida (HTTP 401)**: o NEMO explica que precisa de uma chave nova.

### 3. Dashboard (IDE)

```powershell
cd dashboard
npm.cmd run dev        # http://localhost:5173 (proxy /api/nemo, /api/auth e /api/admin → 8798)
```

Build de produção: `npm.cmd run build` (gera `dashboard/dist/`, já embutido no executável).

### 4. Launcher universal — `python start_nemo.py`

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

### 5. Produção 1-clique (Windows)

- **`NEMO_START.bat`** — launcher robusto: verifica Python, instala dependências se faltarem, compila o dashboard se necessário, copia `.env.example`→`.env` se não existir, sobe o backend e abre o navegador em `http://127.0.0.1:8798/`.
- **`start_nemo.bat`** — sobe o backend com o dashboard compilado e abre o navegador.
- **`start_nemo_dev.bat`** — backend (8798) + Vite dev com HMR (5173).

### 6. Executável standalone (PyInstaller)

```powershell
dist\NEMO_IDE\NEMO_IDE.exe [--port 8798] [--host 127.0.0.1]
```

Para reconstruir o executável com o código atual:

```powershell
cd dashboard; npm.cmd run build; cd ..
python -m PyInstaller NEMO_IDE.spec --noconfirm
```

O build empacota o backend, os `agents/`, `squads/`, `skills/` e o `dashboard/dist/`.

### 7. Diagnóstico do sistema

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

## 🤖 Central de IA (multi-provedor)

O backend fala com **uma camada abstrata** (`ai_providers.py`) — o restante do sistema nunca acessa um provedor diretamente:

| Provedor | Var. de ambiente | Status |
|----------|------------------|--------|
| ✨ Google Gemini | `GEMINI_API_KEY` | REST direto (sem SDK) |
| ⚡ Groq | `GROQ_API_KEY` | OpenAI-compatível |
| 🧠 OpenAI | `OPENAI_API_KEY` | OpenAI-compatível |
| 🌐 OpenRouter | `OPENROUTER_API_KEY` | via `openrouter_client.py` |

- **Resolução**: Configurações do usuário (`Configurações → Inteligência Artificial`) > configuração por agente (`agent_overrides`) > `NEMO_AI_PROVIDER` > modelo padrão do agente.
- **Configuração por agente**: na Central de IA é possível escolher provedor/modelo específicos por agente (missão §40); prioridade: parâmetros da requisição > override do agente > padrão do usuário > padrão do sistema/agente.
- **Rate limit de IA**: por usuário, janela deslizante de 60s (`NEMO_AI_RATE_LIMIT`, padrão `30`/min — missão §35). Ao atingir o limite, o chat responde graciosamente com `rate_limited: True`.
- **Fallbacks**: se o provedor escolhido não tiver chave, degrada para o primeiro configurado (máximo **3 tentativas**, missão §33). Sem nenhuma chave → resposta graciosa offline.
- **Custos/tokens**: cada chamada de chat registra `prompt_tokens`, `completion_tokens` e `total_tokens` na atividade (missão §34) — visíveis em `GET /api/nemo/ai/activity`.
- **API Keys dos usuários**: guardadas **criptografadas** (Fernet derivado de `AUTH_SECRET`, `ai_keys.py`); o frontend só vê a máscara `****...abcd`; nunca vão para logs/Git.
- **Isolamento multiusuário**: todo dado (conversa, memória, chave, tarefa, atividade) é por `user_id`, com RLS `auth.uid() = user_id` no Supabase e pastas separadas no modo local (missão §56).
- **Busca na web**: `web_search.py` usa DuckDuckGo (sem chave) por padrão, com Tavily (`TAVILY_API_KEY`) e Brave (`BRAVE_API_KEY`) quando configurados. A busca é condicional (só quando o agente tem a ferramenta e o pedido indica busca externa) e tem rate-limit por usuário (`WEB_SEARCH_RATE_LIMIT`, padrão 10/min).
- **Memória + conversas + tarefas**: persistidas por usuário via `data_store.py`. Conversas têm **busca no título e no conteúdo** (`GET /api/nemo/conversations?q=...`) e **exclusão** (`DELETE /api/nemo/conversations/{id}`, com as mensagens) — no chat, o botão `📚` reabre ("continuar conversa") ou apaga uma conversa (missão §26).
- **Perfil do usuário**: `GET/POST /api/nemo/profile` persiste nome, idioma e avatar (tabela `profiles` no Supabase / `profile.json` local); cartão "👤 Perfil" em Configurações (missão §8).
- **Health (missão §38)**: `GET /api/nemo/health → ai` expõe `default_provider` e `default_model` — o dashboard mostra "IA ativa", provedor padrão e modelo padrão.

### Configurando no `.env`

```ini
# Pelo menos uma destas desbloqueia o chat real:
GEMINI_API_KEY=
GROQ_API_KEY=
OPENAI_API_KEY=
OPENROUTER_API_KEY=
NEMO_AI_PROVIDER=gemini        # opcional: provedor padrão do sistema
NEMO_AI_RATE_LIMIT=30          # opcional: máx. de requisições de IA por minuto por usuário

# Busca na web (opcionais; DDG funciona sem chave):
TAVILY_API_KEY=
BRAVE_API_KEY=
WEB_SEARCH_RATE_LIMIT=10

# Supabase (opcional — sem isto, usa JSON local em _data/): veja supabase/README.md
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# Autenticação (opcionais):
NEMO_OPEN_REGISTRATION=1            # 0 desativa cadastro aberto (só ADMIN cria contas)
```

> **AUTH_SECRET** passa a ter papel duplo: assina tokens de sessão **e** deriva a chave Fernet das API Keys. Guarde uma valor forte e estável (trocar o valor invalida as chaves já armazenadas).

### Contas (ADMIN + persistência)

- **Contas e sessões no banco**: com Supabase configurado, usuários (`auth_users`) e sessões (`auth_sessions`) vivem no PostgreSQL via **service role** — sobrevivem a redeploy e a login (7 dias) persiste entre restarts. Sem Supabase, caem no `_data/users.json` + sessões em `_data/sessions.json`.
- **Admin bootstrap (admin único)**: o primeiro admin é criado com `python start_nemo.py --create-admin` (ou `POST /api/auth/bootstrap`), exigindo o e-mail `ADMIN_EMAIL` definido no backend. Depois disso, **só existe um admin** — promover uma segunda conta responde `409`, e o admin não pode rebaixar a si mesmo se for o único (`409`).
- **Painel de ADMIN**: Configurações → "🛡️ Usuários" — listar, **criar contas**, promover/rebaixar e redefinir senhas (`GET /api/admin/users`, `POST /api/admin/users`, `PUT /api/admin/users/role`, `PUT /api/admin/users/{id}/password`).
- **Proteções**: só ADMIN acessa o painel; o último admin não pode se rebaixar (`409`); `NEMO_OPEN_REGISTRATION=0` bloqueia cadastro aberto.
- **Migração necessária**: `supabase/migrations/002_auth_tables.sql` (auth_users + auth_sessions com RLS e **sem policies** — só o backend acessa).

### Supabase (opcional)

Com `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`, conversas, memórias, chaves, preferências, tarefas, atividade e buscas passam a viver no PostgreSQL (com **RLS** exigindo `auth.uid() = user_id`). Sem isso, o NEMO continua 100% local em `_data/users/<id>/*.json`. Passo a passo em [`supabase/README.md`](supabase/README.md).

---

## 🗄️ Persistência

- **Interface/estado**: `localStorage` no navegador (chave `nemo-ide`) — temas, tasks, histórico, abas abertas.
- **Squads**: arquivos `yaml`/`csv` em `squads/` + `state.json` por squad (lido pelo snapshot).
- **Dados de usuário (conversas, memórias, chaves, tarefas, atividade)**: via `data_store.py` → **Supabase** quando configurado, senão **JSON local self-contained** em `_data/users/<id>/`. Chaves de IA são criptografadas antes de persistir.

---

## 🧪 Testes

```powershell
# Backend (unit)
python -m pytest test_client_unit.py test_auth.py -q
# ou
python -m unittest test_client_unit test_auth

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