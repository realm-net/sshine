# Listing Servers

## Table View

```bash
sshine list                    # all servers
sshine list -g production      # filter by group
sshine list -t web             # filter by tag
sshine list -w                 # wide mode: key path, auth type
```

Example output:

```
 Name    Host             Port  User   Group       Tags
─────────────────────────────────────────────────────────
 web01   192.168.1.10     22    root   production  web, nginx
 db01    192.168.1.20     22    root   production  db
 vps1    1.2.3.4          22    user   —           —
```

## Tree View

```bash
sshine tree                    # all servers, grouped
sshine tree -g production      # only group 'production'
sshine tree -t docker          # only servers tagged 'docker'
```

Example output:

```
sshine
├── 󰉋 production
│   ├── web01  root@192.168.1.10:22  🗝 key  #web #nginx
│   └── db01   root@192.168.1.20:22  🔑 pw   #db
└── (ungrouped)
    └── vps1   user@1.2.3.4:22  🗝 key
```

Auth icons: `🗝 key` — SSH key, `🔑 pw` — password.

---

← [Back to contents](./readme.md)
