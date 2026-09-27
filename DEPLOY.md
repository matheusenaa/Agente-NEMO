# NEMO — Guia de Deploy

## Visão Geral

Este guia cobre o deploy do NEMO em produção, incluindo backend (FastAPI), frontend (React PWA), banco de dados (Supabase) e aplicativos mobile (Capacitor).

## Arquitetura de Deploy

```
┌─────────────────────────────────────────────────────────────────┐
│                        PRODUÇÃO                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │   USUÁRIOS   │    │   CDN/EDGE   │    │  MONITORING  │     │
│  │  (Web/Mobile)│◀──▶│  (Cloudflare)│    │  (Sentry)    │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
│         │                   │                   │               │
│         ▼                   ▼                   ▼               │
│  ┌──────────────────────────────────────────────────────┐     │
│  │                    RENDER.COM                         │     │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │     │
│  │  │   BACKEND   │  │  FRONTEND   │  │  WORKERS    │   │     │
│  │  │  (FastAPI)  │  │  (Static)   │  │  (Opcional) │   │     │
│  │  │  :8798      │  │  (dist/)    │  │             │   │     │
│  │  └─────────────┘  └─────────────┘  └─────────────┘   │     │
│  └──────────────────────────────────────────────────────┘     │
│         │                   │                   │               │
│         ▼                   ▼                   ▼               │
│  ┌──────────────────────────────────────────────────────┐     │
│  │                    SUPABASE                           │     │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │     │
│  │  │ PostgreSQL  │  │    Auth     │  │   Storage   │   │     │
│  │  │  (Dados)    │  │  (Usuários) │  │  (Arquivos) │   │     │
│  │  └─────────────┘  └─────────────┘  └─────────────┘   │     │
│  └──────────────────────────────────────────────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Checklist Pré-Deploy

### 1. Variáveis de Ambiente Obrigatórias

```env
# ===========================================
# BACKEND (Render Environment Variables)
# ===========================================

# Autenticação
AUTH_SECRET=gere_com: python -c "import secrets; print(secrets.token_urlsafe(48))"
NEMO_ADMIN_EMAIL=matheusenaa@gmail.com
NEMO_OPEN_REGISTRATION=0  # 0 = só admin cria contas

# IA (pelo menos UMA)
OPENROUTER_API_KEY=sk-or-v1-...
# OU
GEMINI_API_KEY=...
GROQ_API_KEY=...
OPENAI_API_KEY=...

# OpenRouter headers (opcional mas recomendado)
OPENROUTER_HTTP_REFERER=https://seu-app.onrender.com
OPENROUTER_APP_TITLE=NEMO AI Studio

# Supabase (OBRIGATÓRIO para produção)
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIs...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIs...

# Rate Limits
NEMO_AI_RATE_LIMIT=30
NEMO_API_RATE_LIMIT=120
NEMO_SYNC_RATE_LIMIT=60

# CORS (domínio de produção)
CORS_ORIGINS=https://seu-app.onrender.com

# OAuth (opcional)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
MICROSOFT_CLIENT_ID=...
MICROSOFT_CLIENT_SECRET=...
APPLE_CLIENT_ID=...
APPLE_TEAM_ID=...
APPLE_KEY_ID=...
APPLE_PRIVATE_KEY=...
OAUTH_REDIRECT_BASE=https://seu-app.onrender.com
```

### 2. Supabase Setup

```sql
-- 1. Criar projeto em https://supabase.com
-- 2. SQL Editor → Execute migrations em ordem:

-- Migration 001: Schema principal
\i supabase/migrations/001_schema_init.sql

-- Migration 002: Auth tables (usuários/sessões persistidas)
\i supabase/migrations/002_auth_tables.sql

-- Migration 003: Offline-first sync support
\i supabase/migrations/003_offline_sync.sql

-- 3. Verificar RLS habilitado em todas as tabelas
SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';

-- 4. Configurar Auth Providers (se usar OAuth)
-- Authentication → Providers → Google/Microsoft/Apple
```

### 3. Build Local (Validação)

```bash
# Backend
cd NEMO
python -m pytest test_client_unit.py -v  # Testes passam?

# Frontend
cd dashboard
npm run build  # Build sem erros TypeScript/Vite?

# Verificar build
ls -la dist/  # index.html, assets/, manifest.webmanifest, sw.js
```

---

## Deploy no Render (Recomendado)

### Opção A: Blueprint (render.yaml) - Mais Fácil

```bash
# 1. Push para GitHub
git add .
git commit -m "Deploy ready"
git push origin main

# 2. No Render Dashboard:
# - New → Blueprint
# - Conecta repositório GitHub
# - Render detecta render.yaml automaticamente
# - Clica "Apply"

# 3. Configure Environment Variables no Render:
# Settings → Environment → Add Environment Variable
# (Copie da seção "Variáveis de Ambiente Obrigatórias" acima)
```

**render.yaml já incluído no projeto:**
```yaml
services:
  - type: web
    name: nemo-ide
    runtime: python
    plan: free
    region: oregon
    buildCommand: |
      pip install -r requirements.txt
      cd dashboard && npm install && npm run build && cd ..
    startCommand: uvicorn nemo_server:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /api/nemo/health
    envVars:
      - key: PYTHON_VERSION
        value: 3.12.10
      - key: OPENROUTER_API_KEY
        sync: false
      # ... demais vars
```

### Opção B: Manual Web Service

```bash
# 1. Render Dashboard → New → Web Service
# 2. Conecta GitHub repo
# 3. Configuração:
#    Name: nemo-ide
#    Runtime: Python 3
#    Build Command: pip install -r requirements.txt && cd dashboard && npm install && npm run build && cd ..
#    Start Command: uvicorn nemo_server:app --host 0.0.0.0 --port $PORT
#    Health Check Path: /api/nemo/health
#    Plan: Free (ou Starter para custom domain)

# 4. Environment Variables → Add (todas da lista acima)
# 5. Deploy!
```

### Opção C: Docker (Alternativo)

```dockerfile
# Dockerfile (raiz do projeto)
FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y \
    nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Frontend build
COPY dashboard/ dashboard/
RUN cd dashboard && npm ci && npm run build

# Backend
COPY . .
EXPOSE 8798

CMD ["uvicorn", "nemo_server:app", "--host", "0.0.0.0", "--port", "8798"]
```

```bash
# Build
docker build -t nemo-ide .

# Run
docker run -p 8798:8798 \
  -e OPENROUTER_API_KEY=... \
  -e SUPABASE_URL=... \
  -e SUPABASE_SERVICE_ROLE_KEY=... \
  nemo-ide
```

---

## Deploy Mobile

### Android (APK/AAB)

```bash
# 1. Build frontend
cd dashboard && npm run build

# 2. Sync Capacitor
npx cap sync android

# 3. Debug APK
cd android && ./gradlew assembleDebug
# Output: app/build/outputs/apk/debug/app-debug.apk

# 4. Release AAB (Play Store)
# Configure signing em android/app/build.gradle
./gradlew bundleRelease
# Output: app/build/outputs/bundle/release/app-release.aab
```

### iOS (Xcode)

```bash
# 1. Build & Sync
cd dashboard && npm run build && npx cap sync ios

# 2. Abre no Xcode
npx cap open ios

# 3. No Xcode:
# - Product → Archive
# - Distribute App → App Store Connect
# - Upload → TestFlight → Review
```

---

## Domínio Personalizado

### Render + Cloudflare (Recomendado)

```bash
# 1. No Render: Settings → Custom Domains → Add
#    Domain: nemo.seudominio.com

# 2. No Cloudflare DNS:
#    Type: CNAME
#    Name: nemo
#    Target: seu-app.onrender.com
#    Proxy: ON (Orange cloud)

# 3. SSL: Automatic (Cloudflare → Render)

# 4. Atualize variáveis:
CORS_ORIGINS=https://nemo.seudominio.com
OPENROUTER_HTTP_REFERER=https://nemo.seudominio.com
OAUTH_REDIRECT_BASE=https://nemo.seudominio.com
```

---

## Monitoramento & Logs

### Render Logs

```bash
# Dashboard → Logs
# - Build logs
# - Runtime logs (stdout/stderr)
# - Live tail disponível
```

### Health Check

```bash
# Endpoint: GET /api/nemo/health
# Response:
{
  "project": "NEMO IDE",
  "version": "1.0.0",
  "api_key_configured": true,
  "ai": {
    "providers_configured": ["openrouter"],
    "default_provider": "openrouter",
    "default_model": "deepseek/deepseek-chat"
  },
  "store_backend": "supabase",
  "authenticated": false
}
```

### Sentry (Opcional)

```bash
# 1. Crie projeto em sentry.io
# 2. Backend: pip install sentry-sdk
# 3. No nemo_server.py:
import sentry_sdk
sentry_sdk.init(dsn="https://...@sentry.io/...", traces_sample_rate=0.1)

# 4. Frontend: npm install @sentry/react
# 5. main.tsx:
import * as Sentry from "@sentry/react";
Sentry.init({ dsn: "https://...@sentry.io/..." });
```

### Uptime Monitoring

```bash
# UptimeRobot / Better Uptime / Pingdom
# Monitor: GET https://seu-app.onrender.com/api/nemo/health
# Intervalo: 5 min
# Alert: Email/Slack/Discord se down > 2 min
```

---

## Backup & Recovery

### Supabase Backup

```bash
# Automático: Supabase faz backup diário (7 dias retenção no Free)
# Manual: Settings → Database → Backups → Create Backup

# Restore: Settings → Database → Backups → Restore
# ⚠️ Restore substitui TODOS os dados
```

### Backup de Arquivos Locais (Development)

```bash
# Antes de mudanças estruturais:
cp -r _data _data_backup_$(date +%Y%m%d_%H%M%S)

# Restore:
rm -rf _data && cp -r _data_backup_20260115_143000 _data
```

---

## Troubleshooting Deploy

| Erro | Causa | Solução |
|------|-------|---------|
| `Module not found: nemo_server` | Working dir errado | `cd /opt/render/project/src && uvicorn nemo_server:app` |
| `npm: command not found` | Node não instalado | Build Command deve ter `npm install` |
| `SUPABASE_URL not set` | Env var faltando | Settings → Environment → Add |
| `CORS error` | Origin não permitido | Adicione domínio no `CORS_ORIGINS` |
| `Health check failed` | App não subiu | Verifique logs, porta `$PORT` |
| `Database connection failed` | Supabase URL/Key errados | Confirme credenciais no Supabase |
| `Static files 404` | Frontend não buildou | `npm run build` antes do start |
| `OAuth callback 404` | Redirect URI mismatch | Configure no Provider + `OAUTH_REDIRECT_BASE` |

---

## Rollback

```bash
# Render: Dashboard → Deploys → Clique no deploy anterior → "Rollback to this deploy"

# Ou git revert:
git revert HEAD
git push origin main  # Trigger novo deploy

# Supabase: Restore backup anterior
# Settings → Database → Backups → Restore
```

---

## Checklist Pós-Deploy

- [ ] Health check `/api/nemo/health` retorna 200
- [ ] Login funciona (admin + usuário comum)
- [ ] Chat IA responde (teste com pergunta simples)
- [ ] PWA instala (ícone na home screen)
- [ ] Offline: desliga Wi-Fi, cria task, reconecta, sync
- [ ] Mobile: APK instala e abre no Android
- [ ] iOS: Build no TestFlight funciona
- [ ] Domínio custom: HTTPS, CORS, OAuth ok
- [ ] Rate limits: não bloqueiam uso normal
- [ ] Logs: sem erros 500 no Render
- [ ] Backup: Supabase backup automático ativo

---

## Custos Estimados (Mensais)

| Serviço | Free Tier | Paid (se necessário) |
|---------|-----------|---------------------|
| **Render Web Service** | 750h/mês, sleep após 15min inativo | $7/mês (Always On, no sleep) |
| **Supabase** | 500MB DB, 1GB bandwidth, 50k MAU | $25/mês (Pro) |
| **Cloudflare** | CDN, DNS, SSL gratuitos | $20/mês (Pro) |
| **Sentry** | 5k errors/mês | $26/mês (Team) |
| **Total Mínimo** | **$0/mês** | ~$78/mês |

---

## Próximos Passos Pós-Deploy

- [ ] Configurar domínio próprio
- [ ] Habilitar Always On no Render ($7/mês)
- [ ] Configurar Sentry para error tracking
- [ ] Configurar uptime monitoring
- [ ] Documentar runbooks de incidentes
- [ ] Testar restore de backup Supabase
- [ ] Configurar CI/CD para auto-deploy em push