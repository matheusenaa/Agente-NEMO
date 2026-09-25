-- ============================================================================
-- NEMO — Supabase schema (migration 001)
-- Núcleo de dados multiusuário: perfis, agentes, conversas, memórias, tarefas,
-- calendário, chaves de IA (criptografadas), preferências, logs e buscas.
--
-- Executar no SQL Editor do Supabase (ou com supabase db push).
-- RLS é OBRIGATÓRIO (missão §6): usuário só vê a própria linha (auth.uid()).
-- O backend usa a service role key e faz a MESMA filtragem por user_id
-- (frontend não é confiável — missão §44).
-- ============================================================================

-- Extensões comuns do Supabase (habilitadas por padrão no projeto).
create extension if not exists "pgcrypto";
create extension if not exists "uuid-ossp";

-- ----------------------------------------------------------------------------
-- 1. Perfis (1:1 com auth.users)
-- ----------------------------------------------------------------------------
create table if not exists public.profiles (
    id          uuid primary key references auth.users (id) on delete cascade,
    name        text not null default '',
    email       text,
    avatar_url  text,
    language    text not null default 'pt-BR',
    role        text not null default 'user' check (role in ('user', 'admin')),
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- 2. Catálogo de agentes (global — não pertence a um usuário)
-- ----------------------------------------------------------------------------
create table if not exists public.agents (
    id            text primary key,
    name          text not null,
    title         text,
    category      text,
    icon          text,
    role          text,
    default_model text,
    tools         jsonb not null default '[]'::jsonb,
    active        boolean not null default true,
    created_at    timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- 3. Configurações de IA por agente por usuário
-- ----------------------------------------------------------------------------
create table if not exists public.agent_settings (
    user_id   uuid not null references auth.users (id) on delete cascade,
    agent_id  text not null references public.agents (id) on delete cascade,
    provider  text,
    model     text,
    temperature real,
    tools     jsonb,
    enabled   boolean not null default true,
    updated_at timestamptz not null default now(),
    primary key (user_id, agent_id)
);

-- ----------------------------------------------------------------------------
-- 4. Memória permanente dos agentes (por usuário — missão §§24-25)
-- ----------------------------------------------------------------------------
create table if not exists public.agent_memories (
    id         uuid primary key default gen_random_uuid(),
    user_id    uuid not null references auth.users (id) on delete cascade,
    agent_id   text not null,
    kind       text not null default 'obs',   -- obs | preferencia | instrucao | aprendizado
    content    text not null,
    created_at timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- 5. Conversas e mensagens
-- ----------------------------------------------------------------------------
create table if not exists public.conversations (
    id         uuid primary key default gen_random_uuid(),
    user_id    uuid not null references auth.users (id) on delete cascade,
    agent_id   text not null,
    title      text not null default 'Nova conversa',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.messages (
    id              uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references public.conversations (id) on delete cascade,
    user_id         uuid not null references auth.users (id) on delete cascade,
    role            text not null check (role in ('user', 'assistant', 'system')),
    content         text not null,
    meta            jsonb not null default '{}'::jsonb,
    created_at      timestamptz not null default now()
);
create index if not exists idx_messages_conversation on public.messages (conversation_id, created_at);

-- ----------------------------------------------------------------------------
-- 6. Tarefas
-- ----------------------------------------------------------------------------
create table if not exists public.tasks (
    id         text primary key,
    user_id    uuid not null references auth.users (id) on delete cascade,
    title      text not null,
    priority   text not null default 'normal',
    agent_id   text not null default 'nemo',
    status     text not null default 'pending' check (status in ('pending', 'running', 'done', 'error', 'cancelled')),
    created_at timestamptz not null default now(),
    due_date   timestamptz,
    done_at    timestamptz
);
create index if not exists idx_tasks_user on public.tasks (user_id, created_at desc);

-- ----------------------------------------------------------------------------
-- 7. Calendário
-- ----------------------------------------------------------------------------
create table if not exists public.calendar_events (
    id         uuid primary key default gen_random_uuid(),
    user_id    uuid not null references auth.users (id) on delete cascade,
    title      text not null,
    description text,
    event_date date not null,
    event_time text not null default '09:00',
    duration_min int not null default 60,
    category   text not null default 'outro',
    agent_id   text not null default 'nemo',
    remind_min int not null default 15,
    created_at timestamptz not null default now()
);
create index if not exists idx_calendar_user_date on public.calendar_events (user_id, event_date);

-- ----------------------------------------------------------------------------
-- 8. Provedores de IA (catálogo) e chaves dos usuários (criptografadas)
-- ----------------------------------------------------------------------------
create table if not exists public.ai_providers (
    id        text primary key,
    name      text not null,
    enabled   boolean not null default true,
    system_key boolean not null default false,  -- define se o backend possui chave própria
    models    jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now()
);

-- A API Key é recebida do frontend e encriptada no BACKEND (Fernet/AES) antes
-- de chegar aqui. Nunca armazenamos texto puro (missão §17).
create table if not exists public.user_ai_keys (
    user_id       uuid not null references auth.users (id) on delete cascade,
    provider      text not null,
    encrypted_key text not null,
    masked        text not null,       -- ex.: ************ABCD
    model         text not null default '',
    verified      boolean not null default false,
    updated_at    timestamptz not null default now(),
    primary key (user_id, provider)
);

-- ----------------------------------------------------------------------------
-- 9. Preferências de IA por usuário
-- ----------------------------------------------------------------------------
create table if not exists public.ai_settings (
    user_id         uuid primary key references auth.users (id) on delete cascade,
    default_provider text,
    default_model    text,
    updated_at       timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- 10. Buscas na web (fontes — missão §50) e logs de atividade (§36)
-- ----------------------------------------------------------------------------
create table if not exists public.web_searches (
    id         uuid primary key default gen_random_uuid(),
    user_id    uuid not null references auth.users (id) on delete cascade,
    agent_id   text not null,
    query      text not null,
    provider   text not null,
    results    jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists public.activity_logs (
    id         bigint generated always as identity primary key,
    user_id    uuid not null references auth.users (id) on delete cascade,
    agent_id   text,
    operation  text not null,
    status     text not null,
    provider   text not null default '',
    model      text not null default '',
    latency_ms real not null default 0,
    prompt_tokens    bigint not null default 0,
    completion_tokens bigint not null default 0,
    total_tokens     bigint not null default 0,
    created_at timestamptz not null default now()
);
create index if not exists idx_activity_user on public.activity_logs (user_id, created_at desc);

-- ============================================================================
-- ROW LEVEL SECURITY (OBRIGATÓRIO — missão §6, §43)
-- ============================================================================

-- Habilitar RLS em TODAS as tabelas com user_id.
alter table public.profiles        enable row level security;
alter table public.agents          enable row level security;
alter table public.agent_settings  enable row level security;
alter table public.agent_memories  enable row level security;
alter table public.conversations   enable row level security;
alter table public.messages        enable row level security;
alter table public.tasks           enable row level security;
alter table public.calendar_events enable row level security;
alter table public.ai_providers    enable row level security;
alter table public.user_ai_keys    enable row level security;
alter table public.ai_settings     enable row level security;
alter table public.web_searches    enable row level security;
alter table public.activity_logs   enable row level security;

-- helper: o usuário autenticado só enxerga as PRÓPRIAS linhas.
create or replace function public.is_owner(uid uuid) returns boolean
language sql security definer stable as $$
    select auth.uid() = uid;
$$;

-- --- profiles (dono = a própria linha) ---
create policy "profiles select own"    on public.profiles for select using (auth.uid() = id);
create policy "profiles update own"    on public.profiles for update using (auth.uid() = id) with check (auth.uid() = id);
create policy "profiles insert own"    on public.profiles for insert with check (auth.uid() = id);

-- --- agentes: qualquer usuário autenticado lê (catálogo); só alterações por trigger/admin ---
create policy "agents select authed" on public.agents for select using (auth.role() = 'authenticated');

-- --- agent_settings: dono ---
create policy "agent_settings select own" on public.agent_settings for select using (auth.uid() = user_id);
create policy "agent_settings insert own" on public.agent_settings for insert with check (auth.uid() = user_id);
create policy "agent_settings update own" on public.agent_settings for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "agent_settings delete own" on public.agent_settings for delete using (auth.uid() = user_id);

-- --- agent_memories: dono ---
create policy "memories select own" on public.agent_memories for select using (auth.uid() = user_id);
create policy "memories insert own" on public.agent_memories for insert with check (auth.uid() = user_id);
create policy "memories update own" on public.agent_memories for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "memories delete own" on public.agent_memories for delete using (auth.uid() = user_id);

-- --- conversations / messages: dono ---
create policy "conversations select own" on public.conversations for select using (auth.uid() = user_id);
create policy "conversations insert own" on public.conversations for insert with check (auth.uid() = user_id);
create policy "conversations update own" on public.conversations for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "conversations delete own" on public.conversations for delete using (auth.uid() = user_id);

create policy "messages select own" on public.messages for select using (auth.uid() = user_id);
create policy "messages insert own" on public.messages for insert with check (auth.uid() = user_id);
create policy "messages delete own" on public.messages for delete using (auth.uid() = user_id);

-- --- tasks: dono ---
create policy "tasks select own" on public.tasks for select using (auth.uid() = user_id);
create policy "tasks insert own" on public.tasks for insert with check (auth.uid() = user_id);
create policy "tasks update own" on public.tasks for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "tasks delete own" on public.tasks for delete using (auth.uid() = user_id);

-- --- calendar_events: dono ---
create policy "calendar select own" on public.calendar_events for select using (auth.uid() = user_id);
create policy "calendar insert own" on public.calendar_events for insert with check (auth.uid() = user_id);
create policy "calendar update own" on public.calendar_events for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "calendar delete own" on public.calendar_events for delete using (auth.uid() = user_id);

-- --- ai_providers: catálogo (leitura para autenticados) ---
create policy "ai_providers select authed" on public.ai_providers for select using (auth.role() = 'authenticated');

-- --- user_ai_keys: dono (e somente máscaras vão ao frontend) ---
create policy "keys select own" on public.user_ai_keys for select using (auth.uid() = user_id);
create policy "keys insert own" on public.user_ai_keys for insert with check (auth.uid() = user_id);
create policy "keys update own" on public.user_ai_keys for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "keys delete own" on public.user_ai_keys for delete using (auth.uid() = user_id);

-- --- ai_settings: dono ---
create policy "ai_settings select own" on public.ai_settings for select using (auth.uid() = user_id);
create policy "ai_settings insert own" on public.ai_settings for insert with check (auth.uid() = user_id);
create policy "ai_settings update own" on public.ai_settings for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "ai_settings delete own" on public.ai_settings for delete using (auth.uid() = user_id);

-- --- web_searches / activity_logs: dono ---
create policy "searches select own" on public.web_searches for select using (auth.uid() = user_id);
create policy "searches insert own" on public.web_searches for insert with check (auth.uid() = user_id);
create policy "searches delete own" on public.web_searches for delete using (auth.uid() = user_id);

create policy "activity select own" on public.activity_logs for select using (auth.uid() = user_id);
create policy "activity insert own" on public.activity_logs for insert with check (auth.uid() = user_id);

-- ----------------------------------------------------------------------------
-- NOTA: ao criar um usuário no Supabase Auth, disparar o perfil automaticamente.
-- Caso o projeto use o auto (hook), rode no SQL Editor:
--   create table if not exists public.profiles (...);  (já criada acima)
-- Habilitar em Authentication → Hooks (custom access token) ou usar um trigger:
-- ----------------------------------------------------------------------------
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
    insert into public.profiles (id, name, email)
    values (new.id, coalesce(new.raw_user_meta_data->>'name', ''), new.email)
    on conflict (id) do nothing;
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute procedure public.handle_new_user();