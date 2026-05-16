# gmailtools

Personal Gmail CLI. Search, label, archive, and trash messages by
Gmail search query, in bulk.

## One-time setup

Done in the browser, by you:

1. Go to <https://console.cloud.google.com/>, create a new project
   (e.g. `gmailtools`).
2. In that project, enable the **Gmail API**
   (APIs & Services → Library → Gmail API → Enable).
3. APIs & Services → **OAuth consent screen**:
   - User type: **External**.
   - Fill in app name + your email; skip the optional fields.
   - On the *Test users* step, add your own Gmail address. Without
     this, token issuance will fail until the app is verified.
4. APIs & Services → **Credentials** → *Create credentials* →
   **OAuth client ID**:
   - Application type: **Desktop app**.
   - Download the JSON. Save it as
     `~/.config/gmailtools/credentials.json` with mode `0600`:
     ```sh
     mkdir -p -m 700 ~/.config/gmailtools
     mv ~/Downloads/client_secret_*.json ~/.config/gmailtools/credentials.json
     chmod 600 ~/.config/gmailtools/credentials.json
     ```

The first `gmt` command run will open a browser tab to consent, then
cache a refresh token at `~/.config/gmailtools/token.json` (also
mode 0600). Neither file is ever in the repo.

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
