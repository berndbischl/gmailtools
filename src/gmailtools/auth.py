"""OAuth flow + token storage for the Gmail API.

Both secrets live encrypted in `pass`; nothing sensitive is on disk
plaintext:

- `gmailtools/credentials` — the OAuth client JSON (static, identifies
  the app to Google). Read on first consent only.
- `gmailtools/token` — the per-user token bundle (refresh_token,
  access_token, client_id, client_secret, scopes, expiry). Read on
  every `gmt` run; rewritten on every access-token refresh.

`pass show` triggers gpg-agent → pinentry; with TTL=0 every read
prompts for the passphrase. Writes (`pass insert`) only need the public
key, so they're silent.

Override entry names with `$GMAILTOOLS_PASS_ENTRY` (client) and
`$GMAILTOOLS_TOKEN_PASS_ENTRY` (token).
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

# gmail.modify covers: read, label, archive (removing INBOX), trash.
# It does NOT cover permanent delete — that needs the full mail.google.com scope.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

CLIENT_PASS_ENTRY = os.environ.get("GMAILTOOLS_PASS_ENTRY", "gmailtools/credentials")
TOKEN_PASS_ENTRY = os.environ.get("GMAILTOOLS_TOKEN_PASS_ENTRY", "gmailtools/token")


def _pass_show(entry: str) -> bytes | None:
    """Return decrypted content, or None if the entry doesn't exist in the store."""
    try:
        return subprocess.check_output(["pass", "show", entry], stderr=subprocess.PIPE)
    except FileNotFoundError as e:
        raise SystemExit(
            "`pass` not found on PATH. Install pass and store the OAuth entries "
            "(see README)."
        ) from e
    except subprocess.CalledProcessError as e:
        msg = e.stderr.decode("utf-8", "replace")
        if "is not in the password store" in msg:
            return None
        raise SystemExit(
            f"`pass show {entry}` failed: {msg.strip() or f'exit {e.returncode}'}"
        ) from e


def _pass_insert(entry: str, data: bytes) -> None:
    """Overwrite the entry with `data` (encrypted to the store's gpg recipient)."""
    try:
        subprocess.run(
            ["pass", "insert", "-m", "-f", entry],
            input=data,
            check=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
        )
    except FileNotFoundError as e:
        raise SystemExit("`pass` not found on PATH.") from e
    except subprocess.CalledProcessError as e:
        msg = e.stderr.decode("utf-8", "replace").strip() or f"exit {e.returncode}"
        raise SystemExit(f"`pass insert {entry}` failed: {msg}") from e


def _load_token() -> Credentials | None:
    out = _pass_show(TOKEN_PASS_ENTRY)
    if out is None:
        return None
    return Credentials.from_authorized_user_info(json.loads(out), SCOPES)


def _save_token(creds: Credentials) -> None:
    _pass_insert(TOKEN_PASS_ENTRY, creds.to_json().encode())


def _load_client_config() -> dict[str, Any]:
    out = _pass_show(CLIENT_PASS_ENTRY)
    if out is None:
        raise SystemExit(
            f"OAuth client not found in pass under '{CLIENT_PASS_ENTRY}'. See README."
        )
    return json.loads(out)


def get_credentials() -> Credentials:
    creds = _load_token()
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_token(creds)
        return creds
    flow = InstalledAppFlow.from_client_config(_load_client_config(), SCOPES)
    creds = flow.run_local_server(port=0)
    _save_token(creds)
    return creds


def service() -> Resource:
    return build("gmail", "v1", credentials=get_credentials(), cache_discovery=False)
