# gmailtools

Personal Gmail CLI. Search, label, archive, and trash messages by
Gmail search query, in bulk.

## How `gmt` connects to Gmail

**Background.** Gmail is Google's hosted email service; the **Gmail
API** is its REST interface (we use the official Python client
`google-api-python-client`). Every Gmail API call is scoped to a
**Google Cloud project** — a namespace/billing container that owns the
API enablement and the OAuth client we register inside it. **OAuth
2.0** is a delegated-authorization protocol: instead of giving the app
your Google password, you grant it a scoped, revocable token through a
Google-hosted consent page.

Access is brokered by two artifacts:

- **OAuth client** — identifies the app. Registered once in Google
  Cloud Console as a **Desktop** client (loopback redirect
  `http://localhost:<port>`, no web server). The downloaded JSON is
  stored encrypted in **`pass`** under the entry `gmailtools/credentials`;
  `gmt` reads it at runtime via `pass show`, which decrypts through
  gpg-agent (pinentry passphrase prompt). Plaintext never lands on disk.
  Override the entry name with `$GMAILTOOLS_PASS_ENTRY`.
- **Refresh token** — identifies the app acting on *your* mailbox.
  Written to `~/.config/gmailtools/token.json` (mode `0600`, dir `0700`,
  outside the repo) after the first browser consent. Auto-refreshed
  thereafter; no re-consent needed within the token's validity window.

Scope is **`gmail.modify` only** — read, label, archive, trash.
Permanent delete (`mail.google.com`) is deliberately not requested:
trashed messages auto-purge after 30 days, so all "destructive" ops are
reversible inside that window.

The OAuth app stays in Google's "testing" status (no verification
needed for personal use); the trade-off is that only Google accounts
explicitly listed as **test users** on the consent screen can complete
the flow. For personal use that's just yourself.

If the client secret leaks: delete the client in Cloud Console →
Clients, create a fresh one, update the `pass` entry
(`pass insert -m gmailtools/credentials < new-client.json`),
`rm ~/.config/gmailtools/token.json`, re-run to re-consent.

## Install and run

```sh
cd ~/cos/gmailtools
uv sync                       # creates .venv, installs deps
uv run gmt --help             # entry point
```

## Scopes

This tool requests `gmail.modify` only — covers read, label, archive,
and trash. It does *not* request permanent-delete; messages go to
Trash (auto-purged by Gmail after 30 days), which is reversible.

## Examples

```sh
# Read-only: see what matches a query
uv run gmt search "from:newsletter@example.com older_than:1y"

# List existing labels
uv run gmt labels

# Bulk label (dry run first, then --yes to commit)
uv run gmt label add Newsletters -q "list:*@example.com" --create
uv run gmt label add Newsletters -q "list:*@example.com" --create --yes

# Bulk archive
uv run gmt archive -q "label:Newsletters older_than:30d" --yes

# Bulk trash (reversible 30 days)
uv run gmt trash -q "from:spammy@example.com older_than:6m" --yes
```

Queries use Gmail's standard search syntax:
<https://support.google.com/mail/answer/7190>.

## Files

```
src/gmailtools/
  auth.py     # OAuth flow, token caching to ~/.config/gmailtools/
  client.py   # Gmail API wrappers (search, label, batch modify, trash)
  cli.py      # Typer commands: search / labels / label / archive / trash
```
