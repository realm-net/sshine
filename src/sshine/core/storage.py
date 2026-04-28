from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import keyring as _keyring

from sshine.const import KEYRING_SERVICE_NAME, STORAGE_KEYCHAIN, STORAGE_KEYRING
from sshine.core.config import Config
from sshine.core.hwid import HWIDManager
from sshine.core.keychain import SshineKeychain
from sshine.exceptions import SecretNotFoundError, SshineError


@runtime_checkable
class StorageBackend(Protocol):
    """Common interface for secret storage backends."""

    @property
    def name(self) -> str: ...

    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str) -> None: ...
    def delete(self, key: str) -> None: ...

    def list_all(self) -> list[tuple[str, str]]:
        """Return ``[(key, plaintext_value), ...]`` for all known entries."""
        ...

    def purge(self) -> int:
        """Delete all sshine entries.  Returns count deleted."""
        ...

    def count(self) -> int: ...

    def is_available(self) -> bool: ...


class KeyringBackend:
    """OS keyring backend (Windows Credential Manager / macOS Keychain / Secret Service)."""

    name = STORAGE_KEYRING

    def get(self, key: str) -> str | None:
        return _keyring.get_password(KEYRING_SERVICE_NAME, key)

    def set(self, key: str, value: str) -> None:
        _keyring.set_password(KEYRING_SERVICE_NAME, key, value)

    def delete(self, key: str) -> None:
        try:
            _keyring.delete_password(KEYRING_SERVICE_NAME, key)
        except Exception as exc:  # keyring.errors.PasswordDeleteError
            raise SecretNotFoundError(key) from exc

    def list_all(self) -> list[tuple[str, str]]:
        # The keyring library has no portable enumerate API.
        # Callers that need enumerate (e.g. migration) must supply a list of
        # known keys obtained from the sshine.db auth_ref column.
        raise NotImplementedError(
            "The OS keyring backend does not support listing all secrets. Migration from 'keyring' enumerates known auth_ref keys from sshine.db.",
        )

    def purge(self) -> int:
        raise NotImplementedError(
            "The OS keyring backend does not support bulk purge. Use `sshine storage purge keyring` which will enumerate keys from sshine.db.",
        )

    def count(self) -> int:
        return -1  # unknown

    def is_available(self) -> bool:
        try:
            backend = _keyring.get_keyring()
            # Fail-safe backends (e.g. chainer with only null backend) are not useful
            return "fail" not in type(backend).__name__.lower() and "null" not in type(backend).__name__.lower()
        except Exception:
            return False


# sshine-keychain backend                                              #


class KeychainBackend:
    """sshine's own AES-256-GCM encrypted SQLite backend."""

    name = STORAGE_KEYCHAIN

    def __init__(self, cfg: Config) -> None:
        key = HWIDManager().get_encryption_key()
        self._kc = SshineKeychain(cfg.keychain_db_path, key)

    def get(self, key: str) -> str | None:
        return self._kc.get_password(KEYRING_SERVICE_NAME, key)

    def set(self, key: str, value: str) -> None:
        self._kc.set_password(KEYRING_SERVICE_NAME, key, value)

    def delete(self, key: str) -> None:
        self._kc.delete_password(KEYRING_SERVICE_NAME, key)

    def list_all(self) -> list[tuple[str, str]]:
        entries = self._kc.list_all(KEYRING_SERVICE_NAME)
        return [(key, value) for _svc, key, value in entries]

    def purge(self) -> int:
        return self._kc.purge(KEYRING_SERVICE_NAME)

    def count(self) -> int:
        return self._kc.count(KEYRING_SERVICE_NAME)

    def is_available(self) -> bool:
        try:
            self._kc.count()
            return True
        except Exception:
            return False


def get_active_backend(cfg: Config) -> KeyringBackend | KeychainBackend:
    """Instantiate and return the configured storage backend."""
    if cfg.storage_backend == STORAGE_KEYCHAIN:
        return KeychainBackend(cfg)
    if cfg.storage_backend == STORAGE_KEYRING:
        return KeyringBackend()
    raise SshineError(f"Unknown storage backend: {cfg.storage_backend!r}")


@dataclass
class MigrationResult:
    migrated: int
    errors: list[str]

    @property
    def success(self) -> bool:
        return not self.errors


def migrate(
    src: KeyringBackend | KeychainBackend,
    dst: KeyringBackend | KeychainBackend,
    *,
    known_keys: list[str] | None = None,
    dry_run: bool = False,
) -> MigrationResult:
    """
    Copy all secrets from *src* to *dst*.

    When *src* is a :class:`KeyringBackend` (which cannot enumerate its own
    entries), *known_keys* must be supplied — typically the ``auth_ref`` column
    values collected from ``sshine.db``.
    """
    migrated = 0
    errors: list[str] = []

    if isinstance(src, KeyringBackend):
        if not known_keys:
            return MigrationResult(
                migrated=0,
                errors=["keyring backend requires known_keys for migration (pass auth_ref values from sshine.db)"],
            )
        entries = []
        for key in known_keys:
            value = src.get(key)
            if value is not None:
                entries.append((key, value))
    else:
        entries = src.list_all()

    for key, value in entries:
        try:
            if not dry_run:
                dst.set(key, value)
            migrated += 1
        except Exception as exc:
            errors.append(f"{key}: {exc}")

    return MigrationResult(migrated=migrated, errors=errors)
