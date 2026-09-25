-- ============================================================================
-- NEMO — Supabase schema (migration 002)
-- Autenticação persistida no banco: usuários + sessões (tokens).
--
-- Motivo: em hosting com disco efêmero (Render), contas em _data/users.json e
-- sessões em memória desaparecem a cada restart/deploy. Com estas tabelas as
-- contas sobrevivem a redeploy e o login permanece válido (sessões 7 dias).
--
-- Acesso: SOMENTE o backend (service role, que ignora RLS). Nada de policies
-- para anon/authenticated — o app autentica localmente; o Supabase é o armazém.
-- ============================================================================

create table if not exists public.auth_users (
    id            text primary key,
    name          text not null,
    email         text not null unique,
    password_hash text,
    role          text not null default 'user' check (role in ('user', 'admin')),
    oauth         text,
    oauth_id      text,
    created_at    timestamptz not null default now()
);

create table if not exists public.auth_sessions (
    token      text primary key,
    user_id    text not null references public.auth_users (id) on delete cascade,
    created_at timestamptz not null default now(),
    expires_at timestamptz not null
);

alter table public.auth_users    enable row level security;
alter table public.auth_sessions enable row level security;

-- Sem policies: RLS nega qualquer acesso anônimo/authenticated. A service role
-- do backend (SUPABASE_SERVICE_ROLE_KEY) ignora RLS por design.