from __future__ import annotations


class SshineError(Exception):
    """Base exception for all sshine errors."""


class StorageError(SshineError):
    """Storage backend error."""


class SecretNotFoundError(StorageError):
    """Secret key not found in storage."""

    def __init__(self, key: str) -> None:
        super().__init__(f"Secret not found: {key!r}")
        self.key = key


class DecryptionError(StorageError):
    """Failed to decrypt a secret — wrong key or corrupted data."""


class ServerNotFoundError(SshineError):
    def __init__(self, name: str) -> None:
        super().__init__(f"Server not found: {name!r}")
        self.name = name


class ServerAlreadyExistsError(SshineError):
    def __init__(self, name: str) -> None:
        super().__init__(f"Server already exists: {name!r}")
        self.name = name


class GroupNotFoundError(SshineError):
    def __init__(self, name: str) -> None:
        super().__init__(f"Group not found: {name!r}")
        self.name = name


class KeyNotFoundError(SshineError):
    def __init__(self, name: str) -> None:
        super().__init__(f"SSH key not found: {name!r}")
        self.name = name


class SshineConnectionError(SshineError):
    """SSH connection failed."""


class TemplateValidationError(SshineError):
    """Template YAML is invalid."""


class TemplateJinja2RequiredError(SshineError):
    """Template uses Jinja2 syntax but jinja2 is not installed."""

    def __init__(self) -> None:
        super().__init__(
            "This template uses Jinja2 syntax ({% %} blocks).\nInstall Jinja2 to use it:\n\n  uv add jinja2\n  # or: pip install jinja2",
        )


class BackupError(SshineError):
    """Backup/restore error."""


class BackupCorruptError(BackupError):
    """Backup file is corrupted or has invalid magic bytes."""


class BackupVersionError(BackupError):
    """Backup file version is unsupported."""

    def __init__(self, version: int) -> None:
        super().__init__(f"Unsupported backup version: {version}")
        self.version = version


class NotInitialisedError(SshineError):
    """sshine has not been initialised yet. Run `sshine init` first."""

    def __init__(self) -> None:
        super().__init__(
            "sshine is not initialised. Run `sshine init` to get started.",
        )
