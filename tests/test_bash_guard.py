"""scripts/hooks/bash-guard.mjs: every banned command blocks, the override works,
read-only and worktree commands pass, and the primary-checkout rules apply only
under `workflow: parallel`. Runs the real module under node."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from rc.paths import ROOT

GUARD = ROOT / "scripts" / "hooks" / "bash-guard.mjs"
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def make_layout(base: Path, preferences: str | None) -> tuple[Path, Path]:
    """A fake primary checkout (.git directory) with one linked worktree (.git file)."""
    primary = base / "primary"
    (primary / ".git").mkdir(parents=True)
    (primary / "applications").mkdir()
    if preferences is not None:
        (primary / "profile").mkdir()
        (primary / "profile" / "preferences.md").write_text(preferences)
    wt = primary / ".claude" / "worktrees" / "app-acme"
    wt.mkdir(parents=True)
    (wt / ".git").write_text(f"gitdir: {primary / '.git' / 'worktrees' / 'app-acme'}\n")
    return primary, wt


@pytest.fixture(scope="module")
def layout(tmp_path_factory):
    """An owner who chose the parallel workflow during onboarding."""
    return make_layout(tmp_path_factory.mktemp("guard"),
                       "# Preferences\n\n## Workflow\n- Workflow: parallel\n")


def decide(cases: list[tuple[str, Path, Path]]) -> list[str | None]:
    script = (f"import {{ decide }} from {json.dumps(GUARD.as_uri())};"
              "const cases = JSON.parse(process.argv[1]);"
              "console.log(JSON.stringify(cases.map(([c, cwd, p]) => decide(c, cwd, p))));")
    payload = json.dumps([[c, str(cwd), str(p)] for c, cwd, p in cases])
    out = subprocess.run(["node", "--input-type=module", "-e", script, payload],
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


DESTRUCTIVE = [
    "git reset --hard origin/main",
    "git clean -fd",
    "git clean -xfd",
    "git checkout -- applications/x/report.json",
    "git restore STATUS.md",
    "git push --force origin app/x",
    "git push -f",
    "git stash",
    "git stash pop",
    "git stash drop",
    "git stash clear",
    "git stash push -u",
    "cd /tmp && /usr/bin/git reset --hard",
    "git -C ../other stash pop",
]
SAFE_GIT = [
    "git status",
    "git stash list",
    "git stash show -p stash@{0}",
    "git stash apply 1a2b3c",
    "git stash push -u -m app-acme-wip",
    "git restore --staged ledger/ledger.yaml",
    "git checkout -b app/acme",
    "git push -u origin app/acme",
    "git clean -n",
]
PRIMARY_ONLY = [
    "git commit -m 'app: acme'",
    "git rebase origin/main",
    "git merge origin/main",
    "git pull",
    "git pull --rebase",
    "git cherry-pick abc123",
    "uv run rc fit applications/x --solve",
    "uv run rc ats x",
    "uv run rc truth x",
    "uv run rc cover x",
    "uv run rc new-app --company A --role B --file build/p.txt",
    "uv run rc gate --write",
    "make check",
    "make gate",
    "make master",
]
READ_ONLY = [
    "git pull --ff-only",
    "git fetch origin",
    "git log --oneline -5",
    "uv run rc status",
    "uv run rc ledger check",
    "uv run rc gate",
    "make doctor",
    "scripts/git-new.sh app/acme 'tailor Acme'",
]


def test_destructive_blocked_everywhere_and_override_works(layout):
    primary, wt = layout
    for where in (primary, wt):
        verdicts = decide([(c, where, where) for c in DESTRUCTIVE])
        for c, v in zip(DESTRUCTIVE, verdicts):
            assert v and "only copy" in v, c
    overridden = decide([(f"RC_DESTRUCTIVE_OK=1 {c}", wt, wt) for c in DESTRUCTIVE])
    assert overridden == [None] * len(DESTRUCTIVE)


def test_safe_git_allowed(layout):
    _, wt = layout
    assert decide([(c, wt, wt) for c in SAFE_GIT]) == [None] * len(SAFE_GIT)


def test_merge_is_the_owners(layout):
    _, wt = layout
    cmds = ["gh pr merge 12 --squash", "/opt/homebrew/bin/gh pr merge 12",
            "gh api -X PUT repos/o/r/pulls/12/merge"]
    for c, v in zip(cmds, decide([(c, wt, wt) for c in cmds])):
        assert v and "the owner merges" in v, c
    assert decide([("gh pr create --fill", wt, wt), ("gh pr view 12", wt, wt)]) == [None, None]


def test_primary_only_rules(layout):
    primary, wt = layout
    in_primary = decide([(c, primary, primary) for c in PRIMARY_ONLY])
    for c, v in zip(PRIMARY_ONLY, in_primary):
        assert v and "primary checkout" in v, c
    # From a subdirectory of the primary, and via a session whose project dir is the worktree.
    sub = decide([("git commit -m x", primary / "applications", primary),
                  (f"cd {primary} && git commit -m x", wt, wt)])
    assert all(v and "primary checkout" in v for v in sub)
    # The same commands are the normal workflow inside a worktree.
    assert decide([(c, wt, wt) for c in PRIMARY_ONLY]) == [None] * len(PRIMARY_ONLY)


def test_read_only_allowed_in_primary(layout):
    primary, _ = layout
    assert decide([(c, primary, primary) for c in READ_ONLY]) == [None] * len(READ_ONLY)


@pytest.mark.parametrize("preferences", [
    None,                                                  # template, before onboarding
    "# Preferences\n\n## Workflow\n- Workflow: single\n",
    "# Preferences\n\n## Targets\n- Roles: analyst\n",  # no workflow line
    "- Workflow: <parallel | single>\n",                  # unfilled example slot
])
def test_single_workflow_commits_on_main(tmp_path, preferences):
    primary, _ = make_layout(tmp_path, preferences)
    assert decide([(c, primary, primary) for c in PRIMARY_ONLY]) == [None] * len(PRIMARY_ONLY)
    # Destructive git and merging stay blocked in every workflow.
    blocked = decide([(DESTRUCTIVE[0], primary, primary), ("gh pr merge 3", primary, primary)])
    assert all(blocked)


def test_workflow_line_forms(tmp_path):
    for i, line in enumerate(["workflow: parallel", "* WORKFLOW: Parallel", "  - Workflow:   parallel  "]):
        primary, _ = make_layout(tmp_path / str(i), f"## Workflow\n{line}\n")
        assert decide([("git commit -m x", primary, primary)])[0], line


def test_unexpanded_cd_target_is_skipped_not_guessed(layout):
    primary, wt = layout
    assert decide([('cd "$SOMEWHERE" && git commit -m x', wt, wt)]) == [None]


def test_hook_protocol_exit_codes(layout):
    """End to end: stdin JSON in, exit 2 + stderr to block, 0 to allow, 0 on garbage (fail open)."""
    primary, wt = layout

    def run(stdin: str, project: Path) -> subprocess.CompletedProcess:
        return subprocess.run(["node", str(GUARD)], input=stdin, capture_output=True, text=True,
                              env={"PATH": "/usr/bin:/bin:/opt/homebrew/bin:/usr/local/bin",
                                   "CLAUDE_PROJECT_DIR": str(project)})

    block = run(json.dumps({"tool_name": "Bash", "cwd": str(primary),
                            "tool_input": {"command": "git commit -m x"}}), primary)
    assert block.returncode == 2 and "primary checkout" in block.stderr
    allow = run(json.dumps({"tool_name": "Bash", "cwd": str(wt),
                            "tool_input": {"command": "git commit -m x"}}), wt)
    assert allow.returncode == 0
    assert run("not json", wt).returncode == 0
