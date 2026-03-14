# Multi-Machine Codex Workflow

Use this folder when `ins14` and `i5` hand work to each other through Git.

## Layout

- `inbox/ins14/`
  - task files for the Codex session running on `ins14`
- `inbox/i5/`
  - task files for the Codex session running on `i5`
- `handoffs/`
  - completion notes, blocked notes, and next steps
- `done/`
  - completed task files moved out of the inbox
- `jobs/active/`
  - long-run jobs that may need resume
- `jobs/done/`
  - completed long-run jobs

## Core Rule

One task = one markdown file.

Do not keep a shared queue in a single file. Per-task files reduce merge conflicts
and make it easy for Codex to pick up the latest assignment.

## File Naming

Use this pattern:

`YYYYMMDD_HHMM_<topic>__<from>_to_<to>.md`

Example:

`20260314_1315_bt_cleanup__ins14_to_i5.md`

## Branch Rule

The machine that executes the task creates the branch.

Use this pattern:

`<machine>/<task_id>`

Example:

`i5/20260314_1315_bt_cleanup`

## Fast Workflow

1. Sender creates a task file in the receiver inbox from the task template.
2. Sender commits and pushes that file.
3. Receiver runs `git pull`.
4. Receiver asks Codex to read the newest task file in its inbox and execute it.
5. Receiver writes a handoff note in `handoffs/`.
6. Receiver moves the original task file from `inbox/<machine>/` to `done/`.
7. Receiver commits and pushes results plus the handoff.

## Suggested Codex Prompt

Use prompts like this on either machine:

`Read the latest task in workspace_codex/coordination/inbox/i5, execute it on a new branch, write a handoff file in workspace_codex/coordination/handoffs, and move the task file to workspace_codex/coordination/done when finished.`

Swap `i5` with `ins14` as needed.

## Handoff Contract

Every handoff should include:

- what was changed
- files touched
- tests or checks run
- what is still blocked
- exact next step for the other machine

For multi-hour collection jobs, also create a job file from:

`workspace_codex/templates/CODEX_LONGRUN_JOB_TEMPLATE.md`

and keep it under:

`workspace_codex/coordination/jobs/active/`

## Scope Guidance

Good delegated tasks:

- isolated bug fixes
- documentation updates
- one analysis run with a clear output path
- test additions
- refactors limited to a known file set

Avoid delegating both sides to edit the same files at the same time unless one side
is clearly stacked on top of the other side's branch.
