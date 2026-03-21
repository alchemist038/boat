# Long-Run Job Tracking

Use this area for jobs that may run for hours or span multiple sessions.

Examples:

- odds backfill on `i5`
- large multi-month collection
- copy-and-merge tasks that finish on `ins14`

## Layout

- `active/`
  - one markdown file per active long-run job
- `done/`
  - completed long-run jobs

## Rule

Every long-run job must have:

- one job file in `active/`
- one exact command to resume
- one clearly stated completion rule
- one copy/import rule if another machine must finish the work

## Resume Principle

Prefer commands that are idempotent by day.

In this project, the safest base is:

- `--resume-existing-days`
- `--refresh-every-days 1`
- machine-local clone and machine-local `data/`

## Ownership

If `i5` performs collection and file copy, keep ownership with `i5` until:

1. collection is complete
2. copy to `ins14` is complete
3. handoff to `ins14` is written

After that, `ins14` owns merge/import/final DB refresh.

## Staging Area

When preparing files for `ins14`, use the repo-root [`copy/`](../../../copy/)
folder as the local staging area:

- `copy/collect/`
  - initial copied files
- `copy/move/`
  - verified handoff bundle
