-- Add per-model identifiers alongside existing brand-level source_console/target_console.
alter table public.translations
  add column if not exists source_model text,
  add column if not exists target_model text,
  add column if not exists channel_names text[] not null default '{}';

-- Matching columns for anonymous previews so the anonymous → authenticated claim flow
-- can carry them forward without data loss.
alter table public.anonymous_previews
  add column if not exists source_model text,
  add column if not exists target_model text,
  add column if not exists channel_names text[] not null default '{}';
