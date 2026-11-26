#!/usr/bin/env bash
# Cut a new branch + worktree from current origin/main.
#
#   scripts/git-new.sh app/acme-ops-analyst "tailor Acme Operations Analyst"
#   scripts/git-new.sh ledger/new-role-facts --no-install    # skip make setup
#
# Always branches from a freshly-fetched origin/main, never from whatever the
# primary checkout is sitting on, so a stale checkout cannot silently become
# the base of new work.
#
# Works from the primary checkout or from inside any worktree: it anchors on
# the primary checkout either way (the one that owns .git), so a worktree is
# never created inside another worktree.
#
# Sets the worktree up unless told not to: .venv and bin/typst are
# per-checkout, and a worktree without them cannot run a single rc command.
# The primary's already-verified typst binary is copied rather than
# re-downloaded; scripts/setup.sh still checks its version. See CONTRIBUTING.md.
set -euo pipefail

branch=""
intent=""
install=1
for arg in "$@"; do
  case "$arg" in
    --no-install) install=0 ;;
    -*)
      echo "error: unknown option '$arg'" >&2
      exit 64
      ;;
    *)
      if [ -z "$branch" ]; then
        branch="$arg"
      elif [ -z "$intent" ]; then
        intent="$arg"
      else
        echo "error: expected a branch and optionally an intent, got extra '$arg'" >&2
        exit 64
      fi
      ;;
  esac
done

if [ -z "$branch" ]; then
  echo "usage: scripts/git-new.sh <type>/<slug> [\"what you will touch\"] [--no-install]" >&2
  echo "       types: app/ ledger/ feat/ fix/ chore/" >&2
  exit 64
fi

case "$branch" in
  app/*|ledger/*|feat/*|fix/*|chore/*) ;;
  *)
    echo "error: branch must start with app/, ledger/, feat/, fix/ or chore/ — got '$branch'" >&2
    echo "       branch names say what changed, not who changed it." >&2
    exit 64
    ;;
esac

# The primary checkout is the directory that owns .git; from inside a linked
# worktree, --show-toplevel would point at the worktree instead and nest the
# new one under it.
root=$(cd "$(git rev-parse --git-common-dir)/.." && pwd -P)
cd "$root"

if git show-ref --quiet --verify "refs/heads/$branch"; then
  echo "error: branch '$branch' already exists" >&2
  exit 1
fi

# Slashes are legal in branch names but make for awkward nested directories.
dir="$root/.claude/worktrees/${branch//\//-}"
if [ -e "$dir" ]; then
  echo "error: worktree path already exists: $dir" >&2
  exit 1
fi

echo "── fetching origin/main"
git fetch origin main --quiet

git worktree add "$dir" -b "$branch" origin/main

if [ "$install" -eq 1 ]; then
  echo "── setting up (bin/typst and .venv are per-worktree; --no-install skips this)"
  if [ -x "$root/bin/typst" ]; then
    mkdir -p "$dir/bin" && cp "$root/bin/typst" "$dir/bin/typst"
  fi
  (cd "$dir" && make setup >/dev/null)
fi

# Record the claim. Sessions cannot see each other's uncommitted work, but
# they can see declared intent: one line per active worktree in the primary
# checkout's claims file. git-tidy.sh prunes claims whose worktree is gone;
# supervisor-report.sh flags stale ones. Tabs are the field separator, so
# they cannot appear in the intent.
state_dir="$root/.claude/state"
mkdir -p "$state_dir"
printf '%s\t%s\t%s\t%s\n' "$branch" "$(date -u +%FT%TZ)" "$dir" "${intent//$'\t'/ }" \
  >> "$state_dir/claims.tsv"

cat <<MSG

── ready
   branch:   $branch
   worktree: $dir

   cd $dir
MSG

# Show what everyone else has claimed, right when overlap is cheapest to
# avoid — before this session has written a line. Two sessions on the same
# application, or both proposing ledger variants for the same accomplishment,
# are the collisions that matter here.
others=$(awk -F'\t' -v me="$branch" \
  '$1 != me { printf "   %s (since %s)%s\n", $1, $2, ($4 != "" ? " — " $4 : "") }' \
  "$state_dir/claims.tsv" 2>/dev/null || true)
if [ -n "$others" ]; then
  echo
  echo "── other sessions have claimed — check for overlap before touching the same files:"
  printf '%s\n' "$others"
fi
