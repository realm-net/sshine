from __future__ import annotations

from pathlib import Path

KEYRING_SERVICE_NAME = "sshine"

APP_DIR = Path("~/.sshine").expanduser()
DB_PATH = APP_DIR / "sshine.db"
KEYCHAIN_DB_PATH = APP_DIR / "keychain.db"
CONFIG_PATH = APP_DIR / "config.toml"
KEYS_DIR = APP_DIR / "keys"
BACKUPS_DIR = APP_DIR / "backups"

STORAGE_KEYRING = "keyring"
STORAGE_KEYCHAIN = "sshine-keychain"
STORAGE_OPTIONS = (STORAGE_KEYRING, STORAGE_KEYCHAIN)

DEFAULT_SSH_METHOD = "ed25519"
DEFAULT_SSH_USER = "root"
DEFAULT_SSH_PORT = 22

SUPPORTED_KEY_METHODS = ("ed25519", "rsa", "ecdsa")

BACKUP_MAGIC = b"SSNB"
BACKUP_VERSION = 1
BACKUP_EXTENSION = ".ssb"
