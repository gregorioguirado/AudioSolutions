-- profiles: extends auth.users
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  free_used boolean not null default false,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "Users can read own profile"
  on public.profiles for select
  using (auth.uid() = id);

create policy "Users can update own profile"
  on public.profiles for update
  using (auth.uid() = id);

-- auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email)
  values (new.id, new.email);
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- translations: one row per completed translation
create table public.translations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  source_console text not null,
  target_console text not null,
  source_filename text not null,
  source_r2_key text,
  output_r2_key text,
  report_r2_key text,
  channel_count integer not null,
  translated_params text[] not null default '{}',
  approximated_params text[] not null default '{}',
  dropped_params text[] not null default '{}',
  status text not null default 'pending',
  error_message text,
  created_at timestamptz not null default now()
);

alter table public.translations enable row level security;

create policy "Users can read own translations"
  on public.translations for select
  using (auth.uid() = user_id);

-- anonymous_previews: short-lived rows for pre-signup users
create table public.anonymous_previews (
  id uuid primary key default gen_random_uuid(),
  session_token text not null unique,
  source_r2_key text,
  output_r2_key text,
  report_r2_key text,
  channel_count integer,
  translated_params text[] not null default '{}',
  approximated_params text[] not null default '{}',
  dropped_params text[] not null default '{}',
  created_at timestamptz not null default now(),
  expires_at timestamptz not null default (now() + interval '1 hour')
);
