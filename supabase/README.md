# Supabase — passagem do NEMO para nuvem (opcional)

O NEMO funciona 100% local (JSON em `_data/`) sem Supabase. Este guia é só para quem
quer persistir conversas, memórias, chaves, tarefas, atividade e buscas em **PostgreSQL
com Row Level Security (RLS)**.

> Precisará de contas externas (Supabase, e depois chaves de IA — Gemini/Groq/OpenRouter)
> para ativar os recursos pagos/free-tiers. Nada neste repositório inventa credenciais.

## 1. Criar o projeto

1. Acesse https://supabase.com e crie uma conta (é gratuito para começar).
2. **New Project** → escolha nome, região e senha do banco.
3. Anote a **Project URL** (ex.: `https://xyzcompany.supabase.co`) e, em
   **Settings → API Keys**:
   - `anon public` → **`SUPABASE_ANON_KEY`**
   - `service_role` (secret) → **`SUPABASE_SERVICE_ROLE_KEY`** *(nunca no frontend!)*

## 2. Criar o schema (migration)

1. No painel: **SQL Editor → New query**.
2. Cole o conteúdo de [`migrations/001_schema_init.sql`](migrations/001_schema_init.sql).
3. **Run**. O script cria as tabelas, as policies de **RLS** (exigem `auth.uid()` igual a `user_id`)
   e um trigger que cria `profiles` automaticamente quando um usuário se registra pelo Auth Supabase.

## 3. Configurar o NEMO

Edite o `.env`:

```ini
SUPABASE_URL=https://xyzcompany.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...   # service_role — só no backend
```

No boot, `data_store.py` detecta os valores e usa **SupabaseStore**; caso contrário mantém
o fallback local. O health `/api/nemo/health` informa `store_backend`.

> **Por que service_role no backend?** O frontend não é confiável: mesmo com Supabase,
> o **backend filtra toda consulta por `user_id`** do token do NEMO (missão §44), e o banco
> ainda tem RLS pedindo `auth.uid()` — assim nem um cliente anon direto leria dados alheios.

## 4. Segurança de API Keys

- As chaves de IA do usuário são **criptografadas com Fernet** (chave derivada de
  `AUTH_SECRET`) **antes** de entrarem na camada de dados — no Supabase ficam na coluna
  `encrypted_key` de `user_ai_keys`, nunca em texto puro.
- Mantenha `AUTH_SECRET` **forte e estável**: trocá-lo invalida o que estiver armazenado.
- `service_role` e `SUPABASE_SERVICE_ROLE_KEY` jamais devem ir a logs ou ao repositório.

## 5. Tabelas criadas

| Tabela | Conteúdo | RLS |
|--------|----------|-----|
| `profiles` | perfil do usuário (criado por trigger) | owner |
| `agents`, `agent_settings` | personas/config (seed) | autenticados |
| `conversations`, `messages` | chats persistidos | `user_id = auth.uid()` |
| `agent_memories` | memória dos agentes | `user_id = auth.uid()` |
| `tasks` | tarefas priorizadas | `user_id = auth.uid()` |
| `calendar_events` | eventos do calendário | `user_id = auth.uid()` |
| `ai_providers` | catálogo de provedores (seed) | autenticados |
| `user_ai_keys` | chaves do usuário (`encrypted_key`) | `user_id = auth.uid()` |
| `ai_settings` | preferências de IA por usuário | `user_id = auth.uid()` |
| `web_searches`, `activity_logs` | buscas e histórico | `user_id = auth.uid()` |

## 6. Voltar ao local (sem nuvem)

Apague `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` do `.env` (ou deixe vazios) e reinicie —
volta automaticamente ao `LocalStore`.