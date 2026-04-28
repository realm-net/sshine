# sshine

> Open-source CLI utility for SSH server management.  
> Store servers, keys, and secrets in one place. Connect with a single command.

```
sshine add prod -h 1.2.3.4 --keygen -g production --tag web
sshine connect prod
```

---

## Contents

| | |
|---|---|
| [Installation](./installation.md) | Requirements, `uv sync`, first run |
| [Storage Backends](./storage.md) | `keyring` and `sshine-keychain`, migration, architecture |
| [Servers](./servers.md) | `add`, `rm`, keys, passwords, groups, tags |
| [Listing Servers](./listing.md) | `list`, `tree`, filtering |
| [Init Templates](./templates.md) | `.inittmp` format, actions, Jinja2 |
| [Backups](./backups.md) | `backup`, `restore`, encryption |
| [Command Reference](./reference.md) | All commands and flags |

---

## Quick Start

```bash
# 1. Initialise
sshine init

# 2. Add a server
sshine add prod -h 1.2.3.4 --keygen m=ed25519 n=prod-key -g production

# 3. Connect
sshine connect prod

# 4. View servers
sshine list
sshine tree
```

---

## Community

Questions, ideas, discussion — join the Telegram channel:

**[t.me/sshine_talks](https://t.me/sshine_talks)**
