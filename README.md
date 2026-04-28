[![Version](https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2Frealm-net%2Fsshine%2Fmain%2Fpyproject.toml&query=%24.project.version&label=version&style=flat&logo=github)](https://github.com/realm-net/sshine/releases)
[![Python](https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2Frealm-net%2Fsshine%2Fmain%2Fpyproject.toml&query=%24.project.requires-python&label=python&style=flat&logo=python&logoColor=white)](https://python.org)
![basedpyright](https://img.shields.io/badge/typecheck-basedpyright-8A2BE2?style=flat)
![ruff](https://img.shields.io/badge/lint-ruff-FCFD00?style=flat)
[![Realm Network](https://img.shields.io/badge/by-Realm%20Network-111111?style=flat&logo=github&logoColor=white)](https://github.com/realm-net)

# sshine

A CLI tool for SSH server management — store connections, manage keys, and provision servers from templates.

---

## Features

- **Server registry** — store servers with host, port, user, group, tags, and auth credentials; connect with a single command
- **SSH key management** — generate, store, and authorize Ed25519/RSA keys; keys are organized by name and kept locally
- **Credential storage** — secrets are kept in the OS keyring (Windows Credential Manager, macOS Keychain, Linux Secret Service) or in a local AES-256-GCM encrypted keychain when no keyring is available
- **Groups & tags** — organize servers into named groups and tag them for filtered listing
- **Provisioning templates** — declarative YAML templates with steps like `shell`, `user.create`, `ssh.keygen`, `package.install`, `docker.install`; supports Jinja2 expressions and per-step conditions
- **Encrypted backup / restore** — export the entire database and keychain to a passphrase-protected archive
- **No cloud dependency** — everything stays on your machine; sshine never phones home

---

## Install

### Linux / macOS

```sh
curl -fsSL https://github.com/realm-net/sshine/releases/latest/download/install-release.sh | sh
```

### Windows (PowerShell)

```powershell
irm https://github.com/realm-net/sshine/releases/latest/download/install-release.ps1 | iex
```

### From source

Requires Python ≥ 3.14 and [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/realm-net/sshine
cd sshine
uv sync
uv run sshine --help
```

---

## Quick start

```sh
# First-time setup: choose a credential backend and create the database
sshine init

# Add a server
sshine add prod-web --host 203.0.113.10 --user deploy --key ~/.ssh/id_ed25519

# Connect
sshine prod-web

# List servers
sshine ls

# Add a server to a group
sshine add staging-db --host 203.0.113.20 --group staging

# List servers in a group
sshine ls --group staging
```

---

## Command reference

| Command | Description |
|---|---|
| `sshine init` | Initialize config, database, and storage backend |
| `sshine add <name>` | Add a server |
| `sshine connect <name>` | Open an SSH session |
| `sshine ls` | List servers |
| `sshine rm <name>` | Remove a server |
| `sshine edit <name>` | Update server fields |
| `sshine show <name>` | Show server details |
| `sshine group add <name>` | Create a group |
| `sshine group ls` | List groups |
| `sshine key gen <name>` | Generate an SSH keypair |
| `sshine key ls` | List stored keys |
| `sshine key authorize <key> <server>` | Push a public key to a server |
| `sshine template add <name>` | Import a provisioning template |
| `sshine template run <template> <server>` | Run a template against a server |
| `sshine template ls` | List templates |
| `sshine backup` | Export encrypted backup |
| `sshine restore <file>` | Restore from backup |
| `sshine storage use <backend>` | Switch credential backend |

---

## Provisioning templates

Templates are YAML files (`.inittmp`) that describe a sequence of steps to run on a remote server over SSH.

```yaml
name: base-setup
description: Install essentials and create deploy user

vars:
  deploy_user: deploy

steps:
  - name: Create deploy user
    action: user.create
    username: "{{ deploy_user }}"

  - name: Install packages
    action: package.install
    packages: [git, curl, htop]

  - name: Install Docker
    action: docker.install
    compose: true

  - name: Authorize key
    action: ssh.authorize
    key: my-key
    user: "{{ deploy_user }}"
```

Run it:

```sh
sshine template run base-setup prod-web
```

Override a variable at runtime:

```sh
sshine template run base-setup prod-web --var deploy_user=ubuntu
```

### Built-in actions

| Action | Description |
|---|---|
| `shell` | Run an arbitrary shell command |
| `user.create` | Create a Linux user with home directory |
| `ssh.keygen` | Generate a keypair and authorize it on the server |
| `ssh.authorize` | Push an existing local key to the server |
| `package.install` | Install packages (auto-detects apt / dnf / yum) |
| `docker.install` | Install Docker Engine via get.docker.com |

---

> *made with ♥  by [Realm Network](https://github.com/realm-net)*
