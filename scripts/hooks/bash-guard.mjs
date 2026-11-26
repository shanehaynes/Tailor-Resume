#!/usr/bin/env node
// PreToolUse hook for the Bash tool (wired in .claude/settings.json): the
// mechanical form of the CLAUDE.md rules for parallel sessions.
//
//   1. Never destroy what you have not looked at: `git reset --hard`,
//      `git clean -f`, `git checkout -- <path>`, `git restore <path>`,
//      force-push, and the shared stash stack (`git stash` / pop / drop /
//      clear) — the working tree or the stash may hold another session's only
//      copy of its work. Reviewed and safe? Re-run prefixed with
//      RC_DESTRUCTIVE_OK=1.
//   2. The owner merges PRs. A session opens the PR and stops.
//   3. Under `workflow: parallel` only: never commit, render, or rebase in the
//      primary checkout — it stays on main, clean, fast-forward only. Worktrees
//      (scripts/git-new.sh) are the workspace. `rc` commands that write files
//      count as rendering. The workflow is the `Workflow:` line in the primary
//      checkout's profile/preferences.md; no file or no line means single, where
//      one session works on main and rule 3 does not apply.
//
// Protocol: exit 2 with the reason on stderr blocks the call and shows the
// agent the message; anything else allows it. Internal errors allow (fail
// open) — a broken guard must not brick every session.

import { existsSync, readFileSync, statSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join, resolve } from 'node:path';

// Walk up from dir to the checkout root (the first dir owning `.git`).
// A linked worktree stops here at its own root: its `.git` is a file.
export function checkoutRoot(dir) {
  let d = resolve(dir);
  for (;;) {
    if (existsSync(join(d, '.git'))) return d;
    const parent = dirname(d);
    if (parent === d) return null;
    d = parent;
  }
}

// Primary checkout = `.git` is a directory; in a linked worktree it is a file.
export function isPrimaryCheckout(root) {
  try {
    return statSync(join(root, '.git')).isDirectory();
  } catch {
    return false;
  }
}

// The primary checkout that owns this session's project dir — from the
// primary itself, or via a linked worktree's `.git` file, which reads
// `gitdir: <primary>/.git/worktrees/<name>`.
export function primaryRootOf(projectDir) {
  const root = checkoutRoot(projectDir);
  if (!root) return null;
  if (isPrimaryCheckout(root)) return root;
  try {
    const gitdir = readFileSync(join(root, '.git'), 'utf8').match(/^gitdir:\s*(.+)\s*$/m);
    if (!gitdir) return null;
    return resolve(root, gitdir[1], '..', '..', '..');
  } catch {
    return null;
  }
}

// The session workflow recorded during onboarding: a line `Workflow: parallel`
// (optionally a list item, any case) in <primary>/profile/preferences.md.
// Anything else, including no file, is single.
export function isParallel(primary) {
  if (!primary) return false;
  try {
    const prefs = readFileSync(join(primary, 'profile', 'preferences.md'), 'utf8');
    return /^\s*(?:[-*]\s+)?workflow:\s*parallel\b/im.test(prefs);
  } catch {
    return false;
  }
}

// Directories a command may execute in: the hook cwd plus any literal `cd`
// targets. `cd "$SOMEWHERE"` with an unexpanded variable is skipped rather
// than guessed at.
export function effectiveDirs(command, cwd) {
  const dirs = [resolve(cwd)];
  for (const segment of command.split(/(?:&&|\|\||[;|\n])/)) {
    const m = segment.trim().match(/^cd\s+(?:"([^"$]+)"|'([^']+)'|([^\s"'$]+))/);
    if (!m) continue;
    let target = m[1] ?? m[2] ?? m[3];
    if (target.startsWith('~')) target = join(homedir(), target.slice(1));
    dirs.push(resolve(cwd, target));
  }
  return dirs;
}

// Destructive git. `\bgit\b` also matches an absolute path to git.
const DESTRUCTIVE_GIT = new RegExp(
  [
    String.raw`\bgit\b[^|;&()]*\breset\s+--hard\b`,
    String.raw`\bgit\b[^|;&()]*\bclean\s+(-[A-Za-z]*f[A-Za-z]*\b|[^|;&]*--force)`,
    String.raw`\bgit\b[^|;&()]*\bcheckout\b[^|;&]*\s--(\s|$)`,
    String.raw`\bgit\b[^|;&()]*\brestore\b(?![^|;&]*--staged)`,
    String.raw`\bgit\b[^|;&()]*\bpush\b[^|;&]*(\s-f\b|--force)`,
    // The stash stack is shared by every worktree. Allowed: list, show,
    // apply, and a tagged push (`git stash push -u -m <tag>`); everything else
    // can take or destroy another session's entry.
    // Anchored to the subcommand slot (optionally after `-C <dir>`), so a
    // `stash@{0}` argument is not read as a second stash command.
    String.raw`\bgit\s+(?:-C\s+\S+\s+)?stash\b(?!\s+(list|show|apply)\b)(?!\s+push\b[^|;&]*\s-m\b)`,
  ].join('|'),
);
// The owner merges. A direct `gh pr merge` (or the API route under it) takes
// that decision away from them.
const GH_MERGE = /\bgh\b[^|;&]*\bpr\s+merge\b|\bgh\s+api\b[^|;&]*\/merge\b/;
// What "do not build there, do not commit there" means concretely: commits,
// history rewrites, non-fast-forward pulls, and every command that writes an
// application's files (rc fit/ats/truth/cover/new-app, rc gate --write) or
// runs the gate's renders. Read-only rc commands (`rc status`, `rc ledger
// check`, plain `rc gate`, which renders only into build/) are allowed, but
// `make check`/`make gate` are not: they belong to the worktree you will
// commit from.
const PRIMARY_BANNED = new RegExp(
  [
    String.raw`\bgit\s+(commit|merge|rebase|cherry-pick|am)\b`,
    String.raw`\bgit\s+pull\b(?![^|;&]*--ff-only)`,
    String.raw`\brc\s+(fit|ats|truth|cover|new-app)\b`,
    String.raw`\brc\s+gate\b[^|;&]*--write`,
    String.raw`\bmake\s+(check|gate|master)\b`,
  ].join('|'),
);

export function decide(command, cwd, projectDir) {
  if (DESTRUCTIVE_GIT.test(command) && !command.includes('RC_DESTRUCTIVE_OK=1')) {
    return (
      'Blocked: this git command can destroy another session’s only copy of its work — the working tree ' +
      'and the stash stack are shared (CONTRIBUTING.md, “Never do this”). First run `git status` (or ' +
      '`git stash list`) and read it; commit anything that exists nowhere else to a branch. To set work ' +
      'aside use a WIP commit, or `git stash push -u -m <tag>` and `git stash apply <sha>`. If you have ' +
      'looked and it is safe, re-run the exact command prefixed with RC_DESTRUCTIVE_OK=1.'
    );
  }

  if (GH_MERGE.test(command)) {
    return (
      'Blocked: the owner merges PRs (CLAUDE.md). Push your branch, open the PR with `gh pr create`, run ' +
      '`scripts/combine-check.sh`, and tell the owner it is ready.'
    );
  }

  if (PRIMARY_BANNED.test(command)) {
    const primary = primaryRootOf(projectDir);
    if (!isParallel(primary)) return null;
    for (const dir of effectiveDirs(command, cwd)) {
      const root = checkoutRoot(dir);
      if (root && root === primary && isPrimaryCheckout(root)) {
        return (
          'Blocked: this copy uses workflow: parallel (profile/preferences.md), so the primary checkout stays ' +
          'on main, clean, fast-forward only — never commit, rebase, or write application files there ' +
          '(CLAUDE.md). Start work with ' +
          '`scripts/git-new.sh <type>/<slug> "<intent>"` and run this inside the worktree it prints. ' +
          'To update main here: `git pull --ff-only`.'
        );
      }
    }
  }

  return null;
}

function main() {
  let input;
  try {
    input = JSON.parse(readFileSync(0, 'utf8'));
  } catch {
    return 0;
  }
  if (input.tool_name !== 'Bash') return 0;
  const command = input.tool_input?.command;
  if (typeof command !== 'string') return 0;
  const cwd = input.cwd || process.cwd();
  const projectDir = process.env.CLAUDE_PROJECT_DIR || cwd;

  let verdict = null;
  try {
    verdict = decide(command, cwd, projectDir);
  } catch {
    return 0; // fail open
  }
  if (verdict) {
    process.stderr.write(verdict + '\n');
    return 2;
  }
  return 0;
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].split('/').pop())) {
  process.exit(main());
}
