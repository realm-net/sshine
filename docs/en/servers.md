# Servers

## Add a Server

```bash
sshine add <name> -h <host> [options]
```

| Option | Description |
|---|---|
| `-h`, `--host` | Hostname or IP address *(required)* |
| `-P`, `--port` | SSH port (default: `22`) |
| `-u`, `--user` | SSH user (default: `root`) |
| `-p`, `--password` | Prompt for password interactively |
| `--key <name/path>` | Use an existing SSH key |
| `--keygen [m=method] [n=name]` | Generate a new key pair |
| `-g`, `--group` | Group (auto-created if it doesn't exist) |
| `--tag <tag>` | Tag — repeatable |
| `-t`, `--template` | Init template to run after adding |

### Examples

```bash
# Password-based server
sshine add vps1 -h 1.2.3.4 -p

# Generate an ed25519 key
sshine add prod -h prod.example.com --keygen m=ed25519 n=prod-key

# Use an existing key
sshine add staging -h 10.0.0.5 --key ~/.ssh/id_rsa

# With group, tags, and a template
sshine add web01 -h 192.168.1.10 --keygen -g production --tag web --tag nginx -t lamp

# RSA key, custom user
sshine add legacy -h old.server.example.com --keygen m=rsa n=legacy-rsa -u deploy
```

## The `--keygen` Option

Generates a key pair and saves it to `~/.sshine/keys/`:

```
--keygen                       → ed25519, name = server name
--keygen m=rsa                 → rsa
--keygen n=mykey               → files: mykey / mykey.pub
--keygen m=ecdsa n=ec-key      → ecdsa, files: ec-key / ec-key.pub
```

Supported methods: `ed25519` (default), `rsa`, `ecdsa`.

## Remove a Server

```bash
sshine rm <name>
sshine rm <name> -y    # skip confirmation
```

The associated secret is automatically deleted from the storage backend.

---

← [Back to contents](./readme.md)
