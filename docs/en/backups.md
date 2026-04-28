# Backups

## Create a Backup

```bash
sshine backup                           # → ~/.sshine/backups/sshine-<date>.ssb
sshine backup -o /path/to/backup.ssb   # custom output path
sshine backup -p "my passphrase"       # set passphrase non-interactively
```

The backup contains: all servers, groups, tags, templates, and **all secrets** (passwords, key passphrases).

### Encryption

Backup files (`.ssb`) are encrypted with AES-256-GCM. The key is derived from your passphrase using scrypt — **not** hardware-bound. Backups can be restored on any machine.

> The passphrase is mandatory. Without it, anyone with access to the file can read all your secrets.

### Integrity

After creation, sshine prints the SHA-256 fingerprint of the output file. Keep it for verification.

---

## Restore from Backup

```bash
sshine restore                             # use the latest backup in ~/.sshine/backups/
sshine restore -i /path/to/backup.ssb     # specific file
sshine restore -i backup.ssb -p "pass"    # pass passphrase directly
sshine restore --no-delete                # keep the file after restore
sshine restore --merge                    # skip conflicting servers instead of overwriting
```

After a successful restore, sshine offers to delete the backup file. Pass `--no-delete` to suppress this.

---

## Moving to a New Machine

```bash
# On the old machine
sshine backup -o transfer.ssb

# Copy the file (scp, USB drive, etc.)

# On the new machine
sshine init
sshine restore -i transfer.ssb
```

---

← [Back to contents](./readme.md)
