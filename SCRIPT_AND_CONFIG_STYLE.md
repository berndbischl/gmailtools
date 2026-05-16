# SCRIPT_AND_CONFIG_STYLE.md — documentation style for `sysadmin/` scripts and config files

Binding documentation style for every `*.sh` / `*.py` / `*.conf` /
systemd unit / sshd drop-in under `sysadmin/`. Consult while writing or
reviewing.

The reader two years from now — a teammate, a future you, or an agent —
must be able to reconstruct **why** every section of every script or
config file in `sysadmin/` exists from the file alone, not only what the
next line does.

## Required for every script (`*.sh`, `*.py`, …)

- **Header block** stating: purpose; when to run; prerequisites;
  side-effects (every file or piece of system state it touches, listed
  explicitly); idempotency strategy; non-obvious failure modes; how to
  extend.
- **Section dividers** for each logical block, each with a comment
  explaining what the section does, *why* it exists, and which files /
  state it touches.
- **Inline rationale** for any non-obvious command, flag, redirection,
  or guard (e.g. why `set -euo pipefail`, why `grep -qxF`, why
  `mkdir -p` rather than `mkdir`). Self-evident lines may stay
  uncommented; non-obvious ones may not. When in doubt, comment.

**Short-script exception:** for very short scripts (under ~20 lines,
single purpose, no non-obvious commands), the header block is still
mandatory, but section dividers and inline rationale may be omitted if
the script is self-evident end-to-end.

## Required for every config file (sshd drop-ins, systemd units, `*.conf`, …)

- **Header block** (in the file's native comment syntax) stating: which
  software consumes the file; the runtime path it must live at; who
  manages it (a script in `sysadmin/`? hand-edited?); how changes are
  applied (restart, reload, signal); and the source of every non-default
  setting (upstream default, hardening guide, our policy).
- **Inline annotation** of every non-default directive: source and
  rationale on the line above or trailing the directive.
- **Section comments** grouping related directives.

## Style

- Explain *why* and *what changed*, not what the next line literally does.
- Use absolute paths in comments where ambiguity matters.
- Verbose clarity over clever brevity. These files are read more often
  than they are run.
