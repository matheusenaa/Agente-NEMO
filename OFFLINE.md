# NEMO — Guia Offline-First

## Visão Geral

O NEMO implementa uma arquitetura **offline-first** completa, permitindo que o usuário continue trabalhando mesmo sem conexão com a internet. Os dados são sincronizados automaticamente quando a conexão é restaurada.

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    NEMO CLIENT                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              DataRepository (Interface)              │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │   │
│  │  │ LocalRepo    │  │ RemoteRepo   │  │ SyncRepo   │  │   │
│  │  │ (IndexedDB)  │  │ (REST API)   │  │ (Orquestra)│  │   │
│  │  └──────────────┘  └──────────────┘  └────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
            ┌─────────────┐      ┌─────────────┐
            │  IndexedDB  │      │   BACKEND   │
            │  (Navegador)│      │  (FastAPI)  │
            └─────────────┘      └─────────────┘
                                      │
                              ┌───────┴───────┐
                              ▼               ▼
                        ┌───────────┐   ┌───────────┐
                        │ Supabase  │   │  Sync     │
                        │ (PostgreSQL)│   │ Endpoints │
                        └───────────┘   └───────────┘
```

## Componentes

### 1. IndexedDB (Local Storage)

**Localização:** `dashboard/src/lib/offline/indexedDB.ts`

Armazena todos os dados localmente:
- `conversations` - Conversas com agentes
- `messages` - Mensagens das conversas
- `memories` - Memórias permanentes dos agentes
- `tasks` - Tarefas do usuário
- `events` - Eventos do calendário
- `ai_keys` - Chaves de IA criptografadas
- `ai_settings` - Preferências de IA
- `profile` - Perfil do usuário
- `activity_logs` - Logs de atividade
- `web_searches` - Histórico de buscas
- `sync_queue` - Fila de operações pendentes

### 2. Repository Pattern

**Localização:** `dashboard/src/lib/offline/repository.ts`

Abstração unificada para acesso a dados:

```typescript
interface DataRepository {
  // Conversas
  listConversations(agentId?: string): Promise<AiConversation[]>;
  createConversation(agentId: string, title: string): Promise<AiConversation>;
  // ... demais métodos
  
  // Sync
  enqueueSync(operation, store, data): Promise<string>;
  getPendingSync(limit?): Promise<any[]>;
  markSynced(id): Promise<void>;
}
```

**Implementações:**
- `LocalRepository` - IndexedDB (sempre disponível)
- `RemoteRepository` - REST API (quando online)
- `SyncRepository` - Orquestrador (decide qual usar)

### 3. Sync Engine

**Localização:** `dashboard/src/lib/offline/syncEngine.ts`

Gerencia sincronização automática:

```typescript
// Inicia sync automático (30s intervalo)
syncEngine.startAutoSync(30000);

// Sync manual
const result = await syncEngine.sync();
// result: { success, failed, conflicts, errors }
```

**Estratégias de Conflito:**
- `local-wins` - Dados locais prevalecem
- `remote-wins` - Dados do servidor prevalecem
- `merge` - Merge simples (spread operator)
- `manual` - Resolução manual pelo usuário

### 4. Detecção de Conectividade

**Localização:** `dashboard/src/hooks/useNetworkStatus.ts`

```typescript
const { status, checkConnection } = useNetworkStatus();
// status: "online" | "offline" | "reconnecting" | "syncing"
```

Indicador visual na TopBar:
- 🟢 **Online** - Conectado, sync ativo
- 🟠 **Offline** - Trabalhando localmente
- 🔄 **Reconectando** - Detectou conexão, validando
- 🔄 **Sincronizando** - Sync em progresso

## Fluxo de Dados

### Escrita (Create/Update/Delete)

```
Usuário → SyncRepository → LocalRepo (imediato) → SyncQueue
                                                    │
                              Online? ─────────────┘
                                │
                                ▼
                        SyncEngine (background)
                                │
                                ▼
                        POST /api/nemo/sync/push
                                │
                                ▼
                        Backend aplica operações
                                │
                                ▼
                        Retorna conflitos/versão
```

### Leitura

```
Componente → SyncRepository
                │
          Online? ──Não──▶ LocalRepo (IndexedDB)
                │
               Sim
                │
                ▼
          RemoteRepo (API) → Cache local
```

### Sincronização (Pull)

```
SyncEngine.sync() 
    │
    ├─▶ POST /api/nemo/sync/push (operações locais)
    │
    └─▶ GET /api/nemo/sync/pull?since=version
                │
                ▼
         Backend retorna mudanças
                │
                ▼
         Aplica no LocalRepo
                │
                ▼
         Atualiza sync_version
```

## Backend Sync Endpoints

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/nemo/sync/push` | POST | Envia operações locais |
| `/api/nemo/sync/pull` | GET | Busca mudanças remotas |
| `/api/nemo/sync/conflicts` | POST | Resolve conflitos |

### Push Request
```json
{
  "operations": [
    {
      "operation": "create|update|delete",
      "store": "conversations",
      "data": { "id": "...", "title": "..." },
      "client_id": "uuid-local",
      "timestamp": 1234567890
    }
  ],
  "last_sync": 1234567890
}
```

### Pull Response
```json
{
  "ok": true,
  "changes": {
    "conversations": [...],
    "tasks": [...]
  },
  "server_version": 42
}
```

## Configuração

### Variáveis de Ambiente (Backend)

```env
# Rate limits
NEMO_API_RATE_LIMIT=120      # req/min por IP (endpoints gerais)
NEMO_SYNC_RATE_LIMIT=60      # req/min por IP (sync endpoints)
NEMO_AI_RATE_LIMIT=30        # req/min por usuário (chat IA)
```

### Variáveis de Ambiente (Frontend)

```env
# Configurado automaticamente via VitePWA
# Service Worker: sw.js
# Manifest: manifest.webmanifest
```

## Testando Offline

### Checklist Manual

1. **Abra o NEMO** - `npm run build && python nemo_server.py`
2. **Faça login** - Crie conta ou use admin
3. **Crie dados offline:**
   - [ ] Nova conversa no Chat
   - [ ] Nova tarefa em Tasks
   - [ ] Novo evento no Calendário
   - [ ] Nova memória (ask agent to remember)
4. **Desconecte internet** - Desative Wi-Fi ou use DevTools Network → Offline
5. **Verifique indicador** - TopBar mostra 🟠 Offline
6. **Continue trabalhando** - Crie mais dados
7. **Feche e reabra aba** - Dados persistem (IndexedDB)
8. **Reconecte internet** - Indicador vira 🔄 Syncing → 🟢 Online
9. **Verifique backend** - Dados sincronizados no Supabase

### DevTools Testing

```javascript
// Console do navegador
// Simular offline
navigator.serviceWorker.controller.postMessage({ type: 'SIMULATE_OFFLINE' })

// Ver fila de sync
const db = await idb.openDB('NEMO_OFFLINE_DB', 1);
const queue = await db.getAll('sync_queue');
console.table(queue);

// Forçar sync manual
import { syncEngine } from '@/lib/offline';
await syncEngine.sync();
```

## Estratégia de Conflitos

### Detecção
- **Optimistic Locking** - `sync_version` incrementado a cada update
- Conflito = `server.sync_version > client.sync_version`

### Resolução Automática
1. **Sem conflito** - Aplica direto
2. **Com conflito** - Mantém na fila, notifica usuário
3. **Usuário resolve** - Escolhe estratégia via UI

### Exemplos de Conflito
```
Cenário: Usuário edita tarefa offline + mesmo task editado online
Local:  { id: "t1", title: "Comprar leite", status: "done" }
Server: { id: "t1", title: "Comprar leite e pão", status: "pending" }

Opções:
1. Local-wins  → "Comprar leite" (done)
2. Remote-wins → "Comprar leite e pão" (pending)  
3. Merge       → { title: "Comprar leite e pão", status: "done" }
```

## Limitações Conhecidas

1. **Busca Web** - Não funciona offline (requer API externa)
2. **Chat IA** - Requer conexão (OpenRouter/Gemini/Groq)
3. **Terminal** - Comandos locais funcionam, remotos não
4. **Upload de arquivos** - Aguarda conexão
5. **Notificações Push** - Requer Service Worker ativo + conexão

## Migração de Dados Existentes

Ao ativar offline-first pela primeira vez:

```bash
# 1. Backup dos dados atuais (JSON local)
cp -r _data _data_backup_$(date +%Y%m%d)

# 2. Aplicar migration Supabase (se usar)
# Execute 003_offline_sync.sql no Supabase SQL Editor

# 3. Reiniciar backend
python nemo_server.py

# 4. Build frontend
cd dashboard && npm run build

# 5. Dados locais migram automaticamente no primeiro load
```

## Monitoramento

### Logs de Sync
```javascript
// Frontend - Console
[NEMO] Sync started
[NEMO] Push: 3 ops, 2 ok, 1 conflict
[NEMO] Pull: 5 changes applied
[NEMO] Sync complete: { success: 5, failed: 0, conflicts: 1 }

// Backend - Logs
[SYNC] Push from user u_abc123: 3 ops
[SYNC] Conflict on conversations/t1: version mismatch
[SYNC] Pull for user u_abc123: 5 changes since v40
```

### Métricas Importantes
- `sync_queue` size - Operações pendentes
- `sync_version` - Versão atual do cliente
- Conflicts/hour - Taxa de conflitos
- Sync latency - Tempo total de sync

## Troubleshooting

| Problema | Causa | Solução |
|----------|-------|---------|
| Dados não sincronizam | Service Worker não registrado | Verifique `navigator.serviceWorker.ready` |
| Conflitos frequentes | Edição simultânea mesmo dado | Eduque usuários / use merge |
| Sync travado | Rate limit backend | Aumente `NEMO_SYNC_RATE_LIMIT` |
| Dados perdidos offline | IndexedDB corrompido | `localStorage.clear()` + re-login |
| Indicador não atualiza | Listener não registrado | Verifique `useNetworkStatus` hook |

## Próximos Passos

- [ ] Background Sync API (quando disponível)
- [ ] Compressão de payloads sync
- [ ] Sync seletivo por store
- [ ] Criptografia client-side adicional
- [ ] Métricas Prometheus/Grafana