#!/usr/bin/env bash
# Apply any pending Supabase migrations to the linked project.
#
# Reads SUPABASE_ACCESS_TOKEN and SUPABASE_PROJECT_REF from web/.env.local
# (which must exist and be gitignored). If the local project isn't linked yet,
# runs `supabase link` first.
#
# Usage:
#   tools/apply-migrations.sh [--dry-run]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$REPO_ROOT/web/.env.local"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE not found. Copy web/.env.local.example and fill in the secrets." >&2
  exit 1
fi

# Export only the Supabase-related vars we need (don't slurp the whole file).
SUPABASE_ACCESS_TOKEN="$(grep -E '^SUPABASE_ACCESS_TOKEN=' "$ENV_FILE" | head -n1 | cut -d= -f2-)"
SUPABASE_PROJECT_REF="$(grep -E '^SUPABASE_PROJECT_REF=' "$ENV_FILE" | head -n1 | cut -d= -f2-)"

if [[ -z "$SUPABASE_ACCESS_TOKEN" || -z "$SUPABASE_PROJECT_REF" ]]; then
  echo "ERROR: SUPABASE_ACCESS_TOKEN and SUPABASE_PROJECT_REF must be set in $ENV_FILE" >&2
  exit 1
fi

export SUPABASE_ACCESS_TOKEN

cd "$REPO_ROOT/web"

# Ensure the project is linked (idempotent — safe to re-run).
if ! npx --yes supabase projects list 2>/dev/null | grep -q "$SUPABASE_PROJECT_REF"; then
  : # user may not have permission to list all projects; skip pre-check
fi

echo "→ linking project $SUPABASE_PROJECT_REF"
npx --yes supabase link --project-ref "$SUPABASE_PROJECT_REF" >/dev/null

if [[ "${1:-}" == "--dry-run" ]]; then
  echo "→ dry-run db push"
  npx --yes supabase db push --dry-run
else
  echo "→ applying pending migrations"
  npx --yes supabase db push
fi

echo "→ current migration state:"
npx --yes supabase migration list
