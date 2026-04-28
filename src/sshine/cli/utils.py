from __future__ import annotations

from typing import NoReturn

from sshine.core.config import Config
from sshine.core.db import Database
from sshine.exceptions import NotInitialisedError


def get_config() -> Config:
    return Config.load()


def require_init(cfg: Config) -> None:
    if not cfg.is_initialised:
        raise NotInitialisedError


def get_db(cfg: Config) -> Database:
    return Database(cfg.db_path)


def error_exit(message: str, code: int = 1) -> NoReturn:
    import typer
    from rich.console import Console
    from rich.panel import Panel

    Console(stderr=True).print(Panel(f"[red]{message}[/red]", title="[bold red]Error[/bold red]", border_style="red"))
    raise typer.Exit(code)
