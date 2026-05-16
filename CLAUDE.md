# CLAUDE.md — project-level Claude Code entrypoint for `sysadmin/`

This is the ruleset for a project to create tools for GMAIL emails.


## MD file overview

Each item is tagged by audience:
**(claude-facing)** means the file exists for Claude to read;
**(human-facing)** means it serves the operator.

- `DECISIONS.md` **(claude-facing)** — locked architectural decisions and their *why*. Complement of `PLAN.md`. **Human does not modify**.
- `PLAN.md` **(claude-facing)** — open follow-ups and deferred discussions. Read at the start of any non-trivial work. **Human does not modify**.
- `README.md` **(human-facing)** — repo entry point.
- `PYTHON_STYLE.md` **(claude-facing)** — style Claude follows when writing Python code in this project.
- `SCRIPT_AND_CONFIG_STYLE.md` **(claude-facing)** — documentation style Claude follows when writing scripts/configs.
- `TODO.md` **(human-facing)** — operator's personal scratch list. **Don't modify, don't reference, don't read proactively.**


## Keep docs in sync

- When the system is changed, update the appropriate docs above.
- If in doubt, ask the user.

## Never mutate Gmail without explicit confirmation

**No action that changes state in the user's Gmail account may be taken without
an explicit, per-action "go" from the user.** This is absolute. No exceptions,
no defaults, no "obvious" follow-ups, no batching multiple mutations under one
approval.

This covers — non-exhaustively — sending, replying, forwarding, drafting (even
unsent drafts), deleting, trashing, archiving, marking read/unread,
starring/unstarring, applying or removing labels, moving messages between
folders/labels, modifying filters or rules, changing settings, granting or
revoking OAuth scopes, and any write/modify call against the Gmail API.

Read-only inspection (listing, searching, reading messages and metadata) is
allowed without per-action confirmation, but never bury a mutating call inside
a read-looking operation.

Announce the intended Gmail action in plain text, name the exact messages /
labels / recipients affected, wait for confirmation, then act. One approval =
one action. Approval for "delete these 3 messages" does NOT extend to a 4th,
even if it looks identical.

## Documenting scripts and config files

Follow `SCRIPT_AND_CONFIG_STYLE.md`.

## General style

- Keep prose terse, precise, no fluff.
- Avoid citing other docs or section numbers unless load-bearing —
  cross-refs rot when files move.
