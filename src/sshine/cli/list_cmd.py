from __future__ import annotations

from typing import Annotated, Optional

import anyio
import typer
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from sshine.cli.utils import error_exit, get_config, get_db, require_init
from sshine.core.db import Server
from sshine.exceptions import SshineError

console = Console()


def list_cmd(
    group: Annotated[str | None, typer.Option("-g", "--group", help="Filter by group")] = None,
    tag: Annotated[str | None, typer.Option("-t", "--tag", help="Filter by tag")] = None,
    wide: Annotated[bool, typer.Option("-w", "--wide", help="Show extra columns")] = False,
) -> None:
    """List servers."""
    cfg = get_config()
    try:
        require_init(cfg)
    except SshineError as exc:
        error_exit(str(exc))

    db = get_db(cfg)
    servers = anyio.run(db.list_servers, group, tag)

    if not servers:
        console.print("[dim]No servers found.[/dim]")
        return

    table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Host")
    table.add_column("Port", justify="right")
    table.add_column("User")
    table.add_column("Group")
    table.add_column("Tags")
    if wide:
        table.add_column("Auth")
        table.add_column("Key")

    for srv in servers:
        auth_info = ""
        if srv.auth_ref:
            auth_info = "[green]password[/green]"
        elif srv.key_path:
            auth_info = "[blue]key[/blue]"

        row = [
            srv.name,
            srv.host,
            str(srv.port),
            srv.user,
            srv.group_name or "[dim]—[/dim]",
            ", ".join(srv.tags) or "[dim]—[/dim]",
        ]
        if wide:
            row.append(auth_info)
            row.append(f"[dim]{srv.key_path or '—'}[/dim]")

        table.add_row(*row)

    console.print(table)


def tree_cmd(
    group: Annotated[str | None, typer.Option("-g", "--group", help="Filter by group")] = None,
    tag: Annotated[str | None, typer.Option("-t", "--tag", help="Filter by tag")] = None,
) -> None:
    """Show servers as a tree (grouped)."""
    cfg = get_config()
    try:
        require_init(cfg)
    except SshineError as exc:
        error_exit(str(exc))

    db = get_db(cfg)
    servers = anyio.run(db.list_servers, group, tag)

    if not servers:
        console.print("[dim]No servers found.[/dim]")
        return

    # Group servers
    grouped: dict[str | None, list[Server]] = {}
    for srv in servers:
        grouped.setdefault(srv.group_name, []).append(srv)

    root = Tree("[bold]sshine[/bold]", guide_style="dim")

    # Named groups first, ungrouped last
    for grp_name in sorted(k for k in grouped if k is not None):
        branch = root.add(f"[bold cyan]󰉋 {grp_name}[/bold cyan]")
        for srv in grouped[grp_name]:
            _add_server_leaf(branch, srv)

    if None in grouped:
        ungrouped = root.add("[dim](ungrouped)[/dim]")
        for srv in grouped[None]:
            _add_server_leaf(ungrouped, srv)

    console.print(root)


def _add_server_leaf(branch, srv: Server) -> None:
    auth = ""
    if srv.auth_ref:
        auth = "  [green]🔑 pw[/green]"
    elif srv.key_path:
        auth = "  [blue]🗝 key[/blue]"

    tags_str = ""
    if srv.tags:
        tags_str = f"  [dim]#{' #'.join(srv.tags)}[/dim]"

    label = f"[bold]{srv.name}[/bold]  [dim]{srv.user}@{srv.host}:{srv.port}[/dim]{auth}{tags_str}"
    branch.add(label)
