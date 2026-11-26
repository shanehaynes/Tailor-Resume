# Working in parallel

This file applies when `profile/preferences.md` says `workflow: parallel`: the
owner runs several Claude sessions in this repo at once. Under
`workflow: single` (the default), one session works on `main` and runs
`make check` before each commit; the "Never do this" list below still applies.

No session can see another's uncommitted changes. Every collision comes from a
resource two sessions share without knowing it. This file names each one, says
how it fails, then gives the rule. CLAUDE.md has the short version. The guard
hook (`scripts/hooks/bash-guard.mjs`) enforces the rules that can be checked by
machine.

## The primary checkout

**Failure:** sessions commit to `main` in the same directory. One rebases and
pushes; the other still holds the old copies of the same commits, plus
uncommitted files from a third session. The next pull conflicts on files
nobody in that session wrote.

**Rule:** the primary checkout (the clone whose `.git` is a directory) stays on
`main`, clean, and only ever fast-forwards: `git pull --ff-only`. Read there;
run `rc status` and `rc ledger check` there. Never commit, rebase, merge, or run
an `rc` command that writes files (`fit`, `ats`, `truth`, `cover`, `new-app`,
`gate --write`) there. The guard blocks these.

## Worktrees

`scripts/git-new.sh <type>/<slug> "<intent>"` fetches, branches from
`origin/main` (never from whatever the primary checkout happens to be on), and
creates `.claude/worktrees/<type>-<slug>`. It copies the primary's verified
`bin/typst` and runs `make setup`. It records your claim in
`.claude/state/claims.tsv` and prints everyone else's claims.

| Type | Use |
|---|---|
| `app/<company>-<role>` | tailoring, cover letter, status changes for one application |
| `ledger/<what>` | ledger-only work (`/ledger`) |
| `feat/` `fix/` `chore/` | changes to `rc`, templates, skills, scripts |

Claims are a hint, not a lock. If someone else has claimed the same application,
stop and ask the owner. Two sessions adding variants to the same accomplishment
will conflict in `ledger.yaml`; that is survivable (below), but cheaper to avoid.

Never copy files between worktrees or branches. If you need another branch's
work, wait for it to merge, then merge `origin/main` into yours. A copied file
carries no history: the merge treats it as your own change and can silently
undo the other branch's later edits.

`scripts/git-tidy.sh` (dry run; `--yes` applies) retires worktrees and branches
whose content has landed on `main`. It never touches a worktree with
uncommitted files, one with no commits yet (a session that just started), or a
branch that has not landed.

## Finishing: the owner merges

1. `make check` in your worktree.
2. Push the branch; `gh pr create` (title is the commit convention: `app: <slug>`).
3. `scripts/combine-check.sh` checks every open PR pair for conflicts with each other.
4. Tell the owner the PR is ready, with anything combine-check reported.

The guard blocks `gh pr merge`. When `main` moves under your PR, merge
`origin/main` into your branch in your worktree and push. Never rebase a pushed
branch: the other sessions still hold the pre-rebase commits, and their next
push duplicates them.

**Do not stack PRs.** Every branch starts from `origin/main` (`git-new.sh` does
this). A branch cut from another unmerged branch carries that branch's commits;
after the first squash-merges, the second shows them again as its own changes.
If you need another branch's work, wait for it to merge, then merge
`origin/main` into yours.

After the owner says they submitted an application, setting `status: submitted`
is a one-line change. Make it on a fresh `app/` branch if the old one has merged.

## Merge settings

The scripts assume the GitHub repo squash-merges and deletes a PR's head branch
on merge. `scripts/git-tidy.sh` uses both to tell a finished branch from one
still in flight; with merge commits it reports finished branches as KEEP
forever. Onboarding sets this when the owner chooses parallel:

```bash
gh repo edit <owner>/<repo> --enable-squash-merge --enable-merge-commit=false \
  --enable-rebase-merge=false --delete-branch-on-merge
```

## Files that are generated and committed

**Failure:** a gate that re-renders every `ready` application and rewrites its
PDF and `report.json` in place lets one session's ledger edit plus
`make check` dirty every other session's applications. Those stray changes
then block a rebase or a pull.

**Rule:** `rc gate` (and so `make check`, and CI) is read-only. It renders into
`build/apps/<slug>/gate/` and compares against the committed copies. A
committed `report.json` section that differs, or a PDF whose text differs, is
reported `STALE` and fails the gate. If your ledger change legitimately moves
another application, run `uv run rc gate --write` in your worktree, read the
diff, and commit it with your change. `rc fit/ats/truth/cover <app>` still
write, for the one application you are working on. Decision:
`docs/decisions/2026-10-07-read-only-gate.md`.

## Shared files: ledger.yaml and STATUS.md

`ledger/ledger.yaml` is the one file every tailoring session may edit. Make
each ledger change its own `ledger:` commit (ledger-update skill). Two open PRs
that both edit the same accomplishment conflict with each other, though each
merges cleanly into `main` alone. `combine-check.sh` reports this before the
owner merges. Resolve after the first lands: merge `origin/main` into the second
branch and keep both sides' entries. The ledger's rules (diff shown, the
owner's approval) apply to the resolution as to any other ledger write.

`STATUS.md` gets a section appended by every session, so two branches always
touch the same last lines. `.gitattributes` marks it `merge=union`: local
merges and `merge-tree` keep both sides. GitHub's web merge ignores that, so if
a PR shows a STATUS.md conflict, merge `origin/main` locally and push.

## Never do this

- `git stash` (bare), `git stash pop`, `drop`, or `clear`. The stash stack is
  shared by every worktree; pop takes whatever is on top, which may be another
  session's. Set work aside with a WIP commit on your branch. If you must
  stash, use `git stash push -u -m <tag>`, then `git stash apply <sha>`.
- `git reset --hard`, `git clean -f`, `git checkout -- <path>`,
  `git restore <path>`, or a force-push, without first reading `git status`.
  Uncommitted files may be someone's only copy.
- Copy a PDF to the repo root for uploading. Upload from the application folder.

The guard blocks the first two. Prefix `RC_DESTRUCTIVE_OK=1` once you have
looked and are sure. The guard is a tripwire for a well-meaning session, not a
sandbox: it reads the command string, so a heredoc that merely quotes a banned
command also trips it. Write such text with the file tools.

## Supervisor sweep

`scripts/supervisor-report.sh` is read-only and safe anywhere. It covers main's
CI, whether the primary checkout is clean, on `main`, and current, the stash
stack, what tidy would retire, worktrees and claims older than a week, and
open PRs with a pairwise combine check. Lines starting `ACTION` need someone.

## Why these rules exist

Without them, the failures compound. If several sessions tailor from the
primary checkout and commit straight to `main`, and one merges a PR and rebases
the others' commits onto it, the checkout is left holding pre-rebase copies of
those commits, someone's unpushed commit, another session's uncommitted cover
letter, and `report.json` files a writing gate rewrote for applications nobody
there touched. The next push then meets a rejected push, a rebase aborted on
untracked files the remote now tracks, a `report.json` conflict, and a
duplicate commit, and one change can be silently undone because the remote's
copy of a file won. Each rule above removes one step of that sequence.
