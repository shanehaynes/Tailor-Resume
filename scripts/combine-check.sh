#!/usr/bin/env bash
# Prove that several in-flight branches combine — textually, and with --check
# semantically — before their PRs open. CONTRIBUTING.md ("Finishing: the
# owner merges", "Shared files") says when to run it.
#
#   scripts/combine-check.sh                        # all open PR branches, pairwise merge-tree
#   scripts/combine-check.sh app/a ledger/b          # specific branches
#   scripts/combine-check.sh --check app/a app/b    # + fold into a throwaway tree and run make check
#
# Pairwise `git merge-tree` finds branches that each merge cleanly into main
# but conflict with each other — which merging the PRs one by one only
# discovers after the first lands. In this repo that is almost always ledger.yaml (two
# sessions adding variants to the same accomplishment). --check additionally
# catches semantic collisions (one branch retires a variant another branch's
# application uses) by building the combined tree in a detached worktree and
# running the full gate.
set -euo pipefail

# Anchor on the checkout this script lives in (so it runs from anywhere),
# then hop to the primary checkout, which owns .claude/worktrees/.
cd "$(cd "$(dirname "$0")/.." && pwd -P)" || exit 1
cd "$(git rev-parse --git-common-dir)/.." || exit 1

check=0
branches=()
for arg in "$@"; do
  case "$arg" in
    --check) check=1 ;;
    -*)
      echo "usage: scripts/combine-check.sh [--check] [branch ...]" >&2
      exit 64
      ;;
    *) branches+=("$arg") ;;
  esac
done

echo "── fetching origin" >&2
git fetch origin --prune --quiet

if [ "${#branches[@]}" -eq 0 ]; then
  GH="${GH:-$(command -v gh || true)}"
  if [ -z "$GH" ]; then
    echo "error: no branches given and gh not found to list open PRs" >&2
    exit 64
  fi
  while IFS= read -r b; do branches+=("$b"); done < <(
    "$GH" pr list --state open --base main --json headRefName --jq '.[].headRefName'
  )
  if [ "${#branches[@]}" -lt 2 ]; then
    echo "fewer than two open PR branches — nothing to combine."
    exit 0
  fi
  echo "checking open PR branches: ${branches[*]}"
fi

# Resolve each name to a ref, preferring the remote (what the PR will merge).
refs=()
for b in "${branches[@]}"; do
  if git rev-parse --quiet --verify "refs/remotes/origin/$b" >/dev/null; then
    refs+=("origin/$b")
  elif git rev-parse --quiet --verify "$b" >/dev/null; then
    refs+=("$b")
  else
    echo "error: no such branch '$b' (local or origin)" >&2
    exit 1
  fi
done

conflicts=0
for ((i = 0; i < ${#refs[@]}; i++)); do
  for ((j = i + 1; j < ${#refs[@]}; j++)); do
    if out=$(git merge-tree --write-tree --name-only "${refs[i]}" "${refs[j]}" 2>&1); then
      echo "ok        ${refs[i]} + ${refs[j]}"
    else
      conflicts=1
      echo "CONFLICT  ${refs[i]} + ${refs[j]}"
      echo "$out" | sed -n '2,$p' | sed 's/^/          /'
    fi
  done
done

if [ "$conflicts" -ne 0 ]; then
  echo
  echo "Pairs conflict (usually ledger.yaml). Tell the owner the merge order; after the"
  echo "first lands, merge origin/main into the other branch in its worktree, resolve"
  echo "keeping both sides' entries, rerun make check, push. Do NOT stack the PRs"
  echo "(CONTRIBUTING.md)."
  exit 1
fi

[ "$check" -eq 1 ] || exit 0

# Fold all branches into one throwaway commit chain and run the gate on it.
echo
echo "── all pairs merge; folding into a combined tree for make check"
cur=$(git rev-parse "${refs[0]}")
for ((i = 1; i < ${#refs[@]}; i++)); do
  tree=$(git merge-tree --write-tree "$cur" "${refs[i]}")
  cur=$(git commit-tree "$tree" -p "$cur" -p "$(git rev-parse "${refs[i]}")" -m "throwaway combine")
done

dir=".claude/worktrees/_combined"
if [ -e "$dir" ]; then
  echo "error: $dir already exists — another combine check running? Remove it first." >&2
  exit 1
fi
trap 'git worktree remove --force "$dir" 2>/dev/null || true' EXIT
git worktree add --detach "$dir" "$cur"
mkdir -p "$dir/bin" && cp bin/typst "$dir/bin/typst"
(cd "$dir" && make setup >/dev/null && make check)
echo "── combined tree passes make check"
