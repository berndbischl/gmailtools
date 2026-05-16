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
