from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import aiosqlite

from sshine.exceptions import (
    GroupNotFoundError,
    ServerAlreadyExistsError,
    ServerNotFoundError,
)

_SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS groups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    description TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS servers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    host        TEXT    NOT NULL,
    port        INTEGER NOT NULL DEFAULT 22,
    user        TEXT    NOT NULL DEFAULT 'root',
    group_id    INTEGER REFERENCES groups(id) ON DELETE SET NULL,
    auth_ref    TEXT,
    key_path    TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tags (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT    NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS server_tags (
    server_id INTEGER NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    tag_id    INTEGER NOT NULL REFERENCES tags(id)    ON DELETE CASCADE,
    PRIMARY KEY (server_id, tag_id)
);

CREATE TABLE IF NOT EXISTS templates (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    group_id    INTEGER REFERENCES groups(id) ON DELETE SET NULL,
    source_path TEXT,
    body        TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


@dataclass
class Group:
    id: int | None
    name: str
    description: str | None
    created_at: str = ""


@dataclass
class Server:
    id: int | None
    name: str
    host: str
    port: int
    user: str
    group_id: int | None = None
    auth_ref: str | None = None
    key_path: str | None = None
    created_at: str = ""
    updated_at: str = ""
    tags: list[str] = field(default_factory=list)
    group_name: str | None = None


@dataclass
class Template:
    id: int | None
    name: str
    body: str
    group_id: int | None = None
    source_path: str | None = None
    created_at: str = ""
    group_name: str | None = None


class Database:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    async def initialise(self) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.executescript(_SCHEMA)
            await db.commit()

    async def create_group(self, name: str, description: str | None = None) -> Group:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            await db.execute(
                "INSERT OR IGNORE INTO groups (name, description) VALUES (?, ?)",
                (name, description),
            )
            await db.commit()
            row = await (
                await db.execute(
                    "SELECT id, name, description, created_at FROM groups WHERE name = ?",
                    (name,),
                )
            ).fetchone()
        if row is None:
            raise RuntimeError(f"Group '{name}' not found after insert")
        return Group(*row)

    async def get_group(self, name: str) -> Group | None:
        async with aiosqlite.connect(self._db_path) as db:
            row = await (
                await db.execute(
                    "SELECT id, name, description, created_at FROM groups WHERE name = ?",
                    (name,),
                )
            ).fetchone()
        return Group(*row) if row else None

    async def list_groups(self) -> list[Group]:
        async with aiosqlite.connect(self._db_path) as db:
            rows = await (
                await db.execute(
                    "SELECT id, name, description, created_at FROM groups ORDER BY name",
                )
            ).fetchall()
        return [Group(*r) for r in rows]

    async def create_server(
        self,
        name: str,
        host: str,
        port: int,
        user: str,
        group_id: int | None = None,
        auth_ref: str | None = None,
        key_path: str | None = None,
        tags: list[str] | None = None,
    ) -> Server:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")

            existing = await (
                await db.execute(
                    "SELECT id FROM servers WHERE name = ?",
                    (name,),
                )
            ).fetchone()
            if existing:
                raise ServerAlreadyExistsError(name)

            await db.execute(
                """
                INSERT INTO servers (name, host, port, user, group_id, auth_ref, key_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (name, host, port, user, group_id, auth_ref, key_path),
            )

            server_row = await (
                await db.execute(
                    "SELECT id, name, host, port, user, group_id, auth_ref, key_path, created_at, updated_at FROM servers WHERE name = ?",
                    (name,),
                )
            ).fetchone()
            if server_row is None:
                raise RuntimeError(f"Server '{name}' not found after insert")
            server_id = server_row[0]

            if tags:
                for tag in tags:
                    await db.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
                    tag_row = await (
                        await db.execute(
                            "SELECT id FROM tags WHERE name = ?",
                            (tag,),
                        )
                    ).fetchone()
                    if tag_row is None:
                        continue
                    await db.execute(
                        "INSERT OR IGNORE INTO server_tags (server_id, tag_id) VALUES (?, ?)",
                        (server_id, tag_row[0]),
                    )

            await db.commit()

        return await self.get_server(name)  # type: ignore[return-value]

    async def get_server(self, name: str) -> Server | None:
        async with aiosqlite.connect(self._db_path) as db:
            row = await (
                await db.execute(
                    """
                SELECT s.id, s.name, s.host, s.port, s.user,
                       s.group_id, s.auth_ref, s.key_path, s.created_at, s.updated_at,
                       g.name AS group_name
                FROM servers s
                LEFT JOIN groups g ON g.id = s.group_id
                WHERE s.name = ?
                """,
                    (name,),
                )
            ).fetchone()
            if row is None:
                return None
            server = Server(
                id=row[0],
                name=row[1],
                host=row[2],
                port=row[3],
                user=row[4],
                group_id=row[5],
                auth_ref=row[6],
                key_path=row[7],
                created_at=row[8],
                updated_at=row[9],
                group_name=row[10],
            )
            tag_rows = await (
                await db.execute(
                    """
                SELECT t.name FROM tags t
                JOIN server_tags st ON st.tag_id = t.id
                WHERE st.server_id = ?
                ORDER BY t.name
                """,
                    (server.id,),
                )
            ).fetchall()
            server.tags = [r[0] for r in tag_rows]
        return server

    async def list_servers(
        self,
        group: str | None = None,
        tag: str | None = None,
    ) -> list[Server]:
        async with aiosqlite.connect(self._db_path) as db:
            where_parts: list[str] = []
            params: list = []

            if group:
                where_parts.append("g.name = ?")
                params.append(group)
            if tag:
                where_parts.append(
                    "EXISTS (SELECT 1 FROM server_tags st2 JOIN tags t2 ON t2.id = st2.tag_id WHERE st2.server_id = s.id AND t2.name = ?)",
                )
                params.append(tag)

            where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

            rows = await (
                await db.execute(
                    f"""
                SELECT s.id, s.name, s.host, s.port, s.user,
                       s.group_id, s.auth_ref, s.key_path, s.created_at, s.updated_at,
                       g.name AS group_name
                FROM servers s
                LEFT JOIN groups g ON g.id = s.group_id
                {where_clause}
                ORDER BY g.name NULLS LAST, s.name
                """,
                    params,
                )
            ).fetchall()

            servers: list[Server] = []
            for row in rows:
                srv = Server(
                    id=row[0],
                    name=row[1],
                    host=row[2],
                    port=row[3],
                    user=row[4],
                    group_id=row[5],
                    auth_ref=row[6],
                    key_path=row[7],
                    created_at=row[8],
                    updated_at=row[9],
                    group_name=row[10],
                )
                tag_rows = await (
                    await db.execute(
                        """
                    SELECT t.name FROM tags t
                    JOIN server_tags st ON st.tag_id = t.id
                    WHERE st.server_id = ?
                    ORDER BY t.name
                    """,
                        (srv.id,),
                    )
                ).fetchall()
                srv.tags = [r[0] for r in tag_rows]
                servers.append(srv)

        return servers

    async def delete_server(self, name: str) -> Server:
        server = await self.get_server(name)
        if server is None:
            raise ServerNotFoundError(name)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            await db.execute("DELETE FROM servers WHERE name = ?", (name,))
            await db.commit()
        return server

    async def update_server(self, name: str, **fields) -> Server:
        allowed = {"host", "port", "user", "group_id", "auth_ref", "key_path"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return await self.get_server(name)  # type: ignore[return-value]

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        params = list(updates.values()) + [name]
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                f"UPDATE servers SET {set_clause}, updated_at = datetime('now') WHERE name = ?",
                params,
            )
            await db.commit()
        return await self.get_server(name)  # type: ignore[return-value]

    async def list_tags(self) -> list[str]:
        async with aiosqlite.connect(self._db_path) as db:
            rows = await (await db.execute("SELECT name FROM tags ORDER BY name")).fetchall()
        return [r[0] for r in rows]

    # Auth refs (for migration)                                          #

    async def list_auth_refs(self) -> list[str]:
        """Return all non-null auth_ref values (for keyring migration)."""
        async with aiosqlite.connect(self._db_path) as db:
            rows = await (
                await db.execute(
                    "SELECT auth_ref FROM servers WHERE auth_ref IS NOT NULL",
                )
            ).fetchall()
        return [r[0] for r in rows]

    async def save_template(self, name: str, body: str, group_id: int | None = None, source_path: str | None = None) -> Template:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO templates (name, body, group_id, source_path)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    body        = excluded.body,
                    group_id    = excluded.group_id,
                    source_path = excluded.source_path
                """,
                (name, body, group_id, source_path),
            )
            await db.commit()
            row = await (
                await db.execute(
                    """
                SELECT t.id, t.name, t.body, t.group_id, t.source_path, t.created_at, g.name
                FROM templates t LEFT JOIN groups g ON g.id = t.group_id
                WHERE t.name = ?
                """,
                    (name,),
                )
            ).fetchone()
        if row is None:
            raise RuntimeError("Template upsert returned no row")
        return Template(id=row[0], name=row[1], body=row[2], group_id=row[3], source_path=row[4], created_at=row[5], group_name=row[6])

    async def get_template(self, name: str) -> Template | None:
        async with aiosqlite.connect(self._db_path) as db:
            row = await (
                await db.execute(
                    """
                SELECT t.id, t.name, t.body, t.group_id, t.source_path, t.created_at, g.name
                FROM templates t LEFT JOIN groups g ON g.id = t.group_id
                WHERE t.name = ?
                """,
                    (name,),
                )
            ).fetchone()
        if row is None:
            return None
        return Template(id=row[0], name=row[1], body=row[2], group_id=row[3], source_path=row[4], created_at=row[5], group_name=row[6])

    async def list_templates(self) -> list[Template]:
        async with aiosqlite.connect(self._db_path) as db:
            rows = await (
                await db.execute(
                    """
                SELECT t.id, t.name, t.body, t.group_id, t.source_path, t.created_at, g.name
                FROM templates t LEFT JOIN groups g ON g.id = t.group_id
                ORDER BY t.name
                """,
                )
            ).fetchall()
        return [Template(id=r[0], name=r[1], body=r[2], group_id=r[3], source_path=r[4], created_at=r[5], group_name=r[6]) for r in rows]

    async def delete_template(self, name: str) -> bool:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute("DELETE FROM templates WHERE name = ?", (name,))
            await db.commit()
        return cursor.rowcount > 0
