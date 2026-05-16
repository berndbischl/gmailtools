"""OAuth flow + token caching for the Gmail API.

Credentials and the cached token live under ~/.config/gmailtools/ so they
stay out of the repo. credentials.json is the OAuth client (downloaded
from Google Cloud Console once); token.json is the per-user refresh
token written after the first browser consent.
"""

from __future__ import annotations

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

# gmail.modify covers: read, label, archive (removing INBOX), trash.
# It does NOT cover permanent delete — that needs the full mail.google.com scope.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

CONFIG_DIR = Path(os.environ.get("GMAILTOOLS_CONFIG_DIR", Path.home() / ".config" / "gmailtools"))
CREDENTIALS_PATH = CONFIG_DIR / "credentials.json"
TOKEN_PATH = CONFIG_DIR / "token.json"


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


def get_credentials() -> Credentials:
    creds = _load_token()
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_token(creds)
        return creds
    if not CREDENTIALS_PATH.exists():
        raise SystemExit(
            f"Missing OAuth client at {CREDENTIALS_PATH}. "
            "See README for the one-time Google Cloud setup."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(port=0)
    _save_token(creds)
    return creds


def service() -> Resource:
    return build("gmail", "v1", credentials=get_credentials(), cache_discovery=False)
