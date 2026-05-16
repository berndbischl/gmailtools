"""OAuth flow + token caching for the Gmail API.

The OAuth client (Google's "credentials.json") is stored encrypted in
`pass` under the entry `gmailtools/credentials`; `pass show` decrypts
through gpg-agent (passphrase via pinentry) at runtime, plaintext never
hits disk. The per-user refresh token lives at
~/.config/gmailtools/token.json (0600), written after the first browser
consent and auto-refreshed thereafter.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

# gmail.modify covers: read, label, archive (removing INBOX), trash.
# It does NOT cover permanent delete — that needs the full mail.google.com scope.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

CONFIG_DIR = Path(os.environ.get("GMAILTOOLS_CONFIG_DIR", Path.home() / ".config" / "gmailtools"))
TOKEN_PATH = CONFIG_DIR / "token.json"
PASS_ENTRY = os.environ.get("GMAILTOOLS_PASS_ENTRY", "gmailtools/credentials")


def _ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(CONFIG_DIR, 0o700)


def _load_token() -> Credentials | None:
    if not TOKEN_PATH.exists():
        return None
    return Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)


def _save_token(creds: Credentials) -> None:
    _ensure_config_dir()
    TOKEN_PATH.write_text(creds.to_json())
    os.chmod(TOKEN_PATH, 0o600)


def _load_client_config() -> dict[str, Any]:
    """Decrypt the OAuth client JSON via `pass show` (gpg-agent will prompt)."""
    try:
        out = subprocess.check_output(["pass", "show", PASS_ENTRY], stderr=subprocess.PIPE)
    except FileNotFoundError as e:
        raise SystemExit(
            "`pass` not found on PATH. Install pass and store the OAuth client as "
            f"'{PASS_ENTRY}' (see README)."
        ) from e
    except subprocess.CalledProcessError as e:
        msg = e.stderr.decode("utf-8", "replace").strip() or f"exit {e.returncode}"
        raise SystemExit(f"`pass show {PASS_ENTRY}` failed: {msg}") from e
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
