"""gmt — Gmail CLI.

All mutating commands show a sample + count first and require --yes to
actually run. Queries use Gmail's standard search syntax
(https://support.google.com/mail/answer/7190).
"""

from __future__ import annotations

import typer

from . import auth, client

app = typer.Typer(no_args_is_help=True, add_completion=False)
label_app = typer.Typer(no_args_is_help=True, help="Add/remove labels in bulk.")
app.add_typer(label_app, name="label")

SAMPLE_SIZE = 5


def _collect(query: str, limit: int | None) -> tuple[list[str], object]:
    svc = auth.service()
    ids = list(client.search_message_ids(svc, query, max_results=limit))
    return ids, svc


def _preview(svc, ids: list[str]) -> None:
    typer.echo(f"matched {len(ids)} message(s)")
    for mid in ids[:SAMPLE_SIZE]:
        m = client.get_message_meta(svc, mid)
        headers = {h["name"]: h["value"] for h in m.get("payload", {}).get("headers", [])}
        typer.echo(f"  {headers.get('Date', '?'):.25} | {headers.get('From', '?'):.40} | {headers.get('Subject', '?'):.60}")
    if len(ids) > SAMPLE_SIZE:
        typer.echo(f"  ... and {len(ids) - SAMPLE_SIZE} more")


def _confirm(yes: bool, verb: str, n: int) -> None:
    if yes:
        return
    typer.echo(f"\nDry run. Re-run with --yes to {verb} {n} message(s).")
    raise typer.Exit(0)


@app.command()
def search(
    query: str = typer.Argument(..., help="Gmail search query, e.g. 'from:foo older_than:1y'"),
    limit: int = typer.Option(50, help="Max results to display."),
) -> None:
    """List messages matching a query (read-only)."""
    ids, svc = _collect(query, limit)
    _preview(svc, ids)


@app.command()
def labels() -> None:
    """List all labels on the account."""
    svc = auth.service()
    for lbl in sorted(client.list_labels(svc), key=lambda x: x["name"]):
        typer.echo(f"{lbl['id']:20} {lbl['name']}")


# System labels worth surfacing in the overview. Gmail also exposes
# CATEGORY_* and CHAT, but those are noise for an account summary.
_OVERVIEW_SYSTEM_LABELS = ["INBOX", "UNREAD", "STARRED", "IMPORTANT", "SENT", "DRAFT", "SPAM", "TRASH"]


@app.command()
def overview(
    top: int = typer.Option(
        10, help="Show the N largest user labels by message count (0 to skip)."
    ),
) -> None:
    """Read-only summary of the account: totals, system labels, user labels."""
    svc = auth.service()
    prof = client.get_profile(svc)
    typer.echo(f"account:  {prof.get('emailAddress', '?')}")
    typer.echo(f"messages: {int(prof.get('messagesTotal', 0)):>10,}")
    typer.echo(f"threads:  {int(prof.get('threadsTotal', 0)):>10,}")

    typer.echo("\nsystem labels:")
    for lid in _OVERVIEW_SYSTEM_LABELS:
        lbl = client.get_label(svc, lid)
        total = int(lbl.get("messagesTotal", 0))
        unread = int(lbl.get("messagesUnread", 0))
        typer.echo(f"  {lid:10} total {total:>8,}   unread {unread:>6,}")

    all_labels = client.list_labels(svc)
    user_labels = [lbl for lbl in all_labels if lbl.get("type") == "user"]
    typer.echo(f"\nuser labels: {len(user_labels)}")

    if top > 0 and user_labels:
        # Per-label .get() is one API call each — cheap for typical label counts.
        sized = [(lbl["name"], client.get_label(svc, lbl["id"])) for lbl in user_labels]
        sized.sort(key=lambda x: int(x[1].get("messagesTotal", 0)), reverse=True)
        typer.echo(f"  top {min(top, len(sized))} by message count:")
        for name, lbl in sized[:top]:
            total = int(lbl.get("messagesTotal", 0))
            unread = int(lbl.get("messagesUnread", 0))
            typer.echo(f"    {name:30.30}  total {total:>8,}   unread {unread:>6,}")


def _resolve_label(svc, name: str, create_if_missing: bool) -> str:
    lid = client.label_id_by_name(svc, name)
    if lid:
        return lid
    if not create_if_missing:
        raise typer.BadParameter(f"label '{name}' does not exist (use --create to make it)")
    return client.create_label(svc, name)


@label_app.command("add")
def label_add(
    name: str = typer.Argument(..., help="Label name to add."),
    query: str = typer.Option(..., "--query", "-q", help="Gmail search query."),
    create: bool = typer.Option(False, help="Create label if it doesn't exist."),
    limit: int | None = typer.Option(None, help="Cap number of messages affected."),
    yes: bool = typer.Option(False, "--yes", help="Actually perform the change."),
) -> None:
    """Add a label to all messages matching --query."""
    ids, svc = _collect(query, limit)
    _preview(svc, ids)
    if not ids:
        return
    _confirm(yes, f"add label '{name}' to", len(ids))
    lid = _resolve_label(svc, name, create)
    client.batch_modify(svc, ids, add=[lid])
    typer.echo(f"added label '{name}' to {len(ids)} message(s)")


@label_app.command("remove")
def label_remove(
    name: str = typer.Argument(..., help="Label name to remove."),
    query: str = typer.Option(..., "--query", "-q", help="Gmail search query."),
    limit: int | None = typer.Option(None, help="Cap number of messages affected."),
    yes: bool = typer.Option(False, "--yes", help="Actually perform the change."),
) -> None:
    """Remove a label from all messages matching --query."""
    ids, svc = _collect(query, limit)
    _preview(svc, ids)
    if not ids:
        return
    _confirm(yes, f"remove label '{name}' from", len(ids))
    lid = client.label_id_by_name(svc, name)
    if not lid:
        raise typer.BadParameter(f"label '{name}' does not exist")
    client.batch_modify(svc, ids, remove=[lid])
    typer.echo(f"removed label '{name}' from {len(ids)} message(s)")


@label_app.command("move")
def label_move(
    src: str = typer.Argument(..., help="Source label to remove."),
    dst: str = typer.Argument(..., help="Destination label to add."),
    query: str | None = typer.Option(
        None, "--query", "-q", help="Extra filter; ANDed with label:<src>."
    ),
    create: bool = typer.Option(False, help="Create destination label if missing."),
    limit: int | None = typer.Option(None, help="Cap number of messages affected."),
    yes: bool = typer.Option(False, "--yes", help="Actually perform the change."),
) -> None:
    """Move messages: add dst label, remove src label, in one batchModify per chunk.

    Match scope defaults to `label:<src>`; --query is ANDed onto it.
    """
    scope = f"label:{src}" + (f" ({query})" if query else "")
    ids, svc = _collect(scope, limit)
    _preview(svc, ids)
    if not ids:
        return
    _confirm(yes, f"move from '{src}' to '{dst}' on", len(ids))
    src_id = client.label_id_by_name(svc, src)
    if not src_id:
        raise typer.BadParameter(f"source label '{src}' does not exist")
    dst_id = _resolve_label(svc, dst, create)
    client.batch_modify(svc, ids, add=[dst_id], remove=[src_id])
    typer.echo(f"moved {len(ids)} message(s) from '{src}' to '{dst}'")


@app.command()
def archive(
    query: str = typer.Option(..., "--query", "-q", help="Gmail search query."),
    limit: int | None = typer.Option(None, help="Cap number of messages affected."),
    yes: bool = typer.Option(False, "--yes", help="Actually perform the change."),
) -> None:
    """Archive (remove INBOX label from) all messages matching --query."""
    ids, svc = _collect(query, limit)
    _preview(svc, ids)
    if not ids:
        return
    _confirm(yes, "archive", len(ids))
    client.batch_modify(svc, ids, remove=["INBOX"])
    typer.echo(f"archived {len(ids)} message(s)")


@app.command()
def trash(
    query: str = typer.Option(..., "--query", "-q", help="Gmail search query."),
    limit: int | None = typer.Option(None, help="Cap number of messages affected."),
    yes: bool = typer.Option(False, "--yes", help="Move to Trash."),
) -> None:
    """Move all messages matching --query to Trash (reversible for 30 days)."""
    ids, svc = _collect(query, limit)
    _preview(svc, ids)
    if not ids:
        return
    _confirm(yes, "trash", len(ids))
    client.trash_messages(svc, ids)
    typer.echo(f"trashed {len(ids)} message(s)")


if __name__ == "__main__":
    app()
