-- SuNoogo database schema (Postgres / Supabase).
-- Run once in the Supabase SQL editor.
--
-- Privacy rules enforced here:
--   * no column holds a woman's name: women are identified by a code such as F-0042;
--   * a session row exists only once consent has been given;
--   * anonymous clients can read the aggregated view public_stats, never the tables.

create table if not exists sessions (
    id            uuid primary key default gen_random_uuid(),
    chw_phone     text not null,
    woman_code    text not null check (woman_code ~ '^F-[0-9]{4}$'),
    consent       boolean not null check (consent),
    -- Raw answers as chosen by the CHW (1..5), in question order. The score is derived from them.
    answers       jsonb not null default '[]'::jsonb
                  check (jsonb_typeof(answers) = 'array' and jsonb_array_length(answers) <= 6),
    score         smallint check (score between 0 and 24),
    level         text check (level in ('green', 'orange', 'red')),
    safety_flag   boolean,
    started_at    timestamptz not null default now(),
    completed_at  timestamptz,
    followup_due  date,
    -- A completed session must carry its full result.
    constraint completed_has_result check (
        completed_at is null
        or (score is not null and level is not null and safety_flag is not null
            and jsonb_array_length(answers) = 6)
    )
);

create index if not exists sessions_started_at_idx on sessions (started_at);
create index if not exists sessions_followup_due_idx on sessions (followup_due)
    where followup_due is not null;

create table if not exists alerts (
    id          uuid primary key default gen_random_uuid(),
    session_id  uuid not null references sessions (id) on delete cascade,
    sent_to     text not null,
    sent_at     timestamptz not null default now(),
    status      text not null default 'pending' check (status in ('pending', 'sent', 'failed'))
);

create index if not exists alerts_session_id_idx on alerts (session_id);

-- Row level security with no policies: only the service role (backend) can touch the tables.
alter table sessions enable row level security;
alter table alerts enable row level security;

-- Weekly aggregated counters, no individual data. Used by the public dashboard and the DHIS2 push.
-- Weeks are ISO weeks (Monday start), keyed on the session start date.
-- The view intentionally runs with its owner's rights (no security_invoker) so that the anon role
-- can read the aggregates while the underlying tables stay closed by RLS.
create or replace view public_stats as
select
    to_char(date_trunc('week', s.started_at), 'IYYY-"W"IW')         as iso_week,
    date_trunc('week', s.started_at)::date                           as week_start,
    count(*)                                                         as sessions_started,
    count(*) filter (where s.completed_at is not null)               as sessions_completed,
    count(*) filter (where s.level = 'green')                        as level_green,
    count(*) filter (where s.level = 'orange')                       as level_orange,
    count(*) filter (where s.level = 'red')                          as level_red,
    coalesce(sum(a.alerts_sent), 0)::bigint                          as alerts_sent
from sessions s
left join (
    select session_id, count(*) as alerts_sent
    from alerts
    where status = 'sent'
    group by session_id
) a on a.session_id = s.id
group by 1, 2;

-- Explicit grants: do not rely on Supabase's "automatically expose new tables" setting.
revoke all on sessions, alerts, public_stats from anon, authenticated;
grant select, insert, update, delete on sessions, alerts to service_role;
grant select on public_stats to anon, authenticated, service_role;
