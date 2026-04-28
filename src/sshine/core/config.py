from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sshine.const import (
    APP_DIR,
    BACKUPS_DIR,
    CONFIG_PATH,
    DB_PATH,
    KEYCHAIN_DB_PATH,
    KEYS_DIR,
    STORAGE_KEYRING,
    STORAGE_OPTIONS,
)
from sshine.exceptions import SshineError


@dataclass
class Config:
    storage_backend: str = STORAGE_KEYRING
    app_dir: Path = field(default_factory=lambda: APP_DIR)
    db_path: Path = field(default_factory=lambda: DB_PATH)
    keychain_db_path: Path = field(default_factory=lambda: KEYCHAIN_DB_PATH)
    keys_dir: Path = field(default_factory=lambda: KEYS_DIR)
    backups_dir: Path = field(default_factory=lambda: BACKUPS_DIR)
    config_path: Path = field(default_factory=lambda: CONFIG_PATH)

    @classmethod
    def load(cls) -> Config:
        """
        Load config from ``~/.sshine/config.toml``.

        Returns defaults if the file does not exist yet.
        Directory structure is created on first call.
        """
        cfg = cls()
        cfg._ensure_dirs()

        if not cfg.config_path.exists():
            return cfg

        try:
            with cfg.config_path.open("rb") as fh:
                data: dict[str, Any] = tomllib.load(fh)
        except Exception as exc:
            raise SshineError(f"Failed to read config: {exc}") from exc

        storage_section = data.get("storage", {})
        backend = storage_section.get("backend", STORAGE_KEYRING)
        if backend not in STORAGE_OPTIONS:
            raise SshineError(
                f"Unknown storage backend in config: {backend!r}. Valid options: {', '.join(STORAGE_OPTIONS)}",
            )
        cfg.storage_backend = backend

        paths_section = data.get("paths", {})
        if app_dir := paths_section.get("app_dir"):
            cfg.app_dir = Path(app_dir).expanduser()
            cfg.db_path = cfg.app_dir / "sshine.db"
            cfg.keychain_db_path = cfg.app_dir / "keychain.db"
            cfg.keys_dir = cfg.app_dir / "keys"
            cfg.backups_dir = cfg.app_dir / "backups"
            cfg.config_path = cfg.app_dir / "config.toml"

        cfg._ensure_dirs()
        return cfg

    def save(self) -> None:
        """Write current config to ``config.toml`` (TOML format)."""
        self._ensure_dirs()
        # Use forward slashes — TOML treats backslash as escape character
        app_dir_str = str(self.app_dir).replace("\\", "/")
        content = f'[storage]\nbackend = "{self.storage_backend}"\n\n[paths]\napp_dir = "{app_dir_str}"\n'
        self.config_path.write_text(content, encoding="utf-8")

    @property
    def is_initialised(self) -> bool:
        """True if the app directory and database file both exist."""
        return self.config_path.exists() and self.db_path.exists()

    def _ensure_dirs(self) -> None:
        for directory in (self.app_dir, self.keys_dir, self.backups_dir):
            directory.mkdir(parents=True, exist_ok=True)
