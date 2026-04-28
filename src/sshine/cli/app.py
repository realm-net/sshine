from __future__ import annotations

from importlib.metadata import version as _pkg_version
from typing import Annotated

import typer
from rich.console import Console

from sshine.cli.backup_cmd import backup_cmd, restore_cmd
from sshine.cli.connect_cmd import connect_cmd
from sshine.cli.init_cmd import init_cmd
from sshine.cli.list_cmd import list_cmd, tree_cmd
from sshine.cli.server_cmd import add_cmd, rm_cmd
from sshine.cli.storage_cmd import storage_app
from sshine.cli.template_cmd import template_app

console = Console()

app = typer.Typer(
    name="sshine",
    help=(
        "[bold]sshine[/bold] — open-source SSH server management utility.\n\n"
        "  [dim]sshine init[/dim]                   Initialise\n"
        "  [dim]sshine add <name> -h <host>[/dim]   Add server\n"
        "  [dim]sshine <name>[/dim]                 Connect\n"
        "  [dim]sshine list[/dim]                   List servers\n"
        "  [dim]sshine tree[/dim]                   Server tree\n"
    ),
    rich_markup_mode="rich",
    no_args_is_help=False,
    add_completion=True,
)

# Sub-apps
app.add_typer(storage_app, name="storage")
app.add_typer(template_app, name="template")

# Named commands
app.command("init", help="Initialise sshine.")(init_cmd)
app.command("add", help="Add a new server.")(add_cmd)
app.command("rm", help="Remove a server.")(rm_cmd)
app.command("list", help="List servers.")(list_cmd)
app.command("tree", help="Show server tree.")(tree_cmd)
app.command("connect", help="Connect to a server.")(connect_cmd)
app.command("backup", help="Export encrypted backup.")(backup_cmd)
app.command("restore", help="Restore from backup.")(restore_cmd)


@app.callback(invoke_without_command=True)
def _main(
    ctx: typer.Context,
    version: Annotated[bool, typer.Option("--version", "-v", help="Show version and exit.", is_eager=True)] = False,
) -> None:
    if version:
        typer.echo(_pkg_version("sshine"))
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
