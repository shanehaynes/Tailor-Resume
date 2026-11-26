#!/usr/bin/env bash
# Read-only supervisor sweep: everything that silently rots between sessions,
# in one report. Lines starting with "ACTION" need the owner or a session;
# everything else is status. Never mutates anything — safe from anywhere.
#
#   scripts/supervisor-report.sh
#
# Covers: is main green, is the primary checkout clean and current (most
# multi-session failures start there; CONTRIBUTING.md), what git-tidy would clean, which
# worktrees and claims look abandoned, and which open PRs are waiting on the
# owner or collide with each other.
set -uo pipefail

# Anchor on the checkout this script lives in (so it runs from anywhere),
# then hop to the primary checkout, which owns .claude/worktrees/.
cd "$(cd "$(dirname "$0")/.." && pwd -P)" || exit 1
cd "$(git rev-parse --git-common-dir)/.." || exit 1

GH="${GH:-$(command -v gh || true)}"

# ISO-8601 UTC -> epoch seconds, GNU or BSD date.
epoch() { date -d "$1" +%s 2>/dev/null || date -j -u -f %Y-%m-%dT%H:%M:%SZ "$1" +%s 2>/dev/null; }

echo "── main"
if [ -n "$GH" ]; then
  latest=$("$GH" run list --workflow check --branch main --limit 1 \
    --json conclusion,status,updatedAt,displayTitle \
    --jq '.[0] | "\(.conclusion // .status)  \(.updatedAt)  \(.displayTitle)"' 2>/dev/null || true)
  case "$latest" in
    success*) echo "   green: $latest" ;;
    "")       echo "   no CI runs found (gh auth?)" ;;
    *)        echo "ACTION main's latest CI run is not green: $latest" ;;
  esac
else
  echo "   gh not found — skipped"
fi

echo
echo "── primary checkout (stays on main, clean, fast-forward only)"
git fetch origin --quiet 2>/dev/null || echo "   fetch failed — comparing against the last known origin/main"
branch=$(git branch --show-current)
[ "$branch" = main ] || echo "ACTION primary checkout is on '$branch', not main — switch it back: git switch main"
ahead=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo 0)
behind=$(git rev-list --count HEAD..origin/main 2>/dev/null || echo 0)
if [ "$ahead" -gt 0 ]; then
  echo "ACTION primary has $ahead commit(s) not on origin/main — move them to a branch (scripts/git-new.sh) before anything else; do not rebase here"
elif [ "$behind" -gt 0 ]; then
  echo "   $behind commit(s) behind origin/main — git pull --ff-only"
else
  echo "   current with origin/main"
fi
dirty=$(git status --porcelain)
if [ -n "$dirty" ]; then
  echo "ACTION primary has uncommitted or untracked files — some session's only copy; find its owner, move them into its worktree and commit:"
  printf '%s\n' "$dirty" | sed 's/^/          /'
fi
git stash list | grep -q . && echo "ACTION the shared stash stack is not empty — read it (git stash list), apply what belongs to a branch, then drop by SHA"

echo
echo "── merged branches and worktrees to retire (git-tidy.sh dry run)"
scripts/git-tidy.sh 2>/dev/null | sed 's/^/   /' || echo "   git-tidy.sh failed"

echo
echo "── worktree age"
for wt in .claude/worktrees/*/; do
  [ -d "$wt" ] || continue
  branch=$(git -C "$wt" branch --show-current 2>/dev/null || echo "?")
  last=$(git -C "$wt" log -1 --format=%ct 2>/dev/null || echo 0)
  age_days=$(( ($(date +%s) - last) / 86400 ))
  dirty=$(git -C "$wt" status --porcelain 2>/dev/null | head -1)
  if [ "$age_days" -ge 7 ]; then
    if [ -n "$dirty" ]; then
      echo "ACTION $wt ($branch): last commit ${age_days}d ago WITH uncommitted changes — commit or finish it; never delete unseen"
    else
      echo "ACTION $wt ($branch): last commit ${age_days}d ago, clean — finish it or git-tidy after merging"
    fi
  else
    echo "   $wt ($branch): ${age_days}d${dirty:+, uncommitted changes}"
  fi
done

echo
echo "── session claims (git-new.sh records them; git-tidy.sh prunes them)"
claims=".claude/state/claims.tsv"
if [ -s "$claims" ]; then
  now=$(date +%s)
  while IFS=$'\t' read -r br ts wt intent; do
    [ -n "$br" ] || continue
    claimed=$(epoch "$ts" || echo "$now")
    age_days=$(( (now - claimed) / 86400 ))
    if [ ! -d "$wt" ]; then
      echo "ACTION claim for $br points at a missing worktree — stale; scripts/git-tidy.sh --yes prunes it"
    elif [ "$age_days" -ge 7 ]; then
      echo "ACTION $br claimed ${age_days}d ago${intent:+ ($intent)} — finish it or retire it"
    else
      echo "   $br (${age_days}d${intent:+ — $intent})"
    fi
  done < "$claims"
else
  echo "   none recorded"
fi

echo
echo "── open PRs (the owner merges)"
if [ -n "$GH" ]; then
  prs=$("$GH" pr list --state open --limit 50 \
    --json number,title,baseRefName,mergeStateStatus \
    --jq '.[] | "   #\(.number)  \(.mergeStateStatus)\(if .baseRefName != "main" then "  BASE=\(.baseRefName)" else "" end)  \(.title)"' 2>/dev/null || true)
  if [ -z "$prs" ]; then
    echo "   none"
  else
    echo "$prs"
    echo "$prs" | grep -q "BASE=" && echo "ACTION a PR above is not based on main — the stacked-PR trap; retarget it"
    echo "$prs" | grep -q "DIRTY" && echo "ACTION a PR above conflicts with main — merge origin/main into its branch in its worktree (STATUS.md union-merges locally), push"
    echo "$prs" | grep -qE "CLEAN|BEHIND|UNSTABLE" && echo "ACTION PRs are waiting for the owner to review and merge"
    # Two open PRs can each merge cleanly into main and still conflict with
    # each other — usually ledger.yaml. Merging one makes the other DIRTY.
    if [ "$(printf '%s\n' "$prs" | wc -l)" -ge 2 ]; then
      echo
      echo "── combine check (pairwise merge-tree across open PR branches)"
      out=$(scripts/combine-check.sh 2>/dev/null) && combined=0 || combined=1
      printf '%s\n' "$out" | sed 's/^/   /'
      [ "$combined" -ne 0 ] && echo "ACTION two open PRs conflict with each other — merge one, then merge origin/main into the other's branch"
    fi
  fi
else
  echo "   gh not found — skipped"
fi
