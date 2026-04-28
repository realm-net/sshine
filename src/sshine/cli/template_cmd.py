from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import anyio
import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from sshine.cli.utils import error_exit, get_config, get_db, require_init
from sshine.core.storage import get_active_backend
from sshine.exceptions import SshineError

console = Console()

template_app = typer.Typer(
    name="template",
    help="Manage init templates.",
    no_args_is_help=True,
)


@template_app.command("create")
def template_create(
    name: Annotated[str, typer.Argument(help="Template name")],
    file: Annotated[Path, typer.Option("-i", "--input", help="Path to .inittmp YAML file")],
    group: Annotated[str | None, typer.Option("-g", "--group", help="Group name")] = None,
) -> None:
    """Register a new template from a .inittmp file."""
    cfg = get_config()
    try:
        require_init(cfg)
    except SshineError as exc:
        error_exit(str(exc))

    if not file.exists():
        error_exit(f"File not found: {file}")

    from sshine.templates.schema import load_template

    try:
        tmpl_def = load_template(path=file)
    except SshineError as exc:
        error_exit(str(exc))

    db = get_db(cfg)

    group_id: int | None = None
    if group:
        grp = anyio.run(db.get_group, group) or anyio.run(db.create_group, group)
        group_id = grp.id

    anyio.run(db.save_template, name, file.read_text(encoding="utf-8"), group_id, str(file))

    step_count = len(tmpl_def.steps)
    console.print(
        Panel(
            f"  Name:  [bold]{name}[/bold]\n  Steps: {step_count}\n  File:  [dim]{file}[/dim]",
            title="[bold green]✓ Template saved[/bold green]",
            border_style="green",
        )
    )


@template_app.command("list")
def template_list() -> None:
    """List all templates."""
    cfg = get_config()
    try:
        require_init(cfg)
    except SshineError as exc:
        error_exit(str(exc))

    db = get_db(cfg)
    templates = anyio.run(db.list_templates)

    if not templates:
        console.print("[dim]No templates found.[/dim]")
        return

    table = Table(show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Group")
    table.add_column("Created")

    for t in templates:
        table.add_row(
            t.name,
            t.group_name or "[dim]—[/dim]",
            t.created_at[:10] if t.created_at else "—",
        )

    console.print(table)


@template_app.command("show")
def template_show(
    name: Annotated[str, typer.Argument(help="Template name")],
) -> None:
    """Show a template's YAML body."""
    cfg = get_config()
    try:
        require_init(cfg)
    except SshineError as exc:
        error_exit(str(exc))

    db = get_db(cfg)
    tmpl = anyio.run(db.get_template, name)

    if tmpl is None:
        error_exit(f"Template not found: {name!r}")

    console.print(Syntax(tmpl.body, "yaml", theme="monokai", line_numbers=True))


@template_app.command("run")
def template_run(
    name: Annotated[str, typer.Argument(help="Template name")],
    server: Annotated[str, typer.Option("--server", help="Target server name")],
    var: Annotated[list[str] | None, typer.Option("--var", help="Variable override: key=value")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show steps without executing")] = False,
) -> None:
    """Run a template on a server."""
    cfg = get_config()
    try:
        require_init(cfg)
    except SshineError as exc:
        error_exit(str(exc))

    db = get_db(cfg)
    storage = get_active_backend(cfg)

    tmpl = anyio.run(db.get_template, name)
    if tmpl is None:
        error_exit(f"Template not found: {name!r}")

    srv = anyio.run(db.get_server, server)
    if srv is None:
        error_exit(f"Server not found: {server!r}")

    # Parse --var key=value pairs
    overrides: dict[str, str] = {}
    for v in var or []:
        if "=" in v:
            k, _, val = v.partition("=")
            overrides[k.strip()] = val.strip()

    if dry_run:
        from sshine.templates.schema import load_template

        tmpl_def = load_template(body=tmpl.body)
        console.print(
            Panel(
                f"[bold]Template:[/bold] {name}\n"
                f"[bold]Server:[/bold]   {server}\n"
                f"[bold]Steps:[/bold]    {len(tmpl_def.steps)}\n\n"
                + "\n".join(f"  {i}. [{s.action}] {s.name or ''}" for i, s in enumerate(tmpl_def.steps, 1)),
                title="[yellow]Dry run[/yellow]",
                border_style="yellow",
            )
        )
        return

    from sshine.templates.runner import run_template

    try:
        result = anyio.run(run_template, srv, tmpl, overrides, storage, console)
    except SshineError as exc:
        error_exit(str(exc))
    except Exception as exc:
        error_exit(f"Template run failed: {exc}")

    status_color = "green" if result.success else "red"
    console.print(
        Panel(
            f"  Total:   {result.steps_total}\n"
            f"  [green]OK:[/green]      {result.steps_ok}\n"
            f"  [red]Failed:[/red]  {result.steps_failed}\n"
            f"  [dim]Skipped:[/dim] {result.steps_skipped}",
            title=f"[bold {status_color}]{'✓ Done' if result.success else '✗ Failed'}[/bold {status_color}]",
            border_style=status_color,
        )
    )

    if not result.success:
        raise typer.Exit(1)


@template_app.command("delete")
def template_delete(
    name: Annotated[str, typer.Argument(help="Template name")],
    yes: Annotated[bool, typer.Option("-y", "--yes")] = False,
) -> None:
    """Delete a template."""
    cfg = get_config()
    db = get_db(cfg)

    from rich.prompt import Confirm

    if not yes and not Confirm.ask(f"Delete template [bold red]{name}[/bold red]?", default=False):
        raise typer.Exit(0)

    deleted = anyio.run(db.delete_template, name)
    if deleted:
        console.print(f"  [green]✓[/green] Deleted template [bold]{name}[/bold]")
    else:
        error_exit(f"Template not found: {name!r}")
