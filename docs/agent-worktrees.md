# Agent worktrees

Use one isolated worktree per mutating agent or task path.

## Preflight

Before creating or using a worktree:

- inspect git status and existing worktrees;
- fetch required remotes;
- verify the exact base commit;
- make sure the intended branch does not already contain unrelated work;
- preserve uncommitted and unique work.

## Pattern

~~~bash
git fetch --all --prune
git worktree list
git status --short --branch
git worktree add <path> -b <task-branch> <exact-base-sha>
~~~

If the execution environment already provides an isolated checkout, use it instead of nesting another worktree.

## Rules

- Never let two mutating agents write to the same branch or worktree concurrently.
- A reviewer should inspect the exact candidate read-only; it does not need to mutate the builder worktree.
- Do not use git clean, hard reset, or force checkout to make a worktree convenient.
- Delete an obsolete worktree only after its useful commits/evidence are preserved and no active task still references it.
- Branch names and worktree paths are labels, not proof of ancestry. Verify commit objects directly.
