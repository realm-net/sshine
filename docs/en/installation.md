# Installation

## Requirements

- Python ≥ 3.14
- [uv](https://docs.astral.sh/uv/) — package manager

## Install

```bash
git clone https://github.com/your-org/sshine
cd sshine
uv sync
```

After syncing, use `uv run sshine` or add `.venv/Scripts` (Windows) / `.venv/bin` (Unix) to your `PATH` to call `sshine` directly.

## Initialise

```bash
sshine init
```

On first run, sshine will:

1. Detect whether a system keyring is available (Windows Credential Manager, macOS Keychain, Linux Secret Service).
2. If no keyring is found, offer `sshine-keychain` as a hardware-bound local fallback.
3. Create the `~/.sshine/` working directory.
4. Initialise the database and config file.
5. Verify the storage backend with a round-trip write/read/delete test.
6. Offer to add your first server.

## Working Directory Layout

```
~/.sshine/
├── config.toml       # settings (storage backend, paths)
├── sshine.db         # servers, groups, tags, templates
├── keychain.db       # encrypted secrets (when sshine-keychain is active)
├── keys/             # SSH keys generated via --keygen
└── backups/          # backup files (.ssb)
```

---

← [Back to contents](./readme.md)
