# To i5 From Me

This is the simple root-level note that the human can edit directly.

## State

- machine: i5
- sender: me
- status: requested
- last_updated: 2026-03-14 13:05 JST
- priority: low
- branch:

## Active Request

Read the root instruction files and confirm that you can receive work from this
repo-driven flow.

Do not change application code for this test.

Reply with:

1. machine name you believe you are on
2. current git branch
3. latest local commit hash and subject
4. whether you can read `CODEX_START_HERE.md` and this file
5. whether `workspace_codex/coordination/inbox/i5/` is visible

Then write a short handoff note saying the intake test was received.

## Context

- files: `CODEX_START_HERE.md`, `TO_I5_FROM_ME.md`, `workspace_codex/coordination/README.md`
- commands: `git branch --show-current`, `git log -1 --oneline`
- constraints: no code edits, no data edits
- output target: `workspace_codex/coordination/handoffs/`

## Codex Action

1. Read `CODEX_START_HERE.md`.
2. If `Active Request` is `NONE`, report that there is no active request.
3. If `Active Request` has content, execute it or convert it into a tracked task
   under `workspace_codex/coordination/inbox/i5/` when needed.
4. Write completion or blocked status to `workspace_codex/coordination/handoffs/`.
5. Update this file when the request is finished or replaced.
