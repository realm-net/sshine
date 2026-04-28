# Command Reference

## Core

```
sshine init                          Initialise sshine

sshine add <name>                    Add a server
  -h, --host <host>                    Hostname or IP (required)
  -P, --port <port>                    Port (default: 22)
  -u, --user <user>                    SSH user (default: root)
  -p, --password                       Prompt for password
  --key <name|path>                    Use an existing key
  --keygen [m=method] [n=name]         Generate a key pair
  -g, --group <group>                  Group
  --tag <tag>                          Tag (repeatable)
  -t, --template <name>                Run init template after adding

sshine rm <name>                     Remove a server
  -y, --yes                            Skip confirmation

sshine connect <name>                Open an SSH session
```

## Listing

```
sshine list                          Server table
  -g, --group <group>                  Filter by group
  -t, --tag <tag>                      Filter by tag
  -w, --wide                           Wide mode (key, auth info)

sshine tree                          Server tree
  -g, --group <group>                  Filter by group
  -t, --tag <tag>                      Filter by tag
```

## Storage

```
sshine storage                       Show current backend info
sshine storage <name>                Show info for a specific backend

sshine storage use <backend>         Switch backend
                                       keyring | sshine-keychain

sshine storage migrate <src> <dst>   Migrate secrets
  --dry-run                            Preview without changes

sshine storage purge <name>          Delete all secrets from a backend
  -y, --yes                            Skip confirmation
```

## Backups

```
sshine backup                        Create an encrypted backup
  -o, --output <path>                  Output path (default: ~/.sshine/backups/)
  -p, --passphrase <pass>              Encryption passphrase

sshine restore                       Restore from a backup
  -i, --input <path>                   File path (or 'latest')
  -p, --passphrase <pass>              Passphrase
  --no-delete                          Keep the file after restore
  --merge                              Skip conflicting servers
```

## Templates

```
sshine template create <name>        Register a template
  -i, --input <file>                   .inittmp file (required)
  -g, --group <group>                  Group

sshine template list                 List all templates

sshine template show <name>          Show template body

sshine template run <name>           Run a template
  --server <name>                      Target server (required)
  --var <key=value>                    Override a variable (repeatable)
  --dry-run                            Preview steps without executing

sshine template delete <name>        Delete a template
  -y, --yes                            Skip confirmation
```

---

← [Back to contents](./readme.md)
