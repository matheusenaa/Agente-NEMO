-- ============================================================================
-- NEMO — Supabase schema (migration 003)
-- Suporte Offline-First: versionamento otimista, tombstones, metadata de sync
-- Executar APÓS 001_schema_init.sql e 002_auth_tables.sql
-- ============================================================================

-- Extensões necessárias
create extension if not exists "pgcrypto";
create extension if not exists "uuid-ossp";

-- ============================================================================
-- Helper: função para incrementar versão automaticamente
-- ============================================================================
create or replace function public.increment_version()
returns trigger language plpgsql security definer set search_path = public as $$
begin
    new.version = coalesce(old.version, 0) + 1;
    new.updated_at = now();
    new.last_synced = now();
    return new;
end;
$$;

create or replace function public.set_sync_version()
returns trigger language plpgsql security definer set search_path = public as $$
begin
    new.sync_version = (select coalesce(max(sync_version), 0) + 1 from public.sync_metadata where user_id = new.user_id);
    new.last_synced = now();
    return new;
end;
$$;

-- ============================================================================
-- Tabela de metadados de sincronização por usuário
-- ============================================================================
create table if not exists public.sync_metadata (
    user_id       text primary key,
    sync_version  bigint not null default 0,
    last_full_sync timestamptz,
    last_incremental_sync timestamptz,
    device_id     text,
    updated_at    timestamptz not null default now()
);

alter table public.sync_metadata enable row level security;
create policy "sync_metadata own" on public.sync_metadata for all using (auth.uid()::text = user_id) with check (auth.uid()::text = user_id);

-- ============================================================================
-- 1. PROFILES - adicionar versionamento e sync
-- ============================================================================
alter table public.profiles
    add column if not exists version bigint not null default 0,
    add column if not exists sync_version bigint not null default 0,
    add column if not exists last_synced timestamptz,
    add column if not exists deleted boolean not null default false,
    add column if not exists device_id text;

create index if not exists idx_profiles_sync on public.profiles (user_id, sync_version) where not deleted;

create trigger trg_profiles_version
    before update on public.profiles
    for each row execute function public.increment_version();

-- ============================================================================
-- 2. AGENTS - catálogo global, versionamento para cache invalidation
-- ============================================================================
alter table public.agents
    add column if not exists version bigint not null default 0,
    add column if not exists sync_version bigint not null default 0,
    add column if not exists last_synced timestamptz;

create trigger trg_agents_version
    before update on public.agents
    for each row execute function public.increment_version();

-- ============================================================================
-- 3. AGENT_SETTINGS - versionamento
-- ============================================================================
alter table public.agent_settings
    add column if not exists version bigint not null default 0,
    add column if not exists sync_version bigint not null default 0,
    add column if not exists last_synced timestamptz,
    add column if not exists deleted boolean not null default false;

create index if not exists idx_agent_settings_sync on public.agent_settings (user_id, sync_version) where not deleted;

create trigger trg_agent_settings_version
    before update on public.agent_settings
    for each row execute function public.increment_version();

-- ============================================================================
-- 4. AGENT_MEMORIES - versionamento + tombstone
-- ============================================================================
alter table public.agent_memories
    add column if not exists version bigint not null default 0,
    add column if not exists sync_version bigint not null default 0,
    add column if not exists last_synced timestamptz,
    add column if not exists deleted boolean not null default false;

create index if not exists idx_agent_memories_sync on public.agent_memories (user_id, sync_version) where not deleted;

create trigger trg_agent_memories_version
    before update on public.agent_memories
    for each row execute function public.increment_version();

-- ============================================================================
-- 5. CONVERSATIONS - versionamento + tombstone
-- ============================================================================
alter table public.conversations
    add column if not exists version bigint not null default 0,
    add column if not exists sync_version bigint not null default 0,
    add column if not exists last_synced timestamptz,
    add column if not exists deleted boolean not null default false;

create index if not exists idx_conversations_sync on public.conversations (user_id, sync_version) where not deleted;

create trigger trg_conversations_version
    before update on public.conversations
    for each row execute function public.increment_version();

-- ============================================================================
-- 6. MESSAGES - versionamento + tombstone (append-only mostly)
-- ============================================================================
alter table public.messages
    add column if not exists version bigint not null default 0,
    add column if not exists sync_version bigint not null default 0,
    add column if not exists last_synced timestamptz,
    add column if not exists deleted boolean not null default false;

create index if not exists idx_messages_sync on public.messages (user_id, sync_version) where not deleted;

create trigger trg_messages_version
    before update on public.messages
    for each row execute function public.increment_version();

-- ============================================================================
-- 7. TASKS - versionamento + tombstone
-- ============================================================================
alter table public.tasks
    add column if not exists version bigint not null default 0,
    add column if not exists sync_version bigint not null default 0,
    add column if not exists last_synced timestamptz,
    add column if not exists deleted boolean not null default false;

create index if not exists idx_tasks_sync on public.tasks (user_id, sync_version) where not deleted;

create trigger trg_tasks_version
    before update on public.tasks
    for each row execute function public.increment_version();

-- ============================================================================
-- 8. CALENDAR_EVENTS - versionamento + tombstone
-- ============================================================================
alter table public.calendar_events
    add column if not exists version bigint not null default 0,
    add column if not exists sync_version bigint not null default 0,
    add column if not exists last_synced timestamptz,
    add column if not exists deleted boolean not null default false;

create index if not exists idx_calendar_events_sync on public.calendar_events (user_id, sync_version) where not deleted;

create trigger trg_calendar_events_version
    before update on public.calendar_events
    for each row execute function public.increment_version();

-- ============================================================================
-- 9. USER_AI_KEYS - versionamento
-- ============================================================================
alter table public.user_ai_keys
    add column if not exists version bigint not null default 0,
    add column if not exists sync_version bigint not null default 0,
    add column if not exists last_synced timestamptz;

create trigger trg_user_ai_keys_version
    before update on public.user_ai_keys
    for each row execute function public.increment_version();

-- ============================================================================
-- 10. AI_SETTINGS - versionamento
-- ============================================================================
alter table public.ai_settings
    add column if not exists version bigint not null default 0,
    add column if not exists sync_version bigint not null default 0,
    add column if not exists last_synced timestamptz;

create trigger trg_ai_settings_version
    before update on public.ai_settings
    for each row execute function public.increment_version();

-- ============================================================================
-- 11. WEB_SEARCHES - versionamento (append-only)
-- ============================================================================
alter table public.web_searches
    add column if not exists version bigint not null default 0,
    add column if not exists sync_version bigint not null default 0,
    add column if not exists last_synced timestamptz;

create index if not exists idx_web_searches_sync on public.web_searches (user_id, sync_version);

create trigger trg_web_searches_version
    before update on public.web_searches
    for each row execute function public.increment_version();

-- ============================================================================
-- 12. ACTIVITY_LOGS - versionamento (append-only)
-- ============================================================================
alter table public.activity_logs
    add column if not exists version bigint not null default 0,
    add column if not exists sync_version bigint not null default 0,
    add column if not exists last_synced timestamptz;

create index if not exists idx_activity_logs_sync on public.activity_logs (user_id, sync_version);

create trigger trg_activity_logs_version
    before update on public.activity_logs
    for each row execute function public.increment_version();

-- ============================================================================
-- VIEWS PARA SINCRONIZAÇÃO EFICIENTE
-- ============================================================================

-- View: mudanças desde última sincronização (incremental)
create or replace view public.v_user_changes as
select 
    'profiles' as store, id, user_id, version, sync_version, updated_at as changed_at, deleted
from public.profiles
union all
select 
    'agent_settings', id, user_id, version, sync_version, updated_at, deleted
from public.agent_settings
union all
select 
    'agent_memories', id, user_id, version, sync_version, updated_at, deleted
from public.agent_memories
union all
select 
    'conversations', id, user_id, version, sync_version, updated_at, deleted
from public.conversations
union all
select 
    'messages', id, user_id, version, sync_version, updated_at, deleted
from public.messages
union all
select 
    'tasks', id, user_id, version, sync_version, updated_at, deleted
from public.tasks
union all
select 
    'calendar_events', id, user_id, version, sync_version, updated_at, deleted
from public.calendar_events
union all
select 
    'user_ai_keys', user_id || '_' || provider as id, user_id, version, sync_version, updated_at, false as deleted
from public.user_ai_keys
union all
select 
    'ai_settings', user_id as id, user_id, version, sync_version, updated_at, false
from public.ai_settings
union all
select 
    'web_searches', id, user_id, version, sync_version, updated_at, false
from public.web_searches
union all
select 
    'activity_logs', id::text, user_id, version, sync_version, updated_at, false
from public.activity_logs;

-- Grant select on view to authenticated users
grant select on public.v_user_changes to authenticated;

-- ============================================================================
-- FUNCTION: Get changes since sync_version (para endpoint /sync/pull)
-- ============================================================================
create or replace function public.get_changes_since(
    p_user_id text,
    p_since_sync_version bigint default 0,
    p_stores text[] default null
)
returns table (
    store text,
    id text,
    version bigint,
    sync_version bigint,
    changed_at timestamptz,
    deleted boolean,
    data jsonb
)
language plpgsql security definer set search_path = public as $$
declare
    v_store text;
    v_query text;
begin
    -- Se stores não especificado, usa todos
    if p_stores is null then
        p_stores := array['profiles','agent_settings','agent_memories','conversations','messages','tasks','calendar_events','user_ai_keys','ai_settings','web_searches','activity_logs'];
    end if;

    -- Para cada store, retorna mudanças
    for v_store in select unnest(p_stores)
    loop
        v_query := format($q$
            select 
                '%1$s' as store,
                id,
                version,
                sync_version,
                updated_at as changed_at,
                coalesce(deleted, false) as deleted,
                to_jsonb(t) as data
            from public.%1$s t
            where user_id = $1
            and sync_version > $2
            and (not coalesce(deleted, false) or sync_version > $2)
            order by sync_version
        $q$, v_store);

        return query execute v_query using p_user_id, p_since_sync_version;
    end loop;
end;
$$;

-- ============================================================================
-- FUNCTION: Apply sync operations (para endpoint /sync/push)
-- ============================================================================
create or replace function public.apply_sync_operations(
    p_user_id text,
    p_operations jsonb
)
returns table (
    client_id text,
    status text,
    server_id text,
    conflict boolean,
    server_data jsonb
)
language plpgsql security definer set search_path = public as $$
declare
    v_op jsonb;
    v_store text;
    v_operation text;
    v_data jsonb;
    v_client_id text;
    v_id text;
    v_existing jsonb;
    v_conflict boolean;
    v_server_data jsonb;
begin
    for v_op in select * from jsonb_array_elements(p_operations)
    loop
        v_client_id := v_op->>'client_id';
        v_store := v_op->>'store';
        v_operation := v_op->>'operation';
        v_data := v_op->'data';

        -- Verifica se existe no servidor (para detectar conflito)
        v_existing := null;
        v_conflict := false;

        if v_operation in ('update', 'delete') then
            v_id := v_data->>'id';
            if v_id is not null then
                execute format('select to_jsonb(t) from public.%I t where id = $1 and user_id = $2', v_store)
                into v_existing using v_id, p_user_id;
                
                if v_existing is not null then
                    -- Verifica conflito de versão (optimistic locking)
                    if (v_existing->>'sync_version')::bigint > (v_data->>'sync_version')::bigint then
                        v_conflict := true;
                        v_server_data := v_existing;
                    end if;
                end if;
            end if;
        end if;

        if v_conflict then
            return query select v_client_id, 'conflict', null, true, v_server_data;
            continue;
        end if;

        -- Aplica operação
        if v_operation = 'create' then
            execute format($q$
                insert into public.%I (select * from jsonb_populate_record(null::public.%I, $1))
                on conflict (id) do update set 
                    version = excluded.version + 1,
                    sync_version = (select coalesce(max(sync_version), 0) + 1 from public.sync_metadata where user_id = $2),
                    updated_at = now(),
                    last_synced = now()
                returning id
            $q$, v_store, v_store)
            into v_id using v_data, p_user_id;
            
            return query select v_client_id, 'ok', v_id, false, null;

        elsif v_operation = 'update' then
            v_id := v_data->>'id';
            execute format($q$
                update public.%I set
                    version = version + 1,
                    sync_version = (select coalesce(max(sync_version), 0) + 1 from public.sync_metadata where user_id = $2),
                    updated_at = now(),
                    last_synced = now(),
                    deleted = coalesce($1->>'deleted', false)
                where id = $3 and user_id = $2
                returning id
            $q$, v_store)
            into v_id using v_data, p_user_id, v_id;
            
            if v_id is null then
                return query select v_client_id, 'error', null, false, jsonb_build_object('error', 'Not found');
            else
                return query select v_client_id, 'ok', v_id, false, null;
            end if;

        elsif v_operation = 'delete' then
            v_id := v_data->>'id';
            -- Soft delete (tombstone)
            execute format($q$
                update public.%I set
                    deleted = true,
                    version = version + 1,
                    sync_version = (select coalesce(max(sync_version), 0) + 1 from public.sync_metadata where user_id = $2),
                    updated_at = now(),
                    last_synced = now()
                where id = $3 and user_id = $2
                returning id
            $q$, v_store)
            into v_id using v_data, p_user_id, v_id;
            
            if v_id is null then
                return query select v_client_id, 'error', null, false, jsonb_build_object('error', 'Not found');
            else
                return query select v_client_id, 'ok', v_id, false, null;
            end if;
        end if;
    end loop;
end;
$$;

-- ============================================================================
-- RLS PARA VIEWS E FUNCTIONS
-- ============================================================================
alter function public.get_changes_since(text, bigint, text[]) security definer;
alter function public.apply_sync_operations(text, jsonb) security definer;

-- ============================================================================
-- ÍNDICES ADICIONAIS PARA PERFORMANCE DE SYNC
-- ============================================================================
create index if not exists idx_conversations_user_updated on public.conversations (user_id, updated_at desc) where not deleted;
create index if not exists idx_tasks_user_status on public.tasks (user_id, status, updated_at desc) where not deleted;
create index if not exists idx_events_user_date on public.calendar_events (user_id, event_date, updated_at desc) where not deleted;

-- ============================================================================
-- COMENTÁRIOS
-- ============================================================================
comment on table public.sync_metadata is 'Metadados de sincronização por usuário para offline-first';
comment on column public.profiles.version is 'Versão otimista para detectar conflitos de atualização concorrente';
comment on column public.profiles.sync_version is 'Versão global de sincronização para pull incremental';
comment on column public.profiles.deleted is 'Tombstone para soft delete (sync de exclusões)';
comment on column public.profiles.last_synced is 'Timestamp da última sincronização bem-sucedida deste registro';