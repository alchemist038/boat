# Codex Start Here

This file is the root-level instruction sheet for Codex sessions working on this
project from `ins14` or `i5`.

## Machine Names

- `ins14`: the main machine for this workspace
- `i5`: the secondary machine that can join the work

## First Steps

1. Identify which machine you are running on.
2. Run `git pull` in the repo root before starting work.
3. Read the direct human instruction file for your machine:
   - `TO_INS14_FROM_ME.md`
   - `TO_I5_FROM_ME.md`
4. Read the coordination guide:
   `workspace_codex/coordination/README.md`
5. Check your machine inbox:
   - `workspace_codex/coordination/inbox/ins14/`
   - `workspace_codex/coordination/inbox/i5/`

## Task Intake Rule

The root-level `TO_*_FROM_ME.md` files are the simplest human-to-Codex entry point.

If a task file exists in your inbox, treat the newest one as the active request.

Task file naming rule:

`YYYYMMDD_HHMM_<topic>__<from>_to_<to>.md`

## Work Rule

- Create a branch as `<machine>/<task_id>`
- Keep scratch work under `workspace_codex/`
- Do not write temporary files in the repo root
- Do not promote outputs to `GPT/output/` unless the task explicitly calls for it
- Avoid editing the same files on both machines at the same time

## Handoff Rule

When work is complete or blocked:

1. Write a note in `workspace_codex/coordination/handoffs/`
2. Move the original task file to `workspace_codex/coordination/done/`
3. Commit and push the branch or result

Use this template:

`workspace_codex/templates/CODEX_HANDOFF_TEMPLATE.md`

## Task Template

When creating a new task for the other machine, use:

`workspace_codex/templates/CODEX_TASK_TEMPLATE.md`

## Suggested Prompt For Codex

For `i5`:

`Read the latest task in workspace_codex/coordination/inbox/i5, execute it on a new branch, write a handoff file in workspace_codex/coordination/handoffs, and move the task file to workspace_codex/coordination/done when finished.`

For `ins14`:

`Read the latest task in workspace_codex/coordination/inbox/ins14, execute it on a new branch, write a handoff file in workspace_codex/coordination/handoffs, and move the task file to workspace_codex/coordination/done when finished.`

## If No Task Exists

Report that the inbox is empty and ask for the next assignment, or create a new
task file for the other machine if this session is the sender.
