from __future__ import annotations

import sys

from sshine.cli.app import app as _app

_KNOWN_COMMANDS = {
    "init",
    "add",
    "rm",
    "list",
    "tree",
    "connect",
    "backup",
    "restore",
    "storage",
    "template",
    "--help",
    "-h",
    "--version",
    "--install-completion",
    "--show-completion",
}

_CONNECT_FLAGS = {"--verbose", "-v"}


def app() -> None:
    """Entry point: rewrite `sshine <name>` → `sshine connect <name>`."""
    args = sys.argv[1:]
    # Filter out flags to find the positional argument
    positional = [a for a in args if not a.startswith("-")]
    if positional and positional[0] not in _KNOWN_COMMANDS:
        # Rewrite: sshine <name> [flags] → sshine connect <name> [flags]
        sys.argv = [sys.argv[0], "connect"] + args
    _app()


if __name__ == "__main__":
    app()
