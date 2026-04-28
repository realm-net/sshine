from __future__ import annotations

import sqlite3
from pathlib import Path

from sshine.const import KEYRING_SERVICE_NAME
from sshine.crypto.aes import decrypt, encrypt
from sshine.exceptions import DecryptionError, SecretNotFoundError

_SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    key         TEXT NOT NULL,
    service     TEXT NOT NULL,
    nonce       BLOB NOT NULL,
    ciphertext  BLOB NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (key, service)
);
"""


class SshineKeychain:
    """
    Local AES-256-GCM encrypted key-value store backed by SQLite.

    This is the *sshine-keychain* storage backend — a fallback for systems
    that lack a native OS keyring.  Secrets are encrypted with a key derived
    from the machine's hardware identity via :class:`~sshine.core.hwid.HWIDManager`.
    """

    def __init__(self, db_path: Path, encryption_key: bytes) -> None:
        self._db_path = db_path
        self._key = encryption_key
        self._init_db()

    # Public API (mirrors keyring interface)                               #

    def get_password(self, service: str, username: str) -> str | None:
        row = self._fetchone(
            "SELECT nonce, ciphertext FROM entries WHERE service = ? AND key = ?",
            (service, username),
        )
        if row is None:
            return None
        nonce, ciphertext = row
        try:
            return decrypt(bytes(nonce), bytes(ciphertext), self._key).decode("utf-8")
        except DecryptionError:
            return None

    def set_password(self, service: str, username: str, password: str) -> None:
        nonce, ciphertext = encrypt(password.encode("utf-8"), self._key)
        self._execute(
            """
            INSERT INTO entries (key, service, nonce, ciphertext)
                VALUES (?, ?, ?, ?)
            ON CONFLICT(key, service) DO UPDATE SET
                nonce      = excluded.nonce,
                ciphertext = excluded.ciphertext,
                updated_at = datetime('now')
            """,
            (username, service, nonce, ciphertext),
        )

    def delete_password(self, service: str, username: str) -> None:
        changes = self._execute(
            "DELETE FROM entries WHERE service = ? AND key = ?",
            (service, username),
        )
        if changes == 0:
            raise SecretNotFoundError(f"{service}/{username}")

    def list_all(self, service: str = KEYRING_SERVICE_NAME) -> list[tuple[str, str, str]]:
        """
        Return all ``(service, key, plaintext)`` entries for *service*.

        Used during storage migration.
        """
        rows = self._fetchall(
            "SELECT service, key, nonce, ciphertext FROM entries WHERE service = ?",
            (service,),
        )
        result: list[tuple[str, str, str]] = []
        for svc, key, nonce, ciphertext in rows:
            try:
                value = decrypt(bytes(nonce), bytes(ciphertext), self._key).decode("utf-8")
                result.append((svc, key, value))
            except DecryptionError:
                continue
        return result

    def import_all(self, entries: list[tuple[str, str, str]]) -> None:
        """Insert ``(service, key, plaintext)`` tuples in bulk."""
        for service, key, value in entries:
            self.set_password(service, key, value)

    def purge(self, service: str = KEYRING_SERVICE_NAME) -> int:
        """Delete all entries for *service*.  Returns the count deleted."""
        return self._execute(
            "DELETE FROM entries WHERE service = ?",
            (service,),
        )

    def count(self, service: str = KEYRING_SERVICE_NAME) -> int:
        row = self._fetchone(
            "SELECT COUNT(*) FROM entries WHERE service = ?",
            (service,),
        )
        return row[0] if row else 0

    # Internal SQLite helpers (synchronous)                                #

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    def _execute(self, sql: str, params: tuple = ()) -> int:
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor.rowcount

    def _fetchone(self, sql: str, params: tuple = ()) -> tuple | None:
        with sqlite3.connect(self._db_path) as conn:
            return conn.execute(sql, params).fetchone()

    def _fetchall(self, sql: str, params: tuple = ()) -> list[tuple]:
        with sqlite3.connect(self._db_path) as conn:
            return conn.execute(sql, params).fetchall()
