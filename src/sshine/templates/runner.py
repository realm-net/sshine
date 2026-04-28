from __future__ import annotations

import asyncio
import shlex
from dataclasses import dataclass, field
from typing import Any

import asyncssh
from rich.console import Console

from sshine.core.db import Server, Template
from sshine.core.storage import KeychainBackend, KeyringBackend
from sshine.templates.schema import TemplateDefinition, TemplateStep, evaluate_condition, render_vars


@dataclass
class ActionResult:
    step_name: str
    action: str
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    skipped: bool = False


@dataclass
class RunResult:
    steps_total: int
    steps_ok: int
    steps_failed: int
    steps_skipped: int
    results: list[ActionResult] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.steps_failed == 0


class TemplateRunner:
    def __init__(
        self,
        conn: asyncssh.SSHClientConnection,
        template: TemplateDefinition,
        var_overrides: dict[str, str],
        server: Server,
        storage: KeychainBackend | KeyringBackend,
        console: Console,
    ) -> None:
        self._conn = conn
        self._template = template
        self._server = server
        self._storage = storage
        self._console = console

        # Build context: defaults → template vars → overrides → built-ins
        self._ctx: dict[str, str] = {
            **template.vars,
            **var_overrides,
            "server_name": server.name,
            "server_host": server.host,
            "server_user": server.user,
            "server_port": str(server.port),
        }

    async def run(self) -> RunResult:
        steps_ok = 0
        steps_failed = 0
        steps_skipped = 0
        results: list[ActionResult] = []

        for i, step in enumerate(self._template.steps, start=1):
            label = step.name or f"Step {i}: {step.action}"
            self._console.rule(f"[bold cyan]{label}[/bold cyan]")

            # Evaluate condition
            if step.condition:
                cond_rendered = render_vars(step.condition, self._ctx, use_jinja2=True)
                if not evaluate_condition(cond_rendered, self._ctx):
                    self._console.print(f"  [dim]Skipped (condition: {step.condition})[/dim]")
                    steps_skipped += 1
                    results.append(ActionResult(step_name=label, action=step.action, success=True, skipped=True))
                    continue

            result = await self._dispatch(step, label)
            results.append(result)

            if result.success:
                self._console.print(f"  [green]✓[/green] {label}")
                steps_ok += 1
            else:
                self._console.print(f"  [red]✗[/red] {label} (exit {result.exit_code})")
                if result.stderr:
                    self._console.print(f"  [red]{result.stderr.strip()}[/red]")
                steps_failed += 1
                break  # stop on first failure

        return RunResult(
            steps_total=len(self._template.steps),
            steps_ok=steps_ok,
            steps_failed=steps_failed,
            steps_skipped=steps_skipped,
            results=results,
        )

    async def _dispatch(self, step: TemplateStep, label: str) -> ActionResult:
        handlers = {
            "shell": self._action_shell,
            "user.create": self._action_user_create,
            "ssh.keygen": self._action_ssh_keygen,
            "ssh.authorize": self._action_ssh_authorize,
            "package.install": self._action_package_install,
            "docker.install": self._action_docker_install,
        }
        handler = handlers.get(step.action)
        if handler is None:
            return ActionResult(
                step_name=label,
                action=step.action,
                success=False,
                stderr=f"Unknown action: {step.action!r}",
            )
        try:
            return await handler(step, label)
        except Exception as exc:
            return ActionResult(step_name=label, action=step.action, success=False, stderr=str(exc))

    def _r(self, value: Any) -> str:
        if isinstance(value, str):
            return render_vars(value, self._ctx, use_jinja2=True)
        return str(value)

    async def _run_cmd(self, cmd: str, label: str, sudo: bool = False) -> ActionResult:
        if sudo:
            cmd = f"sudo -- sh -c {shlex.quote(cmd)}"
        result = await self._conn.run(cmd, check=False)
        return ActionResult(
            step_name=label,
            action="shell",
            success=result.exit_status == 0,
            stdout=str(result.stdout or ""),
            stderr=str(result.stderr or ""),
            exit_code=result.exit_status or 0,
        )

    async def _action_shell(self, step: TemplateStep, label: str) -> ActionResult:
        cmd = self._r(step.params.get("run", ""))
        sudo = bool(step.params.get("sudo", False))
        return await self._run_cmd(cmd, label, sudo=sudo)

    async def _action_user_create(self, step: TemplateStep, label: str) -> ActionResult:
        username = self._r(step.params.get("username", ""))
        shell = self._r(step.params.get("shell", "/bin/bash"))
        sudo = bool(step.params.get("sudo", True))

        cmd = f"id -u {shlex.quote(username)} &>/dev/null || useradd -m -s {shlex.quote(shell)} {shlex.quote(username)}"
        return await self._run_cmd(cmd, label, sudo=sudo)

    async def _action_ssh_keygen(self, step: TemplateStep, label: str) -> ActionResult:
        from sshine.const import DEFAULT_SSH_METHOD
        from sshine.ssh.keygen import generate_keypair

        method = self._r(step.params.get("method", DEFAULT_SSH_METHOD))
        name = self._r(step.params.get("name", f"sshine-{self._server.name}"))

        try:
            from sshine.core.config import Config

            cfg = Config.load()
            priv, pub = generate_keypair(method=method, name=name, keys_dir=cfg.keys_dir)
            pub_content = pub.read_text(encoding="utf-8").strip()

            # Upload public key to server
            user = self._r(step.params.get("user", self._server.user))
            upload_cmd = (
                f"mkdir -p ~{shlex.quote(user)}/.ssh && "
                f"echo {shlex.quote(pub_content)} >> ~{shlex.quote(user)}/.ssh/authorized_keys && "
                f"chown -R {shlex.quote(user)}:{shlex.quote(user)} ~{shlex.quote(user)}/.ssh && "
                f"chmod 700 ~{shlex.quote(user)}/.ssh && "
                f"chmod 600 ~{shlex.quote(user)}/.ssh/authorized_keys"
            )
            result = await self._run_cmd(upload_cmd, label, sudo=True)
            if result.success:
                self._console.print(f"  [dim]Key stored: {priv}[/dim]")
            return result
        except Exception as exc:
            return ActionResult(step_name=label, action="ssh.keygen", success=False, stderr=str(exc))

    async def _action_ssh_authorize(self, step: TemplateStep, label: str) -> ActionResult:
        from sshine.core.config import Config
        from sshine.ssh.keygen import resolve_key

        key_name = self._r(step.params.get("key", ""))
        user = self._r(step.params.get("user", self._server.user))
        cfg = Config.load()

        try:
            key_path = resolve_key(key_name, cfg.keys_dir)
            pub_path = key_path.with_suffix(".pub")
            pub_content = pub_path.read_text(encoding="utf-8").strip()
        except Exception as exc:
            return ActionResult(step_name=label, action="ssh.authorize", success=False, stderr=str(exc))

        cmd = (
            f"mkdir -p ~{shlex.quote(user)}/.ssh && "
            f"echo {shlex.quote(pub_content)} >> ~{shlex.quote(user)}/.ssh/authorized_keys && "
            f"chmod 600 ~{shlex.quote(user)}/.ssh/authorized_keys"
        )
        return await self._run_cmd(cmd, label, sudo=True)

    async def _action_package_install(self, step: TemplateStep, label: str) -> ActionResult:
        packages = [self._r(p) for p in (step.params.get("packages") or [])]
        if not packages:
            return ActionResult(step_name=label, action="package.install", success=True)

        manager = self._r(step.params.get("manager", ""))
        if not manager:
            # Auto-detect
            manager = await self._detect_package_manager()

        pkg_str = " ".join(shlex.quote(p) for p in packages)

        if manager in ("apt", "apt-get"):
            cmd = f"DEBIAN_FRONTEND=noninteractive apt-get install -y {pkg_str}"
        elif manager in ("yum", "dnf"):
            cmd = f"{manager} install -y {pkg_str}"
        elif manager == "brew":
            cmd = f"brew install {pkg_str}"
        else:
            return ActionResult(step_name=label, action="package.install", success=False, stderr=f"Unknown package manager: {manager}")

        return await self._run_cmd(cmd, label, sudo=manager != "brew")

    async def _action_docker_install(self, step: TemplateStep, label: str) -> ActionResult:
        compose = bool(step.params.get("compose", True))
        cmd = "curl -fsSL https://get.docker.com -o /tmp/get-docker.sh && sh /tmp/get-docker.sh"
        result = await self._run_cmd(cmd, label, sudo=True)
        if result.success and compose:
            compose_cmd = (
                "docker compose version >/dev/null 2>&1 || "
                "apt-get install -y docker-compose-plugin 2>/dev/null || "
                "yum install -y docker-compose-plugin 2>/dev/null || true"
            )
            result2 = await self._run_cmd(compose_cmd, label + " (compose)", sudo=True)
            if not result2.success:
                self._console.print("  [yellow]![/yellow] docker-compose-plugin install failed (non-fatal)")
        return result

    async def _detect_package_manager(self) -> str:
        for mgr, check in [("apt-get", "which apt-get"), ("dnf", "which dnf"), ("yum", "which yum")]:
            r = await self._conn.run(check, check=False)
            if r.exit_status == 0:
                return mgr
        return "apt-get"


async def run_template(
    server: Server,
    template_obj,  # Template DB model
    var_overrides: dict[str, str],
    storage,
    console: Console,
    passphrase: str | None = None,
) -> RunResult:
    """Helper called from server_cmd and template_cmd."""
    from sshine.templates.schema import load_template

    tmpl_def = load_template(body=template_obj.body)
    tmpl_def.name = template_obj.name

    connect_kwargs: dict[str, Any] = {
        "host": server.host,
        "port": server.port,
        "username": server.user,
        "known_hosts": None,
    }
    secret: str | None = None
    if server.auth_ref:
        secret = storage.get(server.auth_ref)
    if server.key_path:
        connect_kwargs["client_keys"] = [server.key_path]
        if secret:
            connect_kwargs["passphrase"] = secret
    elif secret:
        connect_kwargs["password"] = secret

    async with asyncssh.connect(**connect_kwargs) as conn:
        runner = TemplateRunner(conn, tmpl_def, var_overrides, server, storage, console)
        return await runner.run()
