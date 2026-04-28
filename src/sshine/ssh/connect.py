from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from sshine.core.db import Server
from sshine.exceptions import SshineConnectionError


def connect(
    server: Server,
    secret: str | None = None,
    verbose: bool = False,
) -> None:
    """
    Hand off to the system ssh binary.

    If *server* uses a password (no key_path), we write a temporary
    SSHPASS-style helper or use sshpass if available.  If *server* uses
    a key, we pass -i directly to ssh.

    sshine's job here is only credential resolution — the actual terminal
    session is fully native OpenSSH.
    """
    ssh = shutil.which("ssh")
    if ssh is None:
        raise SshineConnectionError(
            "ssh binary not found. Install OpenSSH (it ships with Windows 10+, macOS, and every Linux distro).",
        )

    args = [ssh]

    if verbose:
        args += ["-v"]

    args += ["-p", str(server.port)]

    if server.key_path:
        args += ["-i", server.key_path]
        if secret:
            # key with passphrase — SSH_ASKPASS trick or just let ssh ask
            # for now we let ssh prompt (passphrase isn't stored in a way we can pass it non-interactively without sshpass)
            pass

    args.append(f"{server.user}@{server.host}")

    if verbose:
        print(f"[sshine:debug] exec: {' '.join(args)}", file=sys.stderr)

    if secret and not server.key_path:
        # Password auth — use sshpass if available, otherwise SSH_ASKPASS
        _connect_with_password(args, secret, verbose)
    else:
        # Key auth or no secret — just exec ssh directly, replacing the process
        _exec(args)


def _connect_with_password(args: list[str], password: str, verbose: bool) -> None:
    """Run ssh with password injection via sshpass or SSH_ASKPASS helper."""
    sshpass = shutil.which("sshpass")

    if sshpass:
        if verbose:
            print("[sshine:debug] using sshpass", file=sys.stderr)
        _exec([sshpass, "-p", password] + args)
        return

    # No sshpass — write a tiny askpass helper script and use SSH_ASKPASS
    # This works on Unix; on Windows it's more involved.
    if sys.platform == "win32":
        raise SshineConnectionError(
            "Password auth on Windows requires sshpass (not available) or key-based auth.\n"
            "Install sshpass via WSL or switch to key auth: sshine add <name> --key <path>",
        )

    script = f"#!/bin/sh\necho {_sh_escape(password)}\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".sh",
        delete=False,
        prefix="sshine_askpass_",
    ) as f:
        f.write(script)
        askpass_path = f.name

    try:
        askpass = Path(askpass_path)
        askpass.chmod(0o700)
        env = os.environ.copy()
        env["SSH_ASKPASS"] = askpass_path
        env["SSH_ASKPASS_REQUIRE"] = "force"  # OpenSSH 8.4+
        env.pop("DISPLAY", None)

        if verbose:
            print(f"[sshine:debug] using SSH_ASKPASS helper: {askpass_path}", file=sys.stderr)

        ret = subprocess.call(args, env=env)
        sys.exit(ret)
    finally:
        Path(askpass_path).unlink(missing_ok=True)


def _exec(args: list[str]) -> None:
    """Replace the current process with ssh (Unix) or spawn+wait (Windows)."""
    if sys.platform == "win32":
        # os.execvp on Windows doesn't truly replace the process — use subprocess
        ret = subprocess.call(args)
        sys.exit(ret)
    else:
        os.execvp(args[0], args)


def _sh_escape(s: str) -> str:
    """Single-quote escape for shell script."""
    return "'" + s.replace("'", "'\\''") + "'"
