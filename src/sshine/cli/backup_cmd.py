from __future__ import annotations

import datetime
import hashlib
import json
import os
import struct
from pathlib import Path
from typing import Annotated, Optional

import anyio
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from sshine.cli.utils import error_exit, get_config, get_db, require_init
from sshine.const import BACKUP_EXTENSION, BACKUP_MAGIC, BACKUP_VERSION, BACKUPS_DIR
from sshine.core.storage import get_active_backend
from sshine.crypto.aes import decrypt, encrypt
from sshine.exceptions import BackupCorruptError, BackupVersionError, SshineError

console = Console()


def backup_cmd(
    output: Annotated[Path | None, typer.Option("-o", "--output", help="Output file path")] = None,
    passphrase: Annotated[str | None, typer.Option("-p", "--passphrase", help="Encryption passphrase")] = None,
) -> None:
    """Export an encrypted backup of all sshine data."""
    cfg = get_config()
    try:
        require_init(cfg)
    except SshineError as exc:
        error_exit(str(exc))

    if passphrase is None:
        passphrase = typer.prompt("Backup passphrase", hide_input=True, confirmation_prompt=True)

    assert passphrase is not None
    pp: str = passphrase

    db = get_db(cfg)
    storage = get_active_backend(cfg)

    # Collect data
    servers = anyio.run(db.list_servers, None, None)
    groups = anyio.run(db.list_groups)
    tags = anyio.run(db.list_tags)
    templates = anyio.run(db.list_templates)
    auth_refs = anyio.run(db.list_auth_refs)

    secrets = []
    for ref in auth_refs:
        value = storage.get(ref)
        if value is not None:
            secrets.append({"key": ref, "value": value})

    payload = {
        "version": BACKUP_VERSION,
        "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "servers": [
            {
                "name": s.name,
                "host": s.host,
                "port": s.port,
                "user": s.user,
                "group": s.group_name,
                "auth_ref": s.auth_ref,
                "key_path": s.key_path,
                "tags": s.tags,
            }
            for s in servers
        ],
        "groups": [{"name": g.name, "description": g.description} for g in groups],
        "tags": tags,
        "secrets": secrets,
        "templates": [{"name": t.name, "body": t.body, "group": t.group_name} for t in templates],
    }

    plaintext = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    # Prepend magic + version
    header = BACKUP_MAGIC + struct.pack("<Q", BACKUP_VERSION)
    plaintext = header + plaintext

    # Derive key from passphrase (portable — NOT HWID-bound)
    salt = os.urandom(32)
    key = hashlib.scrypt(pp.encode("utf-8"), salt=salt, n=2**17, r=8, p=1, dklen=32)
    nonce, ciphertext = encrypt(plaintext, key)

    # File layout: [32 salt][12 nonce][ciphertext]
    blob = salt + nonce + ciphertext

    if output is None:
        ts = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d-%H%M%S")
        cfg.backups_dir.mkdir(parents=True, exist_ok=True)
        output = cfg.backups_dir / f"sshine-{ts}{BACKUP_EXTENSION}"

    output.write_bytes(blob)
    sha256 = hashlib.sha256(blob).hexdigest()

    console.print(
        Panel(
            f"  File:    [dim]{output}[/dim]\n"
            f"  Size:    {len(blob):,} bytes\n"
            f"  SHA256:  [dim]{sha256[:16]}…[/dim]\n"
            f"  Servers: {len(servers)}\n"
            f"  Secrets: {len(secrets)}",
            title="[bold green]✓ Backup created[/bold green]",
            border_style="green",
        )
    )


def restore_cmd(
    input_file: Annotated[Path | None, typer.Option("-i", "--input", help="Backup file (or 'latest')")] = None,
    passphrase: Annotated[str | None, typer.Option("-p", "--passphrase")] = None,
    no_delete: Annotated[bool, typer.Option("--no-delete", help="Keep backup file after restore")] = False,
    merge: Annotated[bool, typer.Option("--merge", help="Skip conflicting servers instead of overwriting")] = False,
) -> None:
    """Restore sshine data from a backup file."""
    cfg = get_config()

    # Find latest backup if not specified
    if input_file is None or str(input_file) == "latest":
        candidates = sorted(cfg.backups_dir.glob(f"*{BACKUP_EXTENSION}"))
        if not candidates:
            error_exit(f"No backup files found in {cfg.backups_dir}")
        input_file = candidates[-1]
        console.print(f"  Using latest backup: [dim]{input_file}[/dim]")

    if not input_file.exists():
        error_exit(f"Backup file not found: {input_file}")

    if passphrase is None:
        passphrase = typer.prompt("Backup passphrase", hide_input=True)

    assert passphrase is not None
    pp2: str = passphrase
    blob = input_file.read_bytes()
    if len(blob) < 32 + 12:
        error_exit("Backup file is too small / corrupted.")

    salt = blob[:32]
    nonce = blob[32:44]
    ciphertext = blob[44:]

    key = hashlib.scrypt(pp2.encode("utf-8"), salt=salt, n=2**17, r=8, p=1, dklen=32)

    try:
        plaintext = decrypt(nonce, ciphertext, key)
    except Exception:
        error_exit("Failed to decrypt backup — wrong passphrase or corrupted file.")

    # Validate header
    if not plaintext.startswith(BACKUP_MAGIC):
        error_exit("Invalid backup file (bad magic bytes).")

    version = struct.unpack("<Q", plaintext[4:12])[0]
    if version != BACKUP_VERSION:
        error_exit(f"Unsupported backup version: {version}")

    try:
        payload = json.loads(plaintext[12:].decode("utf-8"))
    except Exception as exc:
        error_exit(f"Failed to parse backup payload: {exc}")

    db = get_db(cfg)
    storage = get_active_backend(cfg)

    try:
        anyio.run(_restore_payload, payload, db, storage, merge)
    except SshineError as exc:
        error_exit(str(exc))

    console.print(
        Panel(
            f"  Servers:   {len(payload.get('servers', []))}\n"
            f"  Secrets:   {len(payload.get('secrets', []))}\n"
            f"  Templates: {len(payload.get('templates', []))}",
            title="[bold green]✓ Restored[/bold green]",
            border_style="green",
        )
    )

    if not no_delete:
        if Confirm.ask(f"Delete backup file [dim]{input_file}[/dim]?", default=True):
            input_file.unlink()
            console.print("  [green]✓[/green] Backup file deleted.")


async def _restore_payload(payload, db, storage, merge: bool) -> None:
    from sshine.exceptions import ServerAlreadyExistsError

    # Groups
    for g in payload.get("groups", []):
        await db.create_group(g["name"], g.get("description"))

    # Servers
    for s in payload.get("servers", []):
        group_id = None
        if s.get("group"):
            grp = await db.get_group(s["group"]) or await db.create_group(s["group"])
            group_id = grp.id
        try:
            await db.create_server(
                name=s["name"],
                host=s["host"],
                port=s.get("port", 22),
                user=s.get("user", "root"),
                group_id=group_id,
                auth_ref=s.get("auth_ref"),
                key_path=s.get("key_path"),
                tags=s.get("tags", []),
            )
        except ServerAlreadyExistsError:
            if not merge:
                await db.update_server(
                    s["name"],
                    host=s["host"],
                    port=s.get("port", 22),
                    user=s.get("user", "root"),
                    group_id=group_id,
                    auth_ref=s.get("auth_ref"),
                    key_path=s.get("key_path"),
                )

    # Secrets
    for sec in payload.get("secrets", []):
        storage.set(sec["key"], sec["value"])

    # Templates
    for t in payload.get("templates", []):
        group_id = None
        if t.get("group"):
            grp = await db.get_group(t["group"]) or await db.create_group(t["group"])
            group_id = grp.id
        await db.save_template(t["name"], t["body"], group_id=group_id)
