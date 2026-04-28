from __future__ import annotations

from typing import Annotated, Optional

import anyio
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from sshine.cli.utils import error_exit, get_config, get_db, require_init
from sshine.const import STORAGE_OPTIONS
from sshine.core.storage import KeychainBackend, KeyringBackend, get_active_backend, migrate
from sshine.exceptions import SshineError

console = Console()

storage_app = typer.Typer(
    name="storage",
    help="Manage storage backends.",
    no_args_is_help=False,
)


@storage_app.callback(invoke_without_command=True)
def storage_default(
    ctx: typer.Context,
    name: Annotated[str | None, typer.Argument(help="Backend name to inspect")] = None,
) -> None:
    """Show storage info. Pass a name to inspect a specific backend."""
    if ctx.invoked_subcommand is not None:
        return
    cfg = get_config()
    _show_storage_info(cfg, name or cfg.storage_backend)


@storage_app.command("use")
def storage_use(
    backend: Annotated[str, typer.Argument(help=f"Backend: {' | '.join(STORAGE_OPTIONS)}")],
) -> None:
    """Switch to a different storage backend."""
    if backend not in STORAGE_OPTIONS:
        error_exit(f"Unknown backend: {backend!r}. Valid: {', '.join(STORAGE_OPTIONS)}")

    cfg = get_config()
    if cfg.storage_backend == backend:
        console.print(f"  [yellow]Already using [bold]{backend}[/bold].[/yellow]")
        raise typer.Exit(0)

    if Confirm.ask(f"Migrate existing secrets to [bold]{backend}[/bold]?", default=True):
        old_storage = get_active_backend(cfg)
        cfg.storage_backend = backend
        cfg.save()
        new_storage = get_active_backend(cfg)

        db = get_db(cfg)
        known_keys = anyio.run(db.list_auth_refs)

        result = migrate(old_storage, new_storage, known_keys=known_keys)
        console.print(f"  [green]✓[/green] Migrated {result.migrated} secret(s)")
        if result.errors:
            for err in result.errors:
                console.print(f"  [yellow]![/yellow] {err}")
    else:
        cfg.storage_backend = backend
        cfg.save()

    console.print(f"  [green]✓[/green] Now using [bold]{backend}[/bold]")


@storage_app.command("purge")
def storage_purge(
    name: Annotated[str, typer.Argument(help="Backend to purge")],
    yes: Annotated[bool, typer.Option("-y", "--yes")] = False,
) -> None:
    """Delete all secrets from a storage backend."""
    if name not in STORAGE_OPTIONS:
        error_exit(f"Unknown backend: {name!r}")

    if not yes:
        console.print(f"  [red bold]WARNING:[/red bold] This will permanently delete ALL secrets in [bold]{name}[/bold].")
        if not Confirm.ask("Are you sure?", default=False):
            raise typer.Exit(0)

    cfg = get_config()
    # Temporarily override backend for purge
    orig = cfg.storage_backend
    cfg.storage_backend = name
    storage = get_active_backend(cfg)
    cfg.storage_backend = orig

    if isinstance(storage, KeyringBackend):
        # Enumerate from DB
        db = get_db(cfg)
        auth_refs = anyio.run(db.list_auth_refs)
        count = 0
        for ref in auth_refs:
            try:
                storage.delete(ref)
                count += 1
            except Exception:
                pass
        console.print(f"  [green]✓[/green] Purged {count} secret(s) from keyring")
    else:
        count = storage.purge()
        console.print(f"  [green]✓[/green] Purged {count} secret(s) from {name}")


@storage_app.command("migrate")
def storage_migrate(
    src: Annotated[str, typer.Argument(help="Source backend")],
    dst: Annotated[str, typer.Argument(help="Destination backend")],
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    """Migrate secrets between storage backends."""
    for name in (src, dst):
        if name not in STORAGE_OPTIONS:
            error_exit(f"Unknown backend: {name!r}")

    cfg = get_config()

    cfg.storage_backend = src
    src_storage = get_active_backend(cfg)
    cfg.storage_backend = dst
    dst_storage = get_active_backend(cfg)

    # Restore for listing auth_refs
    db = get_db(cfg)
    known_keys = anyio.run(db.list_auth_refs)

    result = migrate(src_storage, dst_storage, known_keys=known_keys, dry_run=dry_run)

    table = Table(show_header=False, box=None)
    table.add_row("Source", src)
    table.add_row("Destination", dst)
    table.add_row("Migrated", f"[green]{result.migrated}[/green]")
    table.add_row("Errors", f"[red]{len(result.errors)}[/red]" if result.errors else "[green]0[/green]")
    if dry_run:
        table.add_row("Mode", "[yellow]dry-run[/yellow]")

    console.print(Panel(table, title="Migration result"))

    for err in result.errors:
        console.print(f"  [red]✗[/red] {err}")


def _show_storage_info(cfg, name: str) -> None:
    from sshine.const import STORAGE_KEYCHAIN, STORAGE_KEYRING

    is_current = name == cfg.storage_backend

    orig = cfg.storage_backend
    cfg.storage_backend = name
    storage = get_active_backend(cfg)
    cfg.storage_backend = orig

    available = storage.is_available()
    count = storage.count()

    table = Table(show_header=False, box=None)
    table.add_row("Backend", f"[bold]{name}[/bold]")
    table.add_row("Status", "[green]available[/green]" if available else "[red]unavailable[/red]")
    table.add_row("Active", "[green]yes[/green]" if is_current else "[dim]no[/dim]")
    if count >= 0:
        table.add_row("Secrets", str(count))

    console.print(Panel(table, title=f"Storage: {name}"))
