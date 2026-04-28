from __future__ import annotations

from pathlib import Path

import asyncssh

from sshine.const import DEFAULT_SSH_METHOD, KEYS_DIR, SUPPORTED_KEY_METHODS
from sshine.exceptions import KeyNotFoundError, SshineError


def generate_keypair(
    method: str = DEFAULT_SSH_METHOD,
    name: str | None = None,
    keys_dir: Path = KEYS_DIR,
    passphrase: str | None = None,
) -> tuple[Path, Path]:
    """
    Generate an SSH key pair and write it to *keys_dir*.

    Returns ``(private_key_path, public_key_path)``.
    """
    if method not in SUPPORTED_KEY_METHODS:
        raise SshineError(
            f"Unsupported key method: {method!r}. Supported: {', '.join(SUPPORTED_KEY_METHODS)}",
        )

    keys_dir.mkdir(parents=True, exist_ok=True)

    stem = name or f"sshine_{method}"
    private_path = keys_dir / stem
    public_path = keys_dir / f"{stem}.pub"

    if private_path.exists():
        raise SshineError(f"Key already exists: {private_path}")

    key = asyncssh.generate_private_key(
        alg_name=_alg_name(method),
        comment=f"sshine:{stem}",
    )

    private_path.write_bytes(
        key.export_private_key(
            format_name="openssh",
            passphrase=passphrase,
        ),
    )
    private_path.chmod(0o600)

    public_path.write_text(
        key.export_public_key(format_name="openssh").decode(),
        encoding="utf-8",
    )

    return private_path, public_path


def resolve_key(name_or_path: str, keys_dir: Path = KEYS_DIR) -> Path:
    """
    Resolve a key name or path to an absolute :class:`~pathlib.Path`.

    - If *name_or_path* is an existing file path → return as-is.
    - Else try ``keys_dir / name_or_path`` → return if found.
    - Else raise :class:`~sshine.exceptions.KeyNotFoundError`.
    """
    candidate = Path(name_or_path).expanduser()
    if candidate.exists():
        return candidate

    in_keys_dir = keys_dir / name_or_path
    if in_keys_dir.exists():
        return in_keys_dir

    raise KeyNotFoundError(name_or_path)


def read_public_key(private_key_path: Path) -> str:
    """Return the OpenSSH public key string for a given private key file."""
    pub = private_key_path.with_suffix(".pub")
    if not pub.exists():
        # Derive from private key
        key = asyncssh.read_private_key(str(private_key_path))
        return key.export_public_key(format_name="openssh").decode().strip()
    return pub.read_text(encoding="utf-8").strip()


def _alg_name(method: str) -> str:
    mapping = {
        "ed25519": "ssh-ed25519",
        "rsa": "ssh-rsa",
        "ecdsa": "ecdsa-sha2-nistp256",
    }
    return mapping.get(method, method)
