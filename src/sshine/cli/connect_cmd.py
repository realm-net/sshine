from __future__ import annotations

from typing import Annotated

import anyio
import typer
from rich.console import Console

from sshine.cli.utils import error_exit, get_config, get_db, require_init
from sshine.core.storage import get_active_backend
from sshine.exceptions import SshineConnectionError, SshineError

console = Console()


def connect_cmd(
    server_name: Annotated[str, typer.Argument(help="Server name to connect to")],
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show debug output")] = False,
) -> None:
    """Connect to a server by name."""
    cfg = get_config()
    try:
        require_init(cfg)
    except SshineError as exc:
        error_exit(str(exc))

    db = get_db(cfg)
    storage = get_active_backend(cfg)

    server = anyio.run(db.get_server, server_name)
    if server is None:
        error_exit(f"Server not found: {server_name!r}")

    secret: str | None = None
    if server.auth_ref:
        secret = storage.get(server.auth_ref)
        if secret is None:
            error_exit(
                f"Secret not found for auth_ref [bold]{server.auth_ref}[/bold]. Re-add the server or update credentials.",
            )

    console.print(
        f"  Connecting to [bold]{server.user}@{server.host}:{server.port}[/bold]…",
        highlight=False,
    )

    from sshine.ssh.connect import connect

    try:
        connect(server, secret, verbose=verbose)
    except SshineConnectionError as exc:
        error_exit(str(exc))
