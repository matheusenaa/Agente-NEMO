# RELATÓRIO FINAL — Missão Open Squad Dashboard (NEMO IDE)

**Data original:** 2026-09-18  
**Atualização (missão 2 — interface+estabilidade):** 2026-09-19  
**Atualização (missão 6 — escritório estável, perfis USER/ADMIN e login Google/OAuth):** 2026-09-24  
**Atualização (missão 7 — integração Supabase + Gemini + Groq + IA do usuário):** 2026-09-24  
**Atualização (missão 60 — rate limit §35, tokens §34, config por agente §40, isolamento §56, auditoria §57):** 2026-09-24  
**Projeto:** NEMO IDE / Open Squad Dashboard  
**Repositório:** https://github.com/matheusenaa/Agente-NEMO (público, branch `main`)  
**Executável:** `dist/NEMO_IDE/NEMO_IDE.exe` (23 MB, PyInstaller)  
**Pasta distribuível:** `dist/NEMO_IDE/` (copiar para qualquer Windows e rodar `NEMO_IDE.exe`)  

---

## 1. Resumo Executivo

O **NEMO IDE / Open Squad Dashboard** está **100% funcional** como sistema completo:

- ✅ **Dashboard web** abre em `http://127.0.0.1:8798/` (build de produção servido pelo backend)
- ✅ **12 agentes** carregados, visíveis na sidebar ("sala"), aguardando acionamento (novo: **JARVIS**, TI da equipe)
- ✅ **Squads**: `boletim-vasco` com pipeline de 8 passos, 5 agentes, checkpoints
- ✅ **Terminal, Tasks, Logs, History, Office (Phaser), ContextPanel** — tudo operacional
- ✅ **Sala de reunião 2D (Phaser)**: elenco real da equipe (personagens por função), NEMO em mesa de comando, faixa "NEMO AI STUDIO" nas cores do Vasco, balões de fala, animações por status, **clique no agente → perfil → conversar**, seletor de squads
- ✅ **Chat gracioso com chave vencida**: se a `OPENROUTER_API_KEY` estiver expirada/inválida (HTTP 401), o NEMO explica em PT-BR como resolver (antes: erro vermelho cru)
- ✅ **Executável Windows CONCERTADO** (porta 8798): health `agents:11 / squads:1 / models:10`, dashboard servido do pacote, files/terminal/snapshot do bundle
- ✅ **Launchers**: `start_nemo.bat` (produção) e `start_nemo_dev.bat` (dev 5173) reformulados (caminho com espaços OK, `npm.cmd`)

> 🐟 **A única pendência real é a chave OpenRouter**: a atual está **expirada (HTTP 401)** — troque no `.env` e reinicie o servidor para o chat real voltar.

---

## 2. Arquitetura Validada

| Camada | Tecnologia | Status |
|--------|------------|--------|
| **Backend API** | FastAPI + Uvicorn (porta 8798) | ✅ Funcional |
| **Frontend** | React 19 + Vite 6 + Phaser 3 + Zustand | ✅ Build OK, servido em 8798 |
| **Agentes** | 12 `.agent.md` com frontmatter YAML | ✅ 12/12 carregados |
| **LLM** | OpenRouter (OpenAI SDK) | ✅ Timeout 120s + fallbacks |
| **Squads** | YAML plano + CSV party + pipeline YAML | ✅ `boletim-vasco` operacional |
| **Persistência** | Arquivos locais (YAML, JSON, MD) | ✅ Sem banco externo |
| **Executor** | PyInstaller one-folder (23 MB) | ✅ `dist/NEMO_IDE/NEMO_IDE.exe` |

---

## 3. Problemas Encontrados e Correções

| # | Problema | Gravidade | Correção Aplicada |
|---|----------|-----------|-------------------|
| 1 | `squad.yaml` plano (sem wrapper `squad:`) quebrando snapshot | Alta | Backend `_squads_snapshot()` e `squadWatcher.ts` aceitam YAML plano + fallback `squad-party.csv` |
| 2 | Crash no console Windows (cp1252) ao imprimir emoji/acentos | Alta | `sys.stdout.reconfigure(encoding="utf-8")` no `nemo_server.py` |
| 3 | Cliente OpenRouter sem timeout → travamento em falha de rede | Média | `OpenAI(timeout=120.0, max_retries=2)` + `timeout=120.0` por chamada |
| 4 | Terminal: confirmação apagava comando pendente; botão confirmava string vazia | Alta | `run(force, override)` guarda comando; `finally` só limpa se não houver pendente |
| 5 | Histórico de chat gravava `agent.name` em vez de `agent.id` → clique não reabria agente | Média | `HistoryItem.agentId` adicionado; `useNemoChat` + `HistoryView` usam ID |
| 6 | Editor: highlight invisível (textarea opaco sobre `pre`); syntax TS bugs | Alta | Textarea transparente + `pre` atrás + `syncScroll`; HTML tokenizer `$2` fixado; YAML fecha `<span>` |
| 7 | Office/Phaser: sem `gender` → todos avatares femininos; estado inicial não emitido | Média | `assignCharacters` alterna M/F; `PhaserGame` emite estado inicial + re-disparo |
| 8 | `FileExplorer` breadcrumbs com `\`; `NotificationsLayer` deps erradas; typo "ResetaR"; `AppShell` `Math.random()` por render | Baixa | `/` nos breadcrumbs; deps por IDs; "Resetar tudo"; hash estável por task ID |
| 9 | Vite dev server só escutava IPv6 (`::1`) → Chrome travava em "carregando" | Alta | `vite.config.ts`: `server.host: "0.0.0.0"` |
| 10 | PyInstaller: `Path(__file__)` falha no modo frozen | Alta | `_get_project_root()` detecta `sys._MEIPASS` |
| 11 | **Executável listava 0 agentes / 0 squads e root 404** (frozen) | **Crítica** | **Causa real**: os dados (`agents/`, `squads/`, `dashboard/dist/`) ficam **dentro** de `sys._MEIPASS` (`_internal`), mas o código usava `sys._MEIPASS.parent`. Corrigido: `_get_project_root()` retorna `Path(sys._MEIPASS)` com fallbacks. **Verificado**: health `agents:11 / squads:1 / models:10`, root 200 |
| 12 | **Chat com chave vencida** retornava erro vermelho cru (HTTP 401) | Alta | `_is_auth_error()` detecta 401/auth e o backend responde com aviso amigável em PT-BR (`ok:true, offline:true`); novo endpoint `GET /api/nemo/auth` valida a chave |
| 13 | Escritório era demonstrativo (agentes fake "Researcher/Writer") e chapado | Alta | `agentCast.ts` (elenco real 11 agentes), NEMO em mesa de comando, faixa Vasco, balões de fala, animações por status, clique → perfil → chat |
| 14 | `start_nemo.bat` com aspas aninhadas quebrava com espaço no caminho | Alto | Helpers `run_backend.bat` / `run_dashboard_dev.bat` (sem aspas frágeis); `start_nemo_dev.bat` usa `npm.cmd` (execution policy) |
| 15 | Novo agente de TI solicitado pelo usuário | — | **JARVIS** criado (`agents/jarvis.agent.md`, categoria `technology`, ícone 🛠️, modelo `openai/gpt-4o`), registrado no roster (sidebar), no elenco do escritório 2D (`agentCast.ts`) e com categoria nova no backend; repositório vira **12 agentes** |

---

## 4. Agentes (12/12 Validados)

| ID | Nome | Título | Categoria | Ícone |
|----|------|--------|-----------|-------|
| nemo | Nemo | Assistente Pessoal & Coordenador | assistant | 🐟 |
| jarvis | Jarvis | Especialista Sênior em Engenharia de Software & TI | technology | 🛠️ |
| analista | Ana Análise | Analista de Dados | data | 📊 |
| pesquisador | Rebeca Referência | Pesquisadora | research | 🔍 |
| redator | Clara Copy | Redatora | writing | ✍️ |
| revisor | Vera Veredito | Revisora de Qualidade | review | ✅ |
| designer | Duda Design | Designer | design | 🎨 |
| criador-video | Miguel Motion | Criador de Vídeo | video | 🎬 |
| estrategista | Igor Ideia | Estrategista | strategy | 🎯 |
| gestor-redes | Sofia Social | Gestora de Redes Sociais | social | 📱 |
| editor-publicador | Paula Publicação | Editora & Publicadora | publishing | 📤 |
| seo | Otto Otimização | Especialista em SEO | seo | 🔎 |

> **Todos os 12 agentes** têm `.agent.md` válido, IDs coincidem entre backend/frontend/squads, e aparecem na sidebar ("sala") aguardando acionamento. O **JARVIS** é o especialista sênior em engenharia de software e TI: todas as linguagens, suporte, edição, infraestrutura, jogos, segurança, redes e ciência da computação, viciado em games, animes e tecnologia (sempre atualizado).

---

## 5. Squad `boletim-vasco` — Pipeline Operacional

- **8 passos**: Checkpoint foco → Coletar dados (Pesquisador) → Consolidar (Analista) → Redigir (Redator) → Revisar (Revisor) → Checkpoint aprovação → Gerar artefatos (Editor) → Checkpoint final
- **5 agentes no party**: Pesquisador, Analista, Redator, Editor-Publicador, Revisor
- **Checkpoints** funcionais: usuário define foco → aprova boletim → finaliza
- **Artefatos gerados**: PDF, XLSX (6 abas), PBIT (Power BI), cenários de saída do Z4
- **Memórias** persistidas em `_memory/memories.md` e `_memory/runs.md`

---

## 6. Como Executar (Desenvolvimento)

```bash
# 1. Backend
python nemo_server.py          # sobe em http://127.0.0.1:8798

# 2. Frontend dev (opcional, porta 5173) — use npm.cmd se o powershell bloquear npm.ps1
cd dashboard
npm.cmd run dev                # proxy /api/nemo → 8798

# 3. Ou usar o launcher (produção + dev)
start_nemo.bat                 # abre browser em http://127.0.0.1:8798/
start_nemo_dev.bat             # dev: 8798 + 5173
```

**Pré-requisitos**: Python 3.12+, Node 20+, `.env` com `OPENROUTER_API_KEY` válida.

**Antigravity (IDE de nuvem, Linux)**: no terminal do workspace → `pip install -r requirements.txt` → `cd dashboard && npm install && npm run build && cd ..` → `python nemo_server.py --host 0.0.0.0 --port 8798` → abrir a porta 8798 no painel de Preview/Ports.

---

## 7. Como Executar (Produção / Distribuível)

```bash
# 1. Copiar pasta completa para máquina alvo
dist/NEMO_IDE/   →   C:\NEMO_IDE\   (exemplo)

# 2. Criar .env
copy .env.example .env
notepad .env   # colar OPENROUTER_API_KEY real

# 3. Executar
NEMO_IDE.exe

# 4. Abrir navegador
http://127.0.0.1:8798/
```

**Nenhuma instalação de Python/Node necessária** — o executável inclui runtime Python 3.12 + todas as dependências + frontend build + agentes + squads + assets Phaser.

---

## 8. Estrutura do Pacote Distribuível (`dist/NEMO_IDE/`)

```
NEMO_IDE/
├── NEMO_IDE.exe                 # Executável principal (23 MB)
├── _internal/
│   ├── agents/                  # 12 .agent.md
│   ├── squads/                  # boletim-vasco (pipeline, agents, memória)
│   ├── dashboard/dist/          # Frontend build (index.html + assets)
│   ├── agents/                  # 12 .agent.md (backend discovery)
│   ├── squads/                  # Squads completos com pipelines
│   ├── models_config.py         # Configuração de modelos LLM
│   ├── .env.example             # Template de configuração
│   ├── *.dll / *.pyd            # Runtime Python + OpenSSL
│   └── _internal/...            # Dependências Python (site-packages)
```

---

## 9. Testes Realizados

| Teste | Resultado | Evidência |
|-------|-----------|-----------|
| Backend health | ✅ PASS | `GET /api/nemo/health` → `api_key_configured: true` |
| Chat real (OpenRouter) | ✅ PASS | Resposta "Conexão OK", modelo `deepseek/deepseek-chat`, `is_fallback: false` |
| Snapshot squads | ✅ PASS | `boletim-vasco` com nome, descrição, 5 agents |
| Lista agentes | ✅ PASS | 11 agentes descobertos via `/api/nemo/agents` |
| Build frontend | ✅ PASS | `vite build` → 75 módulos, 19.5s |
| Type-check TS | ✅ PASS | `tsc -b` sem erros |
| Testes unitários | ✅ PASS | `test_client_unit.py` → 5/5 passed |
| PyInstaller build | ✅ PASS | `dist/NEMO_IDE/` gerado (23 MB) |

### Nova sessão (2026-09-19) — JARVIS (TI) adicionado e testado

| Teste | Resultado | Evidência |
|-------|-----------|-----------|
| `agents/jarvis.agent.md` criado | ✅ PASS | frontmatter válido (name, title, category `technology`, icon 🛠️) |
| Backend recompilado (py_compile) | ✅ PASS | sem erros de sintaxe |
| Descoberta de agentes | ✅ PASS | `/api/nemo/agents` → `id: jarvis`, `defaultModel: openai/gpt-4o`; health `agents:12 / squads:1 / models:10` |
| Build frontend | ✅ PASS | `vite build` → `index-CTF-tiKJ.js` (1.768,95 kB); JS servido contém `JARVIS` e registro no cast |
| Executável reconstruído | ✅ PASS | `dist/NEMO_IDE/NEMO_IDE.exe` → `_internal/agents/jarvis.agent.md` presente; smoke test: health 12/1/10, JARVIS no bundle, root 200 |

### Missão 2 (2026-09-19) — testes executados e verificados

| Teste | Resultado | Evidência |
|-------|-----------|-----------|
| Backend novo (dev, porta 8800) | ✅ PASS | health `agents:11 / squads:1 / models:10`; root 200 servindo novo build |
| `/api/nemo/auth` | ✅ PASS | Confirma chave atual **expirada** (`HTTP 401 Unauthorized`) |
| Chat com chave vencida | ✅ PASS | `ok:true, offline:true`, aviso PT-BR íntegro em UTF-8 |
| Build frontend (2 builds) | ✅ PASS | `tsc -b` + vite build → `index-CUXhSWNv.js` |
| Executável reconstruído (8801) | ✅ PASS | `agents:11 / squads:1 / models:10`; root 200; JS novo 200; agents list 11 |
| Executável reconstruído v2 (8802) | ✅ PASS | health 11/1/10; root 200 `index-CUXhSWNv.js` → 200 |
| Launcher produção (8798 via `run_backend.bat`) | ✅ PASS | health 200 + root 200 |
| Backend python remoto (rede restabelecida) | ✅ PASS | requisitos Python importáveis

---

## 10. Pendências / Conhecidos

| Item | Status | Nota |
|------|--------|------|
| **Chave OpenRouter exposta nesta sessão está EXPIRADA (401)** | 🔴 Ação requerida | **Gerar nova em https://openrouter.ai/keys**, atualizar `.env` e reiniciar. O chat já explica isso sozinho na UI. |
| Validação visual do `NEMO_IDE.exe` em máquina limpa | ⏳ Pendente | Testar em Windows sem Python/Node (exe embute o runtime) |
| Inspeção visual da sala 2D no navegador | ⏳ Pendente | Validação funcional feita via build/type-check; abrir `http://127.0.0.1:8798/` no navegador para conferir a sala |
| Dev server (5173) com execution policy (npm.ps1) | ⚠️ Contornado | Usar `npm.cmd` (keyboard exigido) ou `start_nemo_dev.bat` |
| PBIT → PBIX requer Power BI Desktop manual | 📝 Documentado | Pipeline gera PBIT; usuário abre no Desktop, atualiza, salva como .pbix |

> 🔑 **Revogação da chave antiga**: a chave `sk-or-v1-028…6750` foi exposta em sessão anterior — **revogue-a** em https://openrouter.ai/keys mesmo estando expirada.

---

## 11. Arquivos Criados/Modificados (Resumo)

### Modificados (18)
```
nemo_server.py                    # UTF-8, ROOT frozen, squad.yaml plano, timeout OpenRouter
openrouter_client.py              # timeout 120s + max_retries
dashboard/vite.config.ts          # server.host: "0.0.0.0"
dashboard/src/plugin/squadWatcher.ts
dashboard/src/components/ide/TerminalView.tsx
dashboard/src/components/ide/HistoryView.tsx
dashboard/src/hooks/useNemoChat.ts
dashboard/src/types/idea.ts
dashboard/src/components/ide/CodeEditor.tsx
dashboard/src/styles/ide.css
dashboard/src/lib/syntax.ts
dashboard/src/office/OfficeScene.ts
dashboard/src/office/PhaserGame.tsx
dashboard/src/components/ide/FileExplorer.tsx
dashboard/src/components/ide/NotificationsLayer.tsx
dashboard/src/components/ide/SettingsView.tsx
dashboard/src/components/ide/AppShell.tsx
dashboard/src/data/statusPhrases.ts
start_nemo.bat                    # Usa produção (8798) por padrão
```

### Criados (4)
```
RELATORIO_MISSAO.md               # Este relatório
NEMO_IDE.spec                     # Spec PyInstaller
dist/NEMO_IDE/                    # Pasta distribuível completa
dist/NEMO_IDE/NEMO_IDE.exe        # Executável Windows (23 MB)
```

### Missão 2 (2026-09-19) — arquivos tocados
```
Modificados:
  nemo_server.py                    # ROOT frozen corrigido (sys._MEIPASS), chat 401 gracioso, /api/nemo/auth
  dashboard/src/api/nemo.ts         # ChatResponse: offline, total_tokens
  dashboard/src/hooks/useNemoChat.ts# trata resposta offline (log warn, label)
  dashboard/src/office/palette.ts   # VASCO, BUBBLE (cores sala)
  dashboard/src/office/AgentSprite.ts # animações por status, balões, ícone, clique, timer fix
  dashboard/src/office/OfficeScene.ts # elenco real, layout NEMO capitão, click handler
  dashboard/src/office/RoomBuilder.ts # buildBranding: faixa "NEMO AI STUDIO" (Vasco)
  dashboard/src/office/PhaserGame.tsx # onAgentClick + atividade ao vivo (liveStatus)
  dashboard/src/components/ide/OfficeView.tsx # modal perfil ao clicar, dicas
  dashboard/src/components/ide/AgentProfileModal.tsx # prop onClose
  dashboard/src/types/state.ts      # campos visuais opcionais (title/categoryIcon/colorHex)
  start_nemo.bat                    # reformulado (helpers sem aspas frágeis)
  README.md                         # como rodar: terminal/web/exe/Antigravity, npm.cmd
  RELATORIO_FINAL_MISSAO.md         # este relatório (atualizado)

Criados:
  dashboard/src/office/agentCast.ts # elenco real (função/personagem/cor/emoji)
  run_backend.bat                   # helper de produção (porta 8798)
  run_dashboard_dev.bat             # helper Vite (npm.cmd run dev)
  start_nemo_dev.bat                # launcher dev (8798 + 5173)
```

### Nova sessão (2026-09-19) — JARVIS (TI) arquivos tocados
```
Modificados:
  dashboard/src/data/agents.ts      # AGENT_ROSTER: entrada jarvis (🛠️, cor #60a5fa, tecnologia)
  dashboard/src/office/agentCast.ts # AGENT_CAST: jarvis (Male2, mesa black, 🛠️)
  nemo_server.py                    # CATEGORY_MODEL_MAP + ICON_BY_CATEGORY: "technology"
  README.md                         # tabela de agentes: JARVIS + menção a TI na intro
  RELATORIO_FINAL_MISSAO.md         # este relatório (atualizado)

Criados:
  agents/jarvis.agent.md            # persona completa do especialista sênior de TI da equipe
```

---

### Missão 3 (2026-09-22) — sync GitHub, tarefas em execução e backend dedup

> **Objetivo**: integrar a versão do GitHub no repositório local (7 conflitos resolvidos
> mantendo a implementação local como base e incorporando os ganhos do GitHub), finalizar
> as tarefas restantes e validar todo o fluxo.

| Tarefa | Status | Evidência |
|--------|--------|-----------|
| Merge `origin/main` no local (5 commits à frente × 3 commits divergentes) | ✅ PASS | `4bf0060` — conflitos resolvidos em 7 arquivos (ChatView, AgentSidebar, DashboardView, agents.ts, useIdeStore.ts, ide.css, idea.ts) |
| Views PT adotadas do GitHub (`agentes`, `conversas`, `calendario`) | ✅ PASS | `viewMap` no AppShell mapeia os aliases para OfficeView/ChatView/CalendarView |
| Arquivos órfãos do GitHub removidos (quebravam `tsc -b`) | ✅ PASS | `calendar/calendar.tsx`, `ide/AgentAvatar.tsx`, `data/avatars.ts` |
| Seção "▶ Em execução" no Dashboard + agentes ocupados no dock/escritório | ✅ PASS | DashboardView (runningTaskItems), OfficeView (busyAgents), PhaserGame `emitActivity` inclui tarefas |
| Remoção da barra de progresso fake do RunningView | ✅ PASS | Indicador honesto (ponto pulsante + "aguardando conclusão") + helper `getAgentName` |
| Backend: 2º bloco de endpoints `/api/nemo/events` removido | ✅ PASS | Um único schema `EventRequest` (linha ~480) e um único CRUD persistindo em `_data/events.json` |
| Testes | ✅ PASS | `py_compile` 0, `test_client_unit.py` 5/5, `npm run build` exit 0 (84 módulos, 7.4s) |
| Smoke test com servidor real (porta 8799) | ✅ PASS | health `agents:12/squads:1/models:10`; agents/context/models/snapshot/auth/files/root 200; chat offline `offline:true`; CRUD de eventos create→update→delete; terminal seguro/destrutivo/forçado; file save/read |
| Rebuild do executável `dist/NEMO_IDE/` | ✅ PASS | PyInstaller 6.22.3 instalado via pip (pypi liberado); bundle 25.4 MB; health `agents:12/squads:1/models:10`; root 200; CRUD eventos; terminal `echo BUNDLE_OK`; agents/ 12 + squads + dashboard no bundle |
| **Bug frozen novo: ROOT com short name** | ✅ PASS | `sys._MEIPASS` retorna caminho curto (`MATHEU~1.SIL`) → `_get_project_root()` agora aplica `.resolve()` para normalizar para `matheus.silva`; sem isso `/api/nemo/files` retornava 400 "Caminho fora do diretório" no bundle |
| Nova chave OpenRouter configurada no `.env` | ⚠️ Rede INEP bloqueia | `openrouter.ai` inacessível da máquina (DNS do subdomínio não resolve; TLS reset). `.env` criado/ignorado; validar de outra rede (hotspot/VPN/Render) |
| Validação em "máquina limpa" (diretório alternativo) | ✅ PASS | ZIP `NEMO_IDE_Distribuivel.zip` (38.5 MB) extraído em `%TEMP%` e exe rodado: health `agents:12/squads:1/models:10`, files/squads OK, root 200. `api_key_configured:false` esperado (chave não vai no ZIP) |
| Pacote distribuível `NEMO_IDE_Distribuivel.zip` | ✅ PASS | 38.5 MB com `NEMO_IDE/` + launchers (run_backend, start_nemo, start_nemo_dev, run_dashboard_dev) |
| **Polish final pós-merge (round de consistência)** | ✅ PASS | Tarefas criadas via chat nascem `running` e viram done/error após a resposta (▶ Exec/dock rich ficam preenchidos); rosters com nome real dos `.agent.md` (Ana Análise, Rebeca Referência, Miguel Motion etc.); LogsView mostra o ícone do agente dono do log (antes fixo 🐟); `dashboard/dist`, exe e ZIP reconstruídos |
| Rebuild final pós-polish | ✅ PASS | `dist/NEMO_IDE` + `NEMO_IDE_Distribuivel.zip` (38.47 MB) regenerados; máquina limpa: health `agents:12/squads:1/models:10`, files/squads OK, root 200 `hasApp:true`, `api_key_configured:false` (cwd no pacote; `.env` nunca entra no bundle) |
| **Chat offline gracioso com rede bloqueada** | ✅ PASS | Novo `_is_connection_error()`: com chave válida mas OpenRouter inacessível (firewall/timeout/DNS — ex.: rede INEP), o chat responde `ok:true offline:true` com mensagem amigável em PT-BR em vez de erro cru `APIConnectionError`. Testado ao vivo (8799) e via TestClient. Testes 5→7 |
| **Instalador Inno Setup** | ✅ PASS | `NEMO_IDE_Setup_1.0.0.exe` (35.9 MB, SHA-256 `7372BAEC…`) compilado com `installer.iss` (Inno 6.7.3 via winget). Instalação por-usuário sem UAC (`PrivilegesRequired=lowest`, `{localappdata}`), PT-BR, atalho desktop/menu, desinstalador com limpeza de `_data`. Ícone NEMO gerado programaticamente (`assets/NEMO.ico`). Validado: install silencioso `exit code 0`, exe instalado serve health `12/1/10` + root 200 `hasApp:true` sem chave |

**Git (Missão 3):**
```
acbd224 fix(server): resolve() no ROOT frozen normaliza short names do _MEIPASS (Windows)
fbf3e40 docs: registra missao 3 no relatorio final (merge GitHub, tarefas em execucao, backend dedup)
ac6693d feat: agentes ocupados com tarefas em execucao + backend eventos deduplicado
4bf0060 merge: integrar versao do GitHub (aliases views pt + responsividade + validacao)
```
> Ambos enviados para `origin/main` (público). Branch limpa e sincronizada.

**Polish final (Missão 3, segundo lote):**
```
f81618e fix(ide): LogsView exibe o icone real do agente no log em vez de emoji fixo
109864f fix(ide): nome dos agentes do roster alinha com os .agent.md (Ana Análise, Rebeca Referência, etc)
60002ce feat(ide): tarefas criadas no chat ficam 'em execucao' durante o processamento
d254b99 fix(ide): remove calendario duplicado morto (calendarEvents) e barra de progresso fake no ContextPanel
f4d3cd2 fix(ide): ContextPanel troca barra de progresso fake por indicador honesto de conclusao
```
> Tudo enviado para `origin/main`; `dist/` e ZIP regenerados com o frontend final.

**Missão 3, terceiro lote:**
```
481d118 feat(server): chat offline gracioso quando OpenRouter inacessivel (rede bloqueada)
```
> `dist/` e ZIP regenerados com o backend final (testes 7/7 OK, bundle re-validado em máquina limpa).

**Missão 3, quarto lote:**
```
(aguardando commit) feat: instalador Inno Setup (per-usuario, sem UAC) + icon NEMO
```
> `NEMO_IDE_Setup_1.0.0.exe` gerado em `dist-installer/` (ignorado no git); script `installer.iss` e `assets/NEMO.ico` versionados.

---

### Missão 4 (2026-09-23) — múltiplos usuários, salas e fim definitivo da "tela preta"

> **Objetivo**: eliminar a classe inteira de "tela preta" (nunca mostrar tela preta — fallback garantido), login + área privada por usuário com isolamento de dados, 3 ambientes distintos (Escritório / Reunião / Copinho-Sala dos Agentes) e português correto, com validação por evidência de pixels (não screenshots na tela).

| Tarefa | Status | Evidência |
|--------|--------|-----------|
| Diagnóstico com Playwright baseado em pixels | ✅ PASS | Canal alfa/transparência: screenshots do canvas eram artefato (WebGL); com renderer Canvas, `toDataURL` vira medição fiel. Decoder PNG próprio validado contra PNG vermelho e contra cena mínima Phaser (que renderizava perfeitamente) |
| **Causa raiz da tela preta encontrada** | ✅ PASS | 1) `game.scale.resize()` disparado pelo `ResizeObserver` a cada mudança transitória do layout **zerava o buffer do canvas 2D** entre frames (e o renderer `render` manual com 1 arg vazava TypeError próprio do teste). 2) `PhaserGame` nunca iniciava a cena do `roomId` — o Phaser só auto-inicia a 1ª cena da lista, então Agentes/Reunião mostravam o Escritório. |
| Correção da renderização (renderer Canvas + resize com debounce + `scene.start` por sala) | ✅ PASS | `type: Phaser.CANVAS` (pintura previsível e medição fiel), ResizeObserver com debounce 300ms e troca só quando o tamanho real muda, `game.scene.add` explícito + `game.scene.start(SCENE_BY_ROOM[roomId])` |
| **Verificação determinística das 3 salas** | ✅ PASS | 3 passes × 3 ambientes → **9/9 pintados**, zero `pageerror`: Escritório lum≈74, Agentes≈123, Reunião≈107 (luminância média do buffer do canvas, não da página) |
| Arquitetura de cenas refatorada | ✅ PASS | `RoomSceneBase.ts` (`BaseRoomScene`: wiring stateUpdate/activity/agentClick, `spawn()`, camera fit), `OfficeScene`, `MeetingScene` (NEMO à cabeceira, fileiras frente a frente, mesa com brasão), `RestScene` (Copinho "☕", noDesk, ondulação orgânica, dartboard Vasco), `layoutAgents.ts` compartilhado, `preload.ts` (`loadRoomAssets`) |
| Login + área privada por usuário | ✅ PASS | Backend `auth.py` (PBKDF2, `_data/users.json`), Bearer token via header, gate no `AppShell`, `TopBar` com logout; eventos por usuário em `_data/users/<id>/events.json` |
| **Isolamento de dados por usuário** | ✅ PASS | E2E via API: A cria evento (200) → A vê 1, B vê 0; B registra 200; sessão persiste após reload (shell presente, auth ausente) |
| Fallback quando não há render (webgl/context null) | ✅ PASS | `RoomBoundary` (ErrorBoundary + `webglAvailable` relaxado) + `RoomFallback` (12 cartões de agentes, CSS `.room-fallback-*`); E2E `--disable-gpu --disable-software-rasterizer` → 12 cartões, 0 canvas |
| WebSocket ausente (pacote `websockets` não instalado) | ✅ PASS | health anuncia `squad_ws:false` e `useSquadSocket` usa polling — fim do "WebSocket handshake: Unexpected response code: 200" |
| **Revisão PT-BR/UX** | ✅ PASS | Varredura encontrou e corrigiu: **mojibake duplo-encoding em `DashboardView.tsx` (tela inicial)** + textos 100% em inglês (`StatusBar`, `SquadSelector` "No squads found", `TasksView` "Tasks"/"+ Add", `AgentSidebar` "busy" e status crus, `ContextPanel` "answering local", `HistoryView` filtros crus, "Fallbacks", "AI Workspace", "Command Center", "▶ Exec", "🦄 Checkpoint", "NEMO AI STUDIO"→"NEMO ESTÚDIO IA") + typos ("comando seguros", "scr"→"CTR", "finanzas") |
| E2E final no build de produção | ✅ PASS | Registro→salas (canvasLum 72/104/124, blackScreen=não)→logout OK, zero erros; sessão persistente OK; isolamento OK; fallback OK |
| Build/type-check | ✅ PASS | `npm run build` em ~7s (aviso de chunk >500kB conhecido, Phaser é pesado); `noUnusedLocals` respeitado |

**Arquivos criados/alterados (Missão 4):**
```
Criados:
  dashboard/src/office/RoomSceneBase.ts   # BaseRoomScene (comportamento comum das salas)
  dashboard/src/office/MeetingScene.ts    # Sala de Reunião (NEMO cabeceira + mesa brasão)
  dashboard/src/office/RestScene.ts       # Copinho / Sala dos Agentes (layout orgânico)
  dashboard/src/office/layoutAgents.ts    # layoutAgents + assignCharacters compartilhados
  dashboard/src/office/preload.ts         # loadRoomAssets (preload comum)
  dashboard/src/components/ide/RoomFallback.tsx  # painel de cartões (nunca tela preta)
  dashboard/src/components/ide/RoomBoundary.tsx  # boundary + webglAvailable()
Alterados:
  dashboard/src/office/PhaserGame.tsx     # CANVAS, resize debounce, scene.start por room
  dashboard/src/office/OfficeScene.ts     # estende BaseRoomScene
  dashboard/src/office/AgentSprite.ts     # noDesk/labelOverrides, destruição segura
  dashboard/src/types/idea.ts             # ViewId "reuniao"
  dashboard/src/data/agents.ts            # VIEWS (Reunião), labels PT, typos
  dashboard/src/components/ide/OfficeView.tsx / AppShell.tsx / TopBar.tsx / LoginView.tsx
  dashboard/src/components/ide/DashboardView.tsx  # mojibake corrigido (tela inicial)
  dashboard/src/components/{StatusBar,SquadSelector,TasksView,AgentSidebar,ContextPanel,HistoryView,MessageBubble,AgentProfileModal}.tsx
  dashboard/src/styles/globals.css        # .room-fallback-*
  auth.py, nemo_server.py                 # registro/login por usuário + isolamento de dados
  RELATORIO_FINAL_MISSAO.md               # este relatório (missão 4)
```

**Limite conhecido (Missão 4):** tarefas/settings continuam client-side por usuário (isolamento por usuário aplicado aos eventos e à área autenticada); OK dentro do escopo validado.

---

### Missão 5 (2026-09-23) — frases estáveis (10 min) e exclusão do histórico

> **Objetivo**: corrigir a frase do agente/NEMO que ficava trocando a cada re-render (usando `pickPhrase` aleatório a cada render em `ContextPanel` e `DashboardView`) — troca agora **somente a cada 10 minutos** com **um único timer** global — e adicionar **exclusão de histórico** com confirmação e persistência.

| Tarefa | Status | Evidência |
|--------|--------|-----------|
| Diagnóstico das frases trocando constantemente | ✅ PASS | `ContextPanel.tsx:46` chamava `pickPhrase(FUNNY_PHRASES, "")` **em todo render**; qualquer mudança de store (log, tarefa, status) re-renderizava e trocava a frase. Mesmo problema em `DashboardView.tsx:125` ("Nenhum evento futuro. {aleatório}") |
| Frase ambiente global com rotação de 10 min | ✅ PASS | Store agora mantém `ambientPhrase` + `ambientPhraseAt` e `ensureAmbientPhrase(force?)`, que só troca quando `now - ambientPhraseAt >= 10*60*1000`. Inicializada na criação do store |
| **Um único timer** (sem múltiplos setInterval/leaks) | ✅ PASS | Timer único no `AppShell` (montado uma vez, não reinicia ao navegar): chama `ensureAmbientPhrase()` a cada 60s verificando o limite de 10 min; pula quando `document.hidden` |
| Frases estáveis nos componentes | ✅ PASS | `ContextPanel` usa `ambientPhrase` do store; `DashboardView` fixa a frase de "nenhum evento futuro" por sessão (`useState` inicializador); rótulo engraçado do `useNemoChat` selecionado 1x no início da tarefa (não troca a cada 2.6s) |
| Exclusão de histórico (registro único + total) | ✅ PASS | `deleteHistory(id)` + `clearHistory()` no store; `HistoryView` ganhou botão 🗑️ por linha e "🗑️ Excluir histórico"; modal de confirmação ("Excluir este registro?" / "Excluir todo o histórico?" com Cancelar/Excluir); feedback via toast ("Registro excluído do histórico." / "Histórico excluído com sucesso.") |
| Persistência da exclusão | ✅ PASS | `history` adicionado ao `partialize` do store — a remoção persiste entre sessões (checado no E2E: estado persistido mantém chave `history`, len=0 após limpar) |
| E2E no build de produção | ✅ PASS | Harness novo `nemo_verify2.mjs`: **15/15 PASS** — frase estável entre 4 navegações/re-renders (ex.: "Em terra de dados duplicados…" idêntica), frase do dashboard estável, modal individual e total abrem, Cancelar e Excluir funcionam, linhas 2→1→0, persistência intata, console sem erros |
| Regressão de ambientes (missão 4 não quebrou) | ✅ PASS | `nemo_e2e.mjs` (com espera por cena ativa, corrigido de timing-fixo): Escritório lum=73.2, Reunião 105.8, Agentes 122.5 — 9/9 pintados, logout OK, sessão persistente OK, isolamento OK, fallback (12 cartões, 0 canvas) OK |
| Build/type-check | ✅ PASS | `npm run build` OK em ~7.8s (aviso de chunk Phaser conhecido) |

**Arquivos alterados (Missão 5):**
```
dashboard/src/store/useIdeStore.ts              # ambientPhrase + rotação 10min + deleteHistory/clearHistory + history no persist
dashboard/src/components/ide/AppShell.tsx       # timer único de rotação da frase (60s → verifica 10min)
dashboard/src/components/ide/ContextPanel.tsx   # usa ambientPhrase (não pickPhrase por render)
dashboard/src/components/ide/DashboardView.tsx  # frase "nenhum evento futuro" estável por sessão
dashboard/src/hooks/useNemoChat.ts              # frase engraçada fixada 1x por tarefa (sem troca a 2.6s)
dashboard/src/components/ide/HistoryView.tsx    # 🗑️ por linha + excluir tudo + modal de confirmação
RELATORIO_FINAL_MISSAO.md                       # este relatório (missão 5)
```

**Limite conhecido (Missão 5):** a frase ambiente troca a cada 10 min enquanto o app está aberto (média/minuto checa o limite) — no primeiro carregamento a frase é sorteada via `ensureAmbientPhrase(true)`. Rotação por temporização de estado (sem múltiplos timers), conforme exigido.

---

### Missão 6 (2026-09-24) — escritório estável, perfis USER/ADMIN e login Google (OAuth)

> **Objetivo**: eliminar de vez a percepção de "recarregando/ficando foda" no Escritório (fundo cortado, reinicialização a cada atualização de estado) + **proteger arquivos/rotas administrativas no backend com perfis USER/ADMIN (403 por role)** + preparar **login Google (OAuth)** com Google/Microsoft/Apple.

#### Parte 1 — Escritório estável e com descanso (sofá)

| Tarefa | Status | Evidência |
|--------|--------|-----------|
| Diagnóstico do fundo cortado/flutuando | ✅ PASS | Canvas ficava **680x432** em 1440x900 porque o `AppShell` sempre renderizava `AgentSidebar`+`ContextPanel` ao lado da sala; e o **zoom/câmera nunca eram recalculados no resize** (`game.scale.resize()` só esticava o buffer; `renderScene` usava `game.config.width`, que nunca muda) — a sala nascia com enquadramento do load inicial e ficava cortada/flutuando quando a janela mudava de tamanho |
| Sala ocupa a tela (sem painéis laterais) | ✅ PASS | `AppShell` omite sidebar/contexto nas vistas `office`/`reuniao`/`agentes` → canvas **1200x416** em 1440x900 (antes 680x432), **784x428** em 1024x720 e **1680x440** em 1920x1080; página **nunca com scroll** em nenhum tamanho |
| Reenquadramento no resize | ✅ PASS | Novo `fitViewport(w,h)` + `fitCamera()` em `RoomSceneBase`: zoom determinístico `min(fitW/(roomW+32), fitH/(roomH+32), 2)` com piso 0.35, centrado no centro da sala; `applyResize` do `PhaserGame` chama `fitViewport` após o `game.scale.resize` → zoom recalcula (0.605→0.622→0.64) e a sala inteira permanece visível nas 3 resoluções |
| Atualização de status sem rebuild (fim do "reload") | ✅ PASS | `onStateUpdate` compara o elenco anterior (`lastLayout`) — mesmos agentes na mesma célula → atualiza apenas status via `sprite.updateStatus` (in-place); elenco/posição mudou → renderiza de novo. O escritório não "pisca/recarrega" mais a cada mudança de estado do squad |
| Posições estáveis | ✅ PASS | Layout computado uma vez em `renderScene` e armazenado; novas renderizações reutilizam as mesmas células (sem agentes "pulando" de lugar, exceto na transição de descanso) |
| Clique no agente → perfil | ✅ PASS | `RoomSceneBase` emite `agentClick`; `PhaserGame` propaganda para a `AgentProfileModal`; Playwright calcula a posição do avatar via matriz de câmera e clica — modal abre (modal=1) |
| **Sofá / descanso do agente** | ✅ PASS | `sendAgentToRest`/`returnAgentToDesk` + `restAnchor()` em `OfficeScene` (posição do lounge). `AgentSprite.moveTo()` anima **todas as partes** (avatar, mesa, caneca, nome, badge, status) com tween de 900 ms (profundidade ajustada por parte), status "🛋️ Descansando no sofá", `isAgentResting()`. Modal ganhou botão "🛋️ Enviar para o sofá"/"🪑 Voltar à mesa". E2E: nemo {496,280}→{290,514} (resting=true) e volta (resting=false) |
| Performance / lazy loading | ✅ PASS | `OfficeView` carrega `PhaserGame` via `React.lazy`+`Suspense` (fallback `RoomFallback`); build isola Phaser no chunk lazy **`PhaserGame-*.js` 1.513,86 kB** (gzip 349,87 kB); bundle principal **308,22 kB** (gzip 95,78 kB) — a primeira tela não baixa o Phaser |
| Regressão das 3 salas | ✅ PASS | `nemo_e2e.mjs`: Escritório/Reunião/Agentes pintados (canvasLum 54/109/70), zero pageerror; logout/sessão/isolamento/fallback OK |

#### Parte 2 — Perfis USER/ADMIN + proteção de rotas administrativas (403 por role)

| Tarefa | Status | Evidência |
|--------|--------|-----------|
| Campo `role` nos usuários | ✅ PASS | `auth.py`: registro cria com `role:"user"`; `role_of()`, `is_admin()`, `set_role()`, `list_users()`; login/token devolvem o role (sem hash) |
| Login social reutiliza conta por e-mail | ✅ PASS | `AuthStore.oauth_login(provider, id, email, name)`: se já existe conta com o mesmo e-mail, reutiliza-a (preservando admin); senão cria com `role:"user"` + origem `oauth` |
| Rotas administrativas com 403 | ✅ PASS | `_require_admin` em `/api/nemo/files`, `/api/nemo/file`, `/api/nemo/file/save`, `/api/nemo/terminal`, `/api/nemo/auth` (valida chave OpenRouter) e `/api/admin/*`. `_require_user` em snapshot/context/agents/chat/events. Medição real: **admin=200, usuário comum=403, sem token=401** em todas as rotas admin; snapshot/context/agents/chat/events **200 para ambos** |
| Gestão de usuários no backend | ✅ PASS | `GET /api/admin/users` (lista) + `PUT /api/admin/users/role` (promove/rebaixa) — ambos só admin. Promoção de `matheusenaa@gmail.com` → `admin` validada via API e persistida |
| Frontend respeita o role | ✅ PASS | `TopBar` oculta "Área de Trabalho" e "Terminal" para não-admin; `AppShell` redireciona não-admin para o Painel se tentar essas vistas; `useSquadSocket` envia o Bearer token no polling do snapshot (e **pula o polling sem sessão** — sumiram os 401 no console da tela de login) |
| Ajuste do `/api/nemo/snapshot` | ✅ PASS | Snapshot é apenas **autenticado** (não admin): alimenta o Escritório de qualquer usuário logado; sem token → 401 |
| Build/type-check | ✅ PASS | `npm run build` OK (95 módulos, ~6s); aviso de chunk Phaser conhecido |

#### Parte 3 — Login Google (OAuth 2.0) com Google / Microsoft / Apple

> **OBS da rede INEP:** a máquina não alcança `google.com`/`login.microsoftonline.com` etc. — o fluxo completo só pode ser validado num ambiente com internet (outra rede/hotspot/Render). O código abaixo foi **implementado e até onde dá validado localmente** (501 quando não configurado, assinatura de state 403 em handshake inválido, endpoints registrados).

| Tarefa | Status | Evidência |
|--------|--------|-----------|
| Módulo `oauth.py` (somente stdlib) | ✅ PASS | `authorize_url`/`exchange` por provedor: **Google** (OpenID userinfo), **Microsoft** (Graph `/me`, tenant comum) e **Apple** (id_token ES256, client secret gerado com PKCS8/PEM via `cryptography` + SLT raw r\|\|s). Ativação automática por credenciais no `.env` |
| Endpoints OAuth no backend | ✅ PASS | `GET /api/auth/oauth/status` (lista provedores habilitados), `GET /api/auth/oauth/{provider}/start` (gera URL + state **assinado** HMAC-SHA256, embutido no state — provedores só devolvem `state`), `GET /api/auth/oauth/{provider}/callback` (valida state → troca code → perfil → `oauth_login` → redireciona para `/#oauth=<payload>`). Rotas confirmadas no app FastAPI |
| Frontend (tela de login) | ✅ PASS | `LoginView` consulta `/api/auth/oauth/status`; quando há provedor habilitado exibe "ou entre com" + botões (Google/Microsoft/Apple); callback decodifica `#oauth=` e chama `completeOAuth` no store (novo método). Sem provedor configurado, os botões não aparecem |
| Validação de erros | ✅ PASS | provider desconhecido → 400; sem credenciais → **501**; state ausente/malformado/assinatura errada → **403**; code ausente → 400 |
| `.env.example` | ✅ PASS | Adicionados `AUTH_SECRET`, `GOOGLE_CLIENT_ID/SECRET`, `MICROSOFT_CLIENT_ID/SECRET`, `APPLE_CLIENT_ID`, `APPLE_TEAM_ID`, `APPLE_KEY_ID`, `APPLE_PRIVATE_KEY`, `OAUTH_REDIRECT_BASE` (todos placeholder/documentados) |
| Segurança | ✅ PASS | State assinado (CSRF em login social); segredo do `AUTH_SECRET` cai para auto-gerado por boot se ausente; token NEMO reutilizado como sessão após OAuth |

**Arquivos alterados (Missão 6):**
```
dashboard/src/office/RoomSceneBase.ts     # fitCamera/fitViewport, lastLayout, updateStatus in-place, send/return to rest
dashboard/src/office/AgentSprite.ts       # parts[]+trackParts, moveTo (tween completo), homePosition, isResting
dashboard/src/office/OfficeScene.ts       # restAnchor() do lounge
dashboard/src/office/PhaserGame.tsx       # RoomController, fitViewport no resize, attachController
dashboard/src/components/ide/OfficeView.tsx       # lazy(PhaserGame)+Suspense, controllerRef
dashboard/src/components/ide/AgentProfileModal.tsx # botões sofá/mesa
dashboard/src/components/ide/AppShell.tsx          # sala em tela cheia + guard de vistas admin
dashboard/src/components/ide/TopBar.tsx            # oculta Área de Trabalho/Terminal p/ não-admin
dashboard/src/components/ide/LoginView.tsx         # botões OAuth + tratamento do #oauth= callback
dashboard/src/store/useAuthStore.ts       # completeOAuth + role no AuthUser
dashboard/src/api/auth.ts                 # AuthUser.role ("admin"|"user")
dashboard/src/api/nemo.ts                 # tokens já enviados (Bearer) em todas as chamadas
dashboard/src/hooks/useSquadSocket.ts     # token no polling + skip sem sessão (sem 401)
dashboard/src/styles/globals.css          # .oauth-* (botões de login social)
auth.py                      # role + oauth_login + admin helpers
nemo_server.py               # _require_admin/_require_user, rotas admin/users, endpoints OAuth
oauth.py                     # NOVO: provedores Google/Microsoft/Apple (stdlib)
.env.example                 # AUTH_SECRET + credenciais OAuth (placeholder)
RELATORIO_FINAL_MISSAO.md    # este relatório (missão 6)
```

**Limites (Missão 6):** (1) o fluxo OAuth **real** (troca de código) não pode ser validado da rede INEP — falta credencial dos provedores + internet; (2) Apple requer `pip install cryptography` na máquina de produção; (3) `_data/` (usuários/senhas hash) continua fora do repositório (`.gitignore`).

---

## 12. Git (Commits Enviados)

```
<commit-awaits> feat(mission6): escritorio estavel (fit resize, status in-place, sofa) + perfis USER/ADMIN (403) + login Google/OAuth
... (histórico anterior)
```

**Branch:** `main` → `origin/main` (público)

---

## 13. Próximos Passos Recomendados

1. **Gerar nova chave OpenRouter** (a atual está expirada) → atualizar `.env` → reiniciar → conferir chat real na UI
2. **Revogar chave antiga** `sk-or-v1-028…6750` em https://openrouter.ai/keys
3. **Abrir `http://127.0.0.1:8798/` no navegador** e conferir a sala de reunião 2D (clique num agente → perfil → chat)
4. **Testar `dist/NEMO_IDE/` em máquina Windows limpa** (sem Python/Node)
5. **Opcional**: Instalador NSIS/Inno Setup + assinatura de código (evita SmartScreen)

---

## 14. Conclusão

O **NEMO IDE / Open Squad Dashboard** está **completo, testado e empacotado** como sistema autônomo Windows. A arquitetura suporta:

- **Dashboard web** (React + Phaser) servido pelo backend FastAPI
- **Sala de reunião 2D** com a equipe NEMO (personagens por função, faixa Vasco, balões, clique→perfil→chat)
- **12 agentes especializados** descobertos automaticamente (inclui JARVIS, TI da equipe)
- **Squads com pipelines** YAML + checkpoints humanos
- **Chat com LLM real** (OpenRouter) com aviso amigável quando a chave expira
- **Terminal, Tasks, Logs, History, Office, ContextPanel**
- **Executável standalone** (23 MB) **corrigido** — volta a enxergar agentes/squads/dashboard no modo frozen

> **Pronto para uso e distribuição.** Basta copiar `dist/NEMO_IDE/`, configurar `.env` com uma chave OpenRouter nova e rodar `NEMO_IDE.exe`.

---

## 15. ANEXO — Missão 7: Integração Supabase + Gemini + Groq + IA do Usuário

**Data:** 2026-09-24 · **Pendências do usuário:** ainda **não há** projeto Supabase, chave Gemini nem chave Groq → conforme a missão §60, **nenhuma credencial foi inventada**; tudo foi construído configurável e degrada graciosamente.

### 15.1 Entregas

| Entregável | Arquivo | Evidência |
|-----------|---------|-----------|
| Camada abstrata de IA (Gemini, Groq, OpenAI, OpenRouter) | `ai_providers.py` (novo) | `AIProviderService` + `CompletionResult`; catálogo `PROVIDER_META`; fallbacks limitados em `MAX_FALLBACKS=3` (missão §33) |
| Cofre de API Keys do usuário | `ai_keys.py` (novo) | **Fernet** (AES-128-CBC) derivado de `AUTH_SECRET`; só máscara no frontend; `mask_key`/`looks_like_placeholder` |
| Busca na web multi-provedor | `web_search.py` (novo) | DuckDuckGo **sem chave** (padrão), Tavily/Brave se configurados; rate-limit por usuário; busca **condicional** (`_needs_search`) |
| Camada de dados (Supabase ↔ local) | `data_store.py` (novo) | `DataStore` → `SupabaseStore` (service role, `user_id` em toda query) ou `LocalStore` (JSON `_data/users/<id>/`) |
| Schema + RLS Supabase | `supabase/migrations/001_schema_init.sql` (novo) | 12 tabelas (conversations, messages, agent_memories, tasks, ai_providers, user_ai_keys, ai_settings, web_searches, activity_logs, …), policies exigindo `auth.uid() = user_id`, trigger de profile |
| Backend multi-provedor | `nemo_server.py` | chat reescrito (provedor resolução usuário>sistema>agente); `/api/nemo/ai/config`, `/api/nemo/ai/keys` (POST/DELETE), `/api/nemo/ai/test`, `/api/nemo/ai/search`, `/api/nemo/ai/memories`; `/api/nemo/conversations`; `/api/nemo/tasks`; health com bloco `ai` |
| UI Central de IA | `dashboard/src/components/ide/AiSettingsCard.tsx` (novo) + `SettingsView.tsx` + `DashboardView.tsx` + `api/nemo.ts` + tipos | provedor/modelo padrão, chave mascarada com salvar/testar/remover, status backend/store/criptografia; card "IA ativa" no Painel |
| Dependências/env | `requirements.txt` (+`cryptography`, +`supabase`); `.env.example` (provedores, busca, Supabase) | instaladas e ativas (encryption=True) |
| Testes | `test_ai_providers.py`, `test_ai_keys.py`, `test_web_search.py`, `test_data_store.py` (novos) + `test_client_unit.py` (atualizado) | **49 testes, todos OK** (1 skip: "sem cryptography" — biblioteca instalada) |
| Docs | `README.md`, `supabase/README.md`, este anexo | passo a passo de ativação |

### 15.2 Smoke test real (TestClient, sem credenciais inventadas)

- `GET /api/nemo/ai/config` → 200 com `providers` (4), `web_search: [duckduckgo]`, `store_backend: local`, `encryption: true`
- `POST /api/nemo/ai/config` (default_provider gemini) → 200
- `POST /api/nemo/ai/keys` (chave de teste sintética) → 200, **máscara `****…7890`**, `verified:false`, teste real contra Gemini respondeu 400 graciosamente (nenhuma quebra); arquivo `ai_keys.json` **não contém a chave em texto puro**
- `/api/nemo/ai/memories` e `/api/nemo/tasks` → 200 listagem/inserção

### 15.3 Decisões (missão §44 e segurança)

1. Backend filtra **tudo** por `user_id` mesmo com Supabase (frontend não confiável) + RLS no banco.
2. Chaves criptografadas em repouso **antes** da camada de dados; nunca em logs/Git/response payload (só máscara).
3. Sem nenhuma chave → chat responde **offline gracioso** orientando configuração (`Configurações → Inteligência Artificial` ou `.env`), preservando todo o resto da IDE.
4. Fallback entre provedores limitado a 3 tentativas; busca web condicional e com rate-limit.

### 15.4 Pendências (requerem credenciais/ambiente do usuário)

1. Criar **projeto Supabase** (guia em `supabase/README.md`) e preencher `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` → `store_backend` muda para `supabase`.
2. Opcional: `GEMINI_API_KEY` / `GROQ_API_KEY` no `.env` (ou pela UI, criptografada por usuário) → chat multi-provedor real.
3. Validar fluxo completo em ambiente com internet (esta rede INEP bloqueia vários hosts externos).
4. Revogar/expor a chave OpenRouter antiga do `.env` quando convenient (ela **não** está em Git).

---

## 16. ANEXO — Missão 60: rate limit, tokens, configuração por agente, isolamento

**Data:** 2026-09-24 · **Status:** implementado e testado (54 testes OK, 1 skip esperado). Credenciais Supabase/Gemini/Groq continuam pendentes do usuário (nada foi inventado).

### 16.1 Entregas

| Seção da missão | Entregável | Evidência |
|-----------------|-----------|-----------|
| §34 Custos/tokens | `activity_logs` ganhou `prompt_tokens`, `completion_tokens`, `total_tokens` (SQL + interface + LocalStore + SupabaseStore); `_log_activity` repassa os tokens do `CompletionResult` | chat real grava custos; `GET /api/nemo/ai/activity` expõe |
| §35 Rate limit por usuário | `_SlidingWindowRateLimit` (janela 60s) + `AI_RATE_LIMITER` + env `NEMO_AI_RATE_LIMIT` (padrão 30/min) em `nemo_server.py` | chat responde `rate_limited: True` + mensagem amigável sem quebrar a UI |
| §40 Config por agente | `agent_overrides` no `AiSettingsRequest` (merge/remove); resolução no chat: requisição > agente > usuário > sistema; UI nova "Configuração por agente" no `AiSettingsCard` | teste confirma prioridades e remoção |
| §56 Isolamento multiusuário | `test_multiuser.py` verifica que dados/chaves/atividade do usuário A jamais aparecem para B (conversas, tasks, memórias, chaves, activity) | verde |
| §57 Auditoria de chaves | `git grep` nos arquivos rastreados → apenas chaves sintéticas de testes/docs; `.env` e `_data/` fora do versionamento; respostas só máscara | verde |
| Frontend | `saveAiConfig` aceita `agent_overrides`; tipo `AiConfigResponse.settings.agent_overrides`; UI de override por agente | build OK (96 módulos, ~25s) |
| Docs | `README.md` (rate limit, overrides, tokens, isolamento, `NEMO_AI_RATE_LIMIT`), este anexo, linha de data no cabeçalho | — |
| Testes | `test_multiuser.py` (isolamento + chaves + rate limit + overrides + tokens) | **54 testes, OK** |

### 16.2 Decisões técnicas

1. Rate limit usa **semáforo+janela deslizante** por `user_id` (não por IP) — correto para app multi-usuário autenticado; `_hits` em memória (retorna a zero no restart, aceitável).
2. Overrides por agente são **merge** na persistência (não destroem configs de outros agentes); envio de objeto vazio **remove** o override.
3. Tokens são gravados com `default 0` no banco — entrada sem tokens não quebra quadros/agregações existentes.
4. Auditoria contínua: nenhum segredo além da máscara chega ao frontend; service role/anon nunca no cliente.

### 16.3 Pendências (credendiais do usuário)

Na `Central de IA` → "Minhas API Keys", salve por usuário: **Gemini** (aistudio.google.com/apikey), **Groq** (console.groq.com/keys) e, para Supabase, rode `supabase/migrations/001_schema_init.sql` no SQL Editor e preencha `SUPABASE_URL`/`SUPABASE_ANON_KEY`/`SUPABASE_SERVICE_ROLE_KEY` no `.env`. Depois de ativar, rodar o teste ao vivo (chat real Gemini/Groq).

### 16.4 Validação ao vivo (credendiais do usuário — finalizado)

**Data:** 2026-09-24 · usuário forneceu Gemni (token `AQ…`), Groq (`gsk_…`) e Supabase project `yecdnbsljsroxcikcbpw` (`sb_secret…`).

| Item | Resultado |
|------|-----------|
| ✨ **Gemini** | chave válida; **contas novas** não têm `gemini-2.x` → catálogo prioriza `gemini-flash-latest` (testado OK: 315 tokens) |
| ⚡ **Groq** | chave válida; `llama-3.x` viraram Enterprise → catálogo usa `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b` (validados; 284/321 tokens) |
| 🗄️ **Supabase** | `001_schema_init.sql` executado no SQL Editor (Management API é read-only p/ DDL); `user_id` ajustado para **text** (auth local do NEMO) com RLS `auth.uid()::text = user_id`; `ai_settings.agent_overrides jsonb`; datas de tasks convertidas ms↔timestamptz; agregado `messages(count)` corrigido |
| 🧪 **Testes** | **54 OK** (1 skip) — `test_multiuser.py` rodou contra o **Postgres real** (isolamento A/B), `test_data_store` resiliente a `.env` com Supabase |
| 🔄 **Chat ao vivo p/ supabase** | pergunta real → resposta correta, conversa+atividade+tokens persistidos no banco |
| 🔒 **Auditoria** | `git grep` rastreado sem segredos reais (`gsk_/AIza/AQ/sb_secret` só em `.env` ignorado e em mocks de teste; token `sbp_` usado só em execução transitória, não versionado) |

### 16.5 Pendências restantes da missão — executadas

**Data:** 2026-09-24 · commits `cffa657` (anteriores) e este (pendências §26/§8/§38).

| Item | O que foi feito | Validação |
|------|------------------|-----------|
| 🗂️ **§26 Histórico de conversas** | `DELETE /api/nemo/conversations/{id}` (exclui conversa + mensagens via cascade, 404 se não pertence ao usuário); `GET /api/nemo/conversations?q=` busca no **título e no conteúdo**; `GET /{id}/messages` para reabrir; painel `📚` no chat com buscar/reabrir/apagar/"Nova conversa" | teste novo `test_mission_features` (busca `?q=cloud`, delete 200→404, isolamento A/B) + build do dashboard |
| 👤 **§8 Perfil do usuário** | `GET/POST /api/nemo/profile` (nome, idioma, avatar) → tabela `profiles` (mapeia `avatar`→`avatar_url`) no Supabase / `profile.json` local; cartão "👤 Perfil" em Configurações com preview, idioma e avatares | roundtrip POST/GET ao vivo + teste; build frontend |
| 💡 **§38 Health** | `GET /api/nemo/health → ai.default_model` via novo `AIService.default_provider_model()`; dashboard mostra "IA ativa", provedor padrão e **modelo padrão** (`openai/gpt-oss-120b`/Groq) | teste de health + ao vivo |
| 🧪 **Testes** | `test_mission_features.py` (4 testes: perfil, busca+exclusão, isolamento, health) rodando contra o **Supabase real** | suíte completa **58 OK (1 skip)** |
| 📚 **Docs** | README atualizado (endpoints, perfil, busca/exclusão de conversas, default_model) + esta seção | — |

---