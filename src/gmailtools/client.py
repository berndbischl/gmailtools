"""Thin wrappers over the Gmail API.

Operations are message-oriented (not thread-oriented) because Gmail
labels and trash apply per-message. Bulk mutations go through
batchModify, which is the cheap path for large queries.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from googleapiclient.discovery import Resource

USER = "me"


def search_message_ids(svc: Resource, query: str, max_results: int | None = None) -> Iterator[str]:
    """Yield message ids matching a Gmail search query, paging as needed."""
    page_token: str | None = None
    yielded = 0
    while True:
        req = svc.users().messages().list(
            userId=USER,
            q=query,
            pageToken=page_token,
            maxResults=500,
        )
        resp = req.execute()
        for m in resp.get("messages", []):
            yield m["id"]
            yielded += 1
            if max_results is not None and yielded >= max_results:
                return
        page_token = resp.get("nextPageToken")
        if not page_token:
            return


def get_message_meta(svc: Resource, msg_id: str) -> dict[str, Any]:
    """Fetch only header metadata for a message (cheap)."""
    return svc.users().messages().get(
        userId=USER,
        id=msg_id,
        format="metadata",
        metadataHeaders=["From", "Subject", "Date"],
    ).execute()


def get_profile(svc: Resource) -> dict[str, Any]:
    """Account-level totals: emailAddress, messagesTotal, threadsTotal, historyId."""
    return svc.users().getProfile(userId=USER).execute()


def get_label(svc: Resource, label_id: str) -> dict[str, Any]:
    """Per-label counts (messagesTotal, messagesUnread, threadsTotal, threadsUnread)."""
    return svc.users().labels().get(userId=USER, id=label_id).execute()


def list_labels(svc: Resource) -> list[dict[str, Any]]:
    return svc.users().labels().list(userId=USER).execute().get("labels", [])


def label_id_by_name(svc: Resource, name: str) -> str | None:
    for lbl in list_labels(svc):
        if lbl["name"] == name:
            return lbl["id"]
    return None


def create_label(svc: Resource, name: str) -> str:
    body = {"name": name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}
    return svc.users().labels().create(userId=USER, body=body).execute()["id"]


def batch_modify(
    svc: Resource,
    ids: list[str],
    add: list[str] | None = None,
    remove: list[str] | None = None,
) -> None:
    """Apply label add/remove to up to 1000 ids per call; chunks larger lists."""
    if not ids:
        return
    body: dict[str, Any] = {}
    if add:
        body["addLabelIds"] = add
    if remove:
        body["removeLabelIds"] = remove
    for chunk_start in range(0, len(ids), 1000):
        chunk = ids[chunk_start:chunk_start + 1000]
        svc.users().messages().batchModify(
            userId=USER,
            body={"ids": chunk, **body},
        ).execute()


def trash_messages(svc: Resource, ids: list[str]) -> None:
    """No batch endpoint for trash; one call per id."""
    for mid in ids:
        svc.users().messages().trash(userId=USER, id=mid).execute()
