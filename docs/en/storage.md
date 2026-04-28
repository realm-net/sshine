# Storage Backends

sshine uses two storage layers:

- **`sshine.db`** — a plain SQLite database. Stores server metadata: host, port, user, groups, tags, and a reference to the secret (`auth_ref`). Not encrypted — easy to copy between machines.
- **Secret backend** — stores actual secrets (passwords, key passphrases). `sshine.db` holds only the key name pointing into the backend.

## Backends

| Backend | Description |
|---|---|
| `keyring` | OS system keyring. **Default.** |
| `sshine-keychain` | Own AES-256-GCM store in `~/.sshine/keychain.db`, hardware-bound via HWID. |

**When to use `sshine-keychain`:** Docker containers, headless servers, or any environment where the OS keyring is unavailable.

> **Note:** `keychain.db` is hardware-bound and cannot be directly moved between machines. Use [`sshine backup/restore`](./backups.md) for that.

## Commands

### Info

```bash
# Current backend status
sshine storage

# Inspect a specific backend
sshine storage keyring
sshine storage sshine-keychain
```

### Switch Backend

```bash
sshine storage use sshine-keychain
sshine storage use keyring
```

sshine will offer to migrate existing secrets from the old backend automatically.

### Manual Migration

```bash
# Move all secrets
sshine storage migrate keyring sshine-keychain

# Preview without making changes
sshine storage migrate keyring sshine-keychain --dry-run
```

> The `keyring` backend cannot enumerate its own entries — migration works by reading known `auth_ref` values from `sshine.db`. All secrets belonging to registered servers will be migrated.

### Purge a Backend

```bash
sshine storage purge sshine-keychain
sshine storage purge keyring
```

Deletes all secrets from the specified backend. Asks for confirmation.

---

← [Back to contents](./readme.md)
