from __future__ import annotations

from typing import Annotated, Optional

import anyio
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.tree import Tree

from sshine.cli.utils import error_exit, get_config, get_db, require_init
from sshine.const import DEFAULT_SSH_METHOD, DEFAULT_SSH_PORT, DEFAULT_SSH_USER
from sshine.core.db import Database
from sshine.core.storage import get_active_backend
from sshine.exceptions import SshineError

console = Console()
err_console = Console(stderr=True)


def add_cmd(
    name: Annotated[str, typer.Argument(help="Server name / alias")],
    host: Annotated[str, typer.Option("-h", "--host", help="Hostname or IP address")],
    port: Annotated[int, typer.Option("-P", "--port", help="SSH port")] = DEFAULT_SSH_PORT,
    user: Annotated[str, typer.Option("-u", "--user", help="SSH user")] = DEFAULT_SSH_USER,
    ask_password: Annotated[bool, typer.Option("-p", "--password", help="Prompt for password")] = False,
    key: Annotated[str | None, typer.Option("--key", help="Existing key name or path")] = None,
    keygen: Annotated[str | None, typer.Option("--keygen", help="Generate key: 'm=ed25519 n=name'")] = None,
    template: Annotated[str | None, typer.Option("-t", "--template", help="Init template name")] = None,
    group: Annotated[str | None, typer.Option("-g", "--group", help="Group name")] = None,
    tag: Annotated[list[str] | None, typer.Option("--tag", help="Tag (repeatable)")] = None,
) -> None:
    """Add a new server."""
    cfg = get_config()
    try:
        require_init(cfg)
    except SshineError as exc:
        error_exit(str(exc))

    db = get_db(cfg)
    storage = get_active_backend(cfg)
    tags = list(tag) if tag else []

    try:
        anyio.run(_add_server, name, host, port, user, ask_password, key, keygen, template, group, tags, db, storage, cfg)
    except SshineError as exc:
        error_exit(str(exc))


async def _add_server(name, host, port, user, ask_password, key, keygen, template, group, tags, db, storage, cfg):
    from sshine.ssh.keygen import generate_keypair, resolve_key

    # Resolve group
    group_id: int | None = None
    if group:
        grp = await db.get_group(group) or await db.create_group(group)
        group_id = grp.id

    # Auth
    auth_ref: str | None = None
    key_path: str | None = None

    if keygen:
        params = _parse_keygen(keygen)
        method = params.get("m", DEFAULT_SSH_METHOD)
        kname = params.get("n", name)
        priv, pub = generate_keypair(method=method, name=kname, keys_dir=cfg.keys_dir)
        key_path = str(priv)
        console.print(f"  [green]✓[/green] Generated {method} key: [dim]{priv}[/dim]")
    elif key:
        resolved = resolve_key(key, cfg.keys_dir)
        key_path = str(resolved)
        console.print(f"  [green]✓[/green] Using key: [dim]{resolved}[/dim]")

    if ask_password:
        password = typer.prompt(f"Password for {user}@{host}", hide_input=True)
        auth_ref = f"server:{name}:password"
        storage.set(auth_ref, password)
        console.print(f"  [green]✓[/green] Password stored → [dim]{auth_ref}[/dim]")

    server = await db.create_server(
        name=name,
        host=host,
        port=port,
        user=user,
        group_id=group_id,
        auth_ref=auth_ref,
        key_path=key_path,
        tags=tags,
    )

    # Run template if requested
    if template:
        tmpl = await db.get_template(template)
        if tmpl is None:
            console.print(f"  [yellow]![/yellow] Template [bold]{template}[/bold] not found — skipping.")
        else:
            from sshine.templates.runner import run_template

            await run_template(server, tmpl, {}, storage, console)

    _print_server_card(server)


def _parse_keygen(s: str) -> dict[str, str]:
    """Parse 'm=ed25519 n=mykey' into {'m': 'ed25519', 'n': 'mykey'}."""
    result = {}
    for part in s.split():
        if "=" in part:
            k, _, v = part.partition("=")
            result[k.strip()] = v.strip()
    return result


def rm_cmd(
    name: Annotated[str, typer.Argument(help="Server name to remove")],
    yes: Annotated[bool, typer.Option("-y", "--yes", help="Skip confirmation")] = False,
) -> None:
    """Remove a server."""
    cfg = get_config()
    try:
        require_init(cfg)
    except SshineError as exc:
        error_exit(str(exc))

    db = get_db(cfg)
    storage = get_active_backend(cfg)

    try:
        server = anyio.run(db.get_server, name)
    except Exception as exc:
        error_exit(str(exc))

    if server is None:
        error_exit(f"Server not found: {name!r}")

    if not yes:
        console.print(f"  Host: [bold]{server.host}:{server.port}[/bold]  User: [bold]{server.user}[/bold]")
        if not Confirm.ask(f"Remove server [bold red]{name}[/bold red]?", default=False):
            raise typer.Exit(0)

    if server.auth_ref:
        try:
            storage.delete(server.auth_ref)
        except Exception:
            pass

    anyio.run(db.delete_server, name)
    console.print(f"  [green]✓[/green] Removed [bold]{name}[/bold]")


def _print_server_card(server) -> None:
    from rich.text import Text

    lines = [
        f"  Host:  [bold]{server.host}:{server.port}[/bold]",
        f"  User:  [bold]{server.user}[/bold]",
    ]
    if server.group_name:
        lines.append(f"  Group: {server.group_name}")
    if server.tags:
        lines.append(f"  Tags:  {', '.join(server.tags)}")
    if server.key_path:
        lines.append(f"  Key:   [dim]{server.key_path}[/dim]")

    console.print(
        Panel(
            "\n".join(lines),
            title=f"[bold green]✓ Added:[/bold green] [bold]{server.name}[/bold]",
            border_style="green",
        )
    )


def add_cmd_interactive(cfg, db, storage) -> None:
    """Interactive first-server wizard called from init."""
    console.print()
    name = Prompt.ask("  Server name")
    host = Prompt.ask("  Host (IP or hostname)")
    user = Prompt.ask("  User", default=DEFAULT_SSH_USER)
    use_key = Confirm.ask("  Generate SSH key?", default=True)

    keygen_str = None
    if use_key:
        method = Prompt.ask("  Key method", default=DEFAULT_SSH_METHOD)
        keygen_str = f"m={method} n={name}"

    ask_pw = not use_key

    try:
        anyio.run(_add_server, name, host, DEFAULT_SSH_PORT, user, ask_pw, None, keygen_str, None, None, [], db, storage, cfg)
    except SshineError as exc:
        error_exit(str(exc))
