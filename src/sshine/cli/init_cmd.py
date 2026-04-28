from __future__ import annotations

import anyio
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from sshine.const import STORAGE_KEYCHAIN, STORAGE_KEYRING
from sshine.core.config import Config
from sshine.core.db import Database
from sshine.core.storage import KeyringBackend, get_active_backend
from sshine.exceptions import NotInitialisedError, SshineError

console = Console()
err_console = Console(stderr=True)


def init_cmd() -> None:
    """Initialise sshine: config, database, and storage backend."""
    cfg = Config.load()

    if cfg.is_initialised:
        console.print(
            Panel(
                "[yellow]sshine is already initialised.[/yellow]\nRe-initialising will [bold]not[/bold] overwrite existing data.",
                title="Already initialised",
                border_style="yellow",
            ),
        )
        if not Confirm.ask("Continue anyway?", default=False):
            raise typer.Exit(0)

    keyring_available = KeyringBackend().is_available()

    if keyring_available:
        console.print("  [green]✓[/green] OS keyring detected")
        chosen_backend = STORAGE_KEYRING
    else:
        console.print(
            "  [yellow]![/yellow] No OS keyring detected (common in Docker / headless environments).",
        )
        use_keychain = Confirm.ask(
            "Use [bold]sshine-keychain[/bold] (local encrypted fallback) instead?",
            default=True,
        )
        chosen_backend = STORAGE_KEYCHAIN if use_keychain else STORAGE_KEYRING

    cfg.storage_backend = chosen_backend
    cfg.save()
    console.print(f"  [green]✓[/green] Storage backend: [bold]{chosen_backend}[/bold]")

    db = Database(cfg.db_path)
    anyio.run(db.initialise)
    console.print(f"  [green]✓[/green] Database: [dim]{cfg.db_path}[/dim]")

    storage = get_active_backend(cfg)
    _test_key = "sshine.init.verify"
    _test_val = "ok"
    try:
        storage.set(_test_key, _test_val)
        verified = storage.get(_test_key)
        storage.delete(_test_key)
        if verified != _test_val:
            raise RuntimeError("Round-trip value mismatch")
        console.print("  [green]✓[/green] Storage round-trip verified")
    except Exception as exc:
        err_console.print(
            Panel(
                f"[red]Storage verification failed:[/red] {exc}\n\n"
                "Consider switching to [bold]sshine-keychain[/bold]:\n"
                "  [dim]sshine storage use sshine-keychain[/dim]",
                title="[red]Storage Error[/red]",
                border_style="red",
            ),
        )
        raise typer.Exit(1) from exc

    console.print()
    console.print(
        Panel(
            "[bold green]sshine initialised successfully![/bold green]\n\n"
            f"  Config:   [dim]{cfg.config_path}[/dim]\n"
            f"  Database: [dim]{cfg.db_path}[/dim]\n"
            f"  Keys:     [dim]{cfg.keys_dir}[/dim]\n"
            f"  Storage:  [bold]{chosen_backend}[/bold]",
            title="[bold]✓ Ready[/bold]",
            border_style="green",
        ),
    )

    console.print()
    if Confirm.ask("Would you like to add your first server?", default=False):
        from sshine.cli.server_cmd import add_cmd_interactive

        add_cmd_interactive(cfg, db, storage)
